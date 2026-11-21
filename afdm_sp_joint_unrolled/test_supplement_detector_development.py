"""Synthetic reservation contracts; no detector performance evidence."""
import tempfile
import json
import hashlib
from types import SimpleNamespace
from .supplement_detector_development import validate_development, validate_loaded_development
from .supplement_detectors import catalogue
from .supplement_data import CAMPAIGN_ID
import unittest
from pathlib import Path
from .supplement_detector_development import reserve_development

class ReservationTests(unittest.TestCase):
    def call(self,out,start=0,stop=16,**kwargs):
        p=dict(baseline='fixture-reference',selection_sha256='a'*64,source_sha256='b'*64);p.update(kwargs)
        return reserve_development(out,start=start,stop=stop,**p)

    def test_full_budget_disjoint_and_no_reclaim(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);total=0
            for a in range(0,192,16):total+=self.call(root/str(a),a,a+16)['T']
            self.assertEqual(total,1536)
            with self.assertRaises(ValueError):self.call(root/'retry',0,1)

    def test_source_and_selection_cannot_change_midstream(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.call(root/'first')
            for change in ({'baseline':'changed'},{'source_sha256':'c'*64},{'selection_sha256':'d'*64}):
                with self.assertRaises(ValueError):self.call(root/'next',16,32,**change)

    def test_range_validation(self):
        with tempfile.TemporaryDirectory() as d:
            for a,b in [(0,17),(-1,2),(192,193),(True,2),(4,4)]:
                with self.assertRaises(ValueError):self.call(Path(d)/'bad',a,b)

class AdmissionTests(unittest.TestCase):
    def test_manifest_and_source_batch_bindings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();ids=[r['id'] for r in catalogue()]
            def artifact(name,value):
                p=root/name;p.write_text(json.dumps(value));return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            batch=dict(config_sha256='config',summary_sha256='summary',contract_file_sha256='contract')
            selection=artifact('selection.json',dict(selection=dict(status='development_references_selected',references=['baseline']),batches=[batch]))
            qualification=artifact('qualification.json',dict(stage='qualification',calls_attempted=64,failures=[],qualified_by_detector={i:False for i in ids}))
            caches=[dict(block=b) for b in range(192)]
            manifest=dict(stage='development',campaign_id=CAMPAIGN_ID,selection=selection,baseline='baseline',qualification=qualification,detectors=ids,caches=caches)
            admission=artifact('admission.json',manifest);args=SimpleNamespace(admission=Path(admission['path']))
            v=validate_development(args,caches[16:32],ids)
            self.assertEqual((v['start'],v['stop']),(16,32))
            for wrong in (caches[:17],caches[2:4][::-1],caches[190:]+caches[:1]):
                with self.assertRaises(ValueError):validate_development(args,wrong,ids)
            with self.assertRaises(ValueError):validate_development(args,caches[:1],ids[:1])
            proof=dict(block=16,config_sha256='config',baseline='baseline',split='design',spec={'local_root':str(root)},
                       files={str(root/'summary.json'):'summary',str(root/'contract.json'):'contract'})
            v.update(start=16,stop=17)
            validate_loaded_development([proof],v)
            proof['files'][str(root/'summary.json')]='changed'
            with self.assertRaises(ValueError):validate_loaded_development([proof],v)
            Path(selection['path']).write_text('{}')
            with self.assertRaises(ValueError):validate_development(args,caches[:1],ids)


class OfflineScoreTests(unittest.TestCase):
    def test_actual_arrays_score_and_truth_tamper_rejected(self):
        import numpy as np
        from .supplement_detector_development import offline_score
        from .budgeted_support_diagnostics import array_hash
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'terminal.npz'
            truth=dict(info=np.array([0,1],dtype=np.uint8),coded=np.array([0,1,1,0],dtype=np.uint8))
            np.savez_compressed(path,**truth)
            proof=dict(terminal_path=str(path),files={str(path):hashlib.sha256(path.read_bytes()).hexdigest()},
                       truth_hashes={k:array_hash(v) for k,v in truth.items()})
            result=dict(info_hat=np.array([1,1]),decoded=np.array([0,1,0,0]),x_hard=np.array([.5+.5j,-.5+.5j]))
            score=offline_score(result,proof)
            self.assertEqual(score['FER'],1)
            self.assertEqual(score['coded_bit_errors'],1)
            self.assertEqual(score['decoded_codeword_bit_errors'],1)
            self.assertEqual(score['raw_bit_errors'],1)
            self.assertEqual(score['coded_bits_denominator'],2)
            self.assertEqual(score['raw_bits_denominator'],4)
            proof['truth_hashes']['info']='bad'
            with self.assertRaises(ValueError):offline_score(result,proof)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):offline_score(result,proof)


class DevelopmentExecutionTests(unittest.TestCase):
    def test_development_dispatches_eight_once_and_scores_after_detection(self):
        import numpy as np
        from contextlib import ExitStack
        from unittest.mock import patch
        from . import supplement_detector_run as run
        ids=[r['id'] for r in catalogue()]
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root=Path(directory);admission=root/'admission.json';admission.write_text('{}')
            args=SimpleNamespace(stage='development',device='cuda',admission=admission,
                deadline_unix=run.time.time()+60,max_terminal_calls=8,max_output_bytes=64*1024**2,
                out=root/'output',caches='[{}]',detectors=json.dumps(ids))
            code={'G':np.eye(2),'H':np.eye(2)}
            data=dict(y_cancelled=np.zeros(2,dtype=complex),H=np.eye(2,dtype=complex),
                      sigma2_terminal=np.array(1.),constellation=run.CONST)
            proof=dict(config_sha256='fixture',block=0,baseline='baseline',files={},
                       code_sha256={k:run.array_hash(v) for k,v in code.items()})
            development=dict(start=0,stop=1,baseline='baseline',selection={'path':'selection','sha256':'a'*64},
                qualification={'path':'qualification','sha256':'b'*64},qualified_by_detector={i:False for i in ids})
            sequence=[]
            def terminal(*arguments,**kwargs):
                self.assertFalse(kwargs['doubled']);self.assertEqual(len(arguments),6)
                sequence.append('detect')
                return dict({k:np.zeros(2) for k in ('mu','var','raw_llr','llr','x_hard','decoded','info_hat')},
                            diagnostics={},terminal_CPU_seconds=0.,decode_ok=False)
            def score(result,origin):
                self.assertEqual(sequence[-1],'detect');sequence.append('score')
                return dict(FER=1,offline_truth_access='synthetic scoring fixture')
            for name,value in [('is_available',True),('current_device',0),('max_memory_allocated',0)]:
                stack.enter_context(patch.object(run.torch.cuda,name,return_value=value))
            for name in ('synchronize','reset_peak_memory_stats','set_per_process_memory_fraction'):
                stack.enter_context(patch.object(run.torch.cuda,name))
            stack.enter_context(patch.object(run.torch,'set_num_threads'))
            stack.enter_context(patch.object(run.torch,'get_num_interop_threads',return_value=1))
            stack.enter_context(patch.object(run,'validate_development',return_value=development))
            stack.enter_context(patch.object(run,'validate_loaded_development'))
            loader=stack.enter_context(patch.object(run,'load_cache',return_value=(data,proof)))
            stack.enter_context(patch.object(run,'build_code',return_value=code))
            reserve=stack.enter_context(patch.object(run,'reserve_development',return_value={'T':8}))
            stack.enter_context(patch.object(run,'reserve_profile',side_effect=AssertionError('wrong engineering ledger')))
            stack.enter_context(patch.object(run,'unchanged'))
            calls=stack.enter_context(patch.object(run,'terminal',side_effect=terminal))
            stack.enter_context(patch.object(run,'offline_score',side_effect=score))
            self.assertEqual(run.execute(args),0)
            self.assertEqual(calls.call_count,8);reserve.assert_called_once()
            loader.assert_called_once_with({},split='design',baseline='baseline')
            self.assertEqual(sequence,['detect','score']*8)
            summary=json.loads((args.out/'summary.json').read_text())
            self.assertEqual(summary['calls_attempted'],8)
            self.assertTrue(all(r['engineering_qualified'] is False for r in summary['records']))

if __name__=='__main__':unittest.main()
