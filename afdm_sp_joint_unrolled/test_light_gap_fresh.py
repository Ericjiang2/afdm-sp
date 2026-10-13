"""Fresh namespace contracts on small fixtures, without campaign data."""
import tempfile
import unittest
import json
from pathlib import Path
import numpy as np
from .bottleneck_pilot import NAMESPACE, generate_exogenous, hashes, pilot_rng
from .e1_ldpc import build_code
from .light_gap_fresh import fresh_namespace, stage_arms, save_fresh_input, require_unused_inputs
from .light_gap_replay import LightRun


class ToySystem:
    N_total = 32
    rho = .5
    _zc_seq = np.ones(32, dtype=complex)

    def generate_channel_matrix(self):
        return np.diag(np.random.randn(32)+1j*np.random.randn(32)), None, {}


class FreshNamespaceTests(unittest.TestCase):
    def test_namespace_only_changes_random_inputs_and_restores_global_rng(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=64, d_v=2, d_c=4, seed=11, cache_dir=tmp)
            before = np.random.get_state()
            raw = generate_exogenous(ToySystem(), code, 2, split=2, namespace=(17,29,43))
            repeat = generate_exogenous(ToySystem(), code, 2, split=2, namespace=(17,29,43))
            other = generate_exogenous(ToySystem(), code, 2, split=2, namespace=(17,29,44))
            after = np.random.get_state()
            np.testing.assert_array_equal(before[1], after[1])
            self.assertEqual(before[2:], after[2:])
            keys = ('H','info','coded','data','pilot','noise')
            self.assertEqual(hashes({k:raw[k] for k in keys}), hashes({k:repeat[k] for k in keys}))
            for key in ('H','info','noise'):
                self.assertFalse(np.array_equal(raw[key], other[key]))
            np.testing.assert_array_equal(raw['pilot'], other['pilot'])
            np.testing.assert_allclose(abs(raw['data'])**2, .5, rtol=0, atol=1e-15)
            np.testing.assert_allclose(abs(raw['pilot'])**2, .5, rtol=0, atol=1e-15)
            np.testing.assert_array_equal(raw['coded'], (code['G'].astype(int)@raw['info'])%2)
            self.assertTrue(all(not raw[k].flags.writeable for k in keys))

    def test_original_stream_is_unchanged_and_invalid_namespace_is_rejected(self):
        expected = np.random.default_rng(np.random.SeedSequence([*NAMESPACE,2,0,1])).random(8)
        np.testing.assert_array_equal(pilot_rng(0,1,split=2).random(8), expected)
        np.testing.assert_array_equal(pilot_rng(0,1,split=2,namespace=NAMESPACE).random(8), expected)
        for namespace in [(1,2), (1,2,True), (1,2,-1), (1,2,2**32), '123']:
            with self.assertRaises(ValueError):
                pilot_rng(0,1,split=2,namespace=namespace)
        with self.assertRaises(ValueError):
            pilot_rng(0,1,split=3,namespace=(17,29,43))

    def test_fresh_repeat_is_engineering_only_and_old_arm_list_is_preserved(self):
        arm = dict(name='MEAN', receiver={}, feedback=dict(retain_messages=True))
        old = dict(arms=[arm])
        self.assertIsNone(fresh_namespace(old))
        self.assertEqual(stage_arms(old,'engineering'), [arm])
        fresh = dict(old, fresh_namespace=[17,29,43], engineering_repeat_mean=True)
        self.assertEqual([a['name'] for a in stage_arms(fresh,'engineering')], ['MEAN','MEAN_REPEAT'])
        self.assertEqual(stage_arms(fresh,'development'), [arm])
        self.assertEqual(fresh['arms'], [arm])
        for bad in [dict(fresh,fresh_namespace=list(NAMESPACE)),dict(fresh,engineering_repeat_mean=False),
                    dict(old,engineering_repeat_mean=True)]:
            with self.assertRaises(ValueError):fresh_namespace(bad)
        with self.assertRaises(ValueError):stage_arms(fresh,'test')

    def test_input_has_its_own_reservation_and_old_collisions_are_not_resampled(self):
        class Guard:
            def check(self):pass
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);code=build_code(n=64,d_v=2,d_c=4,seed=11,cache_dir=root)
            run=LightRun(root/'run','engineering',dict(F=1,seconds=60),8*1024**2,Guard())
            raw,entry=save_fresh_input(run,ToySystem(),code,0,1,(17,29,43),[])
            reserve=json.loads((run.out/'exogenous-000-reserve.json').read_text())
            self.assertEqual(reserve['namespace'],[17,29,43])
            self.assertEqual(run.counts,{'F':0})
            self.assertEqual(entry['hashes']['H'],hashes({'H':raw['H']})['H'])
            with self.assertRaisesRegex(ValueError,'collides'):
                require_unused_inputs(entry['hashes'],[entry])
            collision=LightRun(root/'collision','engineering',dict(F=1,seconds=60),8*1024**2,Guard())
            with self.assertRaisesRegex(ValueError,'collides'):
                save_fresh_input(collision,ToySystem(),code,0,1,(17,29,43),[entry])
            self.assertTrue((collision.out/'exogenous-000-reserve.json').is_file())
            self.assertFalse((collision.out/'exogenous-000.npz').exists())


if __name__ == '__main__':
    unittest.main()
