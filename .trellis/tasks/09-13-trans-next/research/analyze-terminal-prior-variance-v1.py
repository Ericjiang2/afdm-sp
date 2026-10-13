from pathlib import Path
import hashlib,json,statistics
m=Path('.mission/20260913_00-48-38-afdm-trans-next');e=m/'evidence/exact-harvest-v1';r=Path('.trellis/tasks/09-13-trans-next/research');tag='terminal-prior-variance-v1'
path=e/'runs'/tag/'diagnostic/summary.json';s=json.loads(path.read_text());oldpath=e/'runs/strong-terminal-oracles-v1/diagnostic/summary.json';old=json.loads(oldpath.read_text());end=json.loads((e/'evidence'/(tag+'-exit.json')).read_text());auditpath=e/'evidence'/(tag+'-raw-audit.json');audit=json.loads(auditpath.read_text());digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert s['status']=='COMPLETE' and s['calls']==dict(T=288,D=288) and end['exit_code']==0 and not end['timed_out']
assert audit['status']=='PASS' and audit['summary_sha256']==digest(path)
rows=list(s['rows'])+[dict(row,arm=row['arm']+'__RETAIN__ORIGINAL') for row in old['rows']]
assert len(rows)==384 and len({(x['block'],x['arm']) for x in rows})==384
cells={};interactions={}
for h in ['EST','SUPPORT_ORACLE','TRUE_H']:
 values={}
 for prior in ['RETAIN','ZERO']:
  for variance in ['ORIGINAL','PHYSICAL']:
   name=h+'__'+prior+'__'+variance;rr=[x for x in rows if x['arm']==name];assert sorted(x['block'] for x in rr)==list(range(32));values[prior,variance]={x['block']:x['scores']['FER'] for x in rr}
   cells[name]=dict(independent_existing_blocks=32,failures=sum(x['scores']['FER'] for x in rr),failed_blocks=[x['block'] for x in rr if x['scores']['FER']],information_bit_errors=sum(x['scores']['info_bit_errors'] for x in rr),mean_bit_NLL=statistics.mean(x['scores']['bit_NLL'] for x in rr),mean_raw_bit_errors=statistics.mean(x['scores']['raw_bit_errors'] for x in rr))
 original=values['RETAIN','ORIGINAL'];interactions[h]={}
 for (prior,variance),scores in values.items():
  interactions[h][prior+'__'+variance]=dict(rescued_vs_same_H_retained_original=[b for b in range(32) if original[b] and not scores[b]],new_failures_vs_same_H_retained_original=[b for b in range(32) if not original[b] and scores[b]])
 interactions[h]['paired_difference_of_differences_FER']=sum(values['RETAIN','PHYSICAL'][b]-values['RETAIN','ORIGINAL'][b]-values['ZERO','PHYSICAL'][b]+values['ZERO','ORIGINAL'][b] for b in range(32))/32
ratios={x['block']:x['original_sigma2_terminal']/x['physical_sigma2'] for x in s['rows']}
result=dict(scope=s['scope'],new_calls=s['calls'],reused_calls=old['calls'],new_raw=576,reused_raw=192,independent_existing_blocks=32,new_independent_blocks=0,wall_seconds=end['wall_seconds'],summary_sha256=digest(path),baseline_summary_sha256=digest(oldpath),raw_audit_sha256=digest(auditpath),raw_audit=audit,source_sha256=s['source_sha256'],contract_sha256=s['contract_sha256'],cells=cells,interactions=interactions,original_to_physical_variance=dict(median=statistics.median(ratios.values()),minimum=min(ratios.values()),maximum=max(ratios.values()),by_block=ratios),rows=rows)
(r/'terminal-prior-variance-results-v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(cells=cells,variance=result['original_to_physical_variance']),ensure_ascii=False,indent=2))
