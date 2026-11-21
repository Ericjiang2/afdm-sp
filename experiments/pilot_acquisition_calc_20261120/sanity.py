"""Check that physical.regressors reproduces the generator's pilot response (P1 U/G, one frame each)."""
import sys
import numpy as np
sys.path.insert(0, '../tcom_reference_frame_20261015'); sys.path.insert(0, '../sp_afdm_frozen_20260920/src')
import p1_driver as d
from physical import regressors
ctx = d.load_context(); s = ctx.system; sf = d.make_seed_fn()
for sc in ('U', 'G'):
    raw, diag = d.generate(ctx, sc, 0.3, 5.0, 5400, sf)
    p = raw['params']
    A = regressors(raw['pilot'], np.asarray(p['l_i'], int), np.asarray(p['k_real'], float), s.c1, s.c2)
    model = A @ np.asarray(p['g_i'])
    resid = raw['y'] - np.sqrt(raw['sigma2']) * raw['noise']
    true_pilot = raw['H'] @ raw['pilot']
    print(sc, 'keys', sorted(raw)[:20])
    print(sc, 'rel err vs H@pilot', np.linalg.norm(model - true_pilot) / np.linalg.norm(true_pilot),
          '| vs y-noise-H@data', np.linalg.norm(model - (resid - raw['H'] @ raw['data'])) / np.linalg.norm(model),
          '| sum g', float(np.sum(np.abs(p['g_i']) ** 2)))
