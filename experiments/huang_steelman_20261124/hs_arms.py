"""Receiver arms, archive loader, and exact path matching for Huang-2010-style steelman."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
import torch

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
STAGE3 = EXPERIMENTS / 'cstate_codelay_sbl_stage3_20261118'
GAMMA0 = EXPERIMENTS / 'gamma0_exchange_20261120'
RHO_SWEEP = EXPERIMENTS / 'rho_sweep_20261119'
RHO_ARCHIVE_DIR = RHO_SWEEP / 'out' / 'main_20261119'
RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'

SCENARIOS = ('U', 'G')
RHOS = (150, 200, 250, 300, 400, 500)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
LOW_SNRS = (300, 400)
MAIN_FRAMES = tuple(range(5400, 5800))
SMOKE_FRAMES = tuple(range(5800, 5840))
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
THREADS = (
    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
)
EXPECTED_TOTAL_TRIGGERS = 18009
EXPECTED_TRIGGERS_BY_STRATUM = {
    (150, 'low'): 1462, (150, 'mid'): 2186,
    (200, 'low'): 1443, (200, 'mid'): 1174,
    (250, 'low'): 1501, (250, 'mid'): 807,
    (300, 'low'): 1569, (300, 'mid'): 791,
    (400, 'low'): 1600, (400, 'mid'): 1419,
    (500, 'low'): 1600, (500, 'mid'): 2457,
}

# Frozen dependencies verified identical between local vault and deinlab BEFORE importing.
FROZEN_EXTRA_MD5 = {
    'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9',
    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
}
OWN_SOURCE_FILES = (
    'PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'test_analysis.py',
    'gates.py', 'run_main.py', 'timing.py', 'launch_main.sh',
)
OWN_MODULE_NAMES = frozenset({
    'hs_arms', 'hs_analysis', 'test_analysis', 'gates', 'run_main', 'timing', 'hs_p1_agg',
})


def frozen_p1_md5(ctx) -> dict[str, str]:
    """Return ctx.source_md5 restricted to external/frozen modules (independent of which own scripts are imported)."""
    return {k: v for k, v in ctx.source_md5.items() if k not in OWN_MODULE_NAMES}


def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
    """When running inside a git checkout, verify freeze_commit exists and its own blobs match live_own_md5."""
    import subprocess

    repo_root = EXPERIMENTS.parent
    probe = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != 'true':
        return False
    check_commit = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'{freeze_commit}^{{commit}}'],
        capture_output=True, text=True, check=False,
    )
    if check_commit.returncode != 0:
        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repository')
    rel_dir = HERE.relative_to(Path(
        subprocess.run(
            ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    ))
    for name, expected_md5 in live_own_md5.items():
        blob = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
            capture_output=True, check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f'freeze_commit {freeze_commit} missing committed file {name}')
        got_md5 = hashlib.md5(blob.stdout).hexdigest()
        if got_md5 != expected_md5:
            raise RuntimeError(f'Live file {name} ({expected_md5}) differs from freeze_commit {freeze_commit} ({got_md5})')
    return True


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def own_md5() -> dict[str, str]:
    out = {}
    for name in OWN_SOURCE_FILES:
        p = HERE / name
        if not p.is_file():
            raise FileNotFoundError(f'Missing own experiment file: {p}')
        out[name] = md5_file(p)
    return out


def atomic_write_text(path: Path, text: str):
    """Write via temporary .part file + fsync + atomic os.replace."""
    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
    with partial.open('w', encoding='utf-8') as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def check_thread_env() -> dict[str, str]:
    bad = [k for k in THREADS if os.environ.get(k) != '1']
    if bad:
        raise RuntimeError(f'Single-thread env vars must be 1, bad={bad}')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty string for CPU-only execution')
    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}


def verify_frozen_extra_md5() -> dict[str, str]:
    extra_md5 = {}
    for rel, expected in FROZEN_EXTRA_MD5.items():
        actual = md5_file(EXPERIMENTS / rel)
        if actual != expected:
            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
        extra_md5[rel] = actual
    return extra_md5


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_context():
    """Verify frozen MD5s BEFORE importing, then load Stage 3 context + zero_variance wrapper."""
    extra_md5 = verify_frozen_extra_md5()
    if str(STAGE3) not in sys.path:
        sys.path.insert(0, str(STAGE3))
    stage3 = _load_module('hs_stage3_run', STAGE3 / 'run.py')
    ctx, full, cd, e1_checks = stage3.context()
    paired = _load_module('hs_gamma0_paired', GAMMA0 / 'paired.py')
    z_kernel = paired.zero_variance(cd)

    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
    from messages import moments
    from physical import Channel
    from twofft import time_refine

    helpers = dict(
        stage3=stage3,
        full=full,
        cd=cd,
        z_kernel=z_kernel,
        BaselineInitializer=BaselineInitializer,
        Channel=Channel,
        moments=moments,
        time_refine=time_refine,
        e1_checks=e1_checks,
        extra_md5=extra_md5,
    )
    return ctx, helpers


def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
    """Global delay-Doppler grid matching CD resolution: l in 0..l_max_cap, nu in [-3, 3] step 0.25."""
    dopplers = np.linspace(-3.0, 3.0, 25)
    delays = np.arange(l_max_cap + 1, dtype=int)
    return np.repeat(delays, len(dopplers)), np.tile(dopplers, len(delays))


def coarse_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
    """Original pilot_front integer Doppler grid: l in 0..l_max_cap, nu in {-2,-1,0,1,2}."""
    dopplers = np.arange(-2, 3, dtype=float)
    delays = np.arange(l_max_cap + 1, dtype=int)
    return np.repeat(delays, len(dopplers)), np.tile(dopplers, len(delays))


def _require_finite(arr, label: str):
    if not np.isfinite(arr).all():
        raise FloatingPointError(f'Nonfinite values encountered at stage={label}')


def omp_reacquire(
    y: np.ndarray,
    x_ref: np.ndarray,
    ls: np.ndarray,
    ks: np.ndarray,
    system: Any,
    sigma2: float,
    helpers: dict[str, Any],
    *,
    recipe: str = 'B0-p2-s0.5',
    dictionary_limit: int = 2575,
    return_phi: bool = False,
):
    """Global OMP support acquisition using the frozen BaselineInitializer and Channel.regressors."""
    _require_finite(y, 'omp.y')
    _require_finite(x_ref, 'omp.x_ref')
    n = len(y)
    Channel = helpers['Channel']
    BaselineInitializer = helpers['BaselineInitializer']
    A = Channel(n, system.c1, system.c2, ls, ks, np.ones(len(ls))).regressors(x_ref)
    _require_finite(A, 'omp.Phi')
    est = BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=dictionary_limit)
    g, ids = est(
        torch.tensor(y, dtype=torch.complex64),
        torch.tensor(A, dtype=torch.complex64),
        40,
        float(sigma2),
    )
    ids_arr = np.asarray(ids, dtype=int)
    gs = g.detach().cpu().numpy()[ids_arr].copy()
    _require_finite(gs, 'omp.gains')
    out = (ids_arr, ls[ids_arr].copy(), ks[ids_arr].copy(), gs)
    if return_phi:
        return (*out, A)
    return out


def match_paths_1to1(fit_delays, fit_dopplers, truth) -> dict[str, Any]:
    """Exact 1-to-1 matching: l_fit == l_true and |nu_fit - nu_true| <= 0.5.

    Strictly lexicographic tie-breaking:
      1. Maximize matched path count;
      2. Maximize sum of matched true-path power ranks (higher |g_p|^2 strictly preferred);
      3. Minimize total Doppler error |nu_fit - nu_true|.
    """
    fl = np.asarray(fit_delays, dtype=int)
    fk = np.asarray(fit_dopplers, dtype=float)
    tl = np.asarray(truth['l_i'], dtype=int)
    tk = np.asarray(truth['k_real'], dtype=float)
    tg2 = np.abs(np.asarray(truth['g_i'], dtype=complex)) ** 2
    total_power = float(tg2.sum())
    n_true = len(tl)
    n_fit = len(fl)
    matched_true_idx: list[int] = []

    if n_true > 0 and n_fit > 0:
        # Strict integer power rank (largest |g_p|^2 -> rank n_true, smallest -> rank 1).
        # Step of 100.0 per rank unit strictly dominates any sum of <= n_true Doppler errors <= 0.5*n_true.
        order = sorted(range(n_true), key=lambda i: (-float(tg2[i]), i))
        rank_bonus = {idx: float(n_true - pos) * 100.0 for pos, idx in enumerate(order)}
        BIG = 1e12
        cost = np.full((n_true, n_fit), BIG, dtype=float)
        for i in range(n_true):
            for j in range(n_fit):
                if tl[i] == fl[j]:
                    dk = abs(float(fk[j]) - float(tk[i]))
                    if dk <= 0.5:
                        cost[i, j] = -1e9 - rank_bonus[i] + dk
        aug = np.hstack([cost, np.zeros((n_true, n_true), dtype=float)])
        row_ind, col_ind = linear_sum_assignment(aug)
        for r, c in zip(row_ind, col_ind, strict=True):
            if c < n_fit and cost[r, c] < 0.0:
                matched_true_idx.append(int(r))

    matched_power = float(tg2[matched_true_idx].sum()) if matched_true_idx else 0.0
    fit_delay_set = set(fl.tolist())
    uniq_true = np.unique(tl)
    uniq_matched = sum(1 for d in uniq_true if int(d) in fit_delay_set)
    return dict(
        matched_count=len(matched_true_idx),
        total_true=int(n_true),
        matched_power=matched_power,
        total_power=total_power,
        matched_power_frac=matched_power / total_power if total_power > 0 else 0.0,
        unique_delay_matched=int(uniq_matched),
        unique_delay_total=int(len(uniq_true)),
    )


def match_omp_nominated(omp_delays, omp_dopplers, truth) -> dict[str, Any]:
    """Pre-time_refine recall on OMP-nominated columns (unique delays and 1-to-1 delay+Doppler)."""
    ol = np.asarray(omp_delays, dtype=int)
    ok = np.asarray(omp_dopplers, dtype=float)
    tl = np.asarray(truth['l_i'], dtype=int)
    tg2 = np.abs(np.asarray(truth['g_i'], dtype=complex)) ** 2
    total_power = float(tg2.sum())
    ol_set = set(ol.tolist())
    delay_hit = [i for i, d in enumerate(tl) if int(d) in ol_set]
    one_to_one = match_paths_1to1(ol, ok, truth)
    delay_power = float(tg2[delay_hit].sum()) if delay_hit else 0.0
    return dict(
        delay_matched_count=len(delay_hit),
        delay_matched_power=delay_power,
        delay_matched_power_frac=delay_power / total_power if total_power > 0 else 0.0,
        **one_to_one,
    )


def _decision_record(res) -> list[list[Any]]:
    """Exact cstate._decision format: [proposed, accepted] per global exchange step."""
    def action(rec, field):
        return None if rec is None else [int(rec['slot']), rec[field]]
    return [
        [action(step['selected'], 'replacement'), action(step['accepted'], 'new')]
        for step in res.global_trace
    ]


def run_hg_arm(
    ctx,
    helpers: dict[str, Any],
    obs: dict[str, Any],
    arrays: dict[str, Any],
    truth: dict[str, Any],
    *,
    ls: np.ndarray,
    ks: np.ndarray,
    recipe: str = 'B0-p2-s0.5',
    dictionary_limit: int = 2575,
    max_passes: int = 2,
    record_match: bool = True,
) -> dict[str, Any]:
    """Run Huang-2010-style global OMP re-acquisition (1..max_passes, syndrome early stop).

    Decision-ready timing boundary: starts before message prep and stops immediately after
    syndrome check on each pass (excludes truth scoring, hashing, and match diagnostics).
    """
    stage3 = helpers['stage3']
    moments = helpers['moments']
    time_refine = helpers['time_refine']
    system = ctx.system
    native = ctx.native
    pd = 1.0 - system.rho  # 0.5 in normalized observe() convention

    t_branch0 = perf_counter()
    _require_finite(arrays['r1_check'], 'HG.pass1.r1_check')
    _require_finite(arrays['r1_app'], 'HG.pass1.r1_app')
    prior = np.clip(arrays['r1_check'], -20.0, 20.0)
    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
    prep_sec = perf_counter() - t_branch0

    pass_raw = []
    decision_total_sec = 0.0
    for p_idx in range(max_passes):
        tp0 = perf_counter()
        x_ref = obs['pilot'] + mu
        _, omp_l, omp_k, omp_g = omp_reacquire(
            obs['y'], x_ref, ls, ks, system, float(obs['sigma2']), helpers,
            recipe=recipe, dictionary_limit=dictionary_limit,
        )
        c, _detail = time_refine(
            obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
            system.c1, system.c2, float(obs['sigma2']),
            mode='soft', max_paths=8, rounds=2,
        )
        _require_finite(c.dopplers, f'HG.pass{p_idx+1}.time_refine.dopplers')
        _require_finite(c.gains, f'HG.pass{p_idx+1}.time_refine.gains')
        o = native.scalar_joint(
            obs['y'], obs['pilot'], c, float(obs['sigma2']),
            pd=pd, prior=prior, iterations=20, damping=0.3, gain_mode='joint',
        )
        _require_finite(o['extrinsic'], f'HG.pass{p_idx+1}.scalar_joint.extrinsic')
        dec = native.decoder_messages(ctx.code, np.clip(o['extrinsic'], -20.0, 20.0), maxiter=50)
        _require_finite(dec['raw_check_extrinsic'], f'HG.pass{p_idx+1}.ldpc.raw_check_extrinsic')
        _require_finite(dec['raw_app'], f'HG.pass{p_idx+1}.ldpc.raw_app')
        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
        pass_sec = (prep_sec if p_idx == 0 else 0.0) + (perf_counter() - tp0)
        decision_total_sec += pass_sec
        pass_raw.append((dec, syn, c, omp_l, omp_k, pass_sec))
        if syn == 0 or p_idx == max_passes - 1:
            break
        tp_upd = perf_counter()
        prior = np.clip(dec['raw_check_extrinsic'], -20.0, 20.0)
        mu, v, _ = moments(np.clip(dec['raw_app'], -20.0, 20.0), pd)
        decision_total_sec += perf_counter() - tp_upd

    # Post-timing scoring and diagnostics
    pass_records = []
    for dec, syn, c, omp_l, omp_k, pass_sec in pass_raw:
        rec = dict(
            **stage3.decoded(ctx, dec, truth),
            syndrome=syn,
            ldpc_iters=int(dec['iterations']),
            pass_seconds=float(pass_sec),
            paths=[[int(d), float(nu)] for d, nu in zip(c.delays, c.dopplers, strict=True)],
        )
        if record_match:
            rec['match_omp'] = match_omp_nominated(omp_l, omp_k, truth)
            rec['match_refined'] = match_paths_1to1(c.delays, c.dopplers, truth)
        pass_records.append(rec)

    p1 = pass_records[0]
    final = pass_records[-1]
    return dict(
        HG1=dict(
            errors=p1['errors'],
            decoded_sha=p1['decoded_sha'],
            syndrome=p1['syndrome'],
            ldpc_iters=p1['ldpc_iters'],
            seconds=p1['pass_seconds'],
            paths=p1['paths'],
            **(dict(match_omp=p1['match_omp'], match_refined=p1['match_refined']) if record_match else {}),
        ),
        HG=dict(
            errors=final['errors'],
            decoded_sha=final['decoded_sha'],
            syndrome=final['syndrome'],
            ldpc_iters=final['ldpc_iters'],
            passes_used=len(pass_records),
            pass1_seconds=p1['pass_seconds'],
            seconds=float(decision_total_sec),
            paths=final['paths'],
            **(dict(match_omp=final['match_omp'], match_refined=final['match_refined']) if record_match else {}),
        ),
    )


def _run_exchange_arm(
    ctx,
    helpers: dict[str, Any],
    kernel,
    arm_name: str,
    obs: dict[str, Any],
    arrays: dict[str, Any],
    truth: dict[str, Any],
    *,
    record_match: bool = True,
) -> dict[str, Any]:
    """Run local exchange branch (Z or CD) with strict numerical-fallback and decision-ready timing."""
    stage3 = helpers['stage3']
    _require_finite(arrays['r1_check'], f'{arm_name}.r1_check')
    _require_finite(arrays['r1_app'], f'{arm_name}.r1_app')
    t0 = perf_counter()
    branch = stage3.e1.run_branch(ctx, kernel, obs, arrays, 'A1')
    dec = branch['decoder']
    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
    sec = perf_counter() - t0

    res = branch['result']
    if bool(res.diagnostics.get('numerical_fallback')):
        raise FloatingPointError(f'Geometry numerical_fallback triggered in {arm_name}')
    _require_finite(res.gains, f'{arm_name}.geometry.gains')
    _require_finite(branch['detector']['extrinsic'], f'{arm_name}.detector.extrinsic')

    delays = [int(p.delay) for p in res.paths]
    dopplers = [float(p.doppler) for p in res.paths]
    paths = [[d, nu] for d, nu in zip(delays, dopplers, strict=True)]
    state = dict(
        paths=paths,
        gains_sha=stage3.digest(res.gains),
        gamma_sha=stage3.digest(res.diagnostics['gamma']),
        objective=float(res.objective_after),
    )
    out = dict(
        **stage3.decoded(ctx, dec, truth),
        syndrome=syn,
        ldpc_iters=int(dec['iterations']),
        seconds=float(sec),
        paths=paths,
        state=state,
        n_edits=len(res.edits),
        decision=_decision_record(res),
        numerical_fallback=False,
    )
    if record_match:
        out['match_refined'] = match_paths_1to1(delays, dopplers, truth)
    return out


def run_z_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
    return _run_exchange_arm(ctx, helpers, helpers['z_kernel'], 'Z', obs, arrays, truth, record_match=record_match)


def run_cd_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
    return _run_exchange_arm(ctx, helpers, helpers['cd'], 'CD', obs, arrays, truth, record_match=record_match)


def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))


def load_archived_rho_sweep(
    archive_dir: Path = RHO_ARCHIVE_DIR,
    md5_manifest: Path = RHO_ARCHIVE_MD5,
) -> tuple[dict[tuple[str, int, int, int], dict[str, Any]], dict[str, str]]:
    """Pin manifest SHA-256, verify all 24 shard MD5s, validate 62,400 keys, 18,009 triggers, and invariants."""
    manifest_sha = sha256_file(md5_manifest)
    if manifest_sha != RHO_ARCHIVE_MD5_SHA256:
        raise RuntimeError(f'Archive manifest SHA-256 mismatch: {manifest_sha} != {RHO_ARCHIVE_MD5_SHA256}')

    expected_md5: dict[str, str] = {}
    for line in md5_manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, name = line.split()
        expected_md5[name] = digest
    if len(expected_md5) != 24:
        raise RuntimeError(f'Expected 24 archived shards in manifest, got {len(expected_md5)}')

    rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    verified_md5: dict[str, str] = {}
    stratum_counts: dict[tuple[int, str], int] = {(r, b): 0 for r in RHOS for b in ('low', 'mid')}
    for name, exp in sorted(expected_md5.items()):
        path = archive_dir / name
        if not path.is_file():
            raise FileNotFoundError(f'Missing archived shard {path}')
        actual = md5_file(path)
        if actual != exp:
            raise RuntimeError(f'Archived shard MD5 mismatch for {name}: {actual} != {exp}')
        verified_md5[name] = actual
        with path.open('r', encoding='utf-8') as handle:
            for line in handle:
                r = json.loads(line)
                k = row_key(r)
                if k in rows:
                    raise RuntimeError(f'Duplicate archived key {k}')
                if bool(r['triggered']) != bool(r['syndrome']):
                    raise RuntimeError(f'Archive invariant triggered != bool(syndrome) at {k}')
                if not r['syndrome']:
                    f0_out = (r['arms']['F0']['errors'], r['arms']['F0']['decoded_sha'])
                    cd_out = (r['arms']['CD']['errors'], r['arms']['CD']['decoded_sha'])
                    if f0_out != cd_out:
                        raise RuntimeError(f'Untriggered CD != F0 in archive at {k}')
                else:
                    band = 'low' if k[2] in LOW_SNRS else 'mid'
                    stratum_counts[(k[1], band)] += 1
                rows[k] = r

    expected_keys = {
        (s, rho, snr, frame)
        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
    }
    if rows.keys() != expected_keys:
        missing = len(expected_keys - rows.keys())
        extra = len(rows.keys() - expected_keys)
        raise RuntimeError(f'Archived key inventory mismatch: missing={missing}, extra={extra}')
    if sum(stratum_counts.values()) != EXPECTED_TOTAL_TRIGGERS or stratum_counts != EXPECTED_TRIGGERS_BY_STRATUM:
        raise RuntimeError(f'Archived trigger strata mismatch: {stratum_counts} != {EXPECTED_TRIGGERS_BY_STRATUM}')
    return rows, verified_md5
