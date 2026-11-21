"""Evaluate TEST once against committed stage1 seal; no fitting/reselection.

Required: --seal-commit (main's attestation), --seal-md5. Git never accessed.
Missing quiet data yields PENDING_QUIET, never PASS. All result files bind inputs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.stats import t as student_t
import c1apb_lib as L


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seal", type=Path, required=True)
    p.add_argument("--seal-md5", required=True)
    p.add_argument("--seal-commit", required=True)
    p.add_argument("--test", type=Path, default=L.HERE/"out/c1apb_test")
    p.add_argument("--quiet", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--screening", action="store_true", help="A3: exactly1000 TEST/100 quiet, descriptive only")
    p.add_argument("--a3-commit")
    p.add_argument("--manifest-md5")
    p.add_argument("--sealed-anchor-root", type=Path,
                   help="relocated S1 c1apb_smoke directory; exact sealed input digests still required")
    return p.parse_args(argv)


def primary_stats(o, a, b, w):
    ratio = float(a["cost"].mean()/b["cost"].mean())
    rb = L.bootstrap_mean(w, a["cost"])/L.bootstrap_mean(w, b["cost"])
    ni = L.paired_ni(a["fail"], b["fail"])
    up, ub = L.cp_upper(int(a["fail"].sum()), len(o.frames)), L.cp_upper(int(b["fail"].sum()), len(o.frames))
    reliab = up <= L.CELLS[o.cell][2] and ub <= L.CELLS[o.cell][2]
    return dict(n=len(o.frames), FER_P=float(a["fail"].mean()), FER_B=float(b["fail"].mean()),
                CP_upper_P=up, CP_upper_B=ub, NI=ni, R=ratio, R_interval=L.interval(rb),
                saving_interval=L.interval(1-rb), reliability_pass=reliab,
                NI_pass=ni["upper"] <= .01, compute_statistical_pass=ratio <= .85 and np.quantile(rb, 1-L.ALPHA) < 1,
                policy_reliability_kill=L.cp_lower(int(a["fail"].sum()), len(o.frames)) > L.CELLS[o.cell][2]
                or -L.paired_ni(b["fail"], a["fail"])["upper"] > .01,
                cost_P=float(a["cost"].mean()), cost_B=float(b["cost"].mean()),
                secondary_P=dict(inner_updates=float(a["updates"].mean()), rounds=float(a["stop"].mean()),
                                 decoder_iterations=float(a["decoder"].mean()), p95_cost=float(np.quantile(a["cost"], .95)),
                                 giveup_rate=float(a["giveup"].mean()), queries=float(a["queries"].mean())),
                secondary_B=dict(inner_updates=float(b["updates"].mean()), rounds=float(b["stop"].mean()),
                                 decoder_iterations=float(b["decoder"].mean()), p95_cost=float(np.quantile(b["cost"], .95))))


def g3_contrasts(pairs, results, weights):
    out = {}
    alpha = .05/3
    for cls in ("B3", "B4", "B5"):
        if len(results) != 4 or any(cls not in s for s in results.values()):
            out[cls] = dict(status="INCONCLUSIVE", reason="all four sealed class winners required")
            continue
        cp, cb, fp, fb, bootp, bootb, bootd = [], [], [], [], [], [], []
        for cell, s in results.items():
            a, b, w = s["P"], s[cls], weights[cell]
            cp.append(a["cost"].mean()); cb.append(b["cost"].mean())
            fp.append(a["fail"].mean()); fb.append(b["fail"].mean())
            bootp.append(L.bootstrap_mean(w, a["cost"]))
            bootb.append(L.bootstrap_mean(w, b["cost"]))
            bootd.append(L.bootstrap_mean(w, a["fail"].astype(float)-b["fail"].astype(float)))
        ratio = float(np.mean(cp)/np.mean(cb))
        rb = np.mean(bootp, axis=0)/np.mean(bootb, axis=0)
        di = L.interval(np.mean(bootd, axis=0), alpha)
        si = L.interval(1-rb, alpha)
        out[cls] = dict(R=ratio, saving=1-ratio, saving_interval=si, d=float(np.mean(fp)-np.mean(fb)),
                        d_interval=di, alpha=alpha, pass_gate=ratio <= .95 and si["lower"] > 0 and di["upper"] <= .01,
                        pooling="four cell mean costs/FER equal weight; shared frame/block bootstrap")
    return out


def g4_mechanism(pairs, seal, weights):
    brier, ranks, all_contrasts = {}, {}, []
    for cell, pair in pairs.items():
        o, y = pair
        if cell not in seal["models"]["loco"]:
            raise ValueError(f"missing sealed LOCO models {cell}")
        models = seal["models"]["loco"][cell]
        full = L.frame_brier(pair, models["full"], True)
        generic = L.frame_brier(pair, models["generic"], False)
        valid = np.isfinite(full) & np.isfinite(generic)
        if not valid.any():
            brier[cell] = dict(status="INCONCLUSIVE", reason="no live prediction states")
        else:
            gain = generic[valid]-full[valid]
            nonempty = (weights[cell][:, valid].sum(1) > 0).all()
            ci = L.interval(L.bootstrap_mean(weights[cell][:, valid], gain), .05) if nonempty else None
            brier[cell] = dict(full=float(full[valid].mean()), generic=float(generic[valid].mean()),
                               gain=float(gain.mean()), interval=ci, n_live_frames=int(valid.sum()),
                               status="ASSESSED" if nonempty else "INCONCLUSIVE_empty_bootstrap_live_state_group",
                               pass_gate=nonempty and float(gain.mean()) >= .005 and ci["lower"] > 0,
                               interpretation="LOCO probability prediction; no held-cell refit; not policy zero-shot")
            brier[cell]["calibration_full"] = L.calibration_bins(pair, models["full"], True)
            brier[cell]["calibration_generic"] = L.calibration_bins(pair, models["generic"], False)
        q, _ = L.qcache(o, seal["models"]["pooled"]["full"])
        strata = []
        for Rc in range(2, 11):
            for e in range(1, min(3, Rc-1)+1):
                cut = seal["train_quintile_cuts"][cell][f"{e}:{Rc}"]
                if cut is None:
                    continue
                live = (o.syn[0, :, :e] != 0).all(1)
                delta = q[0, e, 10, Rc]-q[0, e, e, Rc]
                quintile = np.searchsorted(cut, delta, side="right")
                y20 = L.terminal_labels(o, y, 0, Rc)
                ye = L.terminal_labels(o, y, L.ARMS.index(f"E{e}"), Rc)
                net = y20.astype(float)-ye.astype(float)
                rescue, harm = y20 & ~ye, ~y20 & ye
                entries = []
                for k in range(5):
                    take = live & (quintile == k)
                    stats = dict(quintile=k+1, n=int(take.sum()), net=float(net[take].mean()) if take.any() else None,
                                        rescue=float(rescue[take].mean()) if take.any() else None,
                                        harm=float(harm[take].mean()) if take.any() else None)
                    stats.update(quintile_cluster_ci(weights[cell], take, net, rescue, harm))
                    entries.append(stats)
                low, high = live & (quintile == 0), live & (quintile == 4)
                entry = dict(e=e, Rc=Rc, cuts=cut, quintiles=entries)
                if low.any() and high.any():
                    # Resample complete frames, preserving all repeated states.
                    w = weights[cell]
                    denhigh, denlow = w@high.astype(float), w@low.astype(float)
                    ok = (denhigh > 0) & (denlow > 0)
                    if not ok.all():
                        entry["contrast_status"] = "INCONCLUSIVE_zero_bootstrap_group"
                        entry["zero_bootstrap_replicates"] = int((~ok).sum())
                    else:
                        contrast = (w@(net*high))/denhigh-(w@(net*low))/denlow
                        entry.update(high_minus_low=float(net[high].mean()-net[low].mean()), interval=L.interval(contrast, .05))
                        all_contrasts.append((cell, entry["high_minus_low"], contrast))
                strata.append(entry)
        ranks[cell] = strata
    # Each cell has equal mass; within cell each predeclared (e,Rc) stratum has
    # equal mass. Empty extremes give INCONCLUSIVE rather than data-driven omission.
    cell_contrasts, cell_points = [], []
    complete = True
    for cell in pairs:
        chosen = [(p, b) for c, p, b in all_contrasts if c == cell]
        expected = sum(1 for s in ranks[cell] if s["cuts"] is not None)
        if len(chosen) != expected or not chosen:
            complete = False
        if chosen:
            cell_points.append(float(np.mean([p for p, _ in chosen])))
            cell_contrasts.append(np.mean([b for _, b in chosen], axis=0))
    pooled = dict(status="INCONCLUSIVE", pass_gate=False, reason="empty quintile extremes or bootstrap group")
    if complete and len(cell_contrasts) == 4:
        ci = L.interval(np.mean(cell_contrasts, axis=0), .05)
        pooled = dict(status="ASSESSED", high_minus_low=float(np.mean(cell_points)), interval=ci,
                      pass_gate=ci["lower"] > 0, pooling="four cells equal; e/Rc strata equal within cell")
    n_pass = sum(z.get("pass_gate", False) for z in brier.values())
    return dict(loco_brier=brier, delta_quintiles=ranks, pooled_delta=pooled,
                pass_gate=n_pass >= 3 and pooled["pass_gate"])


def quintile_cluster_ci(w, take, net, rescue, harm):
    """Descriptive95% two-sided CI, whole frame/shard cluster weights.

    No empty-bootstrap filtering/pseudocounts. Undefined conditional mean -> NA.
    """
    if not take.any():
        return dict(CI_status="EMPTY_QUINTILE", net_CI95=None, rescue_CI95=None, harm_CI95=None)
    denominator = w@take.astype(float)
    zero = int(np.sum(denominator == 0))
    if zero:
        return dict(CI_status="UNDEFINED_BOOTSTRAP_GROUP", zero_bootstrap_replicates=zero,
                    net_CI95=None, rescue_CI95=None, harm_CI95=None)
    return dict(CI_status="DESCRIPTIVE_CLUSTER_95",
                net_CI95=L.interval((w@(net*take))/denominator, .025),
                rescue_CI95=L.interval((w@(rescue*take))/denominator, .025),
                harm_CI95=L.interval((w@(harm*take))/denominator, .025))


def family_kill(pair, cellseal, cache, overhead, baseline):
    """KILL3 only: all presealed P candidates; no TEST winner selection.

    Bounds are simultaneous Bonferroni within cell (three endpoint statements per
    candidate, family alpha=.0125). Cluster-t compute bounds are approximate.
    At least one valid endpoint must exclude each candidate. Otherwise inconclusive.
    """
    o, y = pair
    recs = cellseal["candidates"]["P"]
    alpha = L.ALPHA/(3*len(recs))
    blocks = np.unique(o.blocks)
    unsafe, excluded_saving, unresolved = 0, 0, 0
    capable, capable_unsafe = 0, 0
    for rec in recs:
        s = L.score(o, y, L.replay(o, rec["policy"], cache, overhead))
        dangerous = L.cp_lower(int(s["fail"].sum()), len(o.frames), alpha) > cellseal["ell"]
        dangerous |= -L.paired_ni(baseline["fail"], s["fail"], alpha)["upper"] > .01
        # Positive E[C_P-.85 C_B] excludes 15% saving without Fieller ratio division.
        v = s["cost"]-.85*baseline["cost"]
        deviation = np.array([(v[o.blocks == b]-v.mean()).sum() for b in blocks])
        se = np.sqrt(len(blocks)/(len(blocks)-1)*np.sum(deviation**2))/len(v) if len(blocks) > 1 else np.inf
        low = float(v.mean()-student_t.ppf(1-alpha, max(1, len(blocks)-1))*se)
        cheap = rec["cost"] <= .85*cellseal["choices"]["Bstar"]["expected_cal_cost"]
        capable += int(cheap); capable_unsafe += int(cheap and dangerous)
        unsafe += int(dangerous); excluded_saving += int(low > 0)
        unresolved += int(not dangerous and low <= 0)
    return dict(candidates=len(recs), CAL_capable_15pct=capable, capable_reliability_harm=capable_unsafe,
                unsafe=unsafe, saving_excluded=excluded_saving, unresolved=unresolved, component_alpha=alpha,
                kill=capable > 0 and capable_unsafe == capable and unresolved == 0,
                scope="sealed deterministic P candidates; does not exclude untested mixtures/new action families",
                cost_bound="approximate shard-cluster t; CP finite-sample iid and Tango approximate")


def quiet_validation(pairs, seal, args):
    if args.quiet is None:
        return {}, [], dict(status="PENDING_QUIET", pass_gate=False)
    quiet, files, g0 = L.load_cells([args.quiet], tuple(L.CELLS), range(600, 800), L.NEW,
                                   seal["_config"]["mchecks"], shuffled=True, shards=8)
    report = {}
    for cell, (oq, yq) in quiet.items():
        if g0[cell]["context_signature"] != seal["G0"]["cal"][cell]["context_signature"]:
            raise ValueError(f"quiet kernel/prior changed since CAL {cell}")
        om, ym = pairs[cell]
        selected = (om.frames >= 600) & (om.frames < 800)
        op, yp = L.subset((om, ym), selected)
        # Quiet repeats numeric evidence, not a fresh statistical sample.
        if not np.array_equal(oq.syn, op.syn) or not np.array_equal(oq.dec, op.dec) or not np.array_equal(yq.ierr, yp.ierr):
            raise ValueError(f"quiet numerical mismatch {cell}")
        z = seal["cells"][cell]
        if not z["operable"]:
            report[cell] = dict(status="NONOPERABLE", pass_gate=False)
            continue
        ratios = []
        for o, y in ((oq, yq), (op, yp), (om, ym)):
            cache = L.qcache(o, seal["models"]["pooled"]["full"], seal["models"]["pooled"]["rescue"])
            p = L.eval_mix(o, y, z["choices"]["P"], cache, seal["overhead_seconds"])
            b = L.eval_mix(o, y, z["choices"]["Bstar"], cache, seal["overhead_seconds"])
            ratios.append(float(p["cost"].mean()/b["cost"].mean()))
        gap = abs(ratios[0]-ratios[1])
        report[cell] = dict(R_quiet=ratios[0], R_main_same_200=ratios[1], R_main=ratios[1], R_main_full_TEST=ratios[2], absolute_gap=gap,
                            paired_subset_gap=abs(ratios[0]-ratios[1]),
                            pass_gate=gap <= .03, status="VALIDATED" if gap <= .03 else "contended timing")
    return report, files, g0


def screening_contrast(a, b, w, alpha=.025):
    """Fixed winners, paired frame-block percentile endpoints; never selects."""
    difference = a["fail"].astype(float)-b["fail"].astype(float)
    dboot = L.bootstrap_mean(w, difference)
    result = dict(FER=float(a["fail"].mean()), FER_reference=float(b["fail"].mean()),
                  d=float(difference.mean()), d_interval=L.interval(dboot, alpha),
                  confidence=dict(endpoint_alpha=alpha, bootstrap="paired frame/shard", descriptive_only=True))
    for field, name in (("cost", "seconds"), ("updates", "inner_updates")):
        ratio = float(a[field].mean()/b[field].mean())
        rb = L.bootstrap_mean(w, a[field])/L.bootstrap_mean(w, b[field])
        result[name] = dict(mean=float(a[field].mean()), reference_mean=float(b[field].mean()),
                            R=ratio, R_interval=L.interval(rb, alpha), saving=1-ratio,
                            saving_interval=L.interval(1-rb, alpha))
    return result


def screening_pool(results, weights, policy, reference, cells, alpha=.025):
    """Equal CAL-eligible cell means. C1 stays in primary denominator, never added."""
    if not cells or any(policy not in results.get(c, {}) or reference not in results.get(c, {}) for c in cells):
        return dict(status="UNAVAILABLE_SEALED_WINNER", cells=list(cells))
    a = [results[c][policy] for c in cells]
    b = [results[c][reference] for c in cells]
    db = np.mean([L.bootstrap_mean(weights[c], x["fail"].astype(float)-y["fail"].astype(float))
                  for c, x, y in zip(cells, a, b)], axis=0)
    out = dict(status="SCREENING_DESCRIPTIVE", cells=list(cells),
               d=float(np.mean([x["fail"].mean()-y["fail"].mean() for x, y in zip(a, b)])),
               d_interval=L.interval(db, alpha), endpoint_alpha=alpha,
               pooling="equal cell mean costs/FER; cells fixed by CAL availability, not TEST")
    for field, name in (("cost", "seconds"), ("updates", "inner_updates")):
        ma, mb = float(np.mean([x[field].mean() for x in a])), float(np.mean([y[field].mean() for y in b]))
        ba = np.mean([L.bootstrap_mean(weights[c], x[field]) for c, x in zip(cells, a)], axis=0)
        bb = np.mean([L.bootstrap_mean(weights[c], y[field]) for c, y in zip(cells, b)], axis=0)
        out[name] = dict(mean=ma, reference_mean=mb, R=ma/mb, R_interval=L.interval(ba/bb, alpha),
                         saving=1-ma/mb, saving_interval=L.interval(1-ba/bb, alpha))
    return out


def screening_quiet(pairs, seal, args):
    if args.quiet is None:
        return {}, [], dict(status="MISSING_SCREENING_QUIET")
    quiet, files, g0 = L.load_cells([args.quiet], tuple(L.CELLS), range(600, 700), L.NEW,
                                   seal["_config"]["mchecks"], shuffled=True, shards=8)
    report = {}
    for cell, qpair in quiet.items():
        oq, yq = qpair
        om, ym = pairs[cell]
        op, yp = L.subset((om, ym), om.frames < 700)
        if g0[cell]["context_signature"] != seal["G0"]["cal"][cell]["context_signature"]:
            raise ValueError(f"quiet kernel changed {cell}")
        if not np.array_equal(oq.syn, op.syn) or not np.array_equal(oq.dec, op.dec) or not np.array_equal(yq.ierr, yp.ierr):
            raise ValueError(f"quiet/main numerical mismatch {cell}")
        report[cell] = {}
        for name, pa, pb in (("P_vs_Bstar", "P", "Bstar"), ("B4_vs_B0", "B4", "B0")):
            mixa, mixb = seal["cells"][cell]["choices"].get(pa), seal["cells"][cell]["choices"].get(pb)
            if mixa is None or mixb is None:
                report[cell][name] = dict(status="UNAVAILABLE_SEALED_WINNER")
                continue
            ratios = []
            for o, y in ((oq, yq), (op, yp), (om, ym)):
                cache = L.qcache(o, seal["models"]["pooled"]["full"], seal["models"]["pooled"]["rescue"])
                a = L.eval_mix(o, y, mixa, cache, seal["overhead_seconds"])
                b = L.eval_mix(o, y, mixb, cache, seal["overhead_seconds"])
                ratios.append(float(a["cost"].mean()/b["cost"].mean()))
            gap = abs(ratios[0]-ratios[1])
            report[cell][name] = dict(R_quiet=ratios[0], R_main_matched100=ratios[1],
                                      R_main_full1000=ratios[2], absolute_gap=gap, threshold=.03,
                                      status="MATCHED_TIMING_STABLE" if gap <= .03 else "contended timing",
                                      interpretation="A3 matched100, descriptive, no PASS")
    return report, files, g0


def screening_g4_labels(g4):
    """Preserve frozen engineering lines as screening indicators, no PASS claim."""
    out = dict(g4)
    out["screening_engineering_lines_met"] = out.pop("pass_gate")
    for value in out["loco_brier"].values():
        if "pass_gate" in value:
            value["screening_effect_line_met"] = value.pop("pass_gate")
        value["interval_convention"] = "one-sided95% endpoints (central90), frozen G4 engineering line"
    out["pooled_delta"]["screening_positive_ranking_indicator"] = out["pooled_delta"].pop("pass_gate")
    out["interpretation"] = "SCREENING: LOCO probability transfer, not policy zero-shot; no formal G4/PASS certificate"
    return out


def verify_sealed_inputs(bindings, anchor_root):
    """Only S1's four archived anchors may move; bytes must match the seal."""
    old_root = Path("/data/guoyikun/tmp/c1apb_smoke")
    allowed = {f"{kind}_shard00{i}.{suffix}"
               for kind, suffix in (("config", "json"), ("rows", "jsonl")) for i in (0, 1)}
    relocated = {}
    for name, digest in bindings.items():
        path = Path(name)
        if not path.exists():
            if anchor_root is None or path.parent != old_root or path.name not in allowed:
                raise FileNotFoundError(f"sealed input missing: {path}")
            path = Path(anchor_root)/path.name
            relocated[name] = dict(path=str(path), sealed_md5=digest)
        if L.md5(path) != digest:
            raise ValueError(f"sealed input digest changed: {path}")
    return relocated


def screening_main(args):
    started = time.perf_counter()
    if not args.a3_commit or not args.manifest_md5:
        raise ValueError("SCREENING requires --a3-commit and --manifest-md5 authority attestations")
    if L.md5(args.seal) != args.seal_md5:
        raise ValueError("seal digest mismatch")
    seal = json.loads(args.seal.read_text())
    if seal["label"] != "SEALED_CAL" or len(seal["cells"]) != 4:
        raise ValueError("real four-cell seal required")
    evaluation_changes = {}
    for path, digest in seal["code_md5s"].items():
        local = L.HERE/Path(path).name
        actual = L.md5(local)
        if actual != digest:
            if local.name not in ("c1apb_stage2.py", "unit_check_c1apb.py"):
                raise ValueError(f"sealed fit/replay source changed: {local}")
            evaluation_changes[local.name] = dict(sealed_md5=digest, evaluation_md5=actual,
                                                  reason="authorized A3 SCREENING adapter/tests; frozen policy/model/replay unchanged")
    relocated_inputs = verify_sealed_inputs(seal["input_md5s"], args.sealed_anchor_root)
    if not args.seal_commit.strip():
        raise ValueError("pre-TEST seal commit attestation required")
    pairs, inputs, g0 = L.load_cells([args.test], tuple(L.CELLS), range(600, 1600), L.NEW,
                                    seal["_config"]["mchecks"], shuffled=True, shards=64)
    inputs += [args.seal]+[Path(z["path"]) for z in relocated_inputs.values()]
    bindings = dict(L.snapshot(inputs), **L.code_md5s())
    print("SCREENING G0 pass: four cells1000 frames; frozen winners; no fit/selection", flush=True)
    weights = L.bootstrap_weights({c:o for c,(o,_) in pairs.items()})
    results, primary, practical, g3 = {}, {}, {}, {}
    names = ("B0", "B1", "B2", "B3", "B4", "B5", "P", "Bstar", "P_escalation_only", "P_giveup_only")
    for cell, (o, y) in pairs.items():
        if g0[cell]["context_signature"] != seal["G0"]["cal"][cell]["context_signature"]:
            raise ValueError(f"TEST kernel changed since CAL {cell}")
        choices = seal["cells"][cell]["choices"]
        cache = L.qcache(o, seal["models"]["pooled"]["full"], seal["models"]["pooled"]["rescue"])
        results[cell] = {name:L.eval_mix(o,y,choices[name],cache,seal["overhead_seconds"])
                         for name in names if choices.get(name) is not None}
        s = results[cell]
        if "P" not in s or "Bstar" not in s:
            primary[cell] = dict(status="NONOPERABLE_AT_CAL", n=1000, interpretation="no invented TEST winner")
        else:
            z = primary_stats(o, s["P"], s["Bstar"], weights[cell])
            for key in ("reliability_pass", "NI_pass", "compute_statistical_pass", "policy_reliability_kill"):
                z.pop(key)
            z.update(d=z["NI"]["d"], d_interval=L.interval(L.bootstrap_mean(weights[cell],s["P"]["fail"].astype(float)-s["Bstar"]["fail"].astype(float)),L.ALPHA),
                     status="SCREENING_DESCRIPTIVE_ONLY", no_NI_certification=True)
            primary[cell] = z
        practical[cell], g3[cell] = {}, {}
        for name in ("B1", "B2", "B3", "B4", "B5", "P", "P_escalation_only"):
            practical[cell][name] = screening_contrast(s[name],s["B0"],weights[cell]) if name in s and "B0" in s else dict(status="UNAVAILABLE_SEALED_WINNER")
        for ref in ("B3", "B4", "B5"):
            g3[cell][ref] = screening_contrast(s["P"],s[ref],weights[cell],.05/3) if "P" in s and ref in s else dict(status="UNAVAILABLE_SEALED_WINNER")
        print(f"SCREENING {cell}: {primary[cell].get('R','NA')} vs B*; fixed class replays done", flush=True)
    eligible = [c for c in seal["cells"] if seal["cells"][c]["operable"]]
    practical_pool = {name:screening_pool(results,weights,name,"B0",eligible)
                      for name in ("B1","B2","B3","B4","B5","P","P_escalation_only")}
    g3_pool = {ref:screening_pool(results,weights,"P",ref,eligible,.05/3) for ref in ("B3","B4","B5")}
    print("SCREENING G4: LOCO Brier and fixed TRAIN Delta-quintiles including C1", flush=True)
    g4 = screening_g4_labels(g4_mechanism(pairs,seal,weights))
    quiet, ff, quiet_g0 = screening_quiet(pairs,seal,args)
    inputs += ff; bindings.update(L.snapshot(ff))
    config = dict(label="SCREENING", authority="manifest A3; no NI certification or PASS",
                  seal_commit_attestation=args.seal_commit, a3_commit_attestation=args.a3_commit,
                  manifest_md5=args.manifest_md5, seal_md5=args.seal_md5,
                  attestations_verified_by="main session, no git call", test_frames=[600,1599], quiet_frames=[600,699],
                  B=L.BOOT_B, bootstrap_seed=L.BOOT_SEED, sealed_code_md5s=seal["code_md5s"],
                  authorized_evaluation_changes=evaluation_changes, policy_refit=False, policy_reselection=False,
                  relocated_sealed_inputs=relocated_inputs,
                  practical_CI="unadjusted descriptive95% two-sided paired frame/shard percentile",
                  G3_CI="endpoint alpha=.05/3, screening only", G4_CI="frozen one-sided95% Brier/ranking endpoints; quintile descriptive95% two-sided",
                  pooled_comparison_cells=eligible, pooled_scope="CAL-eligible cells fixed at seal; full-four-cell G3 unavailable due C1",
                  primary_verdict="already unreachable by construction at seal; denominator4 unchanged",
                  scope="known/genie support; one code/N/QPSK; no TCOM/deployment claim")
    L.assert_unchanged(bindings)
    payload = dict(**L.provenance(config,inputs), G0=dict(test=g0,quiet=quiet_g0),
                   primary_descriptive=primary, practical_vs_B0=practical, practical_pooled=practical_pool,
                   G3=dict(per_cell=g3,pooled_CAL_eligible=g3_pool,full_four_cell="UNAVAILABLE_C1_NO_SEALED_WINNER"),
                   G4=g4, quiet=quiet, frozen_choices={c:z["choices"] for c,z in seal["cells"].items()},
                   primary_verdict=config["primary_verdict"], wall_seconds=time.perf_counter()-started)
    args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/"analysis.json").exists():
        raise FileExistsError("refuse overwrite of existing analysis")
    L.write_json(args.out/"analysis.json",payload)
    write_screening_md(args.out/"analysis.md",payload)
    for name in ("analysis.json","analysis.md"):
        size=(args.out/name).stat().st_size
        if size>=1_000_000:
            raise RuntimeError(f"compact result exceeds1MB: {name}={size}; keep remote, do not copy")
    print(f"SCREENING complete: {args.out}; wall={payload['wall_seconds']:.1f}s; no PASS claim",flush=True)


def write_screening_md(path,p):
    def f(x):
        return "NA" if x is None else f"{x:.6f}"
    def ci(z):
        return "NA" if z is None else f"[{f(z['lower'])},{f(z['upper'])}]"
    lines=["# SCREENING — sealed policies, A3", "", "FACT: no fit/reselection. Primary gate already unreachable at seal. No NI certification/PASS.", "",
           "Costs: complete receiver seconds+sealed predictor overhead; secondary inner updates. FER erasures included.", "",
           "## P* vs B* — descriptive98.75% upper endpoints", "",
           "|cell|FER P/B|R [bootstrap endpoints]|d [bootstrap endpoints]|CP upper P/B|Tango upper|", "|---|---|---|---|---|---|"]
    for c,z in p["primary_descriptive"].items():
        if "R" not in z:
            lines.append(f"|{c}|NA: no CAL winner|||||")
        else:
            lines.append(f"|{c}|{f(z['FER_P'])}/{f(z['FER_B'])}|{f(z['R'])} {ci(z['R_interval'])}|{f(z['d'])} {ci(z['d_interval'])}|{f(z['CP_upper_P'])}/{f(z['CP_upper_B'])}|{f(z['NI']['upper'])}|")
    lines += ["", "## Frozen class winners vs B0 clock hull", "", "Descriptive95% two-sided cluster intervals; unadjusted multiple contrasts. Cells/policies fixed by CAL, C1 stays NA.", "",
              "|cell|policy|saving seconds [CI95]|R inner updates [CI95]|d [CI95]|", "|---|---|---|---|---|"]
    for c,rows in list(p["practical_vs_B0"].items())+[("pooled C2–C4",p["practical_pooled"])]:
        for name,z in rows.items():
            if "seconds" in z:
                lines.append(f"|{c}|{name}|{f(z['seconds']['saving'])} {ci(z['seconds']['saving_interval'])}|{f(z['inner_updates']['R'])} {ci(z['inner_updates']['R_interval'])}|{f(z['d'])} {ci(z['d_interval'])}|")
    lines += ["", "## G3 — P vs learned controllers", "", "Per-cell and CAL-eligible pool; full-four-cell contrast unavailable. One-sided endpoints alpha=.05/3, descriptive.", "",
              "|cell|reference|saving seconds [endpoints]|d [endpoints]|", "|---|---|---|---|"]
    for c,rows in list(p["G3"]["per_cell"].items())+[("pooled C2–C4",p["G3"]["pooled_CAL_eligible"])]:
        for name,z in rows.items():
            if "seconds" in z:
                lines.append(f"|{c}|{name}|{f(z['seconds']['saving'])} {ci(z['seconds']['saving_interval'])}|{f(z['d'])} {ci(z['d_interval'])}|")
    lines += ["", "## G4 — LOCO and Delta ranking", "", "LOCO probability models frozen; held-cell TEST never refitted. Brier/ranking intervals use frozen one-sided95% endpoints.", "",
              "|cell|Brier full-A/generic|gain [endpoints]|gain≥.005 and lower>0 (screening indicator)|", "|---|---|---|---|"]
    for c,z in p["G4"]["loco_brier"].items():
        lines.append(f"|{c}|{f(z.get('full'))}/{f(z.get('generic'))}|{f(z.get('gain'))} {ci(z.get('interval'))}|{z.get('screening_effect_line_met',False)}|")
    lines += ["", f"Frozen pooled high-minus-low Delta result: `{json.dumps(p['G4']['pooled_delta'])}`.", "",
              "Every cell/e/Rc/quintile net rescue/harm, counts and frame/shard cluster CI95: `analysis.json:G4.delta_quintiles`. Empty groups/replicates stay undefined; no dropped-stratum certificate.", "",
              "## Quiet — matched100, A2/A3", "", "|cell|contrast|R quiet|R main matched100|R main full1000|gap|status|", "|---|---|---|---|---|---|---|"]
    for c,rows in p["quiet"].items():
        for name,z in rows.items():
            lines.append(f"|{c}|{name}|{f(z.get('R_quiet'))}|{f(z.get('R_main_matched100'))}|{f(z.get('R_main_full1000'))}|{f(z.get('absolute_gap'))}|{z['status']}|")
    lines += ["", "CP assumes iid frames; Tango/cluster bootstrap approximate. Practical contrasts descriptive, no formal NI or receiver-family theorem.", "",
              "```json", json.dumps({k:p[k] for k in ("_argv","_config","input_md5s","code_md5s")},indent=2), "```"]
    Path(path).write_text("\n".join(lines)+"\n")


def main(argv=None):
    args = parse_args(argv)
    if args.screening:
        return screening_main(args)
    started = time.perf_counter()
    if L.md5(args.seal) != args.seal_md5:
        raise ValueError("seal digest mismatch")
    seal = json.loads(args.seal.read_text())
    if seal["label"] != "SEALED_CAL" or len(seal["cells"]) != 4:
        raise ValueError("stage2 requires real four-cell CAL seal")
    for p, digest in seal["code_md5s"].items():
        local = L.HERE/Path(p).name
        if L.md5(local) != digest:
            raise ValueError(f"analysis changed since seal: {local}")
    for p, digest in seal["input_md5s"].items():
        if L.md5(p) != digest:
            raise ValueError(f"TRAIN/CAL/config changed since seal: {p}")
    if not args.seal_commit.strip():
        raise ValueError("main must attest pre-TEST seal commit")
    pairs, inputs, g0 = {}, [args.seal], {}
    for cell, sealed in seal["cells"].items():
        n = sealed["planning"]["n_c"]
        x, ff, report = L.load_cells([args.test], (cell,), range(600, 600+n), L.NEW,
                                    seal["_config"]["mchecks"], shuffled=True, shards=64)
        if report[cell]["context_signature"] != seal["G0"]["cal"][cell]["context_signature"]:
            raise ValueError(f"TEST kernel/prior changed since CAL {cell}")
        pairs.update(x); inputs += ff; g0.update(report)
    bindings = dict(L.snapshot(inputs), **L.code_md5s())
    print("TEST G0 pass; replay sealed choices; bootstrap B=20000", flush=True)
    weights = L.bootstrap_weights({c: o for c, (o, _) in pairs.items()})
    results, primary, family = {}, {}, {}
    for cell, (o, y) in pairs.items():
        z = seal["cells"][cell]
        if not z["operable"]:
            primary[cell] = dict(status="NONOPERABLE", pass_gate=False)
            continue
        cache = L.qcache(o, seal["models"]["pooled"]["full"], seal["models"]["pooled"]["rescue"])
        results[cell] = {name: L.eval_mix(o, y, mix, cache, seal["overhead_seconds"])
                         for name, mix in z["choices"].items() if mix is not None and name != "generic_B4"}
        if z["choices"].get("generic_B4") is not None:
            generic = L.qcache(o, seal["models"]["pooled"]["generic"])
            results[cell]["generic_B4"] = L.eval_mix(o, y, z["choices"]["generic_B4"], generic, seal["overhead_seconds"])
        s = results[cell]
        primary[cell] = primary_stats(o, s["P"], s["Bstar"], weights[cell])
        # Individual contrasts support KILL1, not a new TEST-selected winner.
        primary[cell]["increment_saving_intervals"] = {
            name: L.interval(1-L.bootstrap_mean(weights[cell], s["P"]["cost"])/L.bootstrap_mean(weights[cell], s[name]["cost"]))
            for name in ("B3", "B4", "B5") if name in s}
        primary[cell]["increment_reliability_valid"] = {
            name: L.cp_upper(int(s[name]["fail"].sum()), len(o.frames)) <= z["ell"]
            and L.paired_ni(s["P"]["fail"], s[name]["fail"])["upper"] <= .01
            for name in ("B3", "B4", "B5") if name in s}
        family[cell] = family_kill((o, y), z, cache, seal["overhead_seconds"], s["Bstar"])
        print(f"{cell}: CP={primary[cell]['CP_upper_P']:.4f}, NI={primary[cell]['NI']['upper']:.4f}, R={primary[cell]['R']:.4f}", flush=True)
    g3 = g3_contrasts(pairs, results, weights)
    g4 = g4_mechanism(pairs, seal, weights)
    quiet, ff, g0quiet = quiet_validation(pairs, seal, args)
    inputs += ff
    bindings.update(L.snapshot(ff))
    for cell, z in primary.items():
        if "R" not in z:
            continue
        q = quiet.get(cell, dict(status="PENDING_QUIET", pass_gate=False))
        z["quiet"] = q
        z["pass_gate"] = z["reliability_pass"] and z["NI_pass"] and z["compute_statistical_pass"] and q["pass_gate"]
        z["status"] = "PASS" if z["pass_gate"] else "PENDING_QUIET" if q["status"] == "PENDING_QUIET" else "KILL_SELECTED_POLICY" if z["policy_reliability_kill"] else "INCONCLUSIVE"
    passed = [c for c, z in primary.items() if z.get("pass_gate", False)]
    coverage = len(passed) >= 3 and len({L.CELLS[c][0] for c in passed}) == 2
    kill1 = [c for c, z in primary.items() if z.get("reliability_pass", False) and z.get("NI_pass", False)
             and z["saving_interval"]["upper"] < .15
             and len(z["increment_saving_intervals"]) == 3
             and all(z["increment_reliability_valid"].values())
             and all(v["upper"] < .05 for v in z["increment_saving_intervals"].values())]
    tight_brier = [c for c, z in g4["loco_brier"].items() if (z.get("interval") or {}).get("upper", np.inf) < .005]
    generic_equal = []
    kill4 = []
    for c, s in results.items():
        w = weights[c]
        if "generic_B4" in s:
            generic = s["generic_B4"]
            ci = L.interval(1-L.bootstrap_mean(w, s["P"]["cost"])/L.bootstrap_mean(w, generic["cost"]))
            if ci["upper"] < .05 and L.paired_ni(generic["fail"], s["P"]["fail"])["upper"] <= .01 and L.cp_upper(int(generic["fail"].sum()), len(generic["fail"])) <= L.CELLS[c][2]:
                generic_equal.append(c)
        p, b = s["P"], s["Bstar"]
        uncosted_ratio = (p["cost"]-p["overhead"]).mean()/(b["cost"]-b["overhead"]).mean()
        if primary[c]["reliability_pass"] and primary[c]["NI_pass"] and uncosted_ratio <= .85 and primary[c]["saving_interval"]["upper"] < .15:
            kill4.append(c)
    delta_upper = g4["pooled_delta"].get("interval", {}).get("upper", np.inf)
    kills = dict(KILL1_selected_one_object=len(kill1) >= 3, KILL1_cells=kill1,
                 KILL2_mechanism=len(set(tight_brier) & set(generic_equal)) >= 3 and delta_upper <= 0,
                 KILL2_tight_brier_cells=tight_brier, KILL2_generic_equal_cells=generic_equal,
                 KILL2_equivalence_resolution="generic reliable and NI vs P; tight P incremental saving upper <5%",
                 KILL3_deterministic_candidate_family=sum(z["kill"] for z in family.values()) >= 3,
                 KILL3_detail=family, KILL3_mixture_family="NOT_CERTIFIED: deterministic candidate bounds do not cover arbitrary mixtures",
                 KILL4_overhead_removed_advantage=len(kill4) >= 3, KILL4_cells=kill4,
                 KILL4_scope="full receiver t_cum already includes CE/LDPC; checks marginal predictor overhead; leakage is G0 INVALID, not scientific kill")
    amortized, secondary = {}, {}
    for c, s in results.items():
        cp, cb = float(s["P"]["cost"].mean()), float(s["Bstar"]["cost"].mean())
        cal = seal["calibration_accounting"]
        shared = cal["shared_five_arm_collection_receiver_seconds"]
        fitsearch = cal["fit_seconds"]+sum(cal["search_seconds"].values())
        common = shared+seal["models"]["timing_seconds"]["full"]
        searches = seal["cells"][c]["class_search_seconds"]
        calp = common+searches["P"]
        calb = common+seal["models"]["timing_seconds"]["rescue"]+sum(searches[k] for k in searches if k != "P")
        for other in seal["cells"]:
            if other == c:
                continue
            times = seal["cells"][other]["class_search_seconds"]
            calp += times["P"]; calb += sum(times[k] for k in times if k != "P")
        amortized[c] = dict(shared_collection_seconds=shared, shared_fit_search_seconds=fitsearch,
                           Ccal_P=calp, Ccal_B=calb,
                           Mbreak=max(0., calp-calb)/(cb-cp) if cb > cp else None,
                           attribution="five-arm collection and full q fit shared once; P/B0–B5 search split; rescue fit to B*; generic/LOCO/per-cell work research-only",
                           effective_costs={str(M): dict(P=cp+calp/M, B=cb+calb/M) for M in (1000, 10000, 100000)},
                           effective_shared_costs={str(M): dict(P=cp+(shared+fitsearch)/M,
                                                               B=cb+(shared+fitsearch)/M) for M in (1000, 10000, 100000)})
        secondary[c] = {}
        for name, value in s.items():
            ratio = float(value["cost"].mean()/s["Bstar"]["cost"].mean())
            boot = L.bootstrap_mean(weights[c], value["cost"])/L.bootstrap_mean(weights[c], s["Bstar"]["cost"])
            secondary[c][name] = dict(FER=float(value["fail"].mean()), cost=float(value["cost"].mean()),
                                     R_vs_Bstar=ratio, saving_interval=L.interval(1-boot),
                                     NI_vs_Bstar=L.paired_ni(value["fail"], s["Bstar"]["fail"]),
                                     status="sealed secondary; does not replace primary")
    config = dict(seal_commit_attestation=args.seal_commit, seal_md5=args.seal_md5,
                  commit_verified_by="main session; CLI attestation only, no git call", B=L.BOOT_B,
                  bootstrap_seed=L.BOOT_SEED, alpha=L.ALPHA, G3_alpha=.05/3,
                  status="PASS_DEVELOPMENT" if coverage else "NO_PRIMARY_PASS", quiet_path=str(args.quiet),
                  scope="G5 open: known-support, one code/N/QPSK; no TCOM/deployment certificate")
    L.assert_unchanged(bindings)
    payload = dict(**L.provenance(config, inputs), G0=dict(test=g0, quiet=g0quiet),
                   G1_G2=primary, G2_coverage=dict(pass_gate=coverage, passed=passed, denominator=4, both_SNRs_required=True),
                   G3=g3, G4=g4, KILL=kills, calibration_amortization=amortized, secondary_sealed_winners=secondary,
                   G5="OPEN: needs support acquisition/second receiver/code/few-calibration transfer", wall_seconds=time.perf_counter()-started)
    L.write_json(args.out/"analysis.json", payload)
    md = ["# A' (b) TEST: sealed evaluation", "", f"_argv: `{json.dumps(payload['_argv'])}`", "",
          f"_config: `{json.dumps(config, sort_keys=True)}`", "", "Input md5s: `analysis.json` (including seal, rows/configs/load records).", "",
          "| cell | status | CP P / B | NI upper | R | bootstrap upper R | quiet |", "|---|---|---|---|---|---|---|"]
    for c, z in primary.items():
        md.append(f"| {c} | {z['status']} | {z.get('CP_upper_P')} / {z.get('CP_upper_B')} | {z.get('NI', {}).get('upper')} | {z.get('R')} | {z.get('R_interval', {}).get('upper')} | {z.get('quiet', {}).get('status')} |")
    md += ["", f"G2 development coverage: {coverage}; {len(passed)}/4 cells.", "",
           "G3 / G4 / KILL and every frozen secondary contrast: `analysis.json`.", "",
           "CP: iid Bernoulli coverage. Tango/cluster bootstrap/cluster-t: approximate. No universal scheduler theorem."]
    md += ["", "```json", json.dumps({k: payload[k] for k in ("_argv", "_config", "input_md5s", "code_md5s")}, indent=2), "```"]
    (args.out/"analysis.md").write_text("\n".join(md)+"\n")
    print(f"wrote {args.out/'analysis.json'}; coverage={coverage}", flush=True)


if __name__ == "__main__":
    main()
