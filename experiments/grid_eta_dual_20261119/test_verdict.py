"""Synthetic threshold, precedence, pairing and aggregation checks."""

from itertools import product
import unittest

from verdict import DELTAS, ETAS, S_ARMS, X_ARMS, classify, summarize


def ci(low, high):
    return dict(ci_lo=low, ci_hi=high)


class VerdictTests(unittest.TestCase):
    def test_x_thresholds(self):
        cases = [
            (.10, .20, "supported", "supported"),
            (.01, .099, "supported", "refuted"),
            (.01, .10, "supported", "uncertain"),
            (0, .15, "uncertain", "uncertain"),
            (-.15, 0, "uncertain", "refuted"),
            (-.15, -.01, "opposite", "refuted"),
        ]
        for low, high, direction, quantity in cases:
            with self.subTest(low=low, high=high):
                outcome = classify(ci(low, high), ci(.001, .10), ci(0, 0), ci(0, 0), ci(0, 0))
                self.assertEqual((outcome["X_direction"], outcome["X_quantity"]),
                                 (direction, quantity))

    def test_x_requires_an_a2_increase(self):
        for a2 in (ci(0, .10), ci(-.15, -.02)):
            outcome = classify(ci(.11, .20), a2, ci(.02, .03), ci(.02, .03), ci(.04, .06))
            self.assertEqual(outcome["X_direction"], "uncertain")
            self.assertEqual(outcome["X_quantity"], "supported")
            self.assertEqual(outcome["joint"], "uncertain")

    def test_s_and_joint(self):
        up, down, mixed = ci(.002, .005), ci(-.010, -.002), ci(0, .1)
        cases = [
            (up, up, up, ci(.004, .01), "monotone_supported", "both_directions_supported", True, True),
            (up, mixed, up, ci(.004, .02), "uncertain", "uncertain", False, False),
            (up, up, ci(0, .015), ci(-.015, .015), "insensitive", "uncertain", True, True),
            (up, up, ci(0, .016), ci(-.015, .015), "endpoint_equivalent", "uncertain", False, True),
            (up, down, mixed, ci(-.02, -.001), "uncertain", "opposite_prediction", False, False),
            (up, down, down, ci(-.015, -.001), "insensitive", "opposite_prediction", True, True),
            (up, down, ci(-.01, 0), ci(-.015, 0), "insensitive", "uncertain", True, True),
            (down, up, up, ci(.004, .02), "monotone_supported", "opposite_prediction", False, False),
            (mixed, up, up, ci(.004, .02), "monotone_supported", "uncertain", False, False),
        ]
        for x, d4, d8, total, s, joint, insensitive, endpoint in cases:
            with self.subTest(x=x, d4=d4, d8=d8, total=total):
                verdict = classify(x, up, d4, d8, total)
                self.assertEqual((verdict["S"], verdict["joint"], verdict["S_insensitive"],
                                  verdict["S_endpoint_equivalent"]), (s, joint, insensitive, endpoint))

    def fixture(self):
        x_rows = [dict(frame=f, deltas={str(d): {"arms": {
            a: {"Q": bool(d == .0625 and a == "A2")} for a in X_ARMS}} for d in DELTAS}) for f in (1, 2)]
        s_rows = [dict(key=(scenario, 300, snr, f), eta=eta, grid_low_modes_per_delay=eta,
                       grid_low_modes=eta * 2, screened_block_ranks=[3], census=dict(projector_rank=3), variants={
                           arm: dict(frame_error=arm == "R1" and (eta == 8 or eta == 4 and scenario == "G"),
                                     n_pair=1, added_trace_sbl=0, sbl=dict(beta=2, converged=True))
                           for arm in S_ARMS})
                  for scenario, snr, f, eta in product("UG", (600, 800), (3, 4), ETAS)]
        return x_rows, s_rows, dict(x_frames=(1, 2), s_frames=(3, 4), snrs=(600, 800))

    def test_paired_cluster_readout(self):
        x, s, schedule = self.fixture()
        report = summarize(x[::-1], s[::-1], **schedule)
        self.assertEqual(report["X"]["point"], 1)
        self.assertEqual(report["X"]["changes"]["A2"]["ci_lo"], 1)
        self.assertEqual(report["X"]["changes"]["CODELAY"]["ci_hi"], 0)
        self.assertEqual(report["S"]["clusters"], 2)
        for contrast in ("4_minus_2", "8_minus_4"):
            self.assertEqual(report["S"]["contrasts"][contrast]["ci_lo"], .5)
            self.assertEqual(report["S"]["contrasts"][contrast]["ci_hi"], .5)
        self.assertEqual(report["S"]["eta"][8]["arms"]["S-lo"]["beta_mean"], 2)
        self.assertEqual(report["verdict"]["joint"], "both_directions_supported")

    def test_x_scorers_share_the_same_frame_draw(self):
        x, s, schedule = self.fixture()
        x[1]["deltas"]["0.0625"]["arms"]["A2"]["Q"] = False
        x[1]["deltas"]["0.25"]["arms"]["CODELAY"]["Q"] = True
        report = summarize(x, s, **schedule)["X"]
        self.assertEqual((report["ci_lo"], report["ci_hi"]), (1, 1))
        self.assertEqual(report["changes"]["A2"]["point"], .5)
        self.assertEqual(report["changes"]["CODELAY"]["point"], -.5)

    def test_x_exclusion_and_two_arm_fallback(self):
        x, s, schedule = self.fixture()
        x[0] = dict(frame=x[0]["frame"], exclusions={"0.25": "outside_bank", "0.125": "outside_bank"})
        for row in s:
            del row["variants"]["S-lo"]
        with self.assertRaisesRegex(ValueError, "arm"):
            summarize(x, s, **schedule)
        report = summarize(x, s, **schedule, s_arms=("R0", "R1"))
        self.assertEqual(report["X"]["clusters"], 1)
        self.assertEqual(report["X"]["excluded_frames"], 1)
        self.assertEqual(report["X"]["exclusions_by_reason"], {"outside_bank": 1})
        self.assertEqual(set(report["S"]["slope_by_arm"]), {"R1"})
        x[1] = dict(frame=x[1]["frame"], exclusions={"0.25": "duplicate_atom"})
        with self.assertRaisesRegex(ValueError, "All X"):
            summarize(x, s, **schedule, s_arms=("R0", "R1"))

    def test_incomplete_duplicate_and_invalid_rows(self):
        x, s, schedule = self.fixture()
        for x_rows, s_rows in ((x[:-1], s), (x + x[:1], s), (x, s[:-1]), (x, s + s[:1])):
            with self.assertRaises(ValueError):
                summarize(x_rows, s_rows, **schedule)
        s[0]["variants"]["R0"]["frame_error"] = 1
        with self.assertRaisesRegex(ValueError, "Boolean"):
            summarize(x, s, **schedule)


if __name__ == "__main__":
    unittest.main()
