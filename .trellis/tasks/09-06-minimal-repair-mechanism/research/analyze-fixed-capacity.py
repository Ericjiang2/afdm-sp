"""Engineering and paired errors for frozen-capacity validation/development."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--s2',type=Path);ap.add_argument('--mode',choices=['validation','dev'],required=True);args=ap.parse_args();b=args.base;mode=args.mode
    cal=json.loads((b/'fixed-feedback-calibration.json').read_text());assert cal['passed'];cap=cal['active_cap'];T=cal['selected_temperature']
    chash=hashlib.sha256((b/'fixed-feedback-calibration.json').read_bytes()).hexdigest()
    q=json.loads((b/f'capacity-{mode}-batch.json').read_text());assert q['complete'] and len(q['runs'])==3 and all(x['exit_code']==0 for x in q['runs'])
    reps=(20,21,22) if mode=='validation' else (0,1,2);start=16 if mode=='validation' else 0;n=16 if mode=='validation' else 64
    arms=['baseline','covariance'] if T==1 else ['baseline','temperature_mean','covariance'];all_rows=[];by_rep={};states=[];hashes={}
    for rep in reps:
        p=b/f'capacity-{mode}-rep{rep}';s=json.loads((p/'status.json').read_text());states.append(s)
        assert s['complete'] and s['completed_frames']==n and s['device']=='cuda' and s['config']['active_cap']==cap and s['feedback_calibration_sha256']==chash and s['calibration_sha256']==cal['prior_calibration_sha256']
        rows=read(p/'frames.jsonl');assert len(rows)==n and [(r['replicate'],r['frame_index']) for r in rows]==[(rep,i) for i in range(start,start+n)]
        for r in rows:
            assert set(r['arms'])==set(arms) and r['capacity_source']=='registered_fixed_capacity' and r['active_cap']==cap and r['nomination_cap']==cap//5
            assert r['split']==('D_cal' if mode=='validation' else 'D_dev') and r['snr']==8 and r['coding']=='LDPC'
            for name,a in r['arms'].items():
                assert a['finite'] and len(a['soft_feedback'])==18 and len(a['support']['expanded'])<=cap and len(a['support']['final_nomination'])<=cap//5
                assert a['support']==r['arms']['baseline']['support'] and a['dals_temperature']==(1 if name=='baseline' else T)
        if mode=='dev':
            old=read((args.s2 or b.parent/'s2_20260906')/f'dev-snr8-rep{rep}/frames.jsonl')
            assert len(old)==n and all(r['input_hashes']==o['input_hashes'] for r,o in zip(rows,old))
        all_rows.extend(rows);by_rep[rep]=rows;hashes[str(p/'frames.jsonl')]=hashlib.sha256((p/'frames.jsonl').read_bytes()).hexdigest()
    for key in ('source_sha256','checkpoint_sha256','ldpc_sha256'):
        assert all(s[key]==states[0][key] for s in states)
    table={};cases={}
    for arm in arms:
        entries=[r['arms'][arm] for r in all_rows]
        events=[e for a in entries for e in a['soft_feedback'] if e['stage']=='dals_feedback']
        actual=[next(g for g in e['temperature_grid'] if g['temperature']==1) for e in events]
        table[arm]=dict(frames=len(entries),frame_errors=sum(a['info_errors']>0 for a in entries),per_seed_frame_errors=[sum(r['arms'][arm]['info_errors']>0 for r in by_rep[rep]) for rep in reps],raw_errors=sum(a['raw_errors'] for a in entries),info_errors=sum(a['info_errors'] for a in entries),mean_nmse=float(np.mean([a['nmse'] for a in entries])),mean_active=float(np.mean([len(a['support']['expanded']) for a in entries])),mean_dals_nll=float(np.mean([g['nll'] for g in actual])),concurrent_seconds=float(np.mean([a['standalone_seconds_estimate'] for a in entries])),wins=sum(r['arms']['baseline']['info_errors']>0 and r['arms'][arm]['info_errors']==0 for r in all_rows),harms=sum(r['arms']['baseline']['info_errors']==0 and r['arms'][arm]['info_errors']>0 for r in all_rows))
        for name,predicate in [('win',lambda a,c:a>0 and c==0),('harm',lambda a,c:a==0 and c>0),('uncorrected',lambda a,c:a>0 and c>0)]:
            subset=[r for r in all_rows if predicate(r['arms']['baseline']['info_errors'],r['arms'][arm]['info_errors'])]
            cases[f'{arm}/{name}']=dict(total=len(subset),requested=3,records=subset[:3])
    result=dict(engineering_passed=True,mode=mode,active_cap=cap,nomination_cap=cap//5,temperature=T,table=table,cases=cases,raw_sha256=hashes,calibration_sha256=chash,scope='conservative fixed-capacity exploratory adaptation; not G1/G2, not a strongest baseline')
    with (b/f'capacity-{mode}-report.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(mode=mode,active_cap=cap,temperature=T,table=table),indent=2))
if __name__=='__main__':main()
