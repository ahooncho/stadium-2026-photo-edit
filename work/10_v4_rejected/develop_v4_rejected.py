"""v4 현상 엔진 — 피사체 인식 국소 보정.
원칙: 객체를 지우거나 옮기거나 합성하지 않는다. 그 밖의 톤·색·빛 조작(닷지·번, 배경 채도·대비,
하늘 그라데이션, 광원 글로, 스플릿 톤)은 연출 수단으로 쓴다(docs/creative_brief.md 2절).

usage: python3 -I develop.py <nef_dir> <out_dir> <edits.tsv> [name ...]
산출: <out_dir>/master/<name>.jpg (화면·웹용 마스터), <out_dir>/print/<name>.jpg (신문 인쇄 대응본),
      <out_dir>/masks/<name>.png (실제 쓰인 피사체 마스크, 공개용)
"""
import sys, os, math, json, numpy as np, cv2, rawpy
from PIL import Image, ImageCms

# ---- 룩 -------------------------------------------------------------------
# 전역: wb(현장광 중화 강도) tint(RGB 배율) mid(중간톤 목표) contrast(S커브) black(블랙 포인트) sat(전역 채도)
# 국소: dodge/burn(피사체 +EV / 배경 −EV) bg_sat(배경 채도 배율) subj_clar/bg_clar(국소 대비) bg_blur(배경 연화 σ, 긴 변 대비 ‰)
# 빛·색: sky(회색 하늘 −EV) bloom(광원 글로) split=((그림자 RGB 가산),(하이라이트 RGB 가산)) vign
# hsl: (중심 hue°, 폭°, hue 이동°, 채도 배율, 명도 배율)
LOOKS = {
 "hardwood":  dict(wb=.55, tint=(1.02, 1, .98), mid=.44, contrast=.55, black=.03, sat=1.10,
                   dodge=.30, burn=.55, bg_sat=.75, subj_clar=.45, bg_clar=-.15, bg_blur=0,
                   sky=0, bloom=0, split=((-.010, 0, .020), (.020, .010, -.010)), vign=.25, max_subj=4,
                   hsl=[(45, 25, 0, .85, .92), (0, 15, 0, 1.15, 1), (220, 30, 0, 1.15, 1)]),
 "rainpitch": dict(wb=.50, tint=(.98, 1, 1.03), mid=.40, contrast=.50, black=.02, sat=1.08,
                   dodge=.30, burn=.45, bg_sat=.80, subj_clar=.50, bg_clar=0, bg_blur=0,
                   sky=.8, bloom=0, split=((-.010, .005, .020), (.015, .005, -.010)), vign=.22, max_subj=4,
                   hsl=[(105, 40, 0, 1.15, .92), (0, 15, 0, 1.20, 1), (30, 15, 0, 1.15, 1)]),
 "arena":     dict(wb=.30, tint=(.95, 1, 1.06), mid=.26, contrast=.60, black=.05, sat=1.10,
                   dodge=.45, burn=.90, bg_sat=.80, subj_clar=.35, bg_clar=-.10, bg_blur=0,
                   sky=0, bloom=.35, split=((-.020, .010, .040), (.020, .010, 0)), vign=.30, max_subj=4,
                   hsl=[(120, 30, 0, 1.30, 1.10), (210, 40, 0, 1.25, 1), (30, 25, 0, .80, .95)]),
 "victory":   dict(wb=.40, tint=(1.05, 1, .94), mid=.42, contrast=.50, black=.03, sat=1.12,
                   dodge=.35, burn=.60, bg_sat=.65, subj_clar=.40, bg_clar=-.20, bg_blur=0,
                   sky=0, bloom=.15, split=((0, 0, .015), (.025, .015, -.010)), vign=.28, max_subj=3,
                   hsl=[(320, 30, 0, .70, 1), (50, 18, 0, 1.25, 1.05), (0, 14, 3, 1.10, 1)]),
 "redstage":  dict(wb=0, tint=(1, 1, 1), mid=.26, contrast=.60, black=.06, sat=1.15,
                   dodge=.35, burn=.70, bg_sat=.90, subj_clar=.35, bg_clar=-.10, bg_blur=0,
                   sky=0, bloom=.45, split=((0, 0, .030), (.020, .010, 0)), vign=.20, max_subj=8,
                   hsl=[(0, 20, -3, 1.20, 1), (330, 20, 0, 1.10, 1)]),
 "cleantech": dict(wb=.80, tint=(.99, 1, 1.02), mid=.44, contrast=.50, black=.03, sat=1.10,
                   dodge=.50, burn=.80, bg_sat=.60, subj_clar=.50, bg_clar=-.10, bg_blur=0,
                   sky=0, bloom=0, split=((-.010, 0, .020), (.010, .005, 0)), vign=.28, max_subj=3,
                   hsl=[(115, 30, 0, 1.15, .95)]),
 "campus":    dict(wb=.70, tint=(1, 1, 1), mid=.42, contrast=.40, black=.02, sat=1.05,
                   dodge=.20, burn=.40, bg_sat=.80, subj_clar=.30, bg_clar=0, bg_blur=0,
                   sky=0, bloom=0, split=((0, 0, 0), (0, 0, 0)), vign=.15, max_subj=0, hsl=[]),
}
PRINT_GAMMA, PRINT_SAT_KNEE = 0.90, 0.85   # 인쇄 대응본: 미드톤 리프트, 고채도 압축
OUT_SHARP = 0.65

def luma(x): return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
def tonemap(x): return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
def oetf(x): return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0.0031308, None), 1 / 2.4) - 0.055)

_DET = None
def detector():
    global _DET
    if _DET is None:
        import torch
        from torchvision.models.detection import maskrcnn_resnet50_fpn_v2, MaskRCNN_ResNet50_FPN_V2_Weights
        torch.set_num_threads(2)
        _DET = maskrcnn_resnet50_fpn_v2(weights=MaskRCNN_ResNet50_FPN_V2_Weights.COCO_V1).eval()
    return _DET

def subject_mask(preview, max_subj, focus):
    if focus: max_subj = 0   # 초점 영역 지정 시 자동 탐지는 쓰지 않음(배경 관중이 밝아지는 문제)
    """preview: 표시용 RGB(0..1). 사람(COCO 1)과 공(37) 마스크 → 부드러운 피사체 마스크와 기록."""
    h, w = preview.shape[:2]; diag = math.hypot(h, w)
    M = np.zeros((h, w), np.float32); info = {"detections": []}
    if max_subj > 0:
        import torch
        sc = 1333 / max(h, w); small = cv2.resize(preview, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        with torch.no_grad():
            r = detector()([torch.from_numpy(small.transpose(2, 0, 1).copy()).float()])[0]
        keep = [(i, float(r["scores"][i]), int(r["labels"][i])) for i in range(len(r["scores"]))
                if (int(r["labels"][i]) == 1 and r["scores"][i] > .6) or (int(r["labels"][i]) == 37 and r["scores"][i] > .5)]
        areas = {i: float((r["masks"][i, 0] > .5).sum()) for i, _, _ in keep}
        persons = sorted([k for k in keep if k[2] == 1], key=lambda k: -areas[k[0]])
        if persons:
            amax = areas[persons[0][0]]
            persons = [p for p in persons if areas[p[0]] >= .2 * amax][:max_subj]
        sel = persons + [k for k in keep if k[2] == 37]
        for i, s, lab in sel:
            m = cv2.resize(r["masks"][i, 0].numpy(), (w, h), interpolation=cv2.INTER_LINEAR)
            M = np.maximum(M, m)
            x0, y0, x1, y1 = (r["boxes"][i].numpy() / sc).round().astype(int).tolist()
            info["detections"].append({"label": "person" if lab == 1 else "sports ball", "score": round(s, 3), "box": [x0, y0, x1, y1]})
    if focus:   # 지정 초점 영역(타원) — 탐지되지 않는 피사체(RC카 등)
        x0, y0, x1, y1 = focus; yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy, rx, ry = (x0 + x1) / 2 * w, (y0 + y1) / 2 * h, (x1 - x0) / 2 * w, (y1 - y0) / 2 * h
        M = np.maximum(M, np.clip(1.6 - np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2), 0, 1))
        info["focus"] = focus
    if M.max() == 0:   # 피사체 없음: 중앙 타원
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        M = np.clip(1.3 - np.sqrt(((xx - w / 2) / (w * .45)) ** 2 + ((yy - h / 2) / (h * .45)) ** 2), 0, 1); info["fallback"] = "center"
    if info.get("detections"):   # 윤곽 안쪽으로 살짝 침식 → 경계 전환이 피사체 안에서 일어나 후광이 안 생김
        M = cv2.erode(M, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(diag * .003) | 1,) * 2))
        M = guided(luma(preview).astype(np.float32), M.astype(np.float32), int(diag * .006) | 1, 1e-3)
    M = cv2.GaussianBlur(np.clip(M, 0, 1), (0, 0), diag * (.003 if info.get("detections") else .02))
    return np.clip(M / max(M.max(), 1e-6), 0, 1), info

def guided(I, p, r, eps=1e-3):
    """He et al. guided filter: 마스크(p)를 이미지 경계(I)에 맞춘다."""
    bx = lambda x: cv2.boxFilter(x, -1, (r, r))
    mI, mp = bx(I), bx(p); a = (bx(I * p) - mI * mp) / (bx(I * I) - mI * mI + eps); b = mp - a * mI
    return bx(a) * I + bx(b)

def sky_mask(disp, M):
    hsv = cv2.cvtColor(disp.astype(np.float32), cv2.COLOR_RGB2HSV)
    h = disp.shape[0]; rows = np.linspace(1, 0, h)[:, None] ** .5
    s = ((hsv[..., 1] < .14) & (hsv[..., 2] > .55)).astype(np.float32) * rows
    s = cv2.GaussianBlur(s, (0, 0), max(disp.shape) * .02) * (1 - M)
    return np.clip(s * 1.6, 0, 1)

def hsl_bands(rgb, bands, sat):
    hsv = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    sm, vm, ha = np.full_like(s, sat), np.ones_like(v), np.zeros_like(h)
    for c, w, dh, ds, dv in bands:
        d = np.abs(((h - c + 180) % 360) - 180)
        g = np.exp(-.5 * (d / (w / 2)) ** 2) * np.clip(s * 3, 0, 1)
        sm *= 1 + (ds - 1) * g; vm *= 1 + (dv - 1) * g; ha += dh * g
    hsv[..., 0] = (h + ha) % 360; hsv[..., 1] = np.clip(s * sm, 0, 1); hsv[..., 2] = np.clip(v * vm, 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

def denoise(rgb, iso):
    if iso < 800: return rgb
    ycc = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2YCrCb)
    tiers = [(1600, 1.5, 3), (3200, 2.5, 5), (6400, 3.5, 8), (10 ** 9, 5.0, 11)]
    cs, hh = next((c, k) for lim, c, k in tiers if iso < lim)
    for c in (1, 2): ycc[..., c] = cv2.GaussianBlur(ycc[..., c], (0, 0), cs)
    y8 = (ycc[..., 0].clip(0, 1) * 255).astype(np.uint8)
    yd = cv2.fastNlMeansDenoising(y8, None, hh, 5, 15).astype(np.float32) / 255
    ycc[..., 0] += yd - y8 / 255.0
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2RGB)

def save(arr, path):
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    Image.fromarray((np.clip(arr, 0, 1) * 255 + .5).astype(np.uint8)).save(path, quality=95, dpi=(300, 300), icc_profile=icc, subsampling=0)

def develop(args):
    nef, out_dir, name, look_name, crop, focus = args
    L = LOOKS[look_name]; log = {"name": name, "look": look_name, "crop": crop}
    import exifread
    with open(nef, "rb") as f: iso = int(str(exifread.process_file(f, details=False).get("EXIF ISOSpeedRatings", "0")).split()[0])
    with rawpy.imread(nef) as raw:
        rgb = raw.postprocess(use_camera_wb=True, output_bps=16, gamma=(1, 1), no_auto_bright=True,
                              output_color=rawpy.ColorSpace.sRGB, highlight_mode=rawpy.HighlightMode.Blend)
    img = rgb.astype(np.float32) / 65535; del rgb
    H, W = img.shape[:2]
    if crop: x0, y0, x1, y1 = crop; img = img[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
    h, w = img.shape[:2]; diag = math.hypot(h, w)
    # 1) 부분 WB + 틴트
    y = luma(img); m = (y > np.percentile(y, 20)) & (y < np.percentile(y, 90))
    if L["wb"] > 0: img = img * (img[m].mean(0).mean() / (img[m].mean(0) + 1e-6)) ** L["wb"]
    img = img * np.array(L["tint"], np.float32)
    # 2) 전역 노출(표시값 기준 이분 탐색)
    y = luma(img); cw = cv2.resize(y[h // 6:h * 5 // 6, w // 6:w * 5 // 6], None, fx=.1, fy=.1)
    lo, hi = -3., 5.
    for _ in range(14):
        ev = (lo + hi) / 2
        lo, hi = (ev, hi) if np.median(oetf(tonemap(cw * 2 ** ev))) < L["mid"] else (lo, ev)
    img = img * 2 ** ev; log.update(iso=iso, ev=round(ev, 2))
    # 3) 피사체 마스크(미리보기에서 검출)
    prev = oetf(tonemap(img)).astype(np.float32)
    M, info = subject_mask(prev, L["max_subj"], focus); log["subject"] = info
    # 4) 닷지·번(선형광, 노출 단위) + 회색 하늘 그라데이션
    img = img * (2 ** (L["dodge"] * M - L["burn"] * (1 - M)))[..., None]
    if L["sky"] > 0:
        Sk = sky_mask(prev, M); img = img * (2 ** (-L["sky"] * Sk))[..., None] * (1 + Sk[..., None] * np.array([-.02, 0, .03], np.float32))
        log["sky_area"] = round(float((Sk > .5).mean()), 3)
    # 5) 톤맵 + S커브 + 블랙 포인트
    img = oetf(tonemap(img)).astype(np.float32)
    sm = img * img * (3 - 2 * img); img = img + L["contrast"] * (sm - img)
    img = np.clip((img - L["black"]) / (1 - L["black"]), 0, 1)
    # 6) 노이즈
    img = denoise(img, iso)
    # 7) 색: HSL 대역 + 배경 채도
    img = hsl_bands(img, L["hsl"], L["sat"])
    Y = luma(img)[..., None]; img = Y + (img - Y) * (L["bg_sat"] + (1 - L["bg_sat"]) * M)[..., None]
    # 8) 국소 대비: 피사체/배경 다르게
    Y = luma(img); det = Y - cv2.GaussianBlur(Y, (0, 0), max(h, w) / 150)
    amt = L["subj_clar"] * M + L["bg_clar"] * (1 - M)
    Y2 = Y + amt * det * (1 - np.abs(Y - .5) * 2).clip(0, 1)
    img = img * (Y2 / np.maximum(Y, 1e-4))[..., None]
    if L["bg_blur"] > 0:
        bl = cv2.GaussianBlur(img, (0, 0), max(h, w) * L["bg_blur"] / 1000); img = img * M[..., None] + bl * (1 - M[..., None])
    # 9) 광원 글로(screen) + 스플릿 톤 + 비네팅
    if L["bloom"] > 0:
        Y = luma(img); hl = img * (np.clip((Y - .75) / .25, 0, 1) ** 2)[..., None]
        g = cv2.GaussianBlur(hl, (0, 0), diag * .015); img = 1 - (1 - img) * (1 - L["bloom"] * g)
    Y = luma(img)[..., None]; (sh, hl) = L["split"]
    img = img + np.array(sh, np.float32) * (1 - Y) ** 2 + np.array(hl, np.float32) * Y ** 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); r2 = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
    img = img * (1 - L["vign"] * np.clip(r2 - .3, 0, None) / 1.7)[..., None]
    # 10) 샤프닝(엣지 마스크, 피사체 가중)
    Y = luma(img); usm = Y - cv2.GaussianBlur(Y, (0, 0), 1.1)
    edge = np.clip((np.abs(cv2.GaussianBlur(usm, (0, 0), 2)) - .004) / .012, 0, 1)
    k = OUT_SHARP * (1 if iso < 3200 else .7 if iso < 6400 else .45)
    img = np.clip(img + k * (usm * edge * (.6 + .4 * M))[..., None], 0, 1)
    save(img, f"{out_dir}/master/{name}.jpg")
    # 11) 인쇄 대응본: 미드톤 리프트 + 고채도 압축 + 추가 샤프닝
    p = np.power(img, PRINT_GAMMA)
    hsv = cv2.cvtColor(p.astype(np.float32), cv2.COLOR_RGB2HSV); s = hsv[..., 1]
    hsv[..., 1] = np.where(s > PRINT_SAT_KNEE, PRINT_SAT_KNEE + (s - PRINT_SAT_KNEE) * .4, s); p = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    Y = luma(p); p = p + .25 * (Y - cv2.GaussianBlur(Y, (0, 0), 1.0))[..., None]
    save(p, f"{out_dir}/print/{name}.jpg")
    cv2.imwrite(f"{out_dir}/masks/{name}.png", (cv2.resize(M, (w // 4, h // 4)) * 255).astype(np.uint8))
    log["out"] = [w, h]
    return log

def load_edits(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        if l.startswith("#") or not l.strip(): continue
        f = l.rstrip("\n").split("\t")
        crop = None if f[2] == "-" else tuple(map(float, f[2].split(",")))
        focus = tuple(map(float, f[4].split(","))) if len(f) > 4 and f[4] not in ("", "-") else None
        rows.append((f[0], f[1], crop, focus))
    return rows

if __name__ == "__main__":
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    nef_dir, out_dir, edits = sys.argv[1:4]; only = set(sys.argv[4:])
    for d in ("master", "print", "masks"): os.makedirs(f"{out_dir}/{d}", exist_ok=True)
    jobs = [(f"{nef_dir}/{n}.NEF", out_dir, n, lk, cr, fo) for n, lk, cr, fo in load_edits(edits) if not only or n in only]
    logs = []
    with ProcessPoolExecutor(int(os.environ.get("WORKERS", 3)), mp_context=mp.get_context("spawn")) as ex:
        for r in ex.map(develop, jobs):
            print(r["name"], r["look"], "iso", r["iso"], "ev", r["ev"], "subj", len(r["subject"]["detections"]), flush=True); logs.append(r)
    lp = f"{out_dir}/develop_log.json"
    old = {x["name"]: x for x in json.load(open(lp))} if os.path.exists(lp) else {}
    old.update({x["name"]: x for x in logs}); json.dump(list(old.values()), open(lp, "w"), ensure_ascii=False, indent=1)
