# 循环 5 分析（判据见 PRED_cycle5.md）
import json,glob,math
import numpy as np
exec(open('ana5.py').read().split("R=[json.loads")[0])
R=[json.loads(l) for f in sorted(glob.glob('c5_*.jsonl')) for l in open(f)]
ok=lambda r,a: a in r and 'error' not in r[a]
def pair(S,a,ref,key='a1_err'):
    S=[r for r in S if ok(r,a) and ok(r,ref)]
    b=sum(r[a][key]==0 and r[ref][key]>0 for r in S); c=sum(r[a][key]>0 and r[ref][key]==0 for r in S); return b,c,len(S)
def std(a,ref,groups,label):
    B=C=0; print(f'== {label}: {a} vs {ref}')
    for nm,S in groups:
        S=[r for r in S if ok(r,a) and ok(r,ref)]; b,c,n=pair(S,a,ref); B+=b; C+=c
        fa=wil(sum(r[a]['a1_err']>0 for r in S),n); fr=wil(sum(r[ref]['a1_err']>0 for r in S),n)
        ta=np.mean([r[a]['t'] for r in S]); tr=np.mean([r[ref]['t'] for r in S])
        print(f' {nm} n {n} FER {ref} %.3f [%.3f,%.3f] -> {a} %.3f [%.3f,%.3f]'%(fr+fa),f'b={b} c={c} tF0 {tr:.3f}->{ta:.3f}s')
    print(f' combined b={B} c={C} b-c={B-C} p=%.4f'%sp(B,C))
print('rows',len(R),'errors',sum(1 for r in R for k,v in r.items() if isinstance(v,dict) and 'error' in v))
grp=lambda sc:[('%s rho%d'%(sc,rho),[r for r in R if r['sc']==sc and r['rho']==rho]) for rho in (100,150)]
std('adapt','g25',grp('G'),'c62')
std('w13','g25',grp('U'),'c63'); std('i4','base',grp('U'),'c63 i4 (report)')
std('a1w','base',grp('U'),'c64'); std('a1w','base',grp('G'),'c64 G (report)')
W=[r['a1w']['a1w_win'] for r in R if 'a1w_win' in r.get('a1w',{})]; print(' a1w windows: n',len(W),'frac exactly [-2,2]',np.mean([w==[-2.,2.] for w in W]))
std('emap','g25',grp('G'),'c65'); std('emap','g25',grp('U'),'c65 U (report)')
std('dmap','g25',grp('U')+grp('G'),'c66')
std('g25','base',grp('G'),'c48 on G (report)'); std('adapt','base',grp('G'),'c57 adapt vs base on G (report)')
