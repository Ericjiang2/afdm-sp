Review one small fixed-channel AFDM receiver experiment as a rigorous communications/signal-processing reviewer. The user explicitly requests Claude Opus 5.5. Do not execute tools or experiments. Use the supplied facts and code. English response, around 1000-1600 words, prioritize precise equations/bugs/fairness and the smallest corrective validation. Avoid global novelty claims.

SETTING AND EXECUTION
N=1024, QPSK data power .5, eight estimated physical paths with integer sample delays, fractional Dopplers, CPP, fixed estimated channel for both arms. Thermal noise is proper complex with scalar variance sigma2. Bit order all I then all Q. 40 frames selected by nonzero final native syndrome out of the saved 1024-frame 6.5dB September23 population. Native TF had 40 information-word errors and archived CSTATE rescued34. These frames predate an October generator correction; all conclusions stay within this reused cohort. Both new arms start with identical saved final channel gains and clipped LDPC check-extrinsic prior. TF fixed executes20 scalar iterations before each LDPC invocation. The OAMP-inspired adapter executes1 scalar trace-normalized LMMSE update before each LDPC invocation. Both were capped at2 additional LDPC calls,50 sweeps maximum,clip±20. No OAMP damping sweep or convergence diagnostic was done. The nonlinear module is the code decoder. Prior is obtained by mapping decoder check extrinsic to QPSK moments, then using average symbol variance as isotropic covariance; mean crosses DAFT to time domain. A dense time-domain Gram eigendecomposition is done once per frame.

The OAMP-inspired linear stage was checked against direct LMMSE and scaled-identity channel. Physical time operator checked against independent AF-domain apply for each frame. A separate saved-output reader checked160 decoded checkpoints, pairing, counts and feedback replacement. Those checks do not establish fidelity to a named OAMP algorithm.

OBSERVED SUMMARY
{
  "tf_fixed": {
    "rescued": [
      12,
      14
    ],
    "cstate_rescues_recovered": 14,
    "cstate_failures_rescued": 0,
    "median_seconds": 0.08607739070430398
  },
  "oamp": {
    "rescued": [
      6,
      9
    ],
    "cstate_rescues_recovered": 9,
    "cstate_failures_rescued": 0,
    "median_seconds": 0.6291087912395597
  },
  "oamp_vs_tf_fixed": {
    "rescues": 1,
    "harms": 6,
    "median_time_ratio": 7.308641515409033,
    "advance": false
  }
}
OAMP setup median=.574439693s, full continuation median=.629108791s. TF median=.086077391s. This is single-thread NumPy/SciPy CPU. New calls2 arms*40frames*2decodes=160 LDPC. The initial frozen screen required≥17/34 CSTATE rescues AND median time≤2x TF, and both failed. We need evaluate what this can support, especially whether we built an unfair/incomplete OAMP baseline.

USER QUESTIONS
1. Are2 rounds sufficient? Is convergence checked? Distinguish LE/NLE exchanges and inner TF symbol iterations versus LDPC sweeps. Is matched decoder-call count meaningful here?
2. Does the implementation qualify as OAMP/LDPC, or only an OAMP-inspired linear-extrinsic turbo loop? In particular audit the decoder-to-linear Gaussian extrinsic: is bit-check-extrinsic mapped via tanh enough, or should scalar Gaussian orthogonalization/precision subtraction also be done? Distinguish a valid alternative convention from a demonstrable error.
3. Does rotation to time coordinates while keeping only scalar variance preserve the intended isotropic OAMP map? Separate it from nonuniform exact SISO-LMMSE covariance.
4. Is0.63s forN1024 plausible for a dense complex eigendecomposition? IsOAMP inherently sparse/low-complexity? What exact lower-cost solver can preserve the same LE and trace-normalization on this physical channel? Consider existing exact cyclic-band Gaussian solver supplied below. How should setup amortization and complete latency be reported?
5. What are the smallest two separate follow-ups that decide iteration truncation and implementation overhead, with no result-driven hyperparameter selection? Say what should be corrected in the previous readout now. Do not treat known small-cohort counts as population inferiority.

REFERENCES AVAILABLE TO MAIN SESSION (authoritative formulas, not asserted correct)
Ma/Ping OrthogonalAMP arXiv1602.06509 §III/IV/V: decorrelated LE and divergence-free NLE. LMMSE inversion may cost more thanAMP; partial orthogonalA simplifies. Their numerical examples use50 iterations.
Luo etal AFDM-SCMA arXiv2312.11302 §IV-C,Eq56,60-65: precision subtraction of scalar Gaussian moments between modules, damping. §V-C uses10outerOAMP iterations,8innerLDPC, damping.25. HTML formulas have possible transcription errors, so derive valid relations rather than blindly copying them.
Huang etal OAMP-JED ODDM arXiv2606.25420 uses10JED iterations and exploits block structure for complexity. This is a different waveform/geometry model. Do not infer this SP-AFDM receiver has that same block diagonal structure.

CODE. The complete original experiment follows.
```python
"""Replay observed fixed-channel continuations, then score sealed decisions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from scipy.linalg import eigh

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "tf_production_gap_audit_20260922"))
from audit_io import attach, load_bound, sha256, write_json

ARCHIVE = PROJECT / "results/tf_cstate_prospective_20260923"
SOURCE = HERE.parent / "sp_afdm_native_joint_reviewed_20260921"
BASELINE = HERE.parent / "sp_afdm_frozen_reviewed_20260921"
ARMS = ("tf_fixed", "oamp")
ROUNDS = 2


class LinearOAMP:
    """Scalar Gaussian extrinsic from a fixed channel in observation coordinates."""

    def __init__(self, matrix, observation, noise):
        self.noise = noise
        gram = matrix.conj().T @ matrix
        self.eigenvalues, self.basis = eigh(gram.toarray() if hasattr(gram, "toarray") else gram)
        if self.eigenvalues[0] < -1e-10 * self.eigenvalues[-1]:
            raise FloatingPointError("channel Gram matrix is not positive semidefinite")
        self.eigenvalues = np.maximum(self.eigenvalues, 0)
        self.rhs = self.basis.conj().T @ (matrix.conj().T @ observation)

    def extrinsic(self, mean, variance):
        eigenvalues = self.eigenvalues
        loading = self.noise / variance
        denom = eigenvalues + loading
        response = np.mean(eigenvalues / denom)
        tau = variance * np.mean(loading / denom) / response
        residual = self.rhs - eigenvalues * (self.basis.conj().T @ mean)
        center = mean + self.basis @ (residual / denom) / response
        if not np.isfinite(center).all() or not 0 < tau < np.inf:
            raise FloatingPointError("invalid OAMP extrinsic")
        return center, tau


def qualify():
    rng = np.random.default_rng(19)
    h = rng.normal(size=(8, 8)) + 1j * rng.normal(size=(8, 8))
    y = rng.normal(size=8) + 1j * rng.normal(size=8)
    mu = rng.normal(size=8) + 1j * rng.normal(size=8)
    noise, v = 0.25, 0.4
    w = np.linalg.solve(h.conj().T @ h + (noise / v) * np.eye(8), h.conj().T)
    q = np.trace(w @ h).real / 8
    center, tau = LinearOAMP(h, y, noise).extrinsic(mu, v)
    np.testing.assert_allclose(center, mu + (w @ (y - h @ mu)) / q, atol=1e-12)
    np.testing.assert_allclose(tau, v * (1 - q) / q, atol=1e-12)
    center, tau = LinearOAMP(2 * np.eye(8), y, noise).extrinsic(mu, v)
    np.testing.assert_allclose(center, y / 2, atol=1e-12)
    np.testing.assert_allclose(tau, noise / 4, atol=1e-12)


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def continue_receiver(arm, obs, channel, prior, code, pd):
    from messages import moments
    from physical import daft
    from receiver import decoder_messages
    from structured_ep import time_matrix
    from twofft import scalar_joint

    start = perf_counter()
    if arm == "oamp":
        h = time_matrix(channel)
        transform = lambda x, inverse=False: daft(x, channel.c1, channel.c2, inverse)
        y = transform(obs["y"], True) - h @ transform(obs["pilot"], True)
        oamp = LinearOAMP(h, y, obs["sigma2"])
    setup = perf_counter() - start
    rounds = []
    for _ in range(ROUNDS):
        detector_start = perf_counter()
        if arm == "oamp":
            mu, v, _ = moments(prior, pd)
            r, tau = oamp.extrinsic(transform(mu, True), float(v.mean()))
            z = transform(r) * (4 * np.sqrt(pd / 2) / tau)
            llr = np.r_[z.real, z.imag]
        else:
            llr = scalar_joint(obs["y"], obs["pilot"], channel, obs["sigma2"],
                               pd=pd, prior=prior, gain_mode="fixed",
                               iterations=20, damping=0.3)["extrinsic"]
        decoder_start = perf_counter()
        decoded = decoder_messages(code, np.clip(llr, -20, 20), maxiter=50)
        decoder_seconds = perf_counter() - decoder_start
        rounds.append(dict(incoming=decoded["incoming_llr"], decoded=decoded["decoded"],
                           check=decoded["raw_check_extrinsic"], prior=prior,
                           sweeps=decoded["iterations"], detector_seconds=decoder_start - detector_start,
                           decoder_seconds=decoder_seconds))
        prior = np.clip(decoded["raw_check_extrinsic"], -20, 20)
    return dict(rounds=rounds, setup_seconds=setup, seconds=perf_counter() - start)


def observed_replay(out, evidence, system, code):
    from physical import Channel, daft
    from structured_ep import time_matrix

    population = ARCHIVE / "population_observed"
    observed = ARCHIVE / "observed"
    pop = {r["observation_id"]: r for r in rows(population / "ledger.jsonl")
           if r["snr_centi_db"] == 650}
    cell = [r for r in rows(observed / "ledger.jsonl") if r["snr_centi_db"] == 650]
    native = {r["observation_id"]: r for r in cell if r["arm"] == "TF"}
    cstate = {r["observation_id"]: r for r in cell if r["arm"] == "TF_CSTATE"}
    if set(pop) != set(native) or set(pop) != set(cstate) or len(pop) != 1024 or len(cell) != 2048:
        raise ValueError("archived cell does not have 1024 complete paired frames")
    triggered = sorted(key for key, row in cstate.items() if row["triggered"])
    if len(triggered) != 40 or any(r["status"] != "ok" for r in cell):
        raise ValueError("archived trigger count or status differs")
    sealed = []
    for index, key in enumerate(triggered):
        p, tf, cs = pop[key], native[key], cstate[key]
        if not tf["input_sha256"] == cs["input_sha256"] == p["observation_sha256"]:
            raise ValueError(f"archived pairing differs for {key}")
        obs = load_bound(evidence, population / p["observation_path"], p["observation_sha256"])["observation"]
        saved = load_bound(evidence, observed / tf["raw_path"], tf["raw_sha256"])
        saved_cstate = load_bound(evidence, observed / cs["raw_path"], cs["raw_sha256"])
        if (not np.array_equal(saved["native_decoder"]["decoded"], saved_cstate["native_decoder"]["decoded"])
                or not np.any((code["H"] @ saved["final_decoded"]) % 2)):
            raise ValueError(f"archived prefix/trigger differs for {key}")
        cp = saved["baseline_arrays"]
        prior = np.clip(cp["r1_check"], -20, 20)
        channel = Channel(len(obs["y"]), system.c1, system.c2, cp["r1_delays"],
                          cp["r1_dopplers"], cp["r1_gains"])
        pilot = obs["pilot"]
        applied = time_matrix(channel) @ daft(pilot, system.c1, system.c2, True)
        np.testing.assert_allclose(daft(applied, system.c1, system.c2), channel.apply(pilot), atol=1e-11)
        order = ARMS if index % 2 == 0 else ARMS[::-1]
        print(f"START {index + 1}/40 {key} {order}", flush=True)
        decisions = {arm: continue_receiver(arm, obs, channel, prior, code, 1 - system.rho)
                     for arm in order}
        path = out / f"{key}.npz"
        digest = evidence.save_artifact(
            path, dict(decisions=decisions, tf=saved["final_decoded"], cstate=saved_cstate["final_decoded"]),
            dict(observation_id=key, observation_sha256=p["observation_sha256"],
                 native_sha256=tf["raw_sha256"], cstate_sha256=cs["raw_sha256"]))
        sealed.append(dict(observation_id=key, path=path.name, sha256=digest,
                           observation_hash=p["observation_hash"]))
    write_json(out / "observed_seal.json", sealed)


def score(out, evidence, code):
    from receiver import extract_info

    sealed = json.loads((out / "observed_seal.json").read_text())
    if len(sealed) != 40 or len({row["observation_id"] for row in sealed}) != 40:
        raise ValueError("expected 40 unique sealed decisions")
    truth = ARCHIVE / "population_truth"
    labels = {r["observation_id"]: r for r in rows(truth / "ledger.jsonl")}
    scored = []
    for ref in sealed:
        label = labels[ref["observation_id"]]
        if label["observation_hash"] != ref["observation_hash"]:
            raise ValueError("truth observation identity differs")
        info = load_bound(evidence, truth / label["truth_path"], label["truth_sha256"])["info"]
        payload = load_bound(evidence, out / ref["path"], ref["sha256"])
        errors = {name: int(np.count_nonzero(extract_info(code, payload[name]) != info))
                  for name in ("tf", "cstate")}
        scores = {}
        for arm, decision in payload["decisions"].items():
            rounds = decision["rounds"]
            if len(rounds) != ROUNDS or not np.array_equal(
                    rounds[1]["prior"], np.clip(rounds[0]["check"], -20, 20)):
                raise ValueError("decoder feedback identity differs")
            scores[arm] = dict(errors=[int(np.count_nonzero(extract_info(code, d["decoded"]) != info))
                                       for d in rounds], seconds=decision["seconds"],
                               setup_seconds=decision["setup_seconds"],
                               sweeps=[d["sweeps"] for d in rounds])
        scored.append(dict(observation_id=ref["observation_id"], **errors, **scores))
    if sum(r["tf"] != 0 for r in scored) != 40 or sum(r["cstate"] == 0 for r in scored) != 34:
        raise ValueError("archive score differs from original 40 errors and 34 rescues")
    results = {}
    for arm in ARMS:
        results[arm] = dict(rescued=[sum(r[arm]["errors"][i] == 0 for r in scored) for i in range(ROUNDS)],
                            cstate_rescues_recovered=sum(r["cstate"] == 0 and r[arm]["errors"][-1] == 0 for r in scored),
                            cstate_failures_rescued=sum(r["cstate"] != 0 and r[arm]["errors"][-1] == 0 for r in scored),
                            median_seconds=float(np.median([r[arm]["seconds"] for r in scored])))
    a, b = results["oamp"], results["tf_fixed"]
    results["oamp_vs_tf_fixed"] = dict(
        rescues=sum(r["oamp"]["errors"][-1] == 0 and r["tf_fixed"]["errors"][-1] != 0 for r in scored),
        harms=sum(r["oamp"]["errors"][-1] != 0 and r["tf_fixed"]["errors"][-1] == 0 for r in scored),
        median_time_ratio=a["median_seconds"] / b["median_seconds"],
        advance=a["cstate_rescues_recovered"] >= 17 and a["median_seconds"] <= 2 * b["median_seconds"])
    run_config = json.loads((out / "config.json").read_text())
    write_json(out / "results.json", dict(**run_config, score_argv=sys.argv,
                                         results=results, frames=scored))
    print(json.dumps(results), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("qualify", "observe", "score"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.phase == "qualify":
        qualify()
        print("PASS direct LMMSE and scaled identity")
        return
    out = args.out
    evidence = attach(SOURCE, BASELINE)
    registration_path = ARCHIVE / "protocol/registration.json"
    registration = json.loads(registration_path.read_text())
    for path, key in ((SOURCE, "native_source_hashes"), (BASELINE, "baseline_source_hashes")):
        if evidence.source_hashes(path) != registration[key]:
            raise ValueError(f"frozen {key} differ")
    from receiver import context

    system, _, code, header = context()
    if (header["code_g_sha256"] != registration["code_g_sha256"] or
            sha256(code["cache_path"]) != registration["ldpc_cache_sha256"] or system.rho != 0.5):
        raise ValueError("frozen system or code differs")
    if args.phase == "score":
        score(out, evidence, code)
        return
    qualify()
    write_json(out / "config.json", dict(_argv=sys.argv, _config=dict(
        protocol_sha256=sha256(HERE / "PROTOCOL.md"), code_sha256=sha256(__file__),
        archive_registration_sha256=sha256(registration_path), environment=header["environment"],
        ldpc_h_sha256=hashlib.sha256(code["H"].tobytes()).hexdigest(),
        snr_db=6.5, expected_triggers=40, ldpc_rounds=ROUNDS, ldpc_maxiter=50, threads=1)))
    observed_replay(out, evidence, system, code)


if __name__ == "__main__":
    main()

```

Existing cyclic-band solver and physical time matrix (read-only candidate for solver reuse).
```python
"""Proper-complex dual-domain EP adaptation, not verbatim real-valued EP-T.
Exact cyclic-band Gaussian mean and inverse diagonal. Domain crossing projects
covariances to their marginals; constellation/LDPC factors remain in AF domain.
"""
import numpy as np
from scipy import sparse
from scipy.linalg import cholesky_banded,cho_solve_banded,cho_factor,cho_solve
from physical import daft
from messages import alphabet,marginal

def band_inverse_diagonal(R,b):
    n=R.shape[1];Z=np.zeros((n,b+1),complex)
    for i in range(n-1,-1,-1):
        js=np.arange(i+1,min(n,i+b+1));ri=R[b,i]
        if len(js):
            p,q=np.meshgrid(js,js,indexing='ij');lo=np.minimum(p,q);hi=np.maximum(p,q)
            B=Z[lo,hi-lo];B=np.where(p<=q,B,B.conj());r=R[b+i-js,js]/ri
            z=-r@B;Z[i,js-i]=z;Z[i,0]=1/abs(ri)**2-np.dot(r,z.conj())
        else:Z[i,0]=1/abs(ri)**2
    return Z[:,0].real

class CyclicSolver:
    """Q cyclic half-band b; first b variables form an exact Schur border."""
    def __init__(self,Q,b):
        Q=sparse.csc_matrix(Q);self.n=Q.shape[0];self.b=int(b);self.dense=b>=self.n/2
        if self.dense:
            self.cf=cho_factor(Q.toarray(),lower=True);self.diag=np.diag(cho_solve(self.cf,np.eye(self.n))).real;return
        if b==0:self.diag=1/Q.diagonal().real;return
        A=Q[:b,:b].toarray();self.B=Q[:b,b:].toarray();D=Q[b:,b:].tocoo();nn=self.n-b
        if np.any(abs(D.row-D.col)>b):raise ValueError('Matrix exceeds declared cyclic bandwidth')
        ab=np.zeros((b+1,nn),complex);sel=D.row<=D.col;ab[b+D.row[sel]-D.col[sel],D.col[sel]]=D.data[sel]
        self.R=cholesky_banded(ab,lower=False,check_finite=False)
        self.W=cho_solve_banded((self.R,False),self.B.conj().T,check_finite=False)
        self.S=cho_factor(A-self.B@self.W,lower=True,check_finite=False);si=cho_solve(self.S,np.eye(b),check_finite=False)
        self.diag=np.r_[np.diag(si).real,band_inverse_diagonal(self.R,b)+np.einsum('ij,ij->i',self.W@si,self.W.conj()).real]
    def solve(self,r):
        if self.dense:return cho_solve(self.cf,r)
        if self.b==0:return self.diag*r
        b=self.b;dr=cho_solve_banded((self.R,False),r[b:],check_finite=False)
        ra=cho_solve(self.S,r[:b]-self.B@dr,check_finite=False)
        return np.r_[ra,dr-self.W@ra]

def time_matrix(c):
    n=c.n;k=np.arange(n);rr=[];cc=[];vv=[]
    for l,nu,h in zip(c.delays,c.dopplers,c.gains):
        cp=np.where(k<l,np.exp(2j*np.pi*c.c1*(n*n+2*n*(k-l))),1)
        rr.extend(k);cc.extend((k-l)%n);vv.extend(h*cp*np.exp(2j*np.pi*nu*k/n))
    return sparse.coo_matrix((vv,(rr,cc)),shape=(n,n)).tocsc()


```

TF scalar inner map
```python
"""Two-FFT realization of scalar-variance parametric bilinear AMP for SP-AFDM.
No dense channel/tensor, no independent time-domain QPSK prior, no tail deletion.
The inferential approximation is scalar P-BiG-AMP (Parker/Schniter); the exact
change is a unitary observation rotation and the path-operation contractions.
"""
import numpy as np
from scipy.optimize import minimize_scalar
from physical import Channel,daft,dkernel
from messages import alphabet,marginal,moments

class TimePathOps:
    def __init__(self,c):
        self.c=c;self.n=c.n;self.P=c.p;n=c.n;k=np.arange(n)
        if n<1 or self.P<1 or np.any(c.delays<0) or np.any(c.delays>=n):raise ValueError('invalid path dimensions/delays')
        if not np.isfinite(c.dopplers).all() or not np.isfinite(c.gains).all():raise ValueError('nonfinite paths')
        self.idx=(k[:,None]-c.delays)%n
        wrap=k[:,None]-c.delays
        cp=np.where(wrap<0,np.exp(2j*np.pi*c.c1*(n*n+2*n*wrap)),1.)
        self.phase=cp*np.exp(2j*np.pi*k[:,None]*c.dopplers/n)
        self.R=(c.delays[:,None]==c.delays[None,:])*dkernel(c.dopplers[None,:]-c.dopplers[:,None],n)
    def responses_time(self,xt):return self.phase*xt[self.idx]
    def adjoint_time(self,h,z):
        q=self.phase.conj()*z[:,None]*h.conj()
        return sum(np.roll(q[:,i],-int(l)) for i,l in enumerate(self.c.delays))
    def power(self,h):
        value=float(np.vdot(h,self.R@h).real)
        if value < -1e-10*max(float(np.vdot(h,h).real),1.):raise FloatingPointError('non-PSD physical norm')
        return max(value,0.)

def scalar_joint(y,pilot,c,noise,pd=.5,prior=None,iterations=20,damping=.3,gain_mode='joint',record_states=False,observation_domain='time'):
    """Observed-only detector. Gain prior CN(0,I/P), reused once per batch.
    c.gains is initialization, never an independent observation-derived prior.
    Fixed-gain and zero-variance gain-mean-update controls are explicitly named.
    In each iteration only one IDAFT (new x) and one DAFT (adjoint) are needed;
    B(xbar) is updated by linearity, not with an extra transform.
    """
    y=np.asarray(y,complex);pilot=np.asarray(pilot,complex);n=c.n;P=c.p
    if y.shape!=(n,) or pilot.shape!=(n,) or noise<=0 or not np.isfinite(noise):raise ValueError('observation/noise')
    if iterations<1 or not 0<damping<=1 or gain_mode not in ('joint','point','fixed') or observation_domain not in ('time','af'):raise ValueError('configuration')
    if not np.isfinite(y).all() or not np.isfinite(pilot).all():raise ValueError('nonfinite observations')
    if prior is None:prior=np.zeros(2*n)
    prior=np.asarray(prior,float)
    if prior.shape!=(2*n,) or not np.isfinite(prior).all() or pd<=0:raise ValueError('invalid code prior/data power')
    a,_=alphabet(pd);mu,v,_=moments(prior,pd);x=pilot+mu
    o=TimePathOps(c);Y=daft(y,c.c1,c.c2,True) if observation_domain=='time' else y.copy()
    h=c.gains.copy();vh=1/P if gain_mode=='joint' else 0.;tau=1/P
    xb=x.copy();hb=h.copy();Bb=None;s=np.zeros(n,complex);sv=0.;bar0=None;vp0=None;trace=[];states=[]
    for it in range(iterations):
        xt=daft(x,c.c1,c.c2,True);B=o.responses_time(xt);vx=float(v.mean());ex=float(np.vdot(x,x).real)
        channel_norm=o.power(h)
        bar=vx*channel_norm+P*vh*ex/n;vp=bar+P*vh*vx
        if bar0 is not None:bar=damping*bar+(1-damping)*bar0;vp=damping*vp+(1-damping)*vp0
        bar0=bar;vp0=vp
        z=B@h
        if observation_domain=='af':z=daft(z,c.c1,c.c2)
        ph=z-s*bar
        s=damping*(Y-ph)/(noise+vp)+(1-damping)*s;sv=damping/(noise+vp)+(1-damping)*sv
        st=s if observation_domain=='time' else daft(s,c.c1,c.c2,True)
        xb=damping*x+(1-damping)*xb;hb=damping*h+(1-damping)*hb
        Bb=B.copy() if Bb is None else damping*B+(1-damping)*Bb
        data_precision=sv*o.power(hb);gain_precision=sv*np.vdot(xb,xb).real
        vr=1/max(data_precision,1e-12);vq=1/max(gain_precision,1e-12)
        adj=daft(o.adjoint_time(hb,st),c.c1,c.c2)
        rx=x+vr*(adj-xb*(sv*P*vh))
        rh=h+vq*(Bb.conj().T@st-hb*sv*n*vx)
        ext,app,mu,v=marginal(-abs((rx-pilot)[:,None]-a)**2/vr,prior,pd);x=pilot+mu
        vh=tau*vq/(tau+vq) if gain_mode=='joint' else 0.
        if gain_mode!='fixed':h=tau*rh/(tau+vq)
        if not all(np.isfinite(q).all() for q in (h,mu,v,s)):raise FloatingPointError('nonfinite scalar joint update')
        trace.append(dict(iteration=it,data_variance=float(v.mean()),gain_variance=float(vh),
                          channel_norm_factor=float(channel_norm),pseudo_variance_bar=float(bar),
                          pseudo_variance_total=float(vp),data_pseudo_variance=float(vr),
                          gain_pseudo_variance=float(vq),output_precision=float(sv),
                          data_precision_floor=bool(data_precision<=1e-12),
                          gain_precision_floor=bool(gain_precision<=1e-12),
                          fft_count=2 if observation_domain=='time' else 4))
        if record_states:states.append(dict(h=h.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),vr=vr,vq=vq,vh=vh,sv=sv,bar=bar,vp=vp))
    out=dict(extrinsic=ext,app=app,mu=mu,variance=v,gains=h,gain_variance=np.full(P,vh),trace=trace,iterations=iterations,fft_count=2*iterations+1 if observation_domain=='time' else 4*iterations)
    if record_states:out['states']=states
    return out


```

QPSK moments and marginal definition
```python
"""All bit vectors use the upstream ALL-I THEN ALL-Q order. L>0 means bit zero.
Output APP and extrinsic are distinct; decoder priors are replacements.
"""
import numpy as np
from scipy.special import logsumexp

def alphabet(pd):
    a=np.sqrt(pd/2);return a*np.array([1+1j,1-1j,-1+1j,-1-1j]),np.array([[0,0],[0,1],[1,0],[1,1]])
def logprior(L,pd):
    L=np.asarray(L,float);n=len(L)//2
    if L.ndim!=1 or len(L)%2 or not np.isfinite(L).all():raise ValueError('Invalid grouped LLR vector')
    _,bits=alphabet(pd);li=np.column_stack((L[:n],L[n:]));a=.5*li@(1-2*bits).T
    return a-logsumexp(a,axis=1,keepdims=True)
def moments(L,pd):
    p=np.exp(logprior(L,pd));a,_=alphabet(pd);mu=p@a
    return mu,np.maximum(pd-abs(mu)**2,0),p@(a*a)-mu*mu

def marginal(likelihood,prior,pd):
    post=np.asarray(likelihood,float)+logprior(prior,pd);a,b=alphabet(pd)
    app=np.concatenate([logsumexp(post[:,b[:,j]==0],axis=1)-logsumexp(post[:,b[:,j]==1],axis=1) for j in (0,1)])
    p=np.exp(post-logsumexp(post,axis=1,keepdims=True));mu=p@a
    return app-prior,app,mu,np.maximum(pd-abs(mu)**2,0)


```
