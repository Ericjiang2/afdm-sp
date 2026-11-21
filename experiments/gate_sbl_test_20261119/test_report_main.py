"""Synthetic tests for main aggregation without receiver execution."""

import unittest

from report_main import P1_DOMAIN, P1_ENTROPY, _fingerprint, _render, summarize


def s_row(scenario, snr, frame):
    score = dict(info_errors=0, fer=0, decoded=True, decoded_sha256='a' * 64,
                 nmse=.1, n_pair=1, pairs=[dict()],
                 sbl=dict(max_iter=100, iterations=90, converged=True, beta=5.))
    gate = dict(score, info_errors=1, fer=1, decoded=False) if scenario == 'G' and snr == 600 else score
    blocks = [
        dict(delay=0, size=1, gate_rank=0, s_lo_rank=0, overlap_trace=0.,
             gate_in_s_lo=True, projectors_equal=True),
        dict(delay=1, size=2, gate_rank=0, s_lo_rank=1, overlap_trace=0.,
             gate_in_s_lo=True, projectors_equal=False),
        dict(delay=2, size=4, gate_rank=1, s_lo_rank=1, overlap_trace=.7,
             gate_in_s_lo=False, projectors_equal=False),
        dict(delay=3, size=25, gate_rank=2, s_lo_rank=4, overlap_trace=2.,
             gate_in_s_lo=True, projectors_equal=False),
    ]
    return dict(
        family='P1', key=[scenario, 300, snr, frame], frame=frame, scenario=scenario, rho_permille=300,
        snr_centi_db=snr, sigma2=.1, rng_domain=P1_DOMAIN, rng_entropy=P1_ENTROPY,
        pairing=dict(info_sha256='f' * 64, coded_sha256='a' * 64, noise_sha256='b' * 64,
                     physical_gains_sha256= ('c' if scenario == 'G' else 'd') * 64),
        input_sha256=dict(pilot='0' * 64, data_true='1' * 64),
        variants={'R0': score, 'S-lo': score, 'G': gate},
        n_candidates_stage2=32, gate_census=blocks, projectors_equal=False,
        slo_retained_penalty_fro=float(scenario == 'G'),
    )


def x_row(frame, cd_resolves, gate_resolves, trials, *, local=False, refit=False):
    record = dict(info_errors=0, decoded_sha='c' * 64,
                  doublet_two_atoms={'0.35': True, '0.75': False})
    arms = {name: record for name in ('F0', 'CD', 'G-ex')}
    diagnostics = {name: dict(fer=0, decoded=True, resolution_035={'resolved': resolved})
                   for name, resolved in zip(arms, (False, cd_resolves, gate_resolves), strict=True)}
    fingerprints = {name: _fingerprint(dict(record=arms[name], **diagnostics[name]))
                    for name in ('CD', 'G-ex')}
    census = dict(nonempty_trials=trials, valid_trials=20, active_refits=0,
                  local_pass_blocks=[[dict(gate_rank=int(local)), dict(gate_rank=int(local))]],
                  final_blocks=[dict(gate_rank=int(refit)), dict(gate_rank=int(refit))])
    return dict(frame=frame, scenario='MIXED8', snr_db=7, info_sha='0' * 64, noise_sha='1' * 64, arms=arms,
                arm_diagnostics=diagnostics, output_fingerprints=fingerprints, gate_census=census)


class MainReportTest(unittest.TestCase):
    def setUp(self):
        self.s = [s_row(scenario, snr, frame) for frame in (5800, 6200)
                  for scenario in ('U', 'G') for snr in (600, 700)]
        self.x = [x_row(1600, True, True, 0), x_row(1601, True, False, 2, local=True),
                  x_row(1602, False, False, 8, refit=True)]
        self.keys = [tuple(row['key']) for row in self.s]

    def summarize(self):
        return summarize(self.s, self.x, expected_s_keys=self.keys, expected_x_frames=range(1600, 1603),
                         x_snr_db=7)

    def test_observations_preserve_clusters_and_denominator(self):
        summary = self.summarize()
        s, x = summary['s_leg'], summary['x_leg']
        s_extra, x_extra = summary['s_secondary'], summary['x_secondary']
        self.assertEqual(s['n_frame_clusters'], 2)
        self.assertEqual(s['point'], .25)
        self.assertEqual(s_extra['fer']['overall']['G']['failures'], 2)
        self.assertEqual(s_extra['fer']['by_scenario_snr_db']['G']['6']['contrasts']['G − R0']['point'], 1.)
        self.assertEqual(s_extra['gate_census']['6']['3–24']['subset_fraction'], 0.)
        self.assertEqual(s_extra['gate_census']['6']['25']['overlap_fraction']['median'], .5)
        self.assertEqual(s_extra['em']['S-lo']['total_output_co_delay_pairs'], 8)
        self.assertEqual(summary['retained_penalty']['fraction_exactly_zero'], .5)
        self.assertEqual(x['cd_resolved_frames'], 2)
        self.assertEqual(x['lost_frames'], 1)
        self.assertEqual(summary['x_gate_exposure'],
                         dict(cd_resolved_frames=2, trial_firings=2, local_pass_firings=1, final_refit_firings=0))
        self.assertEqual(x_extra['firings'], dict(trial_firings=10, local_pass_firings=1, final_refit_firings=1))
        self.assertEqual(x_extra['byte_identical_frames'], 2)
        self.assertEqual(x_extra['two_atom_rate']['G-ex']['0.35']['rate'], 1.)
        report = _render(dict(summary, _config={'freeze_commit': 'deadbeef'}))
        self.assertEqual([line for line in report.splitlines() if line.startswith('## ')],
                         ['## Observation', '## Frozen verdict', '## Untested'])
        self.assertIn(f"| Joint | — | {summary['joint']} |", report)

    def test_rejects_missing_key_and_changed_exogenous_hash(self):
        self.s[1]['pairing']['noise_sha256'] = 'e' * 64
        with self.assertRaisesRegex(ValueError, 'changed S exogenous hashes'):
            self.summarize()
        self.s.pop(1)
        with self.assertRaisesRegex(ValueError, 'paired key schedule'):
            self.summarize()

    def test_rejects_divergence_with_empty_gate(self):
        self.x[0] = x_row(1600, True, False, 0)
        with self.assertRaisesRegex(ValueError, 'differ on a frame with empty projectors'):
            self.summarize()


if __name__ == '__main__':
    unittest.main()
