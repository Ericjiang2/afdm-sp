"""Stage A6 (STAGEA6_PROTOCOL.md): end-to-end 1% FER ceiling of semi-blind round-0 Doppler estimation (true delays).

Reuses stageA.setup(), stageA2.{f0_true, crossing, load}, stageA5.{precompute_delay_geometry, estimate_pw, estimate_sb,
doppler_metric}, sameframe.{crossing_bounds_stageA2, _rep}, and hs_analysis._nearest_rank without editing frozen files.
Arms per key (single-factor change vs stageA3.one_arm: replace injected k_real by continuous estimate nu_hat):
  SBdop = round 0 injects (true delays, stageA5.estimate_sb), pilot LS gains via stageA2.f0_true(..., 'ls'), A1 on F0 fail
  PWdop = round 0 injects (true delays, stageA5.estimate_pw), pilot LS gains via stageA2.f0_true(..., 'ls'), A1 on F0 fail
Comparators (CD2, s050, s100, ldop, full) loaded from verified frozen archives on deinlab.
"""
from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import json
import math
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import time
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
HUANG_DIR = EXP / 'huang_steelman_20261124'
SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'
SAMEFRAME_CD2_DIR = EXP / 'sameframe_cd2_20261125'

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HUANG_DIR))
sys.path.insert(0, str(SAMEFRAME_HG_DIR))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402
import sameframe as sf  # noqa: E402

FRAMES = tuple(range(41000, 41400))
SCENARIOS = ('U', 'G')
RHOS = (100, 150)
CANDIDATE_SNRS: tuple[tuple[int, ...], ...] = (
    (200, 250, 300, 400, 450, 500, 550),
    (200, 250, 300, 400, 450, 500),
    (250, 300, 400, 450, 500),
    (300, 400, 450, 500),
)
FULL_SNRS = CANDIDATE_SNRS[0]
CD2_RHOS = tuple(sf.PART1_RHOS)
CD2_SNRS = tuple(sf.PART1_SNRS)

BOOT_DRAWS = 2000
BOOT_SEED = 20261125
GO_THRESH_DB = 0.5
STOP_THRESH_DB = 0.3
OUTLIER_THRESH = 0.25

WORKERS = 32
N_SHARDS = 32
BUDGET_CAP_HOURS = 40.0
BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.15
BUDGET_EXIT_CODE = 124
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100

OWN_FILES = ('STAGEA6_PROTOCOL.md', 'stageA6.py', 'test_stageA6.py', 'stageA6_launch.sh')
PINNED_CODE_MD5 = {
    'data_pilot_fer_20261121/stageA.py': '17be1c3e75e07fb9a4dec1b3774c54aa',
    'data_pilot_fer_20261121/stageA2.py': '01a72e6942ec39de99c0e788b3b5b0a9',
    'data_pilot_fer_20261121/stageA3.py': '305645c21bf13b1bc35ec300aa1bcbb2',
    'data_pilot_fer_20261121/stageA5.py': '073b76973298fbd58ecb0ef38953c97d',
    'sameframe_hg_20261124/sameframe.py': '01197778b2ec3cf7f37719ca3b192152',
    'huang_steelman_20261124/hs_arms.py': 'a43f2934c085bde1b69f929fddf06bf6',
    'huang_steelman_20261124/hs_analysis.py': '864b8b7510872c33dc60fc725c57a45d',
}
ARCHIVE_SPECS = {
    'stageA': (
        HERE / 'out' / 'stageA' / 'REMOTE_ROWS_MD5.txt',
        HERE / 'out' / 'stageA',
        '30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68',
        'rows_shard*.jsonl.gz',
    ),
    'stageA2': (
        HERE / 'out' / 'stageA2' / 'REMOTE_ROWS_MD5.txt',
        HERE / 'out' / 'stageA2',
        '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354',
        'rows_shard*.jsonl.gz',
    ),
    'stageA3': (
        HERE / 'out' / 'stageA3' / 'REMOTE_ROWS_MD5.txt',
        HERE / 'out' / 'stageA3',
        '6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a',
        'rows_shard*.jsonl.gz',
    ),
    'stageA5': (
        HERE / 'out' / 'stageA5' / 'REMOTE_ROWS_MD5.txt',
        HERE / 'out' / 'stageA5' / 'raw',
        'bbbcb37b3fc946c2687c14b09897e10e6c69999e369689cdbf9820a7b76448e2',
        'rows_shard*.jsonl.gz',
    ),
    'sameframe_cd2': (
        SAMEFRAME_CD2_DIR / 'out' / 'REMOTE_ROWS_MD5.txt',
        SAMEFRAME_CD2_DIR / 'out' / 'raw',
        '86513c348dcef47a18cdaebb2bc6ade15e7b9f81b95c66ae832653309dae5a85',
        'partA_shard*.jsonl.gz',
    ),
}


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


def verify_archive(name: str) -> dict[str, str]:
    manifest_path, shard_dir, exp_sha, glob_pat = ARCHIVE_SPECS[name]
    got_sha = ar.sha256_file(manifest_path)
    if got_sha != exp_sha:
        raise RuntimeError(f'{name} manifest SHA-256 mismatch: {got_sha} != {exp_sha}')
    expected: dict[str, str] = {}
    for line in manifest_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, fname = line.split()
        p = shard_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f'Missing {name} shard {p}')
        actual = ar.md5_file(p)
        if actual != digest:
            raise RuntimeError(f'{name} shard MD5 mismatch {p}: {actual} != {digest}')
        expected[fname] = actual
    disk = {p.name for p in shard_dir.glob(glob_pat)}
    expected_matched = {f for f in expected if fnmatch.fnmatch(f, glob_pat)}
    if disk != expected_matched:
        raise RuntimeError(f'{name} shard set mismatch on disk: {sorted(disk ^ expected_matched)}')
    return expected


def verify_all_archives(names: tuple[str, ...]) -> dict[str, dict[str, str]]:
    return {name: verify_archive(name) for name in names}


def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
    repo_root = EXP.parent
    probe = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != 'true':
        return False
    chk = subprocess.run(
        ['git', '-C', str(repo_root), 'cat-file', '-e', f'{freeze_commit}^{{commit}}'],
        capture_output=True, text=True, check=False,
    )
    if chk.returncode != 0:
        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo: {chk.stderr.strip()}')
    top = Path(subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, check=True,
    ).stdout.strip())
    rel_dir = HERE.relative_to(top)
    for name, exp_md5 in live_own.items():
        blob = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
            capture_output=True, check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f'{name} missing from freeze_commit {freeze_commit}')
        if hashlib.md5(blob.stdout).hexdigest() != exp_md5:
            raise RuntimeError(f'Live {name} differs from freeze_commit {freeze_commit}')
    return True


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


# --------------------------------------------------------------------------- Runtime & arm execution
def _load_runtime():
    import stageA  # noqa: E402
    import stageA2  # noqa: E402
    import stageA5  # noqa: E402

    C = stageA.setup()
    from physical import daft  # noqa: E402

    return C, stageA, stageA2, stageA5, daft


def one_arm_nu(
    C,
    stageA,
    stageA2,
    obs,
    truth,
    nu_hat: np.ndarray,
    g_order: np.ndarray | None = None,
) -> dict[str, Any]:
    """Exact copy of stageA3.one_arm with injected k_real replaced by nu_hat (gains stay pilot LS).

    Passes estimated g_order into pert['g_i'] for SBdop/PWdop so truth['g_i'] is never used even for
    round-0 delay ordering inside twofft.time_refine(..., rounds=0); gains are still solved by pilot LS.
    Passing g_order=None (used only in G1 ldop replay) preserves exact stageA2.one_arm(..., 'ls') ordering.
    """
    ctx, stage3 = C['ctx'], C['stage3']
    pert = dict(truth, k_real=np.asarray(nu_hat, dtype=np.float64).tolist())
    if g_order is not None:
        pert['g_i'] = np.asarray(g_order, dtype=np.complex128).tolist()
    dec, arrays, syndrome, _ = stageA2.f0_true(C, obs, pert, 'ls')
    s2 = float(obs['sigma2'])
    rec = dict(
        syndrome=int(syndrome),
        r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
        f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
        r0=stageA.support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
        r1=stageA.support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2),
    )
    if syndrome:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
        rec['final'] = stageA.support_stats(
            [p.delay for p in br['result'].paths],
            [p.doppler for p in br['result'].paths],
            truth,
            s2,
        )
    else:
        rec['errors'] = rec['f0_errors']
        rec['final'] = rec['r1']
    return rec


def eval_key(C, stageA, stageA2, stageA5, daft, base, s: str, rho: int, snr: int, frame: int) -> dict[str, Any]:
    """Evaluate SBdop and PWdop on one observation key (true delays only; no truth peeking in estimators)."""
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

    t0 = time.process_time()
    nu_pw, g_pw = stageA5.estimate_pw(geom, p_t, r)
    pw_cpu = time.process_time() - t0

    t1 = time.process_time()
    nu_sb, g_sb = stageA5.estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
    sb_cpu = time.process_time() - t1

    m_pw, o_pw, e_pw = stageA5.doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
    m_sb, o_sb, e_sb = stageA5.doppler_metric(nu_sb, truth['k_real'], truth['g_i'])

    rec_sb = one_arm_nu(C, stageA, stageA2, obs, truth, nu_sb, g_order=g_sb)
    rec_pw = one_arm_nu(C, stageA, stageA2, obs, truth, nu_pw, g_order=g_pw)

    return dict(
        frame=frame,
        scenario=s,
        rho=rho,
        snr=snr,
        sigma2=float(obs['sigma2']),
        pw_cpu=float(pw_cpu),
        sb_cpu=float(sb_cpu),
        sb_metric=float(m_sb),
        sb_outlier_frac=float(o_sb),
        sb_abs_err=e_sb,
        pw_metric=float(m_pw),
        pw_outlier_frac=float(o_pw),
        pw_abs_err=e_pw,
        truth_power=(np.abs(np.asarray(truth['g_i'], dtype=np.complex128)) ** 2).tolist(),
        arms=dict(SBdop=rec_sb, PWdop=rec_pw),
    )


# --------------------------------------------------------------------------- File-IPC helper
def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
    n_workers = min(max_workers, max(1, len(items)))
    buckets = [items[i::n_workers] for i in range(n_workers)]
    mp_ctx = multiprocessing.get_context('spawn')
    out_files = []
    procs = []
    for wi, bucket in enumerate(buckets):
        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
        in_f.write_text(json.dumps(bucket), encoding='utf-8')
        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
        p.start()
        procs.append((wi, p))
        out_files.append(out_f)
    for wi, p in procs:
        p.join()
        code = p.exitcode
        p.close()
        if code != 0:
            raise RuntimeError(f'{tag} worker {wi} exited with code {code}')
    rows: list[Any] = []
    for out_f in out_files:
        rows.extend(json.loads(out_f.read_text(encoding='utf-8')))
    return rows


# --------------------------------------------------------------------------- Gates G1-G3
def _g3_cost_worker(in_path: str, out_path: str):
    C, stageA, stageA2, stageA5, daft = _load_runtime()
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
            pw_cpu=row['pw_cpu'],
            sb_cpu=row['sb_cpu'],
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(out))


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
    manifests = verify_all_archives(('stageA', 'stageA2', 'stageA3', 'stageA5', 'sameframe_cd2'))
    C, stageA, stageA2, stageA5, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2

    # G1: nu_hat = truth['k_real'] reproduces archived stageA2 'ldop' exactly on 4 keys
    a2_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    with gzip.open(HERE / 'out' / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt', encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            a2_rows[(r['scenario'], int(r['rho']), int(r['snr']), int(r['frame']))] = r
    g1_keys = (('U', 100, 300, 41000), ('G', 150, 400, 41001), ('U', 150, 450, 41002), ('G', 100, 500, 41003))
    g1_rows = []
    for s, rho, snr, frame in g1_keys:
        base = st.inputs(ctx, frame, s, rho)
        _, obs, truth = st.observed(ctx, base, rho, snr)
        rec = one_arm_nu(C, stageA, stageA2, obs, truth, np.asarray(truth['k_real'], dtype=np.float64))
        ref = a2_rows[(s, rho, snr, frame)]['arms']['ldop']
        ok = all(int(rec[k]) == int(ref[k]) for k in ('syndrome', 'f0_errors', 'errors'))
        g1_rows.append(dict(
            key=[s, rho, snr, frame],
            passed=bool(ok),
            got={k: int(rec[k]) for k in ('syndrome', 'f0_errors', 'errors')},
            ref={k: int(ref[k]) for k in ('syndrome', 'f0_errors', 'errors')},
        ))
    g1_pass = bool(len(g1_rows) == 4 and all(x['passed'] for x in g1_rows))
    print(f'G1 {"PASS" if g1_pass else "FAIL"} ({sum(x["passed"] for x in g1_rows)}/4 exact ldop replay)', flush=True)

    # G2: 4 keys from A5 (frames 41000-41099, 4 dB, rho .10/.15) via main eval_key reproduce A5 abs_err['SB'] & metric['SB'] within 1e-6
    g2_targets = {(41000, 'U', 100, 400), (41001, 'G', 150, 400), (41002, 'U', 150, 400), (41003, 'G', 100, 400)}
    a5_ref: dict[tuple[int, str, int, int], dict[str, Any]] = {}
    for sp in sorted((HERE / 'out' / 'stageA5' / 'raw').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                k = (int(r['frame']), r['scenario'], int(r['rho']), int(r['snr']))
                if k in g2_targets:
                    a5_ref[k] = r
        if len(a5_ref) == len(g2_targets):
            break
    if len(a5_ref) != len(g2_targets):
        raise RuntimeError(f'Missing G2 keys in stageA5 archive: found {sorted(a5_ref)}')

    g2_rows = []
    for frame, s, rho, snr in sorted(g2_targets):
        base = st.inputs(ctx, frame, s, rho)
        row = eval_key(C, stageA, stageA2, stageA5, daft, base, s, rho, snr, frame)
        ref = a5_ref[(frame, s, rho, snr)]
        max_abs_diff = float(np.max(np.abs(np.asarray(row['sb_abs_err']) - np.asarray(ref['abs_err']['SB']))))
        metric_diff = float(abs(float(row['sb_metric']) - float(ref['metric']['SB'])))
        ok = bool(max_abs_diff < 1e-6 and metric_diff < 1e-6)
        g2_rows.append(dict(
            key=[frame, s, rho, snr],
            passed=ok,
            max_abs_err_diff=max_abs_diff,
            metric_diff=metric_diff,
        ))
    g2_pass = bool(len(g2_rows) == 4 and all(x['passed'] for x in g2_rows))
    print(f'G2 {"PASS" if g2_pass else "FAIL"} max_diff={max(x["max_abs_err_diff"] for x in g2_rows):.2e}', flush=True)

    # Also verify frozen comparator archives load completely before main run (fail fast on grid/schema mismatch)
    _load_frozen_comparators()
    print('Frozen comparator archives (CD2, stageA2, stageA3) pre-load check: PASS', flush=True)

    # G3: stratified cost projection across all 7 SNRs on isolated frames 41400-41403 (28 keys)
    g3_jobs = []
    for snr in FULL_SNRS:
        g3_jobs.extend([
            [41400, 'U', 100, snr],
            [41401, 'G', 100, snr],
            [41402, 'U', 150, snr],
            [41403, 'G', 150, snr],
        ])
    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'stageA6_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        print(f'Running G3 stratified cost benchmark ({len(g3_jobs)} keys across {len(FULL_SNRS)} SNRs)...', flush=True)
        g3_samples = _spawn_map(_g3_cost_worker, g3_jobs, min(args.workers, len(g3_jobs)), ipc_dir, 'g3')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    mean_cpu_by_snr = {
        snr: float(np.mean([x['total_cpu'] for x in g3_samples if int(x['snr']) == snr]))
        for snr in FULL_SNRS
    }
    mean_sb_by_snr = {
        snr: float(np.mean([x['sb_cpu'] for x in g3_samples if int(x['snr']) == snr]))
        for snr in FULL_SNRS
    }
    keys_per_snr = len(FRAMES) * len(SCENARIOS) * len(RHOS)  # 400 * 2 * 2 = 1600
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
            mean_sb_cpu_sec_by_snr={str(k): v for k, v in mean_sb_by_snr.items()},
            candidates=candidates,
            samples=g3_samples,
        ),
        gate_cpu_hours=gate_cpu_h,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
    sys.exit(0 if all_passed else 1)


# --------------------------------------------------------------------------- Main worker & readout
def _run_shard_worker(shard_idx: int, frames: tuple[int, ...], snrs: tuple[int, ...], raw_dir: Path):
    C, stageA, stageA2, stageA5, daft = _load_runtime()
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


def verdict_a6(ci_lo: float, ci_hi: float) -> str:
    if ci_lo >= GO_THRESH_DB:
        return 'GO'
    if ci_hi < STOP_THRESH_DB:
        return 'STOP'
    return 'ERIC'


def _to_float_bound(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if val == '-inf':
        return -math.inf
    if val in ('inf', '+inf'):
        return math.inf
    raise ValueError(f'Unexpected bound representation: {val!r}')


def analyze_stageA6(
    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
    crossing_fn,
    diagnostics: dict[str, Any],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Frozen Stage A6 readout with exact sameframe_cd2 joint paired physical-frame bootstrap."""
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
        if arm in ('full', 'ldop'):
            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
        else:
            sub_idx = list(range(n_r))
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

    primary = contrast('CD2', 'SBdop')
    lo_val = _to_float_bound(primary['ci95_db'][0])
    hi_val = _to_float_bound(primary['ci95_db'][1])
    primary['verdict'] = verdict_a6(lo_val, hi_val)
    primary['go_threshold_db'] = GO_THRESH_DB
    primary['stop_threshold_db'] = STOP_THRESH_DB

    # Best crossing CIs for SBdop & PWdop
    best_ci = {}
    for arm in ('SBdop', 'PWdop', 'CD2', 's050', 's100', 'ldop'):
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

    secondary = {
        'SBdop_minus_s050': contrast('SBdop', 's050'),
        'SBdop_minus_ldop': contrast('SBdop', 'ldop'),
        'CD2_minus_PWdop': contrast('CD2', 'PWdop'),
        'PWdop_minus_SBdop': contrast('PWdop', 'SBdop'),
        'SBdop_minus_s100': contrast('SBdop', 's100'),
        'CD2_minus_s050': contrast('CD2', 's050'),
        'CD2_minus_ldop': contrast('CD2', 'ldop'),
    }

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
    a5_ref_means: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Compute per-SNR Doppler error, A5 subset check, F0-failure outlier breakdown, and SB/PW timing."""
    by_rho_snr: dict[str, dict[str, Any]] = {}
    for rho in RHOS:
        for snr in snrs:
            sub = [r for r in rows if int(r['rho']) == rho and int(r['snr']) == snr]
            sb_m = np.array([r['sb_metric'] for r in sub], dtype=np.float64)
            pw_m = np.array([r['pw_metric'] for r in sub], dtype=np.float64)
            sb_o = np.array([r['sb_outlier_frac'] for r in sub], dtype=np.float64)
            sb_fer_f0 = float(np.mean([r['arms']['SBdop']['f0_errors'] > 0 for r in sub]))
            sb_fer_fin = float(np.mean([r['arms']['SBdop']['errors'] > 0 for r in sub]))
            pw_fer_fin = float(np.mean([r['arms']['PWdop']['errors'] > 0 for r in sub]))
            by_rho_snr[f'{rho}_{snr}'] = dict(
                n=len(sub),
                sb_doppler_mean=float(sb_m.mean()),
                sb_doppler_median=float(np.median(sb_m)),
                sb_outlier_gt_0p25_frac=float(sb_o.mean()),
                pw_doppler_mean=float(pw_m.mean()),
                pw_doppler_median=float(np.median(pw_m)),
                sb_f0_fer=sb_fer_f0,
                sb_final_fer=sb_fer_fin,
                pw_final_fer=pw_fer_fin,
            )

    # Check A5 subset (frames 41000-41099, 4 dB) directly against archived stageA5 means
    a5_subset = {}
    if 400 in snrs:
        for rho in RHOS:
            sub = [r for r in rows if 41000 <= int(r['frame']) <= 41099 and int(r['rho']) == rho and int(r['snr']) == 400]
            sb_m = float(np.mean([r['sb_metric'] for r in sub]))
            pw_m = float(np.mean([r['pw_metric'] for r in sub]))
            entry: dict[str, Any] = dict(n=len(sub), a6_sb_mean=sb_m, a6_pw_mean=pw_m)
            if a5_ref_means and str(rho) in a5_ref_means:
                ref_sb = float(a5_ref_means[str(rho)]['sb_mean'])
                ref_pw = float(a5_ref_means[str(rho)]['pw_mean'])
                entry['a5_sb_mean'] = ref_sb
                entry['a5_pw_mean'] = ref_pw
                entry['sb_abs_diff'] = float(abs(sb_m - ref_sb))
                entry['pw_abs_diff'] = float(abs(pw_m - ref_pw))
            a5_subset[str(rho)] = entry

    # Weak-path & any-path outlier (> 0.25 bin) shares among SBdop F0 failures vs F0 successes
    def classify_outliers(sub_rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(sub_rows)
        if n == 0:
            return dict(n=0, any_outlier=None, weak_outlier=None, weak_only_outlier=None, strong_outlier=None)
        any_c = weak_c = weak_only_c = strong_c = 0
        for r in sub_rows:
            errs = np.asarray(r['sb_abs_err'], dtype=np.float64)
            pw = np.asarray(r['truth_power'], dtype=np.float64)
            med_pw = float(np.median(pw))
            is_weak = pw < med_pw
            is_strong = ~is_weak
            has_any = bool(np.any(errs > OUTLIER_THRESH))
            has_weak = bool(np.any(errs[is_weak] > OUTLIER_THRESH))
            has_strong = bool(np.any(errs[is_strong] > OUTLIER_THRESH))
            any_c += int(has_any)
            weak_c += int(has_weak)
            weak_only_c += int(has_weak and not has_strong)
            strong_c += int(has_strong)
        return dict(
            n=n,
            any_outlier=float(any_c / n),
            weak_outlier=float(weak_c / n),
            weak_only_outlier=float(weak_only_c / n),
            strong_outlier=float(strong_c / n),
        )

    f0_fail_rows = [r for r in rows if int(r['arms']['SBdop']['f0_errors']) > 0]
    f0_ok_rows = [r for r in rows if int(r['arms']['SBdop']['f0_errors']) == 0]
    syn_fail_rows = [r for r in rows if int(r['arms']['SBdop']['syndrome']) != 0]
    final_fail_rows = [r for r in rows if int(r['arms']['SBdop']['errors']) > 0]
    # Also breakdown at operating band SNR in {300, 400, 450}
    op_f0_fail = [r for r in f0_fail_rows if int(r['snr']) in (300, 400, 450)]
    op_f0_ok = [r for r in f0_ok_rows if int(r['snr']) in (300, 400, 450)]

    sb_t = np.array([r['sb_cpu'] for r in rows], dtype=np.float64)
    pw_t = np.array([r['pw_cpu'] for r in rows], dtype=np.float64)

    return dict(
        by_rho_snr=by_rho_snr,
        a5_4db_subset_check=a5_subset,
        sb_outlier_breakdown=dict(
            f0_errors_gt0_all_snrs=classify_outliers(f0_fail_rows),
            f0_errors_eq0_all_snrs=classify_outliers(f0_ok_rows),
            f0_syndrome_nz_all_snrs=classify_outliers(syn_fail_rows),
            final_errors_gt0_all_snrs=classify_outliers(final_fail_rows),
            f0_errors_gt0_snr300_450=classify_outliers(op_f0_fail),
            f0_errors_eq0_snr300_450=classify_outliers(op_f0_ok),
        ),
        timing_cpu_sec=dict(
            sb_mean=float(sb_t.mean()),
            sb_median=float(np.median(sb_t)),
            sb_p95=float(np.percentile(sb_t, 95)),
            pw_mean=float(pw_t.mean()),
            pw_median=float(np.median(pw_t)),
            pw_p95=float(np.percentile(pw_t, 95)),
            sb_by_snr={
                str(snr): float(np.mean([r['sb_cpu'] for r in rows if int(r['snr']) == snr]))
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
        '# Stage A6 Results: End-to-End 1% FER Ceiling of Semi-Blind Round-0 Doppler (`SBdop`)',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- Grid: frames `41000–41399` × U/G (`800` draws/cell), ρ ∈ `{res["_config"]["rhos"]}`, SNRs = `{res["_config"]["snrs"]}`',
        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap {res["runtime"]["cpu_cap_core_hours"]:.1f} h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
        '',
        '## Primary Verdict (Pre-Registered, 1% info-FER U/G Mean)',
        '',
        '| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |',
        '|---|---:|---|---|',
        f'| `min CD2 (100..250) − min SBdop (100..150)` | **{fval(p["point_db"])}** | **[{fval(p["ci95_db"][0])}, {fval(p["ci95_db"][1])}]** | **{p["verdict"]}** |',
        '',
        '## 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
        '',
        '| Arm | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | Best (dB) [95% CI] | Best ρ |',
        '|---|---:|---:|---:|---:|---|---:|',
    ]
    for arm in ('CD2', 'PWdop', 'SBdop', 's100', 's050', 'ldop'):
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

    lines += ['', '## Round-0 Doppler Metric & FER by (ρ, SNR) (800 Draws/Cell)', '', '| ρ | SNR (dB) | SB MAE [med] | PW MAE [med] | SB Outlier >0.25 | SB F0 FER | SB Final FER | PW Final FER |', '|---:|---:|---|---|---:|---:|---:|---:|']
    for rho in RHOS:
        for snr in res['_config']['snrs']:
            c = d['by_rho_snr'][f'{rho}_{snr}']
            lines.append(
                f'| {rho/1000:.2f} | {snr/100:.1f} | {c["sb_doppler_mean"]:.4f} [{c["sb_doppler_median"]:.4f}] | '
                f'{c["pw_doppler_mean"]:.4f} [{c["pw_doppler_median"]:.4f}] | '
                f'{100*c["sb_outlier_gt_0p25_frac"]:.2f}% | {100*c["sb_f0_fer"]:.2f}% | {100*c["sb_final_fer"]:.2f}% | {100*c["pw_final_fer"]:.2f}% |'
            )

    def fpct(x):
        return 'N/A' if x is None else f'{100*x:.2f}%'

    ob = d['sb_outlier_breakdown']
    tm = d['timing_cpu_sec']
    lines += [
        '',
        '## SB Outlier & Timing Diagnostics',
        '',
        f'- F0 failures (all SNRs, n={ob["f0_errors_gt0_all_snrs"]["n"]}): any >0.25 = `{fpct(ob["f0_errors_gt0_all_snrs"]["any_outlier"])}`, '
        f'weak-path >0.25 = `{fpct(ob["f0_errors_gt0_all_snrs"]["weak_outlier"])}`, '
        f'weak-only >0.25 = `{fpct(ob["f0_errors_gt0_all_snrs"]["weak_only_outlier"])}`, '
        f'strong-path >0.25 = `{fpct(ob["f0_errors_gt0_all_snrs"]["strong_outlier"])}` '
        f'(vs F0 successes n={ob["f0_errors_eq0_all_snrs"]["n"]}: any `{fpct(ob["f0_errors_eq0_all_snrs"]["any_outlier"])}`, '
        f'weak `{fpct(ob["f0_errors_eq0_all_snrs"]["weak_outlier"])}`, strong `{fpct(ob["f0_errors_eq0_all_snrs"]["strong_outlier"])}`).',
        f'- F0 failures (operating band 3.0–4.5 dB, n={ob["f0_errors_gt0_snr300_450"]["n"]}): '
        f'any `{fpct(ob["f0_errors_gt0_snr300_450"]["any_outlier"])}`, '
        f'weak `{fpct(ob["f0_errors_gt0_snr300_450"]["weak_outlier"])}`, '
        f'strong `{fpct(ob["f0_errors_gt0_snr300_450"]["strong_outlier"])}`.',
        f'- Per-key `SB` CPU time: mean **`{tm["sb_mean"]:.3f} s`**, median `{tm["sb_median"]:.3f} s`, p95 `{tm["sb_p95"]:.3f} s` '
        f'(`PW` mean `{tm["pw_mean"]:.4f} s`).',
    ]
    return '\n'.join(lines) + '\n'


def _load_cd2_fail_grid() -> np.ndarray:
    """Load verified CD2 failure grid (400 frames x 2 scen x 4 rhos x 13 SNRs) from stageA + sameframe_cd2."""
    stageA_base = sf.load_stageA_base(CD2_RHOS)
    fi = {f: i for i, f in enumerate(FRAMES)}
    fail = np.zeros((len(FRAMES), 2, len(CD2_RHOS), len(CD2_SNRS)), dtype=bool)
    seen = np.zeros_like(fail)
    for (s, rho, snr, f), b in stageA_base.items():
        if b['syndrome'] == 0:
            ix = (fi[f], SCENARIOS.index(s), CD2_RHOS.index(rho), CD2_SNRS.index(snr))
            fail[ix] = b['f0_errors'] > 0
            seen[ix] = True
    cd2_raw = SAMEFRAME_CD2_DIR / 'out' / 'raw'
    for sp in sorted(cd2_raw.glob('partA_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), CD2_RHOS.index(int(r['rho'])), CD2_SNRS.index(int(r['snr'])))
                if seen[ix]:
                    raise RuntimeError(f'Duplicate CD2 key {r}')
                fail[ix] = int(r['arms']['CD2']['errors']) > 0
                seen[ix] = True
    if not seen.all():
        raise RuntimeError('Incomplete archived CD2 grid')
    return fail


def _load_a5_4db_ref_means() -> dict[str, dict[str, float]]:
    """Compute exact archived Stage A5 4 dB means over frames 41000-41099 from verified raw shards."""
    acc: dict[int, tuple[list[float], list[float]]] = {rho: ([], []) for rho in RHOS}
    for sp in sorted((HERE / 'out' / 'stageA5' / 'raw').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                rho = int(r['rho'])
                if int(r['snr']) == 400 and rho in acc and 41000 <= int(r['frame']) <= 41099:
                    acc[rho][0].append(float(r['metric']['SB']))
                    acc[rho][1].append(float(r['metric']['PW']))
    out: dict[str, dict[str, float]] = {}
    for rho, (sbs, pws) in acc.items():
        if len(sbs) != 200:
            raise RuntimeError(f'Incomplete stageA5 4 dB reference at rho={rho}: {len(sbs)} != 200')
        out[str(rho)] = dict(sb_mean=float(np.mean(sbs)), pw_mean=float(np.mean(pws)))
    return out


def _load_frozen_comparators() -> tuple[dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]], Any]:
    """Load and validate frozen CD2, stageA2 (full/ldop), and stageA3 (s050/s100) failure grids."""
    import stageA2  # noqa: E402
    import stageA3  # noqa: E402

    cd2_fail = _load_cd2_fail_grid()
    fa2, _ = stageA2.load(HERE / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
    fa3, _ = stageA2.load(HERE / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)
    comps = {
        'CD2': (CD2_RHOS, CD2_SNRS, cd2_fail),
        'full': (tuple(stageA2.RHOS), tuple(stageA2.SNRS), fa2[:, 0]),
        'ldop': (tuple(stageA2.RHOS), tuple(stageA2.SNRS), fa2[:, 1]),
        's050': (tuple(stageA3.RHOS), tuple(stageA3.SNRS), fa3[:, stageA3.ARMS.index('s050')]),
        's100': (tuple(stageA3.RHOS), tuple(stageA3.SNRS), fa3[:, stageA3.ARMS.index('s100')]),
    }
    return comps, stageA2.crossing


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
    freeze_git_ok = verify_freeze_commit_if_git(args.freeze_commit, live_own)
    manifests = verify_all_archives(('stageA', 'stageA2', 'stageA3', 'stageA5', 'sameframe_cd2'))
    frozen_comps, crossing_fn = _load_frozen_comparators()
    a5_ref_means = _load_a5_4db_ref_means()

    gate_path = args.gate.resolve()
    gate_bytes = gate_path.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to run without passing stageA6_gate.json')
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('stageA6_gate.json own_md5 mismatch; re-run gates')
    if gate['_config']['pinned_code_md5'] != pinned_md5:
        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA6_gate.json')

    snrs = tuple(int(s) for s in gate['selected']['snrs'])
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
        f'Launching Stage A6: {len(FRAMES)} frames x 2 scen x {len(RHOS)} rhos x {len(snrs)} SNRs '
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
            for r in ready:
                idx, p = running.pop(r)
                p.join()
                code = p.exitcode
                p.close()
                if code != 0:
                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= BUDGET_CAP_SEC - 480.0:
                budget_hit = True
                break
    finally:
        for _, p in running.values():
            p.terminate()
        for _, p in running.values():
            p.join()
            p.close()
    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    # Record shard MD5s and load new rows
    raw_md5: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    fi = {f: i for i, f in enumerate(FRAMES)}
    sb_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
    pw_fail = np.zeros((len(FRAMES), 2, len(RHOS), len(snrs)), dtype=bool)
    seen = np.zeros_like(sb_fail)
    for idx in range(n_shards):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
        raw_md5[sp.name] = ar.md5_file(sp)
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                rows.append(r)
                ix = (fi[int(r['frame'])], SCENARIOS.index(r['scenario']), RHOS.index(int(r['rho'])), snrs.index(int(r['snr'])))
                if seen[ix]:
                    raise RuntimeError(f'Duplicate Stage A6 key {r["frame"]} {r["scenario"]} {r["rho"]} {r["snr"]}')
                sb_fail[ix] = int(r['arms']['SBdop']['errors']) > 0
                pw_fail[ix] = int(r['arms']['PWdop']['errors']) > 0
                seen[ix] = True
    if not seen.all():
        raise RuntimeError('Incomplete Stage A6 failure grid')
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
    )

    fail_by_arm = dict(frozen_comps)
    fail_by_arm['SBdop'] = (RHOS, snrs, sb_fail)
    fail_by_arm['PWdop'] = (RHOS, snrs, pw_fail)
    diagnostics = summarize_diagnostics(rows, snrs, a5_ref_means=a5_ref_means)
    analysis = analyze_stageA6(fail_by_arm, crossing_fn, diagnostics)

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
        f'STAGEA6_DONE verdict={p["verdict"]} D={p["point_db"]} '
        f'ci={p["ci95_db"]} SBdop_best={p["arm_b_best_db"]}@rho{p["arm_b_best_rho"]} '
        f'cpu_hours={total_cpu_h:.4f}',
        flush=True,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    g = sub.add_parser('gate')
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--workers', type=int, default=28)

    r = sub.add_parser('run')
    r.add_argument('--gate', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--freeze-commit', required=True)
    r.add_argument('--workers', type=int, default=WORKERS)

    args = ap.parse_args()
    dict(gate=cmd_gate, run=cmd_run)[args.mode](args)


if __name__ == '__main__':
    main()
