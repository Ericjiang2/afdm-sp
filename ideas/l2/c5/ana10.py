# 循环 8 分析（判据见 PRED_cycle8.md）
import json,glob,math
import numpy as np
exec(open('ana5.py').read().split("R=[json.loads")[0])
R=[json.loads(l) for f in sorted(glob.glob('c8*_*.jsonl')) for l in open(f)]
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
ARMS8=('base','g25','g25off','g25p','g25m','g25n16','g25n8','sbl24')
def cpu(x): return x['t']+x.get('tfront',0.)*0+x.get('ta1',0.)
def selk(r,ks,name):
    if not all(ok(r,k) for k in ks): return
    best=min(ks,key=lambda k:(r[k]['syn'],ks.index(k))); s=dict(r[best]); s['t']=sum(r[k]['t'] for k in ks); r[name]=s
def ork(r,a,b2,name):
    if not(ok(r,a) and ok(r,b2)): return
    A,B=r[a],r[b2]; s=dict(A if A['a1_syn']==0 or B['a1_syn']!=0 else B); s['t']=A['t']+B['t']; r[name]=s
for r in R:
    selk(r,['g25','g25p','g25m'],'sel3'); selk(r,['g25','g25off'],'sel2'); ork(r,'g25','base','orb')
M=[r for r in R if r['snr']==450]; S=[r for r in R if r['snr']!=450]
grp=lambda sc:[('%s rho%d'%(sc,rho),[r for r in M if r['sc']==sc and r['rho']==rho]) for rho in (100,150)]
A4=grp('U')+grp('G')
und=sum(1 for r in R for k in ARMS8 if ok(r,k) and r[k]['a1_syn']==0 and r[k]['a1_err']>0); tot=sum(1 for r in R for k in ARMS8 if ok(r,k))
print('undetected (a1_syn=0, a1_err>0):',und,'of',tot,'arm-frames')
print('orb undetected:',sum(1 for r in M if 'orb' in r and r['orb']['a1_syn']==0 and r['orb']['a1_err']>0),'of',sum('orb' in r for r in M))
X=[r for r in M if ok(r,'g25') and ok(r,'base')]
cg=np.mean([cpu(r['g25']) for r in X]); cser=np.mean([cpu(r['g25'])+(cpu(r['base']) if r['g25']['a1_syn'] else 0.) for r in X]); cpar=np.mean([cpu(r['g25'])+cpu(r['base']) for r in X])
print('c77 CPU/frame (F0+A1): g25 %.3fs serial %.3fs (x%.2f) parallel %.3fs (x%.2f); serial runs base on %.1f%% frames'%(cg,cser,cser/cg,cpar,cpar/cg,100*np.mean([r['g25']['a1_syn']!=0 for r in X])))
print('sbl24 kept atoms mean %.2f min %d'%(np.mean([r['sbl24']['kept'] for r in M if ok(r,'sbl24')]),min(r['sbl24']['kept'] for r in M if ok(r,'sbl24'))))
std('orb','g25',A4,'c77'); std('g25n16','g25',A4,'c78'); std('g25n8','g25',A4,'g25n8 (report)')
std('sel3','g25',A4,'c79'); std('sel3','sel2',A4,'sel3 vs sel2 (report)'); std('sel2','g25',A4,'sel2 (report, c72 replication)')
std('sbl24','g25',A4,'c81')
std('g25','base',[('U snr%d rho%d'%(sn,rho),[r for r in S if r['snr']==sn and r['rho']==rho]) for sn in (300,600) for rho in (100,150)],'c80')
std('g25','base',A4,'c48 (report)')
