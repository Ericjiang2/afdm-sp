"""Validate fixed-denominator S2 controls; no uncoded FER or budget claim."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def load(base,name,arms,coding,snr,rep):
    p=base/name;s=json.loads((p/'status.json').read_text());r=read(p/'frames.jsonl')
    assert s['complete'] and s['completed_frames']==64 and s['device']=='cuda'
    assert len(r)==64 and [(x['replicate'],x['frame_index']) for x in r]==[(rep,i) for i in range(64)]
    assert all(x['coding']==coding and x['snr']==snr and x['split']=='D_dev' and set(x['arms'])==set(arms) and all(a['finite'] for a in x['arms'].values()) for x in r)
    return r,s

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);args=ap.parse_args();b=args.base
    main_arms=['baseline','keep','unprotected','oracle_gains','oracle_data','wide_pool']
    report=dict(scope='S2 diagnostic controls; legacy truth-derived nomination count; not equal-budget deployment',conservative={},uncoded={})
    all_records={};states=[]
    for rep in range(3):
        rows,s=load(b,f'conservative-rep{rep}',['baseline','conservative'],'LDPC',8,rep);states.append(s)
        old=read(b/f'dev-snr8-rep{rep}/frames.jsonl')
        for r,o in zip(rows,old):
            assert r['input_hashes']==o['input_hashes']
            assert all(r['arms']['baseline'][k]==o['arms']['baseline'][k] for k in ('raw_errors','info_errors','output_h_sha256','output_x_sha256','sigma2_final'))
            q=r['arms']['conservative'];assert set(q['support']['raw'])<=set(q['support']['final_nomination'])
            assert len(set(q['support']['final_nomination'])-set(q['support']['raw']))<=4
        all_records[rep]=rows
    rows=sum(all_records.values(),[])
    for arm in ('baseline','conservative'):
        report['conservative'][arm]=dict(frames=192,frame_errors=sum(r['arms'][arm]['info_errors']>0 for r in rows),
            info_errors=sum(r['arms'][arm]['info_errors'] for r in rows),per_seed_frame_errors=[sum(r['arms'][arm]['info_errors']>0 for r in all_records[rep]) for rep in range(3)],
            mean_expanded_capacity=float(np.mean([len(r['arms'][arm]['support']['expanded']) for r in rows])))
    report['conservative']['wins']=sum(r['arms']['baseline']['info_errors']>0 and r['arms']['conservative']['info_errors']==0 for r in rows)
    report['conservative']['harms']=sum(r['arms']['baseline']['info_errors']==0 and r['arms']['conservative']['info_errors']>0 for r in rows)
    cases={}
    for kind,predicate in [('win',lambda a,c:a>0 and c==0),('harm',lambda a,c:a==0 and c>0),('uncorrected',lambda a,c:a>0 and c>0)]:
        subset=[r for r in rows if predicate(r['arms']['baseline']['info_errors'],r['arms']['conservative']['info_errors'])]
        cases[kind]=dict(total=len(subset),requested=3,available=min(3,len(subset)),records=subset[:3])
    report['conservative']['cases']=cases
    uncoded={}
    for snr in (15,20):
        rows=[];per_rep={}
        for rep in range(3):
            x,s=load(b,f'uncoded-snr{snr}-rep{rep}',main_arms,'iid_QPSK_uncoded',snr,rep);states.append(s);rows.extend(x);per_rep[rep]=x
            assert all(r['bits_per_frame']==2048 and all(a['info_errors'] is None and a['decode_ok'] is None for a in r['arms'].values()) for r in x)
            for r in x:
                if snr==15:uncoded[(rep,r['frame_index'])]=r
                else:assert all(r['input_hashes'][k]==uncoded[(rep,r['frame_index'])]['input_hashes'][k] for k in ('H','noise','coded','info','pilot'))
                coded=all_records[rep][r['frame_index']]
                assert all(r['input_hashes'][k]==coded['input_hashes'][k] for k in ('H','noise','pilot'))
        table={}
        for arm in main_arms:
            count=sum(r['arms'][arm]['raw_errors'] for r in rows)
            table[arm]=dict(frames=192,bits=192*2048,raw_errors=count,ber=count/(192*2048),
                per_seed_raw_errors=[sum(r['arms'][arm]['raw_errors'] for r in per_rep[rep]) for rep in range(3)])
        report['uncoded'][snr]=table
    for key in ('source_sha256','checkpoint_sha256','ldpc_sha256'):
        assert all(s[key]==states[0][key] for s in states)
    report.update(pairing_passed=True,baseline_replay_exact=True,independent_exogenous_clusters=192,
                  source_sha256=states[0]['source_sha256'],checkpoint_sha256=states[0]['checkpoint_sha256'])
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:({a:v for a,v in x.items() if a!='cases'} if k=='conservative' else x) for k,x in report.items() if k in ('conservative','uncoded')},indent=2))
if __name__=='__main__':main()
