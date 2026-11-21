import unittest

from aggregate_main import aggregate, s_penalty_summary, x_gate_exposure


def s_row(key, norm):
    return dict(key=key, slo_retained_penalty_fro=norm, projectors_equal=False,
                variants={arm: dict(info_errors=0, fer=0) for arm in ('R0', 'S-lo', 'G')})


def x_row(frame, cd_resolved, *, trials=0, local=(), final=(), gate_resolved=True):
    return dict(frame=frame, arm_diagnostics={
        'CD': dict(resolution_035=dict(resolved=cd_resolved)),
        'G-ex': dict(resolution_035=dict(resolved=gate_resolved)),
    }, gate_census=dict(nonempty_trials=trials, valid_trials=100,
                        local_pass_blocks=[[dict(gate_rank=r) for r in ranks] for ranks in local],
                        final_blocks=[dict(gate_rank=r) for r in final],
                        refit_blocks=[[dict(gate_rank=1)]], active_refits=1))


class AggregationTest(unittest.TestCase):
    def test_penalty_quartiles_and_strict_zero(self):
        norms = [0., 1e-16, 2., 4.]
        summary = s_penalty_summary(dict(slo_retained_penalty_fro=n) for n in norms)
        self.assertEqual(summary['keys'], 4)
        self.assertAlmostEqual(summary['q25'], 7.5e-17, delta=1e-30)
        self.assertEqual(summary['median'], 1.)
        self.assertEqual(summary['q75'], 2.5)
        self.assertEqual(summary['zero_count'], 1)
        self.assertEqual(summary['fraction_exactly_zero'], .25)
        for invalid in ([], [float('nan')], [-1.]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                s_penalty_summary(dict(slo_retained_penalty_fro=n) for n in invalid)

    def test_x_exposure_filters_denominator_and_counts_construction_points(self):
        rows = [
            x_row(1600, True, trials=2, local=[(1, 2), (0,)], final=(1, 2), gate_resolved=False),
            x_row(1601, False, trials=100, local=[(1,), (2,)], final=(1,)),
            x_row(1602, True, trials=3, local=[(0, 0), (2,)], final=(0,)),
            x_row(1603, True),
        ]
        self.assertEqual(x_gate_exposure(rows),
                         dict(cd_resolved_frames=3, trial_firings=5,
                              local_pass_firings=2, final_refit_firings=1))
        self.assertEqual(x_gate_exposure(rows[1:2]),
                         dict(cd_resolved_frames=0, trial_firings=0,
                              local_pass_firings=0, final_refit_firings=0))
        with self.assertRaisesRegex(ValueError, 'legal trial firing count'):
            x_gate_exposure([x_row(1604, True, trials=101)])

    def test_joint_aggregation_preserves_physical_frames_across_segments(self):
        keys = [(scenario, 300, snr, frame) for frame in (5800, 6200)
                for scenario in ('U', 'G') for snr in (600, 700)]
        s_rows = [s_row(key, i) for i, key in enumerate(keys)]
        x_rows = [x_row(1600, True, trials=1), x_row(1601, False, trials=5)]
        result = aggregate(s_rows[::-1], x_rows, expected_s_keys=keys, expected_x_frames=[1600, 1601])
        self.assertEqual(result['s_leg']['n_frame_clusters'], 2)
        self.assertEqual(result['s_leg']['n_keys'], 8)
        self.assertTrue(result['s_leg']['equivalent'])
        self.assertEqual(result['s_leg']['verdict'], 'pass')
        self.assertEqual(result['x_leg']['cd_resolved_frames'], 1)
        self.assertEqual(result['joint'], 'uncertain')
        self.assertEqual(result['retained_penalty']['fraction_exactly_zero'], .125)
        self.assertEqual(result['x_gate_exposure']['trial_firings'], 1)

        for bad_s, bad_x, leg in (
                (s_rows[:-1], x_rows, 'S'), (s_rows + s_rows[:1], x_rows, 'S'),
                (s_rows, x_rows[:-1], 'X'), (s_rows, x_rows + x_rows[:1], 'X')):
            with self.subTest(leg=leg), self.assertRaisesRegex(ValueError, f'^{leg} rows'):
                aggregate(bad_s, bad_x, expected_s_keys=keys, expected_x_frames=[1600, 1601])


if __name__ == '__main__':
    unittest.main()
