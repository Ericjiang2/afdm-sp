"""Synthetic coverage for DRAFT §§9–10 decision rules and estimators."""

import unittest

import numpy as np

import verdict


def ci(lo, hi, evaluable=True):
    return dict(ci_lo=lo, ci_hi=hi, evaluable=evaluable)


def mirrors(hi=ci(.5, .75), lo=ci(.05, .25)):
    return {'C-hi': hi, 'C-lo': lo}


def supported():
    return dict(G_B=ci(.1, .15), A2_minus_CD=ci(.01, .02),
                phi_lo=ci(.5, .8), phi_hi=ci(.1, .25), phi_U2=ci(.5, .9),
                delta_lo=ci(.001, .02), delta_UC=ci(-.005, .005),
                delta_UA=ci(-.03, -.01), delta_C_hi_CD=ci(-.005, .005),
                H=ci(-.005, .005), psi=mirrors(),
                admission=dict(n_units=100, pi=mirrors()))


class TestVerdict(unittest.TestCase):
    def classify(self, **replacements):
        primary = replacements.pop('primary', 'fer')
        return verdict.classify(supported() | replacements, margin=.005, v5_primary=primary)

    def test_supported(self):
        result = self.classify()
        self.assertEqual(result['V1'], verdict.V1_SUPPORT)
        self.assertEqual(result['V2'], 'recovers')
        self.assertEqual(result['V3'], 'non-inferior')
        self.assertEqual(result['V4'], 'superior')
        self.assertEqual(result['C_hi_vs_CD'], 'non-inferior')
        self.assertEqual(result['layers'], dict(spectral_mechanism='supported',
                                                operational_compatibility='supported',
                                                joint_claim='supported'))

    def test_halves_shape_and_harm(self):
        cases = [
            ('V1', 'replay did not replicate', dict(phi_lo=ci(.1, .25))),
            ('V1', verdict.NOT_ESTABLISHED, dict(phi_lo=ci(.1, .7))),
            ('hi', 'carries', dict(phi_hi=ci(.5, .7))),
            ('shape', verdict.UNCERTAIN, dict(delta_lo=ci(-.01, .01))),
            ('shape', verdict.UNCERTAIN, dict(delta_lo=ci(0., .005))),
            ('shape', 'isotropic superior', dict(delta_lo=ci(-.01, -.001))),
            ('shape', 'projector superior', dict(delta_lo=ci(.001, .003))),
            ('H', 'harmful', dict(H=ci(.001, .002))),
            ('H', 'beneficial', dict(H=ci(-.002, -.001))),
            ('H', verdict.UNCERTAIN, dict(H=ci(-.01, 0.))),
        ]
        for field, expected, replacements in cases:
            with self.subTest(field=field, replacements=replacements):
                self.assertEqual(self.classify(**replacements)[field], expected)
        self.assertEqual(self.classify(H=ci(.001, .002))['layers']['joint_claim'], 'supported')

    def test_operational_components(self):
        cases = [
            ('V2', 'does not recover', dict(phi_U2=ci(.1, .25))),
            ('V2', verdict.UNCERTAIN, dict(phi_U2=ci(.25, .5))),
            ('V3', 'inferior', dict(delta_UC=ci(.006, .008))),
            ('V3', verdict.UNCERTAIN, dict(delta_UC=ci(.005, .008))),
            ('V3', 'non-inferior', dict(delta_UC=ci(-.008, -.006))),
            ('V3', verdict.UNCERTAIN, dict(delta_UC=ci(None, .006))),
            ('V4', 'not superior', dict(delta_UA=ci(0, .02))),
            ('V4', verdict.UNCERTAIN, dict(delta_UA=ci(-.005, 0))),
        ]
        for field, expected, replacements in cases:
            with self.subTest(field=field, replacements=replacements):
                result = self.classify(**replacements)
                self.assertEqual(result[field], expected)
                if expected != 'non-inferior':
                    self.assertEqual(result['layers']['operational_compatibility'], verdict.NOT_ESTABLISHED)
                    self.assertEqual(result['layers']['joint_claim'], verdict.NOT_ESTABLISHED)

    def test_crossover_and_invalid_ratios(self):
        for replacement in (dict(G_B=ci(0, .1)),
                            dict(A2_minus_CD=ci(0, .1), phi_U2=ci(.1, .25)),
                            dict(A2_minus_CD=ci(None, None, False))):
            with self.subTest(replacement=replacement):
                result = self.classify(**replacement)
                self.assertEqual(set(result['layers'].values()), {verdict.NOT_EVALUABLE})
        self.assertEqual(self.classify(A2_minus_CD=ci(-.01, .1))['V5']['verdict'], verdict.NOT_EVALUABLE)
        failed = ci(None, None, False)
        self.assertEqual(self.classify(phi_hi=failed)['V1'], verdict.NOT_EVALUABLE)
        v2_failure = self.classify(phi_U2=failed)
        self.assertEqual(v2_failure['V2'], verdict.NOT_EVALUABLE)
        self.assertEqual(v2_failure['layers']['operational_compatibility'], verdict.NOT_EVALUABLE)
        self.assertEqual(v2_failure['layers']['spectral_mechanism'], 'supported')

    def test_mirrors_and_primary_selection(self):
        for ratios, expected in (
            (mirrors(), verdict.V5_SUPPORT),
            (mirrors(hi=ci(.1, .25), lo=ci(.5, .7)), 'mirror opposite'),
            (mirrors(hi=ci(.2, .6), lo=ci(.5, .7)), verdict.NOT_ESTABLISHED),
            (mirrors(hi=ci(.6, .7), lo=ci(.5, .7)), verdict.NOT_ESTABLISHED),
            (mirrors(hi=ci(None, None, False)), verdict.NOT_EVALUABLE),
        ):
            with self.subTest(expected=expected):
                result = self.classify(psi=ratios, admission=dict(n_units=100, pi=ratios))
                self.assertEqual(result['V5']['verdict'], expected)
                self.assertEqual(result['V5_adm']['verdict'], expected)
        fer_only = self.classify(admission=dict(n_units=99, pi={}))
        self.assertEqual(fer_only['V5_adm']['verdict'], verdict.NOT_EVALUABLE)
        self.assertEqual(fer_only['layers']['joint_claim'], 'supported')
        adm_primary = self.classify(primary='adm', admission=dict(n_units=99, pi={}))
        self.assertEqual(adm_primary['layers']['spectral_mechanism'], verdict.NOT_EVALUABLE)
        self.assertEqual(adm_primary['layers']['operational_compatibility'], 'supported')
        opposite = self.classify(psi=mirrors(hi=ci(.1, .25), lo=ci(.5, .7)))
        self.assertEqual(opposite['layers']['spectral_mechanism'], verdict.NOT_ESTABLISHED)
        self.assertEqual(opposite['layers']['joint_claim'], verdict.NOT_ESTABLISHED)
        for width, primary in ((.25, 'fer'), (.25001, 'adm'), (None, 'adm')):
            self.assertEqual(verdict.select_v5_primary(width), primary)

    def test_ratio_denominator_threshold(self):
        point = dict(R1=.5, R0=.1, X=.2)
        for failures, expected in ((0, True), (1, True), (2, False), (100, False)):
            draws = dict(R1=np.r_[np.full(failures, .1), np.full(100 - failures, .5)],
                         R0=np.full(100, .1), X=np.full(100, .2))
            with self.subTest(failures=failures):
                ratio = verdict.ratio_summary(point, draws, {'R1': 1, 'X': -1}, verdict.SBL_GAP)
                self.assertEqual(ratio['denominator_nonpositive_fraction'], failures / 100)
                self.assertEqual(ratio['evaluable'], expected)
        reversed_point = point | {'R1': .1}
        draws = {arm: np.full(100, mean) for arm, mean in point.items()}
        self.assertFalse(verdict.ratio_summary(reversed_point, draws, {'R1': 1, 'X': -1},
                                               verdict.SBL_GAP)['evaluable'])

    def test_rare_event_bound_switch_and_directions(self):
        frames = np.repeat(np.arange(200), 34)
        cstate = {arm: np.zeros(len(frames), dtype=bool) for arm in ('U', 'C-hi', 'CD')}
        p, b, _ = verdict.estimates(cstate, frames)
        rare = verdict.ni_summary(cstate, frames, 'U', point=p, draws=b)
        cp0 = 1 - .05 ** (1 / 200)
        self.assertAlmostEqual(rare['ci_hi'], cp0 / 34, places=15)
        self.assertIsNone(rare['ci_lo'])
        self.assertEqual(rare['max_harm_keys_per_frame_assumed'], 1)

        cstate['CD'][34:37] = True
        cstate['U'][0:3] = True
        cstate['U'][68] = True
        cstate['U'][102] = True
        p, b, _ = verdict.estimates(cstate, frames)
        rare = verdict.ni_summary(cstate, frames, 'U', point=p, draws=b)
        only_beneficial = verdict.ni_summary(cstate, frames, 'C-hi', point=p, draws=b)
        self.assertAlmostEqual(rare['point'], 2 / len(frames))
        self.assertEqual(rare['discordant_frame_clusters'], 4)
        self.assertEqual(rare['candidate_only_failure_clusters'], 3)
        self.assertEqual(rare['reference_only_failure_clusters'], 1)
        self.assertEqual(rare['max_harm_keys_per_frame_assumed'], 3)
        self.assertAlmostEqual(rare['ci_hi'], rare['cp95_upper'] * 3 / 34)
        self.assertEqual(only_beneficial['candidate_only_failure_clusters'], 0)
        self.assertAlmostEqual(only_beneficial['ci_hi'], cp0 / 34, places=15)

        cstate['U'][136] = True
        p, b, _ = verdict.estimates(cstate, frames)
        regular = verdict.ni_summary(cstate, frames, 'U', point=p, draws=b)
        self.assertEqual(regular['discordant_frame_clusters'], 5)
        self.assertEqual(regular['method'], 'paired frame-cluster bootstrap')
        self.assertIsNotNone(regular['ci_lo'])
        with self.assertRaisesRegex(ValueError, 'balanced frame grid'):
            verdict.ni_summary(cstate, frames[:-1], 'U', point=p, draws=b)

    def test_joint_resampling_with_variable_unit_counts(self):
        frames = [1, 1, 1, 2]
        p, b, n = verdict.estimates({'A': [0, 0, 0, 1], 'B': [1, 1, 1, 0]}, frames)
        self.assertEqual((p, n), ({'A': .25, 'B': .75}, 2))
        np.testing.assert_array_equal(np.unique(b['A']), [0., .25, 1.])
        np.testing.assert_array_equal(b['A'] + b['B'], np.ones(verdict.N_BOOT))

    def test_full_readout_gate_and_common_grid(self):
        cframes = np.repeat(np.arange(200), 34)
        sframes = np.repeat(np.arange(200), 12)
        zero, one = np.zeros(len(sframes), int), np.ones(len(sframes), int)
        sbl = {'R0': zero, 'R1': one, 'S-lo': zero, 'S-hi': one, 'S-isolo': one, 'U2': zero}
        mask = np.tile(np.arange(34) < 12, 200)
        cstate = {arm: mask if arm in ('F0', 'A2', 'C-lo') else np.zeros_like(mask)
                  for arm in ('F0', *verdict.ADMISSION_ARMS)}
        preferences = {arm: np.full(100, arm in ('A2', 'C-lo'))
                       for arm in verdict.ADMISSION_ARMS}
        kwargs = dict(margin=.002, v5_primary='adm', cstate_common_mask=mask,
                      adm_preferences=preferences, adm_frames=np.repeat(np.arange(25), 4))

        result = verdict.readout(sbl, sframes, cstate, cframes, **kwargs)
        self.assertEqual(result['verdicts']['layers']['joint_claim'], 'supported')
        self.assertEqual(result['metrics']['admission']['n_frame_clusters'], 25)
        self.assertEqual(result['metrics']['admission']['pi']['C-hi']['point'], 1.)
        self.assertEqual(result['metrics']['admission']['pi']['C-lo']['point'], 0.)
        self.assertEqual(result['common_grid']['A2_minus_CD'], dict(point=1., sign='positive'))
        self.assertAlmostEqual(result['metrics']['A2_minus_CD']['point'], 12 / 34)
        self.assertEqual(result['common_grid']['G_B'], dict(point=1., sign='positive'))
        self.assertEqual(result['metrics']['delta_C_hi_CD']['ci_hi'], result['metrics']['delta_UC']['ci_hi'])

        with self.assertRaisesRegex(ValueError, 'complete physical frame'):
            verdict.readout(sbl, sframes, cstate, cframes[:-1], **kwargs)

    def test_admission_coverage_and_denominator(self):
        preferences = {arm: np.ones(100) for arm in verdict.ADMISSION_ARMS}
        frames = np.arange(100)
        summary = verdict.admission_summary(preferences, frames)
        self.assertFalse(summary['evaluable'])
        self.assertEqual(summary['pi']['C-hi']['denominator_nonpositive_fraction'], 1.)
        self.assertFalse(verdict.admission_summary({}, [])['evaluable'])
        with self.assertRaisesRegex(ValueError, 'paired five-arm'):
            verdict.admission_summary({'A2': preferences['A2']}, frames)


if __name__ == '__main__':
    unittest.main()
