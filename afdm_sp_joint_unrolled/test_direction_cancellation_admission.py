"""Admission evidence contracts use fixtures, not performance results."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from afdm_sp_joint_unrolled.direction_run import validate_cancellation_admission

class AdmissionTests(unittest.TestCase):
 def test_missing_gate_rejects_design(self):
  with self.assertRaises(ValueError):validate_cancellation_admission(None,None,None,None,None,['cancel-scalar'])
 def test_evidence_binding_allowed_modes_and_resources(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)
   def save(name,x):
    f=p/name;f.write_text(json.dumps(x));return f
   def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
   reg=save('registry.json',{});protocol=save('protocol.json',{})
   limits=dict(host_seconds=100,gpu_seconds=100,cpu_core_seconds=400)
   ledger=save('ledger.json',dict(limits=limits,completed=[],reservations=[]))
   complete=save('complete.json',dict(status='complete',calls_attempted=20,calls_completed=20,source_sha256={'code':'hash'}))
   d=dict(status='approved_for_design',registry_sha256=sha(reg),protocol_sha256=sha(protocol),source_sha256={'code':'hash'},allowed_modes=['scalar'],engineering_complete=dict(path=str(complete),sha256=sha(complete)),required_remaining_resources=dict(host_seconds=20,gpu_seconds=20,cpu_core_seconds=80))
   f=save('admission.json',d)
   with patch('afdm_sp_joint_unrolled.direction_run.source_manifest',return_value={'code':'hash'}):
    self.assertEqual(validate_cancellation_admission(f,sha(f),reg,protocol,ledger,['cancel-scalar'])['allowed_modes'],['scalar'])
    with self.assertRaises(ValueError):validate_cancellation_admission(f,sha(f),reg,protocol,ledger,['cancel-lowrank'])
    complete.write_text('{}')
    with self.assertRaises(ValueError):validate_cancellation_admission(f,sha(f),reg,protocol,ledger,['cancel-scalar'])
    with self.assertRaises(ValueError):validate_cancellation_admission(f,'0'*64,reg,protocol,ledger,['cancel-scalar'])
