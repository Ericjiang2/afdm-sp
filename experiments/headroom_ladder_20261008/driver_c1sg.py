#!/usr/bin/env python
"""C1 statistic-gap diagnostic (X2; task 10-08-doppler-cluster; research/c1-prelim-positioning.md, FROZEN before the run).

Question: how much channel-estimation error does the receiver's white refit statistic lose against generalised least squares (GLS)
that whitens the superimposed-data interference?  Diagnostic only: the receiver (SPg_flat FULL: genie delays, flat prior, K = 8 L,
rounds 2, 20 inner updates) runs unmodified and is scored as usual; at each refit call the SAME design is re-solved with other noise
covariances and scored against the truth.  Truth (a_true) enters only these side estimates and their scores.

Refit model in the time domain (dpss_rx.Design):  Y = B h + e,  e = H_t (x - mu)_t + n,
    Cov(e) = H_t S H_t^H + noise I,   S = Dh diag(v) Dh^H  (Dh = inverse-DAFT matrix, v = per-symbol data variance handed to the refit;
    round 1: mu = 0, v = .5  =>  S = .5 I, DAFT unitarity asserted).
Estimators (same design B, same prior tau = the receiver's prior_var):
    W    receiver refit  C = s2 I,  s2 = noise + mean(v) * sum_l E_l (flat E_l = 1/L)   recomputed with dpss_rx._ridge; must equal the receiver gains
    Wt   white with the realised power  s2 = noise + mean(v) * e_real                    (scalar power mismatch only)
    G    genie GLS        C = H_t S H_t^H + noise I, H_t from the true tap sequences        (colour, genie)
    A    achievable GLS   as G with H_t from the receiver's current estimate (round 1: W; round r >= 2: the round r-1 detector gains handed in)
Row fields per refit round r in {1, 2}: eps_W<r>, eps_Wt<r>, eps_G<r>, eps_A<r> (driver_c1.eps_of), w_closure<r> = max|W - receiver gains|,
v_mean<r>, v_cv<r> (coefficient of variation of v); plus eps_ce<r>, eps_det<r>, cerr<r>, ierr<r> of the receiver, base.score fields and
ht_closure = ||Y_t,noiseless - H_t(a_true) x_t|| / ||Y_t,noiseless|| (validates the time-domain tap operator used by G).
Presets:  main  SNR {6.5, 8} x rho {.1, .2, .3, .5, .75} x L {8, 16, 24, 32}, frames 0-199.   --cells/--frames override (smoke).
Observations are those of driver_c1 / driver_c1ib2 for the same (entropy 129abc..., frame, L, rho, SNR).  Run one single-thread process
per shard (launch_c1sg.sh).
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np
from scipy.linalg import solve_triangular

import driver as base
import driver_c1 as c1
import driver_c1i as c1i
import driver_c1ib as ib
import driver_c1ib2 as ib2
import dpss_rx

HERE = base.HERE
CODE_FILES = ('driver_c1sg.py', 'driver_c1ib2.py', 'driver_c1ib.py', 'driver_c1i.py', 'driver_c1.py', 'driver.py', 'dpss_rx.py',
              'tapchannel.py', 'arms.py', 'orders.py')
ARM = 'SG_R2T20'
ROUNDS, ITERS = 2, 20
PRESETS = {'main': dict(cells=[(s, r, [8, 16, 24, 32]) for s in (6.5, 8.0) for r in (0.1, 0.2, 0.3, 0.5, 0.75)], frames=200)}
SG_PARAMS = dict(
    pairing='observations identical to driver_c1 / driver_c1ib2 for the same (entropy_hex 129abc..., frame, L, rho, SNR)',
    receiver='SPg_flat FULL (genie delays, flat prior, K = 8 L): IntervenedRefine(mode=full) under dpss_rx.vector_prior, '
             'interventions._instrumented(rounds=2, iterations=20, gain_mode=joint); outputs unmodified',
    estimators='W receiver white refit (recomputed); Wt white with realised power; G genie GLS C = H_t S H_t^H + noise I; '
               'A achievable GLS (round 1 from W, round >= 2 from the previous detector gains)',
    S='round 1: mean(v) I (DAFT unitarity asserted); otherwise Dh diag(v) Dh^H',
    eps='eps_of semantics of driver_c1: ||H - H^||_F^2 / N')
_SIG = inspect.signature(dpss_rx.DpssRefine.__call__)
_DH = {}


# ------------------------------------------------------------------------ linear algebra
def tap_operator(n, c1v, taps):
    """N x N time-domain operator of dpss_rx.Design: y[k] = sum_l a_l[k] x[(k - l) mod n] (CPP wrap phase for k - l < 0)."""
    H = np.zeros((n, n), complex)
    k = np.arange(n)
    for delay, a in taps.items():
        src = k - int(delay)
        H[k, src % n] += np.asarray(a, complex) * np.where(src < 0, np.exp(2j * np.pi * c1v * (n * n + 2 * n * src)), 1.)
    return H


def inv_daft_matrix(n, c1v, c2v):
    from physical import daft
    key = (int(n), float(c1v), float(c2v))
    if key not in _DH:
        eye = np.eye(n, dtype=complex)
        Dh = np.stack([daft(eye[:, j], c1v, c2v, True) for j in range(n)], axis=1)
        err = float(np.max(np.abs(Dh @ Dh.conj().T - eye)))
        if err > 1e-9:
            raise ValueError(f'inverse DAFT not unitary (max |Dh Dh^H - I| = {err:.2e})')
        _DH[key] = Dh
    return _DH[key]


def white(des, idx, tau, s2):
    return dpss_rx._ridge(des, idx, s2, 1. / tau)[0]


def gls(des, idx, tau, C):
    Lc = np.linalg.cholesky(C)
    Bw = solve_triangular(Lc, des.B[:, idx], lower=True, check_finite=False)
    Yw = solve_triangular(Lc, des.Y, lower=True, check_finite=False)
    h = np.linalg.solve(Bw.conj().T @ Bw + np.diag(1. / tau), Bw.conj().T @ Yw)
    if not np.isfinite(h).all():
        raise FloatingPointError('nonfinite GLS solution')
    return h


def taps_of(snap, h):
    return {delay: snap['M'][:, sl] @ np.asarray(h, complex)[sl] for delay, sl in snap['taps']}


# ------------------------------------------------------------------------ diagnostic refiner
class SGRefine(c1i.IntervenedRefine):
    """IntervenedRefine(mode='full') whose every call is followed by the side estimates W / Wt / G / A (outputs untouched)."""

    def __init__(self, delays, cfg, a_true):
        super().__init__(delays, cfg, mode='full', lam=None, a_true=None)
        self.truth = a_true
        self.n = len(next(iter(a_true.values())))
        self.e_real = sum(float(np.vdot(a, a).real) for a in a_true.values()) / self.n
        self.diag = {}

    def __call__(self, *args, **kwargs):
        ch, detail = super().__call__(*args, **kwargs)
        bound = _SIG.bind(self, *args, **kwargs)
        bound.apply_defaults()
        self.diag.update(self.side(len(self.snaps), bound.arguments, ch))
        return ch, detail

    def side(self, r, a, ch):
        y, pilot, mu, v = (np.asarray(a[k]) for k in ('y', 'pilot', 'mu', 'v'))
        c1v, c2v, noise, n = a['c1'], a['c2'], float(a['noise']), self.n
        v = np.asarray(v, float)
        log, snap = self.log[-1], self.snaps[-1]
        if log['n_taps_kept'] != log['n_taps_in']:
            raise RuntimeError('flat prior with drop 0 must keep every tap')
        taps = [dict(delay=t['delay'], c=t['c'], W=t['W'], D=t['D']) for t in self.prev['taps']]
        des = dpss_rx.Design(y, pilot, mu, taps, c1v, c2v)
        idx = np.arange(des.C)
        tau = np.asarray(ch.prior_var, float)
        if tau.shape != (des.C,):
            raise RuntimeError('prior / design size mismatch')
        Dh = inv_daft_matrix(n, c1v, c2v)
        vbar = float(v.mean())
        uniform = bool(np.ptp(v) <= 1e-12 * max(vbar, 1e-300))
        S = None if uniform else (Dh * v[None, :]) @ Dh.conj().T

        def cov(Ht):
            HS = vbar * Ht if uniform else Ht @ S
            C = HS @ Ht.conj().T
            C[np.diag_indices(n)] += noise
            return C

        hW = white(des, idx, tau, float(log['s2']))
        hWt = white(des, idx, tau, noise + vbar * self.e_real)
        hG = gls(des, idx, tau, cov(tap_operator(n, c1v, self.truth)))
        src = hW if r == 1 else np.asarray(a['gs'], complex)
        if src.shape != (des.C,):
            raise RuntimeError('previous-round gains do not match the design columns')
        hA = gls(des, idx, tau, cov(tap_operator(n, c1v, taps_of(snap, src))))
        eps = {k: c1.eps_of(snap, h, self.truth, n) for k, h in (('W', hW), ('Wt', hWt), ('G', hG), ('A', hA))}
        return {f'eps_W{r}': eps['W'], f'eps_Wt{r}': eps['Wt'], f'eps_G{r}': eps['G'], f'eps_A{r}': eps['A'],
                f'w_closure{r}': float(np.max(np.abs(hW - np.asarray(ch.gains, complex)))),
                f'v_mean{r}': vbar, f'v_cv{r}': float(v.std() / max(vbar, 1e-300)), f'v_uniform{r}': uniform,
                f's2_{r}': float(log['s2'])}


def ht_closure(ctx, raw, rho):
    """Relative misfit of the time-domain tap operator built from the true tap sequences on the noiseless observation."""
    from physical import daft
    s = ctx.system
    scale = np.sqrt(2. * (1. - rho))
    x = (np.asarray(raw['pilot']) + np.asarray(raw['data'])) / scale
    yt = daft(np.asarray(raw['noiseless']) / scale, s.c1, s.c2, True)
    return yt, daft(x, s.c1, s.c2, True)


def run_sg(ctx, obs, truth, genie_delays, cfg, a_true, raw, rho):
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    yt, xt = ht_closure(ctx, raw, rho)
    clo = float(np.linalg.norm(yt - tap_operator(n, ctx.system.c1, a_true) @ xt) / np.linalg.norm(yt))
    refiner = SGRefine(genie_delays, cfg, a_true)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1i_full', rounds=ROUNDS, iterations=ITERS,
                                            gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != ROUNDS:
        raise RuntimeError(f'expected {ROUNDS} refits, got {len(refiner.snaps)}')
    diag = dict(refiner.diag, ht_closure=clo, e_real_taps=refiner.e_real, rounds=ROUNDS, T=ITERS)
    for r, snap in enumerate(refiner.snaps, start=1):
        diag[f'eps_ce{r}'] = c1.eps_of(snap, snap['h'], a_true, n)
        diag[f'eps_det{r}'] = c1.eps_of(snap, ar[f'r{r - 1}_gains'], a_true, n)
        diag.update(c1i.decision_diag(ctx, ar, truth, r))
    s1 = refiner.snaps[0]
    proj = np.zeros(len(s1['h']), complex)
    for delay, sl in s1['taps']:
        proj[sl] = np.linalg.lstsq(s1['M'][:, sl], a_true[delay], rcond=None)[0]
    diag['eps_proj'] = c1.eps_of(s1, proj, a_true, n)
    return dict(arm=ARM, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, diag=diag)


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--preset', choices=tuple(PRESETS), default=None)
    p.add_argument('--cells', default=None, help="'snr:rho:L,L,...;snr:rho:L,...' (overrides the preset)")
    p.add_argument('--frames', type=int, default=None)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=c1i.C1_MAP_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1sg'  # base.fingerprint keys cluster params on 'clustered' only
    return args


def resolve(args):
    pre = PRESETS.get(args.preset, {})
    cells = ib2.parse_cells(args.cells) if args.cells else pre.get('cells')
    frames = args.frames if args.frames else pre.get('frames')
    if not cells or not frames:
        raise ValueError('give --preset or both --cells and --frames')
    if any(L < 1 or L > 101 for (_, _, Ls) in cells for L in Ls):
        raise ValueError('unknown L')
    return cells, int(frames)


def code_md5():
    out = {name: ib.md5_file(HERE / name) for name in CODE_FILES}
    for name in ib.CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = ib.md5_file(module.__file__)
    return out


# --------------------------------------------------------------------- shard i/o (driver_c1ib2.run_shard with the SG arm)
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells, n_frames = resolve(args)
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1i.py', 'driver_c1ib.py', 'driver_c1ib2.py', 'driver_c1sg.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, c1i=c1i.C1I_PARAMS, c1sg=SG_PARAMS,
                  resolved=dict(cells=[[s, r, Ls] for (s, r, Ls) in cells], arm=ARM, frames=n_frames),
                  code_md5=code_md5(), entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest,
                  dpss_defaults=dpss_rx.CFG_DEFAULT)
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
    done = c1i.load_done(jsonl, [ARM])
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    all_L = sorted({L for (_, _, Ls) in cells for L in Ls})
    frames = list(range(args.frame_offset, args.frame_offset + n_frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None
            for L in all_L:
                todo = [(s, r) for (s, r, Ls) in cells if L in Ls
                        and (f'L{L:02d}', int(round(r * 1000)), int(round(s * 100)), frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, int(ctx.system.N_total))
                pair = None
                for rho in sorted({r for (_, r) in todo}):
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                    for snr in sorted({s for (s, r) in todo if r == rho}):
                        snr_centi = int(round(snr * 100))
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
                        genie = sorted(set(int(x) for x in truth['l_i']))
                        try:
                            res = run_sg(ctx, obs, truth, genie, cfg, a_true, raw, rho)
                            rows = [dict(head, arm=ARM, status='ok', **base.score(ctx, res, truth), **res['diag'])]
                        except Exception as error:  # recorded, never silently dropped
                            rows = [dict(head, arm=ARM, status='error', error=repr(error), trace=traceback.format_exc()[-1500:])]
                        base.append_rows(handle, rows)
                        n_cells += 1
                        r0 = rows[0]
                        print(f'[{time.perf_counter() - started:8.1f}s] c1sg snr={snr_centi} rho={rho} L={L} frame={frame} '
                              f"{r0['status']} W1 {r0.get('eps_W1', float('nan')):.4f} G1 {r0.get('eps_G1', float('nan')):.4f} "
                              f"W2 {r0.get('eps_W2', float('nan')):.4f} G2 {r0.get('eps_G2', float('nan')):.4f} "
                              f"({r0.get('seconds', 0.):.1f}s)", flush=True)
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
