import unittest

from main_schedule import choose, s_keys


class MainScheduleTest(unittest.TestCase):
    def test_disjoint_segments_preserve_physical_frame_clusters(self):
        plan, cost = choose(12.8, 1.2, extension_passed=True)
        self.assertEqual(plan["s_segments"], ((5800, 5999), (6200, 6399)))
        keys = s_keys(plan["s_segments"])
        frames = [key[3] for key in keys]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), 4800)
        self.assertEqual(len(set(frames)), 400)
        self.assertEqual(frames[2399:2401], [5999, 6200])
        self.assertTrue(all(frames.count(frame) == 12 for frame in set(frames)))
        self.assertEqual(plan["cluster_unit"], "physical frame")
        self.assertLessEqual(cost["selected_total_core_hours"], 25)

    def test_audit_and_total_cost_choose_the_fallback(self):
        for s_seconds, x_seconds, audited, reason in (
            (12.8, 1.2, False, "extension_audit_failed"),
            (14, 5, True, "extension_over_cap"),
        ):
            with self.subTest(audited=audited):
                plan, cost = choose(s_seconds, x_seconds, extension_passed=audited)
                self.assertEqual(plan["s_segments"], ((5800, 5999),))
                self.assertEqual(plan["s_keys"], 2400)
                self.assertEqual(plan["reason"], reason)
                self.assertEqual(cost["selected_total_core_hours"], cost["total_core_hours"][2400])
        with self.assertRaisesRegex(ValueError, "Both registered schedules"):
            choose(29, 5, extension_passed=True)

    def test_rejects_unregistered_gap_crossing_schedule(self):
        with self.assertRaisesRegex(ValueError, "Unregistered"):
            s_keys(((5800, 6399),))
