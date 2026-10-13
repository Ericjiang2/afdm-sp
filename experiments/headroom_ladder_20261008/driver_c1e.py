#!/usr/bin/env python
"""C1 EXIT-state driver (task 10-08-doppler-cluster; research/c1-scalar-closure.md, Amendment A3 + coordinator correction).

Measures the SP joint receiver's one-round transfer  I_r -> I_{r+1}  where I_r = MI (1 - logloss) of the PREVIOUS round's decoder-input
LLR on the true coded bits.  The round-1 front state is replaced by the decoder-side state that the AWGN decoder EXIT curve of T1
(out/c1_t1/t1_transfer.json, key "exit": I_in, I_ext, I_app per q, monotone) associates with I_r:
    I_A = I_ext(I_r)  (decoder check-extrinsic MI  = detector prior),     I_R = I_app(I_r)  (decoder APP MI = refit soft symbols),
both by linear interpolation against I_in (assert: I_r inside the T1 I_in range; I_in strictly increasing).
GENIE consistent-Gaussian LLRs on the TRUE coded bits (component measurement only, never a receiver-performance claim):
    L_A = (sigma_A^2/2) x + sigma_A w_A,   sigma_A = J^{-1}(I_A),             x = 1 - 2 b  (+1 for bit 0; codebase L > 0 <-> bit 0),
    L_C = (sigma_C^2/2) x + sigma_C w_C,   sigma_C^2 = sigma_R^2 - sigma_A^2,  sigma_R = J^{-1}(I_R)   (L_C = 0 if I_R <= I_A),
    L_R = L_A + L_C  (consistent Gaussian of MI I_R).
w_A, w_C ~ N(0, I) are separate seed components 4 and 5: SeedSequence(entropy + [C1_DOMAIN, frame, 0, component]), shared across L, rho,
snr and I_r (coupled over the grid).  J = exact Gaussian-consistent MI by Gauss-Hermite quadrature (ten Brink's J is its closed-form fit).
Installed through front_override of interventions._instrumented on the state native_twofft.receive reads in round 1:
    state['prior'] = clip(L_A, +-20)  (round-1 detector prior of scalar_joint),
    state['mu'], state['v'] = messages.moments(clip(L_R, +-20), 1 - rho_rx = .5)  (round-1 refit soft symbols; GenieRefine sees them).
Then the unmodified algorithm, rounds = 2 (round 2 = normal decoder-fed state).  Arm EXIT_none = no override = the normal pilot-only round 1
(identical to SPg_flat rounds 1-2 of c1_map / c1_boot).  Observations are the c1_map (6.5 dB) / c1_boot (8 dB) observations (same entropy
129abc..., c1 domain, frames, rho .3).  Imported from driver_c1 / driver_c1i / driver (nothing frozen or already run is edited).
Per row and round r = 1, 2:  eps_ce<r>, eps_det<r>, cerr<r>, ierr<r>, syn<r>, dsha<r>, ll_in<r>, mi_in<r> (= 1 - logloss of the
decoder-input = detector-extrinsic LLR; mi_in1 is the measured I_{r+1}), mi_app<r> (decoder APP), mi_chk<r> (decoder check extrinsic);
plus Ir, IA_target, IR_target, sigma_A, sigma_C, ia_real / ir_real (1 - logloss of the injected clipped L_A / L_R on the true bits),
*_unclipped, mu_sign_agree, first_mu_ms / first_v_mean (what the round-1 refit saw) and the base.score fields of the final decision.
Run one process per shard, single thread (launch_c1e.sh).
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
import driver_c1i as c1i
import dpss_rx

HERE = base.HERE
PRIOR_COMPONENTS = {'w_A': 4, 'w_C': 5}  # new streams (c1 components 1-3 are channel / message / noise)
ROUNDS = 2
T1_JSON = HERE / 'out' / 'c1_t1' / 't1_transfer.json'
C1E_PARAMS = dict(
    pairing='observations identical to c1_map (6.5 dB) / c1_boot (8 dB): same entropy, c1 domain, frames, rho .3',
    state='I_A = I_ext(I_r), I_R = I_app(I_r) from T1 exit curve (linear interp. vs I_in); L_A consistent Gaussian sigma_A = J^-1(I_A) -> '
          'state[prior] = clip(L_A); L_R = L_A + L_C, sigma_C^2 = sigma_R^2 - sigma_A^2 (0 if I_R <= I_A) -> state[mu], state[v] = '
          'moments(clip(L_R), .5); w_A, w_C = seed components 4, 5 keyed (frame, Lkey 0)',
    receiver='GenieRefine (genie delays, flat prior tau_d = 1/K) + frozen native schedule, rounds 2, 20 inner iterations, joint gain mode')

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(240)


def J(sigma):
    """MI (bits) of a consistent Gaussian LLR L ~ N(sigma^2/2, sigma^2) for the transmitted bit."""
    if sigma <= 0.:
        return 0.
    lv = sigma ** 2 / 2. + sigma * _GH_X
    return float(1. - np.sum(_GH_W * np.logaddexp(0., -lv)) / np.sqrt(2. * np.pi) / np.log(2.))


def J_inv(i_a):
    if not 0. <= i_a < 1.:
        raise ValueError('MI must be in [0, 1)')
    return 0. if i_a == 0. else float(brentq(lambda s: J(s) - i_a, 1e-6, 40., xtol=1e-12))


def load_curve(path):
    """T1 decoder EXIT curve (I_in, I_ext, I_app); asserts I_in strictly increasing."""
    curve = json.loads(Path(path).read_text())['exit']['curve']
    c = {k: np.array([r[k] for r in curve], float) for k in ('I_in', 'I_ext', 'I_app')}
    if not np.all(np.diff(c['I_in']) > 0):
        raise ValueError('T1 I_in not strictly increasing')
    return c


def targets(curve, ir):
    """(I_A, I_R, sigma_A, sigma_C) for decoder-input MI I_r (None -> no injection)."""
    if ir is None:
        return None
    if not curve['I_in'][0] <= ir <= curve['I_in'][-1]:
        raise ValueError(f"I_r = {ir} outside the T1 I_in range [{curve['I_in'][0]:.4f}, {curve['I_in'][-1]:.4f}]")
    ia, ir_ = float(np.interp(ir, curve['I_in'], curve['I_ext'])), float(np.interp(ir, curve['I_in'], curve['I_app']))
    sa = J_inv(ia)
    sr = J_inv(ir_)
    sc = float(np.sqrt(sr ** 2 - sa ** 2)) if ir_ > ia else 0.
    return dict(IA=ia, IR=ir_, sigma_A=sa, sigma_R=sr, sigma_C=sc)


def arm_name(ir):
    return 'EXIT_none' if ir is None else f'EXIT_{ir:.2f}'


def exit_noise(entropy_hex, frame, n_bits):
    """(w_A, w_C): independent N(0, I) draws on separate seed components."""
    return tuple(np.random.default_rng(np.random.SeedSequence(base.entropy_words(entropy_hex) + [c1.C1_DOMAIN, int(frame), 0, comp]))
                 .standard_normal(n_bits) for comp in PRIOR_COMPONENTS.values())


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--Ls', default='8,12,16,20,24,28')
    p.add_argument('--rho-list', default='0.3')
    p.add_argument('--snr-list', default='6.5,8')
    p.add_argument('--Ir', default='none,0.42,0.45,0.50,0.53,0.55,0.57,0.60,0.65', help="decoder-input MI of the previous round; 'none' = normal pilot-only round 1")
    p.add_argument('--t1-json', type=Path, default=T1_JSON)
    p.add_argument('--frames', type=int, default=100)
    p.add_argument('--frame-offset', type=int, default=500)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=c1i.C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1e'
    return args


# ------------------------------------------------------------------------ receiver
def mi_of(ctx, llr, coded):
    return 1. - ctx.arms.logloss_bits(np.clip(np.asarray(llr, float), -20., 20.), coded)


def run_exit(ctx, obs, truth, ir, tg, w, genie_delays, cfg, a_true):
    """One EXIT arm: genie decoder-side state through front_override (none for ir None), then the unmodified 2-round SPg_flat algorithm."""
    from messages import moments
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    coded = np.asarray(truth['coded'])
    x = 1. - 2. * coded.astype(float)  # +1 for bit 0 (L > 0 <-> bit 0)
    info = dict(ia_real=None, ir_real=None, ia_real_unclipped=None, ir_real_unclipped=None, mu_sign_agree=None)
    front = None
    if ir is not None:
        l_a = .5 * tg['sigma_A'] ** 2 * x + tg['sigma_A'] * w[0]
        l_r = l_a + (.5 * tg['sigma_C'] ** 2 * x + tg['sigma_C'] * w[1] if tg['sigma_C'] > 0. else 0.)
        prior, soft = np.clip(l_a, -20., 20.), np.clip(l_r, -20., 20.)
        info.update(ia_real=mi_of(ctx, prior, coded), ir_real=mi_of(ctx, soft, coded),
                    ia_real_unclipped=1. - ctx.arms.logloss_bits(l_a, coded), ir_real_unclipped=1. - ctx.arms.logloss_bits(l_r, coded))

        def front(state, observed, model, _code):
            mu, v, _ = moments(soft, 1. - model.rho)  # same call as native_twofft.receive uses for APP -> next soft symbols
            info['mu_sign_agree'] = float(np.mean(np.concatenate([np.sign(mu.real) == x[:n], np.sign(mu.imag) == x[n:]])))
            state = dict(state, prior=prior.copy(), mu=mu, v=v, x_soft=mu.copy())
            return state, dict(kind='genie_decoder_state', Ir=float(ir), **{k: float(val) for k, val in tg.items()})

    refiner = c1.GenieRefine(genie_delays, 'flat', cfg)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1e_exit', rounds=ROUNDS, iterations=20,
                                            gain_mode='joint', front_override=front, refine_override=refiner)
    seconds = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != ROUNDS or (ir is not None and info['mu_sign_agree'] is None):
        raise RuntimeError('front override / refits did not run as expected')
    diag = c1.reliability(ctx, ar, coded)
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(c1i.decision_diag(ctx, ar, truth, r))
        diag[f'mi_in{r}'] = mi_of(ctx, ar[f'r{r - 1}_input_llr'], coded)
        diag[f'mi_app{r}'] = mi_of(ctx, ar[f'r{r - 1}_app'], coded)
        diag[f'mi_chk{r}'] = mi_of(ctx, ar[f'r{r - 1}_check'], coded)
    diag.update(info, Ir=None if ir is None else float(ir), rounds=ROUNDS, sec_pilot=float(result.trace['acquisition_seconds']),
                first_mu_ms=refiner.first_call['mu_ms'], first_v_mean=refiner.first_call['v_mean'])
    diag.update({} if tg is None else dict(IA_target=tg['IA'], IR_target=tg['IR'], sigma_A=tg['sigma_A'], sigma_C=tg['sigma_C']))
    return dict(decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds, triggered=None, diag=diag)


def run_cell(ctx, irs, tgs, w, obs, truth, head, a_true, cfg):
    rows = []
    genie = sorted(set(int(x) for x in truth['l_i']))
    for ir in irs:
        try:
            res = run_exit(ctx, obs, truth, ir, tgs[ir], w, genie, cfg, a_true)
            rows.append(dict(head, arm=arm_name(ir), status='ok', **base.score(ctx, res, truth), **res['diag']))
        except Exception as error:  # recorded, never silently dropped
            rows.append(dict(head, arm=arm_name(ir), Ir=ir, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    return rows


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    irs = [None if x.strip().lower() == 'none' else float(x) for x in base.parse_list(args.Ir, str)]
    if not irs or len({arm_name(x) for x in irs}) != len(irs):
        raise ValueError('bad --Ir')
    curve = load_curve(args.t1_json)
    tgs = {ir: targets(curve, ir) for ir in irs}  # asserts every I_r inside the T1 I_in range
    arms_wanted = [arm_name(ir) for ir in irs]
    Ls = base.parse_list(args.Ls, int)
    rhos = base.parse_list(args.rho_list, float)
    if any(L < 1 or L > 101 for L in Ls) or not args.frames or not args.entropy_hex:
        raise ValueError('bad --Ls / --frames / --entropy-hex')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    ctx.sources['driver_c1e.py'] = base.sha256_file(HERE / 'driver_c1e.py')
    ctx.sources['driver_c1i.py'] = base.sha256_file(HERE / 'driver_c1i.py')
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1e=C1E_PARAMS,
                  c1e_prior_components=PRIOR_COMPONENTS, c1e_targets={arm_name(k): v for k, v in tgs.items()},
                  t1_json_sha256=base.sha256_file(args.t1_json),
                  sp_cfg=cfg, m2_config_sha256=m2_digest, dpss_defaults=dpss_rx.CFG_DEFAULT)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=base.to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = c1i.load_done(jsonl, arms_wanted)
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None
            w = exit_noise(entropy, frame, 2 * n)  # (w_A, w_C)
            for L in Ls:
                cfg_name = f'L{L:02d}'
                todo = [(rho, s) for rho in rhos for s in snr_cells if (cfg_name, int(round(rho * 1000)), s, frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, n)
                e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                pair = None
                for rho in rhos:
                    todo_r = [s for (r, s) in todo if r == rho]
                    if not todo_r:
                        continue
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                    for snr_centi in todo_r:
                        raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                        obs = base.observe(raw, rho, snr_centi / 100)
                        truth = base.truth_from_raw(raw, diag_base)
                        fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                        if pair is None:
                            pair = fp
                        assert fp == pair, 'pairing across rho/snr broken'
                        mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                        if frame_fp is None:
                            frame_fp = mfp
                        assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                        head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                        rows = run_cell(ctx, irs, tgs, w, obs, truth, head, a_true, cfg)
                        base.append_rows(handle, rows)
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] c1e L={L} rho={rho} snr={snr_centi} frame={frame} ' +
                              ' '.join(f"{r['arm'][5:]}:{'E' if r['status'] != 'ok' else round(r['mi_in1'], 3)}" for r in rows),
                              flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        base.merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
