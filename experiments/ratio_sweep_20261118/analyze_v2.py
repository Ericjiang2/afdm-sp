"""Frozen P1–P4 and secondary reads, using paired physical-frame bootstraps."""
import argparse
from collections import Counter
import gzip
from itertools import product
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.special import expit

from phase2 import CLUSTER_SEED, DRAWS, PHASE1B, WORKERS, digest, write


RATIOS = (1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128)
CELLS = tuple(product((.3, .5), RATIOS))
ARMS = ("A2", "CODELAY")
CLASSES = ("no_edit", "phantom", "weak_recovery", "other_missing_recovery", "other")
WINNERS = ("another_anchor_phantom", "third_candidate", "designated_candidate", "no_edit")
COVERAGE = 30


def confidence(draws):
    return [float(x) for x in np.quantile(draws, [.025, .975])]


def p1_verdict(low, high, ci):
    if min(low, high) < COVERAGE:
        return "UNEVALUABLE"
    return "SUPPORTED" if ci[0] > .50 else "NOT_SUPPORTED"


def p2_verdict(left, right, slope, ci):
    if min(left, right) < COVERAGE or slope is None:
        return "UNEVALUABLE"
    if slope <= 0.:
        return "REFUTED"
    if ci[0] >= .5 and ci[1] <= 2.:
        return "SUPPORTED"
    if ci[1] < .5 or ci[0] > 2.:
        return "REFUTED"
    return "INCONCLUSIVE"


def p3_verdict(n, ci):
    if n < COVERAGE:
        return "UNEVALUABLE"
    return "SUPPORTED" if ci[1] <= .10 else "NOT_SUPPORTED"


def p4_verdict(cells):
    if not cells:
        return "UNEVALUABLE"
    if all(c["ci"][1] <= .15 for c in cells):
        return "SUPPORTED"
    if any(c["ci"][0] > .30 for c in cells):
        return "REFUTED"
    return "INCONCLUSIVE"


def weights(rng, n, draws=DRAWS):
    return rng.multinomial(n, np.full(n, 1/n), size=draws).astype(float)


def rate(counts, denom, w):
    return (w @ counts) / (w @ denom)


def lift_counts(mask, y, w):
    per_frame = mask.sum(axis=1)
    yes = (y & mask).sum(axis=1)
    n = int(np.count_nonzero(per_frame))
    if n < COVERAGE:
        return n, None, None
    return n, float(yes.sum()/per_frame.sum()), rate(yes, per_frame, w)


def fit_batch(x, y, w, initial):
    """Fit single-covariate logistic MLE by batched weighted Newton steps."""
    x2 = x*x
    a, b = np.full(len(w), initial[0]), np.full(len(w), initial[1])
    active = np.ones(len(w), dtype=bool)
    for _ in range(60):
        ids = np.flatnonzero(active)
        if not len(ids):
            return a, b
        p = expit(a[ids, None] + b[ids, None]*x)
        mass = w[ids] * p * (1-p)
        residual = w[ids] * (y - p)
        h00, h01, h11 = mass.sum(axis=1), mass @ x, mass @ x2
        g0, g1 = residual.sum(axis=1), residual @ x
        det = h00*h11 - h01*h01
        if np.any(det <= 0):
            raise ArithmeticError("Singular nonseparated logistic fit")
        da, db = (h11*g0 - h01*g1)/det, (h00*g1 - h01*g0)/det
        scale = np.maximum(1., np.maximum(abs(da), abs(db))/3)
        a[ids] += da/scale
        b[ids] += db/scale
        active[ids] = (abs(da) + abs(db)) > 1e-8
    raise ArithmeticError("Nonseparated logistic fit did not converge")


def frame_extremes(x, labels, mask, func, null):
    return func(np.where(mask & labels, x, null), axis=1)


def p2(xi, defined, labels, w):
    valid = defined & np.isfinite(xi) & (xi > 0.)
    assert np.array_equal(defined, valid), "Defined unit has non-finite log xi"
    left = int(np.any(valid & (xi < 1), axis=1).sum())
    right = int(np.any(valid & (xi > 1), axis=1).sum())
    rec = dict(frames_below=left, frames_above=right, xi50=None, ci=None, slope=None,
               method="frame-cluster percentile bootstrap")
    if min(left, right) < COVERAGE or not labels[valid].any() or labels[valid].all():
        return dict(rec, verdict="UNEVALUABLE")
    x = np.log(xi, where=valid, out=np.zeros_like(xi))
    xmin0 = frame_extremes(x, ~labels, valid, np.min, np.inf)
    xmin1 = frame_extremes(x, labels, valid, np.min, np.inf)
    xmax0 = frame_extremes(x, ~labels, valid, np.max, -np.inf)
    xmax1 = frame_extremes(x, labels, valid, np.max, -np.inf)
    lo, hi = xmax0.max(), xmin1.min()
    if lo < hi:
        ci = [float(np.exp(v)) for v in (lo, hi)]
        return dict(rec, ci=ci, method="complete-separation interval",
                    verdict=p2_verdict(left, right, math.inf, ci))
    if xmax1.max() < xmin0.min():
        return dict(rec, method="negative complete separation", verdict="REFUTED")

    xv, y = x[valid], labels[valid]
    indices = np.broadcast_to(np.arange(len(x))[:, None], x.shape)[valid]
    a, b = fit_batch(xv, y, np.ones((1,len(xv))), (0.,0.))
    a, b = float(a[0]), float(b[0])
    rec["slope"] = b
    if b != 0.:
        rec["xi50"] = math.exp(-a/b) if -a/b < math.log(sys.float_info.max) else "+inf"
    if b <= 0:
        return dict(rec, verdict="REFUTED")

    lower, upper = np.empty(len(w)), np.empty(len(w))
    separated = 0
    for start in range(0, len(w), 48):
        stop = min(start+48, len(w))
        ww = w[start:stop]
        present = ww > 0
        low = np.where(present, xmax0, -np.inf).max(axis=1)
        high = np.where(present, xmin1, np.inf).min(axis=1)
        rev_low = np.where(present, xmax1, -np.inf).max(axis=1)
        rev_high = np.where(present, xmin0, np.inf).min(axis=1)
        forward = low < high
        reverse = rev_low < rev_high
        if (forward & reverse).any():
            raise ArithmeticError("Bootstrap draw has only one Q value")
        fit = ~(forward | reverse)
        outlo, outhi = lower[start:stop], upper[start:stop]
        outlo[forward], outhi[forward] = low[forward], high[forward]
        outlo[reverse], outhi[reverse] = rev_low[reverse], rev_high[reverse]
        separated += int((~fit).sum())
        if fit.any():
            aa, bb = fit_batch(xv, y, ww[fit][:, indices], (a,b))
            if (bb == 0).any():
                raise ArithmeticError("Zero bootstrap logistic slope")
            outlo[fit] = outhi[fit] = -aa/bb
    log_ci = [np.quantile(lower,.025), np.quantile(upper,.975)]
    ci = [float(np.exp(v)) if v < math.log(sys.float_info.max) else math.inf for v in log_ci]
    verdict = p2_verdict(left, right, b, ci)
    return dict(rec, ci=[v if math.isfinite(v) else "+inf" for v in ci],
                separated_bootstrap_draws=separated, verdict=verdict)


def load_block(out, block, start, n):
    lookup = {key: i for i, key in enumerate(CELLS)}
    raw = np.empty((n,len(CELLS)), dtype=object)
    files = []
    for i in range(WORKERS):
        path = out/f"{block}_{i:02d}.jsonl.gz"
        files.append(f"{digest(path, 'md5')}  {path.name}")
        with gzip.open(path, "rt") as fh:
            for line in fh:
                row = json.loads(line)
                offset = row["frame"]-start
                assert 0 <= offset < n and offset % WORKERS == i
                cell = offset, lookup[row["rho"],row["R"]]
                assert raw[cell] is None
                raw[cell] = row
    assert all(row is not None for row in raw.flat)
    return raw, files


def array_of(raw, fn, dtype):
    return np.array([fn(row) for row in raw.flat], dtype=dtype).reshape(raw.shape)


def calibration_counts(raw):
    defined = array_of(raw, lambda r:r["defined"],bool)
    a2 = array_of(raw, lambda r:r["gt1"],bool)
    c = array_of(raw, lambda r:r["gt_c"],bool)
    registered = json.loads((PHASE1B/"predictions_v2.json").read_text())
    summary = json.loads((PHASE1B/"calibration_v2_summary.json").read_text())
    assert registered["selected_snr_db"] == {"0.3":4.5,"0.5":4.5}
    prediction_cells = {(r["rho"],r["R"]):r for r in registered["cells"]}
    summary_cells = {(r["rho"],r["R"]):r for r in summary["cells"] if r["snr_db"] == 4.5}
    for i, key in enumerate(CELLS):
        n = int(defined[:,i].sum())
        assert n == summary_cells[key]["window_defined"]
        for label, count, tag in (("P_hat_A2", a2[:,i].sum(), "A2_predicted_count"),
                                  ("P_hat_C", c[:,i].sum(), "CODELAY_predicted_count")):
            assert count == summary_cells[key][tag]
            assert (float(count/n) if n else None) == prediction_cells[key][label]
    return defined, a2


def secondary(raw, w):
    triggered = array_of(raw, lambda r:r["triggered"],bool)
    f0_error = array_of(raw, lambda r:r["f0_frame_error"],bool)
    defined = array_of(raw, lambda r:r["defined"],bool)
    mismatch = array_of(raw, lambda r:r["anchor_mismatch"] is True,bool)
    data = []
    for ratio in RATIOS:
        ix = [i for i in range(raw.shape[1]) if raw[0,i]["R"]==ratio]
        sub = raw[:,ix]
        trig = triggered[:,ix]
        n = int(trig.sum())
        by_arm = {}
        for arm in ARMS:
            outcomes = [row["arms"][arm] for row in sub.flat]
            classes = Counter(o["first_edit_class"] for o in outcomes)
            winners = Counter(o["pair"]["global_winner"] for o in outcomes if o["pair"] is not None)
            by_arm[arm] = dict(first_edit_counts={k:classes[k] for k in CLASSES},
                               global_winner_counts={k:winners[k] for k in WINNERS},
                               numerical_fallbacks=sum(o["numerical_fallback"] for o in outcomes))
        a2 = array_of(sub, lambda r:r["arms"]["A2"]["frame_error"],bool)
        c = array_of(sub, lambda r:r["arms"]["CODELAY"]["frame_error"],bool)
        gain = ((a2.astype(int)-c.astype(int))*trig).sum(axis=1)
        den = trig.sum(axis=1)
        data.append(dict(R=ratio, units=sub.size, triggered=n,
                         f0_fer=float(f0_error[:,ix].mean()), defined=int(defined[:,ix].sum()),
                         anchor_mismatches=int(mismatch[:,ix].sum()), arms=by_arm,
                         triggered_fer_A2=float((a2 & trig).sum()/n) if n else None,
                         triggered_fer_CODELAY=float((c & trig).sum()/n) if n else None,
                         triggered_fer_advantage=float(gain.sum()/n) if n else None,
                         triggered_fer_advantage_ci=confidence(rate(gain,den,w[w@den>0])) if n else None))
    return dict(units=raw.size, window_defined=int(defined.sum()),
                anchor_mismatches=int(mismatch.sum()), by_R=data)


def analyze(cal, raw):
    defined_cal, binary_cal = calibration_counts(cal)
    rng = np.random.default_rng(CLUSTER_SEED)
    wm, wc = weights(rng,len(raw)), weights(rng,len(cal))
    defined = array_of(raw, lambda r:r["defined"],bool)
    xi = array_of(raw, lambda r:float(r["window"]["xi"]) if r["defined"] else 0.,float)
    win = array_of(raw, lambda r:r["defined"] and r["window"]["xi"] != "+inf" and
                   r["R"] > float(r["window"]["R_A2_star"]) and r["R"] < float(r["window"]["R_C_star"]),bool)
    labels = {arm:array_of(raw,lambda r: r["defined"] and r["arms"][arm]["pair"]["Q"],bool) for arm in ARMS}
    p4_cells = {}
    for i, (rho,R) in enumerate(CELLS):
        m, c = defined[:,i], defined_cal[:,i]
        if min(m.sum(), c.sum()) < COVERAGE:
            continue
        ml, cl = labels["A2"][:,i], binary_cal[:,i]
        main, cal = float(ml.sum()/m.sum()), float(cl.sum()/c.sum())
        good = (wm@m > 0) & (wc@c > 0)
        assert good.any()
        ci = confidence(abs(rate(ml,m,wm[good])-rate(cl,c,wc[good])))
        p4_cells[i] = dict(rho=rho,R=R,main=main,cal=cal,absolute_difference=abs(main-cal),
                           ci=ci,main_n=int(m.sum()),cal_n=int(c.sum()))
    results = {}
    for group, ix in (("0.3",list(range(12))), ("0.5",list(range(12,24))), ("pooled", list(range(24)))):
        v, z, a, c = defined[:,ix], xi[:,ix], labels["A2"][:,ix], labels["CODELAY"][:,ix]
        lo, low, bd_lo = lift_counts(v & (z <= .5), a, wm)
        hi, high, bd_hi = lift_counts(v & (z >= 2.), a, wm)
        ci = confidence(bd_hi-bd_lo) if low is not None and high is not None else None
        n, share, bd = lift_counts(win[:,ix], c, wm)
        c_ci = confidence(bd) if share is not None else None
        cells = [p4_cells[i] for i in ix if i in p4_cells]
        results[group] = dict(
            P1=dict(verdict=p1_verdict(lo,hi,ci), lo_frames=lo, hi_frames=hi,
                    low_share=low, high_share=high, difference=high-low if ci is not None else None, ci=ci),
            P2=p2(z,v,a,wm),
            P3=dict(verdict=p3_verdict(n,c_ci), frames=n, share=share, ci=c_ci),
            P4=dict(verdict=p4_verdict(cells), cells=cells,
                    max_abs_difference=max((r["absolute_difference"] for r in cells),default=None),
                    max_ci_lower=max((r["ci"][0] for r in cells),default=None),
                    max_ci_upper=max((r["ci"][1] for r in cells),default=None)),
            secondary=secondary(raw[:,ix],wm))
    return results


def score_predictions(results):
    pooled = results["pooled"]
    forecasts = {"P1 SUPPORTED":.85,"P2 SUPPORTED":.50,"P2 REFUTED":.20,"P3 SUPPORTED":.80,"P4 SUPPORTED":.40}
    scores = {}
    for event, prob in forecasts.items():
        test, verdict = event.split()
        actual = pooled[test]["verdict"]
        hit = int(actual == verdict) if actual != "UNEVALUABLE" else None
        scores[event] = dict(probability=prob, event=hit, brier=(prob-hit)**2 if hit is not None else None)
    return scores


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("calibration","main"))
    p.add_argument("out",type=Path)
    args = p.parse_args()
    out = args.out
    cal, cal_md5 = load_block(out,"calibration",54000,200)
    freeze = json.loads((out/"FREEZE.json").read_text())
    if args.mode == "calibration":
        calibration_counts(cal)
        write(out/"calibration_replay.json",dict(status="PASS",cells=24,frames=200,md5=cal_md5),
              dict(freeze_sha256=digest(out/"FREEZE.json"),snr_db=4.5,masked_f0_only=True))
        return
    assert json.loads((out/"calibration_replay.json").read_text())["md5"] == cal_md5
    raw, raw_md5 = load_block(out,"main",55000,1000)
    results = analyze(cal,raw)
    (out/"RAW_SHARDS_MD5.txt").write_text("\n".join(cal_md5+raw_md5)+"\n")
    write(out/"analysis.json",dict(status="DONE",groups=results,predictions=score_predictions(results)),
          dict(freeze_sha256=digest(out/"FREEZE.json"),commit=freeze["commit"],confidence=.95,
               bootstrap_draws=DRAWS,seed=CLUSTER_SEED,cluster="physical frame, all R and rho",
               cal_main_resampling="independent",p4_interval="percentiles of absolute differences"))


if __name__ == "__main__":
    main()
