"""Synthetic A-02 E-quote contracts; these tests execute no physical refit."""
import hashlib
import json
from pathlib import Path
import os
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np

from . import supplement_bridge_quote as quote


class BridgeQuoteTests(unittest.TestCase):
    def test_blas_threads_are_fixed_before_first_numerical_import(self):
        source=Path(quote.__file__).read_text()
        prefix,separator,_=source.partition('import numpy as np')
        self.assertTrue(separator)
        previous={name:os.environ.get(name) for name in quote.THREAD_ENV}
        try:
            for name in quote.THREAD_ENV:os.environ[name]='7'
            exec(compile(prefix,quote.__file__,'exec'),{})
            self.assertTrue(all(os.environ[name]=='1' for name in quote.THREAD_ENV))
        finally:
            for name,value in previous.items():
                if value is None:os.environ.pop(name,None)
                else:os.environ[name]=value

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cache=self.root/'cache';self.cache.mkdir()
        self.identity=dict(split='engineering',block_id=0,arm_id='group-p2-s0.5',
                           config_sha256='c'*64)
        self._write_inputs()

    @staticmethod
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_inputs(self,*,summary_status='complete',register=True):
        contract=dict(config_sha256=self.identity['config_sha256'],split='engineering',snr=8)
        (self.cache/'contract.json').write_text(json.dumps(contract))
        np.savez(self.cache/'terminal-000-group-p2-s0.5.npz',y=np.ones(2,complex),
            pilot=np.ones(2,complex),H=np.eye(2,dtype=complex),x_soft=np.zeros(2,complex),
            support=np.array([2]),gains=np.ones(1,complex),sigma2=np.array(.25),
            sigma2_terminal=np.array(.125),info=np.array([1]),coded=np.array([1,0]))
        terminal=self.cache/'terminal-000-group-p2-s0.5.npz'
        frame=dict(self.identity,SNR=8,terminal=dict(sha256=self.digest(terminal),
            fields=['y','pilot','H','x_soft','support','gains','sigma2','info','coded']))
        frame_path=self.cache/'frame-000-group-p2-s0.5.json';frame_path.write_text(json.dumps(frame))
        records=([dict(path='/remote/frame-000-group-p2-s0.5.json',sha256=self.digest(frame_path))]
                 if register else [])
        summary=dict(status=summary_status,exitcode=0,config_sha256=self.identity['config_sha256'],records=records)
        (self.cache/'summary.json').write_text(json.dumps(summary))
        files={name:dict(path=str(self.cache/name),sha256=self.digest(self.cache/name),
                         bytes=(self.cache/name).stat().st_size) for name in quote.FILE_KEYS}
        self.manifest=dict(schema='A02-cached-engineering-inputs-v1',
            status='input_bindings_only_not_execution_admission',files=files,
            cache_identity=self.identity,proposed_calls={'F':0,'T':0,'E':8},
            source_state_scope='cached post-refit state; resource probe only',
            sigma_rule='cached sigma2 times recipe scale',allowed_npz_reads=list(quote.ALLOWED_ARRAYS),
            forbidden_consumers='truth and full receiver forbidden',limits=dict(threads=1,
                per_E_seconds=300,stage_seconds=2700,max_output_bytes=64*1024**2,
                no_automatic_retry=True),remaining_pre_reservation={'F':6,'T':187,'E':125})
        self.manifest_path=self.root/'manifest.json';self.manifest_path.write_text(json.dumps(self.manifest))

    def args(self,name='out',**changes):
        values=dict(input_manifest=self.manifest_path,input_manifest_sha256=self.digest(self.manifest_path),
                    out=self.root/name,deadline_unix=time.time()+60,device='cpu')
        values.update(changes);return SimpleNamespace(**values)

    def execution_patches(self,behavior=None):
        calls=[]
        def constructor(_system,identifier):
            def refit(**kwargs):
                calls.append((identifier,kwargs))
                if behavior is not None:behavior(identifier,len(calls))
                return dict(H=kwargs['H'],gains=kwargs['gains'],
                            diagnostics={'converged':False,'query_count':1})
            return refit
        stack=patch.multiple(quote,_make_config_a=lambda *_:SimpleNamespace(N_total=2),
            BaselineTerminalRefit=constructor,reserve_profile=lambda *_:'/ledger',
            source_manifest=lambda :{'source.py':'a'*64})
        return stack,calls

    def test_manifest_binds_successful_registered_frame_and_all_files(self):
        manifest,resolved,frame=quote.validate_manifest(self.manifest_path,self.digest(self.manifest_path))
        self.assertEqual(set(resolved),set(quote.FILE_KEYS));self.assertEqual(frame['arm_id'],'group-p2-s0.5')
        self.assertEqual(manifest['proposed_calls'],{'F':0,'T':0,'E':8})
        (self.cache/'summary.json').write_text(json.dumps(dict(status='failed')))
        self.manifest['files']['summary.json'].update(
            sha256=self.digest(self.cache/'summary.json'),bytes=(self.cache/'summary.json').stat().st_size)
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            quote.validate_manifest(self.manifest_path,self.digest(self.manifest_path))

    def test_cached_loader_reads_only_whitelist_and_uses_thermal_sigma(self):
        state=quote.load_cached_state(self.cache/'terminal-000-group-p2-s0.5.npz',2)
        self.assertEqual(state['sigma2'],.25)
        self.assertNotIn('sigma2_terminal',state);self.assertNotIn('info',state);self.assertNotIn('coded',state)

    def test_eight_routes_use_sigma2_not_cached_terminal_sigma(self):
        stack,calls=self.execution_patches()
        with stack:
            self.assertEqual(quote.execute(self.args()),0)
        self.assertEqual(len(calls),8)
        self.assertEqual({name for name,_ in calls},{r['id'] for r in quote.quote_recipes()})
        self.assertTrue(all(kwargs['sigma_base']==.25 for _,kwargs in calls))
        summary=json.loads((self.root/'out'/'summary.json').read_text())
        self.assertEqual((summary['calls_attempted'],summary['calls_completed']),(8,8))
        self.assertEqual(summary['calls_reserved'],{'F':0,'T':0,'E':8})
        first=json.loads(Path(summary['records'][0]['path']).read_text())
        self.assertEqual(first['gains_after_real'],[1.]);self.assertEqual(first['gains_after_imag'],[0.])
        self.assertGreaterEqual(first['preparation_seconds'],0)
        self.assertGreaterEqual(summary['records'][0]['output_publication_seconds'],0)

    def test_ordinary_failure_is_charged_once_and_never_retried(self):
        def fail_first(_identifier,index):
            if index==1:raise RuntimeError('synthetic expected failure')
        stack,calls=self.execution_patches(fail_first)
        with stack:
            self.assertEqual(quote.execute(self.args('failed')),1)
        summary=json.loads((self.root/'failed'/'summary.json').read_text())
        self.assertEqual((summary['calls_attempted'],summary['calls_completed']),(8,7))
        self.assertEqual(len(summary['failures']),1);self.assertEqual(len(calls),8)

    def test_interrupt_retains_active_e_identity(self):
        def interrupt(_identifier,index):
            if index==1:raise KeyboardInterrupt()
        stack,_=self.execution_patches(interrupt)
        with stack,self.assertRaises(KeyboardInterrupt):quote.execute(self.args('interrupted'))
        failure=json.loads((self.root/'interrupted'/'batch-failure.json').read_text())
        self.assertEqual((failure['calls_attempted'],failure['calls_completed']),(1,0))
        self.assertEqual(failure['active_attempt']['call_type'],'E')
        self.assertEqual(failure['active_attempt']['attempt'],1)

    def test_request_rejects_expired_or_overlong_deadline_and_unavailable_cuda(self):
        limits=self.manifest['limits']
        for deadline in (time.time()-1,time.time()+limits['stage_seconds']+10,float('inf')):
            with self.subTest(deadline=deadline),self.assertRaises(ValueError):
                quote.validate_request(self.args(deadline_unix=deadline),self.manifest)
        with self.assertRaises(ValueError):
            quote.validate_request(self.args(device='cuda'),self.manifest)

    def test_timer_reset_never_turns_expired_deadline_into_disabled_alarm(self):
        with patch.object(quote.time,'time',return_value=100),self.assertRaises(TimeoutError), \
             patch.object(quote.signal,'setitimer') as timer:
            quote._arm_timer(100,300)
        timer.assert_not_called()


if __name__=='__main__':unittest.main()
