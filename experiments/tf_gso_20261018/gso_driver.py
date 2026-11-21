#!/usr/bin/env python
"""GSO driver (task 10-18-gamma-support-only; PROTOCOL.md = design.md + execution facts).

Six arms on the E-3c keys.  They share the E-3 observation, stage 1, round 1, soft-mean dictionary and stage-2 candidate set (the frozen E-3 ``process_key``
arithmetic) and differ ONLY in (i) the Gamma_var of the stage-2 SBL and (ii) the gain estimator on the atoms that SBL selects (E-3 ``select_output``):

  arm     Gamma_var in SBL            gains
  D-sbl   sum(v) I                    SBL posterior mean          (= E-3 L-diag)
  C-sbl   full projected Gamma(v)     SBL posterior mean          (= E-3 L-cov)
  C-ls0   full Gamma(v) (support)     (Bbar^H Bbar + sigma2 I)^-1 Bbar^H Y on the selected atoms, no Gamma
  D-ls0   sum(v) I (support)          same
  Z-sbl   0                           SBL posterior mean
  Z-ls0   0 (support)                 same
LS0 gains = frozen E-1 kernel ``_system(Y, xt_soft, v = 0, paths, c1, c2, ridge = sigma2, gamma_mode = 'full')``, return index 3.  Round 2 = E-3's
``detect_decode`` (scalar_joint gain_mode fixed, prior = round-1 check, then LDPC).  The three SBL runs are shared by the -sbl / -ls0 arm pairs.

Modes: run [--smoke] | gate | gate-merge.   Nothing frozen is edited; no output is overwritten or resumed (use a new output directory).
"""
from __future__ import annotations
import time
IMPORT_START = time.perf_counter()
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gso_lib as lib  # noqa: E402  (also puts the frozen E-3 / E-3b code and the frozen math modules on sys.path)
import e3_driver as e3d  # noqa: E402  (frozen E-3 driver, read-only import: P1 context, observation, detector / decoder wrappers)
from geometry_reopen_variant import Path as GPath, _system  # noqa: E402  (frozen E-1 variant kernel, read-only)

sbl, crb, gd, p1ctx = e3d.sbl, e3d.crb, e3d.gd, e3d.p1ctx

ARMS = ('D-sbl', 'C-sbl', 'C-ls0', 'D-ls0', 'Z-sbl', 'Z-ls0')
KINDS = ('D', 'C', 'Z')
LS0_TOL = 1e-10                                          # LS0 vs independent numpy solve (relative), G2 and aggregation
THREAD_ENV = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
COST_CAP_SECONDS = 6 * 3600.0


def array_sha(a):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def arm_kind(arm):
    return arm.split('-')[0]


def arm_gain(arm):
    return arm.split('-')[1]


# ----------------------------------------------------------------------------- LS0 gains and the independent check
def ls0_gains(Y, xt, delays, dopplers, c1, c2, sigma2):
    """LS0 gains: the frozen kernel with v = 0 and ridge = sigma2; returns (h, Q).  With v = 0 its gamma is all zeros, so Q = Bbar^H Bbar + sigma2 I and
    h = Q^-1 Bbar^H Y."""
    paths = [GPath(int(l), float(nu)) for l, nu in zip(delays, dopplers)]
    _, Q, _, h, _, gamma = _system(Y, xt, np.zeros(len(Y)), paths, c1, c2, float(sigma2), 'full')
    if np.any(gamma != 0):
        raise AssertionError('LS0 must not contain Gamma: _system returned a nonzero gamma for v = 0')
    return h, Q


def ls0_numpy(B, Y, sigma2):
    """Independent numpy solve of (B^H B + sigma2 I) h = B^H Y (LU, not the kernel's Cholesky) from the SBL dictionary columns."""
    m = B.shape[1]
    return np.linalg.solve(B.conj().T @ B + sigma2 * np.eye(m), B.conj().T @ np.asarray(Y, dtype=np.complex128))


def rel_err(a, b):
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))


# ----------------------------------------------------------------------------- the per-key pipeline
def process_key(ctx, cache, grid, obs, truth, meta, clock=None, zero_v=False):
    """One row.  Stage 1, round 1 and the shared candidate set are the E-3 ``process_key`` lines verbatim.  ``zero_v`` (gate G2 only) sets v := 0 after the
    round-1 moments, which makes every Gamma_var identically zero."""
    from messages import moments
    from physical import daft
    t_all = time.perf_counter()
    clock = clock if clock is not None else {}
    clock['phase'] = 'shared stage1/round1'
    s = ctx.system
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    pd = 1 - s.rho
    sigma2 = float(obs['sigma2'])
    delays_g, nus_g = grid
    tp = e3d.truth_paths(truth)
    true_delays = set(tp['delays'])
    sec = {}
    Y = daft(obs['y'], c1, c2, True)
    # ---- stage 1: pilot-only SBL (as E-3)
    t = time.perf_counter()
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    sec['stage1_screen'] = time.perf_counter() - t
    t = time.perf_counter()
    r1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (sigma2 + pd), Gamma=None)
    g1_idx, g1_mu, g1_e = sbl.select_output(cand1[r1['idx']], r1['mu'])
    sec['stage1_sbl'] = time.perf_counter() - t
    ch1 = e3d.make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    # ---- round 1 (as E-3)
    det1, dec1, t_det, t_dec = e3d.detect_decode(ctx, obs, ch1, None)
    sec['round1_detect'], sec['round1_decode'] = t_det, t_dec
    mu_d, v, _ = moments(np.clip(dec1['raw_app'], -20, 20), pd)
    if zero_v:
        v = np.zeros_like(v)
    check = np.clip(dec1['raw_check_extrinsic'], -20, 20)
    err1 = gd.score(ctx, dec1['decoded'], truth)
    # ---- stage-2 shared candidate set (as E-3)
    t = time.perf_counter()
    xt_soft = e3d.self_xt(obs['pilot'] + mu_d, c1, c2)
    Bs = sbl.columns(xt_soft, delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(x) for x in delays_g[g1_idx]), delays_g)
    cd, cn = delays_g[cand2], nus_g[cand2]
    Bc = Bs[:, cand2]
    sec['stage2_screen'] = time.perf_counter() - t
    mean_v = float(np.mean(v))
    beta0_soft = 1.0 / (sigma2 + mean_v)
    row = dict(meta, sigma2=sigma2, zero_v=bool(zero_v),
               truth=dict(delays=tp['delays'], dopplers=tp['dopplers'], gains=[[float(g.real), float(g.imag)] for g in tp['gains']]),
               stage1=dict(n_candidates=int(len(cand1)), iterations=r1['iterations'], converged=r1['converged'], n_final=r1['n_final'], beta=r1['beta'],
                           jitter_events=r1['jitter_events'], atoms=e3d.atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                           nmse=float(crb.channel_nmse(dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu), tp, n))),
               round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])), decoded_sha256=gd.bits_sha(dec1['decoded']),
                           ldpc_iters=int(dec1['iterations'])),
               mean_v=mean_v, sum_v=float(v.sum()), n_candidates_stage2=int(len(cand2)),
               kept_delays_stage1=int(len(set(int(x) for x in delays_g[g1_idx]))), variants={})
    row['input_sha256'] = {k: array_sha(a) for k, a in dict(y=obs['y'], pilot=obs['pilot'], soft_mean=mu_d, app_v=v).items()}
    row['rng_domain'] = str(p1ctx.p1_driver.DOMAIN)
    row['rng_entropy'] = p1ctx.p1_driver.ENTROPY_HEX
    row['pairing'] = dict(noise_sha256=truth['noise_sha256'], physical_gains_sha256=truth['physical_gains_sha256'],
                          coded_sha256=array_sha(truth['coded']), info_sha256=array_sha(truth['info']))
    runs = {}

    def sbl_run(kind):
        """The stage-2 SBL of one Gamma_var, run once per key and shared by the kind-sbl / kind-ls0 arms."""
        if kind in runs:
            return runs[kind]
        clock['phase'] = f'{kind}: Gamma'
        t0 = time.perf_counter()
        if kind == 'D':
            G = float(v.sum())                              # E-3 L-diag
        elif kind == 'C':
            G = sbl.gamma_full(cd, cn, v, c1)               # E-3 L-cov
            row['gamma_diag_rel_err'] = (float(np.max(np.abs(np.diag(G).real - v.sum()) / v.sum())) if v.sum() > 0 else float(np.max(np.abs(np.diag(G)))))
        else:
            G = None                                        # Gamma_var = 0 (standard SBL on the soft-mean dictionary)
        t_g = time.perf_counter() - t0
        clock['phase'] = f'{kind}: SBL'
        t0 = time.perf_counter()
        res = sbl.sbl_em(Bc, Y, beta0=beta0_soft, Gamma=G)
        idx, mu, e = sbl.select_output(cand2[res['idx']], res['mu'])
        runs[kind] = dict(idx=idx, mu=mu, e=e, seconds=time.perf_counter() - t0 + t_g,
                          sbl=dict(max_iter=int(sbl.MAX_ITER), iterations=int(res['iterations']), converged=bool(res['converged']), cap_hit=bool(not res['converged']),
                                   n_start=int(res['n_start']), n_final=int(res['n_final']), beta=float(res['beta']), jitter_events=int(res['jitter_events'])))
        return runs[kind]

    for arm in ARMS:
        kind, gain = arm_kind(arm), arm_gain(arm)
        t_arm = time.perf_counter()
        run = sbl_run(kind)
        idx = run['idx']
        dl, dn0 = delays_g[idx], nus_g[idx]
        t_gain, check_rec = 0.0, None
        if gain == 'sbl':
            gains, energies = run['mu'], run['e']
        else:
            clock['phase'] = f'{arm}: LS0 gains'
            t0 = time.perf_counter()
            gains, Q = ls0_gains(Y, xt_soft, dl, dn0, c1, c2, sigma2)
            t_gain = time.perf_counter() - t0
            energies = np.abs(gains) ** 2
            check_rec = dict(rel_err_numpy=rel_err(gains, ls0_numpy(Bs[:, idx], Y, sigma2)), q_cond=float(np.linalg.cond(Q)))
            if not np.isfinite(check_rec['rel_err_numpy']):
                raise AssertionError(f'{arm}: nonfinite LS0 check')
        clock['phase'] = f'{arm}: round 2'
        ch2 = e3d.make_channel(ctx, n, dl, dn0, gains)
        det2, dec2, t_det, t_dec = e3d.detect_decode(ctx, obs, ch2, check)
        err2 = gd.score(ctx, dec2['decoded'], truth)
        pairs = sbl.codelay_pairs(dl, dn0, n, true_delays)
        out = dict(info_errors=int(err2), fer=int(err2 > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, dec2['decoded'])), decoded_sha256=gd.bits_sha(dec2['decoded']),
                   ldpc_iters=int(dec2['iterations']), gamma_var=kind, gain=gain, n_atoms=int(len(idx)), atoms=e3d.atoms_record(dl, dn0, energies),
                   n_pair=len(pairs), pairs=pairs, nmse=float(crb.channel_nmse(dict(delays=dl, dopplers=dn0, gains=gains), tp, n)),
                   gain_sha256=array_sha(gains), gain_energy=float(np.sum(np.abs(gains) ** 2)), sbl=dict(run['sbl']),
                   seconds=dict(sbl_shared=run['seconds'], gain=t_gain, detect=t_det, decode=t_dec, total=time.perf_counter() - t_arm))
        if check_rec is not None:
            out['ls0_check'] = check_rec
        row['variants'][arm] = out
        clock.setdefault('completed_arms', []).append(arm)
    sec['total'] = time.perf_counter() - t_all
    row['seconds'] = sec
    return row


def compare_baseline(row, old):
    """Bit-exact comparison of the shared stages and of D-sbl / C-sbl with the E-3 L-diag / L-cov rows."""
    checks = dict(stage1=row['stage1']['atoms'] == old['stage1_atoms'], round1=row['round1']['decoded_sha256'] == old['round1_sha'],
                  candidates=row['n_candidates_stage2'] == old['n_cand2'], arms={})
    for a, o in old['variants'].items():
        x = row['variants'][a]
        checks['arms'][a] = dict(sha=x['decoded_sha256'] == o['decoded_sha256'], atoms=x['atoms'] == o['atoms'], errors=x['info_errors'] == o['info_errors'],
                                 fer=x['fer'] == o['fer'], nmse=x['nmse'] == o['nmse'], n_pair=x['n_pair'] == o['n_pair'], n_atoms=x['n_atoms'] == o['n_atoms'],
                                 sbl=all(x['sbl'][k] == o['sbl'][k] for k in ('iterations', 'converged', 'beta', 'n_final')))
    checks['all'] = bool(all(checks[k] for k in ('stage1', 'round1', 'candidates')) and all(all(c.values()) for c in checks['arms'].values()))
    return checks


def strip_timing(value):
    if isinstance(value, dict):
        return {k: strip_timing(x) for k, x in value.items() if not k.endswith('seconds')}
    if isinstance(value, list):
        return [strip_timing(x) for x in value]
    return value


def zero_v_equalities(row):
    """G2: with v == 0 the three SBL runs coincide bit for bit (Z-sbl = D-sbl = C-sbl) and so do the three LS0 solutions; returns {check: bool}."""
    def same(a, b, fields):
        return all(row['variants'][a][f] == row['variants'][b][f] for f in fields)
    sbl_f = ('atoms', 'gain_sha256', 'decoded_sha256', 'nmse', 'info_errors', 'sbl')
    ls0_f = ('atoms', 'gain_sha256', 'decoded_sha256', 'nmse', 'info_errors')
    return {'Z-sbl==D-sbl': same('Z-sbl', 'D-sbl', sbl_f), 'D-sbl==C-sbl': same('D-sbl', 'C-sbl', sbl_f),
            'Z-ls0==D-ls0': same('Z-ls0', 'D-ls0', ls0_f), 'D-ls0==C-ls0': same('D-ls0', 'C-ls0', ls0_f),
            'gamma_zero': bool(row['sum_v'] == 0.0 and row.get('gamma_diag_rel_err', 0.0) == 0.0)}


# ----------------------------------------------------------------------------- run / config
def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=1, allow_nan=False, default=str) + '\n')


def require_env():
    for name in THREAD_ENV:
        if os.environ.get(name) != '1':
            raise RuntimeError(f'{name}=1 required before Python starts')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty')


def make_config(args, ctx, identity, resolutions, keys, manifest, extra=None):
    import scipy
    return dict(args={k: str(x) if isinstance(x, Path) else x for k, x in vars(args).items()}, arms=ARMS, sources_sha256=identity,
                frozen_source_resolution=resolutions, source_md5=ctx.source_md5, ls0_tol=LS0_TOL,
                own_md5={p.name: lib.md5_file(p) for p in lib.own_files() + [HERE / 'PROTOCOL.md'] if p.exists()},
                runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, host=platform.node(),
                             env={k: os.environ.get(k) for k in THREAD_ENV + ('CUDA_VISIBLE_DEVICES',)}),
                hyper_sbl=sbl.HYPER, rng=dict(domain=str(p1ctx.p1_driver.DOMAIN), entropy=p1ctx.p1_driver.ENTROPY_HEX),
                system=dict(rho=float(ctx.system.rho), p_d=float(1 - ctx.system.rho), N=int(ctx.system.N_total), c1=float(ctx.system.c1),
                            c2=float(ctx.system.c2), l_max_cap=int(ctx.system.l_max_cap)),
                e3_manifest=manifest, keys=[list(k) for k in keys], **(extra or {}))


def read_cost(out):
    total = 0.0
    for p in out.glob('cost_shard*.txt'):
        try:
            total += float(p.read_text().strip() or 0)
        except ValueError:
            pass
    return total


def run_mode(args, argv):
    require_env()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    rows_path = out / f'rows_shard{args.shard:03d}.jsonl'
    if cfg_path.exists() or rows_path.exists():
        raise FileExistsError('refuse overwrite/resume: use a new output directory')
    keys = lib.smoke_keys() if args.smoke else lib.main_keys()
    mine = lib.shard_keys(keys, args.shard, args.nshard)
    old, manifest = ({}, None) if args.smoke else lib.load_e3_rows(args.e3_rows, mine)
    ctx = p1ctx.load()
    identity, resolutions = lib.source_identity(ctx)
    cfg = make_config(args, ctx, identity, resolutions, mine, manifest, extra=dict(smoke=bool(args.smoke), cost_cap_seconds=args.cost_cap_seconds))
    write_json(cfg_path, dict(_argv=list(sys.argv), _config=cfg))
    config_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    cost_file = out / f'cost_shard{args.shard:03d}.txt'
    cum, records, stopped = 0.0, [], False
    started = time.perf_counter()
    with rows_path.open('x') as handle:
        for key in mine:
            if args.cost_cap_seconds and read_cost(out) >= args.cost_cap_seconds:
                (out / 'COST_STOP').write_text(f'shard {args.shard} stopped before key {key}: committed cost {read_cost(out):.0f} s >= cap {args.cost_cap_seconds:.0f} s\n')
                stopped = True
                break
            clock = dict(phase='generation')
            t0 = time.perf_counter()
            meta = dict(zip(('scenario', 'rho_permille', 'snr_centi_db', 'frame'), key))
            try:
                sc, rho, snr, frame = key
                base = p1ctx.base(ctx, sc, rho / 1000, frame)
                gen_s = time.perf_counter() - t0
                meta, obs, _, truth = e3d.observe_key(ctx, base[0], base[1], sc, rho, snr, frame, gen_s)
                row = process_key(ctx, cache, grid, obs, truth, meta, clock=clock)
                if args.smoke:
                    row['smoke'] = True
                else:
                    row['baseline_check'] = compare_baseline(row, old[key])
                    if not row['baseline_check']['all']:
                        raise AssertionError(f'E-3 replay mismatch: {row["baseline_check"]}')
            except BaseException as exc:
                failed = dict(meta, status='error', error=repr(exc), trace=traceback.format_exc()[-4000:], phase=clock, elapsed_seconds=time.perf_counter() - t0,
                              config_sha256=config_sha, _argv=list(sys.argv), _config=dict(config_file=cfg_path.name, config_sha256=config_sha))
                e3d.write_row(handle, failed)
                raise
            row.update(status='ok', config_sha256=config_sha, _argv=list(sys.argv), _config=dict(config_file=cfg_path.name, config_sha256=config_sha),
                       elapsed_seconds=time.perf_counter() - t0)
            e3d.write_row(handle, row)
            cum += row['elapsed_seconds']
            tmp = cost_file.with_suffix('.tmp')
            tmp.write_text(f'{cum:.3f}\n')
            os.replace(tmp, cost_file)
            records.append(dict(key=list(key), elapsed_seconds=row['elapsed_seconds']))
            print(json.dumps(dict(key=key, status='ok', seconds=row['elapsed_seconds'])), flush=True)
    write_json(out / f'completed_shard{args.shard:03d}.json', dict(keys=records, config_sha256=config_sha, cost_stopped=stopped, committed_cost_seconds=cum,
                                                                    wall_seconds=time.perf_counter() - started))
    print(f'shard {args.shard}/{args.nshard} {"COST-STOPPED" if stopped else "done"}: {len(records)} keys, committed cost {cum:.0f} s', flush=True)


# ----------------------------------------------------------------------------- gates
def gate_mode(args, argv):
    """Per shard: G1 + G3 on its gate keys (process twice, E-3 replay, exact repeat), G2 on its zero-v keys.  Items are dealt out round-robin."""
    require_env()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    rows_path = out / f'rows_shard{args.shard:03d}.jsonl'
    if cfg_path.exists() or rows_path.exists():
        raise FileExistsError('refuse overwrite/resume: use a new output directory')
    gate = lib.gate_keys()
    zero = set(lib.zero_v_keys())
    items = [('G13', k) for k in gate] + [('G2z', k) for k in gate if k in zero]
    mine = items[args.shard::args.nshard]
    old, manifest = lib.load_e3_rows(args.e3_rows, [k for kind, k in mine if kind == 'G13'])
    ctx = p1ctx.load()
    identity, resolutions = lib.source_identity(ctx)
    write_json(cfg_path, dict(_argv=list(sys.argv), _config=make_config(args, ctx, identity, resolutions, [k for _, k in mine], manifest,
                                                                       extra=dict(gate=True, items=[[kind, list(k)] for kind, k in mine]))))
    config_sha = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    recs, started = [], time.perf_counter()
    with rows_path.open('x') as handle:
        for kind, key in mine:
            rec = dict(kind=kind, key=list(key))
            clock = dict(phase='generation')
            t0 = time.perf_counter()
            try:
                sc, rho, snr, frame = key
                base = p1ctx.base(ctx, sc, rho / 1000, frame)
                meta, obs, _, truth = e3d.observe_key(ctx, base[0], base[1], sc, rho, snr, frame, time.perf_counter() - t0)
                zv = kind == 'G2z'
                row = process_key(ctx, cache, grid, obs, truth, dict(meta), clock=clock, zero_v=zv)
                rec['ls0_rel_err'] = {a: row['variants'][a]['ls0_check']['rel_err_numpy'] for a in ARMS if a.endswith('ls0')}
                rec['ls0_q_cond'] = {a: row['variants'][a]['ls0_check']['q_cond'] for a in ARMS if a.endswith('ls0')}
                rec['cap_hit'] = {a: row['variants'][a]['sbl']['cap_hit'] for a in ARMS}
                if zv:
                    rec['zero_v'] = zero_v_equalities(row)
                else:
                    rec['baseline'] = compare_baseline(row, old[key])
                    row['baseline_check'] = rec['baseline']
                    clock['phase'] = 'G3 repeat'
                    repeat = process_key(ctx, cache, grid, obs, truth, dict(meta), clock=clock)
                    diff = lib.deep_equal(strip_timing(row), strip_timing(dict(repeat, baseline_check=row['baseline_check'])))
                    rec['g3'] = dict(identical=not diff, mismatch=[str(d) for d in diff[:5]])
                row.update(status='ok', config_sha256=config_sha, gate_kind=kind)
                e3d.write_row(handle, row)
            except BaseException as exc:
                rec.update(error=repr(exc), trace=traceback.format_exc()[-3000:], phase=clock)
            rec['elapsed_seconds'] = time.perf_counter() - t0
            recs.append(rec)
            print(f'[{time.perf_counter() - started:8.1f}s] {kind} {key} ' + ('ERROR ' + rec['error'] if 'error' in rec else 'done'), flush=True)
    write_json(out / f'gate_shard{args.shard:03d}.json', dict(records=recs, config_sha256=config_sha, sources_sha256=identity))


def gate_merge(args):
    recs, sources = [], set()
    for p in sorted(args.out.glob('gate_shard*.json')):
        d = json.loads(p.read_text())
        recs += d['records']
        sources.add(json.dumps(d['sources_sha256'], sort_keys=True))
    errors = [dict(kind=r['kind'], key=r['key'], error=r['error']) for r in recs if 'error' in r]
    ok = [r for r in recs if 'error' not in r]
    g13 = [r for r in ok if r['kind'] == 'G13']
    g2z = [r for r in ok if r['kind'] == 'G2z']
    gates = dict(item_errors=errors)
    gates['G1'] = dict(keys=len(g13), replay_exact=sum(bool(r['baseline']['all']) for r in g13),
                       failing=[r['key'] for r in g13 if not r['baseline']['all']][:5])
    gates['G1']['pass_'] = bool(len(g13) == lib.GATE_N and gates['G1']['replay_exact'] == len(g13))
    flags = sorted(g2z[0]['zero_v']) if g2z else []
    ls0_all = [e for r in ok for e in r['ls0_rel_err'].values()]
    gates['G2'] = dict(zero_v_keys=len(g2z), zero_v_checks={f: sum(bool(r['zero_v'][f]) for r in g2z) for f in flags},
                       ls0_keys=len(ok), ls0_arms=len(ls0_all), ls0_worst_rel_err=max(ls0_all or [1.0]), ls0_tol=LS0_TOL,
                       ls0_worst_q_cond=max([c for r in ok for c in r['ls0_q_cond'].values()] or [0.0]))
    gates['G2']['pass_'] = bool(len(g2z) == len(lib.zero_v_keys()) and all(v == len(g2z) for v in gates['G2']['zero_v_checks'].values())
                                and gates['G2']['ls0_worst_rel_err'] <= LS0_TOL and len(ls0_all) == 3 * len(ok))
    gates['G3'] = dict(keys=len(g13), identical=sum(bool(r['g3']['identical']) for r in g13), mismatches=[r['g3']['mismatch'] for r in g13 if not r['g3']['identical']][:3])
    gates['G3']['pass_'] = bool(len(g13) == lib.GATE_N and gates['G3']['identical'] == len(g13))
    cap = [a for r in ok for a, h in r['cap_hit'].items() if h]
    gates['cap_hit_arm_keys_in_gate'] = len(cap)
    eng = sum(r['elapsed_seconds'] for r in recs)
    smoke_rows = []
    if args.smoke_dir is not None:
        for p in sorted(Path(args.smoke_dir).glob('rows_shard*.jsonl')):
            smoke_rows += [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    sm = [r for r in smoke_rows if r.get('status') == 'ok']
    per_key = float(np.mean([r['elapsed_seconds'] for r in sm])) if sm else None
    contention = 1.3
    gates['G4'] = dict(smoke_keys=len(sm), smoke_errors=len(smoke_rows) - len(sm), seconds_per_key=per_key,
                       projected_main_core_hours=(per_key * lib.N_KEYS / 3600 if per_key else None),
                       projected_with_contention_core_hours=(per_key * lib.N_KEYS * contention / 3600 if per_key else None), contention_factor=contention,
                       cap_core_hours=COST_CAP_SECONDS / 3600.0, note='estimate = mean elapsed per smoke key (concurrent shards) x 1200 x 1.3; pass if <= cap')
    gates['G4']['pass_'] = bool(per_key and len(sm) >= lib.SMOKE_N and gates['G4']['smoke_errors'] == 0
                                and gates['G4']['projected_with_contention_core_hours'] <= gates['G4']['cap_core_hours'])
    eng += sum(r['elapsed_seconds'] for r in sm)
    gates['engineering_core_seconds'] = eng
    gates['engineering_core_hours'] = eng / 3600
    unit_names = ('test_gso.json', 'test_gso_agg.json')
    unit = {n: (json.loads((args.unit_dir / n).read_text()) if (args.unit_dir / n).exists() else None) for n in unit_names}
    unit_sources = {json.dumps(u['sources_sha256'], sort_keys=True) for u in unit.values() if u}
    gates['unit'] = dict(dir=str(args.unit_dir), present=[n for n, u in unit.items() if u], pass_=bool(all(u and u.get('all_pass') for u in unit.values())))
    all_sources = sources | unit_sources
    smoke_sources = set()
    if args.smoke_dir is not None:
        for p in sorted(Path(args.smoke_dir).glob('config_shard*.json')):
            smoke_sources.add(json.dumps(json.loads(p.read_text())['_config']['sources_sha256'], sort_keys=True))
    all_sources |= smoke_sources
    gates['sources_identical'] = bool(len(all_sources) == 1 and len(sources) == 1 and len(unit_sources) == 1 and len(smoke_sources) == 1)
    gates['sources_sha256'] = json.loads(next(iter(all_sources))) if gates['sources_identical'] else None
    gates['all_pass'] = bool(not errors and all(gates[k]['pass_'] for k in ('G1', 'G2', 'G3', 'G4', 'unit')) and gates['sources_identical'])
    write_json(args.out / 'gates.json', gates)
    print(json.dumps({k: v for k, v in gates.items() if k != 'sources_sha256'}, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('run', 'gate', 'gate-merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--e3-rows', type=Path, default=lib.E3_ROWS, help='E-3 main rows (rows_shard*.jsonl.gz + REMOTE_ROWS_MD5.txt)')
    p.add_argument('--smoke', action='store_true', help='run: the 8 smoke keys (frames >= 8500); counts only, never analysed')
    p.add_argument('--smoke-dir', type=Path, default=None, help='gate-merge: smoke output directory (G4 timing)')
    p.add_argument('--unit-dir', type=Path, default=HERE / 'out' / 'unit', help='gate-merge: directory with test_gso.json and test_gso_agg.json')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--cost-cap-seconds', type=float, default=0.0, help='run: stop starting keys once the committed cost of all shards reaches this (0 = off)')
    a = p.parse_args(argv)
    if not 1 <= a.nshard <= 16 or not 0 <= a.shard < a.nshard:
        p.error('invalid shard / nshard (at most 16 processes)')
    if a.smoke and a.mode != 'run':
        p.error('--smoke requires --mode run')
    return a


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'run':
        run_mode(A, sys.argv[1:])
    elif A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    else:
        gate_merge(A)
