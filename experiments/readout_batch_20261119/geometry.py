"""Post-hoc support and phase statistics from completed row archives."""

from collections import defaultdict

import numpy as np
from scipy.stats import mannwhitneyu

from common import interval, read_rows


RATIO = "ratio_sweep_20261118/out/main_v2_20261119"
CSTATE = "unified_cov_prospective_20261119/out/main_20261119"
DOUBLET = "doublet_conflict_20261119/out/main_20261119"
CSTATE_ARMS = ("C-hi", "C-lo")
PHASE_GROUPS = ("both two-atom", "CD-only two-atom", "U-only failure")


def format_ci(bounds, digits=3):
    return f"[{bounds[0]:.{digits}f}, {bounds[1]:.{digits}f}]"


def sample_totals(values, rng, draws):
    """Resample whole physical frames so paired rows move together."""
    return np.concatenate([
        values[rng.integers(len(values), size=(min(256, draws - start), len(values)))].sum(axis=1)
        for start in range(0, draws, 256)
    ])


def ratio_readout(root, rng, draws):
    arms = ("A2", "CODELAY")
    clusters = defaultdict(lambda: np.zeros(3, dtype=int))
    seen = set()
    for row in read_rows(root / RATIO, r"main_\d{2}\.jsonl\.gz"):
        key = row["frame"], row["rho"], row["R"]
        if key in seen:
            raise ValueError(f"Duplicate ratio row {key}")
        seen.add(key)
        tally = clusters[row["frame"]]
        if row["defined"]:
            tally[0] += 1
            for i, arm in enumerate(arms, start=1):
                pair = row["arms"][arm]["pair"]
                wins = pair["phantom_gain"] > pair["weak_gain"]
                if wins != pair["Q"]:
                    raise ValueError(f"Ratio score identity disagrees at {key}, {arm}")
                tally[i] += wins
    if len(seen) != 24000 or len(clusters) != 1000:
        raise ValueError("Incomplete ratio main archive: expected 1000 frames by 24 cells")
    values = np.array([clusters[frame] for frame in sorted(clusters)])
    n, *counts = values.sum(axis=0)
    sampled = sample_totals(values, rng, draws)
    estimates = {}
    lines = [
        f"{n:,} defined rows out of {len(seen):,} rows, pooled across both pilot fractions and all ratio settings. "
        f"The 95% percentile intervals resample {len(clusters):,} physical frames across all settings together.",
        "",
        "| Arm | Phantom gain > designated true-delay gain | Fraction [95% interval] |",
        "|---|---:|---:|",
    ]
    for i, (arm, k) in enumerate(zip(arms, counts, strict=True), start=1):
        point = float(k / n)
        bounds = interval(sampled[:, i] / sampled[:, 0])
        estimates[arm] = {"count": int(k), "fraction": point, "interval95": bounds}
        lines.append(f"| {arm} | {k:,}/{n:,} | {point:.3f} {format_ci(bounds)} |")
    a2, cd = (estimates[arm]["fraction"] for arm in arms)
    outcome = "Survives" if a2 >= .8 and cd <= .3 else "Does not survive"
    lines += ["", f"**{outcome}.** The rule requires A2 ≥ 0.80 and CODELAY ≤ 0.30."]
    return dict(
        source=f"`{RATIO}/main_??.jsonl.gz`",
        fields="`frame`, `rho`, `R`, `defined`, and `arms[arm].pair.{phantom_gain,weak_gain,Q}`. "
               "The archived `weak_gain` is the designated true-delay gain. The main shards are named `main_??`.",
        outcome=outcome, headline=f"A2 {a2:.1%}, CODELAY {cd:.1%}",
        report="\n".join(lines), rows=len(seen), defined=int(n), frames=len(clusters), arms=estimates,
    )


def propagation_readout(root, rng, draws):
    clusters = defaultdict(lambda: np.zeros(2, dtype=int))
    cumulative = np.zeros(2, dtype=int)
    round2_trials = np.zeros(2, dtype=int)
    seen = set()
    matched = designated = 0
    for entry in read_rows(root / CSTATE):
        if entry["leg"] != "cstate":
            continue
        key = tuple(entry["key"])
        if key in seen:
            raise ValueError(f"Duplicate CSTATE key {key}")
        seen.add(key)
        row = entry["row"]
        if not row["syndrome"]:
            continue
        hi, lo = (row["arms"][arm] for arm in CSTATE_ARMS)
        rounds = [len(arm["decision"]) for arm in (hi, lo)]
        census = [row["census"]["by_arm"][arm] for arm in CSTATE_ARMS]
        counts = np.array([arm["nonempty_scored_trials"] for arm in census])
        if any(item["scored_trials"] != count * 20600
               for item, count in zip(census, rounds, strict=True)):
            raise ValueError(f"CSTATE census does not match exchange trace length at {key}")
        cumulative += counts
        round2_trials += 20600 * (np.asarray(rounds) == 2)
        if rounds == [2, 2]:
            matched += 1
            change = counts[1] - counts[0]
            target = lo["first_edit_type"] == "existing_delay" and hi["first_edit_type"] != "existing_delay"
            designated += target
            clusters[row["frame"]] += (change, change if target else 0)
    if len(seen) != 6800:
        raise ValueError("Incomplete CSTATE main archive: expected 6800 CSTATE keys")
    values = np.array([clusters[frame] for frame in sorted(clusters)])
    net, contribution = values.sum(axis=0)
    if net <= 0:
        raise ValueError("R-C2 requires a positive net C-lo minus C-hi count")
    sampled = sample_totals(values, rng, draws)
    positive = sampled[:, 0] > 0
    net_ci = interval(sampled[:, 0])
    contribution_ci = interval(sampled[:, 1])
    share_ci = interval(sampled[positive, 1] / sampled[positive, 0])
    share = float(contribution / net)
    bound_lo = float((cumulative[1] - cumulative[0]) / round2_trials[1])
    bound_hi = float(cumulative[0] / round2_trials[0])
    outcome = "First-step phantom drives the gap" if share >= .80 else "Count bound only"
    lines = [
        f"Both arms reached round 2 on {matched:,} paired keys from {len(clusters):,} physical frames. "
        "Round 1 starts from the same support and scans the same candidate bank. The projector depends only "
        "on trial geometry, so the round-1 counts cancel exactly in the within-key difference. "
        "The archived census pools rounds and does not give the separate round-2 counts.",
        "",
        f"- C-lo minus C-hi had **{net:+,}** nonempty scored trials "
        f"[95% interval {net_ci[0]:+,.0f}, {net_ci[1]:+,.0f}].",
        f"- The {designated:,} keys where only C-lo added an atom at an existing delay in its first accepted edit "
        f"contributed **{contribution:+,}** trials [95% interval {contribution_ci[0]:+,.0f}, "
        f"{contribution_ci[1]:+,.0f}], or **{share:.1%}** of the net difference "
        f"[{share_ci[0]:.1%}, {share_ci[1]:.1%}].",
        f"- Across all round-2 keys for each arm, the archived counts imply at least {bound_lo:.1%} nonempty "
        f"trials for C-lo and at most {bound_hi:.1%} for C-hi. This uses {cumulative[1]:,} and "
        f"{cumulative[0]:,} cumulative counts and {round2_trials[1]:,} and {round2_trials[0]:,} round-2 trials.",
        "",
        f"**{outcome}.** The rule requires a contribution of at least 80%. The 95% percentile intervals resample "
        "physical frames jointly across keys. "
        f"The share excludes {int((~positive).sum())} bootstrap draws with a nonpositive net count.",
    ]
    return dict(
        source=f"`{CSTATE}/rows_shard*.jsonl`, `leg == 'cstate'`",
        fields="`key`, `row.{frame,syndrome}`, `row.arms[arm].{decision,first_edit_type}`, and "
               "`row.census.by_arm[arm].{nonempty_scored_trials,scored_trials}`. Two saved decisions "
               "identify a key reaching the second exchange round. The count includes all scored trials.",
        outcome=outcome, headline=f"{share:.1%} of {net:+,} trials",
        report="\n".join(lines), paired_keys=matched, frames=len(clusters), only_lo_existing_delay_keys=designated,
        net_count=int(net), net_count_interval95=net_ci, contribution=int(contribution),
        contribution_interval95=contribution_ci, share=share, share_interval95=share_ci,
        excluded_share_draws=int((~positive).sum()), all_keys_round2_C_lo_lower=bound_lo,
        all_keys_round2_C_hi_upper=bound_hi,
    )


def contrasts(rows, rng, draws):
    values = np.ma.masked_invalid(np.array(rows))
    observed = np.ma.median(values, axis=0).filled(np.nan)
    # These cohorts can overlap. Each sampled row keeps both memberships together.
    bootstrap = np.concatenate([
        np.ma.median(values[rng.integers(len(values), size=(min(256, draws - start), len(values)))],
                     axis=1).filled(np.nan)
        for start in range(0, draws, 256)
    ])
    comparisons = {}
    for i, label in enumerate(PHASE_GROUPS):
        data = values[:, i].compressed()
        finite = np.isfinite(bootstrap[:, i])
        estimate = dict(n=len(data), median=float(observed[i]) if len(data) else None,
                        interval95=interval(bootstrap[finite, i]) if len(data) else None)
        if i:
            ref = values[:, 0].compressed()
            lift = bootstrap[:, i] - bootstrap[:, 0]
            if len(data) and len(ref):
                p = float(mannwhitneyu(data, ref, alternative="two-sided").pvalue)
                point = float(observed[i] - observed[0])
                estimate.update(lift=point, lift_interval95=interval(lift[np.isfinite(lift)]), p=p,
                                overlap=int((~values.mask[:, 0] & ~values.mask[:, i]).sum()),
                                excluded_lift_draws=int((~np.isfinite(lift)).sum()), passes=point >= .10 and p <= .05)
            else:
                estimate.update(lift=None, lift_interval95=None, p=None, overlap=0,
                                excluded_lift_draws=draws, passes=False)
        comparisons[label] = estimate
    return comparisons


def phase_energy(phase, rng, draws):
    estimates = {}
    samples = {}
    for name in ("anti-phase", "in-phase"):
        values = np.array(phase[name])
        omitted, power = values.sum(axis=0)
        observed = float(omitted / power)
        bootstrap = sample_totals(values, rng, draws)
        samples[name] = bootstrap[:, 0] / bootstrap[:, 1]
        estimates[name] = dict(n=len(values), omitted=float(omitted), power=float(power), fraction=observed,
                               interval95=interval(samples[name]))
    diff = estimates["anti-phase"]["fraction"] - estimates["in-phase"]["fraction"]
    diff_ci = interval(samples["anti-phase"] - samples["in-phase"])
    return dict(groups=estimates, difference=diff, interval95=diff_ci, passes=bool(diff_ci[0] > 0))


def doublet_readout(root, rng, draws):
    data = defaultdict(list)
    differing_both = defaultdict(list)
    energy = defaultdict(lambda: defaultdict(list))
    seen = set()
    n_symbols = 1024  # Frozen backbone transform length used by the producer.
    for row in read_rows(root / DOUBLET, r"rows\.jsonl"):
        if row["frame"] in seen:
            raise ValueError(f"Duplicate doublet frame {row['frame']}")
        seen.add(row["frame"])
        truth = row["truth"]
        index_by_delay = {
            delay: [i for i, value in enumerate(truth["delays"]) if value == delay]
            for delay in (6, 22)
        }
        (delay,) = (delay for delay, (i, j) in index_by_delay.items()
                    if np.isclose(abs(truth["dopplers"][i] - truth["dopplers"][j]), .35))
        i, j = sorted(index_by_delay[delay], key=truth["dopplers"].__getitem__)
        delta = truth["dopplers"][j] - truth["dopplers"][i]
        g1, g2 = (complex(*truth["gains"][k]) for k in (i, j))
        aligned_g2 = np.exp(1j * np.pi * (n_symbols - 1) * delta / n_symbols) * g2
        contrast = float(abs(g1 - aligned_g2)**2 / (2 * (abs(g1)**2 + abs(g2)**2)))
        cd, u = (row["arms"][arm] for arm in ("CD", "U"))
        cd_two = cd["doublet_two_atoms"]["0.35"]
        u_two = u["doublet_two_atoms"]["0.35"]
        u_fails = u["info_errors"] > 0 and cd["info_errors"] == 0
        data[delay].append([contrast if flag else np.nan
                            for flag in (cd_two and u_two, cd_two and not u_two, u_fails)])
        differing_both[delay].append(cd["decision"] != u["decision"])
        (tap,) = (tap for tap in row["arms"]["F0"]["doublets"] if tap["separation"] == .35)
        if tap["delay"] != delay:
            raise ValueError(f"Doublet tap and truth disagree at frame {row['frame']}")
        if row["syndrome"] and tap["atoms"] == 1:
            phase_cos = (g1.conjugate() * aligned_g2).real / (abs(g1) * abs(g2))
            if phase_cos < -.5:
                energy[delay]["anti-phase"].append([tap["omitted"], tap["power"]])
            elif phase_cos > .5:
                energy[delay]["in-phase"].append([tap["omitted"], tap["power"]])
    if seen != set(range(1000, 1600)):
        raise ValueError("Incomplete doublet main archive: expected frames 1000–1599")
    if any(len(data[delay]) != 300 for delay in (6, 22)):
        raise ValueError("Unexpected doublet main stratum balance")

    lines = [
        "The two gains are ordered by increasing Doppler. At the 0.35-bin gap, the Dirichlet-kernel phase is "
        "`π(N−1)Δν/N` with `N=1024`, using the producer's positive Doppler convention. "
        "The same phase aligns the gains for contrast `c` and gives the frame-center phase cosine.",
        "",
        "| Delay | Cohort | n | Median c [95% interval] | Lift vs both [95% interval] | Mann–Whitney p | Rule |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    support, sensitivity, pooled_energy = {}, {}, {}
    for delay in (6, 22):
        support[delay] = contrasts(data[delay], rng, draws)
        for name, estimate in support[delay].items():
            median = (f"{estimate['median']:.3f} {format_ci(estimate['interval95'])}"
                      if estimate["median"] is not None else "undefined")
            if name == PHASE_GROUPS[0]:
                lift, p_text, rule = "—", "—", "—"
            elif estimate["p"] is None:
                lift, p_text, rule = "undefined", "undefined", "Unevaluable"
            else:
                lift = f"{estimate['lift']:+.3f} {format_ci(estimate['lift_interval95'])}"
                p_text = f"{estimate['p']:.4g}"
                rule = "Pass" if estimate["passes"] else "Fail"
            lines.append(f"| {delay} | {name} | {estimate['n']} | {median} | {lift} | {p_text} | {rule} |")
        pooled_energy[delay] = phase_energy(energy[delay], rng, draws)
        restricted = np.array(data[delay])
        restricted[~np.array(differing_both[delay]), 0] = np.nan
        sensitivity[delay] = contrasts(restricted, rng, draws)
    lines += ["", "Lift intervals jointly resample physical frames within each delay. The p-values use the "
              "specified Mann–Whitney statistic with a two-sided alternative. "
              "Groups with overlapping memberships give descriptive p-values because samples share frames.", ""]
    for delay, estimates in support.items():
        counts = [f"{name}: {estimates[name]['overlap']} shared, "
                  f"{estimates[name]['excluded_lift_draws']} undefined lift draws"
                  for name in PHASE_GROUPS[1:]]
        lines.append(f"- Delay {delay}, " + " | ".join(counts) + ".")
    lines += [
        "", "The primary contrast uses every both-two-atom frame, as stated in the batch brief. "
        "The source idea cited 179 such frames, counting only keys where the U and CD decisions differed. "
        "Restricting only the reference cohort to that source definition gives the following sensitivity readout.",
        "",
        "| Delay | Restricted reference n | CD-only lift [95% interval], p | U-only-failure lift [95% interval], p |",
        "|---:|---:|---:|---:|",
    ]
    for delay, estimates in sensitivity.items():
        entries = [
            f"{row['lift']:+.3f} {format_ci(row['lift_interval95'])}, {row['p']:.4g}"
            if row["p"] is not None else "undefined"
            for row in (estimates[group] for group in PHASE_GROUPS[1:])
        ]
        lines.append(f"| {delay} | {estimates[PHASE_GROUPS[0]]['n']} | {entries[0]} | {entries[1]} |")
    lines += [
        "", "Omitted-energy shares pool saved energy in each phase group among triggered F0 frames with "
        "exactly one atom at the 0.35-bin doublet delay. Their 95% intervals resample frames within each phase "
        "group and delay. Phase is at the frame center.",
        "",
        "| Delay | Anti-phase n | Anti-phase share [95% interval] | In-phase n | In-phase share [95% interval] "
        "| Difference [95% interval] | Rule |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for delay, estimate in pooled_energy.items():
        anti, in_phase = (estimate["groups"][name] for name in ("anti-phase", "in-phase"))
        rule = "Pass" if estimate["passes"] else "Fail"
        lines.append(f"| {delay} | {anti['n']} | {anti['fraction']:.3f} {format_ci(anti['interval95'])} | "
                     f"{in_phase['n']} | {in_phase['fraction']:.3f} {format_ci(in_phase['interval95'])} | "
                     f"{estimate['difference']:+.3f} {format_ci(estimate['interval95'])} | {rule} |")
    selective = all(estimates[name]["passes"] for estimates in support.values() for name in PHASE_GROUPS[1:])
    tolerance = all(entry["passes"] for entry in pooled_energy.values())
    selective_result = "survives" if selective else "does not survive"
    tolerance_result = "survives" if tolerance else "does not survive"
    outcome = f"Selective harm {selective_result}; phase explanation of tolerance {tolerance_result}"
    lines += ["", f"**{outcome}.** The selective-harm rule requires a lift ≥ 0.10 and p ≤ 0.05 in each "
              "within-delay comparison. The tolerance rule requires both within-delay lower bounds > 0."]
    deltas = [entry["difference"] for entry in pooled_energy.values()]
    failed = sum(not estimates[name]["passes"] for estimates in support.values() for name in PHASE_GROUPS[1:])
    return dict(
        source=f"`{DOUBLET}/rows.jsonl`, all 600 MIXED8 frames at 7 dB",
        fields="`truth.{delays,dopplers,gains}`, `arms.{CD,U}.{doublet_two_atoms,info_errors,decision}`, "
               "`syndrome`, and `arms.F0.doublets[].{separation,delay,atoms,omitted,power}`. "
               "The archive encodes each gain as [real, imag] and provides one row file.",
        outcome=outcome, headline=f"{4-failed}/4 contrast tests pass, energy lifts {deltas[0]:+.1%}/{deltas[1]:+.1%}",
        report="\n".join(lines), frames=len(seen), contrast_by_delay=support,
        reference_disagreement_sensitivity=sensitivity, phase_energy_by_delay=pooled_energy,
        selective_harm=selective, phase_explanation_of_tolerance=tolerance,
    )


def run(root, rng, draws):
    return {
        "R-C1": ratio_readout(root, rng, draws),
        "R-C2": propagation_readout(root, rng, draws),
        "R-E": doublet_readout(root, rng, draws),
    }
