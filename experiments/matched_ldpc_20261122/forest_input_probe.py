#!/usr/bin/env python3
"""Separate first-round C1 input quality and equal-input decoder performance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

import forest_minimal as frozen

c1run = frozen.c1run
NEW_ARCHIVE = Path(__file__).resolve().parent / 'out/forest_minimal_55082b53'
NEW_ROWS_DIGEST = 'be1e0e8c787c8d7406eed485e2f57d5ac3a0d7eacf61d8a93a73052e87b8b12b'
OLD_CODE_MD5 = '601d12c9f2351a33ec6e429ff49fbb4f'
ARMS = ('matched', 'forest')
SEED, DRAWS, CPU_CAP = 20261127, 4000, 300


def selected_rows():
    old = frozen.old_rows()
    new = {}
    manifest = hashlib.sha256()
    for path in sorted(NEW_ARCHIVE.glob('rows_L28_*_part*.jsonl')):
        blob = path.read_bytes()
        manifest.update(f'{hashlib.md5(blob).hexdigest()}  {path.name}\n'.encode())
        for row in map(json.loads, blob.splitlines()):
            key = row['snr_centi_db'], row['frame']
            if key in new or row['load'] != 28:
                raise ValueError('invalid or duplicated new archive row')
            new[key] = row
    if manifest.hexdigest() != NEW_ROWS_DIGEST:
        raise ValueError('forest replay differs from its published row manifest')
    if set(new) != {(snr, f) for snr in frozen.SNRS for f in frozen.FRAMES}:
        raise ValueError('forest replay is missing registered keys')
    rows = {
        (snr, frame): (old[snr][frame], reference)
        for (snr, frame), reference in sorted(new.items())
        if frozen.error(reference['arms']['forest']) and not frozen.error(old[snr][frame]['arms']['matched'])
    }
    if ([sum(key[0] == snr for key in rows) for snr in frozen.SNRS] != [14, 14] or
            len({frame for _, frame in rows}) != 20):
        raise ValueError('added-failure cohort changed')
    return rows


def load_codes(matrix):
    old_path = frozen.ARCHIVE / 'codes.npz'
    if hashlib.md5(old_path.read_bytes()).hexdigest() != OLD_CODE_MD5:
        raise ValueError('old matching matrix archive has changed')
    with np.load(old_path, allow_pickle=False) as arrays:
        old = {key: arrays[f'matched_{key}'] for key in ('H', 'G', 'free_cols', 'chk', 'var', 'row_ptr')}
    old.update(n=2048, k=1024)
    return {'matched': old, 'forest': frozen.forest_code(matrix)}


def bit_score(decoded, word):
    return int(np.count_nonzero(decoded != word))


def replay(ctx, models, cfg, decoder, snr, frame, references):
    paths = c1run.c1.draw_c1_paths(c1run.c1i.C1_MAP_ENTROPY, frame, 28)
    matrix = c1run.c1.c1_physical_h(ctx, paths)
    taps = c1run.c1.tap_sequences(paths, ctx.system.N_total)
    source_inputs, signs, words, inputs, scores = {}, {}, {}, {}, {}
    for arm, archive in zip(ARMS, references):
        model = models[arm]
        msg = c1run.c1.c1_message(model, c1run.c1i.C1_MAP_ENTROPY, frame, c1run.RHO)
        raw, diagnostics = c1run.c1.c1_base(model, msg, paths, matrix)
        raw = c1run.base.cluster_at_snr(raw, snr / 100)
        obs = c1run.base.observe(raw, c1run.RHO, snr / 100)
        truth = c1run.base.truth_from_raw(raw, diagnostics)
        words[arm] = truth['coded']
        ref = archive['arms'][arm]
        share = dict(info_sha256=hashlib.sha256(truth['info'].tobytes()).hexdigest(),
                     noise_sha256=truth['noise_sha256'], pilot_sha256=ctx.array_hash(obs['pilot']),
                     channel_seed=truth['channel_seed'], gains_sha256=truth['physical_gains_sha256'])
        if (any(share[key] != archive[key] for key in frozen.SHARED) or
                ref['coded_sha256'] != ctx.array_hash(words[arm]) or
                ref['observed_sha256'] != ctx.array_hash(obs['y'])):
            raise ValueError(f'regenerated observation differs for {arm}, {snr}, {frame}')
        result = c1run.c1i.run_arm(model, obs, truth, 'FULL_R1', paths['tap_delays'], cfg, taps)
        if (result['diag']['dsha1'] != ref['round_decoded_sha256'][0] or
                result['diag']['ierr1'] != ref['round_info_errors'][0]):
            raise ValueError(f'round-one replay differs for {arm}, {snr}, {frame}')
        signs[arm] = 1 - 2 * words[arm].astype(float)
        aligned = signs[arm] * result['llr']
        if aligned.shape != (2048,) or not np.isfinite(aligned).all() or np.max(np.abs(aligned)) > 20:
            raise ValueError('invalid aligned detector vector')
        source_inputs[arm] = aligned
        inputs[arm] = dict(logloss_bits=float(np.mean(np.logaddexp(0, -aligned)) / np.log(2)),
                           hard_ber=float(np.mean((aligned < 0) + .5 * (aligned == 0))),
                           aligned_sha256=ctx.array_hash(aligned))
        scores[arm] = {arm: bit_score(result['decoded'], words[arm])}
    for source, target in (('matched', 'forest'), ('forest', 'matched')):
        incoming = signs[target] * source_inputs[source]
        if not np.array_equal(incoming * signs[target], source_inputs[source]):
            raise ValueError('equal-input sign alignment failed')
        decoded = decoder(models[target].code, incoming, maxiter=50)['decoded']
        scores[source][target] = bit_score(decoded, words[target])
    return dict(frame=frame, snr_centi_db=snr, inputs=inputs, wrong_coded_bits=scores)


def summarize(rows):
    ids = np.array([row['frame'] for row in rows])
    distinct, index = np.unique(ids, return_inverse=True)
    rng = np.random.default_rng(SEED)
    draws = rng.multinomial(len(distinct), np.full(len(distinct), 1 / len(distinct)), size=DRAWS)[:, index]
    denominators = draws.sum(axis=1)

    def contrast(values, margin):
        observed = float(np.mean(values))
        lo, hi = (float(x) for x in np.quantile((draws @ values) / denominators, [.025, .975]))
        label = 'UNRESOLVED'
        if observed >= margin and lo > 0:
            label = 'WORSE'
        elif observed <= -margin and hi < 0:
            label = 'BETTER'
        elif -margin <= lo <= hi <= margin:
            label = 'SMALL'
        return dict(mean=observed, ci95=[lo, hi], label=label, margin=margin)

    ll = np.array([[row['inputs'][arm]['logloss_bits'] for arm in ARMS] for row in rows])
    hard = np.array([[row['inputs'][arm]['hard_ber'] for arm in ARMS] for row in rows])
    ber = np.array([[[row['wrong_coded_bits'][source][target] / 2048 for target in ARMS]
                     for source in ARMS] for row in rows])
    by_source = {arm: contrast(ber[:, s, 1] - ber[:, s, 0], .01) for s, arm in enumerate(ARMS)}
    return dict(n_keys=len(rows), n_distinct_frames=len(distinct),
                input_logloss=dict(zip(ARMS, ll.mean(axis=0).tolist())),
                input_hard_ber=dict(zip(ARMS, hard.mean(axis=0).tolist())),
                input_forest_minus_matched=contrast(ll[:, 1]-ll[:, 0], .01),
                input_hard_forest_minus_matched=contrast(hard[:, 1]-hard[:, 0], .01),
                coded_ber_by_source={arm: dict(zip(ARMS, ber[:, s, :].mean(axis=0).tolist()))
                                     for s, arm in enumerate(ARMS)},
                words_correct_by_source={arm: dict(zip(ARMS, (ber[:, s, :] == 0).sum(axis=0).tolist()))
                                         for s, arm in enumerate(ARMS)},
                held_input_forest_minus_matched=by_source,
                persistent_worse=all(v['label'] == 'WORSE' for v in by_source.values()),
                diagonal_forest_minus_matched=contrast(ber[:, 1, 1] - ber[:, 0, 0], .01))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    c1run.set_cpu_limit(CPU_CAP)
    args.out.mkdir()
    result = dict(_argv=sys.argv, _config=dict(commit=args.commit, load=28, rounds=1, detector_updates=20,
                  decoder_cap=50, cpu_cap_seconds=CPU_CAP, bootstrap_seed=SEED, bootstrap_draws=DRAWS,
                  rho=c1run.RHO, forest_rows_sha256=NEW_ROWS_DIGEST,
                  old_rows_sha256=frozen.ROWS_DIGEST, old_code_archive_md5=OLD_CODE_MD5,
                  forest_hashes=frozen.HASHES), rows=[])
    try:
        selected = selected_rows()
        ctx, cfg, decoder = c1run.load_context()
        models = c1run.contexts(ctx, load_codes(args.matrix))
        result['_config'].update(c1_source_sha256=ctx.sources, c1_environment=ctx.environment, refit=cfg,
                                 probe_sources={path.name: c1run.base.sha256_file(path)
                                                for path in (Path(__file__), Path(frozen.__file__), Path(c1run.__file__))})
        for (snr, frame), references in selected.items():
            result['rows'].append(replay(ctx, models, cfg, decoder, snr, frame, references))
        result.update(summarize(result['rows']), status='DONE', native_replays=56, extra_decoder_calls=56)
    except Exception as exc:
        result.update(status='STOPPED', reason=f'{type(exc).__name__}: {exc}')
    result['cpu_seconds'] = time.process_time()
    c1run.write_json(args.out / 'results.json', result)
    print(result['status'], result.get('reason', ''), result['cpu_seconds'], flush=True)
    if result['status'] != 'DONE':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
