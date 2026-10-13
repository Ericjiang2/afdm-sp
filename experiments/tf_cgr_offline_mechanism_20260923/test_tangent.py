"""One synthetic scalar-step finite-difference qualification; no receiver trajectory."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "experiments/sp_afdm_frozen_20260920/src"),
                str(ROOT / "experiments/tf_cgr_mechanism_20260923_v2")]
from messages import alphabet, marginal  # noqa: E402
from physical import Channel, daft  # noqa: E402
from tf_base import TimePathOps  # noqa: E402
from tangent import Tangent, _reciprocal, step_jvp  # noqa: E402
from run_offline import clip_jvp  # noqa: E402


def one_synthetic_step(pre, ops, Y, pilot, noise, prior, pd, iteration):
    """Independent one-step formula only; its output is never fed back."""
    p, n = len(pre["h"]), len(Y)
    x, h, v, xb, hb, s = (pre[k] for k in ("x", "h", "v", "xb", "hb", "s"))
    vh, sv = pre["vh"], pre["sv"]
    B = ops.responses_time(daft(x, ops.c.c1, ops.c.c2, True))
    vx = float(v.mean())
    bar = vx * ops.power(h) + p * vh * float(np.vdot(x, x).real) / n
    vp = bar + p * vh * vx
    if iteration:
        bar = .3 * bar + .7 * pre["bar"]
        vp = .3 * vp + .7 * pre["vp"]
    s_new = .3 * (Y - B @ h + s * bar) / (noise + vp) + .7 * s
    sv_new = .3 / (noise + vp) + .7 * sv
    xb_new, hb_new = .3 * x + .7 * xb, .3 * h + .7 * hb
    vr = 1 / max(sv_new * ops.power(hb_new), 1e-12)
    vq = 1 / max(sv_new * float(np.vdot(xb_new, xb_new).real), 1e-12)
    adj = daft(ops.adjoint_time(hb_new, s_new), ops.c.c1, ops.c.c2)
    rx = x + vr * (adj - xb_new * sv_new * p * vh)
    Bb = ops.responses_time(daft(xb_new, ops.c.c1, ops.c.c2, True))
    rh = h + vq * (Bb.conj().T @ s_new - hb_new * sv_new * n * vx)
    tau = 1 / p
    h_new = tau * rh / (tau + vq)
    a, _ = alphabet(pd)
    ext, _, mu, new_v = marginal(-abs((rx - pilot)[:, None] - a)**2 / vr, prior, pd)
    return dict(h=h_new, x=pilot + mu, v=new_v, xbar=xb_new,
                hbar=hb_new, s=s_new, vh=tau * vq / (tau + vq),
                sv=sv_new, bar=bar, vp=vp, vr=vr, vq=vq, rx=rx,
                extrinsic=ext)


def test_full_jvp(iteration):
    rng = np.random.default_rng(68122)
    n, p = 16, 3
    channel = Channel(n, .04, .00001, [1, 1, 4], [.1, -.2, .25],
                      rng.normal(size=p) / 3 + 1j * rng.normal(size=p) / 3)
    ops = TimePathOps(channel)
    pilot = rng.normal(size=n) / 4 + 1j * rng.normal(size=n) / 4
    prior = rng.normal(size=2 * n) / 3
    pre = dict(h=channel.gains, x=pilot + rng.normal(size=n) / 10 + 1j * rng.normal(size=n) / 10,
               v=np.full(n, .3), xb=pilot + rng.normal(size=n) / 10,
               hb=channel.gains + rng.normal(size=p) / 10,
               s=rng.normal(size=n) / 10 + 1j * rng.normal(size=n) / 10,
               vh=.19, sv=.14, bar=.42 if iteration else 0.,
               vp=.52 if iteration else 0.)
    tangent = Tangent(rng.normal(size=p) / 10 + 1j * rng.normal(size=p) / 10,
                      rng.normal(size=n) / 10 + 1j * rng.normal(size=n) / 10,
                      rng.normal(size=n) / 50,
                      rng.normal(size=n) / 10 + 1j * rng.normal(size=n) / 10,
                      rng.normal(size=p) / 10 + 1j * rng.normal(size=p) / 10,
                      rng.normal(size=n) / 10 + 1j * rng.normal(size=n) / 10,
                      .01, .01, .02, .03)
    noise = .2
    Y = rng.normal(size=n) / 4 + 1j * rng.normal(size=n) / 4
    post = one_synthetic_step(pre, ops, Y, pilot, noise, prior, .5, iteration)
    a, bits = alphabet(.5)
    derivative, dllr, checks = step_jvp(pre, post, tangent, ops=ops, daft=daft,
                                         Y=Y, pilot=pilot, noise=noise, prior=prior,
                                         pd=.5, alphabet=a, bits=bits, iteration=iteration,
                                         impulse=np.zeros(p, complex))
    eps = 1e-6
    changed = dict(pre)
    for source, direction in (("h", tangent.h), ("x", tangent.x), ("v", tangent.v),
                              ("xb", tangent.xb), ("hb", tangent.hb), ("s", tangent.s)):
        changed[source] = pre[source] + eps * direction
    changed["vh"] = pre["vh"] + eps * tangent.vh
    changed["sv"] = pre["sv"] + eps * tangent.sv
    changed["bar"] = pre["bar"] + eps * tangent.bar
    changed["vp"] = pre["vp"] + eps * tangent.vp
    next_post = one_synthetic_step(changed, ops, Y, pilot, noise, prior, .5, iteration)
    for field, value in (("h", derivative.h), ("x", derivative.x),
                         ("v", derivative.v), ("xbar", derivative.xb),
                         ("hbar", derivative.hb), ("s", derivative.s),
                         ("vh", derivative.vh), ("sv", derivative.sv),
                         ("bar", derivative.bar), ("vp", derivative.vp)):
        finite = (next_post[field] - post[field]) / eps
        assert np.max(abs(finite - value)) < 2e-5, field
    finite_llr = (next_post["extrinsic"] - post["extrinsic"]) / eps
    assert np.max(abs(finite_llr - dllr)) < 2e-5
    assert max(value for key, value in checks.items() if key not in
               ("data_boundary", "gain_boundary")) < 1e-10
    assert not checks["data_boundary"] and not checks["gain_boundary"]
    print(f"one synthetic full scalar-step JVP, prior damping={bool(iteration)}: pass")


def test_one_sided_boundaries():
    floor = 1e-12
    assert _reciprocal(floor / 2, 1)[1] == 0
    assert _reciprocal(floor, -1)[1] == 0
    assert _reciprocal(floor, 1)[1] == -1 / floor**2
    clipped, count = clip_jvp(np.array([-21., -20., 0., 20., 21.]),
                              np.array([1., -1., 2., 1., -1.]))
    np.testing.assert_array_equal(clipped, [0., 0., 2., 0., 0.])
    assert count == 2
    print("one-sided reciprocal floor and LLR clipping boundaries: pass")


if __name__ == "__main__":
    test_full_jvp(0)
    test_full_jvp(1)
    test_one_sided_boundaries()
