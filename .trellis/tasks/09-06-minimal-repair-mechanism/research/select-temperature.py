"""Registered D_cal fit selection; validation is descriptive, never used to select."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--s2',type=Path,required=True);args=ap.parse_args();b=args.base
    batch=json.loads((b/'cal-batch.json').read_text())
    assert batch['complete'] and len(batch['runs'])==3 and all(r['exit_code']==0 for r in batch['runs'])
    records=[];raw_hashes={};states=[];prior_seeds=set()
    for rep in (10,11,12):
        folder=b/f'cal-rep{rep}';state=json.loads((folder/'status.json').read_text());states.append(state)
        assert state['complete'] and state['completed_frames']==64 and state['device']=='cuda'
        data=read(folder/'frames.jsonl')
        assert len(data)==64 and [(r['replicate'],r['frame_index']) for r in data]==[(rep,i) for i in range(64)]
        assert all(r['split']=='D_cal' and r['snr']==8 and r['coding']=='LDPC' and set(r['arms'])=={'baseline'} for r in data)
        raw_hashes[str(folder/'frames.jsonl')]=digest(folder/'frames.jsonl');records.extend(data)
        prior_seeds.update(json.loads((folder/'calibration.json').read_text())['seeds'])
    for key in ('source_sha256','checkpoint_sha256','calibration_sha256','ldpc_sha256'):
        assert all(s[key]==states[0][key] for s in states)
    assert len({r['channel_seed'] for r in records})==192
    assert not prior_seeds & {r['channel_seed'] for r in records}
    old=[]
    for p in args.s2.glob('dev-snr*-rep*/frames.jsonl'):old.extend(read(p))
    assert len(old)==576
    for key in ('H','noise','coded'):
        hashes={r['input_hashes'][key] for r in records}
        assert len(hashes)==192 and not hashes & {r['input_hashes'][key] for r in old}
    T=(.25,.5,1.,2.,4.);tables={}
    for part,subset in [('fit',[r for r in records if r['frame_index']<32]),('validation',[r for r in records if r['frame_index']>=32])]:
        table={}
        assert len(subset)==96
        for temperature in T:
            per_frame=[]
            for r in subset:
                events=[e for e in r['arms']['baseline']['soft_feedback'] if e['stage']=='dals_feedback']
                assert [e['outer_iter'] for e in events]==list(range(1,10))
                values=[next(g for g in e['temperature_grid'] if g['temperature']==temperature) for e in events]
                per_frame.append({k:float(np.mean([v[k] for v in values])) for k in ('nll','brier_sum','mean_variance','mean_squared_error')})
            table[str(temperature)]={k:float(np.mean([v[k] for v in per_frame])) for k in per_frame[0]}
        tables[part]=table
    selected=min(T,key=lambda t:(tables['fit'][str(t)]['nll'],abs(math.log(t)),t))
    result=dict(passed=True,split='D_cal',snr=8,selected_temperature=selected,grid=T,
        rule='fit frames equal weight, nine DA-LS iterations equal weight, minimum symbol NLL; ties nearest log(T)=0 then lower T',
        fit_ids=[[r,i] for r in (10,11,12) for i in range(32)],validation_ids=[[r,i] for r in (10,11,12) for i in range(32,64)],
        raw_sha256=raw_hashes,source_sha256=states[0]['source_sha256'],checkpoint_sha256=states[0]['checkpoint_sha256'],
        prior_calibration_sha256=states[0]['calibration_sha256'],ldpc_sha256=states[0]['ldpc_sha256'],
        pairing_and_split_checks=True,tables=tables,scope='offline D_cal scalar fit; validation never used for selection; no closed-loop FER claim')
    out=b/'feedback-calibration.json'
    with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(selected_temperature=selected,tables=tables),indent=2))
if __name__=='__main__':main()
