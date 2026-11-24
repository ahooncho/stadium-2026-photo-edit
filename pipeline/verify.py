# Stage 4: full-res focus check. Crop the main face (or sharpest tile) 600x600 at full res, show at 50% (print-relevant scale).
import sys, json, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
S = sys.argv[1]; names = open(f"{S}/short1.txt").read().split()
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
res, crops = [], []
for n in names:
    im = ImageOps.exif_transpose(Image.open(f"{S}/full/{n}.jpg")).convert("RGB")
    a = np.asarray(im); g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY); H, W = g.shape
    sc = 1500 / W; small = cv2.resize(g, None, fx=sc, fy=sc)
    faces = casc.detectMultiScale(small, 1.1, 6, minSize=(18, 18))
    if len(faces):
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3]); cx, cy = (x + w / 2) / sc, (y + h / 2) / sc; src = "face"
    else:
        lap = np.abs(cv2.Laplacian(cv2.resize(g, None, fx=0.25, fy=0.25), cv2.CV_32F))
        m = cv2.blur(lap, (40, 40)); yy, xx = np.unravel_index(m.argmax(), m.shape); cx, cy = xx * 4, yy * 4; src = "tile"
    x0 = int(min(max(cx - 300, 0), W - 600)); y0 = int(min(max(cy - 300, 0), H - 600))
    c = g[y0:y0 + 600, x0:x0 + 600].astype(np.float32)
    lv = float(cv2.Laplacian(c, cv2.CV_32F).var()); con = float(c.std()) + 1
    res.append({"name": n, "src": src, "lapvar": lv, "norm": lv / con, "W": W, "H": H})
    crops.append((n, src, lv / con, im.crop((x0, y0, x0 + 600, y0 + 600)).resize((300, 300), Image.LANCZOS)))
json.dump(res, open(f"{S}/verify.json", "w"))
C, R = 8, 3; font = ImageFont.load_default()
for s in range(0, len(crops), C * R):
    sh = Image.new("RGB", (C * 302, R * 316), "white"); d = ImageDraw.Draw(sh)
    for k, (n, src, nv, c) in enumerate(crops[s:s + C * R]):
        x, y = (k % C) * 302, (k // C) * 316; sh.paste(c, (x, y + 14)); d.text((x + 2, y + 1), f"{n} {src} {nv:.1f}", fill="black", font=font)
    sh.save(f"{S}/crop_{s // (C * R)}.jpg", quality=85)
print(len(res))
