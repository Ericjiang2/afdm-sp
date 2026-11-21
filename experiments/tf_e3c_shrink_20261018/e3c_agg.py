#!/usr/bin/env python
"""Strict complete-pair aggregation; RNG-domain/frame bootstrap, seed 20261018."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'tf_covariance_audit_20261018'))
from sampling import bootstrap_means,linear_summary,ratio_summary
import e3c_lib as lib
ARMS=('diag-off','cov-off','cov+ridge','diag2','cov-oracle','diag-oracle')


def classify(fraction):
    if not fraction['evaluable']:
        return 'not-evaluable'
    if fraction['ci_lo'] >= .8:
        return 'recovered'
    if fraction['ci_hi'] <= .2:
        return 'small'
    return 'unresolved'


def read_rows(directory, expected_keys, smoke=False, gate=False):
    directory=Path(directory)
    want=set(expected_keys)
    rows={}
    source_identity=None
    for path in sorted(directory.glob('rows_shard*.jsonl*')):
        op=gzip.open if path.suffix=='.gz' else open
        cfg=directory/path.name.replace('rows_','config_').split('.jsonl')[0].__add__('.json')
        if not cfg.exists():
            raise RuntimeError(f'missing config for {path}')
        envelope=json.loads(cfg.read_text())
        if not isinstance(envelope.get('_argv'),list) or not envelope['_argv']:
            raise RuntimeError('missing full argv')
        config=envelope['_config']
        identity=config['sources_sha256']
        if source_identity is None:
            source_identity=identity
        if identity != source_identity:
            raise RuntimeError('mixed source snapshots')
        sha=hashlib.sha256(cfg.read_bytes()).hexdigest()
        declared={tuple(k) for k in config['keys']}
        observed=set()
        with op(path,'rt') as handle:
            for line in handle:
                r=json.loads(line)
                key=lib.key_of(r)
                if key in rows or key not in want or key not in declared:
                    raise RuntimeError(f'duplicate/unexpected key {key}')
                if r.get('status')!='ok' or r.get('config_sha256')!=sha:
                    raise RuntimeError(f'failed row or config identity mismatch {key}')
                if bool(r.get('smoke',False)) != smoke:
                    raise RuntimeError('smoke evidence mixed with main evidence')
                if set(r['variants'])!=set(ARMS):
                    raise RuntimeError(f'incomplete arms {key}')
                if not smoke and not r['baseline_check']['all']:
                    raise RuntimeError('baseline replay failed')
                if gate and not r.get('g3',{}).get('pass_'):
                    raise RuntimeError('G3 failed')
                for a,x in r['variants'].items():
                    if x['fer'] not in (0,1) or x['fer'] != int(x['info_errors']>0) or not np.isfinite(x['nmse']) or x['nmse']<0:
                        raise RuntimeError(f'invalid FER/NMSE {key} {a}')
                    if not x['refine']['monotone'] or not x['refine']['value_recheck_equal']:
                        raise RuntimeError('refinement correctness failure')
                    if not x['refine']['in_bounds'] or not x['refine']['in_window'] or x['refine']['max_evals_coord']>16:
                        raise RuntimeError('refinement search contract failure')
                    if x['gamma_check']['relative_error']>1e-12:
                        raise RuntimeError('Gamma consistency failure')
                    if a in ('diag-off','cov-off'):
                        if set(x.get('stages',{}))!={'sbl','fixed_refit'}:
                            raise RuntimeError('missing fixed-geometry stages')
                        for stage,stage_row in x['stages'].items():
                            errors=stage_row['info_errors']
                            if not isinstance(errors,int) or errors<0 or stage_row['fer'] not in (0,1) or stage_row['fer']!=int(errors>0):
                                raise RuntimeError(f'invalid stage FER/info_errors: {key} {a} {stage}')
                            if not np.isfinite(stage_row['nmse']) or stage_row['nmse']<0:
                                raise RuntimeError(f'invalid stage NMSE: {key} {a} {stage}')
                            recomputed=stage_row.get('recomputed')
                            if recomputed is not True and recomputed is not False:
                                raise RuntimeError('stage recomputed flag required')
                            if not isinstance(stage_row.get('provenance'),str) or not stage_row['provenance']:
                                raise RuntimeError('stage provenance required')
                            if stage=='fixed_refit' and recomputed is not True:
                                raise RuntimeError('fixed refit must be recomputed')
                            if recomputed is False and (stage!='sbl' or stage_row['provenance']!='frozen E3 saved row' or smoke or gate):
                                raise RuntimeError('invalid reused-stage provenance')

                observed.add(key)
                rows[key]=r
        if observed!=declared:
            raise RuntimeError(f'incomplete shard {path}')
    if set(rows)!=want:
        raise RuntimeError(f'incomplete key set: {len(rows)}/{len(want)}')
    ordered=[rows[k] for k in sorted(want)]
    # Independent randomness is frame/domain, jointly across U/G/rho/SNR.
    shared={}
    for r in ordered:
        cluster=(r['rng_entropy'],r['rng_domain'],r['frame'])
        fingerprint=(r['pairing']['noise_sha256'],r['pairing']['physical_gains_sha256'],r['pairing']['coded_sha256'],r['pairing']['info_sha256'])
        if cluster in shared and shared[cluster]!=fingerprint:
            raise RuntimeError(f'exogenous cluster hash mismatch {cluster}')
        shared[cluster]=fingerprint
    return ordered,source_identity


def summarize(rows,n_boot=20000,seed=20261018):
    values={a:np.array([r['variants'][a]['fer'] for r in rows],float) for a in ARMS}
    for a in ARMS:
        values[a+'/nmse']=np.array([r['variants'][a]['nmse'] for r in rows])
    for a in ('diag-off','cov-off'):
        for stage in ('sbl','fixed_refit'):
            for metric in ('fer','nmse'):
                values[a+'/'+stage+'/'+metric]=np.array([r['variants'][a]['stages'][stage][metric] for r in rows],float)
    cluster=[f"{r['rng_entropy']}:{r['rng_domain']}:{r['frame']}" for r in rows]
    draws,n_clusters=bootstrap_means(values,cluster,n_boot=n_boot,seed=seed)
    point={k:float(np.mean(v)) for k,v in values.items()}
    metrics={k:linear_summary(point,draws,{k:1}) for k in values}
    denominator={'cov-off':1,'diag-off':-1}
    fractions={}
    for name,target in (('Sh','cov+ridge'),('Or','cov-oracle')):
        fractions[name]=ratio_summary(point,draws,{'cov-off':1,target:-1},denominator)
        fractions[name]['classification']=classify(fractions[name])
    comparisons={}
    for left,right in (('cov+ridge','diag-off'),('cov-oracle','diag-oracle'),('cov+ridge','diag2'),('cov-off','diag-off')):
        comparisons[left+' - '+right]=linear_summary(point,draws,{left:1,right:-1})
    fixed={}
    for a in ('diag-off','cov-off'):
        fixed[a]={}
        for metric in ('fer','nmse'):
            continuous=a if metric=='fer' else a+'/nmse'
            fixed[a][metric]=dict(refit_minus_sbl=linear_summary(point,draws,{a+'/fixed_refit/'+metric:1,a+'/sbl/'+metric:-1}),
                                  continuous_minus_refit=linear_summary(point,draws,{continuous:1,a+'/fixed_refit/'+metric:-1}))
    reliability=[]
    for i in range(5):
        n=sum(r['calibration']['bins'][i]['n'] for r in rows)
        sv=sum(r['calibration']['bins'][i]['sum_v'] for r in rows)
        se=sum(r['calibration']['bins'][i]['sum_err'] for r in rows)
        reliability.append(dict(n=n,sum_v=sv,sum_err=se,mean_v=sv/n if n else None,mean_error_energy=se/n if n else None))
    sv=sum(r['calibration']['sum_v'] for r in rows)
    se=sum(r['calibration']['sum_err'] for r in rows)
    nerr=sum(r['calibration']['n_sym_err'] for r in rows)
    calibration=dict(sum_v=sv,sum_err=se,kappa=se/sv if sv else None,bins=reliability,
                     confident_error_fraction=sum(r['calibration']['n_conf_sym_err'] for r in rows)/nerr if nerr else None)
    census={a:dict(n_atoms=sum(r['variants'][a]['n_atoms'] for r in rows),n_pair=sum(r['variants'][a]['n_pair'] for r in rows),
                   nonconverged_sbl=sum(not r['variants'][a]['sbl']['converged'] for r in rows),
                   same_delay_dn=[p['dnu'] for r in rows for p in r['variants'][a]['pairs']]) for a in ARMS}
    return dict(status='draft',n_keys=len(rows),n_clusters=n_clusters,n_boot=n_boot,seed=seed,
                cluster='RNG entropy/domain/frame, joint U/G and SNR',metrics=metrics,fractions=fractions,comparisons=comparisons,
                fixed_geometry=fixed,calibration=calibration,census=census,
                oracle_noninferior_1pp=bool(comparisons['cov-oracle - diag-oracle']['ci_hi']<=.01),
                interpretation='Intervention recovery descriptions; realized-error-energy profile sensitivity only; no causal certification')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    rows,sources=read_rows(a.out,lib.main_keys())
    result=summarize(rows)
    result['source_sha256']=sources
    result['cells']={f'{sc}/{snr}':summarize([r for r in rows if r['scenario']==sc and r['snr_centi_db']==snr])
                     for sc in lib.SCENARIOS for snr in lib.SNRS}
    path=a.out/'summary.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(result,indent=1,allow_nan=False)+'\n')
    print(json.dumps(dict(status='draft',keys=result['n_keys'],clusters=result['n_clusters'],summary=str(path))))


if __name__=='__main__':
    main()
