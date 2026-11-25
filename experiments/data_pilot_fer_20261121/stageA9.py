"""Stage A9 (STAGEA9_PROTOCOL.md): does the round-0 semi-blind gain survive when delays are NOT given?

Evaluates truth-free Semi-Blind Joint delay+Doppler+gain estimation (`SBJ`, plus gain-vs-cost companions
`SBJ_lite` and `SBJ_ultra`), single-factor control (`Ctrl`: `CD2`'s own delay front end + `SBG` Doppler),
and `CD2` (no truth) on 320 completely unseen fresh confirmation frames (`41500-41819` x U/G = 640 realizations/cell),
with strict `obs = {'y', 'pilot', 'sigma2'}` architectural isolation, <= 0.50 dB empirical bracket verification
on every crossing, quiet single-core per-trigger CPU timing vs `CD2` and `HG`, and persistent ledger enforcement
of cumulative <= 20.0 core-hours across all deinlab runs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import copy
import fcntl
import gzip
import hashlib
import json
import math
import multiprocessing
from multiprocessing.connection import wait as mp_wait
import multiprocessing.reduction as mp_reduction
import os
from pathlib import Path
import platform
import re
import resource
import signal
import sys
import tempfile
import time
from time import perf_counter, process_time
from typing import Any

import numpy as np
from scipy.linalg import cho_factor, cho_solve, cholesky_banded, solve_triangular
from scipy.linalg.lapack import ctbtrs
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
HUANG_DIR = EXP / 'huang_steelman_20261124'
SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'
SAMEFRAME_CD2_DIR = EXP / 'sameframe_cd2_20261125'

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HUANG_DIR))
sys.path.insert(0, str(SAMEFRAME_HG_DIR))
sys.path.insert(0, str(SAMEFRAME_CD2_DIR))

import hs_arms as ar  # noqa: E402
import sameframe as sf  # noqa: E402
import sameframe_cd2 as sf2  # noqa: E402
import stageA6  # noqa: E402
import stageA7  # noqa: E402
import stageA8b  # noqa: E402

CONF_FRAMES = tuple(range(41500, 41820))  # 320 untouched confirmation frames (8 frames/shard x 40 shards)
G1_FRAMES = (41000, 41001, 41002, 41003)
G3_ISOLATION_FRAMES = tuple(range(40900, 40904))  # 4 untouched cost-projection frames (8 U/G realizations/cell)
SCENARIOS = ('U', 'G')
N_SHARDS = 40  # 8 frames per shard

NU_MIN, NU_MAX = -3.0, 3.0
GAIN_MIN, GAIN_MAX = -10.0, 10.0

BOOT_DRAWS = 2000
BOOT_SEED = 20261125
GO_THRESH_DB = 0.50
MAX_BRACKET_GAP_DB = 0.50
HG_TARGET_MS = 640.0

TOTAL_TASK_CAP_HOURS = 20.0
PRIOR_DEV_HOURS = 10.65  # Conservative ceiling of 10.6428h prior deinlab dev exploration
GATE_BUDGET_HOURS = 0.35  # Allows 4-frame G3 to finish measuring up to >25h extrapolated Tier-1 so compact tiers can be evaluated
TIMING_RESERVE_HOURS = 0.22
SAFETY_RESERVE_HOURS = 0.10
COST_MARGIN = 1.25
OVERHEAD_HOURS = 0.06
BUDGET_EXIT_CODE = 124
SIGTERM_EXIT_CODE = 143


def gate_poll_margin_sec(workers: int) -> float:
    """Upper-bounds 10s poll granularity across active gate workers plus gate summary overhead."""
    return float(12.0 * max(1, int(workers)) + 20.0)


def run_poll_margin_sec(workers: int) -> float:
    """Upper-bounds 10s poll granularity across active confirmation workers plus post-run bootstrap analysis."""
    return float(12.0 * max(1, int(workers)) + 60.0)


DEFAULT_LEDGER_PATH = (HERE / 'out' / 'stageA9' / 'cpu_ledger.jsonl').resolve()
DEFAULT_LOCK_PATH = (HERE / 'out' / 'stageA9' / '.exec.flock').resolve()

OWN_FILES = ('STAGEA9_PROTOCOL.md', 'stageA9.py', 'test_stageA9.py', 'stageA9_launch.sh')
PINNED_CODE_MD5 = {
    'data_pilot_fer_20261121/stageA.py': '17be1c3e75e07fb9a4dec1b3774c54aa',
    'data_pilot_fer_20261121/stageA2.py': '01a72e6942ec39de99c0e788b3b5b0a9',
    'data_pilot_fer_20261121/stageA3.py': '305645c21bf13b1bc35ec300aa1bcbb2',
    'data_pilot_fer_20261121/stageA5.py': '073b76973298fbd58ecb0ef38953c97d',
    'data_pilot_fer_20261121/stageA6.py': 'e7e42f0f941613d997c4f71b01b09777',
    'data_pilot_fer_20261121/stageA7.py': '1d6d6021d0e2bf36f1a368e8cc4e687a',
    'data_pilot_fer_20261121/stageA8.py': 'a24ca8b6746734d171dfe540b9baea31',
    'data_pilot_fer_20261121/stageA8b.py': '4ce95d0fcc214bfbdb45abff0e961883',
    'sameframe_hg_20261124/sameframe.py': '01197778b2ec3cf7f37719ca3b192152',
    'sameframe_cd2_20261125/sameframe_cd2.py': 'a4b17879bb0e55586d5473397e8b1f59',
    'huang_steelman_20261124/hs_arms.py': 'a43f2934c085bde1b69f929fddf06bf6',
    'huang_steelman_20261124/hs_analysis.py': '864b8b7510872c33dc60fc725c57a45d',
}

SBJ_CONFIGS = {
    'SBJ_ultra': dict(
        n_beams=1, n_seed_pairs=7, cand_top_k=4,
        swap_rounds=0, swap_slots=0, swap_cands=0,
        escape_peaks=1, post_escape=False, final_maxiter=8,
        include_pw=False, use_c64=True,
    ),
    'SBJ_lite': dict(
        n_beams=1, n_seed_pairs=10, cand_top_k=5,
        swap_rounds=1, swap_slots=3, swap_cands=5,
        escape_peaks=2, post_escape=False, final_maxiter=10,
        include_pw=False, use_c64=True,
    ),
    'SBJ': dict(
        n_beams=2, n_seed_pairs=12, cand_top_k=6,
        swap_rounds=1, swap_slots=3, swap_cands=5,
        escape_peaks=2, post_escape=True, final_maxiter=11,
        include_pw=True, use_c64=True,
    ),
}

TIER1_GRIDS: dict[str, dict[int, tuple[int, ...]]] = {
    'CD2': {
        100: (550, 600, 650, 700, 750, 800, 850, 900),
        150: (375, 425, 475, 525, 575),
        200: (375, 400, 425, 450, 500),
        250: (400, 450, 500, 550),
    },
    'Ctrl': {
        100: (450, 500, 550, 600, 650, 700, 750, 800, 850),
        200: (375, 400, 425, 450, 500),
    },
    'SBJ': {
        100: (325, 350, 375, 400, 425, 475),
        150: (325, 375, 425, 475),
    },
    'SBJ_lite': {
        100: (325, 350, 400, 450, 500),
        150: (325, 375, 425, 475),
    },
    'SBJ_ultra': {
        100: (350, 400, 450, 500, 550),
    },
}

TIER2_GRIDS: dict[str, dict[int, tuple[int, ...]]] = {
    'CD2': TIER1_GRIDS['CD2'],
    'Ctrl': TIER1_GRIDS['Ctrl'],
    'SBJ': TIER1_GRIDS['SBJ'],
    'SBJ_lite': {
        100: TIER1_GRIDS['SBJ_lite'][100],
    },
    'SBJ_ultra': TIER1_GRIDS['SBJ_ultra'],
}

TIER3_GRIDS: dict[str, dict[int, tuple[int, ...]]] = {
    'CD2': TIER1_GRIDS['CD2'],
    'Ctrl': TIER1_GRIDS['Ctrl'],
    'SBJ': TIER1_GRIDS['SBJ'],
    'SBJ_lite': {
        100: TIER1_GRIDS['SBJ_lite'][100],
    },
}

CANDIDATE_TIERS: tuple[tuple[str, dict[str, dict[int, tuple[int, ...]]]], ...] = (
    ('tier1_full', TIER1_GRIDS),
    ('tier2_compact', TIER2_GRIDS),
    ('tier3_core_gvc', TIER3_GRIDS),
)

TIMING_PANELS = (
    ('rho100_snr400', 100, 400, 20),  # 20 U + 20 G = 40 triggers
    ('rho200_snr450', 200, 450, 20),  # 20 U + 20 G = 40 triggers
)
TIMING_ARMS = ('CD', 'CD2', 'HG', 'Ctrl', 'SBJ_ultra', 'SBJ_lite', 'SBJ')


# --------------------------------------------------------------------------- Provenance & Persistent CPU Ledger
def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_pinned_code() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in PINNED_CODE_MD5.items():
        actual = ar.md5_file(EXP / rel)
        if actual != expected:
            raise RuntimeError(f'Pinned dependency MD5 mismatch for {rel}: {actual} != {expected}')
        out[rel] = actual
    return out


def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
    return stageA6.verify_freeze_commit_if_git(freeze_commit, live_own)


def canonical_ledger_path(*_args: Any, **_kwargs: Any) -> Path:
    """Single canonical repository-fixed ledger path shared across all invocations."""
    return DEFAULT_LEDGER_PATH


_ACTIVE_LOCK_FD: int | None = None
_WORKER_HELD_LOCK_FDS: list[int] = []


class _InheritedLockToken:
    """Passes the open flock file descriptor across POSIX `spawn` (`fork_exec` `passfds`) via `DupFd`
    so spawned workers hold the exact same kernel flock until the last worker process exits.
    """
    def __init__(self, fd: int | None):
        self.fd = None if fd is None else int(fd)

    def __reduce__(self):
        if self.fd is None:
            return (_rebuild_inherited_lock_token, (None,))
        return (_rebuild_inherited_lock_token, (mp_reduction.DupFd(self.fd),))


def _rebuild_inherited_lock_token(dup_fd) -> _InheritedLockToken:
    if dup_fd is None:
        return _InheritedLockToken(None)
    fd = int(dup_fd.detach())
    _WORKER_HELD_LOCK_FDS.append(fd)
    return _InheritedLockToken(fd)


def get_active_lock_fd() -> int | None:
    if _ACTIVE_LOCK_FD is not None:
        return _ACTIVE_LOCK_FD
    env_fd = os.environ.get('A9_EXEC_FLOCK_FD', '').strip()
    if env_fd.isdigit():
        fd = int(env_fd)
        try:
            os.fstat(fd)
            return fd
        except OSError:
            return None
    return None


@contextlib.contextmanager
def stage_execution_lock(lock_path: Path = DEFAULT_LOCK_PATH, *, inheritable: bool = False):
    """Process-safe non-blocking flock shared by stageA9_launch.sh and Python tests."""
    global _ACTIVE_LOCK_FD
    if os.environ.get('A9_EXEC_FLOCK_HELD', '').strip() == '1':
        yield
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open('a+', encoding='utf-8')
    os.set_inheritable(fh.fileno(), bool(inheritable))
    prev_fd = _ACTIVE_LOCK_FD
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f'Stage A9 execution lock already held: {lock_path}') from exc
        _ACTIVE_LOCK_FD = fh.fileno()
        yield
    finally:
        _ACTIVE_LOCK_FD = prev_fd
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


def current_attempt_id(mode: str) -> str:
    env_id = os.environ.get('A9_ATTEMPT_ID', '').strip()
    if env_id:
        return env_id
    return f'{mode}_{os.getpid()}_{int(time.time() * 1000)}'


def read_ledger_hours(
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    *,
    exclude_attempt_id: str | None = None,
) -> float:
    """Sum CPU hours across all attempts, deduplicating STARTED/SETTLED records per attempt_id.
    If an attempt crashed violently without any non-STARTED settlement, its reserved_hours is counted.
    """
    if not ledger_path.is_file():
        return 0.0
    by_attempt: dict[str, list[dict[str, Any]]] = {}
    legacy_idx = 0
    for line in ledger_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        aid = str(rec.get('attempt_id') or f'_legacy_{legacy_idx}')
        legacy_idx += 1
        if exclude_attempt_id is not None and aid == exclude_attempt_id:
            continue
        by_attempt.setdefault(aid, []).append(rec)

    total = 0.0
    for recs in by_attempt.values():
        shell_recs = [r for r in recs if str(r.get('status', '')) == 'SHELL_SETTLED']
        if shell_recs:
            clean = all(bool(r.get('reaped_all_workers', False)) for r in shell_recs)
        else:
            clean = any(bool(r.get('reaped_all_workers', False)) for r in recs)
        if clean:
            total += max(max(0.0, float(r.get('cpu_hours', 0.0))) for r in recs)
        else:
            total += max(
                max(0.0, float(r.get('reserved_hours', 0.0)), float(r.get('cpu_hours', 0.0)))
                for r in recs
            )
    return float(total)


def append_ledger_entry(
    ledger_path: Path,
    mode: str,
    status: str,
    cpu_hours: float,
    *,
    attempt_id: str | None = None,
    reserved_hours: float = 0.0,
    reaped_all_workers: bool = False,
) -> str:
    aid = attempt_id or current_attempt_id(mode)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(
        ts=round(time.time(), 3),
        pid=os.getpid(),
        attempt_id=aid,
        mode=mode,
        status=status,
        cpu_hours=float(max(0.0, cpu_hours)),
        reserved_hours=float(max(0.0, reserved_hours)),
        reaped_all_workers=bool(reaped_all_workers),
    )
    with ledger_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec, allow_nan=False) + '\n')
        fh.flush()
        os.fsync(fh.fileno())
    return aid


def _worker_entry_with_lock(lock_token: _InheritedLockToken, target_fn, user_args: tuple[Any, ...]):
    if hasattr(signal, 'pthread_sigmask'):
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    _ = lock_token  # Held in _WORKER_HELD_LOCK_FDS for the lifetime of the worker process
    return target_fn(*user_args)


def _run_sharded_supervised(
    target_fn,
    job_args: list[tuple[Any, ...]],
    max_workers: int,
    cpu_cap_sec: float,
    reap_state: dict[str, bool],
    *,
    lock_fd: int | None = None,
) -> None:
    """Spawn up to max_workers single-thread shard processes inheriting the kernel flock via DupFd,
    block SIGTERM/SIGINT across process registration + start() so zero signal window exists, and set
    `reap_state['clean'] = True` ONLY when 100% of started workers were join()-reaped without SIGKILL.
    """
    mp_ctx = multiprocessing.get_context('spawn')
    eff_lock_fd = lock_fd if lock_fd is not None else get_active_lock_fd()
    pending = list(job_args)
    running: dict[Any, tuple[int, multiprocessing.Process]] = {}
    all_spawned: list[multiprocessing.Process] = []
    budget_hit = False
    reap_state['clean'] = False
    sig_set = {signal.SIGTERM, signal.SIGINT}
    has_sigmask = hasattr(signal, 'pthread_sigmask')
    try:
        while pending or running:
            while pending and len(running) < max_workers:
                u_args = pending.pop(0)
                proc = mp_ctx.Process(
                    target=_worker_entry_with_lock,
                    args=(_InheritedLockToken(eff_lock_fd), target_fn, u_args),
                )
                old_mask = None
                if has_sigmask:
                    old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, sig_set)
                try:
                    all_spawned.append(proc)
                    proc.start()
                    running[proc.sentinel] = (u_args[0], proc)
                finally:
                    if has_sigmask and old_mask is not None:
                        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            ready = mp_wait(running, timeout=10.0)
            for r in ready:
                idx, proc = running.pop(r)
                proc.join()
                code = proc.exitcode
                if code != 0:
                    raise RuntimeError(f'Worker shard {idx:03d} failed with exit code {code}')
            live_cpu = sf._used_cpu_seconds() + sf._active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= cpu_cap_sec:
                budget_hit = True
                break
    finally:
        killed_any = False
        started_procs = [p for p in all_spawned if getattr(p, '_popen', None) is not None]
        for proc in started_procs:
            if proc.is_alive():
                proc.terminate()
        for proc in started_procs:
            proc.join(timeout=10.0)
            if proc.is_alive():
                killed_any = True
                proc.kill()
                proc.join()
        reap_state['clean'] = (not killed_any) and all(
            (p.exitcode is not None and p.exitcode != -int(signal.SIGKILL))
            for p in started_procs
        )
        for p in started_procs:
            with contextlib.suppress(Exception):
                p.close()
    if budget_hit or sf._used_cpu_seconds() >= cpu_cap_sec:
        print(f'STOPPED_BUDGET: CPU limit reached ({sf._used_cpu_seconds()/3600.0:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)


def admit_attempt(
    mode: str,
    freeze_commit: str,
    gate_path: Path,
    out_dir: Path,
    attempt_id: str,
    workers: int = 32,
    *,
    ledger_path: Path | None = None,
    check_env_and_pins: bool = True,
) -> tuple[float, int]:
    """Validate ALL CLI, thread-env, code-pin, artifact, and budget preconditions BEFORE writing STARTED
    or modifying any file. Returns `(reserved_hours, outer_timeout_sec)`.
    """
    if not 1 <= int(workers) <= 32:
        raise ValueError(f'workers must be in 1..32, got {workers}')
    if check_env_and_pins:
        if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
            raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
        ar.check_thread_env()
        pinned_md5 = verify_pinned_code()
        live_own = own_md5()
    else:
        pinned_md5 = {}
        live_own = {}

    lp = (ledger_path if ledger_path is not None else canonical_ledger_path()).resolve()
    prior_h = read_ledger_hours(lp, exclude_attempt_id=attempt_id)
    spent_h = PRIOR_DEV_HOURS + prior_h

    if mode == 'gate':
        res_h = GATE_BUDGET_HOURS
        if spent_h + res_h > TOTAL_TASK_CAP_HOURS:
            raise RuntimeError(
                f'Gate admission denied: spent={spent_h:.4f}h + gate_res={res_h:.4f}h > {TOTAL_TASK_CAP_HOURS:.2f}h'
            )
        timeout_sec = 900
    elif mode == 'run':
        if not re.fullmatch(r'[0-9a-f]{40}', freeze_commit):
            raise ValueError(f'Invalid freeze-commit: {freeze_commit!r}')
        raw_dir = out_dir / 'raw'
        if raw_dir.is_dir() and list(raw_dir.glob('rows_shard*.jsonl*')):
            raise RuntimeError(f'Run admission denied: shards already exist in {raw_dir}')
        if not gate_path.is_file():
            raise RuntimeError(f'Run admission denied: missing {gate_path}')
        gate = json.loads(gate_path.read_text(encoding='utf-8'))
        if not gate.get('all_passed') or not gate.get('selected'):
            raise RuntimeError('Run admission denied: stageA9_gate.json did not pass')
        if Path(gate['_config']['ledger_path']).resolve() != lp:
            raise RuntimeError(f'Ledger mismatch: gate used {gate["_config"]["ledger_path"]} != {lp}')
        if check_env_and_pins:
            verify_freeze_commit_if_git(freeze_commit, live_own)
            if gate['_config']['own_md5'] != live_own:
                raise RuntimeError('gate own_md5 differs from live Stage A9 files')
            if gate['_config']['pinned_code_md5'] != pinned_md5:
                raise RuntimeError('gate pinned_code_md5 differs from live upstream files')
        res_h = compute_effective_run_cap_hours(prior_h)
        poll_m = run_poll_margin_sec(workers)
        if res_h * 3600.0 - poll_m <= 60.0 or spent_h + res_h > TOTAL_TASK_CAP_HOURS:
            raise RuntimeError(f'Run admission denied: eff_cap_h={res_h:.4f}h insufficient for poll_margin={poll_m:.0f}s')
        timeout_sec = 3600
    elif mode == 'timing':
        if not re.fullmatch(r'[0-9a-f]{40}', freeze_commit):
            raise ValueError(f'Invalid freeze-commit: {freeze_commit!r}')
        results_path = out_dir / 'results.json'
        if not results_path.is_file():
            raise RuntimeError(f'Timing admission denied: missing {results_path}')
        results = json.loads(results_path.read_text(encoding='utf-8'))
        if results['_config']['freeze_commit'] != freeze_commit:
            raise RuntimeError('timing freeze-commit differs from results.json')
        if Path(results['_config']['ledger_path']).resolve() != lp:
            raise RuntimeError('timing ledger_path differs from results.json')
        if check_env_and_pins:
            verify_freeze_commit_if_git(freeze_commit, live_own)
            if results['_config']['own_md5'] != live_own:
                raise RuntimeError('timing own_md5 differs from results.json')
        res_h = min(TIMING_RESERVE_HOURS, max(0.0, TOTAL_TASK_CAP_HOURS - spent_h - 0.01))
        if res_h * 3600.0 < 120.0 or spent_h + res_h > TOTAL_TASK_CAP_HOURS:
            raise RuntimeError(f'Timing admission denied: timing_cap_h={res_h:.4f}h insufficient')
        timeout_sec = max(60, int(math.floor(res_h * 3600.0)) - 10)
    else:
        raise ValueError(f'Unknown mode {mode!r}')

    append_ledger_entry(
        lp, mode, 'STARTED', 0.0,
        attempt_id=attempt_id, reserved_hours=res_h, reaped_all_workers=False,
    )
    return float(res_h), int(timeout_sec)


def compute_effective_run_cap_hours(prior_ledger_hours: float) -> float:
    rem = (
        TOTAL_TASK_CAP_HOURS
        - PRIOR_DEV_HOURS
        - max(0.0, float(prior_ledger_hours))
        - TIMING_RESERVE_HOURS
        - SAFETY_RESERVE_HOURS
    )
    return float(max(0.0, rem))


def select_confirmation_tier(
    tier_cpu_per_frame: dict[str, float],
    effective_cap_hours: float,
    *,
    n_conf_frames: int = len(CONF_FRAMES),
    margin: float = COST_MARGIN,
    overhead_hours: float = OVERHEAD_HOURS,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    candidates = []
    for tier_name, grids in CANDIDATE_TIERS:
        sec_per_frame = float(tier_cpu_per_frame[tier_name])
        raw_h = sec_per_frame * float(n_conf_frames) / 3600.0
        proj_h = raw_h * margin + overhead_hours
        candidates.append(dict(
            tier=tier_name,
            grids={arm: {str(r): list(snrs) for r, snrs in rmap.items()} for arm, rmap in grids.items()},
            cpu_sec_per_frame=sec_per_frame,
            raw_hours=raw_h,
            projected_hours_with_margin=proj_h,
            within_budget=bool(proj_h <= effective_cap_hours),
        ))
    selected = next((c for c in candidates if c['within_budget']), None)
    return candidates, selected


# --------------------------------------------------------------------------- Static Tables & Strict `obs`-Only Math
def build_static_tables(n: int, lmax: int, c1: float, c2: float, nu_step: float = 0.05) -> dict[str, Any]:
    k = np.arange(n, dtype=np.int64)
    L = lmax + 1
    cp_all = np.ones((L, n), dtype=np.complex128)
    cols_all = np.empty((L, n), dtype=np.int64)
    for l in range(L):
        cols_all[l] = (k - l) % n
        if l > 0:
            kk = k[:l]
            cp_all[l, :l] = np.exp(2j * np.pi * c1 * (n * n + 2 * n * (kk - l)))
    n_nu = int(round((NU_MAX - NU_MIN) / nu_step)) + 1
    nu_grid = np.linspace(NU_MIN, NU_MAX, n_nu)
    k_norm = 2j * np.pi * k / float(n)
    E_pos = np.exp(np.outer(k_norm.imag, nu_grid) * 1j)
    E_conj = np.conj(E_pos)
    align_grid = np.linspace(NU_MIN, NU_MAX, 121)
    E_align_conj = np.exp(-np.outer(k_norm.imag, align_grid) * 1j)
    return dict(
        n=n, lmax=lmax, L=L, c1=float(c1), c2=float(c2), k=k, k_norm=k_norm,
        cp_all=cp_all, cols_all=cols_all,
        nu_grid=nu_grid, E_pos=E_pos, E_conj=E_conj,
        align_grid=align_grid, E_align_conj=E_align_conj,
    )


def unpack_obs_unit_power(obs: dict[str, Any], c1: float, c2: float) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Recover unit-power DAFT quantities strictly from obs = {'y', 'pilot', 'sigma2'}."""
    from physical import daft

    if set(obs.keys()) != {'y', 'pilot', 'sigma2'}:
        raise ValueError(f'obs must contain strictly {{y, pilot, sigma2}}, got {sorted(obs.keys())}')
    y_obs = np.asarray(obs['y'], dtype=np.complex128)
    p_obs = np.asarray(obs['pilot'], dtype=np.complex128)
    s2_obs = float(obs['sigma2'])
    if y_obs.ndim != 1 or p_obs.shape != y_obs.shape or len(y_obs) == 0:
        raise ValueError('Invalid y/pilot shape in obs')
    if not (np.isfinite(y_obs).all() and np.isfinite(p_obs).all() and np.isfinite(s2_obs) and s2_obs > 0.0):
        raise ValueError('Nonfinite or non-positive noise variance in obs')

    pilot_power_obs = float(np.mean(np.abs(p_obs) ** 2))
    scale = 1.0 / np.sqrt(pilot_power_obs + 0.5)  # Exact identity: scale == sqrt(2 * (1 - rho))
    r = daft(y_obs * scale, c1, c2, True)
    p_t = daft(p_obs * scale, c1, c2, True)
    vd = 0.5 * (scale * scale)
    sigma2 = s2_obs * (scale * scale)
    return r, p_t, float(vd), float(sigma2)


def comp_nll_c64(
    tabs: dict[str, Any],
    delays: np.ndarray,
    nu: np.ndarray,
    g: np.ndarray,
    p_t: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    *,
    diag_floor: float = 0.0,
    need_alpha: bool = False,
) -> tuple[float, np.ndarray | None]:
    n = tabs['n']
    l_arr = np.asarray(delays, dtype=np.int64)
    p = len(l_arr)
    cp = tabs['cp_all'][l_arr]
    spt = p_t[tabs['cols_all'][l_arr]]
    c_mat = cp * np.exp(np.outer(nu, tabs['k_norm']))
    e = r - np.sum((g[:, None] * c_mat) * spt, axis=0)
    d0 = max(float(diag_floor), float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2)))
    if d0 <= 0.0 or not np.isfinite(d0):
        return 1e30, None
    B = int(l_arr.max() - l_arr.min()) if p > 1 else 0
    if p == 1 or B == 0:
        if p == 1:
            return float(n * np.log(d0) + np.vdot(e, e).real / d0), (e / d0 if need_alpha else None)
        v_tot = float(sigma2) + float(vd) * float(np.mean(np.abs(np.sum(g[:, None] * c_mat, axis=0)) ** 2))
        d_use = max(d0, v_tot)
        return float(n * np.log(d_use) + np.vdot(e, e).real / d_use), (e / d_use if need_alpha else None)

    N1 = n - B
    ab = np.zeros((B + 1, N1), dtype=np.complex64)
    ab[0, :] = d0
    gc = (float(vd) * (g[:, None] * c_mat)).astype(np.complex64)
    gcc = np.conj(g[:, None] * c_mat).astype(np.complex64)
    for i in range(p):
        li = int(l_arr[i])
        for j in range(i + 1, p):
            lj = int(l_arr[j])
            if li == lj:
                ab[0, :] += gc[i, :N1] * gcc[j, :N1] + gc[j, :N1] * gcc[i, :N1]
            elif li > lj:
                d = li - lj
                ab[d, :N1 - d] += gc[i, d:N1] * gcc[j, :N1 - d]
            else:
                d = lj - li
                ab[d, :N1 - d] += gc[j, d:N1] * gcc[i, :N1 - d]
    try:
        Lb = cholesky_banded(ab, lower=True, overwrite_ab=True, check_finite=False)
        d_lb = Lb[0].real
        if np.any(d_lb <= 0.0) or not np.isfinite(d_lb).all():
            return 1e30, None
        e1_64 = e[:N1].astype(np.complex64)[:, None]
        y1, info1 = ctbtrs(Lb, e1_64, uplo='L', trans='N', diag='N')
        if info1 != 0:
            return 1e30, None
    except Exception:
        return 1e30, None
    logdet1 = 2.0 * float(np.sum(np.log(d_lb.astype(np.float64))))
    e2 = e[N1:]
    nll = logdet1 + float(np.vdot(y1, y1).real) + B * np.log(d0) + float(np.vdot(e2, e2).real) / d0
    if not np.isfinite(nll):
        return 1e30, None
    if not need_alpha:
        return float(nll), None
    a1, info2 = ctbtrs(Lb, y1, uplo='L', trans='C', diag='N')
    if info2 != 0:
        return 1e30, None
    alpha = np.empty(n, dtype=np.complex128)
    alpha[:N1] = a1[:, 0].astype(np.complex128)
    alpha[N1:] = e2 / d0
    return float(nll), alpha


def prepare_step_cache(tabs: dict[str, Any], cur_l, cur_nu, cur_g, p_t: np.ndarray, r: np.ndarray, vd: float) -> dict[str, Any]:
    n = tabs['n']
    l_arr = np.asarray(cur_l, dtype=np.int64)
    g_arr = np.asarray(cur_g, dtype=np.complex128)
    m = len(l_arr)
    cp = tabs['cp_all'][l_arr]
    spt = p_t[tabs['cols_all'][l_arr]]
    c_mat = cp * np.exp(np.outer(cur_nu, tabs['k_norm']))
    e_base = r - np.sum((g_arr[:, None] * c_mat) * spt, axis=0)
    g2_base = float(np.sum(np.abs(g_arr) ** 2))
    gc = (float(vd) * (g_arr[:, None] * c_mat)).astype(np.complex64)
    gcc = np.conj(g_arr[:, None] * c_mat).astype(np.complex64)
    pair_terms = []
    for i in range(m):
        li = int(l_arr[i])
        for j in range(i + 1, m):
            lj = int(l_arr[j])
            if li == lj:
                pair_terms.append((0, gc[i] * gcc[j] + gc[j] * gcc[i]))
            elif li > lj:
                d = li - lj
                pair_terms.append((d, gc[i, d:n] * gcc[j, :n - d]))
            else:
                d = lj - li
                pair_terms.append((d, gc[j, d:n] * gcc[i, :n - d]))
    return dict(
        n=n, l_arr=l_arr, min_l=int(l_arr.min()), max_l=int(l_arr.max()),
        c_mat=c_mat, e_base=e_base, g2_base=g2_base, gc=gc, gcc=gcc, pair_terms=pair_terms,
    )


def eval_step_cand_c64(
    tabs: dict[str, Any],
    cache: dict[str, Any],
    lc: int,
    gi_c: int,
    gc_val: complex,
    p_t: np.ndarray,
    vd: float,
    sigma2: float,
    diag_floor: float = 0.0,
) -> float:
    n = cache['n']
    c_new = tabs['cp_all'][lc] * tabs['E_pos'][:, gi_c]
    e = cache['e_base'] - gc_val * c_new * p_t[tabs['cols_all'][lc]]
    d0 = max(float(diag_floor), float(sigma2) + float(vd) * (cache['g2_base'] + abs(gc_val) ** 2))
    B = max(cache['max_l'], lc) - min(cache['min_l'], lc)
    if B == 0:
        return float(n * np.log(d0) + np.vdot(e, e).real / d0)
    N1 = n - B
    ab = np.zeros((B + 1, N1), dtype=np.complex64)
    ab[0, :] = d0
    for d, vec in cache['pair_terms']:
        ab[d, :N1 - d] += vec[:N1 - d]
    gc_new = (float(vd) * (gc_val * c_new)).astype(np.complex64)
    gcc_new = np.conj(gc_val * c_new).astype(np.complex64)
    gc_old, gcc_old = cache['gc'], cache['gcc']
    for i, li in enumerate(cache['l_arr']):
        li = int(li)
        if li == lc:
            ab[0, :] += gc_old[i, :N1] * gcc_new[:N1] + gc_new[:N1] * gcc_old[i, :N1]
        elif li > lc:
            d = li - lc
            ab[d, :N1 - d] += gc_old[i, d:N1] * gcc_new[:N1 - d]
        else:
            d = lc - li
            ab[d, :N1 - d] += gc_new[d:N1] * gcc_old[i, :N1 - d]
    try:
        Lb = cholesky_banded(ab, lower=True, overwrite_ab=True, check_finite=False)
        d_lb = Lb[0].real
        if np.any(d_lb <= 0.0) or not np.isfinite(d_lb).all():
            return 1e30
        e1_64 = e[:N1].astype(np.complex64)[:, None]
        y1, info1 = ctbtrs(Lb, e1_64, uplo='L', trans='N', diag='N')
        if info1 != 0:
            return 1e30
    except Exception:
        return 1e30
    logdet1 = 2.0 * float(np.sum(np.log(d_lb.astype(np.float64))))
    e2 = e[N1:]
    nll = logdet1 + float(np.vdot(y1, y1).real) + B * np.log(d0) + float(np.vdot(e2, e2).real) / d0
    return float(nll) if np.isfinite(nll) else 1e30


def cyclic_nll_c64(
    tabs: dict[str, Any],
    delays: np.ndarray,
    nu: np.ndarray,
    g: np.ndarray,
    p_t: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
) -> float:
    import stageA5

    n = tabs['n']
    l_arr = np.asarray(delays, dtype=np.int64)
    p = len(l_arr)
    cp = tabs['cp_all'][l_arr]
    spt = p_t[tabs['cols_all'][l_arr]]
    c_mat = cp * np.exp(np.outer(nu, tabs['k_norm']))
    e = r - np.sum((g[:, None] * c_mat) * spt, axis=0)
    B = int(l_arr.max() - l_arr.min()) if p > 1 else 0
    if p == 1 or B == 0 or B >= n // 3:
        geom = stageA5.precompute_delay_geometry(l_arr, n, tabs['c1'])
        th = np.concatenate([np.asarray(nu, float), np.real(g), np.imag(g)])
        return float(stageA5.sb_nll_and_grad(th, geom, spt, r, vd, sigma2)[0])

    N1 = n - B
    ab = np.zeros((B + 1, N1), dtype=np.complex64)
    C12 = np.zeros((N1, B), dtype=np.complex64)
    C22 = np.zeros((B, B), dtype=np.complex64)
    d0 = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
    ab[0, :] = d0
    idx_B = np.arange(B)
    C22[idx_B, idx_B] = d0
    gc = (float(vd) * (g[:, None] * c_mat)).astype(np.complex64)
    gcc = np.conj(g[:, None] * c_mat).astype(np.complex64)
    for i in range(p):
        li = int(l_arr[i])
        for j in range(i + 1, p):
            lj = int(l_arr[j])
            if li == lj:
                cross0 = gc[i] * gcc[j] + gc[j] * gcc[i]
                ab[0, :] += cross0[:N1]
                C22[idx_B, idx_B] += cross0[N1:]
                continue
            hi, lo, d = (i, j, li - lj) if li > lj else (j, i, lj - li)
            ab[d, :N1 - d] += gc[hi, d:N1] * gcc[lo, :N1 - d]
            kk = np.arange(d)
            C12[kk, (B - d) + kk] += gc[hi, :d] * gcc[lo, n - d:]
            C12[(N1 - d) + kk, kk] += gc[lo, N1 - d:N1] * gcc[hi, N1:N1 + d]
            if d < B:
                rr = np.arange(d, B)
                v22 = gc[hi, N1 + d:n] * gcc[lo, N1:n - d]
                C22[rr, rr - d] += v22
                C22[rr - d, rr] += np.conj(v22)
    try:
        Lb = cholesky_banded(ab, lower=True, overwrite_ab=True, check_finite=False)
        d_lb = Lb[0].real
        if np.any(d_lb <= 0.0) or not np.isfinite(d_lb).all():
            return 1e30
        V, info = ctbtrs(Lb, C12, uplo='L', trans='N', diag='N')
        if info != 0:
            return 1e30
        S = C22 - V.conj().T @ V
        LS, _ = cho_factor(S, lower=True, overwrite_a=True, check_finite=False)
        dLS = np.diag(LS).real
        if np.any(dLS <= 0.0) or not np.isfinite(dLS).all():
            return 1e30
        e1_64 = e[:N1].astype(np.complex64)[:, None]
        y1, info1 = ctbtrs(Lb, e1_64, uplo='L', trans='N', diag='N')
        if info1 != 0:
            return 1e30
        y1 = y1[:, 0]
        rhs2 = e[N1:].astype(np.complex64) - V.conj().T @ y1
        alpha2 = cho_solve((LS, True), rhs2, check_finite=False)
    except Exception:
        return 1e30
    logdet = 2.0 * (float(np.sum(np.log(d_lb.astype(np.float64)))) + float(np.sum(np.log(dLS.astype(np.float64)))))
    val = logdet + float(np.vdot(y1, y1).real + np.vdot(rhs2, alpha2).real)
    return val if np.isfinite(val) else 1e30


def prepare_cyclic_grad_geom(tabs: dict[str, Any], delays: np.ndarray, use_c64: bool = True) -> dict[str, Any]:
    import stageA5

    n = tabs['n']
    l_arr = np.asarray(delays, dtype=np.int64)
    p = len(l_arr)
    B = int(l_arr.max() - l_arr.min()) if p > 1 else 0
    b_blk = max(B, 64)
    if p <= 1 or B == 0 or b_blk >= n // 3 or (n - B) // b_blk < 3:
        geom = stageA5.precompute_delay_geometry(l_arr, n, tabs['c1'])
        return dict(stageA7.prepare_fast_geom(geom), flat_ok=False)

    cp = tabs['cp_all'][l_arr]
    cols = tabs['cols_all'][l_arr]
    N1 = n - B
    n_full = N1 // b_blk
    rem = N1 % b_blk
    sizes = [b_blk] * (n_full - 1) + [b_blk + rem]
    M = len(sizes)
    starts = np.cumsum([0] + sizes[:-1]).tolist()
    ends = np.cumsum(sizes).tolist()
    blk_id = np.empty(N1, dtype=np.int64)
    blk_off = np.empty(N1, dtype=np.int64)
    for m_i, (s0, e0) in enumerate(zip(starts, ends)):
        blk_id[s0:e0] = m_i
        blk_off[s0:e0] = np.arange(e0 - s0, dtype=np.int64)

    off_D, off_E = [], []
    pos = 0
    diag_flat_idx = np.empty(n, dtype=np.int64)
    for m_i, sz in enumerate(sizes):
        off_D.append(pos)
        ar_sz = np.arange(sz, dtype=np.int64)
        diag_flat_idx[starts[m_i]:ends[m_i]] = pos + ar_sz * sz + ar_sz
        pos += sz * sz
    for m_i in range(M - 1):
        off_E.append(pos)
        pos += sizes[m_i + 1] * sizes[m_i]
    off_12_top = pos
    pos += sizes[0] * B
    off_12_bot = pos
    pos += sizes[M - 1] * B
    off_22 = pos
    ar_B = np.arange(B, dtype=np.int64)
    diag_flat_idx[N1:] = off_22 + ar_B * B + ar_B
    pos += B * B
    flat_size = pos
    k = tabs['k']

    def map_rc(r_arr, c_arr):
        f_idx = np.empty(len(r_arr), dtype=np.int64)
        conj_f = np.zeros(len(r_arr), dtype=bool)
        in11 = (r_arr < N1) & (c_arr < N1)
        if in11.any():
            ri, ci = r_arr[in11], c_arr[in11]
            br, bc = blk_id[ri], blk_id[ci]
            orr, occ = blk_off[ri], blk_off[ci]
            f11 = np.empty(len(ri), dtype=np.int64)
            c11 = np.zeros(len(ri), dtype=bool)
            for b_i in range(M):
                s_same = (br == b_i) & (bc == b_i)
                if s_same.any():
                    f11[s_same] = off_D[b_i] + orr[s_same] * sizes[b_i] + occ[s_same]
            for b_i in range(M - 1):
                s_sub = (br == b_i + 1) & (bc == b_i)
                if s_sub.any():
                    f11[s_sub] = off_E[b_i] + orr[s_sub] * sizes[b_i] + occ[s_sub]
                s_sup = (br == b_i) & (bc == b_i + 1)
                if s_sup.any():
                    f11[s_sup] = off_E[b_i] + occ[s_sup] * sizes[b_i] + orr[s_sup]
                    c11[s_sup] = True
            f_idx[in11] = f11
            conj_f[in11] = c11
        in12 = (r_arr < N1) & (c_arr >= N1)
        if in12.any():
            ri, ci = r_arr[in12], c_arr[in12] - N1
            br, orr = blk_id[ri], blk_off[ri]
            f12 = np.empty(len(ri), dtype=np.int64)
            s0 = br == 0
            if s0.any():
                f12[s0] = off_12_top + orr[s0] * B + ci[s0]
            sM = br == (M - 1)
            if sM.any():
                f12[sM] = off_12_bot + orr[sM] * B + ci[sM]
            f_idx[in12] = f12
        in21 = (r_arr >= N1) & (c_arr < N1)
        if in21.any():
            ri, ci = r_arr[in21] - N1, c_arr[in21]
            bc, occ = blk_id[ci], blk_off[ci]
            f21 = np.empty(len(ri), dtype=np.int64)
            s0 = bc == 0
            if s0.any():
                f21[s0] = off_12_top + occ[s0] * B + ri[s0]
            sM = bc == (M - 1)
            if sM.any():
                f21[sM] = off_12_bot + occ[sM] * B + ri[sM]
            f_idx[in21] = f21
            conj_f[in21] = True
        in22 = (r_arr >= N1) & (c_arr >= N1)
        if in22.any():
            ri, ci = r_arr[in22] - N1, c_arr[in22] - N1
            f_idx[in22] = off_22 + ri * B + ci
        return f_idx, conj_f

    sc_dst, sc_i, sc_j, sc_k, sc_m = [], [], [], [], []
    gather_f = np.empty((p, p, n), dtype=np.int64)
    gather_conj = np.zeros((p, p, n), dtype=bool)
    m_mat = np.empty((p, p, n), dtype=np.int64)
    for i in range(p):
        for j in range(p):
            m = (k - l_arr[i] + l_arr[j]) % n
            m_mat[i, j] = m
            fi, cf = map_rc(m, k)
            gather_f[i, j] = fi
            gather_conj[i, j] = cf
            if i != j:
                fb, cfb = map_rc(k, m)
                kb = ~cfb
                sc_dst.append(fb[kb])
                sc_i.append(np.full(int(kb.sum()), i, dtype=np.int64))
                sc_j.append(np.full(int(kb.sum()), j, dtype=np.int64))
                sc_k.append(k[kb])
                sc_m.append(m[kb])

    cdtype = np.complex64 if use_c64 else np.complex128
    return dict(
        n=n, p=p, k=k, k_norm=tabs['k_norm'], delays=l_arr, cp=cp, cols=cols,
        flat_ok=True, use_c64=use_c64, cdtype=cdtype,
        B=B, N1=N1, M=M, sizes=sizes, starts=starts, ends=ends,
        flat_size=flat_size, diag_flat_idx=diag_flat_idx,
        off_D=off_D, off_E=off_E, off_12_top=off_12_top, off_12_bot=off_12_bot, off_22=off_22,
        sc_dst=np.concatenate(sc_dst), sc_i=np.concatenate(sc_i), sc_j=np.concatenate(sc_j),
        sc_k=np.concatenate(sc_k), sc_m=np.concatenate(sc_m),
        gather_f=gather_f, gather_conj=gather_conj, m_mat=m_mat,
        eyes=[np.eye(sz, dtype=cdtype) for sz in sizes],
        eye_B=np.eye(B, dtype=cdtype),
        _flat_C=np.zeros(flat_size, dtype=cdtype),
        _flat_Inv=np.empty(flat_size, dtype=cdtype),
    )


def cyclic_nll_and_grad(
    theta: np.ndarray,
    fgeom: dict[str, Any],
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
) -> tuple[float, np.ndarray]:
    import stageA5

    if not fgeom.get('flat_ok', False):
        return stageA7.sb_nll_and_grad_fast(theta, fgeom, shifted_pt, r, vd, sigma2, stageA5)
    p = fgeom['p']
    cdtype = fgeom['cdtype']
    B, N1, M = fgeom['B'], fgeom['N1'], fgeom['M']
    sizes, starts, ends = fgeom['sizes'], fgeom['starts'], fgeom['ends']
    off_D, off_E = fgeom['off_D'], fgeom['off_E']
    off_12_top, off_12_bot, off_22 = fgeom['off_12_top'], fgeom['off_12_bot'], fgeom['off_22']

    nu = theta[:p]
    g = theta[p:2 * p] + 1j * theta[2 * p:3 * p]
    c_mat = fgeom['cp'] * np.exp(np.outer(nu, fgeom['k_norm']))

    flat_C = fgeom['_flat_C']
    flat_C.fill(0.0)
    flat_C[fgeom['diag_flat_idx']] = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
    gc_all = (float(vd) * (g[:, None] * c_mat)).astype(cdtype)
    gcc_all = np.conj(g[:, None] * c_mat).astype(cdtype)
    np.add.at(flat_C, fgeom['sc_dst'], gc_all[fgeom['sc_i'], fgeom['sc_k']] * gcc_all[fgeom['sc_j'], fgeom['sc_m']])

    L_blks, Linv_blks, G_blks, F_blks = [], [], [], []
    sz0 = sizes[0]
    D_cur = flat_C[off_D[0]:off_D[0] + sz0 * sz0].reshape(sz0, sz0).copy()
    for m_i in range(M):
        sz = sizes[m_i]
        try:
            Lm, _ = cho_factor(D_cur, lower=True, overwrite_a=True, check_finite=False)
        except Exception:
            return 1e30, np.zeros(3 * p, dtype=np.float64)
        dL = np.diag(Lm).real
        if np.any(dL <= 0.0) or not np.isfinite(dL).all():
            return 1e30, np.zeros(3 * p, dtype=np.float64)
        Lm_tril = np.tril(Lm)
        Linv = solve_triangular(Lm_tril, fgeom['eyes'][m_i], lower=True, check_finite=False)
        L_blks.append(Lm_tril)
        Linv_blks.append(Linv)
        if m_i < M - 1:
            sz_n = sizes[m_i + 1]
            Em = flat_C[off_E[m_i]:off_E[m_i] + sz_n * sz].reshape(sz_n, sz)
            Gm = Em @ Linv.conj().T
            Fm = Linv.conj().T @ Gm.conj().T
            G_blks.append(Gm)
            F_blks.append(Fm)
            D_next = flat_C[off_D[m_i + 1]:off_D[m_i + 1] + sz_n * sz_n].reshape(sz_n, sz_n)
            D_cur = D_next - Gm @ Gm.conj().T

    C12_top = flat_C[off_12_top:off_12_top + sizes[0] * B].reshape(sizes[0], B)
    C12_bot = flat_C[off_12_bot:off_12_bot + sizes[M - 1] * B].reshape(sizes[M - 1], B)
    V_blks = [None] * M
    V_blks[0] = Linv_blks[0] @ C12_top
    for m_i in range(1, M - 1):
        V_blks[m_i] = -Linv_blks[m_i] @ (G_blks[m_i - 1] @ V_blks[m_i - 1])
    V_blks[M - 1] = Linv_blks[M - 1] @ (C12_bot - G_blks[M - 2] @ V_blks[M - 2])
    V = np.vstack(V_blks)

    C22 = flat_C[off_22:off_22 + B * B].reshape(B, B)
    S = C22 - V.conj().T @ V
    try:
        LS, _ = cho_factor(S, lower=True, overwrite_a=True, check_finite=False)
    except Exception:
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    dLS = np.diag(LS).real
    if np.any(dLS <= 0.0) or not np.isfinite(dLS).all():
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    LS_tril = np.tril(LS)
    LS_inv = solve_triangular(LS_tril, fgeom['eye_B'], lower=True, check_finite=False)

    logdet = 2.0 * (
        sum(float(np.sum(np.log(np.diag(Lm).real.astype(np.float64)))) for Lm in L_blks)
        + float(np.sum(np.log(dLS.astype(np.float64))))
    )
    e = r - np.sum((g[:, None] * c_mat) * shifted_pt, axis=0)
    ec = e.astype(cdtype)
    y1_blks = [None] * M
    y1_blks[0] = Linv_blks[0] @ ec[starts[0]:ends[0]]
    for m_i in range(1, M):
        y1_blks[m_i] = Linv_blks[m_i] @ (ec[starts[m_i]:ends[m_i]] - G_blks[m_i - 1] @ y1_blks[m_i - 1])
    y1 = np.concatenate(y1_blks)
    y2 = LS_inv @ (ec[N1:] - V.conj().T @ y1)
    nll = logdet + float(
        np.vdot(y1.astype(np.complex128), y1.astype(np.complex128)).real
        + np.vdot(y2.astype(np.complex128), y2.astype(np.complex128)).real
    )
    if not np.isfinite(nll):
        return 1e30, np.zeros(3 * p, dtype=np.float64)

    alpha2 = LS_inv.conj().T @ y2
    RHS_back = np.empty((N1, B + 1), dtype=cdtype)
    RHS_back[:, :B] = V @ LS_inv.conj().T
    RHS_back[:, B] = y1 - V @ alpha2

    X_back = [None] * M
    X_back[M - 1] = Linv_blks[M - 1].conj().T @ RHS_back[starts[M - 1]:ends[M - 1]]
    for m_i in range(M - 2, -1, -1):
        X_back[m_i] = Linv_blks[m_i].conj().T @ RHS_back[starts[m_i]:ends[m_i]] - F_blks[m_i] @ X_back[m_i + 1]
    U_all = np.vstack(X_back)
    U = U_all[:, :B]
    alpha_c = np.concatenate([U_all[:, B], alpha2])
    alpha = alpha_c.astype(np.complex128)

    Z_diag = [None] * M
    Z_sub = [None] * (M - 1)
    Z_diag[M - 1] = Linv_blks[M - 1].conj().T @ Linv_blks[M - 1]
    for m_i in range(M - 2, -1, -1):
        Z_sub[m_i] = -Z_diag[m_i + 1] @ F_blks[m_i].conj().T
        Z_diag[m_i] = Linv_blks[m_i].conj().T @ Linv_blks[m_i] - F_blks[m_i] @ Z_sub[m_i]

    flat_Inv = fgeom['_flat_Inv']
    for m_i in range(M):
        sz = sizes[m_i]
        Um = U[starts[m_i]:ends[m_i]]
        flat_Inv[off_D[m_i]:off_D[m_i] + sz * sz] = (Z_diag[m_i] + Um @ Um.conj().T).ravel()
        if m_i < M - 1:
            sz_n = sizes[m_i + 1]
            flat_Inv[off_E[m_i]:off_E[m_i] + sz_n * sz] = (Z_sub[m_i] + U[starts[m_i + 1]:ends[m_i + 1]] @ Um.conj().T).ravel()
    flat_Inv[off_12_top:off_12_top + sizes[0] * B] = (-U[starts[0]:ends[0]] @ LS_inv).ravel()
    flat_Inv[off_12_bot:off_12_bot + sizes[M - 1] * B] = (-U[starts[M - 1]:ends[M - 1]] @ LS_inv).ravel()
    flat_Inv[off_22:off_22 + B * B] = (LS_inv.conj().T @ LS_inv).ravel()

    cinv_mk = flat_Inv[fgeom['gather_f']]
    cinv_mk = np.where(fgeom['gather_conj'], np.conj(cinv_mk), cinv_mk)
    m_mat = fgeom['m_mat']
    j_idx = np.arange(p)[:, None]
    if fgeom['use_c64']:
        w_mk = cinv_mk - alpha_c[m_mat] * alpha_c.conj()[None, None, :]
        s_all = (2.0 * float(vd)) * np.sum(gcc_all[j_idx[None, :, :], m_mat] * w_mk, axis=1, dtype=np.complex128)
    else:
        w_mk = cinv_mk - alpha[m_mat] * alpha.conj()[None, None, :]
        gcc_128 = np.conj(g[:, None] * c_mat)
        s_all = (2.0 * float(vd)) * np.sum(gcc_128[j_idx[None, :, :], m_mat] * w_mk, axis=1)

    v_nu = (g[:, None] * c_mat) * fgeom['k_norm'][None, :]
    alpha_pt = np.conj(alpha)[None, :] * shifted_pt
    grad = np.empty(3 * p, dtype=np.float64)
    grad[:p] = np.real(np.sum(s_all * v_nu, axis=1)) - 2.0 * np.real(np.sum(alpha_pt * v_nu, axis=1))
    grad[p:2 * p] = np.real(np.sum(s_all * c_mat, axis=1)) - 2.0 * np.real(np.sum(alpha_pt * c_mat, axis=1))
    grad[2 * p:3 * p] = np.real(np.sum(s_all * (1j * c_mat), axis=1)) - 2.0 * np.real(np.sum(alpha_pt * (1j * c_mat), axis=1))
    if not np.isfinite(grad).all():
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    return nll, grad


def align_coherent_pilot(tabs: dict[str, Any], delays: np.ndarray, anchor_l: int, nu_rel: np.ndarray, g_rel: np.ndarray, p_t: np.ndarray, r: np.ndarray):
    n = tabs['n']
    delays = np.asarray(delays, dtype=np.int64)
    lo_a = max(NU_MIN, float(NU_MIN - np.min(nu_rel)))
    hi_a = min(NU_MAX, float(NU_MAX - np.max(nu_rel)))
    if lo_a >= hi_a - 0.05:
        grid_a, E_a = tabs['align_grid'], tabs['E_align_conj']
    else:
        mask = (tabs['align_grid'] >= lo_a - 1e-9) & (tabs['align_grid'] <= hi_a + 1e-9)
        grid_a, E_a = tabs['align_grid'][mask], tabs['E_align_conj'][:, mask]

    cp = tabs['cp_all'][delays]
    shifted_pt = p_t[tabs['cols_all'][delays]]
    c_rel = cp * np.exp(np.outer(nu_rel, tabs['k_norm']))
    M_q = np.conj(g_rel[:, None] * c_rel * shifted_pt) * r[None, :]
    corr_all = (M_q @ E_a) * np.exp(2j * np.pi / n * np.outer(delays - anchor_l, grid_a))
    coh_score = np.abs(np.sum(corr_all, axis=0)) ** 2
    best_idx = int(np.argmax(coh_score))
    if 0 < best_idx < len(coh_score) - 1:
        y0, y1, y2 = float(coh_score[best_idx - 1]), float(coh_score[best_idx]), float(coh_score[best_idx + 1])
        denom = y0 - 2.0 * y1 + y2
        step = float(grid_a[1] - grid_a[0])
        delta_nu = 0.5 * (y0 - y2) / denom * step if abs(denom) > 1e-12 else 0.0
        nu_a = float(np.clip(grid_a[best_idx] + np.clip(delta_nu, -0.5 * step, 0.5 * step), lo_a, hi_a))
    else:
        nu_a = float(grid_a[best_idx])

    nu_out = np.clip(nu_rel + nu_a, NU_MIN, NU_MAX)
    g_out = g_rel * np.exp(-2j * np.pi * (delays - anchor_l) * nu_a / n)
    c_out = cp * np.exp(np.outer(nu_out, tabs['k_norm']))
    mu0 = np.sum((g_out[:, None] * c_out) * shifted_pt, axis=0)
    if float(np.vdot(mu0, mu0).real) > 1e-12:
        g_out = g_out * np.exp(1j * np.angle(np.vdot(mu0, r) / np.vdot(mu0, mu0)))
    return nu_out, g_out, float(coh_score[best_idx])


def fast_crosslag_init(tabs: dict[str, Any], delays: np.ndarray, p_t: np.ndarray, r: np.ndarray, vd: float) -> tuple[np.ndarray, np.ndarray]:
    """Closed-form cross-lag FFT with fftshift monotonic parabolic interpolation and exact reverse-lag phase."""
    n = tabs['n']
    delays = np.asarray(delays, dtype=np.int64)
    p = len(delays)
    cp = tabs['cp_all'][delays]
    n_fft = 2048
    freqs_s = np.fft.fftshift(np.fft.fftfreq(n_fft, d=1.0 / n))
    diff_idx = np.flatnonzero(np.abs(freqs_s) <= 6.2)
    diff_freqs = freqs_s[diff_idx]
    step_f = float(n / n_fft)
    lag_counts = Counter(int(delays[i] - delays[j]) for i in range(p) for j in range(p) if i != j)

    pair_peak = np.zeros((p, p), dtype=np.float64)
    pair_dnu = np.zeros((p, p), dtype=np.float64)
    pair_c = np.zeros((p, p), dtype=np.complex128)
    for i in range(p):
        for j in range(i + 1, p):
            dl = int(delays[i] - delays[j])
            if dl == 0:
                continue
            ks = np.arange(max(0, dl), min(n, n + dl), dtype=np.int64)
            ms = ks - dl
            buf = np.zeros(n_fft, dtype=np.complex64)
            buf[ks] = (r[ks] * np.conj(r[ms]) * np.conj(cp[i, ks]) * cp[j, ms]).astype(np.complex64)
            spec = np.fft.fftshift(np.fft.fft(buf))[diff_idx] / float(lag_counts[dl])
            mag = np.abs(spec)
            bk = int(np.argmax(mag))
            if 0 < bk < len(mag) - 1:
                y0, y1, y2 = float(mag[bk - 1]), float(mag[bk]), float(mag[bk + 1])
                den = y0 - 2.0 * y1 + y2
                frac = float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5)) if abs(den) > 1e-12 else 0.0
                dnu = float(diff_freqs[bk] + frac * step_f)
            else:
                dnu = float(diff_freqs[bk])
            c_exact = complex(
                np.sum(r[ks] * np.conj(r[ms]) * np.conj(cp[i, ks]) * cp[j, ms] * np.exp(-2j * np.pi * ks * dnu / n))
            ) / float(len(ks) * max(float(vd), 1e-6) * lag_counts[dl])
            pair_peak[i, j] = pair_peak[j, i] = abs(c_exact)
            pair_dnu[i, j] = dnu
            pair_dnu[j, i] = -dnu
            pair_c[i, j] = c_exact
            # Exact reverse-lag index-shift phase: c_{ji} = conj(c_{ij}) * exp(-j 2*pi * (l_i - l_j) * dnu / n)
            pair_c[j, i] = np.conj(c_exact) * np.exp(-2j * np.pi * dl * dnu / n)

    anchor = int(np.argmax(np.sum(pair_peak, axis=1)))
    nu_rel = pair_dnu[:, anchor].copy()
    nu_rel[anchor] = 0.0
    if p >= 3:
        other = [j for j in np.argsort(-pair_peak[anchor]) if j != anchor]
        b, c = other[0], other[1]
        p_ab, p_ac, p_bc = max(pair_peak[anchor, b], 1e-4), max(pair_peak[anchor, c], 1e-4), max(pair_peak[b, c], 1e-4)
        g_a_mag = float(np.clip(np.sqrt(p_ab * p_ac / p_bc), 0.15, 0.70))
    else:
        g_a_mag = float(np.clip(np.sqrt(max(pair_peak[anchor].max(), 1e-4)), 0.15, 0.70))
    g_rel0 = pair_c[:, anchor] / g_a_mag
    g_rel0[anchor] = g_a_mag
    mags = np.abs(g_rel0)
    over = mags > 0.70
    if over.any():
        g_rel0[over] *= 0.70 / mags[over]
    nu_cov, g_cov, _ = align_coherent_pilot(tabs, delays, int(delays[anchor]), nu_rel, g_rel0, p_t, r)
    return nu_cov, g_cov


def _escape_1sweep_fast(
    tabs: dict[str, Any],
    delays: np.ndarray,
    cp: np.ndarray,
    shifted_pt: np.ndarray,
    p_t: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    nu_in: np.ndarray,
    g_in: np.ndarray,
    nll_in: float,
    lag_counts: Counter,
    freqs: np.ndarray,
    valid_idx: np.ndarray,
    n_peaks: int,
    p_pow: float,
) -> tuple[np.ndarray, np.ndarray, float, bool]:
    n, p = tabs['n'], len(delays)
    n_fft = len(freqs)
    nu_c, g_c, nll_c = nu_in.copy(), g_in.copy(), float(nll_in)
    esc = False
    c_c = cp * np.exp(np.outer(nu_c, tabs['k_norm']))
    mu_all = np.sum((g_c[:, None] * c_c) * shifted_pt, axis=0)
    r_tilde = r - mu_all
    for i in np.argsort(-np.abs(g_c)):
        i = int(i)
        xi = np.zeros(n, dtype=np.complex128)
        w_cov = 0.0
        for j in range(p):
            if j == i:
                continue
            dl = int(delays[i] - delays[j])
            if dl == 0:
                continue
            m_ij = (tabs['k'] - delays[i] + delays[j]) % n
            wt = 1.0 / float(lag_counts[dl])
            xi += wt * g_c[j] * c_c[j, m_ij] * np.conj(r_tilde[m_ij])
            w_cov += wt * (abs(g_c[j]) ** 2)
        xi = np.conj(cp[i]) * r_tilde * xi
        r_minus_i = r - (mu_all - g_c[i] * c_c[i] * shifted_pt[i])
        xi_pil = np.conj(cp[i]) * np.conj(shifted_pt[i]) * r_minus_i
        buf = np.zeros(n_fft, dtype=np.complex64)
        buf[:n] = (float(vd) * xi + xi_pil).astype(np.complex64)
        spec = np.fft.fft(buf)
        mag = np.abs(spec[valid_idx])
        ord_k = np.argsort(-mag)
        denom = n * (float(vd) * float(vd) * w_cov + p_pow)
        peaks = []
        for idx_v in ord_k:
            fk = float(np.clip(freqs[valid_idx[idx_v]], NU_MIN, NU_MAX))
            if abs(fk - nu_c[i]) < 0.30:
                continue
            if all(abs(fk - pv[0]) >= 0.30 for pv in peaks):
                gk = complex(spec[valid_idx[idx_v]]) / max(denom, 1e-12)
                peaks.append((fk, gk))
                if len(peaks) == n_peaks:
                    break
        updated_i = False
        for fk, gk in peaks:
            nu_try, g_try = nu_c.copy(), g_c.copy()
            nu_try[i] = fk
            g_try[i] = np.clip(gk.real, GAIN_MIN, GAIN_MAX) + 1j * np.clip(gk.imag, GAIN_MIN, GAIN_MAX)
            nll_try = cyclic_nll_c64(tabs, delays, nu_try, g_try, p_t, r, vd, sigma2)
            if nll_try < nll_c - 0.05:
                nll_c, nu_c, g_c = nll_try, nu_try, g_try
                esc = updated_i = True
        if updated_i:
            c_c[i] = cp[i] * np.exp(nu_c[i] * tabs['k_norm'])
            mu_all = np.sum((g_c[:, None] * c_c) * shifted_pt, axis=0)
            r_tilde = r - mu_all
    return nu_c, g_c, nll_c, esc


def polish_cyclic_sbg(
    tabs: dict[str, Any],
    delays: np.ndarray,
    nu_init: np.ndarray,
    g_init: np.ndarray,
    p_t: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    *,
    include_pw: bool = True,
    escape_peaks: int = 2,
    post_escape: bool = True,
    maxiter: int = 11,
    use_c64: bool = True,
) -> tuple[float, np.ndarray, np.ndarray]:
    n = tabs['n']
    delays = np.asarray(delays, dtype=np.int64)
    p = len(delays)
    cp = tabs['cp_all'][delays]
    shifted_pt = p_t[tabs['cols_all'][delays]]
    p_pow = max(float(np.mean(np.abs(p_t) ** 2)), 1e-6)

    n_fft = 2048
    freqs = np.fft.fftfreq(n_fft, d=1.0 / n)
    valid_idx = np.flatnonzero((freqs >= NU_MIN) & (freqs <= NU_MAX))
    lag_counts = Counter(int(delays[i] - delays[j]) for i in range(p) for j in range(p) if i != j)

    cands = []
    nll_i = cyclic_nll_c64(tabs, delays, nu_init, g_init, p_t, r, vd, sigma2)
    cands.append((nll_i, nu_init.copy(), g_init.copy()))

    nu_cl, g_cl = fast_crosslag_init(tabs, delays, p_t, r, vd)
    nll_cl = cyclic_nll_c64(tabs, delays, nu_cl, g_cl, p_t, r, vd, sigma2)
    cands.append((nll_cl, nu_cl, g_cl))

    cands.sort(key=lambda x: x[0])
    nll_b, nu_b, g_b = cands[0]
    nu_b, g_b, nll_b, _ = _escape_1sweep_fast(
        tabs, delays, cp, shifted_pt, p_t, r, vd, sigma2,
        nu_b, g_b, nll_b, lag_counts, freqs, valid_idx, escape_peaks, p_pow,
    )

    if include_pw:
        M_pw = np.conj(cp * shifted_pt) * r[None, :]
        Z_pw = M_pw @ tabs['E_conj']
        gi_pw = np.argmax(np.abs(Z_pw) ** 2, axis=1)
        nu_pw = tabs['nu_grid'][gi_pw].copy()
        g_pw = Z_pw[np.arange(p), gi_pw] / float(n * p_pow)
        nll_pw0 = cyclic_nll_c64(tabs, delays, nu_pw, g_pw, p_t, r, vd, sigma2)
        nu_pwe, g_pwe, nll_pwe, _ = _escape_1sweep_fast(
            tabs, delays, cp, shifted_pt, p_t, r, vd, sigma2,
            nu_pw, g_pw, nll_pw0, lag_counts, freqs, valid_idx, escape_peaks, p_pow,
        )
        if nll_pwe < nll_b:
            nu_b, g_b, nll_b = nu_pwe, g_pwe, nll_pwe

    fgeom = prepare_cyclic_grad_geom(tabs, delays, use_c64=use_c64)
    bounds = [(NU_MIN, NU_MAX)] * p + [(GAIN_MIN, GAIN_MAX)] * (2 * p)
    theta0 = np.concatenate([np.clip(nu_b, NU_MIN, NU_MAX), np.clip(g_b.real, GAIN_MIN, GAIN_MAX), np.clip(g_b.imag, GAIN_MIN, GAIN_MAX)])
    res = minimize(
        cyclic_nll_and_grad, theta0, args=(fgeom, shifted_pt, r, float(vd), float(sigma2)),
        method='L-BFGS-B', jac=True, bounds=bounds,
        options={'maxiter': maxiter, 'ftol': 1e-6 if use_c64 else 1e-8, 'gtol': 1e-4 if use_c64 else 1e-5},
    )
    nu_b = np.asarray(res.x[:p], dtype=np.float64)
    g_b = np.asarray(res.x[p:2 * p] + 1j * res.x[2 * p:3 * p], dtype=np.complex128)
    nll_b = cyclic_nll_c64(tabs, delays, nu_b, g_b, p_t, r, vd, sigma2)

    if post_escape:
        nu_p, g_p, nll_p, esc2 = _escape_1sweep_fast(
            tabs, delays, cp, shifted_pt, p_t, r, vd, sigma2,
            nu_b, g_b, nll_b, lag_counts, freqs, valid_idx, max(1, escape_peaks - 1), p_pow,
        )
        if esc2:
            theta1 = np.concatenate([np.clip(nu_p, NU_MIN, NU_MAX), np.clip(g_p.real, GAIN_MIN, GAIN_MAX), np.clip(g_p.imag, GAIN_MIN, GAIN_MAX)])
            res2 = minimize(
                cyclic_nll_and_grad, theta1, args=(fgeom, shifted_pt, r, float(vd), float(sigma2)),
                method='L-BFGS-B', jac=True, bounds=bounds,
                options={'maxiter': maxiter, 'ftol': 1e-6 if use_c64 else 1e-8, 'gtol': 1e-4 if use_c64 else 1e-5},
            )
            nu_b = np.asarray(res2.x[:p], dtype=np.float64)
            g_b = np.asarray(res2.x[p:2 * p] + 1j * res2.x[2 * p:3 * p], dtype=np.complex128)
            nll_b = cyclic_nll_c64(tabs, delays, nu_b, g_b, p_t, r, vd, sigma2)

    return float(nll_b), nu_b, g_b


def sbg_ctrl_fast(tabs: dict[str, Any], delays: np.ndarray, obs: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Truth-free global cyclic SBG Doppler estimator on fixed `CD2` delays (`obs`-only)."""
    r, p_t, vd, sigma2 = unpack_obs_unit_power(obs, tabs['c1'], tabs['c2'])
    nu_cl, g_cl = fast_crosslag_init(tabs, delays, p_t, r, vd)
    _, nu_sbg, g_sbg = polish_cyclic_sbg(
        tabs, delays, nu_cl, g_cl, p_t, r, vd, sigma2,
        include_pw=True, escape_peaks=3, post_escape=True, maxiter=14, use_c64=True,
    )
    return nu_sbg, g_sbg


def estimate_sbj(
    tabs: dict[str, Any],
    obs: dict[str, Any],
    *,
    P_target: int = 8,
    preset: str = 'SBJ',
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Truth-free Semi-Blind Joint (delay, Doppler, gain) estimator taking ONLY `obs = {'y', 'pilot', 'sigma2'}`."""
    cfg = SBJ_CONFIGS[preset]
    n, L, lmax = tabs['n'], tabs['L'], tabs['lmax']
    r, p_t, vd, sigma2 = unpack_obs_unit_power(obs, tabs['c1'], tabs['c2'])
    cp_all, cols_all, nu_grid, E_conj = tabs['cp_all'], tabs['cols_all'], tabs['nu_grid'], tabs['E_conj']
    p_pow = float(np.mean(np.abs(p_t) ** 2))
    r_tot_var = max(float(sigma2) + 0.25 * float(vd), float(np.mean(np.abs(r) ** 2)) - p_pow)

    M_pil = np.conj(cp_all * p_t[cols_all]) * r[None, :]
    Z_pil = M_pil @ E_conj
    pil_mag2 = np.abs(Z_pil) ** 2
    best_gi_pil = np.argmax(pil_mag2, axis=1)
    best_pil_score = pil_mag2[np.arange(L), best_gi_pil]

    s0 = lmax
    r_int = r[s0:].astype(np.complex64)
    r_c64 = r.astype(np.complex64)
    n_fft = 2048
    freqs = np.fft.fftfreq(n_fft, d=1.0 / n)
    f_mask = np.abs(freqs) <= 6.0
    f_sub = freqs[f_mask]
    Q = np.zeros((lmax + 1, n_fft), dtype=np.complex64)
    for d in range(1, lmax + 1):
        Q[d, s0:n] = r_int * np.conj(r_c64[s0 - d:n - d])
    S_cross = np.fft.fft(Q, axis=1)[:, f_mask]
    cross_idx = np.argmax(np.abs(S_cross), axis=1)
    cross_dnu = f_sub[cross_idx]
    cross_val = S_cross[np.arange(lmax + 1), cross_idx].astype(np.complex128) / float((n - s0) * max(vd, 1e-6))

    top_pil_delays = np.argsort(-best_pil_score)[:10]
    top_lags = np.argsort(-np.abs(cross_val)[1:])[:8] + 1
    pair_set = set()
    for i_a in range(min(7, len(top_pil_delays))):
        la = int(top_pil_delays[i_a])
        for i_b in range(i_a + 1, min(9, len(top_pil_delays))):
            lb = int(top_pil_delays[i_b])
            pair_set.add((min(la, lb), max(la, lb)))
        for d in top_lags[:4]:
            d = int(d)
            if la + d <= lmax:
                pair_set.add((la, la + d))
            if la - d >= 0:
                pair_set.add((la - d, la))

    scored_pairs = []
    for l1, l2 in pair_set:
        d = l2 - l1
        if d > 0:
            scored_pairs.append((abs(cross_val[d]) * np.sqrt(float(best_pil_score[l1] + best_pil_score[l2])), l1, l2))
    scored_pairs.sort(key=lambda x: -x[0])

    pair_evals = []
    for _, l1, l2 in scored_pairs[:cfg['n_seed_pairs']]:
        d = l2 - l1
        dnu = float(cross_dnu[d])
        cv = complex(cross_val[d])
        rat = float(np.clip(np.sqrt((best_pil_score[l2] + 1e-6) / (best_pil_score[l1] + 1e-6)), 0.4, 2.5))
        g1_mag = float(np.clip(np.sqrt(max(abs(cv) / rat, 0.02)), 0.12, 0.70))
        g2_mag = float(np.clip(abs(cv) / g1_mag, 0.08, 0.70))
        g2_ph = cv / max(abs(cv), 1e-12)
        nu_al, g_al, _ = align_coherent_pilot(tabs, np.array([l1, l2]), l1, np.array([0.0, dnu]), np.array([g1_mag, g2_mag * g2_ph]), p_t, r)
        nll_al, _ = comp_nll_c64(tabs, np.array([l1, l2]), nu_al, g_al, p_t, r, vd, sigma2, diag_floor=r_tot_var)
        pair_evals.append((nll_al, [l1, l2], nu_al, g_al))

        nu_p2 = np.array([float(nu_grid[best_gi_pil[l1]]), float(nu_grid[best_gi_pil[l2]])])
        g_p2 = np.array([Z_pil[l1, best_gi_pil[l1]], Z_pil[l2, best_gi_pil[l2]]]) / max(n * p_pow, 1e-6)
        for k_i in (0, 1):
            if abs(g_p2[k_i]) > 0.70:
                g_p2[k_i] *= 0.70 / abs(g_p2[k_i])
        nll_p2, _ = comp_nll_c64(tabs, np.array([l1, l2]), nu_p2, g_p2, p_t, r, vd, sigma2, diag_floor=r_tot_var)
        pair_evals.append((nll_p2, [l1, l2], nu_p2, g_p2))

    pair_evals.sort(key=lambda x: x[0])
    seeds = [pair_evals[0]]
    if cfg['n_beams'] >= 2:
        # Registered rule: prefer disjoint second seed among evaluated pairs; if none is disjoint from seed 0,
        # fall back to the lowest-NLL evaluated pair whose 2-delay set differs from seed 0.
        s0_set = set(seeds[0][1])
        for cand in pair_evals[1:]:
            if len(set(cand[1]) & s0_set) == 0:
                seeds.append(cand)
                break
        if len(seeds) < cfg['n_beams']:
            for cand in pair_evals[1:]:
                if set(cand[1]) != s0_set:
                    seeds.append(cand)
                    break

    def _grow_beam(seed_tuple):
        _, cur_l, nu0, g0 = seed_tuple
        cur_l = list(cur_l)
        cur_nu, cur_g = nu0.tolist(), g0.tolist()
        nu2, g2 = fast_crosslag_init(tabs, np.array(cur_l), p_t, r, vd)
        if comp_nll_c64(tabs, np.array(cur_l), nu2, g2, p_t, r, vd, sigma2, diag_floor=r_tot_var)[0] < comp_nll_c64(tabs, np.array(cur_l), np.array(cur_nu), np.array(cur_g), p_t, r, vd, sigma2, diag_floor=r_tot_var)[0]:
            cur_nu, cur_g = nu2.tolist(), g2.tolist()

        while len(cur_l) < P_target:
            fl = r_tot_var if len(cur_l) < P_target - 1 else 0.0
            _, alpha = comp_nll_c64(tabs, np.array(cur_l), np.array(cur_nu), np.array(cur_g), p_t, r, vd, sigma2, diag_floor=r_tot_var, need_alpha=True)
            if alpha is None:
                nxt = next(int(l) for l in np.argsort(-best_pil_score) if int(l) not in cur_l)
                cur_l.append(nxt)
                cur_nu.append(float(nu_grid[best_gi_pil[nxt]]))
                cur_g.append(complex(Z_pil[nxt, best_gi_pil[nxt]]) / max(n * p_pow, 1e-6))
                continue
            step_cache = prepare_step_cache(tabs, cur_l, cur_nu, cur_g, p_t, r, vd)
            c_mat = step_cache['c_mat']
            h_adj_alpha = np.zeros(n, dtype=np.complex128)
            for j, lj in enumerate(cur_l):
                h_adj_alpha += np.roll(np.conj(c_mat[j]) * alpha * np.conj(cur_g[j]), -int(lj))
            x_hat = p_t + float(vd) * h_adj_alpha
            d_eff = max(float(sigma2), r_tot_var - float(vd) * step_cache['g2_base'])
            x_norm2 = max(float(np.vdot(x_hat, x_hat).real), 1e-6)

            M_em = np.conj(cp_all * x_hat[cols_all]) * alpha[None, :]
            Z_em = M_em @ E_conj
            em_mag2 = np.abs(Z_em) ** 2
            for lj in cur_l:
                em_mag2[lj, :] = -1.0
            best_gi = np.argmax(em_mag2, axis=1)
            em_top = [int(l) for l in np.argsort(-em_mag2[np.arange(L), best_gi])[:cfg['cand_top_k']] if int(l) not in cur_l]
            for lp in top_pil_delays[:5]:
                lp = int(lp)
                if lp not in cur_l and lp not in em_top and len(em_top) < cfg['cand_top_k'] + 2:
                    em_top.append(lp)

            best_add = None
            best_add_nll = 1e30
            for lc in em_top:
                gi1 = int(best_gi[lc])
                gi_list = [gi1]
                gi_p = int(best_gi_pil[lc])
                if abs(nu_grid[gi_p] - nu_grid[gi1]) >= 0.35:
                    gi_list.append(gi_p)
                for gi_c in gi_list:
                    nuc = float(nu_grid[gi_c])
                    gc = (d_eff * complex(Z_em[lc, gi_c])) / x_norm2
                    if abs(gc) > 0.70:
                        gc *= 0.70 / abs(gc)
                    nll_try = eval_step_cand_c64(tabs, step_cache, lc, gi_c, gc, p_t, vd, sigma2, diag_floor=fl)
                    if nll_try < best_add_nll:
                        best_add_nll = nll_try
                        best_add = (lc, nuc, gc)
            cur_l.append(best_add[0])
            cur_nu.append(best_add[1])
            cur_g.append(best_add[2])
            if len(cur_l) == 5:
                nu5, g5 = fast_crosslag_init(tabs, np.array(cur_l), p_t, r, vd)
                if comp_nll_c64(tabs, np.array(cur_l), nu5, g5, p_t, r, vd, sigma2, diag_floor=r_tot_var)[0] < comp_nll_c64(tabs, np.array(cur_l), np.array(cur_nu), np.array(cur_g), p_t, r, vd, sigma2, diag_floor=r_tot_var)[0]:
                    cur_nu, cur_g = nu5.tolist(), g5.tolist()

        nu8_cl, g8_cl = fast_crosslag_init(tabs, np.array(cur_l), p_t, r, vd)
        nll_a = cyclic_nll_c64(tabs, np.array(cur_l), np.array(cur_nu), np.array(cur_g), p_t, r, vd, sigma2)
        nll_b = cyclic_nll_c64(tabs, np.array(cur_l), nu8_cl, g8_cl, p_t, r, vd, sigma2)
        if nll_b < nll_a:
            return nll_b, cur_l, nu8_cl, g8_cl
        return nll_a, cur_l, np.array(cur_nu), np.array(cur_g)

    beams = [_grow_beam(sd) for sd in seeds]
    beams.sort(key=lambda x: x[0])
    _, sel_l, nu8, g8 = beams[0]
    sel_nu, sel_g = nu8.tolist(), g8.tolist()

    for _sr in range(cfg['swap_rounds']):
        swapped = False
        cur_nll, _ = comp_nll_c64(tabs, np.array(sel_l), np.array(sel_nu), np.array(sel_g), p_t, r, vd, sigma2)
        for slot in np.argsort(np.abs(sel_g))[:cfg['swap_slots']]:
            slot = int(slot)
            old_l = int(sel_l[slot])
            keep_l = [sel_l[j] for j in range(P_target) if j != slot]
            keep_nu = [sel_nu[j] for j in range(P_target) if j != slot]
            keep_g = [sel_g[j] for j in range(P_target) if j != slot]
            _, alpha = comp_nll_c64(tabs, np.array(keep_l), np.array(keep_nu), np.array(keep_g), p_t, r, vd, sigma2, need_alpha=True)
            if alpha is None:
                continue
            step_cache = prepare_step_cache(tabs, keep_l, keep_nu, keep_g, p_t, r, vd)
            c_mat = step_cache['c_mat']
            h_adj_alpha = np.zeros(n, dtype=np.complex128)
            for j, lj in enumerate(keep_l):
                h_adj_alpha += np.roll(np.conj(c_mat[j]) * alpha * np.conj(keep_g[j]), -int(lj))
            x_hat = p_t + float(vd) * h_adj_alpha
            x_norm2 = max(float(np.vdot(x_hat, x_hat).real), 1e-6)
            M_em = np.conj(cp_all * x_hat[cols_all]) * alpha[None, :]
            Z_em = M_em @ E_conj
            em_mag2 = np.abs(Z_em) ** 2
            for lj in keep_l:
                em_mag2[lj, :] = -1.0
            em_mag2[old_l, :] = -1.0  # Explicitly mask current slot delay so genuine swaps are never blocked
            best_gi = np.argmax(em_mag2, axis=1)
            top_cands = [
                int(l) for l in np.argsort(-em_mag2[np.arange(L), best_gi])
                if int(l) not in keep_l and int(l) != old_l
            ][:cfg['swap_cands']]
            best_rep = None
            best_rep_nll = cur_nll - 0.4
            for lc in top_cands:
                gi1 = int(best_gi[lc])
                nuc = float(nu_grid[gi1])
                gc = (float(sigma2) * complex(Z_em[lc, gi1])) / x_norm2
                nll_try = eval_step_cand_c64(tabs, step_cache, lc, gi1, gc, p_t, vd, sigma2, diag_floor=0.0)
                if nll_try < best_rep_nll:
                    best_rep_nll = nll_try
                    best_rep = (lc, nuc, gc)
            if best_rep is not None:
                sel_l[slot], sel_nu[slot], sel_g[slot] = best_rep
                cur_nll = best_rep_nll
                swapped = True
        if swapped:
            nu_s, g_s = fast_crosslag_init(tabs, np.array(sel_l), p_t, r, vd)
            if comp_nll_c64(tabs, np.array(sel_l), nu_s, g_s, p_t, r, vd, sigma2)[0] < cur_nll:
                sel_nu, sel_g = nu_s.tolist(), g_s.tolist()
        else:
            break

    _, nu_fin, g_fin = polish_cyclic_sbg(
        tabs, np.array(sel_l), np.array(sel_nu), np.array(sel_g), p_t, r, vd, sigma2,
        include_pw=cfg['include_pw'], escape_peaks=cfg['escape_peaks'],
        post_escape=cfg['post_escape'], maxiter=cfg['final_maxiter'], use_c64=cfg['use_c64'],
    )
    return np.array(sel_l, dtype=int), nu_fin, g_fin


# --------------------------------------------------------------------------- Triggered Receiver Branches (Zero Truth Access!)
def _decoded_sha(bits: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(bits).tobytes()).hexdigest()


def _run_cd2_continuation_notruth(
    ctx,
    helpers: dict[str, Any],
    obs: dict[str, Any],
    arrays: dict[str, Any],
    *,
    max_passes: int = 2,
    tag: str = 'A1',
) -> dict[str, Any]:
    """Truth-free 1-or-2-pass CODELAY continuation with identical numerical_fallback & finiteness checks as sf2.run_cd_timed."""
    stage3 = helpers['stage3']
    cd = helpers['cd']

    ar._require_finite(arrays['r1_check'], f'{tag}.p1.r1_check')
    ar._require_finite(arrays['r1_app'], f'{tag}.p1.r1_app')
    t_wall0 = perf_counter()
    t_cpu0 = process_time()
    br1 = stage3.e1.run_branch(ctx, cd, obs, arrays, 'A1')
    dec1 = br1['decoder']
    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))
    res1 = br1['result']
    if bool(res1.diagnostics.get('numerical_fallback')):
        raise FloatingPointError(f'numerical_fallback in {tag} p1')
    ar._require_finite(res1.gains, f'{tag}.p1.gains')
    ar._require_finite(br1['detector']['extrinsic'], f'{tag}.p1.extrinsic')

    if syn1 == 0 or max_passes == 1:
        return dict(
            decoded=dec1['decoded'],
            syndrome=syn1,
            passes_used=1,
            seconds=float(perf_counter() - t_wall0),
            cpu_seconds=float(process_time() - t_cpu0),
        )

    ar._require_finite(dec1['raw_check_extrinsic'], f'{tag}.p1.raw_check_extrinsic')
    ar._require_finite(dec1['raw_app'], f'{tag}.p1.raw_app')
    arrays2 = dict(
        r1_delays=np.array([int(p.delay) for p in res1.paths], dtype=int),
        r1_dopplers=np.array([float(p.doppler) for p in res1.paths], dtype=float),
        r1_gains=np.asarray(res1.gains, dtype=complex),
        r1_check=dec1['raw_check_extrinsic'],
        r1_app=dec1['raw_app'],
    )
    br2 = stage3.e1.run_branch(ctx, cd, obs, arrays2, 'A1')
    dec2 = br2['decoder']
    syn2 = int(ctx.hd.syndrome_weight(ctx, dec2['decoded']))
    res2 = br2['result']
    if bool(res2.diagnostics.get('numerical_fallback')):
        raise FloatingPointError(f'numerical_fallback in {tag} p2')
    ar._require_finite(res2.gains, f'{tag}.p2.gains')
    ar._require_finite(br2['detector']['extrinsic'], f'{tag}.p2.extrinsic')
    ar._require_finite(dec2['raw_check_extrinsic'], f'{tag}.p2.raw_check_extrinsic')
    ar._require_finite(dec2['raw_app'], f'{tag}.p2.raw_app')

    return dict(
        decoded=dec2['decoded'],
        syndrome=syn2,
        passes_used=2,
        seconds=float(perf_counter() - t_wall0),
        cpu_seconds=float(process_time() - t_cpu0),
    )


def _run_hg_continuation_notruth(
    ctx,
    helpers: dict[str, Any],
    obs: dict[str, Any],
    arrays: dict[str, Any],
    *,
    ls: np.ndarray,
    ks: np.ndarray,
    recipe: str = 'B0-p2-s0.5',
    dictionary_limit: int = 2575,
    max_passes: int = 2,
) -> dict[str, Any]:
    """Truth-free Huang-2010 global OMP continuation stopping clocks immediately at syndrome_weight
    (identical decision-ready timing boundary as CD, CD2, Ctrl, and SBJ*, excluding truth scoring/SHA).
    """
    moments = helpers['moments']
    time_refine = helpers['time_refine']
    system = ctx.system
    native = ctx.native
    pd = 1.0 - system.rho

    t_wall0 = perf_counter()
    t_cpu0 = process_time()
    ar._require_finite(arrays['r1_check'], 'HG.pass1.r1_check')
    ar._require_finite(arrays['r1_app'], 'HG.pass1.r1_app')
    prior = np.clip(arrays['r1_check'], -20.0, 20.0)
    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)

    dec_last = None
    syn_last = 1
    passes_used = 0
    for p_idx in range(max_passes):
        x_ref = obs['pilot'] + mu
        _, omp_l, omp_k, omp_g = ar.omp_reacquire(
            obs['y'], x_ref, ls, ks, system, float(obs['sigma2']), helpers,
            recipe=recipe, dictionary_limit=dictionary_limit,
        )
        c, _ = time_refine(
            obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
            system.c1, system.c2, float(obs['sigma2']),
            mode='soft', max_paths=8, rounds=2,
        )
        ar._require_finite(c.dopplers, f'HG.pass{p_idx+1}.time_refine.dopplers')
        ar._require_finite(c.gains, f'HG.pass{p_idx+1}.time_refine.gains')
        o = native.scalar_joint(
            obs['y'], obs['pilot'], c, float(obs['sigma2']),
            pd=pd, prior=prior, iterations=20, damping=0.3, gain_mode='joint',
        )
        ar._require_finite(o['extrinsic'], f'HG.pass{p_idx+1}.scalar_joint.extrinsic')
        dec = native.decoder_messages(ctx.code, np.clip(o['extrinsic'], -20.0, 20.0), maxiter=50)
        ar._require_finite(dec['raw_check_extrinsic'], f'HG.pass{p_idx+1}.ldpc.raw_check_extrinsic')
        ar._require_finite(dec['raw_app'], f'HG.pass{p_idx+1}.ldpc.raw_app')
        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
        dec_last = dec
        syn_last = syn
        passes_used = p_idx + 1
        if syn == 0 or p_idx == max_passes - 1:
            break
        prior = np.clip(dec['raw_check_extrinsic'], -20.0, 20.0)
        mu, v, _ = moments(np.clip(dec['raw_app'], -20.0, 20.0), pd)

    wall_s = float(perf_counter() - t_wall0)
    cpu_s = float(process_time() - t_cpu0)
    return dict(
        decoded=dec_last['decoded'],
        syndrome=syn_last,
        passes_used=passes_used,
        seconds=wall_s,
        cpu_seconds=cpu_s,
    )


def f0_injected_no_pf(ctx, obs: dict[str, Any], l_in: np.ndarray, nu_in: np.ndarray, g_in: np.ndarray):
    """Bitwise-identical to `stageA2.f0_true(..., 'ls')` without re-running redundant `pilot_front` QROMP."""
    from messages import moments

    system, code, native = ctx.system, ctx.code, ctx.native
    n = len(obs['y'])
    s = dict(
        delays=np.asarray(l_in, dtype=int),
        dopplers=np.asarray(nu_in, dtype=float),
        gains=np.asarray(g_in, dtype=complex),
        mu=np.zeros(n, dtype=complex),
        v=np.full(n, 0.5, dtype=float),
        prior=np.zeros(2 * n, dtype=float),
    )
    arrays = {}
    for r_idx in range(2):
        rds = 0 if r_idx == 0 else 2
        c, _ = native.time_refine(
            obs['y'], obs['pilot'], s['mu'], s['v'],
            s['delays'], s['dopplers'], s['gains'],
            system.c1, system.c2, obs['sigma2'], mode='soft', max_paths=8, rounds=rds,
        )
        o = native.scalar_joint(
            obs['y'], obs['pilot'], c, obs['sigma2'],
            pd=1 - system.rho, prior=s['prior'], iterations=20, gain_mode='joint',
        )
        dec = native.decoder_messages(code, np.clip(o['extrinsic'], -20, 20), maxiter=50)
        s['prior'] = np.clip(dec['raw_check_extrinsic'], -20, 20)
        s['mu'], s['v'], _ = moments(np.clip(dec['raw_app'], -20, 20), 1 - system.rho)
        s['delays'], s['dopplers'], s['gains'] = c.delays, c.dopplers, o['gains']
        arrays.update({
            f'r{r_idx}_decoded': dec['decoded'],
            f'r{r_idx}_app': dec['raw_app'],
            f'r{r_idx}_check': dec['raw_check_extrinsic'],
            f'r{r_idx}_delays': c.delays,
            f'r{r_idx}_dopplers': c.dopplers,
            f'r{r_idx}_gains': o['gains'],
            f'r{r_idx}_ce_gains': c.gains,
        })
    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
    return dec, arrays, syn


def run_ctrl_with_dopplers_notruth(
    ctx,
    helpers: dict[str, Any],
    obs: dict[str, Any],
    l_cd_from_f0: np.ndarray,
    nu_r0: np.ndarray,
) -> dict[str, Any]:
    """Execute single-factor Round-0 Doppler replacement + identical Round-1 + identical 2-pass CD2 continuation."""
    l_cd = np.asarray(l_cd_from_f0, dtype=int)
    nu_in = np.asarray(nu_r0, dtype=float)
    g_order_preserve = np.arange(len(l_cd), 0, -1, dtype=np.complex128)
    dec_f0, arrays_f0, syn_f0 = f0_injected_no_pf(ctx, obs, l_cd, nu_in, g_order_preserve)
    if syn_f0 == 0:
        return dict(
            decoded=dec_f0['decoded'],
            arrays_f0=arrays_f0,
            syndrome=0,
            passes_used=0,
            stage_stopped='ctrl_f0',
        )
    cont = _run_cd2_continuation_notruth(ctx, helpers, obs, arrays_f0, max_passes=2, tag='Ctrl')
    return dict(
        decoded=cont['decoded'],
        arrays_f0=arrays_f0,
        syndrome=int(cont['syndrome']),
        passes_used=int(cont['passes_used']),
        stage_stopped=f'ctrl_cd{cont["passes_used"]}',
    )


def run_ctrl_triggered_branch(
    ctx,
    helpers: dict[str, Any],
    tabs: dict[str, Any],
    obs: dict[str, Any],
    l_cd_from_f0: np.ndarray,
) -> dict[str, Any]:
    """Decision-ready triggered Single-Factor Control (`CD2` own delay front end + `SBG` Doppler + `CD2` continuation)."""
    t_w0, t_c0 = perf_counter(), process_time()
    l_cd = np.asarray(l_cd_from_f0, dtype=int)
    nu_sbg, _ = sbg_ctrl_fast(tabs, l_cd, obs)
    t_est_w = perf_counter() - t_w0

    out = run_ctrl_with_dopplers_notruth(ctx, helpers, obs, l_cd, nu_sbg)
    return dict(
        decoded=out['decoded'],
        syndrome=out['syndrome'],
        stage_stopped=out['stage_stopped'],
        est_seconds=float(t_est_w),
        seconds=float(perf_counter() - t_w0),
        cpu_seconds=float(process_time() - t_c0),
        l_hat=l_cd,
        nu_hat=nu_sbg,
    )


def run_sbj_triggered_branch(
    ctx,
    helpers: dict[str, Any],
    tabs: dict[str, Any],
    obs: dict[str, Any],
    *,
    preset: str = 'SBJ',
) -> dict[str, Any]:
    """Decision-ready triggered SBJ branch (starts after standard F0 fails `syndrome != 0`; zero `truth` access!)."""
    from messages import moments
    from physical import Channel

    system, code, native = ctx.system, ctx.code, ctx.native
    t_w0, t_c0 = perf_counter(), process_time()

    l_hat, nu_hat, g_hat = estimate_sbj(tabs, obs, preset=preset)
    t_est_w = perf_counter() - t_w0

    ord_g = np.argsort(-np.abs(g_hat) ** 2)
    l_ord = l_hat[ord_g]
    nu_ord = nu_hat[ord_g]
    g_ord = g_hat[ord_g]

    ch0 = Channel(len(obs['y']), system.c1, system.c2, l_ord, nu_ord, g_ord)
    o0 = native.scalar_joint(
        obs['y'], obs['pilot'], ch0, obs['sigma2'],
        pd=1 - system.rho, prior=np.zeros(2 * len(obs['y'])), iterations=20, gain_mode='joint',
    )
    dec0 = native.decoder_messages(code, np.clip(o0['extrinsic'], -20, 20), maxiter=50)
    syn0 = int(ctx.hd.syndrome_weight(ctx, dec0['decoded']))
    if syn0 == 0:
        return dict(
            decoded=dec0['decoded'], syndrome=0, stage_stopped='r0',
            est_seconds=float(t_est_w), seconds=float(perf_counter() - t_w0),
            cpu_seconds=float(process_time() - t_c0), l_hat=l_ord, nu_hat=nu_ord,
        )

    prior1 = np.clip(dec0['raw_check_extrinsic'], -20, 20)
    mu1, v1, _ = moments(np.clip(dec0['raw_app'], -20, 20), 1 - system.rho)
    ch1, _ = native.time_refine(
        obs['y'], obs['pilot'], mu1, v1, ch0.delays, ch0.dopplers, o0['gains'],
        system.c1, system.c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2,
    )
    o1 = native.scalar_joint(
        obs['y'], obs['pilot'], ch1, obs['sigma2'],
        pd=1 - system.rho, prior=prior1, iterations=20, gain_mode='joint',
    )
    dec1 = native.decoder_messages(code, np.clip(o1['extrinsic'], -20, 20), maxiter=50)
    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))
    if syn1 == 0:
        return dict(
            decoded=dec1['decoded'], syndrome=0, stage_stopped='r1',
            est_seconds=float(t_est_w), seconds=float(perf_counter() - t_w0),
            cpu_seconds=float(process_time() - t_c0), l_hat=l_ord, nu_hat=nu_ord,
        )

    arrays1 = dict(
        r1_delays=ch1.delays,
        r1_dopplers=ch1.dopplers,
        r1_gains=o1['gains'],
        r1_check=dec1['raw_check_extrinsic'],
        r1_app=dec1['raw_app'],
    )
    cont = _run_cd2_continuation_notruth(ctx, helpers, obs, arrays1, max_passes=2, tag=preset)
    return dict(
        decoded=cont['decoded'],
        syndrome=int(cont['syndrome']),
        stage_stopped=f'cd_p{cont["passes_used"]}',
        est_seconds=float(t_est_w),
        seconds=float(perf_counter() - t_w0),
        cpu_seconds=float(process_time() - t_c0),
        l_hat=l_ord,
        nu_hat=nu_ord,
    )


def eval_key_arms(
    C: dict[str, Any],
    helpers: dict[str, Any],
    tabs: dict[str, Any],
    obs: dict[str, Any],
    truth: dict[str, Any],
    arms_to_run: list[str] | tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Strict two-phase key evaluation:
    Phase 1 runs F0 and ALL requested receiver branches using ONLY `obs` (zero `truth` access!).
    Phase 2 scores the already-produced decisions and delay supports against `truth`.
    """
    ctx, st = C['ctx'], C['stage3']
    obs_only = dict(y=obs['y'], pilot=obs['pilot'], sigma2=obs['sigma2'])

    # Phase 1: Pure `obs`-only execution across all arms
    tf0_w, tf0_c = perf_counter(), process_time()
    dec_f0, arrays_f0, syn_f0, _ = st.e1.f0_state(ctx, obs_only)
    f0_wall = float(perf_counter() - tf0_w)
    f0_cpu = float(process_time() - tf0_c)
    f0_decoded = dec_f0['decoded']
    l_cd = np.asarray(arrays_f0['r0_delays'], dtype=int)

    raw_decisions: dict[str, dict[str, Any]] = {}
    for arm in arms_to_run:
        if syn_f0 == 0:
            raw_decisions[arm] = dict(
                decoded=f0_decoded,
                decoded_sha=_decoded_sha(f0_decoded),
                syndrome=0,
                triggered=False,
                seconds=0.0,
                cpu_seconds=0.0,
                stage='f0_pass',
                l_hat=l_cd,
                nu_hat=np.asarray(arrays_f0['r0_dopplers'], dtype=float),
            )
            continue
        if arm == 'CD2':
            cd2_res = _run_cd2_continuation_notruth(ctx, helpers, obs_only, arrays_f0, max_passes=2, tag='CD2')
            raw_decisions['CD2'] = dict(
                decoded=cd2_res['decoded'],
                decoded_sha=_decoded_sha(cd2_res['decoded']),
                syndrome=int(cd2_res['syndrome']),
                triggered=True,
                seconds=cd2_res['seconds'],
                cpu_seconds=cd2_res['cpu_seconds'],
                stage=f'cd_p{cd2_res["passes_used"]}',
                l_hat=l_cd,
                nu_hat=np.asarray(arrays_f0['r0_dopplers'], dtype=float),
            )
        elif arm == 'Ctrl':
            ctrl_res = run_ctrl_triggered_branch(ctx, helpers, tabs, obs_only, l_cd)
            raw_decisions['Ctrl'] = dict(
                decoded=ctrl_res['decoded'],
                decoded_sha=_decoded_sha(ctrl_res['decoded']),
                syndrome=int(ctrl_res['syndrome']),
                triggered=True,
                seconds=ctrl_res['seconds'],
                cpu_seconds=ctrl_res['cpu_seconds'],
                est_seconds=ctrl_res['est_seconds'],
                stage=ctrl_res['stage_stopped'],
                l_hat=ctrl_res['l_hat'],
                nu_hat=ctrl_res['nu_hat'],
            )
        elif arm in SBJ_CONFIGS:
            sbj_res = run_sbj_triggered_branch(ctx, helpers, tabs, obs_only, preset=arm)
            raw_decisions[arm] = dict(
                decoded=sbj_res['decoded'],
                decoded_sha=_decoded_sha(sbj_res['decoded']),
                syndrome=int(sbj_res['syndrome']),
                triggered=True,
                seconds=sbj_res['seconds'],
                cpu_seconds=sbj_res['cpu_seconds'],
                est_seconds=sbj_res['est_seconds'],
                stage=sbj_res['stage_stopped'],
                l_hat=sbj_res['l_hat'],
                nu_hat=sbj_res['nu_hat'],
            )
        else:
            raise ValueError(f'Unknown arm {arm!r}')

    # Phase 2: Post-decode scoring against `truth` (cannot retroactively alter any decision)
    true_delays = set(int(x) for x in np.asarray(truth['l_i'], dtype=int))
    f0_err = int(st.e1.gd.score(ctx, f0_decoded, truth))
    lcd_hits = int(len(set(int(x) for x in l_cd) & true_delays))
    arms_out: dict[str, Any] = {
        'F0': dict(
            errors=f0_err,
            syndrome=int(syn_f0),
            seconds=f0_wall,
            cpu_seconds=f0_cpu,
            lcd_hits=lcd_hits,
            decoded_sha=_decoded_sha(f0_decoded),
        ),
    }
    for arm, d_rec in raw_decisions.items():
        err = f0_err if not d_rec['triggered'] else int(st.e1.gd.score(ctx, d_rec['decoded'], truth))
        rec_out: dict[str, Any] = dict(
            errors=err,
            syndrome=d_rec['syndrome'],
            triggered=d_rec['triggered'],
            seconds=d_rec['seconds'],
            cpu_seconds=d_rec['cpu_seconds'],
            stage=d_rec['stage'],
            decoded_sha=d_rec['decoded_sha'],
        )
        if 'est_seconds' in d_rec:
            rec_out['est_seconds'] = d_rec['est_seconds']
        if arm in SBJ_CONFIGS and d_rec['triggered']:
            rec_out['delay_hits'] = int(len(set(int(x) for x in d_rec['l_hat']) & true_delays))
        arms_out[arm] = rec_out

    return arms_out, raw_decisions


def eval_frame_grids(
    C: dict[str, Any],
    helpers: dict[str, Any],
    tabs: dict[str, Any],
    frame: int,
    grids: dict[str, dict[int, tuple[int, ...]]],
) -> list[dict[str, Any]]:
    ctx, st = C['ctx'], C['stage3']
    all_rhos = sorted({rho for rmap in grids.values() for rho in rmap})
    rows: list[dict[str, Any]] = []
    for s in SCENARIOS:
        for rho in all_rhos:
            active_arms_by_snr: dict[int, list[str]] = {}
            for arm, rmap in grids.items():
                for snr in rmap.get(rho, ()):
                    active_arms_by_snr.setdefault(int(snr), []).append(arm)
            if not active_arms_by_snr:
                continue
            base = st.inputs(ctx, frame, s, rho)
            for snr in sorted(active_arms_by_snr):
                arms_to_run = active_arms_by_snr[snr]
                _, obs, truth = st.observed(ctx, base, rho, snr)
                arms_out, _ = eval_key_arms(C, helpers, tabs, obs, truth, arms_to_run)
                rows.append(dict(
                    frame=int(frame), scenario=s, rho=int(rho), snr=int(snr),
                    sigma2=float(obs['sigma2']), arms=arms_out,
                ))
    return rows


# --------------------------------------------------------------------------- Bracketing, Bootstrap & Verdict Analysis
def _empirical_1d_bounds(fer_1d: np.ndarray, snrs: tuple[int, ...] | list[int]) -> tuple[float, float]:
    """Interpolation-free conservative bounds (lo, hi) in dB for a 1D FER curve."""
    f = np.asarray(fer_1d, dtype=np.float64)
    x = [float(s) / 100.0 for s in snrs]
    if f[0] <= 0.01:
        return -math.inf, x[0]
    for i in range(1, len(x)):
        if f[i] <= 0.01:
            return x[i - 1], x[i]
    return x[-1], math.inf


def _sanitize_strict_json(obj: Any) -> Any:
    """Ensure strict RFC-8259 JSON compatibility (`allow_nan=False`):
    converts +/-inf bounds to '-inf' / '+inf' while still raising ValueError on NaN!
    """
    if isinstance(obj, dict):
        return {str(k): _sanitize_strict_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_strict_json(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        if math.isnan(f):
            raise ValueError('NaN encountered in Stage A9 JSON output')
        return sf._rep(f)
    return obj


def check_1d_bracket(fer_1d: np.ndarray, snrs: tuple[int, ...] | list[int], max_gap_db: float = MAX_BRACKET_GAP_DB) -> dict[str, Any]:
    """Verify 1% FER crossing is strictly bracketed by measured adjacent SNR points <= max_gap_db apart."""
    f = np.asarray(fer_1d, dtype=np.float64)
    x = [float(s) / 100.0 for s in snrs]
    if len(x) < 2:
        return dict(bracketed=False, reason='fewer_than_2_snrs', bracket=['-inf', '+inf'], lo_db='-inf', hi_db='+inf', gap_db=None)
    lo_db, hi_db = _empirical_1d_bounds(f, snrs)
    if not math.isfinite(lo_db):
        return dict(bracketed=False, reason='starts_at_or_below_1pct', bracket=['-inf', hi_db], lo_db='-inf', hi_db=hi_db, gap_db=None)
    if not math.isfinite(hi_db):
        return dict(bracketed=False, reason='never_reaches_1pct', bracket=[lo_db, '+inf'], lo_db=lo_db, hi_db='+inf', gap_db=None)
    gap = round(float(hi_db - lo_db), 6)
    ok = bool(gap <= max_gap_db + 1e-9)
    return dict(
        bracketed=ok,
        reason='ok' if ok else f'gap_{gap:.2f}db_gt_{max_gap_db:.2f}db',
        bracket=[lo_db, hi_db],
        lo_db=lo_db,
        hi_db=hi_db,
        gap_db=gap,
    )


def verify_crossing_brackets(
    arm_grids: dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]],
    max_gap_db: float = MAX_BRACKET_GAP_DB,
) -> dict[str, dict[str, Any]]:
    """Compute brackets on U, G, and the exact estimator quantity 0.5 * (C_U + C_G)."""
    out: dict[str, dict[str, Any]] = {}
    for arm, rmap in arm_grids.items():
        out[arm] = {}
        for rho, (snrs_r, fail_r) in sorted(rmap.items()):
            fer_sc = fail_r.mean(axis=0)  # [2, n_snrs]
            bu = check_1d_bracket(fer_sc[0], snrs_r, max_gap_db)
            bg = check_1d_bracket(fer_sc[1], snrs_r, max_gap_db)
            u_lo = stageA6._to_float_bound(bu['lo_db'])
            u_hi = stageA6._to_float_bound(bu['hi_db'])
            g_lo = stageA6._to_float_bound(bg['lo_db'])
            g_hi = stageA6._to_float_bound(bg['hi_db'])
            mean_lo = 0.5 * (u_lo + g_lo)
            mean_hi = 0.5 * (u_hi + g_hi)
            both_ok = bool(bu['bracketed'] and bg['bracketed'])
            mean_gap = round(float(mean_hi - mean_lo), 6) if both_ok else None
            bm = dict(
                bracketed=both_ok,
                reason='ok' if both_ok else f'U:{bu["reason"]};G:{bg["reason"]}',
                bracket=[sf._rep(mean_lo), sf._rep(mean_hi)],
                lo_db=sf._rep(mean_lo),
                hi_db=sf._rep(mean_hi),
                gap_db=mean_gap,
            )
            out[arm][str(rho)] = dict(
                U=bu, G=bg, mean=bm,
                all_ok=both_ok,
            )
    return out


def is_arm_min_bracketed(
    arm: str,
    brackets: dict[str, dict[str, Any]],
    std_eval: dict[str, Any],
    best_rho: int,
) -> bool:
    """Verify the cross-rho minimum of 0.5*(C_U + C_G) is genuinely bracketed <= 0.50 dB:
    1) Selected `best_rho` has both U and G bracketed <= 0.50 dB;
    2) No other evaluated `rho` has an unbracketed lower bound (`starts_at_or_below_1pct` or wide gap)
       that could equal or beat the selected `best_rho` point crossing!
    """
    b_map = brackets[arm]
    if not b_map[str(best_rho)]['all_ok']:
        return False
    rhos_list = list(std_eval['arm_rhos'][arm])
    best_idx = rhos_list.index(best_rho)
    best_pt = float(std_eval['arm_hi'][arm][0, best_idx])
    if not math.isfinite(best_pt):
        return False
    for rho_str, info in b_map.items():
        if int(rho_str) == int(best_rho):
            continue
        if info['all_ok']:
            continue
        if stageA6._to_float_bound(info['mean']['lo_db']) <= best_pt + 1e-12:
            return False
    return True


def _arm_min_empirical_bounds(b_map: dict[str, Any]) -> tuple[float, float]:
    lo = min(stageA6._to_float_bound(info['mean']['lo_db']) for info in b_map.values())
    hi = min(stageA6._to_float_bound(info['mean']['hi_db']) for info in b_map.values())
    return lo, hi


def _enforce_bounds_if_unbracketed(
    contrast: dict[str, Any],
    bracketed: bool,
    lo_a: float,
    hi_a: float,
    lo_b: float,
    hi_b: float,
    *,
    a_ok: bool | None = None,
    b_ok: bool | None = None,
) -> dict[str, Any]:
    out = dict(contrast)
    la = stageA6._to_float_bound(lo_a)
    ha = stageA6._to_float_bound(hi_a)
    lb = stageA6._to_float_bound(lo_b)
    hb = stageA6._to_float_bound(hi_b)
    out['bracketed_le_0p5db'] = bool(bracketed)
    if not bracketed:
        # Report conservative interpolation-free bounds only; never publish an unbracketed single-point interpolation
        lo_diff = -math.inf if (la == -math.inf or hb == math.inf) else (math.inf if (la == math.inf or hb == -math.inf) else la - hb)
        hi_diff = math.inf if (ha == math.inf or lb == -math.inf) else (-math.inf if (ha == -math.inf or lb == math.inf) else ha - lb)
        out['point_db'] = [sf._rep(lo_diff), sf._rep(hi_diff)]
    if a_ok is False and 'arm_a_best_db' in out:
        out['arm_a_best_db'] = [sf._rep(la), sf._rep(ha)]
    if b_ok is False and 'arm_b_best_db' in out:
        out['arm_b_best_db'] = [sf._rep(lb), sf._rep(hb)]
    if a_ok is False and 'arm_a_db' in out:
        out['arm_a_db'] = [sf._rep(la), sf._rep(ha)]
    if b_ok is False and 'arm_b_db' in out:
        out['arm_b_db'] = [sf._rep(lb), sf._rep(hb)]
    return out


def _clean_eval_tables(ev: dict[str, Any], brackets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Replace any unbracketed single-point crossing with conservative [lo, hi] bounds across
    best_crossings, mean_crossing, and crossings_by_scenario (applied identically to standard & Haldane).
    """
    best_clean = {}
    for arm, binfo in ev['best_ci'].items():
        b_copy = dict(binfo)
        min_ok = is_arm_min_bracketed(arm, brackets, ev, int(binfo['best_rho']))
        b_copy['min_bracketed_le_0p5db'] = min_ok
        if not min_ok:
            emp_lo, emp_hi = _arm_min_empirical_bounds(brackets[arm])
            b_copy['best_db'] = [sf._rep(emp_lo), sf._rep(emp_hi)]
        best_clean[arm] = b_copy

    mean_clean: dict[str, dict[str, Any]] = {}
    for arm, rmap in ev['arm_mean_pt'].items():
        mean_clean[arm] = {}
        for r_str, val in rmap.items():
            eb_m = brackets[arm][r_str]['mean']
            mean_clean[arm][r_str] = val if eb_m['bracketed'] else eb_m['bracket']

    scen_clean: dict[str, dict[str, dict[str, Any]]] = {}
    for arm, smap in ev['arm_scen_pt'].items():
        scen_clean[arm] = {}
        for sc_name, rmap in smap.items():
            scen_clean[arm][sc_name] = {}
            for r_str, val in rmap.items():
                eb_sc = brackets[arm][r_str][sc_name]
                scen_clean[arm][sc_name][r_str] = val if eb_sc['bracketed'] else eb_sc['bracket']

    return dict(best_crossings=best_clean, mean_crossing=mean_clean, crossings_by_scenario=scen_clean)


def verdict_a9(lb95_db: float, primary_bracketed: bool) -> str:
    """Unique mutually-exclusive Stage A9 verdict:
    - Unbracketed primary min-crossing (or NaN) -> INCONCLUSIVE_UNBRACKETED
    - Bracketed and LB95 >= 0.50 dB -> GO
    - Bracketed and LB95 < 0.50 dB (including censored LB95 == -inf) -> STOP
    """
    if not primary_bracketed or math.isnan(float(lb95_db)):
        return 'INCONCLUSIVE_UNBRACKETED'
    return 'GO' if float(lb95_db) >= GO_THRESH_DB else 'STOP'


def crossing_haldane_n(fer: np.ndarray, snrs: tuple[int, ...] | list[int], n_frames: int) -> float:
    floor = 0.5 / float(max(1, n_frames))
    x = np.asarray(snrs, dtype=np.float64) / 100.0
    lf = np.log10(np.maximum(np.asarray(fer, dtype=np.float64), floor))
    if fer[0] <= 0.01:
        return -np.inf
    for i in range(1, len(x)):
        if fer[i] <= 0.01:
            t = (lf[i - 1] + 2.0) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
            return float(x[i - 1] + t * (x[i] - x[i - 1]))
    return np.inf


def _build_contrasts_from_eval(
    ev: dict[str, Any],
    arm_grids: dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]],
    brackets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cd2_best_rho = int(ev['best_rho']['CD2'])
    sbj_best_rho = int(ev['best_rho']['SBJ'])
    cd2_min_ok = is_arm_min_bracketed('CD2', brackets, ev, cd2_best_rho)
    sbj_min_ok = is_arm_min_bracketed('SBJ', brackets, ev, sbj_best_rho)
    primary_ok = bool(cd2_min_ok and sbj_min_ok)

    cd2_lo, cd2_hi = _arm_min_empirical_bounds(brackets['CD2'])
    sbj_lo, sbj_hi = _arm_min_empirical_bounds(brackets['SBJ'])
    primary = _enforce_bounds_if_unbracketed(
        ev['contrast_best']('CD2', 'SBJ'), primary_ok, cd2_lo, cd2_hi, sbj_lo, sbj_hi,
        a_ok=cd2_min_ok, b_ok=sbj_min_ok,
    )
    lo_val = stageA6._to_float_bound(primary['ci95_db'][0])
    primary['primary_bracketed_le_0p5db'] = primary_ok
    primary['verdict'] = verdict_a9(lo_val, primary_ok)
    primary['go_threshold_db'] = GO_THRESH_DB

    single_factor: dict[str, Any] = {}
    if 'Ctrl' in arm_grids:
        for rho_c in sorted(arm_grids['Ctrl']):
            if rho_c in arm_grids['CD2']:
                r_str = str(rho_c)
                a_rc_ok = bool(brackets['CD2'][r_str]['all_ok'])
                b_rc_ok = bool(brackets['Ctrl'][r_str]['all_ok'])
                ok_rc = bool(a_rc_ok and b_rc_ok)
                single_factor[f'CD2_minus_Ctrl_rho{rho_c}'] = _enforce_bounds_if_unbracketed(
                    ev['contrast_rho']('CD2', rho_c, 'Ctrl', rho_c),
                    ok_rc,
                    brackets['CD2'][r_str]['mean']['lo_db'], brackets['CD2'][r_str]['mean']['hi_db'],
                    brackets['Ctrl'][r_str]['mean']['lo_db'], brackets['Ctrl'][r_str]['mean']['hi_db'],
                    a_ok=a_rc_ok, b_ok=b_rc_ok,
                )
        ctrl_best_rho = int(ev['best_rho']['Ctrl'])
        ctrl_min_ok = is_arm_min_bracketed('Ctrl', brackets, ev, ctrl_best_rho)
        ctrl_lo, ctrl_hi = _arm_min_empirical_bounds(brackets['Ctrl'])
        single_factor['CD2_best_minus_Ctrl_best'] = _enforce_bounds_if_unbracketed(
            ev['contrast_best']('CD2', 'Ctrl'),
            bool(cd2_min_ok and ctrl_min_ok),
            cd2_lo, cd2_hi, ctrl_lo, ctrl_hi,
            a_ok=cd2_min_ok, b_ok=ctrl_min_ok,
        )
        if 100 in arm_grids['Ctrl'] and 100 in arm_grids['SBJ']:
            a_100_ok = bool(brackets['Ctrl']['100']['all_ok'])
            b_100_ok = bool(brackets['SBJ']['100']['all_ok'])
            ok_100 = bool(a_100_ok and b_100_ok)
            single_factor['Ctrl_minus_SBJ_rho100'] = _enforce_bounds_if_unbracketed(
                ev['contrast_rho']('Ctrl', 100, 'SBJ', 100),
                ok_100,
                brackets['Ctrl']['100']['mean']['lo_db'], brackets['Ctrl']['100']['mean']['hi_db'],
                brackets['SBJ']['100']['mean']['lo_db'], brackets['SBJ']['100']['mean']['hi_db'],
                a_ok=a_100_ok, b_ok=b_100_ok,
            )

    gain_vs_cost: dict[str, Any] = {}
    for arm_c in ('SBJ_ultra', 'SBJ_lite', 'SBJ'):
        if arm_c in arm_grids:
            b_rho = int(ev['best_rho'][arm_c])
            c_min_ok = is_arm_min_bracketed(arm_c, brackets, ev, b_rho)
            c_ok = bool(cd2_min_ok and c_min_ok)
            c_lo_emp, c_hi_emp = _arm_min_empirical_bounds(brackets[arm_c])
            c_res = _enforce_bounds_if_unbracketed(
                ev['contrast_best']('CD2', arm_c), c_ok, cd2_lo, cd2_hi, c_lo_emp, c_hi_emp,
                a_ok=cd2_min_ok, b_ok=c_min_ok,
            )
            c_lo = stageA6._to_float_bound(c_res['ci95_db'][0])
            c_res['would_pass_go'] = bool(verdict_a9(c_lo, c_ok) == 'GO')
            gain_vs_cost[f'CD2_minus_{arm_c}'] = c_res

    return dict(
        primary=primary,
        single_factor_controls=single_factor,
        gain_vs_cost_contrasts=gain_vs_cost,
    )


def analyze_stageA9(
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

    brackets = verify_crossing_brackets(arm_grids)
    std = stageA8b._eval_bootstrap_grids(arm_grids, crossing_fn, weights)
    std_con = _build_contrasts_from_eval(std, arm_grids, brackets)
    std_clean = _clean_eval_tables(std, brackets)

    # Haldane zero-floor sensitivity with full secondary contrasts & identical bracket cleaning
    hal_fn = lambda fer, snrs: crossing_haldane_n(fer, snrs, n_frames)
    hal = stageA8b._eval_bootstrap_grids(arm_grids, hal_fn, weights)
    hal_con = _build_contrasts_from_eval(hal, arm_grids, brackets)
    hal_clean = _clean_eval_tables(hal, brackets)

    all_brackets_ok = all(
        binfo['all_ok']
        for rmap in brackets.values()
        for binfo in rmap.values()
    )

    raw_out = dict(
        frames=n_frames,
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary=std_con['primary'],
        single_factor_controls=std_con['single_factor_controls'],
        gain_vs_cost_contrasts=std_con['gain_vs_cost_contrasts'],
        best_crossings=std_clean['best_crossings'],
        mean_crossing=std_clean['mean_crossing'],
        crossings_by_scenario=std_clean['crossings_by_scenario'],
        best_rho=std['best_rho'],
        empirical_brackets=brackets,
        all_reported_crossings_bracketed_le_0p5db=bool(all_brackets_ok),
        haldane_floor_sensitivity=dict(
            floor=0.5 / float(max(1, n_frames)),
            primary_CD2_minus_SBJ=hal_con['primary'],
            single_factor_controls=hal_con['single_factor_controls'],
            gain_vs_cost_contrasts=hal_con['gain_vs_cost_contrasts'],
            best_crossings=hal_clean['best_crossings'],
            mean_crossing=hal_clean['mean_crossing'],
            crossings_by_scenario=hal_clean['crossings_by_scenario'],
        ),
        diagnostics=diagnostics,
    )
    return _sanitize_strict_json(raw_out)


def rows_to_arm_grids_and_diag(
    rows: list[dict[str, Any]],
    frames: tuple[int, ...],
    grids: dict[str, dict[int, tuple[int, ...]]],
) -> tuple[dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]], dict[str, Any]]:
    fi = {f: i for i, f in enumerate(frames)}
    row_map: dict[tuple[int, str, int, int], dict[str, Any]] = {}
    syn0_false = 0
    for r in rows:
        k = (int(r['frame']), str(r['scenario']), int(r['rho']), int(r['snr']))
        if k in row_map:
            raise RuntimeError(f'Duplicate confirmation row key {k}')
        row_map[k] = r
        if int(r['arms']['F0']['syndrome']) == 0 and int(r['arms']['F0']['errors']) > 0:
            syn0_false += 1

    arm_grids: dict[str, dict[int, tuple[tuple[int, ...], np.ndarray]]] = {}
    fer_table: dict[str, dict[str, dict[str, Any]]] = {}
    trig_runtime: dict[str, list[float]] = {a: [] for a in grids}
    stage_counts: dict[str, Counter] = {a: Counter() for a in grids}
    delay_hit_stats: dict[str, list[int]] = {'F0_lcd_rho100_snr400': [], 'SBJ_rho100_snr400': []}

    for arm, rmap in grids.items():
        arm_grids[arm] = {}
        fer_table[arm] = {}
        for rho, snrs in sorted(rmap.items()):
            snrs_t = tuple(int(x) for x in snrs)
            fail_arr = np.zeros((len(frames), 2, len(snrs_t)), dtype=bool)
            fer_table[arm][str(rho)] = {}
            for si_snr, snr in enumerate(snrs_t):
                u_fail = g_fail = u_trig = g_trig = 0
                for f in frames:
                    for sc_i, s in enumerate(SCENARIOS):
                        rec = row_map[(f, s, rho, snr)]
                        a_rec = rec['arms'][arm]
                        err_b = int(a_rec['errors']) > 0
                        fail_arr[fi[f], sc_i, si_snr] = err_b
                        is_t = bool(a_rec.get('triggered', False))
                        if s == 'U':
                            u_fail += int(err_b)
                            u_trig += int(is_t)
                        else:
                            g_fail += int(err_b)
                            g_trig += int(is_t)
                        if is_t:
                            trig_runtime[arm].append(float(a_rec.get('cpu_seconds', a_rec['seconds'])) * 1000.0)
                            stage_counts[arm][str(a_rec.get('stage', ''))] += 1
                        if arm == 'SBJ' and rho == 100 and snr == 400 and is_t:
                            delay_hit_stats['F0_lcd_rho100_snr400'].append(int(rec['arms']['F0']['lcd_hits']))
                            delay_hit_stats['SBJ_rho100_snr400'].append(int(a_rec['delay_hits']))
                n_sc = float(len(frames))
                fer_table[arm][str(rho)][str(snr)] = dict(
                    snr_db=snr / 100.0,
                    U_fail=u_fail, G_fail=g_fail,
                    U_fer=u_fail / n_sc, G_fer=g_fail / n_sc,
                    mean_fer=0.5 * (u_fail + g_fail) / n_sc,
                    U_triggered=u_trig, G_triggered=g_trig,
                    triggered=u_trig + g_trig,
                    U_trigger_rate=u_trig / n_sc,
                    G_trigger_rate=g_trig / n_sc,
                    trigger_rate=(u_trig + g_trig) / (2.0 * n_sc),
                )
            arm_grids[arm][int(rho)] = (snrs_t, fail_arr)

    parallel_trigger_ms = {}
    for arm, vals in trig_runtime.items():
        if vals:
            arr_v = np.asarray(vals, dtype=np.float64)
            parallel_trigger_ms[arm] = dict(
                n_triggers=int(len(arr_v)),
                mean_ms=float(arr_v.mean()),
                median_ms=float(np.median(arr_v)),
                p95_ms=float(np.percentile(arr_v, 95)),
                stage_stops=dict(stage_counts[arm]),
            )

    diagnostics = dict(
        total_rows=len(rows),
        syn0_false_codewords=syn0_false,
        fer_curves=fer_table,
        parallel_worker_trigger_cpu_ms=parallel_trigger_ms,
        rho100_snr400_delay_hits_out_of_8=dict(
            n_triggers=len(delay_hit_stats['SBJ_rho100_snr400']),
            CD2_lcd_mean=(
                float(np.mean(delay_hit_stats['F0_lcd_rho100_snr400']))
                if delay_hit_stats['F0_lcd_rho100_snr400'] else None
            ),
            SBJ_mean=(
                float(np.mean(delay_hit_stats['SBJ_rho100_snr400']))
                if delay_hit_stats['SBJ_rho100_snr400'] else None
            ),
        ),
    )
    return arm_grids, diagnostics


# --------------------------------------------------------------------------- Gates G1-G3 (`cmd_gate`)
def _excluded_tier_cpu_sec(rows_f: list[dict[str, Any]], tier_grids: dict[str, dict[int, tuple[int, ...]]]) -> float:
    """Exact process_time() savings on frame `f` when restricting TIER1_GRIDS to a subset `tier_grids`."""
    saved = 0.0
    for r in rows_f:
        rho_i = int(r['rho'])
        snr_i = int(r['snr'])
        arms_r = r['arms']
        any_kept = False
        for arm_name, a_rec in arms_r.items():
            if arm_name == 'F0':
                continue
            if snr_i in tier_grids.get(arm_name, {}).get(rho_i, ()):
                any_kept = True
            else:
                saved += float(a_rec['cpu_seconds'])
        if not any_kept and 'F0' in arms_r:
            saved += float(arms_r['F0']['cpu_seconds'])
    return float(saved)


def _g3_shard_worker(worker_idx: int, frames: tuple[int, ...], out_path_str: str):
    C, _, _, helpers = sf.load_stage_runtime()
    ctx = C['ctx']
    tabs = build_static_tables(1024, ctx.system.l_max_cap, ctx.system.c1, ctx.system.c2)
    out = []
    for f in frames:
        t0 = process_time()
        rows_f = eval_frame_grids(C, helpers, tabs, int(f), TIER1_GRIDS)
        t_tier1 = float(process_time() - t0)
        tier_secs = {}
        for tname, tgrids in CANDIDATE_TIERS:
            if tname == 'tier1_full':
                tier_secs[tname] = t_tier1
            else:
                tier_secs[tname] = float(max(0.1, t_tier1 - _excluded_tier_cpu_sec(rows_f, tgrids)))
        out.append(dict(
            frame=int(f),
            tier_cpu_sec=tier_secs,
            n_rows=len(rows_f),
        ))
    ar.atomic_write_text(Path(out_path_str), json.dumps(out, allow_nan=False))


def cmd_gate(args):
    import stageA2
    import stageA5

    started = time.monotonic()
    gate_path = args.out.resolve()
    aid = current_attempt_id('gate')
    ledger_path = canonical_ledger_path()
    admitted_ext = os.environ.get('A9_ADMITTED_BY_LAUNCH_SH', '').strip() == '1'
    prior_ledger_h = read_ledger_hours(ledger_path, exclude_attempt_id=aid)
    if not admitted_ext:
        if PRIOR_DEV_HOURS + prior_ledger_h + GATE_BUDGET_HOURS > TOTAL_TASK_CAP_HOURS:
            raise RuntimeError('Insufficient cumulative budget remaining for gate')
        append_ledger_entry(ledger_path, 'gate', 'STARTED', 0.0, attempt_id=aid, reserved_hours=GATE_BUDGET_HOURS)

    gate_status = 'FAILED'
    reap_state = {'clean': True}
    try:
        print(sys.executable, flush=True)
        if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
            raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
        thread_env = ar.check_thread_env()
        if not 1 <= args.workers <= 32:
            raise ValueError('workers must be in 1..32')
        if PRIOR_DEV_HOURS + prior_ledger_h + GATE_BUDGET_HOURS > TOTAL_TASK_CAP_HOURS:
            gate_status = 'FAIL_BUDGET'
            raise RuntimeError('Insufficient cumulative budget remaining for gate')
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        pinned_md5 = verify_pinned_code()
        print(f'G2 PASS ({len(pinned_md5)} frozen upstream files verified)', flush=True)

        C, _, _, helpers = sf.load_stage_runtime()
        ctx, st = C['ctx'], C['stage3']
        tabs = build_static_tables(1024, ctx.system.l_max_cap, ctx.system.c1, ctx.system.c2)

        g1_rows = []
        n_triggered_g1 = 0
        for idx, f in enumerate(G1_FRAMES):
            s = 'U' if idx % 2 == 0 else 'G'
            base = st.inputs(ctx, f, s, 100)
            _, obs, truth = st.observed(ctx, base, 100, 400)

            # G1a: Full-entry `eval_key_arms` tamper invariance across ALL 5 arms (`CD2, Ctrl, SBJ, SBJ_lite, SBJ_ultra`)
            obs_clean = dict(y=obs['y'].copy(), pilot=obs['pilot'].copy(), sigma2=float(obs['sigma2']))
            all_arms = ('CD2', 'Ctrl', 'SBJ', 'SBJ_lite', 'SBJ_ultra')
            scored_real, raw_real = eval_key_arms(C, helpers, tabs, copy.deepcopy(obs_clean), truth, all_arms)
            truth_tampered = dict(
                truth,
                l_i=(np.asarray(truth['l_i'], dtype=int) + 37) % 103,
                k_real=-np.asarray(truth['k_real'], dtype=float),
                g_i=np.full(len(truth['g_i']), -0.5 + 0.5j, dtype=complex),
                info=1 - np.asarray(truth['info'], dtype=np.uint8),
                coded=1 - np.asarray(truth['coded'], dtype=np.uint8),
            )
            scored_tamp, raw_tamp = eval_key_arms(C, helpers, tabs, copy.deepcopy(obs_clean), truth_tampered, all_arms)
            is_trig = bool(scored_real['CD2']['triggered'])
            n_triggered_g1 += int(is_trig)
            tamper_ok = bool(
                scored_real['F0']['decoded_sha'] == scored_tamp['F0']['decoded_sha']
                and all(
                    raw_real[a]['decoded_sha'] == raw_tamp[a]['decoded_sha']
                    and raw_real[a]['syndrome'] == raw_tamp[a]['syndrome']
                    and raw_real[a]['triggered'] == raw_tamp[a]['triggered']
                    and np.array_equal(raw_real[a]['l_hat'], raw_tamp[a]['l_hat'])
                    and np.array_equal(raw_real[a]['nu_hat'], raw_tamp[a]['nu_hat'])
                    for a in all_arms
                )
                and scored_real['SBJ']['errors'] != scored_tamp['SBJ']['errors']
            )

            # G1b: (i) f0_injected_no_pf == stageA2.f0_true(..., 'ls') AND
            #      (ii) Injecting CD2's own r0_dopplers into Ctrl's path bitwise reproduces CD2's Round-0, Round-1
            #           continuation inputs, AND full 2-pass continuation outputs (syndrome, passes_used, decoded)!
            dec_ref, arr_ref, syn_ref, _ = stageA2.f0_true(C, obs, truth, 'ls')
            dec_fast, arr_fast, syn_fast = f0_injected_no_pf(ctx, obs, truth['l_i'], truth['k_real'], truth['g_i'])

            dec_cd0, arr_cd0, syn_cd0, _ = st.e1.f0_state(ctx, obs)
            l_cd0 = np.asarray(arr_cd0['r0_delays'], dtype=int)
            nu_cd0 = np.asarray(arr_cd0['r0_dopplers'], dtype=float)
            ctrl_reinj = run_ctrl_with_dopplers_notruth(ctx, helpers, obs, l_cd0, nu_cd0)
            arr_re = ctrl_reinj['arrays_f0']

            state_keys = (
                'r0_delays', 'r0_dopplers', 'r0_gains', 'r0_decoded', 'r0_app', 'r0_check',
                'r1_delays', 'r1_dopplers', 'r1_gains', 'r1_decoded', 'r1_app', 'r1_check',
            )
            f0_r01_bitwise = all(np.array_equal(arr_re[k], arr_cd0[k]) for k in state_keys)
            if syn_cd0 == 0:
                cont_bitwise = bool(
                    ctrl_reinj['syndrome'] == 0
                    and ctrl_reinj['passes_used'] == 0
                    and np.array_equal(ctrl_reinj['decoded'], dec_cd0['decoded'])
                )
            else:
                cd_notruth = _run_cd2_continuation_notruth(ctx, helpers, obs, arr_cd0, max_passes=2, tag='CD2')
                cd_timed = sf2.run_cd_timed(ctx, helpers, obs, arr_cd0, truth, arm_spec='A1', max_passes=2)
                cont_bitwise = bool(
                    np.array_equal(ctrl_reinj['decoded'], cd_notruth['decoded'])
                    and _decoded_sha(ctrl_reinj['decoded']) == cd_timed['decoded_sha']
                    and int(ctrl_reinj['syndrome']) == int(cd_notruth['syndrome']) == int(cd_timed['syndrome'])
                    and int(ctrl_reinj['passes_used']) == int(cd_notruth['passes_used']) == int(cd_timed['passes_used'])
                )

            ctrl_identity_ok = bool(
                int(syn_ref) == int(syn_fast)
                and np.array_equal(dec_ref['decoded'], dec_fast['decoded'])
                and all(np.array_equal(arr_ref[k], arr_fast[k]) for k in state_keys)
                and f0_r01_bitwise
                and cont_bitwise
            )

            # G1c: cyclic_nll_and_grad(use_c64=False) exactness vs stageA5.sb_nll_and_grad
            r_u, pt_u, vd_u, s2_u = unpack_obs_unit_power(obs, ctx.system.c1, ctx.system.c2)
            l_t = np.asarray(truth['l_i'], dtype=np.int64)
            geom5 = stageA5.precompute_delay_geometry(l_t, 1024, ctx.system.c1)
            spt5 = pt_u[geom5['cols']]
            th_t = np.concatenate([
                np.asarray(truth['k_real'], dtype=float),
                np.real(truth['g_i']),
                np.imag(truth['g_i']),
            ])
            nll5, grad5 = stageA5.sb_nll_and_grad(th_t, geom5, spt5, r_u, vd_u, s2_u)
            fgeom9 = prepare_cyclic_grad_geom(tabs, l_t, use_c64=False)
            nll9, grad9 = cyclic_nll_and_grad(th_t, fgeom9, spt5, r_u, vd_u, s2_u)
            grad_diff = float(np.max(np.abs(grad9 - grad5)))
            nll_diff = float(abs(nll9 - nll5))
            grad_ok = bool(nll_diff < 1e-10 and grad_diff < 1e-10)

            if not (tamper_ok and ctrl_identity_ok and grad_ok):
                raise AssertionError(
                    f'G1 failed at {(f, s)}: tamper={tamper_ok}, ctrl_identity={ctrl_identity_ok}, '
                    f'nll_diff={nll_diff}, grad_diff={grad_diff}'
                )
            g1_rows.append(dict(
                frame=f, scenario=s, triggered=is_trig, tamper_ok=tamper_ok, ctrl_identity_ok=ctrl_identity_ok,
                nll_diff=nll_diff, max_grad_diff=grad_diff,
            ))
        if n_triggered_g1 < 2:
            raise AssertionError(f'G1 must exercise >=2 triggered keys, got n_triggered_g1={n_triggered_g1}')
        print(
            f'G1 PASS ({len(g1_rows)} keys, {n_triggered_g1} triggered: '
            f'full tamper invariance + bitwise Ctrl Round-0/1/continuation identity + exact gradient)',
            flush=True,
        )

        # G3: Live-enforced cost projection on 4 untouched isolation frames 40900-40903
        n_g3_w = min(args.workers, len(G3_ISOLATION_FRAMES))
        poll_margin = gate_poll_margin_sec(n_g3_w)
        live_gate_cap_sec = max(30.0, GATE_BUDGET_HOURS * 3600.0 - poll_margin)
        with tempfile.TemporaryDirectory(dir=str(gate_path.parent), prefix='a9_g3_') as tmp_d:
            tmp_p = Path(tmp_d)
            g3_jobs = [
                (wi, tuple(G3_ISOLATION_FRAMES[wi::n_g3_w]), str(tmp_p / f'g3_{wi:02d}.json'))
                for wi in range(n_g3_w)
            ]
            _run_sharded_supervised(_g3_shard_worker, g3_jobs, n_g3_w, live_gate_cap_sec, reap_state)
            g3_rows = []
            for wi in range(n_g3_w):
                g3_rows.extend(json.loads((tmp_p / f'g3_{wi:02d}.json').read_text(encoding='utf-8')))
            g3_rows.sort(key=lambda r: r['frame'])

        gate_cpu_h = sf._used_cpu_seconds() / 3600.0
        if gate_cpu_h > GATE_BUDGET_HOURS:
            raise RuntimeError(f'Gate exceeded GATE_BUDGET_HOURS ({gate_cpu_h:.4f} > {GATE_BUDGET_HOURS})')

        total_ledger_after_gate = prior_ledger_h + gate_cpu_h
        eff_cap_h = compute_effective_run_cap_hours(total_ledger_after_gate)
        tier_means = {
            tname: float(np.mean([r['tier_cpu_sec'][tname] for r in g3_rows]))
            for tname, _ in CANDIDATE_TIERS
        }
        candidates, selected = select_confirmation_tier(tier_means, eff_cap_h)
        all_passed = bool(
            len(g1_rows) == len(G1_FRAMES)
            and n_triggered_g1 >= 2
            and len(g3_rows) == len(G3_ISOLATION_FRAMES)
            and selected is not None
        )

        payload = dict(
            _argv=sys.argv,
            _config=dict(
                python_executable=sys.executable,
                threads=thread_env,
                workers=args.workers,
                own_md5=own_md5(),
                pinned_code_md5=pinned_md5,
                frozen_extra_md5=helpers['extra_md5'],
                p1_source_md5=ar.frozen_p1_md5(ctx),
                conf_frames=[CONF_FRAMES[0], CONF_FRAMES[-1]],
                g3_isolation_frames=list(G3_ISOLATION_FRAMES),
                ledger_path=str(ledger_path),
            ),
            all_passed=all_passed,
            selected=selected,
            G1=dict(passed=True, keys_checked=len(g1_rows), triggered_keys=n_triggered_g1, rows=g1_rows),
            G2=dict(passed=True, files_verified=len(pinned_md5)),
            G3=dict(
                passed=selected is not None,
                total_task_cap_hours=TOTAL_TASK_CAP_HOURS,
                prior_dev_hours=PRIOR_DEV_HOURS,
                prior_ledger_hours=prior_ledger_h,
                gate_cpu_hours=gate_cpu_h,
                gate_poll_margin_seconds=poll_margin,
                timing_reserve_hours=TIMING_RESERVE_HOURS,
                safety_reserve_hours=SAFETY_RESERVE_HOURS,
                effective_run_cap_hours=eff_cap_h,
                margin=COST_MARGIN,
                overhead_hours=OVERHEAD_HOURS,
                isolation_frames_rows=g3_rows,
                candidates=candidates,
            ),
            gate_cpu_hours=gate_cpu_h,
            gate_wall_seconds=time.monotonic() - started,
        )
        ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
        gate_status = 'PASS' if all_passed else 'FAIL_BUDGET'
        print(
            f'GATE_STATUS={gate_status} '
            f'selected_tier={None if selected is None else selected["tier"]} '
            f'proj_h={None if selected is None else round(selected["projected_hours_with_margin"], 3)} '
            f'cap_h={eff_cap_h:.3f} gate_cpu_h={gate_cpu_h:.4f}',
            flush=True,
        )
    finally:
        append_ledger_entry(
            ledger_path, 'gate', gate_status, sf._used_cpu_seconds() / 3600.0,
            attempt_id=aid, reserved_hours=GATE_BUDGET_HOURS, reaped_all_workers=reap_state['clean'],
        )

    sys.exit(0 if gate_status == 'PASS' else 1)


# --------------------------------------------------------------------------- Confirmation Run (`cmd_run`) & Readout (`cmd_read`)
def _grids_from_selected(sel_grids: dict[str, dict[str, list[int]]]) -> dict[str, dict[int, tuple[int, ...]]]:
    return {
        arm: {int(r): tuple(int(s) for s in snrs) for r, snrs in rmap.items()}
        for arm, rmap in sel_grids.items()
    }


def _conf_shard_worker(shard_idx: int, frames: tuple[int, ...], sel_grids: dict[str, dict[str, list[int]]], raw_dir: Path):
    C, _, _, helpers = sf.load_stage_runtime()
    ctx = C['ctx']
    tabs = build_static_tables(1024, ctx.system.l_max_cap, ctx.system.c1, ctx.system.c2)
    grids = _grids_from_selected(sel_grids)
    lines: list[str] = []
    for f in frames:
        for row in eval_frame_grids(C, helpers, tabs, int(f), grids):
            lines.append(json.dumps(row, allow_nan=False) + '\n')
    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
    sf._write_gzip_jsonl_atomic(final_path, lines)
    print(f'Shard {shard_idx:03d} done ({len(frames)} frames, {len(lines)} rows)', flush=True)


def render_results_md(results: dict[str, Any]) -> str:
    a = results['analysis']
    p = a['primary']
    hal_all = a['haldane_floor_sensitivity']
    hal = hal_all['primary_CD2_minus_SBJ']
    rt = results['runtime']
    lines = [
        f'# Stage A9 Confirmation Results (`frames {CONF_FRAMES[0]}-{CONF_FRAMES[-1]}`)',
        '',
        f'- **Verdict**: **`{p["verdict"]}`** (`GO` threshold: `LB95 >= {p["go_threshold_db"]:.2f} dB` + all primary crossings bracketed `<= 0.50 dB`)',
        f'- **Primary contrast (`min CD2 - min SBJ`)**: **`{p["point_db"]} dB`**, 95% paired frame bootstrap CI **`{p["ci95_db"]} dB`**',
        f'  - `CD2` best: `{p["arm_a_best_db"]} dB` at `rho = {p["arm_a_best_rho"]}`',
        f'  - `SBJ` best: `{p["arm_b_best_db"]} dB` at `rho = {p["arm_b_best_rho"]}`',
        f'  - Primary crossings bracketed `<= 0.50 dB`: `{p["primary_bracketed_le_0p5db"]}` (all reported crossings bracketed: `{a["all_reported_crossings_bracketed_le_0p5db"]}`)',
        f'- **Haldane zero-floor (`0.5/{a["frames"]}`) sensitivity**: `{hal["point_db"]} dB`, 95% CI `{hal["ci95_db"]} dB` (`{hal["verdict"]}`)',
        f'- **Cumulative deinlab CPU**: `{rt["cumulative_core_hours_so_far"]:.4f} / {TOTAL_TASK_CAP_HOURS:.2f}` core-hours (`prior_dev = {rt["prior_dev_core_hours"]:.4f} h`, `prior_ledger = {rt["prior_ledger_core_hours"]:.4f} h`, `run = {rt["run_core_hours"]:.4f} h`, `timing = {rt.get("timing_core_hours", 0.0):.4f} h`)',
        '',
        '## 1. Per-Arm Best Crossings & Same-Quantity Empirical Brackets',
        '',
        '| Arm | Best rho | Best 1% FER (dB) | 95% CI (dB) | U Crossing / Bracket (dB) | G Crossing / Bracket (dB) | 0.5*(C_U+C_G) Bracket (dB) |',
        '|---|---:|---:|---|---|---|---|',
    ]
    scen_pt = a['crossings_by_scenario']
    for arm, binfo in a['best_crossings'].items():
        brho = str(binfo['best_rho'])
        eb = a['empirical_brackets'][arm][brho]
        u_pt = scen_pt[arm]['U'][brho]
        g_pt = scen_pt[arm]['G'][brho]
        lines.append(
            f'| `{arm}` | `{brho}` | `{binfo["best_db"]}` | `{binfo["ci95_db"]}` | '
            f'`{u_pt}` in `{eb["U"]["bracket"]}` (gap `{eb["U"]["gap_db"]}`) | '
            f'`{g_pt}` in `{eb["G"]["bracket"]}` (gap `{eb["G"]["gap_db"]}`) | '
            f'`{eb["mean"]["bracket"]}` (gap `{eb["mean"]["gap_db"]}`) |'
        )

    lines.extend([
        '',
        '## 2. Single-Factor Controls (`CD2` Own Delay Front End + `SBG` Doppler)',
        '',
        '| Contrast | Standard Point (dB) | Standard 95% CI (dB) | Haldane Point (dB) | Haldane 95% CI (dB) | Bracketed <=0.5dB |',
        '|---|---:|---|---:|---|---|',
    ])
    for cname, cval in a['single_factor_controls'].items():
        hval = hal_all['single_factor_controls'][cname]
        lines.append(
            f'| `{cname}` | `{cval["point_db"]}` | `{cval["ci95_db"]}` | '
            f'`{hval["point_db"]}` | `{hval["ci95_db"]}` | `{cval["bracketed_le_0p5db"]}` |'
        )

    lines.extend([
        '',
        '## 3. Gain-vs-Cost Contrasts vs `CD2` Best',
        '',
        '| Contrast | Best rho | Best (dB) | Gain vs CD2 (dB) | 95% CI (dB) | Haldane Gain / CI (dB) | Bracketed <=0.5dB |',
        '|---|---:|---:|---:|---|---|---|',
    ])
    for cname, cval in a['gain_vs_cost_contrasts'].items():
        hval = hal_all['gain_vs_cost_contrasts'][cname]
        lines.append(
            f'| `{cname}` | `{cval["arm_b_best_rho"]}` | `{cval["arm_b_best_db"]}` | '
            f'`{cval["point_db"]}` | `{cval["ci95_db"]}` | `{hval["point_db"]} / {hval["ci95_db"]}` | `{cval["bracketed_le_0p5db"]}` |'
        )

    if results.get('timing') is not None:
        lines.extend([
            '',
            '## 4. Quiet Single-Core CPU Gain-vs-Cost Curve (`taskset` pinned, `process_time` CPU)',
            '',
            '| Arm | Best rho | Best 1% FER (dB) | Gain vs CD2 (dB) [95% CI] | rho=.10,4.0dB Mean/p95 CPU (ms) [Mean & p95 vs CD2 / HG] | rho=.20,4.5dB Mean/p95 CPU (ms) [Mean & p95 vs CD2 / HG] |',
            '|---|---:|---:|---|---|---|',
        ])
        for row in results['timing']['gain_vs_cost_curve']:
            lines.append(
                f'| `{row["arm"]}` | `{row["best_rho"]}` | `{row["best_1pct_fer_db"]}` | '
                f'`{row["gain_vs_CD2_db"]}` `{row["gain_ci95_db"]}` | '
                f'`{row["rho100_snr400_cpu_mean_ms"]:.2f} / {row["rho100_snr400_cpu_p95_ms"]:.2f}` '
                f'[mean `{row["rho100_vs_CD2"]:.2f}x`/`{row["rho100_vs_HG"]:.2f}x`, p95 `{row["rho100_p95_vs_CD2"]:.2f}x`/`{row["rho100_p95_vs_HG"]:.2f}x`] | '
                f'`{row["rho200_snr450_cpu_mean_ms"]:.2f} / {row["rho200_snr450_cpu_p95_ms"]:.2f}` '
                f'[mean `{row["rho200_vs_CD2"]:.2f}x`/`{row["rho200_vs_HG"]:.2f}x`, p95 `{row["rho200_p95_vs_CD2"]:.2f}x`/`{row["rho200_p95_vs_HG"]:.2f}x`] |'
            )

        lines.extend([
            '',
            '## 5. Full Quiet Single-Core Per-Trigger & Scenario-Weighted Amortized CPU Panels',
            '',
            '| Panel | Arm | Mean CPU (ms) | Median CPU (ms) | p95 CPU (ms) | Mean vs CD2 / HG | p95 vs CD2 / HG | Amortized Full-Frame CPU (ms) |',
            '|---|---|---:|---:|---:|---|---|---:|',
        ])
        for pname, pdata in results['timing']['panels'].items():
            am_map = pdata['amortized_full_frame_cpu_ms']['equal_weight_mean']
            for bname, bstat in pdata['branches'].items():
                lines.append(
                    f'| `{pname}` | `{bname}` | `{bstat["mean_ms"]:.2f}` | `{bstat["median_ms"]:.2f}` | '
                    f'`{bstat["p95_ms"]:.2f}` | `{bstat["ratio_vs_CD2"]:.2f}x / {bstat["ratio_vs_HG"]:.2f}x` | '
                    f'`{bstat["p95_ratio_vs_CD2"]:.2f}x / {bstat["p95_ratio_vs_HG"]:.2f}x` | '
                    f'`{am_map[bname]:.2f}` |'
                )
    return '\n'.join(lines) + '\n'


def _load_all_shards(raw_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(N_SHARDS):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
        if not sp.is_file():
            raise FileNotFoundError(f'Missing confirmation shard {sp}')
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def cmd_run(args):
    import stageA2

    out_dir = args.out.resolve()
    raw_dir = out_dir / 'raw'
    aid = current_attempt_id('run')
    ledger_path = canonical_ledger_path()
    admitted_ext = os.environ.get('A9_ADMITTED_BY_LAUNCH_SH', '').strip() == '1'
    prior_ledger_h = read_ledger_hours(ledger_path, exclude_attempt_id=aid)
    eff_cap_h = compute_effective_run_cap_hours(prior_ledger_h)
    poll_margin = run_poll_margin_sec(getattr(args, 'workers', 32))
    if not admitted_ext:
        if eff_cap_h * 3600.0 - poll_margin <= 60.0 or PRIOR_DEV_HOURS + prior_ledger_h + eff_cap_h > TOTAL_TASK_CAP_HOURS:
            print(f'STOPPED_BUDGET before run: eff_cap_h={eff_cap_h:.4f}, poll_margin_s={poll_margin:.1f}', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        append_ledger_entry(ledger_path, 'run', 'STARTED', 0.0, attempt_id=aid, reserved_hours=eff_cap_h)

    run_status = 'FAILED'
    reap_state = {'clean': True}
    try:
        print(sys.executable, flush=True)
        if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
            raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
        thread_env = ar.check_thread_env()
        if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
            raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
        if not 1 <= args.workers <= 32:
            raise ValueError('workers must be in 1..32')
        raw_dir.mkdir(parents=True, exist_ok=True)
        if list(raw_dir.glob('rows_shard*.jsonl*')):
            raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')

        gate_bytes = args.gate.resolve().read_bytes()
        gate_md5 = hashlib.md5(gate_bytes).hexdigest()
        gate = json.loads(gate_bytes.decode('utf-8'))
        if not gate.get('all_passed') or not gate.get('selected'):
            raise RuntimeError('Refusing to run confirmation without passing stageA9_gate.json')
        if Path(gate['_config']['ledger_path']).resolve() != ledger_path:
            raise RuntimeError(f'Ledger mismatch: gate used {gate["_config"]["ledger_path"]} != {ledger_path}')

        live_own = own_md5()
        pinned_md5 = verify_pinned_code()
        verify_freeze_commit_if_git(args.freeze_commit, live_own)
        if gate['_config']['own_md5'] != live_own:
            raise RuntimeError('gate own_md5 differs from live Stage A9 files')
        if gate['_config']['pinned_code_md5'] != pinned_md5:
            raise RuntimeError('gate pinned_code_md5 differs from live upstream files')

        poll_margin = run_poll_margin_sec(args.workers)
        live_shard_cap_sec = eff_cap_h * 3600.0 - poll_margin
        if live_shard_cap_sec <= 60.0:
            run_status = 'STOPPED_BUDGET'
            print(f'STOPPED_BUDGET before run: eff_cap_h={eff_cap_h:.4f}, poll_margin_s={poll_margin:.1f}', flush=True)
            sys.exit(BUDGET_EXIT_CODE)

        sel_tier = gate['selected']['tier']
        sel_grids_raw = gate['selected']['grids']
        grids = _grids_from_selected(sel_grids_raw)
        wall_start = time.monotonic()
        jobs = [
            (idx, tuple(CONF_FRAMES[idx::N_SHARDS]), sel_grids_raw, raw_dir)
            for idx in range(N_SHARDS)
        ]
        run_cfg = dict(
            _argv=sys.argv,
            freeze_commit=args.freeze_commit,
            gate_md5=gate_md5,
            selected_tier=sel_tier,
            conf_frames=[CONF_FRAMES[0], CONF_FRAMES[-1]],
            n_shards=N_SHARDS,
            workers=args.workers,
            effective_run_cap_hours=eff_cap_h,
            run_poll_margin_seconds=poll_margin,
            ledger_path=str(ledger_path),
            own_md5=live_own,
            threads=thread_env,
        )
        ar.atomic_write_text(out_dir / 'RUN_CONFIG.json', json.dumps(run_cfg, indent=2, allow_nan=False) + '\n')

        print(
            f'Launching Stage A9 confirmation ONCE on frames {CONF_FRAMES[0]}..{CONF_FRAMES[-1]} '
            f'(tier={sel_tier}, workers={args.workers}, cap={eff_cap_h:.3f}h, poll_margin={poll_margin:.0f}s)...',
            flush=True,
        )
        _run_sharded_supervised(_conf_shard_worker, jobs, args.workers, live_shard_cap_sec, reap_state)

        raw_md5 = {}
        for idx in range(N_SHARDS):
            sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
            raw_md5[sp.name] = ar.md5_file(sp)
        ar.atomic_write_text(
            out_dir / 'REMOTE_ROWS_MD5.txt',
            ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
        )

        # Include full aggregation + 2000-draw bootstrap CPU in run_cpu_h BEFORE checking 20.0h cap!
        rows = _load_all_shards(raw_dir)
        arm_grids, diag = rows_to_arm_grids_and_diag(rows, CONF_FRAMES, grids)
        analysis = analyze_stageA9(arm_grids, stageA2.crossing, diag)

        run_cpu_h = sf._used_cpu_seconds() / 3600.0
        cum_h = PRIOR_DEV_HOURS + prior_ledger_h + run_cpu_h
        if cum_h >= TOTAL_TASK_CAP_HOURS:
            run_status = 'STOPPED_BUDGET'
            print(f'STOPPED_BUDGET after analysis: cumulative={cum_h:.4f}h >= {TOTAL_TASK_CAP_HOURS}h', flush=True)
            sys.exit(BUDGET_EXIT_CODE)

        results = dict(
            _argv=sys.argv,
            _config=run_cfg,
            runtime=dict(
                prior_dev_core_hours=PRIOR_DEV_HOURS,
                prior_ledger_core_hours=prior_ledger_h,
                gate_core_hours=float(gate['gate_cpu_hours']),
                run_core_hours=run_cpu_h,
                timing_core_hours=0.0,
                cumulative_core_hours_so_far=cum_h,
                total_task_cap_hours=TOTAL_TASK_CAP_HOURS,
                run_wall_seconds=time.monotonic() - wall_start,
            ),
            raw_shard_count=len(raw_md5),
            analysis=analysis,
            timing=None,
        )
        ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
        ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
        run_status = 'DONE'
        print(
            f'STAGEA9_RUN_DONE verdict={analysis["primary"]["verdict"]} '
            f'point={analysis["primary"]["point_db"]} ci={analysis["primary"]["ci95_db"]} '
            f'run_cpu_h={run_cpu_h:.4f} cum_h={cum_h:.4f}',
            flush=True,
        )
    finally:
        append_ledger_entry(
            ledger_path, 'run', run_status, sf._used_cpu_seconds() / 3600.0,
            attempt_id=aid, reserved_hours=eff_cap_h, reaped_all_workers=reap_state['clean'],
        )


# --------------------------------------------------------------------------- Quiet Single-Core Timing (`cmd_timing`)
def get_smt_siblings(cpu_id: int) -> list[int]:
    """Return all hardware threads (SMT siblings) sharing the physical core of `cpu_id`."""
    if platform.system() != 'Linux':
        return [int(cpu_id)]
    topo = Path(f'/sys/devices/system/cpu/cpu{int(cpu_id)}/topology/thread_siblings_list')
    if not topo.is_file():
        return [int(cpu_id)]
    out: list[int] = []
    for part in topo.read_text(encoding='utf-8').strip().split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out)) if out else [int(cpu_id)]


def _measure_physical_core_busy_pct(cpu_id: int, duration_s: float = 0.5) -> tuple[float, list[int]]:
    """Measure max busy percentage across ALL SMT sibling threads of `cpu_id`'s physical core."""
    sibs = get_smt_siblings(cpu_id)
    if platform.system() != 'Linux':
        return 0.0, sibs

    def _read_sibs():
        snap = {}
        for ln in Path('/proc/stat').read_text(encoding='utf-8').splitlines():
            ps = ln.split()
            if ps and ps[0].startswith('cpu') and ps[0][3:].isdigit():
                cid = int(ps[0][3:])
                if cid in sibs:
                    vals = [int(x) for x in ps[1:]]
                    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                    snap[cid] = (sum(vals), idle)
        if len(snap) != len(sibs):
            raise RuntimeError(f'Missing SMT siblings in /proc/stat for {sibs}: got {sorted(snap)}')
        return snap

    s0 = _read_sibs()
    time.sleep(duration_s)
    s1 = _read_sibs()
    max_busy = 0.0
    for cid in sibs:
        dt = max(1, s1[cid][0] - s0[cid][0])
        di = max(0, s1[cid][1] - s0[cid][1])
        max_busy = max(max_busy, float(100.0 * (1.0 - di / float(dt))))
    return max_busy, sibs


def _lat_stats_ms(vals_sec: list[float]) -> dict[str, Any]:
    arr = np.asarray(vals_sec, dtype=np.float64) * 1000.0
    return dict(
        n=int(len(arr)),
        mean_ms=float(arr.mean()),
        median_ms=float(np.median(arr)),
        p95_ms=float(np.percentile(arr, 95)),
    )


def _lookup_conf_trigger_rates(fer_curves: dict[str, Any], rho: int, snr: int) -> tuple[float, float]:
    """Read exact confirmation-cohort U and G F0 trigger rates from any arm that evaluated (rho, snr)."""
    r_str, s_str = str(rho), str(snr)
    for arm_curves in fer_curves.values():
        cell = arm_curves.get(r_str, {}).get(s_str)
        if cell is not None and 'U_trigger_rate' in cell and 'G_trigger_rate' in cell:
            return float(cell['U_trigger_rate']), float(cell['G_trigger_rate'])
    raise KeyError(f'Full confirmation trigger rates for rho={rho}, snr={snr} missing from fer_curves')


def cmd_timing(args):
    out_dir = args.out.resolve()
    aid = current_attempt_id('timing')
    ledger_path = canonical_ledger_path()
    admitted_ext = os.environ.get('A9_ADMITTED_BY_LAUNCH_SH', '').strip() == '1'
    prior_ledger_h = read_ledger_hours(ledger_path, exclude_attempt_id=aid)
    spent_before = PRIOR_DEV_HOURS + prior_ledger_h
    timing_cap_h = min(TIMING_RESERVE_HOURS, max(0.0, TOTAL_TASK_CAP_HOURS - spent_before - 0.01))
    if not admitted_ext:
        if timing_cap_h * 3600.0 < 120.0 or spent_before + timing_cap_h > TOTAL_TASK_CAP_HOURS:
            print(f'STOPPED_BUDGET before timing: spent_before={spent_before:.4f}h, timing_cap_h={timing_cap_h:.4f}h', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        append_ledger_entry(
            ledger_path, 'timing', 'STARTED', 0.0,
            attempt_id=aid,
            reserved_hours=timing_cap_h,
        )

    timing_status = 'FAILED'
    try:
        if timing_cap_h * 3600.0 < 120.0 or spent_before + timing_cap_h > TOTAL_TASK_CAP_HOURS:
            timing_status = 'STOPPED_BUDGET'
            print(f'STOPPED_BUDGET before timing: spent_before={spent_before:.4f}h, timing_cap_h={timing_cap_h:.4f}h', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        if platform.system() == 'Linux':
            hard_cpu_sec = max(30, int(math.floor(timing_cap_h * 3600.0)) - 2)
            _, cur_hard = resource.getrlimit(resource.RLIMIT_CPU)
            if cur_hard > 0:
                hard_cpu_sec = min(hard_cpu_sec, int(cur_hard))
            resource.setrlimit(resource.RLIMIT_CPU, (hard_cpu_sec, hard_cpu_sec))

        print(sys.executable, flush=True)
        if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
            raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
        ar.check_thread_env()
        if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
            raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')

        aff = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else [0]
        if platform.system() == 'Linux' and len(aff) != 1:
            raise RuntimeError(f'timing must be pinned to 1 CPU via taskset, got affinity={aff}')
        pinned_cpu = int(aff[0])
        live_sib_busy, smt_siblings = _measure_physical_core_busy_pct(pinned_cpu, 0.4)
        env_busy = os.environ.get('A9_MEASURED_CPU_BUSY_PCT', '').strip()
        measured_busy_pct = max(live_sib_busy, float(env_busy)) if env_busy else live_sib_busy
        if platform.system() == 'Linux' and measured_busy_pct >= 10.0:
            raise RuntimeError(
                f'Pinned physical core {pinned_cpu} (siblings={smt_siblings}) is not quiet '
                f'(max_busy={measured_busy_pct:.2f}% >= 10%)'
            )

        verify_pinned_code()
        verify_freeze_commit_if_git(args.freeze_commit, own_md5())
        results_path = out_dir / 'results.json'
        results = json.loads(results_path.read_text(encoding='utf-8'))
        if results['_config']['freeze_commit'] != args.freeze_commit:
            raise RuntimeError('timing freeze-commit differs from results.json')
        if results['_config']['own_md5'] != own_md5():
            raise RuntimeError('timing own_md5 differs from results.json')
        if Path(results['_config']['ledger_path']).resolve() != ledger_path:
            raise RuntimeError('timing ledger_path differs from results.json')

        rem_sec = timing_cap_h * 3600.0 - 25.0
        t_wall0 = perf_counter()
        C, _, _, helpers = sf.load_stage_runtime()
        ctx, st = C['ctx'], C['stage3']
        tabs = build_static_tables(1024, ctx.system.l_max_cap, ctx.system.c1, ctx.system.c2)
        ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)

        # Unmeasured warmup on isolation frame 40900 + bitwise parity verification of _run_hg_continuation_notruth
        _, w_obs, w_truth = st.observed(ctx, st.inputs(ctx, 40900, 'U', 100), 100, 400)
        w_obs_only = dict(y=w_obs['y'], pilot=w_obs['pilot'], sigma2=w_obs['sigma2'])
        _, w_arr, _, _ = st.e1.f0_state(ctx, w_obs_only)
        _run_cd2_continuation_notruth(ctx, helpers, w_obs_only, w_arr, max_passes=2, tag='CD2')
        hg_nt = _run_hg_continuation_notruth(
            ctx, helpers, w_obs_only, w_arr,
            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), max_passes=2,
        )
        hg_ref = ar.run_hg_arm(
            ctx, helpers, w_obs_only, w_arr, w_truth,
            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), max_passes=2, record_match=False,
        )['HG']
        if _decoded_sha(hg_nt['decoded']) != hg_ref['decoded_sha'] or int(hg_nt['syndrome']) != int(hg_ref['syndrome']):
            raise RuntimeError('_run_hg_continuation_notruth failed bitwise parity check vs hs_arms.run_hg_arm')
        run_ctrl_triggered_branch(ctx, helpers, tabs, w_obs_only, w_arr['r0_delays'])
        for p_name in ('SBJ_ultra', 'SBJ_lite', 'SBJ'):
            run_sbj_triggered_branch(ctx, helpers, tabs, w_obs_only, preset=p_name)
        if sf._used_cpu_seconds() >= rem_sec:
            timing_status = 'STOPPED_BUDGET'
            sys.exit(BUDGET_EXIT_CODE)

        fer_curves = results['analysis']['diagnostics']['fer_curves']
        panels_out: dict[str, Any] = {}
        for panel_name, rho, snr, n_per_scen in TIMING_PANELS:
            u_trig_rate, g_trig_rate = _lookup_conf_trigger_rates(fer_curves, rho, snr)
            trig_by_s: dict[str, list[tuple[str, int, dict[str, Any], dict[str, Any], float]]] = {'U': [], 'G': []}
            untrig_f0_cpu_by_s: dict[str, list[float]] = {'U': [], 'G': []}
            for s in SCENARIOS:
                for f in CONF_FRAMES:
                    if sf._used_cpu_seconds() >= rem_sec:
                        timing_status = 'STOPPED_BUDGET'
                        sys.exit(BUDGET_EXIT_CODE)
                    base = st.inputs(ctx, f, s, rho)
                    _, obs, _ = st.observed(ctx, base, rho, snr)
                    obs_only = dict(y=obs['y'], pilot=obs['pilot'], sigma2=obs['sigma2'])
                    tc0 = process_time()
                    _, arrays, syn, _ = st.e1.f0_state(ctx, obs_only)
                    f0_cpu = float(process_time() - tc0)
                    if syn == 0:
                        if len(untrig_f0_cpu_by_s[s]) < 20:
                            untrig_f0_cpu_by_s[s].append(f0_cpu)
                    else:
                        if len(trig_by_s[s]) < n_per_scen:
                            trig_by_s[s].append((s, f, obs_only, arrays, f0_cpu))
                    if len(trig_by_s[s]) == n_per_scen and len(untrig_f0_cpu_by_s[s]) >= 10:
                        break
                if len(trig_by_s[s]) < n_per_scen:
                    raise RuntimeError(f'Insufficient triggered keys in {panel_name}/{s}: got {len(trig_by_s[s])}')

            interleaved = [item for pair in zip(trig_by_s['U'], trig_by_s['G'], strict=True) for item in pair]
            cpu_lists: dict[str, list[float]] = {a: [] for a in TIMING_ARMS}
            cpu_by_s: dict[str, dict[str, list[float]]] = {'U': {a: [] for a in TIMING_ARMS}, 'G': {a: [] for a in TIMING_ARMS}}
            wall_lists: dict[str, list[float]] = {a: [] for a in TIMING_ARMS}
            trig_f0_cpu_by_s: dict[str, list[float]] = {'U': [], 'G': []}

            for idx, (s, f, obs_only, arrays, f0_cpu) in enumerate(interleaved):
                trig_f0_cpu_by_s[s].append(f0_cpu)
                rot = idx % len(TIMING_ARMS)
                order = TIMING_ARMS[rot:] + TIMING_ARMS[:rot]
                for arm in order:
                    if arm == 'CD':
                        o = _run_cd2_continuation_notruth(ctx, helpers, obs_only, arrays, max_passes=1, tag='CD')
                    elif arm == 'CD2':
                        o = _run_cd2_continuation_notruth(ctx, helpers, obs_only, arrays, max_passes=2, tag='CD2')
                    elif arm == 'HG':
                        o = _run_hg_continuation_notruth(
                            ctx, helpers, obs_only, arrays,
                            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), max_passes=2,
                        )
                    elif arm == 'Ctrl':
                        o = run_ctrl_triggered_branch(ctx, helpers, tabs, obs_only, arrays['r0_delays'])
                    elif arm in SBJ_CONFIGS:
                        o = run_sbj_triggered_branch(ctx, helpers, tabs, obs_only, preset=arm)
                    else:
                        raise ValueError(arm)
                    cpu_lists[arm].append(o['cpu_seconds'])
                    cpu_by_s[s][arm].append(o['cpu_seconds'])
                    wall_lists[arm].append(o['seconds'])
                    if sf._used_cpu_seconds() >= rem_sec:
                        timing_status = 'STOPPED_BUDGET'
                        sys.exit(BUDGET_EXIT_CODE)

            branches_summary = {}
            for a in TIMING_ARMS:
                st_cpu = _lat_stats_ms(cpu_lists[a])
                st_wall = _lat_stats_ms(wall_lists[a])
                st_cpu['wall_mean_ms'] = st_wall['mean_ms']
                st_cpu['wall_p95_ms'] = st_wall['p95_ms']
                branches_summary[a] = st_cpu

            cd2_mean = branches_summary['CD2']['mean_ms']
            hg_mean = branches_summary['HG']['mean_ms']
            cd2_p95 = branches_summary['CD2']['p95_ms']
            hg_p95 = branches_summary['HG']['p95_ms']
            for a, bstat in branches_summary.items():
                bstat['ratio_vs_CD2'] = round(bstat['mean_ms'] / max(cd2_mean, 1e-6), 4)
                bstat['ratio_vs_HG'] = round(bstat['mean_ms'] / max(hg_mean, 1e-6), 4)
                bstat['p95_ratio_vs_CD2'] = round(bstat['p95_ms'] / max(cd2_p95, 1e-6), 4)
                bstat['p95_ratio_vs_HG'] = round(bstat['p95_ms'] / max(hg_p95, 1e-6), 4)
                bstat['meets_hg_panel_mean'] = bool(bstat['mean_ms'] <= hg_mean)
                bstat['meets_hg_panel_p95'] = bool(bstat['p95_ms'] <= hg_p95)
                bstat['meets_640ms_ref'] = bool(bstat['mean_ms'] <= HG_TARGET_MS)

            # Scenario-weighted full-frame amortized CPU (ms)
            f0_t_u = float(np.mean(trig_f0_cpu_by_s['U'])) * 1000.0
            f0_t_g = float(np.mean(trig_f0_cpu_by_s['G'])) * 1000.0
            f0_u_u = float(np.mean(untrig_f0_cpu_by_s['U'])) * 1000.0 if untrig_f0_cpu_by_s['U'] else f0_t_u
            f0_u_g = float(np.mean(untrig_f0_cpu_by_s['G'])) * 1000.0 if untrig_f0_cpu_by_s['G'] else f0_t_g
            base_u = u_trig_rate * f0_t_u + (1.0 - u_trig_rate) * f0_u_u
            base_g = g_trig_rate * f0_t_g + (1.0 - g_trig_rate) * f0_u_g

            amort_u, amort_g, amort_mean = {}, {}, {}
            for a in TIMING_ARMS:
                br_u = float(np.mean(cpu_by_s['U'][a])) * 1000.0
                br_g = float(np.mean(cpu_by_s['G'][a])) * 1000.0
                au = base_u + u_trig_rate * br_u
                ag = base_g + g_trig_rate * br_g
                amort_u[a] = round(au, 2)
                amort_g[a] = round(ag, 2)
                amort_mean[a] = round(0.5 * (au + ag), 2)

            panels_out[panel_name] = dict(
                rho=rho, snr=snr, n_triggers=len(interleaved),
                U_trigger_rate_conf=u_trig_rate,
                G_trigger_rate_conf=g_trig_rate,
                mean_trigger_rate_conf=0.5 * (u_trig_rate + g_trig_rate),
                f0_triggered_cpu_ms=dict(U=round(f0_t_u, 2), G=round(f0_t_g, 2)),
                f0_untriggered_cpu_ms=dict(U=round(f0_u_u, 2), G=round(f0_u_g, 2)),
                branches=branches_summary,
                amortized_full_frame_cpu_ms=dict(U=amort_u, G=amort_g, equal_weight_mean=amort_mean),
            )

        timing_cpu_h = sf._used_cpu_seconds() / 3600.0
        cum_total = spent_before + timing_cpu_h
        if timing_cpu_h > timing_cap_h or cum_total > TOTAL_TASK_CAP_HOURS:
            timing_status = 'STOPPED_BUDGET'
            print(
                f'STOPPED_BUDGET after timing: timing_cpu_h={timing_cpu_h:.4f}h (cap {timing_cap_h:.4f}h), '
                f'cum_total={cum_total:.4f}h > {TOTAL_TASK_CAP_HOURS}h',
                flush=True,
            )
            sys.exit(BUDGET_EXIT_CODE)

        # Build unified single-core CPU gain-vs-cost curve table
        gvc_curve = []
        best_c = results['analysis']['best_crossings']
        gvc_con = results['analysis']['gain_vs_cost_contrasts']
        for arm_name in ('CD2', 'SBJ_ultra', 'SBJ_lite', 'SBJ'):
            if arm_name not in best_c:
                continue
            p100 = panels_out['rho100_snr400']['branches'][arm_name]
            p200 = panels_out['rho200_snr450']['branches'][arm_name]
            gain_info = (
                dict(point_db=0.0, ci95_db=[0.0, 0.0])
                if arm_name == 'CD2'
                else gvc_con[f'CD2_minus_{arm_name}']
            )
            gvc_curve.append(dict(
                arm=arm_name,
                best_rho=best_c[arm_name]['best_rho'],
                best_1pct_fer_db=best_c[arm_name]['best_db'],
                gain_vs_CD2_db=gain_info['point_db'],
                gain_ci95_db=gain_info['ci95_db'],
                rho100_snr400_cpu_mean_ms=round(p100['mean_ms'], 2),
                rho100_snr400_cpu_p95_ms=round(p100['p95_ms'], 2),
                rho100_vs_CD2=p100['ratio_vs_CD2'],
                rho100_vs_HG=p100['ratio_vs_HG'],
                rho100_p95_vs_CD2=p100['p95_ratio_vs_CD2'],
                rho100_p95_vs_HG=p100['p95_ratio_vs_HG'],
                rho200_snr450_cpu_mean_ms=round(p200['mean_ms'], 2),
                rho200_snr450_cpu_p95_ms=round(p200['p95_ms'], 2),
                rho200_vs_CD2=p200['ratio_vs_CD2'],
                rho200_vs_HG=p200['ratio_vs_HG'],
                rho200_p95_vs_CD2=p200['p95_ratio_vs_CD2'],
                rho200_p95_vs_HG=p200['p95_ratio_vs_HG'],
            ))

        timing_payload = dict(
            pinned_cpu=pinned_cpu,
            smt_siblings=smt_siblings,
            measured_physical_core_max_busy_pct_before_run=measured_busy_pct,
            loadavg=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [],
            timing_cpu_hours=timing_cpu_h,
            timing_wall_seconds=perf_counter() - t_wall0,
            panels=panels_out,
            gain_vs_cost_curve=gvc_curve,
        )
        ar.atomic_write_text(out_dir / 'timing_summary.json', json.dumps(timing_payload, indent=2, allow_nan=False) + '\n')

        results['timing'] = timing_payload
        results['runtime']['timing_core_hours'] = timing_cpu_h
        results['runtime']['cumulative_core_hours_so_far'] = cum_total
        ar.atomic_write_text(results_path, json.dumps(results, indent=2, allow_nan=False) + '\n')
        ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
        timing_status = 'DONE'
        print(f'STAGEA9_TIMING_DONE timing_cpu_h={timing_cpu_h:.4f} cum_total_h={cum_total:.4f}', flush=True)
    finally:
        append_ledger_entry(
            ledger_path, 'timing', timing_status, sf._used_cpu_seconds() / 3600.0,
            attempt_id=aid, reserved_hours=timing_cap_h, reaped_all_workers=True,
        )


def cmd_admit(args):
    gate_path = (HERE / 'out' / 'stageA9_gate.json').resolve()
    out_dir = (HERE / 'out' / 'stageA9').resolve()
    res_h, timeout_sec = admit_attempt(
        args.mode, args.freeze_commit, gate_path, out_dir, args.attempt_id, workers=args.workers,
    )
    print(f'{res_h:.6f} {timeout_sec}', flush=True)


def cmd_read(args):
    import stageA2

    out_dir = args.out.resolve()
    raw_dir = out_dir / 'raw'
    results_path = out_dir / 'results.json'
    prev = json.loads(results_path.read_text(encoding='utf-8'))

    gate_bytes = args.gate.resolve().read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    if gate_md5 != prev['_config']['gate_md5']:
        raise RuntimeError(f'gate_md5 mismatch vs RUN_CONFIG: {gate_md5} != {prev["_config"]["gate_md5"]}')
    gate = json.loads(gate_bytes.decode('utf-8'))

    grids = _grids_from_selected(gate['selected']['grids'])
    rows = _load_all_shards(raw_dir)
    arm_grids, diag = rows_to_arm_grids_and_diag(rows, CONF_FRAMES, grids)
    prev['analysis'] = analyze_stageA9(arm_grids, stageA2.crossing, diag)
    ar.atomic_write_text(results_path, json.dumps(prev, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(prev))
    print(json.dumps(prev['analysis']['primary'], indent=2, allow_nan=False), flush=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)

    ad = sub.add_parser('admit')
    ad.add_argument('--mode', choices=('gate', 'run', 'timing'), required=True)
    ad.add_argument('--freeze-commit', required=True)
    ad.add_argument('--attempt-id', required=True)
    ad.add_argument('--workers', type=int, default=32)

    g = sub.add_parser('gate')
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--workers', type=int, default=8)

    r = sub.add_parser('run')
    r.add_argument('--gate', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--freeze-commit', required=True)
    r.add_argument('--workers', type=int, default=32)

    t = sub.add_parser('timing')
    t.add_argument('--out', type=Path, required=True)
    t.add_argument('--freeze-commit', required=True)

    rd = sub.add_parser('read')
    rd.add_argument('--gate', type=Path, required=True)
    rd.add_argument('--out', type=Path, required=True)
    return p


def _handle_sigterm(signum, frame):
    raise SystemExit(SIGTERM_EXIT_CODE)


def main(argv: list[str] | None = None):
    signal.signal(signal.SIGTERM, _handle_sigterm)
    args = build_parser().parse_args(argv)
    if args.cmd == 'admit':
        with stage_execution_lock():
            cmd_admit(args)
        return
    if args.cmd in ('gate', 'run', 'timing'):
        # Enforce single supervised entry point on Linux so lock & process-group lifetime are unified
        if platform.system() == 'Linux' and os.environ.get('A9_SUPERVISED_BY_LAUNCH_SH', '').strip() != '1':
            canon_gate = (HERE / 'out' / 'stageA9_gate.json').resolve()
            canon_out = (HERE / 'out' / 'stageA9').resolve()
            if args.cmd == 'gate' and args.out.resolve() != canon_gate:
                raise RuntimeError(f'gate --out must be {canon_gate}')
            if args.cmd in ('run', 'timing') and args.out.resolve() != canon_out:
                raise RuntimeError(f'{args.cmd} --out must be {canon_out}')
            if args.cmd == 'run' and args.gate.resolve() != canon_gate:
                raise RuntimeError(f'run --gate must be {canon_gate}')
            if hasattr(args, 'workers'):
                os.environ['A9_WORKERS'] = str(int(args.workers))
            fc = getattr(args, 'freeze_commit', '0' * 40)
            os.execv('/usr/bin/env', ['/usr/bin/env', 'bash', str(HERE / 'stageA9_launch.sh'), args.cmd, fc])
        with stage_execution_lock(inheritable=True):
            if args.cmd == 'gate':
                cmd_gate(args)
            elif args.cmd == 'run':
                cmd_run(args)
            elif args.cmd == 'timing':
                cmd_timing(args)
    elif args.cmd == 'read':
        cmd_read(args)


if __name__ == '__main__':
    main()
