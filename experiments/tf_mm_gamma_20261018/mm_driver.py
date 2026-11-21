#!/usr/bin/env python
"""Model-matched check of the full Gamma (task 10-18-model-matched-gamma; PROTOCOL.md = design.md + execution facts).

Per key (U/G x rho .3 x {6,7,8} dB x frame 4000..4049): the E-3 pipeline (stage-1 pilot SBL -> round-1 detection + LDPC -> stage-2 soft-mean candidate set,
frozen E-3 code imported read-only) gives mu, v, the candidate set and the true paths.  Then
  real observation       S-diag, S-cov  (== E-3 L-diag, L-cov; contrast, bit-identical to the E-3 rows)
  synthetic observation  Y_syn = B(pilot + x~) h_true + CN(0, sigma2), x~ ~ per-symbol QPSK posterior of the round-1 APP (E[x~] = mu, Var[x~] = v), R = 3 draws;
                         S-diag, S-cov, S-hard, S-genie (stage-2 SBL with the E-3 hyper-parameters, candidate set and output selection)
Readouts per run: channel NMSE, same-delay census, EIV lower-bound trace (monotonicity violations).
Modes: gate / gate-merge (G1-G4) | run (--smoke: 6 smoke keys on frames >= 8300).   Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(HERE))
import mm_lib as mm  # noqa: E402  (also puts the frozen E-3 directory and the frozen kernels on sys.path)
import mm_agg as agg  # noqa: E402

import e3_driver as e3d  # noqa: E402  (frozen E-3 driver, read-only import: P1 context, keys, detector/decoder wrappers)

sbl, crb, gd, p1ctx = e3d.sbl, e3d.crb, e3d.gd, e3d.p1ctx

SEED = 20261018
SCENARIOS = ('U', 'G')
RHO_PM = 300
SNRS = (600, 700, 800)                 # centi-dB
FRAMES = (4000, 4050)
REPS = 3
VARIANTS = ('S-diag', 'S-cov', 'S-hard', 'S-genie')
CORE_VARIANTS = ('S-diag', 'S-cov')    # the variants of the frozen criterion; S-hard / S-genie are report-only
REAL_VARIANTS = ('S-diag', 'S-cov')
COST_CAP_SECONDS = 3 * 3600.0
SMOKE_FRAMES = (8300, 8303)            # smoke only: 3 frames x U/G at 7 dB = 6 keys
SMOKE_SNR = 700
G1_FRAMES, G1_SNR = (8310, 8313), 600  # gate G1 / G2: 3 frames x U/G at 6 dB (largest v)
G4_FRAMES = (8320, 8322)               # gate G4 determinism (2 frames x U/G, SNR alternating 6 / 8 dB)
G1_DRAWS = 2000
G3_N = 10
SCEN_CODE = dict(U=0, G=1)


# ----------------------------------------------------------------------------- keys, seeds, provenance
def main_keys():
    """The 300 frozen keys, frame-major (a cost-stopped run leaves whole frames)."""
    return [(sc, RHO_PM, snr, f) for f in range(*FRAMES) for sc in SCENARIOS for snr in SNRS]


def smoke_keys():
    return [(sc, RHO_PM, SMOKE_SNR, f) for f in range(*SMOKE_FRAMES) for sc in SCENARIOS]


def g3_keys():
    keys = main_keys()
    return [keys[i] for i in range(0, len(keys), len(keys) // G3_N)][:G3_N]


def seed_seq(key, r):
    sc, rho_pm, snr, frame = key
    return np.random.SeedSequence([SEED, SCEN_CODE[sc], int(rho_pm), int(snr), int(frame), int(r)])


def key_of(row):
    return (row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame'])


def check_e3_code_md5():
    """The E-3 code files (read-only imports) must have the md5 recorded in SOURCE_MD5.txt."""
    out, bad = {}, []
    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        digest, rel = line.split()
        actual = e3d.e3_lib.md5_file(EXPERIMENTS / rel)
        out[rel] = dict(expected=digest, actual=actual, status='ok' if actual == digest else 'MISMATCH')
        if actual != digest:
            bad.append(rel)
    if bad:
        raise RuntimeError(f'E-3 code md5 mismatch: {bad}')
    return out


def own_md5():
    names = ('mm_lib.py', 'mm_driver.py', 'mm_agg.py', 'PROTOCOL.md', 'SOURCE_MD5.txt', 'launch_mm.sh')
    return {n: e3d.e3_lib.md5_file(HERE / n) for n in names if (HERE / n).exists()}


def write_config(out, shard, argv, args, ctx, extra=None):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    cfg = dict(vars(args), out=str(args.out), variants=VARIANTS, real_variants=REAL_VARIANTS, seed=SEED, reps=args.reps, aux_reps=(args.reps if args.aux_reps is None else args.aux_reps), hyper=sbl.HYPER,
               violation_tol=mm.VIOLATION_TOL, family_P1=dict(entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN),
               frozen_md5_check=e3d.check_frozen_md5(ctx), e3_code_md5_check=check_e3_code_md5(), own_md5=own_md5(), source_md5=ctx.source_md5,
               environment=ctx.environment, **(extra or {}))
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- the per-key pipeline
def make_key(ctx, key, base_cache):
    """(meta, obs, data_af, truth) of one key; the P1 base frame of (scenario, frame) is kept between consecutive keys."""
    sc, rho_pm, snr, frame = key
    bk = (sc, rho_pm, frame)
    gen = 0.0
    if base_cache.get('key') != bk:
        t0 = time.perf_counter()
        base_cache['val'] = p1ctx.base(ctx, sc, rho_pm / 1000, frame)
        base_cache['key'] = bk
        gen = time.perf_counter() - t0
    return e3d.observe_key(ctx, base_cache['val'][0], base_cache['val'][1], sc, rho_pm, int(snr), int(frame), gen)


def prepare_key(ctx, cache, grid, obs, truth, zero_v=False):
    """E-3's process_key up to (and including) the stage-2 candidate set, verbatim arithmetic.  zero_v: v := 0 (gate G2 only)."""
    from messages import moments
    from physical import daft
    s = ctx.system
    n, c1, c2 = len(obs['y']), s.c1, s.c2
    pd = 1 - s.rho
    sigma2 = float(obs['sigma2'])
    delays_g, nus_g = grid
    tp = e3d.truth_paths(truth)
    sec = {}
    Y = daft(obs['y'], c1, c2, True)
    t = time.perf_counter()
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    sec['stage1_screen'] = time.perf_counter() - t
    t = time.perf_counter()
    r1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (sigma2 + pd), Gamma=None)
    g1_idx, g1_mu, g1_e = sbl.select_output(cand1[r1['idx']], r1['mu'])
    sec['stage1_sbl'] = time.perf_counter() - t
    ch1 = e3d.make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    det1, dec1, t_det, t_dec = e3d.detect_decode(ctx, obs, ch1, None)
    sec['round1_detect'], sec['round1_decode'] = t_det, t_dec
    L_app = np.clip(dec1['raw_app'], -20, 20)
    mu_d, v, _ = moments(L_app, pd)
    if zero_v:
        v = np.zeros_like(v)
    err1 = gd.score(ctx, dec1['decoded'], truth)
    t = time.perf_counter()
    Bs = sbl.columns(e3d.self_xt(obs['pilot'] + mu_d, c1, c2), delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    cand2 = sbl.candidate_union(top2, set(int(x) for x in delays_g[g1_idx]), delays_g)
    cd, cn = delays_g[cand2], nus_g[cand2]
    Bsel = Bs[:, cand2]
    del Bs
    sec['stage2_screen'] = time.perf_counter() - t
    mean_v = float(np.mean(v))
    return dict(n=n, c1=c1, c2=c2, pd=pd, sigma2=sigma2, delays_g=delays_g, nus_g=nus_g, tp=tp, true_delays=set(tp['delays']), Y=Y, L_app=L_app, mu_d=mu_d, v=v,
                mean_v=mean_v, beta0_soft=1.0 / (sigma2 + mean_v), cand2=cand2, cd=cd, cn=cn, Bsel=Bsel, sec=sec, gamma=None, Bhard=None, obs=obs, truth=truth,
                stage1=dict(n_candidates=int(len(cand1)), iterations=r1['iterations'], converged=r1['converged'], n_final=r1['n_final'], beta=r1['beta'],
                            jitter_events=r1['jitter_events'], atoms=e3d.atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                            nmse=float(crb.channel_nmse(dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu), tp, n))),
                round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])), decoded_sha256=gd.bits_sha(dec1['decoded']),
                            ldpc_iters=int(dec1['iterations'])), n_candidates_stage2=int(len(cand2)),
                kept_delays_stage1=int(len(set(int(x) for x in delays_g[g1_idx]))))


def gamma_of(st):
    """Full projected covariance Gamma(v) of the candidate atoms (frozen _gamma_cross); computed once per key."""
    if st['gamma'] is None:
        t = time.perf_counter()
        st['gamma'] = sbl.gamma_full(st['cd'], st['cn'], st['v'], st['c1'])
        st['gamma_seconds'] = time.perf_counter() - t
        s = float(st['v'].sum())
        st['gamma_diag_rel_err'] = float(np.max(np.abs(np.diag(st['gamma']).real - s) / s)) if s > 0 else float(np.max(np.abs(np.diag(st['gamma']))))
    return st['gamma']


def run_sbl(st, B, Y, beta0, G):
    """Traced stage-2 SBL + E-3 output selection; returns (raw result, selection, record)."""
    t = time.perf_counter()
    res = mm.sbl_em_traced(B, Y, beta0=beta0, Gamma=G)
    idx, mu, e = sbl.select_output(st['cand2'][res['idx']], res['mu'])
    dl, nu = st['delays_g'][idx], st['nus_g'][idx]
    pairs = sbl.codelay_pairs(dl, nu, st['n'], st['true_delays'])
    rec = dict(n_atoms=int(len(idx)), atoms=e3d.atoms_record(dl, nu, e), n_pair=len(pairs), pairs=pairs,
               nmse=float(crb.channel_nmse(dict(delays=dl, dopplers=nu, gains=mu), st['tp'], st['n'])),
               sbl=dict(max_iter=int(sbl.MAX_ITER), iterations=res['iterations'], converged=res['converged'], n_start=res['n_start'], n_final=res['n_final'],
                        beta=res['beta'], jitter_events=res['jitter_events']),
               eiv=mm.eiv_summary(res['trace'], res['skip']), seconds=time.perf_counter() - t)
    return res, (idx, mu, e), rec


def variant_inputs(st, name, Y, xs=None):
    """(dictionary, Gamma, beta0) of a stage-2 variant; same data models as E-3's L-diag / L-cov / L-hard / L-genie."""
    if name == 'S-diag':
        return st['Bsel'], float(st['v'].sum()), st['beta0_soft']
    if name == 'S-cov':
        return st['Bsel'], gamma_of(st), st['beta0_soft']
    if name == 'S-hard':
        if st['Bhard'] is None:
            st['Bhard'] = sbl.columns(e3d.self_xt(st['obs']['pilot'] + sbl.hard_decision(st['mu_d'], st['pd']), st['c1'], st['c2']), st['cd'], st['cn'], st['c1'], st['c2'])
        return st['Bhard'], None, st['beta0_soft']
    if name == 'S-genie':
        B = sbl.columns(e3d.self_xt(st['obs']['pilot'] + xs, st['c1'], st['c2']), st['cd'], st['cn'], st['c1'], st['c2'])
        return B, None, 1.0 / st['sigma2']
    raise ValueError(name)


def true_response(st, xs):
    """Noiseless observation sum_p g_p B(pilot + xs)[:, p] over the TRUE paths (real-valued Doppler k_real): the construction of E-3's dictionary-convention check."""
    truth = st['truth']
    Bt = sbl.columns(e3d.self_xt(st['obs']['pilot'] + xs, st['c1'], st['c2']), np.asarray(truth['l_i'], dtype=np.int64), np.asarray(truth['k_real'], dtype=float), st['c1'], st['c2'])
    return Bt @ np.asarray(truth['g_i'], dtype=complex)


def synth_observation(st, rng, zero_v=False):
    """x~ ~ posterior (or mu when v == 0) and Y_syn = B(pilot + x~) h_true + CN(0, sigma2).  Draw order: the 2n posterior uniforms, then the 2n noise normals."""
    xs = st['mu_d'].copy() if zero_v else mm.sample_qpsk(st['L_app'], st['pd'], rng)
    noise = np.sqrt(st['sigma2'] / 2.0) * (rng.standard_normal(st['n']) + 1j * rng.standard_normal(st['n']))
    return xs, true_response(st, xs) + noise


def real_variants(st, names=REAL_VARIANTS):
    """S-diag / S-cov on the REAL observation (== E-3 L-diag / L-cov)."""
    return {name: _run_variant(st, name, st['Y'])[2] for name in names}


def _run_variant(st, name, Y, xs=None):
    B, G, beta0 = variant_inputs(st, name, Y, xs)
    return run_sbl(st, B, Y, beta0, G)


def synth_rep(st, key, r, names=VARIANTS, zero_v=False):
    """One synthetic draw (seed = fixed function of key and r).  The RNG stream does not depend on ``names``."""
    rng = np.random.default_rng(seed_seq(key, r))
    xs, Ysyn = synth_observation(st, rng, zero_v)
    sv = float(st['v'].sum())
    out = dict(rep=int(r), x_stats=dict(dev_ratio=(float(np.sum(np.abs(xs - st['mu_d']) ** 2) / sv) if sv > 0 else None),
                                        frac_differs_from_hard=float(np.mean(xs != sbl.hard_decision(st['mu_d'], st['pd'])))))
    for name in names:
        out[name] = _run_variant(st, name, Ysyn, xs)[2]
    return out


def process_key_mm(ctx, cache, grid, obs, truth, meta, reps=REPS, zero_v=False, aux_reps=None):
    """aux_reps (default = reps = the design): S-hard / S-genie are run on the first aux_reps draws only (cost option; S-diag / S-cov always on all reps)."""
    aux_reps = reps if aux_reps is None else aux_reps
    t_all = time.perf_counter()
    key = key_of(meta)
    st = prepare_key(ctx, cache, grid, obs, truth, zero_v=zero_v)
    row = dict(meta, sigma2=st['sigma2'], truth=dict(delays=st['tp']['delays'], dopplers=st['tp']['dopplers'], gains=[[float(g.real), float(g.imag)] for g in st['tp']['gains']]),
               stage1=st['stage1'], round1=st['round1'], mean_v=st['mean_v'], n_candidates_stage2=st['n_candidates_stage2'], kept_delays_stage1=st['kept_delays_stage1'],
               reps=int(reps), aux_reps=int(aux_reps), seed=SEED)
    row['real'] = real_variants(st)
    row['syn'] = [synth_rep(st, key, r, names=VARIANTS if r < aux_reps else CORE_VARIANTS, zero_v=zero_v) for r in range(reps)]
    row['gamma_diag_rel_err'], row['gamma_seconds'] = st['gamma_diag_rel_err'], st['gamma_seconds']
    sec = dict(st['sec'])
    sec['total'] = time.perf_counter() - t_all
    row['seconds'] = sec
    return row


# ----------------------------------------------------------------------------- run / smoke
def read_cost(out):
    total = 0.0
    for p in glob.glob(str(out / 'cost_shard*.txt')):
        try:
            total += float(Path(p).read_text().strip() or 0)
        except ValueError:
            pass
    return total


def run_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    keys = smoke_keys() if args.smoke else main_keys()
    mine = keys[args.shard::args.nshard]
    write_config(out, args.shard, argv, args, ctx, extra=dict(smoke_only=bool(args.smoke), n_keys_total=len(keys), n_keys_shard=len(mine)))
    cache = e3d.PilotCache()
    grid = sbl.full_grid(int(ctx.system.l_max_cap))
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    cost_file = out / f'cost_shard{args.shard:03d}.txt'
    cum = float(cost_file.read_text().strip()) if cost_file.exists() and cost_file.read_text().strip() else 0.0
    done = gd.load_done(jsonl)
    started = time.perf_counter()
    base_cache, n_rows, stopped = {}, 0, False
    with jsonl.open('a') as handle:
        for key in mine:
            if key in done:
                continue
            if args.max_keys and n_rows >= args.max_keys:
                break
            if args.cost_cap_seconds and read_cost(out) >= args.cost_cap_seconds:
                (out / 'COST_STOP').write_text(f'shard {args.shard} stopped before key {key}: committed cost {read_cost(out):.0f} s >= cap {args.cost_cap_seconds:.0f} s\n')
                stopped = True
                break
            meta, obs, _, truth = make_key(ctx, key, base_cache)
            if args.smoke:
                meta['smoke'] = True
            t0 = time.perf_counter()
            try:
                row = process_key_mm(ctx, cache, grid, obs, truth, meta, reps=args.reps, aux_reps=args.aux_reps)
            except Exception as error:  # recorded, never silently dropped
                row = dict(meta, status='error', error=repr(error), trace=traceback.format_exc()[-1500:])
            e3d.write_row(handle, row)
            n_rows += 1
            cum += (time.perf_counter() - t0) + meta.get('gen_seconds', 0.0)
            tmp = cost_file.with_suffix('.tmp')
            tmp.write_text(f'{cum:.3f}\n')
            os.replace(tmp, cost_file)
            if 'real' in row:
                nm = lambda w: '/'.join(f"{row['real'][v]['nmse']:.3g}" for v in w)  # noqa: E731
                print(f"[{time.perf_counter() - started:8.1f}s] {key} total {row['seconds']['total']:.1f}s real_nmse {nm(REAL_VARIANTS)} "
                      f"eiv_viol {sum(x['eiv']['n_viol'] for x in row['real'].values()) + sum(x[v]['eiv']['n_viol'] for x in row['syn'] for v in VARIANTS)}", flush=True)
            else:
                print(f'[{time.perf_counter() - started:8.1f}s] {key} ERROR {row.get("error")}', flush=True)
    print(f'shard {args.shard}/{args.nshard} {"COST-STOPPED" if stopped else "done"}: {n_rows} keys in {time.perf_counter() - started:.1f}s, committed cost {cum:.0f} s', flush=True)


# ----------------------------------------------------------------------------- gates
def strip_seconds(row):
    r = json.loads(json.dumps(row))
    for k in ('seconds', 'gamma_seconds', 'gen_seconds'):
        r.pop(k, None)
    for v in list(r.get('real', {}).values()) + [x[n] for x in r.get('syn', []) for n in VARIANTS if n in x]:
        v.pop('seconds', None)
    return r


def bits_equal(a, b):
    return all(np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in ('idx', 'mu', 'gamma', 'beta', 'iterations', 'converged', 'n_final', 'jitter_events'))


def gate_items(args):
    items = []
    g4 = [(sc, RHO_PM, (600, 800)[i % 2], f) for i, (f, sc) in enumerate((f, sc) for f in range(*G4_FRAMES) for sc in SCENARIOS)]
    items += [('G4', k) for k in g4]
    g12 = [(sc, RHO_PM, G1_SNR, f) for f in range(*G1_FRAMES) for sc in SCENARIOS]
    items += [('G2', k) for k in g12[:3]]
    items += [('G3', k) for k in g3_keys()]
    items += [('G1', k) for k in g12]
    return items


def gate_item(ctx, cache, grid, kind, key, args, e3_rows, base_cache):
    meta, obs, data_af, truth = make_key(ctx, key, base_cache)
    rec = dict(kind=kind, key=list(key))
    if kind == 'G1':
        st = prepare_key(ctx, cache, grid, obs, truth)
        from physical import daft
        raw, _ = ctx.reuse_at_snr(base_cache['val'][0], base_cache['val'][1], key[2] / 100)
        y0 = daft(np.asarray(raw['noiseless']) / np.sqrt(2. * (1. - key[1] / 1000)), st['c1'], st['c2'], True)
        rec['truth_response_rel_err'] = float(np.linalg.norm(true_response(st, data_af) - y0) / np.linalg.norm(y0))
        rng = np.random.default_rng(np.random.SeedSequence([SEED, 1001, SCEN_CODE[key[0]], int(key[3])]))
        R, n = G1_DRAWS, st['n']
        s1, s2 = np.zeros(n, complex), np.zeros(n)
        for _ in range(R):
            x = mm.sample_qpsk(st['L_app'], st['pd'], rng)
            s1 += x
            s2 += np.abs(x) ** 2
        xbar = s1 / R
        var_emp = (s2 - R * np.abs(xbar) ** 2) / (R - 1)
        m_an, v_an = mm.sampler_moments(st['L_app'], st['pd'])
        mu, v = st['mu_d'], st['v']
        from messages import alphabet
        a_pts, _ = alphabet(st['pd'])
        x_probe = mm.sample_qpsk(st['L_app'], st['pd'], rng)
        rec.update(alphabet_dist=float(max(np.min(np.abs(a_pts - z)) for z in x_probe)),
                   hard_agrees_true=float(np.mean(np.abs(sbl.hard_decision(mu, st['pd']) - data_af) < 1e-12)), draws=R, mean_v=st['mean_v'], mean_rel_err=float(np.linalg.norm(xbar - mu) / np.linalg.norm(mu)),
                   var_rel_err=float(abs(var_emp.sum() - v.sum()) / v.sum()), mean_chi2_ratio=float(np.sum(np.abs(xbar - mu) ** 2) / (v.sum() / R)),
                   exact_mean_err=float(np.max(np.abs(m_an - mu))), exact_var_err=float(np.max(np.abs(v_an - v))), round1_info_errors=st['round1']['info_errors'])
    elif kind == 'G2':
        # (a) traced SBL == frozen SBL on the real v > 0 problem; (b) v == 0: S-cov == S-diag == frozen standard SBL, real and synthetic
        st = prepare_key(ctx, cache, grid, obs, truth)
        out = {}
        for name in REAL_VARIANTS:
            B, G, b0 = variant_inputs(st, name, st['Y'])
            out[f'frozen_vs_traced_{name}'] = bits_equal(sbl.sbl_em(B, st['Y'], beta0=b0, Gamma=G), mm.sbl_em_traced(B, st['Y'], beta0=b0, Gamma=G))
        z = prepare_key(ctx, cache, grid, obs, truth, zero_v=True)
        gz = gamma_of(z)
        out['gamma_zero'] = bool(np.all(gz == 0))
        rng = np.random.default_rng(seed_seq(key, 0))
        xs, Ysyn = synth_observation(z, rng, zero_v=True)
        for world, Y, x_, names in (('real', z['Y'], None, ('S-diag', 'S-cov')), ('syn', Ysyn, xs, ('S-diag', 'S-cov', 'S-genie'))):
            res = {n: _run_variant(z, n, Y, x_) for n in names}
            B, _, b0 = variant_inputs(z, 'S-diag', Y)
            std = sbl.sbl_em(B, Y, beta0=b0, Gamma=None)
            out[f'{world}_cov_eq_diag'] = bool(bits_equal(res['S-cov'][0], res['S-diag'][0]) and res['S-cov'][2]['atoms'] == res['S-diag'][2]['atoms'])
            out[f'{world}_diag_eq_frozen_standard_sbl'] = bool(bits_equal(res['S-diag'][0], std))
            if 'S-genie' in res:
                out['syn_genie_vs_diag_max_rel_mu'] = float(np.max(np.abs(res['S-genie'][0]['mu'] - res['S-diag'][0]['mu'])) / np.max(np.abs(res['S-diag'][0]['mu'])))
            out[f'{world}_trace_equals_standard_marginal'] = float(abs(res['S-diag'][0]['trace'][-1] - mm.standard_sbl_ll(B[:, res['S-diag'][0]['idx']], Y, res['S-diag'][0]['beta'],
                                                                                                                         res['S-diag'][0]['gamma'])) / max(1., abs(res['S-diag'][0]['trace'][-1])))
        rec.update(out)
    elif kind == 'G3':
        st = prepare_key(ctx, cache, grid, obs, truth)
        real = real_variants(st)
        shell = dict(stage1=st['stage1'], round1=st['round1'], n_candidates_stage2=st['n_candidates_stage2'], real=real)
        rec['match'] = agg.e3_match(shell, e3_rows[key])
        rec['eiv'] = {n: real[n]['eiv'] for n in real}
        rec['seconds'] = {n: real[n]['seconds'] for n in real}
    elif kind == 'G4':
        r1 = process_key_mm(ctx, cache, grid, obs, truth, dict(meta))
        r2 = process_key_mm(ctx, cache, grid, obs, truth, dict(meta))
        diff = e3d.e3_lib.deep_equal(strip_seconds(r1), strip_seconds(r2))
        rec.update(identical=not diff, mismatch=diff[:3], seconds=[r1['seconds']['total'], r2['seconds']['total']], gen_seconds=meta.get('gen_seconds', 0.0),
                   n_sbl_runs=len(r1['real']) + sum(len(x) - 2 for x in r1['syn']), mean_sbl_seconds=float(np.mean(
                       [v['seconds'] for v in r1['real'].values()] + [x[n]['seconds'] for x in r1['syn'] for n in VARIANTS])))
    return rec


def gate_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    items = gate_items(args)[args.shard::args.nshard]
    wanted = {k for kind, k in items if kind == 'G3'}
    e3_rows = agg.load_e3_rows(args.e3_rows, wanted) if wanted else {}
    missing = wanted - set(e3_rows)
    if missing:
        raise SystemExit(f'E-3 rows missing for G3 keys: {sorted(missing)}')
    cache, grid, base_cache = e3d.PilotCache(), sbl.full_grid(int(ctx.system.l_max_cap)), {}
    recs, started = [], time.perf_counter()
    for kind, key in items:
        try:
            recs.append(gate_item(ctx, cache, grid, kind, key, args, e3_rows, base_cache))
        except Exception as error:  # recorded: the gate then fails visibly instead of silently losing the shard
            recs.append(dict(kind=kind, key=list(key), error=repr(error), trace=traceback.format_exc()[-1500:]))
        print(f'[{time.perf_counter() - started:8.1f}s] {kind} {key} done' + (' ERROR' if 'error' in recs[-1] else ''), flush=True)
    (out / f'gate_shard{args.shard:03d}.json').write_text(json.dumps(dict(records=recs), default=str) + '\n')


def gate_merge(args):
    recs = []
    for p in sorted(args.out.glob('gate_shard*.json')):
        recs += json.loads(p.read_text())['records']
    errors = [r for r in recs if 'error' in r]
    by = lambda k: [r for r in recs if r['kind'] == k and 'error' not in r]  # noqa: E731
    gates = dict(item_errors=[dict(kind=r['kind'], key=r['key'], error=r['error']) for r in errors])
    g1 = by('G1')
    gates['G1'] = dict(keys=len(g1), draws=G1_DRAWS, worst_mean_rel_err=max([r['mean_rel_err'] for r in g1] or [1.]), worst_var_rel_err=max([r['var_rel_err'] for r in g1] or [1.]),
                       mean_v=[r['mean_v'] for r in g1], mean_chi2_ratio=[r['mean_chi2_ratio'] for r in g1], worst_exact_mean_err=max([r['exact_mean_err'] for r in g1] or [1.]),
                       worst_exact_var_err=max([r['exact_var_err'] for r in g1] or [1.]), worst_alphabet_dist=max([r['alphabet_dist'] for r in g1] or [1.]),
                       min_hard_agrees_true=min([r['hard_agrees_true'] for r in g1] or [0.]), worst_truth_response_rel_err=max([r['truth_response_rel_err'] for r in g1] or [1.]), round1_info_errors=[r['round1_info_errors'] for r in g1])
    gates['G1']['pass_'] = bool(len(g1) >= 6 and gates['G1']['worst_alphabet_dist'] < 1e-12 and gates['G1']['worst_truth_response_rel_err'] < 1e-10 and gates['G1']['min_hard_agrees_true'] > .5 and gates['G1']['worst_mean_rel_err'] <= .02 and gates['G1']['worst_var_rel_err'] <= .02 and gates['G1']['worst_exact_mean_err'] < 1e-12
                                and gates['G1']['worst_exact_var_err'] < 1e-12)
    g2 = by('G2')
    flags = ('real_cov_eq_diag', 'real_diag_eq_frozen_standard_sbl', 'syn_cov_eq_diag', 'syn_diag_eq_frozen_standard_sbl', 'gamma_zero',
             'frozen_vs_traced_S-diag', 'frozen_vs_traced_S-cov')
    gates['G2'] = dict(keys=len(g2), checks={f: sum(bool(r[f]) for r in g2) for f in flags}, worst_genie_vs_diag_rel_mu_syn=max([r['syn_genie_vs_diag_max_rel_mu'] for r in g2] or [1.]),
                       worst_trace_vs_standard_marginal=max([max(r['real_trace_equals_standard_marginal'], r['syn_trace_equals_standard_marginal']) for r in g2] or [1.]))
    gates['G2']['pass_'] = bool(len(g2) >= 3 and all(v == len(g2) for v in gates['G2']['checks'].values()) and gates['G2']['worst_trace_vs_standard_marginal'] < 1e-9)
    g3 = by('G3')
    names = sorted(next(iter(g3))['match']) if g3 else []
    gates['G3'] = dict(keys=len(g3), match_counts={n: sum(bool(r['match'][n]) for r in g3) for n in names},
                       real_key_eiv=dict(runs=2 * len(g3), violations=sum(e['n_viol'] for r in g3 for e in r['eiv'].values()),
                                         runs_with_violation=sum(e['n_viol'] > 0 for r in g3 for e in r['eiv'].values()),
                                         max_rel_drop=max([e['max_rel_drop'] for r in g3 for e in r['eiv'].values()] or [0.]),
                                         prune_events=sum(e['n_prune_events'] for r in g3 for e in r['eiv'].values())))
    gates['G3']['pass_'] = bool(len(g3) >= G3_N and all(v == len(g3) for v in gates['G3']['match_counts'].values()))
    g4 = by('G4')
    sec = [s for r in g4 for s in r['seconds']]
    per_key = float(np.mean(sec)) + float(np.mean([r['gen_seconds'] for r in g4] or [0.]))
    gates['G4'] = dict(keys=len(g4), identical=sum(bool(r['identical']) for r in g4), mismatches=[r['mismatch'] for r in g4 if not r['identical']][:3],
                       seconds_per_key=per_key, mean_sbl_seconds=float(np.mean([r['mean_sbl_seconds'] for r in g4] or [0.])),
                       sbl_runs_per_key=g4[0]['n_sbl_runs'] if g4 else None, est_core_hours_300_keys=300 * per_key / 3600.0, cap_core_hours=COST_CAP_SECONDS / 3600.0,
                       note='estimate at the load of the gate run; not a pass criterion (reported separately)')
    gates['G4']['cost_within_cap'] = bool(gates['G4']['est_core_hours_300_keys'] <= gates['G4']['cap_core_hours'])
    gates['G4']['pass_'] = bool(len(g4) >= 4 and gates['G4']['identical'] == len(g4))
    names = ('test_mm.json', 'test_mm_agg.json')
    gates['unit'] = dict(dir=str(args.unit_dir), present=[n for n in names if (args.unit_dir / n).exists()],
                         pass_=bool(all((args.unit_dir / n).exists() and json.loads((args.unit_dir / n).read_text()).get('all_pass') for n in names)))
    gates['all_pass'] = bool(not errors and all(gates[k]['pass_'] for k in ('G1', 'G2', 'G3', 'G4', 'unit')))
    (args.out / 'gates.json').write_text(json.dumps(gates, indent=1) + '\n')
    print(json.dumps(gates, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('gate', 'gate-merge', 'run'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--e3-rows', type=Path, default=EXPERIMENTS / 'tf_e3_sbl_20261017' / 'out' / 'main', help='gate: E-3 main rows (rows_shard*.jsonl.gz) for G3')
    p.add_argument('--unit-dir', type=Path, default=HERE / 'out' / 'unit', help='gate-merge: directory with test_mm.json and test_mm_agg.json')
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--reps', type=int, default=REPS)
    p.add_argument('--aux-reps', type=int, default=None, help='run: S-hard / S-genie on the first AUX_REPS draws only (default = reps = the design)')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--max-keys', type=int, default=0)
    p.add_argument('--cost-cap-seconds', type=float, default=0.0, help='run: stop starting keys once the committed cost of all shards reaches this (0 = off)')
    return p.parse_args(argv)


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    elif A.mode == 'gate-merge':
        gate_merge(A)
    else:
        run_mode(A, sys.argv[1:])
