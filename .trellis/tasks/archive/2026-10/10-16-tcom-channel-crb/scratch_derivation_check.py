import sys, numpy as np
sys.path.insert(0, sys.argv[1])
from physical import Channel
rng=np.random.default_rng(1)
N=64; c1=5/(2*N); c2=np.sqrt(2)/N
l=np.array([0,3,3]); nu=np.array([.3,-.7,.45]); g=(rng.standard_normal(3)+1j*rng.standard_normal(3))/np.sqrt(6)
P=3; k=np.arange(N)
def cols(u,nu=nu,g=g):
    R=Channel(N,c1,c2,l,nu,np.ones(P)).regressors(u); Rd=Channel(N,c1,c2,l,nu,np.ones(P)).regressors(u,derivative=True)
    return np.hstack([Rd*g, R, 1j*R])
def dense(nu=nu,g=g):
    return np.stack([Channel(N,c1,c2,l,nu,g).apply(e) for e in np.eye(N)],1)
# derivative check
h=1e-6; Hp=dense(nu+np.array([h,0,0])); Hm=dense(nu-np.array([h,0,0]))
u=rng.standard_normal(N)+1j*rng.standard_normal(N)
print('dnu fd err', np.linalg.norm((Hp-Hm)@u/(2*h)-cols(u)[:,0])/np.linalg.norm(cols(u)[:,0]))
# analytic K
def tr(i,j,w):
    if l[i]!=l[j]: return 0
    return np.sum(w*np.exp(2j*np.pi*k*(nu[j]-nu[i])/N))
w0=np.ones(N); w1=1j*2*np.pi*k/N
K=np.zeros((3*P,3*P),complex)
# param a: (type, i): type 0 nu coef g_i with D, 1 Re coef 1, 2 Im coef j
pars=[(0,i) for i in range(P)]+[(1,i) for i in range(P)]+[(2,i) for i in range(P)]
coef=lambda t,i: g[i] if t==0 else (1 if t==1 else 1j)
for a,(ta,i) in enumerate(pars):
  for b,(tb,j) in enumerate(pars):
    wa = w1 if ta==0 else w0; wb = w1 if tb==0 else w0
    K[a,b]=np.conj(coef(ta,i))*coef(tb,j)*tr(i,j,np.conj(wa)*wb)
# dense K via derivative matrices
H=dense(); G=[]
for a,(t,i) in enumerate(pars):
    if t==0:
        d=np.zeros(P); d[i]=h; G.append((dense(nu+d)-dense(nu-d))/(2*h))
    else:
        e=np.zeros(P,complex); e[i]=1 if t==1 else 1j
        G.append(dense(g=e))   # H linear in g
Kd=np.array([[np.vdot(A,B) for B in G] for A in G])
print('K err', np.linalg.norm(K-Kd)/np.linalg.norm(Kd))
s2=.1
# identity: J=(2/s2)ReK -> b=3P s2/(2||H||^2)
J=(2/s2)*K.real; b=np.trace(np.linalg.solve(J,K.real)); print('identity', b, 3*P*s2/2)
# G3a DA MC score covariance
x=np.exp(2j*np.pi*rng.random(N))
B=cols(x); JDA=(2/s2)*(B.conj().T@B).real
M=20000; mu=H@x
W=(rng.standard_normal((N,M))+1j*rng.standard_normal((N,M)))*np.sqrt(s2/2)
S=(2/s2)*(B.conj().T@W).real     # analytic score at truth
print('DA MC err', np.linalg.norm(S@S.T/M-JDA)/np.linalg.norm(JDA))
# G5 attainability: GN ML with data known at high SNR
s2=1e-3; JDA=(2/s2)*(B.conj().T@B).real; crb=np.linalg.inv(JDA)
th0=np.concatenate([nu,g.real,g.imag]); errs=[]; nm=[]
for r in range(2000):
    y=mu+(rng.standard_normal(N)+1j*rng.standard_normal(N))*np.sqrt(s2/2)
    th=th0.copy()
    for it in range(4):
        nn=th[:P]; gg=th[P:2*P]+1j*th[2*P:]
        Bt=cols(x,nn,gg); res=y-Channel(N,c1,c2,l,nn,gg).apply(x)
        A=np.vstack([Bt.real,Bt.imag]) ; rr=np.concatenate([res.real,res.imag])
        th=th+np.linalg.lstsq(A,rr,rcond=None)[0]
    errs.append(th-th0)
    nn=th[:P]; gg=th[P:2*P]+1j*th[2*P:]
    nm.append(np.linalg.norm(Channel(N,c1,c2,l,nn,gg).apply(np.eye(N)[0])*0)+np.linalg.norm(dense(nn,gg)-H)**2 if r<200 else np.nan)
E=np.array(errs); print('GN mse/crb trace', np.trace(E.T@E/len(E))/np.trace(crb))
nm=np.array(nm)[:200]; print('H nmse ratio', np.mean(nm)/np.trace(crb@K.real))
