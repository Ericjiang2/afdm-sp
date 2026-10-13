"""Small operator/uncoded-oracle experiments; explicitly not production FER evidence."""
import ast
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE.parent / 'code' / 'source'  # Frozen source copies supplied in this bundle.


def load_original_functions():
    namespace = {'np': np}
    bindings = {}
    sources = {'supplement_pilots.py': ['_vector', 'transform', 'cpp', 'propagate_cpp'],
               'supplement_g1.py': ['physical_channel_matrix']}
    for filename, wanted in sources.items():
        path = SOURCE_DIR / filename
        raw = path.read_bytes()
        tree = ast.parse(raw.decode())
        selected = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in wanted]
        assert {x.name for x in selected} == set(wanted)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
        bindings[filename] = {'sha256': hashlib.sha256(raw).hexdigest(), 'functions': wanted}
    return namespace, bindings


def coefficients(n, delays, dopplers, gains):
    t = np.arange(n)
    return {int(delay): np.fft.fft(sum(g*np.exp(2j*np.pi*nu*t/n)
                                     for l, nu, g in zip(delays,dopplers,gains) if l==delay))/n
            for delay in np.unique(delays)}


def projected_apply(x, coeffs, width, c1, c2):
    n = len(x); index = np.arange(n); out = np.zeros(n, complex)
    for delay, coeff in coeffs.items():
        for q in range(-width, width+1):
            row = (index + round(2*n*c1)*delay + q) % n
            phase = np.exp(2j*np.pi*(-c1*delay**2+c2*(row**2-index**2)-delay*index/n))
            out[row] += coeff[q % n]*phase*x
    return out


def projection_matrix(n, coeffs, width, c1, c2):
    index=np.arange(n); out=np.zeros((n,n),complex)
    for delay, coeff in coeffs.items():
        for q in range(-width,width+1):
            row=(index+round(2*n*c1)*delay+q)%n
            out[row,index]+=coeff[q%n]*np.exp(2j*np.pi*(-c1*delay**2+c2*(row**2-index**2)-delay*index/n))
    return out


def symbol_errors(estimate, actual):
    return int(np.count_nonzero(
        ((estimate.real >= 0)!=(actual.real >= 0)) | ((estimate.imag >= 0)!=(actual.imag >= 0))))


def main():
    start=time.perf_counter(); f, bindings=load_original_functions()
    contract=json.loads((HERE/'small_experiments_contract.json').read_text())
    transform, propagate = f['transform'],f['propagate_cpp']
    e0=[]; n=1024; idx=np.arange(n); c1=5/(2*n); c2=(np.sqrt(2)-1)/(2*n*n)
    pilot=np.sqrt(.5)*np.exp(-1j*np.pi*idx**2/n)
    for center in (0,2):
        for eps in (0.,.1,.25,.49):
            delays=np.array([1]); nu=np.array([center+eps]); gains=np.array([1+0j])
            coeffs=coefficients(n,delays,nu,gains)
            full_p=transform(propagate(transform(pilot,c1,c2,inverse=True),c1,delays,nu,gains,
                                      prefix_length=3),c1,c2)
            for width in (2,4,8,16,32):
                kept=sum(np.sum(abs(co[(np.arange(-width,width+1)%n)])**2) for co in coeffs.values())
                total=sum(np.sum(abs(co)**2) for co in coeffs.values())
                matrix_tail=n*max(0.,total-kept)
                pe=full_p-projected_apply(pilot,coeffs,width,c1,c2)
                e0.append(dict(center=center,epsilon=eps,width=width,
                    operator_nmse=matrix_tail/(n*total),pilot_error_energy=float(np.vdot(pe,pe).real),
                    expected_data_error_energy=.5*matrix_tail,
                    pilot_relative_error=float(np.vdot(pe,pe).real/np.vdot(full_p,full_p).real)))
    e1=[]; checks=[]; n=128; idx=np.arange(n);c1=5/(2*n);c2=(np.sqrt(2)-1)/(2*n*n)
    path_g=np.array([.7,.45*np.exp(.4j),.35*np.exp(-.3j)]);path_g/=np.linalg.norm(path_g)
    scenarios=[('single',np.array([1]),np.array([.49]),np.array([1+0j])),
               ('three_paths',np.array([1,3,3]),np.array([.37,-1.48,1.35]),path_g)]
    raw_arrays={}
    for si,(name,delays,nu,gains) in enumerate(scenarios):
        h=f['physical_channel_matrix'](n,c1,c2,delays,nu,gains,prefix_length=3)
        coeffs=coefficients(n,delays,nu,gains)
        raw_arrays[f'{name}_H']=h
        for rho in (.2,.5):
            pd=1-rho;pilot=np.sqrt(rho)*np.exp(-1j*np.pi*idx**2/n)
            for snr in (8,14):
                sigma=10**(-snr/10); ests={}
                full_filter=np.linalg.solve(h.conj().T@h+(sigma/pd)*np.eye(n),h.conj().T)
                for width in (2,8):
                    hc=projection_matrix(n,coeffs,width,c1,c2)
                    err=h-hc
                    filt=np.linalg.solve(hc.conj().T@hc+(sigma/pd)*np.eye(n),hc.conj().T)
                    ests[width]=(hc,filt,dict(operator_nmse=float(np.linalg.norm(err)**2/np.linalg.norm(h)**2),
                        pilot_error_energy=float(np.linalg.norm(err@pilot)**2),
                        expected_data_error_energy=float(pd*np.linalg.norm(err)**2)))
                for block in range(16):
                    # Same exogenous data/noise across SNR/rho/width/arms for a scenario+block.
                    rng=np.random.default_rng(np.random.SeedSequence([20260913,177,si,block]))
                    data=np.sqrt(pd/2)*((2*rng.integers(0,2,n)-1)+1j*(2*rng.integers(0,2,n)-1))
                    noise=(rng.standard_normal(n)+1j*rng.standard_normal(n))/np.sqrt(2)
                    clean=transform(propagate(transform(pilot+data,c1,c2,inverse=True),c1,delays,nu,gains,
                                              prefix_length=3),c1,c2)
                    rel=float(np.linalg.norm(clean-h@(pilot+data))/np.linalg.norm(clean))
                    assert rel<1e-10,rel
                    checks.append(rel); y=clean+np.sqrt(sigma)*noise
                    truth_errors=symbol_errors(full_filter@(y-h@pilot),data)
                    raw_arrays[f'{name}_rho{rho}_s{snr}_b{block}_y']=y
                    raw_arrays[f'{name}_rho{rho}_s{snr}_b{block}_data']=data
                    for width,(hc,filt,diag) in ests.items():
                        e1.append(dict(scenario=name,rho=rho,snr_db=snr,width=width,block=block,
                            errors_same=symbol_errors(filt@(y-hc@pilot),data),
                            errors_full_pilot=symbol_errors(filt@(y-h@pilot),data),
                            errors_full_H=truth_errors,symbols=n,**diag))
    groups=[]
    for name,_,_,_ in scenarios:
        for rho in (.2,.5):
            for snr in (8,14):
                for width in (2,8):
                    rows=[r for r in e1 if (r['scenario'],r['rho'],r['snr_db'],r['width'])==(name,rho,snr,width)]
                    groups.append(dict(scenario=name,rho=rho,snr_db=snr,width=width,
                        symbols=sum(r['symbols'] for r in rows),
                        errors={k:sum(r[k] for r in rows) for k in ('errors_same','errors_full_pilot','errors_full_H')},
                        pilot_improves_blocks=sum(r['errors_full_pilot']<r['errors_same'] for r in rows),
                        pilot_worsens_blocks=sum(r['errors_full_pilot']>r['errors_same'] for r in rows)))
    raw_path=HERE/'small_experiments_raw.npz';np.savez_compressed(raw_path,**raw_arrays)
    result=dict(scope=contract['scope'],source_functions=bindings,numpy_version=np.__version__,
        contract_sha256=hashlib.sha256((HERE/'small_experiments_contract.json').read_bytes()).hexdigest(),
        unique_synthetic_data_noise_blocks=32,observation_frames=128,
        fractional_estimation_performed=False,LDPC_performed=False,truth_scope=contract['E1']['truth_access'],
        E0=e0,E1_per_frame=e1,E1_summary=groups,max_CPP_matrix_relative_error=max(checks),
        seconds=time.perf_counter()-start,raw_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest())
    assert result['seconds']<120
    out=HERE/'small_experiments_results.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    # Fresh readback of saved values, no claimed full receiver audit.
    with np.load(raw_path,allow_pickle=False) as saved:
        assert len(saved.files)==len(raw_arrays)
        assert all(np.array_equal(saved[k],v) for k,v in raw_arrays.items())
    print(json.dumps({'status':'PASS','seconds':result['seconds'],'cpp_error':max(checks),'summary':groups},ensure_ascii=False))


if __name__=='__main__':
    main()
