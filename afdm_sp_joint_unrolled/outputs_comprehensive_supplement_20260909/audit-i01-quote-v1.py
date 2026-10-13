from pathlib import Path
import sys,json,hashlib,importlib.util
import numpy as np
R=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909');root=R/'source-i01-quote-v1'
sys.path.insert(0,str(root/'source'))
spec=importlib.util.spec_from_file_location('q',root/'run-i01-engineering-quote-v1.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
from afdm_sp_joint_unrolled.supplement_profile import score_errors
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import qpsk_map
out=R/'i01-quote-v1';contract=json.loads((out/'contract.json').read_text());q.check_frozen(contract)
assert (R/'i01-quote-v1.exit').read_text().strip()=='0'
s=json.loads((out/'summary.json').read_text());assert s['status']=='complete' and s['attempted_F']==72 and s['config_sha256']==contract['config_sha256']
seen=set();pairs={};proof=[]
for r in s['records']:
 identity=(r['checkpoint'],r['block'],r['arm'],r['outer_bp_iterations']);assert identity not in seen;seen.add(identity)
 t=r['terminal'];assert q.SHA(t['path'])==t['sha256']
 with np.load(t['path'],allow_pickle=False) as f:a={k:f[k].copy() for k in ['y','pilot','coded','info','info_hat','decoded','x_hard']}
 assert score_errors(a,a)==r['errors']
 for k in ['y','pilot','coded','info']:assert array_hash(a[k])==r['input_hashes'][k]
 assert pairs.setdefault(r['block'],r['input_hashes'])==r['input_hashes']
 b=r['bp_schedule'];assert b['outer_bp_iterations']==r['outer_bp_iterations'] and b['outer_iterations']==10 and b['final_bp_iterations']==20 and b['final_ldpc_maxiter']==50
 assert len(b['calls'])==10 and [c['outer_iter'] for c in b['calls']]==list(range(10))
 for c in b['calls']:assert c['requested_iterations']==r['outer_bp_iterations'] and c['executed_iterations']==(r['outer_bp_iterations'] if c['edges'] else 0)
 oracle=r['diagnostic_consumption_records'];assert len(oracle)==int(r['arm'] in ['I2','I2realloc'])
 if oracle:
  data=np.sqrt(.5)*qpsk_map(a['coded']);assert oracle[0]['supplied_sha256']==array_hash(data)
  assert oracle[0]['consumed_mean_sha256']==array_hash(data.astype(np.complex64))
  assert oracle[0]['status']=='consumed' and oracle[0]['outer_iter']==r['checkpoint']+1
 feedback=r['code_feedback_records'];assert sum(c['stage']=='decoder' for c in feedback)==int(r['arm'] in ['I1','Isham','Irealloc','I2realloc'])
 proof.append(dict(identity=identity,terminal=t,errors=r['errors']))
expected={(cp,b,arm,n) for cp in [1,4] for b in [1,2] for n in [20,18,16,12] for arm in (['I0','I1','Irealloc','Isham','I2','I2realloc'] if n==20 else ['I1','Irealloc','Isham','I2realloc'])}
assert seen==expected
selected={}
for cp in [1,4]:
 mean=lambda arm,n:np.mean([r['seconds'] for r in s['records'] if r['checkpoint']==cp and r['arm']==arm and r['outer_bp_iterations']==n])
 selected[str(cp)]=next((n for n in [20,18,16,12] if all(mean(arm,n)<=mean('I0',20) for arm in ['I1','Irealloc','Isham'])),None)
assert selected==s['selected']=={'1':12,'4':None}
result=dict(status='passed',F_audited=72,audit_F=0,audit_T=0,summary_sha256=q.SHA(out/'summary.json'),contract_sha256=q.SHA(out/'contract.json'),selected=selected,proofs=proof,scope='raw terminal errors, pairing, mapped oracle symbol hash and runtime consumer records; no independent intermediate-A reconstruction or cost confidence claim')
target=R/'i01-quote-raw-audit-v1.json'
with target.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(status='passed',F_audited=72,sha256=q.SHA(target),bytes=target.stat().st_size)))
