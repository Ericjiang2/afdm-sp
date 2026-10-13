"""Validate recorded REP engineering evidence; no receiver execution."""
import hashlib,json,tarfile
from pathlib import Path
E=Path(__file__).resolve().parent
names=['repwire-1788686663','repwirefix-1788686809','repwirejson-1788686884','repwiresets-1788686980']
archives={}
for name in names:
 p=E/(name+'-runtime.tar.gz')
 with tarfile.open(p) as t:
  files={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
 archives[name]=files
latest=archives[names[-1]]
queue=json.loads(latest['queue-status.json'])
assert queue['complete'] and all(r['exit_code']==0 for r in queue['runs'])
frames={n:json.loads(latest[n+'/frames.jsonl'].splitlines()[0]) for n in ['on','off','det_on','det_off']}
primary=['output_h_sha256','output_x_sha256','sigma2_final','raw_errors','info_errors','decode_ok','decoded_bits_sha256']
soft=['final_bp_mu_sha256','final_bp_var_sha256','final_llr_sha256']
report={'scope':'one fixed Dcal997 frame, A0/A2; engineering only','arms':{},'attempts':[]}
for name in names:
 q=json.loads(archives[name]['queue-status.json'])
 report['attempts'].append(dict(name=name,archive_sha256=hashlib.sha256((E/(name+'-runtime.tar.gz')).read_bytes()).hexdigest(),
   exits={r['name']:r['exit_code'] for r in q['runs']},queue_seconds=q['ended_at']-q['started_at'],
   process_seconds=sum(r['ended_at']-r['started_at'] for r in q['runs']),peak_gpu_mib=q['peak_gpu_mib']))
for n,f in frames.items():
 assert f['input_hashes']==frames['on']['input_hashes']
 assert f['active_cap']==40 and f['receiver_extension']==0
 for a in ('a0','baseline'):
  assert max(x['unique_count'] for x in f['arms'][a]['capacity_trace'] if x['stage']!='temporary')<=40
for a in ('a0','baseline'):
 x=frames['on']['arms'][a]; rep=x['representation']
 assert [(g['stage'],g['outer_iter']) for g in rep['graphs']]==[('outer_bp',i) for i in range(10)]+[('final_bp',None)]
 for g in rep['graphs']:
  assert g['edges']==sum(g['row_degrees'])==sum(g['column_degrees'])
  assert g['dtype']=='torch.complex128' and g['operator']=='>='
  assert g['discarded_squared_frobenius']>=0
 assert rep['graphs'][-1]['H_hash']==frames['det_on']['arms'][a]['representation']['graphs'][-1]['H_hash']
 assert rep['error']['dense_reference']['rank']==40
 assert rep['error']['dense_reference']['projection_difference_norm']<1e-10
 assert all(frames['on']['arms'][a][k]==frames['off']['arms'][a][k] for k in primary)
 assert all(frames['det_on']['arms'][a][k]==frames['det_off']['arms'][a][k] for k in primary+soft)
 original=json.loads(archives[names[0]]['off/frames.jsonl'].splitlines()[0])
 assert all(original['arms'][a][k]==frames['off']['arms'][a][k] for k in primary)
 report['arms'][a]=dict(ordinary_primary_exact=True,isolated_deterministic_all_exact=True,
  ordinary_soft_equal={k:frames['on']['arms'][a][k]==frames['off']['arms'][a][k] for k in soft},
  representation=rep,receiver_seconds=x['receiver_seconds'],info_errors=x['info_errors'],
  support_counts=dict(raw=len(x['support']['raw']),final=len(x['support']['expanded']),
    proposal_stages=[dict(stage=e['stage'],round=e.get('round'),
      counts={k:len(e[k]) for k in ('support','candidate_ids','selected_ids','protected_ids','pruned_ids') if k in e})
      for e in rep['proposal_events']],temporary=[c for c in x['capacity_trace'] if c['stage']=='temporary']))
report['truth']=frames['on']['representation_truth']
report['input_hashes']=frames['on']['input_hashes']
report['limitations']=['ordinary final BP soft hashes vary; deterministic reference is isolated and not production',
 'dense generator LS independent of Torch implementation, not independent physical model',
 'zero graph diagnostic contract does not verify terminal soft/LDPC handling of a zero graph',
 'all failed attempts retained; instrumented parallel runtime is not deployment latency']
(E/'repwire-runtime-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'validated':True,'attempts':report['attempts'],'E_repr':{a:v['representation']['error']['E_repr'] for a,v in report['arms'].items()}},indent=2))
