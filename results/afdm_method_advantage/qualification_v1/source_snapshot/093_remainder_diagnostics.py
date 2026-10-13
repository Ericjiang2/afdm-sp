"""Exact bilinear-remainder moments from a finite proper-Gaussian mixture.

Consumes saved oracle components; does not rerun any receiver or data generator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / '.mission/20261002_22-12-10-afdm-inference-causal-defects/execution/oracle/comparison_v1'
BINDING = ROOT / '.mission/20261001_23-33-35-afdm-innovation-space/controls/thread_binding.py'
CONFIG = dict(schema='exact-posterior-remainder/1', case_count=48,
              take_initialization='pilot_ridge', independent_exogenous_clusters=6,
              criterion_t_energy_noise_ratio=.1, criterion_abs_cross_noise_ratio=.1,
              criterion_scope='necessary engineering admission screen, not mathematical sufficiency for inference accuracy',
              cpu_budget_seconds=60, wall_budget_seconds=120,
              groups=['all', 'pilot=0.0', 'pilot=0.6', 'separated', 'near_duplicate'],
              scope='saved exact small-model posterior diagnostic; no new receiver/oracle/generator calls')


def _finite(value, name, ndim, real=False):
    raw = np.asarray(value)
    if real and np.iscomplexobj(raw) and np.any(raw.imag != 0):
        raise ValueError(f'{name} must be real')
    a = np.asarray(raw.real if real else raw, dtype=float if real else complex)
    if a.ndim != ndim or not np.isfinite(a).all():
        raise ValueError(f'invalid {name}')
    return a


def _ratio(numerator, denominator):
    return None if denominator == 0 else float(numerator/denominator)


def remainder_moments(operators, pilot, words, probabilities, component_h_mean,
                      component_h_cov, noise_variance):
    """Return metrics and arrays for expansion centered at posterior h/d means.

    h|d is proper Gaussian; d is the supplied finite distribution. No posterior
    independence is assumed. The independent-product expression is returned only
    as a diagnostic using the same marginal covariances.
    """
    u = _finite(operators, 'operators', 3)
    pilot = _finite(pilot, 'pilot', 1)
    words = _finite(words, 'words', 2)
    weight = _finite(probabilities, 'probabilities', 1, True)
    conditional_mean = _finite(component_h_mean, 'component_h_mean', 2)
    conditional_cov = _finite(component_h_cov, 'component_h_cov', 3)
    p, m, n = u.shape
    k = len(words)
    if (min(p,m,n,k) < 1 or pilot.shape != (n,) or words.shape != (k,n)
            or weight.shape != (k,) or conditional_mean.shape != (k,p)
            or conditional_cov.shape != (k,p,p)):
        raise ValueError('incompatible mixture/operator dimensions')
    if np.any(weight < 0) or not np.isclose(weight.sum(), 1., rtol=1e-13, atol=1e-15):
        raise ValueError('mixture weights must be nonnegative and normalized')
    weight = weight/weight.sum()
    if not np.isscalar(noise_variance) or np.iscomplexobj(noise_variance) or not np.isfinite(noise_variance) or noise_variance <= 0:
        raise ValueError('noise variance must be positive finite real')
    for c in conditional_cov:
        tolerance = 64*np.finfo(float).eps*p*np.linalg.norm(c)
        if np.linalg.norm(c-c.conj().T)>tolerance or np.linalg.eigvalsh((c+c.conj().T)/2).min() < -tolerance:
            raise ValueError('conditional covariance must be Hermitian PSD')
    mh, md = weight@conditional_mean, weight@words
    hg, dg = conditional_mean-mh, words-md
    ch = np.einsum('k,kij->ij', weight, conditional_cov)+np.einsum('k,ki,kj->ij',weight,hg,hg.conj())
    cd = np.einsum('k,ki,kj->ij',weight,dg,dg.conj())
    ph = np.einsum('k,ki,kj->ij',weight,hg,hg)
    pd = np.einsum('k,ki,kj->ij',weight,dg,dg)
    b0 = np.einsum('pij,j->ip', u, pilot+md)
    h0 = np.einsum('p,pij->ij', mh, u)
    t_mean = np.zeros(m,complex)
    linear_mean = np.zeros(m,complex)
    direct_mean = np.zeros(m,complex)
    t_second = np.zeros((m,m),complex)
    t_pseudo_second = np.zeros((m,m),complex)
    linear_energy = 0.; direct_energy = 0.; cross_complex = 0j
    component_rows = []
    for w, d, g, c in zip(weight, dg, hg, conditional_cov):
        q = np.einsum('pij,j->ip',u,d)
        tm = q@g
        lm = b0@g+h0@d
        # Independent direct route uses the unexpanded physical response B(d).
        bfull = np.einsum('pij,j->ip',u,pilot+md+d)
        fm = bfull@(g+mh)-h0@(pilot+md)
        ts = q@c@q.conj().T+np.outer(tm,tm.conj())
        le = float((np.trace(b0@c@b0.conj().T)+np.vdot(lm,lm)).real)
        de = float((np.trace(bfull@c@bfull.conj().T)+np.vdot(fm,fm)).real)
        ct = np.trace(b0.conj().T@q@c)+np.vdot(lm,tm)
        t_mean += w*tm;linear_mean += w*lm;direct_mean += w*fm
        t_second += w*ts
        t_pseudo_second += w*np.outer(tm,tm)
        linear_energy += w*le;direct_energy += w*de;cross_complex += w*ct
        component_rows.append([np.trace(ts).real,le,de,2*ct.real])
    t_energy = float(np.trace(t_second).real)
    cross = float(2*cross_complex.real)
    expanded = float(linear_energy+t_energy+cross)
    t_cov = t_second-np.outer(t_mean,t_mean.conj())
    t_pseudo = t_pseudo_second-np.outer(t_mean,t_mean)
    independent = float(sum(ch[a,b]*np.trace(u[b].conj().T@u[a]@cd)
                            for a in range(p) for b in range(p)).real)
    tolerance = 1e-10*max(1.,abs(direct_energy),abs(expanded))
    if abs(direct_energy-expanded)>tolerance or np.linalg.norm(direct_mean-t_mean)>np.sqrt(tolerance):
        raise AssertionError('exact decomposition contract failed')
    noise_energy = m*float(noise_variance)
    t_pass = t_energy <= CONFIG['criterion_t_energy_noise_ratio']*noise_energy
    cross_pass = abs(cross) <= CONFIG['criterion_abs_cross_noise_ratio']*noise_energy
    mean_energy = float(np.vdot(t_mean,t_mean).real)
    metrics = dict(t_energy=t_energy, linear_energy=float(linear_energy), cross=cross,
                   cross_imaginary=float(cross_complex.imag), expanded_energy=expanded,
                   direct_energy=float(direct_energy), decomposition_abs_error=abs(direct_energy-expanded),
                   t_mean_energy=mean_energy, t_cov_trace=float(np.trace(t_cov).real),
                   direct_centered_variance=float(direct_energy-np.vdot(direct_mean,direct_mean).real),
                   independent_energy=independent, independent_minus_exact=independent-t_energy,
                   noise_energy=noise_energy, t_noise_ratio=t_energy/noise_energy,
                   abs_cross_noise_ratio=abs(cross)/noise_energy,
                   t_to_linear_ratio=_ratio(t_energy,linear_energy),
                   linear_mean_norm=float(np.linalg.norm(linear_mean)),
                   h_mean_norm=float(np.linalg.norm(mh)),d_mean_norm=float(np.linalg.norm(md)),
                   h_pseudo_fro=float(np.linalg.norm(ph)),d_pseudo_fro=float(np.linalg.norm(pd)),
                   t_pseudo_fro=float(np.linalg.norm(t_pseudo)),
                   t_improper_ratio=_ratio(np.linalg.norm(t_pseudo),np.linalg.norm(t_cov)),
                   t_screen_pass=bool(t_pass),cross_screen_pass=bool(cross_pass),
                   local_screen_pass=bool(t_pass and cross_pass))
    arrays = dict(t_mean=t_mean,t_cov=t_cov,t_pseudo_cov=t_pseudo,linear_mean=linear_mean,
                  direct_mean=direct_mean,h_mean=mh,d_mean=md,h_cov=ch,d_cov=cd,
                  h_pseudo_cov=ph,d_pseudo_cov=pd,component_energy_table=np.array(component_rows))
    return dict(metrics=metrics,arrays=arrays)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registration():
    source_paths = [Path(__file__),ROOT/'tests/test_remainder_diagnostics.py',BINDING]
    input_paths = [REFERENCE/'registration.json',REFERENCE/'results.json',REFERENCE/'recount.json']
    return dict(config=CONFIG,sources={str(p.relative_to(ROOT)):_sha(p) for p in source_paths},
                inputs={str(p.relative_to(ROOT)):_sha(p) for p in input_paths})


def write_json(path, value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['register','run'])
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    folder=args.output
    if args.action=='register':
        folder.mkdir(parents=True,exist_ok=True)
        write_json(folder/'registration.json',registration())
        print('registered remainder screen and existing oracle inputs; no computation')
        return
    frozen=json.loads((folder/'registration.json').read_text())
    if frozen!=registration():raise RuntimeError('registered source/input/config changed')
    reference=json.loads((REFERENCE/'results.json').read_text())
    records=[r for r in reference['records'] if r['initialization']==CONFIG['take_initialization']]
    if len(records)!=48 or len({r['case'] for r in records})!=48:
        raise ValueError('reference is not the full48-case oracle cohort')
    bind=runpy.run_path(str(BINDING))['blas_binding'];binding=bind()
    cpu_start,wall_start=time.process_time(),time.perf_counter()
    rawdir=folder/'raw';rawdir.mkdir(exist_ok=False)
    results=[]
    with (folder/'attempts.jsonl').open('x') as ledger:
        for record in records:
            if time.process_time()-cpu_start>60 or time.perf_counter()-wall_start>120:
                raise TimeoutError('registered remainder diagnostic budget exceeded')
            source=REFERENCE/'raw'/record['raw']
            if _sha(source)!=record['raw_sha256']:raise ValueError('oracle raw hash mismatch')
            ledger.write(json.dumps(dict(case=record['case'],event='started'))+'\n');ledger.flush()
            with np.load(source,allow_pickle=False) as data:
                out=remainder_moments(data['operators'],data['pilot'],data['words'],data['exact_probabilities'],
                                      data['component_h_mean'],data['component_h_cov'],record['sigma2'])
            filename=f"case_{record['case']:03d}.npz";np.savez(rawdir/filename,**out['arrays'])
            results.append(dict(case=record['case'],n=record['n'],geometry=record['geometry'],
                                pilot_amplitude=record['pilot_amplitude'],sigma2=record['sigma2'],seed=record['seed'],
                                metrics=out['metrics'],raw=filename,raw_sha256=_sha(rawdir/filename),
                                input_raw=str(source.relative_to(ROOT)),input_raw_sha256=record['raw_sha256']))
            ledger.write(json.dumps(dict(case=record['case'],event='finished'))+'\n');ledger.flush()
    if bind()!=binding or registration()!=frozen:raise RuntimeError('binding/source/input drift')
    summary={}
    for group in CONFIG['groups']:
        subset=[r for r in results if group=='all' or group==f"pilot={r['pilot_amplitude']}" or group==r['geometry']]
        selected=['t_noise_ratio','abs_cross_noise_ratio','t_energy','linear_energy','cross',
                  'independent_energy','independent_minus_exact','t_mean_energy','t_improper_ratio','decomposition_abs_error']
        summary[group]=dict(cases=len(subset),passed=sum(r['metrics']['local_screen_pass'] for r in subset),
                            t_passed=sum(r['metrics']['t_screen_pass'] for r in subset),
                            cross_passed=sum(r['metrics']['cross_screen_pass'] for r in subset),
                            means={k:float(np.mean([r['metrics'][k] for r in subset if r['metrics'][k] is not None])) for k in selected},
                            t_noise_ratio_range=[min(r['metrics']['t_noise_ratio'] for r in subset),max(r['metrics']['t_noise_ratio'] for r in subset)])
    result=dict(status='completed',registration=frozen,registration_sha256=_sha(folder/'registration.json'),
                binding=binding,records=results,summary=summary,case_count=48,oracle_calls=0,scalar_joint_calls=0,
                cpu_seconds=time.process_time()-cpu_start,wall_seconds=time.perf_counter()-wall_start)
    write_json(folder/'results.json',result)
    print(json.dumps({k:result[k] for k in ['status','case_count','cpu_seconds','wall_seconds']}))


if __name__=='__main__':main()
