"""Read-only audit and scoring of the fixed-channel Gaussian development."""
from pathlib import Path
import json
import numpy as np
from score_development import bound,same,sha,lines,ROOT,BASE,TASK
from score_new_runs import need
from decoder_equivalence import same_decoder


def main():
 exp=TASK/'experiments';run=exp/'noncircular_dev_v1';regpath=exp/'noncircular_registration.json';reg=json.loads(regpath.read_text());arms=reg['policies'];ids=reg['observation_ids']
 result=json.loads((run/'result.json').read_text());manifest=json.loads((run/'manifest.json').read_text())
 need(result['status']=='pass' and result['completed_calls']==384,'incomplete campaign')
 need(result['registration_sha256']==manifest['registration_sha256']==sha(regpath),'registration')
 for path,digest in reg['task_sources'].items():need(sha(TASK/path)==digest,'source binding')
 for name,key in [('manifest.json','manifest_sha256'),('ledger.jsonl','ledger_sha256'),('attempts.jsonl','attempts_sha256')]:need(sha(run/name)==result[key],'campaign hash')
 rows=lines(run/'ledger.jsonl');events=lines(run/'attempts.jsonl')
 need(len(rows)==384 and len(events)==768,'call counts')
 schedule=[(s,a) for i,s in enumerate(ids) for a in arms[i%3:]+arms[:i%3]]
 need([(r['observation_id'],r['policy']) for r in rows]==schedule,'registered schedule')
 for i,r in enumerate(rows):
  a,b=events[2*i:2*i+2];need(r['call_index']==i and r['status']=='ok' and a['event']=='started' and b['event']=='finished','event order')
  for key in ('call_index','observation_id','policy','input_sha256'):need(a[key]==b[key]==r[key],'event identity')
  need({k:v for k,v in b.items() if k!='event'}==r,'finish payload')
 pop=ROOT/'results/tf_cstate_prospective_20260923/population_observed';trroot=pop.parent/'population_truth'
 inputs={r['observation_id']:r for r in lines(pop/'ledger.jsonl')};truths={r['observation_id']:r for r in lines(trroot/'ledger.jsonl')}
 for folder,kind in [(pop,'observed'),(trroot,'truth')]:
  seal=json.loads((folder/f'{kind}_seal.json').read_text());need(seal['status']=='pass' and sha(folder/'ledger.jsonl')==seal['files']['ledger.jsonl'],'population ledger')
 cache=BASE/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
 need(sha(cache)==manifest['locked_hashes']['ldpc_cache_sha256'],'LDPC hash')
 with np.load(cache) as z:H,free=z['H'],z['free_cols']
 syn=lambda d:int(np.count_nonzero((H@d['decoded'])%2))
 indexed={(r['observation_id'],r['policy']):r for r in rows};frames=[]
 for stem in ids:
  inp=inputs[stem];tr=truths[stem];need(inp['observation_hash']==tr['observation_hash'] and inp['stream_ids']==tr['stream_ids'],'truth pairing')
  obs=bound(pop/inp['observation_path'],inp['observation_sha256']);need(obs['observation_id']==stem,'input identity')
  truth=bound(trroot/tr['truth_path'],tr['truth_sha256']);coded=np.asarray(truth['coded']);info=np.asarray(truth['info']);need(np.array_equal(coded[free],info) and np.count_nonzero((H@coded)%2)==0,'truth valid')
  payload={};frame=dict(observation_id=stem,input_sha256=inp['observation_sha256'],truth_sha256=tr['truth_sha256'],arms={})
  for arm in arms:
   row=indexed[stem,arm];need(row['input_sha256']==inp['observation_sha256'],'input pairing');identity=dict(observation_id=stem,policy=arm,input_sha256=inp['observation_sha256'])
   raw=bound(run/row['raw_path'],row['raw_sha256'],identity);payload[arm]=raw
   dec=raw['prefix_decoder'];need((raw['scalar_branch'] is not None)==bool(syn(dec)),'CSTATE gate')
   if syn(dec):dec=raw['scalar_branch']['decoder']
   need((raw['siso'] is not None)==bool(syn(dec) and arm!='scalar3')==row['siso_executed'],'SISO gate')
   if raw['siso'] is not None:
    need(np.array_equal(raw['siso']['check_prior'],raw['scalar_branch']['check_prior']),'original prior reused');dec=raw['siso']['decoder']
   need(same(dec,raw['final_decoder']),'selected decoder');final=np.asarray(dec['decoded']);need(final.shape==(2048,) and np.isin(final,(0,1)).all(),'bits')
   syndrome=syn(dec);need(syndrome==row['final_syndrome'],'syndrome recount')
   frame['arms'][arm]=dict(coded_errors=int(np.count_nonzero(final!=coded)),info_errors=int(np.count_nonzero(final[free]!=info)),syndrome=syndrome,ready_seconds=row['receiver_ready_seconds'],complete_seconds=row['complete_seconds'],raw_sha256=row['raw_sha256'],siso_executed=row['siso_executed'],pseudo_ratio=raw['siso']['detector']['prior_pseudo_l2_ratio'] if raw['siso'] is not None else None)
  for arm in arms[1:]:
   need(same(payload['scalar3']['prefix_arrays'],payload[arm]['prefix_arrays']),'prefix parity')
   b=payload['scalar3']['scalar_branch'];c=payload[arm]['scalar_branch']
   if b is not None:
    need(same_decoder(b['decoder'],c['decoder']),'scalar decoder parity')
    need(same(b['check_prior'],c['check_prior']),'common check prior')
    for key in ('paths','gains'):need(same(b['geometry_result'][key],c['geometry_result'][key]),'geometry parity')
   if syn(payload['scalar3']['final_decoder'])==0:need(same_decoder(payload['scalar3']['final_decoder'],payload[arm]['final_decoder']),'guard preserved')
  frames.append(frame)
 summaries={a:dict(n=128,coded_frame_errors=sum(f['arms'][a]['coded_errors']>0 for f in frames),information_frame_errors=sum(f['arms'][a]['info_errors']>0 for f in frames),undetected_errors=sum(f['arms'][a]['coded_errors']>0 and f['arms'][a]['syndrome']==0 for f in frames),siso_calls=sum(f['arms'][a]['siso_executed'] for f in frames),mean_ready_seconds=float(np.mean([f['arms'][a]['ready_seconds'] for f in frames])),mean_complete_seconds=float(np.mean([f['arms'][a]['complete_seconds'] for f in frames]))) for a in arms}
 pairs=[]
 for a,b in [('scalar3','proper'),('scalar3','augmented'),('proper','augmented')]:
  pairs.append(dict(reference=a,candidate=b,rescue=[f['observation_id'] for f in frames if f['arms'][a]['coded_errors']>0 and f['arms'][b]['coded_errors']==0],harm=[f['observation_id'] for f in frames if f['arms'][a]['coded_errors']==0 and f['arms'][b]['coded_errors']>0]))
 print(json.dumps(dict(status='pass',scope='128 exposed enriched frames, no population inference',scorer_sha256=sha(Path(__file__)),checks=dict(calls=384,raw_identity=True,gate_checks=True,prefix_geometry_parity=True),summary=summaries,pairs=pairs,frames=frames,manifest_sha256=sha(run/'manifest.json'),ledger_sha256=sha(run/'ledger.jsonl')),indent=2,allow_nan=False))

if __name__=='__main__':main()
