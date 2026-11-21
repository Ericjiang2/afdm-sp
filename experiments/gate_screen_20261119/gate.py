"""Frozen half-variance decision on isolated co-delay blocks."""

import numpy as np


def hermitian(matrix):
    return (matrix + matrix.conj().T) / 2


def pair_contrast(dirichlet):
    """Unit contrast orthogonal to the phase-aligned pair sum."""
    cross = dirichlet[0, 1]
    phase = cross / abs(cross) if cross else 1.
    return np.array([phase, -1.]) / np.sqrt(2.)


def floor_pair(gram, gamma, ridge, p):
    q0 = hermitian(gamma) + ridge * np.eye(2)
    q1 = q0 + hermitian(gram)
    return bool(2 * np.vdot(p, np.linalg.solve(q1, p)).real
                > np.vdot(p, np.linalg.solve(q0, p)).real)


def compare_block(gram, dirichlet, uncertainty, ridge):
    """Return gate rank, S-lo rank and trace of the projector product."""
    values, modes = np.linalg.eigh(dirichlet)
    low = modes[:, values < .5]
    q0 = uncertainty * dirichlet + ridge * np.eye(len(dirichlet))
    q1 = q0 + hermitian(gram)
    if len(dirichlet) == 2:
        contrast = pair_contrast(dirichlet)
        selected = contrast[:, None] if floor_pair(gram, uncertainty * dirichlet, ridge, contrast) else modes[:, :0]
    else:
        protected = modes[:, values < 1.]
        # Project the inverse quadratic forms, not the inverse of a restricted precision.
        difference = protected.conj().T @ (2 * np.linalg.solve(q1, protected)
                                           - np.linalg.solve(q0, protected))
        eig, vectors = np.linalg.eigh(hermitian(difference))
        selected = protected @ vectors[:, eig > 0.]
    overlap_trace = np.linalg.norm(selected.conj().T @ low, ord='fro') ** 2
    return selected.shape[1], low.shape[1], float(overlap_trace)
