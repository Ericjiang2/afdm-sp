#!/usr/bin/env python
"""E-3b driver (task 10-17-offgrid-sbl-e3b; PROTOCOL.md = design.md + execution facts).

Per key (U/G x rho .3 x SNR 6..11 dB x frames 4000..4199): stage 1, round 1 and the stage-2 SBL of the four E-3 variants are the E-3 pipeline bit for bit
(sbl_rx.py and the helpers of e3_driver.py imported read-only; process_key below is the E-3 flow with the continuous refinement inserted between
select_output and the round-2 detector).  Per variant:  SBL on the shared candidate set -> output atoms (<= 24, descending energy) -> continuous Doppler
refinement (offgrid_refine.refine, objective geometry_reopen_variant._system) -> gains = _system's h -> round 2 -> LDPC -> unconditional FER.
  hard-off  : xt from the hard-decision remodulation, v = 0                      genie-off : xt from the true data, v = 0
  diag-off  : xt from the soft mean, v = v, gamma_mode 'diag'                    cov-off   : xt from the soft mean, v = v, gamma_mode 'full'
On-grid results (L-hard / L-diag / L-cov / L-genie) are taken from the E-3 rows for the pairing, not re-run (the rows keep the on-grid atoms, so the
SBL stage is compared with E-3 key by key; gate G1 additionally compares the on-grid decoded sha).

Modes: gate-prep / gate / gate-merge (G1-G4) | run (main; --smoke for the 16-key smoke on frames >= 8300) | smoke-counts | cost-check (launcher helper).
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3b_lib as lib  # noqa: E402  (also puts E-3 dir and the frozen modules on sys.path)

import e3_driver as e3d  # noqa: E402  (frozen E-3 driver: imported read-only)
import offgrid_refine as ref  # noqa: E402
import sbl_rx as sbl  # noqa: E402

gd, crb, p1ctx = e3d.gd, e3d.crb, e3d.p1ctx
OFF, ONGRID = lib.OFF, lib.ONGRID
G4_LIMIT_CORE_H = 30.0
CONTENTION = 1.3          # design 4: smoke-load -> 24-process load factor
COST_LIMIT = 30.0


# ----------------------------------------------------------------------------- provenance
def check_frozen_md5(ctx):
    """Every file of SOURCE_MD5.txt must have the recorded md5 (the loaded module of the same stem if there is one, else the file on disk)."""
    results, bad = {}, []
    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        digest, rel = line.split()
        path = lib.EXPERIMENTS / rel
        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
        if loaded is not None:
            actual, how = loaded, 'loaded-module'
        elif path.exists():
            actual, how = lib.md5_file(path), 'file'
        else:
            actual, how = None, 'absent'
        results[rel] = dict(expected=digest, actual=actual, via=how, status='unchecked' if actual is None else ('ok' if actual == digest else 'MISMATCH'))
        if results[rel]['status'] == 'MISMATCH':
            bad.append(rel)
    if bad:
        raise RuntimeError(f'frozen source md5 mismatch: {bad}')
    return results


def own_md5():
    names = ('e3b_lib.py', 'offgrid_refine.py', 'e3b_driver.py', 'e3b_agg.py', 'launch_e3b.sh', 'PROTOCOL.md', 'SOURCE_MD5.txt')
    return {n: lib.md5_file(HERE / n) for n in names if (HERE / n).exists()}


def write_config(out, shard, argv, args, ctx, extra=None):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    import scipy
    cfg = dict(vars(args), out=str(args.out), variants=OFF, hyper_sbl=sbl.HYPER, hyper_refine=ref.HYPER,
               receiver='E-3 receiver unchanged (sbl_rx.py) + continuous Doppler refinement on the SBL output atoms (offgrid_refine.py); detection '
                        'scalar_joint(iterations=20, damping=.3, gain_mode=fixed), LDPC decoder_messages(maxiter=50)',
               family_P1=dict(entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN),
               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment,
               runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, host=platform.node(),
                            threads={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS')}), **(extra or {}))
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- the pipeline for one key
def process_key(ctx, cache, grid, obs, data_true_af, truth, meta, ongrid_check=False):
    """One row.  Stage 1, round 1, the shared candidate set and the four stage-2 SBL runs are the E-3 process_key lines; the refinement is new.
    ``ongrid_check`` (gate / smoke only) additionally runs round 2 on the unrefined SBL atoms (E-3's on-grid result) and records it; its time is
    excluded from every ``total``."""
    from messages import moments
    from physical import daft
    t_all = time.perf_counter()
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
    check = np.clip(dec1['raw_check_extrinsic'], -20, 20)
    err1 = gd.score(ctx, dec1['decoded'], truth)
    # ---- stage 2 shared candidate set (as E-3)
    t = time.perf_counter()
    xt_soft = e3d.self_xt(obs['pilot'] + mu_d, c1, c2)
    Bs = sbl.columns(xt_soft, delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(x) for x in delays_g[g1_idx]), delays_g)
    cd, cn = delays_g[cand2], nus_g[cand2]
    sec['stage2_screen'] = time.perf_counter() - t
    mean_v = float(np.mean(v))
    beta0_soft = 1.0 / (sigma2 + mean_v)
    row = dict(meta, sigma2=sigma2,
               truth=dict(delays=tp['delays'], dopplers=tp['dopplers'], gains=[[float(g.real), float(g.imag)] for g in tp['gains']]),
               stage1=dict(n_candidates=int(len(cand1)), iterations=r1['iterations'], converged=r1['converged'], n_final=r1['n_final'], beta=r1['beta'],
                           jitter_events=r1['jitter_events'], atoms=e3d.atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                           nmse=float(crb.channel_nmse(dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu), tp, n))),
               round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])), decoded_sha256=gd.bits_sha(dec1['decoded']),
                           ldpc_iters=int(dec1['iterations'])),
               mean_v=mean_v, n_candidates_stage2=int(len(cand2)), kept_delays_stage1=int(len(set(int(x) for x in delays_g[g1_idx]))), variants={})
    gamma = None
    zeros = np.zeros(n)
    excluded = 0.
    for name in OFF:
        kind = ONGRID[name]
        t_v = time.perf_counter()
        vsec = {}
        t = time.perf_counter()
        if kind == 'L-hard':
            xt = e3d.self_xt(obs['pilot'] + sbl.hard_decision(mu_d, pd), c1, c2)
            B, G, beta0, v_m, g_m = sbl.columns(xt, cd, cn, c1, c2), None, beta0_soft, zeros, 'full'
        elif kind == 'L-genie':
            xt = e3d.self_xt(obs['pilot'] + data_true_af, c1, c2)
            B, G, beta0, v_m, g_m = sbl.columns(xt, cd, cn, c1, c2), None, 1.0 / sigma2, zeros, 'full'
        else:
            xt, B, beta0, v_m = xt_soft, Bs[:, cand2], beta0_soft, v
            if kind == 'L-diag':
                G, g_m = float(v.sum()), 'diag'
            else:
                if gamma is None:
                    t_g = time.perf_counter()
                    gamma = sbl.gamma_full(cd, cn, v, c1)
                    row['gamma_diag_rel_err'] = float(np.max(np.abs(np.diag(gamma).real - v.sum()) / v.sum()))
                    row['gamma_seconds'] = time.perf_counter() - t_g
                G, g_m = gamma, 'full'
        vsec['columns'] = time.perf_counter() - t
        t = time.perf_counter()
        res = sbl.sbl_em(B, Y, beta0=beta0, Gamma=G)
        idx, mu, e = sbl.select_output(cand2[res['idx']], res['mu'])
        vsec['sbl'] = time.perf_counter() - t
        dl, dn0 = delays_g[idx], nus_g[idx]
        t = time.perf_counter()
        rf = ref.refine(Y, xt, v_m, dl, dn0, c1, c2, sigma2, g_m)
        vsec['refine'] = time.perf_counter() - t
        ch2 = e3d.make_channel(ctx, n, dl, rf['dopplers'], rf['gains'])
        det2, dec2, t_det, t_dec = e3d.detect_decode(ctx, obs, ch2, check)
        vsec['detect'], vsec['decode'] = t_det, t_dec
        err2 = gd.score(ctx, dec2['decoded'], truth)
        pairs = sbl.codelay_pairs(dl, rf['dopplers'], n, true_delays)
        out = dict(info_errors=int(err2), fer=int(err2 > 0), syndrome=int(ctx.hd.syndrome_weight(ctx, dec2['decoded'])), decoded_sha256=gd.bits_sha(dec2['decoded']),
                   ldpc_iters=int(dec2['iterations']), n_atoms=int(len(idx)), gamma_mode=g_m, atoms_ongrid=e3d.atoms_record(dl, dn0, e),
                   atoms=e3d.atoms_record(dl, rf['dopplers'], np.abs(rf['gains']) ** 2), n_pair=len(pairs), pairs=pairs,
                   nmse=float(crb.channel_nmse(dict(delays=dl, dopplers=rf['dopplers'], gains=rf['gains']), tp, n)),
                   sbl=dict(max_iter=sbl.MAX_ITER, iterations=res['iterations'], converged=res['converged'], n_start=res['n_start'], n_final=res['n_final'],
                            beta=res['beta'], jitter_events=res['jitter_events']),
                   refine={k: val for k, val in rf.items() if k not in ('dopplers', 'gains')})
        if ongrid_check:      # E-3's on-grid round 2 on the unrefined SBL atoms (gate G1 / smoke counts); excluded from the cost
            t_c = time.perf_counter()
            _, decg, _, _ = e3d.detect_decode(ctx, obs, e3d.make_channel(ctx, n, dl, dn0, mu), check)
            errg = gd.score(ctx, decg['decoded'], truth)
            out['ongrid_check'] = dict(info_errors=int(errg), fer=int(errg > 0), decoded_sha256=gd.bits_sha(decg['decoded']))
            excluded += time.perf_counter() - t_c
            vsec['ongrid_check'] = time.perf_counter() - t_c
        vsec['total'] = time.perf_counter() - t_v - vsec.get('ongrid_check', 0.)
        out['seconds'] = vsec
        row['variants'][name] = out
    sec['total'] = time.perf_counter() - t_all - excluded
    row['seconds'] = sec
    return row


def strip_seconds(row):
    r = json.loads(json.dumps(row))
    for k in ('seconds', 'gamma_seconds', 'gen_seconds'):
        r.pop(k, None)
    for v in r.get('variants', {}).values():
        v.pop('seconds', None)
    return r


# ----------------------------------------------------------------------------- run / smoke
def observe(ctx, base, scenario, rho_pm, snr, frame, gen_seconds):
    return e3d.observe_key(ctx, base[0], base[1], scenario, rho_pm, snr, frame, gen_seconds)


def run_keys(ctx, keys, jsonl, smoke, ongrid_check=False, fingerprint=None):
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    done = gd.load_done(jsonl)
    started = time.perf_counter()
    n_rows, base_key, base = 0, None, None
    with jsonl.open('a') as handle:
        for key in keys:
            if key in done:
                continue
            scenario, rho_pm, snr, frame = key
            if base_key != (scenario, rho_pm, frame):
                g0 = time.perf_counter()
                base_key, base = (scenario, rho_pm, frame), p1ctx.base(ctx, scenario, rho_pm / 1000, frame)
                gen_now = time.perf_counter() - g0
            else:
                gen_now = 0.
            meta, obs, data_af, truth = observe(ctx, base, scenario, rho_pm, snr, frame, gen_now)
            if smoke:
                meta['smoke'] = True
            try:
                row = process_key(ctx, cache, grid, obs, data_af, truth, meta, ongrid_check=ongrid_check)
            except Exception as error:  # recorded, never silently dropped
                row = dict(meta, status='error', error=repr(error), trace=traceback.format_exc()[-1500:])
            row.update(fingerprint or {})
            e3d.write_row(handle, row)
            n_rows += 1
            print(f"[{time.perf_counter() - started:8.1f}s] {key} "
                  + (' '.join(f"{v}:{r['info_errors']}/{r['refine']['n_accept']}/{r['n_pair']}" for v, r in row.get('variants', {}).items())
                     if 'variants' in row else row.get('error', '')), flush=True)
    return n_rows, time.perf_counter() - started


def run_mode(args, argv):
    keys = lib.smoke_keys() if args.smoke else lib.main_keys()
    mine = lib.shard_block(keys, args.shard, args.nshard)
    if args.smoke and any(k[3] < lib.SMOKE_FRAME_MIN for k in mine):
        raise ValueError('smoke frames must be >= 8300')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx, extra=dict(smoke_only=bool(args.smoke), n_keys_total=len(keys), n_keys_shard=len(mine)))
    cfg_path = out / f'config_shard{args.shard:03d}.json'
    fingerprint = dict(_argv=list(argv), _config=dict(mode='run', smoke=bool(args.smoke), shard=args.shard, nshard=args.nshard, n_keys_total=len(keys), n_keys_shard=len(mine),
                                                      variants=list(OFF), hyper_sbl=sbl.HYPER, hyper_refine=ref.HYPER, ridge='obs[sigma2]', own_md5=own_md5(),
                                                      config_file=cfg_path.name, config_md5=lib.md5_file(cfg_path)))
    n, secs = run_keys(ctx, mine, out / f'rows_shard{args.shard:03d}.jsonl', args.smoke, ongrid_check=args.smoke, fingerprint=fingerprint)
    print(f'shard {args.shard}/{args.nshard} done: {n} keys in {secs:.1f}s', flush=True)


# ----------------------------------------------------------------------------- cost check (launcher helper)
def projected_core_hours(rows, total_keys):
    """Mean per-key seconds (pipeline total + frame generation) over the good rows, times ``total_keys``, in core-hours; None without rows."""
    good = [r for r in rows if 'variants' in r]
    if not good:
        return None
    return float(np.mean([r['seconds']['total'] + r.get('gen_seconds', 0.) for r in good]) * total_keys / 3600.)


def cost_check(args):
    import glob
    rows = []
    for p in sorted(glob.glob(str(args.out / 'rows_shard*.jsonl'))):
        rows += [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    proj = projected_core_hours(rows, args.total)
    print(json.dumps(dict(rows=len(rows), projected_core_hours=proj, limit=args.limit)))
    return 0 if (proj is None or proj <= args.limit) else 3          # 3 = projection above the limit (any other non-zero exit = the check itself failed)


# ----------------------------------------------------------------------------- gates
def gate_prep(args):
    """Read the E-3 rows of the G1 keys (md5-checked) into out/g1_e3_rows.json."""
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    keys = lib.gate_keys()
    rows, info = lib.load_e3_rows(args.e3_rows, keys, verify=True)
    missing = [k for k in keys if k not in rows]
    if missing:
        raise SystemExit(f'E-3 rows missing for gate keys: {missing[:3]}')
    (out / 'g1_e3_rows.json').write_text(json.dumps(dict(keys=[list(k) for k in keys], rows=[rows[k] for k in keys], manifest=info,
                                                         e3_rows_dir=str(args.e3_rows))) + '\n')
    print(f'gate-prep: {len(keys)} keys; E-3 manifest files checked {info["files"]}, mismatches {len(info["mismatches"])}')


def compare_g1(row, e3):
    """On-grid comparison of an E-3b gate row with the slim E-3 row of the same key (exact)."""
    row = json.loads(json.dumps(row))
    res = dict(stage1_atoms=row['stage1']['atoms'] == e3['stage1_atoms'], round1_sha=row['round1']['decoded_sha256'] == e3['round1_sha'],
               n_cand2=row['n_candidates_stage2'] == e3['n_cand2'], variants={})
    for off, on in ONGRID.items():
        x, y = row['variants'][off], e3['variants'][on]
        res['variants'][off] = dict(atoms=x['atoms_ongrid'] == y['atoms'], sha=x['ongrid_check']['decoded_sha256'] == y['decoded_sha256'],
                                    info_errors=x['ongrid_check']['info_errors'] == y['info_errors'])
    res['all'] = bool(res['stage1_atoms'] and res['round1_sha'] and res['n_cand2'] and all(all(d.values()) for d in res['variants'].values()))
    return res


def real_checks(row):
    """G2 on a real key: monotone value, evaluation cap, bounds / window, gamma structure, no near-singular failure."""
    out = {}
    for name, x in row['variants'].items():
        r = x['refine']
        zero_v = ONGRID[name] in ('L-hard', 'L-genie')
        out[name] = dict(monotone=r['monotone'], recheck=r['value_recheck_equal'], evals_ok=r['max_evals_coord'] <= ref.MAX_EVALS, in_bounds=r['in_bounds'],
                         in_window=r['in_window'],
                         gamma=(r['gamma_abs_max'] == 0.0) if zero_v else (r['gamma_diag_rel_err'] is not None and r['gamma_diag_rel_err'] < 1e-10
                                                                         and (r['gamma_offdiag_abs_max'] == 0.0 if name == 'diag-off' else True)))
    out['all'] = all(all(d.values()) for d in out.values())
    return out


def gate_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    g1 = json.loads((out / 'g1_e3_rows.json').read_text())
    keys = [tuple(k) for k in g1['keys']]
    e3rows = dict(zip(keys, g1['rows']))
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    records = []
    for key in keys[args.shard::args.nshard]:
        scenario, rho_pm, snr, frame = key
        base = p1ctx.base(ctx, scenario, rho_pm / 1000, frame)
        meta, obs, data_af, truth = observe(ctx, base, scenario, rho_pm, snr, frame, 0.)
        r1 = process_key(ctx, cache, grid, obs, data_af, truth, dict(meta), ongrid_check=True)
        r2 = process_key(ctx, cache, grid, obs, data_af, truth, dict(meta), ongrid_check=True)
        diff = lib.deep_equal(strip_seconds(r1), strip_seconds(r2))
        records.append(dict(key=list(key), g1=compare_g1(r1, e3rows[key]), g2=real_checks(r1), g3_identical=not diff, g3_mismatch=diff[:3],
                            n_accept={v: x['refine']['n_accept'] for v, x in r1['variants'].items()},
                            n_coord={v: x['refine']['n_coord'] for v, x in r1['variants'].items()},
                            cond_Q_max={v: x['refine']['cond_Q'] for v, x in r1['variants'].items()},
                            seconds=r1['seconds']['total']))
        print(f'gate key {key}: G1 {records[-1]["g1"]["all"]} G2 {records[-1]["g2"]["all"]} G3 {records[-1]["g3_identical"]}', flush=True)
    (out / f'gate_shard{args.shard:03d}.json').write_text(json.dumps(dict(records=records)) + '\n')


def gate_merge(args):
    out = args.out.resolve()
    recs = []
    for p in sorted(out.glob('gate_shard*.json')):
        recs += json.loads(p.read_text())['records']
    unit_path = args.unit
    unit = json.loads(Path(unit_path).read_text()) if unit_path and Path(unit_path).exists() else None
    gates = dict(n_keys=len(recs))
    gates['G1'] = dict(keys=len(recs), identical=sum(r['g1']['all'] for r in recs), failures=[r['key'] for r in recs if not r['g1']['all']][:5],
                       note='stage-1 atoms, round-1 decoded sha, stage-2 candidate count and, per variant, the on-grid SBL output atoms, the on-grid round-2 decoded sha '
                            'and info-error count equal the E-3 row of the same key')
    gates['G1']['pass_'] = bool(len(recs) == lib.GATE_N and gates['G1']['identical'] == len(recs))
    g2_real = dict(keys=len(recs), ok=sum(r['g2']['all'] for r in recs), failures=[r['key'] for r in recs if not r['g2']['all']][:5],
                   total_coordinates=int(sum(sum(r['n_coord'].values()) for r in recs)), accepted_coordinates=int(sum(sum(r['n_accept'].values()) for r in recs)),
                   cond_Q_max=max([max(r['cond_Q_max'].values()) for r in recs] or [0.]))
    gates['G2'] = dict(real=g2_real, synthetic=None if unit is None else unit.get('G2'))
    gates['G2']['pass_'] = bool(len(recs) == lib.GATE_N and g2_real['ok'] == len(recs) and unit is not None and unit.get('G2', {}).get('pass_'))
    gates['G3'] = dict(real_identical=sum(r['g3_identical'] for r in recs), keys=len(recs), mismatches=[r['g3_mismatch'] for r in recs if not r['g3_identical']][:3],
                       synthetic=None if unit is None else unit.get('G3'))
    gates['G3']['pass_'] = bool(len(recs) == lib.GATE_N and gates['G3']['real_identical'] == len(recs) and unit is not None and unit.get('G3', {}).get('pass_'))
    if args.smoke_dir and Path(args.smoke_dir).exists():
        import glob
        rows = []
        for p in sorted(glob.glob(str(Path(args.smoke_dir) / 'rows_shard*.jsonl'))):
            rows += [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
        good = [r for r in rows if 'variants' in r]
        per_key = float(np.mean([r['seconds']['total'] + r.get('gen_seconds', 0.) for r in good])) if good else None
        raw = None if per_key is None else per_key * lib.N_KEYS / 3600
        gates['G4'] = dict(smoke_rows=len(rows), smoke_good_rows=len(good), mean_seconds_per_key=per_key, core_hours_estimate_raw=raw,
                           core_hours_estimate_contended=None if raw is None else raw * CONTENTION, contention_factor=CONTENTION, limit_core_hours=G4_LIMIT_CORE_H,
                           rule='estimate = mean smoke seconds per key (pipeline + frame generation, on-grid check excluded) x 2400 / 3600; gate uses the x1.3 '
                                'contention-adjusted value (design section 4)')
        gates['G4']['pass_'] = bool(raw is not None and raw * CONTENTION <= G4_LIMIT_CORE_H)
    else:
        gates['G4'] = dict(pass_=False, note='no smoke rows yet')
    gates['all_pass'] = bool(all(gates[k]['pass_'] for k in ('G1', 'G2', 'G3', 'G4')))
    (out / 'gates.json').write_text(json.dumps(gates, indent=1) + '\n')
    print(json.dumps(gates, indent=1))


def smoke_counts(args):
    """Counts only (no interpretation) of the smoke rows -> out/SMOKE_COUNTS.md.  The smoke keys are never part of the analysis."""
    import glob
    rows = []
    for p in sorted(glob.glob(str(args.out / 'rows_shard*.jsonl'))):
        rows += [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    good = [r for r in rows if 'variants' in r]
    errs = [r for r in rows if r.get('status') == 'error']
    L = ['# E-3b smoke counts (counts only; frames >= 8300, never analysed)', '', f'rows {len(rows)}, good {len(good)}, error rows {len(errs)}'
         + ''.join(f"; error: {r.get('error')}" for r in errs[:3]), '']
    if good:
        L += ['| variant | FER events on-grid (re-run) | FER events off-grid | n_pair total | coordinates | accepted | evals | max evals/coordinate | atoms moved / atoms | non-converged SBL |',
              '|---|---|---|---|---|---|---|---|---|---|']
        for o in OFF:
            x = [r['variants'][o] for r in good]
            L.append(f"| {o} | {sum(v['ongrid_check']['fer'] for v in x)} | {sum(v['fer'] for v in x)} | {sum(v['n_pair'] for v in x)} | {sum(v['refine']['n_coord'] for v in x)} | "
                     f"{sum(v['refine']['n_accept'] for v in x)} | {sum(v['refine']['evals'] for v in x)} | {max(v['refine']['max_evals_coord'] for v in x)} | "
                     f"{sum(v['refine']['n_moved'] for v in x)} / {sum(v['n_atoms'] for v in x)} | {sum(not v['sbl']['converged'] for v in x)} |")
        per_key = [r['seconds']['total'] + r.get('gen_seconds', 0.) for r in good]
        L += ['', f"seconds per key (pipeline + frame generation, on-grid check excluded): mean {np.mean(per_key):.2f}, min {min(per_key):.2f}, max {max(per_key):.2f}; "
                  f"mean refine seconds per variant: " + ', '.join(f"{o} {np.mean([r['variants'][o]['seconds']['refine'] for r in good]):.2f}" for o in OFF)
                  + '; mean SBL seconds per variant: ' + ', '.join(f"{o} {np.mean([r['variants'][o]['seconds']['sbl'] for r in good]):.2f}" for o in OFF),
              f"core-hours for 2400 keys: raw {np.mean(per_key) * lib.N_KEYS / 3600:.2f}, x{CONTENTION} {np.mean(per_key) * lib.N_KEYS / 3600 * CONTENTION:.2f}",
              f"max cond(Q) over all refinements: {max(r['variants'][o]['refine']['cond_Q'] for r in good for o in OFF):.3g}",
              f"keys: {sorted(lib.key_of(r) for r in good)}"]
    (args.out / 'SMOKE_COUNTS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('gate-prep', 'gate', 'gate-merge', 'run', 'smoke-counts', 'cost-check'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--e3-rows', type=Path, default=lib.E3_ROWS, help='E-3 main rows (gz) + REMOTE_ROWS_MD5.txt')
    p.add_argument('--unit', type=Path, default=None, help='gate-merge: out/unit/test_e3b.json (synthetic G2 / G3)')
    p.add_argument('--smoke-dir', type=Path, default=None, help='gate-merge: smoke rows for G4')
    p.add_argument('--smoke', action='store_true', help='run: the 16 smoke keys (frames >= 8300), with the on-grid round-2 check; never analysed')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--total', type=int, default=lib.N_KEYS, help='cost-check: total number of keys')
    p.add_argument('--limit', type=float, default=COST_LIMIT, help='cost-check: core-hour limit')
    return p.parse_args(argv)


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'run':
        run_mode(A, sys.argv[1:])
    elif A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    elif A.mode == 'gate-prep':
        gate_prep(A)
    elif A.mode == 'gate-merge':
        gate_merge(A)
    elif A.mode == 'smoke-counts':
        smoke_counts(A)
    else:
        sys.exit(cost_check(A))
