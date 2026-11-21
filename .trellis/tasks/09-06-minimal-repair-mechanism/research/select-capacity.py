"""Predeclared A2-oriented capacity selection and selected-cap temperature fit."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np

def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);args=ap.parse_args();b=args.base
    q=json.loads((b/'capacity-fit-batch.json').read_text());assert q['complete'] and len(q['runs'])==15 and all(x['exit_code']==0 for x in q['runs'])
    tables={};data={};digests={};states={};anchor=None
    for cap in (8,16,24,32,40):
        records=[]
        for rep in (20,21,22):
            p=b/f'capacity-fit{cap}-rep{rep}';s=json.loads((p/'status.json').read_text());states[cap]=s
            assert s['complete'] and s['completed_frames']==16 and s['config']['active_cap']==cap
            rows=read(p/'frames.jsonl');assert len(rows)==16 and [(r['replicate'],r['frame_index']) for r in rows]==[(rep,i) for i in range(16)]
            prior=json.loads((p/'calibration.json').read_text());assert prior['config']['nomination_cap']==cap//5
            for r in rows:
                assert r['split']=='D_cal' and r['capacity_source']=='registered_fixed_capacity' and r['active_cap']==cap and r['nomination_cap']==cap//5 and set(r['arms'])=={'baseline'}
                a=r['arms']['baseline'];assert a['finite'] and len(a['support']['expanded'])<=cap and len(a['support']['raw'])<=cap//5 and len(a['support']['final_nomination'])<=cap//5
                assert r['channel_seed'] not in prior['seeds']
            records.extend(rows);digests[str(p/'frames.jsonl')]=hashlib.sha256((p/'frames.jsonl').read_bytes()).hexdigest()
        if anchor is None:anchor=records
        else:assert all(x['input_hashes']==y['input_hashes'] for x,y in zip(records,anchor))
        data[cap]=records;tables[cap]=dict(frames=48,frame_errors=sum(r['arms']['baseline']['info_errors']>0 for r in records),info_errors=sum(r['arms']['baseline']['info_errors'] for r in records),mean_active=float(np.mean([len(r['arms']['baseline']['support']['expanded']) for r in records])),per_seed_frame_errors=[sum(r['arms']['baseline']['info_errors']>0 for r in records if r['replicate']==rep) for rep in (20,21,22)])
    cap=min(tables,key=lambda c:(tables[c]['frame_errors'],tables[c]['info_errors'],c))
    rows=data[cap];table={}
    for T in (.25,.5,1.,2.,4.):
        values=[]
        for r in rows:
            es=[e for e in r['arms']['baseline']['soft_feedback'] if e['stage']=='dals_feedback'];assert [e['outer_iter'] for e in es]==list(range(1,10))
            values.append(float(np.mean([next(g['nll'] for g in e['temperature_grid'] if g['temperature']==T) for e in es])))
        table[T]=float(np.mean(values))
    T=min(table,key=lambda t:(table[t],abs(math.log(t)),t));s=states[cap]
    result=dict(passed=True,split='D_cal',snr=8,active_cap=cap,nomination_cap=cap//5,selected_temperature=T,
        selection='A2 fit FER, then info errors, then smaller cap; NLL temperature only for selected cap',capacity_table=tables,temperature_nll=table,
        fit_ids=[[rep,i] for rep in (20,21,22) for i in range(16)],validation_ids=[[rep,i] for rep in (20,21,22) for i in range(16,32)],
        raw_sha256=digests,source_sha256=s['source_sha256'],checkpoint_sha256=s['checkpoint_sha256'],ldpc_sha256=s['ldpc_sha256'],prior_calibration_sha256=s['calibration_sha256'],
        scope='conservative fixed-capacity adaptation; not a strongest-baseline claim')
    with (b/'fixed-feedback-calibration.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(active_cap=cap,selected_temperature=T,capacity_table=tables,temperature_nll=table),indent=2))
if __name__=='__main__':main()
