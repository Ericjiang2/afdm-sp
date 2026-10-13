"""Actual-prior branch and complete-derivative regression contracts."""
import numpy as np
import pytest
from experiments.afdm_higher_order_information import prior


def test_frozen_dense_gram_including_collision_plateau_and_clipping():
    system = prior.small_system()
    for mu, delta in [(0,0), (0,.01), (.27,.05), (2,.2)]:
        g = prior.geometry(system, mu, delta)
        np.testing.assert_allclose(g['gram'], prior.dense_gram(system,g['weights']), atol=1e-13)
        np.testing.assert_allclose(g['g0'].conj().T@g['g0']/16, g['gram'], atol=1e-13)


def test_open_pruning_plateau_g0_bounded_g1_second_moment_diverges():
    system = prior.small_system()
    for delta in [0,.001,.01,.05]:
        g = prior.geometry(system, 0, delta)
        assert np.count_nonzero(np.any(g['weights'] != 0, axis=1)) == 1
        assert prior.singular_moment_status(g['gram'],g['g0'])['output_bounded']
        s = prior.singular_moment_status(g['gram'],g['g1'])
        assert s['second'] == ('finite' if delta == 0 else 'infinite')
    z,w = prior.sphere_rule(16)
    g = prior.geometry(system,0,.01)
    actual,_ = prior.pushforward_nodes(z,w,[1,.3],g['gram'])
    np.testing.assert_allclose(abs(actual@g['g0'].T)**2,1,atol=1e-11)


def test_complete_pushforward_derivative_includes_pdp_gram_and_map():
    z,w = prior.sphere_rule(12)
    pdp = np.array([1.,.3]); dp=np.array([.2,-.1])
    W=np.array([[1.,.1j],[.2,.7]],complex); dW=np.array([[.1,.2],[.3j,-.2]])
    B=np.array([[1.,1j],[.2,.3]],complex); dB=np.array([[.2,-.1],[.1j,.3]])
    R=W.conj().T@W; dR=dW.conj().T@W+W.conj().T@dW
    y,dy=prior.pushforward_jvp(z,pdp,R,B,dp,dR,dB)
    e=1e-5
    def f(t):
        WT=W+t*dW
        h,_=prior.pushforward_nodes(z,w,pdp+t*dp,WT.conj().T@WT)
        return h@(B+t*dB).T
    np.testing.assert_allclose((f(e)-f(-e))/(2*e),dy,rtol=1e-8,atol=1e-8)
    assert np.linalg.norm(dy-(prior.normalize_gain(z*np.sqrt(pdp),R)@dB.T)) > .1


def test_gaussian_radial_elimination_matches_control_identity():
    system=prior.small_system(); z,w=prior.sphere_rule(24)
    g=prior.geometry(system,0,.13)
    result=prior.mapped_moments(z,w,np.ones(2),g['gram'],g['g1'],'gaussian')
    t=2*np.pi*np.arange(16)/16
    expected=(1-1/16)*(np.cos(.13*t[3])**2-np.cos(.13*t[7])**2)
    np.testing.assert_allclose(result['T'],expected,atol=2e-14)
    np.testing.assert_allclose(result['second'],1.2,atol=2e-14)


def test_invalid_singular_jvp_and_zero_map_rejected():
    z,_=prior.sphere_rule(4)
    with pytest.raises(ValueError):
        prior.pushforward_jvp(z,np.ones(2),np.ones((2,2)),np.eye(2),np.zeros(2),np.zeros((2,2)),np.zeros((2,2)))
    assert prior.singular_moment_status(np.zeros((2,2)),np.eye(2))['second']=='undefined'


def test_bridge_feature_computation_has_no_truth_or_pilot_channel_dependency():
    from experiments.afdm_higher_order_information.bridge import observed_features, ROOT
    from experiments.afdm_inference_causal_20261002.oracle_comparison import _load
    physical=_load('bridge_test_physical',ROOT/'experiments/sp_afdm_frozen_20260920/src/physical.py')
    data=dict(y=np.exp(.17j*np.arange(1024)),pilot=np.ones(1024),sigma2=.2)
    first=observed_features(data,.003,.00001,physical)
    second=observed_features(dict(data,pilot=np.zeros(1024),truth=object()),.003,.00001,physical)
    np.testing.assert_array_equal(first['contrasts'],second['contrasts'])
    assert first['pilot_energy']==1024 and second['pilot_energy']==0
    with pytest.raises(ValueError):
        observed_features(dict(data,y=np.ones(16)),.003,.00001,physical)


def test_physical_doppler_clip_precedes_virtual_weight_clipping():
    system=prior.small_system()
    result=prior.geometry(system,2,.2)
    np.testing.assert_array_equal(result['dopplers'],[1.8,2.])
    expected,weights=prior.normalization_gram(system,np.zeros(2,dtype=int),[1.8,2.])
    np.testing.assert_array_equal(result['gram'],expected)
    np.testing.assert_array_equal(result['weights'],weights)
