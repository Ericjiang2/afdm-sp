"""Unit tests for ri_analysis.py (synthetic rows; no project data)."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'tf_cstate_e2_20261017'))
import ri_analysis as ri  # noqa: E402
import codelay_guard as cg  # noqa: E402


def row(edit, r1=((10, .3), (20, -1.), (30, .5)), truth=((10, .3, .6), (20, -1., .3), (40, 1.2, .1)), frame=1, rho=.3):
    return dict(frame=frame, rho=rho, snr_centi_db=650, scenario='U', triggered=True,
                r1=dict(delays=[d for d, _ in r1], dopplers=[nu for _, nu in r1]),
                truth=dict(delays=[d for d, _, _ in truth], dopplers=[nu for _, nu, _ in truth],
                           gains=[[np.sqrt(p), 0.] for _, _, p in truth]),
                arms={'A2n': dict(status='ok', edits=[] if edit is None else [edit])})


def ed(slot, old, new, step=0):
    return dict(step=step, slot=slot, old=dict(delay=old[0], doppler=old[1]), new=dict(delay=new[0], doppler=new[1]), decrease=1.)


def test_abs_dn_matches_guard():
    x = np.array([0., .06, .3, .61, 1.7, -2.2])
    assert np.allclose(ri.abs_dn(x), cg.abs_dn(x, 1024), rtol=0, atol=1e-15)


def test_classes_and_quantities():
    # phantom: slot 2 (delay 30, spurious) replaced by an atom on delay 10 (occupied by true path power .6)
    u = ri.unit_record(row(ed(2, (30, .5), (10, 1.0))), 'A2n')
    assert u['cls'] == 'phantom' and np.isclose(u['h1'], .6) and np.isclose(u['hw2'], .1)
    assert np.isclose(u['D'], ri.abs_dn(.7)) and np.isclose(u['h1max2'], .6)
    assert np.isclose(u['hw2_grid'], .1 * ri.abs_dn(.05) ** 2)  # nearest grid point to 1.2 is 1.25
    # phantom on a spurious occupant
    u = ri.unit_record(row(ed(0, (10, .3), (30, 1.2))), 'A2n')
    assert u['cls'] == 'phantom' and u['h1'] is None
    assert ri.unit_record(row(ed(1, (20, -1.), (20, -.5))), 'A2n')['cls'] == 'same_slot'
    assert ri.unit_record(row(ed(2, (30, .5), (40, 1.2))), 'A2n')['cls'] == 'new_delay'
    assert ri.unit_record(row(None), 'A2n')['cls'] is None
    # no missed true delay
    u = ri.unit_record(row(None, truth=((10, .3, .6), (20, -1., .4))), 'A2n')
    assert u['hw2'] == 0 and u['hw2_grid'] == 0


def test_first_edit_must_start_from_r1():
    try:
        ri.unit_record(row(ed(2, (31, .5), (10, 1.))), 'A2n')
    except ValueError:
        return
    raise AssertionError('I1 violation not raised')


def test_weighted_auc_matches_bruteforce():
    rng = np.random.default_rng(0)
    s = rng.integers(0, 6, 200).astype(float)
    y = (rng.random(200) < .4).astype(float)
    w = rng.integers(0, 3, 200).astype(float)
    levels, inv = np.unique(s, return_inverse=True)
    got = ri.weighted_auc(inv, len(levels), y, w)
    num = sum(w[i] * w[j] * ((s[i] > s[j]) + .5 * (s[i] == s[j])) for i in range(200) for j in range(200) if y[i] and not y[j])
    den = (w * y).sum() * (w * (1 - y)).sum()
    assert np.isclose(got, num / den)


def test_logistic_x50_recovers_threshold():
    rng = np.random.default_rng(1)
    x = rng.uniform(-10, 10, 20000)
    y = (rng.random(20000) < 1 / (1 + np.exp(-(x - 3.)))).astype(float)
    assert abs(ri.logistic_x50(x, y, np.ones_like(x)) - 3.) < .2


def test_first_bootstrap_weight_is_point():
    w0 = next(ri.cluster_weights(np.array([3, 3, 5]), np.random.default_rng(0), 5))
    assert np.array_equal(w0, np.ones(3))


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
