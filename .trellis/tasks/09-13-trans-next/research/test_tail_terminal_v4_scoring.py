"""Regression for the v4 scorer split.

v3 aligned the loader binding and recorded rows with the producer definition
(``score_errors`` over ``x_hard``) but also applied it to the audit decode
replay, whose output has no ``x_hard`` and therefore crashed the audit. v4
keeps the producer definition where it is authoritative and restores the
LLR-based definition for that audit-internal replay score only.
"""
from pathlib import Path

import tail_terminal_run_v4 as run_v4

RESEARCH = Path(run_v4.__file__).parent


def source_of(name):
    return RESEARCH.joinpath(name).read_text()


def test_loader_and_rows_use_the_producer_scorer():
    v4 = source_of('tail_terminal_run_v4.py')
    assert 'self.producer_scores, self.reuse = hashes, verified_record, score_errors, reuse_at_snr' in v4
    assert 'scores = dict(self.producer_scores(old, raw), **channel_scores(old[\'H\'], raw))' in v4
    assert 'self.decoder_scores' not in v4


def test_binding_uses_the_producer_key_set():
    v4 = source_of('tail_terminal_run_v4.py')
    assert ("for key in ('FER', 'coded_bit_errors', 'raw_bit_errors', "
            "'decoded_codeword_bit_errors'):") in v4
    assert "('info_bit_errors', 'coded_bit_errors')" not in v4


def test_audit_replay_keeps_the_llr_definition():
    v4 = source_of('tail_terminal_run_v4.py')
    assert 'lambda v: decoder_scores(v, point[\'raw\'])' in v4
    assert 'returns no x_hard' in v4  # reason recorded next to the call


def test_v3_exit_and_v4_exit_differ_exactly_here():
    v3, v4 = source_of('tail_terminal_run_v3.py'), source_of('tail_terminal_run_v4.py')
    # v3 scored the audit replay with the producer scorer; that is the only defect fixed
    assert 'lambda v: score_errors(v, point[\'raw\'])' in v3
    assert 'lambda v: score_errors(v, point[\'raw\'])' not in v4
