#!/usr/bin/env python
"""Gate A analysis: frame-level block bootstrap on paired per-frame error counts.

Each arm run (head / white / geom / genie) dumps perframe_snr<SNR>.npz with
per-frame (classical_errs, learned_errs). All arms share seed=20260601 -> the
frame sequence and the classical baseline are IDENTICAL across arms, so arms are
paired frame-by-frame. We test whether the LEARNED HEAD commits fewer bit errors
than each manual scorer inside the SAME F2-P loop:

  diff_f = (manual_errs_f - head_errs_f)   ( >0 => head better on frame f )

Frame-level paired bootstrap (block = frame, captures intra-frame bit
correlation that bit-level McNemar ignores) -> 95% CI on mean(diff) and the
BER-ratio, plus a frame sign-test. CI strictly > 0 => head CI-separated above
the manual scorer => HERO. CI spans 0 => THEORY (gain is F2-P, not the scorer).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

ARMS = ['head', 'white', 'geom', 'genie', 'achievable', 'covhead']


def boot_ci(diffs, n_boot=10000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    n = len(diffs)
    if n == 0:
        return dict(mean=float('nan'), lo=float('nan'), hi=float('nan'))
    idx = rng.integers(0, n, size=(n_boot, n))
    bm = diffs[idx].mean(axis=1)
    return dict(mean=float(diffs.mean()),
                lo=float(np.quantile(bm, alpha / 2)),
                hi=float(np.quantile(bm, 1 - alpha / 2)))


def boot_ratio_ci(num, den, n_boot=10000, alpha=0.05, seed=0):
    # BER ratio = sum(num)/sum(den) resampled by frame (block bootstrap).
    rng = np.random.default_rng(seed)
    n = len(num)
    idx = rng.integers(0, n, size=(n_boot, n))
    r = num[idx].sum(axis=1) / np.maximum(den[idx].sum(axis=1), 1)
    return dict(ratio=float(num.sum() / max(den.sum(), 1)),
                lo=float(np.quantile(r, alpha / 2)),
                hi=float(np.quantile(r, 1 - alpha / 2)))


def sign_test_p(diffs):
    pos = int((diffs > 0).sum()); neg = int((diffs < 0).sum())
    n = pos + neg
    if n == 0:
        return 1.0
    from scipy.stats import binomtest
    return float(binomtest(pos, n, 0.5, alternative='greater').pvalue)


def run(root, snr, n_boot=10000):
    root = Path(root)
    data = {}
    for a in ARMS:
        f = root / a / f'perframe_snr{snr}.npz'
        if not f.exists():
            print(f"[skip] missing {f}")
            continue
        d = np.load(f, allow_pickle=True)
        data[a] = dict(cls=d['classical_errs'].astype(np.int64),
                       arm=d['learned_errs'].astype(np.int64),
                       bits=int(d['bits_per_frame']))
    if 'head' not in data:
        raise SystemExit("head arm npz required")

    # Pairing sanity: classical baseline must be identical across arms.
    base = data['head']['cls']
    for a in data:
        if not np.array_equal(data[a]['cls'], base):
            print(f"[WARN] {a} classical baseline differs from head "
                  f"(sum {data[a]['cls'].sum()} vs {base.sum()}) -> NOT paired!")

    nf = len(base)
    bits_tot = data['head']['bits'] * nf
    cls_tot = int(base.sum())
    out = {'snr': snr, 'n_frames': nf, 'bits_per_frame': data['head']['bits'],
           'classical_errs': cls_tot,
           'classical_ber': cls_tot / max(bits_tot, 1), 'arms': {}}

    print(f"\n===== Gate A  SNR={snr}  ({nf} frames, classical={cls_tot} errs, "
          f"BER={cls_tot/max(bits_tot,1):.3e}) =====")
    head_e = data['head']['arm']
    for a in ARMS:
        if a not in data:
            continue
        e = data[a]['arm']
        tot = int(e.sum())
        rel = (1 - tot / max(cls_tot, 1)) * 100
        cell = dict(errs=tot, ber=tot / max(bits_tot, 1),
                    rel_vs_classical_pct=rel)
        if a != 'head':
            # diff = manual - head ; >0 => head better
            diff = (e - head_e).astype(np.float64)
            ci = boot_ci(diff, n_boot)
            sp = sign_test_p(diff)
            # head vs manual BER ratio (head/manual): <1 => head better
            rr = boot_ratio_ci(head_e.astype(np.int64), e.astype(np.int64),
                               n_boot)
            sep = ci['lo'] > 0   # head CI-separated above this manual scorer
            cell.update(dict(
                head_minus_self_per_frame=dict(
                    mean=ci['mean'], ci95=[ci['lo'], ci['hi']]),
                head_vs_self_ber_ratio=dict(
                    ratio=rr['ratio'], ci95=[rr['lo'], rr['hi']]),
                sign_test_p_head_better=sp,
                head_CI_separated_above=bool(sep)))
            print(f"  head vs {a:6s}: head={tot and head_e.sum()} "
                  f"manual_errs={tot:6d} rel_cls={rel:+.1f}%  "
                  f"Δ(manual-head)/frame={ci['mean']:+.2f} "
                  f"CI95=[{ci['lo']:+.2f},{ci['hi']:+.2f}] "
                  f"ratio(head/{a})={rr['ratio']:.3f}"
                  f"[{rr['lo']:.3f},{rr['hi']:.3f}] "
                  f"sign_p={sp:.2e}  {'HERO-sep' if sep else 'overlap'}")
        else:
            print(f"  {a:6s}        : errs={tot:6d} rel_cls={rel:+.1f}% "
                  f"BER={cell['ber']:.3e}")
        out['arms'][a] = cell

    # Gate B decision: is achievable-Λ (Ĥ⁰ cov) CI-separated ABOVE pure-geom?
    # If yes -> a realisable (non-genie) whitening scorer beats the geometry
    # prior in F2-P BER => a genuine learnable target the head does not capture.
    if 'achievable' in data and 'geom' in data:
        ach = data['achievable']['arm']; gm = data['geom']['arm']
        diff = (gm - ach).astype(np.float64)   # >0 => achievable better
        ci = boot_ci(diff, n_boot); sp = sign_test_p(diff)
        rr = boot_ratio_ci(ach.astype(np.int64), gm.astype(np.int64), n_boot)
        sep = ci['lo'] > 0
        out['achievable_vs_geom'] = dict(
            geom_minus_ach_per_frame=dict(mean=ci['mean'],
                                          ci95=[ci['lo'], ci['hi']]),
            ach_vs_geom_ber_ratio=dict(ratio=rr['ratio'],
                                       ci95=[rr['lo'], rr['hi']]),
            sign_test_p_ach_better=sp,
            achievable_CI_separated_above_geom=bool(sep))
        print(f"  >> achievable vs geom: ach={int(ach.sum())} geom={int(gm.sum())} "
              f"Δ(geom-ach)/frame={ci['mean']:+.2f} CI95=[{ci['lo']:+.2f},"
              f"{ci['hi']:+.2f}] ratio(ach/geom)={rr['ratio']:.3f}"
              f"[{rr['lo']:.3f},{rr['hi']:.3f}] sign_p={sp:.2e}  "
              f"{'ACH-SEPARATED (learnable target!)' if sep else 'overlap'}")

    # Win condition: does the TRAINED covhead beat the hand-tuned achievable-Λ
    # (and the geometry prior)? covhead better => learning the calibration pays.
    for ref in ('achievable', 'geom', 'head'):
        if 'covhead' in data and ref in data:
            cov = data['covhead']['arm']; rf = data[ref]['arm']
            diff = (rf - cov).astype(np.float64)   # >0 => covhead better
            ci = boot_ci(diff, n_boot); sp = sign_test_p(diff)
            rr = boot_ratio_ci(cov.astype(np.int64), rf.astype(np.int64), n_boot)
            sep = ci['lo'] > 0
            out[f'covhead_vs_{ref}'] = dict(
                ref_minus_cov_per_frame=dict(mean=ci['mean'],
                                             ci95=[ci['lo'], ci['hi']]),
                cov_vs_ref_ber_ratio=dict(ratio=rr['ratio'],
                                          ci95=[rr['lo'], rr['hi']]),
                sign_test_p_cov_better=sp,
                covhead_CI_separated_above=bool(sep))
            print(f"  >> covhead vs {ref:10s}: cov={int(cov.sum())} "
                  f"{ref}={int(rf.sum())} Δ({ref}-cov)/frame={ci['mean']:+.2f} "
                  f"CI95=[{ci['lo']:+.2f},{ci['hi']:+.2f}] "
                  f"ratio(cov/{ref})={rr['ratio']:.3f}[{rr['lo']:.3f},"
                  f"{rr['hi']:.3f}] sign_p={sp:.2e}  "
                  f"{'COV-WINS' if sep else 'overlap'}")

    (root / f'gateA_bootstrap_snr{snr}.json').write_text(
        json.dumps(out, indent=2, default=float))
    print(f"[saved] {root}/gateA_bootstrap_snr{snr}.json")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True,
                    help='dir containing head/ white/ geom/ genie/ subdirs')
    ap.add_argument('--snrs', nargs='+', type=int, default=[15, 20])
    ap.add_argument('--n-boot', type=int, default=10000)
    args = ap.parse_args()
    verdicts = {}
    for snr in args.snrs:
        o = run(args.root, snr, args.n_boot)
        verdicts[snr] = {a: o['arms'][a].get('head_CI_separated_above')
                         for a in ARMS if a in o['arms'] and a != 'head'}
    print("\n===== VERDICT (head CI-separated above manual scorer?) =====")
    for snr, v in verdicts.items():
        print(f"  SNR={snr}: {v}")
    sep_white = all(verdicts[s].get('white') for s in verdicts)
    print(f"\n  white-Λ separated at all SNR: {sep_white}  -> "
          f"{'HERO (learned scorer drives BER)' if sep_white else 'THEORY/partial (gain is F2-P mechanism)'}")


if __name__ == '__main__':
    main()
