import itertools
import sys
from pathlib import Path
import numpy as np
import pytest
from candidates import acquire, reliable_basis, symbols, PhysicalScore
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'geometry'))
from test_profile_geometry import make_channel


def small_code():
    return np.array([[1,1,1,0,0,0,0,0], [0,0,1,1,1,0,0,0], [0,0,0,0,1,1,1,1]], np.uint8)


def test_reliable_basis_illegal_hard_and_full_small_code():
    h = small_code()
    llr = np.array([-.2, 4, 3, 2, 1, .4, .8, 5])
    assert np.any((h @ (llr<0))%2)
    b = reliable_basis(h,llr)
    assert not np.any((h @ b['anchor'])%2)
    found = set()
    for u in itertools.product((0,1), repeat=b['generator'].shape[1]):
        w = (b['generator']@np.array(u,dtype=np.uint8))%2
        assert not np.any((h@w)%2)
        found.add(tuple(w))
    exact = {bits for bits in itertools.product((0,1), repeat=8) if not np.any(h@np.array(bits)%2)}
    assert found == exact
    assert not np.array_equal(b['permutation'], reliable_basis(h,llr[::-1])['permutation'])


def test_i_then_q_and_known_channel_limit():
    bits=np.array([0,1,0,1,1,0,1,0])
    np.testing.assert_allclose(symbols(bits, .7), .7/np.sqrt(2)*np.array([1-1j,-1+1j,1-1j,-1+1j]))
    ch=make_channel(4);pilot=np.arange(4)*(.1+.2j);y=np.ones(4,dtype=complex)
    score,_=PhysicalScore(ch,y,pilot,.3,.7,known_channel=True)(bits)
    np.testing.assert_allclose(score,np.linalg.norm(ch.apply(pilot+symbols(bits,.7))-y)**2/.3)


def test_common_profile_matches_direct_dense_gain_lstsq():
    ch=make_channel(4);bits=np.zeros(8,dtype=np.uint8);pilot=np.arange(4)*(.1+.2j);y=np.ones(4,dtype=complex)
    scorer=PhysicalScore(ch,y,pilot,.3,.7,gain_precision=.2)
    score,g=scorer(bits)
    a=ch.regressors(pilot+symbols(bits,.7));aug=np.vstack([a/np.sqrt(.3),np.sqrt(.2)*np.eye(2)])
    target=np.r_[y/np.sqrt(.3),np.sqrt(.2)*ch.gains]
    direct=np.linalg.lstsq(aug,target,rcond=None)[0]
    np.testing.assert_allclose(g,direct)
    np.testing.assert_allclose(score,np.linalg.norm(aug@direct-target)**2)


def test_geometry_changes_acquisition_and_is_deterministic():
    rng=np.random.default_rng(891);h=small_code();ch=make_channel(4)
    llr=np.array([-.2,4,3,2,1,.4,.8,5]);pilot=rng.normal(size=4)*.3+1j*rng.normal(size=4)*.3
    y=rng.normal(size=4)+1j*rng.normal(size=4)
    options=dict(scale=.7,list_size=6,branching=5,max_depth=3)
    osd=acquire(h,llr,ch,y,pilot,.3,mode='osd',**options)
    geo=acquire(h,llr,ch,y,pilot,.3,mode='geometry',**options)
    repeat=acquire(h,llr,ch,y,pilot,.3,mode='geometry',**options)
    np.testing.assert_array_equal(geo['candidates'],repeat['candidates'])
    np.testing.assert_array_equal(geo['scores'],repeat['scores'])
    assert {tuple(w) for w in osd['candidates']} != {tuple(w) for w in geo['candidates']}
    for out in (osd,geo):
        assert not np.any(h@out['candidates'].T%2)
        assert out['counts']['physical_scores']==6
        assert out['timing']['total_seconds']>=out['timing']['physical_score_seconds']
    assert geo['counts']['geometry_prescreens'] < 32  # not exhaustive tiny codebook
    assert geo['counts']['geometry_prescreens'] > 6


def test_invalid_observations_and_code_rejected():
    ch=make_channel(4);h=small_code();llr=np.ones(8)
    with pytest.raises(ValueError):
        acquire(h,llr,ch,np.ones(4),np.ones(4),0.,scale=.7)
    with pytest.raises(ValueError):
        reliable_basis(h+.1,llr)
    with pytest.raises(ValueError):
        acquire(h,llr,ch,np.ones(4),np.ones(4),1.,scale=.7,list_size=0)
