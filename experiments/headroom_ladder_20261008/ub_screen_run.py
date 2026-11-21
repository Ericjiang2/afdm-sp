#!/usr/bin/env python
"""Upper-bound screen runner (spec research/ub-screen-20261015.md section 7): per-frame f, J and u = J + Cst - f for every condition, one JSONL row per (stage, L, frame, reference).

    python -B ub_screen_run.py --stage decision|ro|grid|timing --refs MODEL,PHYS,RAY --Ls ... --frames n --out DIR --shard i --nshard k [--with-9p5]      (plain numpy, single thread)
Frames are shared across the conditions of a (stage, ref, L, frame); every stage has its own seed stream (ub_screen_core.STAGE_ID), so decision / ro / grid frames are independent.
Decision stage: the 5 frozen conditions; ro and grid add the report-only 9.5 dB rho .3 condition via --with-9p5.  Resumable: finished (L, frame, ref) units are skipped.
Rows stay on deinlab (gzip'd after aggregation; md5 of the .gz recorded).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import ib_screen_core as C
import ub_screen_core as U

HERE = Path(__file__).resolve().parent
CODE_FILES = ('ub_screen_core.py', 'ub_screen_run.py', 'ib_screen_core.py')


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--stage', choices=('decision', 'ro', 'grid', 'timing'), required=True)
    ap.add_argument('--Ls', default='')
    ap.add_argument('--frames', type=int, required=True)
    ap.add_argument('--refs', default='MODEL,PHYS,RAY')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshard', type=int, default=1)
    ap.add_argument('--with-9p5', action='store_true')
    args = ap.parse_args(argv)
    argv = list(sys.argv[1:] if argv is None else argv)
    conds = U.CONDS + ((U.COND_REPORT,) if args.with_9p5 else ())
    default_Ls = {'decision': U.decision_Ls(), 'ro': U.ro_Ls(), 'grid': list(C.LGRID), 'timing': [28, 43]}[args.stage]
    Ls = [int(x) for x in args.Ls.split(',') if x] or default_Ls
    refs = [x for x in args.refs.split(',') if x]
    args.out.mkdir(parents=True, exist_ok=True)
    consts = C.Consts()
    models = {'MODEL': C.ModelRef(), 'PHYS': C.PhysRef(), 'RAY': U.RayRef()}
    cfg = dict(stage=args.stage, Ls=Ls, frames=args.frames, refs=refs, conds=[list(c) for c in conds], with_9p5=args.with_9p5, nshard=args.nshard,
               seed_root=U.SEED_ROOT, seed_domain=U.SEED_DOMAIN, stage_id=U.STAGE_ID[args.stage], stage_ids=U.STAGE_ID, comp_ids=U.COMP, alpha=U.ALPHA, n_endpoints=U.N_ENDPOINTS,
               delta_endpoint=U.delta_endpoint(), k_switch=U.K_SWITCH, consts_md5=md5_file(C.OUT / 'consts.json'), code_md5={n: md5_file(HERE / n) for n in CODE_FILES},
               phys_rank=models['PHYS'].r, phys_trunc_err=models['PHYS'].trunc_err)
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
    units = [(L, f) for L in Ls for f in range(args.frames)][args.shard::args.nshard]
    t_start = time.perf_counter()
    n_done = 0
    with jpath.open('a') as h:
        for L, f in units:
            common = None
            for ref in refs:
                if (L, f, ref) in done:
                    continue
                if common is None:
                    common = U.draw_common(args.stage, L, f)
                o = U.frame_u(consts, models[ref], args.stage, L, f, conds, common)
                row = dict(stage=args.stage, L=L, frame=f, ref=ref, f=o['f'].tolist(), J=o['J'].tolist(), u=o['u'].tolist(), sec=o['sec'])
                row.update({k: o[k] for k in ('rank', 'side') if k in o})
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
