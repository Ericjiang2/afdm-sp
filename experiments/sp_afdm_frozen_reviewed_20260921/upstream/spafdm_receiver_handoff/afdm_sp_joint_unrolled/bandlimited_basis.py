"""Public fixed time bases and observed-only delay-group selection.

These primitives describe a sampled CPP channel. They do not estimate a
continuous path Doppler or imply that a small projection error improves BER.
"""
from __future__ import annotations

import numpy as np

from .supplement_pilots import transform


def basis_from_public_band(family, n, q, sample_rate, max_doppler):
    if (type(n) is not int or type(q) is not int or not 0 < q <= n or q % 2 != 1
            or not np.isfinite([sample_rate, max_doppler]).all()
            or not 0 < max_doppler < sample_rate/2):
        raise ValueError("finite public band and positive odd basis dimension required")
    time = np.arange(n, dtype=float)
    if family == "dpss":
        covariance = np.sinc(2*max_doppler/sample_rate*(time[:, None]-time[None, :]))
        _, vectors = np.linalg.eigh(covariance)
        basis = vectors[:, -q:][:, ::-1].astype(complex)
    elif family in ("fourier", "gce"):
        frequencies = (np.arange(-(q//2), q//2+1)*sample_rate/n if family == "fourier"
                       else np.linspace(-max_doppler, max_doppler, q) if q > 1 else np.zeros(1))
        raw = np.exp(2j*np.pi*time[:, None]*frequencies[None, :]/sample_rate)/np.sqrt(n)
        basis = raw if family == "fourier" else np.linalg.qr(raw, mode="reduced")[0]
    else:
        raise ValueError("unregistered public basis family")
    # Fix phases at the first significant coordinate. An amplitude argmax is
    # unstable on equal-magnitude Fourier rows (and symmetric DPSS extrema):
    # tiny SIMD/roundoff differences can rotate the coefficient coordinates.
    for col in range(q):
        magnitudes = abs(basis[:, col])
        anchor = np.flatnonzero(magnitudes > 1e-12*magnitudes.max())[0]
        pivot = basis[anchor, col]
        basis[:, col] *= np.conj(pivot)/abs(pivot)
    if not np.allclose(basis.conj().T@basis, np.eye(q), atol=1e-10, rtol=0):
        raise ValueError("public basis lost orthonormality")
    return basis


def normalized_geometry(design, *, condition_limit=1e8):
    design = np.asarray(design)
    if (design.ndim != 2 or min(design.shape) == 0 or not np.isfinite(design).all()
            or not np.isfinite(condition_limit) or condition_limit < 1):
        raise ValueError("finite nonempty sensing matrix required")
    norms = np.linalg.norm(design, axis=0)
    if np.any(norms == 0):
        raise ValueError("zero sensing column")
    normalized = design/norms
    singular = np.linalg.svd(normalized, compute_uv=False)
    tolerance = max(normalized.shape)*np.finfo(float).eps*singular[0]
    rank = int(np.count_nonzero(singular > tolerance))
    full_rank = rank == design.shape[1]
    condition = float(singular[0]/singular[-1]) if full_rank else None
    gram = abs(normalized.conj().T@normalized)
    np.fill_diagonal(gram, 0)
    return dict(rows=design.shape[0], columns=design.shape[1], rank=rank,
                singular_values=singular.tolist(), column_norms=norms.tolist(),
                condition=condition, max_coherence=float(gram.max()),
                qualified=bool(full_rank and condition <= condition_limit))


def group_omp(design, observation, *, group_size, max_groups, condition_limit=1e8):
    """Select whole delay subspaces; reject dependent additions explicitly."""
    design, observation = np.asarray(design), np.asarray(observation)
    if (design.ndim != 2 or observation.shape != (design.shape[0],)
            or type(group_size) is not int or group_size < 1
            or design.shape[1] % group_size or type(max_groups) is not int
            or not 0 < max_groups <= design.shape[1]//group_size
            or not np.isfinite(design).all() or not np.isfinite(observation).all()):
        raise ValueError("invalid observed group selection inputs")
    groups = design.shape[1]//group_size
    projectors, rejected, banned = [], [], set()
    for delay in range(groups):
        block = design[:, delay*group_size:(delay+1)*group_size]
        info = normalized_geometry(block, condition_limit=condition_limit)
        if not info["qualified"]:
            banned.add(delay)
            rejected.append(dict(iteration=-1, delay=delay, reason="within_group_rank_or_condition",
                                 rank=info["rank"], condition=info["condition"]))
        projectors.append(np.linalg.qr(block, mode="reduced")[0])
    selected, columns, history = [], [], []
    residual = observation.copy()
    for iteration in range(max_groups):
        scores = np.array([float(np.vdot(u.conj().T@residual, u.conj().T@residual).real)
                           for u in projectors])
        excluded = set(selected) | banned
        scores[list(excluded)] = -np.inf
        chosen = None
        for delay in np.argsort(-scores, kind="stable"):
            delay = int(delay)
            if delay in excluded:
                continue
            proposed = columns+list(range(delay*group_size, (delay+1)*group_size))
            info = normalized_geometry(design[:, proposed], condition_limit=condition_limit)
            if not info["qualified"]:
                banned.add(delay)
                rejected.append(dict(iteration=iteration, delay=delay, reason="active_rank_or_condition",
                                     rank=info["rank"], condition=info["condition"]))
                continue
            chosen, columns = delay, proposed
            break
        if chosen is None:
            raise ValueError(f"rank/condition exclusions exhausted fixed group budget: {rejected}")
        selected.append(chosen)
        coefficients, _, rank, _ = np.linalg.lstsq(design[:, columns], observation, rcond=None)
        if rank != len(columns):
            raise ValueError("selected least-squares design lost rank")
        residual = observation-design[:, columns]@coefficients
        history.append(dict(iteration=iteration, delay=chosen, rank=int(rank),
                            condition=info["condition"], score=float(scores[chosen]),
                            residual_squared=float(np.vdot(residual, residual).real)))
    return dict(delays=selected, columns=columns, coefficients=coefficients,
                residual=residual, history=history, rejected_groups=rejected,
                group_qr_calls=groups, refits=len(history),
                geometry=normalized_geometry(design[:, columns], condition_limit=condition_limit))


class BasisGeometry:
    """CPP/DAFT operators for a fixed orthonormal time basis, scaled by sqrt(N)."""
    def __init__(self, basis, *, c1, c2, delay_cap, prefix_length):
        basis = np.asarray(basis, dtype=complex)
        if (basis.ndim != 2 or min(basis.shape) == 0 or basis.shape[1] > basis.shape[0]
                or not np.isfinite(basis).all() or not np.isfinite([c1, c2]).all()
                or type(delay_cap) is not int or type(prefix_length) is not int
                or not 0 <= delay_cap <= prefix_length < basis.shape[0]
                or not np.allclose(basis.conj().T@basis, np.eye(basis.shape[1]), atol=1e-10, rtol=0)):
            raise ValueError("orthonormal basis and valid public CPP geometry required")
        self.basis = basis.copy()
        self.basis.flags.writeable = False
        self.n, self.q = basis.shape
        self.c1, self.c2 = float(c1), float(c2)
        self.delay_cap, self.prefix_length = delay_cap, prefix_length
        self.values = np.sqrt(self.n)*basis
        time = np.arange(self.n, dtype=float)
        self.l1, self.l2 = np.exp(2j*np.pi*self.c1*time*time), np.exp(2j*np.pi*self.c2*time*time)

    def _delays(self, delays):
        delays = np.arange(self.delay_cap+1) if delays is None else np.asarray(delays)
        if (delays.ndim != 1 or len(delays) == 0 or np.iscomplexobj(delays)
                or not np.isfinite(delays).all() or np.any(delays != np.floor(delays))
                or np.any(delays < 0) or np.any(delays > self.delay_cap)
                or len(set(delays.tolist())) != len(delays)):
            raise ValueError("unique public integer delays within CPP required")
        return delays.astype(int)

    def _indices_phase(self, delays):
        source_time = np.arange(self.n)[:, None]-delays[None, :]
        phase = np.ones(source_time.shape, complex)
        negative = source_time < 0
        phase[negative] = np.exp(2j*np.pi*self.c1*(self.n*self.n+2*self.n*source_time[negative]))
        return source_time % self.n, phase

    def sensing(self, symbols, delays=None):
        symbols = np.asarray(symbols)
        if symbols.shape != (self.n,) or not np.isfinite(symbols).all():
            raise ValueError("finite public transmitted-moment vector required")
        delays = self._delays(delays)
        waveform = transform(symbols, self.c1, self.c2, inverse=True)
        indices, phase = self._indices_phase(delays)
        delayed = waveform[indices]*phase
        columns = (delayed[:, :, None]*self.values[:, None, :]).reshape(self.n, -1)
        # Batched form of production transform(), with columns as RHS vectors.
        return self.l2[:, None]*np.fft.fft(self.l1[:, None]*columns, axis=0)/np.sqrt(self.n)

    def channel(self, delays, coefficients):
        delays = self._delays(delays)
        coefficients = np.asarray(coefficients)
        if coefficients.shape != (len(delays)*self.q,) or not np.isfinite(coefficients).all():
            raise ValueError("finite coefficients matched to declared delay groups required")
        envelope = self.values@coefficients.reshape(len(delays), self.q).T
        indices, phase = self._indices_phase(delays)
        time_matrix = np.zeros((self.n, self.n), complex)
        rows = np.arange(self.n)
        for group in range(len(delays)):
            time_matrix[rows, indices[:, group]] += envelope[:, group]*phase[:, group]
        chirped = self.l1[:, None]*time_matrix*self.l1.conj()[None, :]
        transformed = np.fft.ifft(np.fft.fft(chirped, axis=0, norm="ortho"), axis=1, norm="ortho")
        return self.l2[:, None]*transformed*self.l2.conj()[None, :]
