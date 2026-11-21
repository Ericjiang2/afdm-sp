"""Low-eigenvalue projector of the closed-form co-delay Doppler kernel."""

import numpy as np


def block_projector(dopplers, n, tau):
    from physical import dkernel

    kernel = dkernel(dopplers[..., None, :] - dopplers[..., :, None], n)
    values, vectors = np.linalg.eigh((kernel + kernel.swapaxes(-1, -2).conj()) * .5)
    low = values < tau
    return ((vectors * low[..., None, :]) @ vectors.swapaxes(-1, -2).conj(),
            np.count_nonzero(low, axis=-1))


def low_projector(delays, dopplers, n, tau=.5):
    delays = np.asarray(delays)
    dopplers = np.asarray(dopplers)
    projector = np.zeros((len(delays), len(delays)), dtype=complex)
    if tau:
        for delay in np.unique(delays):
            indices = np.flatnonzero(delays == delay)
            if len(indices) > 1:
                projector[np.ix_(indices, indices)], _ = block_projector(dopplers[indices], n, tau)
    return projector
