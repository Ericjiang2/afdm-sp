#!/usr/bin/env python3
"""Saved-output qualification and paired frame-cluster screening; no receiver imports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent


def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


trajectory=module('__gram_cohort_trajectory','trajectory_analysis.py')
reference=module('__gram_cohort_reference','aggregate_restart.py')
key,row_sha=reference.base.key,reference.row_sha
V=('L-diag','L-cov');NATIVE=('fixed','point','joint');MODES=NATIVE+('full','diag')
ARMS=tuple(f'{v}/{m}' for v in V for m in MODES)
SEED,N_BOOT=20261026,10000
FLOATS=('extrinsic_bit_logloss','nmse_final','data_mse_final','symbol_variance_final')
PRIMARY=tuple((f'{v}/full',f'{v}/diag') for v in V)+tuple((f'{v}/full','L-cov/joint') for v in V)
CONTRASTS=PRIMARY+tuple((f'{v}/full',f'{v}/{m}') for v in V for m in NATIVE
                      if (f'{v}/full',f'{v}/{m}') not in PRIMARY)


def native_score(saved):
    last=saved['trajectory'][-1]
    return {k:saved[k] for k in ('decoded_sha256','info_errors','fer','ldpc_iters','extrinsic_bit_logloss')}|dict(
        nmse_final=last['channel_nmse'],data_mse_final=last['data_mse'],symbol_variance_final=last['symbol_variance'])


def validate(rows,three,old):
    keys=[key(r) for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=set(three) or set(keys)!=set(old):
        raise ValueError('missing/duplicate/extra cohort keys')
    for r in rows:
        k=key(r);saved,prior=three[k],old[k]
        if (r.get('status')!='ok' or r.get('receiver_calls')!=10 or r.get('decoder_calls')!=10
                or r['three_row_sha256']!=row_sha(saved) or r['run2_row_sha256']!=row_sha(prior)
                or r['input_sha256']!=prior['input_sha256'] or set(r['inputs'])!=set(V) or set(r['arms'])!=set(V)):
            raise ValueError('failed row/call count/reference binding')
        for v in V:
            inputs=saved['three_mode'][v]
            expected={name:inputs[name] for name in ('support','h0','prior_sha256')}
            if (r['inputs'][v]!=expected or expected['prior_sha256']!=prior['input_sha256']['prior']
                    or set(r['arms'][v])!=set(MODES)):
                raise ValueError('saved input/prior/arm drift')
            for m,d in r['arms'][v].items():
                block=m in ('full','diag');p=len(expected['h0'])
                gains=np.asarray(d['final_gains'],float)
                if (type(d['info_errors']) is not int or d['info_errors']<0 or d['fer']!=int(d['info_errors']>0)
                        or type(d['ldpc_iters']) is not int or not 1<=d['ldpc_iters']<=50
                        or gains.shape!=(p,2) or not np.isfinite(gains).all()
                        or any(not np.isfinite(d[f]) or d[f]<0 for f in FLOATS+('detect_seconds','decode_seconds'))
                        or d['fft_count']!=(61 if block else 41)
                        or d['gain_solve_calls']!=(20 if block else 0)
                        or d['covariance_solve_calls']!=(20 if block else 0)
                        or d['gamma_fft_count']!=(20 if block else 0)
                        or d['native_symbol_fft_count']!=41 or d['recorded_states']!=20):
                    raise ValueError('invalid score/final gains/compute counters')
                trace=d['trace']
                if (len(trace)!=20 or [s['iteration'] for s in trace]!=list(range(20))
                        or any(not all(np.isfinite(x) for x in s.values()) for s in trace)
                        or any(s['fft_count']!=(3 if block else 2) for s in trace)
                        or any(s['gain_variance']<0 or (m!='joint' and s['gain_variance']!=0) for s in trace)):
                    raise ValueError('incomplete/nonfinite/non-point trace')
                diagnostics=d['block_diagnostics']
                if (len(diagnostics)!=(20 if block else 0) or any(
                        item['iteration']!=i or item['gamma_fft_count']!=1
                        or not all(np.isfinite(x) for x in item.values())
                        or item['normal_relative_residual']>1e-10 or item['covariance_relative_residual']>1e-10
                        or item['seconds']<0 or item['solve_seconds']<0 or item['alpha']<=0
                        for i,item in enumerate(diagnostics))):
                    raise ValueError('invalid block diagnostic coverage/residual/timing')
                if m=='fixed' and not np.array_equal(gains,np.asarray(expected['h0'])):
                    raise ValueError('fixed gains changed')
                if m in NATIVE:
                    if not np.allclose(gains,np.asarray(inputs['modes'][m]['trajectory'][-1]['h']),rtol=1e-10,atol=1e-12):
                        raise ValueError('native final gains drift')
                    for field,value in native_score(inputs['modes'][m]).items():
                        equal=(d[field]==value if field not in FLOATS else np.isclose(d[field],value,rtol=1e-10,atol=1e-12))
                        if not equal:raise ValueError(f'native replay drift {k}/{v}/{m}/{field}')
    return rows


def arm(row,name):
    v,m=name.split('/');return row['arms'][v][m]


def timing(values):
    return dict(mean=float(np.mean(values)),median=float(np.median(values)),p90=float(np.percentile(values,90)),p95=float(np.percentile(values,95)))


def summarize(rows,n_boot=N_BOOT):
    groups={'pooled':rows}|{f'{sc}_{snr}':[r for r in rows if r['scenario']==sc and r['snr_centi_db']==snr]
                          for sc in ('U','G') for snr in (700,800)}
    output={}
    for name,selected in groups.items():
        group=dict(n=len(selected),arms={},contrasts={})
        for label in ARMS:
            records=[arm(r,label) for r in selected]
            elapsed={field:np.array([d[field] for d in records]) for field in ('detect_seconds','decode_seconds')}
            elapsed['combined_seconds']=elapsed['detect_seconds']+elapsed['decode_seconds']
            group['arms'][label]=dict(failures=sum(d['fer'] for d in records),fer=float(np.mean([d['fer'] for d in records])),
                mean_info_errors=float(np.mean([d['info_errors'] for d in records])),
                **{f'mean_{f}':float(np.mean([d[f] for d in records])) for f in FLOATS},
                timing={f:timing(values) for f,values in elapsed.items()})
        columns=[np.array([arm(r,left)['fer']-arm(r,right)['fer'] for r in selected]) for left,right in CONTRASTS]
        columns += [np.array([arm(r,left)['extrinsic_bit_logloss']-arm(r,right)['extrinsic_bit_logloss'] for r in selected]) for left,right in PRIMARY]
        effects=trajectory.paired(np.column_stack(columns),[r['frame'] for r in selected],n_boot=n_boot,seed=SEED)
        for i,(left,right) in enumerate(CONTRASTS):
            ref=group['arms'][right]['fer'];effect=effects[i]
            entry=dict(tier='primary' if (left,right) in PRIMARY else 'secondary',fer=effect,
                relative_fer_reduction=-effect['point']/ref if ref>0 else None,
                transitions={f'{x}->{y}':sum(arm(r,right)['fer']==x and arm(r,left)['fer']==y for r in selected)
                             for x in (0,1) for y in (0,1)})
            if (left,right) in PRIMARY:entry['logloss']=effects[len(CONTRASTS)+PRIMARY.index((left,right))]
            group['contrasts'][f'{left}-{right}']=entry
        output[name]=group
    return output


def load(directory,three,old,receipt):
    files=sorted(directory.glob('rows_shard*.jsonl'));configs=sorted(directory.glob('config_shard*.json'))
    if ([p.name for p in files]!=[f'rows_shard{i:03d}.jsonl' for i in range(12)]
            or [p.name for p in configs]!=[f'config_shard{i:03d}.json' for i in range(12)]):
        raise ValueError('exact12 raw/config shard coverage required')
    identities=[{k:json.loads(p.read_text())['_config'][k] for k in ('reference','source_md5','frozen_actual_paths','own_md5')} for p in configs]
    if any(c!=identities[0] for c in identities) or identities[0]['reference']!=receipt:
        raise ValueError('mixed source/reference/config identities')
    gate=json.loads((directory/'gate.json').read_text())
    if (gate.get('passed') is not True or {k:gate['_config'][k] for k in identities[0]}!=identities[0]):
        raise ValueError('representative gate absent/failed/source drift')
    gate_row=gate['row'];k=key(gate_row)
    if (k!=('U',300,700,9100) or not gate_row['observer_parity'] or not gate_row['old_baseline_replay']
            or gate_row['receiver_calls']+gate_row['gate_receiver_calls']>32
            or gate_row['decoder_calls']+gate_row['gate_decoder_calls']>20):
        raise ValueError('representative gate key/parity/call budget')
    validate([gate_row],{k:three[k]},{k:old[k]})
    rows=[json.loads(line) for p in files for line in p.read_text().splitlines() if line.strip()]
    validate(rows,three,old)
    return rows,{p.name:reference.file_sha(p) for p in files},identities[0],gate


def main():
    parser=argparse.ArgumentParser()
    for name in ('old-rows','three-rows','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    old,r2=reference.load_reference(args.old_rows)
    raw,t3,_=trajectory.load(args.three_rows,args.three_rows.parent/'analysis_fix/summary.json')
    three={key(r):r for r in raw};receipt=dict(three=t3,run2=r2)
    rows,hashes,identity,gate=load(args.out,three,old,receipt)
    groups=summarize(rows)
    pooled=groups['pooled']['contrasts']
    verdict=dict(C1=all(pooled[f'{v}/full-{v}/diag']['fer']['ci95'][1]<0 for v in V),
        C2=pooled['L-diag/full-L-diag/point']['fer']['ci95'][1]<0,
        C3=groups['pooled']['arms']['L-cov/full']['failures']<=2)
    report=dict(label='Informed old-cohort soft-Gram screening; pointwise intervals, no mechanism or independent confirmation',
        _argv=__import__('sys').argv[1:],bootstrap=dict(seed=SEED,resamples=N_BOOT,cluster='P1 frame'),
        n_keys=len(rows),source_identity=identity,raw_sha256=hashes,gate=gate,
        main_calls=dict(receiver=sum(r['receiver_calls'] for r in rows),decoder=sum(r['decoder_calls'] for r in rows)),
        groups=groups,frozen_forecasts=verdict)
    with (args.out/'summary.json').open('x') as f:f.write(json.dumps(report,indent=1,allow_nan=False)+'\n')
    print(f'validated {len(rows)} keys,2000 main receiver/decoder calls')


if __name__=='__main__':main()
