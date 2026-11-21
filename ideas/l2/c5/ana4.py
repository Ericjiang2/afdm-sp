# 确认批（帧 47000–47199）分析：c47/c48 配对符号检验，c51 F0 失败帧恢复率
import json,glob,math
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return p,max(0,c-h),min(1,c+h)
def sp(b,c):
    n=b+c; k=min(b,c); return min(1,2*sum(math.comb(n,i) for i in range(k+1))/2**n) if n else 1
R=[json.loads(l) for f in sorted(glob.glob('cf_*.jsonl')) for l in open(f)]
for rho in (100,150):
    S=[r for r in R if r['rho']==rho]; print('rho',rho,'n',len(S))
    for a in ('base','g50','g25'):
        k=sum(r[a]['a1_err']>0 for r in S)
        b=sum(r[a]['a1_err']==0 and r['base']['a1_err']>0 for r in S); c=sum(r[a]['a1_err']>0 and r['base']['a1_err']==0 for r in S)
        print(f' {a} FER=%.3f [%.3f,%.3f]'%wil(k,len(S)),f'b={b} c={c} t={sum(r[a]["t"] for r in S)/len(S):.3f}s')
for a in ('g50','g25'):
    b=sum(r[a]['a1_err']==0 and r['base']['a1_err']>0 for r in R); c=sum(r[a]['a1_err']>0 and r['base']['a1_err']==0 for r in R)
    print('combined',a,'b',b,'c',c,'b-c',b-c,'p=%.4f'%sp(b,c))
for rho in (100,150):
    L=[json.loads(l) for f in sorted(glob.glob(f'c51cf_{rho}*.jsonl')) for l in open(f)]
    print('c51',rho,'F0fail',len(L),{k:'%.2f [%.2f,%.2f]'%wil(sum(r[k]==0 for r in L),len(L)) for k in ('A1','A1g1L','A1g1')})
