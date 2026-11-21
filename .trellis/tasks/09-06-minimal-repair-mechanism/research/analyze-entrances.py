"""Paired fixed-denominator S4 analysis, with exact baseline and T=1 replay."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.stats import beta

def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--s2',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();b=args.base
    batch=json.loads((b/'entrances-dev-batch.json').read_text());assert batch['complete'] and len(batch['runs'])==3 and all(r['exit_code']==0 for r in batch['runs'])
    calibration=json.loads((b/'feedback-calibration.json').read_text());assert calibration['passed']
    chash=hashlib.sha256((b/'feedback-calibration.json').read_bytes()).hexdigest()
    records=[];states=[];by_rep={};arms=('baseline','temperature_mean','jsoft','covariance')
    for rep in range(3):
        folder=b/f'entrances-dev-rep{rep}';s=json.loads((folder/'status.json').read_text());states.append(s)
        assert s['complete'] and s['completed_frames']==64 and s['device']=='cuda' and s['feedback_calibration_sha256']==chash
        data=read(folder/'frames.jsonl');old=read(args.s2/f'dev-snr8-rep{rep}/frames.jsonl')
        assert len(data)==len(old)==64 and [(r['replicate'],r['frame_index']) for r in data]==[(rep,i) for i in range(64)]
        for r,o in zip(data,old):
            assert r['split']=='D_dev' and r['snr']==8 and r['coding']=='LDPC' and set(r['arms'])==set(arms)
            assert r['input_hashes']==o['input_hashes'] and all(v['finite'] for v in r['arms'].values())
            assert all(r['arms']['baseline'][k]==o['arms']['baseline'][k] for k in ('raw_errors','info_errors','output_h_sha256','output_x_sha256','sigma2_final'))
            assert all(len(v['soft_feedback'])==18 for v in r['arms'].values())
            if calibration['selected_temperature']==1:
                assert all(r['arms']['baseline'][k]==r['arms']['temperature_mean'][k] for k in ('raw_errors','info_errors','output_h_sha256','output_x_sha256','sigma2_final'))
        records.extend(data);by_rep[rep]=data
    for key in ('source_sha256','checkpoint_sha256','ldpc_sha256','calibration_sha256'):
        assert all(s[key]==states[0][key] for s in states)
    table={};cases={}
    for arm in arms:
        k=sum(r['arms'][arm]['info_errors']>0 for r in records);n=len(records)
        low=0. if k==0 else float(beta.ppf(.025,k,n-k+1));high=1. if k==n else float(beta.ppf(.975,k+1,n-k))
        entries=[r['arms'][arm] for r in records]
        stages={}
        for stage in ('dals_feedback','noise_feedback'):
            events=[e for a in entries for e in a['soft_feedback'] if e['stage']==stage]
            actual=[next(g for g in e['temperature_grid'] if g['temperature']==1) for e in events]
            stages[stage]={key:float(np.mean([g[key] for g in actual])) for key in ('nll','brier_sum','mean_variance','mean_squared_error')}
        table[arm]=dict(frames=n,frame_errors=k,fer=k/n,fer_two_sided95=[low,high],
            per_seed_frame_errors=[sum(r['arms'][arm]['info_errors']>0 for r in by_rep[rep]) for rep in range(3)],
            raw_errors=sum(a['raw_errors'] for a in entries),info_errors=sum(a['info_errors'] for a in entries),
            wins=sum(r['arms']['baseline']['info_errors']>0 and r['arms'][arm]['info_errors']==0 for r in records),
            harms=sum(r['arms']['baseline']['info_errors']==0 and r['arms'][arm]['info_errors']>0 for r in records),
            mean_nmse=float(np.mean([a['nmse'] for a in entries])),
            observed_concurrent_seconds=float(np.mean([a['standalone_seconds_estimate'] for a in entries])),soft=stages)
        for name,predicate in [('win',lambda a,c:a>0 and c==0),('harm',lambda a,c:a==0 and c>0),('uncorrected',lambda a,c:a>0 and c>0)]:
            subset=[r for r in records if predicate(r['arms']['baseline']['info_errors'],r['arms'][arm]['info_errors'])]
            cases[f'{arm}/{name}']=dict(total=len(subset),requested=3,records=subset[:3])
    report=dict(scope='exploratory legacy-capacity S4 comparison, no G1/G2',pairing_passed=True,baseline_exact=True,
        temperature=calibration['selected_temperature'],calibration_sha256=chash,table=table,cases=cases,
        source_sha256=states[0]['source_sha256'],checkpoint_sha256=states[0]['checkpoint_sha256'])
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps(table,indent=2))
if __name__=='__main__':main()
