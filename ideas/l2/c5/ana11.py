# 循环 9 分析（判据见 PRED_cycle9.md）
import json,glob,math
import numpy as np
exec(open('ana5.py').read().split("R=[json.loads")[0])
R=[json.loads(l) for f in sorted(glob.glob('c9*_*.jsonl')) for l in open(f)]
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
ARMS9=('base','g25','g25off','g25n8','n16','g25r3')
def cpu(x): return x['t']+x.get('ta1',0.)
def orser(r,ks,name):
    if not all(ok(r,k) for k in ks): return
    pick=next((k for k in ks if r[k]['a1_syn']==0),ks[0]); s=dict(r[pick]); c=0.
    for k in ks:
        c+=cpu(r[k])
        if r[k]['a1_syn']==0: break
    s['t']=c; s['ta1']=0.; r[name]=s
for r in R:
    orser(r,['g25','base','g25off'],'or3'); orser(r,['g25','base'],'orb'); orser(r,['g25','g25n8'],'or8'); orser(r,['base','n16'],'orn')
    if ok(r,'g25r3'): r['g25r3']=dict(r['g25r3'],t=cpu(r['g25r3']),ta1=0.)
    for k in ('g25','base'):
        if ok(r,k): r[k+'_c']=dict(r[k],t=cpu(r[k]),ta1=0.)
M=[r for r in R if r['rho']!=200]; H=[r for r in R if r['rho']==200]
grp=lambda sc:[('%s rho%d'%(sc,rho),[r for r in M if r['sc']==sc and r['rho']==rho]) for rho in (100,150)]
A4=grp('U')+grp('G')
und=sum(1 for r in R for k in ARMS9 if ok(r,k) and r[k]['a1_syn']==0 and r[k]['a1_err']>0); tot=sum(1 for r in R for k in ARMS9 if ok(r,k))
print('undetected (a1_syn=0, a1_err>0):',und,'of',tot,'arm-frames')
for k in ('or3','orb','or8','orn'): print(k,'undetected',sum(1 for r in M if k in r and r[k]['a1_syn']==0 and r[k]['a1_err']>0),'of',sum(k in r for r in M))
print('NOTE: tF0 below = serial total CPU (F0+A1) per frame for or*/g25r3/*_c arms')
std('or3','orb',A4,'c82'); std('or8','g25_c',A4,'c83'); std('or8','orb',A4,'or8 vs orb (report)')
std('orn','g25_c',A4,'c85'); std('orn','base_c',A4,'orn vs base (report)')
std('orb','g25r3',A4,'c86'); std('g25r3','g25_c',A4,'g25r3 vs g25 (report)'); std('orb','g25_c',A4,'orb vs g25 (report, c77 replication)')
std('g25','base',[('%s rho200'%sc,[r for r in H if r['sc']==sc]) for sc in ('U','G')],'c84')
std('g25','base',A4,'c48 (report)')
