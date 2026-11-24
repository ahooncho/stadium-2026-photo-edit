import sys, json, collections, numpy as np
sys.argv += []
S = sys.argv[1]
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rank.py")).read().split("# greedy diverse pick")[0].replace("S, N = sys.argv[1], int(sys.argv[2])", "S, N = sys.argv[1], 0"))
shown = {r["name"] for r in json.load(open(f"{S}/cand.json"))["chosen"]}
rest = [r for r in best if r["name"] not in shown]
print(len(rest), collections.Counter(r["scene"] for r in rest))
# drop wide soccer (already well covered), keep the rest ranked
rest = [r for r in rest if r["scene"] != "soccer"][:60]
rest.sort(key=lambda r: r["ts"])
from PIL import Image, ImageDraw, ImageFont, ImageOps
C, R, W, H = 5, 4, 320, 214; font = ImageFont.load_default()
for s in range(0, len(rest), 20):
    sheet = Image.new("RGB", (C*W, R*(H+14)), "white"); d = ImageDraw.Draw(sheet)
    for k, r in enumerate(rest[s:s+20]):
        im = ImageOps.exif_transpose(Image.open(f"{S}/thumbs/{r['name']}.jpg")); im.thumbnail((W-4, H-4))
        x, y = (k % C)*W, (k//C)*(H+14)
        sheet.paste(im, (x+(W-im.width)//2, y+14+(H-im.height)//2))
        d.text((x+3, y+1), f"{r['name'][:3]}{r['name'][4:]} s{r['sharpz']:+.1f} q{r['qz']:+.1f} b{r['burst']}", fill="black", font=font)
    sheet.save(f"{S}/extra_{s//20}.jpg", quality=80)
