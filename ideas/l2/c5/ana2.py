import json,math,random
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return p,max(0,c-h),min(1,c+h)
R={(r['rho'],r['frame']):r for rho in (100,150) for r in map(json.loads,open(f'ideas/l2/c5/r{rho}.jsonl'))}
Fe={(r['rho'],r['frame']):r for r in map(json.loads,open('ideas/l2/c5/feat.jsonl'))}
fr=range(43000,43060)
same=all(Fe[(100,f)]['gap']==Fe[(150,f)]['gap'] and Fe[(100,f)]['npath']==Fe[(150,f)]['npath'] for f in fr); print('same channel across rho:',same)
fail=lambda r: r['syn']>0 and r['a1_err']>0
f10=[f for f in fr if fail(R[(100,f)])]; f15=[f for f in fr if fail(R[(150,f)])]
both=[f for f in f15 if f in f10]
print('P(fail15)=%.3f'%(len(f15)/60),'P(fail15|fail10)=%.2f [%.2f,%.2f]'%wil(len(both),len(f10)),len(f10),len(f15),len(both),'P(fail15|ok10)',sum(f not in f10 for f in f15),'/',60-len(f10))
def auc(x,y):
    pos=[a for a,b in zip(x,y) if b]; neg=[a for a,b in zip(x,y) if not b]
    return sum((p>n)+.5*(p==n) for p in pos for n in neg)/(len(pos)*len(neg))
y=[fail(R[(150,f)]) for f in fr]
feats=dict(gap=lambda e:-e['gap'],weak=lambda e:-e['weak'],ddop=lambda e:-e['ddop'],nrel=lambda e:e['nrel'])
random.seed(1)
for k,fn in feats.items():
    x=[fn(Fe[(150,f)]) for f in fr]; a=auc(x,y); bs=[]
    for _ in range(1000):
        idx=[random.randrange(60) for _ in range(60)]; yy=[y[i] for i in idx]
        if 0<sum(yy)<60: bs.append(auc([x[i] for i in idx],yy))
    bs.sort(); print(k,'AUC %.2f [%.2f,%.2f]'%(a,bs[25],bs[974]))
for rho in (100,150):
    A=[R[(rho,f)]['a1_err'] for f in fr if fail(R[(rho,f)])]
    print(rho,'A1 fail n',len(A),'<=20: %.2f [%.2f,%.2f]'%wil(sum(a<=20 for a in A),len(A)),'sorted',sorted(A))
