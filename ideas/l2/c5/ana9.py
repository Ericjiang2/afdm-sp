# 循环 7 分析（判据见 PRED_cycle7.md）
import json,glob,math
import numpy as np
exec(open('ana5.py').read().split("R=[json.loads")[0])
R=[json.loads(l) for f in sorted(glob.glob('c7*_*.jsonl')) for l in open(f)]
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
def mk(r,a,b2,name,mode):
    if not(ok(r,a) and ok(r,b2)): return
    A,B=r[a],r[b2]
    if mode=='sel': s=dict(A if A['syn']<=B['syn'] else B); s['t']=A['t']+B['t']
    else: s=dict(A if A['a1_syn']==0 or B['a1_syn']!=0 else B); s['t']=A['t']+B['t']
    r[name]=s
for r in R:
    mk(r,'g25','g25off','sel2','sel'); mk(r,'g25','g25off','or2','or'); mk(r,'g25','base','orb','or')
M=[r for r in R if r['snr']==450]; S=[r for r in R if r['snr']!=450]
grp=lambda sc:[('%s rho%d'%(sc,rho),[r for r in M if r['sc']==sc and r['rho']==rho]) for rho in (100,150)]
A4=grp('U')+grp('G')
und=sum(1 for r in R for k in ('base','g25','g25off','rdg','sbl','g25n40') if ok(r,k) and r[k]['a1_syn']==0 and r[k]['a1_err']>0)
tot=sum(1 for r in R for k in ('base','g25','g25off','rdg','sbl','g25n40') if ok(r,k))
print('undetected (a1_syn=0, a1_err>0):',und,'of',tot,'arm-frames')
print('or2 undetected:',sum(1 for r in M if 'or2' in r and r['or2']['a1_syn']==0 and r['or2']['a1_err']>0),'of',sum('or2' in r for r in M))
std('sel2','g25',A4,'c72'); std('or2','g25',A4,'c73'); std('orb','g25',A4,'c73 or(base,g25) (report)')
std('rdg','g25',A4,'c74'); std('sbl','g25',A4,'c75'); std('g25n40','g25',A4,'g25n40 (report)'); std('sbl','g25n40',A4,'sbl vs g25n40 (report)'); std('rdg','g25n40',A4,'rdg vs g25n40 (report)')
std('g25','base',[('G snr%d rho%d'%(sn,rho),[r for r in S if r['snr']==sn and r['rho']==rho]) for sn in (300,600) for rho in (100,150)],'c76')
std('g25','base',A4,'c48 (report)')
