#!/usr/bin/env python3
"""Strict Gamma-only readout against immutable full scores; no receiver calls."""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__gamma_producer', HERE/'gamma_ablation.py')
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
a = g.oldagg
SEED, N_BOOT = 20261027, 10000
IDENTITY = ('schema', 'reference', 'full_reference', 'source_md5', 'frozen_actual_paths', 'own_md5', 'normal_system', 'timing_scope')


def validate(rows, three, old, full, gate=False):
    expected = set(three) if not gate else {k for k in three if k[3] == 9100}
    keys = [a.key(r) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != expected:
        raise ValueError('missing/duplicate/extra Gamma-only keys')
    for r in rows:
        k = a.key(r); baseline = full[k]
        calls = 4 if gate else 2
        if (r.get('schema') != g.SCHEMA or r.get('status') != 'ok'
                or r.get('receiver_calls') != calls or r.get('decoder_calls') != calls
                or r.get('observer_receiver_calls') != (2 if gate else 0)
                or r.get('observer_parity') is not gate or r.get('full_replay') is not gate
                or r.get('full_row_sha256') != a.row_sha(baseline)
                or any(r.get(f) != baseline[f] for f in ('three_row_sha256', 'run2_row_sha256', 'input_sha256', 'inputs', 'observation_sha256'))
                or set(r.get('arms', {})) != set(g.VARIANTS)):
            raise ValueError('failed row/calls/source/input binding')
        attempts = r['attempts']
        required = {(v, m, observed) for v in g.VARIANTS
                    for m, observed in ((('full', False), ('gamma_diag', False), ('gamma_diag', True)) if gate else (('gamma_diag', False),))}
        actual = [(t['variant'], t['mode'], t.get('record_states') is False) for t in attempts]
        if (len(actual) != len(required) or set(actual) != required or any(t['status'] != 'ok' for t in attempts)
                or any(not np.isfinite(t[f]) or t[f] < 0 for t in attempts if t.get('record_states') is not False
                       for f in ('detect_seconds', 'score_seconds'))):
            raise ValueError('attempt coverage/failure retention')
        # Use the immutable ten-arm validator as a schema-validation view only:
        # replace its full score, retaining genuine old context. Never emit this view
        # or its old call counters as this experiment's rows or statistics.
        view = copy.deepcopy(baseline)
        for v in g.VARIANTS:
            if set(r['arms'][v]) != ({'full', 'gamma_diag'} if gate else {'gamma_diag'}):
                raise ValueError('unexpected scientific arm')
            view['arms'][v]['full'] = r['arms'][v]['gamma_diag']
            if gate: g.validate_full(r['arms'][v]['full'], baseline['arms'][v]['full'])
        a.validate([view], {k:three[k]}, {k:old[k]})
        if gate:
            for v in g.VARIANTS: view['arms'][v]['full'] = r['arms'][v]['full']
            a.validate([view], {k:three[k]}, {k:old[k]})
    return rows


def load(directory, three, old, full, receipt, full_receipt):
    paths = [directory/f'rows_shard{i:03d}.jsonl' for i in range(12)]
    configs = [directory/f'config_shard{i:03d}.json' for i in range(12)]
    if (set(directory.glob('rows_shard*.jsonl')) != set(paths)
            or set(directory.glob('config_shard*.json')) != set(configs)):
        raise ValueError('exact12 raw/config shards required')
    values = [json.loads(p.read_text()) for p in configs]
    identities = [{k:c['_config'][k] for k in IDENTITY} for c in values]
    identity = identities[0]
    if (any(x != identity for x in identities) or identity['schema'] != g.SCHEMA
            or identity['reference'] != receipt or identity['full_reference'] != full_receipt
            or identity['source_md5'] != full_receipt['identity']['source_md5']
            or identity['frozen_actual_paths'] != full_receipt['identity']['frozen_actual_paths']):
        raise ValueError('mixed source/reference identity')
    gate_config = json.loads((directory/'config_gate.json').read_text())
    if {k:gate_config['_config'][k] for k in IDENTITY} != identity or gate_config['_config']['shard'] != 0:
        raise ValueError('gate source/reference drift')
    gate = [json.loads(line) for line in (directory/'gate.jsonl').read_text().splitlines() if line.strip()]
    validate(gate, three, old, full, gate=True)
    rows = []
    for shard, (path, config) in enumerate(zip(paths, values)):
        if config['_config']['shard'] != shard or not 0 < config['_config']['deadline_seconds'] <= 700 or not isinstance(config['_argv'], list):
            raise ValueError('shard config ownership/deadline/argv')
        selected = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if any((r['frame']-9100)%12 != shard for r in selected): raise ValueError('shard key ownership')
        rows.extend(selected)
    validate(rows, three, old, full)
    hashes = {p.name:a.reference.file_sha(p) for p in paths+configs+[directory/'gate.jsonl', directory/'config_gate.json']}
    return rows, hashes, identity, gate


def summarize(rows, full, n_boot=N_BOOT):
    groups = {'pooled':rows}|{f'{sc}_{snr}':[r for r in rows if r['scenario']==sc and r['snr_centi_db']==snr]
                              for sc in ('U','G') for snr in (700,800)}
    result = {}
    for name, selected in groups.items():
        scores = {}
        for v in g.VARIANTS:
            scores[v+'/gamma_diag'] = [r['arms'][v]['gamma_diag'] for r in selected]
            scores[v+'/full'] = [full[a.key(r)]['arms'][v]['full'] for r in selected]
        metrics = ('extrinsic_bit_logloss', 'fer', 'info_errors', 'nmse_final', 'data_mse_final', 'symbol_variance_final')
        columns = [np.array([x[f]-y[f] for x,y in zip(scores[v+'/gamma_diag'], scores[v+'/full'])])
                   for v in g.VARIANTS for f in metrics]
        effects = a.trajectory.paired(np.column_stack(columns), [r['frame'] for r in selected], n_boot=n_boot, seed=SEED)
        contrasts = {}
        for vi, v in enumerate(g.VARIANTS):
            effect = {f:effects[vi*len(metrics)+i] for i,f in enumerate(metrics)}
            lo, hi = effect['extrinsic_bit_logloss']['ci95']
            verdict = 'favors_full_Gamma' if lo > 0 else ('favors_gamma_diag' if hi < 0 else 'inconclusive')
            full_mean = float(np.mean([d['extrinsic_bit_logloss'] for d in scores[v+'/full']]))
            contrasts[v] = dict(delta='gamma_diag minus saved full', primary_logloss_verdict=verdict, effects=effect,
                relative_logloss_change=effect['extrinsic_bit_logloss']['point']/full_mean if full_mean > 0 else None,
                transitions={f'{x}->{y}':sum(d['fer']==x and e['fer']==y for d,e in zip(scores[v+'/full'],scores[v+'/gamma_diag']))
                             for x in (0,1) for y in (0,1)})
        arms = {}
        for label, records in scores.items():
            elapsed = {f:np.array([d[f] for d in records]) for f in ('detect_seconds','decode_seconds')}
            elapsed['combined_seconds'] = elapsed['detect_seconds']+elapsed['decode_seconds']
            arms[label] = dict(failures=sum(d['fer'] for d in records), fer=float(np.mean([d['fer'] for d in records])),
                **{f'mean_{f}':float(np.mean([d[f] for d in records])) for f in metrics if f != 'fer'},
                timing={f:a.timing(value) for f,value in elapsed.items()})
        result[name] = dict(n=len(selected), arms=arms, contrasts=contrasts)
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ('old-rows','three-rows','full-rows','out'): parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    old, r2 = a.reference.load_reference(args.old_rows)
    raw, t3, _ = a.trajectory.load(args.three_rows,args.three_rows.parent/'analysis_fix/summary.json')
    three = {a.key(r):r for r in raw}; receipt = dict(three=t3, run2=r2)
    full, full_receipt = g.load_full(args.full_rows,three,old,receipt)
    rows, hashes, identity, gate = load(args.out,three,old,full,receipt,full_receipt)
    report = dict(label='Informed old-cohort Gamma-only ablation; no equivalence, unique mechanism or independent confirmation',
        _argv=sys.argv[1:], bootstrap=dict(seed=SEED,resamples=N_BOOT,cluster='50 shared P1 frames; all4 cells jointly'),
        n_keys=len(rows), source_identity=identity, raw_sha256=hashes, groups=summarize(rows,full),
        main_calls=dict(receiver=sum(r['receiver_calls'] for r in rows),decoder=sum(r['decoder_calls'] for r in rows)),
        gate_calls=dict(receiver=sum(r['receiver_calls']+r['observer_receiver_calls'] for r in gate),decoder=sum(r['decoder_calls'] for r in gate)),
        timing_scope=identity['timing_scope'])
    with (args.out/'summary.json').open('x') as handle: handle.write(json.dumps(report,indent=1,allow_nan=False)+'\n')
    print('validated200 keys; main400/400; gate24/16 receiver/decoder calls')


if __name__ == '__main__': main()
