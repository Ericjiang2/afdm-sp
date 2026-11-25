"""Round 7 runner l, dropped draft 11 (2026-11-23): does the amount of spreading (OFDM none / AFDM / single carrier full)
change which code is right?  True channel, N=256, 8 paths, fractional Doppler +-2 bins, QPSK, LMMSE-PIC detector EXIT curves
(measured), regular (3,6) LDPC by Gaussian-approximation density evolution, matched code by the area property.
Read-only; 76 s on the laptop (over the 30 s probe cap: the SNR grid is 1 dB and only 10 channels).  Exploratory."""
import numpy as np, time
t0=time.time()
def J(s): return (1-2**(-0.3073*np.maximum(s,0)**(2*0.8935)))**1.1064
def Jinv(I):
    I=np.clip(I,1e-9,1-1e-9); return (-(1/0.3073)*np.log2(1-I**(1/1.1064)))**(1/(2*0.8935))
def dec36(Ich,iters=200):                      # regular (3,6) LDPC, Gaussian-approx DE; returns extrinsic MI fed back, posterior MI
    Icv=0.0
    for _ in range(iters):
        Ivc=J(np.sqrt(2*Jinv(Icv)**2+Jinv(Ich)**2)); Icv=1-J(np.sqrt(5)*Jinv(1-Ivc))
    return J(np.sqrt(3)*Jinv(Icv)), J(np.sqrt(3*Jinv(Icv)**2+Jinv(Ich)**2))
N=256; P=8; rng=np.random.default_rng(11); k=np.arange(N)
F=np.fft.fft(np.eye(N),axis=0)/np.sqrt(N)
c1=5/(2*N); c2=1/(N*N*np.pi)
A=np.exp(2j*np.pi*c2*k**2)[:,None]*F*np.exp(2j*np.pi*c1*k**2)[None,:]
U=dict(afdm=A.conj().T, ofdm=F.conj().T, sc=np.eye(N,dtype=complex))
IA=np.array([0,.2,.4,.6,.8,.95,.999]); SNR=np.arange(0,9.01,1.0); NCH=10
def exit_curve(Heff,s2,rng):
    out=[]
    b=rng.choice([-1.,1.],(2,N)); s=(b[0]+1j*b[1])/np.sqrt(2)
    y=Heff@s+np.sqrt(s2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
    HH=Heff.conj().T
    for ia in IA:
        sa=Jinv(ia); L=(sa**2/2)*b+sa*rng.standard_normal((2,N))
        m=(np.tanh(L[0]/2)+1j*np.tanh(L[1]/2))/np.sqrt(2); v=np.maximum(1-np.abs(m)**2,1e-9)
        S=np.linalg.inv((Heff*v[None,:])@HH+s2*np.eye(N)); G=HH@S
        a=np.real(np.einsum('ij,ji->i',G,Heff)); r=G@(y-Heff@m)
        rho=a/(1-v*a); z=(r+a*m)/a
        LE=np.stack([2*np.sqrt(2)*rho*z.real,2*np.sqrt(2)*rho*z.imag])
        out.append(1-np.mean(np.log2(1+np.exp(-b*LE))))
    return np.array(out)
res={w:np.zeros((NCH,len(SNR),len(IA))) for w in U}
for c in range(NCH):
    l=rng.choice(26,P,replace=False); nu=rng.uniform(-2,2,P); h=(rng.standard_normal(P)+1j*rng.standard_normal(P)); h/=np.linalg.norm(h)
    Ht=np.zeros((N,N),complex)
    for li,ni,hi in zip(l,nu,h): Ht[k,(k-li)%N]+=hi*np.exp(2j*np.pi*ni*k/N)
    for w,Uw in U.items():
        Heff=Ht@Uw
        for i,sdb in enumerate(SNR):
            res[w][c,i]=np.mean([exit_curve(Heff,10**(-sdb/10),rng) for _ in range(2)],axis=0)
def thr(vals,target):                           # first SNR where vals>=target, linear interpolation
    for i in range(len(SNR)):
        if vals[i]>=target:
            if i==0: return SNR[0]
            return SNR[i-1]+(target-vals[i-1])/(vals[i]-vals[i-1])
    return np.nan
print('per-channel thresholds for 1 bit/sym (QPSK, rate 1/2), median [10%..90%] over',NCH,'channels; N=256, 8 paths, true channel')
summ={}
for w in U:
    area=np.trapz(res[w],IA,axis=2)/(IA[-1]-IA[0]); t0v=res[w][:,:,0]
    conv=np.zeros((NCH,len(SNR)))
    for c in range(NCH):
        for i in range(len(SNR)):
            ia=0.0
            for _ in range(60):
                idet=np.interp(ia,IA,res[w][c,i]); ia,post=dec36(idet)
            conv[c,i]=post
    T_area=np.array([thr(area[c],0.5) for c in range(NCH)]); T_reg=np.array([thr(conv[c],0.999) for c in range(NCH)]); T_one=np.array([thr(t0v[c],0.577) for c in range(NCH)])
    summ[w]=(T_area,T_reg,T_one)
    q=lambda x: f'{np.nanmedian(x):5.2f} [{np.nanquantile(x,.1):5.2f}..{np.nanquantile(x,.9):5.2f}]'
    print(f'{w:5s} matched-code(area=0.5): {q(T_area)} | regular(3,6) turbo DE: {q(T_reg)} | one-shot T(0)>=.577: {q(T_one)} | mean T(0),T(1),area @4dB: {t0v[:,4].mean():.3f} {res[w][:,4,-1].mean():.3f} {area[:,4].mean():.3f}')
for a_,b_ in (('ofdm','afdm'),('sc','afdm')):
    print(f'paired {a_}-{b_}: matched {np.nanmean(summ[a_][0]-summ[b_][0]):+.2f} dB | regular {np.nanmean(summ[a_][1]-summ[b_][1]):+.2f} dB | one-shot {np.nanmean(summ[a_][2]-summ[b_][2]):+.2f} dB')
print('gain of matched over regular: ',{w:round(float(np.nanmean(summ[w][1]-summ[w][0])),2) for w in U})
print('t',round(time.time()-t0,1))
