"""Quiet single-core per-trigger timing panel (100 archived triggers + 50 untriggered F0 at rho=0.30, 5.0 dB)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import sys
from time import perf_counter
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402

BUDGET_EXIT_CODE = 124
TIMING_BUDGET_SECONDS = 1750.0  # strictly < 0.5 core-hours (1800s) including process startup


def latency(values: list[float]) -> dict[str, Any]:
    arr = np.asarray(values, dtype=float)
    return dict(
        n=len(values),
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        p95=float(np.quantile(arr, 0.95)),
    )


def _load_verified_live_rows(out: Path, raw_dir: Path, expected_md5: dict[str, str]):
    """Verify all raw shard MD5s from REMOTE_ROWS_MD5.txt and assert unique keys."""
    md5_txt = (out / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8')
    manifest = dict(line.split()[::-1] for line in md5_txt.splitlines() if line.strip())
    if manifest != expected_md5:
        raise RuntimeError('REMOTE_ROWS_MD5.txt differs from summary.json _config.raw_rows_md5')

    live_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    seen_all: set[tuple[str, int, int, int]] = set()
    for name, exp in sorted(manifest.items()):
        p = raw_dir / name
        actual = ar.md5_file(p)
        if actual != exp:
            raise RuntimeError(f'Raw shard MD5 mismatch before timing: {name} ({actual} != {exp})')
        with p.open('r', encoding='utf-8') as handle:
            for line in handle:
                r = json.loads(line)
                k = ar.row_key(r)
                if k in seen_all:
                    raise RuntimeError(f'Duplicate raw row key {k}')
                seen_all.add(k)
                if k[1] == 300 and k[2] == 500:
                    live_rows[k] = r
    return live_rows


def main():
    proc_start = perf_counter()
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    thread_env = ar.check_thread_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze-commit', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        parser.error('freeze-commit must be a 40-char lowercase hex git SHA')

    # Verify process was already pinned to a single quiet CPU before Python started (launch_main.sh taskset)
    affinity = sorted(os.sched_getaffinity(0))
    if len(affinity) != 1:
        raise RuntimeError(f'timing.py expects single-CPU affinity pinned before launch, got {affinity}')
    cpu_info = dict(
        idle_cpu=int(affinity[0]),
        measured_utilization_pct=float(os.environ.get('HS_QUIET_CPU_UTIL', '0.0')),
        load=list(os.getloadavg()),
    )
    print(f'Quiet timing running on pre-pinned CPU {cpu_info}', flush=True)

    out = args.out.resolve()
    ar.verify_freeze_commit_if_git(args.freeze_commit, ar.own_md5())
    summary_path = out / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    cfg = summary['_config']
    if cfg['freeze_commit'] != args.freeze_commit:
        raise RuntimeError('timing.py freeze-commit differs from summary.json')
    hg_recipe = cfg['hg_recipe']
    include_hgint = bool(cfg['include_hgint'])

    ctx, helpers = ar.load_context()
    stage3 = helpers['stage3']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)

    archived_rows, _ = ar.load_archived_rho_sweep()
    live_rows = _load_verified_live_rows(out, Path(cfg['raw_output_dir']), cfg['raw_rows_md5'])

    trig_by_s = {}
    untrig_by_s = {}
    for s in ar.SCENARIOS:
        trig_by_s[s] = sorted(
            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and r['triggered']),
            key=lambda k: k[3],
        )
        untrig_by_s[s] = sorted(
            (k for k, r in archived_rows.items() if k[0] == s and k[1] == 300 and k[2] == 500 and not r['triggered']),
            key=lambda k: k[3],
        )
        if len(trig_by_s[s]) < 50 or len(untrig_by_s[s]) < 25:
            raise RuntimeError(f'Insufficient keys for {s}/300/500')

    panel_keys = [k for pair in zip(trig_by_s['U'][:50], trig_by_s['G'][:50], strict=True) for k in pair]
    untrig_keys = [k for pair in zip(untrig_by_s['U'][:25], untrig_by_s['G'][:25], strict=True) for k in pair]

    # Prewarm frame-invariant structures on smoke frame 5800 (not measured)
    warm_base = stage3.inputs(ctx, 5800, 'U', 300)
    _, warm_obs, warm_truth = stage3.observed(ctx, warm_base, 300, 500)
    _, warm_arr, _, _ = stage3.e1.f0_state(ctx, warm_obs)
    ar.run_cd_arm(ctx, helpers, warm_obs, warm_arr, warm_truth, record_match=False)
    ar.run_hg_arm(
        ctx, helpers, warm_obs, warm_arr, warm_truth,
        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
        max_passes=1, record_match=False,
    )

    branch_labels = ('CD', 'Z', 'HG') + (('HGint',) if include_hgint else ())
    timed_rows = []
    untrig_f0_sec: dict[str, list[float]] = {'U': [], 'G': []}
    rows_lines: list[str] = []

    # First time 50 untriggered F0 keys (25 U + 25 G) for exact scenario-stratified full-frame amortization
    for key in untrig_keys:
        s, rho, snr, frame = key
        arch = archived_rows[key]
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)
        t_f0 = perf_counter()
        dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
        f0_sec = perf_counter() - t_f0
        f0 = stage3.decoded(ctx, dec, truth)
        if syn != 0 or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
            raise AssertionError(f'Timing untriggered F0 drift at {key}')
        untrig_f0_sec[s].append(float(f0_sec))
        rows_lines.append(json.dumps(dict(
            kind='untriggered_f0', key=list(key), f0_seconds=float(f0_sec),
        ), allow_nan=False) + '\n')
        if perf_counter() - proc_start >= TIMING_BUDGET_SECONDS:
            sys.exit(BUDGET_EXIT_CODE)

    # Next time the 100 triggered keys (per-scenario balanced round-robin branch order, decision-ready boundary)
    scenario_pos = {'U': 0, 'G': 0}
    for idx, key in enumerate(panel_keys):
        s, rho, snr, frame = key
        arch = archived_rows[key]
        live = live_rows[key]
        base = stage3.inputs(ctx, frame, s, rho)
        _, obs, truth = stage3.observed(ctx, base, rho, snr)

        t_f0 = perf_counter()
        dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
        f0_sec = perf_counter() - t_f0
        f0 = stage3.decoded(ctx, dec, truth)
        if syn != arch['syndrome'] or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
            raise AssertionError(f'Timing F0 drift at {key}')

        offset = scenario_pos[s] % len(branch_labels)
        scenario_pos[s] += 1
        order = branch_labels[offset:] + branch_labels[:offset]
        sec_map: dict[str, float] = {}
        hg_passes = None
        for arm in order:
            if arm == 'CD':
                r = ar.run_cd_arm(ctx, helpers, obs, arrays, truth, record_match=False)
                if r['decoded_sha'] != arch['arms']['CD']['decoded_sha']:
                    raise AssertionError(f'Timing CD drift at {key}')
                sec_map['CD'] = r['seconds']
            elif arm == 'Z':
                r = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=False)
                if r['decoded_sha'] != live['arms']['Z']['decoded_sha']:
                    raise AssertionError(f'Timing Z drift at {key}')
                sec_map['Z'] = r['seconds']
            elif arm == 'HG':
                r = ar.run_hg_arm(
                    ctx, helpers, obs, arrays, truth,
                    ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
                    max_passes=2, record_match=False,
                )
                if (r['HG']['decoded_sha'] != live['arms']['HG']['decoded_sha']
                        or r['HG1']['decoded_sha'] != live['arms']['HG1']['decoded_sha']):
                    raise AssertionError(f'Timing HG/HG1 drift at {key}')
                sec_map['HG'] = r['HG']['seconds']
                sec_map['HG1'] = r['HG1']['seconds']
                hg_passes = r['HG']['passes_used']
            elif arm == 'HGint':
                r = ar.run_hg_arm(
                    ctx, helpers, obs, arrays, truth,
                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
                    max_passes=2, record_match=False,
                )
                if r['HG']['decoded_sha'] != live['arms']['HGint']['decoded_sha']:
                    raise AssertionError(f'Timing HGint drift at {key}')
                sec_map['HGint'] = r['HG']['seconds']

        row = dict(
            kind='triggered_panel', key=list(key), order=list(order), f0_seconds=float(f0_sec),
            hg_passes=int(hg_passes), branch_seconds=sec_map,
        )
        rows_lines.append(json.dumps(row, allow_nan=False) + '\n')
        timed_rows.append(row)

        elapsed = perf_counter() - proc_start
        if elapsed >= TIMING_BUDGET_SECONDS:
            print(f'STOPPED_BUDGET in timing panel at {idx+1}/100 ({elapsed:.1f}s)', flush=True)
            sys.exit(BUDGET_EXIT_CODE)
        if (idx + 1) % 25 == 0:
            print(f'Timing {idx + 1}/100 done in {elapsed:.1f}s', flush=True)

    timing_rows_path = out / 'raw' / 'timing_rows.jsonl'
    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
    timing_rows_md5 = ar.md5_file(timing_rows_path)

    wall = perf_counter() - proc_start
    all_report_arms = ('CD', 'Z', 'HG', 'HG1') + (('HGint',) if include_hgint else ())
    cd_arr = np.array([r['branch_seconds']['CD'] for r in timed_rows], dtype=float)
    f0_arr = np.array([r['f0_seconds'] for r in timed_rows], dtype=float)
    branches = {}
    rel_cd = {}
    full_frame = {}
    for arm in all_report_arms:
        arr = np.array([r['branch_seconds'][arm] for r in timed_rows], dtype=float)
        branches[arm] = latency(arr.tolist())
        full_frame[arm] = latency((f0_arr + arr).tolist())
        if arm != 'CD':
            rel_cd[arm] = dict(
                ratio_of_means=float(arr.mean() / cd_arr.mean()),
                median_paired_ratio=float(np.median(arr / cd_arr)),
                cd_faster_fraction=float(np.mean(cd_arr < arr)),
            )

    # Exact scenario-stratified full-frame amortization using U (88/400) and G (110/400) trigger rates
    p_trig_by_s = {s: len(trig_by_s[s]) / 400.0 for s in ar.SCENARIOS}
    amortized_by_s: dict[str, dict[str, float]] = {}
    for s in ar.SCENARIOS:
        s_rows = [r for r in timed_rows if r['key'][0] == s]
        p_s = p_trig_by_s[s]
        f0_u_mean = float(np.mean(untrig_f0_sec[s]))
        f0_t_mean = float(np.mean([r['f0_seconds'] for r in s_rows]))
        amortized_by_s[s] = {
            arm: float(
                (1.0 - p_s) * f0_u_mean
                + p_s * (f0_t_mean + float(np.mean([r['branch_seconds'][arm] for r in s_rows])))
            )
            for arm in all_report_arms
        }
    amortized_full_frame_mean = {
        arm: 0.5 * (amortized_by_s['U'][arm] + amortized_by_s['G'][arm])
        for arm in all_report_arms
    }

    timing_payload = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            python_executable=sys.executable,
            threads=thread_env,
            hg_recipe=hg_recipe,
            include_hgint=include_hgint,
            panel='rho=0.30, 5.0 dB, first 50 U + first 50 G triggered keys + 25 U + 25 G untriggered F0 keys',
            timing_boundary='decision-ready (after syndrome check, before truth scoring/hashing/match)',
            keys=len(timed_rows),
            untriggered_f0_keys=len(untrig_keys),
            timing_rows_path=str(timing_rows_path),
            timing_rows_md5=timing_rows_md5,
        ),
        cpu=cpu_info,
        end_load=list(os.getloadavg()),
        wall_seconds=float(wall),
        hg_pass1_stop_count=sum(1 for r in timed_rows if r['hg_passes'] == 1),
        f0=latency(f0_arr.tolist()),
        f0_untriggered={s: latency(untrig_f0_sec[s]) for s in ar.SCENARIOS},
        branches=branches,
        relative_to_cd=rel_cd,
        triggered_full_frame=full_frame,
        trigger_rate_rho300_5db_by_scenario=p_trig_by_s,
        amortized_full_frame_mean_by_scenario=amortized_by_s,
        amortized_full_frame_mean_seconds=amortized_full_frame_mean,
    )
    ar.atomic_write_text(
        out / 'timing_summary.json',
        json.dumps(timing_payload, indent=2, allow_nan=False) + '\n',
    )

    # Atomically update summary.json and RESULTS.md so interruption can never corrupt completed main results
    summary['timing'] = timing_payload
    ar.atomic_write_text(summary_path, json.dumps(summary, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
    print(
        f'TIMING_DONE wall={wall:.1f}s '
        f'CD_med={1000*branches["CD"]["median"]:.1f}ms '
        f'HG_med={1000*branches["HG"]["median"]:.1f}ms '
        f'HG/CD_med_ratio={rel_cd["HG"]["median_paired_ratio"]:.3f}x',
        flush=True,
    )


if __name__ == '__main__':
    main()
