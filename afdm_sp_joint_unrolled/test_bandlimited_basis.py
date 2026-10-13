"""Physical operator and selection contracts, not receiver performance tests."""
import numpy as np
import pytest

from afdm_sp_joint_unrolled.bandlimited_basis import (
    BasisGeometry, basis_from_public_band, group_omp, normalized_geometry,
)
from afdm_sp_joint_unrolled.supplement_pilots import propagate_cpp, transform


@pytest.mark.parametrize("family", ["fourier", "gce", "dpss"])
@pytest.mark.parametrize("q", [3, 5, 7])
def test_public_bases_are_orthonormal(family, q):
    basis = basis_from_public_band(family, 256, q, 4000., 16.)
    np.testing.assert_allclose(basis.conj().T @ basis, np.eye(q), atol=2e-12)


def test_dpss_flat_band_projection_and_angle_result():
    n = np.arange(256)
    basis = basis_from_public_band("dpss", 256, 5, 4000., 16.)
    angles = 2*np.pi*np.arange(2048)/2048
    vectors = np.exp(2j*np.pi*n[:, None]*.004*np.cos(angles)[None, :])
    residual = vectors-basis@(basis.conj().T@vectors)
    assert np.mean(np.sum(abs(residual)**2, axis=0))/256 == pytest.approx(3.7403e-5, rel=2e-5)


@pytest.mark.parametrize("family", ["fourier", "gce", "dpss"])
def test_basis_matrix_matches_independent_cpp_column_propagation(family):
    n, q, c1, c2 = 32, 3, 1.3/64, .00031
    basis = basis_from_public_band(family, n, q, 4000., 100.)
    geometry = BasisGeometry(basis, c1=c1, c2=c2, delay_cap=5, prefix_length=8)
    delays = np.array([0, 3, 5])
    rng = np.random.default_rng(41)
    coefficients = rng.normal(size=9)+1j*rng.normal(size=9)
    symbols = rng.normal(size=n)+1j*rng.normal(size=n)
    matrix = geometry.channel(delays, coefficients)
    sensing = geometry.sensing(symbols, delays)
    np.testing.assert_allclose(matrix@symbols, sensing@coefficients, atol=4e-12)
    # Independent columns: construct each time-domain impulse, use production
    # CPP delay, multiply the arbitrary time envelope, then production DAFT.
    direct = np.empty((n, n), complex)
    envelopes = np.sqrt(n)*basis@coefficients.reshape(len(delays), q).T
    for col in range(n):
        impulse = np.eye(n, dtype=complex)[:, col]
        time_signal = transform(impulse, c1, c2, inverse=True)
        received = np.zeros(n, complex)
        for j, delay in enumerate(delays):
            shifted = propagate_cpp(time_signal, c1, [delay], [0.], [1.], prefix_length=8)
            received += envelopes[:, j]*shifted
        direct[:, col] = transform(received, c1, c2)
    np.testing.assert_allclose(matrix, direct, atol=4e-12)


def test_fourier_pz_delay_collisions_are_reported():
    n = 256
    basis = basis_from_public_band("fourier", n, 7, 4000., 16.)
    geometry = BasisGeometry(basis, c1=5/(2*n), c2=(np.sqrt(2)-1)/(2*n*n),
                             delay_cap=24, prefix_length=32)
    pz = np.zeros(n, complex); pz[0] = np.sqrt(n*.5)
    report = normalized_geometry(geometry.sensing(pz))
    assert report["rank"] < report["columns"]
    assert report["qualified"] is False


def test_group_selection_depends_on_subspace_not_column_orientation():
    rng = np.random.default_rng(20)
    design = rng.normal(size=(32, 12))+1j*rng.normal(size=(32, 12))
    y = design[:, :3]@np.array([1., 2., -1.])+design[:, 6:9]@np.array([2., -1., 3.])
    original = group_omp(design, y, group_size=3, max_groups=2)
    rotated = design.copy()
    for group in range(4):
        u, _ = np.linalg.qr(rng.normal(size=(3, 3))+1j*rng.normal(size=(3, 3)))
        rotated[:, group*3:(group+1)*3] = design[:, group*3:(group+1)*3]@u
    changed = group_omp(rotated, y, group_size=3, max_groups=2)
    assert changed["delays"] == original["delays"]
    np.testing.assert_allclose(rotated[:, changed["columns"]]@changed["coefficients"],
                               design[:, original["columns"]]@original["coefficients"], atol=1e-11)


def test_rank_exhaustion_and_invalid_inputs_fail():
    design = np.eye(4, dtype=complex)[:, [0, 0, 1]]
    with pytest.raises(ValueError, match="rank|budget"):
        group_omp(design, np.ones(4), group_size=1, max_groups=3)
    with pytest.raises(ValueError):
        basis_from_public_band("dpss", 32, 3, 4000., float("nan"))
    with pytest.raises(ValueError):
        BasisGeometry(np.eye(8, 3), c1=0., c2=0., delay_cap=5, prefix_length=4)

@pytest.mark.parametrize('family',['fourier','gce','dpss'])
@pytest.mark.parametrize('q',[3,5,7])
def test_public_basis_has_fixed_first_coordinate_phase(family,q):
    # Equal-magnitude Fourier rows must not choose an argmax phase anchor:
    # roundoff can change the winning row and rotate every coefficient.
    basis=basis_from_public_band(family,256,q,4000.,16.)
    assert np.max(abs(basis[0].imag))<1e-12
    assert np.all(basis[0].real>0)
