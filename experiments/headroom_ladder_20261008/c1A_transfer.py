"""Frozen A-transfer screen: SOURCE fit, prelabel seal, then separate truth evaluation.

No receiver or simulation is called by this program. The prelabel path never
JSON-decodes TARGET truth fields. See the frozen 2026-10-13 protocol.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

import c1A_io as io
import c1A_stats as stats

HERE = Path(__file__).resolve().parent
PROTOCOL_MD5 = '104e980ade8969d3ab77217df289f3d6'
PROTOCOL_COMMIT = 'd65137de'
RIDGES = (.001, .01, .1, 1., 10.)
MODELS = ('A', 'G', 'L', 'C')
SOURCE = {'c1esc': ((650, 300, 16), (650, 300, 20)),
          'c1apb_train8': ((800, 300, 28), (800, 300, 32))}
PRIMARY = {'H1': (650, 200, (4, 8, 12, 16, 20, 24, 28)),
           'H2': (800, 200, (12, 16, 20, 24, 28, 32, 36)),
           'H3': (800, 300, (12, 16, 20, 24, 28, 32, 36)),
           'H4': (800, 500, (4, 8, 12, 16, 20, 24, 28, 32)),
           'H5': (950, 300, (16, 20, 24, 28, 32, 36, 40))}
TARGET = {'c1ib2_rep': ('primary', [(s, r, L) for s, r, ls in PRIMARY.values() for L in ls],
                         ('R4T20', 'R4T40'), 4),
          'c1f_r10': ('long', [(650, 300, L) for L in (24, 28, 32)], ('FULL_R10',), 10),
          'c1ib2_r10': ('long', [(650, 300, L) for L in (16, 20, 24, 28, 32)], ('R10T40',), 10),
          'c1g_r10lo': ('closure', [(650, 300, L) for L in (16, 20)], ('FULL_R10',), 10)}
ALIASES = {'c1i': ('FULL_R4', 4), 'c1ib': ('IB_T40', 4)}


def utc():
    return datetime.now(timezone.utc).isoformat()


def json_dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
                      default=lambda x: x.tolist() if isinstance(x, np.ndarray) else
                      x.item() if isinstance(x, np.generic) else str(x)) + '\n'


def write_exclusive(path, data, binary=False):
    with Path(path).open('xb' if binary else 'x') as stream:
        stream.write(data)


def model_features(name, syn, snr, rho, L, T, Rc):
    syn = np.asarray(syn, dtype=float)
    if not np.isfinite(syn).all() or (syn < 0).any() or (syn > 1026).any():
        raise ValueError('invalid round-1 syndrome')
    k = 8 * L / 1024
    v = 10 ** (-snr / 1000) / (2 * (1 - rho / 1000))
    u = np.log1p(syn)
    one = np.ones_like(u)
    if name == 'A':
        b = T * (Rc - 1) / 400
        return np.column_stack((u, one * int(T == 40), one * Rc / 10,
                                one * k, one * math.log(v), one * b, one * k * b))
    if name == 'G':
        return np.column_stack((u, one * int(T == 40), one * Rc / 10))
    if name == 'C':
        return np.column_stack((one * math.log(k), one * math.log(v),
                                one * math.log(T / 20), one * math.log(Rc)))
    raise ValueError(name)


def _fit_once(x, y, w, ridge, name):
    w = np.asarray(w, dtype=float)
    w = w / w.sum()
    mean = np.sum(w[:, None] * x, axis=0)
    var = np.sum(w[:, None] * (x - mean) ** 2, axis=0)
    keep = np.flatnonzero(np.any(x != x[0], axis=0))
    sd = np.sqrt(var[keep])
    if not np.isfinite(sd).all() or (sd <= 0).any():
        raise ValueError('bad SOURCE standard deviation')
    z = (x[:, keep] - mean[keep]) / sd
    constraints = {'C': {0: (0, None), 1: (0, None), 2: (None, 0), 3: (None, 0)}}
    bounds = [(None, None)] + [constraints.get(name, {}).get(int(j), (None, None)) for j in keep]

    def objective(param):
        eta = param[0] + z @ param[1:]
        loss = np.sum(w * (np.logaddexp(0, eta) - y * eta)) + ridge * np.dot(param[1:], param[1:]) / 2
        err = w * (expit(eta) - y)
        grad = np.r_[err.sum(), z.T @ err + ridge * param[1:]]
        return float(loss), grad

    result = minimize(objective, np.zeros(len(keep) + 1), method='L-BFGS-B', jac=True,
                      bounds=bounds, options={'maxiter': 1000, 'maxls': 100, 'gtol': 1e-8, 'ftol': 1e-12})
    if not result.success:
        raise RuntimeError(f'{name} optimizer failed at lambda={ridge}: {result.message}')
    return {'name': name, 'ridge': ridge, 'columns_kept': keep.tolist(),
            'columns_dropped': [j for j in range(x.shape[1]) if j not in keep],
            'mean': mean[keep].tolist(), 'sd': sd.tolist(), 'intercept': float(result.x[0]),
            'coef': result.x[1:].tolist(), 'solver': {'method': 'L-BFGS-B', 'maxiter': 1000,
            'maxls': 100, 'gtol': 1e-8, 'ftol': 1e-12, 'iterations': int(result.nit),
            'objective': float(result.fun), 'grad_inf': float(np.linalg.norm(result.jac, np.inf)),
            'status': str(result.message)}}


def predict_model(model, x):
    keep = model['columns_kept']
    z = (np.asarray(x)[:, keep] - np.asarray(model['mean'])) / np.asarray(model['sd'])
    return expit(model['intercept'] + z @ np.asarray(model['coef']))


def fit_model(x, y, frame, w, name):
    x, y, frame, w = map(np.asarray, (x, y, frame, w))
    if x.ndim != 2 or len(x) != len(y) or len(x) != len(frame) or len(x) != len(w):
        raise ValueError('SOURCE dataset shape mismatch')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(w).all():
        raise ValueError('nonfinite SOURCE dataset')
    if (w <= 0).any() or not np.isin(y, (0, 1)).all() or set(frame % 5) != set(range(5)):
        raise ValueError('invalid SOURCE labels/weights/folds')
    scores = []
    for ridge in RIDGES:
        loss = 0.0
        for fold in range(5):
            train = frame % 5 != fold
            valid = ~train
            model = _fit_once(x[train], y[train], w[train], ridge, name)
            prob = predict_model(model, x[valid])
            loss += float(np.dot(w[valid], (prob - y[valid]) ** 2))
        scores.append(loss / float(w.sum()))
    ranks = [(round(score, 12), -ridge, j) for j, (score, ridge) in enumerate(zip(scores, RIDGES))]
    best = min(ranks)[2]
    model = _fit_once(x, y, w, RIDGES[best], name)
    model['cv'] = {'fold': 'parent_frame_mod_5', 'criterion': 'frame_weighted_Brier',
                   'ridges': list(RIDGES), 'scores': scores, 'tie_round_decimals': 12,
                   'tie': 'larger_lambda'}
    return model


def _config_inventory(directory):
    shards = io.shard_files(directory)
    docs = [(cp, json.loads(cp.read_text())) for _, cp, _ in shards]
    if len({doc['_config']['nshard'] for _, doc in docs}) != 1 or len(shards) != docs[0][1]['_config']['nshard']:
        raise ValueError(f'incomplete shards {directory}')
    if {doc['_config']['shard'] for _, doc in docs} != set(range(len(shards))):
        raise ValueError(f'wrong shard IDs {directory}')
    return shards, docs


def _load_archive(root, archive, cells, arms, frames, rounds, phase):
    directory = Path(root) / 'out' / archive
    shards, configs = _config_inventory(directory)
    c0 = configs[0][1]['_config']
    resolved = c0.get('resolved')
    if resolved is None:
        resolved = dict(cells=[[float(s), float(r), [int(x) for x in c0['Ls'].split(',')]]
                              for s in c0['snr_list'].split(',') for r in c0['rho_list'].split(',')],
                        frames=c0['frames'], arms=c0['arms'].split(','))
    resolved_cells = {(int(round(s * 100)), int(round(r * 1000)), int(L))
                      for s, r, ls in resolved['cells'] for L in ls}
    if not set(cells) <= resolved_cells or not set(frames) <= set(range(c0['frame_offset'], c0['frame_offset']+resolved['frames'])):
        raise ValueError(f'unexpected grid in {archive}')
    if not set(arms) <= set(resolved['arms']):
        raise ValueError(f'missing arms in {archive}')
    for _, doc in configs:
        c = doc['_config']
        for key in ('resolved', 'Ls', 'snr_list', 'rho_list', 'frames', 'arms', 'frame_offset'):
            if c.get(key) != c0.get(key):
                raise ValueError(f'shard design mismatch in {archive}/{key}')
    records = {}
    fps = {}
    inputs = {}
    ledger = directory/'REMOTE_ROWS_MD5.txt'
    inputs[str(ledger)] = {'md5': io.digest(ledger)}
    for path, cp, row_md5s in shards:
        inputs.update(row_md5s)
        inputs[str(cp)] = {'md5': io.digest(cp)}
        for number, meta, *raw in io.rows(path, 'source' if phase == 'source' else 'prelabel'):
            # Metadata is projected first. SOURCE labels of excluded frames are never decoded.
            if meta.get('frame') not in frames or meta.get('arm') not in arms:
                continue
            cell = (meta.get('snr_centi_db'), meta.get('rho_permille'), meta.get('L'))
            if cell not in cells:
                continue
            arm = meta['arm']
            T = io.validate_row(meta, (*cell, arm), rounds)
            key = (*cell, arm, meta['frame'])
            if key in records:
                raise ValueError(f'duplicate row {archive}/{key}')
            if phase == 'source':
                full = json.loads(raw[0])
                for r in range(1, 11):
                    if f'ierr{r}' not in full or f'syn{r}' not in full or f'dsha{r}' not in full:
                        raise ValueError(f'incomplete SOURCE endpoint {key}/r{r}')
                meta['labels'] = [int(full[f'ierr{r}'] > 0) for r in range(1, 11)]
            records[key] = meta
            fp_key = (*cell, meta['frame'])
            fp = tuple(meta[k] for k in ('info_sha256', 'noise_sha256', 'physical_gains_sha256', 'channel_seed', 'sigma2'))
            if fp_key in fps and fps[fp_key] != fp:
                raise ValueError(f'arm fingerprint mismatch {archive}/{fp_key}')
            fps[fp_key] = fp
    expected = len(cells) * len(arms) * len(frames)
    if len(records) != expected:
        raise ValueError(f'incomplete {archive}: {len(records)}/{expected}')
    # T20 and T40 have different first-round outputs; only exogenous inputs pair.
    return records, configs, inputs


def build_source(root):
    all_records, all_configs, all_inputs = {}, [], {}
    for archive, cells in SOURCE.items():
        records, configs, inputs = _load_archive(root, archive, cells, ('E10', 'E0'), range(200, 600), 10, 'source')
        all_records.update(records)
        all_configs += configs
        all_inputs.update(inputs)
    context = io.validate_context(all_configs)
    xs, ys, fs, weights = {m: [] for m in ('A', 'G', 'C')}, [], [], []
    for cell in [c for cells in SOURCE.values() for c in cells]:
        for frame in range(200, 600):
            for arm, T in (('E10', 20), ('E0', 40)):
                row = all_records[(*cell, arm, frame)]
                for Rc in range(1, 11):
                    for name in xs:
                        xs[name].append(model_features(name, [row['syn1']], *cell, T, Rc)[0])
                    ys.append(row['labels'][Rc - 1])
                    fs.append(frame)
                    weights.append(1 / 32000)
    if len(ys) != 32000:
        raise ValueError('SOURCE must contain exactly 32000 endpoints')
    data = {k: np.asarray(v, float) for k, v in xs.items()}
    return data, np.asarray(ys, float), np.asarray(fs, int), np.asarray(weights), all_records, context, all_inputs


def _config_id(cohort, snr, rho, L, T, Rc):
    return f'{cohort}_s{snr}r{rho}L{L}T{T}Rc{Rc}'


def build_target(root):
    records, all_configs, inputs, configs = {}, [], {}, []
    for archive, (cohort, cells, arms, rounds) in TARGET.items():
        part, cfgs, inp = _load_archive(root, archive, cells, arms, range(200), rounds, 'target')
        all_configs += cfgs
        inputs.update(inp)
        for cell in cells:
            snr, rho, L = cell
            row_cohort = 'closure' if archive == 'c1ib2_r10' and L in (16, 20) else cohort
            for arm in arms:
                T = 20 if arm in ('FULL_R10', 'R4T20') else 40
                for Rc in range(1, rounds + 1):
                    family = next((f for f, (s, r, ls) in PRIMARY.items() if (s, r) == (snr, rho) and L in ls), None)
                    configs.append({'id': _config_id(row_cohort, snr, rho, L, T, Rc),
                                    'cohort': row_cohort, 'family': family if row_cohort == 'primary' else None,
                                    'snr_centi_db': snr, 'rho_permille': rho, 'L': L, 'K': 8 * L,
                                    'T': T, 'Rc': Rc, 'nframes': 200, 'archive': archive, 'arm': arm})
                    records[_config_id(row_cohort, snr, rho, L, T, Rc)] = [part[(*cell, arm, f)] for f in range(200)]
    # Aliases use the same T, channel and first-round receiver, unlike T20/T40.
    for archive,(arm,rounds) in ALIASES.items():
        cells=[(650,300,L) for L in (16,20,24)]
        part,cfgs,inp=_load_archive(root,archive,cells,(arm,),range(200),rounds,'target')
        inputs.update(inp); all_configs+=cfgs
        T=20 if archive=='c1i' else 40
        for cell in cells:
            comparisons=[c for c in configs if (c['snr_centi_db'],c['rho_permille'],c['L'],c['T'])==(*cell,T)]
            for f in range(200):
                row=part[(*cell,arm,f)]
                for c in comparisons:
                    ref=records[c['id']][f]
                    for field in ('syn1','dsha1','info_sha256','noise_sha256','physical_gains_sha256','channel_seed'):
                        if row[field]!=ref[field]:
                            raise ValueError(f'alias first-round mismatch {archive}/{cell}/{f}/{field}')
    context = io.validate_context(all_configs)
    if len(configs) != 388 or len({c['id'] for c in configs}) != len(configs):
        raise ValueError(f'target configuration count {len(configs)} != 388')
    # Parent message/noise fingerprints must pair across every target cell.
    for f in range(200):
        pair = {(records[c['id']][f]['info_sha256'], records[c['id']][f]['noise_sha256']) for c in configs}
        if len(pair) != 1:
            raise ValueError(f'target parent mismatch at frame {f}')
        for L in sorted({c['L'] for c in configs}):
            gains = {(records[c['id']][f]['physical_gains_sha256'], records[c['id']][f]['channel_seed'])
                     for c in configs if c['L'] == L}
            if len(gains) != 1:
                raise ValueError(f'target physical channel mismatch {L}/{f}')
    return configs, records, context, inputs


def _nearest(source_records, snr, rho, L, T, Rc):
    v = 10 ** (-snr / 1000) / (2 * (1 - rho / 1000))
    choices = []
    for s, r, l in [c for cells in SOURCE.values() for c in cells]:
        vj = 10 ** (-s / 1000) / (2 * (1 - r / 1000))
        d2 = ((8 * L - 8 * l) / 32) ** 2 + ((math.log(v) - math.log(vj)) / (1.5 * math.log(10) / 10)) ** 2
        choices.append((d2, s, l, r))
    _, s, l, r = min(choices)
    arm = 'E10' if T == 20 else 'E0'
    events = sum(source_records[(s, r, l, arm, f)]['labels'][Rc - 1] for f in range(200, 600))
    return (events + .5) / 401


def predict_all(models, source_records, configs, records):
    q = np.empty((4, len(configs), 200), dtype=float)
    for j, c in enumerate(configs):
        syn = [row['syn1'] for row in records[c['id']]]
        args = (c['snr_centi_db'], c['rho_permille'], c['L'], c['T'], c['Rc'])
        for m, name in enumerate(('A', 'G', 'C')):
            q[(0, 1, 3)[m], j] = predict_model(models[name], model_features(name, syn, *args))
        q[2, j] = _nearest(source_records, *args)
    if not np.isfinite(q).all() or (q < 0).any() or (q > 1).any():
        raise ValueError('invalid prediction probabilities')
    return q


def code_hashes():
    names = ('c1A_transfer.py', 'c1A_io.py', 'c1A_stats.py')
    return {str(HERE / name): io.digest(HERE / name) for name in names}


def feature_range_audit(source_x,configs,target_rows):
    audit={}
    for name,x in source_x.items():
        target=np.concatenate([model_features(name,[r['syn1'] for r in target_rows[c['id']]],
            c['snr_centi_db'],c['rho_permille'],c['L'],c['T'],c['Rc']) for c in configs])
        low,high=x.min(axis=0),x.max(axis=0)
        audit[name]=dict(source_min=low.tolist(),source_max=high.tolist(),
                        target_below_records_per_column=(target<low).sum(axis=0).tolist(),
                        target_above_records_per_column=(target>high).sum(axis=0).tolist(),
                        clipped_or_removed=False)
    return audit


def _verify_protocol(args):
    if args.protocol_md5 != PROTOCOL_MD5 or args.protocol_commit != PROTOCOL_COMMIT:
        raise ValueError('wrong frozen protocol attestation')
    if io.digest(args.protocol) != PROTOCOL_MD5:
        raise ValueError('frozen protocol MD5 mismatch')


def _provenance(args, inputs, code):
    return {'_argv': sys.argv, '_config': dict(stage=args.stage,zero_new_simulation=True,bootstrap_B=20000,bootstrap_seed=20261017),
            'protocol_path': str(Path(args.protocol).resolve()),
            'protocol_md5': PROTOCOL_MD5, 'protocol_commit': PROTOCOL_COMMIT,
            'inputs': inputs, 'code_md5s': code, 'phase_utc': utc(),
            'environment': {'python': sys.version, 'platform': platform.platform(),
                            'numpy': np.__version__, 'scipy': __import__('scipy').__version__,
                            'hostname': platform.node(), 'threads': {k: os.environ.get(k) for k in
                            ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')}}}


def _guard(inputs, code):
    for path, hashes in inputs.items():
        if 'md5' in hashes and io.digest(path) != hashes['md5']:
            raise ValueError(f'changed config {path}')
        if 'compressed_md5' in hashes and io.digest(path) != hashes['compressed_md5']:
            raise ValueError(f'changed input {path}')
    if code_hashes() != code:
        raise ValueError('code changed during phase')


def prelabel(args):
    _verify_protocol(args)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    code = code_hashes()
    x, y, frame, w, source_rows, source_context, source_inputs = build_source(args.root)
    models = {name: fit_model(x[name], y, frame, w, name) for name in ('A', 'G', 'C')}
    configs, target_rows, target_context, target_inputs = build_target(args.root)
    if source_context != target_context:
        raise ValueError('SOURCE/TARGET numerical context mismatch')
    for field in ('info_sha256','noise_sha256'):
        train_ids={r[field] for r in source_rows.values()}
        target_ids={r[field] for rr in target_rows.values() for r in rr}
        if train_ids & target_ids:
            raise ValueError(f'SOURCE/TARGET fingerprint overlap: {field}')
    q = predict_all(models, source_rows, configs, target_rows)
    predictions = stats.static_predictions(configs, q)
    inputs = {**source_inputs, **target_inputs}
    inputs[str(args.protocol)]={'md5':io.digest(args.protocol)}
    _guard(inputs, code)
    out.mkdir(parents=True, exist_ok=False)
    npz = out / 'pred_q.npz'
    with npz.open('xb') as stream:
        np.savez_compressed(stream, q=q)
    seal = {'schema': 'c1A_transfer_seal_v1', 'protocol': 'A-prefix7 fixed endpoint',
            'models': models, 'lookup': {'distance': '((K-Kj)/32)^2+((lnv-lnvj)/(1.5ln10/10))^2',
            'tie': 'SNR_L_ascending', 'rate': 'Jeffreys (events+.5)/401',
            'source_rates': [dict(snr_centi_db=s,rho_permille=r,L=L,T=T,Rc=Rc,
                q=_nearest(source_rows,s,r,L,T,Rc)) for cells in SOURCE.values()
                for s,r,L in cells for T in (20,40) for Rc in range(1,11)]},
            'configs': configs, 'predictions': predictions, 'q_npz_md5': io.digest(npz),
            'features': {'A': ['log1p_syn1', 'T40', 'Rc/10', 'K/N', 'ln_receiver_v', 'b', 'K/N*b'],
            'G': ['log1p_syn1', 'T40', 'Rc/10'], 'C': ['ln_K/N', 'ln_receiver_v', 'ln_T/20', 'ln_Rc']},
            'source_partition': 'OLD frames200:599, c1esc/c1apb_train8 E10/E0 only; 32000 endpoints',
            'target_partition': 'OLD frames0:199; primary+long+closure; prelabel metadata projection only',
            'feature_range_audit': feature_range_audit(x,configs,target_rows),
            'context': source_context, 'provenance': _provenance(args, inputs, code)}
    write_exclusive(out / 'seal.json', json_dump(seal))
    write_exclusive(out / 'seal.md', f'# A transfer prediction seal\n\nUTC: {seal["provenance"]["phase_utc"]}\n\n'
                    f'Protocol MD5: {PROTOCOL_MD5}\n\nPrediction NPZ MD5: {seal["q_npz_md5"]}\n\n'
                    f'Seal JSON MD5: {io.digest(out / "seal.json")}\n\nTARGET truth remains sealed.\n\n```json\n'+json_dump(seal['provenance'])+'```\n')
    print(json_dump({'seal': str(out / 'seal.json'), 'seal_md5': io.digest(out / 'seal.json')}))


def _eval_labels(root, configs):
    expected = {(c['archive'], c['snr_centi_db'], c['rho_permille'], c['L'], c['arm'], f)
                for c in configs for f in range(200)}
    truth = {}
    inputs = {}
    for archive in sorted({c['archive'] for c in configs}|set(ALIASES)):
        ledger = Path(root)/'out'/archive/'REMOTE_ROWS_MD5.txt'
        inputs[str(ledger)] = {'md5': io.digest(ledger)}
        for path, cp, md5s in io.shard_files(Path(root) / 'out' / archive):
            inputs.update(md5s)
            inputs[str(cp)] = {'md5': io.digest(cp)}
            for number, meta, raw in io.rows(path, 'evaluate'):
                key = (archive, meta.get('snr_centi_db'), meta.get('rho_permille'), meta.get('L'),
                       meta.get('arm'), meta.get('frame'))
                if key not in expected:
                    continue
                if key in truth:
                    raise ValueError(f'duplicate target truth {key}')
                row = json.loads(raw)
                maxr = max(c['Rc'] for c in configs if (c['archive'], c['snr_centi_db'],
                            c['rho_permille'], c['L'], c['arm']) == key[:5])
                vals = []
                for r in range(1, maxr + 1):
                    if f'ierr{r}' not in row or f'syn{r}' not in row or f'dsha{r}' not in row:
                        raise ValueError(f'missing endpoint {key}/r{r}')
                    vals.append(int(row[f'ierr{r}'] > 0))
                truth[key] = (row, vals)
    for archive,(arm,rounds) in ALIASES.items():
        directory=Path(root)/'out'/archive
        aliases={}
        for path,_,_ in io.shard_files(directory):
            for _,meta,raw in io.rows(path,'evaluate'):
                if meta.get('frame') not in range(200) or meta.get('arm')!=arm or meta.get('L') not in (16,20,24):
                    continue
                key=(meta['L'],meta['frame'])
                if key in aliases:
                    raise ValueError(f'duplicate alias truth {archive}/{key}')
                aliases[key]=json.loads(raw)
        if len(aliases)!=600:
            raise ValueError(f'incomplete alias truth {archive}')
        T=20 if archive=='c1i' else 40
        for c in configs:
            if c['snr_centi_db']!=650 or c['rho_permille']!=300 or c['L'] not in (16,20,24) or c['T']!=T:
                continue
            for f in range(200):
                ref=truth[(c['archive'],650,300,c['L'],c['arm'],f)][0]
                alias=aliases[(c['L'],f)]
                for r in range(1,rounds+1):
                    for prefix in ('syn','ierr','cerr','dsha'):
                        if alias[f'{prefix}{r}']!=ref[f'{prefix}{r}']:
                            raise ValueError(f'alias future mismatch {archive}/{c["L"]}/{f}/r{r}/{prefix}')
    if set(truth) != expected:
        raise ValueError(f'incomplete target labels: {len(truth)}/{len(expected)}')
    y = np.asarray([[truth[(c['archive'], c['snr_centi_db'], c['rho_permille'], c['L'],
                            c['arm'], f)][1][c['Rc'] - 1] for f in range(200)] for c in configs], dtype=np.uint8)
    # Full future/prefix audit is deliberately delayed until after seal verification.
    for c in configs:
        if c['Rc'] == 1:
            continue
        for f in range(200):
            key = (c['archive'], c['snr_centi_db'], c['rho_permille'], c['L'], c['arm'], f)
            row = truth[key][0]
            for r in range(1, c['Rc'] + 1):
                if not 0 <= row[f'syn{r}'] <= 1026 or not isinstance(row[f'dsha{r}'], str):
                    raise ValueError(f'invalid future endpoint {key}/r{r}')
    return y, inputs


def evaluate(args):
    _verify_protocol(args)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    if io.digest(args.seal) != args.seal_md5:
        raise ValueError('seal MD5 mismatch')
    seal = json.loads(Path(args.seal).read_text())
    if seal['schema'] != 'c1A_transfer_seal_v1' or seal['provenance']['protocol_md5'] != PROTOCOL_MD5:
        raise ValueError('wrong seal')
    if seal['provenance']['code_md5s'] != code_hashes():
        raise ValueError('code changed since seal')
    if io.digest(Path(args.seal).with_name('pred_q.npz')) != seal['q_npz_md5']:
        raise ValueError('prediction NPZ changed')
    _guard(seal['provenance']['inputs'], seal['provenance']['code_md5s'])
    with np.load(Path(args.seal).with_name('pred_q.npz'), allow_pickle=False) as data:
        q = data['q']
    configs = seal['configs']
    if q.shape != (4, len(configs), 200):
        raise ValueError('prediction NPZ shape mismatch')
    if stats.static_predictions(configs,q)!=seal['predictions']:
        raise ValueError('sealed prediction replay changed')
    # All guards above run before the first TARGET truth field is decoded.
    y, current_inputs = _eval_labels(args.root, configs)
    if current_inputs != {k: v for k, v in seal['provenance']['inputs'].items()
                          if any(f'/out/{archive}/' in k for archive in (*TARGET,*ALIASES))}:
        raise ValueError('TARGET input inventory changed')
    analysis = stats.evaluate(configs, q, y, audit={'seal_md5': args.seal_md5,'integrity_pass':True,
                               'parents_disjoint':True,'prelabel_truth_values_decoded':0,'full_alias_prefixes_equal':True})
    _guard(seal['provenance']['inputs'], seal['provenance']['code_md5s'])
    out.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'c1A_transfer_analysis_v1', 'analysis': analysis,
              'seal_md5': args.seal_md5, 'provenance': _provenance(args, current_inputs, code_hashes())}
    write_exclusive(out / 'analysis.json', json_dump(result))
    write_exclusive(out / 'analysis.md', render_analysis(result))
    print(json_dump({'analysis': str(out / 'analysis.json'), 'analysis_md5': io.digest(out / 'analysis.json')}))


def render_analysis(result):
    a=result['analysis']
    lines=['# A transfer — ARCHIVAL SCREENING','',f'Verdict: **{a["verdict"]}**.',
           'SOURCE200–599 calibrated once; target0–199 round-1 probes; fixed endpoint info FER. No TCOM/latency claim.',
           f'Seal MD5: `{result["seal_md5"]}`.','',
           '|Gate|Status|','|---|---|']
    lines += [f'|{key}|{val["status"]}|' for key,val in a['gates'].items()]
    lines += ['',f'ECE_A={a["calibration"]["A"]["ECE"]:.6f}; E_delta_A={a["E_delta"]["A"]["point"]:.6f}; '
              f'boundary error≤.05 fraction={a["E_delta"]["A"]["fraction_error_le_005"]:.6f}.',
              '', '|Comparator|Brier gain [simultaneous endpoints]|J gain [simultaneous endpoints]|','|---|---|---|']
    for name in ('G','L','C'):
        b,j=a['Brier_gains'][name],a['J_gains'][name]
        lines.append(f'|{name}|{b["point"]:.6f} [{b["interval"]["lower"]:.6f},{b["interval"]["upper"]:.6f}]|'
                     f'{j["point"]:.6f} [{j["interval"]["lower"]:.6f},{j["interval"]["upper"]:.6f}]|')
    lines += ['',f'J_A={a["J"]["A"]["point"]:.6f}; tasks J≤.1 fraction={a["fraction_tasks_J_A_le_010"]:.6f}; '
              f'population-certified fraction={a["gates"]["A4"]["certified_task_fraction"]:.6f}.',
              '', '|Kill rule|Triggered|','|---|---|']
    lines += [f'|{k}|{v["triggered"]}|' for k,v in a['kills'].items()]
    lines += ['', 'Full reliability bins/family bias, all 388 configurations (288 primary), 23 empirical/population designs, '
              'Kc censor statuses and secondary δ=.2: analysis.json.',
              'Bootstrap gain tails=.04/12; negative tails=.05/7; uniform primary CP tails=.01/576. '
              'Frame parents synchronized; predictors fixed; selectors/panel/oracle redrawn each bootstrap.',
              *a['limitations'],'','```json',json_dump(result['provenance']),'```']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='stage', required=True)
    for stage in ('prelabel', 'evaluate'):
        p = sub.add_parser(stage)
        p.add_argument('--root', type=Path, required=True, help='experiment root containing out/')
        p.add_argument('--out', type=Path, required=True, help='new result directory')
        p.add_argument('--protocol', type=Path, required=True)
        p.add_argument('--protocol-md5', required=True)
        p.add_argument('--protocol-commit', required=True)
        if stage == 'evaluate':
            p.add_argument('--seal', type=Path, required=True)
            p.add_argument('--seal-md5', required=True)
    args = parser.parse_args(argv)
    if args.stage == 'prelabel':
        prelabel(args)
    else:
        evaluate(args)


if __name__ == '__main__':
    main()
