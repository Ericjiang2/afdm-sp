"""Soft-only replay of the frozen LDPC flooding schedule."""

import numpy as np


def soft_app(native, code, llr, iterations, *, early_stop=False):
    # Source: frozen e1_ldpc.py::_decode_llr_core. Its public APIs return a
    # decoded word. Keep the same floating-point message updates, and use
    # archived sweep counts wherever available.
    decoder = native.decoder_messages.__globals__['decode_soft_messages']
    phi = decoder.__globals__['_phi']
    chk, var, row_ptr = code['chk'], code['var'], code['row_ptr']
    m, n = code['H'].shape
    if llr.shape != (n,) or not np.isfinite(llr).all() or not 1 <= iterations <= 50:
        raise ValueError('Invalid soft replay input or sweep count')
    row_deg = np.diff(row_ptr)
    msg_c2v = np.zeros(chk.size, dtype=float)
    for _ in range(iterations):
        total = llr + np.bincount(var, weights=msg_c2v, minlength=n)
        msg_v2c = total[var] - msg_c2v
        neg = (msg_v2c < 0).astype(np.int64)
        ph = phi(np.abs(msg_v2c))
        ph_sum = np.add.reduceat(ph, row_ptr[:-1])
        neg_sum = np.add.reduceat(neg, row_ptr[:-1])
        ph_ext = np.repeat(ph_sum, row_deg) - ph
        neg_ext = np.repeat(neg_sum, row_deg) - neg
        msg_c2v = (1.0 - 2.0 * (neg_ext & 1)) * phi(ph_ext)
        if early_stop:
            total = llr + np.bincount(var, weights=msg_c2v, minlength=n)
            # Verify check parity from edge signs for stopping the soft
            # updates, without constructing a hard word or scoring it.
            parity = np.bincount(chk, weights=(total[var] < 0).astype(float),
                                 minlength=m).astype(np.int64) & 1
            if not parity.any():
                break
    check = np.bincount(var, weights=msg_c2v, minlength=n)
    return llr + check, check
