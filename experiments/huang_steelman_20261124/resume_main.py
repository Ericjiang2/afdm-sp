"""Resume incomplete shards under the unmodified frozen 4772365c code and cumulative 12 core-hour cap."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import sys
import time
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402
import run_main as rm  # noqa: E402


def _read_prior_cpu(path: Path) -> tuple[float, float]:
    """Read GNU time '%U %S %e' output -> (cpu_seconds, wall_seconds)."""
    parts = path.read_text(encoding='utf-8').strip().split()
    if len(parts) != 3:
        raise RuntimeError(f'Unexpected time file format in {path}: {parts!r}')
    u, s, e = float(parts[0]), float(parts[1]), float(parts[2])
    return u + s, e


def main():
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    thread_env = ar.check_thread_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--prior-cpu-file', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        parser.error(f'freeze-commit must be a 40-char lowercase hex git SHA, got {args.freeze_commit!r}')

    prior_cpu_sec, prior_wall_sec = _read_prior_cpu(args.prior_cpu_file)
    if prior_cpu_sec >= rm.CPU_LIMIT_SECONDS:
        print(f'STOPPED_BUDGET: prior CPU already at cap ({prior_cpu_sec/3600:.3f} core-hours)', flush=True)
        sys.exit(rm.BUDGET_EXIT_CODE)

    gate_bytes = args.gate.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to resume without a passing gate.json')

    live_own_md5 = ar.own_md5()
    ar.verify_freeze_commit_if_git(args.freeze_commit, live_own_md5)
    if gate['_config'].get('own_md5') != live_own_md5:
        raise RuntimeError('gate.json own_md5 does not match unmodified frozen files')
    if gate['_config'].get('archive_manifest_sha256') != ar.RHO_ARCHIVE_MD5_SHA256:
        raise RuntimeError('gate.json archive manifest SHA-256 mismatch')

    sel = gate['selected']
    hg_recipe = sel['hg_recipe']
    include_hgint = bool(sel['include_hgint'])
    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())

    out = args.out.resolve()
    raw_dir = out / 'raw'
    if not raw_dir.is_dir():
        raise RuntimeError(f'Missing raw directory: {raw_dir}')

    wall_start = time.monotonic()
    ctx, helpers = ar.load_context()
    live_p1_md5 = ar.frozen_p1_md5(ctx)
    if gate['_config'].get('frozen_extra_md5') != helpers['extra_md5']:
        raise RuntimeError('gate.json frozen_extra_md5 differs from live frozen sources')
    if gate['_config'].get('p1_source_md5') != live_p1_md5:
        raise RuntimeError('gate.json p1_source_md5 differs from live context')
    archived_rows, archive_md5 = ar.load_archived_rho_sweep()

    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
    n_triggered = 0
    for k, r in archived_rows.items():
        if k[1] in retained_rhos and r['triggered']:
            triggered_by_frame.setdefault(k[3], []).append(r)
            n_triggered += 1

    # Remove incomplete .part files and identify missing shards
    for stale in sorted(raw_dir.glob('rows_shard*.part')):
        stale.unlink()

    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::rm.WORKERS]) for idx in range(rm.WORKERS)}
    missing_shards: list[int] = []
    for idx, frames in assignments.items():
        exp_keys = {
            ar.row_key(item)
            for f in frames for item in triggered_by_frame.get(f, [])
        }
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
        if sp.exists():
            got_keys = set()
            with sp.open('r', encoding='utf-8') as handle:
                for line in handle:
                    k = ar.row_key(json.loads(line))
                    if k in got_keys:
                        raise RuntimeError(f'Duplicate key {k} in completed shard {idx:03d}')
                    got_keys.add(k)
            if got_keys != exp_keys:
                raise RuntimeError(f'Completed shard {idx:03d} key mismatch: {len(got_keys)} != {len(exp_keys)}')
        else:
            missing_shards.append(idx)

    print(
        f'Verified {rm.WORKERS - len(missing_shards)}/{rm.WORKERS} completed shards. '
        f'Resuming {len(missing_shards)} missing shards {missing_shards} '
        f'(prior_cpu={prior_cpu_sec/3600:.3f}h, cap={rm.CPU_LIMIT_SECONDS/3600:.2f}h).',
        flush=True,
    )

    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    budget_hit = False
    try:
        for idx in missing_shards:
            frames = assignments[idx]
            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
            proc = mp_ctx.Process(
                target=rm._shard_worker,
                args=(idx, frames, sub_trig, hg_recipe, include_hgint, raw_dir),
            )
            proc.start()
            running[proc.sentinel] = (idx, proc)
        while running:
            ready_list = wait(running, timeout=10.0)
            for ready in ready_list:
                idx, proc = running.pop(ready)
                proc.join()
                code = proc.exitcode
                proc.close()
                if code != 0:
                    raise RuntimeError(f'Resumed shard {idx:03d} exited with code {code}')
            live_cpu = prior_cpu_sec + rm.used_cpu_seconds() + rm._active_pids_cpu(
                [p.pid for _, p in running.values() if p.pid]
            )
            if live_cpu >= rm.CPU_LIMIT_SECONDS:
                budget_hit = True
                break
    finally:
        for _, proc in running.values():
            proc.terminate()
        for _, proc in running.values():
            proc.join()
            proc.close()

    if budget_hit or (prior_cpu_sec + rm.used_cpu_seconds()) >= rm.CPU_LIMIT_SECONDS:
        tot = prior_cpu_sec + rm.used_cpu_seconds()
        print(f'STOPPED_BUDGET: cumulative CPU limit reached ({tot/3600:.3f} core-hours)', flush=True)
        sys.exit(rm.BUDGET_EXIT_CODE)

    raw_md5: dict[str, str] = {}
    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for idx in range(rm.WORKERS):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl'
        raw_md5[sp.name] = ar.md5_file(sp)
        with sp.open('r', encoding='utf-8') as handle:
            for line in handle:
                row = json.loads(line)
                k = ar.row_key(row)
                if k in live_triggered:
                    raise RuntimeError(f'Duplicate live triggered row {k}')
                live_triggered[k] = row

    if len(live_triggered) != n_triggered:
        raise RuntimeError(f'Expected {n_triggered} triggered rows, got {len(live_triggered)}')

    ar.atomic_write_text(
        out / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw_md5.items())),
    )

    full_rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for k, arch in archived_rows.items():
        if k[1] not in retained_rhos:
            continue
        if arch['triggered']:
            full_rows[k] = live_triggered[k]
        else:
            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
            full_rows[k] = dict(
                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
                syndrome=0, triggered=False,
                arms={a: f0 for a in arms},
            )

    print(f'Running pre-registered analysis on {len(full_rows)} keys...', flush=True)
    analysis_out = an.analyze(full_rows, arms, retained_rhos, ar.SNRS, ar.MAIN_FRAMES)
    resume_cpu_sec = rm.used_cpu_seconds()
    resume_wall = time.monotonic() - wall_start
    total_cpu_sec = prior_cpu_sec + resume_cpu_sec
    if total_cpu_sec >= rm.CPU_LIMIT_SECONDS:
        print(f'STOPPED_BUDGET after aggregation ({total_cpu_sec/3600:.3f} core-hours)', flush=True)
        sys.exit(rm.BUDGET_EXIT_CODE)

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            python_executable=sys.executable,
            threads=thread_env,
            workers=rm.WORKERS,
            resumed_shards=missing_shards,
            hg_recipe=hg_recipe,
            max_passes=2,
            include_hgint=include_hgint,
            retained_rhos=list(retained_rhos),
            snrs=list(ar.SNRS),
            frames_inclusive=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
            arms=list(arms),
            total_keys=len(full_rows),
            triggered_keys=n_triggered,
            untriggered_keys=len(full_rows) - n_triggered,
            frozen_extra_md5=helpers['extra_md5'],
            p1_source_md5=live_p1_md5,
            archive_manifest_sha256=ar.RHO_ARCHIVE_MD5_SHA256,
            archived_rho_sweep_md5=archive_md5,
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
            own_md5=live_own_md5,
            gate_md5=gate_md5,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G1_keys=gate['G1']['keys_checked'],
            G2_passed=gate['G2']['passed'],
            G3a={k: {fk: fv for fk, fv in v.items() if fk != 'per_frame'} for k, v in gate['G3a'].items()},
            G3b={k: v for k, v in gate['G3b'].items() if k != 'rows'},
            G4_projected_core_hours=sel['projected_core_hours_with_margin'],
        ),
        runtime=dict(
            main_core_hours=total_cpu_sec / 3600.0,
            main_cpu_seconds=total_cpu_sec,
            initial_pass_cpu_seconds=prior_cpu_sec,
            initial_pass_wall_seconds=prior_wall_sec,
            resume_pass_cpu_seconds=resume_cpu_sec,
            resume_pass_wall_seconds=resume_wall,
            main_wall_seconds=prior_wall_sec + resume_wall,
            cpu_cap_core_hours=rm.CPU_LIMIT_SECONDS / 3600.0,
            resume_reason='Initial 24-worker pass hit conservative 1650s wall cap at 8.341 core-hours with 20/24 shards complete; remaining 4 shards resumed under identical unmodified frozen 4772365c code within the 12.0 core-hour budget.',
        ),
        analysis=analysis_out,
        timing=None,
    )
    rm.write_json(out / 'summary.json', summary)
    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
    print(
        f'MAIN_DONE Q2={analysis_out["primary"]["Q2"]["verdict"]} '
        f'Q3={analysis_out["primary"]["Q3"]["verdict"]} '
        f'cumulative_cpu_hours={total_cpu_sec/3600:.4f}',
        flush=True,
    )


if __name__ == '__main__':
    main()
