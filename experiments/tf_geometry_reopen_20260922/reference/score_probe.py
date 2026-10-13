"""Exploratory exact-code score comparison; not production TF."""
import json
from pathlib import Path
import numpy as np
from scipy.special import logsumexp

def physical(n, l, nu, c1=.037, c2=.011):
    t=np.arange(n); F=np.exp(-2j*np.pi*t[:,None]*t[None,:]/n)/np.sqrt(n)
    A=np.exp(2j*np.pi*c2*t*t)[:,None]*F*np.exp(2j*np.pi*c1*t*t)[None,:]
    chi=np.where(t<l,np.exp(2j*np.pi*c1*(n*n+2*n*(t-l))),1)
    M=np.zeros((n,n),complex); M[t,(t-l)%n]=chi*np.exp(2j*np.pi*nu*t/n)
    return A@M@A.conj().T

def run(seed=9122,frames=300):
    rng=np.random.default_rng(seed); n=12;k=8
    G=np.vstack([np.eye(k,dtype=int),rng.integers(0,2,(2*n-k,k))])
    bits=(np.arange(2**k)[:,None]>>np.arange(k)[None,:])&1
    cb=(bits@G.T)%2
    D=.5*((1-2*cb[:,0::2])+1j*(1-2*cb[:,1::2]))
    p=np.exp(2j*np.pi*rng.random(n))/np.sqrt(2); X=D+p
    coords=[(l,v) for l in range(1,7) for v in [-1.7,-1.1,-.4,.3,.9,1.6]]
    U=np.array([physical(n,l,v) for l,v in coords]);
    UX=np.einsum('qij,cj->qci',U,X)
    U0=physical(n,0,.17); x0=X@U0.T
    amp0=np.sqrt(.7); amp1=np.sqrt(.3)
    gammas=np.array([.01,.04,.15,.5])
    records=[]
    for idx in range(frames):
        sn=.3 if idx%2==0 else .6
        true=rng.integers(len(X)); target=rng.integers(len(coords)); phase=np.exp(2j*np.pi*rng.random())
        y=amp0*x0[true]+amp1*phase*UX[target,true]+np.sqrt(sn/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
        R=y-amp0*x0
        logp=-np.sum(abs(R)**2,axis=1)/sn; logp-=logsumexp(logp); q=np.exp(logp)
        z=np.einsum('qci,ci->qc',UX.conj(),R)
        a=np.sum(abs(X)**2,axis=1)
        Ez=z@q; Ea=a@q
        coh=abs(Ez)**2/Ea
        vscore=(abs(z)**2)@q-sn*Ea
        # VB: integrate exp(E_q log likelihood ratio), vs collapse inside q.
        vb=np.max(abs(Ez[:,None])**2/(sn*(Ea+sn/gammas[None,:]))-np.log1p(gammas[None,:]*Ea/sn),axis=1)
        lr=(gammas[None,:,None]*abs(z[:,None,:])**2/(sn**2*(1+gammas[None,:,None]*a[None,None,:]/sn))
             -np.log1p(gammas[None,:,None]*a[None,None,:]/sn))
        allbf=logsumexp(logp[None,None,:]+lr,axis=-1)
        ib=np.unravel_index(np.argmax(allbf),allbf.shape)
        cand=np.array([np.argmax(coh),np.argmax(vscore),np.argmax(vb),ib[0]])
        out=[]
        for which in cand:
            gidx=int(np.argmax(allbf[which]))
            out.append(int(np.argmax(logp+lr[which,gidx])))
        records.append(dict(frame=idx,sigma2=sn,baseline_error=bool(np.argmax(q)!=true),
             rank_coh=int(np.sum(coh>coh[target])+1),rank_var=int(np.sum(vscore>vscore[target])+1),
             rank_vb=int(np.sum(vb>vb[target])+1),rank_bf=int(np.sum(allbf.max(1)>allbf.max(1)[target])+1),
             correct_choices=(cand==target).tolist(),output_errors=[bool(c!=true) for c in out],
             maxq=float(q.max()),truthq=float(q[true]),target=int(target)))
    out={}
    for sn in [.3,.6]:
        rr=[r for r in records if r['sigma2']==sn]
        out[str(sn)]={'n':len(rr),'baseline_errors':sum(r['baseline_error'] for r in rr)}
        for j,name in enumerate(['coherent','variance_score','vb','collapsed_bf']):
            out[str(sn)][name]={'right_atom':sum(r['correct_choices'][j] for r in rr),
                 'errors':sum(r['output_errors'][j] for r in rr),
                 'rescue':sum(r['baseline_error'] and not r['output_errors'][j] for r in rr),
                 'harm':sum(not r['baseline_error'] and r['output_errors'][j] for r in rr)}
    Path(__file__).with_name('score_probe_results.json').write_text(json.dumps({'summary':out,'records':records},indent=2))
    print(json.dumps(out,indent=2))
if __name__=='__main__':run()
