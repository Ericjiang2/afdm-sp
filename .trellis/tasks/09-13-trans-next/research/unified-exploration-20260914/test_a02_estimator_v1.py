"""Observed boundary and new independent seed namespace contracts."""
from pathlib import Path
import sys
import numpy as np
import pytest

HERE=Path(__file__).resolve().parent
HELPERS=HERE if (HERE/'physical_transfer_model_v1.py').exists() else HERE.parent
sys.path[:0]=[str(HERE),str(HELPERS)]
from ab_model_v1 import physical_module
from a02_estimator_v1 import estimate, make_geometry


def test_split_namespace_reuses_generator_without_modifying_source():
    source=HELPERS/'physical_transfer_model_v1.py'
    before=source.read_bytes()
    first=physical_module(source,0);second=physical_module(source,1)
    actual=first._rng('uwa',0,5).integers(0,2,512)
    expected=np.random.default_rng([20260914,125851,0,0,0,5]).integers(0,2,512)
    np.testing.assert_array_equal(actual,expected)
    assert not np.array_equal(actual,second._rng('uwa',0,5).integers(0,2,512))
    assert source.read_bytes()==before and first.SEED_PREFIX!=second.SEED_PREFIX


@pytest.mark.parametrize('extra',['H','bits','delays','physical_paths','code'])
def test_truth_fields_rejected_before_estimation(extra):
    obs=dict(y=np.ones(256,complex),pilot=np.ones(256,complex),sigma2=np.array(.1),
        constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
    obs[extra]=np.zeros(1)
    with pytest.raises(ValueError,match='four public'):estimate(obs,'dpss',5)


def test_classical_geometry_matches_existing_integer_atoms():
    import torch
    from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch
    geom=make_geometry('small',5)
    pilot=np.random.default_rng(90).normal(size=256).astype(complex)
    expected=construct_sensing_matrix_torch(256,torch.tensor(pilot),geom.c1,geom.c2,24,2).numpy()
    np.testing.assert_allclose(geom.sensing(pilot),expected,atol=1e-10,rtol=1e-10)


def test_external_score_uses_saved_basis(monkeypatch):
    import a02_estimator_v1 as module
    from afdm_sp_joint_unrolled.bandlimited_estimation import fit_coefficients
    geom=make_geometry('fourier',3);coefficients=np.zeros(75,complex);coefficients[:3]=[.2,.5,.1]
    h=geom.channel(np.arange(25),coefficients)
    pilot=np.sqrt(128)*np.eye(1,256,dtype=complex)[0]
    obs=dict(pilot=pilot,y=h@pilot,sigma2=np.array(.01))
    fit=fit_coefficients(geom.sensing(pilot)[:,:3],obs['y'])
    value=dict(family='fourier',q=3,basis=geom.basis,selection=dict(columns=[0,1,2]),fits=dict(ls=fit))
    def forbidden(*args):raise AssertionError('score regenerated the coordinate basis')
    monkeypatch.setattr(module,'make_geometry',forbidden)
    scored=module.score(value,obs,dict(H=h,data=np.zeros(256,complex),noise=np.zeros(256,complex)))
    assert scored['ls']['channel_nmse']<1e-12


def test_replay_comparison_keeps_discrete_and_single_precision_exact():
    from a02_runner_v1 import check_equal
    check_equal(np.array([1.],dtype=np.float64),np.array([1.+1e-13],dtype=np.float64))
    with pytest.raises(AssertionError):check_equal(np.array([1],dtype=np.int64),np.array([2],dtype=np.int64))
    with pytest.raises(AssertionError):check_equal(np.array([1],dtype=np.complex64),np.array([1.000001],dtype=np.complex64))
    with pytest.raises(AssertionError):check_equal(np.array([1],dtype=np.complex128),np.array([1.08554],dtype=np.complex128))
