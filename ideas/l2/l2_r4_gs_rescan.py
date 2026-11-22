#!/usr/bin/env python
"""Idea-funnel local round 4, L2 batch 5 (card I-20261122-l37; criteria in PREDICTIONS_r4_batch5.md; runner l, claude-fable-5.2).

res-20261016-03: with the true delays (GS-set) the refit is still 4.5-5.3 dB above the constrained MCRB at rho .3.  Is that floor
made by the round-1 Doppler search being confined to +-0.75 bin around the round-0 values (headroom arms.refine_fixed_delays
coarse-scans only unmatched slots)?  New arm GS-set-rescan: identical to GS-set, except that the second refit call gets an empty
acquired-path list, so the existing 25-point coarse scan runs on all slots before the unchanged local refinement.
gs_driver, arms and crb are imported unchanged; GS-set, B and the MCRB come from the archived rows on the same keys.

  python l2_r4_gs_rescan.py gate --out out_r4b5 ; python l2_r4_gs_rescan.py run --out out_r4b5 ; python l2_r4_gs_rescan.py read --out out_r4b5
"""
import argparse, gzip, json, resource, sys, time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1] / 'experiments'
GS_DIR, CRB_DIR = EXP / 'tcom_genie_support_20261016', EXP / 'tcom_channel_crb_20261016'
FRAMES = range(12, 500)
SCEN, RHOS, SNRS = ('U', 'G'), (.3, .5), (650, 700, 750, 800)
WORKERS, BOOT, SEED = 48, 2000, 20261125


def mods():
    sys.path.insert(0, str(GS_DIR))
    import gs_driver
    return gs_driver


def rescan_refine(arms, delays, log, rescan):
    delays = np.asarray(delays, int).copy(); st = dict(calls=0)

    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw):
        st['calls'] += 1
        if rescan and st['calls'] >= 2:
            ls, ks, gs = np.zeros(0, int), np.zeros(0), np.zeros(0, complex)
        ch, det = arms.refine_fixed_delays(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, delays=delays, mode=kw.get('mode', 'soft'), rounds=kw.get('rounds', 2))
        log.append(int(det['n_missing_slots']))
        return ch, det
    return refine


def one(gsd, ctx, obs, truth, n, rescan):
    delays = gsd.genie_delays(truth, 'GS-set'); log = []
    res = gsd.run_gs(ctx, obs, rescan_refine(ctx.arms, delays, log, rescan)); a = res.arrays
    tp = dict(delays=np.asarray(truth['l_i'], int), dopplers=np.asarray(truth['k_real'], float), gains=np.asarray(truth['g_i'], complex))
    dec = res.decoder['decoded']
    return dict(fer=int(gsd.score(ctx, dec, truth) > 0), decoded_sha256=gsd.bits_sha(dec), n_missing_slots=log,
                nmse=gsd.crb.channel_nmse(gsd.paths(a['r1_delays'], a['r1_dopplers'], a['r1_gains']), tp, n))


def shard_job(job):
    idx, frames, out = job
    gsd = mods(); ctx = gsd.p1ctx.load(); k = 0
    with open(Path(out) / f'rows_shard{idx:03d}.jsonl', 'w') as fh:
        for frame in frames:
            for sc in SCEN:
                for rho in RHOS:
                    raw_base, diag_base = gsd.p1ctx.base(ctx, sc, rho, frame)
                    for snr in SNRS:
                        raw, obs, truth = gsd.observe(ctx, raw_base, diag_base, rho, snr)
                        r = one(gsd, ctx, obs, truth, len(raw['y']), True)
                        print(json.dumps(dict(scenario=sc, rho_permille=int(round(rho * 1000)), snr_centi_db=snr, frame=frame, rescan=r)), file=fh, flush=True); k += 1
    return idx, k


def load(d, keys, slim):
    out = {}
    for p in sorted(Path(d).glob('rows_shard*.jsonl*')):
        with (gzip.open(p, 'rt') if p.suffix == '.gz' else open(p)) as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line); k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
                    if keys is None or k in keys:
                        out[k] = slim(r)
    return out


def gate(out):
    gsd = mods(); ctx = gsd.p1ctx.load()
    keys = {(sc, 300, snr, f) for sc in SCEN for snr in (650, 800) for f in (12, 13)}
    old = load(GS_DIR / 'out' / 'main', keys, lambda r: r['arms']['GS-set']); recs = []
    for sc, rho_pm, snr, f in sorted(keys):
        raw_base, diag_base = gsd.p1ctx.base(ctx, sc, rho_pm / 1000, f)
        raw, obs, truth = gsd.observe(ctx, raw_base, diag_base, rho_pm / 1000, snr)
        r = one(gsd, ctx, obs, truth, len(raw['y']), False); o = old[(sc, rho_pm, snr, f)]
        r2 = one(gsd, ctx, obs, truth, len(raw['y']), True)
        recs.append(dict(key=[sc, rho_pm, snr, f], sha=r['decoded_sha256'] == o['decoded_sha256'], nmse=bool(np.isclose(r['nmse'], o['nmse'], rtol=1e-9)),
                         nmse_db=dict(archived=10 * np.log10(o['nmse']), rescan=10 * np.log10(r2['nmse'])), rescan_missing=r2['n_missing_slots']))
        print(recs[-1], flush=True)
    ok = len(recs) == 8 and all(r['sha'] and r['nmse'] for r in recs) and all(r['rescan_missing'][1] == 8 for r in recs)
    json.dump(dict(pass_=ok, records=recs), open(out / 'gate.json', 'w'), indent=1)
    print('GATE', 'PASS' if ok else 'FAIL')


def run(out):
    frames = list(FRAMES); jobs = [(i, frames[i::WORKERS], str(out)) for i in range(WORKERS)]; t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    json.dump(dict(_argv=sys.argv, _config=dict(frames=[FRAMES.start, FRAMES.stop - 1], scenarios=SCEN, rhos=RHOS, snrs=SNRS, workers=WORKERS,
                                                 arm='GS-set with the round-1 refit given an empty acquired list (coarse scan on all slots)'),
                   keys=done, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), open(out / 'run.json', 'w'), indent=1)
    print('DONE', done, 'keys', round((ch.ru_utime + ch.ru_stime) / 3600, 3), 'core-hours', round(time.time() - t0), 's wall')


def read(out):
    N = load(out, None, lambda r: r['rescan']); keys = set(N)
    G = load(GS_DIR / 'out' / 'main', keys, lambda r: r['arms']['GS-set'])
    Cr = load(CRB_DIR / 'out' / 'main', keys, lambda r: dict(nmse_B=r['nmse']['B-final'], mcrb=r['bounds']['mcrb']['c'], flagged=bool(r['bounds']['mcrb']['flagged'])))
    if set(G) != keys or set(Cr) != keys:
        raise ValueError(f'archived rows missing: gs {len(keys - set(G))}, crb {len(keys - set(Cr))}')
    rng = np.random.default_rng(SEED); res = dict(keys=len(N), cells={})
    db = lambda x: float(10 * np.log10(x))
    for sc in ('G', 'U'):
        for rho in (300, 500):
            cell = dict(points={})
            for snr in SNRS:
                ks = [(sc, rho, snr, f) for f in FRAMES if not Cr[(sc, rho, snr, f)]['flagged']]
                m = np.array([Cr[k]['mcrb'] for k in ks]); nb = np.array([Cr[k]['nmse_B'] for k in ks])
                a = np.array([G[k]['nmse'] for k in ks]); b = np.array([N[k]['nmse'] for k in ks])
                idx = rng.integers(0, len(ks), (BOOT, len(ks))); mean = lambda x: x[idx].mean(1)
                mm, ma, mb_, mB = mean(m), mean(a), mean(b), mean(nb)
                ci = lambda x: [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]
                cell['points'][str(snr)] = dict(
                    frames=len(ks), r_set=db(a.mean() / m.mean()), r_set_ci=ci(10 * np.log10(ma / mm)),
                    r_rescan=db(b.mean() / m.mean()), r_rescan_ci=ci(10 * np.log10(mb_ / mm)),
                    drop=db(a.mean() / b.mean()), drop_ci=ci(10 * np.log10(ma / mb_)),
                    f_set=float((nb.mean() - a.mean()) / (nb.mean() - m.mean())), f_rescan=float((nb.mean() - b.mean()) / (nb.mean() - m.mean())),
                    fer_set=float(np.mean([G[k]['fer'] for k in ks])), fer_rescan=float(np.mean([N[k]['fer'] for k in ks])),
                    frac_worse=float(np.mean(b > a * 1.001)))
            his = [p['r_rescan_ci'][1] for p in cell['points'].values()]; los = [p['r_rescan_ci'][0] for p in cell['points'].values()]
            cell['H-S2_rescan'] = 'SUPPORTED' if max(his) <= 3 else 'REFUTED' if min(los) > 3 else 'INCONCLUSIVE'
            hs = [p['r_set_ci'][1] for p in cell['points'].values()]; ls = [p['r_set_ci'][0] for p in cell['points'].values()]
            cell['H-S2_set_same_frames'] = 'SUPPORTED' if max(hs) <= 3 else 'REFUTED' if min(ls) > 3 else 'INCONCLUSIVE'
            cell['min_drop_lo'] = min(p['drop_ci'][0] for p in cell['points'].values()); cell['max_drop_hi'] = max(p['drop_ci'][1] for p in cell['points'].values())
            res['cells'][f'{sc}_{rho}'] = cell
    json.dump(res, open(out / 'summary.json', 'w'), indent=1)
    for c, v in res['cells'].items():
        print(c, 'H-S2 rescan', v['H-S2_rescan'], '| GS-set same frames', v['H-S2_set_same_frames'], '| drop lo/hi', round(v['min_drop_lo'], 2), round(v['max_drop_hi'], 2))
        for s, p in v['points'].items():
            print('  ', s, {k: (round(x, 3) if isinstance(x, float) else ([round(y, 2) for y in x] if isinstance(x, list) else x)) for k, x in p.items()})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=('gate', 'run', 'read')); ap.add_argument('--out', default='out_r4b5'); a = ap.parse_args()
    out = HERE / a.out; out.mkdir(exist_ok=True)
    {'gate': gate, 'run': run, 'read': read}[a.cmd](out)
