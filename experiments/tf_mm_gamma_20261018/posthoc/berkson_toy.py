# Toy, independent of project code: Berkson data uncertainty in a data-aided dictionary.
# Atoms b_k(x) = x * exp(j2pi nu_k n/N); x_true = mu + u, u ~ indep per symbol, Var v_n (Berkson: u indep of mu).
# Oracle support (true atoms incl. two co-delay atoms with close Doppler). Compare gain estimators:
#   LS     : (Bm^H Bm + s2 I)^-1 Bm^H y                (Gamma = 0, soft means)
#   EIVdiag: (Bm^H Bm + sum(v) I + s2 I)^-1 Bm^H y
#   EIVfull: (Bm^H Bm + G + s2 I)^-1 Bm^H y,  G_jk = sum_n v_n exp(j2pi(nu_k-nu_j)n/N)
import numpy as np
rng=np.random.default_rng(0); N=256; s2=0.05; T=4000
nus=np.array([0.3,0.45,1.7,-1.2]); K=len(nus); n=np.arange(N)
E=np.exp(2j*np.pi*np.outer(n,nus)/N)
G_phase=np.exp(2j*np.pi*(nus[None,:]-nus[:,None])[:,:,None]*n[None,None,:]/N)  # K,K,N
for vscale in (0.05,0.2,0.5):
    mse={'LS':0,'EIVdiag':0,'EIVfull':0,'oracle_x':0}
    for t in range(T):
        # soft posterior: per-symbol QPSK with random reliability -> mu, v ; x_true sampled from it
        p=rng.uniform(0.5,1.0,(N,2))**(1/vscale*0.05) if False else None
        sgn=rng.choice([-1,1],(N,2)); r=np.clip(rng.normal(1-vscale,vscale/2,(N,2)),0,1)  # |E[component]|
        mu=(sgn[:,0]*r[:,0]+1j*sgn[:,1]*r[:,1])/np.sqrt(2)
        pr=(1+r)/2; comp=np.where(rng.random((N,2))<pr,sgn,-sgn)
        x=(comp[:,0]+1j*comp[:,1])/np.sqrt(2); v=(2-r[:,0]**2-r[:,1]**2)/2
        h=(rng.normal(size=K)+1j*rng.normal(size=K))/np.sqrt(2)
        y=(x[:,None]*E)@h+np.sqrt(s2/2)*(rng.normal(size=N)+1j*rng.normal(size=N))
        Bm=mu[:,None]*E; Bx=x[:,None]*E; b=Bm.conj().T@y
        G=(G_phase*v[None,None,:]).sum(-1)
        Q=Bm.conj().T@Bm
        est={'LS':np.linalg.solve(Q+s2*np.eye(K),b),
             'EIVdiag':np.linalg.solve(Q+v.sum()*np.eye(K)+s2*np.eye(K),b),
             'EIVfull':np.linalg.solve(Q+G+s2*np.eye(K),b),
             'oracle_x':np.linalg.solve(Bx.conj().T@Bx+s2*np.eye(K),Bx.conj().T@y)}
        for k,e in est.items(): mse[k]+=np.sum(abs(e-h)**2)/np.sum(abs(h)**2)/T
    print(f"mean v={v.mean():.3f}", {k:round(10*np.log10(m),2) for k,m in mse.items()})
