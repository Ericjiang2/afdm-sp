"""Local fixed-support nuisance geometry; not a likelihood or correctness score."""
import numpy as np


def realify(z):
    z = np.asarray(z)
    return np.concatenate((z.real, z.imag), axis=0)


def channel_jacobian(channel, x):
    """Real parameters ordered [Re(g), Im(g), nu]; x includes fixed pilot."""
    x = np.asarray(x, complex)
    if x.shape != (channel.n,) or not np.isfinite(x).all():
        raise ValueError('x must be finite with channel.n entries')
    a = channel.regressors(x)
    derivative = channel.regressors(x, derivative=True) * channel.gains[None, :]
    return realify(np.concatenate((a, 1j * a, derivative), axis=1))


class ProfileGeometry:
    """Whitened augmented-SVD elimination with explicit numerical rank.

    variance is a scalar or positive diagonal REAL-coordinate noise variance.
    penalty is the PSD precision on nuisance increments, not on data symbols.
    Storage O(m k + k^2), construction O(m k^2), application O(m k).
    No dense m-by-m projector or explicit normal-equation inverse is formed.
    """
    def __init__(self, jacobian, variance, penalty=None, rtol=None):
        j = np.asarray(jacobian, float)
        if j.ndim != 2 or not np.isfinite(j).all():
            raise ValueError('jacobian must be a finite real matrix')
        m, k = j.shape
        v = np.broadcast_to(np.asarray(variance, float), (m,)).copy()
        if not np.isfinite(v).all() or np.any(v <= 0):
            raise ValueError('real noise variances must be finite and positive')
        p = np.zeros((k, k)) if penalty is None else np.asarray(penalty, float)
        if p.shape != (k, k) or not np.isfinite(p).all():
            raise ValueError('penalty dimensions or entries invalid')
        if not np.allclose(p, p.T, rtol=1e-12, atol=1e-14):
            raise ValueError('penalty must be symmetric')
        vals, vecs = np.linalg.eigh((p + p.T) / 2)
        tol = 100 * np.finfo(float).eps * max(1., np.linalg.norm(p, 2))
        if np.any(vals < -tol):
            raise ValueError('penalty must be PSD')
        # Roundoff-only negative eigenvalues are zeroed; model is PSD by contract.
        self.root = np.sqrt(np.maximum(vals, 0))[:, None] * vecs.T
        self.whitener = 1 / np.sqrt(v)
        self.a = self.whitener[:, None] * j
        augmented = np.vstack((self.a, self.root))
        u, s, vh = np.linalg.svd(augmented, full_matrices=False)
        self.rtol = max(augmented.shape) * np.finfo(float).eps if rtol is None else float(rtol)
        if not np.isfinite(self.rtol) or self.rtol < 0 or self.rtol >= 1:
            raise ValueError('rtol must be finite in [0,1)')
        keep = s > self.rtol * (s[0] if len(s) else 0.)
        self.rank = int(keep.sum())
        self.singular_values = s
        self.u_top = u[:m, keep]
        self.inverse_factor = vh[keep].T / s[keep]

    def _input(self, residual):
        r = np.asarray(residual, float)
        if r.ndim not in (1, 2) or r.shape[0] != len(self.whitener) or not np.isfinite(r).all():
            raise ValueError('residual must have real observation rows')
        w = self.whitener if r.ndim == 1 else self.whitener[:, None]
        return w, w * r

    def nuisance_step(self, residual):
        """Minimum-norm step minimizing ||r+J step||^2_R + step.T penalty step."""
        _, z = self._input(residual)
        return -self.inverse_factor @ (self.u_top.T @ z)

    def apply(self, residual):
        """W times residual (columns accepted)."""
        w, z = self._input(residual)
        return w * (z - self.u_top @ (self.u_top.T @ z))

    def value(self, residual):
        """Nonnegative residual-form objective; columns return separate values."""
        _, z = self._input(residual)
        step = -self.inverse_factor @ (self.u_top.T @ z)
        fit = z + self.a @ step
        prior = self.root @ step
        return np.sum(fit * fit, axis=0) + np.sum(prior * prior, axis=0)
