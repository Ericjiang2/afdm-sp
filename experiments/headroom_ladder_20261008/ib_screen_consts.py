#!/usr/bin/env python
"""Extract the generator constants the information-budget screen needs (frozen context, run once on deinlab):
N, c1, c2, the frozen unit-power ZC pilot (DAFT domain) and its IDAFT.  Writes out/ib_screen/consts.json (sha256 of the sources recorded) so that the
screen itself is plain numpy.  Checks that the numpy IDAFT used by ib_screen_core equals physical.daft(.., inverse=True) to 1e-12.
    python -B ib_screen_consts.py     (inside `source env_single.sh; conda activate AFDM`)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'ib_screen'


def main():
    import driver_c1
    ns = SimpleNamespace(project=HERE.parents[1], native_dir='sp_afdm_native_joint_reviewed_20260921',
                         baseline_dir='sp_afdm_frozen_reviewed_20260921')
    ctx = driver_c1.load_context(ns)
    from physical import daft
    s = ctx.system
    n = int(s.N_total)
    zc = np.asarray(s._zc_seq, complex)
    k = np.arange(n)
    l1, l2 = np.exp(2j * np.pi * s.c1 * k * k), np.exp(2j * np.pi * s.c2 * k * k)
    mine = np.conj(l1) * np.fft.ifft(np.conj(l2) * zc) * np.sqrt(n)
    ref = daft(zc, s.c1, s.c2, True)
    err = float(np.max(np.abs(mine - ref)))
    assert err < 1e-12, err
    q = np.exp(2j * np.pi * np.random.default_rng(1).random(n))
    err2 = float(np.max(np.abs(np.conj(l1) * np.fft.ifft(np.conj(l2) * q) * np.sqrt(n) - daft(q, s.c1, s.c2, True))))
    assert err2 < 1e-12
    out = dict(N=n, c1=float(s.c1), c2=float(s.c2), l_max_cap=int(s.l_max_cap), zc_re=zc.real.tolist(), zc_im=zc.imag.tolist(),
               zc_abs_min=float(np.abs(zc).min()), zc_abs_max=float(np.abs(zc).max()), idaft_check_max_abs=err, idaft_check2=err2,
               source_sha256={k2: v for k2, v in ctx.sources.items() if k2 in ('driver.py', 'driver_c1.py', 'dpss_rx.py', 'tapchannel.py', 'orders.py')},
               _argv=sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'consts.json').write_text(json.dumps(out))
    print('N', n, 'c1', s.c1, 'c2', s.c2, 'l_max_cap', s.l_max_cap, '|zc| in', out['zc_abs_min'], out['zc_abs_max'], 'idaft check', err, err2)


if __name__ == '__main__':
    main()
