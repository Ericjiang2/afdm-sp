#!/usr/bin/env python
"""Gates S1-S6 (protocol.md section 4, task 10-16-tcom-genie-support).  Run on deinlab (frozen receiver tree is remote only).

--stage s123 --shard k --nshard m   S1 (refit copy == twofft.time_refine), S2 (run_gs + true H + fixed gains == P1 A3 ledger),
                                    S3 (production F0 == P1 F0 ledger) on frames 0..19; writes s123_shardKKK.json
--stage merge                       combines the s123 shards into gates_s123.json
--stage smoke --smoke-dir D         S5 (join with CRB rows, true-path NMSE) and S6 (timing) from a 20-frame gs_driver run;
                                    S4 is asserted inside gs_driver on every row (a failure aborts the shard)
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_driver as gd  # noqa: E402
from gs_driver import crb, p1ctx  # noqa: E402

PROJECT = HERE.parents[1]
P1_ROWS = PROJECT / 'experiments' / 'tcom_reference_frame_20261015' / 'out' / 'p1'
CRB_ROWS = PROJECT / 'experiments' / 'tcom_channel_crb_20261016' / 'out' / 'main'
GATE_FRAMES = 20
S1_SNR = (450, 800)
TOL = 1e-12
MAIN_ROWS = 2000 * 2 * 2 * 8  # frames x scenarios x rho x snr
CORE_HOUR_CAP = 16.


def key(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


def load_gz_rows(d, keep):
    out = {}
    for p in sorted(Path(d).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if keep(r):
                    out[key(r)] = r
    return out


def s1_check(ctx, obs):
    """Capture both production refits; re-solve each with refine_fixed_delays on the production-selected delay list."""
    import twofft
    recs = []

    def refine(*args, **kwargs):
        channel, detail = twofft.time_refine(*args, **kwargs)
        y, pilot, mu, v, ls, ks, gs, c1, c2, noise = args
        ls, gs = np.asarray(ls, int), np.asarray(gs, complex)
        unique = np.unique(ls)
        energy = np.array([np.sum(abs(gs[ls == d]) ** 2) for d in unique])
        sel = unique[np.argsort(-energy)[:kwargs.get('max_paths', 8)]]
        copy, cd = ctx.arms.refine_fixed_delays(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, delays=sel,
                                                mode=kwargs.get('mode', 'soft'), rounds=kwargs.get('rounds', 2))
        scale = max(float(np.max(np.abs(channel.gains))), 1e-300)
        recs.append(dict(delays_equal=bool(np.array_equal(copy.delays, channel.delays)),
                         dnu=float(np.max(np.abs(copy.dopplers - channel.dopplers))),
                         dh_rel=float(np.max(np.abs(copy.gains - channel.gains)) / scale),
                         missing=int(cd['n_missing_slots'])))
        return channel, detail

    res = gd.run_gs(ctx, obs, refine, arm='s1_capture')
    return recs, gd.bits_sha(res.decoder['decoded'])


def stage_s123(args):
    ctx = p1ctx.load()
    frames = list(range(GATE_FRAMES))[args.shard::args.nshard]
    want = lambda r: r['frame'] in frames  # noqa: E731
    ledger = load_gz_rows(args.p1_rows, want)
    s1, s2, s3 = [], [], []
    for frame in frames:
        for scenario in gd.SCENARIOS:
            for rho in (0.3, 0.5):
                raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
                for snr in (450, 500, 550, 600, 650, 700, 750, 800):
                    raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                    k = (scenario, int(round(rho * 1000)), snr, frame)
                    led = ledger.get(k)
                    if snr in S1_SNR:
                        recs, sha_capture = s1_check(ctx, obs)
                        s1.append(dict(key=list(k), recs=recs,
                                       capture_matches_f0=bool(led is not None and sha_capture == led['arms']['F0']['decoded_sha256'])))
                    ch = ctx.Channel(len(obs['y']), ctx.system.c1, ctx.system.c2, truth['l_i'], truth['k_real'], truth['g_i'])
                    passthrough = lambda *a, **kw: (ch, dict(history=[], objective=None, gamma=None,  # noqa: E731
                                                             evaluations=0, fft_count=0))
                    sha_a3 = gd.bits_sha(gd.run_gs(ctx, obs, passthrough, gain_mode='fixed', arm='s2_true_h').decoder['decoded'])
                    dec0, _, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
                                                    ce_mode='soft', gain_mode='joint')
                    s2.append(dict(key=list(k), match=bool(led is not None and sha_a3 == led['arms']['A3']['decoded_sha256'])))
                    s3.append(dict(key=list(k), match=bool(led is not None and gd.bits_sha(dec0['decoded']) == led['arms']['F0']['decoded_sha256'])))
    doc = dict(frames=frames, s1=s1, s2=s2, s3=s3)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f's123_shard{args.shard:03d}.json').write_text(json.dumps(doc) + '\n')
    print(f'shard {args.shard}: S1 {len(s1)} S2 {sum(x["match"] for x in s2)}/{len(s2)} S3 {sum(x["match"] for x in s3)}/{len(s3)}')
    return None


def stage_merge(args):
    s1, s2, s3, frames = [], [], [], []
    for p in sorted(args.out.glob('s123_shard*.json')):
        d = json.loads(p.read_text())
        s1 += d['s1']; s2 += d['s2']; s3 += d['s3']; frames += d['frames']
    recs = [r for x in s1 for r in x['recs']]
    res = {}
    res['S1'] = dict(cells=len(s1), refits=len(recs), all_delays_equal=all(r['delays_equal'] for r in recs),
                     max_dnu=max(r['dnu'] for r in recs), max_dh_rel=max(r['dh_rel'] for r in recs),
                     max_missing=max(r['missing'] for r in recs),
                     capture_matches_f0=sum(x['capture_matches_f0'] for x in s1))
    res['S1']['pass'] = bool(res['S1']['all_delays_equal'] and res['S1']['max_dnu'] <= TOL and res['S1']['max_dh_rel'] <= TOL
                             and res['S1']['max_missing'] == 0 and res['S1']['capture_matches_f0'] == len(s1)
                             and len(recs) == 2 * len(s1) and len(s1) == GATE_FRAMES * 4 * len(S1_SNR))
    for name, lst in (('S2', s2), ('S3', s3)):
        bad = [x['key'] for x in lst if not x['match']]
        res[name] = dict(cells=len(lst), matched=len(lst) - len(bad), mismatches=bad[:20],
                         pass_=bool(not bad and len(lst) == GATE_FRAMES * 32))
        res[name]['pass'] = res[name].pop('pass_')
    res['frames'] = sorted(frames)
    return res


def stage_smoke(args):
    rows = []
    for p in sorted(Path(args.smoke_dir).glob('rows_shard*.jsonl')):
        rows += [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    keys = {key(r) for r in rows}
    crb_rows = load_gz_rows(args.crb_rows, lambda r: key(r) in keys)
    missing, sig_bad, frob_rel = [], [], 0.
    for r in rows:
        c = crb_rows.get(key(r))
        if c is None:
            missing.append(list(key(r)))
            continue
        if c['sigma2'] != r['sigma2']:
            sig_bad.append(list(key(r)))
        frob_rel = max(frob_rel, abs(c['frob'] - r['frob']) / c['frob'])
    ctx = p1ctx.load()
    true_nmse = 0.
    for frame in sorted({r['frame'] for r in rows})[:5]:
        raw_base, diag_base = p1ctx.base(ctx, 'U', 0.3, frame)
        t = ctx.hd.truth_from_raw(raw_base, diag_base)
        tp = dict(delays=np.asarray(t['l_i'], int), dopplers=np.asarray(t['k_real'], float), gains=np.asarray(t['g_i'], complex))
        true_nmse = max(true_nmse, crb.channel_nmse(gd.paths(tp['delays'], tp['dopplers'], tp['gains']), tp, len(raw_base['y'])))
    secs = np.array([sum(a['seconds'] for a in r['arms'].values()) for r in rows])
    projected = float(secs.mean() * MAIN_ROWS / 3600)
    res = {'S5': dict(rows=len(rows), missing_crb=missing[:20], n_missing=len(missing), sigma2_mismatch=sig_bad[:20],
                      max_frob_rel=frob_rel, max_true_path_nmse=true_nmse,
                      pass_=bool(rows and not missing and not sig_bad and frob_rel <= TOL and true_nmse <= TOL)),
           'S6': dict(mean_row_seconds=float(secs.mean()), projected_core_hours=projected, cap=CORE_HOUR_CAP,
                      pass_=bool(projected <= CORE_HOUR_CAP)),
           'S4': dict(rows=len(rows), note='asserted per row in gs_driver.gs_arm; rows exist only if S4 held',
                      pass_=bool(len(rows) == len(keys) == GATE_FRAMES * 32))}
    for v in res.values():
        v['pass'] = v.pop('pass_')
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--stage', choices=('s123', 'merge', 'smoke'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--smoke-dir', type=Path)
    p.add_argument('--p1-rows', type=Path, default=P1_ROWS)
    p.add_argument('--crb-rows', type=Path, default=CRB_ROWS)
    args = p.parse_args(argv)
    t0 = time.perf_counter()
    if args.stage == 's123':
        stage_s123(args)
        return
    res = stage_merge(args) if args.stage == 'merge' else stage_smoke(args)
    status = all(v.get('pass', True) for v in res.values() if isinstance(v, dict))
    doc = dict(_argv=sys.argv, _config=dict(stage=args.stage, tol=TOL, gate_frames=GATE_FRAMES, cap=CORE_HOUR_CAP),
               gates=res, all_pass=status, seconds=time.perf_counter() - t0)
    name = 'gates_s123.json' if args.stage == 'merge' else 'gates_smoke.json'
    (args.out / name).write_text(json.dumps(doc, indent=1, default=float) + '\n')
    for k, v in res.items():
        if isinstance(v, dict):
            print(k, 'PASS' if v.get('pass', True) else 'FAIL', {a: b for a, b in v.items() if a not in ('mismatches',)})
    print('ALL PASS' if status else 'GATE FAILURE')
    sys.exit(0 if status else 1)


if __name__ == '__main__':
    main()
