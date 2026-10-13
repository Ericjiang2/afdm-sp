"""Two accounted CPU N1024 engineering checks; no timing or development claim."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import numpy as np,json,tempfile,hashlib,sys,signal
signal.signal(signal.SIGALRM,lambda *args: (_ for _ in ()).throw(TimeoutError('600 second engineering cap')))
signal.alarm(600)
from afdm_sp_joint_unrolled.supplement_data import SupplementData
from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
from afdm_sp_joint_unrolled.direction_receiver import ObservedReceiver
from afdm_sp_joint_unrolled.supplement_feedback_diagnostic import DiagnosticCodeSymbols
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.supplement_baseline_run import terminal_snapshot
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
P=Path('.mission/20260909_09-01-15-afdm-comprehensive-supplement');out=P/'evidence/local-oracle-interface-v1';out.mkdir()
reservation=json.loads((P/'evidence/local-oracle-checks-reservation-v1.json').read_text());assert reservation['calls_reserved']==dict(F=2,T=0,E=0)
modules={n:Path(m.__file__) for n,m in sys.modules.copy().items() if n.startswith('afdm_sp_joint_unrolled.') and getattr(m,'__file__',None) and m.__file__.endswith('.py')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bindings={n:sha(p) for n,p in modules.items()};rows=[];system=_make_config_a(1024,2.,8,10.,4.)
with tempfile.TemporaryDirectory(dir='/private/tmp') as d:
 code=build_code(cache_dir=d);data=SupplementData(P/'evidence/data-protocol.json',code)
 frame=data.make_frame(system,'engineering',0,8)
 for control in ('I2','I2realloc'):
  (out/(control+'-started.json')).write_text(json.dumps(dict(control=control,call_type='F',block=0,split='engineering')))
  model=ObservedReceiver.build(P/'evidence/frozen-c2rel-checkpoint.pt',system,code,device='cpu').model
  controller=DiagnosticCodeSymbols(code,frame._truth['data'],tag=control,checkpoint=0)
  result=BaselineReceiver(model,code,'B0-p2-s0.5',system=system).run_diagnostic(frame.observed,audit=True,diagnostic_code_symbols=controller)
  records=result['diagnostic_consumption_records'];n=model.cfg.n_outer_iter
  assert controller.consumed==1 and len(records)==1 and records[0]['status']=='consumed'
  assert result['truth_access_level']=='true_symbols_oracle'
  assert sum(s['oracle_mean'] for s in result['dals'])==1
  target=result['dals'][0]
  np.testing.assert_array_equal(target['mu'],frame._truth['data'])
  assert records[0]['A_sha256']==array_hash(target['A'])
  assert any(g['stage']=='final_bp' for g in result['graphs'])
  assert result['decoded'].shape==(code['n'],) and result['info_hat'].shape==(code['k'],)
  assert np.isfinite(result['H']).all() and np.isfinite(result['llr']).all()
  feedback=result['code_feedback_records']
  assert sum(r['stage']=='decoder' for r in feedback)==int(control=='I2realloc')
  if control=='I2realloc':np.testing.assert_array_equal(controller.feedback.prior.cpu().numpy(),np.zeros(code['n']))
  terminal=terminal_snapshot(out/(control+'.npz'),frame,result)
  rows.append(dict(control=control,outer_iterations=n,records=records,terminal=terminal,H_sha256=array_hash(result['H']),errors=score_errors(result,frame._truth),baseline_eligible=result['baseline_eligible']))
 assert bindings=={n:sha(p) for n,p in modules.items()}
 result=dict(status='passed',full_receiver_checks=2,reservation=reservation,source_sha256=bindings,metadata=frame.metadata,records=rows,scope='CPU N1024 engineering block0 checkpoint0 interface check; not deployment schedule choice, development FER, or remote cost measurement')
 with (out/'summary.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status='passed',checks=2,FER=[r['errors']['FER'] for r in rows],summary_sha256=sha(out/'summary.json'))))
