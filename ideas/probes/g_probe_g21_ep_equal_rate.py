#!/usr/bin/env python3
"""Read-only L1 sanity probe for I-20261122-g21 (<= 30 s on local CPU).
Checks Scenario-S EP performance in experiments/tcom_reference_frame_20261015/ep_rx.py
when EP's code rate is matched to deliver ~1024 info bits/frame (n=1530, d_v=3, d_c=9 -> k=1022)
under identical total frame energy (N=1024), guard width (259), channel, noise, estimator and detector.
"""
import os
import sys
import time

os.environ.update(
    OMP_NUM_THREADS='1',
    OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',
    VECLIB_MAXIMUM_THREADS='1',
    NUMEXPR_NUM_THREADS='1',
)
M = '/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation'
sys.path[:0] = [M, M + '/experiments/tcom_reference_frame_20261015']

import numpy as np
import ep_rx as E
import gen_fixed
import p1_driver as P
from afdm_sp_joint_unrolled.e1_ldpc import build_code


def main():
    t0 = time.time()
    cdir = '/Users/guoyikun/.cache/idea-funnel/afdm-20261122-g/ldpc'
    os.makedirs(cdir, exist_ok=True)
    ctx = P.load_context()
    code_r23 = build_code(1530, d_v=3, d_c=9, seed=20260726, cache_dir=cdir)
    ep23 = E.EP(ctx.system, code_r23)
    flags = gen_fixed.Flags(
        fix_delay_cap=True, fix_delay_grid=True, doppler_law='geometric',
        fix_energy=True, delay_scale=25.0 / 102.0, l_trunc=25,
    )
    seed_fn = P.make_seed_fn('ca68a12bfdb5c0a5e797efb26e6c71c4c4f30cc46113c33e8b8c962da6a789b8', 0x54434450)
    snrs = [5.0, 5.5, 6.0, 6.5, 7.0]
    res = {(tag, snr): 0 for tag in ('ep23_p10', 'ep23_p15', 'epg23_p10') for snr in snrs}
    nf = 6
    for f in range(500, 500 + nf):
        raw0, _ = P.generate(ctx, flags, 0.3, 5.0, f, seed_fn)
        noise = raw0['noise']
        rf = gen_fixed.make_rng_factory(seed_fn, f)
        h_true = raw0['H']
        g_gram = E.gram(ep23, h_true)
        info23 = rf(0, f, 2, split=2).integers(0, 2, size=1024).astype(np.uint8)[:ep23.k]
        x23_10 = E.make_frame(ep23, info23, 0.10)[0]
        x23_15 = E.make_frame(ep23, info23, 0.15)[0]
        for snr in snrs:
            s2 = 10.0 ** (-snr / 10.0)
            r10 = E.run_ep(ep23, E.observe(ep23, h_true, x23_10, noise, s2), s2, 0.10, info23,
                           H_true=h_true, genie_gram=g_gram, arms=('EP', 'EPG'))
            r15 = E.run_ep(ep23, E.observe(ep23, h_true, x23_15, noise, s2), s2, 0.15, info23, arms=('EP',))
            res[('ep23_p10', snr)] += int(r10['EP']['info_errors'] > 0)
            res[('epg23_p10', snr)] += int(r10['EPG']['info_errors'] > 0)
            res[('ep23_p15', snr)] += int(r15['EP']['info_errors'] > 0)
    for snr in snrs:
        print(f'SNR={snr:.1f}dB:', {t: f'{res[(t, snr)]}/{nf}' for t in ('ep23_p10', 'ep23_p15', 'epg23_p10')})
    print('k_ep23 =', ep23.k, 'elapsed:', round(time.time() - t0, 2), 's')


if __name__ == '__main__':
    main()
