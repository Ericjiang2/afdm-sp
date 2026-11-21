import json,sys,math
def wil(k,n,z=1.96):
    if n==0: return (float('nan'),)*3
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return p,max(0,c-h),min(1,c+h)
T=140
for rho in (100,150):
    R=[json.loads(l) for l in open(f'ideas/l2/c5/r{rho}.jsonl')]
    F=[r for r in R if r['syn']]
    print(f'rho={rho} frames={len(R)} F0fail(syn>0)={len(F)} f0_err>0={sum(r["f0_err"]>0 for r in R)}')
    keep=[r for r in F if r['syn']<=T]; skip=[r for r in F if r['syn']>T]
    rec=[r for r in F if r['a1_err']==0]
    print(' p_skip %.2f [%.2f,%.2f]'%wil(len(skip),len(F)))
    print(' recall %.2f [%.2f,%.2f] (%d/%d)'%(*wil(sum(r['syn']<=T for r in rec),len(rec)),sum(r['syn']<=T for r in rec),len(rec)))
    print(' A1 time saved %.2f'%(sum(r['t_a1'] for r in skip)/sum(r['t_a1'] for r in F)))
    print(' FER gate %.3f vs always-A1 %.3f'%(sum((r['syn']>0 and (r['syn']>T or r['a1_err']>0)) for r in R)/len(R), sum(r['syn']>0 and r['a1_err']>0 for r in R)/len(R)))
    for name,G in (('low',keep),('high',skip)):
        a1=sum(r['a1_err']==0 for r in G); a7=sum(r['a7_err']==0 for r in G); either=sum(r['a1_err']==0 or r['a7_err']==0 for r in G)
        print(f' {name} n={len(G)} A1 %.2f [%.2f,%.2f]'%wil(a1,len(G)), ' A7 %.2f [%.2f,%.2f]'%wil(a7,len(G)), f'either {either}', ' tA1 %.3f tA7 %.3f'%(sum(r['t_a1'] for r in G)/max(1,len(G)),sum(r['t_a7'] for r in G)/max(1,len(G))))
    print(' mean t_f0 %.3f'%(sum(r['t_f0'] for r in R)/len(R)))
