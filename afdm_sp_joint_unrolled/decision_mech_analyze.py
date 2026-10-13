#!/usr/bin/env python
"""Mechanism analysis for the theory-first §VII / §IV remarks.

Two modes, both reuse the paired frame-level block bootstrap from
decision_gateA_bootstrap (block = frame, captures intra-frame bit correlation):

  rho   : per-rho ratio(achievable / geom). Claim C_d ∝ (1-rho): the achievable-Λ
          advantage over the pure-geometry prior (1 - ratio) should GROW as rho
          decreases. The --integer-doppler control should collapse the advantage
          (ratio -> 1): no fractional-Doppler leakage -> no off-grid prior value.

  pool  : pool achievable + genie per-frame arrays across seed-shards at a fixed
          SNR, then ratio(achievable / genie). Self-suppression prediction: at
          high SNR ratio(ach/genie) < 1 (achievable BEATS the genie covariance,
          because the genie C contains the leaked atom's own direction and
          self-whitens the signal it should detect).

Each arm dir holds perframe_snr<SNR>.npz with paired (classical_errs,
learned_errs). Within one (rho|shard, SNR) the two scorers share seed -> identical
frames -> paired. Pooling across shards concatenates paired vectors (valid for the
ratio bootstrap, which resamples frames i.i.d.).
"""
from __future__ import annotations
import argparse, glob, json
from pathlib import Path
import numpy as np

from afdm_sp_joint_unrolled.decision_gateA_bootstrap import (
    boot_ci, boot_ratio_ci, sign_test_p)


def _load(arm_dir, snr):
    fs = glob.glob(str(Path(arm_dir) / f'perframe_snr{snr}.npz'))
    if not fs:
        return None
    d = np.load(fs[0], allow_pickle=True)
    return dict(cls=d['classical_errs'].astype(np.int64),
                arm=d['learned_errs'].astype(np.int64),
                bits=int(d['bits_per_frame']))


def _pair(num_dir, den_dir, snr, label, n_boot):
    """ratio(num/den) with num=better-if-<1. Returns row dict or None."""
    A = _load(num_dir, snr); B = _load(den_dir, snr)
    if A is None or B is None:
        print(f"[skip] {label}: missing ({num_dir} or {den_dir})")
        return None
    if not np.array_equal(A['cls'], B['cls']):
        print(f"[WARN] {label}: classical baselines differ "
              f"({A['cls'].sum()} vs {B['cls'].sum()}) -> NOT paired, skipping")
        return None
    num, den = A['arm'], B['arm']
    diff = (den - num).astype(np.float64)          # >0 => num better
    ci = boot_ci(diff, n_boot)
    rr = boot_ratio_ci(num, den, n_boot)
    sp = sign_test_p(diff)
    return dict(label=label, n_frames=len(num), cls_errs=int(A['cls'].sum()),
                num_errs=int(num.sum()), den_errs=int(den.sum()),
                ratio=rr['ratio'], ratio_ci=[rr['lo'], rr['hi']],
                delta_per_frame=ci['mean'], delta_ci=[ci['lo'], ci['hi']],
                sign_p=sp, num_separated_below=bool(rr['hi'] < 1.0))


def mode_rho(args):
    """ratio(achievable/geom) per rho + integer-Doppler control."""
    rows = []
    # explicit reference rho=0.5 (frac) from the firm Gate-B dir, if given
    if args.ref05_geom and args.ref05_ach:
        r = _pair(args.ref05_ach, args.ref05_geom, args.snr,
                  'rho0.5(frac,ref)', args.n_boot)
        if r:
            rows.append(r)
    root = Path(args.root)
    for gdir in sorted(glob.glob(str(root / 'rho*_geom'))):
        rho = Path(gdir).name.replace('rho', '').replace('_geom', '')
        adir = str(root / f'rho{rho}_achievable')
        r = _pair(adir, gdir, args.snr, f'rho{rho}', args.n_boot)
        if r:
            rows.append(r)
    # integer-Doppler control
    igd = root / 'intdopp_geom'; iad = root / 'intdopp_achievable'
    if igd.exists() and iad.exists():
        r = _pair(str(iad), str(igd), args.snr, 'intDopp(rho0.5)', args.n_boot)
        if r:
            rows.append(r)

    rows.sort(key=lambda x: (0 if 'intDopp' in x['label'] else 1,
                             x['label']))
    print(f"\n===== Mechanism: ratio(achievable/geom) @ SNR={args.snr} "
          f"(<1 => achievable beats geom prior) =====")
    print(f"{'config':18s} {'frames':>6} {'cls':>6} {'ach':>6} {'geom':>6} "
          f"{'ratio':>7} {'ratio_CI95':>18} {'sign_p':>9} {'sep?':>5}")
    for r in rows:
        print(f"{r['label']:18s} {r['n_frames']:>6} {r['cls_errs']:>6} "
              f"{r['num_errs']:>6} {r['den_errs']:>6} {r['ratio']:>7.3f} "
              f"[{r['ratio_ci'][0]:.3f},{r['ratio_ci'][1]:.3f}]".rjust(19)
              + f" {r['sign_p']:>9.2e} "
              + ('  yes' if r['num_separated_below'] else '   no'))
    out = Path(args.out) if args.out else root / f'mech_rho_snr{args.snr}.json'
    out.write_text(json.dumps(rows, indent=2, default=float))
    print(f"[saved] {out}")


def mode_pool(args):
    """Pool achievable + genie across shard dirs, ratio(achievable/genie)."""
    ach_cls, ach_e, gen_cls, gen_e = [], [], [], []
    bits = None
    for sd in args.shards:
        A = _load(Path(sd) / 'achievable', args.snr)
        G = _load(Path(sd) / 'genie', args.snr)
        if A is None or G is None:
            print(f"[skip shard] {sd}: missing achievable or genie")
            continue
        if not np.array_equal(A['cls'], G['cls']):
            print(f"[WARN shard] {sd}: ach/genie not paired "
                  f"({A['cls'].sum()} vs {G['cls'].sum()}) -> skipping")
            continue
        ach_cls.append(A['cls']); ach_e.append(A['arm'])
        gen_cls.append(G['cls']); gen_e.append(G['arm'])
        bits = A['bits']
        print(f"[shard] {sd}: nfr={len(A['arm'])} cls={A['cls'].sum()} "
              f"ach={A['arm'].sum()} genie={G['arm'].sum()}")
    if not ach_e:
        raise SystemExit("no usable shards")
    ach = np.concatenate(ach_e); gen = np.concatenate(gen_e)
    cls = np.concatenate(ach_cls)
    diff = (gen - ach).astype(np.float64)          # >0 => achievable better
    ci = boot_ci(diff, args.n_boot)
    rr = boot_ratio_ci(ach, gen, args.n_boot)
    sp = sign_test_p(diff)
    out = dict(snr=args.snr, n_frames=len(ach), n_shards=len(ach_e),
               classical_errs=int(cls.sum()), bits_per_frame=bits,
               achievable_errs=int(ach.sum()), genie_errs=int(gen.sum()),
               ratio_ach_over_genie=rr['ratio'],
               ratio_ci95=[rr['lo'], rr['hi']],
               genie_minus_ach_per_frame=dict(mean=ci['mean'],
                                              ci95=[ci['lo'], ci['hi']]),
               sign_test_p_ach_better=sp,
               self_suppression_confirmed=bool(rr['hi'] < 1.0))
    print(f"\n===== Self-suppression @ SNR={args.snr}: pooled "
          f"{len(ach)} frames / {len(ach_e)} shards (classical={int(cls.sum())}) "
          f"=====")
    print(f"  achievable={int(ach.sum())}  genie={int(gen.sum())}  "
          f"ratio(ach/genie)={rr['ratio']:.3f} CI95=[{rr['lo']:.3f},{rr['hi']:.3f}]")
    print(f"  Δ(genie-ach)/frame={ci['mean']:+.3f} CI95=[{ci['lo']:+.3f},"
          f"{ci['hi']:+.3f}]  sign_p={sp:.2e}")
    print(f"  >> self-suppression (achievable CI-beats genie): "
          f"{'CONFIRMED' if out['self_suppression_confirmed'] else 'overlap (underpowered or null)'}")
    op = Path(args.out) if args.out else Path(args.shards[0]).parent / f'selfsupp_snr{args.snr}.json'
    op.write_text(json.dumps(out, indent=2, default=float))
    print(f"[saved] {op}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('rho')
    a.add_argument('--root', required=True)
    a.add_argument('--snr', type=int, default=15)
    a.add_argument('--ref05-geom', default=None)
    a.add_argument('--ref05-ach', default=None)
    a.add_argument('--n-boot', type=int, default=10000)
    a.add_argument('--out', default=None)
    a.set_defaults(func=mode_rho)
    b = sub.add_parser('pool')
    b.add_argument('--shards', nargs='+', required=True,
                   help='dirs each containing achievable/ and genie/ subdirs')
    b.add_argument('--snr', type=int, default=20)
    b.add_argument('--n-boot', type=int, default=10000)
    b.add_argument('--out', default=None)
    b.set_defaults(func=mode_pool)
    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
