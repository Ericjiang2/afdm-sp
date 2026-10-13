"""Deterministic algebra and small synthetic frozen-TF qualification.

No archived observation, full receiver, decoder, or statistical FER experiment.
Run with a registered NumPy/SciPy environment and BLAS thread counts set to 1.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy

from tf_reaction_adapter import load_variant


ROOT = Path(__file__).resolve().parents[3]
PHYSICAL = ROOT / "experiments/sp_afdm_frozen_20260920/src"
sys.path.insert(0, str(PHYSICAL))
from physical import Channel, daft  # noqa: E402
from messages import moments  # noqa: E402

SOURCES = {
    "experiments/sp_afdm_frozen_20260920/src/physical.py":
        "c0398247b59d10366a0602a3bf115271e57d339e5a783691dd703e4da02348c6",
    "experiments/sp_afdm_frozen_20260920/src/messages.py":
        "9b19937c90a6e2b15f30d4e326320a38cd2635f9c0c5b14814406991da25ec95",
    "experiments/tf_cgr_mechanism_20260923_v2/tf_base.py":
        "0e3a94045b0b395c28efa02f181433bbc3aa2f569c05683ad83e1d1cf4f9699e",
    "experiments/sp_afdm_native_joint_20260921/src/twofft.py":
        "c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0",
}
RNG = np.random.default_rng(2026100102)
CALLS = 0


def complex_normal(shape):
    return (RNG.standard_normal(shape) + 1j * RNG.standard_normal(shape)) / np.sqrt(2)


def close(actual, expected, *, atol=2e-10, rtol=2e-10):
    if not np.allclose(actual, expected, atol=atol, rtol=rtol):
        raise AssertionError(f"mismatch: max absolute error={np.max(np.abs(actual-expected))}")
    return float(np.max(np.abs(actual - expected)))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def dense_path(n, delay, nu, c1, c2):
    """Explicit unitary DFT/chirp/CPP construction, independent of Channel.apply."""
    k = np.arange(n)
    f = np.exp(-2j * np.pi * k[:, None] * k[None, :] / n) / np.sqrt(n)
    a = np.diag(np.exp(2j * np.pi * c2 * k*k)) @ f @ np.diag(np.exp(2j * np.pi * c1 * k*k))
    shift = np.eye(n)[(k - delay) % n]
    cp = np.where(k < delay, np.exp(2j*np.pi*c1*(n*n+2*n*(k-delay))), 1.)
    u = a @ np.diag(np.exp(2j*np.pi*nu*k/n)*cp) @ shift @ a.conj().T
    return u, a


def sensitivity():
    bmat = complex_normal((8, 3))
    s, ridge = 3., .7
    e = np.array([[0., .8j, 0.], [-.8j, 0., 0.], [0., 0., 0.]])
    a0 = bmat.conj().T @ bmat + (s + ridge) * np.eye(3)
    a = a0 + e
    require(np.linalg.eigvalsh(s*np.eye(3)+e).min() > 0, "Gamma must be PSD")
    residuals, norms = [], []
    for h0 in (np.array([0., 0., 1.]), np.array([1., 0., 0.])):
        b = a0 @ h0
        h = np.linalg.solve(a, b)
        residuals.append(close(h-h0, -np.linalg.solve(a, e@h0)))
        norms.append(float(np.linalg.norm(h-h0)))
    require(norms[0] < 1e-12 and norms[1] > 1e-4, "directional null witness failed")
    vals, vecs = np.linalg.eigh(a0)
    invroot = (vecs / np.sqrt(vals)) @ vecs.conj().T
    root = (vecs * np.sqrt(vals)) @ vecs.conj().T
    f = invroot @ e @ invroot
    eta = np.linalg.norm(f, 2)
    h0 = complex_normal(3)
    h = np.linalg.solve(a, a0@h0)
    bound = np.linalg.norm(f@(root@h0))/(1-eta)
    actual = np.linalg.norm(root@(h-h0))
    require(eta < 1 and actual <= bound + 1e-12, "preconditioned bound failed")
    return {"identity_max_error": max(residuals), "same_E_gain_changes": norms,
            "eta": float(eta), "energy_error": float(actual), "energy_bound": float(bound)}


def candidate_certificate():
    h0 = complex_normal((6, 6)) / 3
    dh = complex_normal((6, 6)) / 100
    candidates = complex_normal((7, 6))
    y = h0 @ candidates[0] + complex_normal(6)/20
    r0 = y[None, :] - candidates @ h0.T
    change = candidates @ dh.T
    old = np.sum(abs(r0)**2, axis=1)
    new = np.sum(abs(r0-change)**2, axis=1)
    eps = 2*np.linalg.norm(r0, axis=1)*np.linalg.norm(change, axis=1) + np.sum(abs(change)**2, axis=1)
    require(np.all(abs(new-old) <= eps+1e-12), "candidate score bound failed")
    best = int(np.argmin(old))
    certificates = [old[j]-old[best] > eps[j]+eps[best] for j in range(7) if j != best]
    require(all(certificates) and np.argmin(new) == best, "positive margin fixture failed")
    flips = []
    for delta in (1e-3, 1e-6, 1e-9):
        target = 1.5 + .25*delta
        baseline = (target-np.array([1., 2.]))**2
        changed = (target-(1+delta)*np.array([1., 2.]))**2
        require(np.argmin(baseline) != np.argmin(changed), "arbitrarily small near-tie flip failed")
        flips.append({"perturbation": delta, "old_winner": int(np.argmin(baseline)),
                      "new_winner": int(np.argmin(changed))})
    return {"certified_fixed_bank_size": 7, "near_tie_counterexamples": flips}


def cluster_taylor():
    records = []
    for n in (8, 17, 64):
        t = (np.arange(n)-(n-1)/2)/n
        z = complex_normal(n)
        b0 = np.exp(2j*np.pi*.37*t)*z
        derivative = 2j*np.pi*t*b0
        for delta in (0., 1e-6, .001, .05, .3):
            for gains in (np.array([.7+.3j, -.2+.4j]), np.array([1., -1.])):
                minus = b0*np.exp(-1j*np.pi*delta*t)
                plus = b0*np.exp(1j*np.pi*delta*t)
                original = gains[0]*minus+gains[1]*plus
                a0 = gains.sum()
                a1 = delta*(gains[1]-gains[0])/2
                approx = a0*b0+a1*derivative
                error = np.linalg.norm(original-approx)
                bound = np.pi**2*delta**2*(n-1)**2/(8*n*n)*np.sum(abs(gains))*np.linalg.norm(z)
                require(error <= bound+5e-14, "Taylor remainder exceeded absolute bound")
                even = b0*np.cos(np.pi*delta*t)
                odd = derivative*np.sinc(delta*t)
                exact = a0*even+a1*odd
                close(exact, original)
                records.append({"n": n, "delta": delta, "opposite_gains": bool(gains.sum()==0),
                                "error": float(error), "bound": float(bound)})
    return {"cases": records, "max_error_minus_bound": max(r["error"]-r["bound"] for r in records)}


def cluster_prior_and_fit():
    n, delta, ridge = 19, .03, .2
    t = (np.arange(n)-(n-1)/2)/n
    z = complex_normal(n)
    b0 = np.exp(2j*np.pi*.4*t)*z
    original = np.column_stack([b0*np.exp(-1j*np.pi*delta*t), b0*np.exp(1j*np.pi*delta*t)])
    transform = np.array([[1., 1.], [-delta/2, delta/2]])
    inverse = np.linalg.inv(transform)
    modes = np.column_stack([b0*np.cos(np.pi*delta*t), 2j*np.pi*t*b0*np.sinc(delta*t)])
    close(modes@transform, original)
    penalty = inverse.conj().T@inverse
    close(penalty, np.diag([.5, 2/delta**2]))
    prior_cov = .125*transform@transform.conj().T
    close(prior_cov, np.diag([.25, .125*delta**2/2]))
    y = complex_normal(n)
    h = np.linalg.lstsq(np.vstack([original, np.sqrt(ridge)*np.eye(2)]), np.r_[y, np.zeros(2)], rcond=None)[0]
    a = np.linalg.lstsq(np.vstack([modes, np.sqrt(ridge)*inverse]), np.r_[y, np.zeros(2)], rcond=None)[0]
    err = close(a, transform@h)
    wrong = np.linalg.solve(modes.conj().T@modes+ridge*np.eye(2), modes.conj().T@y)
    require(np.linalg.norm(modes@(wrong-a)) > 1e-3, "wrong isotropic prior witness failed")
    # At delta=0 finite original gains force a1=0, and eliminating their difference gives ridge/2.
    original_zero = np.column_stack([b0, b0])
    hzero = np.linalg.solve(original_zero.conj().T@original_zero+ridge*np.eye(2), original_zero.conj().T@y)
    a0 = np.vdot(b0,y)/(np.vdot(b0,b0).real+ridge/2)
    close(hzero.sum(), a0)
    return {"exact_regularized_change_error": err, "correct_penalty_diagonal": np.diag(penalty).tolist(),
            "wrong_prior_prediction_change": float(np.linalg.norm(modes@(wrong-a))),
            "delta_zero_merged_ridge": ridge/2}


def cluster_gamma():
    rows = []
    for n in (8, 17):
        c1, c2, nu, delay = 5/(2*n), .031, .37, 2
        u, a = dense_path(n, delay, nu, c1, c2)
        k = np.arange(n)
        t = (k-(n-1)/2)/n
        phase = np.exp(-2j*np.pi*nu*(n-1)/(2*n))
        u0 = phase*u
        u1 = a@np.diag(2j*np.pi*t)@a.conj().T@u0
        v = .05+RNG.random(n)
        vv = np.diag(v)
        operators = [u0, u1]
        gamma = np.array([[np.trace(x.conj().T@y@vv) for y in operators] for x in operators])
        expected = v.sum()*np.diag([1., np.pi**2*(1-1/n**2)/3])
        residual = close(gamma, expected)
        channel = Channel(n,c1,c2,np.array([delay]),np.array([nu]),np.ones(1))
        x = complex_normal(n)
        close(u@x,channel.apply(x))
        centered_derivative = phase*(channel.regressors(x,derivative=True)[:,0]-2j*np.pi*(n-1)/(2*n)*channel.regressors(x)[:,0])
        close(u1@x,centered_derivative)
        other, _ = dense_path(n, delay+1, -.41, c1, c2)
        cross = np.trace(u1.conj().T@other@vv)
        require(abs(cross) > 1e-5, "cross-cluster term unexpectedly zero")
        # Arbitrary dense PSD V does not obey the AF-diagonal contraction.
        q = complex_normal(n)
        dense_v = np.outer(q,q.conj())
        non_diagonal_cross = np.trace(u0.conj().T@u1@dense_v)
        require(abs(non_diagonal_cross) > 1e-5, "dense covariance counterexample failed")
        rows.append({"n":n,"gamma_max_error":residual,"cross_cluster_magnitude":float(abs(cross)),
                     "dense_V_cross_magnitude":float(abs(non_diagonal_cross))})
    return {"cases": rows}


def condition_boundary():
    n = 32
    t = (np.arange(n)-(n-1)/2)/n
    rows = []
    for delta in (.1,.01,.001,1e-6):
        old = np.column_stack([np.exp(-1j*np.pi*delta*t), np.exp(1j*np.pi*delta*t)])
        modes = np.column_stack([np.cos(np.pi*delta*t),2j*np.pi*t*np.sinc(delta*t)])
        rows.append({"delta":delta,"physical_condition":float(np.linalg.cond(old)),
                     "mode_condition":float(np.linalg.cond(modes))})
    z = np.zeros(n);z[3]=1
    degenerate = np.column_stack([z, 2j*np.pi*t*z])
    require(np.linalg.matrix_rank(degenerate)==1, "sparse-waveform counterexample failed")
    # A single supported sample can cancel the exact signal while Taylor output is nonzero.
    delta=.3
    hminus=1.
    hplus=-np.exp(-2j*np.pi*delta*t[3])
    exact=z*(hminus*np.exp(-1j*np.pi*delta*t)+hplus*np.exp(1j*np.pi*delta*t))
    approx=(hminus+hplus)*z+delta*(hplus-hminus)/2*(2j*np.pi*t*z)
    require(np.linalg.norm(exact)<1e-14 and np.linalg.norm(approx)>1e-5,
            "relative-error counterexample failed")
    return {"condition_sweep":rows,"degenerate_mode_rank":1,
            "relative_counterexample_exact_norm":float(np.linalg.norm(exact)),
            "relative_counterexample_approx_norm":float(np.linalg.norm(approx))}


def call_tf(module, *args, **kwargs):
    global CALLS
    CALLS += 1
    return module.scalar_joint(*args, **kwargs)


def tf_contract():
    tf_path = ROOT/"experiments/tf_cgr_mechanism_20260923_v2/tf_base.py"
    digest = SOURCES[str(tf_path.relative_to(ROOT))]
    variants = {mode: load_variant(tf_path,expected_sha256=digest,mode=mode) for mode in ("identity","coherent","full")}
    spec = importlib.util.spec_from_file_location("untouched_tf",tf_path)
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    n=16;c1=5/(2*n);c2=.013
    c=Channel(n,c1,c2,np.array([2,2,5]),np.array([.21,.27,-.6]),complex_normal(3)/2)
    prior=RNG.uniform(-3.,3.,2*n);pilot=complex_normal(n)/3;y=complex_normal(n)
    args=(y,pilot,c,.4)
    old=call_tf(original,*args,prior=prior,iterations=3,record_states=True)
    unchanged=call_tf(variants["identity"],*args,prior=prior,iterations=3,record_states=True)
    for key in ("extrinsic","app","mu","variance","gains","gain_variance"):
        require(np.array_equal(old[key],unchanged[key]),f"identity parity failed: {key}")
    results={mode:call_tf(module,*args,prior=prior,iterations=1,record_states=True) for mode,module in variants.items()}
    base=results["identity"]["states"][0]
    _,v,_=moments(prior,.5)
    identity=n*v.mean()*np.eye(c.p)
    coherent=n*v.mean()*base["gain_R"]
    full=c.gamma(v)
    residuals={}
    for mode,matrix in (("coherent",coherent),("full",full)):
        prediction=-base["alpha"]/(c.p+1/base["vq"])*(matrix-identity)@base["hbar"]
        residuals[mode]=close(results[mode]["gains"]-results["identity"]["gains"],prediction)
        require(np.array_equal(results[mode]["extrinsic"],results["identity"]["extrinsic"]),
                "final gain update changed already computed LLR")
    two={mode:call_tf(module,*args,prior=prior,iterations=2) for mode,module in variants.items()}
    llr_change=float(np.linalg.norm(two["full"]["extrinsic"]-two["identity"]["extrinsic"]))
    require(llr_change>1e-7,"second-iteration LLR sensitivity missing")
    # Observers are not numerical inputs, and AF/time rotation must preserve the adapter.
    full_record=call_tf(variants["full"],*args,prior=prior,iterations=2,record_states=True)
    require(np.array_equal(two["full"]["extrinsic"],full_record["extrinsic"]),"observer altered output")
    full_af=call_tf(variants["full"],*args,prior=prior,iterations=2,observation_domain="af")
    rotation_error=close(two["full"]["extrinsic"],full_af["extrinsic"])
    # Uniform marginal variances imply full Gamma=sR, even with repeated delays.
    uniform={mode:call_tf(module,*args,prior=np.zeros(2*n),iterations=1)
             for mode,module in variants.items()}
    uniform_error=close(uniform["full"]["gains"],uniform["coherent"]["gains"])
    return {"identity_exact_array_fields":6,"common_state_gain_errors":residuals,
            "last_step_llr_unchanged":True,"second_step_full_identity_llr_l2":llr_change,
            "af_time_llr_max_error":rotation_error,"uniform_full_coherent_gain_error":uniform_error}


def adapter_guards():
    path=ROOT/"experiments/sp_afdm_native_joint_20260921/src/twofft.py"
    digest=SOURCES[str(path.relative_to(ROOT))]
    for mode in ("identity","coherent","full"):
        load_variant(path,expected_sha256=digest,mode=mode)
    for expected,mode in (("0"*64,"full"),(digest,"unknown")):
        try:
            load_variant(path,expected_sha256=expected,mode=mode)
        except ValueError:
            continue
        raise AssertionError("adapter failed to reject invalid input")
    return {"native_source_modes_compiled":3,"invalid_configurations_rejected":2}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    for relative,expected in SOURCES.items():
        require(sha(ROOT/relative)==expected,f"source drift: {relative}")
    require(Path(sys.modules["physical"].__file__).resolve()==PHYSICAL/"physical.py", "wrong physical dependency")
    for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
        require(os.environ.get(name)=="1",f"set {name}=1 before numerical qualification")
    started=time.perf_counter()
    cases=[]
    for check in (sensitivity,candidate_certificate,cluster_taylor,cluster_prior_and_fit,
                  cluster_gamma,condition_boundary,tf_contract,adapter_guards):
        try:
            detail=check()
            cases.append({"check":check.__name__,"status":"pass","detail":detail})
        except Exception as exc:
            cases.append({"check":check.__name__,"status":"fail","error_type":type(exc).__name__,"error":str(exc)})
    passed=all(case["status"]=="pass" for case in cases)
    report={"status":"pass" if passed else "fail","scope":"synthetic algebra and small frozen TF module calls",
            "new_observations":0,"full_receivers":0,"decoders":0,"synthetic_tf_calls":CALLS,
            "seed":2026100102,"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,
            "thread_environment":{key:os.environ[key] for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
            "source_sha256":SOURCES,"checker_sha256":sha(Path(__file__)),
            "adapter_sha256":sha(Path(__file__).with_name("tf_reaction_adapter.py")),
            "elapsed_seconds":time.perf_counter()-started,"checks":cases}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"checks":len(cases),"synthetic_tf_calls":CALLS,
                      "failures":[case for case in cases if case["status"]=="fail"]},ensure_ascii=False))
    return 0 if passed else 1


if __name__=="__main__":
    raise SystemExit(main())
