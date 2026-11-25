from plan import W,ar,LINE,CPL,TOP,BOT
from functools import lru_cache
import itertools
CAPB=4.8; GAP=4.8; MINL=8; TOL=2.5; H=round(BOT-TOP,2)
SP={'38':(3,),'21':(2,),'49':(2,),'2':(1,),'17':(2,)}
CROPS=(0,-0.04,0.04,-0.08,0.08)   # 높이 변화율(+: 좌우를 잘라 세로가 길어짐, -: 위아래를 잘라 짧아짐)
def hasT(t):
    return t[0]=='T' or (t[0] in 'VH' and (hasT(t[1]) or hasT(t[2])))
def crop_cost(t):
    if t[0]=='P': return abs(t[3])
    if t[0]=='T': return 0
    return crop_cost(t[1])+crop_cost(t[2])
@lru_cache(None)
def lay(span,h,photos):
    out=[]
    if not photos:
        n=int((h+1e-6)//LINE)
        if n>=MINL: out.append((n*CPL*span,('T',span,n)))
        return out
    for p in photos:
        if span not in SP[p]: continue
        for cr in CROPS:
            b=W(span)/ar(p)*(1+cr)+CAPB; rest=photos-{p}; r=round(h-b,2)
            P=('P',p,span,cr)
            if not rest and abs(r)<=TOL: out.append((0,P))
            if r-GAP>0:
                for c,t in lay(span,round(r-GAP,2),rest):
                    out+= [(c,('V',P,t)),(c,('V',t,P))]
    if span>1:
        ps=list(photos)
        for k in range(1,span):
            for m in range(len(ps)+1):
                for L in itertools.combinations(ps,m):
                    Lf=frozenset(L)
                    for a in lay(k,h,Lf)[:4]:
                        for b in lay(span-k,h,photos-Lf)[:4]:
                            A,B=a[1],b[1]
                            if (A[0]=='T' and hasT(B) and B[0]!='T') or (B[0]=='T' and hasT(A) and A[0]!='T'): continue
                            if A[0]=='T' and B[0]=='T': continue
                            out.append((a[0]+b[0],('H',A,B)))
    out.sort(key=lambda x:(crop_cost(x[1]),-x[0]))
    return out[:8]
def show(t):
    if t[0]=='T': return f"본문{t[1]}단×{t[2]}줄"
    if t[0]=='P': return f"[{t[1]}:{t[2]}단{'' if t[3]==0 else f' {t[3]:+.0%}'}]"
    return f"({show(t[1])} {'/' if t[0]=='V' else '|'} {show(t[2])})"
import pickle
R={}
for names in (['38','21','49','2'],['38','21','49','17']):
    r=lay(5,H,frozenset(names)); R['+'.join(names)]=r
    print(names)
    for c,t in r[:5]: print('  ',c,'자',show(t))
pickle.dump(R,open('g2.pkl','wb'))
