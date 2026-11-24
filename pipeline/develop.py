"""NEF -> 신문 게재용 JPG. 장면별 룩(looks/edits.tsv)을 적용한다.
보도사진 원칙: 전역 톤·색, 크롭만 쓴다. 국소 합성이나 객체 제거는 하지 않는다.
usage: python3 -I develop.py <nef_dir> <out_dir> <edits.tsv> [name ...]
"""
import sys, os, math, numpy as np, cv2, rawpy
from PIL import Image, ImageCms
from concurrent.futures import ProcessPoolExecutor

# ---- 룩 정의 -------------------------------------------------------------
# wb: 중화 강도(0=현장광 유지, 1=완전 중화), tint: 최종 RGB 배율(따뜻/차가움)
# key: 중간톤 목표(선형), clarity: 국소 대비, matte: 블랙 리프트, vign: 비네팅
# hsl: (중심 hue°, 폭°, hue 이동°, 채도 배율) 목록, sat: 전역 채도
LOOKS = {
    "hardwood":  dict(wb=0.45, tint=(1.03, 1.00, 0.97), mid=0.45, contrast=0.35, clarity=0.30, matte=0.015, vign=0.18, sat=0.95,
                      hsl=[(45, 25, 0, 0.80), (20, 15, 4, 0.92)]),
    "rainpitch": dict(wb=0.50, tint=(0.97, 1.00, 1.04), mid=0.44, contrast=0.30, clarity=0.28, matte=0.030, vign=0.12, sat=0.93,
                      hsl=[(110, 35, -6, 0.72), (30, 15, 0, 1.10), (0, 12, 0, 1.05)]),
    "arena":     dict(wb=0.20, tint=(0.97, 1.00, 1.04), mid=0.28, contrast=0.35, clarity=0.22, matte=0.000, vign=0.20, sat=0.95,
                      hsl=[(200, 40, 0, 1.06), (20, 18, 3, 0.90)]),
    # 21번(PT1_0253) 전용: 기자가 카메라 원본 색감(어둡고 따뜻하고 블랙이 깊음)을 선호 → 리프트·매트·차가운 틴트 제거
    "arena_cam": dict(wb=0.00, tint=(0.98, 1.00, 0.99), mid=0.245, contrast=0.40, clarity=0.18, matte=0, vign=0.15, sat=1.00, lift=1.0,
                      hsl=[(120, 30, 0, 1.06)]),
    "victory":   dict(wb=0.25, tint=(1.06, 1.00, 0.92), mid=0.42, contrast=0.35, clarity=0.22, matte=0.010, vign=0.16, sat=0.98,
                      hsl=[(320, 30, 0, 0.65), (8, 14, 5, 0.88), (50, 15, 0, 1.10)]),
    "redstage":  dict(wb=0.00, tint=(1.00, 1.00, 1.00), mid=0.30, contrast=0.45, clarity=0.20, matte=0.000, vign=0.12, sat=0.95,
                      hsl=[(5, 22, 6, 0.85), (340, 18, 5, 0.85)]),
    "cleantech": dict(wb=0.80, tint=(1.00, 1.00, 1.00), mid=0.48, contrast=0.30, clarity=0.25, matte=0.010, vign=0.08, sat=1.00,
                      hsl=[(115, 30, 0, 0.85)]),
    "campus":    dict(wb=0.70, tint=(1.00, 1.00, 1.00), mid=0.45, contrast=0.25, clarity=0.20, matte=0.010, vign=0.05, sat=1.00, hsl=[]),
}
# mid: 중앙 가중 중간톤의 '표시값' 목표(0..1). 무드 장면은 낮게.
NEWSPRINT_MID_LIFT = 0.92   # 출력 감마(<1이면 밝아짐): 망점 확대 선보상
OUT_SHARP = 0.65            # 신문 출력 샤프닝 양

def luma(x): return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]

def wb_gains(img, strength):
    """partial_wb 와 같은 수식으로 이득만 계산(측광 영역과 적용 영역 분리용)."""
    if strength <= 0: return np.ones(3, np.float32)
    y = luma(img); m = (y > np.percentile(y, 20)) & (y < np.percentile(y, 90))
    mean = img[m].mean(0) + 1e-6
    return ((mean.mean() / mean) ** strength).astype(np.float32)

def partial_wb(img, strength):
    if strength <= 0: return img
    y = luma(img); m = (y > np.percentile(y, 20)) & (y < np.percentile(y, 90))
    mean = img[m].mean(0) + 1e-6
    gains = (mean.mean() / mean) ** strength
    return img * gains

def tonemap(x):  # ACES fitted (Narkowicz), 하이라이트 롤오프
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)

def srgb_oetf(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0.0031308, None), 1 / 2.4) - 0.055)

def hsl_adjust(rgb, bands, sat):
    hsv = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2HSV)  # H 0..360, S,V 0..1
    h, s = hsv[..., 0], hsv[..., 1]
    s_mul = np.full_like(s, sat); h_add = np.zeros_like(h)
    for c, w, dh, ds in bands:
        d = np.abs(((h - c + 180) % 360) - 180)
        wgt = np.exp(-0.5 * (d / (w / 2)) ** 2) * np.clip(s * 3, 0, 1)  # 무채색엔 영향 줄임
        s_mul *= 1 + (ds - 1) * wgt; h_add += dh * wgt
    hsv[..., 0] = (h + h_add) % 360
    s2 = s * s_mul
    hsv[..., 1] = np.where(s2 > 0.8, 0.8 + (s2 - 0.8) * 0.4, s2).clip(0, 1)  # 신문 색역 압축
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

def denoise(rgb, iso):
    if iso < 800: return rgb
    ycc = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2YCrCb)
    tiers = [(1600, 1.5, 3), (3200, 2.5, 5), (6400, 3.5, 8), (10**9, 5.0, 11)]
    cs, h = next((c, hh) for lim, c, hh in tiers if iso < lim)
    for c in (1, 2): ycc[..., c] = cv2.GaussianBlur(ycc[..., c], (0, 0), cs)
    y8 = (ycc[..., 0].clip(0, 1) * 255).astype(np.uint8)
    yd = cv2.fastNlMeansDenoising(y8, None, h, 5, 15).astype(np.float32) / 255
    ycc[..., 0] = ycc[..., 0] + (yd - y8 / 255.0)  # 디테일 보존형 잔차 적용
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB)

def develop(args):
    nef, out, look_name, crop, meter = args
    L = LOOKS[look_name]
    with rawpy.imread(nef) as raw:
        iso = 0
        try:
            import exifread
            with open(nef, "rb") as f: iso = int(str(exifread.process_file(f, details=False).get("EXIF ISOSpeedRatings", "0")).split()[0])
        except Exception: pass
        rgb = raw.postprocess(use_camera_wb=True, output_bps=16, gamma=(1, 1), no_auto_bright=True,
                              output_color=rawpy.ColorSpace.sRGB, highlight_mode=rawpy.HighlightMode.Blend)
    img = rgb.astype(np.float32) / 65535.0; del rgb
    H, W = img.shape[:2]
    cut = lambda a, c: a if not c else a[int(c[1] * H):int(c[3] * H), int(c[0] * W):int(c[2] * W)]
    # 측광 기준 영역: 지정(meter)이 있으면 그 영역, 없으면 최종 크롭 영역.
    # 리프레이밍 때 기존에 승인된 프레임을 meter로 두면 크롭이 바뀌어도 WB·노출·국소대비 반경이 그대로 유지된다.
    ref = cut(img, meter or crop)
    img = cut(img, crop)
    # 1) 화이트밸런스: 현장광을 장면 의도만큼만 중화 + 룩 틴트 (이득은 측광 영역에서 계산)
    gains = wb_gains(ref, L["wb"])
    img = img * gains * np.array(L["tint"], np.float32)
    # 2) 노출: 톤맵 후 표시값 기준으로 측광 영역 중앙 중간톤을 룩의 mid에 맞춤(이분 탐색)
    y = luma(ref * gains * np.array(L["tint"], np.float32)); h, w = y.shape; clar_ref = max(h, w); del ref
    cw = cv2.resize(y[h // 6: h * 5 // 6, w // 6: w * 5 // 6], None, fx=0.1, fy=0.1)
    lo, hi = -3.0, 5.0
    for _ in range(14):
        ev = (lo + hi) / 2
        if np.median(srgb_oetf(tonemap(cw * 2 ** ev))) < L["mid"]: lo = ev
        else: hi = ev
    img = img * (2 ** ev)
    h, w = img.shape[:2]   # 이후 단계(비네팅 등)는 최종 크롭 크기 기준
    # 3) 톤맵 + 감마 + S커브 콘트라스트
    img = srgb_oetf(tonemap(img)).astype(np.float32)
    sm = img * img * (3 - 2 * img); img = img + L["contrast"] * (sm - img)
    # 4) 노이즈(고감도)
    img = denoise(img, iso)
    # 5) 색: 장면별 HSL + 신문 색역 압축
    img = hsl_adjust(np.clip(img, 0, 1), L["hsl"], L["sat"])
    # 6) 국소 대비(clarity), 중간톤에만
    Y = luma(img); blur = cv2.GaussianBlur(Y, (0, 0), clar_ref / 150)   # 반경은 측광 영역 기준(크롭 무관)
    mid = 1 - np.abs(Y - 0.5) * 2
    Y2 = Y + L["clarity"] * (Y - blur) * mid.clip(0, 1)
    img = img * (Y2 / np.maximum(Y, 1e-4))[..., None]
    # 7) 신문용 미드톤 리프트 + 매트 블랙 + 비네팅
    img = np.power(np.clip(img, 0, 1), L.get("lift", NEWSPRINT_MID_LIFT))   # 룩별 덮어쓰기 가능(기본 0.92)
    img = L["matte"] + (1 - L["matte"]) * img
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r2 = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
    img = img * (1 - L["vign"] * np.clip(r2 - 0.25, 0, None) / 1.75)[..., None]
    # 8) 출력 샤프닝(휘도 USM): 고감도일수록 약하게, 평탄부(노이즈)는 제외하는 엣지 마스크
    Y = luma(img); usm = Y - cv2.GaussianBlur(Y, (0, 0), 1.1)
    amt = OUT_SHARP * (1.0 if iso < 3200 else 0.7 if iso < 6400 else 0.45)
    edge = np.clip((np.abs(cv2.GaussianBlur(usm, (0, 0), 2)) - 0.004) / 0.012, 0, 1)
    img = img + amt * (usm * edge)[..., None]
    out8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    Image.fromarray(out8).save(out, quality=95, dpi=(300, 300), icc_profile=icc, subsampling=0)
    return f"{os.path.basename(out)} {look_name} iso{iso} ev{ev:+.2f} {out8.shape[1]}x{out8.shape[0]}"

def load_edits(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        if l.startswith("#") or not l.strip(): continue
        f = l.rstrip("\n").split("\t"); n, look, crop = f[:3]
        meter = f[4] if len(f) > 4 else "-"   # 5열: 측광 기준 영역(리프레이밍 컷용), "-"면 크롭 영역
        p = lambda v: None if v in ("-", "") else tuple(map(float, v.split(",")))
        rows.append((n, look, p(crop), p(meter)))
    return rows

if __name__ == "__main__":
    nef_dir, out_dir, edits = sys.argv[1:4]; only = set(sys.argv[4:])
    os.makedirs(out_dir, exist_ok=True)
    jobs = [(f"{nef_dir}/{n}.NEF", f"{out_dir}/{n}.jpg", look, crop, meter) for n, look, crop, meter in load_edits(edits) if not only or n in only]
    import multiprocessing as mp
    with ProcessPoolExecutor(int(os.environ.get("WORKERS", 3)), mp_context=mp.get_context("spawn")) as ex:
        for r in ex.map(develop, jobs): print(r, flush=True)
