import numpy as np
from ab_statistics_v1 import cluster_intervals


def test_cluster_interval_preserves_paired_scaling():
    x=np.random.default_rng(71).normal(size=32)
    result=cluster_intervals(np.column_stack((x,2*x)),draws=2000)
    assert result['channels']==32
    a,b=result['rows']
    assert a['inference_usable'] and b['inference_usable']
    np.testing.assert_allclose(b['simultaneous_95'],2*np.array(a['simultaneous_95']),atol=1e-12)


def test_zero_variance_cannot_claim_equivalence():
    result=cluster_intervals(np.zeros((16,2)),draws=2000)
    assert all(not row['inference_usable'] and row['simultaneous_95'] is None for row in result['rows'])
