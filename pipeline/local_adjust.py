"""현상본에 국소 톤 보정(닷지·번 범위)을 적용한다. 원칙 예외: 480호 4면 38번(PT2_0246)만, 기자 결정(2026-11-26).
마스크 = 손으로 지정한 영역(정규화 다각형) ∩ 색상 대역(형광 연두) → 가우시안 페더.
밝기·채도만 낮춘다. 흐림(초점 조절), 복제, 제거는 하지 않는다.
usage: python3 -I local_adjust.py <in.jpg> <out.jpg> <light_mul> <sat_mul> [mask_png]
"""
import sys, numpy as np, cv2
from PIL import Image
POLY = [(0.52, 0.40), (0.99, 0.40), (0.99, 1.00), (0.52, 1.00)]   # 심판(오른쪽 아래) 영역, 정규화 좌표
HUE = (55, 100)      # 형광 연두(°)
src, dst, lm, sm = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
im = Image.open(src); icc = im.info.get("icc_profile")
rgb = np.asarray(im.convert("RGB")).astype(np.float32) / 255
h, w = rgb.shape[:2]
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
region = np.zeros((h, w), np.uint8)
cv2.fillPoly(region, [np.array([(int(x * w), int(y * h)) for x, y in POLY], np.int32)], 1)
hue = ((hsv[..., 0] >= HUE[0]) & (hsv[..., 0] <= HUE[1]) & (hsv[..., 1] > 0.25) & (hsv[..., 2] > 0.25)).astype(np.uint8)
m = (region & hue).astype(np.uint8)
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)                          # 가장 큰 덩어리(재킷)만
m = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
ff = m.copy(); cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)   # 바깥 채우기 → 구멍 = 미채움
m = m | (1 - ff)                                                                # 주름 그늘 구멍 메움
m = m & (hsv[..., 2] > 0.20).astype(np.uint8)                                   # 머리카락 등 아주 어두운 부분 제외
m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(h, w) / 400)            # 페더
hsv[..., 2] *= 1 - (1 - lm) * m
hsv[..., 1] *= 1 - (1 - sm) * m
out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, quality=95, dpi=(300, 300), icc_profile=icc, subsampling=0)
if len(sys.argv) > 5: Image.fromarray((m * 255).astype(np.uint8)).save(sys.argv[5])
print(dst, "mask coverage", round(float(m.mean()) * 100, 1), "%")
