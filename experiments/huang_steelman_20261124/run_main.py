"""Execute the frozen Huang-2010-style steelman main run over all archived F0-triggered keys, then aggregate."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import resource
import sys
import time
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402

WORKERS = 24
CPU_LIMIT_SECONDS = 12.0 * 3600.0
BUDGET_EXIT_CODE = 124


@contextmanager
def publish(path: Path, *, buffering: int = -1):
    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
    with partial.open('x', encoding='utf-8', buffering=buffering) as handle:
        yield handle
        handle.flush()
        os.fsync(handle.fileno())
    os.link(partial, path)
    partial.unlink()


def write_json(path: Path, value: Any):
    ar.atomic_write_text(path, json.dumps(value, indent=2, allow_nan=False) + '\n')


def _shard_worker(
    shard_idx: int,
    frames: tuple[int, ...],
    triggered_by_frame: dict[int, list[dict[str, Any]]],
    hg_recipe: str,
    include_hgint: bool,
    raw_dir: Path,
):
    ctx, helpers = ar.load_context()
    stage3 = helpers['stage3']
    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    shard_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl'
    count = 0
    with publish(shard_path, buffering=1) as handle:
        for frame in frames:
            items = triggered_by_frame.get(frame, [])
            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
            for item in items:
                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
            for (s, rho), grp in sorted(grouped.items()):
                base = stage3.inputs(ctx, frame, s, rho)
                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
                    snr = int(item['snr_centi_db'])
                    key = (s, rho, snr, frame)
                    t_key = time.process_time()
                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
                    inp = stage3.input_record(raw, obs)
                    if inp != item['inputs']:
                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
                    f0 = stage3.decoded(ctx, dec, truth)
                    if syn != int(item['syndrome']) or f0 != dict(
                        errors=int(item['arms']['F0']['errors']),
                        decoded_sha=item['arms']['F0']['decoded_sha'],
                    ):
                        raise RuntimeError(f'Live F0 diverged from archive at {key}')

                    hg_out = ar.run_hg_arm(
                        ctx, helpers, obs, arrays, truth,
                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
                        max_passes=2, record_match=True,
                    )
                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)

                    arch_cd = item['arms']['CD']
                    cd_paths = arch_cd['state']['paths']
                    cd_match = ar.match_paths_1to1(
                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
                    )

                    arm_records = dict(
                        F0=f0,
                        CD=dict(
                            errors=int(arch_cd['errors']),
                            decoded_sha=arch_cd['decoded_sha'],
                            paths=cd_paths,
                            match_refined=cd_match,
                        ),
                        HG=hg_out['HG'],
                        HG1=hg_out['HG1'],
                        Z=z_out,
                    )
                    if include_hgint:
                        hgint_out = ar.run_hg_arm(
                            ctx, helpers, obs, arrays, truth,
                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
                            max_passes=2, record_match=True,
                        )
                        arm_records['HGint'] = hgint_out['HG']

                    row = dict(
                        scenario=s,
                        rho_permille=rho,
                        snr_centi_db=snr,
                        frame=frame,
                        syndrome=int(syn),
                        triggered=True,
                        cpu_seconds=float(time.process_time() - t_key),
                        arms=arm_records,
                    )
                    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
                    count += 1
    print(f'Shard {shard_idx:03d} completed ({count} triggered keys)', flush=True)


def used_cpu_seconds() -> float:
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + ch.ru_utime + ch.ru_stime


def _active_pids_cpu(pids: list[int]) -> float:
    """Sum utime+stime (in seconds) of live worker PIDs from /proc/<pid>/stat on Linux."""
    clk = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    total = 0.0
    for pid in pids:
        try:
            txt = Path(f'/proc/{pid}/stat').read_text()
            rparen = txt.rfind(')')
            fields = txt[rparen + 2:].split()
            total += (int(fields[11]) + int(fields[12])) / clk
        except OSError:
            pass
    return total


def main():
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter on deinlab: {sys.executable}')
    thread_env = ar.check_thread_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--workers', type=int, default=WORKERS)
    args = parser.parse_args()
    if not 1 <= args.workers <= 32:
        parser.error('workers must be in 1..32')
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        parser.error(f'freeze-commit must be a 40-char lowercase hex git SHA, got {args.freeze_commit!r}')

    gate_bytes = args.gate.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to launch main run without a passing gate.json')

    # Bind gate receipt strictly to the exact current deployed code, protocol, and frozen dependencies
    live_own_md5 = ar.own_md5()
    ar.verify_freeze_commit_if_git(args.freeze_commit, live_own_md5)
    if gate['_config'].get('own_md5') != live_own_md5:
        raise RuntimeError('gate.json own_md5 does not match current deployed files; re-run gates first')
    if gate['_config'].get('archive_manifest_sha256') != ar.RHO_ARCHIVE_MD5_SHA256:
        raise RuntimeError('gate.json archive manifest SHA-256 mismatch')

    sel = gate['selected']
    hg_recipe = sel['hg_recipe']
    include_hgint = bool(sel['include_hgint'])
    retained_rhos = tuple(int(r) for r in sel['retained_rhos'])
    arms = ('F0', 'CD', 'HG', 'HG1', 'Z') + (('HGint',) if include_hgint else ())

    out = args.out.resolve()
    raw_dir = out / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    if list(raw_dir.glob('rows_shard*.jsonl*')):
        raise RuntimeError(f'Output raw directory already contains shards: {raw_dir}')

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

    print(
        f'Validated archive, gate binding, and frozen sources. Launching {args.workers} workers on '
        f'{n_triggered} triggered keys (recipe={hg_recipe}, include_hgint={include_hgint}, rhos={retained_rhos}).',
        flush=True,
    )

    assignments = {idx: tuple(ar.MAIN_FRAMES[idx::args.workers]) for idx in range(args.workers)}
    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    budget_hit = False
    try:
        for idx, frames in assignments.items():
            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
            proc = mp_ctx.Process(
                target=_shard_worker,
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
                    raise RuntimeError(f'Shard {idx:03d} exited with code {code}')
            # Live CPU budget monitoring across finished + active workers
            live_cpu = used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= CPU_LIMIT_SECONDS:
                budget_hit = True
                break
    finally:
        for _, proc in running.values():
            proc.terminate()
        for _, proc in running.values():
            proc.join()
            proc.close()

    if budget_hit or used_cpu_seconds() >= CPU_LIMIT_SECONDS:
        print(f'STOPPED_BUDGET: CPU limit reached ({used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    raw_md5: dict[str, str] = {}
    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
    for idx in range(args.workers):
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
    total_cpu_sec = used_cpu_seconds()
    total_wall = time.monotonic() - wall_start
    if total_cpu_sec >= CPU_LIMIT_SECONDS:
        print(f'STOPPED_BUDGET after aggregation ({total_cpu_sec/3600:.3f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
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
            main_wall_seconds=total_wall,
            cpu_cap_core_hours=CPU_LIMIT_SECONDS / 3600.0,
        ),
        analysis=analysis_out,
        timing=None,
    )
    write_json(out / 'summary.json', summary)
    ar.atomic_write_text(out / 'RESULTS.md', an.render_results_md(summary))
    print(
        f'MAIN_DONE Q2={analysis_out["primary"]["Q2"]["verdict"]} '
        f'Q3={analysis_out["primary"]["Q3"]["verdict"]} '
        f'cpu_hours={total_cpu_sec/3600:.4f}',
        flush=True,
    )


if __name__ == '__main__':
    main()
