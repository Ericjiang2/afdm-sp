"""Stage A8b (STAGEA8B_PROTOCOL.md): 3.50 / 3.75 dB densified 1% FER verification of SBGdop vs CD2 and ldop.

Eliminates Stage A8's 1e-4 zero-floor interpolation blind spot across (3.0, 4.0) dB at rho = 0.10 by measuring
both `SBGdop` (frozen `stageA7.estimate_sb_global`, zero changes) and `ldop` (archived `stageA2` true-Doppler
ceiling definition) at SNRs in {350, 375} across all 400 physical frames (41000-41399 x U/G = 1,600 keys),
merging them with verified frozen Stage A8 / Stage A2 shards to form (300, 350, 375, 400, 450, 500).
"""
from __future__ import annotations

import argparse
import fnmatch
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
import stageA8  # noqa: E402

FRAMES = stageA8.FRAMES
SCENARIOS = stageA8.SCENARIOS
RHO_DENS = 100
BASE_A8_SNRS = (300, 400, 450, 500)
CANDIDATE_NEW_SNRS: tuple[tuple[int, ...], ...] = (
    (350, 375),
    (375,),
)
FULL_NEW_SNRS = CANDIDATE_NEW_SNRS[0]

BOOT_DRAWS = 2000
BOOT_SEED = 20261125
GO_THRESH_DB = 0.5
STOP_REF_DB = 0.3
HALDANE_FLOOR = 0.5 / float(len(FRAMES))  # 0.00125 for N=400 per scenario

WORKERS = 32
TOTAL_TASK_CAP_HOURS = 10.0
PRIOR_CUMULATIVE_HOURS = 7.0310  # dev 0.6960 + A7 0.3856 + A8 5.9434 + audit 0.0060
GATE_BUDGET_HOURS = 0.08
STAGE_CAP_HOURS = 2.45
SAFETY_RESERVE_HOURS = 0.05
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.08
BUDGET_EXIT_CODE = 124
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100

OWN_FILES = ('STAGEA8B_PROTOCOL.md', 'stageA8b.py', 'test_stageA8b.py', 'stageA8b_launch.sh')
PINNED_STAGEA8_MD5 = 'a24ca8b6746734d171dfe540b9baea31'
STAGEA8_ARCHIVE_SPEC = (
    HERE / 'out' / 'stageA8' / 'REMOTE_ROWS_MD5.txt',
    HERE / 'out' / 'stageA8' / 'raw',
    '8aa05927d27739fec064ee86a1a8c9fe42a79e5686a1f07e7d4236ff1a61a179',
    'rows_shard*.jsonl.gz',
)


def compute_effective_run_cap_hours(gate_cpu_hours: float) -> float:
    """Enforce both stage cap (2.45 h) and cumulative 10.0 core-hour task cap."""
    rem = TOTAL_TASK_CAP_HOURS - PRIOR_CUMULATIVE_HOURS - max(0.0, float(gate_cpu_hours)) - SAFETY_RESERVE_HOURS
    return float(min(STAGE_CAP_HOURS, max(0.0, rem)))


def select_candidate_snrs(
    mean_cpu_by_snr: dict[int, float],
    effective_cap_hours: float,
    *,
    keys_per_snr: int = len(FRAMES) * len(SCENARIOS),
    margin: float = COST_MARGIN,
    overhead_hours: float = OVERHEAD_HOURS,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Protocol G3 cost projection: projected = raw_hours * 1.3 + 0.08 <= effective_cap_hours."""
    candidates = []
    for cand_snrs in CANDIDATE_NEW_SNRS:
        raw_h = sum(float(mean_cpu_by_snr[s]) * keys_per_snr for s in cand_snrs) / 3600.0
        marg_h = raw_h * margin + overhead_hours
        candidates.append(dict(
            new_snrs=list(cand_snrs),
            n_keys=keys_per_snr * len(cand_snrs),
            raw_hours=raw_h,
            projected_hours_with_margin=marg_h,
            within_budget=bool(marg_h <= effective_cap_hours),
        ))
    selected = next((c for c in candidates if c['within_budget']), None)
    return candidates, selected


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_pinned_code() -> dict[str, str]:
    out = stageA8.verify_pinned_code()
    a8_actual = ar.md5_file(HERE / 'stageA8.py')
    if a8_actual != PINNED_STAGEA8_MD5:
        raise RuntimeError(f'Pinned stageA8.py MD5 mismatch: {a8_actual} != {PINNED_STAGEA8_MD5}')
    out['data_pilot_fer_20261121/stageA8.py'] = a8_actual
    return out


def verify_stageA8_archive() -> dict[str, str]:
    manifest_path, shard_dir, exp_sha, glob_pat = STAGEA8_ARCHIVE_SPEC
    got_sha = ar.sha256_file(manifest_path)
    if got_sha != exp_sha:
        raise RuntimeError(f'stageA8 manifest SHA-256 mismatch: {got_sha} != {exp_sha}')
    expected: dict[str, str] = {}
    for line in manifest_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, fname = line.split()
        p = shard_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f'Missing stageA8 shard {p}')
        actual = ar.md5_file(p)
        if actual != digest:
            raise RuntimeError(f'stageA8 shard MD5 mismatch {p}: {actual} != {digest}')
        expected[fname] = actual
    disk = {p.name for p in shard_dir.glob(glob_pat)}
    expected_matched = {f for f in expected if fnmatch.fnmatch(f, glob_pat)}
    if disk != expected_matched:
        raise RuntimeError(f'stageA8 shard set mismatch on disk: {sorted(disk ^ expected_matched)}')
    return expected


def verify_all_archives() -> dict[str, dict[str, str]]:
    res = stageA8.verify_all_archives()
    res['stageA8'] = verify_stageA8_archive()
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


def crossing_haldane(fer: np.ndarray, snrs: tuple[int, ...] | list[int]) -> float:
    """Sensitivity variant of stageA2.crossing replacing 1e-4 floor with 0.5/N (= 1.25e-3 for N=400)."""
    x = np.asarray(snrs, dtype=np.float64) / 100.0
    lf = np.log10(np.maximum(np.asarray(fer, dtype=np.float64), HALDANE_FLOOR))
    if fer[0] <= 0.01:
        return -np.inf
    for i in range(1, len(x)):
        if fer[i] <= 0.01:
            t = (lf[i - 1] + 2.0) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
            return float(x[i - 1] + t * (x[i] - x[i - 1]))
    return np.inf


def empirical_bracket_db(fer: np.ndarray, snrs: tuple[int, ...] | list[int]) -> list[Any]:
    """Interpolation-free empirical bracket [last SNR > 1%, first SNR <= 1%] in dB."""
    x = [float(s) / 100.0 for s in snrs]
    if fer[0] <= 0.01:
        return ['-inf', x[0]]
    for i in range(1, len(x)):
        if fer[i] <= 0.01:
            return [x[i - 1], x[i]]
    return [x[-1], '+inf']


# --------------------------------------------------------------------------- Per-key evaluation (SBGdop + ldop)
def eval_key_a8b(C, stageA, stageA2, stageA5, daft, base, s: str, rho: int, snr: int, frame: int) -> dict[str, Any]:
    """Evaluate frozen SBGdop and archived-definition ldop sequentially on the exact same observation."""
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

    t1 = time.process_time()
    rec_sbg = stageA6.one_arm_nu(C, stageA, stageA2, obs, truth, nu_sbg, g_order=g_sbg)
    sbg_rx_cpu = time.process_time() - t1

    t2 = time.process_time()
    rec_ldop = stageA6.one_arm_nu(
        C, stageA, stageA2, obs, truth, np.asarray(truth['k_real'], dtype=np.float64), g_order=None
    )
    ldop_cpu = time.process_time() - t2

    return dict(
        frame=frame,
        scenario=s,
        rho=rho,
        snr=snr,
        sigma2=float(obs['sigma2']),
        sbg_cpu=float(sbg_cpu),
        sbg_rx_cpu=float(sbg_rx_cpu),
        ldop_cpu=float(ldop_cpu),
        sbg_metric=float(m_sbg),
        sbg_outlier_frac=float(o_sbg),
        sbg_abs_err=e_sbg,
        arms=dict(SBGdop=rec_sbg, ldop=rec_ldop),
    )


# --------------------------------------------------------------------------- Archive loaders
def _load_a8_archives(snrs: tuple[int, ...] = BASE_A8_SNRS) -> tuple[np.ndarray, dict[tuple[int, str, int, int], dict[str, Any]]]:
    fi = {f: i for i, f in enumerate(FRAMES)}
    rhos = stageA8.RHOS
    sbg_fail = np.zeros((len(FRAMES), 2, len(rhos), len(snrs)), dtype=bool)
    seen = np.zeros_like(sbg_fail)
    row_map: dict[tuple[int, str, int, int], dict[str, Any]] = {}
    snr_set = set(snrs)
    for sp in sorted((HERE / 'out' / 'stageA8' / 'raw').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                snr = int(r['snr'])
                if snr not in snr_set:
                    continue
                f, s, rho = int(r['frame']), str(r['scenario']), int(r['rho'])
                ix = (fi[f], SCENARIOS.index(s), rhos.index(rho), snrs.index(snr))
                if seen[ix]:
                    raise RuntimeError(f'Duplicate Stage A8 key {(f, s, rho, snr)}')
                sbg_fail[ix] = int(r['arms']['SBGdop']['errors']) > 0
                seen[ix] = True
                row_map[(f, s, rho, snr)] = r
    if not seen.all():
        raise RuntimeError('Incomplete Stage A8 archive grid')
    return sbg_fail, row_map


def _load_a2_rho100_map(snrs: tuple[int, ...] = BASE_A8_SNRS) -> dict[tuple[int, str, int], dict[str, Any]]:
    snr_set = set(snrs)
    out: dict[tuple[int, str, int], dict[str, Any]] = {}
    for sp in sorted((HERE / 'out' / 'stageA2').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                if int(r['rho']) == RHO_DENS and int(r['snr']) in snr_set:
                    out[(int(r['frame']), str(r['scenario']), int(r['snr']))] = r['arms']['ldop']
    if len(out) != len(FRAMES) * len(SCENARIOS) * len(snrs):
        raise RuntimeError('Incomplete Stage A2 rho=100 ldop map')
    return out


def to_rho_grid_map(rhos: tuple[int, ...], snrs: tuple[int, ...], fail_4d: np.ndarray) -> dict[int, tuple[tuple[int, ...], np.ndarray]]:
    return {int(rho): (tuple(snrs), fail_4d[:, :, ri, :]) for ri, rho in enumerate(rhos)}


def merge_rho_snrs(
    base_snrs: tuple[int, ...],
    base_fail_3d: np.ndarray,
    new_snrs: tuple[int, ...],
    new_fail_3d: np.ndarray,
) -> tuple[tuple[int, ...], np.ndarray]:
    """Merge disjoint base and new SNR slices along axis=2 into sorted ascending SNR order."""
    if set(base_snrs) & set(new_snrs):
        raise ValueError(f'Overlapping SNR grids: {base_snrs} vs {new_snrs}')
    combined = sorted(
        [(s, base_fail_3d[:, :, i]) for i, s in enumerate(base_snrs)]
        + [(s, new_fail_3d[:, :, i]) for i, s in enumerate(new_snrs)],
        key=lambda x: x[0],
    )
    merged_snrs = tuple(int(s) for s, _ in combined)
    merged_fail = np.stack([arr for _, arr in combined], axis=2)
    return merged_snrs, merged_fail


# --------------------------------------------------------------------------- Gates G1-G3
def _g3_cost_worker(in_path: str, out_path: str):
    C, stageA, stageA2, stageA5, daft = stageA6._load_runtime()
    st, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    out = []
    for frame, s, rho, snr in jobs:
        t0 = time.process_time()
        base = st.inputs(ctx, frame, s, rho)
        row = eval_key_a8b(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
        tot = time.process_time() - t0
        out.append(dict(
            key=[frame, s, rho, snr],
            snr=snr,
            total_cpu=float(tot),
            sbg_cpu=row['sbg_cpu'],
            ldop_cpu=row['ldop_cpu'],
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
    stageA6._load_frozen_comparators()
    stageA8._load_a6_archives(BASE_A8_SNRS)
    _, a8_map = _load_a8_archives(BASE_A8_SNRS)
    a2_rho100 = _load_a2_rho100_map(BASE_A8_SNRS)
    g2_pass = True
    print(f'G2 PASS ({len(manifests)} archive manifests + comparator/A8/A2 grids verified)', flush=True)

    # G1: Sequential SBGdop + ldop in eval_key_a8b matches BOTH stageA8 and stageA2 score fields on 4 keys
    C, stageA, stageA2, stageA5, daft = stageA6._load_runtime()
    st, ctx = C['stage3'], C['ctx']
    g1_keys = ((41000, 'U', 100, 300), (41001, 'G', 100, 300), (41002, 'U', 100, 400), (41003, 'G', 100, 400))
    g1_rows = []
    for frame, s, rho, snr in g1_keys:
        base = st.inputs(ctx, frame, s, rho)
        got = eval_key_a8b(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
        ref_a8 = a8_map[(frame, s, rho, snr)]
        ref_a2 = a2_rho100[(frame, s, snr)]
        dm = float(abs(got['sbg_metric'] - float(ref_a8['sbg_metric'])))
        de = float(abs(max(got['sbg_abs_err']) - max(ref_a8['sbg_abs_err'])))
        sbg_ok = all(
            int(got['arms']['SBGdop'][k]) == int(ref_a8['arms']['SBGdop'][k])
            for k in ('syndrome', 'f0_errors', 'errors')
        ) and dm < 1e-12 and de < 1e-12
        ldop_ok = all(
            int(got['arms']['ldop'][k]) == int(ref_a2[k])
            for k in ('syndrome', 'f0_errors', 'errors')
        )
        ok = bool(sbg_ok and ldop_ok)
        g1_rows.append(dict(key=[frame, s, rho, snr], metric_diff=dm, max_err_diff=de, sbg_ok=sbg_ok, ldop_ok=ldop_ok, passed=ok))
    g1_pass = bool(len(g1_rows) == 4 and all(x['passed'] for x in g1_rows))
    print(f'G1 {"PASS" if g1_pass else "FAIL"} ({sum(x["passed"] for x in g1_rows)}/4 sequential SBGdop+ldop parity)', flush=True)

    # G3: Cost benchmark on isolated frames 41400-41403 at rho=100, snr in {350, 375} (8 keys)
    g3_jobs = []
    for snr in FULL_NEW_SNRS:
        g3_jobs.extend([
            [41400, 'U', RHO_DENS, snr],
            [41401, 'G', RHO_DENS, snr],
            [41402, 'U', RHO_DENS, snr],
            [41403, 'G', RHO_DENS, snr],
        ])
    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'stageA8b_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        g3_samples = stageA6._spawn_map(_g3_cost_worker, g3_jobs, min(args.workers, len(g3_jobs)), ipc_dir, 'g3b')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    gate_cpu_h = _used_cpu_seconds() / 3600.0
    gate_within_cap = bool(gate_cpu_h <= GATE_BUDGET_HOURS)
    effective_run_cap_h = compute_effective_run_cap_hours(gate_cpu_h)
    mean_cpu_by_snr = {
        snr: float(np.mean([x['total_cpu'] for x in g3_samples if int(x['snr']) == snr]))
        for snr in FULL_NEW_SNRS
    }
    candidates, selected = select_candidate_snrs(mean_cpu_by_snr, effective_run_cap_h)
    g3_pass = bool(gate_within_cap and selected is not None)
    all_passed = bool(g1_pass and g2_pass and g3_pass)

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
        G2=dict(passed=g2_pass, archives=list(manifests.keys())),
        G3=dict(
            passed=g3_pass,
            gate_budget_cap_hours=GATE_BUDGET_HOURS,
            gate_within_cap=gate_within_cap,
            prior_cumulative_hours=PRIOR_CUMULATIVE_HOURS,
            total_task_cap_hours=TOTAL_TASK_CAP_HOURS,
            effective_run_cap_core_hours=effective_run_cap_h,
            margin=COST_MARGIN,
            overhead_hours=OVERHEAD_HOURS,
            mean_total_cpu_sec_by_snr={str(k): v for k, v in mean_cpu_by_snr.items()},
            candidates=candidates,
            samples=g3_samples,
        ),
        gate_cpu_hours=gate_cpu_h,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(
        f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} '
        f'gate_cpu_h={gate_cpu_h:.4f} effective_run_cap_h={effective_run_cap_h:.4f}',
        flush=True,
    )
    sys.exit(0 if all_passed else 1)


# --------------------------------------------------------------------------- Sharded run & frozen readout
def _run_shard_worker(shard_idx: int, frames: tuple[int, ...], new_snrs: tuple[int, ...], raw_dir: Path):
    C, stageA, stageA2, stageA5, daft = stageA6._load_runtime()
    st, ctx = C['stage3'], C['ctx']
    lines: list[str] = []
    for frame in frames:
        for s in SCENARIOS:
            base = st.inputs(ctx, frame, s, RHO_DENS)
            for snr in new_snrs:
                row = eval_key_a8b(C, stageA, stageA2, stageA5, daft, base, s, RHO_DENS, snr, frame)
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


def _eval_bootstrap_grids(
    arm_grids: dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]],
    crossing_fn,
    weights: np.ndarray,
) -> dict[str, Any]:
    boot_draws = weights.shape[0] - 1
    arm_lo: dict[str, np.ndarray] = {}
    arm_hi: dict[str, np.ndarray] = {}
    arm_rhos: dict[str, tuple[int, ...]] = {}
    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
    arm_mean_pt: dict[str, dict[str, Any]] = {}
    arm_best_lo: dict[str, np.ndarray] = {}
    arm_best_hi: dict[str, np.ndarray] = {}
    arm_best_rho: dict[str, int] = {}

    for arm, rho_map in arm_grids.items():
        rhos = tuple(sorted(rho_map.keys()))
        arm_rhos[arm] = rhos
        n_r = len(rhos)
        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
        scen_pt = {'U': {}, 'G': {}}
        for ri, rho in enumerate(rhos):
            snrs_r, fail_r = rho_map[rho]
            fer_r = np.tensordot(weights, fail_r.astype(np.float64), axes=(1, 0))
            for bi in range(boot_draws + 1):
                u_lo, u_hi = sf.crossing_bounds_stageA2(fer_r[bi, 0], snrs_r, crossing_fn)
                g_lo, g_hi = sf.crossing_bounds_stageA2(fer_r[bi, 1], snrs_r, crossing_fn)
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
        sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200] if arm in ('full', 'ldop', 'ldop_dens') else list(range(n_r))
        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
        arm_best_rho[arm] = int(rhos[sub_idx[int(np.argmin(hi_arr[0, sub_idx]))]])

    def pair_diff(lo_a: np.ndarray, hi_a: np.ndarray, lo_b: np.ndarray, hi_b: np.ndarray) -> dict[str, Any]:
        d_lo = lo_a - hi_b
        d_hi = hi_a - lo_b
        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
        if cens_frac == 0.0:
            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
        else:
            lo = an._nearest_rank(d_lo[1:], 0.025)
            hi = an._nearest_rank(d_hi[1:], 0.975)
        pt = sf._rep(d_lo[0]) if d_lo[0] == d_hi[0] else [sf._rep(d_lo[0]), sf._rep(d_hi[0])]
        return dict(point_db=pt, ci95_db=[sf._rep(lo), sf._rep(hi)], censored_draw_fraction=cens_frac)

    def contrast_best(arm_a: str, arm_b: str) -> dict[str, Any]:
        res = pair_diff(arm_best_lo[arm_a], arm_best_hi[arm_a], arm_best_lo[arm_b], arm_best_hi[arm_b])
        res['arm_a_best_db'] = sf._rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [sf._rep(arm_best_lo[arm_a][0]), sf._rep(arm_best_hi[arm_a][0])]
        res['arm_a_best_rho'] = arm_best_rho[arm_a]
        res['arm_b_best_db'] = sf._rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [sf._rep(arm_best_lo[arm_b][0]), sf._rep(arm_best_hi[arm_b][0])]
        res['arm_b_best_rho'] = arm_best_rho[arm_b]
        return res

    def contrast_rho(arm_a: str, rho_a: int, arm_b: str, rho_b: int) -> dict[str, Any]:
        ia = arm_rhos[arm_a].index(rho_a)
        ib = arm_rhos[arm_b].index(rho_b)
        return pair_diff(arm_lo[arm_a][:, ia], arm_hi[arm_a][:, ia], arm_lo[arm_b][:, ib], arm_hi[arm_b][:, ib])

    best_ci = {}
    for arm in arm_grids:
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

    return dict(
        arm_lo=arm_lo,
        arm_hi=arm_hi,
        arm_best_lo=arm_best_lo,
        arm_best_hi=arm_best_hi,
        arm_rhos=arm_rhos,
        arm_scen_pt=arm_scen_pt,
        arm_mean_pt=arm_mean_pt,
        best_ci=best_ci,
        best_rho=arm_best_rho,
        pair_diff=pair_diff,
        contrast_best=contrast_best,
        contrast_rho=contrast_rho,
    )


def analyze_stageA8b(
    arm_grids: dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]],
    crossing_fn,
    diagnostics: dict[str, Any],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    first_rho_map = next(iter(arm_grids.values()))
    n_frames = next(iter(first_rho_map.values()))[1].shape[0]
    rng = np.random.default_rng(boot_seed)
    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
    weights[0] = 1.0 / n_frames
    for b in range(1, boot_draws + 1):
        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames

    std = _eval_bootstrap_grids(arm_grids, crossing_fn, weights)
    primary = std['contrast_best']('CD2', 'SBGdop_dens')
    lo_val = stageA6._to_float_bound(primary['ci95_db'][0])
    hi_val = stageA6._to_float_bound(primary['ci95_db'][1])
    primary['verdict'] = stageA8.verdict_a8(lo_val)
    primary['go_threshold_db'] = GO_THRESH_DB
    primary['stop_below_0p3_ref'] = bool(hi_val < STOP_REF_DB)

    secondary: dict[str, Any] = {}
    if 'SBGdop_dens' in arm_grids and 'ldop_dens' in arm_grids:
        secondary['SBGdop_dens_minus_ldop_dens_rho100'] = std['contrast_rho']('SBGdop_dens', 100, 'ldop_dens', 100)
        secondary['SBGdop_dens_minus_ldop_dens_best'] = std['contrast_best']('SBGdop_dens', 'ldop_dens')
    if 'CD2' in arm_grids and 'SBGdop_dens' in arm_grids and 100 in arm_grids['SBGdop_dens']:
        ia = std['arm_rhos']['SBGdop_dens'].index(100)
        secondary['CD2_best_minus_SBGdop_dens_rho100'] = std['pair_diff'](
            std['arm_best_lo']['CD2'],
            std['arm_best_hi']['CD2'],
            std['arm_lo']['SBGdop_dens'][:, ia],
            std['arm_hi']['SBGdop_dens'][:, ia],
        )
    for name, (a_arm, b_arm) in (
        ('SBdop_minus_SBGdop_dens', ('SBdop', 'SBGdop_dens')),
        ('PWdop_minus_SBGdop_dens', ('PWdop', 'SBGdop_dens')),
        ('CD2_minus_ldop_dens', ('CD2', 'ldop_dens')),
        ('CD2_minus_SBGdop_A8_ref', ('CD2', 'SBGdop_A8')),
    ):
        if a_arm in arm_grids and b_arm in arm_grids:
            secondary[name] = std['contrast_best'](a_arm, b_arm)

    # Sensitivity check replacing 1e-4 floor with Haldane 0.5/N (= 1.25e-3)
    hal = _eval_bootstrap_grids(arm_grids, crossing_haldane, weights)
    hal_primary = hal['contrast_best']('CD2', 'SBGdop_dens')
    hal_lo = stageA6._to_float_bound(hal_primary['ci95_db'][0])
    hal_primary['verdict'] = stageA8.verdict_a8(hal_lo)
    hal_gap = (
        hal['contrast_rho']('SBGdop_dens', 100, 'ldop_dens', 100)
        if ('SBGdop_dens' in arm_grids and 'ldop_dens' in arm_grids)
        else None
    )

    # Empirical uninterpolated brackets at rho=100
    brackets = {}
    for arm in ('SBGdop_dens', 'ldop_dens'):
        if arm in arm_grids and 100 in arm_grids[arm]:
            snrs_r, fail_r = arm_grids[arm][100]
            fer_pt = fail_r.mean(axis=0)
            brackets[arm] = dict(
                U=empirical_bracket_db(fer_pt[0], snrs_r),
                G=empirical_bracket_db(fer_pt[1], snrs_r),
            )

    return dict(
        frames=n_frames,
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary=primary,
        best_crossings=std['best_ci'],
        secondary_contrasts=secondary,
        mean_crossing=std['arm_mean_pt'],
        crossings_by_scenario=std['arm_scen_pt'],
        best_rho=std['best_rho'],
        haldane_floor_sensitivity=dict(
            floor=HALDANE_FLOOR,
            primary_CD2_minus_SBGdop_dens=hal_primary,
            SBGdop_dens_best=hal['best_ci'].get('SBGdop_dens'),
            ldop_dens_best=hal['best_ci'].get('ldop_dens'),
            SBGdop_minus_ldop_rho100=hal_gap,
        ),
        empirical_brackets_rho100=brackets,
        diagnostics=diagnostics,
    )


def summarize_rho100_curve(
    new_rows: list[dict[str, Any]],
    new_snrs: tuple[int, ...],
    a8_map: dict[tuple[int, str, int, int], dict[str, Any]],
    a2_rho100: dict[tuple[int, str, int], dict[str, Any]],
) -> dict[str, Any]:
    all_snrs = tuple(sorted(set(BASE_A8_SNRS) | set(new_snrs)))
    new_map = {(int(r['frame']), str(r['scenario']), int(r['snr'])): r for r in new_rows}
    curve = {}
    for snr in all_snrs:
        u_sbg_f0 = u_sbg_fin = g_sbg_f0 = g_sbg_fin = 0
        u_ld_f0 = u_ld_fin = g_ld_f0 = g_ld_fin = 0
        paired_by_s = {'U': [0, 0, 0, 0], 'G': [0, 0, 0, 0]}  # [ld_ok_sbg_fail, ld_fail_sbg_ok, both_fail, both_ok]
        maes_by_s: dict[str, list[float]] = {'U': [], 'G': []}
        outs_by_s: dict[str, list[float]] = {'U': [], 'G': []}
        for f in FRAMES:
            for s in SCENARIOS:
                if snr in new_snrs:
                    rec = new_map[(f, s, snr)]
                    sbg_arm = rec['arms']['SBGdop']
                    ld_arm = rec['arms']['ldop']
                    maes_by_s[s].append(float(rec['sbg_metric']))
                    outs_by_s[s].append(float(rec['sbg_outlier_frac']))
                else:
                    rec8 = a8_map[(f, s, RHO_DENS, snr)]
                    sbg_arm = rec8['arms']['SBGdop']
                    ld_arm = a2_rho100[(f, s, snr)]
                    maes_by_s[s].append(float(rec8['sbg_metric']))
                    outs_by_s[s].append(float(rec8['sbg_outlier_frac']))
                sf0, sfin = int(sbg_arm['f0_errors']) > 0, int(sbg_arm['errors']) > 0
                lf0, lfin = int(ld_arm['f0_errors']) > 0, int(ld_arm['errors']) > 0
                if s == 'U':
                    u_sbg_f0 += int(sf0); u_sbg_fin += int(sfin)
                    u_ld_f0 += int(lf0); u_ld_fin += int(lfin)
                else:
                    g_sbg_f0 += int(sf0); g_sbg_fin += int(sfin)
                    g_ld_f0 += int(lf0); g_ld_fin += int(lfin)
                pb = paired_by_s[s]
                if (not lfin) and sfin:
                    pb[0] += 1
                elif lfin and (not sfin):
                    pb[1] += 1
                elif lfin and sfin:
                    pb[2] += 1
                else:
                    pb[3] += 1
        u_mae, g_mae = float(np.mean(maes_by_s['U'])), float(np.mean(maes_by_s['G']))
        u_out, g_out = float(np.mean(outs_by_s['U'])), float(np.mean(outs_by_s['G']))
        pu, pg = paired_by_s['U'], paired_by_s['G']
        curve[str(snr)] = dict(
            snr_db=snr / 100.0,
            source='stageA8b_new' if snr in new_snrs else 'stageA8_stageA2_frozen',
            sbg_doppler_mean=0.5 * (u_mae + g_mae),
            sbg_doppler_mean_U=u_mae,
            sbg_doppler_mean_G=g_mae,
            sbg_outlier_frac=0.5 * (u_out + g_out),
            sbg_outlier_frac_U=u_out,
            sbg_outlier_frac_G=g_out,
            sbg_U_f0_fail=u_sbg_f0,
            sbg_U_fin_fail=u_sbg_fin,
            sbg_G_f0_fail=g_sbg_f0,
            sbg_G_fin_fail=g_sbg_fin,
            sbg_total_f0_fer=(u_sbg_f0 + g_sbg_f0) / 800.0,
            sbg_total_fin_fer=(u_sbg_fin + g_sbg_fin) / 800.0,
            ldop_U_f0_fail=u_ld_f0,
            ldop_U_fin_fail=u_ld_fin,
            ldop_G_f0_fail=g_ld_f0,
            ldop_G_fin_fail=g_ld_fin,
            ldop_total_f0_fer=(u_ld_f0 + g_ld_f0) / 800.0,
            ldop_total_fin_fer=(u_ld_fin + g_ld_fin) / 800.0,
            paired_vs_ldop=dict(
                ldop_ok_sbg_fail=pu[0] + pg[0],
                ldop_ok_sbg_fail_U=pu[0],
                ldop_ok_sbg_fail_G=pg[0],
                ldop_fail_sbg_ok=pu[1] + pg[1],
                ldop_fail_sbg_ok_U=pu[1],
                ldop_fail_sbg_ok_G=pg[1],
                both_fail=pu[2] + pg[2],
                both_ok=pu[3] + pg[3],
            ),
        )
    sbg_t = np.array([r['sbg_cpu'] for r in new_rows], dtype=np.float64)
    ld_t = np.array([r['ldop_cpu'] for r in new_rows], dtype=np.float64)
    return dict(
        rho100_densified_curve=curve,
        timing_new_keys_sec=dict(
            n_new_keys=len(new_rows),
            sbg_mean=float(sbg_t.mean()),
            sbg_median=float(np.median(sbg_t)),
            sbg_p95=float(np.percentile(sbg_t, 95)),
            ldop_mean=float(ld_t.mean()),
        ),
    )


def render_results_md(res: dict[str, Any]) -> str:
    a = res['analysis']
    p = a['primary']
    hal = a['haldane_floor_sensitivity']
    curve = a['diagnostics']['rho100_densified_curve']

    def fval(x):
        if isinstance(x, list):
            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
        return x if isinstance(x, str) else f'{x:.4f}'

    lines = [
        '# Stage A8b Results: `3.50 / 3.75 dB` Densified 1% FER Verification (`SBGdop_dens` vs `CD2` and `ldop_dens`)',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- New keys: frames `41000–41399` × U/G, `ρ = 0.10`, new SNRs = `{res["_config"]["new_snrs"]}` (`{len(res["_config"]["new_snrs"])*800}` keys); merged `ρ = 0.10` grid = `{res["_config"]["merged_rho100_snrs"]}`',
        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (effective cap `{res["runtime"]["cpu_cap_core_hours"]:.4f} h`, cumulative task total `{res["runtime"]["cumulative_task_core_hours"]:.4f} / 10.0 h`, wall `{res["runtime"]["wall_seconds"]:.1f} s`)',
        '',
        '## Primary Verdict & Zero-Floor Sensitivity (LB >= 0.50 dB Gate)',
        '',
        '| Estimator / Floor | Point (dB) | 95% Paired CI (dB) | Verdict |',
        '|---|---:|---|---|',
        f'| **Primary `min CD2 − min SBGdop_dens` (`stageA2.crossing`, `1e-4` floor)** | **{fval(p["point_db"])}** | **[{fval(p["ci95_db"][0])}, {fval(p["ci95_db"][1])}]** | **{p["verdict"]}** |',
        f'| Sensitivity `min CD2 − min SBGdop_dens` (Haldane `0.5/400 = 1.25e-3` floor) | {fval(hal["primary_CD2_minus_SBGdop_dens"]["point_db"])} | [{fval(hal["primary_CD2_minus_SBGdop_dens"]["ci95_db"][0])}, {fval(hal["primary_CD2_minus_SBGdop_dens"]["ci95_db"][1])}] | **{hal["primary_CD2_minus_SBGdop_dens"]["verdict"]}** |',
    ]
    if hal.get('SBGdop_minus_ldop_rho100') is not None:
        hg = hal['SBGdop_minus_ldop_rho100']
        lines.append(
            f'| Sensitivity `SBGdop_dens(100) − ldop_dens(100)` (Haldane `1.25e-3` floor) | {fval(hg["point_db"])} | [{fval(hg["ci95_db"][0])}, {fval(hg["ci95_db"][1])}] | — |'
        )

    lines += [
        '',
        '## Crossings & Empirical Brackets (Frames 41000–41399, U/G Mean, dB)',
        '',
        '| Arm | ρ=0.10 | ρ=0.15 | ρ=0.20 | Best (dB) [95% CI] | Empirical Bracket @ ρ=0.10 (U / G) |',
        '|---|---:|---:|---:|---|---|',
    ]
    for arm in ('CD2', 'SBdop', 'SBGdop_A8', 'SBGdop_dens', 'ldop_dens', 's050', 's100'):
        if arm not in a['mean_crossing']:
            continue
        c10 = fval(a['mean_crossing'][arm].get('100', '—'))
        c15 = fval(a['mean_crossing'][arm].get('150', '—'))
        c20 = fval(a['mean_crossing'][arm].get('200', '—'))
        bc = a['best_crossings'][arm]
        br = a['empirical_brackets_rho100'].get(arm)
        br_s = f'`{br["U"]}` / `{br["G"]}`' if br else '—'
        lines.append(f'| {arm} | {c10} | {c15} | {c20} | **{fval(bc["best_db"])}** [{fval(bc["ci95_db"][0])}, {fval(bc["ci95_db"][1])}] | {br_s} |')

    lines += ['', '## Secondary Contrasts (`1e-4` floor, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
    for name, c in a['secondary_contrasts'].items():
        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')

    lines += [
        '',
        '## Complete `ρ = 0.10` Waterfall Table (`400` U + `400` G = `800` Draws/SNR)',
        '',
        '| SNR (dB) | Source | `SBG` MAE (U/G) | `SBG` >0.25 (U/G) | `SBGdop` F0 (U/G) | **`SBGdop` Final (U/G, %)** | `ldop` F0 (U/G) | **`ldop` Final (U/G, %)** | `ldop` ok->`SBG` fail (U/G) | `ldop` fail->`SBG` ok (U/G) |',
        '|---:|---|---|---|---|---|---|---|---:|---:|',
    ]
    for snr_k in sorted(curve.keys(), key=int):
        c = curve[snr_k]
        pv = c['paired_vs_ldop']
        lines.append(
            f'| {c["snr_db"]:.2f} | {c["source"]} | '
            f'{c["sbg_doppler_mean"]:.4f} (`{c["sbg_doppler_mean_U"]:.4f}/{c["sbg_doppler_mean_G"]:.4f}`) | '
            f'{100*c["sbg_outlier_frac"]:.2f}% (`{100*c["sbg_outlier_frac_U"]:.1f}%/{100*c["sbg_outlier_frac_G"]:.1f}%`) | '
            f'`{c["sbg_U_f0_fail"]}/{c["sbg_G_f0_fail"]}` (`{100*c["sbg_total_f0_fer"]:.2f}%`) | '
            f'**`{c["sbg_U_fin_fail"]}/{c["sbg_G_fin_fail"]}` (`{100*c["sbg_total_fin_fer"]:.2f}%`)** | '
            f'`{c["ldop_U_f0_fail"]}/{c["ldop_G_f0_fail"]}` (`{100*c["ldop_total_f0_fer"]:.2f}%`) | '
            f'**`{c["ldop_U_fin_fail"]}/{c["ldop_G_fin_fail"]}` (`{100*c["ldop_total_fin_fer"]:.2f}%`)** | '
            f'`{pv["ldop_ok_sbg_fail"]}` (`{pv["ldop_ok_sbg_fail_U"]}/{pv["ldop_ok_sbg_fail_G"]}`) | '
            f'`{pv["ldop_fail_sbg_ok"]}` (`{pv["ldop_fail_sbg_ok_U"]}/{pv["ldop_fail_sbg_ok_G"]}`) |'
        )
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
        raise RuntimeError('Refusing to run without passing stageA8b_gate.json')
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('stageA8b_gate.json own_md5 mismatch; re-run gates')
    if gate['_config']['pinned_code_md5'] != pinned_md5:
        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA8b_gate.json')

    gate_cpu_h = float(gate['gate_cpu_hours'])
    effective_cap_h = compute_effective_run_cap_hours(gate_cpu_h)
    effective_cap_sec = effective_cap_h * 3600.0
    if effective_cap_h <= 0.15:
        raise RuntimeError(f'Insufficient remaining cumulative core-hour budget: {effective_cap_h:.4f} h')

    new_snrs = tuple(int(s) for s in gate['selected']['new_snrs'])
    frozen_comps, crossing_fn = stageA6._load_frozen_comparators()
    a6_sb_fail, a6_pw_fail, _ = stageA8._load_a6_archives(BASE_A8_SNRS)
    a8_sbg_fail, a8_map = _load_a8_archives(BASE_A8_SNRS)
    a2_rho100 = _load_a2_rho100_map(BASE_A8_SNRS)

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
        f'Launching Stage A8b: {len(FRAMES)} frames x 2 scen x rho=100 x {len(new_snrs)} new SNRs '
        f'({new_snrs}) = {len(FRAMES)*2*len(new_snrs)} keys on {n_shards} workers '
        f'(effective_cap={effective_cap_h:.4f} h)...',
        flush=True,
    )
    try:
        for idx in range(n_shards):
            sub_frames = tuple(FRAMES[idx::n_shards])
            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_frames, new_snrs, raw_dir))
            p.start()
            running[p.sentinel] = (idx, p)
        while running:
            ready = wait(running, timeout=4.0)
            for r_ready in ready:
                idx, p = running.pop(r_ready)
                p.join()
                code = p.exitcode
                p.close()
                if code != 0:
                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= effective_cap_sec - 90.0:
                budget_hit = True
                break
    finally:
        for _, p in running.values():
            p.terminate()
        for _, p in running.values():
            p.join()
            p.close()
    if budget_hit or _used_cpu_seconds() >= effective_cap_sec:
        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    raw_md5: dict[str, str] = {}
    new_rows: list[dict[str, Any]] = []
    fi = {f: i for i, f in enumerate(FRAMES)}
    new_sbg_fail = np.zeros((len(FRAMES), 2, len(new_snrs)), dtype=bool)
    new_ldop_fail = np.zeros((len(FRAMES), 2, len(new_snrs)), dtype=bool)
    seen = np.zeros_like(new_sbg_fail)
    for idx in range(n_shards):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
        raw_md5[sp.name] = ar.md5_file(sp)
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                new_rows.append(r)
                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), new_snrs.index(int(r['snr'])))
                if seen[ix]:
                    raise RuntimeError(f'Duplicate Stage A8b key {r["frame"]} {r["scenario"]} {r["snr"]}')
                new_sbg_fail[ix] = int(r['arms']['SBGdop']['errors']) > 0
                new_ldop_fail[ix] = int(r['arms']['ldop']['errors']) > 0
                seen[ix] = True
    if not seen.all():
        raise RuntimeError('Incomplete Stage A8b failure grid')
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
    )

    arm_grids: dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]] = {
        arm: to_rho_grid_map(rhos, snrs, fail)
        for arm, (rhos, snrs, fail) in frozen_comps.items()
    }
    arm_grids['SBdop'] = to_rho_grid_map(stageA8.RHOS, BASE_A8_SNRS, a6_sb_fail)
    arm_grids['PWdop'] = to_rho_grid_map(stageA8.RHOS, BASE_A8_SNRS, a6_pw_fail)
    arm_grids['SBGdop_A8'] = to_rho_grid_map(stageA8.RHOS, BASE_A8_SNRS, a8_sbg_fail)

    merged_sbg_snrs, merged_sbg_100 = merge_rho_snrs(
        BASE_A8_SNRS, a8_sbg_fail[:, :, 0, :], new_snrs, new_sbg_fail
    )
    arm_grids['SBGdop_dens'] = {
        100: (merged_sbg_snrs, merged_sbg_100),
        150: (BASE_A8_SNRS, a8_sbg_fail[:, :, 1, :]),
    }

    ldop_base_map = dict(arm_grids['ldop'])
    ld_snrs_100, ld_fail_100 = ldop_base_map[100]
    merged_ld_snrs, merged_ld_100 = merge_rho_snrs(ld_snrs_100, ld_fail_100, new_snrs, new_ldop_fail)
    ldop_dens_map = dict(ldop_base_map)
    ldop_dens_map[100] = (merged_ld_snrs, merged_ld_100)
    arm_grids['ldop_dens'] = ldop_dens_map

    diagnostics = summarize_rho100_curve(new_rows, new_snrs, a8_map, a2_rho100)
    analysis = analyze_stageA8b(arm_grids, crossing_fn, diagnostics)

    total_cpu_h = _used_cpu_seconds() / 3600.0
    cum_cpu_h = PRIOR_CUMULATIVE_HOURS + gate_cpu_h + total_cpu_h
    if total_cpu_h >= effective_cap_h or cum_cpu_h >= TOTAL_TASK_CAP_HOURS:
        print(f'STOPPED_BUDGET after analysis (run={total_cpu_h:.4f} h, cum={cum_cpu_h:.4f} h)', flush=True)
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
            rho_dens=RHO_DENS,
            new_snrs=list(new_snrs),
            merged_rho100_snrs=list(merged_sbg_snrs),
            frames=[FRAMES[0], FRAMES[-1]],
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G1_passed=gate['G1']['passed'],
            G2_passed=gate['G2']['passed'],
            gate_cpu_hours=gate_cpu_h,
        ),
        runtime=dict(
            total_core_hours=total_cpu_h,
            prior_cumulative_core_hours=PRIOR_CUMULATIVE_HOURS,
            gate_core_hours=gate_cpu_h,
            cumulative_task_core_hours=cum_cpu_h,
            wall_seconds=time.monotonic() - wall_start,
            cpu_cap_core_hours=effective_cap_h,
        ),
        analysis=analysis,
    )
    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    p = analysis['primary']
    gap = analysis['secondary_contrasts']['SBGdop_dens_minus_ldop_dens_rho100']
    print(
        f'STAGEA8B_DONE verdict={p["verdict"]} D_dens={p["point_db"]} ci={p["ci95_db"]} '
        f'SBGdop_dens_best={p["arm_b_best_db"]} gap_vs_ldop={gap["point_db"]} '
        f'cpu_hours={total_cpu_h:.4f} cum_hours={cum_cpu_h:.4f}',
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
