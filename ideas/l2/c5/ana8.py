# 循环 6 分析（判据见 PRED_cycle6.md）
import json,glob,math
import numpy as np
exec(open('ana5.py').read().split("R=[json.loads")[0])
R=[json.loads(l) for f in sorted(glob.glob('c6_*.jsonl')) for l in open(f)]
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
for r in R:
    if ok(r,'base') and ok(r,'g25'):
        s=dict(r['g25'] if r['g25']['syn']<=r['base']['syn'] else r['base']); s['t']=r['base']['t']+r['g25']['t']; s['pick']='g25' if r['g25']['syn']<=r['base']['syn'] else 'base'; r['sel']=s
grp=lambda sc:[('%s rho%d'%(sc,rho),[r for r in R if r['sc']==sc and r['rho']==rho]) for rho in (100,150)]
A4=grp('U')+grp('G')
V=[r for r in R if 'g25my' in r]; print('g25my validity: n',len(V),'syn mismatch',sum(r['g25my']['syn']!=r['g25']['syn'] for r in V),'f0 mismatch',sum(r['g25my']['f0_err']!=r['g25']['f0_err'] for r in V))
print('cg90 identical-to-g25 frac',np.mean([r['cg90']['syn']==r['g25']['syn'] for r in R if ok(r,'cg90')]))
print('sel picks base frac',np.mean([r['sel']['pick']=='base' for r in R if 'sel' in r]))
std('g125','g25',A4,'c67'); std('di52','base',A4,'c68'); std('sel','g25',A4,'c69'); std('cg90','g25',A4,'c70'); std('g25off','g25',A4,'c71')
std('g25','base',A4,'c48 (report)')
