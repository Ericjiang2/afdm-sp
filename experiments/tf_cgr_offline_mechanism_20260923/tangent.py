"""Analytic real-linear JVP of the frozen scalar TF step at saved BASE states.

No receiver step is executed here. Every primal value is read from, or checked
against, the sealed trace. Only tangent vectors are propagated.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


FLOOR = 1e-12
DAMPING = 0.3


@dataclass
class Tangent:
    h: np.ndarray
    x: np.ndarray
    v: np.ndarray
    xb: np.ndarray
    hb: np.ndarray
    s: np.ndarray
    vh: float = 0.0
    sv: float = 0.0
    bar: float = 0.0
    vp: float = 0.0

    @classmethod
    def zero(cls, n: int, p: int) -> "Tangent":
        return cls(np.zeros(p, complex), np.zeros(n, complex),
                   np.zeros(n), np.zeros(n, complex), np.zeros(p, complex),
                   np.zeros(n, complex))


def _power(h: np.ndarray, dh: np.ndarray, R: np.ndarray) -> tuple[float, float]:
    raw = float(np.vdot(h, R @ h).real)
    direct = 2 * float(np.vdot(dh, R @ h).real)
    if raw < 0:
        return 0.0, 0.0
    if raw == 0:
        return 0.0, max(direct, 0.0)
    return raw, direct


def _reciprocal(value: float, derivative: float) -> tuple[float, float, bool]:
    if value < FLOOR:
        return 1 / FLOOR, 0.0, False
    if value == FLOOR:
        return 1 / FLOOR, -max(derivative, 0.0) / FLOOR**2, True
    return 1 / value, -derivative / value**2, False


def _soft_jvp(rx: np.ndarray, drx: np.ndarray, vr: float, dvr: float,
              pilot: np.ndarray, prior: np.ndarray, pd: float,
              alphabet: np.ndarray, bits: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Differentiate the four-symbol softmax, including the variance and prior."""
    from scipy.special import logsumexp

    n = len(rx)
    err = (rx - pilot)[:, None] - alphabet
    likelihood = -abs(err)**2 / vr
    dlike = -2 * np.real(err.conj() * drx[:, None]) / vr + abs(err)**2 * dvr / vr**2
    li = np.column_stack((prior[:n], prior[n:]))
    logprior = 0.5 * li @ (1 - 2 * bits).T
    logprior -= logsumexp(logprior, axis=1, keepdims=True)
    logits = likelihood + logprior
    prob = np.exp(logits - logsumexp(logits, axis=1, keepdims=True))
    dprob = prob * (dlike - np.sum(prob * dlike, axis=1)[:, None])
    mu = prob @ alphabet
    dmu = dprob @ alphabet
    vraw = pd - abs(mu)**2
    dv = np.where(vraw > 0, -2 * np.real(mu.conj() * dmu), 0.0)
    if np.any(vraw == 0):
        dv = np.where(vraw == 0, np.maximum(-2 * np.real(mu.conj() * dmu), 0.0), dv)
    parts = []
    for j in (0, 1):
        slopes = []
        for bit in (0, 1):
            group = bits[:, j] == bit
            weights = np.exp(logits[:, group] - logsumexp(logits[:, group], axis=1, keepdims=True))
            slopes.append(np.sum(weights * dlike[:, group], axis=1))
        parts.append(slopes[0] - slopes[1])
    dapp = np.concatenate(parts)
    return dmu, dv, dapp


def step_jvp(pre: dict, post: dict, tangent: Tangent, *, ops, daft,
             Y: np.ndarray, pilot: np.ndarray, noise: float, prior: np.ndarray,
             pd: float, alphabet: np.ndarray, bits: np.ndarray,
             iteration: int, impulse: np.ndarray) -> tuple[Tangent, np.ndarray, dict]:
    """Evaluate one source-derived JVP at an archived BASE input state.

    The only intervention is added to the post-gain tangent. This function
    does not feed its primal outputs to the next step.
    """
    n, p = len(pilot), len(pre["h"])
    R = ops.R
    h, x, v, xb, hb, s = (pre[k] for k in ("h", "x", "v", "xb", "hb", "s"))
    vh, sv = pre["vh"], pre["sv"]
    xt = daft(x, ops.c.c1, ops.c.c2, True)
    B = ops.responses_time(xt)
    dB = ops.responses_time(daft(tangent.x, ops.c.c1, ops.c.c2, True))
    vx, dvx = float(v.mean()), float(tangent.v.mean())
    ex = float(np.vdot(x, x).real)
    dex = 2 * float(np.vdot(tangent.x, x).real)
    cn, dcn = _power(h, tangent.h, R)
    raw_bar = vx * cn + p * vh * ex / n
    dbar = dvx * cn + vx * dcn + p * (tangent.vh * ex + vh * dex) / n
    raw_vp = raw_bar + p * vh * vx
    dvp = dbar + p * (tangent.vh * vx + vh * dvx)
    if iteration:
        bar = DAMPING * raw_bar + (1 - DAMPING) * pre["bar"]
        vp = DAMPING * raw_vp + (1 - DAMPING) * pre["vp"]
        dbar = DAMPING * dbar + (1 - DAMPING) * tangent.bar
        dvp = DAMPING * dvp + (1 - DAMPING) * tangent.vp
    else:
        bar, vp = raw_bar, raw_vp
    # The saved post-residual is the exact anchor. The source ph=z-s_pre*bar.
    denom = noise + vp
    z = B @ h
    observed_residual = Y - z + s * bar
    s_new = DAMPING * observed_residual / denom + (1 - DAMPING) * s
    ds = DAMPING * (-(dB @ h + B @ tangent.h - tangent.s * bar - s * dbar) / denom
                     - observed_residual * dvp / denom**2) + (1 - DAMPING) * tangent.s
    dsv = -DAMPING * dvp / denom**2 + (1 - DAMPING) * tangent.sv
    sv_new = DAMPING / denom + (1 - DAMPING) * sv
    xb_new = DAMPING * x + (1 - DAMPING) * xb
    hb_new = DAMPING * h + (1 - DAMPING) * hb
    dxb = DAMPING * tangent.x + (1 - DAMPING) * tangent.xb
    dhb = DAMPING * tangent.h + (1 - DAMPING) * tangent.hb
    power_hb, dpower_hb = _power(hb_new, dhb, R)
    data_precision = sv_new * power_hb
    ddata_precision = dsv * power_hb + sv_new * dpower_hb
    gain_energy = float(np.vdot(xb_new, xb_new).real)
    dgain_energy = 2 * float(np.vdot(dxb, xb_new).real)
    gain_precision = sv_new * gain_energy
    dgain_precision = dsv * gain_energy + sv_new * dgain_energy
    vr, dvr, data_boundary = _reciprocal(data_precision, ddata_precision)
    vq, dvq, gain_boundary = _reciprocal(gain_precision, dgain_precision)
    adj = daft(ops.adjoint_time(hb_new, post["s"]), ops.c.c1, ops.c.c2)
    dadj = daft(ops.adjoint_time(dhb, post["s"]) +
                ops.adjoint_time(hb_new, ds), ops.c.c1, ops.c.c2)
    core = adj - xb_new * (sv_new * p * vh)
    dcore = dadj - dxb * (sv_new * p * vh) - xb_new * p * (dsv * vh + sv_new * tangent.vh)
    rx = x + vr * core
    drx = tangent.x + dvr * core + vr * dcore
    Bb = ops.responses_time(daft(xb_new, ops.c.c1, ops.c.c2, True))
    dBb = ops.responses_time(daft(dxb, ops.c.c1, ops.c.c2, True))
    force = Bb.conj().T @ post["s"] - hb_new * sv_new * n * vx
    dforce = (dBb.conj().T @ post["s"] + Bb.conj().T @ ds
              - n * (dhb * sv_new * vx + hb_new * dsv * vx + hb_new * sv_new * dvx))
    rh = h + vq * force
    drh = tangent.h + dvq * force + vq * dforce
    tau = 1 / p
    factor = tau / (tau + vq)
    dfactor = -tau * dvq / (tau + vq)**2
    dh = factor * drh + dfactor * rh + impulse
    dvh = tau**2 * dvq / (tau + vq)**2
    dmu, dv, dapp = _soft_jvp(rx, drx, vr, dvr, pilot, prior, pd, alphabet, bits)
    f = (rx - pilot) / vr
    df = drx / vr - (rx - pilot) * dvr / vr**2
    a = float(abs(alphabet[0].real))
    dllr = 4 * a * np.concatenate((df.real, df.imag))
    llr = 4 * a * np.concatenate((f.real, f.imag))
    checks = {
        "bar": abs(bar - post["bar"]), "vp": abs(vp - post["vp"]),
        "sv": abs(sv_new - post["sv"]), "vr": abs(vr - post["vr"]),
        "vq": abs(vq - post["vq"]),
        "xb": float(np.max(abs(xb_new - post["xbar"]))),
        "hb": float(np.max(abs(hb_new - post["hbar"]))),
        "s": float(np.max(abs(s_new - post["s"]))),
        "rx": float(np.max(abs(rx - post["rx"]))),
        "llr": float(np.max(abs(llr - post["extrinsic"]))),
        "gain": float(np.max(abs(factor * rh - post["h"]))),
        "data_boundary": data_boundary, "gain_boundary": gain_boundary,
    }
    return Tangent(dh, dmu, dv, dxb, dhb, ds, dvh, dsv, dbar, dvp), dllr, checks
