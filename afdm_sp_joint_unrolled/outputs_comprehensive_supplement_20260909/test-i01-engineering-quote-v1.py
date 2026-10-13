"""Mocked guard contracts only; no GPU or receiver execution evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import time
import json

spec=importlib.util.spec_from_file_location('quote',Path(__file__).with_name('run-i01-engineering-quote-v1.py'))
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)


class QuoteGuardTests(unittest.TestCase):
    def contract(self):
        value=dict(deadline_unix=time.time()+100,external_timeout_seconds=120,
            calls_reserved={'F':72,'T':0,'E':0},max_output_bytes=72*32*1024**2+q.FAILURE_RESERVE)
        value['config_sha256']=q.canonical_hash(value)
        return value

    def test_canonical_binding_and_derived_exclusions(self):
        c=self.contract();q.validate_limits(c,time.time())
        c['reservation_path']='derived';c['ledger']='derived'
        self.assertEqual(q.canonical_hash(c),c['config_sha256'])
        c['deadline_unix']+=1
        with self.assertRaisesRegex(ValueError,'canonical'):q.validate_limits(c,time.time())

    def test_time_budget_and_output_boundaries(self):
        for key,value in [('deadline_unix',float('inf')),('external_timeout_seconds',10),
                          ('max_output_bytes',1),('calls_reserved',{'F':73,'T':0,'E':0})]:
            c=self.contract();c[key]=value
            if key=='deadline_unix':
                with self.assertRaises(ValueError):q.canonical_hash(c)
                continue
            c['config_sha256']=q.canonical_hash(c)
            with self.assertRaises(ValueError):q.validate_limits(c,time.time())
        self.assertTrue(q.timeout_argv_valid(['timeout','--signal=TERM','--kill-after=15s','120s','python'],120))
        self.assertFalse(q.timeout_argv_valid(['python'],120))
        self.assertFalse(q.timeout_argv_valid(['timeout','--signal=TERM','--kill-after=15s','121s'],120))

    def test_actual_device_uuid_and_single_visibility(self):
        with patch.object(q.torch.cuda,'device_count',return_value=1), \
             patch.object(q.torch.cuda,'get_device_properties',return_value=SimpleNamespace(uuid='GPU-mock')):
            q.verify_device('GPU-mock','cuda:0')
            with self.assertRaisesRegex(ValueError,'UUID'):q.verify_device('GPU-other','cuda:0')
        with patch.object(q.torch.cuda,'device_count',return_value=2):
            with self.assertRaisesRegex(ValueError,'one visible'):q.verify_device('GPU-mock','cuda:0')

    def test_preflight_failure_is_immutable_and_no_gpu_work(self):
        with tempfile.TemporaryDirectory() as directory:
            c=self.contract();c['out']=directory;c['config_sha256']=q.canonical_hash(c)
            with patch.object(q,'check_external_timeout',side_effect=ValueError('missing timeout')), \
                 patch.object(q.torch.cuda,'is_available') as gpu:
                with self.assertRaisesRegex(ValueError,'missing timeout'):q.execute(c)
                gpu.assert_not_called()
            failure=json.loads((Path(directory)/'failure.json').read_text())
            self.assertEqual(failure['attempted_F'],0);self.assertEqual(failure['status'],'failed')
            with self.assertRaisesRegex(ValueError,'already attempted'):q.execute(c)


if __name__=='__main__':unittest.main()
