#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l02 (2026-11-21, runner l): the receiver's outer-round schedule in the EXIT model.
  /opt/anaconda3/bin/python ideas/l2/l2_exit_schedule.py ideas/l2/out3/exit_schedule.json"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import l2_exit_tunnel as X  # noqa: E402
ROUNDS, DEC_ITERS = 10, 50


def decode(E, i_ch, iters=DEC_ITERS):
    """Decoder from zero messages on a fixed channel information i_ch. Returns (check-to-variable information, extrinsic to the detector)."""
    ic = 0.0; s_ch = float(X.Jinv(i_ch)) if i_ch > 0 else 0.0
    for _ in range(iters):
        s_c = float(X.Jinv(ic)) if ic > 0 else 0.0
        iev = float(np.sum(E['lam'] * X.J(np.sqrt((E['d'] - 1) * s_c ** 2 + s_ch ** 2))))
        new = 1 - sum(r * X.J(np.sqrt(k - 1) * X.Jinv(1 - iev)) for k, r in E['rho'].items())
        if new - ic < 1e-9:
            ic = new; break
        ic = new
    s_c = float(X.Jinv(ic)) if ic > 0 else 0.0
    return ic, float(np.sum(E['Ld'] * X.J(np.sqrt(E['d']) * s_c)))


def outer(E, x, y, rounds=ROUNDS):
    ia = 0.0; traj = []
    for r in range(1, rounds + 1):
        ic, ia = decode(E, float(np.interp(ia, x, y))); traj.append(round(ia, 4))
        if ic > 1 - 1e-4:
            return r, traj
    return None, traj


def main():
    P = json.loads(X.PHI.read_text())['Phi']; names = dict(X.candidates())
    prev = json.loads((Path(__file__).resolve().parent / 'out3' / 'exit_tunnel.json').read_text())['min_snr']
    ctl = json.loads((Path(__file__).resolve().parent / 'out3' / 'exit_tunnel_awgn_control.json').read_text())
    awgn = ctl['best_awgn'][0][1]; res = dict(_argv=sys.argv, rounds=ROUNDS, decoder_iterations=DEC_ITERS, awgn_best=awgn, cells={})
    for snr in ('6.5', '8'):
        for L in P[snr]:
            x, y = X.transfer(P, snr, L)
            sp = prev[L]['best_irregular'] if L in prev else prev['L28']['best_irregular']
            codes = {'reg36': names['(3,6) regular'], 'awgn_best': names[awgn], 'sp_best': names[sp]}
            res['cells'][f'{snr}dB_{L}'] = dict(sp_best_name=sp, **{k: dict(zip(('rounds', 'trajectory'), outer(E, x, y))) for k, E in codes.items()},
                                               sp_best_rounds_100=outer(codes['sp_best'], x, y, 100)[0], reg36_rounds_100=outer(codes['reg36'], x, y, 100)[0])
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1))
    for k, v in res['cells'].items():
        print(k, 'rounds to decode within 10: (3,6)', v['reg36']['rounds'], '| AWGN-best', v['awgn_best']['rounds'], '| inner-loop-best', v['sp_best']['rounds'],
              '| within 100: (3,6)', v['reg36_rounds_100'], 'inner-loop-best', v['sp_best_rounds_100'])


if __name__ == '__main__':
    main()
