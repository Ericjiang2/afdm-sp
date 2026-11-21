"""Frozen A' (b) analysis. No receiver execution; truth lives only in Labels.

Authority: aprime-b-manifest-20261013.md (including amendment A1), R3 §6.
Ridge objective = mean weighted cross entropy + lambda * ||beta||² / 2.
Timing blocks = acquisition shards; bootstrap is a stratified hierarchical
block/frame bootstrap, with ONE frame weight stream shared by all cells.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.special import expit, xlogy
from scipy.stats import beta, norm

HERE = Path(__file__).resolve().parent
ARMS = ("E10", "E0", "E1", "E2", "E3")
ES = (10, 0, 1, 2, 3)
CELLS = {"C1": (650, 16, .10), "C2": (650, 20, .20),
         "C3": (800, 28, .10), "C4": (800, 32, .20)}
OLD = "129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812"
NEW = hashlib.sha256(b"AFDM_C1_APRIME_B_20261013_R3").hexdigest()
N = 1024
CODE_HASH = "bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af"
MCHECKS = 1026
RIDGES = (.001, .01, .1, 1., 10.)
TAUE = tuple(i / 10 for i in range(11))
TAUG = (.5, .6, .7, .8, .9, .95, .99, 1.)
KAPPAS = (0., .02, .05, .10)
TAUR = (0., .05, .1, .2, .3, .5, 1.)
CLASSES = ("P", "B0", "B1", "B2", "B3", "B4", "B5")
BOOT_B, BOOT_SEED, ALPHA = 20000, 20261016, .0125
GENERIC = ("log1p_syn", "decoder_iterations", "round", "delta_log1p_syn",
           "Rc/10", "e/10", "current_high_mode")
FULL = GENERIC + ("K/N", "log_receiver_sigma2", "remaining_steps/400",
                  "(K/N)*remaining_steps/400")


def md5(path):
    h = hashlib.md5()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def code_md5s():
    return {str(HERE / p): md5(HERE / p) for p in
            ("c1apb_lib.py", "c1apb_stage1.py", "c1apb_stage2.py", "unit_check_c1apb.py")}


def provenance(config, inputs):
    return dict(_argv=sys.argv, _config=config,
                input_md5s={str(p): md5(p) for p in sorted(set(map(Path, inputs)))},
                code_md5s=code_md5s(),
                analysis_environment=dict(python=sys.version, numpy=np.__version__, hostname=os.uname().nodename,
                                          thread_environment={k: os.environ.get(k) for k in
                                                              ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False,
                              default=lambda x: x.tolist() if isinstance(x, np.ndarray)
                              else x.item() if isinstance(x, np.generic) else str(x)) + "\n")


def snapshot(inputs):
    return {str(p): md5(p) for p in sorted(set(map(Path, inputs)))}


def context_signature(config):
    # Shuffle-only driver change is allowed; numerical/generator modules are not.
    numerical = {k: v for k, v in config["source_sha256"].items() if k != "driver_c1esc.py"}
    payload = {k: config[k] for k in ("code_g_sha256", "checkpoint_sha256", "m2_config_sha256", "sp_cfg", "dpss_defaults")}
    payload["numerical_sources"] = numerical
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def assert_unchanged(bindings):
    for path, digest in bindings.items():
        if md5(path) != digest:
            raise ValueError(f"input/source changed during analysis: {path}")


@dataclass
class Observations:
    cell: str
    namespace: str
    frames: np.ndarray
    syn: np.ndarray                 # arm, frame, round
    dec: np.ndarray
    tcum: np.ndarray
    sigma2: np.ndarray              # known RECEIVER noise variance
    K: np.ndarray
    blocks: np.ndarray
    mchecks: int


@dataclass
class Labels:
    ierr: np.ndarray


def load_cells(dirs, cell_names, frames, entropy, mchecks, shuffled=False, shards=None):
    """Strict completeness, no intersection-dropping or error-row filtering."""
    wanted = set(map(int, frames))
    records, files, configs = {}, [], []
    for directory in dict.fromkeys(map(str, dirs)):
        directory = Path(directory)
        rowfiles = sorted(directory.glob("rows_shard*.jsonl"))
        if not rowfiles:
            raise ValueError(f"no rows in {directory}")
        for p in rowfiles:
            cp = p.with_name(p.name.replace("rows_", "config_").replace(".jsonl", ".json"))
            if not cp.exists():
                raise ValueError(f"missing config {cp}")
            c = json.loads(cp.read_text())["_config"]
            files.extend((p, cp))
            configs.append(c)
            if c["entropy_hex"] != entropy or c["code_g_sha256"] != CODE_HASH:
                raise ValueError(f"namespace/code mismatch {cp}")
            if shuffled and not c.get("shuffle_arms", False):
                raise ValueError(f"unshuffled acquisition {cp}")
            if shards is not None and c["nshard"] != shards:
                raise ValueError(f"wrong shard count {cp}")
            if shuffled:
                env = c["environment"]
                if env["torch_num_threads"] != 1 or env["torch_num_interop_threads"] != 1:
                    raise ValueError(f"not single threaded {cp}")
                summary = p.with_name(p.name.replace("rows_", "results_").replace(".jsonl", ".json"))
                if not summary.exists():
                    raise ValueError(f"incomplete shard/no load record {summary}")
                result = json.loads(summary.read_text())
                if "loadavg_start" not in result or "loadavg_end" not in result:
                    raise ValueError(f"missing load records {summary}")
                files.append(summary)
            for line in p.open():
                if not line.strip():
                    continue
                row = json.loads(line)
                for cell in cell_names:
                    snr, L, _ = CELLS[cell]
                    if (row["snr_centi_db"], row["L"], row["rho_permille"]) != (snr, L, 300):
                        continue
                    if row["frame"] not in wanted or row["arm"] not in ARMS:
                        continue
                    if row["status"] != "ok":
                        raise ValueError(f"error row {p}: {cell}/{row['frame']}/{row['arm']}")
                    key = cell, row["frame"], row["arm"]
                    if key in records:
                        raise ValueError(f"duplicate {key}")
                    if shuffled:
                        words = np.frombuffer(bytes.fromhex(entropy), dtype="<u4").astype(int).tolist()
                        given = c["resolved"]["arms"]
                        perm = np.random.default_rng(np.random.SeedSequence(words+[0x41505242, row["frame"], row["L"]])).permutation(5)
                        expected_order = [given[int(i)] for i in perm]
                        if row["arm_order"] != expected_order:
                            raise ValueError(f"shuffle RNG mismatch {key}")
                    records[key] = row, int(c["shard"])
    expected = len(cell_names) * len(wanted) * len(ARMS)
    if len(records) != expected:
        missing = [(c, f, a) for c in cell_names for f in sorted(wanted) for a in ARMS
                   if (c, f, a) not in records]
        raise ValueError(f"incomplete {len(records)}/{expected}; missing {missing[:8]}")
    # Same numerical kernel/prior/code, even if driver bytes changed for shuffle.
    for key in ("m2_config_sha256", "sp_cfg", "dpss_defaults", "checkpoint_sha256"):
        vals = {json.dumps(c[key], sort_keys=True) for c in configs}
        if len(vals) != 1:
            raise ValueError(f"incompatible contexts: {key}")
    for module in ("native_twofft", "twofft", "receiver", "messages", "physical",
                   "dpss_rx.py", "driver_c1.py", "driver_c1i.py"):
        if len({c["source_sha256"][module] for c in configs}) != 1:
            raise ValueError(f"numerical source mismatch: {module}")
    signatures = {context_signature(c) for c in configs}
    if len(signatures) != 1:
        raise ValueError("incompatible numerical/generator source contexts")
    outputs, reports = {}, {}
    fps = ("info_sha256", "noise_sha256", "physical_gains_sha256", "channel_seed", "sigma2", "tap_delays")
    fs = np.array(sorted(wanted), dtype=int)
    for cell in cell_names:
        table = [[records[(cell, int(f), a)][0] for f in fs] for a in ARMS]
        for j, f in enumerate(fs):
            ref = table[0][j]
            for a, arm in enumerate(ARMS):
                row = table[a][j]
                if any(row[k] != ref[k] for k in fps) or records[(cell, int(f), arm)][1] != records[(cell, int(f), "E10")][1]:
                    raise ValueError(f"G0 fingerprint {cell}/{f}/{arm}")
                schedule = [20 if r <= ES[a] else 40 for r in range(1, 11)]
                if row["R"] != 10 or row["schedule"] != schedule or row["inner_iters"] != schedule:
                    raise ValueError(f"wrong schedule {cell}/{f}/{arm}")
                if shuffled:
                    order = row["arm_order"]
                    if len(order) != 5 or set(order) != set(ARMS) or order[row["arm_rank"]] != arm:
                        raise ValueError(f"G0 arm order {cell}/{f}/{arm}")
                    if order != ref["arm_order"]:
                        raise ValueError(f"inconsistent arm order {cell}/{f}")
                if arm in ("E1", "E2", "E3"):
                    for r in range(1, ES[a] + 1):
                        fields = [f"{k}{r}" for k in ("ierr", "cerr", "dsha", "syn")]
                        if any(row[k] != ref[k] for k in fields) or row["dec_iters_r"][r-1] != ref["dec_iters_r"][r-1]:
                            raise ValueError(f"G0 prefix {cell}/{f}/{arm}/r{r}")
        syn = np.array([[[r[f"syn{i}"] for i in range(1, 11)] for r in a] for a in table])
        dec = np.array([[r["dec_iters_r"] for r in a] for a in table])
        tc = np.array([[r["t_cum"] for r in a] for a in table], dtype=float)
        ierr = np.array([[[r[f"ierr{i}"] for i in range(1, 11)] for r in a] for a in table])
        if not np.isfinite(tc).all() or (np.diff(tc, axis=2) <= 0).any() or (tc[:, :, 0] <= 0).any():
            raise ValueError(f"bad elapsed time {cell}")
        if any(row["t_cum"][0] < row["sec_pilot"] for arm_rows in table for row in arm_rows):
            raise ValueError(f"pilot omitted from elapsed time {cell}")
        if (syn < 0).any() or (syn > mchecks).any() or (dec < 0).any():
            raise ValueError(f"invalid decoder counters {cell}")
        snr, L, _ = CELLS[cell]
        rawsigma = np.array([r["sigma2"] for r in table[0]])
        if not np.allclose(rawsigma, 10 ** (-snr/1000), rtol=1e-9, atol=0):
            raise ValueError(f"wrong known sigma2 {cell}")
        kval = np.array([r["K"] for r in table[0]])
        if not np.all(kval == 8*L):
            raise ValueError(f"wrong K {cell}")
        obs = Observations(cell, entropy, fs, syn, dec, tc, rawsigma/(2*.7), kval,
                           np.array([records[(cell, int(f), "E10")][1] for f in fs]), mchecks)
        outputs[cell] = obs, Labels(ierr)
        reports[cell] = dict(frames=len(fs), five_arm_fingerprints=True, escalation_prefixes=True,
                             context_signature=next(iter(signatures)),
                             fingerprint_scope="generator/message/noise/channel fingerprints; no saved raw-y digest",
                             shuffled=shuffled, shards=shards)
    # Message and noise are shared across cells, unlike their physical channels.
    for f in fs:
        for field in ("info_sha256", "noise_sha256"):
            if len({records[(c, int(f), "E10")][0][field] for c in cell_names}) != 1:
                raise ValueError(f"cross-cell pairing {f}/{field}")
    return outputs, sorted(set(files)), reports


def audit_freshness(root):
    checked = []
    excluded = {"c1apb_cal", "c1apb_test", "c1apb_quiet", "c1apb"}
    for p in sorted(Path(root).rglob("config*.json")):
        if any(part in excluded for part in p.parts):
            continue
        if NEW in p.read_text():
            raise ValueError(f"new namespace already used by old config {p}")
        checked.append(p)
    if not checked:
        raise ValueError("no old configs checked for freshness")
    return checked


def check_shuffle_anchors(reference_dir, anchor_dir):
    """Shuffle smoke vs OLD E10/E0 anchors; evidence must be saved by data owner."""
    references, files, checked, groups = {}, [], 0, {}
    for p in sorted(Path(reference_dir).glob("rows_shard*.jsonl")):
        for line in p.open():
            r = json.loads(line)
            if r["arm"] in ("E10", "E0"):
                references[r["snr_centi_db"], r["L"], r["frame"], r["arm"]] = r
    for p in sorted(Path(anchor_dir).glob("rows_shard*.jsonl")):
        cp = p.with_name(p.name.replace("rows_", "config_").replace(".jsonl", ".json"))
        cfg = json.loads(cp.read_text())["_config"]
        if cfg["entropy_hex"] != OLD or not cfg.get("shuffle_arms") or cfg["code_g_sha256"] != CODE_HASH:
            raise ValueError(f"invalid shuffle anchor context {cp}")
        files += [p, cp]
        for line in p.open():
            r = json.loads(line)
            if r["arm"] not in ("E10", "E0"):
                continue
            key = r["snr_centi_db"], r["L"], r["frame"], r["arm"]
            if key not in references or r["status"] != "ok":
                raise ValueError(f"missing/failed shuffle anchor {key}")
            old = references[key]
            fields = [f"{k}{i}" for k in ("ierr", "cerr", "syn", "dsha") for i in range(1, 11)]
            fields += ["dec_iters_r", "info_sha256", "noise_sha256", "physical_gains_sha256", "channel_seed"]
            if any(r[k] != old[k] for k in fields):
                raise ValueError(f"shuffle changed old anchor {key}")
            order = r["arm_order"]
            if order[r["arm_rank"]] != r["arm"]:
                raise ValueError(f"invalid anchor arm order {key}")
            checked += 1
            groups.setdefault(key[:3], set()).add(r["arm"])
    if not groups or any(g != {"E10", "E0"} for g in groups.values()):
        raise ValueError("need saved shuffled E10 AND E0 at each smoke frame/cell")
    return dict(pairs=checked, frames_cells=len(groups), mismatches=0), files


def subset(pair, mask):
    o, y = pair
    return Observations(o.cell, o.namespace, o.frames[mask], o.syn[:, mask], o.dec[:, mask],
                        o.tcum[:, mask], o.sigma2[mask], o.K[mask], o.blocks[mask], o.mchecks), Labels(y.ierr[:, mask])


def features(o, a, r, e, Rc, full=True):
    """Observable allowlist. Labels cannot enter this API."""
    current = np.log1p(o.syn[a, :, r-1])
    delta = np.zeros(len(o.frames)) if r == 1 else current - np.log1p(o.syn[a, :, r-2])
    const = np.ones(len(o.frames))
    cols = [current, o.dec[a, :, r-1], const*r, delta, const*Rc/10, const*e/10,
            const*int(r > ES[a])]
    if full:
        brem = (20*max(0, min(e, Rc)-r) + 40*max(0, Rc-max(e, r)))/400
        cols += [o.K/N, np.log(o.sigma2), const*brem, (o.K/N)*brem]
    return np.column_stack(cols)


def fixed_stop(o, a, Rc):
    z = o.syn[a] == 0
    return np.minimum(np.where(z.any(1), z.argmax(1)+1, 11), Rc)


def terminal_labels(o, y, a, Rc):
    s = fixed_stop(o, a, Rc)
    return y.ierr[a, np.arange(len(s)), s-1] > 0


def dataset(pairs, full=True, rescue=False):
    xs, ys, frames, cells = [], [], [], []
    for cell, (o, y) in pairs.items():
        for Rc in range(2, 11):
            if rescue:
                choices = [(0, r, r) for r in range(1, min(3, Rc-1)+1)]
            else:
                choices = [(a, r, e) for a, e in enumerate(ES) for r in range(1, Rc)]
            for a, r, e in choices:
                live = (o.syn[a, :, :r] != 0).all(1)
                if not live.any():
                    continue
                target = terminal_labels(o, y, a, Rc)
                if rescue:
                    target = target & ~terminal_labels(o, y, ARMS.index(f"E{r}"), Rc)
                xs.append(features(o, a, r, e, Rc, full)[live])
                ys.append(target[live]); frames.extend(o.frames[live]); cells.extend([cell]*live.sum())
    if not xs:
        raise ValueError("no live training decisions")
    x, target, frames, cells = np.concatenate(xs), np.concatenate(ys), np.array(frames), np.array(cells)
    # Each cell gets equal total mass; each represented frame within it gets equal mass.
    w = np.empty(len(frames))
    for cell in pairs:
        take = cells == cell
        if not take.any():
            raise ValueError(f"no live states in {cell}")
        _, inverse, counts = np.unique(frames[take], return_inverse=True, return_counts=True)
        w[take] = 1 / (len(pairs)*len(counts)*counts[inverse])
    return dict(x=x, y=target.astype(float), frame=frames, cell=cells, w=w)


def fit_logistic(x, y, w, ridge):
    w = w/w.sum()
    mean, sd = np.sum(w[:, None]*x, axis=0), None
    sd = np.sqrt(np.sum(w[:, None]*(x-mean)**2, axis=0))
    sd = np.where(sd < 1e-12, 1., sd)
    counts = dict(events=int(y.sum()), records=len(y))
    if np.all(y == y[0]):
        # Explicit special model, not a hidden optimizer fallback.
        p = (y.sum()+.5)/(len(y)+1)
        return dict(mean=mean.tolist(), sd=sd.tolist(), coef=[0.]*x.shape[1],
                    intercept=float(np.log(p/(1-p))), ridge=ridge, constant=counts)
    z = (x-mean)/sd
    def objective(v):
        t = z@v[1:]+v[0]
        loss = np.sum(w*(np.logaddexp(0., t)-y*t)) + ridge*.5*np.dot(v[1:], v[1:])
        err = w*(expit(t)-y)
        return loss, np.r_[err.sum(), z.T@err + ridge*v[1:]]
    result = minimize(objective, np.zeros(x.shape[1]+1), jac=True, method="L-BFGS-B",
                      options=dict(maxiter=1000, ftol=1e-12, gtol=1e-8, maxls=100))
    if not result.success:
        raise RuntimeError(f"logistic optimizer failed: {result.message}")
    return dict(mean=mean.tolist(), sd=sd.tolist(), coef=result.x[1:].tolist(),
                intercept=float(result.x[0]), ridge=ridge, constant=None, counts=counts,
                solver=dict(method="L-BFGS-B", maxls=100, iterations=int(result.nit),
                            loss=float(result.fun), grad_inf=float(np.linalg.norm(result.jac, np.inf)),
                            status=str(result.message)))


def predict(model, x):
    return expit(((x-np.asarray(model["mean"]))/model["sd"])@np.asarray(model["coef"])+model["intercept"])


def fit_cv(ds):
    results = []
    for ridge in RIDGES:
        scores, constants = [], []
        for fold in range(5):
            val = ds["frame"] % 5 == fold
            if not val.any() or val.all():
                raise ValueError(f"empty grouped CV fold {fold}")
            model = fit_logistic(ds["x"][~val], ds["y"][~val], ds["w"][~val], ridge)
            err = (predict(model, ds["x"][val])-ds["y"][val])**2
            scores.append(float(np.average(err, weights=ds["w"][val])))
            constants.append(model["constant"])
        results.append(dict(ridge=ridge, brier=float(np.mean(scores)), folds=scores, constant_folds=constants))
    best = min(results, key=lambda z: (round(z["brier"], 12), -z["ridge"]))
    model = fit_logistic(ds["x"], ds["y"], ds["w"], best["ridge"])
    model.update(cv=results, columns=list(FULL if ds["x"].shape[1] == len(FULL) else GENERIC))
    return model


def fit_models(pairs):
    out = dict(pooled={}, loco={}, per_cell={}, timing_seconds={})
    for name, full, rescue in (("full", True, False), ("generic", False, False), ("rescue", True, True)):
        started = time.perf_counter()
        out["pooled"][name] = fit_cv(dataset(pairs, full, rescue))
        out["timing_seconds"][name] = time.perf_counter()-started
    for cell in pairs:
        others = {k: v for k, v in pairs.items() if k != cell}
        if others:
            out["loco"][cell] = {name: fit_cv(dataset(others, full))
                                 for name, full in (("full", True), ("generic", False))}
        out["per_cell"][cell] = fit_cv(dataset({cell: pairs[cell]}))
    return out


def qcache(o, model, rescue=None):
    # Key = actual observed arm, current r, counterfactual fixed e, chosen cap.
    q, rho = {}, {}
    for Rc in range(2, 11):
        for a, e in enumerate(ES):
            for r in range(1, Rc):
                q[a, r, e, Rc] = predict(model, features(o, a, r, e, Rc, len(model["coef"]) == len(FULL)))
        for r in range(1, min(3, Rc-1)+1):
            q[0, r, r, Rc] = predict(model, features(o, 0, r, r, Rc, len(model["coef"]) == len(FULL)))
            if rescue is not None:
                rho[r, Rc] = predict(rescue, features(o, 0, r, r, Rc))
    return q, rho


def candidate_id(p):
    return json.dumps(p, sort_keys=True, separators=(",", ":"))


def candidates(cls):
    for Rc in range(1, 11):
        base = dict(cls=cls, Rc=Rc)
        if cls in ("P", "B4", "B5"):
            thresholds = TAUR if cls == "B5" else TAUE
            for te, tg, k in itertools.product(thresholds, TAUG, KAPPAS if cls == "P" else (0.,)):
                yield dict(base, te=te, tg=tg, k=k)
        elif cls in ("B0", "B1", "B2", "B3"):
            for a in range(5):
                p = dict(base, arm=ARMS[a])
                if cls == "B0":
                    yield p
                elif cls == "B1":
                    if Rc == 1:
                        yield dict(p, rg=0, theta=1.)
                    for rg, theta in itertools.product(range(1, min(4, Rc-1)+1), (i*.025 for i in range(41))):
                        yield dict(p, rg=rg, theta=theta)
                elif cls == "B2":
                    for w, ts, td in itertools.product((1, 2, 3), (i*.1 for i in range(10)), (0., .01, .025, .05)):
                        yield dict(p, w=w, ts=ts, td=td)
                else:
                    for tg in TAUG:
                        yield dict(p, tg=tg)
        else:
            raise ValueError(f"unknown class {cls}")


@dataclass
class PathResult:
    arm: np.ndarray
    stop: np.ndarray
    giveup: np.ndarray
    overhead: np.ndarray
    queries: np.ndarray


def replay(o, p, cache=None, overhead=None):
    """Pure causal decisions. Does not accept Labels. query cache is observable only."""
    oh = dict(feature=0., q=0., decision=0., simple=0., rescue=0., stop=0.) if overhead is None else overhead
    n, Rc, cls = len(o.frames), int(p["Rc"]), p["cls"]
    if cls not in CLASSES:
        raise ValueError(cls)
    adaptive = cls in ("P", "B4", "B5")
    arm = np.zeros(n, int) if adaptive else np.full(n, ARMS.index(p["arm"]), int)
    live, stop, give = np.ones(n, bool), np.zeros(n, int), np.zeros(n, bool)
    spent, queries = np.zeros(n), np.zeros(n, int)
    q, rho = ({}, {}) if cache is None else cache
    for r in range(1, Rc+1):
        spent[live] += oh["stop"]
        syn = o.syn[arm, np.arange(n), r-1]
        finish = live & ((syn == 0) | (r == Rc))
        stop[finish] = r; live[finish] = False
        if not live.any():
            continue
        promo = np.zeros(n, bool)
        quitnow = np.zeros(n, bool)
        if cls in ("P", "B3", "B4", "B5"):
            qsel = np.zeros(n)
            # Query only when a decision can still be taken (no give-up after4,
            # no promotion after3). Idle outer rounds incur no predictor cost.
            relevant = live & (r <= 4)
            for a in range(5):
                take = relevant & (arm == a)
                if take.any():
                    qsel[take] = q[a, r, ES[a], Rc][take]
            spent[relevant] += oh["feature"]+oh["q"]+oh["decision"]
            queries[relevant] += 1
            low = relevant & (arm == 0) & adaptive & (r <= 3)
            if low.any():
                if cls == "B5":
                    spent[low] += oh["feature"]+oh["rescue"]; queries[low] += 1
                    promo = low & (rho[r, Rc] > p["te"])
                elif cls == "P":
                    # Delta needed only after q20 crossed its threshold.
                    check = low & (qsel > p["te"])
                    qe = q[0, r, r, Rc]
                    spent[check] += oh["feature"]+oh["q"]; queries[check] += 1
                    promo = check & ((qsel-qe) > p["k"])
                else:
                    promo = low & (qsel > p["te"])
                if cls != "P":
                    spent[promo] += oh["feature"]+oh["q"]; queries[promo] += 1
                qsel[promo] = q[0, r, r, Rc][promo]
            quitnow = relevant & (qsel > p["tg"])
        elif cls == "B1":
            if r == p["rg"]:
                spent[live] += oh["simple"]
                quitnow = live & (syn/o.mchecks > p["theta"])
        elif cls == "B2" and r <= 4 and r > p["w"]:
            spent[live] += oh["simple"]
            # All of the most recent w single-round changes must stall.
            histories = o.syn[arm, np.arange(n)]
            diffs = np.diff(histories[:, r-p["w"]-1:r], axis=1)/o.mchecks
            quitnow = live & (syn/o.mchecks > p["ts"]) & (diffs >= -p["td"]).all(1)
        give[quitnow] = True; stop[quitnow] = r; live[quitnow] = False
        # Scheduled escalation executes next round. Give-up pays current low path.
        executing = promo & live
        if executing.any():
            arm[executing] = ARMS.index(f"E{r}")
    if live.any() or (stop == 0).any():
        raise AssertionError("unterminated replay")
    return PathResult(arm, stop, give, spent, queries)


def score(o, labels, path):
    idx = np.arange(len(o.frames))
    fail = path.giveup | (labels.ierr[path.arm, idx, path.stop-1] > 0)
    cost = o.tcum[path.arm, idx, path.stop-1]+path.overhead
    rounds = path.stop
    switch = np.asarray(ES)[path.arm]
    updates = 20*np.minimum(rounds, switch)+40*np.maximum(0, rounds-switch)
    decoder = (o.dec[path.arm, idx]*(np.arange(10)[None, :] < rounds[:, None])).sum(1)
    return dict(fail=fail, cost=cost, stop=rounds, updates=updates, decoder=decoder,
                giveup=path.giveup, arm=path.arm, queries=path.queries, overhead=path.overhead)


def mixture_u(frames, L, entropy=NEW):
    words = list(np.frombuffer(bytes.fromhex(entropy), dtype="<u4").astype(int))
    # Literal domain is ASCII 'mix', packed little endian, not Python's salted hash.
    domain = int.from_bytes(b"mix", "little")
    return np.array([np.random.default_rng(np.random.SeedSequence(words+[int(f), int(L), domain])).random() for f in frames])


def eval_mix(o, y, mix, cache, overhead):
    u = mixture_u(o.frames, CELLS[o.cell][1])
    outputs = [score(o, y, replay(o, p, cache, overhead)) for p in mix["policies"]]
    if len(outputs) == 1:
        return outputs[0]
    take = u < mix["weights"][0]
    return {k: np.where(take, outputs[0][k], outputs[1][k]) for k in outputs[0]}


def lower_hull(records):
    """One cheapest point per FER; monotone lower convex envelope."""
    ordered = sorted(records, key=lambda x: (x["fer"], x["cost"], x["queries"], candidate_id(x["policy"])))
    points = []
    for rec in ordered:
        if points and rec["fer"] == points[-1]["fer"]:
            continue
        points.append(rec)
    hull = []
    for p in points:
        while len(hull) >= 2:
            a, b = hull[-2:]
            cross = (b["fer"]-a["fer"])*(p["cost"]-b["cost"])-(b["cost"]-a["cost"])*(p["fer"]-b["fer"])
            if cross <= 1e-14:
                hull.pop()
            else:
                break
        hull.append(p)
    return hull


def hull_select(records, limit):
    hull = lower_hull(records)
    choices = []
    for h in hull:
        if h["fer"] <= limit:
            choices.append(dict(policies=[h["policy"]], weights=[1.],
                                expected_cal_fer=h["fer"], expected_cal_cost=h["cost"], queries=h["queries"]))
    for a, b in zip(hull, hull[1:]):
        if a["fer"] < limit < b["fer"]:
            w = (b["fer"]-limit)/(b["fer"]-a["fer"])
            choices.append(dict(policies=[a["policy"], b["policy"]], weights=[w, 1-w],
                                expected_cal_fer=limit, expected_cal_cost=w*a["cost"]+(1-w)*b["cost"],
                                queries=w*a["queries"]+(1-w)*b["queries"]))
    if not choices:
        return None
    return min(choices, key=lambda x: (x["expected_cal_cost"], x["expected_cal_fer"],
                                      x["queries"], json.dumps(x["policies"], sort_keys=True)))


def evaluate_candidates(o, y, cache, overhead, timings=None):
    records = {c: [] for c in CLASSES}
    for cls in CLASSES:
        started = time.perf_counter()
        for p in candidates(cls):
            path = replay(o, p, cache, overhead)
            s = score(o, y, path)
            records[cls].append(dict(policy=p, fer=float(s["fail"].mean()), cost=float(s["cost"].mean()),
                                     queries=float(s["queries"].mean())))
        if timings is not None:
            timings[cls] = time.perf_counter()-started
    return records


def plan_n(fp, fb):
    q = float(np.mean(fp != fb))
    inflated = min(1., max(.04, q+1.96*math.sqrt(q*(1-q)/600)+1/600))
    req = 100*math.ceil(95100*inflated/100)
    return dict(q_cal=q, q_plan=inflated, n_req=req, n_c=min(10000, max(4000, req)), power_capped=req > 10000)


def cp_upper(k, n, alpha=ALPHA):
    if not 0 <= k <= n or n <= 0:
        raise ValueError((k, n))
    return 1. if k == n else float(beta.ppf(1-alpha, k+1, n-k))


def cp_lower(k, n, alpha=ALPHA):
    if not 0 <= k <= n or n <= 0:
        raise ValueError((k, n))
    return 0. if k == 0 else float(beta.ppf(alpha, k, n-k+1))


def constrained_q(xplus, xminus, n, d0):
    s, t, x0 = xplus+xminus, xplus-xminus, n-xplus-xminus
    lo, hi = abs(d0), 1.
    roots = np.roots([n, -(s+d0*t), d0*t-x0*d0*d0])
    candidates_q = [lo, hi]+[float(v.real) for v in roots if abs(v.imag) < 1e-10 and lo <= v.real <= hi]
    def ll(q):
        return xlogy(xplus, max(0., (q+d0)/2))+xlogy(xminus, max(0., (q-d0)/2))+xlogy(x0, max(0., 1-q))
    return max(candidates_q, key=ll)


def tango_upper(xplus, xminus, n, alpha=ALPHA):
    if min(xplus, xminus) < 0 or xplus+xminus > n or n <= 0:
        raise ValueError((xplus, xminus, n))
    d = (xplus-xminus)/n
    if xplus+xminus < 20:
        return dict(upper=cp_upper(xplus, n, alpha/2)-cp_lower(xminus, n, alpha/2),
                    method="exact_component_CP_Bonferroni", d=d, xplus=xplus, xminus=xminus)
    target = norm.ppf(1-alpha)
    def root(d0):
        q = constrained_q(xplus, xminus, n, d0)
        var = max(0., q-d0*d0)/n
        if var <= 1e-24:
            return target if d0 == d else -1e100
        return (d-d0)/math.sqrt(var)+target
    hi = 1-1e-12
    upper = 1. if d >= hi or root(hi) >= 0 else float(brentq(root, d, hi, xtol=1e-12))
    return dict(upper=upper, method="Tango_paired_score", d=d, xplus=xplus, xminus=xminus)


def paired_ni(fp, fb, alpha=ALPHA):
    return tango_upper(int(np.sum(fp & ~fb)), int(np.sum(~fp & fb)), len(fp), alpha)


def bootstrap_weights(observations, B=BOOT_B, seed=BOOT_SEED):
    """Availability-stratified, shard-block then frame resampling.

    Each selected block contributes its original number of frames. Unequal block
    sizes are normalized within availability stratum to preserve its mass.
    Cells with the same frame ID always receive exactly the same draw weight.
    """
    ids = sorted(set.union(*(set(map(int, o.frames)) for o in observations.values())))
    available = {c: set(map(int, o.frames)) for c, o in observations.items()}
    memberships = {f: tuple(c for c in observations if f in available[c]) for f in ids}
    strata = {}
    for f in ids:
        strata.setdefault(memberships[f], []).append(f)
    index = {f: j for j, f in enumerate(ids)}
    weights = np.zeros((B, len(ids)), dtype=np.float64)
    rng = np.random.default_rng(seed)
    block_for = {}
    for c, o in observations.items():
        for f, block in zip(o.frames, o.blocks):
            f, block = int(f), int(block)
            if f in block_for and block_for[f] != block:
                raise ValueError(f"frame {f} uses incompatible timing blocks across cells")
            block_for[f] = block
    for fs in strata.values():
        blocks = {}
        for f in fs:
            blocks.setdefault(block_for[f], []).append(index[f])
        bb = list(blocks.values())
        positions = [index[f] for f in fs]
        for b in range(B):
            counts = rng.multinomial(len(bb), np.full(len(bb), 1/len(bb)))
            for block, count in zip(bb, counts):
                if count:
                    v = rng.multinomial(len(block)*int(count), np.full(len(block), 1/len(block)))
                    weights[b, block] = v
            weights[b, positions] *= len(fs)/weights[b, positions].sum()
    out = {}
    for c, o in observations.items():
        pos = [index[int(f)] for f in o.frames]
        if pos == list(range(pos[0], pos[-1]+1)):
            # Shared views: no 4x matrix copies and no per-GEMV dtype coercion.
            out[c] = weights[:, pos[0]:pos[-1]+1]
        else:
            out[c] = weights[:, pos]
    return out


def bootstrap_mean(w, v):
    return (w@np.asarray(v, dtype=float))/w.sum(axis=1)


def interval(v, alpha=ALPHA):
    return dict(lower=float(np.quantile(v, alpha)), upper=float(np.quantile(v, 1-alpha)))


def measure_overhead(o, model, rescue_model, repeats=3000):
    """Scalar serving work, measured separately from vectorized offline search."""
    model = {k: np.asarray(model[k]) if k in ("mean", "sd", "coef") else model[k] for k in model}
    rescue_model = {k: np.asarray(rescue_model[k]) if k in ("mean", "sd", "coef") else rescue_model[k] for k in rescue_model}
    j = int(np.flatnonzero(o.syn[0, :, 0] != 0)[0])
    def feature():
        current = math.log1p(int(o.syn[0, j, 1])); k = float(o.K[j])/N
        change = current-math.log1p(int(o.syn[0, j, 0]))
        return np.array([current, float(o.dec[0, j, 1]), 2., change, 1., .2, 0.,
                         k, math.log(float(o.sigma2[j])), .8, k*.8])
    x = feature()
    state = dict(q20=.7, qe=.2, te=.6, tg=.8, k=.05)
    jobs = dict(feature=feature, q=lambda: predict(model, x), rescue=lambda: predict(rescue_model, x),
                decision=lambda: bool(state["q20"] > state["te"] and state["q20"]-state["qe"] > state["k"] and state["qe"] > state["tg"]),
                simple=lambda: bool(o.syn[0, j, 0]/o.mchecks > .1),
                stop=lambda: bool(o.syn[0, j, 0] == 0 or 1 == 10))
    result = {}
    for name, job in jobs.items():
        for _ in range(100):
            job()
        batches = []
        for _ in range(5):
            t = time.perf_counter()
            for _ in range(repeats):
                job()
            batches.append((time.perf_counter()-t)/repeats)
        # Mean complete call time; loop overhead retained conservatively.
        result[name] = float(np.mean(batches))
    return result


def quintile_cuts(pairs, model):
    out = {}
    for cell, (o, _) in pairs.items():
        q, _ = qcache(o, model)
        out[cell] = {}
        for Rc in range(2, 11):
            for e in range(1, min(3, Rc-1)+1):
                live = (o.syn[0, :, :e] != 0).all(1)
                delta = q[0, e, 10, Rc]-q[0, e, e, Rc]
                out[cell][f"{e}:{Rc}"] = np.quantile(delta[live], [.2, .4, .6, .8]).tolist() if live.any() else None
    return out


def frame_brier(pair, model, full):
    o, _ = pair
    ds = dataset({o.cell: pair}, full)
    err = (predict(model, ds["x"])-ds["y"])**2
    val = np.full(len(o.frames), np.nan)
    for j, f in enumerate(o.frames):
        take = ds["frame"] == f
        if take.any():
            val[j] = err[take].mean()
    return val


def calibration_bins(pair, model, full, nbins=10):
    ds = dataset({pair[0].cell: pair}, full)
    q = predict(model, ds["x"])
    index = np.minimum((q*nbins).astype(int), nbins-1)
    out = []
    for i in range(nbins):
        take = index == i
        out.append(dict(lower=i/nbins, upper=(i+1)/nbins, records=int(take.sum()),
                        weight=float(ds["w"][take].sum()),
                        predicted=float(np.average(q[take], weights=ds["w"][take])) if take.any() else None,
                        observed=float(np.average(ds["y"][take], weights=ds["w"][take])) if take.any() else None))
    return out
