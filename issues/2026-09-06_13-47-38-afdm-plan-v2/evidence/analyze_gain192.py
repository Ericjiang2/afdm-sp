"""Paired fixed-final-support terminal diagnostics, never confirmatory data."""
import hashlib,json,tarfile
from pathlib import Path
import numpy as np
E=Path(__file__).resolve().parent
reference=json.loads((E/'gain192-reference.json').read_text())
old={(r['replicate'],r['frame_index']):r for r in reference['frames']}
rows=[];costs=[];packet_refs=[]
for name,jobs in [('gainpilot-1788687500',['first']),('gainrest-1788687670',['part0','part1','part2'])]:
 p=E/(name+'-runtime.tar.gz')
 with tarfile.open(p) as t:
  raw={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
 q=json.loads(raw['queue-status.json']);packet=json.loads(raw['packet.json'])
 assert q['complete'] and all(r['exit_code']==0 for r in q['runs'])
 assert packet['reference_sha256']==hashlib.sha256((E/'gain192-reference.json').read_bytes()).hexdigest()
 for j in jobs:
  status=json.loads(raw[j+'/status.json']);cells=[json.loads(x) for x in raw[j+'/frames.jsonl'].splitlines()]
  assert status['complete'] and status['completed']==len(cells);rows+=cells
 costs.append(dict(name=name,queue_seconds=q['ended_at']-q['started_at'],process_seconds=sum(r['ended_at']-r['started_at'] for r in q['runs']),peak_gpu_mib=q['peak_gpu_mib'],archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 packet_refs.append(dict(name=name,source_hashes=packet['source_hashes']))
rows.sort(key=lambda r:(r['replicate'],r['frame_index']))
assert len(rows)==192 and [(r['replicate'],r['frame_index']) for r in rows]==sorted(old)
for r in rows:
 o=old[r['replicate'],r['frame_index']];a=o['arms']['baseline']
 assert r['input_hashes']==o['input_hashes'] and r['old_info_errors']==a['info_errors']
 assert r['original_sigma']==a['sigma2_final'] and r['original_H_hash']==a['output_h_sha256']
 assert r['final_ids']==[t for t in a['capacity_trace'] if t['stage']=='final'][0]['atom_ids']
 assert np.isfinite(a['nmse']) and a['nmse']>=0 and np.isfinite(r['denominator']) and r['denominator']>0
 assert r['effective_channel_excess_squared']>=-r['excess_numerical_bound']
 assert abs(r['E_repr']+r['effective_channel_excess_squared']/r['denominator']-a['nmse'])<1e-12
 if r['independent_dense']:
  assert r['frame_index']==0 and r['independent_dense']['dense_reference']['rank']==40
  assert r['independent_dense']['dense_reference']['projection_difference_norm']<1e-10
old_bits=np.array([r['old_info_errors'] for r in rows]);new_bits=np.array([r['info_errors'] for r in rows]);delta=(new_bits>0).astype(float)-(old_bits>0)
rng=np.random.default_rng(2026090613);boot=np.zeros(20000)
for k in range(3):boot+=delta[k*64:(k+1)*64][rng.integers(0,64,size=(20000,64))].mean(1)/3
report=dict(scope='192 used fit frames, fixed final S and original sigma, terminal H-only oracle',
 old_error_frames=int((old_bits>0).sum()),new_error_frames=int((new_bits>0).sum()),
 paired_FER_difference=float(delta.mean()),paired_bootstrap95=np.quantile(boot,[.025,.975]).tolist(),
 old_info_errors=int(old_bits.sum()),new_info_errors=int(new_bits.sum()),
 frame_wins=int(((old_bits>0)&(new_bits==0)).sum()),frame_harms=int(((old_bits==0)&(new_bits>0)).sum()),
 streams=[dict(replicate=rep,old_error_frames=int((old_bits[j*64:(j+1)*64]>0).sum()),new_error_frames=int((new_bits[j*64:(j+1)*64]>0).sum())) for j,rep in enumerate((30,31,32))],
 representation=dict(mean=float(np.mean([r['E_repr'] for r in rows])),max=float(max(r['E_repr'] for r in rows)),
  old_nmse_mean=float(np.mean([old[r['replicate'],r['frame_index']]['arms']['baseline']['nmse'] for r in rows])),
  effective_excess_mean=float(np.mean([r['effective_channel_excess_squared']/r['denominator'] for r in rows])),
  worst_cross_and_rounding_allowance=float(max(r['excess_numerical_bound'] for r in rows)),
  injection_precision_max_delta=float(max(abs(r['E_injected']-r['E_repr']) for r in rows))),
 costs=costs,preparation_seconds=sum(r['preparation_seconds'] for r in rows),terminal_seconds=sum(r['terminal_seconds'] for r in rows),
 independent_dense_count=sum(r['independent_dense'] is not None for r in rows),
 pilot_source_change='remainder adds ten-outer validation and labels heuristic rounding allowance; arithmetic unchanged; successful pilot reused',
 limitations=['oracle diagnostic, not achievable method or formal gate','old raw errors are upstream; no cross-stage raw BER comparison',
  'effective channel excess is not raw gain-vector error; original source coordinate-support invariant verified',
  '64eps rounding allowance is heuristic, not certified interval arithmetic','three independent dense references; remaining analytic projection uses verified integer convention'],
 packet_sources=packet_refs,rows=rows)
(E/'gain192-runtime-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('rows','packet_sources')},indent=2))
