import sys, os; sys.path.insert(0, os.path.expanduser('~/repos/afdm-sp/ideas/l2'))
import c_l2_c08_iface as m, numpy as np
from multiprocessing import get_context
def job(fr):
    C=m.stageA.setup(); ctx=C['ctx']; st=C['stage3']; out=[]; N=1024; n=np.arange(N)
    for s in ('U','G'):
        b=st.inputs(ctx,fr,s,100); p=b[0]['params']; raw,obs,truth=st.observed(ctx,b,100,550)
        d,arr,syn,_=st.e1.f0_state(ctx,obs)
        l=np.asarray(p['l_i']).astype(int); k=np.asarray(p['k_real'],float); g=np.asarray(p['g_i'],complex)
        le=np.asarray(arr['r1_delays']).astype(int); ke=np.asarray(arr['r1_dopplers'],float); ge=np.asarray(arr['r1_gains'],complex)
        prof=np.zeros(N); miss=0.; false=0.; dk=[]
        for i in range(len(l)):
            tr=g[i]*np.exp(2j*np.pi*k[i]*n/N); j=np.flatnonzero(le==l[i])
            if len(j)==0: miss+=abs(g[i])**2; prof+=abs(tr)**2; continue
            es=sum(ge[q]*np.exp(2j*np.pi*ke[q]*n/N) for q in j)
            # remove unknown constant phase convention: best complex scalar fit
            a=np.vdot(es,tr)/np.vdot(es,es); prof+=abs(tr-a*es)**2; dk.append(ke[j[np.argmax(abs(ge[j]))]]-k[i]); out_a=abs(a)
        for q in range(len(le)):
            if le[q] not in l: false+=abs(ge[q])**2; prof+=abs(ge[q])**2
        out.append(dict(syn=int(syn>0), seg=prof.reshape(8,-1).mean(1).tolist(), miss=miss, false=false, tot=float(np.sum(abs(g)**2)), dk=float(np.sqrt(np.mean(np.square(dk)))) if dk else -1, a=float(out_a) if dk else -1, s2=float(obs['sigma2'])))
    return out
if __name__=='__main__':
    with get_context('spawn').Pool(2) as p: R=sum(p.map(job, range(41000,41030)),[])
    for nm,sel in (('F0 pass',[r for r in R if not r['syn']]),('F0 fail',[r for r in R if r['syn']])):
        seg=np.mean([np.array(r['seg'])/r['s2'] for r in sel],0)
        print(nm,len(sel),'interf/sigma2 by 8 time segments',np.round(seg,2),'miss/tot',np.round(np.mean([r['miss']/r['tot'] for r in sel]),3),'false/tot',np.round(np.mean([r['false']/r['tot'] for r in sel]),3),'dk rms',np.round(np.mean([r['dk'] for r in sel]),3),'|a|',np.round(np.median([r['a'] for r in sel]),2),'tot',np.round(np.mean([r['tot'] for r in sel]),2),'s2',np.round(sel[0]['s2'],3))
