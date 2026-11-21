"""TRAIN fitting + CAL-only selection/seal. No TEST input accepted.

DRYRUN example (TRAIN namespace only; never writes a scientific seal):
 python -B c1apb_stage1.py --dry-run --out /data/guoyikun/tmp/c1apb_dryrun
Real invocation requires authority file hashes supplied by main session.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

import numpy as np
import c1apb_lib as L


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train6", type=Path, default=L.HERE/"out/c1esc")
    p.add_argument("--train8", type=Path, default=L.HERE/"out/c1apb_train8")
    p.add_argument("--cal", type=Path, default=L.HERE/"out/c1apb_cal")
    p.add_argument("--shuffle-anchor-dir", type=Path,
                   help="Sonnet's saved OLD-namespace shuffled E10/E0 smoke rows+configs; required for real seal")
    p.add_argument("--old-config-root", type=Path, default=L.HERE/"out")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--manifest-md5")
    p.add_argument("--protocol-md5")
    p.add_argument("--mchecks", type=int, default=1026,
                   help="frozen LDPC H row count; must match code metadata (unit check verifies)")
    return p.parse_args(argv)


def select_cell(pair, models, overhead):
    o, y = pair
    cache = L.qcache(o, models["pooled"]["full"], models["pooled"]["rescue"])
    class_times = {}
    rec = L.evaluate_candidates(o, y, cache, overhead, class_times)
    ell = L.CELLS[o.cell][2]
    margin = 1.645*math.sqrt(ell*(1-ell)/600)
    limit = ell-margin
    choices = {c: L.hull_select(rec[c], limit) for c in L.CLASSES}
    choices["Bstar"] = L.hull_select([r for c in L.CLASSES if c != "P" for r in rec[c]], limit)
    choices["P_escalation_only"] = L.hull_select([r for r in rec["P"] if r["policy"]["tg"] == 1.], limit)
    choices["P_giveup_only"] = L.hull_select([r for r in rec["P"] if r["policy"]["te"] == 1.], limit)
    # Same controlled generic state ablation: generic q in B4; never primary rescue.
    generic_cache = L.qcache(o, models["pooled"]["generic"])
    grecords = []
    for p in L.candidates("B4"):
        s = L.score(o, y, L.replay(o, p, generic_cache, overhead))
        grecords.append(dict(policy=p, fer=float(s["fail"].mean()), cost=float(s["cost"].mean()),
                             queries=float(s["queries"].mean())))
    choices["generic_B4"] = L.hull_select(grecords, limit)
    actual = {}
    for c, mix in choices.items():
        if mix is not None:
            usecache = generic_cache if c == "generic_B4" else cache
            value = L.eval_mix(o, y, mix, usecache, overhead)
            actual[c] = dict(fer=float(value["fail"].mean()), cost=float(value["cost"].mean()),
                             mean_queries=float(value["queries"].mean()),
                             mixture_allocations=[int(sum(L.mixture_u(o.frames, L.CELLS[o.cell][1]) < mix["weights"][0])),
                                                  int(sum(L.mixture_u(o.frames, L.CELLS[o.cell][1]) >= mix["weights"][0]))]
                             if len(mix["policies"]) == 2 else [len(o.frames)])
    operable = choices["P"] is not None and choices["Bstar"] is not None
    planning = dict(n_c=4000, n_req=4000, power_capped=False, q_cal=None, q_plan=None,
                    reason="nonoperable CAL; diagnostic sample only")
    if operable:
        fp = L.eval_mix(o, y, choices["P"], cache, overhead)["fail"]
        fb = L.eval_mix(o, y, choices["Bstar"], cache, overhead)["fail"]
        planning = L.plan_n(fp, fb)
    return dict(ell=ell, margin=margin, cal_limit=limit, operable=operable,
                choices=choices, actual_cal=actual, planning=planning,
                class_search_seconds=class_times,
                candidate_counts={c: len(v) for c, v in rec.items()},
                # Whole candidate family is sealed BEFORE TEST, enabling the
                # simultaneous conservative family KILL audit without reselection.
                candidates=rec, generic_candidates=grecords)


def main(argv=None):
    args = parse_args(argv)
    started = time.perf_counter()
    out = args.out.resolve()
    if args.mchecks != L.MCHECKS:
        raise ValueError("H row count must equal1026 for frozen code hash")
    if args.dry_run and "seal" in out.parts:
        raise ValueError("DRYRUN cannot write any seal directory")
    if not args.dry_run:
        if not args.manifest_md5 or not args.protocol_md5:
            raise ValueError("real stage1 requires --manifest-md5 and --protocol-md5")
        if (out/"seal.json").exists():
            raise FileExistsError("existing seal: refuse overwrite")
        if args.shuffle_anchor_dir is None:
            raise ValueError("real seal requires --shuffle-anchor-dir: manifest shuffle-vs-old closure evidence")
    inputs = L.audit_freshness(args.old_config_root)
    train6, ff, g0train = L.load_cells([args.train6], ("C1", "C2"), range(600), L.OLD, args.mchecks)
    inputs += ff
    if args.dry_run:
        train = {c: L.subset(v, v[0].frames < 300) for c, v in train6.items()}
        cal = {c: L.subset(v, v[0].frames >= 300) for c, v in train6.items()}
        g0cal = {c: dict(label="DRYRUN TRAIN holdout", frames=300, cost_scope="old contended rows; screening only") for c in cal}
        label = "DRYRUN"
        closure = dict(status="NOT_APPLICABLE_DRYRUN", reason="old stored TRAIN; no new shuffled6.5 anchors")
    else:
        closure, ff = L.check_shuffle_anchors(args.train6, args.shuffle_anchor_dir)
        inputs += ff
        train8, ff, report = L.load_cells([args.train8], ("C3", "C4"), range(600), L.OLD, args.mchecks,
                                         shuffled=True, shards=64)
        inputs += ff; g0train.update(report)
        train = dict(train6, **train8)
        cal, ff, g0cal = L.load_cells([args.cal], tuple(L.CELLS), range(600), L.NEW,
                                     args.mchecks, shuffled=True, shards=64)
        inputs += ff
        label = "SEALED_CAL"
        if len({r["context_signature"] for r in list(g0train.values())+list(g0cal.values())}) != 1:
            raise ValueError("TRAIN/CAL numerical kernel or prior changed")
    bindings = dict(L.snapshot(inputs), **L.code_md5s())
    print(f"{label}: G0 pass; fit pooled/full/generic/rescue + LOCO + per-cell", flush=True)
    fitstart = time.perf_counter()
    models = L.fit_models(train)
    fit_seconds = time.perf_counter()-fitstart
    overhead = L.measure_overhead(next(iter(train.values()))[0], models["pooled"]["full"], models["pooled"]["rescue"])
    cells, search_seconds = {}, {}
    for c, pair in cal.items():
        t = time.perf_counter()
        cells[c] = select_cell(pair, models, overhead)
        search_seconds[c] = time.perf_counter()-t
        print(f"{label} {c}: operable={cells[c]['operable']} n={cells[c]['planning']['n_c']} cal={cells[c]['actual_cal'].get('P')}", flush=True)
    configuration = dict(label=label, frozen_manifest="aprime-b-manifest-20261013.md INCLUDING A1/B5 and A2/matched quiet subset",
                         manifest_md5=args.manifest_md5, protocol_md5=args.protocol_md5,
                         mchecks=args.mchecks, N=L.N, cells=L.CELLS, ridge_grid=L.RIDGES,
                         objective="mean weighted CE + lambda/2 ||beta||²; intercept unpenalized",
                         CV="TRAIN frame mod5; cells/frame equal weights; tie stronger lambda",
                         mixture="SeedSequence(little-endian entropy words + [frame,L,int.from_bytes(b'mix','little')])",
                         thresholds=dict(tau_e=L.TAUE, tau_g=L.TAUG, kappa=L.KAPPAS, tau_rescue=L.TAUR),
                         bootstrap=dict(B=L.BOOT_B, seed=L.BOOT_SEED, block="shard", scheme="hierarchical block/frame, availability stratified, shared weights"),
                         family_kill="simultaneous Bonferroni CP/paired Tango and shard-cluster t bounds; approximate cost coverage",
                         alpha=L.ALPHA, G3_alpha=.05/3, amendments=["A1", "A2"],
                         quiet_comparison="R_quiet vs R_main on same first200 TEST frames; full TEST R separately reported",
                         authority_hash_scope="supplied by main session; no git read or commit verification",
                         gate="main session reviews+commits seal BEFORE TEST generation")
    L.assert_unchanged(bindings)
    payload = dict(**L.provenance(configuration, inputs), created_utc=datetime.now(timezone.utc).isoformat(),
                   label=label, cells=cells, models=models, overhead_seconds=overhead,
                   train_quintile_cuts=L.quintile_cuts(train, models["pooled"]["full"]),
                   G0=dict(train=g0train, cal=g0cal, shuffle_vs_old=closure,
                           old_configs_checked=len(L.audit_freshness(args.old_config_root))),
                   calibration_accounting=dict(shared_five_arm_collection_receiver_seconds=float(sum(o.tcum[:, :, -1].sum() for o, _ in train.values())+sum(o.tcum[:, :, -1].sum() for o, _ in cal.values())),
                                               fit_seconds=fit_seconds, search_seconds=search_seconds,
                                               attribution="collection shared by P/B*: count once; pooled fit timing and per-class search timing stored separately; generic/LOCO/per-cell are research-only"),
                   wall_seconds=time.perf_counter()-started,
                   scope="known/genie delays; one LDPC/N/QPSK; no TCOM/deployment certificate")
    name = "dryrun.json" if args.dry_run else "seal.json"
    L.write_json(out/name, payload)
    md = [f"# {label}: A' (b)", "", f"_argv: `{json.dumps(payload['_argv'])}`", "",
          f"_config: `{json.dumps(configuration, sort_keys=True)}`", "",
          f"Input md5s + coefficients/standardisation/CV/candidates: `{name}`.", "",
          "| cell | operable | CAL P FER / cost | CAL B* FER / cost | n_c | cap |", "|---|---|---|---|---|---|"]
    for c, z in cells.items():
        md.append(f"| {c} | {z['operable']} | {z['actual_cal'].get('P')} | {z['actual_cal'].get('Bstar')} | {z['planning']['n_c']} | {z['planning']['power_capped']} |")
    md += ["", "DRYRUN: TRAIN 0–299 fit / 300–599 selection; denominator600 margin retained; no scientific gate."
           if args.dry_run else "Main must review+commit seal BEFORE TEST generation; stage2 requires declared commit + seal MD5.",
           "", "No TEST read. No receiver run. No git command."]
    md += ["", "```json", json.dumps({k: payload[k] for k in ("_argv", "_config", "input_md5s", "code_md5s")}, indent=2), "```"]
    (out/("dryrun.md" if args.dry_run else "seal.md")).write_text("\n".join(md)+"\n")
    print(f"{label} wrote {out/name}; seconds={payload['wall_seconds']:.1f}", flush=True)


if __name__ == "__main__":
    main()
