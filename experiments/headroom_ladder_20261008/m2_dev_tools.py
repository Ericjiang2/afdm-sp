#!/usr/bin/env python
"""M2 dev-tuning helpers (frames 1000..1199 ONLY; configs N4b, J4, D1 at 8 dB).  Selection criterion = mean logloss_bits (mean over the
three configs of the per-config mean), NOT FER.

  m2_dev_tools.py grid-a  <out.json>                       stage A: kappa x drop for M_full (F_*) and M_adapt (A_*; eps .05, margin .25)
  m2_dev_tools.py grid-a2 <out.json>                       stage A2 (A had its optimum on the kappa grid edge): kappa {.1,.2,.3} x drop {0,.01}
  m2_dev_tools.py grid-b  <out.json> <kappa> <drop>        stage B: eps x margin for M_adapt at the stage-A (kappa, drop)
  m2_dev_tools.py grid-c  <out.json> <drop> <eps> <margin> stage C: kappa line search for M_full and M_adapt at (drop, eps, margin)
  m2_dev_tools.py report  <out.md> <rows_dir> [<rows_dir> ...]   per-arm mean logloss / FER / cols / seconds, sorted
  m2_dev_tools.py freeze  <out.json> '<M_full cfg json>' '<M_adapt cfg json>' <selection note>   write the frozen test config (+ .sha256)
"""
import glob
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

KAPPAS = (0.15, 0.3, 0.6, 1.0)
DROPS = (0.0, 0.01)
EPS = (0.02, 0.05, 0.1, 0.2)
MARGINS = (0.0, 0.25, 0.5)
A_DEFAULT = dict(eps=0.05, margin=0.25)  # M_adapt defaults in stage A (best of the earlier realized-law dev pass)
CONFIGS = ('N4b', 'J4', 'D1')


def tag(x):
    return str(x).replace('.', 'p')


def write(path, arms, note):
    Path(path).write_text(json.dumps(dict(arms=arms, note=note), indent=1) + '\n')
    print(f'{len(arms)} arms -> {path}')


def main():
    cmd = sys.argv[1]
    if cmd == 'grid-a':
        arms = {}
        for k in KAPPAS:
            for d in DROPS:
                arms[f'F_k{tag(k)}_d{tag(d)}'] = dict(mode='full', kappa=k, drop=d)
                arms[f'A_k{tag(k)}_d{tag(d)}'] = dict(mode='adapt', kappa=k, drop=d, **A_DEFAULT)
        write(sys.argv[2], arms, 'dev stage A')
    elif cmd == 'grid-a2':
        arms = {}
        for k in (0.1, 0.2, 0.3):
            for d in (0.0, 0.01):
                arms[f'F_k{tag(k)}_d{tag(d)}'] = dict(mode='full', kappa=k, drop=d)
                arms[f'A_k{tag(k)}_d{tag(d)}'] = dict(mode='adapt', kappa=k, drop=d, eps=.15, margin=.5)
        write(sys.argv[2], arms, 'dev stage A2')
    elif cmd == 'grid-b':
        k, d = float(sys.argv[3]), float(sys.argv[4])
        arms = {f'A_e{tag(e)}_m{tag(m)}': dict(mode='adapt', kappa=k, drop=d, eps=e, margin=m) for e in EPS for m in MARGINS}
        write(sys.argv[2], arms, f'dev stage B at kappa={k} drop={d}')
    elif cmd == 'grid-c':
        d, e, m = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
        arms = {}
        for k in (0.2, 0.25, 0.3, 0.4, 0.5):
            arms[f'F_k{tag(k)}'] = dict(mode='full', kappa=k, drop=d)
            arms[f'A_k{tag(k)}'] = dict(mode='adapt', kappa=k, drop=d, eps=e, margin=m)
        write(sys.argv[2], arms, f'dev stage C (kappa line search, both arms) at drop={d} eps={e} margin={m}')
    elif cmd == 'report':
        acc, frames = {}, {}
        for d in sys.argv[3:]:
            for f in sorted(glob.glob(d + '/rows_shard*.jsonl')):
                for line in open(f):
                    r = json.loads(line)
                    if r['status'] != 'ok':
                        print('ERROR ROW', r['arm'], r['config'], r['frame'], r.get('error'))
                        continue
                    if not 1000 <= r['frame'] <= 1199:
                        raise ValueError('dev report accepts frames 1000..1199 only')
                    acc.setdefault(r['arm'], {}).setdefault(r['config'], []).append(
                        (r['frame'], r['logloss_bits'], r['info_errors'] > 0, r['seconds'], r.get('n_cols'), r.get('misfit')))
                    frames.setdefault(r['arm'], {})[(r['config'], r['frame'])] = r['logloss_bits']
        lines = ['| arm | ' + ' | '.join(f'{c} ll' for c in CONFIGS) + ' | mean ll | d_ll vs best (paired se) | ' + ' | '.join(f'{c} FER' for c in CONFIGS)
                 + ' | cols | misfit(med) | sec |', '|' + '---|' * (3 + 2 * len(CONFIGS) + 3)]
        rows = []
        for arm, byc in acc.items():
            if not all(c in byc for c in CONFIGS):
                continue
            ll = [float(np.mean([x[1] for x in byc[c]])) for c in CONFIGS]
            fer = [float(np.mean([x[2] for x in byc[c]])) for c in CONFIGS]
            cols = [x[4] for c in CONFIGS for x in byc[c] if x[4] is not None]
            mis = [x[5] for c in CONFIGS for x in byc[c] if x[5] is not None]
            sec = float(np.mean([x[3] for c in CONFIGS for x in byc[c]]))
            n = [len(byc[c]) for c in CONFIGS]
            rows.append((float(np.mean(ll)), arm, ll, fer, float(np.mean(cols)) if cols else None, float(np.median(mis)) if mis else None, sec, n))
        cand = [r for r in sorted(rows) if r[1].startswith(('F_', 'A_', 'M_'))]
        best = cand[0][1] if cand else None

        def paired(arm):
            keys = sorted(set(frames[arm]) & set(frames[best]))
            # mean over configs of per-config mean == mean over equal-size cells; se of the per-frame difference (pooled over configs)
            dlt = np.array([frames[arm][k] - frames[best][k] for k in keys])
            return float(dlt.mean()), float(dlt.std(ddof=1) / np.sqrt(len(dlt)))
        for m, arm, ll, fer, cols, mis, sec, n in sorted(rows):
            dm, se = paired(arm) if best and arm.startswith(('F_', 'A_', 'M_')) else (float('nan'), float('nan'))
            lines.append(f'| {arm} | ' + ' | '.join(f'{x:.4f}' for x in ll) + f' | {m:.4f} | {dm:+.4f} ({se:.4f}) | ' + ' | '.join(f'{x:.3f}' for x in fer)
                         + f" | {'-' if cols is None else f'{cols:.1f}'} | {'-' if mis is None else f'{mis:.4f}'} | {sec:.2f} |")
        text = f'frames/arm/config: {sorted(set(tuple(r[-1]) for r in rows))}\n\n' + '\n'.join(lines) + '\n'
        Path(sys.argv[2]).write_text(text)
        print(text)
    elif cmd == 'freeze':
        arms = {'M_full': json.loads(sys.argv[3]), 'M_adapt': json.loads(sys.argv[4])}
        out = Path(sys.argv[2])
        out.write_text(json.dumps(dict(arms=arms, dev_frames='1000..1199', dev_configs=list(CONFIGS), dev_snr_db=8.0,
                                       criterion='mean logloss_bits (mean over configs of per-config mean)', selection=sys.argv[5]),
                                  indent=1) + '\n')
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        Path(str(out) + '.sha256').write_text(f'{digest}  {out.name}\n')
        print(digest)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
