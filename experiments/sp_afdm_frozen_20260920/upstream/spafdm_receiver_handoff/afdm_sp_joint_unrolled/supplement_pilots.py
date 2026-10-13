"""Public-geometry pilot design and explicit DAFT/CPP waveform contract."""
import numpy as np
from .afdm_baselines import construct_sensing_matrix
from .budgeted_support_diagnostics import array_hash


def _vector(x):
    x=np.asarray(x)
    if x.ndim!=1 or not len(x) or not np.isfinite(x).all():raise ValueError('finite nonempty vector required')
    return x


def transform(x,c1,c2,*,inverse=False):
    x=_vector(x);n=np.arange(len(x));N=len(x)
    if not np.isfinite([c1,c2]).all():raise ValueError('finite chirps required')
    l1=np.exp(2j*np.pi*c1*n*n);l2=np.exp(2j*np.pi*c2*n*n)
    return np.conj(l1)*np.fft.ifft(np.conj(l2)*x)*np.sqrt(N) if inverse else l2*np.fft.fft(l1*x)/np.sqrt(N)


def cpp(signal,c1,length):
    signal=_vector(signal);N=len(signal)
    if type(length) is not int or not 0<=length<N or not np.isfinite(c1):raise ValueError('valid prefix length/chirp required')
    n=np.arange(-length,0)
    prefix=signal[n%N]*np.exp(2j*np.pi*c1*(N*N+2*N*n))
    return np.concatenate((prefix,signal))


def propagate_cpp(signal,c1,delays,dopplers,gains,*,prefix_length):
    """Sampled integer delays and continuous normalized Doppler; no channel scaling."""
    signal=_vector(signal);delays=_vector(delays);dopplers=_vector(dopplers);gains=_vector(gains)
    if (delays.shape!=dopplers.shape or delays.shape!=gains.shape or np.iscomplexobj(delays) or
            np.iscomplexobj(dopplers) or np.any(delays!=np.floor(delays)) or
            np.any(delays<0) or np.any(delays>prefix_length)):
        raise ValueError('matched paths with supported integer delays required')
    extended=cpp(signal,c1,prefix_length);N=len(signal);n=np.arange(N);out=np.zeros(N,complex)
    for delay,nu,gain in zip(delays.astype(int),dopplers,gains):
        out+=gain*np.exp(2j*np.pi*nu*n/N)*extended[prefix_length+n-delay]
    return out


def candidates(N,p0):
    p0=_vector(p0)
    if type(N) is not int or N<2 or p0.shape!=(N,) or not np.allclose(abs(p0),1,atol=1e-12,rtol=0):
        raise ValueError('unit modulus original pilot required')
    # Seeds fixed before geometry/receiver evaluation. p2 is never a p1 candidate.
    rows=[('original',p0.copy())]
    for i in range(7):
        rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([20260909,501,i])))
        rows.append((f'phase-{i}',np.exp(2j*np.pi*rng.random(N))))
    rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([20260909,502,0])))
    return rows,np.exp(2j*np.pi*rng.random(N))


def select_pilots(p0,*,c1,c2,l_max,k_max,rho=.5):
    """One deterministic choice among eight; only public sensing geometry is input."""
    p0=_vector(p0);N=len(p0)
    if not 0<rho<1:raise ValueError('interior power split required')
    choices,p2=candidates(N,p0);scores=[]
    for index,(name,p) in enumerate(choices):
        phi=construct_sensing_matrix(N,np.sqrt(rho)*p,c1,c2,l_max,k_max)
        norms=np.linalg.norm(phi,axis=0)
        if np.any(norms<=0) or not np.isfinite(norms).all():raise ValueError('invalid dictionary norms')
        normalized=phi/norms;gram=abs(normalized.conj().T@normalized);np.fill_diagonal(gram,0)
        scores.append(dict(index=index,name=name,max_coherence=float(gram.max()),
            pilot_sha256=array_hash(p),dictionary_sha256=array_hash(phi)))
    selected=min(range(8),key=lambda i:(scores[i]['max_coherence'],i))
    return dict(p0=p0.copy(),p1=choices[selected][1].copy(),p2=p2),dict(
        candidates=scores,selected_index=selected,selection='minimum maximum normalized dictionary coherence; tie by fixed index',
        truth_access='none',receiver_evaluations=0,p2_sha256=array_hash(p2))


def waveform_metrics(pilot,data,*,rho,c1,c2,prefix_length,papr_limit_db,peak_power_limit):
    """Scaled data supplied explicitly; no framewise renormalization or clipping."""
    pilot=_vector(pilot);data=_vector(data)
    if pilot.shape!=data.shape or not 0<rho<1 or not np.allclose(abs(pilot),1,atol=1e-12,rtol=0):raise ValueError('matched unit pilot and scaled data required')
    if not np.isfinite([papr_limit_db,peak_power_limit]).all() or papr_limit_db<0 or peak_power_limit<=0:raise ValueError('finite common power gates required')
    p=np.sqrt(rho)*pilot;z=p+data;s=transform(z,c1,c2,inverse=True);extended=cpp(s,c1,prefix_length)
    power=abs(s)**2;mean=float(power.mean());peak=float(np.max(abs(extended)**2))
    if mean<=0:raise ValueError('zero transmit energy')
    papr=float(10*np.log10(peak/mean));cross=float(2*np.vdot(p,data).real)
    metrics=dict(pilot_energy=float(np.vdot(p,p).real),data_energy=float(np.vdot(data,data).real),cross_energy=cross,
        payload_energy=float(power.sum()),prefix_energy=float(np.vdot(extended[:prefix_length],extended[:prefix_length]).real),
        mean_payload_power=mean,peak_power=peak,papr_db=papr,papr_limit_db=papr_limit_db,peak_power_limit=peak_power_limit,
        passes_declared_simulation_power_gate=bool(papr<=papr_limit_db and peak<=peak_power_limit),
        normalization='none; preserve original rho and individual pilot+data cross energy',
        deployment_scope='declared simulation gate only; no hardware amplifier validation')
    return s,extended,metrics


def paired_observations(H,data,noise,pilots,*,rho,sigma2):
    """Generator-only common H/data/noise construction; receiver sees observations only."""
    data=_vector(data);noise=_vector(noise);H=np.asarray(H);N=len(data)
    if (H.shape!=(N,N) or noise.shape!=(N,) or not np.isfinite(H).all() or
            set(pilots)!={'p0','p1','p2'} or not np.isfinite([rho,sigma2]).all() or not 0<rho<1 or sigma2<=0):
        raise ValueError('valid common channel/data/noise and three pilots required')
    common=H@data+np.sqrt(sigma2)*noise;observed={}
    for name,p in pilots.items():
        p=_vector(p)
        if p.shape!=(N,) or not np.allclose(abs(p),1,atol=1e-12,rtol=0):raise ValueError('unit pilot required')
        scaled=np.sqrt(rho)*p
        observed[name]=dict(y=H@scaled+common,pilot=scaled.copy(),sigma2=float(sigma2))
    return observed,dict(H_sha256=array_hash(H),data_sha256=array_hash(data),noise_sha256=array_hash(noise),
        rho=rho,sigma2=sigma2,normalization='none',scope='generator-only shared external block; no H returned to receiver')
