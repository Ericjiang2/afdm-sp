"""Admission fixtures test authority/provenance, never scientific performance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from afdm_sp_joint_unrolled import direction_run as runner


class PhysicalAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source={'direction_physical.py':'numerical','direction_run.py':'new'}
        self.arms=['m-group','m-param-budget','m-param-reference','m-soft']
        self.protocol=self.save('protocol.json',{})
        self.registry=self.save('algorithm.json',{'arms':self.arms})
        engineering=self.save('engineering.json',dict(status='complete',calls_attempted=16,
            calls_completed=16,source_sha256=dict(self.source,**{'direction_run.py':'old'})))
        audit=self.save('audit.json',dict(exit_code=0,records=18,jobs={
            'physical-engineering-v9':dict(calls=16,complete_sha256=self.sha(engineering)),
            'baseline-v8':dict(calls=1),'baseline-v9':dict(calls=1)},
            same_parent_state_each_block=True,single_terminal_graph_and_H_consumption_verified=True,
            independent_H_assembly_and_fitted_residual_verified=True))
        plan=self.save('preregister.json',dict(campaign_id='fixture',block_start=0,block_stop=192,
            SNR=8,new_arms=self.arms,new_full_calls=768,algorithm_sha256=self.sha(self.registry),
            protocol_sha256=self.sha(self.protocol),engineering_audit_sha256=self.sha(audit),
            resources={'anchor_deadline_seconds':2400}))
        self.state=dict(campaign_id='fixture',protocol_sha256=self.sha(self.protocol),
            calls_caps={'prototype_full':1728},completed=[],reservations=[],
            limits=dict(host_seconds=10000,gpu_seconds=10000,cpu_core_seconds=40000))
        self.ledger=self.save('ledger.json',self.state)
        self.inputs={k:'fixture-'+k for k in ('y','H','info','coded','noise','pilot','data')}
        snapshot=self.root/'snapshot.npz';snapshot.write_bytes(b'fixture bytes, not a real snapshot')
        segments=[]
        for segment in range(2):
            entries=[]
            for block in range(segment*96,(segment+1)*96):
                row=dict(block_id=block,split='design',SNR=8,arm_id='sbl-s0.5',
                    source_sha256={'v4':'fixture'},config_sha256='fixture-config',
                    protocol_sha256=self.sha(self.protocol),failure=None,
                    input_hashes=self.inputs,snapshot=self.ref(snapshot))
                entries.append(self.ref(self.save(f'frame-{block}.json',row)))
            complete=self.save(f'complete-{segment}.json',dict(status='complete',calls_attempted=768,
                calls_completed=768,source_sha256={'v4':'fixture'},config_sha256='fixture-config',
                protocol_sha256=self.sha(self.protocol),record_sha256={e['path']:e['sha256'] for e in entries}))
            segments.append(dict(complete=self.ref(complete),source_sha256={'v4':'fixture'},
                config_sha256='fixture-config',records=entries))
        self.decision=dict(status='approved_for_design',source_sha256=self.source,
            algorithm_sha256=self.sha(self.registry),protocol_sha256=self.sha(self.protocol),
            preregister=self.ref(plan),engineering_audit=self.ref(audit),engineering_complete=self.ref(engineering),
            required_remaining_resources=dict(host_seconds=2400,gpu_seconds=2400,cpu_core_seconds=9600),
            baseline_cache=segments)
        self.addCleanup(patch.stopall)
        patch.object(runner,'source_manifest',return_value=self.source).start()
        patch.object(runner,'PHYSICAL_DEVELOPMENT_SHA256',self.sha(plan)).start()

    def save(self,name,value):
        path=self.root/name;path.write_text(json.dumps(value));return path

    @staticmethod
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

    def ref(self,path):return dict(path=str(path),sha256=self.sha(path))

    def check(self,decision=None,**overrides):
        path=self.save('admission.json',self.decision if decision is None else decision)
        args=dict(path=path,expected_sha=self.sha(path),registry=self.registry,protocol=self.protocol,
            ledger=self.ledger,chosen=self.arms,start=0,stop=192,snr=8,max_calls=768)
        args.update(overrides)
        return runner.validate_physical_admission(**args)

    def test_complete_cache_and_runner_only_source_change_allowed(self):
        _,cache=self.check()
        self.assertEqual(set(cache),set(range(192)))
        runner.validate_physical_pair(SimpleNamespace(metadata={'block':0,'input_hashes':self.inputs}),cache)

    def test_missing_status_hash_and_source_rejected(self):
        for kwargs in ({'path':None},{'expected_sha':'wrong'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.check(**kwargs)
        for key,value in (('status','pending'),('source_sha256',{}),('algorithm_sha256','wrong')):
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.check(dict(self.decision,**{key:value}))

    def test_unregistered_range_snr_arms_budget_rejected(self):
        for kwargs in ({'start':1},{'stop':193},{'snr':9},{'chosen':self.arms[:3]},{'max_calls':769}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.check(**kwargs)

    def test_preregister_and_engineering_hash_rejected(self):
        for key in ('preregister','engineering_audit','engineering_complete'):
            decision=copy.deepcopy(self.decision);decision[key]['sha256']='wrong'
            with self.subTest(key=key),self.assertRaises(ValueError):self.check(decision)

    def test_numerical_source_change_rejected(self):
        changed=dict(self.source,**{'direction_physical.py':'changed'})
        with patch.object(runner,'source_manifest',return_value=changed),self.assertRaisesRegex(ValueError,'numerical source'):
            self.check(dict(self.decision,source_sha256=changed))

    def test_insufficient_calls_or_resources_rejected(self):
        for state in (dict(self.state,calls_caps={'prototype_full':767}),
                      dict(self.state,limits=dict(self.state['limits'],gpu_seconds=2399))):
            self.save('ledger.json',state)
            with self.assertRaises(ValueError):self.check()

    def test_snapshot_tamper_and_incomplete_cache_rejected(self):
        decision=copy.deepcopy(self.decision);decision['baseline_cache'][0]['records'].pop()
        with self.assertRaises(ValueError):self.check(decision)
        (self.root/'snapshot.npz').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'snapshot hash'):self.check()

    def test_input_pair_rejected_before_receiver_call(self):
        _,cache=self.check()
        for inputs in (dict(self.inputs,y='different'),{'y':self.inputs['y']}):
            with self.assertRaisesRegex(ValueError,'input hashes differ'):
                runner.validate_physical_pair(SimpleNamespace(metadata={'block':0,'input_hashes':inputs}),cache)


if __name__=='__main__':unittest.main()
