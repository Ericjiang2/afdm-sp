#!/usr/bin/env python
"""Information-budget screen runner (spec research/info-budget-screen-20261014.md section 7): per-frame terms A, f, J for every condition, one JSONL row per (stage, L, frame, reference).

    python -B ib_screen_run.py --stage locate --Ls 4,8,...,96 --frames 64 --out DIR --shard i --nshard n           (plain numpy, single thread)
Frames are shared across the conditions of a (stage, L, frame, reference) (the QR of A(h) does not depend on sigma2 or rho; marginal laws per condition are unchanged).
Stage 'locate' / 'confirm' use disjoint seed streams (independent frames).  Optional report-only extras: --ray (RAY reference: A under the ray law, U, J_z), --gmi (LMMSE-GMI
column), --with-9p5 (adds the report-only 9.5 dB rho .3 condition).  Resumable: finished (L, frame) units are skipped.  Rows stay on deinlab (md5 of the gzip'd files recorded).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

import ib_screen_core as C

HERE = Path(__file__).resolve().parent
CONDS_REPORT = ((9.5, .3),)


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--stage', choices=('locate', 'confirm', 'test', 'timing'), required=True)
    ap.add_argument('--Ls', default=','.join(str(x) for x in C.LGRID))
    ap.add_argument('--frames', type=int, required=True)
    ap.add_argument('--frame0', type=int, default=0)
    ap.add_argument('--refs', default='MODEL,PHYS')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshard', type=int, default=1)
    ap.add_argument('--ray', action='store_true')
    ap.add_argument('--gmi', action='store_true')
    ap.add_argument('--with-9p5', action='store_true')
    ap.add_argument('--side', default='auto', choices=('auto', 'N', 'K'))
    args = ap.parse_args(argv)
    argv = list(sys.argv[1:] if argv is None else argv)
    if args.stage in ('locate', 'confirm') and args.frame0 != 0:
        raise ValueError('locate / confirm use frames 0..n-1 of their own seed domain')
    conds = C.CONDS + (CONDS_REPORT if args.with_9p5 else ())
    Ls = [int(x) for x in args.Ls.split(',')]
    refs = [x for x in args.refs.split(',') if x]
    args.out.mkdir(parents=True, exist_ok=True)
    consts, tab = C.Consts(), C.QpskMI()
    models = {'MODEL': C.ModelRef(), 'PHYS': C.PhysRef()}
    cfg = dict(stage=args.stage, Ls=Ls, frames=args.frames, frame0=args.frame0, refs=refs, conds=[list(c) for c in conds], ray=args.ray, gmi=args.gmi, side=args.side,
               nshard=args.nshard, seed_domain=C.SEED_DOMAIN, stage_id=C.STAGE_ID[args.stage], alpha=C.ALPHA, n_endpoints=C.n_endpoints(), delta_endpoint=C.delta_endpoint(),
               consts_md5=md5_file(C.OUT / 'consts.json'), code_md5={n: md5_file(HERE / n) for n in ('ib_screen_core.py', 'ib_screen_run.py')},
               phys_rank=models['PHYS'].r, phys_trunc_err=models['PHYS'].trunc_err, qpsk_table_node_err=tab.node_err_max)
    cpath = args.out / f'config_shard{args.shard:03d}.json'
    if cpath.exists():
        prev = json.loads(cpath.read_text())['_config']
        if {k: v for k, v in prev.items() if k != 'nshard'} != {k: v for k, v in json.loads(json.dumps(cfg)).items() if k != 'nshard'}:
            raise ValueError('resume refused: configuration differs')
    else:
        cpath.write_text(json.dumps(dict(_argv=argv, _config=cfg), indent=1))
    jpath = args.out / f'rows_shard{args.shard:03d}.jsonl'
    done = set()
    if jpath.exists():
        data = jpath.read_bytes()
        cut = data.rfind(b'\n') + 1
        if cut != len(data):
            jpath.write_bytes(data[:cut])
        for line in data[:cut].decode().splitlines():
            r = json.loads(line)
            done.add((r['L'], r['frame'], r['ref']))
    units = [(L, f) for L in Ls for f in range(args.frame0, args.frame0 + args.frames)][args.shard::args.nshard]
    t_start = time.perf_counter()
    n_done = 0
    with jpath.open('a') as h:
        for L, f in units:
            common = None
            for ref in refs + (['RAY'] if args.ray else []):
                if (L, f, ref) in done:
                    continue
                if common is None:
                    common = C.draw_common(args.stage, L, f)
                t0 = time.perf_counter()
                if ref == 'RAY':
                    o = C.ray_terms(consts, tab, models['PHYS'], args.stage, L, f, common, conds)
                    row = dict(A=o['A'].tolist(), U=o['U'].tolist(), Jz=o['Jz'].tolist())
                else:
                    o = C.frame_terms(consts, tab, models[ref], args.stage, L, f, common, conds, side=args.side, want_time=True, want_gmi=args.gmi)
                    row = dict(A=o['A'].tolist(), f=o['f'].tolist(), J=o['J'].tolist(), side=o['side'], sec_parts=o['sec'])
                    if args.gmi:
                        row['gmi'] = o['gmi'].tolist()
                row.update(stage=args.stage, L=L, frame=f, ref=ref, sec=time.perf_counter() - t0)
                h.write(json.dumps(row, allow_nan=False) + '\n')
                h.flush()
            n_done += 1
            if n_done % 16 == 0:
                print(f'[{time.perf_counter() - t_start:8.1f}s] L={L} frame={f} ({n_done}/{len(units)})', flush=True)
    rows = [json.loads(x) for x in jpath.read_text().splitlines() if x.strip()]
    (args.out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=argv, _config=cfg, shard=args.shard, n_rows=len(rows), rows_sha256=hashlib.sha256(jpath.read_bytes()).hexdigest(), wall_seconds=time.perf_counter() - t_start,
        sum_row_seconds=float(sum(r['sec'] for r in rows))), indent=1))
    print(f'shard {args.shard} done: {len(rows)} rows, {time.perf_counter() - t_start:.1f}s', flush=True)


if __name__ == '__main__':
    main()
