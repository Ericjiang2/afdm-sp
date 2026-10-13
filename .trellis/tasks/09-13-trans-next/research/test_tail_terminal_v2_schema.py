"""Regression for the actual-terminal loader schema.

The legacy ridge producer (outputs_dirichlet_shrinkage_20260914) records the
terminal controls fields but never wrote the upstream stop-runner flag
``terminal_executed``. v1's loader required that flag and therefore raised
KeyError on every saved record. v2 removes the clause; the surviving
prior/control/temperature/variance/scale/sigma2 clauses must still reject.
"""
from pathlib import Path

import pytest

import tail_terminal_run_v2 as run_v2


def real_old(**overrides):
    """Exactly the keys the legacy ridge producer wrote for a ridge record."""
    old = dict(
        dals=[dict(outer_iter=i) for i in range(1, 10)],
        terminal_check_prior_consumed=True,
        terminal_controls_consumed=True,
        terminal_bp_temperature=1.0,
        terminal_variance_source='physical',
        terminal_scale_applied=False,
        sigma2_terminal=0.2,
    )
    old.update(overrides)
    return old


def record(**overrides):
    base = dict(physical_record_sha256='phys', observed_hashes={'y': 'h'},
                strength=.1, truth_access='offline scoring only')
    base.update(overrides)
    return base


def binding(**overrides):
    kwargs = dict(record=record(), physical_sha256='phys', split_matches=True,
                  observed_hashes={'y': 'h'}, old=real_old(), sigma2=0.2)
    kwargs.update(overrides)
    return run_v2.old_binding_ok(**kwargs)


def test_producer_schema_has_no_terminal_executed():
    assert 'terminal_executed' not in real_old()


def test_real_schema_is_accepted():
    assert binding() is True


def test_v1_recorded_the_removed_clause_and_v2_does_not():
    v1 = Path(run_v2.__file__).with_name('tail_terminal_run_v1.py').read_text()
    v2 = Path(run_v2.__file__).read_text()
    assert "or not old['terminal_executed']" in v1
    assert "or not old['terminal_executed']" not in v2


@pytest.mark.parametrize('overrides', [
    dict(old=real_old(terminal_check_prior_consumed=False)),
    dict(old=real_old(terminal_controls_consumed=False)),
    dict(old=real_old(terminal_bp_temperature=2.0)),
    dict(old=real_old(terminal_variance_source='ema')),
    dict(old=real_old(terminal_scale_applied=True)),
    dict(old=real_old(sigma2_terminal=0.25)),
    dict(old=real_old(dals=[dict(outer_iter=i) for i in range(1, 9)])),
    dict(record=record(strength=1.0)),
    dict(record=record(truth_access='none')),
    dict(record=record(observed_hashes={'y': 'other'})),
    dict(physical_sha256='other'),
    dict(split_matches=False),
    dict(observed_hashes={'y': 'other'}),
], ids=['prior-not-consumed', 'controls-not-consumed', 'temperature-2',
        'variance-not-physical', 'scale-applied', 'sigma2-mismatch',
        'dals-not-9', 'strength-not-.1', 'truth-access', 'record-hashes',
        'physical-sha', 'split', 'observed-hashes'])
def test_surviving_clauses_still_reject(overrides):
    assert binding(**overrides) is False


def test_missing_controls_key_is_not_silently_accepted():
    old = real_old()
    del old['terminal_controls_consumed']
    with pytest.raises(KeyError):
        binding(old=old)
