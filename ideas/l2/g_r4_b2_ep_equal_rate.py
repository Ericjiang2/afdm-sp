#!/usr/bin/env python3
"""L2 paired verification for I-20261122-g21 on deinlab.
Strictly reuses frozen experiments/tcom_reference_frame_20261015/{ep_rx, p2b_driver, p2b_agg, gen_fixed, p1_driver}
without editing any frozen file:
  0. Implementation Gate: runs unmodified ep_rx (d_v=3, d_c=6, seed=20260726, k=767, rho_EP=0.20)
     on 8 archived keys from out/p2b_test/rows_shard000.jsonl.gz and asserts 100% bit-exact match.
  1. Disjoint Dev Selection: on ENTROPY_DEV / DOMAIN_DEV (frames 0..499 at 6.0 dB, Scenario S),
     evaluates EP_r23 (build_code(1530, d_v=3, d_c=9, seed=20260726), k=1022) across rho_EP in
     (0.05, 0.10, 0.15, 0.20, 0.30) and selects rho_EP* by p2b_agg.dev_select (max goodput, tie->smaller).
     Also evaluates the original 4-point grid (0.05, 0.10, 0.20, 0.30) and keeps untuned rho_EP=0.20 as control.
  2. Paired Test Run: on ENTROPY_TEST / DOMAIN_TEST (frames 0..499 x 8 SNRs 4.5..8.0 dB = 4,000 keys),
     runs EP_r23(rho_EP*), EPG_r23(rho_EP*), and untuned control EP_r23(0.20), pairs frame-by-frame
     against archived out/p2b_test/ rows (B_r300, B_r500, F0_r300, F0_r500, A3_r300, A3_r500, SPG_r300,
     SPG_r500, EP_k767, EPG_k767), and runs exact p2b_agg.analyze (B=20000 cluster bootstrap, seed=20261016).
"""
from __future__ import annotations

import os
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_k] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import argparse
from concurrent.futures import ProcessPoolExecutor
import glob
import gzip
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
EXP_DIR = PROJECT / 'experiments' / 'tcom_reference_frame_20261015'
sys.path.insert(0, str(EXP_DIR))

import ep_rx as E  # noqa: E402
import gen_fixed  # noqa: E402
import p1_driver as P  # noqa: E402
import p2b_agg as AGG  # noqa: E402
import p2b_driver as PD  # noqa: E402

SNRS_CENTI = (450, 500, 550, 600, 650, 700, 750, 800)
DEV_RHO_GRID5 = (0.05, 0.10, 0.15, 0.20, 0.30)
DEV_RHO_GRID4 = (0.05, 0.10, 0.20, 0.30)

_G = {}


def _init_worker(cache_dir_str: str):
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[k] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    ctx = P.load_context()
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    cdir = Path(cache_dir_str)
    code23 = build_code(E.CODE_N, d_v=3, d_c=9, seed=E.CODE_SEED, cache_dir=cdir)
    _G['ctx'] = ctx
    _G['ep23'] = E.EP(ctx.system, code23)
    _G['seed_dev'] = P.make_seed_fn(PD.ENTROPY_DEV, PD.DOMAIN_DEV)
    _G['seed_test'] = P.make_seed_fn(PD.ENTROPY_TEST, PD.DOMAIN_TEST)


def _dev_frame_worker(frame: int):
    ctx, ep23, seed_fn = _G['ctx'], _G['ep23'], _G['seed_dev']
    raw0, _ = P.generate(ctx, PD.FLAGS_S, 0.3, 6.0, frame, seed_fn)
    params, noise = raw0['params'], raw0['noise']
    H_true = E.channel_matrix(ep23, params['l_i'], params['k_real'], params['g_i'])
    rf = gen_fixed.make_rng_factory(seed_fn, frame)
    info = rf(0, frame, 2, split=2).integers(0, 2, size=ep23.k).astype(np.uint8)
    s2_60 = 10.0 ** (-6.0 / 10.0)
    s2_55 = 10.0 ** (-5.5 / 10.0)
    arms_60, arms_55 = {}, {}
    for r in DEV_RHO_GRID5:
        x = E.make_frame(ep23, info, r)[0]
        res60 = E.run_ep(ep23, E.observe(ep23, H_true, x, noise, s2_60), s2_60, r, info, arms=('EP',))
        arms_60[PD.arm_key('EP', rho_ep=r)] = PD.ep_record(res60['EP'], params['l_i'], params['k_real'], ep23.k)
        res55 = E.run_ep(ep23, E.observe(ep23, H_true, x, noise, s2_55), s2_55, r, info, arms=('EP',))
        arms_55[PD.arm_key('EP', rho_ep=r)] = PD.ep_record(res55['EP'], params['l_i'], params['k_real'], ep23.k)
    return (
        dict(frame=int(frame), snr_centi_db=600, arms=arms_60),
        dict(frame=int(frame), snr_centi_db=550, arms=arms_55),
    )


def _test_frame_worker(task):
    frame, rhos_to_run = task
    ctx, ep23, seed_fn = _G['ctx'], _G['ep23'], _G['seed_test']
    raw0, _ = P.generate(ctx, PD.FLAGS_S, 0.3, SNRS_CENTI[0] / 100.0, frame, seed_fn)
    params, noise = raw0['params'], raw0['noise']
    H_true = E.channel_matrix(ep23, params['l_i'], params['k_real'], params['g_i'])
    genie_gram = E.gram(ep23, H_true)
    rf = gen_fixed.make_rng_factory(seed_fn, frame)
    info = rf(0, frame, 2, split=2).integers(0, 2, size=ep23.k).astype(np.uint8)
    frames_x = {r: E.make_frame(ep23, info, r)[0] for r in rhos_to_run}
    out_rows = []
    for snr_c in SNRS_CENTI:
        s2 = 10.0 ** (-snr_c / 100.0 / 10.0)
        arms_rec = {}
        for r in rhos_to_run:
            tag = int(round(r * 1000))
            y = E.observe(ep23, H_true, frames_x[r], noise, s2)
            res = E.run_ep(ep23, y, s2, r, info, H_true=H_true, genie_gram=genie_gram, arms=('EP', 'EPG'))
            arms_rec[f'EP23_p{tag:03d}'] = PD.ep_record(res['EP'], params['l_i'], params['k_real'], ep23.k)
            arms_rec[f'EPG23_p{tag:03d}'] = PD.ep_record(res['EPG'], params['l_i'], params['k_real'], ep23.k)
        out_rows.append(dict(frame=int(frame), snr_centi_db=int(snr_c), snr_db=snr_c / 100.0, arms=arms_rec))
    return out_rows


def run_implementation_gate(ctx, p2b_test_dir: Path, cache_dir: Path):
    code12 = E.build_ep_code(cache_dir)
    ep12 = E.EP(ctx.system, code12)
    seed_test = P.make_seed_fn(PD.ENTROPY_TEST, PD.DOMAIN_TEST)
    shard0 = p2b_test_dir / 'rows_shard000.jsonl.gz'
    with gzip.open(shard0, 'rt') as f:
        arch_rows = [json.loads(line) for _, line in zip(range(8), f)]
    checked = 0
    for r in arch_rows:
        frame = int(r['frame'])
        snr_c = int(r['snr_centi_db'])
        raw0, _ = P.generate(ctx, PD.FLAGS_S, 0.3, snr_c / 100.0, frame, seed_test)
        params, noise = raw0['params'], raw0['noise']
        H_true = E.channel_matrix(ep12, params['l_i'], params['k_real'], params['g_i'])
        genie_gram = E.gram(ep12, H_true)
        rf = gen_fixed.make_rng_factory(seed_test, frame)
        info = rf(0, frame, 2, split=2).integers(0, 2, size=ep12.k).astype(np.uint8)
        x = E.make_frame(ep12, info, PD.RHO_EP)[0]
        s2 = 10.0 ** (-snr_c / 100.0 / 10.0)
        res = E.run_ep(ep12, E.observe(ep12, H_true, x, noise, s2), s2, PD.RHO_EP, info,
                       H_true=H_true, genie_gram=genie_gram, arms=('EP', 'EPG'))
        for arm in ('EP', 'EPG'):
            got = PD.ep_record(res[arm], params['l_i'], params['k_real'], ep12.k)
            exp = r['arms'][arm]
            for field in ('fer', 'info_errors', 'info_bits', 'decode_ok', 'iterations'):
                assert got[field] == exp[field], f'Gate mismatch at frame={frame}, snr={snr_c}, arm={arm}, {field}: {got[field]} != {exp[field]}'
        checked += 1
    return dict(passed=True, keys_checked=checked, k_ep12=ep12.k)


def load_archived_subset(p2b_test_dir: Path, frame_set: set[int]):
    by_key = {}
    shards = sorted(glob.glob(str(p2b_test_dir / 'rows_shard*.jsonl.gz')))
    for sf in shards:
        with gzip.open(sf, 'rt') as stream:
            for line in stream:
                if not line.strip():
                    continue
                r = json.loads(line)
                fr = int(r['frame'])
                if fr in frame_set:
                    by_key[(fr, int(r['snr_centi_db']))] = r
    return by_key


def md5_path(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--p2b-test-dir', type=Path,
                    default=PROJECT / 'experiments' / 'tcom_reference_frame_20261015' / 'out' / 'p2b_test')
    ap.add_argument('--dev-frames', type=int, default=500)
    ap.add_argument('--test-frames', type=int, default=500)
    ap.add_argument('--workers', type=int, default=48)
    args = ap.parse_args()

    t0 = time.perf_counter()
    args.out.mkdir(parents=True, exist_ok=True)
    cache_dir = args.out / 'ldpc_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Call P.load_context() ONCE in main process; workers use 'spawn' so each worker calls load_context() once!
    ctx_main = P.load_context()
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    _ = E.build_ep_code(cache_dir)
    code23 = build_code(E.CODE_N, d_v=3, d_c=9, seed=E.CODE_SEED, cache_dir=cache_dir)
    print(f'[0] Built LDPC codes: k_r12=767, k_r23={code23["k"]} ({time.perf_counter()-t0:.1f}s)', flush=True)

    # Step 0: Implementation Gate on 8 archived keys
    gate = run_implementation_gate(ctx_main, args.p2b_test_dir, cache_dir)
    print(f'[1] Implementation gate PASSED on {gate["keys_checked"]} archived keys ({time.perf_counter()-t0:.1f}s)', flush=True)

    # Step 1: Disjoint Dev Selection (500 dev frames at 6.0 dB per frozen P2b protocol; also log 5.5 dB diagnostic)
    t_dev0 = time.perf_counter()
    spawn_ctx = mp.get_context('spawn')
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=spawn_ctx, initializer=_init_worker, initargs=(str(cache_dir),)) as ex:
        dev_pairs = list(ex.map(_dev_frame_worker, range(args.dev_frames), chunksize=4))
    dev_rows_60 = [p[0] for p in dev_pairs]
    dev_rows_55 = [p[1] for p in dev_pairs]
    dev_tab5_60, rho_star_5 = AGG.dev_select(dev_rows_60)
    # Also compute on original 4-point grid (0.05, 0.10, 0.20, 0.30)
    dev_rows_60_g4 = [dict(frame=r['frame'], snr_centi_db=600,
                           arms={k: v for k, v in r['arms'].items() if k != 'EP_p150'}) for r in dev_rows_60]
    dev_tab4_60, rho_star_4 = AGG.dev_select(dev_rows_60_g4)
    dev_tab5_55, rho_star_55 = AGG.dev_select(dev_rows_55)
    t_dev = time.perf_counter() - t_dev0
    print(f'[2] Dev tuning done in {t_dev:.1f}s: chosen rho_EP* (5-grid @6.0dB)={rho_star_5}, (4-grid @6.0dB)={rho_star_4}, (@5.5dB)={rho_star_55}', flush=True)

    # Step 2: Paired Test Run on ENTROPY_TEST frames 0..test_frames-1 across all 8 SNRs
    rhos_test = sorted({rho_star_5, rho_star_4, 0.20, 0.15})
    t_te0 = time.perf_counter()
    tasks = [(f, rhos_test) for f in range(args.test_frames)]
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=spawn_ctx, initializer=_init_worker, initargs=(str(cache_dir),)) as ex:
        nested = list(ex.map(_test_frame_worker, tasks, chunksize=4))
    new_rows = [r for sub in nested for r in sub]
    t_te = time.perf_counter() - t_te0
    print(f'[3] Test simulation ({len(new_rows)} cells, rhos={rhos_test}) done in {t_te:.1f}s', flush=True)

    # Save raw new rows compressed & record MD5
    raw_gz = args.out / 'g_r4b2_ep23_test_rows.jsonl.gz'
    with gzip.open(raw_gz, 'wt') as gz:
        for r in new_rows:
            gz.write(json.dumps(r, sort_keys=True) + '\n')
    raw_md5 = md5_path(raw_gz)
    (args.out / 'REMOTE_ROWS_MD5.txt').write_text(f'{raw_md5}  {raw_gz.name}\n')

    # Pair frame-by-frame with archived out/p2b_test rows on exact same frames 0..test_frames-1
    arch_by_key = load_archived_subset(args.p2b_test_dir, set(range(args.test_frames)))
    assert len(arch_by_key) == args.test_frames * len(SNRS_CENTI), f'Missing archived rows: got {len(arch_by_key)}'

    def eval_variant(rho_val: float):
        tag = int(round(rho_val * 1000))
        merged = []
        for r in new_rows:
            key = (r['frame'], r['snr_centi_db'])
            ar = arch_by_key[key]['arms']
            arms_m = {k: ar[k] for k in ar if k not in ('EP', 'EPG')}
            arms_m['EP'] = r['arms'][f'EP23_p{tag:03d}']
            arms_m['EPG'] = r['arms'][f'EPG23_p{tag:03d}']
            merged.append(dict(frame=r['frame'], snr_centi_db=r['snr_centi_db'], arms=arms_m))
        res = AGG.analyze(merged, B=20000, seed=20261016)
        # Also compute 1% FER crossing differences B_r300 - EP and B_r500 - EP!
        data_m, snr_m, _, _ = AGG.build(merged, ['EP', 'EPG', 'B_r300', 'B_r500', 'A3_r300', 'SPG_r300'])
        rng_c = np.random.default_rng(20261122)
        cross_b300_ep = AGG.crossing_calibration(data_m, 'EP', 'B_r300', snr_m, 20000, rng_c)
        cross_b500_ep = AGG.crossing_calibration(data_m, 'EP', 'B_r500', snr_m, 20000, rng_c)
        cross_epg_a3  = AGG.crossing_calibration(data_m, 'EPG', 'A3_r300', snr_m, 20000, rng_c)
        res['crossing_fer1e2'] = dict(EP_minus_B_r300=cross_b300_ep, EP_minus_B_r500=cross_b500_ep, EPG_minus_A3_r300=cross_epg_a3)
        # Rate-normalized delivery difference (1024 * (FER_EP - FER_SP), isolating FER from the 2-bit 1024-vs-1022 code granularity)
        rng_n = np.random.default_rng(20261016)
        norm_diffs = {
            'B_r300_minus_EP_norm1024': 1024.0 * ((1.0 - data_m['B_r300']['fer']) - (1.0 - data_m['EP']['fer'])),
            'B_r500_minus_EP_norm1024': 1024.0 * ((1.0 - data_m['B_r500']['fer']) - (1.0 - data_m['EP']['fer'])),
        }
        norm_ci = AGG.paired_ci(norm_diffs, 20000, rng_n)
        res['H6_norm1024'] = {
            'rho300': dict(zip(('label', 'points_sp_better', 'points_ep_better'), AGG.h6_label(norm_ci['B_r300_minus_EP_norm1024']['lo'], norm_ci['B_r300_minus_EP_norm1024']['hi']))),
            'rho500': dict(zip(('label', 'points_sp_better', 'points_ep_better'), AGG.h6_label(norm_ci['B_r500_minus_EP_norm1024']['lo'], norm_ci['B_r500_minus_EP_norm1024']['hi']))),
        }
        return res

    # Baseline archived k=767 on exact same 500 frames for direct sanity comparison
    arch_list = [arch_by_key[(f, s)] for f in range(args.test_frames) for s in SNRS_CENTI]
    res_arch_k767 = AGG.analyze(arch_list, B=20000, seed=20261016)

    res_primary = eval_variant(rho_star_5)
    res_grid4   = eval_variant(rho_star_4) if rho_star_4 != rho_star_5 else res_primary
    res_untuned = eval_variant(0.20)
    res_p150    = eval_variant(0.15)

    # Boolean pre-registered gates check on primary (rho_star_5)
    snr_grid = res_primary['snr_db']
    diff_b300 = res_primary['difference_ci']['B_r300-EP']
    diff_b500 = res_primary['difference_ci']['B_r500-EP']
    idx_ge6 = [i for i, s in enumerate(snr_grid) if s >= 6.0 - 1e-9]
    idx_60  = snr_grid.index(6.0)
    max_b300_adv_ge6 = max(diff_b300['point'][i] for i in idx_ge6)
    b500_at_60 = dict(point=diff_b500['point'][idx_60], lo=diff_b500['lo'][idx_60], hi=diff_b500['hi'][idx_60])
    gates = dict(
        P1_high_snr_plateau_collapsed=bool(max_b300_adv_ge6 <= 8.0),
        P2_rho500_flipped_negative_at_6dB=bool(b500_at_60['hi'] < 0.0),
        veto_triggered=bool(max_b300_adv_ge6 >= 51.0 and b500_at_60['lo'] > 0.0),
        max_B_r300_minus_EP23_bits_ge_6dB=float(max_b300_adv_ge6),
        B_r500_minus_EP23_at_6dB=b500_at_60,
    )

    summary = dict(
        card='I-20261122-g21',
        wall_seconds_total=float(time.perf_counter() - t0),
        dev_seconds=float(t_dev),
        test_seconds=float(t_te),
        workers=args.workers,
        dev_frames=args.dev_frames,
        test_frames=args.test_frames,
        k_ep23=int(code23['k']),
        raw_rows_gz=str(raw_gz),
        raw_rows_md5=raw_md5,
        implementation_gate=gate,
        dev_tuning=dict(
            grid5_at_6dB=dev_tab5_60, chosen_rho_ep_grid5=rho_star_5,
            grid4_at_6dB=dev_tab4_60, chosen_rho_ep_grid4=rho_star_4,
            grid5_at_5_5dB_diag=dev_tab5_55, chosen_rho_ep_at_5_5dB_diag=rho_star_55,
        ),
        gates_primary=gates,
        primary_ep23_dev_selected=dict(rho_ep=rho_star_5, analysis=res_primary),
        control_ep23_grid4_selected=dict(rho_ep=rho_star_4, analysis=res_grid4),
        control_ep23_untuned_p200=dict(rho_ep=0.20, analysis=res_untuned),
        diag_ep23_p150=dict(rho_ep=0.15, analysis=res_p150),
        archived_ep12_k767_same_frames=res_arch_k767,
    )
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print('[4] DONE! Gates:', json.dumps(gates, indent=2), flush=True)
    print('    H6 (archived k=767, 500 frames):', res_arch_k767['H6'], flush=True)
    print(f'    H6 (EP_r23 k=1022, dev rho*={rho_star_5}):', res_primary['H6'], flush=True)
    print('    H6 (EP_r23 k=1022, untuned rho=0.20):', res_untuned['H6'], flush=True)


if __name__ == '__main__':
    main()
