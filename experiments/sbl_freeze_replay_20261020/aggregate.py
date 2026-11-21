#!/usr/bin/env python3
"""Strict paired readout for the 200-key scalar-Gamma freeze replay."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

FRAMES = range(9100, 9150)
ARMS = ('fixed20','point20','P40','RF')
CONTRASTS = (('RF','point20'),('P40','point20'),('RF','P40'))
SEED, N_BOOT = 20261021, 10000


def key(r):
    return r['scenario'],r['rho_permille'],r['snr_centi_db'],r['frame']


def validate(rows, expected=None):
    expected = expected if expected is not None else {(sc,300,snr,f) for sc in ('U','G') for snr in (700,800) for f in FRAMES}
    keys = [key(r) for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=expected:
        raise ValueError(f'duplicate/missing/extra keys: rows {len(rows)} unique {len(set(keys))} missing {len(expected-set(keys))} extra {len(set(keys)-expected)}')
    for r in rows:
        if r.get('status')!='ok' or r.get('point40_prefix_match') is not True:
            raise ValueError(f'failed/prefix-mismatched row: {key(r)}')
        if set(r['baseline'])!={'fixed20','point20'} or set(r['arms'])!={'P40','RF'}:
            raise ValueError(f'arm coverage: {key(r)}')
        if r['input_sha256']['prior'] != hashlib.sha256(np.asarray(r['prior'],float).tobytes()).hexdigest():
            raise ValueError(f'prior hash: {key(r)}')
        for arm in ARMS:
            d = r['baseline'].get(arm,r['arms'].get(arm))
            if d['fer'] != int(d['info_errors']>0) or any(not np.isfinite(d[f]) for f in ('extrinsic_bit_logloss','nmse_final','data_mse_final','symbol_variance_final')):
                raise ValueError(f'nonfinite/inconsistent arm: {key(r)} {arm}')
    return rows


def load(directory):
    files=sorted(directory.glob('rows_shard*.jsonl*'))
    configs=sorted(directory.glob('config_shard*.json'))
    if len(files)!=12 or len(configs)!=12:
        raise ValueError('expected exactly 12 raw and config shards')
    identities=[]
    for path in configs:
        c=json.loads(path.read_text())['_config']
        identities.append({k:c[k] for k in ('old_raw_sha256','old_identity','frozen_md5_check','frozen_actual_paths','source_md5','own_md5')})
    if any(x!=identities[0] for x in identities):
        raise ValueError('mixed source/input identities')
    rows=[]
    for path in files:
        with (gzip.open if path.suffix=='.gz' else open)(path,'rt') as h:
            rows.extend(json.loads(line) for line in h if line.strip())
    if sum(bool(r.get('observer_parity')) for r in rows)!=1:
        raise ValueError('representative observer parity missing/duplicated')
    validate(rows)
    return rows,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},identities[0]


def paired(values,frames,n_boot=N_BOOT,seed=SEED):
    buckets={f:[] for f in frames}
    for f,v in values:
        buckets[f].append(v)
    if any(not buckets[f] for f in frames):
        raise ValueError('empty frame cluster')
    sums=np.array([sum(buckets[f]) for f in frames],float)
    counts=np.array([len(buckets[f]) for f in frames],float)
    rng=np.random.default_rng(seed)
    W=np.stack([np.bincount(rng.integers(0,len(frames),len(frames)),minlength=len(frames)) for _ in range(n_boot)])
    boot=(W@sums)/(W@counts)
    return dict(point=float(sums.sum()/counts.sum()),ci95=[float(np.percentile(boot,2.5)),float(np.percentile(boot,97.5))])


def arm(r,name):
    return r['baseline'][name] if name in r['baseline'] else r['arms'][name]


def summarize(rows):
    validate(rows)
    groups={'pooled':rows}
    for sc in ('U','G'):
        for snr in (700,800):
            groups[f'{sc}_{snr}']=[r for r in rows if r['scenario']==sc and r['snr_centi_db']==snr]
    out={}
    for name,rs in groups.items():
        g=dict(n=len(rs),arms={},contrasts={},transitions={})
        for a in ARMS:
            records=[arm(r,a) for r in rs]
            g['arms'][a]=dict(failures=sum(d['fer'] for d in records),fer=float(np.mean([d['fer'] for d in records])),
                mean_logloss=float(np.mean([d['extrinsic_bit_logloss'] for d in records])),
                mean_nmse_final=float(np.mean([d['nmse_final'] for d in records])),
                mean_data_mse_final=float(np.mean([d['data_mse_final'] for d in records])),
                mean_symbol_variance_final=float(np.mean([d['symbol_variance_final'] for d in records])))
        for left,right in CONTRASTS:
            label=f'{left}-{right}'
            g['contrasts'][label]=paired([(r['frame'],arm(r,left)['fer']-arm(r,right)['fer']) for r in rs],list(FRAMES))
            g['transitions'][f'{right}->{left}']={f'{x}->{y}':sum(arm(r,right)['fer']==x and arm(r,left)['fer']==y for r in rs)
                                                 for x in (0,1) for y in (0,1)}
        out[name]=g
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rows',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    rows,hashes,identity=load(a.rows)
    report=dict(label='exploratory SBL final-gain reset/freeze replay, 200 keys; pointwise paired frame-cluster intervals',
        n_keys=len(rows),bootstrap=dict(seed=SEED,resamples=N_BOOT,cluster='P1 frame'),
        source_identity=identity,raw_sha256=hashes,groups=summarize(rows))
    a.out.write_text(json.dumps(report,indent=1,allow_nan=False)+'\n')
    print(f'validated {len(rows)} keys; summary: {a.out}')

if __name__=='__main__':
    main()
