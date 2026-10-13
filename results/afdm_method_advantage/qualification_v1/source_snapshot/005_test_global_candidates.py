import numpy as np
import pytest
from candidates import reliable_basis,PhysicalScore,symbols
from global_candidates import nominate,acquire_global
from test_candidates import small_code,make_channel
from profile_geometry import realify


def fixture():
    rng=np.random.default_rng(817)
    return small_code(),np.array([-.2,4,3,2,1,.4,.8,5]),make_channel(4),rng.normal(size=4)+1j*rng.normal(size=4),np.ones(4)*(.2+.1j)


def test_all_basis_influence_matches_directional_derivative():
    h,llr,ch,y,p=fixture();basis=reliable_basis(h,llr);s=.7
    x=p+symbols(basis['anchor'],s)
    for mode in ('residual','projected'):
        _,influence,geo=nominate(basis,llr,ch,y,p,.3,s,.1,mode,2)
        r=realify(ch.apply(x)-y)
        for j in range(len(basis['free'])):
            dx=symbols(basis['anchor']^basis['generator'][:,j],s)-symbols(basis['anchor'],s)
            dr=realify(ch.apply(dx));eps=1e-6
            def f(z):return .5*geo.value(z) if mode=='projected' else np.dot(z,z)/.3
            finite=(f(r+eps*dr)-f(r-eps*dr))/(2*eps)
            np.testing.assert_allclose(influence[j],finite,rtol=1e-7,atol=1e-7)


def test_global_results_legal_deterministic_and_common_scores():
    h,llr,ch,y,p=fixture()
    for mode in ('osd','geometry'):
        r=acquire_global(h,llr,ch,y,p,.3,scale=.7,mode=mode,list_size=6,branching=3,max_depth=3)
        again=acquire_global(h,llr,ch,y,p,.3,scale=.7,mode=mode,list_size=6,branching=3,max_depth=3)
        np.testing.assert_array_equal(r['candidates'],again['candidates'])
        assert not np.any(h@r['candidates'].T%2)
        assert r['counts']['channel_adjoint_calls']==1
        assert r['counts']['physical_scores']==6
        score=PhysicalScore(ch,y,p,.3,.7)
        np.testing.assert_allclose(r['scores'],[score(w)[0] for w in r['candidates']])
        assert len(r['nomination_influence'])==len(r['free'])


def test_global_rejects_unsupported_scope():
    h,llr,ch,y,p=fixture()
    with pytest.raises(ValueError):acquire_global(h,llr,ch,y,p,.3,scale=.7,known_channel=True)
