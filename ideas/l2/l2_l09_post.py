#!/usr/bin/env python3
"""Post-processing for card I-20261121-l09 stage 1 (2026-11-21, runner l): thresholds from the tables of l2_l09_cluster.py.
  /opt/anaconda3/bin/python ideas/l2/l2_l09_post.py ideas/l2/out9/l09_cluster.json ideas/l2/out9/l09_thresholds.json"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import l2_exit_tunnel as X  # noqa: E402

d = json.loads(Path(sys.argv[1]).read_text()); snrs = np.array(d['_config']['snrs']); vs = np.array(d['_config']['vs'])
xg, wg = np.polynomial.hermite_e.hermegauss(64); wg = wg / wg.sum()
def v_of(ia):                                   # residual symbol variance when the decoder extrinsic information is ia
    if ia <= 1e-9: return 1.0
    if ia >= 1 - 1e-9: return 0.0
    s = float(X.Jinv(ia)); L = s * s / 2 + s * xg
    return float(1 - np.sum(wg * np.tanh(L / 2) ** 2))
ia = np.linspace(0, 1, 201); vg = np.array([v_of(a) for a in ia]); reg = X.ensemble({3: 1.0}, 6.0); order = np.argsort(vs)
fine = np.arange(snrs[0], snrs[-1] + 1e-9, 0.05); res = dict(_argv=sys.argv, G1_max=d['G1_max'])
CH = d['_config'].get('channels', ('p1', 'cluster'))
for ch in CH:
    out = {}
    for b in ('afdm', 'sc', 'ofdm'):
        T = np.array(d[ch][b]); thr1 = float(np.interp(0.57, T[:, 0], snrs)); tun = None
        for s in fine:
            row = np.array([np.interp(s, snrs, T[:, j]) for j in range(len(vs))])
            y = np.interp(vg, vs[order], row[order])
            if X.opens(reg, ia, np.maximum.accumulate(y)):
                tun = float(s); break
        i4 = int(np.argmin(np.abs(snrs - 4.0)))
        out[b] = dict(threshold_v1_db=thr1, tunnel_threshold_db=tun, I_4dB_v1=float(T[i4, 0]), I_4dB_v0=float(T[i4, -1]))
    out['diag_cv'] = d[ch]['diag_cv']
    out['afdm_minus_sc_tunnel_db'] = out['afdm']['tunnel_threshold_db'] - out['sc']['tunnel_threshold_db']
    out['ofdm_minus_afdm_tunnel_db'] = out['ofdm']['tunnel_threshold_db'] - out['afdm']['tunnel_threshold_db']
    res[ch] = out
if 'p1' in res:
    res['claim_i_holds'] = bool(abs(res['p1']['afdm_minus_sc_tunnel_db']) <= 0.15)
    res['claim_iii_holds'] = bool(res['cluster']['afdm_minus_sc_tunnel_db'] <= -0.5)
Path(sys.argv[2]).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
