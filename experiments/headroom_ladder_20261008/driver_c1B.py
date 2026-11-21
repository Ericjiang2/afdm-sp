#!/usr/bin/env python
"""Frozen B0 and B1/B2 C1 screen for directional soft feedback.

Only six registered cells, frames 0..31, round one, and the six registered
arms are accepted. Truth is accessed after each receiver call for diagnostics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np
from scipy.optimize import brentq

import driver as base
import driver_c1 as c1
import driver_c1v2 as v2
import c1B_rx

HERE = base.HERE
ENTROPY = hashlib.sha256(b'C1-DIR-B-20261013-v1').hexdigest()
CELLS = ((8.0, .2, 8), (8.0, .2, 24), (8.0, .5, 24),
         (6.5, .3, 16), (6.5, .3, 28), (11.0, .2, 32))
ARMS = ('BASE20', 'BASE40', 'DAMP20', 'RAW20', 'GLOB20', 'DIR20')
SPEC = {
    'schema': 'c1-dir-b-20261013-v1', 'entropy_ascii': 'C1-DIR-B-20261013-v1',
    'entropy_sha256': ENTROPY, 'cells_snr_rho_L': CELLS, 'frames': [0, 32],
    'rounds': 1, 'arms': ARMS, 'epsilon': .01, 'damping': .3,
    'damp_control': .1, 'diagnostic_frames': 16, 'probe_frames': 8,
    'probe_steps': [5, 10, 20], 'probe_relative_steps': [1e-5, 1e-6],
    'independent_logq': [float(x) for x in v2.INDEP_LOGQ],
}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('b0', 'generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    a = p.parse_args(argv)
    a.channel_model = 'c1B'
    if not (1 <= a.nshard <= 32 and 0 <= a.shard < a.nshard):
        raise ValueError('shards must be 1..32 and shard must be in range')
    return a


def arm_spec(arm, b0):
    if b0:
        if arm == 'OFF20':
            return 'OFF', 20, .3
        if arm == 'DIR20':
            return 'DIR', 20, .3
    else:
        if arm in ('BASE20', 'BASE40'):
            return 'BASE', 40 if arm == 'BASE40' else 20, .3
        if arm == 'DAMP20':
            return 'BASE', 20, .1
        if arm in ('RAW20', 'GLOB20', 'DIR20'):
            return arm[:-2], 20, .3
    raise ValueError(f'unregistered arm {arm}')


def fp_head(paths, truth, rho, snr, frame, L, obs):
    row = c1.head_fields(paths, truth, rho, int(round(100 * snr)), frame, L)
    for key in ('y', 'pilot'):
        arr = np.ascontiguousarray(obs[key])
        row[f'observation_{key}_sha256'] = hashlib.sha256(arr.tobytes()).hexdigest()
    row['observation_sigma2'] = float(obs['sigma2'])
    return row


def truth_projection(snap, a_true):
    h_o = np.zeros(len(snap['h']), complex)
    for delay, sl in snap['taps']:
        h_o[sl] = np.linalg.lstsq(snap['M'][:, sl], a_true[delay], rcond=None)[0]
    norm = float(np.vdot(h_o, h_o).real)
    if norm <= 0 or not np.isfinite(norm):
        raise ValueError('invalid projected truth norm')
    return h_o, norm


def perp_energy(h, h_o, norm):
    e = np.asarray(h, complex) - h_o
    e -= h_o * (np.vdot(h_o, e) / norm)
    return float(np.vdot(e, e).real)


def independent_control(data, w, target, pd, arm, state):
    """Match true CE-symbol MSE, applying the frozen DIR export map when needed."""
    from messages import alphabet, marginal
    alphabet_q, _ = alphabet(pd)
    prior = np.zeros(2 * len(data))

    def at(logq):
        var = pd / np.exp(logq)
        pseudo = data + np.sqrt(var) * w
        _, _, mu, _ = marginal(-np.abs(pseudo[:, None] - alphabet_q) ** 2 / var, prior, pd)
        if arm == 'DIR20':
            if state is None:
                raise ValueError('missing DIR export state')
            q, u, coef = state['q'], state['u'], float(state['c'])
            real_mu = np.concatenate((mu.real, mu.imag))
            real_r = np.concatenate((pseudo.real, pseudo.imag))
            correction = coef * u * float(np.dot(q, real_mu - real_r))
            mu = mu + correction[:len(mu)] + 1j * correction[len(mu):]
        return mu

    lo, hi = v2.INDEP_LOGQ
    def residual(logq):
        mu = at(logq)
        return float(np.mean(np.abs(data - mu) ** 2) - target)
    flo, fhi = residual(lo), residual(hi)
    if not np.isfinite([flo, fhi]).all() or flo * fhi > 0:
        return None, dict(status='matching_failure', endpoint_residuals=[flo, fhi])
    root = float(brentq(residual, lo, hi, xtol=1e-13, rtol=1e-13, maxiter=200))
    mu = at(root)
    actual = float(np.mean(np.abs(data - mu) ** 2))
    relative = abs(actual - target) / max(target, 1e-15)
    if relative > .01:
        return None, dict(status='matching_failure', relative_error=relative)
    return mu, dict(status='ok', q=float(np.exp(root)), relative_error=relative,
                    mse=actual)


def matched_refits(ctx, obs, data, snap, h_t, m_ce, v_ce, state, arm,
                   a_true, entropy, frame, L):
    """Two plain ridge solves using identical reported variance and lambda."""
    K = len(h_t)
    if np.asarray(v_ce).shape != (len(data),):
        raise ValueError('reported CE variance must have one value per symbol')
    target = float(np.mean(np.abs(data - m_ce) ** 2))
    lam = float(K * (obs['sigma2'] + np.mean(v_ce)))
    h_o, norm = truth_projection(snap, a_true)
    own = v2.soft_refit(ctx, obs, sorted(a_true), flat_cfg(), m_ce, v_ce)[0]
    rng = v2.v2_rng(entropy, frame, L, 8)
    w = (rng.standard_normal(len(data)) + 1j * rng.standard_normal(len(data))) / np.sqrt(2)
    ind, matching = independent_control(data, w, target, .5, arm, state)
    result = dict(status=matching['status'], true_symbol_mse=target,
                  reported_ce_variance=float(np.mean(v_ce)), variance_to_true_mse=float(np.mean(v_ce) / target),
                  lambda_plain=lam, matching=matching,
                  own_orthogonal_risk=perp_energy(own, h_o, norm),
                  receiver_orthogonal_risk=perp_energy(h_t, h_o, norm))
    if ind is None:
        return result
    independent = v2.soft_refit(ctx, obs, sorted(a_true), flat_cfg(), ind, v_ce)[0]
    def project(e):
        e = e - h_o * (np.vdot(h_o, e) / norm)
        return e
    z = project(independent - h_o)
    u = project(own - independent)
    w_alg = project(h_t - own)
    z2 = float(np.vdot(z, z).real)
    result.update(z2=z2, zu2=2 * float(np.vdot(z, u).real), u2=float(np.vdot(u, u).real),
                  zw2=2 * float(np.vdot(z, w_alg).real), w2=float(np.vdot(w_alg, w_alg).real),
                  uw2=2 * float(np.vdot(u, w_alg).real),
                  independent_orthogonal_risk=perp_energy(independent, h_o, norm))
    return result


def flat_cfg():
    # Loaded once by run_shard and rebound below; fail if diagnostics run before it.
    if _FLAT_CFG is None:
        raise RuntimeError('flat refit configuration unavailable')
    return _FLAT_CFG


_FLAT_CFG = None


def run_arm(ctx, obs, truth, true_data, arm, genie, cfg, a_true, entropy, frame, L, b0):
    mode, iterations, damping = arm_spec(arm, b0)
    capture = () if mode == 'OFF' else tuple(sorted({9, 19, iterations - 1} |
                ({4} if arm == 'DIR20' and frame < 8 else set())))
    steps = []
    snapshots = {}
    def observer(snapshot):
        index = len(steps)
        steps.append(np.asarray(snapshot['h'], complex).copy())
        if index in capture:
            snapshots[index] = snapshot
    refiner = c1.GenieRefine(genie, 'flat', cfg)
    started = time.perf_counter()
    with c1B_rx.route(ctx.native, mode=mode, damping=damping,
                      capture_steps=capture, observer=None if mode == 'OFF' else observer):
        result = ctx.wrappers._instrumented(
            ctx.native, obs, ctx.system, ctx.code, arm='c1j12_round1', rounds=1,
            iterations=iterations, gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - started
    if len(refiner.snaps) != 1:
        raise RuntimeError(f'expected one genie refit, got {len(refiner.snaps)}')
    arrays = result.arrays
    h_t = np.asarray(arrays['r0_gains'], complex)
    raw_mu = np.asarray(arrays['r0_mu'], complex)
    raw_v = np.asarray(arrays['r0_variance'], float)
    if mode != 'OFF' and len(steps) != iterations:
        raise RuntimeError(f'expected {iterations} observed gain steps, got {len(steps)}')
    diag = c1.reliability(ctx, arrays, truth['coded'])
    diag.update(n_cols=len(h_t), eps_ce1=c1.eps_of(refiner.snaps[0], refiner.snaps[0]['h'], a_true, len(obs['y'])),
                eps_det1=c1.eps_of(refiner.snaps[0], h_t, a_true, len(obs['y'])),
                sec_pilot=float(result.trace['acquisition_seconds']),
                sec_ce=float(sum(e['ce'] for e in result.timing['events'])),
                sec_inference=float(sum(e['inference'] for e in result.timing['events'])))
    h_o, norm = truth_projection(refiner.snaps[0], a_true)
    diag['orthogonal_trajectory'] = [perp_energy(h, h_o, norm) for h in steps]
    diag['orthogonal_risk'] = perp_energy(h_t, h_o, norm)
    diag['trace'] = arrays['r0_inference_trace']
    # Remote evidence only: retain the registered soft states for an exact
    # replay; compact local reports never include these symbol vectors.
    def complex_values(z):
        z = np.asarray(z)
        return dict(real=z.real.tolist(), imag=z.imag.tolist())
    diag['selected_states'] = {str(t + 1): dict(
        h=complex_values(state['h']), mu_raw=complex_values(state['mu_raw']),
        mu_ce=complex_values(state['mu_ce']), v_raw=state['v_raw'].tolist(),
        v_ce=state['v_ce'].tolist()) for t, state in snapshots.items()}
    if not b0 and arm in ('BASE20', 'RAW20', 'DIR20') and frame < 16:
        if mode == 'DIR':
            state = snapshots.get(iterations - 1)
            if state is None:
                raise RuntimeError('missing final DIR export snapshot')
            m_ce = np.asarray(state['mu_ce'], complex)
            v_ce = np.asarray(state['v_ce'], float)
        else:
            state, m_ce, v_ce = None, raw_mu, raw_v
        diag['matched_refit'] = matched_refits(
            ctx, obs, true_data, refiner.snaps[0], h_t, m_ce, v_ce,
            state, arm, a_true, entropy, frame, L)
    if arm == 'DIR20' and frame < 8:
        if not {4, 9, 19}.issubset(snapshots):
            raise RuntimeError('missing DIR probe snapshots')
        diag['probes'] = []
        for t in (5, 10, 20):
            state = snapshots[t - 1]
            for relative in (1e-5, 1e-6):
                for recompute in (False, True):
                    probe = c1B_rx.probe_current_step(state, relative_step=relative,
                                                     recompute_coefficients=recompute)
                    scalars = {key: (float(value) if np.isfinite(value) else None)
                               for key, value in probe.items() if key in ('raw_norm', 'ce_norm', 'ratio')}
                    diag['probes'].append(dict(step=t, relative_step=relative,
                                               recompute_coefficients=recompute,
                                               rank_zero=bool(probe['rank_zero']), **scalars))
    return dict(arm=arm, decoded=result.decoder['decoded'], llr=result.decoder['incoming_llr'],
                iters=int(result.decoder['iterations']), seconds=seconds, triggered=None, diag=diag)


def manifest(args, ctx, cfg_digest):
    names = ('driver_c1B.py', 'c1B_rx.py', 'driver_c1.py', 'driver_c1v2.py',
             'driver.py', 'dpss_rx.py', 'tapchannel.py', 'orders.py')
    sources = {name: base.sha256_file(HERE / name) for name in names}
    sources.update(ctx.sources)
    return dict(spec=SPEC, cfg_sha256=cfg_digest, sources=sources,
                code_g_sha256=ctx.header['code_g_sha256'],
                args=dict(project=str(args.project), native_dir=args.native_dir,
                          baseline_dir=args.baseline_dir, m2_config=str(args.m2_config),
                          nshard=args.nshard, mode=args.mode))


def run_shard(args):
    global _FLAT_CFG
    b0 = args.mode == 'b0'
    arms = ('OFF20', 'DIR20') if b0 else ARMS
    frames = (0,) if b0 else tuple(range(32))
    ctx = c1.load_context(args)
    cfgs, cfg_digest, _ = c1.load_cfgs(args)
    _FLAT_CFG = cfgs['SPg_flat']
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    expected = manifest(args, ctx, cfg_digest)
    config_path = out / f'config_shard{args.shard:03d}.json'
    path = out / f'rows_shard{args.shard:03d}.jsonl'
    receipt_path = out / f'results_shard{args.shard:03d}.json'
    if path.exists() and not config_path.exists():
        raise ValueError('resume refused: rows exist without source/config manifest')
    if config_path.exists():
        if json.loads(config_path.read_text()) != expected:
            raise ValueError('resume refused: source/config manifest mismatch')
    else:
        config_path.write_text(json.dumps(expected, indent=1, allow_nan=False) + '\n')
    completed = {}
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            key = (row['cell'] - 1, row['frame'], row['arm'])
            if key in completed:
                raise ValueError(f'duplicate saved row: {key}')
            completed[key] = row
    assigned = [(ci, frame) for ci in range(len(CELLS)) for frame in frames
                if (ci * len(frames) + frame) % args.nshard == args.shard]
    required = {(ci, frame, arm) for ci, frame in assigned for arm in arms}
    if set(completed) - required:
        raise ValueError('saved rows outside assigned registered scope')
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if (receipt.get('manifest_sha256') != base.sha256_file(config_path)
                or receipt.get('rows_sha256') != base.sha256_file(path)
                or set(completed) != required):
            raise ValueError('resume refused: completed shard receipt differs')
        return
    started = time.perf_counter()
    with path.open('a') as stream:
        for ci, frame in assigned:
            snr, rho, L = CELLS[ci]
            pending = [arm for arm in arms if (ci, frame, arm) not in completed]
            if not pending:
                continue
            paths = c1.draw_c1_paths(ENTROPY, frame, L)
            H = c1.c1_physical_h(ctx, paths)
            a_true = c1.tap_sequences(paths, int(ctx.system.N_total))
            msg = c1.c1_message(ctx, ENTROPY, frame, rho)
            raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
            raw = base.cluster_at_snr(raw_base, snr)
            obs = base.observe(raw, rho, snr)
            true_data = np.asarray(raw['data'], complex) / np.sqrt(2. * (1. - rho))
            truth = base.truth_from_raw(raw, diag_base)
            head = dict(fp_head(paths, truth, rho, snr, frame, L, obs), cell=ci + 1)
            for arm in pending:
                call_start = time.perf_counter()
                try:
                    result = run_arm(ctx, obs, truth, true_data, arm, sorted(a_true), _FLAT_CFG,
                                     a_true, ENTROPY, frame, L, b0)
                    row = dict(head, arm=arm, status='ok', **base.score(ctx, result, truth), **result['diag'])
                except Exception as exc:
                    row = dict(head, arm=arm, status='error', error=repr(exc),
                               traceback=traceback.format_exc()[-3000:],
                               seconds=time.perf_counter() - call_start)
                base.append_rows(stream, [row])
                stream.flush()
                completed[(ci, frame, arm)] = row
                print(f'B {args.mode} cell={ci + 1} frame={frame} arm={arm} {row["status"]}', flush=True)
    if set(completed) != required:
        raise RuntimeError('shard incomplete')
    receipt = dict(schema=SPEC['schema'], mode=args.mode, shard=args.shard, nshard=args.nshard,
                   rows=len(completed), errors=sum(r['status'] != 'ok' for r in completed.values()),
                   rows_sha256=base.sha256_file(path), manifest_sha256=base.sha256_file(config_path),
                   wall_seconds=time.perf_counter() - started)
    receipt_path.write_text(json.dumps(receipt, indent=1, allow_nan=False) + '\n')


def merge(args):
    out = args.out.resolve()
    receipts = [json.loads(p.read_text()) for p in sorted(out.glob('results_shard*.json'))]
    if not receipts:
        raise FileNotFoundError('no shard receipts')
    nshard = receipts[0]['nshard']
    if len(receipts) != nshard or sorted(x['shard'] for x in receipts) != list(range(nshard)):
        raise ValueError('incomplete shards')
    manifests = []
    rows = {}
    for receipt in receipts:
        shard = receipt['shard']
        cp = out / f'config_shard{shard:03d}.json'
        rp = out / f'rows_shard{shard:03d}.jsonl'
        if base.sha256_file(cp) != receipt['manifest_sha256'] or base.sha256_file(rp) != receipt['rows_sha256']:
            raise ValueError(f'shard {shard} hash mismatch')
        manifests.append(json.loads(cp.read_text()))
        for line in rp.read_text().splitlines():
            row = json.loads(line)
            key = (row['cell'], row['frame'], row['arm'])
            if key in rows:
                raise ValueError(f'duplicate row {key}')
            rows[key] = row
    first = manifests[0]
    for other in manifests[1:]:
        a, b = dict(first), dict(other)
        if a != b:
            raise ValueError('shard manifests differ')
    mode = first['args']['mode']
    arms = ('OFF20', 'DIR20') if mode == 'b0' else ARMS
    frames = (0,) if mode == 'b0' else range(32)
    expected = {(ci + 1, f, arm) for ci in range(6) for f in frames for arm in arms}
    if set(rows) != expected:
        raise ValueError(f'row allocation mismatch: {len(rows)} vs {len(expected)}')
    for ci in range(1, 7):
        for f in frames:
            part = [rows[ci, f, arm] for arm in arms]
            fp = tuple(part[0][k] for k in ('physical_gains_sha256', 'info_sha256', 'noise_sha256',
                                           'observation_y_sha256', 'observation_pilot_sha256',
                                           'observation_sigma2'))
            if any(tuple(r[k] for k in ('physical_gains_sha256', 'info_sha256', 'noise_sha256',
                                        'observation_y_sha256', 'observation_pilot_sha256',
                                        'observation_sigma2')) != fp for r in part[1:]):
                raise ValueError(f'paired observation mismatch at cell {ci}, frame {f}')
    for f in frames:
        common = {(rows[ci, f, arms[0]]['info_sha256'], rows[ci, f, arms[0]]['noise_sha256'])
                  for ci in range(1, 7)}
        if len(common) != 1:
            raise ValueError(f'cross-cell message/noise pairing mismatch at frame {f}')
        for left, right in ((2, 3),):
            a, b = rows[left, f, arms[0]], rows[right, f, arms[0]]
            if (a['physical_gains_sha256'] != b['physical_gains_sha256']
                    or a['channel_seed'] != b['channel_seed']):
                raise ValueError(f'cross-rho channel pairing mismatch at frame {f}')
    summary = []
    for ci in range(1, 7):
        for arm in arms:
            sample = [rows[ci, f, arm] for f in frames]
            ok = [r for r in sample if r['status'] == 'ok']
            summary.append(dict(cell=ci, arm=arm, rows=len(sample), errors=len(sample) - len(ok),
                                mean_seconds=float(np.mean([r['seconds'] for r in sample])),
                                fer=float(np.mean([r['info_errors'] > 0 for r in ok])) if len(ok) == len(sample) else None,
                                matched_failures=sum(r.get('matched_refit', {}).get('status') == 'matching_failure' for r in ok)))
    result = dict(schema=SPEC['schema'], mode=mode, n_rows=len(rows), n_error_rows=sum(r['status'] != 'ok' for r in rows.values()),
                  manifest=first, shard_receipts=receipts, summary=summary)
    target = out / 'results.json'
    if target.exists() and json.loads(target.read_text()) != result:
        raise ValueError('merge refused: existing result differs')
    target.write_text(json.dumps(result, indent=1, allow_nan=False) + '\n')


def main(argv=None):
    args = parse_args(argv)
    if args.mode == 'merge':
        merge(args)
    else:
        run_shard(args)


if __name__ == '__main__':
    main()
