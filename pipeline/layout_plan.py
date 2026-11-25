# 480호 4면 시안 배치 계산기. 단위 mm. 규격: docs/layout_spec.md A-3, C-1, C-2
import json,sys,glob,csv
from PIL import Image,ImageDraw,ImageFont
REPO='/home/user/stadium-2026-photo-edit'
L,CW,G=11.885,56.646,4.0
P=CW+G
def X(c): return L+(c-1)*P            # 단 c(1..5) 왼쪽
def W(n): return CW*n+G*(n-1)
TOP=63.2          # 사진·본문 시작 (479호 4면)
BOT=310.0         # 본문 마지막 줄 바닥 한계 (기사 하단 괘선 316.84 위)
LINE=4.8; CPL=21  # 행 간격, 한 줄 글자 수(477–479호 실측)
CAP_GAP,CAP_H=1.8,3.0   # 캡션: 사진 아래 1.8mm, 한 줄
AFTER=LINE        # 캡션 아래 본문까지 한 줄 띄움
BEFORE=LINE       # 본문 아래 사진까지 한 줄 띄움
rows={r['번호']:r for r in csv.DictReader(open(f'{REPO}/out/final8/manifest.csv',encoding='utf-8-sig'))}
def ar(n):
    w,h=map(int,rows[n]['크기'].split('x')); return w/h
def photo(n,c,span,y=None,bottom=None,crop=(0,0,1,1)):
    w=W(span); a=ar(n)*(crop[2]-crop[0])/(crop[3]-crop[1]); h=w/a
    if y is None: y=bottom-CAP_GAP-CAP_H-h
    return dict(no=n,file=rows[n]['파일'],col=c,span=span,x=X(c),y=y,w=w,h=h,crop=crop)
def text_regions(photos):
    regs=[]
    for c in range(1,6):
        occ=sorted([(p['y']-BEFORE if p['y']>TOP+0.1 else TOP, p['y']+p['h']+CAP_GAP+CAP_H+AFTER) for p in photos if p['col']<=c<p['col']+p['span']])
        y=TOP
        for a,b in occ:
            if a>y: regs.append((c,y,a))
            y=max(y,b)
        if BOT>y: regs.append((c,y,BOT))
    out=[]
    for c,a,b in regs:
        n=int((b-a+0.01)//LINE)
        if n>=1: out.append(dict(col=c,x=X(c),y=a,w=CW,h=n*LINE,lines=n))
    return out
def build(name,photos):
    t=text_regions(photos); lines=sum(r['lines'] for r in t)
    area=sum(p['w']*p['h'] for p in photos); dom=max(photos,key=lambda p:p['w']*p['h'])
    rep=dict(name=name,photos=photos,text=t,lines=lines,chars=lines*CPL,
             photo_share=round(area/(W(5)*(BOT-TOP)),3),
             secondary_vs_dominant=[(p['no'],round(p['w']*p['h']/(dom['w']*dom['h']),2)) for p in photos if p is not dom])
    return rep
def render(rep,path,s=3):
    im=Image.new('RGB',(int(323*s),int(470*s)),'white'); d=ImageDraw.Draw(im)
    f=lambda v:int(round(v*s))
    d.rectangle([f(12),f(24.4)-1,f(311),f(24.4)+2],fill='black')
    d.rectangle([f(11.9),f(316.84),f(310.9),f(316.84)+1],fill='black')
    d.rectangle([f(12.39),f(327.32),f(128.53),f(441.46)],outline='black',width=3)
    d.rectangle([f(133.2),f(327.14),f(310.51),f(441.64)],outline=(181,181,182),width=2)
    d.rectangle([f(12.4),f(451.45),f(311.4),f(451.45)+1],fill='black')
    d.text((f(140),f(380)),'가로세로',fill='gray'); d.text((f(55),f(380)),'만평',fill='gray')
    d.rectangle([f(40),f(34.9),f(283),f(47.2)],fill=(60,60,60))
    d.rectangle([f(81),f(50),f(242),f(54.9)],fill=(150,150,150))
    for r in rep['text']:
        for i in range(r['lines']):
            y=r['y']+i*LINE+1.2; d.rectangle([f(r['x']),f(y),f(r['x']+r['w']),f(y+2.4)],fill=(205,205,205))
    for p in rep['photos']:
        src=glob.glob(f"{REPO}/out/final8/*_{p['file']}.jpg")[0]; ph=Image.open(src); ph.draft('RGB',(ph.width//4,ph.height//4))
        ph=ph.convert('RGB'); c=p['crop']; ph=ph.crop((int(c[0]*ph.width),int(c[1]*ph.height),int(c[2]*ph.width),int(c[3]*ph.height))).resize((f(p['w']),f(p['h']))); im.paste(ph,(f(p['x']),f(p['y'])))
        cy=p['y']+p['h']+CAP_GAP; d.rectangle([f(p['x']),f(cy),f(p['x']+p['w']*0.7),f(cy+2.6)],fill=(120,120,120))
        d.text((f(p['x'])+3,f(p['y'])+3),str(p['no']),fill='yellow')
    im.save(path,quality=88)
