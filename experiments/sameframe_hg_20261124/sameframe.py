"""Same-frame decisive check: Part 1 (HG/HGint on 41000-41399) + Part 2 (CD2/CD2e8 on 5400-5799)."""
from __future__ import annotations

import argparse
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
import sys
import time
from types import FunctionType, SimpleNamespace
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
DATA_PILOT_DIR = EXP / 'data_pilot_fer_20261121'
HUANG_DIR = EXP / 'huang_steelman_20261124'
RHO_SWEEP_DIR = EXP / 'rho_sweep_20261119'

sys.path.insert(0, str(DATA_PILOT_DIR))
sys.path.insert(0, str(HUANG_DIR))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402

PART1_RHOS = (100, 150, 200, 250)
PART1_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
PART1_FRAMES = tuple(range(41000, 41400))
PART1_BOOT_DRAWS = 2000
PART1_BOOT_SEED = 20261124
P1_THRESHOLD_DB = 0.5
P2_THRESHOLD_DB = 0.2

ARCHIVE_MANIFESTS = {
    'stageA': (DATA_PILOT_DIR / 'out' / 'stageA', '30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68'),
    'stageA2': (DATA_PILOT_DIR / 'out' / 'stageA2', '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354'),
    'stageA3': (DATA_PILOT_DIR / 'out' / 'stageA3', '6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a'),
    'rho_sweep': (RHO_SWEEP_DIR / 'out' / 'main_20261119', ar.RHO_ARCHIVE_MD5_SHA256),
    'huang': (HUANG_DIR / 'out', 'b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc'),
}
OWN_FILES = ('PROTOCOL.md', 'sameframe.py', 'test_sameframe.py', 'launch.sh')
WORKERS = 24
BUDGET_CAP_HOURS = 16.0
BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.25
BUDGET_EXIT_CODE = 124
N_SHARDS = 24
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_manifest(name: str) -> dict[str, str]:
    base_dir, expected_sha = ARCHIVE_MANIFESTS[name]
    manifest = base_dir / 'REMOTE_ROWS_MD5.txt'
    got_sha = ar.sha256_file(manifest)
    if got_sha != expected_sha:
        raise RuntimeError(f'{name} manifest SHA-256 mismatch: {got_sha} != {expected_sha}')
    raw_dir = base_dir / 'raw' if name == 'huang' else base_dir
    out: dict[str, str] = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, fname = line.split()
        p = raw_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f'Missing archive shard {p}')
        actual = ar.md5_file(p)
        if actual != digest:
            raise RuntimeError(f'Archive shard MD5 mismatch {p}: {actual} != {digest}')
        out[fname] = actual
    disk_shards = {p.name for p in raw_dir.glob('rows_shard*.jsonl*')}
    if disk_shards != set(out):
        raise RuntimeError(
            f'{name} shard set mismatch on disk vs manifest: extra={sorted(disk_shards - set(out))}, '
            f'missing={sorted(set(out) - disk_shards)}'
        )
    return out


def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
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
    for name, exp_md5 in live_own_md5.items():
        blob = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
            capture_output=True, check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f'freeze_commit {freeze_commit} missing {name}')
        got = hashlib.md5(blob.stdout).hexdigest()
        if got != exp_md5:
            raise RuntimeError(f'Live {name} ({exp_md5}) differs from freeze_commit {freeze_commit} ({got})')
    return True


def _make_cd_e8_kernel(cd):
    """Runtime-only clone of cd.reopen_geometry allowing max_edits <= 8 (leaving frozen cd untouched)."""
    orig_validate = cd._validate

    def _validate_e8(
        Y, x, v, paths, c1, c2, ridge, max_delay, doppler_min,
        doppler_max, grid_step, max_edits, chunk_size, local_passes,
        local_halfwidth, local_max_evals, duplicate_tolerance, top_k,
    ):
        if (isinstance(max_edits, (bool, np.bool_))
                or not isinstance(max_edits, (int, np.integer))
                or not (0 <= int(max_edits) <= 8)):
            raise ValueError(f'invalid max_edits for A1e8: {max_edits!r}')
        return orig_validate(
            Y, x, v, paths, c1, c2, ridge, max_delay, doppler_min,
            doppler_max, grid_step, min(int(max_edits), 2), chunk_size, local_passes,
            local_halfwidth, local_max_evals, duplicate_tolerance, top_k,
        )

    reopen_e8 = FunctionType(
        cd.reopen_geometry.__code__,
        dict(cd.reopen_geometry.__globals__, _validate=_validate_e8),
        cd.reopen_geometry.__name__,
        cd.reopen_geometry.__defaults__,
    )
    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen_e8)


def load_stage_runtime():
    """Verify frozen MD5s first, then initialize via stageA.setup() and build hs_arms helpers."""
    extra_md5 = ar.verify_frozen_extra_md5()
    import stageA  # noqa: E402
    import stageA2  # noqa: E402

    C = stageA.setup()
    stage3 = C['stage3']
    # Register A1e8 (max_edits=8, local_passes=2, full Gamma) at runtime without modifying frozen files
    stage3.e1.ARM_SPECS['A1e8'] = dict(gamma_mode='full', max_edits=8, local_passes=2)
    cd_e8 = _make_cd_e8_kernel(C['cd'])

    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
    from messages import moments
    from physical import Channel
    from twofft import time_refine

    helpers = dict(
        stage3=stage3,
        cd=C['cd'],
        cd_e8=cd_e8,
        BaselineInitializer=BaselineInitializer,
        Channel=Channel,
        moments=moments,
        time_refine=time_refine,
        extra_md5=extra_md5,
    )
    return C, stageA, stageA2, helpers


def run_cd_two_pass(
    ctx,
    helpers: dict[str, Any],
    obs: dict[str, Any],
    arrays: dict[str, Any],
    truth: dict[str, Any],
    *,
    arm_spec: str,
    expected_pass1: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run 1-to-2-pass CODELAY local exchange with syndrome early stop (same inter-pass update as HG)."""
    stage3 = helpers['stage3']
    cd = helpers['cd_e8'] if arm_spec == 'A1e8' else helpers['cd']
    ar._require_finite(arrays['r1_check'], f'{arm_spec}.p1.r1_check')
    ar._require_finite(arrays['r1_app'], f'{arm_spec}.p1.r1_app')

    br1 = stage3.e1.run_branch(ctx, cd, obs, arrays, arm_spec)
    res1 = br1['result']
    if bool(res1.diagnostics.get('numerical_fallback')):
        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 1')
    ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
    ar._require_finite(br1['detector']['extrinsic'], f'{arm_spec}.p1.extrinsic')
    dec1 = br1['decoder']
    ar._require_finite(dec1['raw_check_extrinsic'], f'{arm_spec}.p1.raw_check_extrinsic')
    ar._require_finite(dec1['raw_app'], f'{arm_spec}.p1.raw_app')
    d1 = stage3.decoded(ctx, dec1, truth)
    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))

    if expected_pass1 is not None:
        if d1['errors'] != int(expected_pass1['errors']) or d1['decoded_sha'] != expected_pass1['decoded_sha']:
            raise RuntimeError(
                f'{arm_spec} pass-1 mismatch vs archived CD: got {d1}, expected {expected_pass1}'
            )

    if syn1 == 0:
        return dict(
            errors=d1['errors'],
            decoded_sha=d1['decoded_sha'],
            syndrome=0,
            passes_used=1,
            pass1_errors=d1['errors'],
            pass1_syndrome=0,
            pass1_edits=len(res1.edits),
            pass2_edits=0,
            numerical_fallback=False,
        )

    arrays2 = dict(
        r1_delays=np.array([int(p.delay) for p in res1.paths], dtype=int),
        r1_dopplers=np.array([float(p.doppler) for p in res1.paths], dtype=float),
        r1_gains=np.asarray(res1.gains, dtype=complex),
        r1_check=dec1['raw_check_extrinsic'],
        r1_app=dec1['raw_app'],
    )
    br2 = stage3.e1.run_branch(ctx, cd, obs, arrays2, arm_spec)
    res2 = br2['result']
    if bool(res2.diagnostics.get('numerical_fallback')):
        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 2')
    ar._require_finite(res2.gains, f'{arm_spec}.p2.gains')
    ar._require_finite(br2['detector']['extrinsic'], f'{arm_spec}.p2.extrinsic')
    dec2 = br2['decoder']
    ar._require_finite(dec2['raw_check_extrinsic'], f'{arm_spec}.p2.raw_check_extrinsic')
    ar._require_finite(dec2['raw_app'], f'{arm_spec}.p2.raw_app')
    d2 = stage3.decoded(ctx, dec2, truth)
    syn2 = int(ctx.hd.syndrome_weight(ctx, dec2['decoded']))

    return dict(
        errors=d2['errors'],
        decoded_sha=d2['decoded_sha'],
        syndrome=syn2,
        passes_used=2,
        pass1_errors=d1['errors'],
        pass1_syndrome=syn1,
        pass1_edits=len(res1.edits),
        pass2_edits=len(res2.edits),
        numerical_fallback=False,
    )


def load_stageA_base(rhos: tuple[int, ...] = PART1_RHOS) -> dict[tuple[str, int, int, int], dict[str, int]]:
    """Load archived stageA arms.base (syndrome, f0_errors, errors) for requested rhos."""
    base_dir = DATA_PILOT_DIR / 'out' / 'stageA'
    out: dict[tuple[str, int, int, int], dict[str, int]] = {}
    for p in sorted(base_dir.glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                rho = int(r['rho'])
                if rho not in rhos:
                    continue
                k = (r['scenario'], rho, int(r['snr']), int(r['frame']))
                b = r['arms']['base']
                out[k] = dict(
                    syndrome=int(b['syndrome']),
                    f0_errors=int(b['f0_errors']),
                    errors=int(b['errors']),
                )
    expected = len(PART1_FRAMES) * 2 * len(rhos) * len(PART1_SNRS)
    if len(out) != expected:
        raise RuntimeError(f'stageA base count mismatch: got {len(out)}, expected {expected}')
    return out


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


def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
    """File-IPC spawn worker pool (zero /dev/shm named semaphores)."""
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
            raise RuntimeError(f'Gate worker {tag}/{wi} exited with code {code}')
    merged: list[tuple[int, Any]] = []
    for wi, out_f in enumerate(out_files):
        chunk = json.loads(out_f.read_text(encoding='utf-8'))
        for pos, val in enumerate(chunk):
            merged.append((wi + pos * n_workers, val))
    merged.sort(key=lambda x: x[0])
    return [v for _, v in merged]


def _g1_worker(in_path: str, out_path: str):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for s, rho, snr, frame, exp_syn, exp_f0_err in jobs:
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
        f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
        ok = bool(int(syn) == int(exp_syn) and f0_err == int(exp_f0_err) and int(syn) != 0)
        if not ok:
            raise AssertionError(
                f'G1 F0 mismatch at {(s, rho, snr, frame)}: live=({syn},{f0_err}) != stageA=({exp_syn},{exp_f0_err})'
            )
        res.append(dict(key=[s, rho, snr, frame], syndrome=int(syn), f0_errors=f0_err, ok=True))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def _g2_worker(in_path: str, out_path: str):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for item in jobs:
        s, rho, snr, frame = item['key']
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        if int(syn) == 0:
            raise AssertionError(f'G2 key not triggered: {item["key"]}')
        out = ar.run_hg_arm(
            ctx, helpers, obs, arrays, truth,
            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
            max_passes=2, record_match=False,
        )
        ok_hg = (
            out['HG']['errors'] == item['HG']['errors']
            and out['HG']['decoded_sha'] == item['HG']['decoded_sha']
            and out['HG']['passes_used'] == item['HG']['passes_used']
        )
        ok_hg1 = (
            out['HG1']['errors'] == item['HG1']['errors']
            and out['HG1']['decoded_sha'] == item['HG1']['decoded_sha']
        )
        if not (ok_hg and ok_hg1):
            raise AssertionError(f'G2 HG parity mismatch at {item["key"]}: got {out}, expected {item}')
        res.append(dict(key=item['key'], passes_used=out['HG']['passes_used'], ok=True))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def _g3_worker(in_path: str, out_path: str):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for item in jobs:
        s, rho, snr, frame = item['key']
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        if int(syn) == 0:
            raise AssertionError(f'G3 key not triggered: {item["key"]}')
        cd2 = run_cd_two_pass(
            ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=item['CD'],
        )
        cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
        res.append(dict(
            key=item['key'],
            cd2_passes=cd2['passes_used'],
            cd2_p1_err=cd2['pass1_errors'],
            cd2_final_err=cd2['errors'],
            cd2e8_passes=cd2e8['passes_used'],
            cd2e8_final_err=cd2e8['errors'],
            cd2e8_p1_edits=cd2e8['pass1_edits'],
            cd2e8_p2_edits=cd2e8['pass2_edits'],
            ok=True,
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def _g4_part1_worker(in_path: str, out_path: str):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for s, rho, snr, frame, band in jobs:
        t0 = time.process_time()
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        t_f0 = time.process_time() - t0
        if int(syn) == 0:
            raise AssertionError(f'G4 part1 key untriggered: {(s, rho, snr, frame)}')
        t1 = time.process_time()
        hg = ar.run_hg_arm(
            ctx, helpers, obs, arrays, truth,
            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
            max_passes=2, record_match=False,
        )
        t_hg = time.process_time() - t1
        t2 = time.process_time()
        hgint = ar.run_hg_arm(
            ctx, helpers, obs, arrays, truth,
            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
            max_passes=2, record_match=False,
        )
        t_hgint = time.process_time() - t2
        res.append(dict(
            key=[s, rho, snr, frame], rho=rho, band=band,
            f0_cpu=t_f0, hg_cpu=t_hg, hgint_cpu=t_hgint,
            hg_passes=hg['HG']['passes_used'], hgint_passes=hgint['HG']['passes_used'],
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def _g4_part2_worker(in_path: str, out_path: str):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    res = []
    for s, rho, snr, frame, band, arch_cd in jobs:
        t0 = time.process_time()
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        t_f0 = time.process_time() - t0
        if int(syn) == 0:
            raise AssertionError(f'G4 part2 key untriggered: {(s, rho, snr, frame)}')
        t1 = time.process_time()
        cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
        t_cd2 = time.process_time() - t1
        t2 = time.process_time()
        cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
        t_cd2e8 = time.process_time() - t2
        res.append(dict(
            key=[s, rho, snr, frame], rho=rho, band=band,
            f0_cpu=t_f0, cd2_cpu=t_cd2, cd2e8_cpu=t_cd2e8,
            cd2_passes=cd2['passes_used'], cd2e8_passes=cd2e8['passes_used'],
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(res))


def _select_balanced_keys(
    keys_by_stratum: dict[tuple[int, str], list[tuple[str, int, int, int]]],
    per_stratum: int,
) -> list[tuple[str, int, int, int, str]]:
    """Select balanced U/G and interior SNR-quantile keys per (rho, band) deterministically."""
    selected = []
    for (rho, band), ks in sorted(keys_by_stratum.items()):
        u_ks = sorted((k for k in ks if k[0] == 'U'), key=lambda k: (k[2], k[3]))
        g_ks = sorted((k for k in ks if k[0] == 'G'), key=lambda k: (k[2], k[3]))
        n_each = per_stratum // 2
        picks = []
        for pool in (u_ks, g_ks):
            if len(pool) < n_each:
                raise RuntimeError(f'Insufficient keys in stratum {(rho, band)}: {len(pool)} < {n_each}')
            # Use interior quantiles (q = (i + 0.5) / n_each) so n_each=1 hits median and n_each=2 hits 25%/75%
            idxs = [min(len(pool) - 1, int((i + 0.5) * len(pool) / n_each)) for i in range(n_each)]
            picks.extend(pool[i] for i in idxs)
        for s, r, snr, f in picks:
            selected.append((s, r, snr, f, band))
    return selected


def cmd_gate(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    started = time.monotonic()

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    # Remove any stale gate.json BEFORE running gates so an aborted run can never leave an old PASS behind
    stale_gate = out_dir / 'gate.json'
    if stale_gate.exists():
        stale_gate.unlink()

    manifests = {name: verify_manifest(name) for name in ARCHIVE_MANIFESTS}
    C, _, _, helpers = load_stage_runtime()
    ctx = C['ctx']

    stageA_base = load_stageA_base(PART1_RHOS)
    rho_arch, _ = ar.load_archived_rho_sweep()

    # Load 5 archived huang_steelman HG keys (mix of U/G and 1-pass/2-pass stops)
    g2_jobs = []
    seen_p = set()
    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
        with p.open('r', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                pu = int(r['arms']['HG']['passes_used'])
                tag = (r['scenario'], pu)
                if len(g2_jobs) < 5 and (tag not in seen_p or len(seen_p) >= 4):
                    seen_p.add(tag)
                    g2_jobs.append(dict(
                        key=[r['scenario'], int(r['rho_permille']), int(r['snr_centi_db']), int(r['frame'])],
                        HG=dict(
                            errors=int(r['arms']['HG']['errors']),
                            decoded_sha=r['arms']['HG']['decoded_sha'],
                            passes_used=pu,
                        ),
                        HG1=dict(
                            errors=int(r['arms']['HG1']['errors']),
                            decoded_sha=r['arms']['HG1']['decoded_sha'],
                        ),
                    ))
                if len(g2_jobs) >= 5:
                    break
        if len(g2_jobs) >= 5:
            break
    if len(g2_jobs) != 5:
        raise RuntimeError(f'Expected 5 huang HG keys for G2, got {len(g2_jobs)}')

    # G1: 20 triggered stageA keys (5 per rho in 100..250, guaranteed to cover both U/G and both low/mid bands)
    p1_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
    for k, v in stageA_base.items():
        if v['syndrome'] != 0:
            band = 'low' if k[2] <= 400 else 'mid'
            p1_strata.setdefault((k[1], band), []).append(k)
    g1_jobs = []
    for rho in PART1_RHOS:
        picks = []
        for band in ('low', 'mid'):
            for scen in ('U', 'G'):
                pool = sorted((k for k in p1_strata[(rho, band)] if k[0] == scen), key=lambda k: (k[2], k[3]))
                picks.append(pool[len(pool) // 2])
        # 5th key from mid band (higher SNR interior)
        extra_pool = sorted(p1_strata[(rho, 'mid')], key=lambda k: (k[2], k[3]))
        picks.append(next(k for k in extra_pool[len(extra_pool) * 3 // 4:] if k not in picks))
        for s, r, snr, f in picks:
            v = stageA_base[(s, r, snr, f)]
            g1_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors']])

    # G3: 20 triggered rho_sweep keys across all 6 rhos (mix of CD pass-1 pass and fail)
    p2_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
    for k, r in rho_arch.items():
        if r['triggered']:
            band = 'low' if k[2] <= 400 else 'mid'
            p2_strata.setdefault((k[1], band), []).append(k)
    g3_jobs = []
    for rho in ar.RHOS:
        all_r = sorted(p2_strata[(rho, 'low')] + p2_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
        fails = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) > 0]
        passes = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) == 0]
        picks = [fails[0], fails[len(fails) // 2], passes[0]] + ([passes[-1]] if rho in (200, 300) else [])
        for k in picks:
            cd_arch = rho_arch[k]['arms']['CD']
            g3_jobs.append(dict(
                key=list(k),
                CD=dict(errors=int(cd_arch['errors']), decoded_sha=cd_arch['decoded_sha']),
            ))
    g3_jobs = g3_jobs[:20]

    # G4 stratified samples (4 per stratum = 2 U + 2 G at 25%/75% SNR quantiles for BOTH Part 1 and Part 2)
    g4_p1_picks = _select_balanced_keys(p1_strata, per_stratum=4)  # 4 rhos * 2 bands * 4 = 32 keys
    g4_p2_picks = _select_balanced_keys(p2_strata, per_stratum=4)  # 6 rhos * 2 bands * 4 = 48 keys
    g4_p2_jobs = [
        [s, r, snr, f, band, dict(
            errors=int(rho_arch[(s, r, snr, f)]['arms']['CD']['errors']),
            decoded_sha=rho_arch[(s, r, snr, f)]['arms']['CD']['decoded_sha'],
        )]
        for s, r, snr, f, band in g4_p2_picks
    ]

    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'sameframe_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        print('Running G1 (20 stageA F0 replay keys)...', flush=True)
        g1_rows = _spawn_map(_g1_worker, g1_jobs, args.workers, ipc_dir, 'g1')
        print(f'G1 PASS ({len(g1_rows)}/20)', flush=True)

        print('Running G2 (5 archived huang HG parity keys)...', flush=True)
        g2_rows = _spawn_map(_g2_worker, g2_jobs, min(5, args.workers), ipc_dir, 'g2')
        print(f'G2 PASS ({len(g2_rows)}/5)', flush=True)

        print('Running G3 (20 CD2 pass-1 parity + CD2/CD2e8 smoke keys)...', flush=True)
        g3_rows = _spawn_map(_g3_worker, g3_jobs, args.workers, ipc_dir, 'g3')
        g3_cd2_p2 = sum(1 for x in g3_rows if x['cd2_passes'] == 2)
        g3_cd2_p1 = sum(1 for x in g3_rows if x['cd2_passes'] == 1)
        g3_e8_p2 = sum(1 for x in g3_rows if x['cd2e8_passes'] == 2)
        if not (g3_cd2_p1 > 0 and g3_cd2_p2 > 0 and g3_e8_p2 > 0):
            raise AssertionError(
                f'G3 did not exercise both pass-1 and pass-2 paths: '
                f'cd2_p1={g3_cd2_p1}, cd2_p2={g3_cd2_p2}, cd2e8_p2={g3_e8_p2}'
            )
        print(f'G3 PASS ({len(g3_rows)}/20; cd2_p1={g3_cd2_p1}, cd2_p2={g3_cd2_p2}, cd2e8_p2={g3_e8_p2})', flush=True)

        print(f'Running G4 cost projection ({len(g4_p1_picks)} Part-1 + {len(g4_p2_jobs)} Part-2 keys)...', flush=True)
        g4_p1_rows = _spawn_map(_g4_part1_worker, [list(x) for x in g4_p1_picks], args.workers, ipc_dir, 'g4p1')
        g4_p2_rows = _spawn_map(_g4_part2_worker, g4_p2_jobs, args.workers, ipc_dir, 'g4p2')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    # Compute stratified cost projections
    p1_counts = {k: len(v) for k, v in p1_strata.items()}
    p2_counts = {k: len(v) for k, v in p2_strata.items()}

    def project(part1_rhos: tuple[int, ...], include_hgint: bool) -> dict[str, Any]:
        p1_sec = 0.0
        p1_detail = {}
        for rho in part1_rhos:
            for band in ('low', 'mid'):
                sub = [x for x in g4_p1_rows if x['rho'] == rho and x['band'] == band]
                mean_cpu = float(np.mean([
                    x['f0_cpu'] + x['hg_cpu'] + (x['hgint_cpu'] if include_hgint else 0.0)
                    for x in sub
                ]))
                cnt = p1_counts[(rho, band)]
                p1_sec += mean_cpu * cnt
                p1_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
        p2_sec = 0.0
        p2_detail = {}
        for rho in ar.RHOS:
            for band in ('low', 'mid'):
                sub = [x for x in g4_p2_rows if x['rho'] == rho and x['band'] == band]
                mean_cpu = float(np.mean([x['f0_cpu'] + x['cd2_cpu'] + x['cd2e8_cpu'] for x in sub]))
                cnt = p2_counts[(rho, band)]
                p2_sec += mean_cpu * cnt
                p2_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
        raw_h = p1_sec / 3600.0 + p2_sec / 3600.0 + OVERHEAD_HOURS
        marg_h = raw_h * COST_MARGIN
        return dict(
            part1_rhos=list(part1_rhos),
            include_hgint=include_hgint,
            part1_raw_hours=p1_sec / 3600.0,
            part2_raw_hours=p2_sec / 3600.0,
            overhead_hours=OVERHEAD_HOURS,
            raw_total_hours=raw_h,
            projected_hours_with_margin=marg_h,
            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
            part1_strata=p1_detail,
            part2_strata=p2_detail,
        )

    candidates = [
        project(PART1_RHOS, True),
    ]
    selected = candidates[0] if candidates[0]['within_budget'] else None
    gate_cpu_h = _used_cpu_seconds() / 3600.0
    all_passed = bool(
        len(g1_rows) == 20 and len(g2_rows) == 5 and len(g3_rows) == 20
        and g3_cd2_p1 > 0 and g3_cd2_p2 > 0 and g3_e8_p2 > 0
        and selected is not None
    )

    payload = dict(
        _argv=sys.argv,
        _config=dict(
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
            own_md5=own_md5(),
            frozen_extra_md5=helpers['extra_md5'],
            p1_source_md5=ar.frozen_p1_md5(ctx),
            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
            archive_shards_verified={k: len(v) for k, v in manifests.items()},
        ),
        all_passed=all_passed,
        selected=None if selected is None else dict(
            part1_rhos=selected['part1_rhos'],
            include_hgint=selected['include_hgint'],
            projected_hours_with_margin=selected['projected_hours_with_margin'],
            raw_total_hours=selected['raw_total_hours'],
        ),
        G1=dict(passed=len(g1_rows) == 20, keys_checked=len(g1_rows), rows=g1_rows),
        G2=dict(passed=len(g2_rows) == 5, keys_checked=len(g2_rows), rows=g2_rows),
        G3=dict(passed=len(g3_rows) == 20, keys_checked=len(g3_rows), rows=g3_rows),
        G4=dict(
            passed=selected is not None,
            budget_cap_core_hours=BUDGET_CAP_HOURS,
            margin=COST_MARGIN,
            overhead_hours=OVERHEAD_HOURS,
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


def _write_gzip_jsonl_atomic(final_path: Path, lines: list[str]):
    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
    with part_path.open('wb') as raw_fh:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
            for ln in lines:
                gz.write(ln.encode('utf-8'))
        raw_fh.flush()
        os.fsync(raw_fh.fileno())
    os.replace(part_path, final_path)


def _part1_shard_worker(
    shard_idx: int,
    frames: tuple[int, ...],
    trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]],
    include_hgint: bool,
    raw_dir: Path,
):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    final_path = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
    out_lines: list[str] = []
    for frame in frames:
        items = trig_by_frame.get(frame, [])
        grouped: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
        for s, rho, snr, exp_syn, exp_f0_err in items:
            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err))
        for (s, rho), grp in sorted(grouped.items()):
            base = stage3.inputs(ctx, frame, s, rho)
            for snr, exp_syn, exp_f0_err in sorted(grp):
                _, obs, truth = stage3.observed(ctx, base, rho, snr)
                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
                if int(syn) != exp_syn or f0_err != exp_f0_err:
                    raise RuntimeError(
                        f'Part1 F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
                    )
                hg_out = ar.run_hg_arm(
                    ctx, helpers, obs, arrays, truth,
                    ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
                    max_passes=2, record_match=False,
                )
                arms_rec = dict(
                    HG=dict(
                        errors=hg_out['HG']['errors'],
                        decoded_sha=hg_out['HG']['decoded_sha'],
                        syndrome=hg_out['HG']['syndrome'],
                        passes_used=hg_out['HG']['passes_used'],
                    ),
                    HG1=dict(
                        errors=hg_out['HG1']['errors'],
                        decoded_sha=hg_out['HG1']['decoded_sha'],
                        syndrome=hg_out['HG1']['syndrome'],
                    ),
                )
                if include_hgint:
                    hgint_out = ar.run_hg_arm(
                        ctx, helpers, obs, arrays, truth,
                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
                        max_passes=2, record_match=False,
                    )
                    arms_rec['HGint'] = dict(
                        errors=hgint_out['HG']['errors'],
                        decoded_sha=hgint_out['HG']['decoded_sha'],
                        syndrome=hgint_out['HG']['syndrome'],
                        passes_used=hgint_out['HG']['passes_used'],
                    )
                out_lines.append(json.dumps(dict(
                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
                ), allow_nan=False) + '\n')
    _write_gzip_jsonl_atomic(final_path, out_lines)
    print(f'Part1 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)


def _part2_shard_worker(
    shard_idx: int,
    frames: tuple[int, ...],
    trig_by_frame: dict[int, list[dict[str, Any]]],
    raw_dir: Path,
):
    C, _, _, helpers = load_stage_runtime()
    stage3, ctx = C['stage3'], C['ctx']
    final_path = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
    out_lines: list[str] = []
    for frame in frames:
        items = trig_by_frame.get(frame, [])
        grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
        for item in items:
            grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
        for (s, rho), grp in sorted(grouped.items()):
            base = stage3.inputs(ctx, frame, s, rho)
            for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
                snr = int(item['snr_centi_db'])
                raw, obs, truth = stage3.observed(ctx, base, rho, snr)
                if stage3.input_record(raw, obs) != item['inputs']:
                    raise RuntimeError(f'Part2 input mismatch at {(s, rho, snr, frame)}')
                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
                f0 = stage3.decoded(ctx, dec, truth)
                if int(syn) != int(item['syndrome']) or f0 != dict(
                    errors=int(item['arms']['F0']['errors']),
                    decoded_sha=item['arms']['F0']['decoded_sha'],
                ):
                    raise RuntimeError(f'Part2 F0 drift at {(s, rho, snr, frame)}')
                arch_cd = dict(
                    errors=int(item['arms']['CD']['errors']),
                    decoded_sha=item['arms']['CD']['decoded_sha'],
                )
                cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
                cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
                out_lines.append(json.dumps(dict(
                    scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=int(syn),
                    arms=dict(CD2=cd2, CD2e8=cd2e8),
                ), allow_nan=False) + '\n')
    _write_gzip_jsonl_atomic(final_path, out_lines)
    print(f'Part2 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)


def _run_sharded_phase(target_fn, job_args: list[tuple[Any, ...]], max_workers: int, cpu_cap_sec: float):
    """Run up to max_workers spawned processes concurrently with live CPU budget check."""
    mp_ctx = multiprocessing.get_context('spawn')
    pending = list(job_args)
    running = {}
    budget_hit = False
    try:
        while pending or running:
            while pending and len(running) < max_workers:
                args = pending.pop(0)
                proc = mp_ctx.Process(target=target_fn, args=args)
                proc.start()
                running[proc.sentinel] = (args[0], proc)
            ready = wait(running, timeout=10.0)
            for r in ready:
                idx, proc = running.pop(r)
                proc.join()
                code = proc.exitcode
                proc.close()
                if code != 0:
                    raise RuntimeError(f'Worker shard {idx:03d} failed with exit code {code}')
            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= cpu_cap_sec:
                budget_hit = True
                break
    finally:
        for _, proc in running.values():
            proc.terminate()
        for _, proc in running.values():
            proc.join()
            proc.close()
    if budget_hit or _used_cpu_seconds() >= cpu_cap_sec:
        print(f'STOPPED_BUDGET: CPU limit reached ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)


# --------------------------------------------------------------------------- Analysis (P1 & P2)
def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
    """Wrap stageA2.crossing into conservative (lo, hi) bounds so censored draws never silently yield NaN."""
    c = float(crossing_fn(fer, snrs))
    if math.isfinite(c):
        return c, c
    if c < 0:
        return -math.inf, float(snrs[0]) / 100.0
    return float(snrs[-1]) / 100.0, math.inf


def p1_verdict(ci_lo: float, ci_hi: float) -> str:
    if ci_lo >= P1_THRESHOLD_DB:
        return 'DOPPLER-LINE'
    if ci_hi < P1_THRESHOLD_DB:
        return 'WRITE-A'
    return 'INCONCLUSIVE'


def p2_verdict(ci_lo: float, ci_hi: float) -> str:
    if ci_lo > P2_THRESHOLD_DB:
        return 'STILL_BEHIND'
    if ci_hi < P2_THRESHOLD_DB:
        return 'CATCHES_UP'
    return 'MIXED'


def _rep(v: float) -> Any:
    if math.isinf(v):
        return '+inf' if v > 0 else '-inf'
    if math.isnan(v):
        raise FloatingPointError('NaN encountered in readout')
    return float(v)


def analyze_part1(
    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
    part1_rhos: tuple[int, ...],
    include_hgint: bool,
    crossing_fn,
    *,
    boot_draws: int = PART1_BOOT_DRAWS,
    boot_seed: int = PART1_BOOT_SEED,
) -> dict[str, Any]:
    """Paired physical-frame bootstrap analysis for P1 (frames 41000-41399).

    fail_by_arm[arm] = (rhos_tuple, snrs_tuple, fail_bool_array[n_frames, 2, n_rhos, n_snrs]).
    """
    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
    rng = np.random.default_rng(boot_seed)
    # Draw exact multinomial weights once, shared across ALL arms (stageA, stageA2, stageA3, new)
    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
    weights[0] = 1.0 / n_frames
    for b in range(1, boot_draws + 1):
        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames

    # Compute U/G mean crossing bounds [boot_draws+1, n_rhos] for every arm
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
        # fer[draw, scen, rho, snr]
        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
        scen_pt = {'U': {}, 'G': {}}
        for ri, rho in enumerate(rhos):
            for bi in range(boot_draws + 1):
                u_lo, u_hi = crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
                g_lo, g_hi = crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
                if bi == 0:
                    scen_pt['U'][str(rho)] = _rep(u_lo) if u_lo == u_hi else [_rep(u_lo), _rep(u_hi)]
                    scen_pt['G'][str(rho)] = _rep(g_lo) if g_lo == g_hi else [_rep(g_lo), _rep(g_hi)]
        arm_lo[arm] = lo_arr
        arm_hi[arm] = hi_arr
        arm_scen_pt[arm] = scen_pt
        arm_mean_pt[arm] = {
            str(rho): (_rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [_rep(lo_arr[0, ri]), _rep(hi_arr[0, ri])])
            for ri, rho in enumerate(rhos)
        }
        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; full/ldop/delay over 100..200; base over all
        if arm in ('delay', 'full', 'ldop'):
            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
        else:
            sub_idx = list(range(n_r))
        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
        best_pos = int(np.argmin(hi_arr[0, sub_idx]))
        arm_best_rho[arm] = int(rhos[sub_idx[best_pos]])

    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
        # D = min_rho arm_a - min_rho arm_b (conservative bounds; collapses to exact diff when finite)
        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
        if cens_frac == 0.0:
            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
        else:
            lo = an._nearest_rank(d_lo[1:], 0.025)
            hi = an._nearest_rank(d_hi[1:], 0.975)
        pt = _rep(d_lo[0]) if d_lo[0] == d_hi[0] else [_rep(d_lo[0]), _rep(d_hi[0])]
        return dict(
            point_db=pt,
            ci95_db=[_rep(lo), _rep(hi)],
            censored_draw_fraction=cens_frac,
            arm_a_best_db=_rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [_rep(arm_best_lo[arm_a][0]), _rep(arm_best_hi[arm_a][0])],
            arm_a_best_rho=arm_best_rho[arm_a],
            arm_b_best_db=_rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [_rep(arm_best_lo[arm_b][0]), _rep(arm_best_hi[arm_b][0])],
            arm_b_best_rho=arm_best_rho[arm_b],
        )

    primary_p1 = contrast('HG', 's100')
    p1_lo = float(primary_p1['ci95_db'][0]) if isinstance(primary_p1['ci95_db'][0], float) else (-math.inf if primary_p1['ci95_db'][0] == '-inf' else math.inf)
    p1_hi = float(primary_p1['ci95_db'][1]) if isinstance(primary_p1['ci95_db'][1], float) else (-math.inf if primary_p1['ci95_db'][1] == '-inf' else math.inf)
    primary_p1['verdict'] = p1_verdict(p1_lo, p1_hi)

    sec_contrasts = {}
    for comp in ('s050', 'ldop', 'full', 'delay', 'base'):
        if comp in fail_by_arm:
            sec_contrasts[f'HG_minus_{comp}'] = contrast('HG', comp)
    sec_contrasts['HG1_minus_s100'] = contrast('HG1', 's100')
    if include_hgint and 'HGint' in fail_by_arm:
        for comp in ('s100', 's050', 'ldop', 'full', 'HG'):
            if comp in fail_by_arm:
                sec_contrasts[f'HGint_minus_{comp}'] = contrast('HGint', comp)

    return dict(
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        part1_rhos=list(part1_rhos),
        include_hgint=include_hgint,
        primary_P1=primary_p1,
        secondary_contrasts=sec_contrasts,
        mean_crossing=arm_mean_pt,
        crossings_by_scenario=arm_scen_pt,
        best_rho=arm_best_rho,
    )


def analyze_part2(
    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
    arms: tuple[str, ...],
    *,
    boot_draws: int = an.BOOT_DRAWS,
    boot_seed: int = an.BOOT_SEED,
) -> dict[str, Any]:
    """Reuse hs_analysis crossing & 36-pair simultaneous projection for P2 (frames 5400-5799)."""
    rhos = ar.RHOS
    snrs = ar.SNRS
    frames = ar.MAIN_FRAMES
    errors_by_key = {k: {a: int(r['arms'][a]['errors']) for a in arms} for k, r in full_rows.items()}
    crossings, cells = an.compute_crossings(
        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
    )
    pooled = an.scene_means(crossings, rhos, arms)

    def eval_p2(arm_a: str, arm_b: str) -> dict[str, Any]:
        c98 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.PRIMARY_ALPHA)
        c95 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.FAMILY_ALPHA)
        _, _, lo98, hi98 = c98['_raw']
        _, _, lo95, hi95 = c95['_raw']
        return dict(
            point_db=c98['point_db'],
            ci9833_projected_db=c98['ci_projected_db'],
            ci9833_per_draw_db=c98['ci_per_draw_db'],
            ci95_projected_db=c95['ci_projected_db'],
            ci95_per_draw_db=c95['ci_per_draw_db'],
            censored_draw_fraction=c98['censored_draw_fraction'],
            verdict=p2_verdict(lo98, hi98),
            verdict_at_95_descriptive=p2_verdict(lo95, hi95),
        )

    p2_E = eval_p2('CD2', 'HG')
    p2_E8 = eval_p2('CD2e8', 'HG')

    # Per-scenario P2
    by_scen = {}
    for s in ar.SCENARIOS:
        s_curves = {(r, a): crossings[s, r, a] for r in rhos for a in arms}
        by_scen[s] = {}
        for label, arm_a in (('E_CD2_minus_HG', 'CD2'), ('E8_CD2e8_minus_HG', 'CD2e8')):
            c98 = an.projected_best_diff(s_curves, arm_a, 'HG', rhos, an.PRIMARY_ALPHA)
            _, _, lo98, hi98 = c98['_raw']
            by_scen[s][label] = dict(
                point_db=c98['point_db'],
                ci9833_projected_db=c98['ci_projected_db'],
                verdict=p2_verdict(lo98, hi98),
            )

    # Secondary contrasts (95% projected CI)
    sec = {}
    for name, a1, a2 in (
        ('CD2_minus_CD', 'CD2', 'CD'),
        ('CD2e8_minus_CD', 'CD2e8', 'CD'),
        ('CD2e8_minus_CD2', 'CD2e8', 'CD2'),
        ('CD2_minus_HGint', 'CD2', 'HGint'),
        ('CD2e8_minus_HGint', 'CD2e8', 'HGint'),
    ):
        if a1 in arms and a2 in arms:
            c = an.projected_best_diff(pooled, a1, a2, rhos, an.FAMILY_ALPHA)
            sec[name] = {k: v for k, v in c.items() if k != '_raw'}

    # Scene-averaged crossing table
    pooled_table = {}
    best_rho = {}
    for a in arms:
        pooled_table[a] = {}
        best_val = math.inf
        best_r = rhos[0]
        for r in rhos:
            b = pooled[r, a]
            lo95, hi95 = an._interval(b, 0.05)
            pt_lo, pt_hi = float(b.lower[0]), float(b.upper[0])
            pooled_table[a][str(r)] = dict(
                point_db=[_rep(pt_lo), _rep(pt_hi)],
                ci95_db=[_rep(lo95), _rep(hi95)],
            )
            if pt_hi < best_val:
                best_val = pt_hi
                best_r = r
        best_rho[a] = int(best_r)

    # Diagnostics on triggered keys
    trig_rows = [r for r in full_rows.values() if r['triggered']]
    diag = {}
    for arm in ('CD2', 'CD2e8'):
        p1_stop = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 1)
        p2_ran = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 2)
        p2_rescued = sum(
            1 for r in trig_rows
            if r['arms'][arm]['passes_used'] == 2 and r['arms'][arm]['pass1_errors'] > 0 and r['arms'][arm]['errors'] == 0
        )
        vs_hg = dict(
            arm_only=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] > 0),
            hg_only=sum(1 for r in trig_rows if r['arms']['HG']['errors'] == 0 and r['arms'][arm]['errors'] > 0),
            both=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] == 0),
            neither=sum(1 for r in trig_rows if r['arms'][arm]['errors'] > 0 and r['arms']['HG']['errors'] > 0),
        )
        diag[arm] = dict(
            triggered=len(trig_rows),
            pass1_early_stop=p1_stop,
            pass2_ran=p2_ran,
            pass2_rescued=p2_rescued,
            mean_pass1_edits=float(np.mean([r['arms'][arm]['pass1_edits'] for r in trig_rows])),
            mean_pass2_edits_when_ran=float(np.mean([r['arms'][arm]['pass2_edits'] for r in trig_rows if r['arms'][arm]['passes_used'] == 2])) if p2_ran else 0.0,
            paired_vs_hg=vs_hg,
        )

    return dict(
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary_alpha=an.PRIMARY_ALPHA,
        E_CD2_minus_HG=p2_E,
        E8_CD2e8_minus_HG=p2_E8,
        by_scenario=by_scen,
        secondary_contrasts_95=sec,
        pooled_crossings=pooled_table,
        best_rho=best_rho,
        diagnostics=diag,
        cells=cells,
    )


def render_results_md(res: dict[str, Any]) -> str:
    p1 = res['part1']
    p2 = res['part2']
    q1 = p1['primary_P1']
    e1 = p2['E_CD2_minus_HG']
    e8 = p2['E8_CD2e8_minus_HG']

    def fval(x):
        if isinstance(x, list):
            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
        return x if isinstance(x, str) else f'{x:.4f}'

    r1_span = f'{min(p1["part1_rhos"])}..{max(p1["part1_rhos"])}'
    lines = [
        '# Same-Frame Decisive Check Results (`sameframe_hg_20261124`)',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- Cumulative CPU: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap {res["runtime"]["cpu_cap_core_hours"]:.1f} h; wall {res["runtime"]["total_wall_seconds"]:.1f} s)',
        '',
        '## Primary Verdicts (Pre-Registered)',
        '',
        '| Test | Contrast | Point (dB) | Primary CI (dB) | Verdict |',
        '|---|---|---:|---|---|',
        f'| **P1** (95% paired) | `min HG ({r1_span}) − min s100 (100..200)` | {fval(q1["point_db"])} | [{fval(q1["ci95_db"][0])}, {fval(q1["ci95_db"][1])}] | **{q1["verdict"]}** |',
        f'| **P2-E** (98.33% 36-pair proj) | `min CD2 − min HG` | {fval(e1["point_db"])} | [{fval(e1["ci9833_projected_db"][0])}, {fval(e1["ci9833_projected_db"][1])}] (95%: [{fval(e1["ci95_projected_db"][0])}, {fval(e1["ci95_projected_db"][1])}]) | **{e1["verdict"]}** |',
        f'| **P2-E8** (98.33% 36-pair proj) | `min CD2e8 − min HG` | {fval(e8["point_db"])} | [{fval(e8["ci9833_projected_db"][0])}, {fval(e8["ci9833_projected_db"][1])}] (95%: [{fval(e8["ci95_projected_db"][0])}, {fval(e8["ci95_projected_db"][1])}]) | **{e8["verdict"]}** |',
        '',
        '## Part 1: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
        '',
    ]
    p1_arms = [a for a in ('base', 'delay', 'HG', 'HG1', 'HGint', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in p1['mean_crossing']]
    all_p1_rhos = ('50', '100', '150', '200', '250', '300')
    lines.append('| Arm | ' + ' | '.join(f'ρ={int(r)/1000:.2f}' for r in all_p1_rhos) + ' | Best ρ |')
    lines.append('|---|' + '---:|' * len(all_p1_rhos) + '---:|')
    for a in p1_arms:
        row_cells = [fval(p1['mean_crossing'][a][r]) if r in p1['mean_crossing'][a] else '—' for r in all_p1_rhos]
        lines.append(f'| {a} | ' + ' | '.join(row_cells) + f' | {p1["best_rho"][a]/1000:.2f} |')
    lines += ['', '### Part 1 Secondary Contrasts (95% Paired Frame Bootstrap, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
    for name, c in p1['secondary_contrasts'].items():
        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')

    lines += ['', '## Part 2: 1% FER Crossings on Huang Frames (5400–5799, U/G Mean, dB)', '']
    p2_arms = [a for a in ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z') if a in p2['pooled_crossings']]
    lines.append('| ρ | ' + ' | '.join(p2_arms) + ' |')
    lines.append('|---:|' + '---|' * len(p2_arms))
    for r in ar.RHOS:
        cells_str = []
        for a in p2_arms:
            d = p2['pooled_crossings'][a][str(r)]
            cells_str.append(f'{fval(d["point_db"])} [{fval(d["ci95_db"][0])}, {fval(d["ci95_db"][1])}]')
        lines.append(f'| {r/1000:.2f} | ' + ' | '.join(cells_str) + ' |')

    lines += ['', '### Part 2 Diagnostics & Secondary Contrasts', '']
    for arm in ('CD2', 'CD2e8'):
        d = p2['diagnostics'][arm]
        v = d['paired_vs_hg']
        lines.append(
            f'- `{arm}`: pass-1 stop {d["pass1_early_stop"]}/{d["triggered"]}, '
            f'pass-2 ran {d["pass2_ran"]} (rescued {d["pass2_rescued"]}), '
            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}; '
            f'vs HG: {arm}_only={v["arm_only"]}, HG_only={v["hg_only"]}, both={v["both"]}, neither={v["neither"]}'
        )
    lines += ['', '| Contrast | Point (dB) | 95% Projected CI (dB) |', '|---|---:|---|']
    for name, c in p2['secondary_contrasts_95'].items():
        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci_projected_db"][0])}, {fval(c["ci_projected_db"][1])}] |')
    return '\n'.join(lines) + '\n'


def _do_read(
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

    sel = gate['selected']
    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
    include_hgint = bool(sel['include_hgint'])
    raw_dir = out_dir / 'raw'

    # Verify all manifests and our own raw shard MD5s
    for name in ARCHIVE_MANIFESTS:
        verify_manifest(name)
    for fname, expected in raw_md5.items():
        actual = ar.md5_file(raw_dir / fname)
        if actual != expected:
            raise RuntimeError(f'Raw shard MD5 mismatch {fname}: {actual} != {expected}')

    # --- Load Part 1 arrays (archived stageA/A2/A3 + new Part 1) ---
    fa, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)
    fa2, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
    fa3, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)

    stageA_base = load_stageA_base(part1_rhos)
    new_p1_arms = ('HG', 'HG1') + (('HGint',) if include_hgint else ())
    fi = {f: i for i, f in enumerate(PART1_FRAMES)}
    p1_fail = {a: np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool) for a in new_p1_arms}
    p1_seen = np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool)

    # Fill untriggered keys from stageA_base
    for (s, rho, snr, f), b in stageA_base.items():
        if b['syndrome'] == 0:
            ix = (fi[f], ar.SCENARIOS.index(s), part1_rhos.index(rho), PART1_SNRS.index(snr))
            err_flag = b['f0_errors'] > 0
            for a in new_p1_arms:
                p1_fail[a][ix] = err_flag
            p1_seen[ix] = True

    # Fill triggered keys from new Part-1 shards
    p1_trig_seen = 0
    for shard_idx in range(N_SHARDS):
        sp = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), part1_rhos.index(int(r['rho'])), PART1_SNRS.index(int(r['snr'])))
                if p1_seen[ix]:
                    raise RuntimeError(f'Duplicate Part1 key {r}')
                for a in new_p1_arms:
                    p1_fail[a][ix] = int(r['arms'][a]['errors']) > 0
                p1_seen[ix] = True
                p1_trig_seen += 1
    if not p1_seen.all():
        raise RuntimeError(f'Incomplete Part1 grid: missing {int((~p1_seen).sum())} keys')

    fail_by_arm = {
        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
    }
    for i, a in enumerate(stageA3.ARMS):
        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
    for a in new_p1_arms:
        fail_by_arm[a] = (part1_rhos, PART1_SNRS, p1_fail[a])

    print(f'Analyzing Part 1 ({int(p1_seen.sum())} keys, {p1_trig_seen} triggered)...', flush=True)
    part1_out = analyze_part1(fail_by_arm, part1_rhos, include_hgint, stageA2.crossing)

    # --- Load Part 2 rows (archived rho_sweep + huang_steelman + new CD2/CD2e8) ---
    rho_arch, _ = ar.load_archived_rho_sweep()
    huang_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
        with p.open('r', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                huang_trig[ar.row_key(r)] = r

    new_p2_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for shard_idx in range(N_SHARDS):
        sp = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                k = ar.row_key(r)
                if k in new_p2_trig:
                    raise RuntimeError(f'Duplicate Part2 key {k}')
                new_p2_trig[k] = r
    if len(new_p2_trig) != ar.EXPECTED_TOTAL_TRIGGERS or len(huang_trig) != ar.EXPECTED_TOTAL_TRIGGERS:
        raise RuntimeError(f'Part2 trigger count mismatch: new={len(new_p2_trig)}, huang={len(huang_trig)}')

    p2_arms = ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z')
    full_p2: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for k, arch in rho_arch.items():
        if arch['triggered']:
            hr = huang_trig[k]['arms']
            nr = new_p2_trig[k]['arms']
            full_p2[k] = dict(
                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
                triggered=True,
                arms=dict(
                    F0=hr['F0'], CD=hr['CD'], HG=hr['HG'], HG1=hr['HG1'], HGint=hr['HGint'], Z=hr['Z'],
                    CD2=nr['CD2'], CD2e8=nr['CD2e8'],
                ),
            )
        else:
            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
            full_p2[k] = dict(
                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
                triggered=False,
                arms={a: f0 for a in p2_arms},
            )

    print(f'Analyzing Part 2 ({len(full_p2)} keys, {len(new_p2_trig)} triggered)...', flush=True)
    part2_out = analyze_part2(full_p2, p2_arms)

    if enforce_cpu_cap:
        final_cpu = _used_cpu_seconds()
        if final_cpu >= BUDGET_CAP_SEC:
            print(f'STOPPED_BUDGET after analysis ({final_cpu/3600:.3f} core-hours)', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        runtime_info = dict(
            runtime_info,
            analysis_cpu_hours=max(0.0, final_cpu / 3600.0 - runtime_info.get('workers_core_hours', 0.0)),
            total_core_hours=final_cpu / 3600.0,
            total_wall_seconds=(time.monotonic() - wall_start) if wall_start is not None else runtime_info['total_wall_seconds'],
        )

    results = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=freeze_commit,
            python_executable=sys.executable,
            own_md5=own_md5(),
            gate_md5=gate_md5,
            part1_rhos=list(part1_rhos),
            include_hgint=include_hgint,
            part1_frames=[PART1_FRAMES[0], PART1_FRAMES[-1]],
            part1_triggered_keys=p1_trig_seen,
            part2_frames=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
            part2_triggered_keys=len(new_p2_trig),
            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G1_keys=gate['G1']['keys_checked'],
            G2_keys=gate['G2']['keys_checked'],
            G3_keys=gate['G3']['keys_checked'],
            G4_projected_hours=sel['projected_hours_with_margin'],
        ),
        runtime=runtime_info,
        part1=part1_out,
        part2=part2_out,
    )
    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    print(
        f'DONE P1={part1_out["primary_P1"]["verdict"]} '
        f'P2_CD2={part2_out["E_CD2_minus_HG"]["verdict"]} '
        f'P2_CD2e8={part2_out["E8_CD2e8_minus_HG"]["verdict"]}',
        flush=True,
    )


def cmd_run(args):
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
    if list(raw_dir.glob('part*_shard*.jsonl*')):
        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')

    gate_bytes = (out_dir / 'gate.json').read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to run without passing gate.json')
    live_own = own_md5()
    verify_freeze_commit_if_git(args.freeze_commit, live_own)
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')

    sel = gate['selected']
    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
    include_hgint = bool(sel['include_hgint'])

    wall_start = time.monotonic()
    for name in ARCHIVE_MANIFESTS:
        verify_manifest(name)
    C, _, _, helpers = load_stage_runtime()
    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
        raise RuntimeError('p1_source_md5 mismatch vs gate.json')

    # --- Part 1 ---
    stageA_base = load_stageA_base(part1_rhos)
    p1_trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]] = {}
    p1_n_trig = 0
    for (s, rho, snr, f), b in stageA_base.items():
        if b['syndrome'] != 0:
            p1_trig_by_frame.setdefault(f, []).append((s, rho, snr, b['syndrome'], b['f0_errors']))
            p1_n_trig += 1
    p1_jobs = [
        (idx, tuple(PART1_FRAMES[idx::N_SHARDS]), {f: p1_trig_by_frame.get(f, []) for f in PART1_FRAMES[idx::N_SHARDS]}, include_hgint, raw_dir)
        for idx in range(N_SHARDS)
    ]
    print(f'Launching Part 1: {p1_n_trig} triggered keys on {args.workers} workers (rhos={part1_rhos}, hgint={include_hgint})...', flush=True)
    t_p1 = time.monotonic()
    _run_sharded_phase(_part1_shard_worker, p1_jobs, args.workers, BUDGET_CAP_SEC)
    p1_wall = time.monotonic() - t_p1
    p1_cpu = _used_cpu_seconds()
    print(f'Part 1 complete: wall={p1_wall:.1f}s, cumulative_cpu={p1_cpu/3600:.4f}h', flush=True)

    # --- Part 2 ---
    rho_arch, _ = ar.load_archived_rho_sweep()
    p2_trig_by_frame: dict[int, list[dict[str, Any]]] = {}
    p2_n_trig = 0
    for k, r in rho_arch.items():
        if r['triggered']:
            p2_trig_by_frame.setdefault(k[3], []).append(r)
            p2_n_trig += 1
    p2_jobs = [
        (idx, tuple(ar.MAIN_FRAMES[idx::N_SHARDS]), {f: p2_trig_by_frame.get(f, []) for f in ar.MAIN_FRAMES[idx::N_SHARDS]}, raw_dir)
        for idx in range(N_SHARDS)
    ]
    print(f'Launching Part 2: {p2_n_trig} triggered keys on {args.workers} workers (CD2 + CD2e8)...', flush=True)
    t_p2 = time.monotonic()
    _run_sharded_phase(_part2_shard_worker, p2_jobs, args.workers, BUDGET_CAP_SEC)
    p2_wall = time.monotonic() - t_p2
    total_cpu = _used_cpu_seconds()
    print(f'Part 2 complete: wall={p2_wall:.1f}s, cumulative_cpu={total_cpu/3600:.4f}h', flush=True)

    raw_md5 = {}
    for prefix in ('part1', 'part2'):
        for idx in range(N_SHARDS):
            p = raw_dir / f'{prefix}_shard{idx:03d}.jsonl.gz'
            raw_md5[p.name] = ar.md5_file(p)
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
    )

    runtime_info = dict(
        part1_wall_seconds=p1_wall,
        part1_cpu_hours=p1_cpu / 3600.0,
        part2_wall_seconds=p2_wall,
        part2_cpu_hours=(total_cpu - p1_cpu) / 3600.0,
        workers_core_hours=total_cpu / 3600.0,
        total_wall_seconds=time.monotonic() - wall_start,
        total_core_hours=total_cpu / 3600.0,
        cpu_cap_core_hours=BUDGET_CAP_HOURS,
    )
    _do_read(
        out_dir, gate, gate_md5, args.freeze_commit, runtime_info, raw_md5,
        enforce_cpu_cap=True, wall_start=wall_start,
    )


def cmd_read(args):
    out_dir = args.out.resolve()
    gate_bytes = (out_dir / 'gate.json').read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    raw_md5 = {}
    for line in (out_dir / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8').splitlines():
        if line.strip():
            d, n = line.split()
            raw_md5[n] = d
    prev = json.loads((out_dir / 'results.json').read_text(encoding='utf-8')) if (out_dir / 'results.json').is_file() else {}
    runtime_info = prev.get('runtime', dict(total_core_hours=0.0, total_wall_seconds=0.0, cpu_cap_core_hours=BUDGET_CAP_HOURS))
    _do_read(out_dir, gate, gate_md5, args.freeze_commit, runtime_info, raw_md5)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    g = sub.add_parser('gate')
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--workers', type=int, default=16)

    r = sub.add_parser('run')
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--freeze-commit', required=True)
    r.add_argument('--workers', type=int, default=WORKERS)

    rd = sub.add_parser('read')
    rd.add_argument('--out', type=Path, required=True)
    rd.add_argument('--freeze-commit', required=True)

    args = ap.parse_args()
    dict(gate=cmd_gate, run=cmd_run, read=cmd_read)[args.mode](args)


if __name__ == '__main__':
    main()
