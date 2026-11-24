# Stage 1: technical metrics (no model tokens). Usage: python3 -I tech.py <scratch>
import sys, os, json, cv2, numpy as np, exifread, imagehash
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
S = sys.argv[1]

def ratio(v):
    try:
        v = v.values[0]; return float(v.num) / float(v.den)
    except Exception:
        return None

def one(name):
    p = f"{S}/thumbs/{name}.jpg"
    img = cv2.imread(p)
    if img is None:
        return None
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    lap = cv2.Laplacian(g, cv2.CV_64F)
    # tile-wise sharpness: subject is usually the sharpest region
    n = 8; th, tw = h // n, w // n
    tv = np.array([lap[i*th:(i+1)*th, j*tw:(j+1)*tw].var() for i in range(n) for j in range(n)])
    sharp_p95 = float(np.percentile(tv, 95)); sharp_max = float(tv.max())
    # edge width proxy: ratio of strong-gradient energy (motion/defocus lowers it)
    sob = cv2.magnitude(cv2.Sobel(g, cv2.CV_64F, 1, 0), cv2.Sobel(g, cv2.CV_64F, 0, 1))
    tenen = float(np.percentile(sob, 99))
    hi = float((g >= 250).mean()); lo = float((g <= 5).mean()); mean = float(g.mean())
    r = {"name": name, "w": w, "h": h, "sharp_p95": sharp_p95, "sharp_max": sharp_max,
         "tenen99": tenen, "clip_hi": hi, "clip_lo": lo, "mean": mean,
         "phash": str(imagehash.phash(Image.open(p)))}
    try:
        with open(f"{S}/exifhead/{name}.bin", "rb") as f:
            t = exifread.process_file(f, details=False)
        r.update(time=str(t.get("EXIF DateTimeOriginal")), subsec=str(t.get("EXIF SubSecTimeOriginal", "")),
                 iso=int(str(t.get("EXIF ISOSpeedRatings", "0")).split()[0] or 0),
                 shutter=ratio(t.get("EXIF ExposureTime")), fnum=ratio(t.get("EXIF FNumber")),
                 focal=ratio(t.get("EXIF FocalLength")), model=str(t.get("Image Model")),
                 orient=str(t.get("Image Orientation")))
    except Exception as e:
        r["exif_err"] = str(e)
    return r

if __name__ == "__main__":
    names = sorted(x[:-4] for x in os.listdir(f"{S}/thumbs") if x.endswith(".jpg"))
    with ProcessPoolExecutor(4) as ex:
        out = [r for r in ex.map(one, names, chunksize=8) if r]
    json.dump(out, open(f"{S}/tech.json", "w"))
    print(len(out))
