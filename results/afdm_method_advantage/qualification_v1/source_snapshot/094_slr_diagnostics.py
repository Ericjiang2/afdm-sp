"""Ideal real-augmented affine projection of saved exact joint posteriors.

This is a diagnostic oracle, not an implementable inference update. No posterior
moment is reinterpreted as an independent prior or incoming message.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.afdm_inference_causal_20261002.remainder_diagnostics import remainder_moments

REFERENCE=ROOT/'.mission/20261002_22-12-10-afdm-inference-causal-defects/execution/oracle/comparison_v1'
REMAINDER=ROOT/'.mission/20261002_22-12-10-afdm-inference-causal-defects/execution/remainder/v1'
BINDING=ROOT/'.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py'
CONFIG=dict(schema='ideal-affine-posterior-projection/1',case_count=48,
            take_initialization='pilot_ridge',rank_rtol=1e-12,
            residual_noise_gate=.1,cpu_budget_seconds=60,wall_budget_seconds=120,
            support_policy='retained-eigen support plus full-positive sensitivity; no jitter',
            groups=['all','pilot=0.0','pilot=0.6','separated','near_duplicate'],
            scope='one registered mechanism revision; same exposed48 oracle conditions, no fresh confirmation or deployable method')


def real_map(matrix):
    """Complex linear map in grouped real then imaginary coordinates."""
    return np.block([[matrix.real,-matrix.imag],[matrix.imag,matrix.real]])


def slr_moments(operators,pilot,words,probabilities,component_h_mean,component_h_cov,noise_variance):
    baseline=remainder_moments(operators,pilot,words,probabilities,component_h_mean,component_h_cov,noise_variance)
    u=np.asarray(operators,complex);pilot=np.asarray(pilot,complex);words=np.asarray(words,complex)
    weight=np.asarray(probabilities,float);weight=weight/weight.sum()
    hmeans=np.asarray(component_h_mean,complex);hcovs=np.asarray(component_h_cov,complex)
    p,m,n=u.shape;dim=2*p+2*n;k=len(words)
    means_z=np.concatenate([hmeans.real,hmeans.imag,words.real,words.imag],axis=1)
    means_f=[];maps=[];real_h_cov=[]
    for d,mh,ch in zip(words,hmeans,hcovs):
        b=np.einsum('pij,j->ip',u,pilot+d)
        t=real_map(b);r=.5*real_map(ch)
        means_f.append(t@np.r_[mh.real,mh.imag]);maps.append(t);real_h_cov.append(r)
    means_f=np.asarray(means_f);mean_z=weight@means_z;mean_f=weight@means_f
    zdev=means_z-mean_z;fdev=means_f-mean_f
    czz=np.einsum('k,ki,kj->ij',weight,zdev,zdev)
    cf=np.einsum('k,ki,kj->ij',weight,fdev,fdev)
    cfz=np.einsum('k,ki,kj->ij',weight,fdev,zdev)
    for w,t,r in zip(weight,maps,real_h_cov):
        czz[:2*p,:2*p]+=w*r
        cf+=w*(t@r@t.T)
        cfz[:,:2*p]+=w*(t@r)
    czz=(czz+czz.T)/2;cf=(cf+cf.T)/2
    values,vectors=np.linalg.eigh(czz)
    largest=float(max(values.max(),0.))
    tolerance=64*np.finfo(float).eps*dim*np.linalg.norm(czz,2)
    if values.min() < -tolerance:raise ValueError('joint covariance is not PSD')
    retained=values>CONFIG['rank_rtol']*largest
    positive=values>0
    discarded=positive&~retained

    def fit(mask):
        v=vectors[:,mask];e=values[mask]
        a=(cfz@v/e)@v.T if len(e) else np.zeros((2*m,dim))
        intercept=mean_f-a@mean_z
        second=np.zeros((2*m,2*m));rmean=np.zeros(2*m)
        for w,t,r,mz,mf in zip(weight,maps,real_h_cov,means_z,means_f):
            rm=mf-a@mz-intercept
            slope=t-a[:,:2*p]
            second+=w*(slope@r@slope.T+np.outer(rm,rm));rmean+=w*rm
        residual_cov=second-np.outer(rmean,rmean)
        formula=cf-a@cfz.T
        orth=cfz-a@czz
        return dict(A=a,intercept=intercept,cov=(residual_cov+residual_cov.T)/2,
                    energy=float(np.trace(second)),mean=rmean,formula=formula,orth=orth)

    chosen=fit(retained)
    full=chosen if np.array_equal(retained,positive) else fit(positive)
    predicted_drop=float(np.sum(np.sum((cfz@vectors[:,discarded])**2,axis=0)/values[discarded])) if discarded.any() else 0.
    energy=chosen['energy'];noise_energy=m*float(noise_variance)
    residual_min=float(np.linalg.eigvalsh(chosen['cov']).min())
    cov_tol=1e-10*max(1.,np.linalg.norm(cf))
    if residual_min < -cov_tol:raise AssertionError('direct affine residual covariance is non-PSD')
    orth_retained=float(np.linalg.norm(chosen['orth']@vectors[:,retained]))
    if orth_retained > 1e-9*max(1.,np.linalg.norm(cfz)):
        raise AssertionError('affine residual not orthogonal on retained support')
    b=baseline['metrics']
    centered_tangent=b['t_energy']-b['t_mean_energy']
    no_truncation=not discarded.any()
    metrics=dict(residual_energy=energy,residual_noise_ratio=energy/noise_energy,
                 screen_pass=bool(energy<=CONFIG['residual_noise_gate']*noise_energy),
                 signal_variance_energy=float(np.trace(cf)),noise_energy=noise_energy,
                 tangent_uncentered_energy=b['t_energy'],tangent_centered_energy=centered_tangent,
                 reduction_vs_tangent=b['t_energy']-energy,
                 reduction_vs_centered_tangent=centered_tangent-energy,
                 retained_rank=int(retained.sum()),positive_rank=int(positive.sum()),joint_dimension=dim,
                 eigenvalue_min=float(values.min()),eigenvalue_max=largest,
                 retained_min_eigenvalue=float(values[retained].min()) if retained.any() else None,
                 discarded_positive_modes=int(discarded.sum()),discarded_positive_mass=float(values[discarded].sum()),
                 nonpositive_roundoff_mass=float(abs(values[values<0]).sum()),
                 discarded_predicted_reduction=predicted_drop,
                 full_positive_residual_energy=full['energy'],
                 full_positive_energy_sensitivity=abs(full['energy']-energy),
                 full_positive_A_norm=float(np.linalg.norm(full['A'])),
                 orthogonality_full_fro=float(np.linalg.norm(chosen['orth'])),
                 orthogonality_retained_fro=orth_retained,
                 residual_formula_error=float(np.linalg.norm(chosen['cov']-chosen['formula'])),
                 residual_cov_min_eigenvalue=residual_min,residual_mean_norm=float(np.linalg.norm(chosen['mean'])),
                 lower_bound_status='all_positive_support_retained' if no_truncation else 'rank_ambiguous_no_all_affine_certificate')
    arrays=dict(mean_z=mean_z,mean_f=mean_f,Czz=czz,Cfz=cfz,Cf=cf,
                eigenvalues=values,eigenvectors=vectors,retained_mask=retained,
                A=chosen['A'],intercept=chosen['intercept'],residual_cov=chosen['cov'],
                residual_cross_cov=chosen['orth'],full_positive_A=full['A'],
                full_positive_residual_cov=full['cov'])
    return dict(metrics=metrics,arrays=arrays)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def registration():
    sources=[Path(__file__),Path(__file__).with_name('remainder_diagnostics.py'),ROOT/'tests/test_slr_diagnostics.py',BINDING]
    inputs=[REFERENCE/'registration.json',REFERENCE/'results.json',REMAINDER/'registration.json',REMAINDER/'results.json']
    return dict(config=CONFIG,sources={str(p.relative_to(ROOT)):sha(p) for p in sources},
                inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs})


def write_json(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['register','run'])
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();folder=args.output
    if args.action=='register':
        folder.mkdir(parents=True,exist_ok=True);write_json(folder/'registration.json',registration())
        print('SLR support policy, residual gate and48-case cohort registered before computation');return
    frozen=json.loads((folder/'registration.json').read_text())
    if frozen!=registration():raise RuntimeError('SLR registration differs from current source/input')
    old=json.loads((REFERENCE/'results.json').read_text())
    records=[r for r in old['records'] if r['initialization']==CONFIG['take_initialization']]
    if len(records)!=48 or len({r['case'] for r in records})!=48:raise ValueError('incomplete48-case oracle cohort')
    bind=runpy.run_path(str(BINDING))['blas_binding'];binding=bind();cpu=time.process_time();wall=time.perf_counter()
    rawdir=folder/'raw';rawdir.mkdir(exist_ok=False);results=[]
    with (folder/'attempts.jsonl').open('x') as ledger:
        for row in records:
            if time.process_time()-cpu>60 or time.perf_counter()-wall>120:raise TimeoutError('SLR diagnostic exceeded budget')
            source=REFERENCE/'raw'/row['raw']
            if sha(source)!=row['raw_sha256']:raise ValueError('oracle raw source hash mismatch')
            ledger.write(json.dumps(dict(case=row['case'],event='started'))+'\n');ledger.flush()
            with np.load(source,allow_pickle=False) as d:
                out=slr_moments(d['operators'],d['pilot'],d['words'],d['exact_probabilities'],d['component_h_mean'],d['component_h_cov'],row['sigma2'])
            filename=f"case_{row['case']:03d}.npz";np.savez(rawdir/filename,**out['arrays'])
            results.append(dict(case=row['case'],n=row['n'],geometry=row['geometry'],pilot_amplitude=row['pilot_amplitude'],
                                sigma2=row['sigma2'],seed=row['seed'],metrics=out['metrics'],raw=filename,raw_sha256=sha(rawdir/filename),
                                input_raw=str(source.relative_to(ROOT)),input_raw_sha256=row['raw_sha256']))
            ledger.write(json.dumps(dict(case=row['case'],event='finished'))+'\n');ledger.flush()
    if bind()!=binding or frozen!=registration():raise RuntimeError('binding or registered source/input drift')
    summary={}
    for group in CONFIG['groups']:
        rows=[r for r in results if group=='all' or group==f"pilot={r['pilot_amplitude']}" or group==r['geometry']]
        keys=['residual_noise_ratio','residual_energy','tangent_uncentered_energy','tangent_centered_energy',
              'reduction_vs_tangent','reduction_vs_centered_tangent','discarded_positive_mass','full_positive_energy_sensitivity']
        summary[group]=dict(cases=len(rows),passed=sum(r['metrics']['screen_pass'] for r in rows),
                            all_positive_support_retained=sum(r['metrics']['discarded_positive_modes']==0 for r in rows),
                            means={k:float(np.mean([r['metrics'][k] for r in rows])) for k in keys},
                            residual_noise_range=[min(r['metrics']['residual_noise_ratio'] for r in rows),max(r['metrics']['residual_noise_ratio'] for r in rows)])
    result=dict(status='completed',registration=frozen,registration_sha256=sha(folder/'registration.json'),binding=binding,
                records=results,summary=summary,case_count=48,independent_exogenous_clusters=6,oracle_calls=0,
                scalar_joint_calls=0,receiver_calls=0,cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
    write_json(folder/'results.json',result)
    print(json.dumps({k:result[k] for k in ['status','case_count','cpu_seconds','wall_seconds']}))


if __name__=='__main__':main()
