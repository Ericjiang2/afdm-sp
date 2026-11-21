"""Synthetic fixtures for the frozen verdict logic and main result boundary."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

import aggregate as agg


def interval(lo, hi, evaluable=True):
    return dict(ci_lo=lo, ci_hi=hi, evaluable=evaluable)


def support_metrics():
    return {
        's': interval(.5, .93), 't': interval(-.10, .25),
        'f_lo': interval(.5, 1.18), 'f_hi': interval(-.10, .25),
        'delta_lo': interval(.004, .008), 'delta_hi': interval(-.01, .01),
    }


class VerdictTest(unittest.TestCase):
    def test_sbl_support_thresholds_and_prediction_score(self):
        verdict = agg.frozen_verdicts(support_metrics())
        self.assertEqual(verdict['stage'], 'SBL')
        self.assertEqual(verdict['lo'], agg.CARRIES)
        self.assertEqual(verdict['hi'], agg.INSUFFICIENT)
        self.assertEqual(verdict['delta_lo'], agg.PROJECTOR)
        self.assertTrue(verdict['shape_equivalence_overlap']['delta_lo'])
        self.assertEqual(verdict['candidate'], agg.SUPPORT)
        score = agg.prediction_score(verdict['candidate'])
        self.assertAlmostEqual(score['brier'], (.25 - 1) ** 2 + .35 ** 2 + .4 ** 2)
        self.assertAlmostEqual(score['log_loss'], -math.log(.25))

    def test_other_stages_and_candidate_classes(self):
        cases = (
            (interval(-.10, .25), interval(.50, .95), support_metrics()['f_lo'],
             'REFINEMENT', agg.LOW_ONLY_INSUFFICIENT),
            (interval(.25, .45), interval(.25, .48), support_metrics()['f_lo'],
             'SHARED', agg.UNESTABLISHED),
            (interval(.25, .45), interval(.10, .48), interval(.1, .25),
             'INCONCLUSIVE', agg.LOW_ONLY_INSUFFICIENT),
            (interval(.5, .8, False), interval(-.10, .20), interval(.5, .8, False),
             'INCONCLUSIVE', agg.UNESTABLISHED),
        )
        for s, t, f_lo, stage, candidate in cases:
            with self.subTest(stage=stage, candidate=candidate):
                verdict = agg.frozen_verdicts(dict(support_metrics(), s=s, t=t, f_lo=f_lo))
                self.assertEqual(verdict['stage'], stage)
                self.assertEqual(verdict['candidate'], candidate)
                if not f_lo['evaluable']:
                    self.assertEqual(verdict['lo'], agg.UNEVALUABLE)

    def test_nonsignificance_does_not_refute(self):
        verdict = agg.frozen_verdicts(dict(support_metrics(), delta_lo=interval(-.02, .03)))
        self.assertEqual(verdict['delta_lo'], agg.UNCERTAIN)
        self.assertEqual(verdict['candidate'], agg.UNESTABLISHED)

    def test_shape_list_order_and_margin_edges(self):
        cases = (
            ((.001, .01), agg.PROJECTOR, True),
            ((-.01, -.001), agg.EQUIVALENT, True),
            ((-.01, .01), agg.EQUIVALENT, False),
            ((-.02, -.01), agg.ISOTROPIC, False),
            ((-.02, 0), agg.UNCERTAIN, False),
            ((0, .02), agg.UNCERTAIN, False),
            ((.01, .02), agg.PROJECTOR, False),
        )
        for bounds, label, overlap in cases:
            with self.subTest(bounds=bounds):
                self.assertEqual(agg.shape_class(interval(*bounds)), (label, overlap))

    def test_contrasts_and_nonpositive_ratio_limit(self):
        point = dict(zip(agg.ARMS, (.05, .40, .20, .30, .20, .20, .35, .25, .34)))
        draws = {key: np.full(100, value) for key, value in point.items()}
        metrics = agg.contrasts(point, draws)
        for name, expected in {'s': .5, 't': 1, 'I': -.5, 'f_lo': 2, 'f_hi': .5,
                               'delta_lo': .05, 'delta_hi': -.01}.items():
            with self.subTest(contrast=name):
                self.assertAlmostEqual(metrics[name]['point'], expected)
                self.assertAlmostEqual(metrics[name]['ci_lo'], expected)
                self.assertAlmostEqual(metrics[name]['ci_hi'], expected)
        for bad, evaluable in ((1, True), (2, False)):
            with self.subTest(nonpositive=bad):
                draws['R2'][:bad] = point['R1']
                metrics = agg.contrasts(point, draws)
                self.assertEqual(metrics['I']['evaluable'], evaluable)
                self.assertEqual(metrics['s']['denominator_nonpositive_fraction'], bad / 100)
                self.assertTrue(metrics['f_lo']['evaluable'])
                self.assertAlmostEqual(metrics['delta_lo']['point'], .05)


def synthetic_arm(failure, budget):
    return dict(info_errors=failure, fer=failure, nmse=.5, n_atoms=2, n_pair=1,
                added_trace_sbl=0., added_trace_refinement=0.,
                sbl=dict(n_final=3, beta=2., iterations=budget, max_iter=budget, converged=False))


class AggregateIntegrationTest(unittest.TestCase):
    def test_complete_synthetic_main_and_primary_verdict_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            config = json.dumps({'_argv': ['run_main.py'], '_config': {'workers': 1}}).encode()
            (out / 'config.json').write_bytes(config)
            (out / 'receiver_receipt.json').write_text(json.dumps({'receiver_core_hours': 1.25}))
            config_sha256 = hashlib.sha256(config).hexdigest()
            cutoffs = dict(zip(agg.ARMS, (1, 4, 2, 2, 4, 2, 4, 3, 4)))
            with (out / 'rows_shard000.jsonl').open('w') as handle:
                for key in sorted(agg.MAIN_KEYS):
                    frame = key[-1]
                    budgets = {'100': {arm: synthetic_arm(int(frame % 10 < cutoff), 100)
                                       for arm, cutoff in cutoffs.items()}}
                    if frame in agg.EXTENDED_FRAMES:
                        budgets['400'] = {arm: synthetic_arm(1, 400) for arm in agg.EXTENDED}
                    row = dict(key=key, config_sha256=config_sha256, status='ok',
                               rng_domain='synthetic', rng_entropy='test',
                               pairing={field: f'{frame:064x}' for field in agg.FINGERPRINTS},
                               n_candidates_stage2=3, budgets=budgets,
                               census=dict(eigenvalues_in_025_075=1, eigenvalues_total=3))
                    handle.write(json.dumps(row) + '\n')

            agg.main(['--out', directory])
            result = json.loads((out / 'results.json').read_text())
            self.assertEqual(result['n_keys'], 1200)
            self.assertEqual(result['n_clusters'], 100)
            self.assertEqual(result['extended']['n_keys'], 600)
            self.assertEqual(result['extended']['n_clusters'], 50)
            self.assertEqual(result['extended']['arms']['S-lo']['400']['point'], 1.)
            self.assertEqual(result['verdicts']['candidate'], agg.SUPPORT)
            self.assertEqual(result['census']['share'], 1 / 3)
            self.assertEqual(result['receiver_core_hours'], 1.25)
            self.assertEqual(result['_config']['bootstrap']['seed'], 20261119)
            self.assertEqual(result['_config']['bootstrap']['draws'], 20_000)
            self.assertIn('Claude’s §7.4 prediction score', (out / 'RESULTS.md').read_text())

            with (out / 'rows_shard000.jsonl').open('r+') as handle:
                first = json.loads(handle.readline())
                handle.seek(0, 2)
                handle.write(json.dumps(first) + '\n')
            with self.assertRaisesRegex(ValueError, 'duplicate or unexpected key'):
                agg.load_rows(out, {'workers': 1}, config_sha256)


if __name__ == '__main__':
    unittest.main()
