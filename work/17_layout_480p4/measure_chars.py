# 발행본 [대학]면에서 '실효 글자 수/줄 칸'을 측정. 본문(Jabml, 9~10pt)+소제목(Jatgb, 9~10pt)만 대상
import pymupdf,collections,statistics,sys
mm=25.4/72; L=11.885; P=60.4
def col(x): return int(round((x-L)/P))
rows=[]
for f,pg in [('476_kor.pdf',3),('476_kor.pdf',4),('477_kor.pdf',3),('477_kor.pdf',4),('478_kor.pdf',3),('478_kor.pdf',4),('479_kor.pdf',3),('479_kor.pdf',4)]:
    p=pymupdf.open(f)[pg-1]
    lines=collections.defaultdict(list)
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            sp=[s for s in l['spans'] if 9.0<=s['size']<=10.0 and (s['font'].startswith('Jabml') or s['font'].startswith('Jatgb'))]
            if not sp: continue
            t=''.join(c['c'] for s in sp for c in s['chars'])
            if not t.strip(): continue
            x0=l['bbox'][0]*mm; y0=l['bbox'][1]*mm
            if y0<60 and any(s['size']>12 for s in l['spans']): continue
            lines[(col(x0),)].append((round(y0,2),t))
    slots=0;ch=0;chns=0;nl=0
    for k,v in lines.items():
        ys=sorted(set(y for y,_ in v))
        # 같은 단 안에서 사진 등으로 끊긴 구간은 4.8mm보다 큰 간격 → 구간별로 칸 수 계산
        seg=[[ys[0]]]
        for a,b in zip(ys,ys[1:]):
            if b-a>4.8*2.6: seg.append([b])
            else: seg[-1].append(b)
        for s in seg: slots+=int(round((s[-1]-s[0])/4.8))+1
        for y,t in v: ch+=len(t.rstrip()); chns+=len(t.replace(' ','').strip()); nl+=1
    rows.append((f[:3],pg,nl,slots,ch,chns))
    print(f[:3],pg,'줄',nl,'칸',slots,'글자(공백포함)',ch,'공백제외',chns,'칸당',round(ch/slots,2),round(chns/slots,2))
S=sum(r[3] for r in rows);C=sum(r[4] for r in rows);N=sum(r[5] for r in rows)
print('합계 칸',S,'칸당 공백포함',round(C/S,3),'공백제외',round(N/S,3))
per=[r[4]/r[3] for r in rows];per2=[r[5]/r[3] for r in rows]
print('면별 범위 공백포함',round(min(per),2),'~',round(max(per),2),' 공백제외',round(min(per2),2),'~',round(max(per2),2))
for k in (88,):
    print(f'시안 {k}칸: 공백포함 {k*C/S:.0f}자 (면별 {k*min(per):.0f}~{k*max(per):.0f}), 공백제외 {k*N/S:.0f}자 (면별 {k*min(per2):.0f}~{k*max(per2):.0f})')
