"""Offline physical-channel and codeword diagnostics for the TF gap audit.

Inputs ``x`` and ``y`` are AF-domain vectors.  ``response_matrix`` and all
likelihood scores use the unitary time-domain observation ``Y=IDAFT(y)``.
The production source directories must be on ``sys.path`` before a helper
that constructs a physical channel is called.  No receiver is run here.
"""

from __future__ import annotations

import numpy as np


def _complex_vector(value, name, n=None):
    a = np.asarray(value, dtype=complex)
    if a.ndim != 1 or (n is not None and a.shape != (n,)) or not np.isfinite(a).all():
        raise ValueError(f"invalid {name}")
    return a


def _geometry(delays, dopplers, n):
    l = np.asarray(delays)
    nu = np.asarray(dopplers, dtype=float)
    if l.ndim != 1 or not len(l) or l.shape != nu.shape:
        raise ValueError("invalid path geometry")
    if not np.issubdtype(l.dtype, np.integer) or np.any(l < 0) or np.any(l >= n):
        raise ValueError("invalid delays")
    if not np.isfinite(nu).all():
        raise ValueError("nonfinite Dopplers")
    return l.astype(int), nu


def response_matrix(x, delays, dopplers, c1, c2, *, derivative=False):
    """Exact CPP path responses in time; derivative is with respect to real nu.

    The returned derivative has the same shape as B and includes the complete
    CPP phase.  It multiplies each column by 2*pi*i*time_index/N.
    """
    from physical import Channel, daft
    from twofft import TimePathOps

    x = _complex_vector(x, "AF input")
    n = len(x)
    l, nu = _geometry(delays, dopplers, n)
    c = Channel(n, c1, c2, l, nu, np.ones(len(l), complex))
    ops = TimePathOps(c)
    B = ops.responses_time(daft(x, c1, c2, True))
    if derivative:
        return B, B * (2j * np.pi * np.arange(n)[:, None] / n)
    return B


def score_geometry(Y, B, sigma2, *, conditional_gains=None, ridge_lambda=None):
    """Score one fixed geometry; all values are lower-is-better.

    ``ridge_lambda`` multiplies ||h||^2 in unscaled squared-error units, so
    ridge_score=(||Y-Bh||^2+lambda||h||^2)/sigma2.  Marginal uses the declared
    CN(0,I/P) working prior.  Conditional gains are never fitted implicitly.
    ``profile_rank`` makes deficient geometries visible; SVD gives the declared
    minimum-norm unregularized solution.
    """
    Y = _complex_vector(Y, "time observation")
    B = np.asarray(B, dtype=complex)
    if B.ndim != 2 or B.shape[0] != len(Y) or B.shape[1] < 1 or not np.isfinite(B).all():
        raise ValueError("invalid response matrix")
    if not np.isfinite(sigma2) or sigma2 <= 0:
        raise ValueError("invalid complex noise variance")
    if ridge_lambda is not None and (not np.isfinite(ridge_lambda) or ridge_lambda <= 0):
        raise ValueError("ridge lambda must be positive")
    U, s, Vh = np.linalg.svd(B, full_matrices=False)
    if not len(s) or s[0] == 0:
        raise ValueError("all-zero response matrix")
    tol = max(B.shape) * np.finfo(float).eps * s[0]
    keep = s > tol
    rank = int(np.count_nonzero(keep))
    z = U.conj().T @ Y
    hz = np.zeros(len(s), complex)
    hz[keep] = z[keep] / s[keep]
    h_profile = Vh.conj().T @ hz
    profile = float(np.vdot(Y - B @ h_profile, Y - B @ h_profile).real / sigma2)
    tau = 1.0 / B.shape[1]
    # The covariance is sigma2*I+tau*B B^H; the orthogonal complement keeps
    # variance sigma2.  This form avoids cancellation in a Woodbury subtract.
    orth = max(float(np.vdot(Y, Y).real - np.vdot(z, z).real), 0.0)
    marginal = float(orth / sigma2 + np.sum(abs(z) ** 2 / (sigma2 + tau * s**2))
                     + np.sum(np.log1p(tau * s**2 / sigma2)))
    gram_eigenvalues = np.linalg.eigvalsh(B.conj().T @ B).real
    if gram_eigenvalues[0] < -1e-9 * max(1.0, gram_eigenvalues[-1]):
        raise FloatingPointError("response Gram is not positive semidefinite")
    out = dict(profile_score=profile, profile_gains=h_profile, profile_rank=rank,
               profile_singular_values=s, response_gram_eigenvalues=np.maximum(gram_eigenvalues, 0),
               marginal_score=marginal, marginal_prior_variance=tau,
               marginal_posterior_mean=Vh.conj().T @ (tau * s * z / (sigma2 + tau * s**2)))
    if conditional_gains is not None:
        h0 = _complex_vector(conditional_gains, "conditional gains", B.shape[1])
        r0 = Y - B @ h0
        out["conditional_score"] = float(np.vdot(r0, r0).real / sigma2)
    if ridge_lambda is not None:
        h_ridge = Vh.conj().T @ (s * z / (s**2 + ridge_lambda))
        r = Y - B @ h_ridge
        out["ridge_score"] = float((np.vdot(r, r).real + ridge_lambda * np.vdot(h_ridge, h_ridge).real) / sigma2)
        out["ridge_gains"] = h_ridge
        out["ridge_lambda"] = float(ridge_lambda)
    return out


def _bounds(bounds, p):
    b = np.asarray(bounds, dtype=float)
    if b.shape != (p, 2) or not np.isfinite(b).all() or np.any(b[:, 0] >= b[:, 1]):
        raise ValueError("invalid Doppler bounds")
    return b


def search_geometry(Y, x, delays, starts, bounds, c1, c2, sigma2, *,
                    objective="profile", ridge_lambda=None, passes=2, maxiter=16):
    """Finite local same-delay Doppler search with every score evaluation charged.

    ``starts`` is an explicit (K,P) deterministic grid.  Each start receives
    bounded golden-section coordinate passes.  This does not claim a global
    optimum.  The returned gains belong to the selected objective.
    """
    Y = _complex_vector(Y, "time observation")
    x = _complex_vector(x, "AF input", len(Y))
    l, _ = _geometry(delays, np.zeros(len(delays)), len(Y))
    p = len(l)
    bounds = _bounds(bounds, p)
    starts = np.asarray(starts, dtype=float)
    if starts.ndim == 1:
        starts = starts[None, :]
    if starts.ndim != 2 or starts.shape[1] != p or not len(starts) or not np.isfinite(starts).all():
        raise ValueError("invalid search starts")
    if np.any(starts < bounds[:, 0] - 1e-12) or np.any(starts > bounds[:, 1] + 1e-12):
        raise ValueError("start outside bounds")
    if objective not in ("profile", "marginal", "ridge"):
        raise ValueError("unknown search objective")
    if objective == "ridge" and ridge_lambda is None:
        raise ValueError("ridge search needs ridge lambda")
    if not isinstance(passes, int) or passes < 0 or not isinstance(maxiter, int) or maxiter < 1:
        raise ValueError("invalid search budget")
    key = objective + "_score"
    count = 0
    k = np.arange(len(Y))[:, None]
    reference = starts[0]
    # The CPP wrap factor and IDAFT(x) stay fixed as Doppler moves.
    base = response_matrix(x, l, reference, c1, c2) * np.exp(-2j * np.pi * k * reference[None, :] / len(Y))

    def evaluate(nu):
        nonlocal count
        B = base * np.exp(2j * np.pi * k * nu[None, :] / len(Y))
        scores = score_geometry(Y, B, sigma2, ridge_lambda=ridge_lambda)
        count += 1
        return float(scores[key]), scores

    best = None
    for start in starts:
        nu = start.copy()
        value, scores = evaluate(nu)
        for _ in range(passes):
            for j, (lo, hi) in enumerate(bounds):
                # Endpoints and the current coordinate are explicitly evaluated;
                # fixed-iteration golden search makes the budget deterministic.
                trial = nu.copy()
                for edge in (lo, hi):
                    trial[j] = edge
                    v, sc = evaluate(trial)
                    if v < value:
                        value, scores = v, sc
                        nu[j] = edge
                a, b = float(lo), float(hi)
                phi = (np.sqrt(5.0) - 1.0) / 2.0
                q1, q2 = b - phi * (b - a), a + phi * (b - a)
                trial[j] = q1
                f1, sc1 = evaluate(trial)
                trial[j] = q2
                f2, sc2 = evaluate(trial)
                for _ in range(maxiter - 1):
                    if f1 <= f2:
                        b, q2, f2, sc2 = q2, q1, f1, sc1
                        q1 = b - phi * (b - a)
                        trial[j] = q1
                        f1, sc1 = evaluate(trial)
                    else:
                        a, q1, f1, sc1 = q1, q2, f2, sc2
                        q2 = a + phi * (b - a)
                        trial[j] = q2
                        f2, sc2 = evaluate(trial)
                if f1 < value:
                    value, scores = f1, sc1
                    nu[j] = q1
                if f2 < value:
                    value, scores = f2, sc2
                    nu[j] = q2
        if best is None or value < best[0]:
            best = value, nu.copy(), scores
    value, nu, scores = best
    gain_key = {"profile": "profile_gains", "ridge": "ridge_gains", "marginal": "marginal_posterior_mean"}[objective]
    return dict(score=value, objective=objective, delays=l.copy(), dopplers=nu,
                gains=scores[gain_key], scores=scores, evaluations=count,
                starts_count=len(starts), coordinate_passes=passes, bounds=bounds.copy())


def axial_grid_starts(center, bounds):
    """Center plus each coordinate's lower/mid/upper point, deduplicated."""
    center = np.asarray(center, dtype=float)
    if center.ndim != 1 or not np.isfinite(center).all():
        raise ValueError("invalid center")
    b = _bounds(bounds, len(center))
    if np.any(center < b[:, 0]) or np.any(center > b[:, 1]):
        raise ValueError("center outside bounds")
    starts = [center.copy()]
    for j in range(len(center)):
        for v in (b[j, 0], np.mean(b[j]), b[j, 1]):
            t = center.copy()
            t[j] = v
            if not any(np.array_equal(t, previous) for previous in starts):
                starts.append(t)
    return np.asarray(starts)


def final_refit_bounds(center, *, expanded=False):
    """Original saved final-refit interval or the declared [-3,3] expansion."""
    center = np.asarray(center, dtype=float)
    if center.ndim != 1 or not len(center) or not np.isfinite(center).all() or np.any(abs(center) > 3):
        raise ValueError("invalid final-refit centers")
    if expanded:
        return np.tile([-3.0, 3.0], (len(center), 1))
    return np.column_stack((np.maximum(-3.0, center - 0.75),
                            np.minimum(3.0, center + 0.75)))


def fit_true_data(y, pilot, true_symbols, delays, center, bounds, c1, c2, sigma2, *,
                  objective="profile", ridge_lambda=None, passes=2, maxiter=16,
                  grid_starts=False):
    """Fit measured y with true mapped data and supplied acquired delay slots.

    ``center`` and ``bounds`` come from the saved receiver geometry, not truth.
    The routine never receives truth gains or truth Dopplers.
    """
    from physical import daft

    y = _complex_vector(y, "AF observation")
    pilot = _complex_vector(pilot, "pilot", len(y))
    true_symbols = _complex_vector(true_symbols, "true mapped data", len(y))
    Y = daft(y, c1, c2, True)
    starts = axial_grid_starts(center, bounds) if grid_starts else np.asarray(center, float)[None, :]
    return search_geometry(Y, pilot + true_symbols, delays, starts, bounds, c1, c2,
                           sigma2, objective=objective, ridge_lambda=ridge_lambda,
                           passes=passes, maxiter=maxiter)


def operator_mismatch(fitted, truth, pilot, *, data_covariance, data_mean=None):
    """Exact physical overlap and SP-weighted mismatch for two Channels.

    ``data_covariance`` may be scalar Pd for a proven pairwise independent
    mapped code, its actual full AF-domain covariance, or a sparse correction
    dict with ``diagonal, rows, cols, values``.  ``data_mean`` is used for
    biased symbols.  The caller must establish those code moments.
    """
    from physical import Channel
    from twofft import TimePathOps

    if (fitted.n, fitted.c1, fitted.c2) != (truth.n, truth.c1, truth.c2):
        raise ValueError("channel coordinate mismatch")
    n = truth.n
    pilot = _complex_vector(pilot, "pilot", n)
    l = np.concatenate((fitted.delays, truth.delays))
    nu = np.concatenate((fitted.dopplers, truth.dopplers))
    delta_h = np.concatenate((fitted.gains, -truth.gains))
    delta = Channel(n, truth.c1, truth.c2, l, nu, delta_h)
    R = TimePathOps(delta).R
    power = float(np.vdot(delta_h, R @ delta_h).real)
    if power < -1e-9 * max(1.0, np.vdot(delta_h, delta_h).real):
        raise FloatingPointError("negative physical operator power")
    operator_fro2 = n * max(power, 0.0)
    mean = np.zeros(n, complex) if data_mean is None else _complex_vector(data_mean, "data mean", n)
    difference_pilot = delta.apply(pilot + mean)
    pilot_mismatch = float(np.vdot(difference_pilot, difference_pilot).real)
    if isinstance(data_covariance, dict):
        keys = {'diagonal', 'rows', 'cols', 'values'}
        if set(data_covariance) != keys:
            raise ValueError('invalid sparse data covariance keys')
        diagonal = np.asarray(data_covariance['diagonal'], dtype=float)
        rows = np.asarray(data_covariance['rows'])
        cols = np.asarray(data_covariance['cols'])
        values = np.asarray(data_covariance['values'], dtype=complex)
        if (rows.ndim != 1 or cols.shape != rows.shape or values.shape != rows.shape
                or not np.issubdtype(rows.dtype, np.integer)
                or not np.issubdtype(cols.dtype, np.integer)
                or np.any(rows < 0) or np.any(rows >= n)
                or np.any(cols < 0) or np.any(cols >= n)
                or np.any(rows == cols) or not np.isfinite(values).all()):
            raise ValueError('invalid sparse data covariance entries')
        if diagonal.ndim == 0:
            if not np.isfinite(diagonal) or diagonal < 0:
                raise ValueError('invalid covariance diagonal')
            data_mismatch = float(diagonal) * operator_fro2
        elif diagonal.shape == (n,) and np.isfinite(diagonal).all() and np.all(diagonal >= 0):
            data_mismatch = 0.0
        else:
            raise ValueError('invalid covariance diagonal')
        entries = {(int(i), int(j)): complex(v) for i, j, v in zip(rows, cols, values)}
        if len(entries) != len(rows) or any(not np.isclose(v, entries.get((j, i), np.nan).conjugate(), atol=1e-10)
                                           for (i, j), v in entries.items()):
            raise ValueError('sparse covariance is not Hermitian or has duplicate entries')
        needed = sorted(set(rows.tolist()) | set(cols.tolist()))
        if needed:
            position = {index: offset for offset, index in enumerate(needed)}
            local = np.diag(np.full(len(needed), float(diagonal)) if diagonal.ndim == 0
                            else diagonal[needed]).astype(complex)
            for (i, j), value in entries.items():
                local[position[i], position[j]] = value
            local_eigenvalues = np.linalg.eigvalsh(local)
            if local_eigenvalues[0] < -1e-9 * max(1.0, local_eigenvalues[-1]):
                raise ValueError('sparse data covariance is not positive semidefinite')
        eye_columns = {}
        for j in range(n) if diagonal.ndim else needed:
            basis = np.zeros(n, complex)
            basis[j] = 1
            eye_columns[j] = delta.apply(basis)
            if diagonal.ndim:
                data_mismatch += float(diagonal[j] * np.vdot(eye_columns[j], eye_columns[j]).real)
        for (i, j), value in entries.items():
            data_mismatch += float((value * np.vdot(eye_columns[j], eye_columns[i])).real)
        if data_mismatch < -1e-9 * max(1.0, operator_fro2):
            raise ValueError('sparse data covariance gives negative power')
    else:
        covariance = np.asarray(data_covariance)
        if covariance.ndim == 0:
            pd = float(covariance)
            if not np.isfinite(pd) or pd < 0:
                raise ValueError("invalid data power")
            data_mismatch = pd * operator_fro2
        elif covariance.shape == (n, n):
            if not np.isfinite(covariance).all() or not np.allclose(covariance, covariance.conj().T, atol=1e-10):
                raise ValueError("invalid data covariance")
            eig = np.linalg.eigvalsh((covariance + covariance.conj().T) / 2)
            if eig[0] < -1e-9 * max(1.0, eig[-1]):
                raise ValueError("data covariance is not positive semidefinite")
            eye = np.eye(n, dtype=complex)
            H = np.column_stack([delta.apply(eye[:, j]) for j in range(n)])
            data_mismatch = float(np.trace(H @ covariance @ H.conj().T).real)
            if data_mismatch < -1e-9 * max(1.0, np.linalg.norm(covariance)):
                raise ValueError("data covariance is not positive semidefinite")
        else:
            raise ValueError("data covariance must be scalar, sparse dict, or NxN")
    return dict(operator_frobenius_squared=operator_fro2,
                pilot_mismatch=pilot_mismatch, data_mismatch=max(0.0, data_mismatch),
                sp_weighted_mismatch=pilot_mismatch + max(0.0, data_mismatch),
                physical_operator_gram=R, combined_gains=delta_h)


def exact_code_moments(generator, pd):
    """Exact mapped QPSK mean/covariance from a binary linear generator.

    ``generator`` has coded-bit rows and independent uniform information-bit
    columns.  QPSK bits are ordered all I then all Q.  Equal nonzero generator
    rows identify the only correlated Rademacher bits.  The result stores a
    diagonal plus sparse off-diagonal covariance without an N-by-N matrix.
    """
    G = np.asarray(generator)
    if (G.ndim != 2 or G.shape[0] < 2 or G.shape[0] % 2
            or not G.shape[1] or not np.isin(G, (0, 1)).all()):
        raise ValueError('invalid coded-bit-row generator')
    if not np.isfinite(pd) or pd <= 0:
        raise ValueError('invalid QPSK data power')
    n = G.shape[0] // 2
    groups = {}
    nonzero = np.any(G, axis=1)
    for bit, row in enumerate(np.asarray(G, np.uint8)):
        if nonzero[bit]:
            groups.setdefault(np.packbits(row).tobytes(), []).append(bit)
    bit_mean = (~nonzero).astype(float)
    scale = np.sqrt(pd / 2)
    mean = scale * (bit_mean[:n] + 1j * bit_mean[n:])
    diagonal = (pd / 2) * (nonzero[:n].astype(float) + nonzero[n:].astype(float))
    entries = {}
    duplicate_groups = []
    for group in groups.values():
        if len(group) < 2:
            continue
        duplicate_groups.append(group)
        for a in group:
            i, phase_i = a % n, (1j if a >= n else 1)
            for b in group:
                j, phase_j = b % n, (1j if b >= n else 1)
                if i != j:
                    key = (i, j)
                    entries[key] = entries.get(key, 0j) + (pd / 2) * phase_i * np.conj(phase_j)
    entries = {key: value for key, value in entries.items() if value != 0}
    ordered = sorted(entries)
    covariance = dict(diagonal=float(pd) if np.all(diagonal == pd) else diagonal,
                      rows=np.asarray([x[0] for x in ordered], int),
                      cols=np.asarray([x[1] for x in ordered], int),
                      values=np.asarray([entries[x] for x in ordered], complex))
    return dict(mean=mean, covariance=covariance, zero_mean=bool(np.all(mean == 0)),
                scalar_covariance=bool(not entries and np.all(diagonal == pd)),
                duplicate_generator_row_groups=duplicate_groups,
                covariance_offdiagonal_count=len(entries))


def real_tangent_projection(contrast, B, dB, gains):
    """Project a complex contrast on real gain/Doppler tangent coordinates."""
    contrast = _complex_vector(contrast, "contrast")
    B = np.asarray(B, complex)
    dB = np.asarray(dB, complex)
    if B.ndim != 2 or B.shape != dB.shape or B.shape[0] != len(contrast) or not np.isfinite(B).all() or not np.isfinite(dB).all():
        raise ValueError("invalid tangent responses")
    h = _complex_vector(gains, "tangent gains", B.shape[1])
    J = np.column_stack((B, 1j * B, dB * h[None, :]))
    Jr = np.vstack((J.real, J.imag))
    vr = np.concatenate((contrast.real, contrast.imag))
    U, s, _ = np.linalg.svd(Jr, full_matrices=False)
    tol = max(Jr.shape) * np.finfo(float).eps * (s[0] if len(s) else 0)
    rank = int(np.count_nonzero(s > tol))
    projected = U[:, :rank] @ (U[:, :rank].T @ vr)
    norm2 = float(vr @ vr)
    return dict(projection_fraction=float(projected @ projected / norm2) if norm2 else 0.0,
                projected_norm_squared=float(projected @ projected), contrast_norm_squared=norm2,
                tangent_rank=rank, tangent_columns=Jr.shape[1], tangent_singular_values=s,
                projected_complex=projected[:len(contrast)] + 1j * projected[len(contrast):])


def isotropic_real_controls(contrast, B, dB, gains, *, count, seed):
    """Independent real directions with the contrast's norm (descriptive control)."""
    v = _complex_vector(contrast, "contrast")
    if not isinstance(count, int) or count < 1:
        raise ValueError("invalid control count")
    rng = np.random.default_rng(seed)
    norm = np.linalg.norm(v)
    out = []
    for _ in range(count):
        u = rng.standard_normal(2 * len(v))
        u *= norm / np.linalg.norm(u)
        z = u[:len(v)] + 1j * u[len(v):]
        out.append(real_tangent_projection(z, B, dB, gains)["projection_fraction"])
    return np.asarray(out)


def transplant_legal_error_contrast(failure_truth_bits, failure_candidate_bits,
                                    success_truth_bits, *, is_legal, bits_to_symbols,
                                    success_channel):
    """Move one legal error pattern to a matched-success physical channel.

    The caller chooses a success whose comparison error has the same Hamming
    weight.  XOR of linear-code codewords preserves legality, which is checked
    explicitly here.  The returned contrast is in the time observation domain.
    """
    from physical import daft

    bits = []
    for name, value in (("failure truth", failure_truth_bits),
                        ("failure candidate", failure_candidate_bits),
                        ("success truth", success_truth_bits)):
        b = np.asarray(value)
        if b.ndim != 1 or not len(b) or not np.isin(b, (0, 1)).all():
            raise ValueError(f"invalid {name} bits")
        bits.append(b.astype(np.uint8))
    if bits[0].shape != bits[1].shape or bits[0].shape != bits[2].shape:
        raise ValueError("codeword length mismatch")
    if not all(bool(is_legal(b)) for b in bits):
        raise ValueError("a source word is not legal")
    transplanted = bits[2] ^ bits[0] ^ bits[1]
    if not bool(is_legal(transplanted)):
        raise ValueError("transplanted word is not legal")
    true_symbols = _complex_vector(bits_to_symbols(bits[2]), "success mapped truth", success_channel.n)
    candidate_symbols = _complex_vector(bits_to_symbols(transplanted), "transplanted mapped candidate", success_channel.n)
    contrast_af = success_channel.apply(true_symbols - candidate_symbols)
    return dict(bits=transplanted, hamming_weight=int(np.count_nonzero(bits[0] ^ bits[1])),
                contrast_time=daft(contrast_af, success_channel.c1, success_channel.c2, True))
