"""Stage A8 (STAGEA8_PROTOCOL.md): full-frame 1% FER test of truth-free global semi-blind Doppler (`SBGdop`) vs `CD2`.

Directly imports `stageA6` (one_arm_nu, archive loaders) and `stageA7` (prepare_fast_geom, estimate_sb_global)
with zero duplicated math or hyperparameter changes.
Evaluates `SBGdop` on Stage A6 frames 41000-41399 (true delays) paired against verified frozen archives
(`CD2`, `SBdop`, `PWdop`, `s050`, `s100`, `ldop`, `full`).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import sys
import time
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
HUANG_DIR = EXP / 'huang_steelman_20261124'
SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HUANG_DIR))
sys.path.insert(0, str(SAMEFRAME_HG_DIR))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402
import sameframe as sf  # noqa: E402
import stageA6  # noqa: E402
import stageA7  # noqa: E402

FRAMES = stageA6.FRAMES
SCENARIOS = stageA6.SCENARIOS
RHOS = stageA6.RHOS
CANDIDATE_SNRS: tuple[tuple[int, ...], ...] = (
    (300, 400, 450, 500),
    (300, 400, 450),
)
FULL_SNRS = CANDIDATE_SNRS[0]

BOOT_DRAWS = 2000
BOOT_SEED = 20261125
GO_THRESH_DB = 0.5
STOP_REF_DB = 0.3
OUTLIER_THRESH = 0.25

WORKERS = 32
BUDGET_CAP_HOURS = 8.20
BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.15
BUDGET_EXIT_CODE = 124
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100

OWN_FILES = ('STAGEA8_PROTOCOL.md', 'stageA8.py', 'test_stageA8.py', 'stageA8_launch.sh')
PINNED_STAGEA7_MD5 = '1d6d6021d0e2bf36f1a368e8cc4e687a'


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_pinned_code() -> dict[str, str]:
    out = stageA7.verify_pinned_code()
    a7_actual = ar.md5_file(HERE / 'stageA7.py')
    if a7_actual != PINNED_STAGEA7_MD5:
        raise RuntimeError(f'Pinned stageA7.py MD5 mismatch: {a7_actual} != {PINNED_STAGEA7_MD5}')
    out['data_pilot_fer_20261121/stageA7.py'] = a7_actual
    return out


def verify_all_archives() -> dict[str, dict[str, str]]:
    res = stageA6.verify_all_archives(('stageA', 'stageA2', 'stageA3', 'stageA5', 'sameframe_cd2'))
    res['stageA6'] = stageA7.verify_archive('stageA6')
    return res


def _used_cpu_seconds() -> float:
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + ch.ru_utime + ch.ru_stime


def _active_pids_cpu(pids: list[int]) -> float:
    total = 0.0
    for pid in pids:
        try:
            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
            after = raw[raw.rfind(')') + 2:].split()
            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
        except OSError:
            pass
    return total


# --------------------------------------------------------------------------- Per-key evaluation
def eval_key(C, stageA, stageA2, stageA5, daft, base, s: str, rho: int, snr: int, frame: int) -> dict[str, Any]:
    """Evaluate SBGdop on one key (true delays only; zero truth peeking)."""
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2
    raw, obs, truth = st.observed(ctx, base, rho, snr)

    y = np.asarray(raw['y'], dtype=np.complex128)
    p = np.asarray(raw['pilot'], dtype=np.complex128)
    d = np.asarray(raw['data'], dtype=np.complex128)
    sigma2 = float(raw['sigma2'])
    vd = float(np.mean(np.abs(d) ** 2))
    n = len(y)
    r = daft(y, c1, c2, True)
    p_t = daft(p, c1, c2, True)
    geom = stageA5.precompute_delay_geometry(truth['l_i'], n, c1)
    fgeom = stageA7.prepare_fast_geom(geom)

    t0 = time.process_time()
    nu_sbg, g_sbg = stageA7.estimate_sb_global(stageA5, fgeom, p_t, r, vd, sigma2)
    sbg_cpu = time.process_time() - t0

    m_sbg, o_sbg, e_sbg = stageA5.doppler_metric(nu_sbg, truth['k_real'], truth['g_i'])
    rec_sbg = stageA6.one_arm_nu(C, stageA, stageA2, obs, truth, nu_sbg, g_order=g_sbg)

    return dict(
        frame=frame,
        scenario=s,
        rho=rho,
        snr=snr,
        sigma2=float(obs['sigma2']),
        sbg_cpu=float(sbg_cpu),
        sbg_metric=float(m_sbg),
        sbg_outlier_frac=float(o_sbg),
        sbg_abs_err=e_sbg,
        truth_power=(np.abs(np.asarray(truth['g_i'], dtype=np.complex128)) ** 2).tolist(),
        arms=dict(SBGdop=rec_sbg),
    )


# --------------------------------------------------------------------------- Frozen Stage A6 archive loader
def _load_a6_archives(snrs: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray, dict[tuple[int, str, int, int], dict[str, Any]]]:
    """Load verified Stage A6 SBdop and PWdop failure grids and row map on selected SNRs."""
    fi = {f: i for i, f in enumerate(FRAMES)}
    sb_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
    pw_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
    seen = np.zeros_like(sb_fail)
    row_map: dict[tuple[int, str, int, int], dict[str, Any]] = {}
    snr_set = set(snrs)
    for sp in sorted((HERE / 'out' / 'stageA6' / 'raw').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                snr = int(r['snr'])
                if snr not in snr_set:
                    continue
                f, s, rho = int(r['frame']), str(r['scenario']), int(r['rho'])
                ix = (fi[f], SCENARIOS.index(s), RHOS.index(rho), snrs.index(snr))
                if seen[ix]:
                    raise RuntimeError(f'Duplicate Stage A6 archive key {(f, s, rho, snr)}')
                sb_fail[ix] = int(r['arms']['SBdop']['errors']) > 0
                pw_fail[ix] = int(r['arms']['PWdop']['errors']) > 0
                seen[ix] = True
                row_map[(f, s, rho, snr)] = r
    if not seen.all():
        raise RuntimeError('Incomplete Stage A6 archive grid for selected SNRs')
    return sb_fail, pw_fail, row_map


# --------------------------------------------------------------------------- Gates G1-G3
def _g3_cost_worker(in_path: str, out_path: str):
    C, stageA, stageA2, stageA5, daft = stageA6._load_runtime()
    st, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    out = []
    for frame, s, rho, snr in jobs:
        t0 = time.process_time()
        base = st.inputs(ctx, frame, s, rho)
        row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
        tot = time.process_time() - t0
        out.append(dict(
            key=[frame, s, rho, snr],
            snr=snr,
            total_cpu=float(tot),
            sbg_cpu=row['sbg_cpu'],
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(out, allow_nan=False))


def cmd_gate(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    if not 1 <= args.workers <= 32:
        raise ValueError('workers must be in 1..32')
    started = time.monotonic()

    gate_path = args.out.resolve()
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    if gate_path.exists():
        gate_path.unlink()

    pinned_md5 = verify_pinned_code()
    manifests = verify_all_archives()
    C, stageA, stageA2, stageA5, daft = stageA6._load_runtime()
    st, ctx = C['stage3'], C['ctx']

    # G1: nu_hat = truth['k_real'] reproduces stageA2 'ldop' exactly on 4 keys
    a2_rows = {}
    with gzip.open(HERE / 'out' / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt', encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            a2_rows[(r['scenario'], int(r['rho']), int(r['snr']), int(r['frame']))] = r
    g1_keys = (('U', 100, 300, 41000), ('G', 150, 400, 41001), ('U', 150, 450, 41002), ('G', 100, 500, 41003))
    g1_rows = []
    for s, rho, snr, frame in g1_keys:
        base = st.inputs(ctx, frame, s, rho)
        _, obs, truth = st.observed(ctx, base, rho, snr)
        rec = stageA6.one_arm_nu(C, stageA, stageA2, obs, truth, np.asarray(truth['k_real'], dtype=np.float64))
        ref = a2_rows[(s, rho, snr, frame)]['arms']['ldop']
        ok = all(int(rec[k]) == int(ref[k]) for k in ('syndrome', 'f0_errors', 'errors'))
        g1_rows.append(dict(key=[s, rho, snr, frame], passed=bool(ok)))
    g1_pass = bool(len(g1_rows) == 4 and all(x['passed'] for x in g1_rows))
    print(f'G1 {"PASS" if g1_pass else "FAIL"} ({sum(x["passed"] for x in g1_rows)}/4 exact ldop replay)', flush=True)

    # G2: 4 keys from Stage A7 results.json reproduce sbg_metric, sbg_max_err, and SBGdop errors bitwise (< 1e-12)
    a7_res = json.loads((HERE / 'out' / 'stageA7' / 'results.json').read_text(encoding='utf-8'))
    a7_sample = [
        a7_res['rows'][0],
        next(x for x in a7_res['rows'] if int(x['snr']) == 500 and int(x['rho']) == 100),
        next(x for x in a7_res['rows'] if int(x['rho']) == 150 and int(x['snr']) == 450),
        next(x for x in a7_res['rows'] if int(x['rho']) == 150 and int(x['snr']) == 500),
    ]
    g2_rows = []
    for ref in a7_sample:
        f, s, rho, snr = int(ref['frame']), str(ref['scenario']), int(ref['rho']), int(ref['snr'])
        base = st.inputs(ctx, f, s, rho)
        row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, f)
        dm = float(abs(row['sbg_metric'] - float(ref['sbg_metric'])))
        de = float(abs(max(row['sbg_abs_err']) - float(ref['sbg_max_err'])))
        rec_got = row['arms']['SBGdop']
        rec_ref = ref['receiver']['sbgdop']
        rec_ok = (
            int(rec_got['syndrome']) == int(rec_ref['f0_syndrome'])
            and int(rec_got['f0_errors']) == int(rec_ref['f0_errors'])
            and int(rec_got['errors']) == int(rec_ref['errors'])
        )
        ok = bool(dm < 1e-12 and de < 1e-12 and rec_ok)
        g2_rows.append(dict(key=[f, s, rho, snr], metric_diff=dm, max_err_diff=de, rec_ok=rec_ok, passed=ok))
    g2_pass = bool(len(g2_rows) == 4 and all(x['passed'] for x in g2_rows))
    print(f'G2 {"PASS" if g2_pass else "FAIL"} max_diff={max(max(x["metric_diff"], x["max_err_diff"]) for x in g2_rows):.2e}', flush=True)

    # Pre-load check on all comparator archives (CD2, stageA2, stageA3, stageA6)
    stageA6._load_frozen_comparators()
    _load_a6_archives(FULL_SNRS)
    print('Frozen comparator archives (CD2, stageA2, stageA3, stageA6) pre-load check: PASS', flush=True)

    # G3: Stratified cost benchmark on isolated frames 41400-41403 across [300, 400, 450, 500] (16 keys)
    g3_jobs = []
    for snr in FULL_SNRS:
        g3_jobs.extend([
            [41400, 'U', 100, snr],
            [41401, 'G', 100, snr],
            [41402, 'U', 150, snr],
            [41403, 'G', 150, snr],
        ])
    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'stageA8_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        g3_samples = stageA6._spawn_map(_g3_cost_worker, g3_jobs, min(args.workers, len(g3_jobs)), ipc_dir, 'g3')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    mean_cpu_by_snr = {
        snr: float(np.mean([x['total_cpu'] for x in g3_samples if int(x['snr']) == snr]))
        for snr in FULL_SNRS
    }
    mean_sbg_by_snr = {
        snr: float(np.mean([x['sbg_cpu'] for x in g3_samples if int(x['snr']) == snr]))
        for snr in FULL_SNRS
    }
    keys_per_snr = len(FRAMES) * len(SCENARIOS) * len(RHOS)
    candidates = []
    for cand_snrs in CANDIDATE_SNRS:
        raw_h = sum(mean_cpu_by_snr[s] * keys_per_snr for s in cand_snrs) / 3600.0 + OVERHEAD_HOURS
        marg_h = raw_h * COST_MARGIN
        candidates.append(dict(
            snrs=list(cand_snrs),
            dropped_snrs=[s for s in FULL_SNRS if s not in cand_snrs],
            n_keys=keys_per_snr * len(cand_snrs),
            raw_hours=raw_h,
            projected_hours_with_margin=marg_h,
            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
        ))
    selected = next((c for c in candidates if c['within_budget']), None)
    g3_pass = selected is not None
    all_passed = bool(g1_pass and g2_pass and g3_pass)
    gate_cpu_h = _used_cpu_seconds() / 3600.0

    payload = dict(
        _argv=sys.argv,
        _config=dict(
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
            own_md5=own_md5(),
            pinned_code_md5=pinned_md5,
            archive_shards_verified={k: len(v) for k, v in manifests.items()},
        ),
        all_passed=all_passed,
        selected=selected,
        G1=dict(passed=g1_pass, rows=g1_rows),
        G2=dict(passed=g2_pass, rows=g2_rows),
        G3=dict(
            passed=g3_pass,
            budget_cap_core_hours=BUDGET_CAP_HOURS,
            margin=COST_MARGIN,
            overhead_hours=OVERHEAD_HOURS,
            mean_total_cpu_sec_by_snr={str(k): v for k, v in mean_cpu_by_snr.items()},
            mean_sbg_cpu_sec_by_snr={str(k): v for k, v in mean_sbg_by_snr.items()},
            candidates=candidates,
            samples=g3_samples,
        ),
        gate_cpu_hours=gate_cpu_h,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
    sys.exit(0 if all_passed else 1)


# --------------------------------------------------------------------------- Sharded run & frozen readout
def _run_shard_worker(shard_idx: int, frames: tuple[int, ...], snrs: tuple[int, ...], raw_dir: Path):
    C, stageA, stageA2, stageA5, daft = stageA6._load_runtime()
    st, ctx = C['stage3'], C['ctx']
    lines: list[str] = []
    for frame in frames:
        for s in SCENARIOS:
            for rho in RHOS:
                base = st.inputs(ctx, frame, s, rho)
                for snr in snrs:
                    row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
                    lines.append(json.dumps(row, allow_nan=False) + '\n')

    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
    with part_path.open('wb') as raw_fh:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
            for ln in lines:
                gz.write(ln.encode('utf-8'))
        raw_fh.flush()
        os.fsync(raw_fh.fileno())
    os.replace(part_path, final_path)
    print(f'Shard {shard_idx:03d} done ({len(lines)} keys, {len(frames)} frames)', flush=True)


def verdict_a8(ci_lo: float) -> str:
    """Task Rule 2 binary gate: worth continuing iff 95% lower bound >= 0.5 dB."""
    return 'GO' if ci_lo >= GO_THRESH_DB else 'STOP'


def analyze_stageA8(
    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
    crossing_fn,
    diagnostics: dict[str, Any],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Frozen Stage A8 readout with exact Stage A6 / sameframe_cd2 joint physical-frame bootstrap."""
    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
    rng = np.random.default_rng(boot_seed)
    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
    weights[0] = 1.0 / n_frames
    for b in range(1, boot_draws + 1):
        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames

    arm_lo: dict[str, np.ndarray] = {}
    arm_hi: dict[str, np.ndarray] = {}
    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
    arm_mean_pt: dict[str, dict[str, Any]] = {}
    arm_best_lo: dict[str, np.ndarray] = {}
    arm_best_hi: dict[str, np.ndarray] = {}
    arm_best_rho: dict[str, int] = {}

    for arm, (rhos, snrs, fail) in fail_by_arm.items():
        n_r = len(rhos)
        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
        scen_pt = {'U': {}, 'G': {}}
        for ri, rho in enumerate(rhos):
            for bi in range(boot_draws + 1):
                u_lo, u_hi = sf.crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
                g_lo, g_hi = sf.crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
                if bi == 0:
                    scen_pt['U'][str(rho)] = sf._rep(u_lo) if u_lo == u_hi else [sf._rep(u_lo), sf._rep(u_hi)]
                    scen_pt['G'][str(rho)] = sf._rep(g_lo) if g_lo == g_hi else [sf._rep(g_lo), sf._rep(g_hi)]
        arm_lo[arm] = lo_arr
        arm_hi[arm] = hi_arr
        arm_scen_pt[arm] = scen_pt
        arm_mean_pt[arm] = {
            str(rho): (sf._rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [sf._rep(lo_arr[0, ri]), sf._rep(hi_arr[0, ri])])
            for ri, rho in enumerate(rhos)
        }
        sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200] if arm in ('full', 'ldop') else list(range(n_r))
        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
        arm_best_rho[arm] = int(rhos[sub_idx[int(np.argmin(hi_arr[0, sub_idx]))]])

    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
        if cens_frac == 0.0:
            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
        else:
            lo = an._nearest_rank(d_lo[1:], 0.025)
            hi = an._nearest_rank(d_hi[1:], 0.975)
        pt = sf._rep(d_lo[0]) if d_lo[0] == d_hi[0] else [sf._rep(d_lo[0]), sf._rep(d_hi[0])]
        return dict(
            point_db=pt,
            ci95_db=[sf._rep(lo), sf._rep(hi)],
            censored_draw_fraction=cens_frac,
            arm_a_best_db=sf._rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [sf._rep(arm_best_lo[arm_a][0]), sf._rep(arm_best_hi[arm_a][0])],
            arm_a_best_rho=arm_best_rho[arm_a],
            arm_b_best_db=sf._rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [sf._rep(arm_best_lo[arm_b][0]), sf._rep(arm_best_hi[arm_b][0])],
            arm_b_best_rho=arm_best_rho[arm_b],
        )

    primary = contrast('CD2', 'SBGdop')
    lo_val = stageA6._to_float_bound(primary['ci95_db'][0])
    hi_val = stageA6._to_float_bound(primary['ci95_db'][1])
    primary['verdict'] = verdict_a8(lo_val)
    primary['go_threshold_db'] = GO_THRESH_DB
    primary['stop_below_0p3_ref'] = bool(hi_val < STOP_REF_DB)

    best_ci = {}
    for arm in ('SBGdop', 'SBdop', 'PWdop', 'CD2', 's050', 's100', 'ldop'):
        if arm not in arm_best_lo:
            continue
        blo, bhi = arm_best_lo[arm], arm_best_hi[arm]
        cf = float(np.mean(~(np.isfinite(blo[1:]) & np.isfinite(bhi[1:]))))
        if cf == 0.0:
            c_lo, c_hi = (float(v) for v in np.percentile(blo[1:], [2.5, 97.5]))
        else:
            c_lo = an._nearest_rank(blo[1:], 0.025)
            c_hi = an._nearest_rank(bhi[1:], 0.975)
        best_ci[arm] = dict(
            best_db=sf._rep(blo[0]) if blo[0] == bhi[0] else [sf._rep(blo[0]), sf._rep(bhi[0])],
            best_rho=arm_best_rho[arm],
            ci95_db=[sf._rep(c_lo), sf._rep(c_hi)],
            censored_draw_fraction=cf,
        )

    secondary = {}
    for name, (a_arm, b_arm) in (
        ('SBdop_minus_SBGdop', ('SBdop', 'SBGdop')),
        ('PWdop_minus_SBGdop', ('PWdop', 'SBGdop')),
        ('SBGdop_minus_s050', ('SBGdop', 's050')),
        ('SBGdop_minus_ldop', ('SBGdop', 'ldop')),
        ('SBGdop_minus_s100', ('SBGdop', 's100')),
        ('CD2_minus_SBdop', ('CD2', 'SBdop')),
        ('CD2_minus_ldop', ('CD2', 'ldop')),
    ):
        if a_arm in arm_best_lo and b_arm in arm_best_lo:
            secondary[name] = contrast(a_arm, b_arm)

    return dict(
        frames=n_frames,
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary=primary,
        best_crossings=best_ci,
        secondary_contrasts=secondary,
        mean_crossing=arm_mean_pt,
        crossings_by_scenario=arm_scen_pt,
        best_rho=arm_best_rho,
        diagnostics=diagnostics,
    )


def summarize_diagnostics(
    rows: list[dict[str, Any]],
    snrs: tuple[int, ...],
    a6_map: dict[tuple[int, str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    by_rho_snr: dict[str, dict[str, Any]] = {}
    tot_rescued = tot_regressed = tot_both_fail = tot_both_ok = 0

    for rho in RHOS:
        for snr in snrs:
            sub = [r for r in rows if int(r['rho']) == rho and int(r['snr']) == snr]
            sbg_m = np.array([r['sbg_metric'] for r in sub], dtype=np.float64)
            sbg_o = np.array([r['sbg_outlier_frac'] for r in sub], dtype=np.float64)
            sbg_f0 = float(np.mean([r['arms']['SBGdop']['f0_errors'] > 0 for r in sub]))
            sbg_fin = float(np.mean([r['arms']['SBGdop']['errors'] > 0 for r in sub]))

            resc = regr = b_fail = b_ok = 0
            sb_m_list = []
            sb_fin_list = []
            for r in sub:
                ref = a6_map[(int(r['frame']), str(r['scenario']), int(r['rho']), int(r['snr']))]
                sb_m_list.append(float(ref['sb_metric']))
                sb_failed = int(ref['arms']['SBdop']['errors']) > 0
                sbg_failed = int(r['arms']['SBGdop']['errors']) > 0
                sb_fin_list.append(sb_failed)
                if sb_failed and not sbg_failed:
                    resc += 1
                elif (not sb_failed) and sbg_failed:
                    regr += 1
                elif sb_failed and sbg_failed:
                    b_fail += 1
                else:
                    b_ok += 1
            tot_rescued += resc
            tot_regressed += regr
            tot_both_fail += b_fail
            tot_both_ok += b_ok

            by_rho_snr[f'{rho}_{snr}'] = dict(
                n=len(sub),
                sbg_doppler_mean=float(sbg_m.mean()),
                sbg_doppler_median=float(np.median(sbg_m)),
                sbg_outlier_gt_0p25_frac=float(sbg_o.mean()),
                a6_sb_doppler_mean=float(np.mean(sb_m_list)),
                sbg_f0_fer=sbg_f0,
                sbg_final_fer=sbg_fin,
                a6_sb_final_fer=float(np.mean(sb_fin_list)),
                rescued_from_sbdop=resc,
                regressed_vs_sbdop=regr,
                both_fail=b_fail,
                both_ok=b_ok,
            )

    sbg_t = np.array([r['sbg_cpu'] for r in rows], dtype=np.float64)
    return dict(
        by_rho_snr=by_rho_snr,
        paired_vs_sbdop_totals=dict(
            n_keys=len(rows),
            rescued_sb_fail_to_sbg_ok=tot_rescued,
            regressed_sb_ok_to_sbg_fail=tot_regressed,
            both_fail=tot_both_fail,
            both_ok=tot_both_ok,
        ),
        timing_cpu_sec=dict(
            sbg_mean=float(sbg_t.mean()),
            sbg_median=float(np.median(sbg_t)),
            sbg_p95=float(np.percentile(sbg_t, 95)),
            sbg_by_snr={
                str(snr): float(np.mean([r['sbg_cpu'] for r in rows if int(r['snr']) == snr]))
                for snr in snrs
            },
        ),
    )


def render_results_md(res: dict[str, Any]) -> str:
    a = res['analysis']
    p = a['primary']
    d = a['diagnostics']

    def fval(x):
        if isinstance(x, list):
            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
        return x if isinstance(x, str) else f'{x:.4f}'

    lines = [
        '# Stage A8 Results: Full-Frame 1% FER Recovery of Truth-Free Global Semi-Blind Doppler (`SBGdop`)',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- Grid: frames `41000–41399` × U/G (`800` draws/cell), ρ ∈ `{res["_config"]["rhos"]}`, SNRs = `{res["_config"]["snrs"]}`',
        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap `{res["runtime"]["cpu_cap_core_hours"]:.2f} h`, wall `{res["runtime"]["wall_seconds"]:.1f} s`)',
        '',
        '## Primary Verdict (Pre-Registered, 1% info-FER U/G Mean, LB >= 0.50 dB Gate)',
        '',
        '| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |',
        '|---|---:|---|---|',
        f'| `min CD2 (100..250) − min SBGdop (100..150)` | **{fval(p["point_db"])}** | **[{fval(p["ci95_db"][0])}, {fval(p["ci95_db"][1])}]** | **{p["verdict"]}** |',
        '',
        '## 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
        '',
        '| Arm | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | Best (dB) [95% CI] | Best ρ |',
        '|---|---:|---:|---:|---:|---|---:|',
    ]
    for arm in ('CD2', 'PWdop', 'SBdop', 'SBGdop', 's100', 's050', 'ldop'):
        if arm not in a['mean_crossing']:
            continue
        cells = [fval(a['mean_crossing'][arm][r]) if r in a['mean_crossing'][arm] else '—' for r in ('100', '150', '200', '250')]
        bc = a['best_crossings'][arm]
        lines.append(
            f'| {arm} | ' + ' | '.join(cells) + f' | **{fval(bc["best_db"])}** [{fval(bc["ci95_db"][0])}, {fval(bc["ci95_db"][1])}] | {bc["best_rho"]/1000:.2f} |'
        )

    lines += ['', '## Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
    for name, c in a['secondary_contrasts'].items():
        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')

    lines += [
        '',
        '## Per-(ρ, SNR) Doppler Metric, FER & Paired Rescue/Regression vs `SBdop` (800 Draws/Cell)',
        '',
        '| ρ | SNR (dB) | `SBG` MAE [med] | `SBG` >0.25 | `SBG` F0 FER | `SBG` Final FER | `SB` Final FER | Rescued (`SB->SBG`) | Regressed (`SB->SBG`) |',
        '|---:|---:|---|---:|---:|---:|---:|---:|---:|',
    ]
    for rho in RHOS:
        for snr in res['_config']['snrs']:
            c = d['by_rho_snr'][f'{rho}_{snr}']
            lines.append(
                f'| {rho/1000:.2f} | {snr/100:.1f} | {c["sbg_doppler_mean"]:.4f} [{c["sbg_doppler_median"]:.4f}] | '
                f'{100*c["sbg_outlier_gt_0p25_frac"]:.2f}% | {100*c["sbg_f0_fer"]:.2f}% | '
                f'**{100*c["sbg_final_fer"]:.2f}%** | {100*c["a6_sb_final_fer"]:.2f}% | '
                f'`+{c["rescued_from_sbdop"]}` | `-{c["regressed_vs_sbdop"]}` |'
            )

    ptot = d['paired_vs_sbdop_totals']
    tm = d['timing_cpu_sec']
    lines += [
        '',
        '## Paired Accounting & Timing Summary',
        '',
        f'- Across all `{ptot["n_keys"]}` paired keys vs Stage A6 `SBdop`: rescued `{ptot["rescued_sb_fail_to_sbg_ok"]}`, '
        f'regressed `{ptot["regressed_sb_ok_to_sbg_fail"]}`, both failed `{ptot["both_fail"]}`, both succeeded `{ptot["both_ok"]}`.',
        f'- Per-key `SBG` CPU time: mean **`{tm["sbg_mean"]:.3f} s`**, median `{tm["sbg_median"]:.3f} s`, p95 `{tm["sbg_p95"]:.3f} s`.',
    ]
    return '\n'.join(lines) + '\n'


def cmd_run(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    ar.check_thread_env()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
    if not 1 <= args.workers <= 32:
        raise ValueError('workers must be in 1..32')

    pinned_md5 = verify_pinned_code()
    live_own = own_md5()
    freeze_git_ok = stageA6.verify_freeze_commit_if_git(args.freeze_commit, live_own)
    manifests = verify_all_archives()

    gate_path = args.gate.resolve()
    gate_bytes = gate_path.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to run without passing stageA8_gate.json')
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('stageA8_gate.json own_md5 mismatch; re-run gates')
    if gate['_config']['pinned_code_md5'] != pinned_md5:
        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA8_gate.json')

    snrs = tuple(int(s) for s in gate['selected']['snrs'])
    frozen_comps, crossing_fn = stageA6._load_frozen_comparators()
    a6_sb_fail, a6_pw_fail, a6_map = _load_a6_archives(snrs)

    out_dir = args.out.resolve()
    raw_dir = out_dir / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    if list(raw_dir.glob('rows_shard*.jsonl*')):
        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')

    wall_start = time.monotonic()
    n_shards = args.workers
    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    budget_hit = False
    print(
        f'Launching Stage A8: {len(FRAMES)} frames x 2 scen x {len(RHOS)} rhos x {len(snrs)} SNRs '
        f'({snrs}) = {len(FRAMES)*2*len(RHOS)*len(snrs)} keys on {n_shards} workers...',
        flush=True,
    )
    try:
        for idx in range(n_shards):
            sub_frames = tuple(FRAMES[idx::n_shards])
            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_frames, snrs, raw_dir))
            p.start()
            running[p.sentinel] = (idx, p)
        while running:
            ready = wait(running, timeout=5.0)
            for r_ready in ready:
                idx, p = running.pop(r_ready)
                p.join()
                code = p.exitcode
                p.close()
                if code != 0:
                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= BUDGET_CAP_SEC - 180.0:
                budget_hit = True
                break
    finally:
        for _, p in running.values():
            p.terminate()
        for _, p in running.values():
            p.join()
            p.close()
    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    raw_md5: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    fi = {f: i for i, f in enumerate(FRAMES)}
    sbg_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
    seen = np.zeros_like(sbg_fail)
    for idx in range(n_shards):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
        raw_md5[sp.name] = ar.md5_file(sp)
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                rows.append(r)
                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), RHOS.index(int(r['rho'])), snrs.index(int(r['snr'])))
                if seen[ix]:
                    raise RuntimeError(f'Duplicate Stage A8 key {r["frame"]} {r["scenario"]} {r["rho"]} {r["snr"]}')
                sbg_fail[ix] = int(r['arms']['SBGdop']['errors']) > 0
                seen[ix] = True
    if not seen.all():
        raise RuntimeError('Incomplete Stage A8 failure grid')
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
    )

    fail_by_arm = dict(frozen_comps)
    fail_by_arm['SBdop'] = (RHOS, snrs, a6_sb_fail)
    fail_by_arm['PWdop'] = (RHOS, snrs, a6_pw_fail)
    fail_by_arm['SBGdop'] = (RHOS, snrs, sbg_fail)

    diagnostics = summarize_diagnostics(rows, snrs, a6_map)
    analysis = analyze_stageA8(fail_by_arm, crossing_fn, diagnostics)

    total_cpu_h = _used_cpu_seconds() / 3600.0
    if total_cpu_h >= BUDGET_CAP_HOURS:
        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    results = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            freeze_commit_git_verified=freeze_git_ok,
            python_executable=sys.executable,
            own_md5=live_own,
            pinned_code_md5=pinned_md5,
            gate_md5=gate_md5,
            archive_shards_verified={k: len(v) for k, v in manifests.items()},
            snrs=list(snrs),
            rhos=list(RHOS),
            frames=[FRAMES[0], FRAMES[-1]],
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G1_passed=gate['G1']['passed'],
            G2_passed=gate['G2']['passed'],
        ),
        runtime=dict(
            total_core_hours=total_cpu_h,
            wall_seconds=time.monotonic() - wall_start,
            cpu_cap_core_hours=BUDGET_CAP_HOURS,
        ),
        analysis=analysis,
    )
    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    p = analysis['primary']
    print(
        f'STAGEA8_DONE verdict={p["verdict"]} D={p["point_db"]} '
        f'ci={p["ci95_db"]} SBGdop_best={p["arm_b_best_db"]}@rho{p["arm_b_best_rho"]} '
        f'cpu_hours={total_cpu_h:.4f}',
        flush=True,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    g = sub.add_parser('gate')
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--workers', type=int, default=16)

    r = sub.add_parser('run')
    r.add_argument('--gate', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--freeze-commit', required=True)
    r.add_argument('--workers', type=int, default=WORKERS)

    args = ap.parse_args()
    dict(gate=cmd_gate, run=cmd_run)[args.mode](args)


if __name__ == '__main__':
    main()
