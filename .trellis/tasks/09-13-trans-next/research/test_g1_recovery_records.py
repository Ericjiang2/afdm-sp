"""Small synthetic tests of recovery bookkeeping, not receiver/physics validation."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name('g1-strong-development-recovery-v1.py')
spec = importlib.util.spec_from_file_location('g1_recovery', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RunFixture:
    def __init__(self):
        self.records = []
        self.executed = 0
        self.checked = 0

    def check(self):
        self.checked += 1

    def call(self, kind, identity, fn, score, provenance):
        self.executed += 1
        value = fn()
        return value, dict(identity, kind=kind, scores=score(value), **provenance)


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.run = RunFixture()
        self.identity = dict(block=7, snr=8, split=2, arm='G1_FULL')
        self.key = ('F', 7, 8, 'G1_FULL')
        self.value = {'answer': 42}
        self.provenance = dict(observed_hashes={'y': 'observed'}, physical_record_sha256='physical', scope='new prose')
        self.record = dict(self.identity, kind='F', scores={'score':42}, **self.provenance)
        self.record['scope'] = 'old prose'
        self.entry = dict(self.identity, kind='F', scores={'score':42}, sha256='record')
        self.recovered = {self.key:self.entry}
        self.consumed = set()

    def score(self, value):
        return {'score':value['answer']}

    def no_compute(self):
        raise AssertionError('completed computation must never be invoked')

    def invoke(self, fn=None):
        return module.call_with_reuse(self.run,self.recovered,self.consumed,'F',self.identity,
            fn or self.no_compute,self.score,self.provenance,lambda entry:(self.record,self.value))

    def test_committed_identity_reuses_record_without_computation(self):
        value, record = self.invoke()
        self.assertIs(value,self.value)
        self.assertIs(record,self.record)
        self.assertEqual(self.run.executed,0)
        self.assertEqual(self.run.checked,1)
        self.assertEqual(self.run.records,[self.entry])
        self.assertEqual(self.consumed,{self.key})

    def test_missing_identity_executes_once(self):
        self.recovered.clear()
        self.assertEqual(self.invoke(lambda:{'answer':42})[0],self.value)
        self.assertEqual(self.run.executed,1)
        self.assertEqual(self.consumed,set())

    def test_repeated_identity_rejected(self):
        self.invoke()
        with self.assertRaisesRegex(ValueError,'twice'):self.invoke()
        self.assertEqual(self.run.executed,0)
        self.assertEqual(len(self.run.records),1)

    def test_operational_provenance_changes_rejected(self):
        for key in ('observed_hashes','physical_record_sha256'):
            with self.subTest(key=key):
                original=copy.deepcopy(self.record[key])
                self.record[key]='different'
                with self.assertRaisesRegex(ValueError,'provenance'):self.invoke()
                self.record[key]=original
        self.assertEqual(self.run.executed,0)
        self.assertFalse(self.consumed)

    def test_identity_changes_rejected(self):
        for key in ('kind','block','snr','split','arm'):
            with self.subTest(key=key):
                original=self.record[key];self.record[key]='different'
                with self.assertRaisesRegex(ValueError,'identity'):self.invoke()
                self.record[key]=original
        self.assertFalse(self.run.records)

    def test_stale_scores_rejected(self):
        self.value['answer']=41
        with self.assertRaisesRegex(ValueError,'scores'):self.invoke()
        self.assertEqual(self.run.executed,0)
        self.assertFalse(self.run.records)

    def test_loader_failure_never_runs_missing_path(self):
        def reject(entry):raise ValueError('corrupt raw hash')
        with self.assertRaisesRegex(ValueError,'corrupt'):
            module.call_with_reuse(self.run,self.recovered,self.consumed,'F',self.identity,
                self.no_compute,self.score,self.provenance,reject)
        self.assertEqual(self.run.executed,0)


if __name__ == '__main__':
    unittest.main()
