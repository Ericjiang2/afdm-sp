#!/usr/bin/env python
"""Small, synthetic contracts for the C1-B directional-feedback kernel.

Run ``python -B unit_check_c1B.py --project PROJECT --out checks.json``.
The N=32 fixtures exercise the actual CPP/general-tap operator.  The N=1024
fixture calls only the scalar kernel; it does not run a coded receiver or
constitute B1/B2 empirical evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch

import numpy as np

import driver


HERE = Path(__file__).resolve().parent


def close(a, b, *, rtol=1e-8, atol=1e-10):
    a, b = np.asarray(a), np.asarray(b)
    return bool(np.allclose(a, b, rtol=rtol, atol=atol))


def error(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


class Checks:
    def __init__(self):
        self.rows = {}

    def add(self, name, passed, **detail):
        self.rows[name] = dict(pass_=bool(passed), **detail)
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)

    def write(self, path):
        failures = [k for k, v in self.rows.items() if not v['pass_']]
        report = dict(kind='synthetic-unit-contracts', checks=self.rows,
                      passed=len(failures) == 0, failures=failures)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        if path.stat().st_size >= 1_000_000:
            raise AssertionError('contract report exceeds 1 MB')
        return not failures


def fixture(n, *, nonuniform=True, seed=991):
    import dpss_rx
    import tapchannel
    from physical import daft

    rng = np.random.default_rng(seed + n)
    c1, c2 = 1 / (2 * n), 3 / (5 * n)
    # One delayed tap wraps through CPP; modulation varies both in time and
    # across DPSS columns.  K=6 is intentionally distinct from tap count 2.
    left = dpss_rx.tap_columns(n, .23, 1.7, 3)[0]
    right = dpss_rx.tap_columns(n, -.41, 1.3, 3)[0]
    mods = np.hstack((left, right))
    delays = np.array([0, 0, 0, 7, 7, 7])
    gains = np.array([.22+.06j, -.11+.15j, .07-.04j,
                      .13-.12j, -.09-.03j, .04+.08j])
    Channel = tapchannel.tap_channel_class()
    ch = Channel(n, c1, c2, delays, np.zeros(6), gains)
    object.__setattr__(ch, 'tap_mods', np.ascontiguousarray(mods))
    if nonuniform:
        tau = np.array([.07, .14, .28, .11, .22, .32])
    else:
        tau = np.full(6, 1 / 6)
    pilot = (.12 + .02j) * np.exp(2j*np.pi*np.arange(n)/n)
    data = np.sqrt(.25) * (rng.choice([-1, 1], n) +
                           1j*rng.choice([-1, 1], n))
    import twofft
    B = twofft.TimePathOps(ch).responses_time(daft(pilot + data, c1, c2, True))
    Y = B @ gains + .02 * (rng.normal(size=n) + 1j*rng.normal(size=n))
    y = daft(Y, c1, c2)
    prior = rng.normal(scale=.17, size=2*n)
    return ch, y, pilot, .08, tau, prior


def compare_outputs(a, b, *, tol=1e-10):
    keys = ('extrinsic', 'app', 'mu', 'variance', 'gains', 'gain_variance')
    diffs = {k: error(a[k], b[k]) for k in keys}
    return max(diffs.values()) <= tol, diffs


def check_reference(checks, kernel):
    import dpss_rx
    import twofft
    import native_twofft

    for n in (32, 1024):
        for nonuniform in (False, True):
            if n == 1024 and nonuniform:
                continue
            ch, y, pilot, noise, tau, prior = fixture(n, nonuniform=nonuniform)
            kwargs = dict(pd=.5, prior=prior, iterations=20 if n == 1024 else 3, damping=.3)
            ref = dpss_rx.scalar_joint_cols(y, pilot, ch, noise, tau, **kwargs)
            off = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='OFF', **kwargs)
            base = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='BASE', **kwargs)
            ok_off, diff_off = compare_outputs(off, ref)
            ok_base, diff_base = compare_outputs(base, ref)
            tag = f'n{n}_' + ('nonuniform' if nonuniform else 'uniform')
            checks.add('OFF_reference_' + tag, ok_off and off['fft_count'] == ref['fft_count'],
                       max_diff=max(diff_off.values()), fft=off['fft_count'])
            checks.add('BASE_reference_' + tag, ok_base and base['fft_count'] == ref['fft_count'],
                       max_diff=max(diff_base.values()), fft=base['fft_count'])
            if n == 32 and not nonuniform:
                frozen = twofft.scalar_joint(y, pilot, ch, noise, gain_mode='joint', **kwargs)
                ok, diffs = compare_outputs(ref, frozen)
                checks.add('original_cols_frozen_arithmetic', ok, max_diff=max(diffs.values()))
            # Capturing state is observational; final result must be bitwise
            # unchanged and the capture must not add transforms.
            if n == 32:
                cap = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode='BASE',
                                               capture_steps=(0, 1, 2), **kwargs)
                ok, diffs = compare_outputs(cap, base, tol=0)
                checks.add('BASE_capture_parity_' + tag,
                           ok and cap['fft_count'] == base['fft_count'],
                           max_diff=max(diffs.values()), fft=cap['fft_count'])

    original = native_twofft.scalar_joint
    try:
        with kernel.route(native_twofft, 'DIR'):
            checks.add('route_installed', native_twofft.scalar_joint is not original)
            raise RuntimeError('intentional scope test')
    except RuntimeError as exc:
        if str(exc) != 'intentional scope test':
            raise
    checks.add('route_restored_on_exception', native_twofft.scalar_joint is original)


def check_qpsk(checks):
    from messages import alphabet, marginal
    rng = np.random.default_rng(613)
    n, pd = 32, .5
    a, _ = alphabet(pd)
    r = .4*(rng.normal(size=n) + 1j*rng.normal(size=n))
    prior = rng.normal(scale=.6, size=2*n)
    vr = .39

    def mean(rr, vv):
        return marginal(-abs(rr[:, None] - a)**2/vv, prior, pd)[2]

    mu = mean(r, vr)
    vI = pd/2 - mu.real**2
    vQ = pd/2 - mu.imag**2
    ji, jq = 2*vI/vr, 2*vQ/vr
    kv = -2*(vI*r.real + 1j*vQ*r.imag)/vr**2
    t = 1e-6
    dr = rng.normal(size=n) + 1j*rng.normal(size=n)
    fd_r = (mean(r+t*dr, vr) - mean(r-t*dr, vr))/(2*t)
    model_r = ji*dr.real + 1j*jq*dr.imag
    fd_v = (mean(r, vr+t) - mean(r, vr-t))/(2*t)
    checks.add('QPSK_real_Jacobian', close(fd_r, model_r, rtol=1e-6, atol=1e-8),
               max_diff=error(fd_r, model_r))
    checks.add('QPSK_direct_temperature_9b', close(fd_v, kv, rtol=1e-6, atol=1e-8),
               max_diff=error(fd_v, kv))


def check_algebra(checks):
    rng = np.random.default_rng(42)
    q = rng.normal(size=64)
    q /= np.linalg.norm(q)
    u = rng.normal(size=64)*.23
    alpha = float(q@u)
    eps = .01
    den = (1-alpha)**2 + eps*float(u@u)
    c = (1-alpha)/den
    attenuation = eps*float(u@u)/den
    # Freeze u, q and c.  This is equation (13), not a probe of the full
    # re-computed correction map or a claim about B1 mechanism outcomes.
    t = 1e-4
    r = rng.normal(size=64)
    m = rng.normal(size=64)
    f = lambda z: z[0] + c*u*float(q@(z[0]-z[1]))
    deriv = (f((m+t*u, r+t*q)) - f((m-t*u, r-t*q)))/(2*t)
    checks.add('locked_coefficient_attenuation_13', close(deriv, attenuation*u),
               max_diff=error(deriv, attenuation*u), attenuation=attenuation)
    checks.add('rank_one_operator_bound', abs(c)*np.linalg.norm(u) <= 5+1e-12,
               norm=float(abs(c)*np.linalg.norm(u)))

    # Equation (19) with a nonorthogonal complex design and nonuniform prior.
    B = rng.normal(size=(32, 6)) + 1j*rng.normal(size=(32, 6))
    Y = rng.normal(size=32) + 1j*rng.normal(size=32)
    h = rng.normal(size=6) + 1j*rng.normal(size=6)
    tau = np.array([.07, .14, .28, .11, .22, .32])
    s2, damping = .21, .3
    beta = np.sum(abs(B)**2, axis=0)
    g = B.conj().T@(Y-B@h) - s2*h/tau
    p = g/(beta+s2/tau)
    aa = float(np.vdot(g,p).real)
    bb = float(np.vdot(B@p,B@p).real + s2*np.sum(abs(p)**2/tau))
    zeta = aa/bb
    L = lambda hh: float(np.vdot(Y-B@hh, Y-B@hh).real+s2*np.sum(abs(hh)**2/tau))
    change = L(h+damping*zeta*p)-L(h)
    target = -(2*damping-damping**2)*aa**2/bb
    checks.add('quadratic_descent_19', change <= 1e-9 and abs(change-target) < 1e-9,
               observed=change, predicted=target)
    g0 = B.conj().T@(Y-B@h) - s2*h/tau
    Q = B.conj().T@B + s2*np.diag(1/tau)
    stationary = np.linalg.solve(Q, B.conj().T@Y)
    gstationary = B.conj().T@(Y-B@stationary) - s2*stationary/tau
    checks.add('stationary_score', np.linalg.norm(gstationary) < 1e-10,
               residual=float(np.linalg.norm(gstationary)))
    variance = s2/(beta+s2/tau)
    checks.add('finite_tau_variance', np.isfinite(variance).all() and (variance > 0).all()
               and (variance < tau).all() and np.isfinite(g0).all(),
               min_variance=float(variance.min()))


def relative_error(actual, expected):
    return float(np.linalg.norm(actual-expected)/max(np.linalg.norm(expected), 1e-20))


def check_kernel_contracts(checks, kernel):
    from physical import daft
    rng = np.random.default_rng(1801)
    ch, y, pilot, noise, tau, prior = fixture(32)
    kwargs = dict(pd=.5, prior=prior, iterations=5, damping=.3)
    for mode, fft in (('BASE', 11), ('RAW', 16), ('GLOB', 16), ('DIR', 21)):
        result = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode=mode, **kwargs)
        captured = kernel.scalar_joint_cols(y, pilot, ch, noise, tau, mode=mode,
                                             capture_steps=(0, 1, 4), **kwargs)
        ok, diffs = compare_outputs(result, captured, tol=0)
        checks.add(mode+'_capture_and_FFT', ok and result['fft_count'] == fft
                   and captured['fft_count'] == fft, max_diff=max(diffs.values()), fft=fft)
        if mode != 'DIR':
            continue
        for index, snap in captured['snapshots'].items():
            pre = snap['pre_state']
            current = kernel._step_feedback(pre)
            checks.add(f'current_step_replay_{index}',
                       close(current['mu_ce'], snap['mu_ce'], rtol=0, atol=1e-14)
                       and close(current['rx'], snap['rx'], rtol=0, atol=1e-14))
            g = rng.normal(size=ch.p)+1j*rng.normal(size=ch.p)
            g *= .03/np.linalg.norm(g)
            pre = dict(pre, h_prev=pre['h']-g)
            current = kernel._step_feedback(pre)
            t = 1e-5
            plus = kernel._step_feedback(pre, pre['h']+t*g)
            minus = kernel._step_feedback(pre, pre['h']-t*g)
            fd = (plus['rx']-minus['rx'])/(2*t)
            fd_vr = (plus['vr']-minus['vr'])/(2*t)
            e_rx = relative_error(fd, current['ell'])
            e_vr = abs(fd_vr-current['dot_vr'])/max(abs(current['dot_vr']), 1e-20)
            norm = np.linalg.norm(current['ell'])
            raw_fd = (plus['mu_raw']-minus['mu_raw'])/(2*t)
            modeled = kernel._complex(current['coefficients']['u'])*norm
            e_mu = relative_error(raw_fd, modeled)
            checks.add(f'actual_tangent_FD_{index}', max(e_rx, e_vr, e_mu) <= 1e-5,
                       rx_relative_error=e_rx, vr_relative_error=e_vr, mu_relative_error=e_mu)
            locked = current['coefficients']
            plus = kernel._step_feedback(pre, pre['h']+t*g, locked=locked)
            minus = kernel._step_feedback(pre, pre['h']-t*g, locked=locked)
            fd_ce = (plus['mu_ce']-minus['mu_ce'])/(2*t)
            expected = modeled*locked['attenuation']
            # Normalize the response residual by the incoming raw response:
            # near-zero attenuated outputs otherwise magnify FD roundoff.
            err = float(np.linalg.norm(fd_ce-expected)/np.linalg.norm(modeled))
            checks.add(f'actual_locked_attenuation_{index}', err <= 1e-5,
                       residual_over_raw_response=err,
                       predicted_attenuation=locked['attenuation'],
                       measured_attenuation=float(np.linalg.norm(fd_ce)/np.linalg.norm(modeled)))
            h_new, vh_new, channel = kernel._channel_step(
                pre['o'], pre['Y'], pilot, snap['mu_ce'], snap['v_ce'],
                pre['h'], pre['vh'], tau, noise, .3)
            Bc = pre['o'].responses_time(daft(pilot+snap['mu_ce'], ch.c1, ch.c2, True))
            def objective(h):
                residual = pre['Y']-Bc@h
                return float(np.vdot(residual,residual).real+channel['s2']*np.sum(abs(h)**2/tau))
            change = objective(h_new)-objective(pre['h'])
            checks.add(f'actual_quadratic_descent_{index}', change <= 1e-10
                       and abs(change-channel['objective_change']) <= 1e-10,
                       observed=change, predicted=channel['objective_change'])
            checks.add(f'actual_variance_{index}', (vh_new > 0).all()
                       and (vh_new <= tau).all() and np.isfinite(snap['v_ce']).all()
                       and close(snap['v_ce'], snap['v_raw']+abs(snap['mu_ce']-snap['mu_raw'])**2))
        pre = dict(captured['snapshots'][0]['pre_state'])
        g = np.ones(ch.p, complex)*1e-6
        pre.update(h_prev=pre['h']-g, hb=-.3/.7*pre['h'])
        current = kernel._step_feedback(pre)
        plus = kernel._step_feedback(pre, pre['h']+1e-5*g)
        minus = kernel._step_feedback(pre, pre['h']-1e-5*g)
        checks.add('precision_floor_derivative', current['precision'] <= 1e-12
                   and current['dot_vr'] == 0 and plus['vr'] == minus['vr'] == 1e12)
        zero = captured['snapshots'][0]
        probe = kernel.probe_current_step(zero)
        checks.add('rank_zero_is_unusable', zero['rank_zero'] and probe['rank_zero']
                   and np.isnan(probe['ratio']) and close(zero['mu_ce'], zero['mu_raw'], atol=0, rtol=0))
        h0 = np.zeros(ch.p, complex)
        h1, vh1, info = kernel._channel_step(pre['o'], np.zeros(32, complex), pilot,
            np.zeros(32, complex), np.zeros(32), h0, tau, tau, noise, .3)
        checks.add('actual_stationary_zero_score', np.array_equal(h0,h1)
                   and info['zeta'] == 0 and info['objective_change'] == 0
                   and np.isfinite(vh1).all())


def check_resume(checks):
    import driver_c1B as harness
    old_cfg = harness._FLAT_CFG
    try:
        with tempfile.TemporaryDirectory(prefix='c1B_resume_') as tmp:
            path = Path(tmp)
            rows = [dict(cell=1, frame=0, arm=arm, status='ok')
                    for arm in ('OFF20','DIR20')]
            (path/'rows_shard000.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            (path/'config_shard000.json').write_text('{}\n')
            args = SimpleNamespace(mode='b0',out=path,shard=0,nshard=6)
            with patch.object(harness.c1,'load_context',return_value=None), \
                 patch.object(harness.c1,'load_cfgs',return_value=({'SPg_flat':{}},'fixture',None)), \
                 patch.object(harness,'manifest',return_value={}), \
                 patch.object(harness,'run_arm',side_effect=AssertionError('must not rerun saved calls')):
                harness.run_shard(args)
                harness.run_shard(args)
            receipt = json.loads((path/'results_shard000.json').read_text())
            checks.add('resume_1_based_rows_no_receiver_call', receipt['rows'] == 2
                       and receipt['errors'] == 0)
    finally:
        harness._FLAT_CFG = old_cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    args = p.parse_args()
    driver.setup_paths(SimpleNamespace(project=args.project, native_dir=args.native_dir,
                                       baseline_dir=args.baseline_dir))
    import tapchannel
    import twofft
    tapchannel.install_general_taps(twofft)
    import c1B_rx as kernel
    checks = Checks()
    try:
        check_reference(checks, kernel)
        check_qpsk(checks)
        check_algebra(checks)
        check_kernel_contracts(checks, kernel)
        check_resume(checks)
    except Exception as exc:
        checks.add('unhandled_exception', False, error=repr(exc))
        checks.write(args.out)
        raise
    if not checks.write(args.out):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
