"""Three accounted CPU N1024 engineering checks; no timing or development claim."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import numpy as np,json,tempfile,hashlib,sys
from afdm_sp_joint_unrolled.supplement_data import SupplementData
from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver
from afdm_sp_joint_unrolled.supplement_feedback import CodeFeedback
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.supplement_baseline_run import terminal_snapshot
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
P=Path('.mission/20260909_09-01-15-afdm-comprehensive-supplement');out=P/'evidence/local-feedback-interface-v1';out.mkdir()
reservation=json.loads((P/'evidence/local-feedback-checks-reservation-v1.json').read_text());assert reservation['calls_reserved']==dict(F=3,T=0,E=0)
modules={n:Path(m.__file__) for n,m in sys.modules.copy().items() if n.startswith('afdm_sp_joint_unrolled.') and getattr(m,'__file__',None) and m.__file__.endswith('.py')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bindings={n:sha(p) for n,p in modules.items()};rows=[];system=_make_config_a(1024,2.,8,10.,4.)
with tempfile.TemporaryDirectory(dir='/private/tmp') as d:
 code=build_code(cache_dir=d);data=SupplementData(P/'evidence/data-protocol.json',code)
 frame=data.make_frame(system,'engineering',0,8)
 for control in ('legal','zero','fixed_sham'):
  (out/(control+'-started.json')).write_text(json.dumps(dict(control=control,call_type='F',block=0,split='engineering')))
  model=ObservedReceiver.build(P/'evidence/frozen-c2rel-checkpoint.pt',system,code,device='cpu').model
  controller=CodeFeedback(code,checkpoint=0,control=control,sham_seed=18 if control=='fixed_sham' else None)
  result=BaselineReceiver(model,code,'B0-p2-s0.5',system=system).run(frame.observed,audit=True,code_feedback=controller)
  records=result['code_feedback_records'];n=model.cfg.n_outer_iter
  assert sum(r['stage']=='decoder' for r in records)==1
  assert sum(r['stage']=='CE_consume' for r in records)==n-1
  assert sum(r['stage']=='detector_consume' for r in records)==n
  assert len(result['dals'])==n-1 and all(s['moment_source']=='code_feedback.ce' for s in result['dals'])
  assert any(g['stage']=='final_bp' for g in result['graphs'])
  assert result['decoded'].shape==(code['n'],) and result['info_hat'].shape==(code['k'],)
  assert np.isfinite(result['H']).all() and np.isfinite(result['llr']).all()
  if control=='zero':np.testing.assert_array_equal(controller.prior.cpu().numpy(),np.zeros(code['n']))
  terminal=terminal_snapshot(out/(control+'.npz'),frame,result)
  rows.append(dict(control=control,outer_iterations=n,records=records,terminal=terminal,H_sha256=array_hash(result['H']),errors=score_errors(result,frame._truth),baseline_eligible=result['baseline_eligible']))
 assert len({r['H_sha256'] for r in rows})>=2,'legal and controls failed to alter actual CE outputs'
 assert bindings=={n:sha(p) for n,p in modules.items()}
 result=dict(status='passed',full_receiver_checks=3,reservation=reservation,source_sha256=bindings,metadata=frame.metadata,records=rows,scope='CPU N1024 engineering block0 checkpoint0 interface check; not deployment schedule choice, development FER, or remote cost measurement')
 with (out/'summary.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status='passed',checks=3,FER=[r['errors']['FER'] for r in rows],summary_sha256=sha(out/'summary.json'))))
