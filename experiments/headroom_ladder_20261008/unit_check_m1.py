#!/usr/bin/env python
"""Unit checks for the M1 DPSS oracle (dpss_taps.py, tapchannel.py, driver_m1.py).  Run on deinlab, single thread, CPU.

U1  DPSS basis: orthonormal (E^H E = I), nested in D, band concentration, for W in {0.5 .. 4.7}; every ray inside [c-W, c+W].
U2  misfit identity: tap-sequence misfit == explicit ||H_true - H_alt||_F^2/||H_true||_F^2, H_true = physical_channel_matrix,
    H_alt = TapChannel operator applied to the identity (D in 1,2,3,4,6,8; N4a/N4b/J4/D1); misfit monotone non-increasing in D.
U3  exact taps: TapChannel(exact) == physical H (rel Frobenius ~1e-15); adjoint == H^H; <y,Hx> = <H^H y,x>; TapChannel.apply ==
    Channel(true rays).apply.
U4  GeneralTimePathOps vs frozen TimePathOps on the same operator: responses_time@h, adjoint_time, power, B^H st agree to 1e-12;
    plain Channel path unchanged (class falls through to the frozen __init__).
U5  end-to-end: GX (exact taps, general-tap operator) vs A3 (true rays, frozen path) on real frames, fixed-H TF20R2:
    identical info_errors/decode, max |LLR diff|, logloss diff.
U6  Gram generalization for M2 (soft-data ridge Gamma): Gamma_ij = e^{2j pi c1 (l_i^2-l_j^2)} fft(v)[(l_j-l_i)%N]
    (1/N) sum_k conj(m_i[k]) m_j[k] e^{4j pi c1 k (l_j-l_i)}, symmetrized, equals physical.projected_variance for exponentials.
usage: unit_check_m1.py <out.json>
"""
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver  # noqa: E402
import driver_f2 as f2  # noqa: E402
import driver_m1 as m1  # noqa: E402
import dpss_taps  # noqa: E402
import orders  # noqa: E402
import tapchannel  # noqa: E402

ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
N = 1024


def frame_paths(frame, config):
    return driver.cluster_paths(driver.draw_cluster_geometry(ENTROPY, frame), config)


def make_obs(ctx, config, frame, snr, msg_cache):
    msg = msg_cache.setdefault(frame, driver.cluster_message(ctx, ENTROPY, frame))
    raw_base, diag = driver.cluster_base(ctx, msg, driver.draw_cluster_geometry(ENTROPY, frame), config)
    raw = driver.cluster_at_snr(raw_base, snr)
    return driver.observe(raw, .5, snr), driver.truth_from_raw(raw, diag)


def main():
    out = Path(sys.argv[1])
    args = f2.parse_args(['--mode', 'generate', '--out', str(out.parent), '--frames', '1', '--entropy-hex', ENTROPY,
                          '--snr-list', '8'])
    ctx = m1.load_context(args)
    import twofft
    General = twofft.TimePathOps
    Frozen = General.__mro__[1]
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    rng = np.random.default_rng(11)
    rep = {}

    # ---- U1 ----
    u1 = []
    for W in (0.5, 0.9, 1.7, 3.0, 4.7):
        E = dpss_taps.dpss_basis(N, 0.37, W, 8)
        gram = float(np.max(np.abs(E.conj().T @ E - np.eye(8))))
        from scipy.signal.windows import dpss
        _, ratios = dpss(N, W, 8, sym=True, norm=2, return_ratios=True)
        u1.append(dict(W=W, gram_dev=gram, concentration=[float(x) for x in ratios]))
        assert gram < 1e-12, (W, gram)
    cover = []
    for config in ('N4a', 'N4b', 'J4'):
        for f in range(20):
            pa = frame_paths(f, config)
            for d, (nu, g) in orders.tap_groups(pa['l_i'], pa['k_real'], pa['g_i']).items():
                c, half, W = dpss_taps.tap_band(nu, g)
                cover.append(float(np.max(np.abs(nu - c)) - W))
    assert max(cover) < 0 and abs(max(cover) + 0.5) < 1e-9
    rep['U1'] = dict(rows=u1, max_ray_offset_minus_W=max(cover))
    print('U1 ok', flush=True)

    # ---- U2 / U3 ----
    Ds = (1, 2, 3, 4, 6, 8)
    u2, worst = [], 0.
    x = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    y = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    u3 = []
    for config, frames in (('D1', range(0, 3)), ('N4a', range(3, 7)), ('N4b', range(7, 12)), ('J4', range(12, 17))):
        for f in frames:
            pa = frame_paths(f, config)
            l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
            ht = ctx.physical_channel_matrix(n, s.c1, s.c2, l, nu, g, prefix_length=prefix)
            p = dpss_taps.project_taps(l, nu, g, Ds, n)
            prev = np.inf
            for D in Ds:
                ch = tapchannel.make_tap_channel(n, s.c1, s.c2, p['delays'], p['by_order'][D]['taps'])
                ha = tapchannel.tap_matrix(ch)
                mm = float(np.linalg.norm(ht - ha) ** 2 / np.linalg.norm(ht) ** 2)
                mis = p['by_order'][D]['misfit']
                worst = max(worst, abs(mm - mis))
                assert mis <= prev * (1 + 1e-9) + 1e-30, (config, f, D, mis, prev)
                prev = mis
                u2.append(dict(config=config, frame=f, D=D, misfit_tap=mis, misfit_matrix=mm))
            ch = tapchannel.make_tap_channel(n, s.c1, s.c2, p['delays'], p['exact_taps'])
            ha = tapchannel.tap_matrix(ch)
            rel_h = float(np.linalg.norm(ht - ha) / np.linalg.norm(ht))
            ct = ctx.Channel(n, s.c1, s.c2, l, nu, g)
            rel_apply = float(np.linalg.norm(ch.apply(x) - ct.apply(x)) / np.linalg.norm(ct.apply(x)))
            rel_adj = float(np.linalg.norm(ch.adjoint(y) - ha.conj().T @ y) / np.linalg.norm(ha.conj().T @ y))
            dot = abs(np.vdot(y, ch.apply(x)) - np.vdot(ch.adjoint(y), x)) / abs(np.vdot(y, ch.apply(x)))
            u3.append(dict(config=config, frame=f, rel_H=rel_h, rel_apply_vs_Channel=rel_apply, rel_adjoint=rel_adj,
                           rel_dot_test=float(dot)))
            assert max(rel_h, rel_apply, rel_adj, dot) < 1e-11, u3[-1]
    rep['U2_max_abs_diff_misfit'] = worst
    rep['U2_rows'] = u2
    rep['U3_rows'] = u3
    assert worst < 1e-10, worst
    print('U2 ok', worst, flush=True)
    print('U3 ok', max(max(r['rel_H'], r['rel_apply_vs_Channel'], r['rel_adjoint'], r['rel_dot_test']) for r in u3), flush=True)

    # ---- U4 ----
    u4 = []
    for config, f in (('N4b', 5), ('J4', 14)):
        pa = frame_paths(f, config)
        l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
        p = dpss_taps.project_taps(l, nu, g, (3,), n)
        ct = ctx.Channel(n, s.c1, s.c2, l, nu, g)
        tc = tapchannel.make_tap_channel(n, s.c1, s.c2, p['delays'], p['exact_taps'])
        xt = rng.standard_normal(n) + 1j * rng.standard_normal(n)
        z = rng.standard_normal(n) + 1j * rng.standard_normal(n)
        fo, fg = Frozen(ct), General(tc)
        a = fo.responses_time(xt) @ ct.gains
        b = fg.responses_time(xt) @ tc.gains
        a2 = fo.adjoint_time(ct.gains, z)
        b2 = fg.adjoint_time(tc.gains, z)
        a3, b3 = fo.power(ct.gains), fg.power(tc.gains)
        plain = General(ct)
        rec = dict(config=config, frame=f, rel_B_h=float(np.linalg.norm(a - b) / np.linalg.norm(a)),
                   rel_adjoint=float(np.linalg.norm(a2 - b2) / np.linalg.norm(a2)), power_rel=float(abs(a3 - b3) / a3),
                   power_exact=float(b3), power_target=float(sum(np.vdot(c, c).real for c in p['exact_taps'].T) / n),
                   plain_channel_same=bool(np.array_equal(plain.phase, fo.phase) and np.array_equal(plain.R, fo.R)))
        assert max(rec['rel_B_h'], rec['rel_adjoint'], rec['power_rel']) < 1e-12 and rec['plain_channel_same'], rec
        assert abs(rec['power_exact'] - rec['power_target']) < 1e-12 * rec['power_target']
        u4.append(rec)
    rep['U4'] = u4
    print('U4 ok', flush=True)

    # ---- U5 ----
    msg_cache, u5 = {}, []
    for config, frames, snr in (('D1', range(0, 2), 7.0), ('N4b', range(0, 3), 8.0), ('J4', range(0, 3), 8.0),
                                ('N4a', range(0, 2), 8.0)):
        for f in frames:
            obs, truth = make_obs(ctx, config, f, snr, msg_cache)
            a3 = driver.run_a3(ctx, obs, truth)[0]
            gx = m1.run_arm(ctx, obs, truth, 'GX')
            sa, sg = driver.score(ctx, a3, truth), driver.score(ctx, gx, truth)
            dllr = float(np.max(np.abs(np.asarray(a3['llr']) - np.asarray(gx['llr']))))
            rec = dict(config=config, frame=f, snr=snr, a3_info_errors=sa['info_errors'], gx_info_errors=sg['info_errors'],
                       max_abs_llr_diff=dllr, logloss_diff=abs(sa['logloss_bits'] - sg['logloss_bits']),
                       a3_seconds=a3['seconds'], gx_seconds=gx['seconds'], gx_paths=gx['oracle_n_paths'],
                       a3_paths=int(len(truth['l_i'])))
            assert sa['info_errors'] == sg['info_errors'] and np.array_equal(a3['decoded'], gx['decoded'])
            assert dllr < 1e-6 and rec['logloss_diff'] < 1e-9, rec
            u5.append(rec)
            print('U5', config, f, rec['a3_info_errors'], f'{dllr:.2e}', flush=True)
    rep['U5'] = u5

    # ---- U6 ----
    from physical import projected_variance
    u6 = []
    for config, f in (('N4b', 5), ('J4', 14), ('D1', 1)):
        pa = frame_paths(f, config)
        l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
        v = rng.random(n) * .5
        ref = projected_variance(v, l, nu, s.c1)
        k = np.arange(n)
        M = np.exp(2j * np.pi * np.outer(k, nu) / n)
        P = len(l)
        gam = np.zeros((P, P), complex)
        fv = np.fft.fft(v)
        for i in range(P):
            for j in range(P):
                dl = int(l[j] - l[i])
                gram = np.sum(np.conj(M[:, i]) * M[:, j] * np.exp(4j * np.pi * s.c1 * k * dl)) / n
                gam[i, j] = np.exp(2j * np.pi * s.c1 * (l[i] ** 2 - l[j] ** 2)) * fv[dl % n] * gram
        gam = (gam + gam.conj().T) / 2
        rec = dict(config=config, frame=f, P=P, rel=float(np.linalg.norm(gam - ref) / np.linalg.norm(ref)))
        assert rec['rel'] < 1e-10, rec
        u6.append(rec)
    rep['U6'] = u6
    rep['status'] = 'pass'
    out.write_text(json.dumps(rep, indent=1, default=driver.to_jsonable, allow_nan=False) + '\n')
    print('all pass', flush=True)


if __name__ == '__main__':
    main()
