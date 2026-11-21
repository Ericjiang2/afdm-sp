#!/usr/bin/env python
"""C1 salvageability diagnosis: does whitened evidence ever beat geometry?

Sweeps (rho, SNR). At each cell, on the SAME held-out FINE geometric prior,
measures the marginal value of:
  - evidence  : genie_Lam_FINE - pure_geom_FINE   (correct whitened evidence vs geometry)
  - whitening : genie_Lam_FINE - white_Lam_FINE   (correct vs MISMATCHED covariance = C1 core)

Theory (C1) predicts whitening should help when the data interference is strong
and colored: low rho (more data power) and/or where C_d dominates. If both deltas
stay ~0 across the whole grid, C1 (the detection-theoretic / whitening centrepiece)
is dead and the narrative must move to the geometric prior. If they grow at low
rho / low SNR, C1 survives with a regime caveat.
"""
from __future__ import annotations
import argparse, json, time, itertools
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from afdm_sp_joint_unrolled.decision_harvest import run_harvest
from afdm_sp_joint_unrolled.decision_bound import run as bound_run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--ckpt', nargs='+', required=True)
    ap.add_argument('--rhos', nargs='+', type=float, default=[0.3, 0.5, 0.7])
    ap.add_argument('--snrs', nargs='+', type=int, default=[5, 10, 15, 20])
    ap.add_argument('--n-frames', type=int, default=400)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--p-paths', type=int, default=10)
    ap.add_argument('--M', type=int, default=48)
    ap.add_argument('--min-count', type=int, default=30)
    ap.add_argument('--keep-cache', action='store_true',
                    help='keep per-cell caches (default: delete after eval to save disk)')
    args = ap.parse_args()

    root = Path(args.out_root); root.mkdir(parents=True, exist_ok=True)
    cells = []
    t0 = time.time()
    for rho, snr in itertools.product(args.rhos, args.snrs):
        tag = f"rho{rho}_snr{snr}"
        cdir = root / tag
        print(f"\n########## CELL {tag}  ({time.time()-t0:.0f}s elapsed) ##########",
              flush=True)
        try:
            cache = run_harvest(str(cdir), snr, args.n_frames, 1024, 2.0,
                                args.p_paths, 10.0, args.fs_factor, args.M, 64,
                                seed_base=20260609, print_every=200,
                                rho_override=rho)
            res = bound_run(str(cache), args.ckpt, calib_frac=0.5, seed=0,
                            min_count=args.min_count, out=str(cdir / 'bound.json'))
            res['rho_set'] = rho
            cells.append(res)
            if not args.keep_cache:
                Path(cache).unlink(missing_ok=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            cells.append(dict(rho_set=rho, snr=snr, error=str(e)))

    # ---- summary grid ---------------------------------------------------- #
    print("\n" + "=" * 78)
    print("C1 DIAGNOSIS GRID  (value on the SAME fine geometric prior; rec@1)")
    print(f"{'rho':>5s} {'SNR':>4s} {'geomFINE':>9s} {'whiteFINE':>9s} {'genieFINE':>9s} "
          f"{'d_evid':>7s} {'d_whiten':>8s} {'head':>6s} {'head-bnd':>8s}")
    ok = [c for c in cells if 'error' not in c]
    for c in ok:
        gf = c['rec1']['pure_geom_FINE']; wf = c['rec1']['white_Lam_FINE']
        nf = c['rec1']['genie_Lam_FINE']
        print(f"{c['rho_set']:5.1f} {c['snr']:4d} {gf:9.3f} {wf:9.3f} {nf:9.3f} "
              f"{c['ev_value_rec1']:+7.3f} {c['whitening_value_rec1']:+8.3f} "
              f"{c['head_rec1']:6.3f} {c['head_minus_finebound_rec1']:+8.3f}")
    print("=" * 78)
    print("READ: d_evid>0 => whitened evidence beats pure geometry (C1 has value).")
    print("      d_whiten>0 => correct cov beats mismatched white (OMP is mismatched).")
    print("      if both ~0 across grid => C1 dead, narrative -> geometric prior.")
    print("      watch the LOW-rho / LOW-SNR corner where C1 theory predicts value.")

    (root / 'c1_sweep_summary.json').write_text(json.dumps(dict(
        rhos=args.rhos, snrs=args.snrs, n_frames=args.n_frames,
        fs_factor=args.fs_factor, cells=cells), indent=2, default=float))
    print(f"[saved] {root/'c1_sweep_summary.json'}  ({time.time()-t0:.0f}s total)")


if __name__ == '__main__':
    main()
