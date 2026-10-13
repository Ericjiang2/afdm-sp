#!/usr/bin/env python
"""eval_listwise_envelope.py — 5-seed paired-eval orchestrator + aggregator.

For each seed:
    runs paired_learned_eval with the listwise ckpt at fixed eval seed,
    saving results.json to outputs_listwise_eval/seed_<N>/.

Then aggregates per-SNR mean/std BER across seeds and writes
outputs_listwise_eval/envelope.json + .md.

Closes FYP R3 W-2 (single-checkpoint, no retraining variance) +
W-3 (BCE+rank-hinge train vs top-K_add deploy misalignment) by giving
both a 5-seed envelope AND alignment between train and deploy objectives.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import subprocess
import sys
import time


def run_one_seed(ckpt: pathlib.Path, out: pathlib.Path,
                 snr_list: list[int], frames: int, eval_seed: int,
                 fs_factor: float = 4.0) -> int:
    cmd = [
        sys.executable,
        'afdm_sp_joint_unrolled/paired_learned_eval.py',
        '--ckpt', str(ckpt),
        '--variant', 'C2-rel',
        '--mp-mode', 'bp', '--pic-damp', '0.5',
        '--p-paths', '8', '--tau-spread', '0.010',
        '--n-total', '1024', '--v-mean', '2.0',
        '--fs-factor', str(fs_factor),
        '--snr-list', *[str(s) for s in snr_list],
        '--frames-per-snr', str(frames),
        '--refine-rounds', '2', '--cand-topm', '96',
        '--defer-prune-until-final', '--protect-added', '2',
        '--seed', str(eval_seed),
        '--cdtype', 'complex64',
        '--out', str(out),
    ]
    print(f'[run] {" ".join(cmd)}', flush=True)
    return subprocess.call(cmd)


def aggregate(eval_dirs: list[pathlib.Path], snr_list: list[int]
              ) -> dict:
    per_seed = {}
    for d in eval_dirs:
        rj = d / 'results.json'
        if not rj.exists():
            print(f'[warn] missing {rj}')
            continue
        per_seed[d.name] = json.loads(rj.read_text())

    out = {'snr_list': snr_list, 'n_seeds': len(per_seed),
           'per_snr': {}, 'per_seed': per_seed}
    for snr in snr_list:
        snr_str = str(snr)
        cls_bers = []; lrn_bers = []
        for name, r in per_seed.items():
            if snr_str in r:
                cls_bers.append(float(r[snr_str].get('classical_ber',
                                                       float('nan'))))
                lrn_bers.append(float(r[snr_str].get('learned_ber',
                                                       float('nan'))))
        n_valid = sum(1 for x in lrn_bers if x == x)
        out['per_snr'][snr_str] = dict(
            n_seeds=len(lrn_bers),
            classical_mean=statistics.fmean([x for x in cls_bers if x == x] or [float('nan')]),
            learned_mean=statistics.fmean([x for x in lrn_bers if x == x] or [float('nan')]),
            learned_std=(statistics.stdev([x for x in lrn_bers if x == x])
                         if n_valid >= 2 else float('nan')),
            learned_min=min((x for x in lrn_bers if x == x), default=float('nan')),
            learned_max=max((x for x in lrn_bers if x == x), default=float('nan')),
            per_seed_learned=lrn_bers,
        )
    return out


def render_md(env: dict) -> str:
    lines = [
        '# Listwise 5-seed eval envelope', '',
        f'Seeds: {env["n_seeds"]}  | SNR list: {env["snr_list"]}', '',
        '| SNR (dB) | classical BER | learned mean BER | learned std | learned [min, max] | per-seed learned |',
        '|---|---|---|---|---|---|',
    ]
    for snr in env['snr_list']:
        s = env['per_snr'].get(str(snr), {})
        if not s:
            continue
        per_seed_str = ', '.join(f'{x:.3e}' if x == x else 'nan'
                                  for x in s['per_seed_learned'])
        lines.append(
            f'| {snr} | {s["classical_mean"]:.3e} | {s["learned_mean"]:.3e} '
            f'| {s["learned_std"]:.3e} | [{s["learned_min"]:.3e}, '
            f'{s["learned_max"]:.3e}] | {per_seed_str} |'
        )
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt-root', required=True,
                    help='dir with seed_<N>/ckpt_listwise.pt subdirs')
    ap.add_argument('--out-root', required=True,
                    help='dir to write per-seed eval results into')
    ap.add_argument('--snr-list', nargs='+', type=int,
                    default=[20, 25, 30])
    ap.add_argument('--frames', type=int, default=100)
    ap.add_argument('--eval-seed', type=int, default=20260423)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--skip-eval', action='store_true',
                    help='skip per-seed eval and just aggregate existing dirs')
    args = ap.parse_args()

    ckpt_root = pathlib.Path(args.ckpt_root)
    out_root = pathlib.Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    eval_dirs = []

    seed_dirs = sorted(ckpt_root.glob('seed_*'))
    if not seed_dirs:
        raise SystemExit(f'no seed_* under {ckpt_root}')

    if not args.skip_eval:
        t0 = time.time()
        for sd in seed_dirs:
            ckpt = sd / 'ckpt_listwise.pt'
            if not ckpt.exists():
                print(f'[skip] no ckpt at {ckpt}')
                continue
            out = out_root / sd.name
            if (out / 'results.json').exists():
                print(f'[skip] eval already done at {out}')
                eval_dirs.append(out)
                continue
            rc = run_one_seed(ckpt, out, args.snr_list, args.frames,
                               args.eval_seed, fs_factor=args.fs_factor)
            if rc != 0:
                print(f'[fail] eval rc={rc} for {sd.name}')
            else:
                eval_dirs.append(out)
        print(f'[run] all seeds done in {time.time() - t0:.0f}s', flush=True)
    else:
        eval_dirs = [out_root / sd.name for sd in seed_dirs
                     if (out_root / sd.name / 'results.json').exists()]

    env = aggregate(eval_dirs, args.snr_list)
    (out_root / 'envelope.json').write_text(json.dumps(env, indent=2))
    (out_root / 'envelope.md').write_text(render_md(env))
    print(f'\n=== envelope ===\n{render_md(env)}', flush=True)


if __name__ == '__main__':
    main()
