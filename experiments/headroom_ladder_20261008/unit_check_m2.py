#!/usr/bin/env python
"""Unit checks for the M2 DPSS-BEM receiver (dpss_rx.py, driver_m2.py).  Run on deinlab, single thread, CPU.

V1  vector-prior detector: scalar_joint_cols with tau = 1/P reproduces the frozen twofft.scalar_joint(gain_mode='joint') (plain Channel and a
    multi-column general-tap channel); native.scalar_joint is restored after the context (also on exception) and delegates to the frozen
    function for channels without prior_var.
V2  (a) DPSS columns (dpss_rx.tap_columns) == M1 dpss_taps.dpss_basis * sqrt(N); orthogonality m^H m = N I; with ORACLE exact coefficients
    (m_d^H a / N) the per-column representation reproduces the M1 projected taps and, through the frozen fixed-H TF20R2 detector, the stored
    M1 rows (info_errors identical, |logloss diff| <= 1e-9) on a few frames/orders.
V3  (b) joint mode with oracle band + true-H init: DpssRefine subclass with true delays, oracle (c, W, D), true-tap Slepian prior and true
    projected coefficients as initial gains, scalar_joint_cols joint mode (TF20R2, LDPC50) vs the M1 fixed-H P_D arm and A3 on the same frames.
V4  (c) priors finite / positive, Slepian eigenvalues in (0,1], ridge conditions finite, over frames x configs x {6, 11} dB x {full, adapt}.
V5  (d) count-blind: AST scan of dpss_rx.py / run_m for truth identifiers; observation key-access log; bit-exact determinism of repeated runs.
V6  full-basis representation floor: projection misfit of true taps on (c=0, W=2.5, D=8), per config.
usage: unit_check_m2.py <out.json> <m1_rows_dir>[,<m1_rows_dir>...] [expected|realized]   (default realized: V2 compares with the stored M1 rows,
       which are realized-law; under 'expected' V2 keeps the basis/tap/orthogonality checks and skips the stored-row comparison)
"""
import ast
import glob
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver  # noqa: E402
import driver_f2 as f2  # noqa: E402
import driver_m2 as m2  # noqa: E402
import dpss_rx  # noqa: E402
import dpss_taps  # noqa: E402
import orders  # noqa: E402
import tapchannel  # noqa: E402

ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
N = 1024
FORBIDDEN = {'truth', 'l_i', 'k_real', 'g_i', 'cluster', 'coded', 'info', 'noiseless', 'channel_seed', 'tap_delays', 'rays_per_tap',
             'physical_channel_matrix', 'truth_from_raw', 'cluster_paths'}


def make_obs(ctx, config, frame, snr, cache):
    msg = cache.setdefault(frame, driver.cluster_message(ctx, ENTROPY, frame))
    raw_base, diag = driver.cluster_base(ctx, msg, driver.draw_cluster_geometry(ENTROPY, frame), config)
    raw = driver.cluster_at_snr(raw_base, snr)
    return driver.observe(raw, .5, snr), driver.truth_from_raw(raw, diag)


def column_channel(n, c1, c2, cols_by_tap):
    """cols_by_tap: [(delay, M (n,D), coef (D,))] -> one path per column (repeated delays), gains = coef."""
    delays = np.concatenate([[d] * M.shape[1] for d, M, _ in cols_by_tap]).astype(int)
    ch = tapchannel.tap_channel_class()(n, c1, c2, delays, np.zeros(len(delays)), np.concatenate([c for _, _, c in cols_by_tap]))
    object.__setattr__(ch, 'tap_mods', np.ascontiguousarray(np.hstack([M for _, M, _ in cols_by_tap])))
    return ch


def m1_rows(dirs, snr_centi, arms, cells):
    want = {(c, f, a) for c, f in cells for a in arms}
    out = {}
    for d in dirs:
        for fpath in sorted(glob.glob(d + '/rows_shard*.jsonl')):
            with open(fpath) as fh:
                for line in fh:
                    if f'"snr_centi_db": {snr_centi},' not in line or '"arm": "P' not in line:
                        continue
                    r = json.loads(line)
                    k = (r['config'], r['frame'], r['arm'])
                    if k in want and r['status'] == 'ok':
                        out[k] = r
    return out


class OracleRefine(dpss_rx.DpssRefine):
    """Unit-check ONLY: true delays, oracle band, true-tap energies / projections (never reachable from run_m's default path)."""

    def __init__(self, cfg, truth, n, order):
        super().__init__(cfg)
        self.groups = sorted(orders.tap_groups(truth['l_i'], truth['k_real'], truth['g_i']).items())
        self.n, self.order = n, order
        self.a = {d: orders.tap_sequence(nu, g, n) for d, (nu, g) in self.groups}

    def _taps(self):
        taps = []
        for d, (nu, g) in self.groups:
            c, _, W = dpss_taps.tap_band(nu, g)
            taps.append(dict(delay=int(d), c=c, W=W, D=self.order, E=float(np.vdot(self.a[d], self.a[d]).real / self.n)))
        return taps

    def initial_taps(self, ls, gs):
        return self._taps()

    def next_taps(self, gs):
        return self._taps()

    def first_round_energies(self, des, taps, noise, vbar):
        pass  # E already set from the truth

    def init_gains(self, des, idx, tau, s2, kept_taps):
        h = np.concatenate([des.M[:, t['sl']].conj().T @ self.a[t['delay']] / self.n for t in kept_taps])
        return h, np.eye(len(h))


def main():
    out = Path(sys.argv[1])
    m1_dirs = sys.argv[2].split(',')
    law = sys.argv[3] if len(sys.argv) > 3 else 'realized'
    args = f2.parse_args(['--mode', 'generate', '--out', str(out.parent), '--frames', '1', '--entropy-hex', ENTROPY, '--snr-list', '8',
                          '--power-norm', law])
    ctx = m2.load_context(args)
    import twofft
    import native_twofft
    from physical import Channel
    s = ctx.system
    n = int(s.N_total)
    rng = np.random.default_rng(5)
    rep = dict(power_norm=law)
    cache = {}

    # ---------------------------------------------------------------- V1
    v1 = []
    obs, truth = make_obs(ctx, 'N4b', 1, 8.0, cache)
    ch_plain = Channel(n, s.c1, s.c2, truth['l_i'], truth['k_real'], truth['g_i'])
    M3 = np.hstack([dpss_rx.tap_columns(n, c, W, 3)[0] for c, W in ((0., 1.2), (.3, 2.), (-.4, .7))])
    gains3 = (rng.standard_normal(9) + 1j * rng.standard_normal(9)) * .2
    ch_gen = column_channel(n, s.c1, s.c2, [(0, M3[:, :3], gains3[:3]), (0, M3[:, 3:6], gains3[3:6]), (17, M3[:, 6:], gains3[6:])])
    for name, ch in (('plain_channel', ch_plain), ('general_columns', ch_gen)):
        P = ch.p
        fr = twofft.scalar_joint(obs['y'], obs['pilot'], ch, obs['sigma2'], pd=.5, prior=None, iterations=20, damping=.3, gain_mode='joint')
        vc = dpss_rx.scalar_joint_cols(obs['y'], obs['pilot'], ch, obs['sigma2'], np.full(P, 1. / P), pd=.5, prior=None, iterations=20)
        rec = dict(channel=name, P=P)
        for key in ('extrinsic', 'app', 'mu', 'variance', 'gains'):
            rec['max_abs_diff_' + key] = float(np.max(np.abs(np.asarray(fr[key]) - np.asarray(vc[key]))))
        rec['max_abs_value_extrinsic'] = float(np.max(np.abs(fr['extrinsic'])))
        assert max(v for k, v in rec.items() if k.startswith('max_abs_diff')) < 1e-7 * max(1., rec['max_abs_value_extrinsic']), rec
        v1.append(rec)
    frozen_fn = native_twofft.scalar_joint
    with dpss_rx.vector_prior(native_twofft):
        assert native_twofft.scalar_joint is not frozen_fn
        routed = native_twofft.scalar_joint(obs['y'], obs['pilot'], ch_plain, obs['sigma2'], pd=.5, iterations=20, gain_mode='joint')
        assert np.array_equal(routed['extrinsic'], twofft.scalar_joint(obs['y'], obs['pilot'], ch_plain, obs['sigma2'], pd=.5, iterations=20,
                                                                       gain_mode='joint')['extrinsic'])
    assert native_twofft.scalar_joint is frozen_fn
    try:
        with dpss_rx.vector_prior(native_twofft):
            raise RuntimeError('x')
    except RuntimeError:
        pass
    assert native_twofft.scalar_joint is frozen_fn
    rep['V1'] = dict(rows=v1, restored=True, delegates_to_frozen_without_prior_var=True)
    print('V1 ok', [round(max(v for k, v in r.items() if k.startswith('max_abs_diff')), 12) for r in v1], flush=True)

    # ---------------------------------------------------------------- V2
    cells = [('D1', 0), ('D1', 1), ('N4a', 0), ('N4a', 1), ('N4b', 0), ('N4b', 1), ('N4b', 2), ('J4', 0), ('J4', 1), ('J4', 2)]
    orders_chk = (3, 6, 8)
    stored = m1_rows(m1_dirs, 800, tuple(f'P{d}' for d in orders_chk), cells)
    v2, n_compared = [], 0
    for config, frame in cells:
        obs, truth = make_obs(ctx, config, frame, 8.0, cache)
        p = dpss_taps.project_taps(truth['l_i'], truth['k_real'], truth['g_i'], orders_chk, n)
        groups = sorted(orders.tap_groups(truth['l_i'], truth['k_real'], truth['g_i']).items())
        for D in orders_chk:
            cols_by_tap, taps_sum, basis_dev, gram_dev = [], [], 0., 0.
            for i, (d, (nu, g)) in enumerate(groups):
                c, _, W = dpss_taps.tap_band(nu, g)
                M, lam = dpss_rx.tap_columns(n, c, W, D)
                E_m1 = dpss_taps.dpss_basis(n, c, W, D)
                basis_dev = max(basis_dev, float(np.max(np.abs(M / np.sqrt(n) - E_m1))))
                gram_dev = max(gram_dev, float(np.max(np.abs(M.conj().T @ M / n - np.eye(D)))))
                a = orders.tap_sequence(nu, g, n)
                coef = M.conj().T @ a / n
                cols_by_tap.append((int(d), M, coef))
                taps_sum.append(M @ coef)
            tap_dev = float(np.max(np.abs(np.stack(taps_sum, 1) - p['by_order'][D]['taps'])))
            assert basis_dev < 1e-13 and gram_dev < 1e-12 and tap_dev < 1e-9, (config, frame, D, basis_dev, gram_dev, tap_dev)
            ch = column_channel(n, s.c1, s.c2, cols_by_tap)
            res = ctx.wrappers.run_fixed_channel(obs, s, ctx.code, ctx.native, channel=ch, detector='tf')
            dec = res.decoder
            sc = driver.score(ctx, dict(decoded=dec['decoded'], llr=dec['incoming_llr'], iters=int(dec['iterations']), seconds=0.,
                                        triggered=None), truth)
            rec = dict(config=config, frame=frame, D=D, n_paths=int(ch.p), basis_dev=basis_dev, gram_dev=gram_dev, tap_dev=tap_dev,
                       info_errors=sc['info_errors'], logloss_bits=sc['logloss_bits'])
            ref = stored.get((config, frame, f'P{D}')) if law == 'realized' else None
            if ref is not None:
                rec.update(m1_info_errors=ref['info_errors'], m1_logloss_bits=ref['logloss_bits'],
                           logloss_abs_diff=abs(ref['logloss_bits'] - sc['logloss_bits']))
                assert ref['info_errors'] == sc['info_errors'] and rec['logloss_abs_diff'] < 1e-9, rec
                n_compared += 1
            v2.append(rec)
    rep['V2'] = dict(rows=v2, n_vs_stored_m1_rows=n_compared)
    assert law != 'realized' or n_compared >= 12, n_compared
    print('V2 ok; compared with stored M1 rows:', n_compared, flush=True)

    # ---------------------------------------------------------------- V3
    v3 = []
    for config, frames in (('D1', range(0, 8)), ('N4b', range(0, 8)), ('J4', range(0, 8))):
        for frame in frames:
            obs, truth = make_obs(ctx, config, frame, 8.0, cache)
            order = 3 if config == 'D1' else 8
            a3 = driver.run_a3(ctx, obs, truth)[0]
            p = dpss_taps.project_taps(truth['l_i'], truth['k_real'], truth['g_i'], (order,), n)
            fixed = ctx.wrappers.run_fixed_channel(obs, s, ctx.code, ctx.native, detector='tf',
                                                   channel=tapchannel.make_tap_channel(n, s.c1, s.c2, p['delays'], p['by_order'][order]['taps']))
            fixed_sc = driver.score(ctx, dict(decoded=fixed.decoder['decoded'], llr=fixed.decoder['incoming_llr'],
                                              iters=int(fixed.decoder['iterations']), seconds=0., triggered=None), truth)
            ref = OracleRefine(dict(mode='full', kappa=1.0, drop=0.0), truth, n, order)
            r = m2.run_m(ctx, obs, 'oracle_joint', {}, refiner=ref)
            sc = driver.score(ctx, r, truth)
            v3.append(dict(config=config, frame=frame, D=order, a3_err=driver.score(ctx, a3, truth)['info_errors'],
                           a3_ll=driver.score(ctx, a3, truth)['logloss_bits'], fixedPD_err=fixed_sc['info_errors'],
                           fixedPD_ll=fixed_sc['logloss_bits'], joint_err=sc['info_errors'], joint_ll=sc['logloss_bits'],
                           joint_misfit=m2.tap_misfit(truth, n, ref, r['gains']), seconds=r['seconds']))
            print('V3', config, frame, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in v3[-1].items() if k.endswith(('err', 'll', 'misfit'))},
                  flush=True)
    rep['V3'] = dict(rows=v3)
    summ = {}
    for config in ('D1', 'N4b', 'J4'):
        rs = [r for r in v3 if r['config'] == config]
        summ[config] = dict(frames=len(rs), a3_ll=float(np.mean([r['a3_ll'] for r in rs])), fixedPD_ll=float(np.mean([r['fixedPD_ll'] for r in rs])),
                            joint_ll=float(np.mean([r['joint_ll'] for r in rs])), a3_fail=sum(r['a3_err'] > 0 for r in rs),
                            fixedPD_fail=sum(r['fixedPD_err'] > 0 for r in rs), joint_fail=sum(r['joint_err'] > 0 for r in rs),
                            joint_misfit_median=float(np.median([r['joint_misfit'] for r in rs])))
    rep['V3_summary'] = summ
    print('V3 summary', json.dumps(summ), flush=True)

    # ---------------------------------------------------------------- V4
    v4 = dict(n_runs=0, tau_min=np.inf, tau_max=0., cond_max=0., s2_min=np.inf, lam_min=np.inf, lam_max=0., nonfinite=0)
    for W, D in ((.5, 3), (1., 4), (1.5, 5), (2., 6), (2.5, 7), (2.5, 8)):
        lam = dpss_rx.slepian(n, W, D)[1]
        v4['lam_min'], v4['lam_max'] = min(v4['lam_min'], float(lam.min())), max(v4['lam_max'], float(lam.max()))
        assert (lam > 0).all() and (lam <= 1 + 1e-9).all() and np.isfinite(lam).all(), (W, D, lam)
    for config in ('D1', 'N4a', 'N4b', 'J4', 'J8'):
        for frame in range(8):
            for snr in (6., 11.):
                obs, truth = make_obs(ctx, config, frame, snr, cache)
                for mode in ('full', 'adapt'):
                    r = m2.run_m(ctx, obs, mode, dict(mode=mode, drop=0.01))
                    for lg in r['refiner'].log:
                        v4['n_runs'] += 1
                        v4['tau_min'], v4['tau_max'] = min(v4['tau_min'], lg['tau_min']), max(v4['tau_max'], lg['tau_max'])
                        v4['cond_max'], v4['s2_min'] = max(v4['cond_max'], lg['cond_Q']), min(v4['s2_min'], lg['s2'])
                        ok = all(np.isfinite(x) for x in (lg['tau_min'], lg['tau_max'], lg['tau_sum'], lg['cond_Q'], lg['s2'])) and lg['tau_min'] > 0
                        v4['nonfinite'] += int(not ok)
    assert v4['nonfinite'] == 0 and v4['tau_min'] > 0 and np.isfinite(v4['cond_max']), v4
    rep['V4'] = v4
    print('V4 ok', v4, flush=True)

    # ---------------------------------------------------------------- V5
    src = Path(dpss_rx.__file__).read_text()
    names = {n_.id for n_ in ast.walk(ast.parse(src)) if isinstance(n_, ast.Name)} | {n_.attr for n_ in ast.walk(ast.parse(src))
                                                                                   if isinstance(n_, ast.Attribute)}
    names |= {a.arg for n_ in ast.walk(ast.parse(src)) if isinstance(n_, ast.arguments) for a in n_.args + n_.kwonlyargs}
    hit = sorted(names & FORBIDDEN)
    assert not hit, hit
    run_m_src = ast.parse(Path(m2.__file__).read_text())
    fn = [f for f in ast.walk(run_m_src) if isinstance(f, ast.FunctionDef) and f.name == 'run_m'][0]
    run_m_names = {n_.id for n_ in ast.walk(fn) if isinstance(n_, ast.Name)} | {a.arg for a in fn.args.args}
    assert 'truth' not in run_m_names and not (run_m_names & FORBIDDEN), sorted(run_m_names & FORBIDDEN)

    class Logged(dict):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.accessed = set()

        def __getitem__(self, key):
            self.accessed.add(key)
            return super().__getitem__(key)

        def get(self, key, default=None):
            self.accessed.add(key)
            return super().get(key, default)

    obs, truth = make_obs(ctx, 'N4b', 3, 8., cache)
    lo = Logged(obs)
    r1 = m2.run_m(ctx, lo, 'x', dict(mode='adapt', drop=0.01))
    r2 = m2.run_m(ctx, dict(obs), 'x', dict(mode='adapt', drop=0.01))
    assert lo.accessed <= {'y', 'pilot', 'sigma2'}, lo.accessed
    assert np.array_equal(r1['llr'], r2['llr']) and np.array_equal(r1['decoded'], r2['decoded'])
    rep['V5'] = dict(forbidden_identifiers_in_dpss_rx=hit, run_m_names=sorted(run_m_names), obs_keys_accessed=sorted(lo.accessed),
                     bit_exact_repeat=True)
    print('V5 ok', sorted(lo.accessed), flush=True)

    # ---------------------------------------------------------------- V6
    v6 = {}
    for config in ('D1', 'N4a', 'N4b', 'J4', 'J8'):
        mis = []
        for frame in range(100):
            geom = driver.draw_cluster_geometry(ENTROPY, frame)
            pa = driver.cluster_paths(geom, config)
            num = den = 0.
            for d, (nu, g) in orders.tap_groups(pa['l_i'], pa['k_real'], pa['g_i']).items():
                a = orders.tap_sequence(nu, g, n)
                M, _ = dpss_rx.tap_columns(n, 0., 2.5, 8)
                r = a - M @ (M.conj().T @ a / n)
                num += float(np.vdot(r, r).real)
                den += float(np.vdot(a, a).real)
            mis.append(num / den)
        v6[config] = dict(median=float(np.median(mis)), p95=float(np.percentile(mis, 95)), max=float(np.max(mis)))
    rep['V6_full_basis_misfit'] = v6
    print('V6', json.dumps(v6), flush=True)
    rep['status'] = 'pass'
    out.write_text(json.dumps(rep, indent=1, default=driver.to_jsonable, allow_nan=False) + '\n')
    print('all pass', flush=True)


if __name__ == '__main__':
    main()
