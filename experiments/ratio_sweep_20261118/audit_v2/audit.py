"""Post hoc diagnostics from a frame-balanced replay of frozen main-v2 rows."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import itertools
import json
import multiprocessing
from pathlib import Path
import resource
import struct
import sys

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.stats import spearmanr


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
SOURCE = EXPERIMENT / "out/main_v2_20261119"
FREEZE_SHA = "929ab55238fc9fd2ae8c6b2e79451e0e361ef92894b8f5a6bf75fa627ea791f3"
MANIFEST_SHA = "5a47d2cce03a25819bdaa7724b24f1e71b806a3fe4dd89c7f228468800571ed4"
SEED = 20261119
FRAMES = 84
WORKERS = 14
CELL_R = (1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128)
CELLS = tuple(itertools.product((.3, .5), CELL_R))
ARMS = ("A2", "CODELAY")
PCTS = (5, 25, 50, 75, 95)
TOL = 1e-12


def digest(path, algorithm="sha256"):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def initialize():
    global study, v2, sw, paired, observers, daft, dkernel, moments, modeled_gain
    # The frozen loader inventories imports, so load its context before audit helpers.
    g4 = json.loads((EXPERIMENT / "out/phase1b/g1.json").read_text())
    sys.path.insert(0, g4["_config"]["frozen_slot"])
    import qualify_v2 as q

    study = (q, *q.load())
    sys.path.insert(0, str(EXPERIMENT))
    import phase2

    phase2.study = study
    freeze = phase2.verify_freeze(SOURCE)
    assert freeze["loaded_source_sha256"] == study[1].source_sha256
    assert freeze["_config"]["snr_db"] == 4.5
    import forced_miss as v2
    import paired_scores as paired
    import sweep as sw
    from messages import moments
    from physical import daft, dkernel

    sys.path.insert(0, str(EXPERIMENT.parent / "admission_law_20261118"))
    from replay import modeled_gain

    observers = {name: paired.instrument(kernel) for name, kernel in zip(ARMS, study[3:5], strict=True)}


def saved_rows(frames):
    manifest = SOURCE / "RAW_SHARDS_MD5.txt"
    assert digest(SOURCE / "FREEZE.json") == FREEZE_SHA
    assert digest(manifest) == MANIFEST_SHA and (SOURCE / "STATUS").read_text().strip() == "DONE"
    wanted = {int(frame): {} for frame in frames}
    for line in manifest.read_text().splitlines():
        md5, name = line.split()
        if not name.startswith("main_"):
            continue
        path = SOURCE / name
        assert digest(path, "md5") == md5, name
        with gzip.open(path, "rt") as f:
            for line in f:
                row = json.loads(line)
                frame = row["frame"]
                if frame in wanted:
                    cell = row["rho"], row["R"]
                    assert cell not in wanted[frame]
                    wanted[frame][cell] = row
    assert all(rows.keys() == set(CELLS) for rows in wanted.values())
    return list(wanted.items())


def replay_frame(item):
    frame, rows = item
    _, ctx, _, full, *_ = study
    s = ctx.system
    draw = sw.draw_frame(study, frame)
    weak = draw["weak"]
    weak_delay, weak_nu = int(draw["l_i"][weak]), float(draw["k_real"][weak])
    data_power = 1 - s.rho
    collected = []
    for rho, ratio in CELLS:
        saved = rows[rho, ratio]
        assert saved["defined"]
        base, truth = sw.controlled_base(ctx, draw, rho, ratio, background_clip=v2.BACKGROUND_CLIP)
        obs = sw.observation(ctx, base, rho, 4.5)
        _, r1, syndrome = v2.f0_state(study, obs, weak_delay)
        assert bool(syndrome) == saved["triggered"] and weak_delay not in r1["r1_delays"]
        window = v2.window(full, s, obs, r1, ratio)
        assert window is not None and window == {k:float(v) for k,v in saved["window"].items()}
        mu, _, _ = moments(np.clip(r1["r1_app"], -20, 20), data_power)
        d = base["data"] / np.sqrt(2 * (1 - rho))
        hw = abs(truth["g_i"][weak])
        dl = r1["r1_delays"] - weak_delay
        alias = bool(np.any((abs(dl) == 1) & (abs(r1["r1_dopplers"] - weak_nu + 2*s.N_total*s.c1*dl) <= 1)))
        audit = dict(frame=frame, rho=rho, R=ratio, alias=alias, arms={})

        def capture(name, kernel, args, opts, result, matrix, pair, anchor):
            replay_pair = pair
            stored_pair = saved["arms"][name]["pair"]
            for key in ("slot","phantom_index","weak_index","phantom_doppler","weak_doppler","Q"):
                assert replay_pair[key] == stored_pair[key], (frame, rho, ratio, name, key)
            for key in ("phantom_gain","weak_gain"):
                assert struct.pack("d", replay_pair[key]) == struct.pack("d", stored_pair[key]), (frame, rho, ratio, name, key)
            assert not result.diagnostics["numerical_fallback"] and not saved["arms"][name]["numerical_fallback"]
            Y, x, v, paths = args
            np.testing.assert_array_equal(x, obs["pilot"] + mu)
            E, u, ridge = float(np.vdot(x, x).real), float(v.sum()), float(opts["ridge"])
            values = dict(E=E, u=u, **{"lambda":ridge})
            expected = {k:window[k] for k in values}
            xt = daft(x,s.c1,s.c2,True)
            ph = kernel.Path(paths[anchor].delay, pair["phantom_doppler"])
            wk = kernel.Path(weak_delay, pair["weak_doppler"])
            ph_response, weak_response = kernel._responses(xt,[ph,wk],s.c1,s.c2).T
            B, Q, b, h, _, _ = kernel._system(Y,xt,v,paths,s.c1,s.c2,ridge,opts["gamma_mode"])
            fitted = result.global_trace[0]["entering_gains"][anchor]
            assert struct.pack("dd",fitted.real,fitted.imag) == struct.pack("dd",h[anchor].real,h[anchor].imag)
            kappa = np.vdot(B[:,anchor],ph_response) / E
            D = dkernel(ph.doppler-paths[anchor].doppler,len(Y))
            assert abs(float(abs(D)) - window["z"]) <= TOL
            T = E+u+ridge
            p_model = float(modeled_gain(E,u,T,kappa,D,fitted,opts["gamma_mode"]))
            w_model = float(E**2 * hw**2 * abs(dkernel(wk.doppler-weak_nu,len(Y)))**2 / T)
            keep = np.arange(len(paths)) != pair["slot"]
            Qr = Q[np.ix_(keep,keep)]
            hr = cho_solve(cho_factor(Qr,lower=True,check_finite=True),b[keep],check_finite=True)
            bw = np.vdot(weak_response,Y - B[:,keep] @ hr)
            wx = stored_pair["weak_gain"]
            px = stored_pair["phantom_gain"]
            audit["arms"][name] = dict(phantom_model=p_model, phantom_measured=px,
                                      weak_measured=wx, weak_ratio=wx/w_model if w_model > 0 else None,
                                      bw_ratio=float(abs(bw)/(E*hw)), weak_doppler=wk.doppler,
                                      scoring=values, logged=expected)
            if name == "A2":
                err = d - mu
                audit["gamma"] = float((np.vdot(obs["pilot"],obs["pilot"]).real + np.vdot(mu,d).real)/E)
                audit["kappa_cal"] = float(np.vdot(err,err).real/u) if u > 0 else None

        # The saved first-step gains must match even when the rest of the branch is omitted.
        paired.run_from_r1(study, observers, obs, r1, truth, weak, False, window, audit=capture)
        collected.append(audit)
    return collected


def distribution(values):
    valid = [x for x in values if x is not None]
    assert all(np.isfinite(valid))
    return dict(n=len(valid), quantiles=np.percentile(valid,PCTS).tolist() if valid else None)


def summarize(rows):
    counts = {}
    for arm in ARMS:
        arm_rows = [r["arms"][arm] for r in rows]
        logged = np.array([r["phantom_measured"] for r in arm_rows])
        model = np.array([r["phantom_model"] for r in arm_rows])
        valid = abs(logged) > 0
        err = abs(model[valid]-logged[valid])/abs(logged[valid])
        rho = spearmanr(model,logged).statistic if np.ptp(model)>0 and np.ptp(logged)>0 else None
        counts[arm] = dict(phantom_median_relative_error=float(np.median(err)) if len(err) else None,
                           phantom_relative_error_n=int(valid.sum()),
                           phantom_spearman=float(rho) if rho is not None else None,
                           weak_measured_over_model=distribution([r["weak_ratio"] for r in arm_rows]),
                           bw_over_E_hw=distribution([r["bw_ratio"] for r in arm_rows]))
    weak_diffs = [abs(r["arms"]["A2"]["weak_measured"] - r["arms"]["CODELAY"]["weak_measured"]) for r in rows]
    mismatched_dopplers = sum(r["arms"]["A2"]["weak_doppler"] != r["arms"]["CODELAY"]["weak_doppler"] for r in rows)
    return dict(n=len(rows), arms=counts, gamma=distribution([r["gamma"] for r in rows]),
                kappa_cal=distribution([r["kappa_cal"] for r in rows]), alias_count=sum(r["alias"] for r in rows),
                alias_share=sum(r["alias"] for r in rows)/len(rows),
                weak_gain_max_abs_arm_difference=max(weak_diffs),
                weak_candidate_doppler_mismatches=mismatched_dopplers)


def seconds():
    times = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF,resource.RUSAGE_CHILDREN)]
    return sum(t.ru_utime+t.ru_stime for t in times)


def main(out):
    # 14 replay workers plus a coordinator and a multiprocessing resource tracker.
    # The coordinator's inherited hard limit bounds total CPU below 1.5 core-hours.
    resource.setrlimit(resource.RLIMIT_CPU,(330,330))
    rng = np.random.default_rng(SEED)
    frames = sorted(rng.choice(np.arange(55000,56000),FRAMES,replace=False).tolist())
    check = sorted(rng.choice(FRAMES*len(CELLS),20,replace=False).tolist())
    units = saved_rows(frames)
    with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context("spawn"),
                             initializer=initialize) as pool:
        rows = []
        for i, result in enumerate(pool.map(replay_frame,units),1):
            rows.extend(result)
            if i % 12 == 0:
                print(f"Replayed {i}/{FRAMES} frames",flush=True)
    assert len(rows) == FRAMES*len(CELLS)
    recorded = [dict(frame=rows[i]["frame"],rho=rows[i]["rho"],R=rows[i]["R"],
                     arms={name:{k:a[k] for k in ("scoring","logged")} for name,a in rows[i]["arms"].items()})
                for i in check]
    max_diffs = {k:max(abs(a["scoring"][k] - a["logged"][k])
                      for row in recorded for a in row["arms"].values()) for k in ("E","u","lambda")}
    unit_check = dict(status="PASS" if max(max_diffs.values())<=TOL else "FAIL",
                      units=len(recorded),max_absolute_error=max_diffs,per_unit=recorded)
    summary = [dict(rho=rho,R=ratio,**summarize([r for r in rows if (r["rho"],r["R"])==(rho,ratio)]))
               for rho,ratio in CELLS]
    for rho in (.3,.5):
        summary.append(dict(rho=rho,R="pooled",**summarize([r for r in rows if r["rho"]==rho])))
    cfg = dict(analysis="post hoc",model="gpt-6.2-sol",source=str(SOURCE),freeze_sha256=FREEZE_SHA,
               manifest_sha256=MANIFEST_SHA,source_commit="1a86112bdf9f8e30fccce8f88cc35dba5b900cd8",
               audit_source_sha256=digest(Path(__file__)),seed=SEED,frames=frames,units=len(rows),snr_db=4.5,
               workers=WORKERS,threads=1,cap_core_hours=1.5,per_python_cpu_limit_seconds=330,
               quantile_percentiles=PCTS,unit_absolute_tolerance=TOL,
               relative_error="abs(predicted - measured) / abs(measured)",
               d_scaling="physical data / sqrt(2*(1-rho)); physical h unchanged",
               bw="unpenalized response inner product with residual of reduced penalized fit")
    audit = dict(_argv=sys.argv,_config=cfg,label="post hoc",core_hours=seconds()/3600,
                 summary=summary,unit_check=unit_check)
    assert audit["core_hours"] <= cfg["cap_core_hours"]
    with out.open("x") as fh:
        json.dump(audit,fh,indent=2,allow_nan=False)
        fh.write("\n")
    print(f"Post hoc audit complete. Item 5 {unit_check['status']}. CPU {audit['core_hours']:.6f} core-hours.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    main(p.parse_args().out)
