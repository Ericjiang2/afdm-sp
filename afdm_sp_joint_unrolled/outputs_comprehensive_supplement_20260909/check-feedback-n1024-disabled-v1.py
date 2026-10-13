"""Local CPU regression replay: 2F on one existing engineering block, no new data."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import hashlib,json,types,ast,textwrap,subprocess,tempfile,time
import numpy as np
import torch
from unittest.mock import patch
from afdm_sp_joint_unrolled.test_supplement_feedback import LEGACY_FORWARD
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver,CHECKPOINT_HASH
from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
P=Path('.mission/20260909_09-01-15-afdm-comprehensive-supplement')
L=Path('afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909')
checkpoint=P/'evidence/frozen-c2rel-checkpoint.pt'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(checkpoint)==CHECKPOINT_HASH
old=subprocess.check_output(['git','show','25ba45f:00_Inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/classical_joint_unrolled.py'],text=True)
cls=next(n for n in ast.parse(old).body if isinstance(n,ast.ClassDef) and n.name=='ClassicalJointUnrolled')
forward=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward')
fixture=ast.parse(LEGACY_FORWARD).body[0]
# textwrap.dedent changes only docstring indentation; compare executable AST.
assert ast.dump(ast.Module(body=fixture.body[1:],type_ignores=[]))==ast.dump(ast.Module(body=forward.body[1:],type_ignores=[])), 'frozen executable body differs from commit'
assert ast.dump(fixture.args)==ast.dump(forward.args)
LEGACY_FORWARD=ast.unparse(forward)
row=json.loads((L/'baseline-smoke-v1/frame-000-B0-p3-s1.json').read_text());raw=L/'baseline-smoke-v1/terminal-000-B0-p3-s1.npz'
assert sha(raw)==row['terminal']['sha256']
with np.load(raw,allow_pickle=False) as z:
 observed={k:z[k].copy() for k in ('y','pilot','constellation')};observed['sigma2']=float(z['sigma2_thermal'])
# Do not load info/coded/true H. Same observed arrays go to both replays.
system=_make_config_a(1024,2.,8,10.,4.);torch.set_num_threads(1)
outputs=[];controller=None
with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
 code=build_code(cache_dir=directory)
 for disabled in (False,True):
  receiver=ObservedReceiver.build(checkpoint,system,code,device='cpu');model=receiver.model
  if not disabled:
   namespace=dict(model.forward.__func__.__globals__);exec(LEGACY_FORWARD,namespace)
   model.forward=types.MethodType(namespace['forward'],model)
  else:
   controller=CodeFeedback(code,checkpoint=0,enabled=False);f=model.forward
   model.forward=lambda *a,**kw:f(*a,**kw,code_feedback=controller)
  baseline=BaselineReceiver(model,code,'B0-p2-s0.5',system=system)
  with patch('afdm_sp_joint_unrolled.supplement_feedback.decoder_messages',side_effect=AssertionError('disabled decoder invoked')):
   outputs.append(baseline.run(observed,audit=False))
 keys=('H','x_soft','gains','support','sigma2','sigma2_terminal','mu','var','llr','decoded','info_hat','x_hard')
 equal={}
 for k in keys:
  np.testing.assert_array_equal(outputs[0][k],outputs[1][k],err_msg=k)
  equal[k]=array_hash(np.asarray(outputs[1][k]))
 assert controller.records==[]
 evidence=dict(status='passed',scope='CPU full frozen N1024 direct40 B0-p2-s0.5 disabled feedback regression; two replays of existing engineering block; no new data, GPU timing or FER claim',
   source_reference='25ba45f',checkpoint_sha256=sha(checkpoint),cached_observation_sha256=sha(raw),equal_arrays=equal,
   feedback_records=controller.records,source_sha256={n:sha(Path('afdm_sp_joint_unrolled')/n) for n in ('classical_joint_unrolled.py','mp_detect_bp_torch.py','supplement_feedback.py','e1_ldpc.py')})
 with (P/'evidence/message-disabled-n1024-v1.json').open('x') as h:json.dump(evidence,h,indent=2)
 print(json.dumps(evidence))
