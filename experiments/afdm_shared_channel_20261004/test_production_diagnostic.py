"""Independent arithmetic/interface contracts; no production receiver calls."""
import numpy as np
import pytest
from scipy.special import logsumexp

from experiments.afdm_shared_channel_20261004 import production_diagnostic as diagnostic


@pytest.mark.parametrize('n', [2, 4])
@pytest.mark.parametrize('noise', [.02, 2.])
@pytest.mark.parametrize('block', [1, 2])
def test_original_gaussian_pair_dense_and_enumerated_moments(n, noise, block):
    result, _ = diagnostic.arithmetic_case(n, noise, block)
    assert result['likelihood_max_abs'] < 1e-9
    assert result['moment_max_abs'] < 1e-10


def test_iq_order_power_llr_sign_and_native_interface():
    from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen
    from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk
    from experiments.afdm_structured_inference_20261003.message import bit_extrinsic
    _, messages, _ = load_frozen()
    words, bits = diagnostic.independent_words(2)
    np.testing.assert_array_equal(enumerate_qpsk(2)[0], words)
    np.testing.assert_array_equal(words.real**2+words.imag**2, np.full(words.shape, .5))
    local, local_bits = diagnostic.independent_words(1)
    np.testing.assert_array_equal(messages.alphabet(.5)[0], local[:, 0])
    np.testing.assert_array_equal(messages.alphabet(.5)[1], local_bits)
    # Distinct I/Q signs at both positions catch transposition and sign errors.
    target = np.array([.5-.5j, -.5+.5j])
    ll = -abs(target[:, None]-local[:, 0])**2/.2
    ext, app, _, _ = messages.marginal(ll, np.zeros(4), .5)
    np.testing.assert_allclose(app, [5, -5, -5, 5], atol=1e-13)
    np.testing.assert_array_equal(ext, app)
    joint = -np.sum(abs(words-target)**2, axis=1)/.2
    actual_app, actual_ext = bit_extrinsic(joint, bits, np.zeros(4))
    np.testing.assert_allclose(actual_app, app, atol=1e-13)
    np.testing.assert_allclose(actual_ext, app, atol=1e-13)


@pytest.mark.parametrize('block_size', [1, 2])
def test_fixed_observed_h_against_independent_dense_blocks(block_size):
    rng = np.random.default_rng(11)
    h = (rng.normal(size=(4, 4))+1j*rng.normal(size=(4, 4)))/3
    y = rng.normal(size=4)+1j*rng.normal(size=4)
    pilot = np.array([.1, .2j, -.3, .4j])
    result = diagnostic.fixed_h_pair(y, pilot, h, .07, block_size)
    for start in range(0, 4, block_size):
        ids = np.arange(start, start+block_size)
        outside = np.setdiff1d(np.arange(4), ids)
        words, bits = diagnostic.independent_words(block_size)
        covariance = .07*np.eye(4)+.5*h[:, outside]@h[:, outside].conj().T
        scores = []
        for word in words:
            x = pilot.copy(); x[ids] += word
            scores.append(diagnostic.dense_gaussian(y, covariance, h@x))
        scores = np.array(scores)
        np.testing.assert_allclose(result['log_likelihood'][start//block_size], scores, rtol=1e-12, atol=1e-11)
        expected = [logsumexp(scores[bits[:, j] == 0])-logsumexp(scores[bits[:, j] == 1]) for j in range(2*block_size)]
        np.testing.assert_allclose(result['app'][np.r_[ids, ids+4]], expected, atol=1e-11)


def test_saved_baseline_parity_rejects_changed_bits_and_llrs():
    expected = dict(decoder=dict(decoded=np.array([0, 1]), incoming_llr=np.array([1., -2.]),
        raw_app=np.array([2., -3.]), raw_check_extrinsic=np.array([1., -1.])), arrays={})
    actual = dict(decoder={k:v.copy() for k, v in expected['decoder'].items()}, arrays={})
    assert max(diagnostic.compare_saved(actual, expected).values()) == 0
    actual['decoder']['decoded'][0] = 1
    with pytest.raises(AssertionError, match='discrete parity'):
        diagnostic.compare_saved(actual, expected)
    actual['decoder']['decoded'][0] = 0
    actual['decoder']['incoming_llr'][0] += .01
    with pytest.raises(AssertionError, match='continuous parity'):
        diagnostic.compare_saved(actual, expected)


def test_saved_registration_and_all_24_raw_hashes_present():
    import json
    diagnostic.verify_saved_sources()
    records = [json.loads(line) for line in (diagnostic.OLD/'calls.jsonl').read_text().splitlines()]
    assert len(records) == 24
    assert len({r['observation_id'] for r in records}) == 6
    for record in records:
        assert diagnostic.sha(diagnostic.OLD/record['raw_path']) == record['raw_sha256']


def test_native_one_and_twenty_updates_keep_same_observed_initial_gain():
    from experiments.afdm_inference_causal_20261002.oracle_comparison import load_frozen
    physical, _, native = load_frozen()
    channel = physical.Channel(4, .03, .001, [0, 1], [.2, -.3], [.6+.1j, -.2+.4j])
    pilot = np.full(4, np.sqrt(.5), complex)
    y = channel.apply(pilot+np.array([.5+.5j, -.5+.5j, .5-.5j, -.5-.5j]))
    for gain_mode in ('fixed', 'joint'):
        first = native.scalar_joint(y, pilot, channel, .2, iterations=1, gain_mode=gain_mode, record_states=True)
        full = native.scalar_joint(y, pilot, channel, .2, iterations=20, gain_mode=gain_mode, record_states=True)
        assert len(first['states']) == 1
        assert len(full['states']) == 20
        np.testing.assert_array_equal(first['states'][0]['h'], full['states'][0]['h'])
        np.testing.assert_array_equal(first['states'][0]['mu'], full['states'][0]['mu'])
        if gain_mode == 'fixed':
            np.testing.assert_array_equal(full['gains'], channel.gains)
            np.testing.assert_array_equal(full['gain_variance'], 0)


def test_real_frozen_bootstrap_then_effective_verification():
    # A fresh process is required: frozen build owns the one-time Torch interop
    # setting. This exercises real build/LDPC/checkpoint/BLAS, with zero receivers.
    import os
    import subprocess
    import sys
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='')
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        env[key] = '1'
    result = subprocess.run([sys.executable, '-c', '''
from experiments.afdm_shared_channel_20261004.production_diagnostic import prepare_runtime
rt = prepare_runtime()
from thread_binding import verify_effective
assert verify_effective(rt) == rt.environment['effective_blas_post_bootstrap']
rt.evidence.verify_runtime_binding()
assert rt.code['H'].shape == (1026, 2048)
assert rt.header['checkpoint_sha256'] == '052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91'
print('real-bootstrap-verified-zero-receiver-calls')
'''], cwd=diagnostic.ROOT, env=env, text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'real-bootstrap-verified-zero-receiver-calls' in result.stdout
