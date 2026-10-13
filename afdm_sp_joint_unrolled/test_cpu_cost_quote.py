"""Cost plans must balance each SNR without treating repeats as new blocks."""
from collections import Counter
import unittest
from .trans_next_cpu_cost_quote import arms, order, compare_scores


class CPUCostQuoteTests(unittest.TestCase):
    def test_factorial_pairs_and_positions_balanced_within_each_snr(self):
        rows=order(True);names={a['name'] for a in arms(True)}
        self.assertEqual(len(rows),136)
        self.assertEqual(Counter(r['arm'] for r in rows[:8]),{a:2 for a in names})
        self.assertTrue(all(r['phase']=='warmup' for r in rows[:8]))
        self.assertTrue(all(r['phase']=='measurement' for r in rows[8:]))
        positions=Counter();identities=set()
        for start in range(8,136,4):
            group=rows[start:start+4]
            self.assertEqual({r['arm'] for r in group},names)
            self.assertEqual(len({(r['block'],r['snr'],r['repeat']) for r in group}),1)
            for position,row in enumerate(group):
                key=row['block'],row['snr'],row['repeat'],row['arm']
                self.assertNotIn(key,identities);identities.add(key)
                positions[row['snr'],row['arm'],position]+=1
        self.assertEqual(len(identities),128)
        self.assertEqual(set(positions.values()),{4})
        self.assertEqual(len(positions),32)

    def test_original_two_arm_plan_preserves_68_calls(self):
        rows=order();self.assertEqual(len(rows),68)
        self.assertEqual(Counter(r['phase'] for r in rows),dict(warmup=4,measurement=64))
        self.assertEqual({r['arm'] for r in rows},{'DENSE','INTEGER'})

    def test_soft_score_roundoff_never_allows_changed_error_count(self):
        expected=dict(FER=0,coded_bit_errors=0,bit_NLL=.1,decode_ok=True)
        compare_scores(dict(expected,bit_NLL=.10000001),expected,True)
        with self.assertRaises(ValueError):compare_scores(dict(expected,FER=1),expected,True)
        with self.assertRaises(AssertionError):compare_scores(dict(expected,bit_NLL=.2),expected,True)


if __name__=='__main__':unittest.main()
