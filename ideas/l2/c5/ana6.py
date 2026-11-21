# 循环 4 分析（判据见 PRED_cycle4.md）
import json,glob,math
import numpy as np
exec(open('ana5.py').read().split("R=[json.loads")[0])
R=[json.loads(l) for f in sorted(glob.glob('c4_*.jsonl')) for l in open(f)]
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
M=[('rho%d'%rho,[r for r in R if r['snr']==450 and r['rho']==rho]) for rho in (100,150)]
S450=[r for r in R if r['snr']==450]
print('int24==base syn/f0 match',np.mean([r['int24']['syn']==r['base']['syn'] and r['int24']['f0_err']==r['base']['f0_err'] for r in S450]))
std('adapt','g25',M,'c57'); std('adapt','pos25',M,'c57 vs oracle (report)')
ch=np.array([r['chat'] for r in S450]); print(' chat quantiles',np.quantile(ch,[0,.1,.5,.9,1]),'frac window covers [0.25,1.75]',np.mean((ch-1<=.25)&(ch+1>=1.75)))
std('g25','base',[('snr%d'%s,[r for r in R if r['snr']==s]) for s in (300,600)],'c58')
std('pos25','g25',[('snr%d'%s,[r for r in R if r['snr']==s]) for s in (300,600)],'c58 pos25 (report)')
std('n16','base',M,'c59a'); std('g25n16','g25',M,'c59b')
std('pos1','base',M,'c60')
std('loc','base',M,'c61'); std('loc','g25',M,'c61 vs g25 (report)')
std('g25','base',M,'c48 fourth batch (report)'); std('pos25','g25',M,'c56 second batch (report)')
