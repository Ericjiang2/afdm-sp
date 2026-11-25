"""Pre-main qualification gates G1-G4 on deinlab (zero /dev/shm IPC; smoke frames 5800-5839 + 20 archived keys)."""
from __future__ import annotations

import argparse
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import resource
import shutil
import sys
import time
from typing import Any

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_arms as ar  # noqa: E402

G4_LOW_TARGETS = (('U', 300), ('G', 400), ('U', 400), ('G', 300))
G4_MID_TARGETS = (
    ('U', (450, 500)),
    ('G', (500, 450)),
    ('U', (550, 500, 450)),
    ('G', (550, 500, 450)),
)
BUDGET_CAP_CORE_HOURS = 12.0
OVERHEAD_ALLOWANCE_HOURS = 0.15
COST_MARGIN = 1.2


def _spawn_map(fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
    """Run fn(item) across spawned workers using file IPC under TMPDIR (never touches /dev/shm)."""
    if not items:
        return []
    n_workers = min(max_workers, len(items))
    chunks = [items[i::n_workers] for i in range(n_workers)]
    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    out_paths = []
    try:
        for w_idx, chunk in enumerate(chunks):
            out_p = ipc_dir / f'{tag}_w{w_idx:02d}.json'
            out_paths.append((chunk, out_p))
            proc = mp_ctx.Process(target=_chunk_runner, args=(fn, chunk, out_p))
            proc.start()
            running[proc.sentinel] = (w_idx, proc)
        while running:
            for ready in wait(running):
                w_idx, proc = running.pop(ready)
                proc.join()
                code = proc.exitcode
                proc.close()
                if code != 0:
                    raise RuntimeError(f'Gate worker {tag}/{w_idx} exited with code {code}')
    finally:
        for _, proc in running.values():
            proc.terminate()
        for _, proc in running.values():
            proc.join()
            proc.close()

    # Reassemble in original item order
    results: list[Any] = [None] * len(items)
    for w_idx, (_chunk, out_p) in enumerate(out_paths):
        chunk_res = json.loads(out_p.read_text(encoding='utf-8'))
        for pos, val in enumerate(chunk_res):
            results[w_idx + pos * n_workers] = val
    return results


def _chunk_runner(fn, chunk: list[Any], out_path: Path):
    ctx, helpers = ar.load_context()
    out = [fn(ctx, helpers, item) for item in chunk]
    ar.atomic_write_text(out_path, json.dumps(out, allow_nan=False))


def _g1_eval_key(ctx, helpers, item):
    key, archived, check_cd = item
    s, rho, snr, frame = key
    stage3 = helpers['stage3']
    base = stage3.inputs(ctx, frame, s, rho)
    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    inp = stage3.input_record(raw, obs)
    if inp != archived['inputs']:
        raise AssertionError(f'G1 input fingerprint mismatch at {key}')
    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    f0 = stage3.decoded(ctx, dec, truth)
    if syn != archived['syndrome']:
        raise AssertionError(f'G1 F0 syndrome mismatch at {key}: {syn} != {archived["syndrome"]}')
    if f0 != dict(errors=archived['arms']['F0']['errors'], decoded_sha=archived['arms']['F0']['decoded_sha']):
        raise AssertionError(f'G1 F0 decoded mismatch at {key}: {f0} vs {archived["arms"]["F0"]}')

    cd_checked = False
    if check_cd:
        if not syn:
            raise AssertionError(f'Expected triggered key for CD check at {key}')
        cd_rec = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
        arch_cd = archived['arms']['CD']
        if cd_rec['errors'] != arch_cd['errors'] or cd_rec['decoded_sha'] != arch_cd['decoded_sha']:
            raise AssertionError(f'G1 CD decoded mismatch at {key}')
        if 'state' not in arch_cd or arch_cd['state'] is None or 'decision' not in arch_cd or arch_cd['decision'] is None:
            raise AssertionError(f'G1 archived CD missing required geometry fields at {key}')
        if cd_rec['state'] != arch_cd['state']:
            raise AssertionError(f'G1 CD full state mismatch at {key}: {cd_rec["state"]} != {arch_cd["state"]}')
        if cd_rec['decision'] != arch_cd['decision']:
            raise AssertionError(f'G1 CD full decision trace mismatch at {key}: {cd_rec["decision"]} != {arch_cd["decision"]}')
        cd_checked = True
    return dict(key=list(key), triggered=bool(syn), f0_ok=True, cd_ok=cd_checked, numerical_fallback=False)


def run_g1(archived_rows, max_workers: int, ipc_dir: Path) -> dict[str, Any]:
    def sort_key(k):
        return (k[0], k[1], k[3], k[2])

    tasks = []
    for s in ar.SCENARIOS:
        for rho in (300, 500):
            trig = sorted(
                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and r['triggered']),
                key=sort_key,
            )
            for k in trig[:2]:
                tasks.append((k, archived_rows[k], True))
        for rho in ar.RHOS:
            untrig = sorted(
                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and not r['triggered']),
                key=sort_key,
            )
            tasks.append((untrig[0], archived_rows[untrig[0]], False))

    results = _spawn_map(_g1_eval_key, tasks, max_workers, ipc_dir, 'g1')
    assert len(results) == 20
    print('G1 PASS (20/20 archived keys matched bit-for-bit incl. full CD decision trace)', flush=True)
    return dict(passed=True, keys_checked=len(results), details=results)


def _g2_worker(ctx, helpers, _dummy) -> dict[str, Any]:
    stage3 = helpers['stage3']
    from receiver import pilot_front
    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch

    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    parity_rows = []
    for frame in (5800, 5801):
        for s in ar.SCENARIOS:
            base = stage3.inputs(ctx, frame, s, 300)
            _, obs, _ = stage3.observed(ctx, base, 300, 500)
            pf = pilot_front(obs, ctx.system, ctx.code)
            pf_ids = np.asarray(pf['delays'], int) * 5 + (np.asarray(pf['dopplers'], int) + 2)
            ids, _, _, gs = ar.omp_reacquire(
                obs['y'], obs['pilot'], ls_int, ks_int, ctx.system, float(obs['sigma2']),
                helpers, recipe='B0-p2-s0.5', dictionary_limit=515,
            )
            if not np.array_equal(ids, pf_ids):
                raise AssertionError(f'G2a column sequence mismatch at {(s, frame)}: {ids} != {pf_ids}')
            max_diff = float(np.max(np.abs(gs - pf['gains'])))
            if max_diff >= 1e-6:
                raise AssertionError(f'G2a gain mismatch at {(s, frame)}: {max_diff}')
            parity_rows.append(dict(key=[s, 300, 500, frame], n_cols=len(ids), max_gain_diff=max_diff))

    # G2b: independent forward physical Channel.apply() + actual step-3 complex64 gels observer
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    base = stage3.inputs(ctx, 5800, 'U', 300)
    raw, obs, _ = stage3.observed(ctx, base, 300, 1000)
    x_ref = obs['pilot'] + raw['data'] / np.sqrt(2.0 * (1.0 - 0.30))
    true_paths = [(7, -2.75, 0.7 + 0.2j), (33, 2.75, -0.5 + 0.4j), (78, 0.25, 0.3 - 0.35j)]
    true_cols = [int(l * 25 + round((nu + 3.0) * 4)) for l, nu, _ in true_paths]
    g_true = np.array([p[2] for p in true_paths], dtype=complex)
    Channel = helpers['Channel']
    # Independent forward operator Channel.apply (time-domain per-path loop, NOT Channel.regressors)
    y_synth = Channel(
        len(x_ref), ctx.system.c1, ctx.system.c2,
        [p[0] for p in true_paths], [p[1] for p in true_paths], g_true,
    ).apply(x_ref)

    ids_f, _, _, _, Phi_f = ar.omp_reacquire(
        y_synth, x_ref, ls_fine, ks_fine, ctx.system, 1e-4, helpers,
        recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), return_phi=True,
    )
    if set(ids_f[:3].tolist()) != set(true_cols):
        raise AssertionError(f'G2b failed to recover 3 synthetic fine-grid paths: got {ids_f[:3]} vs {true_cols}')

    # Capture ACTUAL complex64 gels step-3 coefficients from omp_sparse_torch
    step3 = {}
    def observer(sup, sol, _res):
        if len(sup) == 3:
            step3['ids'] = list(sup)
            step3['sol'] = sol.detach().cpu().numpy().copy()

    omp_sparse_torch(
        torch.tensor(y_synth, dtype=torch.complex64),
        torch.tensor(Phi_f, dtype=torch.complex64),
        24, lstsq_driver='gels', path_observer=observer,
    )
    if step3.get('ids') != ids_f[:3].tolist():
        raise AssertionError(f'G2b observer step-3 ids mismatch: {step3.get("ids")} vs {ids_f[:3].tolist()}')
    rec_map = {int(i): complex(g) for i, g in zip(step3['ids'], step3['sol'], strict=True)}
    rel_err = float(
        np.linalg.norm([rec_map[c] - g for c, g in zip(true_cols, g_true, strict=True)])
        / np.linalg.norm(g_true)
    )
    if rel_err >= 1e-4:
        raise AssertionError(f'G2b step-3 complex64 gels gain relative error too large: {rel_err}')

    return dict(
        passed=True,
        g2a_pilot_front_parity=parity_rows,
        g2b_fine_grid_synthetic=dict(
            dictionary_cols=len(ls_fine),
            forward_operator='Channel.apply (independent of Channel.regressors)',
            true_cols=true_cols,
            first3_ids=ids_f[:3].tolist(),
            step3_complex64_gels_rel_gain_error=rel_err,
        ),
    )


def _g3a_frame_worker(ctx, helpers, item):
    frame, recipe = item
    stage3 = helpers['stage3']
    time_refine = helpers['time_refine']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)

    base = stage3.inputs(ctx, frame, 'U', 300)
    raw, obs, truth = stage3.observed(ctx, base, 300, 1000)
    mu_true = np.asarray(raw['data'], dtype=complex) / np.sqrt(2.0 * (1.0 - 0.30))
    v_zero = np.zeros(len(mu_true), dtype=float)
    x_ref = obs['pilot'] + mu_true

    _, omp_l, omp_k, omp_g = ar.omp_reacquire(
        obs['y'], x_ref, ls_fine, ks_fine, ctx.system, float(obs['sigma2']),
        helpers, recipe=recipe, dictionary_limit=len(ls_fine),
    )
    c, _ = time_refine(
        obs['y'], obs['pilot'], mu_true, v_zero, omp_l, omp_k, omp_g,
        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
        mode='soft', max_paths=8, rounds=2,
    )
    return dict(
        frame=frame, recipe=recipe,
        omp=ar.match_omp_nominated(omp_l, omp_k, truth),
        refined=ar.match_paths_1to1(c.delays, c.dopplers, truth),
    )


def _g3b_eval_triggered_worker(ctx, helpers, item):
    s, rho, snr, frame, recipe = item
    stage3 = helpers['stage3']
    moments = helpers['moments']
    time_refine = helpers['time_refine']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)

    base = stage3.inputs(ctx, frame, s, rho)
    _, obs, truth = stage3.observed(ctx, base, rho, snr)
    _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    if not syn:
        raise AssertionError(f'G3b expected triggered key at {(s, rho, snr, frame)}')

    pd = 1.0 - ctx.system.rho
    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
    x_ref = obs['pilot'] + mu
    ids, omp_l, omp_k, omp_g, Phi = ar.omp_reacquire(
        obs['y'], x_ref, ls_fine, ks_fine, ctx.system, float(obs['sigma2']),
        helpers, recipe=recipe, dictionary_limit=len(ls_fine), return_phi=True,
    )
    c, _ = time_refine(
        obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
        mode='soft', max_paths=8, rounds=2,
    )
    Phi_S = Phi[:, ids].astype(np.complex128)
    cond = float(np.linalg.cond(Phi_S))
    g_128, *_ = np.linalg.lstsq(Phi_S, obs['y'].astype(np.complex128), rcond=None)
    rel_ls_diff = float(np.linalg.norm(omp_g - g_128) / max(np.linalg.norm(g_128), 1e-12))

    from afdm_sp_joint_unrolled.classical_joint_unrolled import omp_sparse_torch
    k_omp = 24 if recipe == 'B0-p2-s0.5' else 40
    h128, ids128 = omp_sparse_torch(
        torch.tensor(obs['y'], dtype=torch.complex128),
        torch.tensor(Phi, dtype=torch.complex128),
        k_omp, lstsq_driver='gelsd',
    )
    ids128_arr = np.asarray(ids128, dtype=int)
    jacc = len(set(ids.tolist()) & set(ids128_arr.tolist())) / len(set(ids.tolist()) | set(ids128_arr.tolist()))
    g128_full = h128.detach().cpu().numpy()[ids128_arr]
    c128, _ = time_refine(
        obs['y'], obs['pilot'], mu, v, ls_fine[ids128_arr], ks_fine[ids128_arr], g128_full,
        ctx.system.c1, ctx.system.c2, float(obs['sigma2']),
        mode='soft', max_paths=8, rounds=2,
    )
    return dict(
        key=[s, rho, snr, frame],
        cond_Phi_S=cond,
        rel_ls_diff_64_vs_128=rel_ls_diff,
        support_jaccard_64_vs_128=float(jacc),
        omp=ar.match_omp_nominated(omp_l, omp_k, truth),
        refined_64=ar.match_paths_1to1(c.delays, c.dopplers, truth),
        refined_128=ar.match_paths_1to1(c128.delays, c128.dopplers, truth),
    )


def _g3b_scan_trigger_worker(ctx, helpers, item):
    s, rho, snr, frame = item
    stage3 = helpers['stage3']
    base = stage3.inputs(ctx, frame, s, rho)
    _, obs, _ = stage3.observed(ctx, base, rho, snr)
    _, _, syn, _ = stage3.e1.f0_state(ctx, obs)
    return [s, rho, snr, frame] if syn else None


def _g4_probe_worker(ctx, helpers, item):
    """Collect 4 balanced triggered keys (exact 2 U + 2 G, covering stratum SNRs) for (rho, band)."""
    rho, band = item
    stage3 = helpers['stage3']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)

    found = []
    used_frames: set[int] = set()
    targets = [(s, (snr,)) for s, snr in G4_LOW_TARGETS] if band == 'low' else list(G4_MID_TARGETS)

    for s_target, snr_prefs in targets:
        hit = None
        for snr_try in snr_prefs:
            for frame in ar.SMOKE_FRAMES:
                if frame in used_frames:
                    continue
                t_base0 = time.process_time()
                base = stage3.inputs(ctx, frame, s_target, rho)
                base_cpu = time.process_time() - t_base0
                t_f0 = time.process_time()
                _, obs, truth = stage3.observed(ctx, base, rho, snr_try)
                _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
                f0_cpu = time.process_time() - t_f0
                if not syn:
                    continue
                t_z0 = time.process_time()
                ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
                z_cpu = time.process_time() - t_z0

                t_int0 = time.process_time()
                hgint = ar.run_hg_arm(
                    ctx, helpers, obs, arrays, truth,
                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int), max_passes=2,
                )
                hgint_cpu = time.process_time() - t_int0

                hg_times = {}
                hg_passes = {}
                for rec_name in ('B0-p2-s0.5', 'B0-p3-s0.5'):
                    t_hg0 = time.process_time()
                    hg = ar.run_hg_arm(
                        ctx, helpers, obs, arrays, truth,
                        ls=ls_fine, ks=ks_fine, recipe=rec_name, dictionary_limit=len(ls_fine), max_passes=2,
                    )
                    hg_times[rec_name] = time.process_time() - t_hg0
                    hg_passes[rec_name] = int(hg['HG']['passes_used'])

                used_frames.add(frame)
                hit = dict(
                    key=[s_target, rho, snr_try, frame],
                    target_snrs=list(snr_prefs),
                    band=band,
                    base_cpu=float(base_cpu), f0_cpu=float(f0_cpu), z_cpu=float(z_cpu),
                    hgint_cpu=float(hgint_cpu), hgint_passes=int(hgint['HG']['passes_used']),
                    hg_cpu=hg_times, hg_passes=hg_passes,
                )
                break
            if hit is not None:
                break
        if hit is None:
            raise RuntimeError(f'G4 could not find trigger for rho={rho}, band={band}, target={(s_target, snr_prefs)}')
        found.append(hit)

    assert [x['key'][0] for x in found] == ['U', 'G', 'U', 'G']
    return [rho, band, found]


def project_cost(
    g4_strata: dict[tuple[int, str], list[dict[str, Any]]],
    archived_counts: dict[tuple[int, str], int],
    recipe: str,
    *,
    include_hgint: bool,
    rhos: tuple[int, ...],
) -> dict[str, Any]:
    total_raw_sec = 0.0
    per_stratum = {}
    for rho in rhos:
        for band in ('low', 'mid'):
            samples = g4_strata[(rho, band)]
            n_trig = archived_counts[(rho, band)]
            per_key = [
                s['base_cpu'] + s['f0_cpu'] + s['z_cpu'] + s['hg_cpu'][recipe]
                + (s['hgint_cpu'] if include_hgint else 0.0)
                for s in samples
            ]
            mean_sec = float(np.mean(per_key))
            sec_stratum = mean_sec * n_trig
            total_raw_sec += sec_stratum
            per_stratum[f'{rho}/{band}'] = dict(
                archived_triggers=n_trig,
                mean_cpu_sec=mean_sec,
                projected_core_hours=sec_stratum / 3600.0,
                mean_hg_passes=float(np.mean([s['hg_passes'][recipe] for s in samples])),
            )
    raw_hours = total_raw_sec / 3600.0 + OVERHEAD_ALLOWANCE_HOURS
    with_margin = raw_hours * COST_MARGIN
    return dict(
        recipe=recipe,
        include_hgint=include_hgint,
        rhos=list(rhos),
        raw_core_hours=raw_hours,
        core_hours_with_margin=with_margin,
        within_budget=bool(with_margin <= BUDGET_CAP_CORE_HOURS),
        per_stratum=per_stratum,
    )


def main():
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    thread_env = ar.check_thread_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.workers <= 24:
        parser.error('workers must be in 1..24')
    args.out.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmpdir / f'hs_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=False)

    started = time.monotonic()
    try:
        ctx, helpers = ar.load_context()
        archived_rows, archive_md5 = ar.load_archived_rho_sweep()
        arch_counts = dict(ar.EXPECTED_TRIGGERS_BY_STRATUM)
        print(f'Archive verified: {len(archived_rows)} keys, {sum(arch_counts.values())} triggers.', flush=True)

        # G1
        g1 = run_g1(archived_rows, args.workers, ipc_dir)

        # G2
        g2 = _spawn_map(_g2_worker, [0], 1, ipc_dir, 'g2')[0]
        print('G2 PASS (pilot_front parity + independent Channel.apply 2575-col step-3 gels)', flush=True)

        # G3a
        g3a_summary = {}
        for rec_name in ('B0-p2-s0.5', 'B0-p3-s0.5'):
            jobs = [(f, rec_name) for f in range(5800, 5820)]
            rows = _spawn_map(_g3a_frame_worker, jobs, args.workers, ipc_dir, f'g3a_{rec_name}')
            tot_m = sum(r['refined']['matched_count'] for r in rows)
            tot_t = sum(r['refined']['total_true'] for r in rows)
            tot_omp_d = sum(r['omp']['delay_matched_count'] for r in rows)
            sum_mp = sum(r['refined']['matched_power'] for r in rows)
            sum_tp = sum(r['refined']['total_power'] for r in rows)
            pooled_pw = sum_mp / sum_tp if sum_tp > 0 else 0.0
            mean_pw = float(np.mean([r['refined']['matched_power_frac'] for r in rows]))
            min_frame_m = min(r['refined']['matched_count'] for r in rows)
            passed = bool(tot_m >= 144 and pooled_pw >= 0.95)
            g3a_summary[rec_name] = dict(
                passed=passed,
                matched_paths=tot_m,
                total_true_paths=tot_t,
                path_recall=tot_m / tot_t,
                omp_delay_recall=tot_omp_d / tot_t,
                pooled_matched_power_frac=pooled_pw,
                mean_matched_power_frac=mean_pw,
                min_frame_matched_power_frac=float(np.min([r['refined']['matched_power_frac'] for r in rows])),
                min_frame_matched_paths=int(min_frame_m),
                per_frame=rows,
            )
            print(
                f"G3a [{rec_name}]: {tot_m}/{tot_t} ({100*tot_m/tot_t:.2f}%), "
                f"pooled_power={100*pooled_pw:.2f}%, min_frame={min_frame_m}/8 -> {'PASS' if passed else 'FAIL'}",
                flush=True,
            )

        # G4
        g4_jobs = [(rho, band) for rho in ar.RHOS for band in ('low', 'mid')]
        g4_raw = _spawn_map(_g4_probe_worker, g4_jobs, min(args.workers, 12), ipc_dir, 'g4')
        g4_strata = {(rho, band): samples for rho, band, samples in g4_raw}

        def best_schedule(rec_name: str):
            attempts = [
                (True, ar.RHOS),
                (False, ar.RHOS),
                (False, tuple(r for r in ar.RHOS if r != 400)),
                (False, tuple(r for r in ar.RHOS if r not in (400, 150))),
            ]
            tried = []
            for inc_int, rhos in attempts:
                proj = project_cost(g4_strata, arch_counts, rec_name, include_hgint=inc_int, rhos=rhos)
                tried.append(proj)
                if proj['within_budget']:
                    return proj, tried
            return None, tried

        sched_24, tried_24 = best_schedule('B0-p2-s0.5')
        sched_40, tried_40 = best_schedule('B0-p3-s0.5')

        ok_24 = g3a_summary['B0-p2-s0.5']['passed'] and (sched_24 is not None)
        ok_40 = g3a_summary['B0-p3-s0.5']['passed'] and (sched_40 is not None)
        if not ok_24 and not ok_40:
            selected_recipe, selected_sched = None, None
        elif ok_24 and ok_40:
            if g3a_summary['B0-p3-s0.5']['matched_paths'] >= g3a_summary['B0-p2-s0.5']['matched_paths'] + 4:
                selected_recipe, selected_sched = 'B0-p3-s0.5', sched_40
            else:
                selected_recipe, selected_sched = 'B0-p2-s0.5', sched_24
        elif ok_24:
            selected_recipe, selected_sched = 'B0-p2-s0.5', sched_24
        else:
            selected_recipe, selected_sched = 'B0-p3-s0.5', sched_40

        print(
            f'Selection: recipe={selected_recipe}, sched='
            f'{None if selected_sched is None else dict(hours=round(selected_sched["core_hours_with_margin"], 3), include_hgint=selected_sched["include_hgint"], rhos=selected_sched["rhos"])}',
            flush=True,
        )

        # G3b: first identify exact 24 triggered smoke keys (cheap F0 scan), then evaluate ONLY those 24 keys
        g3b = dict(passed=False, skipped=True)
        if selected_recipe is not None:
            scan_jobs = [
                (s, rho, 500, frame)
                for frame in ar.SMOKE_FRAMES for s in ar.SCENARIOS for rho in (200, 250, 300)
            ]
            trig_keys: list[list[Any]] = []
            for start_i in range(0, len(scan_jobs), 32):
                if len(trig_keys) >= 24:
                    break
                batch_hits = _spawn_map(
                    _g3b_scan_trigger_worker, scan_jobs[start_i:start_i + 32],
                    args.workers, ipc_dir, f'g3b_scan_{start_i}',
                )
                trig_keys.extend(x for x in batch_hits if x is not None)
            trig_keys = trig_keys[:24]
            if len(trig_keys) != 24:
                raise RuntimeError(f'G3b expected exactly 24 triggered smoke keys, got {len(trig_keys)}')
            eval_jobs = [(s, rho, snr, frame, selected_recipe) for s, rho, snr, frame in trig_keys]
            g3b_rows = _spawn_map(_g3b_eval_triggered_worker, eval_jobs, args.workers, ipc_dir, 'g3b_eval')
            med_rel_diff = float(np.median([x['rel_ls_diff_64_vs_128'] for x in g3b_rows]))
            max_cond = float(np.max([x['cond_Phi_S'] for x in g3b_rows]))
            med_cond = float(np.median([x['cond_Phi_S'] for x in g3b_rows]))
            med_jacc = float(np.median([x['support_jaccard_64_vs_128'] for x in g3b_rows]))
            omp_rec = sum(x['omp']['delay_matched_count'] for x in g3b_rows) / sum(x['omp']['total_true'] for x in g3b_rows)
            ref64_rec = sum(x['refined_64']['matched_count'] for x in g3b_rows) / sum(x['refined_64']['total_true'] for x in g3b_rows)
            ref128_rec = sum(x['refined_128']['matched_count'] for x in g3b_rows) / sum(x['refined_128']['total_true'] for x in g3b_rows)
            g3b_pass = bool(np.isfinite(med_rel_diff) and med_rel_diff <= 0.10)
            g3b = dict(
                passed=g3b_pass,
                keys_evaluated=len(g3b_rows),
                recipe=selected_recipe,
                median_rel_ls_diff_64_vs_128=med_rel_diff,
                median_support_jaccard_64_vs_128=med_jacc,
                median_cond_Phi_S=med_cond,
                max_cond_Phi_S=max_cond,
                omp_delay_recall=omp_rec,
                refined_64_path_recall=ref64_rec,
                refined_128_path_recall=ref128_rec,
                rows=g3b_rows,
            )
            print(
                f"G3b [{selected_recipe}] ({len(g3b_rows)} exact real triggers): "
                f"med_64v128_diff={med_rel_diff:.2e}, jacc={med_jacc:.3f}, med_cond={med_cond:.1f}, "
                f"omp_delay={100*omp_rec:.1f}%, ref64={100*ref64_rec:.1f}%, ref128={100*ref128_rec:.1f}% -> "
                f"{'PASS' if g3b_pass else 'FAIL'}",
                flush=True,
            )
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    gate_cpu_sec = time.process_time() + children.ru_utime + children.ru_stime
    all_passed = bool(
        g1['passed'] and g2['passed'] and (selected_recipe is not None)
        and (selected_sched is not None) and g3b['passed']
    )
    payload = dict(
        _argv=sys.argv,
        _config=dict(
            out=str(args.out),
            workers=args.workers,
            python_executable=sys.executable,
            threads=thread_env,
            own_md5=ar.own_md5(),
            frozen_extra_md5=helpers['extra_md5'],
            p1_source_md5=ar.frozen_p1_md5(ctx),
            archive_manifest_sha256=ar.RHO_ARCHIVE_MD5_SHA256,
            archive_shards_verified=len(archive_md5),
            archived_triggers_by_stratum={f'{r}/{b}': c for (r, b), c in sorted(arch_counts.items())},
        ),
        all_passed=all_passed,
        selected=None if selected_sched is None else dict(
            hg_recipe=selected_recipe,
            include_hgint=selected_sched['include_hgint'],
            retained_rhos=selected_sched['rhos'],
            projected_core_hours_with_margin=selected_sched['core_hours_with_margin'],
        ),
        G1=g1,
        G2=g2,
        G3a=g3a_summary,
        G3b=g3b,
        G4=dict(
            passed=selected_sched is not None,
            budget_cap_core_hours=BUDGET_CAP_CORE_HOURS,
            margin=COST_MARGIN,
            overhead_allowance_hours=OVERHEAD_ALLOWANCE_HOURS,
            projections={'B0-p2-s0.5': tried_24, 'B0-p3-s0.5': tried_40},
            strata_samples={f'{r}/{b}': s for (r, b), s in sorted(g4_strata.items())},
        ),
        gate_cpu_hours=gate_cpu_sec / 3600.0,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(args.out / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} cpu_hours={gate_cpu_sec/3600:.4f}', flush=True)
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
