"""Part A (CD2/CD2e8 on low-pilot frames 41000-41399) + Part B (quiet single-core dual-panel timing)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time
from time import perf_counter
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'
DATA_PILOT_DIR = EXP / 'data_pilot_fer_20261121'
HUANG_DIR = EXP / 'huang_steelman_20261124'

sys.path.insert(0, str(SAMEFRAME_HG_DIR))
sys.path.insert(0, str(DATA_PILOT_DIR))
sys.path.insert(0, str(HUANG_DIR))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402
import sameframe as sf  # noqa: E402

PARTA_RHOS = sf.PART1_RHOS
PARTA_SNRS = sf.PART1_SNRS
PARTA_FRAMES = sf.PART1_FRAMES
BOOT_DRAWS = 2000
BOOT_SEED = 20261125
P1P_THRESHOLD_DB = 0.5
WORKERS = 24
N_SHARDS = 24
BUDGET_CAP_HOURS = 6.0
BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
COST_MARGIN = 1.3
TIMING_ALLOWANCE_HOURS = 0.18
IO_ALLOWANCE_HOURS = 0.12
BUDGET_EXIT_CODE = 124
TIMING_BUDGET_SEC = 1740.0

SAMEFRAME_HG_MANIFEST_SHA256 = '7cac38cd7cc8fa610ddf8c0b5908b62c668901cf5b72756889c1fd6a0f6b435f'
REUSED_UPSTREAM_MD5 = {
    'sameframe_hg_20261124/sameframe.py': '01197778b2ec3cf7f37719ca3b192152',
    'huang_steelman_20261124/hs_arms.py': 'a43f2934c085bde1b69f929fddf06bf6',
    'huang_steelman_20261124/hs_analysis.py': '864b8b7510872c33dc60fc725c57a45d',
    'data_pilot_fer_20261121/stageA.py': '17be1c3e75e07fb9a4dec1b3774c54aa',
    'data_pilot_fer_20261121/stageA2.py': '01a72e6942ec39de99c0e788b3b5b0a9',
    'data_pilot_fer_20261121/stageA3.py': '305645c21bf13b1bc35ec300aa1bcbb2',
}
OWN_FILES = ('PROTOCOL.md', 'sameframe_cd2.py', 'test_sameframe_cd2.py', 'launch.sh')
TIMING_PANELS = (
    ('rho200_snr450', 200, 450),
    ('rho300_snr500', 300, 500),
)
TIMING_BRANCHES = ('CD', 'CD2', 'CD2e8', 'HG', 'HGint')


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_reused_upstream_md5() -> dict[str, str]:
    out = {}
    for rel, expected in REUSED_UPSTREAM_MD5.items():
        actual = ar.md5_file(EXP / rel)
        if actual != expected:
            raise RuntimeError(f'Reused upstream MD5 mismatch for {rel}: {actual} != {expected}')
        out[rel] = actual
    return out


def verify_sameframe_hg_manifest() -> dict[str, str]:
    manifest = SAMEFRAME_HG_DIR / 'out' / 'REMOTE_ROWS_MD5.txt'
    got_sha = ar.sha256_file(manifest)
    if got_sha != SAMEFRAME_HG_MANIFEST_SHA256:
        raise RuntimeError(f'sameframe_hg manifest SHA-256 mismatch: {got_sha} != {SAMEFRAME_HG_MANIFEST_SHA256}')
    raw_dir = SAMEFRAME_HG_DIR / 'out' / 'raw'
    out: dict[str, str] = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, fname = line.split()
        p = raw_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f'Missing sameframe_hg shard {p}')
        actual = ar.md5_file(p)
        if actual != digest:
            raise RuntimeError(f'sameframe_hg shard MD5 mismatch {p}: {actual} != {digest}')
        out[fname] = actual
    disk_shards = {p.name for p in raw_dir.glob('part*_shard*.jsonl.gz')}
    if disk_shards != set(out):
        raise RuntimeError(f'sameframe_hg shard set mismatch on disk: {sorted(disk_shards ^ set(out))}')
    return out


def verify_all_archives() -> dict[str, dict[str, str]]:
    res = {name: sf.verify_manifest(name) for name in sf.ARCHIVE_MANIFESTS}
    res['sameframe_hg'] = verify_sameframe_hg_manifest()
    return res


def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
    import subprocess

    repo_root = EXP.parent
    probe = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != 'true':
        return False
    check = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'{freeze_commit}^{{commit}}'],
        capture_output=True, text=True, check=False,
    )
    if check.returncode != 0:
        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo')
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
            raise RuntimeError(f'freeze_commit {freeze_commit} missing {name}')
        if hashlib.md5(blob.stdout).hexdigest() != exp_md5:
            raise RuntimeError(f'Live {name} differs from freeze_commit {freeze_commit}')
    return True


def run_cd_timed(
    ctx,
    helpers: dict[str, Any],
    obs: dict[str, Any],
    arrays: dict[str, Any],
    truth: dict[str, Any],
    *,
    arm_spec: str,
    max_passes: int,
) -> dict[str, Any]:
    """Decision-ready timed 1-or-2-pass CODELAY (same timer boundary as hs_arms._run_exchange_arm)."""
    stage3 = helpers['stage3']
    cd = helpers['cd_e8'] if arm_spec == 'A1e8' else helpers['cd']

    ar._require_finite(arrays['r1_check'], f'{arm_spec}.p1.r1_check')
    ar._require_finite(arrays['r1_app'], f'{arm_spec}.p1.r1_app')
    t0 = perf_counter()
    br1 = stage3.e1.run_branch(ctx, cd, obs, arrays, arm_spec)
    dec1 = br1['decoder']
    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))
    if syn1 == 0 or max_passes == 1:
        sec = perf_counter() - t0
        res1 = br1['result']
        if bool(res1.diagnostics.get('numerical_fallback')):
            raise FloatingPointError(f'numerical_fallback in {arm_spec} p1')
        ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
        ar._require_finite(br1['detector']['extrinsic'], f'{arm_spec}.p1.extrinsic')
        d1 = stage3.decoded(ctx, dec1, truth)
        return dict(
            errors=d1['errors'], decoded_sha=d1['decoded_sha'], syndrome=syn1,
            passes_used=1, seconds=float(sec),
        )

    res1 = br1['result']
    arrays2 = dict(
        r1_delays=np.array([int(p.delay) for p in res1.paths], dtype=int),
        r1_dopplers=np.array([float(p.doppler) for p in res1.paths], dtype=float),
        r1_gains=np.asarray(res1.gains, dtype=complex),
        r1_check=dec1['raw_check_extrinsic'],
        r1_app=dec1['raw_app'],
    )
    br2 = stage3.e1.run_branch(ctx, cd, obs, arrays2, arm_spec)
    dec2 = br2['decoder']
    syn2 = int(ctx.hd.syndrome_weight(ctx, dec2['decoded']))
    sec = perf_counter() - t0

    res2 = br2['result']
    if bool(res1.diagnostics.get('numerical_fallback')) or bool(res2.diagnostics.get('numerical_fallback')):
        raise FloatingPointError(f'numerical_fallback in {arm_spec}')
    ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
    ar._require_finite(res2.gains, f'{arm_spec}.p2.gains')
    ar._require_finite(br2['detector']['extrinsic'], f'{arm_spec}.p2.extrinsic')
    ar._require_finite(dec2['raw_check_extrinsic'], f'{arm_spec}.p2.raw_check_extrinsic')
    ar._require_finite(dec2['raw_app'], f'{arm_spec}.p2.raw_app')
    d2 = stage3.decoded(ctx, dec2, truth)
    return dict(
        errors=d2['errors'], decoded_sha=d2['decoded_sha'], syndrome=syn2,
        passes_used=2, seconds=float(sec),
    )


# --------------------------------------------------------------------------- Gates G1-G3
def _g1_g2_worker(in_path: str, out_path: str):
    C, _, _, helpers = sf.load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for s, rho, snr, frame, exp_syn, exp_f0_err, exp_base_err in jobs:
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
        if int(syn) != int(exp_syn) or f0_err != int(exp_f0_err) or int(syn) == 0:
            raise AssertionError(f'G1 F0 mismatch at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})')
        cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
        if int(cd2['pass1_errors']) != int(exp_base_err):
            raise AssertionError(
                f'G2 CD2 pass-1 errors mismatch vs stageA base at {(s, rho, snr, frame)}: '
                f'{cd2["pass1_errors"]} != {exp_base_err}'
            )
        cd2e8 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
        res.append(dict(
            key=[s, rho, snr, frame],
            f0_ok=True,
            cd2_pass1_ok=True,
            cd2_passes=cd2['passes_used'],
            cd2_p1_err=cd2['pass1_errors'],
            cd2_final_err=cd2['errors'],
            cd2e8_passes=cd2e8['passes_used'],
            cd2e8_final_err=cd2e8['errors'],
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def _g3_cost_worker(in_path: str, out_path: str):
    C, _, _, helpers = sf.load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for s, rho, snr, frame, band, exp_base_err in jobs:
        t0 = time.process_time()
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        t_f0 = time.process_time() - t0
        if int(syn) == 0:
            raise AssertionError(f'G3 key untriggered: {(s, rho, snr, frame)}')
        t1 = time.process_time()
        cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
        t_cd2 = time.process_time() - t1
        if int(cd2['pass1_errors']) != int(exp_base_err):
            raise AssertionError(f'G3 CD2 pass-1 drift at {(s, rho, snr, frame)}')
        t2 = time.process_time()
        cd2e8 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
        t_cd2e8 = time.process_time() - t2
        res.append(dict(
            key=[s, rho, snr, frame], rho=rho, band=band,
            f0_cpu=t_f0, cd2_cpu=t_cd2, cd2e8_cpu=t_cd2e8,
            cd2_passes=cd2['passes_used'], cd2e8_passes=cd2e8['passes_used'],
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def cmd_gate(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    started = time.monotonic()

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stale = out_dir / 'gate.json'
    if stale.exists():
        stale.unlink()

    reused_md5 = verify_reused_upstream_md5()
    manifests = verify_all_archives()
    C, _, _, helpers = sf.load_stage_runtime()
    ctx = C['ctx']

    stageA_base = sf.load_stageA_base(PARTA_RHOS)
    pA_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
    for k, v in stageA_base.items():
        if v['syndrome'] != 0:
            band = 'low' if k[2] <= 400 else 'mid'
            pA_strata.setdefault((k[1], band), []).append(k)

    # 20 keys for G1+G2: 5 per rho in 100..250, guaranteeing U/G, low/mid, and both pass-1 pass & fail
    g12_jobs = []
    for rho in PARTA_RHOS:
        all_r = sorted(pA_strata[(rho, 'low')] + pA_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
        picks = []
        for band in ('low', 'mid'):
            for scen in ('U', 'G'):
                pool = sorted((k for k in pA_strata[(rho, band)] if k[0] == scen), key=lambda k: (k[2], k[3]))
                picks.append(pool[len(pool) // 2])
        # 5th key: ensure a pass-1 rescue (base errors == 0) in mid band if available
        rescued = [k for k in pA_strata[(rho, 'mid')] if stageA_base[k]['errors'] == 0 and k not in picks]
        if rescued:
            picks.append(sorted(rescued, key=lambda k: (k[2], k[3]))[len(rescued) // 2])
        else:
            picks.append(next(k for k in all_r if k not in picks))
        for s, r, snr, f in picks:
            v = stageA_base[(s, r, snr, f)]
            g12_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors'], v['errors']])

    g3_picks = sf._select_balanced_keys(pA_strata, per_stratum=4)  # 4 rhos * 2 bands * 4 = 32 keys
    g3_jobs = [
        [s, r, snr, f, band, stageA_base[(s, r, snr, f)]['errors']]
        for s, r, snr, f, band in g3_picks
    ]

    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'sameframe_cd2_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        print('Running G1+G2 (20 low-pilot stageA F0 + CD2 pass-1 + CD2e8 keys)...', flush=True)
        g12_rows = sf._spawn_map(_g1_g2_worker, g12_jobs, args.workers, ipc_dir, 'g12')
        cd2_p1 = sum(1 for x in g12_rows if x['cd2_passes'] == 1)
        cd2_p2 = sum(1 for x in g12_rows if x['cd2_passes'] == 2)
        e8_p1 = sum(1 for x in g12_rows if x['cd2e8_passes'] == 1)
        e8_p2 = sum(1 for x in g12_rows if x['cd2e8_passes'] == 2)
        if not (cd2_p1 > 0 and cd2_p2 > 0 and e8_p1 > 0 and e8_p2 > 0):
            raise AssertionError(f'G2 did not cover pass-1 and pass-2 for both arms: cd2=({cd2_p1},{cd2_p2}), e8=({e8_p1},{e8_p2})')
        print(f'G1+G2 PASS (20/20; cd2=({cd2_p1}p1,{cd2_p2}p2), cd2e8=({e8_p1}p1,{e8_p2}p2))', flush=True)

        print(f'Running G3 stratified cost projection ({len(g3_jobs)} Part-A keys)...', flush=True)
        g3_rows = sf._spawn_map(_g3_cost_worker, g3_jobs, args.workers, ipc_dir, 'g3')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    counts = {k: len(v) for k, v in pA_strata.items()}

    def project(include_cd2e8: bool) -> dict[str, Any]:
        pA_sec = 0.0
        detail = {}
        for rho in PARTA_RHOS:
            for band in ('low', 'mid'):
                sub = [x for x in g3_rows if x['rho'] == rho and x['band'] == band]
                mean_cpu = float(np.mean([
                    x['f0_cpu'] + x['cd2_cpu'] + (x['cd2e8_cpu'] if include_cd2e8 else 0.0)
                    for x in sub
                ]))
                cnt = counts[(rho, band)]
                pA_sec += mean_cpu * cnt
                detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
        raw_h = pA_sec / 3600.0 + TIMING_ALLOWANCE_HOURS + IO_ALLOWANCE_HOURS
        marg_h = raw_h * COST_MARGIN
        return dict(
            include_cd2e8=include_cd2e8,
            partA_raw_hours=pA_sec / 3600.0,
            timing_allowance_hours=TIMING_ALLOWANCE_HOURS,
            io_allowance_hours=IO_ALLOWANCE_HOURS,
            raw_total_hours=raw_h,
            projected_hours_with_margin=marg_h,
            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
            strata=detail,
        )

    candidates = [project(True), project(False)]
    selected = next((c for c in candidates if c['within_budget']), None)
    gate_cpu_h = sf._used_cpu_seconds() / 3600.0
    all_passed = bool(
        len(g12_rows) == 20 and cd2_p1 > 0 and cd2_p2 > 0 and e8_p1 > 0 and e8_p2 > 0
        and selected is not None
    )

    payload = dict(
        _argv=sys.argv,
        _config=dict(
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
            own_md5=own_md5(),
            reused_upstream_md5=reused_md5,
            frozen_extra_md5=helpers['extra_md5'],
            p1_source_md5=ar.frozen_p1_md5(ctx),
            archive_shards_verified={k: len(v) for k, v in manifests.items()},
            sameframe_hg_manifest_sha256=SAMEFRAME_HG_MANIFEST_SHA256,
        ),
        all_passed=all_passed,
        selected=None if selected is None else dict(
            partA_rhos=list(PARTA_RHOS),
            include_cd2e8=selected['include_cd2e8'],
            projected_hours_with_margin=selected['projected_hours_with_margin'],
            raw_total_hours=selected['raw_total_hours'],
        ),
        G1=dict(passed=len(g12_rows) == 20, keys_checked=len(g12_rows)),
        G2=dict(passed=True, keys_checked=len(g12_rows), cd2_p1=cd2_p1, cd2_p2=cd2_p2, cd2e8_p1=e8_p1, cd2e8_p2=e8_p2, rows=g12_rows),
        G3=dict(
            passed=selected is not None,
            budget_cap_core_hours=BUDGET_CAP_HOURS,
            margin=COST_MARGIN,
            candidates=candidates,
        ),
        gate_cpu_hours=gate_cpu_h,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(out_dir / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(
        f'GATE_STATUS={"PASS" if all_passed else "FAIL_BUDGET"} '
        f'selected={payload["selected"]} cpu_hours={gate_cpu_h:.4f}',
        flush=True,
    )
    sys.exit(0 if all_passed else 1)


# --------------------------------------------------------------------------- Part A worker & analysis
def _partA_shard_worker(
    shard_idx: int,
    frames: tuple[int, ...],
    trig_by_frame: dict[int, list[tuple[str, int, int, int, int, int]]],
    include_cd2e8: bool,
    raw_dir: Path,
):
    C, _, _, helpers = sf.load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    final_path = raw_dir / f'partA_shard{shard_idx:03d}.jsonl.gz'
    out_lines: list[str] = []
    for frame in frames:
        items = trig_by_frame.get(frame, [])
        grouped: dict[tuple[str, int], list[tuple[int, int, int, int]]] = {}
        for s, rho, snr, exp_syn, exp_f0_err, exp_base_err in items:
            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err, exp_base_err))
        for (s, rho), grp in sorted(grouped.items()):
            base = stage3.inputs(ctx, frame, s, rho)
            for snr, exp_syn, exp_f0_err, exp_base_err in sorted(grp):
                _, obs, truth = stage3.observed(ctx, base, rho, snr)
                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
                if int(syn) != exp_syn or f0_err != exp_f0_err:
                    raise RuntimeError(
                        f'PartA F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
                    )
                cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
                if int(cd2['pass1_errors']) != exp_base_err:
                    raise RuntimeError(
                        f'PartA CD2 pass-1 drift vs stageA base at {(s, rho, snr, frame)}: '
                        f'{cd2["pass1_errors"]} != {exp_base_err}'
                    )
                arms_rec = dict(CD2=cd2)
                if include_cd2e8:
                    arms_rec['CD2e8'] = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
                out_lines.append(json.dumps(dict(
                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
                ), allow_nan=False) + '\n')
    sf._write_gzip_jsonl_atomic(final_path, out_lines)
    print(f'PartA shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)


def p1p_verdict(ci_lo: float, ci_hi: float) -> str:
    if ci_lo >= P1P_THRESHOLD_DB:
        return 'DOPPLER-LINE'
    if ci_hi < P1P_THRESHOLD_DB:
        return 'STOP-LINE'
    return 'INCONCLUSIVE'


def analyze_partA(
    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
    include_cd2e8: bool,
    crossing_fn,
    diag_stats: dict[str, Any],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Joint paired physical-frame bootstrap analysis for P1' (frames 41000-41399, seed 20261125)."""
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
        if arm in ('delay', 'full', 'ldop'):
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

    p1p = contrast('CD2', 's100')
    lo_val = float(p1p['ci95_db'][0]) if isinstance(p1p['ci95_db'][0], float) else (-math.inf if p1p['ci95_db'][0] == '-inf' else math.inf)
    hi_val = float(p1p['ci95_db'][1]) if isinstance(p1p['ci95_db'][1], float) else (-math.inf if p1p['ci95_db'][1] == '-inf' else math.inf)
    p1p['verdict'] = p1p_verdict(lo_val, hi_val)

    sec = {}
    for comp in ('s050', 'ldop', 'full', 'delay', 'base', 'HG', 'HGint'):
        if comp in fail_by_arm:
            sec[f'CD2_minus_{comp}'] = contrast('CD2', comp)
    if include_cd2e8 and 'CD2e8' in fail_by_arm:
        for comp in ('s100', 's050', 'ldop', 'full', 'HG', 'HGint', 'CD2'):
            if comp in fail_by_arm:
                sec[f'CD2e8_minus_{comp}'] = contrast('CD2e8', comp)
    sec['HG_minus_s100'] = contrast('HG', 's100')

    return dict(
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        partA_rhos=list(PARTA_RHOS),
        include_cd2e8=include_cd2e8,
        primary_P1_prime=p1p,
        secondary_contrasts=sec,
        mean_crossing=arm_mean_pt,
        crossings_by_scenario=arm_scen_pt,
        best_rho=arm_best_rho,
        diagnostics=diag_stats,
    )


def render_results_md(res: dict[str, Any]) -> str:
    pA = res['partA']
    p1p = pA['primary_P1_prime']

    def fval(x):
        if isinstance(x, list):
            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
        return x if isinstance(x, str) else f'{x:.4f}'

    lines = [
        '# Same-Frame CD2 Headroom & Quiet Timing Results (`sameframe_cd2_20261125`)',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- Part A CPU: **{res["runtime"]["partA_total_core_hours"]:.4f} core-hours** (cap {res["runtime"]["cpu_cap_core_hours"]:.1f} h; wall {res["runtime"]["partA_wall_seconds"]:.1f} s)',
        '',
        '## Primary Verdict P1\' (Pre-Registered, Frames 41000–41399)',
        '',
        '| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |',
        '|---|---:|---|---|',
        f'| `min CD2 (100..250) − min s100 (100..200)` | **{fval(p1p["point_db"])}** | **[{fval(p1p["ci95_db"][0])}, {fval(p1p["ci95_db"][1])}]** | **{p1p["verdict"]}** |',
        '',
        '## Part A: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
        '',
    ]
    arms_order = [a for a in ('base', 'delay', 'HG', 'HGint', 'CD2', 'CD2e8', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in pA['mean_crossing']]
    rhos_all = ('50', '100', '150', '200', '250', '300')
    lines.append('| Arm | ' + ' | '.join(f'ρ={int(r)/1000:.2f}' for r in rhos_all) + ' | Best ρ |')
    lines.append('|---|' + '---:|' * len(rhos_all) + '---:|')
    for a in arms_order:
        cells = [fval(pA['mean_crossing'][a][r]) if r in pA['mean_crossing'][a] else '—' for r in rhos_all]
        lines.append(f'| {a} | ' + ' | '.join(cells) + f' | {pA["best_rho"][a]/1000:.2f} |')

    lines += ['', '### Part A Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
    for name, c in pA['secondary_contrasts'].items():
        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')

    lines += ['', '### Part A Pass-2 Diagnostics', '']
    for arm, d in pA['diagnostics'].items():
        lines.append(
            f'- `{arm}`: pass-1 stop {d["pass1_early_stop"]}/{d["triggered"]}, '
            f'pass-2 ran {d["pass2_ran"]} (rescued {d["pass2_rescued"]}), '
            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}'
        )

    timing = res.get('timing')
    if timing:
        lines += ['', '## Part B: Quiet Single-Core Timing Panels (Huang Frames 5400–5799)', '']
        lines.append(
            f'- Pinned CPU: `{timing["cpu"]["idle_cpu"]}` (pre-start util `{timing["cpu"]["measured_utilization_pct"]:.1f}%`, '
            f'wall `{timing["wall_seconds"]:.1f} s`, timing CPU `{timing["timing_cpu_hours"]:.4f} core-hours`)'
        )
        for pname, pdata in timing['panels'].items():
            lines += [
                '',
                f'### Panel `{pname}` (ρ={pdata["rho_permille"]/1000:.2f}, SNR={pdata["snr_centi_db"]/100:.1f} dB; '
                f'100 triggered + 50 untriggered F0; shared F0 median {1000*pdata["f0"]["median"]:.2f} ms)',
                '',
                '| Arm | Mean (ms) | Median (ms) | p95 (ms) | Pass-2 Rate | Ratio of Means vs CD | Median Paired Ratio vs CD | Amortized Full-Frame (ms) |',
                '|---|---:|---:|---:|---:|---:|---:|---:|',
            ]
            for arm in ('CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint'):
                b = pdata['branches'][arm]
                p2r = pdata['pass2_rate'].get(arm, 0.0)
                rm = 1.0 if arm == 'CD' else pdata['relative_to_cd'][arm]['ratio_of_means']
                mp = 1.0 if arm == 'CD' else pdata['relative_to_cd'][arm]['median_paired_ratio']
                am = pdata['amortized_full_frame_mean_seconds'][arm]
                lines.append(
                    f'| {arm} | {1000*b["mean"]:.2f} | {1000*b["median"]:.2f} | {1000*b["p95"]:.2f} | '
                    f'{100*p2r:.1f}% | {rm:.3f}× | {mp:.3f}× | {1000*am:.2f} |'
                )
    return '\n'.join(lines) + '\n'


def _do_read_partA(
    out_dir: Path,
    gate: dict[str, Any],
    gate_md5: str,
    freeze_commit: str,
    runtime_info: dict[str, Any],
    raw_md5: dict[str, str],
    *,
    enforce_cpu_cap: bool = False,
    wall_start: float | None = None,
):
    import stageA  # noqa: E402
    import stageA2  # noqa: E402
    import stageA3  # noqa: E402

    include_cd2e8 = bool(gate['selected']['include_cd2e8'])
    raw_dir = out_dir / 'raw'
    verify_all_archives()
    for fname, expected in raw_md5.items():
        if ar.md5_file(raw_dir / fname) != expected:
            raise RuntimeError(f'PartA raw shard MD5 mismatch {fname}')

    # Load stageA, stageA2, stageA3 archived failure grids
    fa, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)
    fa2, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
    fa3, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)

    stageA_base = sf.load_stageA_base(PARTA_RHOS)
    fi = {f: i for i, f in enumerate(PARTA_FRAMES)}

    # Load archived sameframe_hg Part 1 (HG, HG1, HGint)
    hg_arms = ('HG', 'HG1', 'HGint')
    hg_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in hg_arms}
    hg_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
    for (s, rho, snr, f), b in stageA_base.items():
        if b['syndrome'] == 0:
            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
            ef = b['f0_errors'] > 0
            for a in hg_arms:
                hg_fail[a][ix] = ef
            hg_seen[ix] = True
    for idx in range(N_SHARDS):
        sp = SAMEFRAME_HG_DIR / 'out' / 'raw' / f'part1_shard{idx:03d}.jsonl.gz'
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
                if hg_seen[ix]:
                    raise RuntimeError(f'Duplicate sameframe_hg key {r}')
                for a in hg_arms:
                    hg_fail[a][ix] = int(r['arms'][a]['errors']) > 0
                hg_seen[ix] = True
    if not hg_seen.all():
        raise RuntimeError('Incomplete sameframe_hg Part 1 grid')

    # Load new Part A (CD2, optional CD2e8)
    new_arms = ('CD2',) + (('CD2e8',) if include_cd2e8 else ())
    pA_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in new_arms}
    pA_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
    for (s, rho, snr, f), b in stageA_base.items():
        if b['syndrome'] == 0:
            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
            ef = b['f0_errors'] > 0
            for a in new_arms:
                pA_fail[a][ix] = ef
            pA_seen[ix] = True

    diag_acc = {a: dict(triggered=0, pass1_early_stop=0, pass2_ran=0, pass2_rescued=0, p1_edits=[], p2_edits=[]) for a in new_arms}
    trig_count = 0
    for idx in range(N_SHARDS):
        sp = raw_dir / f'partA_shard{idx:03d}.jsonl.gz'
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
                if pA_seen[ix]:
                    raise RuntimeError(f'Duplicate PartA key {r}')
                for a in new_arms:
                    rec = r['arms'][a]
                    pA_fail[a][ix] = int(rec['errors']) > 0
                    d = diag_acc[a]
                    d['triggered'] += 1
                    d['p1_edits'].append(int(rec['pass1_edits']))
                    if int(rec['passes_used']) == 1:
                        d['pass1_early_stop'] += 1
                    else:
                        d['pass2_ran'] += 1
                        d['p2_edits'].append(int(rec['pass2_edits']))
                        if int(rec['pass1_errors']) > 0 and int(rec['errors']) == 0:
                            d['pass2_rescued'] += 1
                pA_seen[ix] = True
                trig_count += 1
    if not pA_seen.all():
        raise RuntimeError(f'Incomplete PartA grid: missing {int((~pA_seen).sum())}')

    diag_stats = {
        a: dict(
            triggered=d['triggered'],
            pass1_early_stop=d['pass1_early_stop'],
            pass2_ran=d['pass2_ran'],
            pass2_rescued=d['pass2_rescued'],
            mean_pass1_edits=float(np.mean(d['p1_edits'])) if d['p1_edits'] else 0.0,
            mean_pass2_edits_when_ran=float(np.mean(d['p2_edits'])) if d['p2_edits'] else 0.0,
        )
        for a, d in diag_acc.items()
    }

    fail_by_arm = {
        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
    }
    for i, a in enumerate(stageA3.ARMS):
        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
    for a in hg_arms:
        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, hg_fail[a])
    for a in new_arms:
        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, pA_fail[a])

    print(f'Analyzing Part A ({int(pA_seen.sum())} keys, {trig_count} triggered, seed={BOOT_SEED})...', flush=True)
    partA_out = analyze_partA(fail_by_arm, include_cd2e8, stageA2.crossing, diag_stats)

    if enforce_cpu_cap:
        final_cpu = sf._used_cpu_seconds()
        if final_cpu >= BUDGET_CAP_SEC:
            print(f'STOPPED_BUDGET after Part A analysis ({final_cpu/3600:.3f} core-hours)', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        runtime_info = dict(
            runtime_info,
            partA_analysis_cpu_hours=max(0.0, final_cpu / 3600.0 - runtime_info['partA_workers_core_hours']),
            partA_total_core_hours=final_cpu / 3600.0,
            partA_wall_seconds=(time.monotonic() - wall_start) if wall_start is not None else runtime_info['partA_wall_seconds'],
        )

    results = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=freeze_commit,
            python_executable=sys.executable,
            own_md5=own_md5(),
            gate_md5=gate_md5,
            partA_rhos=list(PARTA_RHOS),
            include_cd2e8=include_cd2e8,
            partA_frames=[PARTA_FRAMES[0], PARTA_FRAMES[-1]],
            partA_triggered_keys=trig_count,
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
            sameframe_hg_manifest_sha256=SAMEFRAME_HG_MANIFEST_SHA256,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G1_keys=gate['G1']['keys_checked'],
            G2_keys=gate['G2']['keys_checked'],
            G3_projected_hours=gate['selected']['projected_hours_with_margin'],
        ),
        runtime=runtime_info,
        partA=partA_out,
        timing=None,
    )
    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    print(
        f'PARTA_DONE P1_prime={partA_out["primary_P1_prime"]["verdict"]} '
        f'point={partA_out["primary_P1_prime"]["point_db"]} '
        f'ci={partA_out["primary_P1_prime"]["ci95_db"]} '
        f'cpu_hours={runtime_info["partA_total_core_hours"]:.4f}',
        flush=True,
    )


def cmd_run_partA(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    ar.check_thread_env()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
    if not 1 <= args.workers <= 32:
        raise ValueError('workers must be in 1..32')

    out_dir = args.out.resolve()
    raw_dir = out_dir / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    if list(raw_dir.glob('partA_shard*.jsonl*')):
        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')

    gate_bytes = (out_dir / 'gate.json').read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to run without passing gate.json')
    live_own = own_md5()
    reused_md5 = verify_reused_upstream_md5()
    verify_freeze_commit_if_git(args.freeze_commit, live_own)
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
    if gate['_config'].get('reused_upstream_md5') != reused_md5:
        raise RuntimeError('gate.json reused_upstream_md5 differs from live upstream files')

    include_cd2e8 = bool(gate['selected']['include_cd2e8'])
    wall_start = time.monotonic()
    verify_all_archives()
    C, _, _, helpers = sf.load_stage_runtime()
    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
        raise RuntimeError('p1_source_md5 mismatch vs gate.json')

    stageA_base = sf.load_stageA_base(PARTA_RHOS)
    trig_by_frame: dict[int, list[tuple[str, int, int, int, int, int]]] = {}
    n_trig = 0
    for (s, rho, snr, f), b in stageA_base.items():
        if b['syndrome'] != 0:
            trig_by_frame.setdefault(f, []).append((s, rho, snr, b['syndrome'], b['f0_errors'], b['errors']))
            n_trig += 1
    jobs = [
        (idx, tuple(PARTA_FRAMES[idx::N_SHARDS]), {f: trig_by_frame.get(f, []) for f in PARTA_FRAMES[idx::N_SHARDS]}, include_cd2e8, raw_dir)
        for idx in range(N_SHARDS)
    ]
    print(f'Launching Part A: {n_trig} triggered keys on {args.workers} workers (include_cd2e8={include_cd2e8})...', flush=True)
    # Reserve 300 CPU-s headroom for poll latency, aggregation, and Part B margin check
    sf._run_sharded_phase(_partA_shard_worker, jobs, args.workers, BUDGET_CAP_SEC - 300.0)
    workers_cpu = sf._used_cpu_seconds()

    raw_md5 = {}
    for idx in range(N_SHARDS):
        p = raw_dir / f'partA_shard{idx:03d}.jsonl.gz'
        raw_md5[p.name] = ar.md5_file(p)
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
    )

    runtime_info = dict(
        partA_workers_core_hours=workers_cpu / 3600.0,
        partA_total_core_hours=workers_cpu / 3600.0,
        partA_wall_seconds=time.monotonic() - wall_start,
        cpu_cap_core_hours=BUDGET_CAP_HOURS,
    )
    _do_read_partA(
        out_dir, gate, gate_md5, args.freeze_commit, runtime_info, raw_md5,
        enforce_cpu_cap=True, wall_start=wall_start,
    )


# --------------------------------------------------------------------------- Part B: quiet single-core timing
def _latency(values: list[float]) -> dict[str, Any]:
    arr = np.asarray(values, dtype=float)
    return dict(
        n=int(len(arr)),
        mean=float(arr.mean()),
        median=float(np.median(arr)),
        p95=float(np.percentile(arr, 95)),
    )


def _load_huang_and_cd2_archives_for_panels(target_pairs: set[tuple[int, int]]):
    """Load archived decoded_sha for HG/HG1/HGint (huang_steelman) and CD2/CD2e8 (sameframe_hg) on target (rho, snr)."""
    hg_map: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
        with p.open('r', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                if (int(r['rho_permille']), int(r['snr_centi_db'])) in target_pairs:
                    hg_map[ar.row_key(r)] = r['arms']
    cd2_map: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for idx in range(N_SHARDS):
        sp = SAMEFRAME_HG_DIR / 'out' / 'raw' / f'part2_shard{idx:03d}.jsonl.gz'
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                if (int(r['rho_permille']), int(r['snr_centi_db'])) in target_pairs:
                    cd2_map[ar.row_key(r)] = r['arms']
    return hg_map, cd2_map


def cmd_timing(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
    proc_start = perf_counter()

    aff = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else [0]
    if platform.system() == 'Linux' and len(aff) != 1:
        raise RuntimeError(f'timing must be pre-pinned to 1 CPU via taskset, got affinity={aff}')
    cpu_info = dict(
        idle_cpu=int(aff[0]),
        measured_utilization_pct=float(os.environ.get('HS_QUIET_CPU_UTIL', '-1.0')),
        load=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [],
    )
    print(f'Quiet timing running on pre-pinned CPU {cpu_info}', flush=True)

    out_dir = args.out.resolve()
    verify_reused_upstream_md5()
    verify_freeze_commit_if_git(args.freeze_commit, own_md5())
    results_path = out_dir / 'results.json'
    results = json.loads(results_path.read_text(encoding='utf-8'))
    if results['_config']['freeze_commit'] != args.freeze_commit:
        raise RuntimeError('timing freeze-commit differs from results.json')
    if results['_config']['own_md5'] != own_md5():
        raise RuntimeError('timing own_md5 differs from results.json')

    # Verify cumulative budget before starting timing
    partA_cpu_h = float(results['runtime']['partA_total_core_hours'])
    remaining_cpu_sec = min(TIMING_BUDGET_SEC, BUDGET_CAP_SEC - partA_cpu_h * 3600.0)
    if remaining_cpu_sec <= 60.0:
        print(f'STOPPED_BUDGET before timing (partA_cpu={partA_cpu_h:.4f}h)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    verify_all_archives()
    C, _, _, helpers = sf.load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)

    archived_rows, _ = ar.load_archived_rho_sweep()
    target_pairs = {(rho, snr) for _, rho, snr in TIMING_PANELS}
    hg_arch, cd2_arch = _load_huang_and_cd2_archives_for_panels(target_pairs)

    # Prewarm on smoke frame 5800 (not measured)
    warm_base = stage3.inputs(ctx, 5800, 'U', 200)
    _, warm_obs, warm_truth = stage3.observed(ctx, warm_base, 200, 450)
    _, warm_arr, _, _ = stage3.e1.f0_state(ctx, warm_obs)
    run_cd_timed(ctx, helpers, warm_obs, warm_arr, warm_truth, arm_spec='A1', max_passes=1)
    ar.run_hg_arm(
        ctx, helpers, warm_obs, warm_arr, warm_truth,
        ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
        max_passes=1, record_match=False,
    )

    rows_lines: list[str] = []
    panels_summary: dict[str, Any] = {}
    all_report_arms = ('CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint')

    for panel_name, rho, snr in TIMING_PANELS:
        trig_by_s = {}
        untrig_by_s = {}
        for s in ar.SCENARIOS:
            trig_by_s[s] = sorted(
                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and k[2] == snr and r['triggered']),
                key=lambda k: k[3],
            )
            untrig_by_s[s] = sorted(
                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and k[2] == snr and not r['triggered']),
                key=lambda k: k[3],
            )
            if len(trig_by_s[s]) < 50 or len(untrig_by_s[s]) < 25:
                raise RuntimeError(f'Insufficient keys for {panel_name}/{s}: trig={len(trig_by_s[s])}, untrig={len(untrig_by_s[s])}')

        panel_keys = [k for pair in zip(trig_by_s['U'][:50], trig_by_s['G'][:50], strict=True) for k in pair]
        untrig_keys = [k for pair in zip(untrig_by_s['U'][:25], untrig_by_s['G'][:25], strict=True) for k in pair]

        untrig_f0_sec: dict[str, list[float]] = {'U': [], 'G': []}
        for key in untrig_keys:
            s, r_, snr_, frame = key
            arch = archived_rows[key]
            base = stage3.inputs(ctx, frame, s, r_)
            _, obs, truth = stage3.observed(ctx, base, r_, snr_)
            t_f0 = perf_counter()
            dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
            f0_sec = perf_counter() - t_f0
            f0 = stage3.decoded(ctx, dec, truth)
            if syn != 0 or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
                raise AssertionError(f'Timing untriggered F0 drift at {key}')
            untrig_f0_sec[s].append(float(f0_sec))
            rows_lines.append(json.dumps(dict(
                panel=panel_name, kind='untriggered_f0', key=list(key), f0_seconds=float(f0_sec),
            ), allow_nan=False) + '\n')
            if perf_counter() - proc_start >= remaining_cpu_sec:
                sys.exit(BUDGET_EXIT_CODE)

        timed_rows = []
        scen_pos = {'U': 0, 'G': 0}
        for idx, key in enumerate(panel_keys):
            s, r_, snr_, frame = key
            arch = archived_rows[key]
            hga = hg_arch[key]
            cd2a = cd2_arch[key]
            base = stage3.inputs(ctx, frame, s, r_)
            _, obs, truth = stage3.observed(ctx, base, r_, snr_)

            t_f0 = perf_counter()
            dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
            f0_sec = perf_counter() - t_f0
            f0 = stage3.decoded(ctx, dec, truth)
            if syn != arch['syndrome'] or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
                raise AssertionError(f'Timing F0 drift at {key}')

            offset = scen_pos[s] % len(TIMING_BRANCHES)
            scen_pos[s] += 1
            order = TIMING_BRANCHES[offset:] + TIMING_BRANCHES[:offset]
            sec_map: dict[str, float] = {}
            passes_map: dict[str, int] = {}
            for arm in order:
                if arm == 'CD':
                    out = run_cd_timed(ctx, helpers, obs, arrays, truth, arm_spec='A1', max_passes=1)
                    if out['decoded_sha'] != arch['arms']['CD']['decoded_sha']:
                        raise AssertionError(f'Timing CD drift at {key}')
                    sec_map['CD'] = out['seconds']
                    passes_map['CD'] = 1
                elif arm == 'CD2':
                    out = run_cd_timed(ctx, helpers, obs, arrays, truth, arm_spec='A1', max_passes=2)
                    if out['decoded_sha'] != cd2a['CD2']['decoded_sha']:
                        raise AssertionError(f'Timing CD2 drift at {key}')
                    sec_map['CD2'] = out['seconds']
                    passes_map['CD2'] = out['passes_used']
                elif arm == 'CD2e8':
                    out = run_cd_timed(ctx, helpers, obs, arrays, truth, arm_spec='A1e8', max_passes=2)
                    if out['decoded_sha'] != cd2a['CD2e8']['decoded_sha']:
                        raise AssertionError(f'Timing CD2e8 drift at {key}')
                    sec_map['CD2e8'] = out['seconds']
                    passes_map['CD2e8'] = out['passes_used']
                elif arm == 'HG':
                    out = ar.run_hg_arm(
                        ctx, helpers, obs, arrays, truth,
                        ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
                        max_passes=2, record_match=False,
                    )
                    if (out['HG']['decoded_sha'] != hga['HG']['decoded_sha']
                            or out['HG1']['decoded_sha'] != hga['HG1']['decoded_sha']):
                        raise AssertionError(f'Timing HG/HG1 drift at {key}')
                    sec_map['HG'] = out['HG']['seconds']
                    sec_map['HG1'] = out['HG1']['seconds']
                    passes_map['HG'] = out['HG']['passes_used']
                    passes_map['HG1'] = 1
                elif arm == 'HGint':
                    out = ar.run_hg_arm(
                        ctx, helpers, obs, arrays, truth,
                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
                        max_passes=2, record_match=False,
                    )
                    if out['HG']['decoded_sha'] != hga['HGint']['decoded_sha']:
                        raise AssertionError(f'Timing HGint drift at {key}')
                    sec_map['HGint'] = out['HG']['seconds']
                    passes_map['HGint'] = out['HG']['passes_used']

            row = dict(
                panel=panel_name, kind='triggered_panel', key=list(key), order=list(order),
                f0_seconds=float(f0_sec), passes_used=passes_map, branch_seconds=sec_map,
            )
            rows_lines.append(json.dumps(row, allow_nan=False) + '\n')
            timed_rows.append(row)

            elapsed = perf_counter() - proc_start
            if elapsed >= remaining_cpu_sec - 10.0 or sf._used_cpu_seconds() >= remaining_cpu_sec - 10.0:
                print(f'STOPPED_BUDGET in timing {panel_name} at {idx+1}/100 ({elapsed:.1f}s)', flush=True)
                sys.exit(BUDGET_EXIT_CODE)
            if (idx + 1) % 25 == 0:
                print(f'Timing [{panel_name}] {idx+1}/100 done in {elapsed:.1f}s', flush=True)

        cd_arr = np.array([r['branch_seconds']['CD'] for r in timed_rows], dtype=float)
        f0_arr = np.array([r['f0_seconds'] for r in timed_rows], dtype=float)
        branches = {}
        rel_cd = {}
        pass2_rate = {}
        for arm in all_report_arms:
            arr = np.array([r['branch_seconds'][arm] for r in timed_rows], dtype=float)
            branches[arm] = _latency(arr.tolist())
            pass2_rate[arm] = float(np.mean([r['passes_used'][arm] == 2 for r in timed_rows]))
            if arm != 'CD':
                rel_cd[arm] = dict(
                    ratio_of_means=float(arr.mean() / cd_arr.mean()),
                    median_paired_ratio=float(np.median(arr / cd_arr)),
                    cd_faster_fraction=float(np.mean(cd_arr < arr)),
                )

        p_trig_by_s = {s: len(trig_by_s[s]) / 400.0 for s in ar.SCENARIOS}
        amortized_by_s = {}
        for s in ar.SCENARIOS:
            s_rows = [r for r in timed_rows if r['key'][0] == s]
            p_s = p_trig_by_s[s]
            f0_u = float(np.mean(untrig_f0_sec[s]))
            f0_t = float(np.mean([r['f0_seconds'] for r in s_rows]))
            amortized_by_s[s] = {
                arm: float((1.0 - p_s) * f0_u + p_s * (f0_t + float(np.mean([r['branch_seconds'][arm] for r in s_rows]))))
                for arm in all_report_arms
            }
        amortized_mean = {arm: 0.5 * (amortized_by_s['U'][arm] + amortized_by_s['G'][arm]) for arm in all_report_arms}

        panels_summary[panel_name] = dict(
            rho_permille=rho,
            snr_centi_db=snr,
            keys=len(timed_rows),
            untriggered_f0_keys=len(untrig_keys),
            f0=_latency(f0_arr.tolist()),
            f0_untriggered={s: _latency(untrig_f0_sec[s]) for s in ar.SCENARIOS},
            branches=branches,
            pass2_rate=pass2_rate,
            relative_to_cd=rel_cd,
            trigger_rate_by_scenario=p_trig_by_s,
            amortized_full_frame_mean_by_scenario=amortized_by_s,
            amortized_full_frame_mean_seconds=amortized_mean,
        )

    timing_rows_path = out_dir / 'raw' / 'timing_rows.jsonl'
    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
    timing_rows_md5 = ar.md5_file(timing_rows_path)

    # Append timing_rows.jsonl MD5 into REMOTE_ROWS_MD5.txt atomically
    md5_map = {}
    for line in (out_dir / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8').splitlines():
        if line.strip():
            d, n = line.split()
            md5_map[n] = d
    md5_map[timing_rows_path.name] = timing_rows_md5
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(md5_map.items())),
    )

    wall = perf_counter() - proc_start
    timing_cpu_h = sf._used_cpu_seconds() / 3600.0
    if partA_cpu_h + timing_cpu_h >= BUDGET_CAP_HOURS:
        print(f'STOPPED_BUDGET after timing (total={partA_cpu_h + timing_cpu_h:.4f}h)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    timing_payload = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            python_executable=sys.executable,
            threads=thread_env,
            timing_boundary='decision-ready (after syndrome check, before truth scoring/hashing)',
            branches=list(TIMING_BRANCHES),
            timing_rows_path=str(timing_rows_path),
            timing_rows_md5=timing_rows_md5,
        ),
        cpu=cpu_info,
        end_load=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [],
        wall_seconds=float(wall),
        timing_cpu_hours=float(timing_cpu_h),
        panels=panels_summary,
    )
    ar.atomic_write_text(out_dir / 'timing_summary.json', json.dumps(timing_payload, indent=2, allow_nan=False) + '\n')

    results['timing'] = timing_payload
    results['runtime']['timing_cpu_hours'] = float(timing_cpu_h)
    results['runtime']['total_core_hours'] = float(partA_cpu_h + timing_cpu_h)
    results['_config']['raw_rows_md5'] = md5_map
    ar.atomic_write_text(results_path, json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    p20 = panels_summary['rho200_snr450']['branches']
    print(
        f'TIMING_DONE wall={wall:.1f}s cpu={timing_cpu_h:.4f}h '
        f'rho200_mean: CD={1000*p20["CD"]["mean"]:.1f}ms CD2={1000*p20["CD2"]["mean"]:.1f}ms '
        f'HG={1000*p20["HG"]["mean"]:.1f}ms HGint={1000*p20["HGint"]["mean"]:.1f}ms',
        flush=True,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    g = sub.add_parser('gate')
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--workers', type=int, default=16)

    r = sub.add_parser('partA')
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--freeze-commit', required=True)
    r.add_argument('--workers', type=int, default=WORKERS)

    t = sub.add_parser('timing')
    t.add_argument('--out', type=Path, required=True)
    t.add_argument('--freeze-commit', required=True)

    args = ap.parse_args()
    dict(gate=cmd_gate, partA=cmd_run_partA, timing=cmd_timing)[args.mode](args)


if __name__ == '__main__':
    main()
