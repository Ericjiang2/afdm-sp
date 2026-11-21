#!/usr/bin/env python3
"""Idea-funnel L2 diagnostic for card I-20261121-l04 and its child (2026-11-21, runner l).
Reads out2/l04_rows.jsonl.gz and recomputes, for the 13 failed frames, (a) whether same-codeword re-send failures
come with a wrong round-0 support, (b) a transmitter-computable data-pilot cross-ambiguity peak for the original
codeword and for the 8 alternative codewords used in the l04 run.  Reuses l2_batch2 / stageA setup; no decoding.
  python l2_slm_diag.py --out out2/slm_diag.json
"""
import argparse, gzip, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch2 as b2  # noqa: E402
from l2_batch2 import setup, SCENARIOS, CFG  # noqa: E402


def xamb_atoms(C, n):
    """Unit-norm pilot atoms at relative offsets dl in [-lmax, lmax], dk in [-4, 4] step .5 (delay 0 Doppler 0 excluded)."""
    from physical import regressors
    s = C['ctx'].system; lmax = C['lmax']
    dl = np.repeat(np.arange(-lmax, lmax + 1), 17); dk = np.tile(np.arange(-4, 4.01, .5), 2 * lmax + 1)
    keep = ~((dl == 0) & (np.abs(dk) < 1e-9)); dl, dk = dl[keep], dk[keep]
    U = regressors(np.asarray(s._zc_seq), dl % n, dk, s.c1, s.c2)
    return U / np.linalg.norm(U, axis=0, keepdims=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l04']
    rows = [json.loads(l) for l in gzip.open(HERE / 'out2' / 'l04_rows.jsonl.gz', 'rt')]
    sr = dict(A_fail=[0, 0], A_ok=[0, 0], B_fail=[0, 0], B_ok=[0, 0])
    for r in rows:
        for x in r['reps']:
            for arm in 'AB':
                k = f"{arm}_{'fail' if x[arm]['errors'] > 0 else 'ok'}"; sr[k][0] += int(x[arm]['support_right']); sr[k][1] += 1
    U = None; per = []
    for r in rows:
        s_, frame = r['scenario'], r['frame']
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, cfg['rho']), cfg['rho'], cfg['snr'])
        n = len(obs['y'])
        if U is None:
            U = xamb_atoms(C, n)
        def peak(d):
            z = np.abs(U.conj().T @ d) ** 2 / (np.vdot(d, d).real / n)
            return float(z.max()), float(np.sort(z)[-10:].mean())
        orig = peak(np.asarray(raw['data'], complex)); alts = []
        for j in range(cfg['repeats']):
            raw2, _, _ = stage3.observed(ctx, stage3.inputs(ctx, frame + cfg['frame_offset'] * (j + 1), s_, cfg['rho']), cfg['rho'], cfg['snr'])
            alts.append(peak(np.asarray(raw2['data'], complex)))
        a_fail = sum(x['A']['errors'] > 0 for x in r['reps'])
        per.append(dict(scenario=s_, frame=frame, A_fail=a_fail, orig_peak=orig[0], orig_top10=orig[1],
                        alt_peak_median=float(np.median([x[0] for x in alts])), alt_top10_median=float(np.median([x[1] for x in alts])),
                        rank_of_orig_peak=int(1 + sum(x[0] > orig[0] for x in alts)), rank_of_orig_top10=int(1 + sum(x[1] > orig[1] for x in alts)),
                        alt_fail=[int(x['B']['errors'] > 0) for x in r['reps']], alt_peaks=[x[0] for x in alts]))
    o = dict(_argv=sys.argv, atoms=int(U.shape[1]), support_right_share=sr, frames=per)
    Path(a.out).write_text(json.dumps(o, indent=1))
    print(json.dumps(dict(atoms=o['atoms'], support_right_share=sr), indent=1))
    for p in per:
        print(p['scenario'], p['frame'], 'A_fail', p['A_fail'], 'orig peak %.2f top10 %.2f | alt median peak %.2f top10 %.2f | rank of orig (1 = highest of 9): peak %d top10 %d' %
              (p['orig_peak'], p['orig_top10'], p['alt_peak_median'], p['alt_top10_median'], p['rank_of_orig_peak'], p['rank_of_orig_top10']))


if __name__ == '__main__':
    main()
