"""Zero-simulation check of the detector gain re-estimation lead (prediction P7, research-assets/prediction-ledger.md).

On the 10-18 prospective K-family rows: does fixing the gains (K-diag-fullfix) help more than letting the detector
re-estimate them jointly (K-diag) specifically in units whose diagonal-Gamma geometry holds near-collinear co-delay pairs?
Strata by the largest |D_N(dnu)| over co-delay pairs in the K-diag final geometry. Net gain = share(fullfix rescues and
K-diag fails) - share(reverse). Frame-cluster bootstrap, 2000 resamples. Usage: python check.py '<rows_K glob>'
"""
import glob
import gzip
import json
import math
import random
import sys

N = 1024
BINS = (('none', None), ('[0,.5)', (0, .5)), ('[.5,.8)', (.5, .8)), ('[.8,1]', (.8, 1.01)))


def abs_dn(x):
    x = abs(x)
    return 1.0 if x == 0 else abs(math.sin(math.pi * x) / (N * math.sin(math.pi * x / N)))


def max_dn(delays, dopplers):
    best = None
    for i in range(len(delays)):
        for j in range(i + 1, len(delays)):
            if delays[i] == delays[j]:
                d = abs_dn(dopplers[i] - dopplers[j])
                best = d if best is None else max(best, d)
    return best


units = []
same_atoms = 0
for f in sorted(glob.glob(sys.argv[1])):
    for line in gzip.open(f, 'rt'):
        r = json.loads(line)
        if r['family'] != 'K' or not r.get('triggered') or not r.get('arms'):
            continue
        kd, kf = r['arms']['K-diag'], r['arms']['K-diag-fullfix']
        same_atoms += (kd['final_delays'] == kf['final_delays'] and kd['final_dopplers'] == kf['final_dopplers'])
        m = max_dn(kd['final_delays'], kd['final_dopplers'])
        stratum = 'none' if m is None else next(name for name, rng in BINS[1:] if rng[0] <= m < rng[1])
        units.append(dict(frame=r['frame'], stratum=stratum,
                          x=int(kd['info_errors'] > 0 and kf['info_errors'] == 0),
                          y=int(kd['info_errors'] == 0 and kf['info_errors'] > 0),
                          kd_ok=int(kd['info_errors'] == 0), kf_ok=int(kf['info_errors'] == 0)))

frames = sorted({u['frame'] for u in units})
by_frame = {fr: [u for u in units if u['frame'] == fr] for fr in frames}
rng = random.Random(20261019)
out = dict(n_units=len(units), atoms_identical_kdiag_vs_fullfix=same_atoms, strata={})
for name, _ in BINS:
    sel = [u for u in units if u['stratum'] == name]
    if not sel:
        out['strata'][name] = dict(n=0)
        continue
    net = (sum(u['x'] for u in sel) - sum(u['y'] for u in sel)) / len(sel)
    boots = []
    for _ in range(2000):
        draw = [u for fr in (rng.choice(frames) for _ in frames) for u in by_frame[fr] if u['stratum'] == name]
        if draw:
            boots.append((sum(u['x'] for u in draw) - sum(u['y'] for u in draw)) / len(draw))
    boots.sort()
    out['strata'][name] = dict(n=len(sel), rescue_kdiag=round(sum(u['kd_ok'] for u in sel) / len(sel), 4),
                               rescue_fullfix=round(sum(u['kf_ok'] for u in sel) / len(sel), 4),
                               fix_only=sum(u['x'] for u in sel), kdiag_only=sum(u['y'] for u in sel),
                               net=round(net, 4), ci=[round(boots[int(.025 * len(boots))], 4), round(boots[int(.975 * len(boots)) - 1], 4)])
print(json.dumps(out, indent=1))
