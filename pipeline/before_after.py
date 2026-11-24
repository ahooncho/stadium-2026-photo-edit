import sys
from PIL import Image, ImageOps, ImageDraw
S=sys.argv[1]; names=sys.argv[2:]; W=520
sh=Image.new("RGB",(2*W+10,len(names)*(W*2//3+6)),"white")
for i,n in enumerate(names):
    a=ImageOps.exif_transpose(Image.open(f"{S}/thumbs/{n}.jpg")); a.thumbnail((W,W*2//3))
    b=Image.open(f"{S}/out/{n}.jpg"); b.draft("RGB",(W*2,W*2)); b.thumbnail((W,W*2//3))
    y=i*(W*2//3+6); sh.paste(a,(0,y)); sh.paste(b,(W+10,y))
sh.save(f"{S}/ba.jpg",quality=82)
