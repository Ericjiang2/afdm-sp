#!/usr/bin/env python3
"""Deterministic, small-matrix checks of the joint finite-time closure.

This is an algebra/JVP fixture, not a C1 frame, Monte Carlo experiment, FER run,
or matched-MSE independent probe. Only the named source definitions are loaded
through AST; experiment drivers and receiver/decoder entry points are not run.
All primal and real-directional derivative states remain in memory. The report
stores their hashes and error summaries, and any failed check gives exit code 1.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import traceback
import types

import numpy as np
import scipy
from scipy.signal.windows import dpss


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OUTPUT = HERE / "joint_finite_time_checks.json"
CONFIG = {
    "N": 32,
    "K": [8, 16, 24],
    "D_per_tap": 8,
    "tap_delays": [0, 3, 7],
    "dpss_center": 0.0,
    "dpss_NW": 2.5,
    "rho": 0.3,
    "pilot_power": 0.3,
    "data_power": 0.7,
    "noise_power": 0.18,
    "damping": 0.3,
    "floor": 1e-12,
    "T": [10, 20, 40, 80],
    "epsilon": [4e-4, 2e-4, 1e-4, 5e-5],
    "reference": {"K": 16, "T": 20},
}
# Fixed before the first execution; no threshold adjustment or adaptive epsilon.
TOLERANCES = {
    "algebra": {"atol": 2e-12, "rtol": 2e-11},
    "reference": {"atol": 2e-12, "rtol": 2e-10},
    "jvp_finest": {"atol": 1e-8, "rtol": 2e-5},
    "second_order_ratio": [3.2, 4.8],
    "roundoff_indicator_factor": 64.0,
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_hash(value):
    digest = hashlib.sha256()

    def add(item):
        if isinstance(item, dict):
            digest.update(b"dict")
            for key in sorted(item):
                add(key)
                add(item[key])
        elif isinstance(item, (list, tuple)):
            digest.update(f"sequence:{len(item)}:".encode())
            for child in item:
                add(child)
        elif isinstance(item, np.ndarray):
            digest.update(f"array:{item.dtype}:{item.shape}:".encode())
            digest.update(np.ascontiguousarray(item).tobytes())
        else:
            if isinstance(item, np.generic):
                item = item.item()
            digest.update(json.dumps(item, allow_nan=False).encode())
            digest.update(b";")

    add(value)
    return digest.hexdigest()


def copy_state(state):
    return {key: value.copy() if isinstance(value, np.ndarray) else value
            for key, value in state.items()}


def load_definitions(path, names, namespace, constants=()):
    """Execute exact named AST nodes, never the source module's top-level imports."""
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    selected = []
    found = set()
    for node in tree.body:
        name = None
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            name = node.name
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id in constants):
            name = node.targets[0].id
            ast.literal_eval(node.value)
        if name is not None:
            if name in found:
                raise ValueError(f"Duplicate source definition: {path}:{name}")
            selected.append(node)
            found.add(name)
    expected = set(names) | set(constants)
    if found != expected:
        raise ValueError(f"Missing source definitions in {path}: {expected - found}")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    segment = "\n\n".join(ast.get_source_segment(source, node) for node in selected)
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "selected_names": sorted(expected),
        "selected_source_sha256": hashlib.sha256(segment.encode()).hexdigest(),
        "loading": "Exact original AST definitions/constants; module imports not executed",
    }


class Audit:
    def __init__(self):
        self.count = 0
        self.failures = []

    def require(self, passed, label, detail=None):
        self.count += 1
        if not bool(passed):
            self.failures.append({"check": label, "detail": detail})
        return bool(passed)

    def close(self, label, actual, expected, tolerance="algebra"):
        actual, expected = np.asarray(actual), np.asarray(expected)
        absolute = float(np.linalg.norm(actual - expected))
        scale = float(np.linalg.norm(actual) + np.linalg.norm(expected))
        relative = absolute / scale if scale else (0.0 if absolute == 0.0 else None)
        tol = TOLERANCES[tolerance]
        limit = tol["atol"] + tol["rtol"] * scale
        passed = bool(np.isfinite(absolute) and absolute <= limit)
        result = {"absolute": absolute, "relative_to_sum_norms": relative,
                  "limit": limit, "passed": passed}
        self.require(passed, label, result)
        return result


class DenseOps:
    """Independent dense construction from actual DAFT, DPSS and CPP definitions."""
    def __init__(self, n, c1, c2, delays, mods, daft):
        self.n, self.k = n, len(delays)
        inverse = daft(np.eye(n), c1, c2, inverse=True)
        self.inverse_daft = inverse
        self.atoms = np.empty((n, n, self.k), complex)
        prefix = []
        for j, delay in enumerate(delays):
            shifted = np.arange(n) - delay
            phase = np.ones(n, complex)
            wrapped = shifted < 0
            phase[wrapped] = np.exp(2j * np.pi * c1 *
                                    (n * n + 2 * n * shifted[wrapped]))
            self.atoms[:, :, j] = ((phase * mods[:, j])[:, None]
                                   * inverse[shifted % n, :])
            prefix.append(phase)
        self.cpp = np.asarray(prefix).T
        self.gram_h = np.einsum("ijk,ijl->kl", self.atoms.conj(), self.atoms) / n

    def B(self, x):
        return np.einsum("ijk,j->ik", self.atoms, x)

    def HHs(self, h, s):
        return np.einsum("ijk,k,i->j", self.atoms.conj(), h.conj(), s)

    def q(self, h):
        return float(np.vdot(h, self.gram_h @ h).real)

    def dq(self, h, dh):
        return float(2.0 * np.vdot(h, self.gram_h @ dh).real)


def fixture(k, tap_columns, daft):
    n = CONFIG["N"]
    index = np.arange(n)
    c1, c2 = 5.25 / (2 * n), np.sqrt(2.0) / (2 * n)
    tap, eigenvalues = tap_columns(n, CONFIG["dpss_center"],
                                   CONFIG["dpss_NW"], CONFIG["D_per_tap"])
    tap_delays = CONFIG["tap_delays"][:k // CONFIG["D_per_tap"]]
    delays = np.repeat(tap_delays, CONFIG["D_per_tap"])
    mods = np.tile(tap, (1, len(tap_delays)))
    ops = DenseOps(n, c1, c2, delays, mods, daft)
    p = np.sqrt(CONFIG["pilot_power"]) * np.exp(-1j * np.pi * 5 * index ** 2 / n)
    c = np.sqrt(CONFIG["data_power"] / 2.0)
    sign_i = np.where((index * index + 3 * index + 1) % 7 < 3, 1.0, -1.0)
    sign_q = np.where((5 * index + 2) % 11 < 5, 1.0, -1.0)
    data = c * (sign_i + 1j * sign_q)
    j = np.arange(1, k + 1)
    truth = (np.cos(.43 * j) + .25 * np.sin(.17 * j)
             + 1j * (np.sin(.61 * j) - .2 * np.cos(.23 * j)))
    truth /= np.linalg.norm(truth)
    t = index + 1
    noise = (np.cos(.37 * t) + .3 * np.sin(.91 * t)
             + 1j * (np.sin(.53 * t) - .4 * np.cos(.19 * t)))
    noise *= np.sqrt(n * CONFIG["noise_power"]) / np.linalg.norm(noise)
    y = ops.B(p + data) @ truth + noise
    dy = (np.sin(.29 * t) + .35 * np.cos(.77 * t)
          + 1j * (np.cos(.41 * t) + .2 * np.sin(.13 * t)))
    dy *= np.linalg.norm(y) / np.linalg.norm(dy)
    independent_fixture = c * (.45 * np.sin(.63 * t) + 1j * .35 * np.cos(.47 * t))
    return {"ops": ops, "p": p, "data": data, "truth": truth,
            "noise": noise, "Y": y, "dY": dy, "m_I": independent_fixture,
            "delays": delays, "mods": mods, "c1": c1, "c2": c2,
            "eigenvalues": eigenvalues}


def recursion(ops, y, p, dy, iterations):
    """Eqs. 12–20 with a real JVP for one additive complex dY at every step."""
    n, k = ops.n, ops.k
    pd, n0 = CONFIG["data_power"], CONFIG["noise_power"]
    beta, floor = CONFIG["damping"], CONFIG["floor"]
    c = np.sqrt(pd / 2.0)
    bp = ops.B(p)
    wp = np.linalg.solve(bp.conj().T @ bp + k * (n0 + pd) * np.eye(k), bp.conj().T)
    h0, dh0 = wp @ y, wp @ dy
    state = dict(h=h0, m=np.zeros(n, complex), x=p.copy(), v=pd, V=1.0,
                 s=np.zeros(n, complex), u=0.0, xb=p.copy(), hb=h0.copy(), a=None, b=None)
    tangent = dict(h=dh0, m=np.zeros(n, complex), x=np.zeros(n, complex), v=0.0, V=0.0,
                   s=np.zeros(n, complex), u=0.0, xb=np.zeros(n, complex), hb=dh0.copy(),
                   a=None, b=None)
    result = {"initial": copy_state(state), "dinitial": copy_state(tangent),
              "Wp": wp, "history": []}
    for t in range(iterations):
        pre, dpre = copy_state(state), copy_state(tangent)
        h, x, v, V = (pre[key] for key in ("h", "x", "v", "V"))
        dh, dx, dv, dV = (dpre[key] for key in ("h", "x", "v", "V"))
        xpower = float(np.vdot(x, x).real) / n
        dxpower = float(2 * np.vdot(x, dx).real) / n
        q, dq = ops.q(h), ops.dq(h, dh)
        bt = v * q + V * xpower
        dbt = dv * q + v * dq + dV * xpower + V * dxpower
        at, dat = bt + V * v, dbt + dV * v + V * dv
        if t == 0:
            b, a, db, da = bt, at, dbt, dat
        else:
            b, a = beta * bt + (1 - beta) * pre["b"], beta * at + (1 - beta) * pre["a"]
            db = beta * dbt + (1 - beta) * dpre["b"]
            da = beta * dat + (1 - beta) * dpre["a"]
        D = n0 + a
        bx, bdx = ops.B(x), ops.B(dx)
        num = y - bx @ h + b * pre["s"]
        dnum = dy - bdx @ h - bx @ dh + db * pre["s"] + b * dpre["s"]
        s = beta * num / D + (1 - beta) * pre["s"]
        ds = beta * (dnum / D - num * da / D ** 2) + (1 - beta) * dpre["s"]
        u = beta / D + (1 - beta) * pre["u"]
        du = -beta * da / D ** 2 + (1 - beta) * dpre["u"]
        xb = beta * x + (1 - beta) * pre["xb"]
        hb = beta * h + (1 - beta) * pre["hb"]
        dxb = beta * dx + (1 - beta) * dpre["xb"]
        dhb = beta * dh + (1 - beta) * dpre["hb"]
        qb, dqb = ops.q(hb), ops.dq(hb, dhb)
        xb2 = float(np.vdot(xb, xb).real)
        dxb2 = float(2 * np.vdot(xb, dxb).real)
        jx_raw, jh_raw = u * qb, u * xb2
        jx, jh = max(jx_raw, floor), max(jh_raw, floor)
        djx = du * qb + u * dqb if jx_raw > floor else 0.0
        djh = du * xb2 + u * dxb2 if jh_raw > floor else 0.0
        adj = ops.HHs(hb, s)
        dadj = ops.HHs(dhb, s) + ops.HHs(hb, ds)
        z = jx * (x - p) + adj - u * V * xb
        dz = djx * (x - p) + jx * dx + dadj - (du * V + u * dV) * xb - u * V * dxb
        llr = 4 * c * np.concatenate((z.real, z.imag))
        dllr = 4 * c * np.concatenate((dz.real, dz.imag))
        tanh = np.tanh(llr / 2)
        m = c * (tanh[:n] + 1j * tanh[n:])
        dm = c / 2 * ((1 - tanh[:n] ** 2) * dllr[:n]
                       + 1j * (1 - tanh[n:] ** 2) * dllr[n:])
        variance_raw = pd - np.abs(m) ** 2
        variance_positive = variance_raw > 0
        vnew = float(np.mean(np.maximum(variance_raw, 0)))
        dvnew = float(np.mean(np.where(variance_positive, -2 * (m.conj() * dm).real, 0)))
        bb, dbb = ops.B(xb), ops.B(dxb)
        gain_num = jh * h + bb.conj().T @ s - u * n * v * hb
        dgain_num = (djh * h + jh * dh + dbb.conj().T @ s + bb.conj().T @ ds
                     - n * ((du * v + u * dv) * hb + u * v * dhb))
        hnew = gain_num / (k + jh)
        dhnew = (dgain_num - hnew * djh) / (k + jh)
        Vnew, dVnew = k / (k + jh), -k * djh / (k + jh) ** 2
        state = dict(h=hnew, m=m, x=p + m, v=vnew, V=Vnew,
                     s=s, u=u, xb=xb, hb=hb, a=a, b=b)
        tangent = dict(h=dhnew, m=dm, x=dm.copy(), v=dvnew, V=dVnew,
                       s=ds, u=du, xb=dxb, hb=dhb, a=da, b=db)
        mid = dict(X=xpower, q=q, bt=bt, at=at, a=a, b=b, D=D, num=num, s=s, u=u,
                   xb=xb, hb=hb, Jx=jx, Jh=jh, Jx_raw=jx_raw, Jh_raw=jh_raw,
                   z=z, llr=llr, tanh=tanh, variance_raw=variance_raw,
                   Jx_floor=jx_raw <= floor, Jh_floor=jh_raw <= floor,
                   variance_positive=variance_positive)
        dmid = dict(X=dxpower, q=dq, bt=dbt, at=dat, a=da, b=db, D=da, num=dnum,
                    s=ds, u=du, xb=dxb, hb=dhb, Jx=djx, Jh=djh, z=dz, llr=dllr)
        record = dict(iteration=t + 1, pre=pre, dpre=dpre, mid=mid, dmid=dmid,
                      post=copy_state(state), dpost=copy_state(tangent))
        for group in (state, tangent, mid, dmid):
            for name, value in group.items():
                if not np.all(np.isfinite(value)):
                    raise FloatingPointError(f"Nonfinite {name} at K={k}, iteration={t + 1}")
        result["history"].append(record)
    return result


def update_error_summary(summary, label, result, iteration):
    entry = summary.setdefault(label, {"count": 0, "max_absolute": -1.0,
                                      "max_relative_to_sum_norms": -1.0})
    entry["count"] += 1
    if result["absolute"] > entry["max_absolute"]:
        entry["max_absolute"] = result["absolute"]
        entry["worst_absolute_iteration"] = iteration
    entry["max_relative_to_sum_norms"] = max(entry["max_relative_to_sum_norms"],
                                             result["relative_to_sum_norms"])


def finite_time_identities(case, run, audit):
    ops, y = case["ops"], case["Y"]
    n, k, beta = ops.n, ops.k, CONFIG["damping"]
    summary, lambdas, ells, term_norms = {}, [], [], []
    conditions = []
    for step in run["history"]:
        pre, mid, post = step["pre"], step["mid"], step["post"]
        t = step["iteration"]
        bt, bb = ops.B(pre["x"]), ops.B(mid["xb"])
        dh, ds = post["h"] - pre["h"], mid["s"] - pre["s"]
        ell = mid["D"] - mid["b"]
        omega = mid["b"] + (1 - beta) * mid["D"] / beta
        lam = ell * (k + mid["u"] * n * pre["v"])
        Q = bb.conj().T @ bb + lam * np.eye(k)
        terms = [bb.conj().T @ (bt - bb) @ pre["h"],
                 ell * (k + mid["Jh"]) * dh,
                 ell * mid["u"] * n * pre["v"] * (mid["hb"] - pre["h"]),
                 omega * bb.conj().T @ ds]
        forcing = sum(terms)
        ridge = np.linalg.solve(Q, bb.conj().T @ y)
        prefix = f"K={k}/t={t}/"
        audit.require(ell > 0 and lam > 0, prefix + "positive_ell_lambda", [ell, lam])
        checks = {
            "J3": (y - bt @ pre["h"], ell * mid["s"] + omega * ds),
            "J6_with_J7_four_terms": (Q @ pre["h"], bb.conj().T @ y - forcing),
            "J8": (post["h"], ridge + dh - np.linalg.solve(Q, forcing)),
        }
        for label, (left, right) in checks.items():
            update_error_summary(summary, label, audit.close(prefix + label, left, right), t)
        lambdas.append(lam)
        ells.append(ell)
        conditions.append(float(np.linalg.cond(Q)))
        term_norms.append([float(np.linalg.norm(term)) for term in terms])
    summary["J7_term_order"] = ["regressor_lag", "gain_increment", "gain_bar_lag", "score_increment"]
    summary["J7_max_term_norms"] = np.max(term_norms, axis=0).tolist()
    summary["ell_range"] = [min(ells), max(ells)]
    summary["lambda_range"] = [min(lambdas), max(lambdas)]
    summary["max_Q_condition_number"] = max(conditions)
    return summary, lambdas


def ridge_pair_checks(case, run, lambdas, audit):
    ops, y, truth = case["ops"], case["Y"], case["truth"]
    k = ops.k
    projector = np.eye(k) - np.outer(truth, truth.conj()) / np.vdot(truth, truth).real
    bi = ops.B(case["p"] + case["m_I"])
    rows = []
    for T in CONFIG["T"]:
        post = run["history"][T - 1]["post"]
        bs = ops.B(post["x"])
        E = bs - bi
        lambda_s = lambdas[T - 1]
        qs = bs.conj().T @ bs + lambda_s * np.eye(k)
        hs = np.linalg.solve(qs, bs.conj().T @ y)
        for mode, factor in (("equal_lambda", 1.0), ("unequal_lambda", 1.4)):
            lambda_i = factor * lambda_s
            hi = np.linalg.solve(bi.conj().T @ bi + lambda_i * np.eye(k), bi.conj().T @ y)
            ri = y - bi @ hi
            regularization_term = -(lambda_s - lambda_i) * hi
            rhs = np.linalg.solve(qs, E.conj().T @ ri - bs.conj().T @ E @ hi
                                  + regularization_term)
            prefix = f"K={k}/T={T}/{mode}/"
            j11 = audit.close(prefix + "J11", hs - hi, rhs)
            if factor != 1.0:
                audit.require(np.linalg.norm(regularization_term) > 0,
                              prefix + "nonzero_regularization_difference")
            z, u, w = (projector @ vector for vector in
                       (hi - truth, hs - hi, post["h"] - hs))
            denominator = float(np.vdot(z, z).real)
            if denominator <= 0:
                raise ValueError(prefix + "J12 has a nonpositive denominator")
            direct = float(np.linalg.norm(projector @ (post["h"] - truth)) ** 2 / denominator)
            split = float(1 + (2 * np.vdot(z, u).real + 2 * np.vdot(z, w).real
                              + np.vdot(u, u).real + np.vdot(w, w).real
                              + 2 * np.vdot(u, w).real) / denominator)
            rows.append({"T": T, "mode": mode, "lambda_S": lambda_s, "lambda_I": lambda_i,
                         "regularization_difference_term_norm": float(np.linalg.norm(regularization_term)),
                         "J11": j11, "J12": audit.close(prefix + "J12", direct, split),
                         "J12_denominator": denominator, "R_direct": direct, "R_split": split,
                         "two_actual_ridge_solves": True})
    return {"m_I_scope": "Fixed legal soft-symbol algebra fixture; not a matched-MSE independent probe",
            "rows": rows}


def branch_summary(run):
    history = run["history"]
    llrs = np.concatenate([step["mid"]["llr"] for step in history])
    tanh = np.concatenate([step["mid"]["tanh"] for step in history])
    return {
        "Jx_floor_steps": sum(bool(step["mid"]["Jx_floor"]) for step in history),
        "Jh_floor_steps": sum(bool(step["mid"]["Jh_floor"]) for step in history),
        "min_Jx_minus_floor": min(step["mid"]["Jx_raw"] - CONFIG["floor"] for step in history),
        "min_Jh_minus_floor": min(step["mid"]["Jh_raw"] - CONFIG["floor"] for step in history),
        "min_variance_raw": min(float(np.min(step["mid"]["variance_raw"])) for step in history),
        "variance_nonpositive_elements": sum(int(np.sum(~step["mid"]["variance_positive"])) for step in history),
        "raw_llr_range": [float(np.min(llrs)), float(np.max(llrs))],
        "raw_llr_abs_ge_20": int(np.sum(np.abs(llrs) >= 20)),
        "tanh_exact_saturated_elements": int(np.sum(np.abs(tanh) == 1.0)),
        "tanh_derivative_below_1e_minus_8": int(np.sum(1 - tanh ** 2 < 1e-8)),
        "llr_clipping": "None; comparison uses raw LLR",
    }


def same_branches(nominal, perturbed):
    for first, second in zip(nominal["history"], perturbed["history"], strict=True):
        a, b = first["mid"], second["mid"]
        for key in ("Jx_floor", "Jh_floor", "variance_positive"):
            if not np.array_equal(a[key], b[key]):
                return False
    return True


def finite_difference_checks(case, nominal, audit):
    ops, y, p, dy = (case[key] for key in ("ops", "Y", "p", "dY"))
    runs = []
    perturbation_metadata = []
    for epsilon in CONFIG["epsilon"]:
        plus = recursion(ops, y + epsilon * dy, p, np.zeros_like(dy), max(CONFIG["T"]))
        minus = recursion(ops, y - epsilon * dy, p, np.zeros_like(dy), max(CONFIG["T"]))
        smooth = same_branches(nominal, plus) and same_branches(nominal, minus)
        audit.require(smooth, f"K={ops.k}/eps={epsilon}/unchanged_branch_masks")
        runs.append((epsilon, plus, minus))
        perturbation_metadata.append({"epsilon": epsilon, "same_branches": smooth,
                                      "plus_state_sha256": state_hash(plus),
                                      "minus_state_sha256": state_hash(minus),
                                      "plus_branches": branch_summary(plus),
                                      "minus_branches": branch_summary(minus)})
    rows = []
    machine_epsilon = np.finfo(float).eps
    lower, upper = TOLERANCES["second_order_ratio"]
    for T in CONFIG["T"]:
        for field, state_key, derivative_key in (("h", "post", "dpost"), ("raw_llr", "mid", "dmid")):
            key = "h" if field == "h" else "llr"
            step = nominal["history"][T - 1]
            tangent = step[derivative_key][key]
            tangent_norm = float(np.linalg.norm(tangent))
            if tangent_norm == 0:
                raise ValueError(f"K={ops.k}/T={T}/{field}: zero JVP fixture")
            errors = []
            for epsilon, plus, minus in runs:
                yp, ym = plus["history"][T - 1][state_key][key], minus["history"][T - 1][state_key][key]
                difference = (yp - ym) / (2 * epsilon)
                absolute = float(np.linalg.norm(difference - tangent))
                indicator = (TOLERANCES["roundoff_indicator_factor"] * machine_epsilon
                             * max(np.linalg.norm(yp), np.linalg.norm(ym), np.linalg.norm(step[state_key][key]))
                             / epsilon)
                errors.append({"epsilon": epsilon, "absolute": absolute,
                               "relative_to_JVP_norm": absolute / tangent_norm,
                               "floating_point_indicator": float(indicator)})
            finest = errors[-1]
            tol = TOLERANCES["jvp_finest"]
            prefix = f"K={ops.k}/T={T}/{field}/"
            audit.require(finest["absolute"] <= tol["atol"] + tol["rtol"] * tangent_norm,
                          prefix + "finest_JVP_accuracy", finest)
            convergence = []
            resolved_order_seen = False
            for coarse, fine in zip(errors, errors[1:]):
                ratio = coarse["absolute"] / fine["absolute"] if fine["absolute"] > 0 else None
                second_order = ratio is not None and lower <= ratio <= upper
                roundoff_limited = (resolved_order_seen
                                    and coarse["absolute"] <= coarse["floating_point_indicator"]
                                    and fine["absolute"] <= fine["floating_point_indicator"])
                status = "second_order" if second_order else ("roundoff_limited_after_resolved_order" if roundoff_limited else "failed")
                detail = {"coarse_epsilon": coarse["epsilon"], "fine_epsilon": fine["epsilon"],
                          "error_ratio": ratio, "status": status}
                audit.require(second_order or roundoff_limited, prefix + "second_order", detail)
                resolved_order_seen = resolved_order_seen or second_order
                convergence.append(detail)
            audit.require(resolved_order_seen, prefix + "at_least_one_resolved_second_order_pair")
            rows.append({"T": T, "field": field, "JVP_norm": tangent_norm,
                         "errors": errors, "convergence": convergence})
    return {"same_additive_dY_at_all_steps": True, "initialization_derivative": "dh_0 = W_p dY",
            "method": "Central real-direction finite difference; conjugate-aware analytic JVP; no complex-step",
            "roundoff_note": "64*u*output_norm/epsilon is an indicator, not a rigorous bound; an earlier resolved second-order pair is mandatory",
            "perturbed_runs": perturbation_metadata, "rows": rows}


def reference_check(case, nominal, namespace, audit):
    ops = case["ops"]
    refops = namespace["CodexOps"](ops.n, case["c1"], case["c2"], case["delays"], case["mods"])
    T = CONFIG["reference"]["T"]
    reference = namespace["codex_recursion"](
        refops, case["Y"], case["p"], CONFIG["noise_power"], CONFIG["data_power"], ops.k,
        T=T, damp=CONFIG["damping"], eps=CONFIG["floor"])
    step = nominal["history"][T - 1]
    results = {
        "B": audit.close("reference/B", ops.B(case["p"] + case["data"]),
                          refops.B(case["p"] + case["data"]), "reference"),
        "HHs": audit.close("reference/HHs", ops.HHs(case["truth"], case["Y"]),
                            refops.HHs(case["truth"], case["Y"]), "reference"),
        "h_init": audit.close("reference/h_init", nominal["initial"]["h"], reference["h_init"], "reference"),
        "raw_llr": audit.close("reference/raw_llr", step["mid"]["llr"], reference["llr"], "reference"),
    }
    for field in ("h", "m", "x", "v", "V"):
        results[field] = audit.close("reference/" + field, step["post"][field], reference[field], "reference")
    return {"K": ops.k, "T": T, "reference_recursion_calls": 1,
            "source": "driver_c1jfp.codex_recursion (AST isolated)", "errors": results}


def counterexamples(audit):
    xi = np.array([1.0, -1.0, 1j, -1j])
    a = b = 0.5
    scalar_rows = []
    for sign in (1, -1):
        error = sign * xi
        U = float(np.mean(np.abs(error) ** 2))
        C = np.mean(error * xi.conj())
        output = float(np.mean(np.abs(a * error + b * xi) ** 2))
        predicted = float(a * a * U + b * b * np.mean(np.abs(xi) ** 2) + 2 * a * b * C.real)
        audit.close(f"single_mode/sign={sign}/next_variance", output, predicted)
        audit.close(f"single_mode/sign={sign}/exact_value", output, 1.0 if sign == 1 else 0.0)
        scalar_rows.append({"sign": sign, "U": U, "C_real": float(C.real), "C_imag": float(C.imag),
                            "next_U": output})
    c = 0.35
    rows = []
    for M in (0.0, 0.5, 2.0, 5.0):
        matrix = np.array([[c, M], [0.0, c]])
        inverse = np.linalg.solve(np.eye(2) - matrix, np.eye(2))
        gain = float(np.linalg.norm(inverse, "fro") ** 2 / 2)
        formula = float(1 / (1 - c) ** 2 + M ** 2 / (2 * (1 - c) ** 4))
        rows.append({"c": c, "M": M, "trace_over_dimension": float(np.trace(matrix) / 2),
                     "gain": gain, "formula": formula,
                     "J23": audit.close(f"J23/M={M}", gain, formula)})
    audit.require(len({row["trace_over_dimension"] for row in rows}) == 1, "J23/same_trace")
    audit.require(len({row["gain"] for row in rows}) == len(rows), "J23/distinct_gains")
    return {"single_mode": {"a": a, "b": b, "deterministic_xi": ["1", "-1", "i", "-i"], "rows": scalar_rows},
            "nonnormal_same_trace": rows}


def run_checks(report, audit):
    source_dir = ROOT / "experiments/headroom_ladder_20261008"
    physical_path = ROOT / "experiments/sp_afdm_frozen_20260920/src/physical.py"
    physical = types.ModuleType("physical")
    physical.__file__ = str(physical_path)
    physical.__dict__["np"] = np
    if "physical" in sys.modules:
        raise RuntimeError("Unexpected existing physical module; refusing source substitution")
    report["sources"] = [load_definitions(physical_path, ("daft",), physical.__dict__)]
    sys.modules["physical"] = physical
    dpss_namespace = {"np": np, "dpss": dpss}
    report["sources"].append(load_definitions(source_dir / "dpss_rx.py", ("slepian", "tap_columns"),
                                               dpss_namespace, ("_BASIS",)))
    reference_namespace = {"np": np}
    report["sources"].append(load_definitions(source_dir / "driver_c1jfp.py", ("CodexOps", "codex_recursion"),
                                               reference_namespace, ("T_INNER", "DAMP", "FLOOR")))
    for name in ("CODEX_JOINT_FINITE_TIME_CLOSURE.md", "CODEX_FIRST_ROUND_INFORMATION_DERIVATION.md"):
        path = HERE / name
        report["sources"].append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "loading": "Document hash only in this script"})
    report["sources"].append({"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256(Path(__file__))})
    report["cases"] = []
    for k in CONFIG["K"]:
        case = fixture(k, dpss_namespace["tap_columns"], physical.daft)
        ops = case["ops"]
        row = {"K": k, "tap_delays": list(np.unique(case["delays"]).astype(int).tolist()),
               "c1": case["c1"], "c2": float(case["c2"]),
               "fixture_sha256": state_hash({key: value for key, value in case.items() if key != "ops"}),
               "dense_atoms_sha256": state_hash(ops.atoms),
               "units": {"convention": "Physical nominal total power 1; Pp=rho, Pd=1-rho; no internal .5-power rescaling",
                         "pilot_mean_power": float(np.mean(np.abs(case["p"]) ** 2)),
                         "data_mean_power": float(np.mean(np.abs(case["data"]) ** 2)),
                         "noise_mean_power": float(np.mean(np.abs(case["noise"]) ** 2)),
                         "pilot_plus_data_sample_power": float(np.mean(np.abs(case["p"] + case["data"]) ** 2)),
                         "true_gain_energy": float(np.vdot(case["truth"], case["truth"]).real),
                         "dY_norm_over_Y_norm": float(np.linalg.norm(case["dY"]) / np.linalg.norm(case["Y"]))}}
        report["cases"].append(row)
        row["operators"] = {
            "DAFT_unitarity": audit.close(f"K={k}/DAFT_unitarity", ops.inverse_daft.conj().T @ ops.inverse_daft, np.eye(ops.n)),
            "G_H_identity": audit.close(f"K={k}/G_H_identity", ops.gram_h, np.eye(k)),
            "max_CPP_departure_from_one": float(np.max(np.abs(ops.cpp - 1))),
            "DPSS_eigenvalue_range": [float(np.min(case["eigenvalues"])), float(np.max(case["eigenvalues"]))],
        }
        for key, expected in (("pilot_mean_power", CONFIG["pilot_power"]), ("data_mean_power", CONFIG["data_power"]),
                              ("noise_mean_power", CONFIG["noise_power"]), ("dY_norm_over_Y_norm", 1.0)):
            audit.close(f"K={k}/units/{key}", row["units"][key], expected)
        nominal = recursion(ops, case["Y"], case["p"], case["dY"], max(CONFIG["T"]))
        row["full_state_sha256"] = state_hash(nominal)
        row["retained_steps"] = len(nominal["history"])
        row["identities"], lambdas = finite_time_identities(case, nominal, audit)
        row["ridge_pairs"] = ridge_pair_checks(case, nominal, lambdas, audit)
        row["nominal_branches"] = branch_summary(nominal)
        audit.require(row["nominal_branches"]["min_variance_raw"] > 0,
                      f"K={k}/strictly_positive_variance_branch", row["nominal_branches"])
        row["finite_differences"] = finite_difference_checks(case, nominal, audit)
        if k == CONFIG["reference"]["K"]:
            report["reference_consistency"] = reference_check(case, nominal, reference_namespace, audit)
        print(f"K={k}: completed T=10/20/40/80; cumulative failed checks={len(audit.failures)}", flush=True)
    report["counterexamples"] = counterexamples(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = {
        "schema_version": 1,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv,
        "executable": sys.executable,
        "cwd": str(Path.cwd()),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                     "platform": platform.platform()},
        "scope": "Deterministic algebra/JVP fixtures only; no actual C1 frames, Monte Carlo, FER, LDPC, SSH or fixed-point convergence claim",
        "config": CONFIG,
        "tolerances_frozen_before_run": TOLERANCES,
        "full_state_storage": "Primal pre/mid/post state and real JVP at every step retained in memory; report stores SHA256, not arrays",
        "status": "running",
    }
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text())
        failed_attempts = previous.get("previous_failed_attempts", [])
        if previous.get("status") != "passed":
            previous.pop("previous_failed_attempts", None)
            failed_attempts.append(previous)
        if failed_attempts:
            report["previous_failed_attempts"] = failed_attempts
    audit = Audit()
    try:
        run_checks(report, audit)
    except Exception:
        audit.require(False, "execution_exception", traceback.format_exc())
    report["checks_evaluated"] = audit.count
    report["failures"] = audit.failures
    report["status"] = "failed" if audit.failures else "passed"
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(f"{report['status']}: {audit.count} checks; report={OUTPUT}", flush=True)
    for failure in audit.failures:
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr, flush=True)
    return 1 if audit.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
