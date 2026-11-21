# 循环 3 分析（判据见 PRED_cycle3.md）
import json,glob,math
import numpy as np
def wil(k,n,z=1.96):
    if n==0: return (float('nan'),0,1)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return p,max(0,c-h),min(1,c+h)
def sp(b,c):
    n=b+c; k=min(b,c); return min(1,2*sum(math.comb(n,i) for i in range(k+1))/2**n) if n else 1
R=[json.loads(l) for f in sorted(glob.glob('c3_*.jsonl')) for l in open(f)]
ok=lambda r,a: a in r and 'error' not in r[a]
def pair(S,a,ref,key='a1_err'):
    S=[r for r in S if ok(r,a) and ok(r,ref)]
    b=sum(r[a][key]==0 and r[ref][key]>0 for r in S); c=sum(r[a][key]>0 and r[ref][key]==0 for r in S); return b,c,len(S)
def std(a,ref,rhos,label):
    B=C=0; print(f'== {label}: {a} vs {ref}')
    for rho in rhos:
        S=[r for r in R if r['rho']==rho and ok(r,a) and ok(r,ref)]
        b,c,n=pair(S,a,ref); B+=b; C+=c
        fa=wil(sum(r[a]['a1_err']>0 for r in S),n); fr=wil(sum(r[ref]['a1_err']>0 for r in S),n)
        ta=np.mean([r[a]['t'] for r in S]); tr=np.mean([r[ref]['t'] for r in S])
        print(f' rho {rho} n {n} FER {ref} %.3f [%.3f,%.3f] -> {a} %.3f [%.3f,%.3f]'%(fr+fa),f'b={b} c={c} tF0 {tr:.3f}->{ta:.3f}s')
    print(f' combined b={B} c={C} b-c={B-C} p=%.4f'%sp(B,C))
print('errors',sum(1 for r in R for k,v in r.items() if isinstance(v,dict) and 'error' in v))
std('g25','base',(75,200),'c52')
std('n40','base',(100,150),'c53a'); std('g25n40','g25',(100,150),'c53b')
std('pos25','g25',(100,150),'c56')
S=[r for r in R if r['rho'] in (100,150) and ok(r,'g25') and ok(r,'base')]
med=float(np.median([r['m'] for r in S])); print('== c54 median m %.4f'%med)
for nm,T in (('high',[r for r in S if r['m']>med]),('low',[r for r in S if r['m']<=med])):
    b,c,n=pair(T,'g25','base'); print(f' {nm} n {n} b={b} c={c} b-c={b-c}')
print('== c55')
B0=C0=0
for rho in (100,150):
    T=[r for r in S if r['rho']==rho]; b0,c0,n=pair(T,'g25','base','f0_err'); B0+=b0; C0+=c0
    for a in ('base','g25'):
        F=[r for r in T if r[a]['f0_err']>0]; k=sum(r[a]['a1_err']==0 for r in F)
        print(f' rho {rho} {a} F0FER %.3f'%(len(F)/n),'A1 rescue %.3f [%.3f,%.3f]'%wil(k,len(F)),f'nfail {len(F)}')
    print(f' rho {rho} F0-level b0={b0} c0={c0}')
b,c,_=pair(S,'g25','base'); print(f' combined F0 b0-c0={B0-C0} (p=%.4f) ; A1 b-c={b-c}'%sp(B0,C0))
