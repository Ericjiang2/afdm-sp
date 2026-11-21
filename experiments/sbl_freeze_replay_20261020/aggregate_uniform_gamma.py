#!/usr/bin/env python3
"""Strict saved-output adequacy readout; no receiver or SBL execution."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__uniform_producer', HERE/'uniform_gamma.py')
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
a = g.oldagg
SEED, N_BOOT = 20261029, 10000
IDENTITY = ('schema', 'producing_commit', 'reference', 'full_reference', 'diag_reference', 'source_md5',
            'frozen_actual_paths', 'own_md5', 'actual_sources', 'normal_system', 'timing_scope')


def validate(rows, three, old, full, diag, gate=False):
    expected = set(three) if not gate else {k for k in three if k[3] == 9100}
    keys = [a.key(r) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != expected:
        raise ValueError('missing/duplicate/extra uniform Gamma keys')
    for r in rows:
        k = a.key(r); baseline = full[k]
        if (r.get('schema') != g.SCHEMA or r.get('sbl_calls') != 0 or r.get('status') != 'ok'
                or r.get('receiver_calls') != (4 if gate else 2) or r.get('decoder_calls') != (4 if gate else 2)
                or r.get('observer_receiver_calls') != (2 if gate else 0)
                or r.get('observer_parity') is not gate or r.get('full_replay') is not gate
                or r.get('full_row_sha256') != a.row_sha(baseline) or r.get('diag_row_sha256') != a.row_sha(diag[k])
                or any(r.get(f) != baseline[f] for f in ('three_row_sha256', 'run2_row_sha256', 'input_sha256', 'inputs', 'observation_sha256'))
                or set(r.get('arms', {})) != set(g.VARIANTS)):
            raise ValueError('failed row/calls/source/input binding')
        attempts = r['attempts']
        required = {(v, m, observed) for v in g.VARIANTS for m, observed in
                    ((('full', False), ('uniform_gamma', False), ('uniform_gamma', True)) if gate else (('uniform_gamma', False),))}
        actual = [(t['variant'], t['mode'], t.get('record_states') is False) for t in attempts]
        if (len(actual) != len(required) or set(actual) != required or any(t['status'] != 'ok' for t in attempts)
                or any(not np.isfinite(t[f]) or t[f] < 0 for t in attempts if t.get('record_states') is not False
                       for f in ('detect_seconds', 'score_seconds'))):
            raise ValueError('attempt coverage/failure retention')
        # Reuse frozen schema validator without emitting a synthetic baseline view.
        view = copy.deepcopy(baseline)
        for v in g.VARIANTS:
            if set(r['arms'][v]) != ({'full', 'uniform_gamma'} if gate else {'uniform_gamma'}):
                raise ValueError('unexpected scientific arm')
            score = r['arms'][v]['uniform_gamma']
            g.validate_projection(score['projection_diagnostics'])
            if (score['actual_gamma_fft_count'] != 40 or score['gamma_projected_variance_calls'] != 40
                    or score['actual_fft_count'] != 81 or score['logical_fft_count'] != 61):
                raise ValueError('actual versus logical transform count')
            view['arms'][v]['full'] = score
            if gate: g.gamma.validate_full(r['arms'][v]['full'], baseline['arms'][v]['full'])
        a.validate([view], {k:three[k]}, {k:old[k]})
        if gate:
            for v in g.VARIANTS: view['arms'][v]['full'] = r['arms'][v]['full']
            a.validate([view], {k:three[k]}, {k:old[k]})
    return rows


def validate_identity(identity, receipt, full_receipt, diag_receipt):
    if (identity['schema'] != g.SCHEMA or not re.fullmatch(r'[0-9a-f]{40}', identity['producing_commit'])
            or identity['reference'] != receipt or identity['full_reference'] != full_receipt
            or identity['diag_reference'] != diag_receipt
            or identity['source_md5'] != full_receipt['identity']['source_md5']
            or identity['frozen_actual_paths'] != full_receipt['identity']['frozen_actual_paths']
            or identity['normal_system'] != g.NORMAL or identity['timing_scope'] != g.TIMING):
        raise ValueError('mixed source/reference/commit identity')
    if set(identity['own_md5']) != set(g.OWN): raise ValueError('new source inventory coverage')
    for name in g.OWN:
        digest = hashlib.md5((HERE/name).read_bytes()).hexdigest()
        if (identity['own_md5'][name] != digest or identity['actual_sources'].get(name) !=
                dict(path=str(g.ROOT/'experiments/sbl_freeze_replay_20261020'/name), md5=digest)):
            raise ValueError('actual new source path/hash drift')
    required = {'gamma', 'gamma_aggregate', 'cohort', 'oldagg', 'helper', 'trajectory', 'block', 'native',
                'physical', 'replay', 'aggregate', 'base', 'oldd', 'oldagg_replay', 'reference'} | set(g.OWN)
    if set(identity['actual_sources']) != required: raise ValueError('actual loaded source inventory coverage')
    # Exact loaded receiver/helper paths come from the qualified frozen inventory.
    frozen = full_receipt['identity']['own_md5'] | diag_receipt['identity']['own_md5']
    for name, record in identity['actual_sources'].items():
        path = Path(record['path'])
        if not path.is_relative_to(g.ROOT): raise ValueError('actual source outside frozen project')
        relative = str(path.relative_to(g.ROOT))
        if name not in g.OWN and frozen.get(relative) != record['md5']:
            raise ValueError('actual loaded helper differs from frozen reference')


def load(directory, three, old, full, diag, receipt, full_receipt, diag_receipt):
    paths = [directory/f'rows_shard{i:03d}.jsonl' for i in range(12)]
    configs = [directory/f'config_shard{i:03d}.json' for i in range(12)]
    if set(directory.glob('rows_shard*.jsonl')) != set(paths) or set(directory.glob('config_shard*.json')) != set(configs):
        raise ValueError('exact12 raw/config shards required')
    values = [json.loads(p.read_text()) for p in configs]
    identities = [{k:c['_config'][k] for k in IDENTITY} for c in values]
    identity = identities[0]
    if any(x != identity for x in identities): raise ValueError('mixed shard source identity')
    validate_identity(identity, receipt, full_receipt, diag_receipt)
    if (directory/'PRODUCING_COMMIT.txt').read_text().strip() != identity['producing_commit']:
        raise ValueError('producing commit stamp drift')
    gate_config = json.loads((directory/'config_gate.json').read_text())
    if {k:gate_config['_config'][k] for k in IDENTITY} != identity or gate_config['_config']['shard'] != 0:
        raise ValueError('gate source/reference drift')
    gate = [json.loads(line) for line in (directory/'gate.jsonl').read_text().splitlines() if line.strip()]
    validate(gate, three, old, full, diag, gate=True)
    rows = []
    for shard, (path, config) in enumerate(zip(paths, values)):
        argv = config['_argv']
        if (config['_config']['shard'] != shard or not 0 < config['_config']['deadline_seconds'] <= 690
                or not isinstance(argv, list) or '--producing-commit' not in argv
                or argv[argv.index('--producing-commit')+1] != identity['producing_commit']):
            raise ValueError('shard config ownership/deadline/argv')
        selected = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if any((r['frame']-9100)%12 != shard for r in selected): raise ValueError('shard key ownership')
        rows.extend(selected)
    validate(rows, three, old, full, diag)
    hashes = {p.name:a.reference.file_sha(p) for p in paths+configs+
              [directory/'gate.jsonl', directory/'config_gate.json', directory/'PRODUCING_COMMIT.txt']}
    return rows, hashes, identity, gate


def bootstrap_means(values, frame_ids, n_boot=N_BOOT):
    """Joint arm/upstream draws; shared frame rows use their actual denominator."""
    values = np.asarray(values, float)
    sums = np.zeros((50,)+values.shape[1:]); counts = np.zeros(50)
    if len(values) != len(frame_ids) or not np.isfinite(values).all(): raise ValueError('bootstrap input')
    for frame, value in zip(frame_ids, values):
        if frame not in g.cohort.FRAMES: raise ValueError('unregistered frame')
        sums[frame-9100] += value; counts[frame-9100] += 1
    if np.any(counts == 0): raise ValueError('empty bootstrap frame')
    rng = np.random.default_rng(SEED)
    weights = np.stack([np.bincount(rng.integers(0, 50, 50), minlength=50) for _ in range(n_boot)])
    boot = (weights @ sums.reshape(50, -1))/(weights @ counts)[:, None]
    return values.mean(axis=0), boot.reshape((n_boot,)+values.shape[1:])


def effect(point, draws):
    return dict(point=float(point), ci95=np.percentile(draws, [2.5, 97.5]).tolist())


def adequacy(point, draws):
    """Columns are F,D,U, always paired; linear T avoids a ratio singularity."""
    f, d, u = point; fb, db, ub = draws.T
    denominator, numerator = d-f, d-u
    den, num = db-fb, db-ub
    margin = effect(.1*d+.9*f-u, .1*db+.9*fb-ub)
    lo, hi = margin['ci95']
    invalid_fraction = float(np.mean(den <= 0))
    evaluable = denominator > 0 and invalid_fraction < .01
    verdict = ('PASS' if lo >= 0 else ('FAIL' if hi < 0 else 'INCONCLUSIVE')) if evaluable else 'UNEVALUABLE'
    ratio = dict(point=float(numerator/denominator) if denominator > 0 else None,
        ci95=np.percentile(num/den, [2.5, 97.5]).tolist() if np.all(den > 0) else None,
        nonpositive_denominator_fraction=invalid_fraction, positive_denominator_draws=int(np.sum(den > 0)),
        evaluable=bool(evaluable), threshold=.9)
    return dict(verdict=verdict, T=margin, D=effect(u-f, ub-fb),
        baseline_gain=effect(denominator, den), retained_gain=effect(numerator, num), retention_ratio=ratio)


def summarize(rows, full, diag, n_boot=N_BOOT):
    groups = {'pooled':rows} | {f'{sc}_{snr}':[r for r in rows if r['scenario']==sc and r['snr_centi_db']==snr]
                               for sc in ('U','G') for snr in (700,800)}
    result = {}
    for name, selected in groups.items():
        scores = {v:{m:[] for m in ('full','gamma_diag','uniform_gamma')} for v in g.VARIANTS}
        for r in selected:
            for v in g.VARIANTS:
                for m, score in (('full', full[a.key(r)]['arms'][v]['full']),
                                 ('gamma_diag', diag[a.key(r)]['arms'][v]['gamma_diag']),
                                 ('uniform_gamma', r['arms'][v]['uniform_gamma'])):
                    scores[v][m].append(score)
        values = np.array([[[scores[v][m][i]['extrinsic_bit_logloss'] for m in scores[v]]
                            for v in g.VARIANTS] for i in range(len(selected))])
        point, boot = bootstrap_means(values, [r['frame'] for r in selected], n_boot)
        contrasts = {v:adequacy(point[j], boot[:,j]) for j,v in enumerate(g.VARIANTS)}
        arms = {}
        for v in g.VARIANTS:
            for m, records in scores[v].items():
                elapsed = {f:np.array([d[f] for d in records]) for f in ('detect_seconds','decode_seconds')}
                elapsed['combined_seconds'] = elapsed['detect_seconds']+elapsed['decode_seconds']
                arms[v+'/'+m] = dict(failures=sum(d['fer'] for d in records), fer=float(np.mean([d['fer'] for d in records])),
                    **{f'mean_{f}':float(np.mean([d[f] for d in records])) for f in a.FLOATS+('info_errors',)},
                    timing={f:a.timing(x) for f,x in elapsed.items()})
            contrasts[v]['fer_transitions_full_to_uniform'] = {f'{x}->{y}':sum(d['fer']==x and e['fer']==y
                for d,e in zip(scores[v]['full'],scores[v]['uniform_gamma'])) for x in (0,1) for y in (0,1)}
        result[name] = dict(n=len(selected), arms=arms, contrasts=contrasts,
            joint_adequacy=all(x['verdict']=='PASS' for x in contrasts.values()))
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ('old-rows','three-rows','full-rows','diag-rows','out'): parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    old, r2 = a.reference.load_reference(args.old_rows)
    raw, t3, _ = a.trajectory.load(args.three_rows,args.three_rows.parent/'analysis_fix/summary.json')
    three = {a.key(r):r for r in raw}; receipt = dict(three=t3, run2=r2)
    full, full_receipt = g.gamma.load_full(args.full_rows,three,old,receipt)
    diag, diag_receipt = g.load_diag(args.diag_rows,three,old,full,receipt,full_receipt)
    rows, hashes, identity, gate = load(args.out,three,old,full,diag,receipt,full_receipt,diag_receipt)
    report = dict(label='Informed old-cohort 90% Gamma-benefit retention; no mechanism or independent confirmation',
        _argv=sys.argv[1:], bootstrap=dict(seed=SEED,resamples=N_BOOT,cluster='50 shared P1 frames; all4 cells/all3 arms/both upstreams jointly'),
        n_keys=len(rows), source_identity=identity, raw_sha256=hashes, groups=summarize(rows,full,diag),
        main_calls=dict(receiver=sum(r['receiver_calls'] for r in rows),decoder=sum(r['decoder_calls'] for r in rows),sbl=0),
        gate_calls=dict(receiver=sum(r['receiver_calls']+r['observer_receiver_calls'] for r in gate),decoder=sum(r['decoder_calls'] for r in gate),sbl=0),
        transforms_per_uniform_terminal=dict(logical_frozen_loop=61, actual_gamma=40, native_symbol=41, actual_total=81),
        timing_scope=identity['timing_scope'])
    with (args.out/'summary.json').open('x') as handle: handle.write(json.dumps(report,indent=1,allow_nan=False)+'\n')
    print('validated200 keys; main400/400; gate24/16 receiver/decoder calls; SBL0')


if __name__ == '__main__': main()
