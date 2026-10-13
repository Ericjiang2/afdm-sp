"""Selection policy unit fixtures; not campaign performance evidence."""
import unittest
from afdm_sp_joint_unrolled.direction_select import pareto_and_choice,indexed,paired_interval


class SelectionTests(unittest.TestCase):
    def test_operational_tie_and_unresolved_pareto(self):
        metrics={'a':{'FER':.1,'mean_seconds':3},'b':{'FER':.11,'mean_seconds':2},
                 'c':{'FER':.12,'mean_seconds':1},'d':{'FER':.1,'mean_seconds':4}}
        intervals={('a','b'):{'interval':[-.1,.1]},('a','c'):{'interval':[-.1,.1]}}
        result=pareto_and_choice(metrics,intervals)
        self.assertEqual(result['B_star_operational'],'a')
        self.assertEqual(result['all_Pareto'],['a','b','c'])
        self.assertEqual(result['representatives'],['a','c'])
        self.assertEqual(result['not_eliminated'],['b'])
        self.assertIn('unverified',result['formal_cost_status'])

    def test_equal_fer_prefers_latency_then_lexical(self):
        metrics={a:{'FER':.1,'mean_seconds':t} for a,t in [('b',1),('a',1),('c',2)]}
        result=pareto_and_choice(metrics,{('a','b'):{'interval':[-.1,.1]}})
        self.assertEqual(result['B_star_operational'],'a')

    def test_missing_or_duplicate_frames_rejected(self):
        with self.assertRaises(ValueError):indexed([],{'a':{}},range(192),'design')
        row={'block_id':0,'arm_id':'a'}
        with self.assertRaises(ValueError):indexed([row,row],{'a':{}},range(192),'design')

    def test_cp_interval_direction_and_zero_error_uncertainty(self):
        result=paired_interval([1]*192,[0]*192,28)
        self.assertEqual(result['delta'],1)
        self.assertGreater(result['interval'][0],0)
        zero=paired_interval([0]*192,[0]*192,28)
        self.assertLess(zero['interval'][0],0)
        self.assertGreater(zero['interval'][1],0)
        reverse=paired_interval([0]*192,[1]*192,28)
        self.assertAlmostEqual(reverse['interval'][1],-result['interval'][0])


if __name__=='__main__':unittest.main()
