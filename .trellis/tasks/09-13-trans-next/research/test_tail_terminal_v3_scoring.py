"""Regression for the actual-terminal scoring definition.

The legacy ridge producer scored with ``supplement_profile.score_errors``: the
raw bit error count comes from the hard *symbol* decisions ``x_hard``
(``concatenate((real<0, imag<0))``), not from LLR signs. v2 used
``light_gap_replay.decoder_scores`` and therefore disagreed with every saved
record (real record: producer 85 vs v2 221) although FER agreed.
"""
from pathlib import Path

import numpy as np

import tail_terminal_run_v3 as run_v3

RESEARCH = Path(run_v3.__file__).parent
PRODUCER_KEYS = ('FER', 'coded_bit_errors', 'raw_bit_errors', 'decoded_codeword_bit_errors')


def producer_score_errors(value, truth):
    """Verbatim copy of afdm_sp_joint_unrolled.supplement_profile.score_errors."""
    info, coded = np.asarray(truth['info']), np.asarray(truth['coded'])
    ihat, decoded, hard = (np.asarray(value[k]) for k in ('info_hat', 'decoded', 'x_hard'))
    errors = int(np.count_nonzero(ihat != info))
    raw = np.concatenate((hard.real < 0, hard.imag < 0)).astype(np.uint8)
    return dict(FER=int(errors > 0), coded_bit_errors=errors,
                raw_bit_errors=int(np.count_nonzero(raw != coded)),
                decoded_codeword_bit_errors=int(np.count_nonzero(decoded != coded)))


def decoder_scores(value, truth):
    """Verbatim copy of the superseded light_gap_replay.decoder_scores."""
    llr, bits = np.asarray(value['llr']), np.asarray(truth['coded'])
    info, expected_info = np.asarray(value['info_hat']), np.asarray(truth['info'])
    errors = int(np.count_nonzero(info != expected_info))
    return dict(FER=int(errors > 0), info_bit_errors=errors,
                raw_bit_errors=int(np.count_nonzero((llr < 0) != bits)),
                decoded_codeword_bit_errors=int(np.count_nonzero(value['decoded'] != bits)))


def fixture():
    """One frame where the two definitions provably disagree."""
    rng = np.random.default_rng(20260916)
    coded = rng.integers(0, 2, 2048).astype(np.uint8)
    info = rng.integers(0, 2, 1024).astype(np.uint8)
    hard = (rng.normal(size=1024) + 1j * rng.normal(size=1024))
    # LLR sign pattern deliberately different from the symbol hard decisions
    llr = np.where(hard.real > 0.5, -1.0, 1.0).repeat(2)
    value = dict(info_hat=info.copy(), decoded=coded.copy(), x_hard=hard, llr=llr)
    return value, dict(info=info, coded=coded)


def test_two_definitions_agree_on_fer_and_differ_on_raw_bits():
    value, truth = fixture()
    a, b = producer_score_errors(value, truth), decoder_scores(value, truth)
    assert a['FER'] == b['FER']
    assert a['coded_bit_errors'] == b['info_bit_errors']
    assert a['decoded_codeword_bit_errors'] == b['decoded_codeword_bit_errors']
    assert a['raw_bit_errors'] != b['raw_bit_errors']


def test_producer_definition_matches_x_hard_convention():
    value, truth = fixture()
    expected = int(np.count_nonzero(
        np.concatenate((value['x_hard'].real < 0, value['x_hard'].imag < 0)).astype(np.uint8) != truth['coded']))
    assert producer_score_errors(value, truth)['raw_bit_errors'] == expected


def test_v3_binds_producer_scorer_and_drops_decoder_scores():
    v3 = Path(run_v3.__file__).read_text()
    v2 = RESEARCH.joinpath('tail_terminal_run_v2.py').read_text()
    assert 'self.producer_scores, self.reuse = hashes, verified_record, score_errors, reuse_at_snr' in v3
    assert 'self.decoder_scores' not in v3      # no superseded scorer call survives
    assert 'decoder_scores(' not in v3          # docstring prose is fine, calls are not
    assert 'decoder_scores(' in v2              # superseded definition, preserved


def test_v3_binding_key_set_is_the_producer_schema():
    v3 = Path(run_v3.__file__).read_text()
    assert ("for key in ('FER', 'coded_bit_errors', 'raw_bit_errors', "
            "'decoded_codeword_bit_errors'):") in v3
    assert set(PRODUCER_KEYS) >= {'FER', 'raw_bit_errors'}
