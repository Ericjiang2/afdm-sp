"""BP susceptibility screen on the SAME exact-enumeration fixture.
Not the production decoder; no TF end-to-end claim.
"""
import json
from pathlib import Path
import numpy as np
from scipy.special import logsumexp
from score_probe import physical

def bp_response(H, L, iters=50, damping=.5):
    """Finite-iteration sum-product plus exact forward derivative wrt L.
    Deliberately return the raw symmetric response, without PSD repair.
    """
    checks=[np.flatnonzero(row) for row in H]
    masks=[]
    for vs in checks:
        t=np.arange(len(vs)); off=t[:,None]!=t[None,:]
        triple=(t[None,None,:]!=t[:,None,None]) & (t[None,None,:]!=t[None,:,None])
        masks.append((off,triple))
    nb=len(L); offsets=np.cumsum([0]+[len(s) for s in checks])
    ev=np.concatenate(checks); ident=np.eye(nb); nv=len(ev)
    vmsg=L[ev].copy(); dv=ident[ev].copy()
    r=np.zeros(nv); dr=np.zeros((nv,nb))
    for _ in range(iters):
        rnew=np.zeros(nv); drnew=np.zeros((nv,nb))
        for j,vs in enumerate(checks):
            ix=np.arange(offsets[j],offsets[j+1]); z=np.tanh(vmsg[ix]/2)
            dz=.5*(1-z*z)[:,None]*dv[ix]
            off,triple=masks[j]
            prods=np.prod(np.where(off,z[None,:],1.),axis=1)
            pc=np.clip(prods,-1+1e-12,1-1e-12)
            rnew[ix]=2*np.arctanh(pc)
            others=np.prod(np.where(triple,z[None,None,:],1.),axis=2)
            local=others*(1-z*z)[None,:]/np.maximum(1e-24,1-prods*prods)[:,None]
            local*=off
            local[abs(prods)>=1-1e-12]=0
            drnew[ix]=local@dv[ix]
        r=(1-damping)*r+damping*rnew; dr=(1-damping)*dr+damping*drnew
        app=L.copy(); da=ident.copy();np.add.at(app,ev,r);np.add.at(da,ev,dr)
        vmsg=app[ev]-r;dv=da[ev]-dr
    m=np.tanh(app/2); jac=.5*(1-m*m)[:,None]*da
    raw=2*jac; sym=(raw+raw.T)/2
    return m,sym,dict(asymmetry=float(np.linalg.norm(raw-raw.T)/max(1e-12,np.linalg.norm(raw))),min_eig=float(np.linalg.eigvalsh(sym)[0]))

def product_or_response_score(U,y,H0,T,p,m,Sigma):
    mx=p+T@m
    # E||x||^2 from first and second moments, no iid-symbol assumption.
    Ea=float(np.vdot(mx,mx).real+np.trace(T@Sigma@T.conj().T).real)
    coh=[]; score=[]
    for Um in U:
        aa=Um.conj().T@y;K=Um.conj().T@H0
        b=T.conj().T@(aa-K@mx)-(mx.conj()@K@T).T
        SS=T.conj().T@K@T;SS=(SS+SS.T)/2
        ez=mx.conj()@(aa-K@mx)-np.sum(SS*Sigma)
        vv=float(np.real(b@Sigma@b.conj()))
        coh.append(abs(ez)**2/max(Ea,1e-12));score.append((abs(ez)**2+vv,Ea))
    return np.array(coh),np.array(score)

def run(seed=9122,frames=300):
    rng=np.random.default_rng(seed);n=12;k=8;nb=24
    G=np.vstack([np.eye(k,dtype=int),rng.integers(0,2,(2*n-k,k))]);H=np.hstack([G[k:],np.eye(nb-k,dtype=int)])
    assert np.max((H@G)%2)==0
    bits=(np.arange(2**k)[:,None]>>np.arange(k)[None,:])&1;cb=(bits@G.T)%2;signs=1-2*cb
    D=.5*(signs[:,0::2]+1j*signs[:,1::2]);p=np.exp(2j*np.pi*rng.random(n))/np.sqrt(2);X=D+p
    coords=[(l,v) for l in range(1,7) for v in [-1.7,-1.1,-.4,.3,.9,1.6]]
    U=np.array([physical(n,l,v) for l,v in coords]);UX=np.einsum('qij,cj->qci',U,X)
    U0=physical(n,0,.17);x0=X@U0.T;H0=np.sqrt(.7)*U0
    T=np.zeros((n,2*n),complex);T[np.arange(n),2*np.arange(n)]=.5;T[np.arange(n),2*np.arange(n)+1]=.5j
    gammas=np.array([.01,.04,.15,.5]);records=[]
    for idx in range(frames):
        sn=.3 if idx%2==0 else .6;true=rng.integers(len(X));target=rng.integers(len(coords));phase=np.exp(2j*np.pi*rng.random())
        y=np.sqrt(.7)*x0[true]+np.sqrt(.3)*phase*UX[target,true]+np.sqrt(sn/2)*(rng.normal(size=n)+1j*rng.normal(size=n))
        R=y-np.sqrt(.7)*x0;logp=-np.sum(abs(R)**2,axis=1)/sn;logp-=logsumexp(logp);q=np.exp(logp)
        # The one-path known H0 is unitary up to scale: scalar bit LLRs are exact.
        ym=U0.conj().T@y/np.sqrt(.7)-p;L=np.empty(nb);L[0::2]=2*ym.real/(sn/.7);L[1::2]=2*ym.imag/(sn/.7)
        lcode=.5*signs@L;lcode-=logsumexp(lcode);assert np.max(abs(lcode-logp))<1e-10
        m,Sig,meta=bp_response(H,L)
        cprod,sprod=product_or_response_score(U,y,H0,T,p,m,np.diag(1-m*m))
        cres,sres=product_or_response_score(U,y,H0,T,p,m,Sig)
        valid=meta['min_eig']>=-1e-8 and meta['asymmetry']<1e-3
        score=sres[:,0]-sn*sres[:,1]
        # Frozen non-PSD/asymmetry fallback; no eigenvalue tuning.
        if not valid:score=sprod[:,0]-sn*sprod[:,1]
        cand=[int(np.argmax(cprod)),int(np.argmax(sprod[:,0]-sn*sprod[:,1])),int(np.argmax(cres)),int(np.argmax(score))]
        z=np.einsum('qci,ci->qc',UX.conj(),R);a=np.sum(abs(X)**2,axis=1)
        lr=gammas[None,:,None]*abs(z[:,None,:])**2/(sn**2*(1+gammas[None,:,None]*a[None,None,:]/sn))-np.log1p(gammas[None,:,None]*a[None,None,:]/sn)
        bf=logsumexp(logp[None,None,:]+lr,axis=-1)
        outs=[]
        for c in cand:outs.append(int(np.argmax(logp+lr[c,np.argmax(bf[c])])))
        records.append(dict(frame=idx,sigma2=sn,baseline_error=bool(np.argmax(q)!=true),correct_choices=[bool(c==target) for c in cand],output_errors=[bool(o!=true) for o in outs],response_valid=bool(valid),mse_mean=float(np.mean((m-q@signs)**2)),**meta))
    out={}
    for sn in [.3,.6]:
        rr=[r for r in records if r['sigma2']==sn];o={'n':len(rr),'baseline_errors':sum(r['baseline_error'] for r in rr),'valid_responses':sum(r['response_valid'] for r in rr),'mean_mse':float(np.mean([r['mse_mean'] for r in rr]))}
        for j,name in enumerate(['bp_product_coherent','bp_product_linear_variance','bp_response_coherent_unchecked','bp_response_linear_variance_guarded']):
            o[name]=dict(right_atom=sum(r['correct_choices'][j] for r in rr),errors=sum(r['output_errors'][j] for r in rr),rescue=sum(r['baseline_error'] and not r['output_errors'][j] for r in rr),harm=sum(not r['baseline_error'] and r['output_errors'][j] for r in rr))
        out[str(sn)]=o
    Path(__file__).with_name('bp_response_probe_results.json').write_text(json.dumps(dict(summary=out,records=records),indent=2));print(json.dumps(out,indent=2))

if __name__=='__main__':run()
