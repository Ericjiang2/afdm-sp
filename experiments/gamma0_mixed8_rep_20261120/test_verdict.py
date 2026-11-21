"""Synthetic checks for replication decisions, counts, and analysis wiring."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

import numpy as np
import pytest

spec = spec_from_file_location('gamma0_mixed8_rep_verdict', Path(__file__).with_name('verdict.py'))
verdict = module_from_spec(spec)
spec.loader.exec_module(verdict)

FRAMES = range(80400, 82800)


@pytest.mark.parametrize('lo,hi,q1,q2', [
    (.002, .013, 'CD_BETTER', 'EQUIVALENT'),
    (.002, .016, 'CD_BETTER', 'NOT_EQUIVALENT'),
    (-.013, -.002, 'Z_BETTER', 'EQUIVALENT'),
    (-.016, -.002, 'Z_BETTER', 'NOT_EQUIVALENT'),
    (-.015, .015, 'NO_DIFFERENCE_SHOWN', 'EQUIVALENT'),
    (-.001, .016, 'NO_DIFFERENCE_SHOWN', 'NOT_EQUIVALENT'),
    (0., .015, 'NO_DIFFERENCE_SHOWN', 'EQUIVALENT'),
    (-.015, 0., 'NO_DIFFERENCE_SHOWN', 'EQUIVALENT'),
    (0., 0., 'NO_DIFFERENCE_SHOWN', 'EQUIVALENT'),
    (-.015001, .015, 'NO_DIFFERENCE_SHOWN', 'NOT_EQUIVALENT'),
])
def test_q1_q2_boundaries_and_anchor_precedence(lo, hi, q1, q2):
    assert verdict.classify(lo, hi, True) == dict(Q1=q1, Q2=q2)
    assert verdict.classify(lo, hi, False) == dict(Q1='ANCHOR_FAIL', Q2='ANCHOR_FAIL')


@pytest.mark.parametrize('cd,s,passed', [(72, 312, True), (216, 456, True),
                                         (71, 311, False), (217, 457, False),
                                         (120, 359, False)])
def test_unconditional_anchor_boundaries(cd, s, passed):
    index = np.arange(verdict.N_FRAMES)
    report = verdict.leg2.check_anchors((index < cd).astype(int), (index < s).astype(int))
    assert report['passed'] is passed


def test_paired_newcombe_cells_and_zero_discordance():
    zero = np.zeros(verdict.N_FRAMES, dtype=int)
    exact = zero.copy()
    exact[:120] = 1
    result = verdict.paired_difference(exact, exact)
    assert result['cells'] == dict(both=120, z_only=0, cd_only=0, neither=2280)
    assert result['ci_lo'] < result['point'] == 0 < result['ci_hi']
    assert result['method'] == 'Newcombe (1998), method 10'
    result = verdict.paired_difference(exact, zero)
    expected = verdict.leg2.newcombe10(0, 120, 0, 2280)
    assert result == expected


def test_historical_pin_and_descriptive_only(tmp_path):
    history = verdict.historical_panel()
    assert history['frames_inclusive'] == [2200, 2799]
    assert history['cells'] == dict(both=29, z_only=10, cd_only=4, neither=557)
    result = verdict.pooled_description(dict(both=100, z_only=20, cd_only=8, neither=2272), history)
    assert result['cells'] == dict(both=129, z_only=30, cd_only=12, neither=2829)
    assert result['point'] == .006 and result['frames'] == 3000 and result['use'] == 'descriptive only'
    assert not {'Q1', 'Q2', 'verdict', 'ci_lo', 'ci_hi'}.intersection(result)
    malformed = tmp_path/'results.json'
    malformed.write_text('{}')
    with pytest.raises(ValueError, match='Frozen checksum mismatch'):
        verdict.historical_panel(malformed)
    with pytest.raises(ValueError, match='3,000-frame'):
        verdict.pooled_description(dict(both=0, z_only=0, cd_only=0, neither=0), history)


def record(*, fail=False, count_035=2, omitted=0., power=1., phantom=0):
    atoms = [[6, 0.], [6, .35]][:count_035] + [[22, 0.], [22, .75]]
    return dict(info_errors=int(fail), decoded_sha='a'*64, atoms=atoms, gains=[[1., 0.]]*len(atoms),
                singleton_phantom_le_025=phantom, singleton_phantom=phantom, close_phantom=phantom,
                doublet_two_atoms={'0.35': count_035 >= 2, '0.75': True},
                doublets=[dict(delay=6, separation=.35, atoms=count_035, omitted=omitted, power=power),
                          dict(delay=22, separation=.75, atoms=2, omitted=0., power=1.)])


def row(frame, arms=None, *, syndrome=1):
    return dict(frame=frame, scenario='MIXED8', snr_db=7, syndrome=syndrome,
                arms=arms if arms is not None else {arm: record() for arm in verdict.ARMS},
                truth=dict(delays=[6, 6, 22, 22], dopplers=[0., .35, 0., .75]))


def test_invalid_or_incomplete_panel():
    first = row(FRAMES.start)
    with pytest.raises(ValueError, match='contiguous'):
        verdict.ordered_rows([], range(2200, 4600))
    with pytest.raises(ValueError, match='contiguous'):
        verdict.ordered_rows([], range(10))
    with pytest.raises(ValueError, match='got 1'):
        verdict.ordered_rows([first], FRAMES)
    with pytest.raises(ValueError, match='duplicate'):
        verdict.ordered_rows([first, first], FRAMES)
    wrong_snr = dict(first, snr_db=6)
    with pytest.raises(ValueError, match='Unexpected'):
        verdict.ordered_rows([wrong_snr], FRAMES)
    missing_arm = deepcopy(first)
    del missing_arm['arms']['H']
    with pytest.raises(ValueError, match='Unexpected'):
        verdict.ordered_rows([missing_arm], FRAMES)
    invalid_errors = deepcopy(first)
    invalid_errors['arms']['Z']['info_errors'] = -1
    with pytest.raises(ValueError, match='Invalid information errors'):
        verdict.ordered_rows([invalid_errors], FRAMES)


def test_pass_through_and_fixed_support():
    first = row(FRAMES.start, syndrome=0)
    first['arms']['Z']['info_errors'] = 1
    with pytest.raises(ValueError, match='did not pass F0 through'):
        verdict.ordered_rows([first], FRAMES)
    first['arms']['Z-sel']['atoms'] = []
    with pytest.raises(ValueError, match='changed Z support'):
        verdict.ordered_rows([first], FRAMES)


def test_full_synthetic_panel_and_cli(tmp_path, monkeypatch):
    rows = []
    for i, frame in enumerate(FRAMES):
        z_support = dict(count_035=1 if i == 0 else 2, power=1. + i % 2)
        cd_support = dict(z_support, count_035=1 if i == 1 else 2)
        arms = {
            'F0': record(fail=i < 600, **cd_support),
            'CD': record(fail=i < 120, omitted=.2 if i == 1 else 0., **cd_support),
            'Z': record(fail=8 <= i < 140, omitted=.1, phantom=int(i == 1), **z_support),
            'H': record(fail=4 <= i < 129, **cd_support),
            'S': record(fail=i < 480, **cd_support),
            'Z-sel': record(fail=8 <= i < 133, **z_support),
        }
        rows.append(row(frame, arms))
    n_resamples = []
    original = verdict.leg2.bootstrap_means

    def observe_bootstrap(values, frames, **opts):
        n_resamples.append((len(frames), opts))
        return original(values, frames, **opts)

    monkeypatch.setattr(verdict.leg2, 'bootstrap_means', observe_bootstrap)
    source, output = tmp_path/'synthetic.jsonl', tmp_path/'verdict.json'
    source.write_text(''.join(json.dumps(item)+'\n' for item in reversed(rows)))
    cli = [str(source), '--frame-start', str(FRAMES.start), '--out', str(output)]
    verdict.main(cli)
    got = json.loads(output.read_bytes())
    assert n_resamples == [(2400, dict(n_boot=20_000, seed=20261127))]
    assert got['_argv'] == cli
    assert got['_config']['frames_inclusive'] == [80400, 82799]
    assert got['frames'] == 2400 and got['anchors']['passed']
    primary = got['primary']
    assert primary['cells'] == dict(both=112, z_only=20, cd_only=8, neither=2260)
    assert primary['point'] == .005 and primary['Q1'] == 'CD_BETTER' and primary['Q2'] == 'EQUIVALENT'
    sec = got['secondary']
    assert sec['pooled_fer_z_minus_cd']['point'] == .006
    assert sec['pooled_fer_z_minus_cd']['frames'] == 3000
    assert set(sec['fer']) == set(verdict.ARMS)
    for contrast, first, second in (('H_minus_CD', 9, 4), ('Z-sel_minus_Z', 0, 7)):
        value = sec['fer_contrasts'][contrast]
        assert (value['only_first_failed'], value['only_second_failed']) == (first, second)
    occupancy = sec['occupancy_z_minus_cd_035']
    assert occupancy['cells'] == dict(both=2398, z_only=1, cd_only=1, neither=0)
    assert occupancy['point'] == 0 and occupancy['ci_lo'] < 0 < occupancy['ci_hi']
    by_direction = sec['occupancy_discordance_035']
    assert by_direction['CD_only']['count'] == by_direction['Z_only']['count'] == 1
    assert by_direction['CD_only']['pooled_omitted_fraction']['Z_minus_CD'] == .1
    assert by_direction['Z_only']['pooled_omitted_fraction']['Z_minus_CD'] == -.05
    assert sec['geometry']['Z']['singleton_phantom_frame']['count'] == 1
    assert sec['geometry']['Z']['close_phantom_frame']['count'] == 1
    assert sec['geometry']['Z']['singleton_phantom_le_025_frame']['count'] == 1
    assert sec['geometry']['Z']['omitted_energy_fraction']['0.35']['point'] == pytest.approx(1/15)
