"""Pre-registered statistical analysis, 36-pair simultaneous projection, and Markdown rendering."""
from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
P1_AGG_PATH = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'p1_agg.py'
EXPECTED_P1_AGG_MD5 = '047bd512a1c5c3bc437a334a54b075e7'

_p1_agg_md5 = hashlib.md5(P1_AGG_PATH.read_bytes()).hexdigest()
if _p1_agg_md5 != EXPECTED_P1_AGG_MD5:
    raise RuntimeError(f'Frozen p1_agg.py MD5 mismatch before import: {_p1_agg_md5} != {EXPECTED_P1_AGG_MD5}')

_spec = importlib.util.spec_from_file_location('hs_p1_agg', P1_AGG_PATH)
p1_agg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p1_agg)

SCENARIOS = ('U', 'G')
ALL_RHOS = (150, 200, 250, 300, 400, 500)
ALL_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
BOOT_DRAWS = 50_000
BOOT_SEED = 20261124
FAMILY_ALPHA = 0.05
PRIMARY_ALPHA = FAMILY_ALPHA / 3.0
EQUIV_MARGIN_DB = 0.5


class Bounds(NamedTuple):
    """Parallel lower/upper arrays; index 0 is the full-sample point estimate, 1: are bootstrap draws."""
    lower: np.ndarray
    upper: np.ndarray


def _difference(first: Bounds, second: Bounds) -> Bounds:
    return Bounds(first.lower - second.upper, first.upper - second.lower)


def _mean(bounds_list: list[Bounds]) -> Bounds:
    return Bounds(
        np.mean([b.lower for b in bounds_list], axis=0),
        np.mean([b.upper for b in bounds_list], axis=0),
    )


def _minimum(bounds_list: list[Bounds]) -> Bounds:
    return Bounds(
        np.min([b.lower for b in bounds_list], axis=0),
        np.min([b.upper for b in bounds_list], axis=0),
    )


def _nearest_rank(draws: np.ndarray, probability: float) -> float:
    n = len(draws)
    rank = min(n - 1, max(0, math.ceil(n * probability) - 1))
    return float(np.partition(draws, rank)[rank])


def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
    return (
        _nearest_rank(bounds.lower[1:], alpha / 2.0),
        _nearest_rank(bounds.upper[1:], 1.0 - alpha / 2.0),
    )


def _represent(value: float) -> Any:
    if np.isposinf(value):
        return '+inf'
    if np.isneginf(value):
        return '-inf'
    if np.isnan(value):
        raise FloatingPointError('NaN encountered in crossing bound')
    return float(value)


def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs_centi, dtype=float) / 100.0)
    return Bounds(
        np.where(status == p1_agg.LOW, -np.inf, x),
        np.where(status == p1_agg.HIGH, np.inf, x),
    )


def compute_crossings(
    errors_by_key: dict[tuple[str, int, int, int], dict[str, int]],
    arms: tuple[str, ...],
    rhos: tuple[int, ...],
    snrs: tuple[int, ...],
    frames: tuple[int, ...],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> tuple[dict[tuple[str, int, str], Bounds], dict[str, dict[str, Any]]]:
    """Compute censor-aware 1% FER crossings using one shared physical-frame bootstrap."""
    if not frames or len(frames) != len(set(frames)):
        raise ValueError('Frames must be non-empty and unique')
    snrs = tuple(sorted(snrs))
    expected = {
        (s, rho, snr, f)
        for s in SCENARIOS for rho in rhos for snr in snrs for f in frames
    }
    if errors_by_key.keys() != expected:
        raise ValueError(
            f'Key mismatch: missing={len(expected - errors_by_key.keys())}, '
            f'extra={len(errors_by_key.keys() - expected)}'
        )

    n = len(frames)
    rng = np.random.default_rng(boot_seed)
    # Chunked matrix multiply keeps memory bounded (~40 MB per 10k chunk)
    weights = rng.multinomial(n, np.full(n, 1.0 / n), size=boot_draws).astype(np.float64) / n

    crossings: dict[tuple[str, int, str], Bounds] = {}
    cells: dict[str, dict[str, Any]] = {}
    for s in SCENARIOS:
        for rho in rhos:
            cell_id = f'{s}_{rho}'
            cells[cell_id] = {}
            for arm in arms:
                failures = np.array(
                    [[errors_by_key[s, rho, snr, f][arm] > 0 for snr in snrs] for f in frames],
                    dtype=np.int8,
                )
                fer_pt = failures.mean(axis=0)
                pt = _crossing(fer_pt, n, snrs)
                dr = _crossing(weights @ failures, n, snrs)
                b = Bounds(
                    np.concatenate([pt.lower, dr.lower]),
                    np.concatenate([pt.upper, dr.upper]),
                )
                crossings[s, rho, arm] = b
                lo95, hi95 = _interval(b, 0.05)
                cells[cell_id][arm] = dict(
                    point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
                    ci95_db=[_represent(lo95), _represent(hi95)],
                    half_width_db=_represent((hi95 - lo95) / 2.0),
                    left_censored_draws=int(np.isneginf(b.lower[1:]).sum()),
                    right_censored_draws=int(np.isposinf(b.upper[1:]).sum()),
                    fer={str(snr): float(rate) for snr, rate in zip(snrs, fer_pt, strict=True)},
                )
    return crossings, cells


def scene_means(
    crossings: dict[tuple[str, int, str], Bounds],
    rhos: tuple[int, ...],
    arms: tuple[str, ...],
) -> dict[tuple[int, str], Bounds]:
    return {
        (rho, arm): _mean([crossings[s, rho, arm] for s in SCENARIOS])
        for rho in rhos for arm in arms
    }


def projected_best_diff(
    curves: dict[tuple[int, str], Bounds],
    arm_a: str,
    arm_b: str,
    rhos: tuple[int, ...],
    alpha: float,
) -> dict[str, Any]:
    """36-pair simultaneous confidence projection for min_a c_A(a) - min_b c_B(b).

    Uses the exact identity:
      min_a c_A(a) - min_b c_B(b) = min_a max_b (c_A(a) - c_B(b)) = max_b min_a (c_A(a) - c_B(b)).
    For all |R|^2 pairs (a, b), constructs simultaneous (1 - alpha) intervals [L(a,b), U(a,b)]
    with Bonferroni alpha_pair = alpha / |R|^2, then projects:
      L_proj = min_a max_b L(a,b),  U_proj = max_b min_a U(a,b).
    Also reports the paired per-draw bootstrap interval as a secondary precision readout.
    """
    m = len(rhos)
    alpha_pair = alpha / (m * m)
    L_mat = np.empty((m, m), dtype=float)
    U_mat = np.empty((m, m), dtype=float)
    for i, ra in enumerate(rhos):
        for j, rb in enumerate(rhos):
            diff_ab = _difference(curves[ra, arm_a], curves[rb, arm_b])
            lo, hi = _interval(diff_ab, alpha_pair)
            L_mat[i, j] = lo
            U_mat[i, j] = hi
    L_proj = float(np.min(np.max(L_mat, axis=1)))
    U_proj = float(np.max(np.min(U_mat, axis=0)))
    if L_proj > U_proj + 1e-12:
        raise AssertionError(f'Projected lower bound {L_proj} exceeds upper bound {U_proj}')

    min_a = _minimum([curves[r, arm_a] for r in rhos])
    min_b = _minimum([curves[r, arm_b] for r in rhos])
    per_draw = _difference(min_a, min_b)
    pd_lo, pd_hi = _interval(per_draw, alpha)
    censored_frac = float(np.mean(~(np.isfinite(per_draw.lower[1:]) & np.isfinite(per_draw.upper[1:]))))

    pt_lo = float(per_draw.lower[0])
    pt_hi = float(per_draw.upper[0])
    return dict(
        point_db=[_represent(pt_lo), _represent(pt_hi)],
        ci_projected_db=[_represent(L_proj), _represent(U_proj)],
        ci_per_draw_db=[_represent(pd_lo), _represent(pd_hi)],
        half_width_projected_db=_represent((U_proj - L_proj) / 2.0),
        half_width_per_draw_db=_represent((pd_hi - pd_lo) / 2.0),
        censored_draw_fraction=censored_frac,
        alpha=float(alpha),
        alpha_pair=float(alpha_pair),
        _raw=(pt_lo, pt_hi, L_proj, U_proj),
    )


def single_rho_diff(
    curves: dict[tuple[int, str], Bounds],
    arm_a: str,
    arm_b: str,
    rho: int,
    alpha: float,
) -> dict[str, Any]:
    diff = _difference(curves[rho, arm_a], curves[rho, arm_b])
    lo, hi = _interval(diff, alpha)
    censored_frac = float(np.mean(~(np.isfinite(diff.lower[1:]) & np.isfinite(diff.upper[1:]))))
    pt_lo, pt_hi = float(diff.lower[0]), float(diff.upper[0])
    return dict(
        rho_permille=int(rho),
        point_db=[_represent(pt_lo), _represent(pt_hi)],
        ci_db=[_represent(lo), _represent(hi)],
        half_width_db=_represent((hi - lo) / 2.0),
        censored_draw_fraction=censored_frac,
        alpha=float(alpha),
        _raw=(pt_lo, pt_hi, lo, hi),
    )


def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
    """Frozen mutually exclusive Q2 verdict table (HG vs CD; positive = CD better)."""
    if ci_lo > 0.0 and point_lo >= EQUIV_MARGIN_DB:
        label = 'CD_AHEAD'
    elif ci_lo > 0.0 and point_lo < EQUIV_MARGIN_DB:
        label = 'CD_SLIGHT'
    elif ci_hi < 0.0:
        label = 'HG_AHEAD'
    elif ci_lo <= 0.0 <= ci_hi and ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
        label = 'EQUIVALENT'
    else:
        label = 'INCONCLUSIVE'

    zero_dir = 'CD_better' if ci_lo > 0.0 else ('HG_better' if ci_hi < 0.0 else 'includes_zero')
    return dict(
        verdict=label,
        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
        zero_direction=zero_dir,
    )


def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
    """Frozen mutually exclusive Q3 verdict table (Z vs CD; positive = CD better)."""
    if ci_lo >= -EQUIV_MARGIN_DB and ci_hi <= EQUIV_MARGIN_DB:
        label = 'Z_EQUIVALENT'
    elif ci_lo > 0.0 and ci_hi > EQUIV_MARGIN_DB:
        label = 'CD_NEEDED'
    elif ci_hi < 0.0 and ci_lo < -EQUIV_MARGIN_DB:
        label = 'Z_BETTER'
    else:
        label = 'Z_INCONCLUSIVE'

    zero_dir = 'CD_better' if ci_lo > 0.0 else ('Z_better' if ci_hi < 0.0 else 'includes_zero')
    return dict(
        verdict=label,
        strictly_nonzero=bool(ci_lo > 0.0 or ci_hi < 0.0),
        strict_gt_0p5_db=bool(ci_lo > EQUIV_MARGIN_DB),
        strict_lt_neg0p5_db=bool(ci_hi < -EQUIV_MARGIN_DB),
        zero_direction=zero_dir,
    )


def _strip_raw(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k != '_raw'}


def _unpaired_optimum_sets(
    curves: dict[tuple[int, str], Bounds],
    arms: tuple[str, ...],
    rhos: tuple[int, ...],
    alpha: float,
) -> dict[str, Any]:
    """Descriptive unpaired Bonferroni rectangle optimum sets per arm (matching rho_sweep style)."""
    alpha_per = alpha / (len(arms) * len(rhos))
    rect = {(r, a): _interval(curves[r, a], alpha_per) for r in rhos for a in arms}
    compatible = {}
    point_argmin = {}
    for a in arms:
        min_upper = min(rect[r, a][1] for r in rhos)
        compatible[a] = [int(r) for r in rhos if rect[r, a][0] <= min_upper]
        # Point argmin on upper bound then lower bound (handles right-censoring cleanly)
        best_val = min((curves[r, a].upper[0], curves[r, a].lower[0]) for r in rhos)
        point_argmin[a] = [
            int(r) for r in rhos
            if math.isclose(curves[r, a].upper[0], best_val[0], rel_tol=0.0, abs_tol=1e-12)
            and math.isclose(curves[r, a].lower[0], best_val[1], rel_tol=0.0, abs_tol=1e-12)
        ]
    return dict(
        compatible_rho_permille=compatible,
        point_argmin_rho_permille=point_argmin,
        simultaneous_confidence=1.0 - alpha,
        crossing_bounds_db={
            str(r): {a: [_represent(x) for x in rect[r, a]] for a in arms}
            for r in rhos
        },
    )


def paired_rescue_summary(
    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
    rhos: tuple[int, ...],
    snrs: tuple[int, ...],
) -> dict[str, Any]:
    """Per (scenario, rho, snr) paired rescue breakdown on F0-triggered keys."""
    cells = {}
    totals_hg = dict(triggered=0, cd_only=0, hg_only=0, both=0, neither=0)
    totals_z = dict(triggered=0, cd_only=0, z_only=0, both=0, neither=0)
    for s in SCENARIOS:
        for rho in rhos:
            for snr in snrs:
                trig = [
                    r for k, r in full_rows.items()
                    if k[0] == s and k[1] == rho and k[2] == snr and r['triggered']
                ]
                cd_only = hg_only = both = neither = 0
                z_cd_only = z_only = z_both = z_neither = 0
                for r in trig:
                    cd_ok = r['arms']['CD']['errors'] == 0
                    hg_ok = r['arms']['HG']['errors'] == 0
                    z_ok = r['arms']['Z']['errors'] == 0
                    if cd_ok and hg_ok:
                        both += 1
                    elif cd_ok and not hg_ok:
                        cd_only += 1
                    elif not cd_ok and hg_ok:
                        hg_only += 1
                    else:
                        neither += 1
                    if cd_ok and z_ok:
                        z_both += 1
                    elif cd_ok and not z_ok:
                        z_cd_only += 1
                    elif not cd_ok and z_ok:
                        z_only += 1
                    else:
                        z_neither += 1
                cells[f'{s}/{rho}/{snr}'] = dict(
                    triggered=len(trig),
                    hg_vs_cd=dict(cd_only=cd_only, hg_only=hg_only, both=both, neither=neither),
                    z_vs_cd=dict(cd_only=z_cd_only, z_only=z_only, both=z_both, neither=z_neither),
                )
                totals_hg['triggered'] += len(trig)
                totals_hg['cd_only'] += cd_only
                totals_hg['hg_only'] += hg_only
                totals_hg['both'] += both
                totals_hg['neither'] += neither
                totals_z['triggered'] += len(trig)
                totals_z['cd_only'] += z_cd_only
                totals_z['z_only'] += z_only
                totals_z['both'] += z_both
                totals_z['neither'] += z_neither
    return dict(totals_hg_vs_cd=totals_hg, totals_z_vs_cd=totals_z, by_cell=cells)


def pass2_and_support_summary(triggered_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize HG pass-1 early stop, pass-2 net rescues/degradations, and support recovery."""
    n = len(triggered_rows)
    early_stop = 0
    ran_pass2 = 0
    p2_rescued = 0
    p2_fer_harmed = 0
    p2_bit_improved = 0
    p2_bit_worsened = 0
    p2_still_failed = 0
    match_acc: dict[str, list[tuple[int, int, float, float, float]]] = {
        'HG1_omp': [], 'HG1_refined': [], 'HG_final_refined': [],
        'HG_pass2_subset_p1_refined': [], 'HG_pass2_subset_p2_refined': [],
        'CD_final_refined': [], 'Z_final_refined': [],
    }

    def _push(label: str, rec: dict[str, Any] | None):
        if rec is None:
            return
        mp = float(rec.get('matched_power', rec['matched_power_frac']))
        tp = float(rec.get('total_power', 1.0))
        match_acc[label].append((
            int(rec['matched_count']),
            int(rec['total_true']),
            float(rec['matched_power_frac']),
            mp,
            tp,
        ))

    for r in triggered_rows:
        hg = r['arms']['HG']
        hg1 = r['arms']['HG1']
        passes = int(hg['passes_used'])
        if passes == 1:
            early_stop += 1
        else:
            ran_pass2 += 1
            e1, e2 = int(hg1['errors']), int(hg['errors'])
            if e1 > 0 and e2 == 0:
                p2_rescued += 1
            elif e1 == 0 and e2 > 0:
                p2_fer_harmed += 1
            if e2 < e1:
                p2_bit_improved += 1
            elif e2 > e1:
                p2_bit_worsened += 1
            if e2 > 0:
                p2_still_failed += 1
            _push('HG_pass2_subset_p1_refined', hg1.get('match_refined'))
            _push('HG_pass2_subset_p2_refined', hg.get('match_refined'))

        _push('HG1_omp', hg1.get('match_omp'))
        _push('HG1_refined', hg1.get('match_refined'))
        _push('HG_final_refined', hg.get('match_refined'))
        _push('CD_final_refined', r['arms']['CD'].get('match_refined'))
        _push('Z_final_refined', r['arms']['Z'].get('match_refined'))

    support = {}
    for label, vals in match_acc.items():
        if not vals:
            continue
        mc = sum(v[0] for v in vals)
        tt = sum(v[1] for v in vals)
        pw = [v[2] for v in vals]
        sum_mp = sum(v[3] for v in vals)
        sum_tp = sum(v[4] for v in vals)
        support[label] = dict(
            keys=len(vals),
            matched_paths=mc,
            total_true_paths=tt,
            path_recall=mc / tt if tt > 0 else 0.0,
            pooled_matched_power_frac=sum_mp / sum_tp if sum_tp > 0 else 0.0,
            mean_matched_power_frac=float(np.mean(pw)),
            median_matched_power_frac=float(np.median(pw)),
        )
    return dict(
        triggered_keys=n,
        pass1_early_stop=early_stop,
        pass1_early_stop_rate=early_stop / n if n > 0 else 0.0,
        ran_pass2=ran_pass2,
        pass2_rescued=p2_rescued,
        pass2_fer_harmed=p2_fer_harmed,
        pass2_net_rescued=p2_rescued - p2_fer_harmed,
        pass2_bit_improved=p2_bit_improved,
        pass2_bit_worsened=p2_bit_worsened,
        pass2_still_failed=p2_still_failed,
        support_recovery=support,
    )


def analyze(
    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
    arms: tuple[str, ...],
    rhos: tuple[int, ...],
    snrs: tuple[int, ...],
    frames: tuple[int, ...],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Run complete pre-registered primary verdicts (Q1/Q2/Q3) and all secondary readouts."""
    errors_by_key = {
        k: {arm: int(r['arms'][arm]['errors']) for arm in arms}
        for k, r in full_rows.items()
    }
    crossings, cells = compute_crossings(
        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
    )
    pooled = scene_means(crossings, rhos, arms)

    # Primary tests (Bonferroni alpha = 0.05 / 3)
    q1 = single_rho_diff(pooled, 'HG', 'CD', 300, PRIMARY_ALPHA)
    q2 = projected_best_diff(pooled, 'HG', 'CD', rhos, PRIMARY_ALPHA)
    q3 = projected_best_diff(pooled, 'Z', 'CD', rhos, PRIMARY_ALPHA)

    q2_v = verdict_q2(*q2['_raw'])
    q3_v = verdict_q3(q3['_raw'][2], q3['_raw'][3])

    primary = dict(
        Q1=dict(**_strip_raw(q1), note='consistency readout at fixed rho=0.30'),
        Q2=dict(**_strip_raw(q2), **q2_v),
        Q3=dict(**_strip_raw(q3), **q3_v),
    )

    # Per-scenario Q1/Q2/Q3
    by_scenario = {}
    for s in SCENARIOS:
        sc = {(rho, arm): crossings[s, rho, arm] for rho in rhos for arm in arms}
        sq1 = single_rho_diff(sc, 'HG', 'CD', 300, PRIMARY_ALPHA)
        sq2 = projected_best_diff(sc, 'HG', 'CD', rhos, PRIMARY_ALPHA)
        sq3 = projected_best_diff(sc, 'Z', 'CD', rhos, PRIMARY_ALPHA)
        by_scenario[s] = dict(
            Q1=_strip_raw(sq1),
            Q2=dict(**_strip_raw(sq2), **verdict_q2(*sq2['_raw'])),
            Q3=dict(**_strip_raw(sq3), **verdict_q3(sq3['_raw'][2], sq3['_raw'][3])),
        )

    # Secondary arm contrasts (95% simultaneous projection)
    secondary_contrasts = {}
    for label, a, b in (
        ('HG1_minus_HG', 'HG1', 'HG'),
        ('HG1_minus_CD', 'HG1', 'CD'),
        ('HG_minus_F0', 'HG', 'F0'),
        ('Z_minus_F0', 'Z', 'F0'),
        ('HGint_minus_HG', 'HGint', 'HG'),
        ('HGint_minus_CD', 'HGint', 'CD'),
    ):
        if a in arms and b in arms:
            res = projected_best_diff(pooled, a, b, rhos, 0.05)
            at30 = single_rho_diff(pooled, a, b, 300, 0.05)
            secondary_contrasts[label] = dict(best=_strip_raw(res), rho_300=_strip_raw(at30))

    # Per-rho paired HG - CD and Z - CD (95%)
    per_rho_diff = {}
    for rho in rhos:
        per_rho_diff[str(rho)] = dict(
            HG_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG', 'CD', rho, 0.05)),
            Z_minus_CD=_strip_raw(single_rho_diff(pooled, 'Z', 'CD', rho, 0.05)),
            HG1_minus_CD=_strip_raw(single_rho_diff(pooled, 'HG1', 'CD', rho, 0.05)),
            **({'HGint_minus_CD': _strip_raw(single_rho_diff(pooled, 'HGint', 'CD', rho, 0.05))}
               if 'HGint' in arms else {}),
        )

    # Scene-averaged crossings per (rho, arm)
    pooled_crossings = {}
    for rho in rhos:
        pooled_crossings[str(rho)] = {}
        for arm in arms:
            b = pooled[rho, arm]
            lo95, hi95 = _interval(b, 0.05)
            pooled_crossings[str(rho)][arm] = dict(
                point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
                ci95_db=[_represent(lo95), _represent(hi95)],
            )

    triggered_rows = [r for r in full_rows.values() if r['triggered']]
    return dict(
        family_alpha=FAMILY_ALPHA,
        primary_alpha=PRIMARY_ALPHA,
        equiv_margin_db=EQUIV_MARGIN_DB,
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary=primary,
        by_scenario=by_scenario,
        secondary_contrasts=secondary_contrasts,
        per_rho_diff=per_rho_diff,
        pooled_crossings=pooled_crossings,
        optimum_sets=_unpaired_optimum_sets(pooled, arms, rhos, PRIMARY_ALPHA),
        paired_rescues=paired_rescue_summary(full_rows, rhos, snrs),
        pass2_and_support=pass2_and_support_summary(triggered_rows),
        crossings=cells,
    )


def _fmt_pt(pt: list[Any]) -> str:
    if pt[0] == pt[1]:
        return f'{pt[0]:.4f}' if isinstance(pt[0], float) else str(pt[0])
    a = f'{pt[0]:.4f}' if isinstance(pt[0], float) else str(pt[0])
    b = f'{pt[1]:.4f}' if isinstance(pt[1], float) else str(pt[1])
    return f'[{a}, {b}]'


def _fmt_ci(ci: list[Any]) -> str:
    a = f'{ci[0]:.4f}' if isinstance(ci[0], float) else str(ci[0])
    b = f'{ci[1]:.4f}' if isinstance(ci[1], float) else str(ci[1])
    return f'[{a}, {b}]'


def render_results_md(summary: dict[str, Any]) -> str:
    """Render concise, audit-friendly RESULTS.md from summary.json payload."""
    a = summary['analysis']
    p = a['primary']
    n_rhos = len(summary['_config']['retained_rhos'])
    grid_scope = 'full 6-rho grid' if n_rhos == 6 else f'REDUCED {n_rhos}-rho grid ({summary["_config"]["retained_rhos"]})'
    lines = [
        '# Huang-2010-style Steelman Experiment Results',
        '',
        f"- Keys: **{summary['_config']['total_keys']}** ({summary['_config']['triggered_keys']} archived F0 triggers across 400 physical frames 5400–5799; {grid_scope})",
        f"- HG OMP recipe: `{summary['_config']['hg_recipe']}`, max passes: `{summary['_config']['max_passes']}`, arms: `{summary['_config']['arms']}`",
        f"- Main CPU: **{summary['runtime']['main_core_hours']:.4f} core-hours** (wall {summary['runtime']['main_wall_seconds']:.1f} s)",
        f"- Bootstrap: {a['boot_draws']:,} paired physical-frame draws (seed {a['boot_seed']}); Bonferroni α = 0.05/3 (98.33% CIs); Q2/Q3 use {n_rhos**2}-pair simultaneous projection.",
        '',
        '## Primary Verdicts (Pre-registered)',
        '',
        '| Contrast | Point (dB) | 98.33% Projected CI (dB) | 98.33% Per-draw CI (dB) | Verdict | Notes |',
        '|---|---|---|---|---|---|',
        f"| Q1: HG(.30) − CD(.30) | {_fmt_pt(p['Q1']['point_db'])} | {_fmt_ci(p['Q1']['ci_db'])} | — | consistency | fixed ρ=0.30 |",
        f"| Q2: min HG − min CD | {_fmt_pt(p['Q2']['point_db'])} | {_fmt_ci(p['Q2']['ci_projected_db'])} | {_fmt_ci(p['Q2']['ci_per_draw_db'])} | **{p['Q2']['verdict']}** | dir={p['Q2']['zero_direction']}, L>0.5={p['Q2']['strict_gt_0p5_db']} |",
        f"| Q3: min Z − min CD | {_fmt_pt(p['Q3']['point_db'])} | {_fmt_ci(p['Q3']['ci_projected_db'])} | {_fmt_ci(p['Q3']['ci_per_draw_db'])} | **{p['Q3']['verdict']}** | dir={p['Q3']['zero_direction']}, nonzero={p['Q3']['strictly_nonzero']} |",
        '',
        '## Per-Scenario Primary Contrasts',
        '',
        '| Scenario | Q1 (dB) | Q2 (dB) / Verdict | Q3 (dB) / Verdict |',
        '|---|---|---|---|',
    ]
    for s in SCENARIOS:
        bs = a['by_scenario'][s]
        lines.append(
            f"| {s} | {_fmt_pt(bs['Q1']['point_db'])} {_fmt_ci(bs['Q1']['ci_db'])} "
            f"| {_fmt_pt(bs['Q2']['point_db'])} {_fmt_ci(bs['Q2']['ci_projected_db'])} ({bs['Q2']['verdict']}) "
            f"| {_fmt_pt(bs['Q3']['point_db'])} {_fmt_ci(bs['Q3']['ci_projected_db'])} ({bs['Q3']['verdict']}) |"
        )

    arms = summary['_config']['arms']
    lines.extend([
        '',
        '## Scene-Averaged 1% FER Crossings (dB, Point and 95% CI)',
        '',
        '| ρ | ' + ' | '.join(arms) + ' |',
        '|---|' + '---|' * len(arms),
    ])
    for rho_str, row in a['pooled_crossings'].items():
        rho_f = int(rho_str) / 1000.0
        vals = [f"{_fmt_pt(row[arm]['point_db'])} {_fmt_ci(row[arm]['ci95_db'])}" for arm in arms]
        lines.append(f'| {rho_f:.2f} | ' + ' | '.join(vals) + ' |')

    lines.extend([
        '',
        '## Secondary Contrasts (95% Projected CI, dB)',
        '',
        '| Contrast | Best-vs-Best Point / 95% Projected CI | Fixed ρ=0.30 Point / 95% CI |',
        '|---|---|---|',
    ])
    for label, v in a['secondary_contrasts'].items():
        lines.append(
            f"| {label} | {_fmt_pt(v['best']['point_db'])} {_fmt_ci(v['best']['ci_projected_db'])} "
            f"| {_fmt_pt(v['rho_300']['point_db'])} {_fmt_ci(v['rho_300']['ci_db'])} |"
        )

    pr = a['paired_rescues']
    ps = a['pass2_and_support']
    lines.extend([
        '',
        '## Paired Rescues & HG Pass-2 Diagnostics',
        '',
        f"- HG vs CD on {pr['totals_hg_vs_cd']['triggered']} triggers: CD_only={pr['totals_hg_vs_cd']['cd_only']}, HG_only={pr['totals_hg_vs_cd']['hg_only']}, both={pr['totals_hg_vs_cd']['both']}, neither={pr['totals_hg_vs_cd']['neither']}",
        f"- Z vs CD on {pr['totals_z_vs_cd']['triggered']} triggers: CD_only={pr['totals_z_vs_cd']['cd_only']}, Z_only={pr['totals_z_vs_cd']['z_only']}, both={pr['totals_z_vs_cd']['both']}, neither={pr['totals_z_vs_cd']['neither']}",
        f"- HG pass-1 early stop: {ps['pass1_early_stop']}/{ps['triggered_keys']} ({100*ps['pass1_early_stop_rate']:.2f}%)",
        f"- HG pass-2 ran: {ps['ran_pass2']}, rescued: {ps['pass2_rescued']}, FER harmed: {ps['pass2_fer_harmed']}, bit-improved: {ps['pass2_bit_improved']}, bit-worsened: {ps['pass2_bit_worsened']}, still failed: {ps['pass2_still_failed']}",
        '',
        '## Support Recovery on Triggered Keys (1-to-1 Match: exact delay & |Δk| ≤ 0.5)',
        '',
        '| Stage / Arm | Keys | Path Recall | Pooled Power Frac | Mean Power Frac | Median Power Frac |',
        '|---|---:|---:|---:|---:|---:|',
    ])
    for label, st in ps['support_recovery'].items():
        lines.append(
            f"| {label} | {st['keys']} | {100*st['path_recall']:.2f}% ({st['matched_paths']}/{st['total_true_paths']}) "
            f"| {100*st['pooled_matched_power_frac']:.2f}% | {100*st['mean_matched_power_frac']:.2f}% | {100*st['median_matched_power_frac']:.2f}% |"
        )

    if summary.get('timing'):
        t = summary['timing']
        lines.extend([
            '',
            '## Quiet Single-Core Per-Trigger Runtime Panel (ρ=0.30, 5.0 dB, 100 Triggered Keys)',
            '',
            f"- CPU pinned: `{t['cpu']['idle_cpu']}` (util {t['cpu']['measured_utilization_pct']:.1f}%), shared F0 median: `{1000*t['f0']['median']:.2f} ms`",
            '',
            '| Arm | Mean (ms) | Median (ms) | p95 (ms) | Ratio of Means vs CD | Median Paired Ratio vs CD |',
            '|---|---:|---:|---:|---:|---:|',
        ])
        for arm, lat in t['branches'].items():
            rel = t['relative_to_cd'].get(arm)
            rm = f"{rel['ratio_of_means']:.3f}×" if rel else '1.000×'
            mr = f"{rel['median_paired_ratio']:.3f}×" if rel else '1.000×'
            lines.append(
                f"| {arm} | {1000*lat['mean']:.2f} | {1000*lat['median']:.2f} | {1000*lat['p95']:.2f} | {rm} | {mr} |"
            )

    return '\n'.join(lines) + '\n'
