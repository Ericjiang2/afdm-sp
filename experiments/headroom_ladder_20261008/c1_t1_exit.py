#!/usr/bin/env python
"""C1 T1 addendum: decoder EXIT curve of the fixed code/decoder on AWGN QPSK (same frames/streams as c1_t1_transfer.py, frames 0..F-1).
Per coded-grid q: I_in = 1 - logloss(clip(channel LLR)), I_ext = 1 - logloss(clip(raw_check_extrinsic)), I_app = 1 - logloss(clip(raw_app)),
logloss = arms.logloss_bits (mean log2(1+exp(-(1-2b)L)) over 2048 coded bits).  Modes: run (--shard/--nshard) | merge (appends key "exit" to
t1_transfer.json and a section to T1_TRANSFER.md).  Reuses c1_t1_transfer.bind / frame_data unchanged."""
import argparse, json, os, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_t1_transfer as T


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('run', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--frames', type=int, default=1000)
    p.add_argument('--chunk', type=int, default=250)
    return p.parse_args()


def tasks(a):
    return [(q, f0, min(a.chunk, a.frames - f0)) for q in range(-10, 41, 2) for f0 in range(0, a.frames, a.chunk)]


def run(a):
    ctx = T.bind(a)
    parts = a.out / 'exit_parts'
    parts.mkdir(parents=True, exist_ok=True)
    for i, (q, f0, nf) in enumerate(tasks(a)):
        if i % a.nshard != a.shard:
            continue
        path = parts / f'exit_{q:+04d}_{f0:06d}.npz'
        if path.exists():
            continue
        cols = {k: [] for k in ('ll_chan', 'll_chk', 'll_app', 'info_err')}
        for f in range(f0, f0 + nf):
            info, coded, d, llr = T.frame_data(ctx, f, 10 ** (q / 100.))
            dec = ctx.decoder_messages(ctx.code, llr, maxiter=50)
            cols['ll_chan'].append(ctx.arms.logloss_bits(llr, coded))
            cols['ll_chk'].append(ctx.arms.logloss_bits(np.clip(dec['raw_check_extrinsic'], -20., 20.), coded))
            cols['ll_app'].append(ctx.arms.logloss_bits(np.clip(dec['raw_app'], -20., 20.), coded))
            cols['info_err'].append(int(np.count_nonzero(ctx.extract_info(ctx.code, np.asarray(dec['decoded'])) != info)))
        tmp = parts / f'exit_{q:+04d}_{f0:06d}.tmp.npz'
        np.savez(tmp, frame=np.arange(f0, f0 + nf), **{k: np.asarray(v) for k, v in cols.items()})
        os.replace(tmp, path)
        print('shard', a.shard, path.name, flush=True)


def merge(a):
    by = {}
    for p in sorted((a.out / 'exit_parts').glob('exit_*.npz')):
        if '.tmp' in p.name:
            continue
        z = np.load(p)
        by.setdefault(int(p.name.split('_')[1]), []).append({k: z[k] for k in z.files})
    rows = []
    for q in sorted(by):
        lst = sorted(by[q], key=lambda x: x['frame'][0])
        c = {k: np.concatenate([x[k] for x in lst]) for k in lst[0]}
        assert np.array_equal(c['frame'], np.arange(a.frames))
        r = dict(q_db=q / 10., n_frames=len(c['frame']), FER=float(np.mean(c['info_err'] > 0)))
        for key, name in (('chan', 'I_in'), ('chk', 'I_ext'), ('app', 'I_app')):
            r[name] = float(1 - c['ll_' + key].mean())
            r[name + '_se'] = T.se(c['ll_' + key])
        rows.append(r)
    path = a.out / 't1_transfer.json'
    d = json.loads(path.read_text())
    qd = np.array([r['q_db'] for r in d['coded']])
    jin = np.array([d['coded'][i]['J_chan'] for i in range(len(qd))])  # 3000-9000 frame channel-LLR MI
    cross = {}
    for k, v in d['crossings'].items():
        if k.endswith('_logit') or k.endswith('_linear'):
            f = lambda x: float(np.interp(x, qd, jin)) if x is not None else None
            cross[k] = dict(q_db=v['q_db'], I_in=f(v['q_db']), I_in_ci95=[f(v['ci95'][0]), f(v['ci95'][1])],
                            I_in_analytic=float(T.gh_uncoded(10 ** (v['q_db'] / 10))[1]))
    d['exit'] = dict(_argv=sys.argv, frames_per_point=a.frames, source='same frame streams as main run (frames 0..F-1); logloss_bits of clipped LLR',
                     definition='I = 1 - mean_bits log2(1+exp(-(1-2b)L)); I_in channel LLR, I_ext raw_check_extrinsic, I_app raw_app',
                     curve=rows, I_in_at_crossings=cross)
    path.write_text(json.dumps(T.clean(d), indent=1, allow_nan=False))
    md = a.out / 'T1_TRANSFER.md'
    txt = md.read_text()
    txt = txt.split('\n## Decoder EXIT curve')[0]
    L = ['', '## Decoder EXIT curve (same code/decoder, AWGN; frames 0..%d per point; I = 1 - logloss)' % (a.frames - 1), '',
         '| q_dB | I_in | I_ext | I_app | FER |', '|---|---|---|---|---|']
    for r in rows:
        L.append(f'| {r["q_db"]:.1f} | {r["I_in"]:.4f} ({r["I_in_se"]:.1e}) | {r["I_ext"]:.4f} ({r["I_ext_se"]:.1e}) | {r["I_app"]:.4f} ({r["I_app_se"]:.1e}) | {r["FER"]:.3f} |')
    L += ['', 'I_in at the FER crossings (I_in(q) interpolated from the 3000-9000 frame channel-LLR curve):', '',
          '| crossing | q_dB | I_in | I_in 95% (from q CI) | I_in analytic |', '|---|---|---|---|---|']
    for k, v in cross.items():
        L.append(f'| {k} | {v["q_db"]:.3f} | {v["I_in"]:.4f} | [{v["I_in_ci95"][0]:.4f}, {v["I_in_ci95"][1]:.4f}] | {v["I_in_analytic"]:.4f} |')
    md.write_text(txt.rstrip('\n') + '\n' + '\n'.join(L) + '\n')
    print(json.dumps(cross, indent=1))


if __name__ == '__main__':
    a = parse_args()
    a.out = a.out.resolve()
    run(a) if a.mode == 'run' else merge(a)
