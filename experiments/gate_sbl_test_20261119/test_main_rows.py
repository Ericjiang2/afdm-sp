"""Test admission bindings with stub arms, without generating any channels."""

from types import SimpleNamespace
import unittest

from run_main_rows import bind_s_key, bind_x_frame, phase2_schedule, validate_x_identity


S_SMOKE = ('U', 300, 600, 8400)
ARCHIVE_FRAMES = range(1000, 1020)
S_RECEIVER = SimpleNamespace(e3c=SimpleNamespace(lib=SimpleNamespace(smoke_keys=lambda: {S_SMOKE})))


def receiver():
    return S_RECEIVER


def simulated_s_arm(ctx, grid, key, *, replace_with_low=False):
    if key not in receiver().e3c.lib.smoke_keys():
        raise ValueError(key)
    return ctx, grid, key, replace_with_low


def simulated_x_arm(ctx, full, cd, frame, *, gate):
    if frame not in ARCHIVE_FRAMES:
        raise ValueError(frame)
    return ctx, full, cd, frame, gate


class MainRowsTest(unittest.TestCase):
    def test_s_admission_is_private_and_exact(self):
        _, keys, _ = phase2_schedule()
        allowed = frozenset(keys)
        run = bind_s_key(simulated_s_arm, S_RECEIVER, allowed)
        self.assertEqual(len(allowed), 4800)
        for frame in (5800, 5999, 6200, 6399):
            key = ('U', 300, 600, frame)
            self.assertEqual(run('ctx', 'grid', key), ('ctx', 'grid', key, False))
            with self.assertRaises(ValueError):
                simulated_s_arm('ctx', 'grid', key)
        for frame in (5799, 6000, 6199, 6400, 8400):
            with self.assertRaises(ValueError):
                run('ctx', 'grid', ('U', 300, 600, frame))
        for key in (('MIXED8', 300, 600, 5800), ('U', 500, 600, 5800), ('U', 300, 7000, 5800)):
            with self.assertRaises(ValueError):
                run('ctx', 'grid', key)
        self.assertEqual(simulated_s_arm('ctx', 'grid', S_SMOKE)[2], S_SMOKE)

    def test_x_admission_is_private_and_exact(self):
        _, _, allowed = phase2_schedule()
        run = bind_x_frame(simulated_x_arm, allowed)
        self.assertEqual(len(allowed), 600)
        for frame in (1600, 2199):
            self.assertEqual(run('ctx', 'full', 'cd', frame), ('ctx', 'full', 'cd', frame, 'actual'))
            with self.assertRaises(ValueError):
                simulated_x_arm('ctx', 'full', 'cd', frame, gate='actual')
        for frame in (1000, 1599, 2200):
            with self.assertRaises(ValueError):
                run('ctx', 'full', 'cd', frame)
        self.assertEqual(simulated_x_arm('ctx', 'full', 'cd', 1000, gate='low')[-1], 'low')

    def test_x_identity_when_every_effective_projector_is_empty(self):
        counts = dict(nonempty_trials=0, active_refits=0, local_pass_blocks=[], final_blocks=[])
        row = dict(frame=1600, gate_census=counts, output_fingerprints={'CD': 'a', 'G-ex': 'a'})
        validate_x_identity(row)
        row['output_fingerprints']['G-ex'] = 'b'
        with self.assertRaisesRegex(RuntimeError, 'empty effective projectors'):
            validate_x_identity(row)
        for activity in (dict(nonempty_trials=1), dict(active_refits=1),
                         dict(local_pass_blocks=[[{'gate_rank': 1}]]), dict(final_blocks=[{'gate_rank': 1}])):
            with self.subTest(activity=activity):
                validate_x_identity(dict(row, gate_census=dict(counts, **activity)))


if __name__ == '__main__':
    unittest.main()
