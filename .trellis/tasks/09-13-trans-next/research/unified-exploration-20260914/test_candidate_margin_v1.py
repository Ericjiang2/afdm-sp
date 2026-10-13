import numpy as np
import pytest
from candidate_margin_v1 import QPSK,candidates,stability,external_coverage


def test_fast_metric_equals_direct_full_vector_distances():
    rng=np.random.default_rng(16);h=rng.normal(size=(5,5))+1j*rng.normal(size=(5,5))
    z=rng.normal(size=5)+1j*rng.normal(size=5);anchor=QPSK[[0,1,2,3,0]]
    c=candidates(dict(H=h,z=z,anchor=anchor,sigma2=.1,constellation=QPSK))
    base=np.linalg.norm(z-h@anchor)**2
    for i in range(5):
        for k in range(4):
            x=anchor.copy();x[i]=QPSK[k]
            assert c['metrics_relative_to_anchor'][i,k]==pytest.approx(np.linalg.norm(z-h@x)**2-base,abs=1e-12)


def test_full_vector_coverage_is_not_local_alphabet_coverage():
    anchor=QPSK[[0,1,2]];c=candidates(dict(H=np.eye(3),z=anchor,anchor=anchor,sigma2=.1,constellation=QPSK))
    assert external_coverage(c,anchor)['coverage_fraction']==1
    truth=anchor.copy();truth[0]=QPSK[3]
    np.testing.assert_array_equal(external_coverage(c,truth)['full_vector_in_local_set'],[True,False,False])
    truth[1]=QPSK[0]
    assert external_coverage(c,truth)['coverage_fraction']==0
    assert stability(c,c)['certified_fraction']==1


def test_zero_column_ties_and_forbidden_truth():
    public=dict(H=np.zeros((2,2)),z=np.ones(2),anchor=QPSK[:2],sigma2=.1,constellation=QPSK)
    c=candidates(public);assert c['tie_count']==2 and stability(c,c)['certified_fraction']==0
    with pytest.raises(ValueError):candidates(dict(public,bits=np.zeros(4)))
