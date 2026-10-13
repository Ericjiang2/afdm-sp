"""Numerical contracts for fixed-support estimation and external accounting."""
import numpy as np
import pytest

from afdm_sp_joint_unrolled.bandlimited_basis import BasisGeometry, basis_from_public_band
from afdm_sp_joint_unrolled.bandlimited_estimation import fit_coefficients, operator_coordinates, external_error_accounting


def geometry():
    return BasisGeometry(basis_from_public_band('gce',16,3,4000.,16.),
                         c1=5/32,c2=.0003,delay_cap=2,prefix_length=3)


@pytest.mark.parametrize('strength',[0.,.1])
def test_fit_matches_independent_normal_equations(strength):
    rng=np.random.default_rng(19)
    a=rng.normal(size=(24,5))+1j*rng.normal(size=(24,5))
    y=rng.normal(size=24)+1j*rng.normal(size=24)
    value=fit_coefficients(a,y,strength)
    expected=np.linalg.solve(a.conj().T@a+value['penalty']*np.eye(5),a.conj().T@y)
    np.testing.assert_allclose(value['coefficients'],expected,atol=2e-6,rtol=2e-6)
    assert value['completed_solves']==1 and value['normal_residual']<1e-5


def test_operator_coordinates_round_trip_with_cpp():
    geom=geometry();rng=np.random.default_rng(21)
    coefficients=rng.normal(size=9)+1j*rng.normal(size=9)
    h=geom.channel([0,1,2],coefficients)
    np.testing.assert_allclose(operator_coordinates(geom,h),coefficients,atol=1e-11,rtol=1e-11)


@pytest.mark.parametrize('strength',[0.,.1])
def test_error_decomposition_retains_nonzero_cross_terms(strength):
    geom=geometry();rng=np.random.default_rng(41)
    h=rng.normal(size=(16,16))+1j*rng.normal(size=(16,16))
    pilot=rng.normal(size=16)+1j*rng.normal(size=16)
    data=.5*(rng.choice([-1.,1.],16)+1j*rng.choice([-1.,1.],16))
    noise=rng.normal(size=16)+1j*rng.normal(size=16)
    obs=dict(pilot=pilot,y=h@(pilot+data)+.2*noise,sigma2=np.array(.04))
    columns=[0,1,2,6,7,8]
    fit=fit_coefficients(geom.sensing(pilot)[:,columns],obs['y'],strength)
    score=external_error_accounting(geom,columns,fit,obs,dict(H=h,data=data,noise=noise))
    assert score['closure_error']<1e-10 and abs(score['cross_terms'])>1e-6
    assert score['selection']>0 and score['representation']>0


@pytest.mark.parametrize('a,y,strength',[
    (np.ones((3,2)),np.ones(3),0.),
    (np.eye(3),np.ones(3),-1.),
    (np.eye(3),np.ones(3),True),
    (np.eye(3),np.array([1.,np.nan,1.]),0.),
    (np.ones(3),np.ones(3),0.),
])
def test_invalid_fit_fails(a,y,strength):
    with pytest.raises(ValueError):fit_coefficients(a,y,strength)
