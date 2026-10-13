"""Small synthetic contracts; these are not target G1 performance samples."""
from pathlib import Path
import os
import sys
from unittest.mock import patch

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get('AFDM_TEST_SOURCE_DIR', str(
    HERE.parents[3] / 'afdm_sp_joint_unrolled/outputs_ce_state_20260915/source-v4')))
if not (SOURCE/'source-manifest.json').is_file():
    raise RuntimeError('explicit frozen test source is unavailable')
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(HERE))

import tail_completion_v2 as frozen_tail
import tail_terminal_v1 as terminal
from afdm_sp_joint_unrolled import direction_receiver
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix

if not Path(direction_receiver.__file__).resolve().is_relative_to(SOURCE.resolve()):
    raise RuntimeError('test imported a different receiver source')


def case(n=32):
    rng = np.random.default_rng(202609160701)
    delays = np.repeat(np.arange(1, 9, dtype=np.int64), 3)
    dopplers = np.tile(np.array([-1, 0, 1], dtype=np.int64), 8)
    c1, c2 = 5 / (2 * n), .000197
    gains = (rng.normal(size=24) + 1j * rng.normal(size=24)) / 10
    H = physical_channel_matrix(n, c1, c2, delays, dopplers, gains, prefix_length=16)
    pilot = (rng.normal(size=n) + 1j * rng.normal(size=n)) / 2
    soft = (rng.uniform(-.5, .5, n) + 1j * rng.uniform(-.5, .5, n))
    y = rng.normal(size=n) + 1j * rng.normal(size=n)
    return dict(H=H, y=y, pilot=pilot, x_soft=soft, delays=delays,
                dopplers=dopplers, c1=c1, c2=c2)


def dense_atoms(atoms, c):
    n = len(c['y'])
    return [physical_channel_matrix(n, c['c1'], c['c2'], [l], [k], [1 + 0j],
                                    prefix_length=16) for l, k in atoms]


def project(H, atoms):
    return np.array([np.vdot(U, H) / len(H) for U in atoms])


def test_tail_replaces_existing_T_and_preserves_actual_core_and_remainder():
    c = case()
    S, T = frozen_tail.support_and_tail(c['delays'], c['dopplers'], n=32)
    Us, Ut = dense_atoms(S, c), dense_atoms(T, c)
    z = project(c['H'], Us)
    predicted = frozen_tail.completed_tail(S, T, z, frozen_tail.actual_centres(S, z), n=32)
    outside = dense_atoms(((12, 7),), c)[0] * (.31 + .12j)
    existing_tail = sum(g * U for g, U in zip(predicted, Ut))
    c['H'] += existing_tail + outside
    before = {k: v.copy() for k, v in c.items() if isinstance(v, np.ndarray)}
    value = terminal.make_candidate(**c, arm='TAIL')
    # Existing correct tail must not be added a second time.
    np.testing.assert_allclose(value['H'], c['H'], atol=2e-12, rtol=2e-12)
    np.testing.assert_allclose(project(value['H'], Us), project(c['H'], Us), atol=2e-12)
    np.testing.assert_allclose(project(value['H'], Ut), value['tail_gains'], atol=2e-12)
    np.testing.assert_allclose(value['H'] - sum(g * U for g, U in zip(z, Us)) - existing_tail,
                               outside, atol=2e-12)
    for k, expected in before.items():
        np.testing.assert_array_equal(c[k], expected)
    assert value['counts']['tail_refit_solves'] == 0
    assert value['counts']['F_matrix_solves'] > 0


def test_same_shift_atoms_remain_distinct_in_actual_H_projection():
    c = case(n=31)
    S, T = frozen_tail.support_and_tail(c['delays'], c['dopplers'], n=31)
    a, b = ((1, 5), (2, 0))
    assert a in T and b in S and 5*a[0]+a[1] == 5*b[0]+b[1]
    Ua, Ub = dense_atoms((a, b), c)
    c['H'] = (.8 + .3j)*Ua + (.4 - .6j)*Ub
    value = terminal.make_candidate(**c, arm='TAIL')
    np.testing.assert_allclose(value['core_gains'][S.index(b)], .4-.6j, atol=2e-12)
    np.testing.assert_allclose(value['tail_before'][T.index(a)], .8+.3j, atol=2e-12)
    np.testing.assert_allclose(project(value['H'], [Ub]), [.4-.6j], atol=2e-12)


def test_ridge_matches_augmented_least_squares_on_same_tail():
    c = case()
    S, T = frozen_tail.support_and_tail(c['delays'], c['dopplers'], n=32)
    Us, Ut = dense_atoms(S, c), dense_atoms(T, c)
    c['H'] += (.4+.2j)*Ut[0]
    zt = project(c['H'], Ut)
    A = np.column_stack([U @ (c['pilot'] + c['x_soft']) for U in Ut])
    r = c['y'] - c['H'] @ (c['pilot'] + c['x_soft']) + A @ zt
    lam = .1 * np.vdot(A, A).real / len(T)
    augmented = np.vstack((A, np.sqrt(lam)*np.eye(len(T))))
    target = np.r_[r, np.zeros(len(T))]
    expected = np.linalg.lstsq(augmented, target, rcond=None)[0]
    value = terminal.make_candidate(**c, arm='RIDGE_T')
    np.testing.assert_allclose(value['tail_gains'], expected, atol=3e-12, rtol=3e-12)
    np.testing.assert_allclose(project(value['H'], Us), project(c['H'], Us), atol=3e-12)
    np.testing.assert_allclose(value['z'], c['y'] - value['H'] @ c['pilot'], atol=1e-14)
    direct = np.linalg.norm(r - A @ expected)**2 + lam*np.vdot(expected, expected).real
    np.testing.assert_allclose(value['ridge']['objective'], direct, rtol=2e-12)
    assert value['counts']['tail_refit_solves'] == 1
    assert value['counts']['F_matrix_solves'] == 0


def test_original_preserves_dtype_and_exact_cancellation_without_solves():
    c = case()
    c['H'] = c['H'].astype(np.complex64)
    with patch.object(frozen_tail, 'predictor', side_effect=AssertionError('unexpected predictor')):
        value = terminal.make_candidate(**c, arm='ORIGINAL')
    np.testing.assert_array_equal(value['H'], c['H'])
    np.testing.assert_array_equal(value['z'], c['y'] - c['H'] @ c['pilot'])
    assert value['H'].dtype == np.complex64
    assert all(v == 0 for v in value['counts'].values())


def test_zero_core_tail_and_invalid_inputs():
    c = case()
    c['H'][:] = 0
    value = terminal.make_candidate(**c, arm='TAIL')
    np.testing.assert_array_equal(value['H'], c['H'])
    changes = [dict(arm='tuned'), dict(delays=c['delays'].astype(float)),
               dict(dopplers=np.full(24, 3)), dict(c1=.13), dict(c2=float('nan')),
               dict(y=np.full(32, np.nan)), dict(H=np.zeros((31, 31), complex))]
    for changed in changes:
        with pytest.raises(ValueError):
            terminal.make_candidate(**{**c, 'arm': 'TAIL', **changed})
    with pytest.raises(ValueError):
        terminal.make_candidate(**dict(c, pilot=np.zeros(32), x_soft=np.zeros(32)), arm='RIDGE_T')


def test_real_terminal_consumes_transformed_H_and_original_identity(tmp_path):
    c = case()
    code = build_code(n=64, d_v=2, d_c=4, seed=91, cache_dir=tmp_path)
    constellation = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
    prior = np.linspace(-2., 2., 64)
    original = terminal.make_candidate(**c, arm='ORIGINAL')
    expected = direction_receiver.terminal_decode(original['z'], c['H'], .2, constellation,
        code, code_prior=prior, bp_temperature=1., bp_iterations=20, audit=True)
    actual = terminal.decode_candidate(original, .2, constellation, prior, code)
    for key in ('mu', 'var', 'raw_llr', 'llr', 'decoded', 'info_hat', 'x_hard', 'decode_ok'):
        np.testing.assert_array_equal(actual[key], expected[key])
    candidate = terminal.make_candidate(**c, arm='TAIL')
    with patch.object(direction_receiver, 'terminal_decode', wraps=direction_receiver.terminal_decode) as call:
        value = terminal.decode_candidate(candidate, .2, constellation, prior, code)
    assert call.call_count == 1
    np.testing.assert_array_equal(call.call_args.args[0], c['y'] - candidate['H'] @ c['pilot'])
    np.testing.assert_array_equal(call.call_args.args[1], candidate['H'])
    np.testing.assert_array_equal(value['finite_message']['prior_llr'], prior)
    assert value['graphs'][0]['H_hash'] == array_hash(candidate['H'].astype(np.complex128))
    assert value['actual_edges'] == np.count_nonzero(abs(candidate['H']) >= 1e-4)
    assert value['resource_counts'] == dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0)
