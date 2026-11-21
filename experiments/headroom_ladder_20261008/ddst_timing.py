#!/usr/bin/env python
"""Stage-1 cost estimate from a timing run of ddst_driver.py (2 frames x L in {8, 16, 32, 40}, all four arms, one quiet single-thread process).

Per (frame, cell, L) block the driver spends: sum over arms of the receiver seconds (rows' `seconds`) + generator overhead (messages, c1_base, DDST
precoding, scoring; measured as the remainder of the shard wall time) ; per (frame, L) once more the Tx side (interference matrix + eigendecomposition,
shared by all cells containing L).  Stage-1 estimate: the S1 cells x 200 frames, per-arm seconds linearly interpolated in L (np.interp).
  usage: ddst_timing.py <dir with rows_shard000.jsonl, results_shard000.json>
"""
import json
import sys
from pathlib import Path

import numpy as np

S1_CELLS = [(6.5, [8, 12, 16, 20, 24, 28, 32]), (8.0, [16, 20, 24, 28, 32, 36, 40])]
FRAMES = 200


def main(d):
    d = Path(d)
    rows = [json.loads(x) for x in (d / 'rows_shard000.jsonl').read_text().splitlines() if x.strip()]
    res = json.loads((d / 'results_shard000.json').read_text())
    assert all(r['status'] == 'ok' for r in rows)
    Ls = sorted({r['L'] for r in rows})
    arms = sorted({r['arm'] for r in rows})
    per = {a: [np.mean([r['seconds'] for r in rows if r['arm'] == a and r['L'] == L]) for L in Ls] for a in arms}
    tx = [np.mean([r['sec_tx_M'] + r['sec_tx_eig'] for r in rows if r['arm'] == 'DDST-A' and r['L'] == L]) for L in Ls]
    blocks = len({(r['frame'], r['L']) for r in rows})
    arm_sum = sum(r['seconds'] for r in rows)
    tx_sum = sum(r['sec_tx_M'] + r['sec_tx_eig'] for r in rows if r['arm'] == 'DDST-A')
    overhead = (res['wall_seconds'] - arm_sum - tx_sum) / blocks
    est = {}
    for name, use in (('3 arms (SPg_flat, DDST-A, DDST-N)', ['SPg_flat', 'DDST-A', 'DDST-N']), ('4 arms (+ DDST-A-blind)', arms)):
        total = 0.
        all_L = sorted({L for _, Lc in S1_CELLS for L in Lc})
        for snr, Lc in S1_CELLS:
            for L in Lc:
                total += sum(np.interp(L, Ls, per[a]) for a in use) + overhead
        total += sum(np.interp(L, Ls, tx) for L in all_L)
        est[name] = dict(sec_per_frame=total, core_hours=total * FRAMES / 3600.)
    out = dict(_argv=sys.argv, _config=dict(source_dir=str(d), s1_cells=S1_CELLS, frames_per_cell=FRAMES, driver_argv=json.loads((d / 'config_shard000.json').read_text())['_argv'],
                                           interpolation='np.interp in L over the measured L'), L=Ls, receiver_seconds_per_arm={a: dict(zip(map(str, Ls), v)) for a, v in per.items()}, tx_seconds=dict(zip(map(str, Ls), tx)),
               overhead_per_block=overhead, n_blocks=blocks, wall_seconds=res['wall_seconds'], stage1_estimate=est, frames_per_cell=FRAMES)
    (d / 'timing.json').write_text(json.dumps(out, indent=1, default=float))
    lines = ['# DDST Stage-1 cost estimate (timing run: frames 7100-7101, one single-thread process, quiet server)', '',
             '| L | ' + ' | '.join(arms) + ' | Tx (M + eig) |', '|---|' + '---|' * (len(arms) + 1)]
    for i, L in enumerate(Ls):
        lines.append(f'| {L} | ' + ' | '.join(f'{per[a][i]:.2f} s' for a in arms) + f' | {tx[i]:.2f} s |')
    lines += ['', f'Generator/scoring overhead per (frame, cell, L) block: {overhead:.2f} s (remainder of the shard wall time {res["wall_seconds"]:.1f} s over {blocks} blocks).', '']
    for k, v in est.items():
        lines.append(f'- {k}: {v["sec_per_frame"]:.1f} s per frame over the 14 cells, x {FRAMES} frames = **{v["core_hours"]:.2f} core-hours** (budget 20).')
    (d / 'TIMING.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main(sys.argv[1])
