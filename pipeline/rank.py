# Stage 3: combine scores, collapse bursts, pick diverse candidates, render contact sheets.
# Usage: python3 -I rank.py <scratch> <n_candidates>
import sys, json, numpy as np, collections, datetime as dt
from PIL import Image, ImageDraw, ImageFont, ImageOps
S, N = sys.argv[1], int(sys.argv[2])
tech = {r["name"]: r for r in json.load(open(f"{S}/tech.json"))}
clip = json.load(open(f"{S}/clip.json")); emb = np.load(f"{S}/emb.npy")
idx = {c["name"]: i for i, c in enumerate(clip)}
rows = []
for c in clip:
    r = {**tech[c["name"]], **c}
    t = r.get("time") or "2026:11:14 00:00:00"
    r["ts"] = dt.datetime.strptime(t, "%Y:%m:%d %H:%M:%S").timestamp()
    rows.append(r)
def z(a): a = np.asarray(a, float); return (a - a.mean()) / (a.std() + 1e-9)
sh = z(np.log([r["sharp_p95"] + 1 for r in rows]))
q = np.clip([r["clipq"] for r in rows], 1e-4, 1 - 1e-4); qz = z(np.log(q / (1 - q)))
for i, r in enumerate(rows):
    pen = 0
    if r["clip_hi"] > 0.08 or r["clip_lo"] > 0.2: pen += 1.0          # unrecoverable clipping
    if (r.get("iso") or 0) >= 6400: pen += 0.3                        # heavy noise (partly fixable)
    if r.get("shutter") and r.get("focal") and r["shutter"] > 1 / (1.5 * r["focal"]): pen += 0.4  # shake risk
    r["sharpz"], r["qz"] = float(sh[i]), float(qz[i])
    r["score"] = float(0.5 * sh[i] + 0.5 * qz[i] - pen)
    r["reject"] = bool(sh[i] < -1.0)                                  # bottom ~16% sharpness: drop outright
# burst collapse: time-ordered, same group if <=3s apart and visually similar
rows.sort(key=lambda r: r["ts"])
gid, g = 0, []
for i, r in enumerate(rows):
    if i and r["ts"] - rows[i-1]["ts"] <= 3 and float(emb[idx[r["name"]]] @ emb[idx[rows[i-1]["name"]]]) > 0.88:
        pass
    else:
        gid += 1
    r["group"] = gid
groups = collections.defaultdict(list)
for r in rows: groups[r["group"]].append(r)
best = []
for gr in groups.values():
    gr.sort(key=lambda r: -r["score"]); b = gr[0]; b["burst"] = len(gr)
    if not b["reject"]: best.append(b)
best.sort(key=lambda r: -r["score"])
# greedy diverse pick: skip near-duplicates (cos>0.93) of already chosen; soft cap per scene
chosen, per = [], collections.Counter()
cap = max(14, N // 4)
for r in best:
    e = emb[idx[r["name"]]]
    if any(float(e @ emb[idx[c["name"]]]) > 0.95 for c in chosen): continue
    if per[r["scene"]] >= cap: continue
    chosen.append(r); per[r["scene"]] += 1
    if len(chosen) >= N: break
json.dump({"chosen": chosen, "groups": len(groups), "after_reject": len(best)}, open(f"{S}/cand.json", "w"))
print("groups", len(groups), "non-rejected bests", len(best), "chosen", len(chosen), dict(per))
# contact sheets in time order so related shots sit together
chosen.sort(key=lambda r: r["ts"])
C, R, W, H = 5, 4, 320, 214
font = ImageFont.load_default()
for s in range(0, len(chosen), C * R):
    sheet = Image.new("RGB", (C * W, R * (H + 14)), "white"); d = ImageDraw.Draw(sheet)
    for k, r in enumerate(chosen[s:s + C * R]):
        im = ImageOps.exif_transpose(Image.open(f"{S}/thumbs/{r['name']}.jpg")); im.thumbnail((W - 4, H - 4))
        x, y = (k % C) * W, (k // C) * (H + 14)
        sheet.paste(im, (x + (W - im.width) // 2, y + 14 + (H - im.height) // 2))
        d.text((x + 3, y + 1), f"{r['name'][:3]}{r['name'][4:]} s{r['sharpz']:+.1f} q{r['qz']:+.1f}", fill="black", font=font)
    sheet.save(f"{S}/sheet_{s // (C * R):02d}.jpg", quality=80)
