import json,glob,math
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return p,max(0,c-h),min(1,c+h)
def sign_p(b,c):
    n=b+c; k=min(b,c); return min(1,2*sum(math.comb(n,i) for i in range(k+1))/2**n) if n else 1
R=[json.loads(l) for f in sorted(glob.glob('c2_*.jsonl')) for l in open(f)]
arms=['base','g50','g25','r0re','g50re']
for rho in (100,150):
    S=[r for r in R if r['rho']==rho]; n=len(S); print('rho',rho,'n',n)
    for a in arms:
        ok=[r for r in S if 'error' not in r[a]]
        fer=sum(r[a]['a1_err']>0 for r in ok)/len(ok); f0=sum(r[a]['f0_err']>0 for r in ok)/len(ok)
        b=sum(r[a]['a1_err']==0 and r['base']['a1_err']>0 for r in ok); c=sum(r[a]['a1_err']>0 and r['base']['a1_err']==0 for r in ok)
        t=sum(r[a]['t'] for r in ok)/len(ok)
        print(f' {a:6s} ok={len(ok)} F0fer={f0:.3f} FER=%.3f [%.3f,%.3f]'%wil(round(fer*len(ok)),len(ok)),f'b={b} c={c} p={sign_p(b,c):.3f} t={t:.3f}s')
print('combined')
for a in arms[1:]:
    ok=[r for r in R if 'error' not in r[a]]
    b=sum(r[a]['a1_err']==0 and r['base']['a1_err']>0 for r in ok); c=sum(r[a]['a1_err']>0 and r['base']['a1_err']==0 for r in ok)
    print(f' {a} b={b} c={c} b-c={b-c} p={sign_p(b,c):.4f}')
for rho in (100,150):
    try: L=[json.loads(l) for l in open(f'c51_{rho}.jsonl')]
    except: continue
    print('c51 rho',rho,'F0fail',len(L),{k:'%.2f [%.2f,%.2f]'%wil(sum(r[k]==0 for r in L),len(L)) for k in ('A1','A1g1L','A1g1')})
