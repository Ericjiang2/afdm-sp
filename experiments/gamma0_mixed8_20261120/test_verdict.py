"""Synthetic tests for the MIXED8 analysis, without a receiver or channel draw."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('gamma0_mixed8_verdict', Path(__file__).with_name('verdict.py'))
verdict = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verdict)

FAKE_FRAMES = range(80400, 81000)


@pytest.mark.parametrize('rule,lo,hi,want', [
    (verdict.P_F, -.015, .015, 'EQUIVALENT'),
    (verdict.P_F, -.03, -.015001, 'Z_BETTER'),
    (verdict.P_F, .015001, .03, 'Z_WORSE'),
    (verdict.P_F, -.03, -.015, 'INCONCLUSIVE'),
    (verdict.P_F, .015, .03, 'INCONCLUSIVE'),
    (verdict.P_F, -.016, .017, 'INCONCLUSIVE'),
    (verdict.P_D, -.03, .03, 'EQUIVALENT'),
    (verdict.P_D, -.04, -.030001, 'Z_LOWER'),
    (verdict.P_D, .030001, .04, 'Z_HIGHER'),
    (verdict.P_D, -.04, -.03, 'INCONCLUSIVE'),
    (verdict.P_D, .03, .04, 'INCONCLUSIVE'),
    (verdict.P_D, -.031, .031, 'INCONCLUSIVE'),
])
def test_frozen_labels(rule, lo, hi, want):
    assert verdict.classify(lo, hi, rule, True) == want
    assert verdict.classify(lo, hi, rule, False) == 'ANCHOR_FAIL'


@pytest.mark.parametrize('n_cd,n_s,passed', [
    (18, 78, True),
    (54, 114, True),
    (17, 77, False),
    (55, 115, False),
    (18, 77, False),
    (18, 0, False),
])
def test_anchor_boundaries(n_cd, n_s, passed):
    flags = np.arange(600)
    assert verdict.check_anchors((flags < n_cd).astype(int), (flags < n_s).astype(int))['passed'] is passed


@pytest.mark.parametrize('cells,lo,hi', [
    ((20, 12, 2, 16), .0562, .3292),
    ((36, 12, 2, 0), .0569, .3404),
    ((53, 0, 0, 1), -.0729, .0729),
    ((27, 0, 0, 27), -.0351, .0351),
    ((54, 0, 0, 0), -.0664, .0664),
])
def test_newcombe_table_iii(cells, lo, hi):
    result = verdict.newcombe10(*cells)
    assert result['ci_lo'] == pytest.approx(lo, abs=.00005)
    assert result['ci_hi'] == pytest.approx(hi, abs=.00005)
    both, first_only, second_only, neither = cells
    swapped = verdict.newcombe10(both, second_only, first_only, neither)
    assert result['ci_lo'] == pytest.approx(-swapped['ci_hi'])
    assert result['ci_hi'] == pytest.approx(-swapped['ci_lo'])


@pytest.mark.parametrize('count', [0, 30, 300, 600])
def test_primary_intervals_stay_nonzero_when_all_pairs_agree(count):
    flags = (np.arange(600) < count).astype(int)
    got = verdict.paired_primary(flags, flags, verdict.P_F, True)
    assert got['point'] == 0.
    assert got['ci_lo'] < 0. < got['ci_hi']


def record(*, fail=False, count_035=2, count_075=2, omitted=0., power=1., phantom=0, legacy=0):
    atoms = [[6, 0.], [6, .35]][:count_035] + [[22, 0.], [22, .75]][:count_075]
    return dict(info_errors=int(fail), decoded_sha='a'*64, atoms=atoms, gains=[[1., 0.]]*len(atoms),
                first_edit_type=None, edits=[], singleton_phantom_le_025=phantom,
                singleton_phantom=legacy, close_phantom=phantom,
                doublet_two_atoms={'0.35': count_035 >= 2, '0.75': count_075 >= 2},
                doublets=[dict(delay=6, separation=.35, atoms=count_035, omitted=omitted, power=power),
                          dict(delay=22, separation=.75, atoms=count_075, omitted=0., power=1.)])


def row(frame, arms=None, *, syndrome=1):
    return dict(frame=frame, scenario='MIXED8', snr_db=7, syndrome=syndrome,
                arms=arms if arms is not None else {arm: record() for arm in verdict.ARMS},
                truth=dict(delays=[6, 6, 22, 22], dopplers=[0., .35, 0., .75]))


def test_first_edit_classification_and_agreement():
    rows = [row(first) for first in range(4)]
    for index, arm, delay, kind in ((0, 'CD', 6, 'existing_delay'), (0, 'Z', 6, 'existing_delay'),
                                    (1, 'CD', 7, 'new_delay'), (1, 'Z', 8, 'new_delay'),
                                    (3, 'Z', 6, 'existing_delay')):
        r = rows[index]['arms'][arm]
        r['edits'] = [dict(slot=0, new=dict(delay=delay, doppler=.25))]
        r['first_edit_type'] = kind
    got = verdict.first_edits(rows)
    assert got['z_vs_cd'] == dict(frames=4, same_accepted_slot_and_atom=1, both_no_edit=1,
                                  different=2, same_accepted_rate=.25, agreement_including_no_edit=.50)
    assert got['categories']['CD']['existing_delay'] == {'count': 1, 'rate': .25}
    assert got['categories']['CD']['new_delay'] == {'count': 1, 'rate': .25}
    assert got['categories']['Z-sel'] == got['categories']['Z']
    rows[0]['syndrome'] = 0
    with pytest.raises(ValueError, match='Unexpected accepted edit'):
        verdict.first_edits(rows)


def test_missing_duplicate_and_off_grid_rows():
    rows = [row(frame) for frame in FAKE_FRAMES]
    with pytest.raises(ValueError, match='contiguous block'):
        verdict.ordered_rows(rows, range(20))
    with pytest.raises(ValueError, match='got 599'):
        verdict.ordered_rows(rows[:-1], FAKE_FRAMES)
    with pytest.raises(ValueError, match='duplicate'):
        verdict.ordered_rows([*rows, rows[0]], FAKE_FRAMES)
    rows[0]['snr_db'] = 6
    with pytest.raises(ValueError, match='Unexpected'):
        verdict.ordered_rows(rows, FAKE_FRAMES)


def test_row_pairing_and_metrics_fail_closed():
    r = row(FAKE_FRAMES.start, syndrome=0)
    r['arms']['A2g']['info_errors'] = 1
    with pytest.raises(ValueError, match='did not pass F0 through'):
        verdict.ordered_rows([r], FAKE_FRAMES)
    r['arms']['Z-sel']['atoms'] = []
    with pytest.raises(ValueError, match='changed Z support'):
        verdict.ordered_rows([r], FAKE_FRAMES)
    arm = record()
    invalid = deepcopy(arm)
    invalid['doublets'][0]['power'] = 0
    with pytest.raises(ValueError, match='omitted energy'):
        verdict.support(invalid)
    invalid = deepcopy(arm)
    invalid['doublet_two_atoms']['0.35'] = False
    with pytest.raises(ValueError, match='two-atom flag'):
        verdict.support(invalid)
    invalid = deepcopy(arm)
    invalid['singleton_phantom_le_025'] = 1
    with pytest.raises(ValueError, match='phantom counts'):
        verdict.support(invalid)


def test_full_synthetic_panel_and_cli(tmp_path):
    rows = []
    for i, frame in enumerate(FAKE_FRAMES):
        n035 = 2 if i < 300 else 1
        n075 = 2 if i < 480 else 1
        power = 1. + i % 2
        common = dict(count_035=n035, count_075=n075, power=power)
        z_common = dict(common, count_035={0: 1, 300: 2}.get(i, n035))
        arms = {
            'F0': record(fail=i < 120, **common),
            'CD': record(fail=i < 30, omitted=.2 if i == 300 else 0., **common),
            'Z': record(fail=0 < i <= 30, omitted=.1, phantom=int(i == 0), legacy=int(i < 2), **z_common),
            'H': record(fail=i < 28 or 30 <= i < 35, **common),
            'S': record(fail=i < 120, **common),
            'A2g': record(fail=i < 70, **common),
            'Z-sel': record(fail=0 < i < 25, **z_common),
            'TRUE_GEOMETRY': record(**common),
        }
        rows.append(row(frame, arms))
    source, output = tmp_path/'synthetic.jsonl', tmp_path/'verdict.json'
    source.write_text(''.join(json.dumps(r)+'\n' for r in reversed(rows)))
    args = [str(source), '--frame-start', str(FAKE_FRAMES.start), '--out', str(output)]
    verdict.main(args)
    got = json.loads(output.read_text())
    assert got['_argv'] == args
    assert got['_config']['frames_inclusive'] == [80400, 80999]
    assert got['frames'] == 600 and got['anchors']['passed']
    assert got['bootstrap'] == dict(draws=20_000, seed=20261127, unit='physical frame', use='secondary readouts only')
    assert {k: p['verdict'] for k, p in got['primary'].items()} == {
        'P-F': 'EQUIVALENT', 'P-D': 'EQUIVALENT'}
    assert got['joint_equivalent']
    assert got['primary']['P-F']['method'] == 'Newcombe (1998), method 10'
    assert got['primary']['P-D']['cells'] == dict(both=299, z_only=1, cd_only=1, neither=299)
    secondary = got['secondary']
    for arm, only_arm, only_cd in (('Z', 1, 1), ('H', 5, 2)):
        contrast = secondary['fer_contrasts'][f'{arm}_minus_CD']
        assert (contrast[f'only_{arm}_failed'], contrast['only_CD_failed']) == (only_arm, only_cd)
    assert secondary['fer_contrasts']['Z-sel_minus_Z']['point'] == -.01
    assert secondary['fer_contrasts']['CD_minus_TRUE_GEOMETRY']['point'] == .05
    assert secondary['geometry']['Z']['two_atoms_0.75']['count'] == 480
    assert secondary['geometry']['Z']['singleton_phantom_frame']['count'] == 2
    assert secondary['geometry']['Z']['close_phantom_frame']['count'] == 1
    assert secondary['geometry']['Z']['singleton_phantom_le_025_frame']['count'] == 1
    assert secondary['geometry']['Z']['omitted_energy_fraction']['0.35']['point'] == pytest.approx(60/900)
    discordance = secondary['occupancy_discordance_035']
    assert discordance['Z_only']['count'] == discordance['CD_only']['count'] == 1
    assert discordance['Z_only']['pooled_omitted_fraction']['Z_minus_CD'] == -.1
    assert discordance['CD_only']['pooled_omitted_fraction']['Z_minus_CD'] == .1
    z_only = discordance['Z_only']['frames'][0]
    assert z_only['frame'] == 80700 and z_only['true_dopplers'] == [0., .35]
    assert z_only['fitted']['Z'] == [{'doppler': 0., 'gain': [1., 0.]},
                                     {'doppler': .35, 'gain': [1., 0.]}]


def test_no_occupancy_discordance():
    report = verdict.occupancy_discordance([row(FAKE_FRAMES.start)])
    assert report['Z_only'] == report['CD_only'] == {
        'count': 0, 'frames': [], 'mean_z_minus_cd_omitted_energy': None, 'pooled_omitted_fraction': None,
    }
