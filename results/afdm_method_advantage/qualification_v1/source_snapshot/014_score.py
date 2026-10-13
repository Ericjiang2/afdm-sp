"""Offline saved-output scoring; only this stage opens truth, no receiver calls."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from wrapper import sha256,write_json


def score(run,truthroot,evidence,h,*,output):
    run=Path(run).resolve();truthroot=Path(truthroot).resolve()
    result=json.loads((run/'result.json').read_text())
    manifest=json.loads((run/'manifest.json').read_text())
    if result['status']!='pass' or result['completed_calls']!=result['expected_calls']:raise ValueError('incomplete receiver result')
    if sha256(run/'ledger.jsonl')!=result['ledger_sha256'] or sha256(run/'manifest.json')!=result['manifest_sha256']:raise ValueError('receiver receipt mismatch')
    rows=[json.loads(l) for l in (run/'ledger.jsonl').read_text().splitlines()]
    if len(rows)!=result['completed_calls'] or len({(r['observation_id'],r['policy']) for r in rows})!=len(rows):raise ValueError('receiver rows differ')
    for row in rows:
        p=(run/row['raw_path']).resolve()
        if not p.is_relative_to(run) or sha256(p)!=row['raw_sha256']:raise ValueError('raw hash/path differs')
    # Validate all producer outputs before opening the distinct truth population.
    seal=json.loads((truthroot/'truth_seal.json').read_text())
    if seal['allocation_sha256']!=manifest['registration']['allocation_sha256']:raise ValueError('truth allocation mismatch')
    for path,digest in seal['files'].items():
        p=(truthroot/path).resolve()
        if not p.is_relative_to(truthroot) or sha256(p)!=digest:raise ValueError('truth seal mismatch')
    truthrows=[json.loads(l) for l in (truthroot/'ledger.jsonl').read_text().splitlines()]
    lookup={r['observation_id']:r for r in truthrows}
    if len(lookup)!=len(truthrows):raise ValueError('duplicate truth identity')
    expected={(stem,p) for stem in lookup for p in manifest['registration']['policies']}
    if {(r['observation_id'],r['policy']) for r in rows}!=expected:raise ValueError('whole cohort/policy allocation differs')
    records=[]
    for row in rows:
        tr=lookup[row['observation_id']]
        truth_path=truthroot/tr['truth_path']
        if sha256(truth_path)!=tr['truth_sha256']:raise ValueError('truth raw mismatch')
        truth,_=evidence.load_artifact(truth_path)
        payload,meta=evidence.load_artifact(run/row['raw_path'])
        # Raw metadata producer binds observed source; truth/observed hash joined via ledger below.
        if meta.get('observation_id')!=row['observation_id'] or meta.get('policy')!=row['policy'] or meta.get('input_sha256')!=row['input_sha256']:raise ValueError('raw identity mismatch')
        if row['observation_hash']!=tr['observation_hash'] or row['stream_ids']!=tr['stream_ids'] or truth['observation_hash']!=row['observation_hash'] or truth['stream_ids']!=row['stream_ids']:raise ValueError('observed/truth join mismatch')
        coded=np.asarray(truth['coded'])
        decoded=np.asarray(payload['final_decoder']['decoded'])
        if not np.isin(coded,(0,1)).all() or not np.isin(decoded,(0,1)).all():raise ValueError('nonbinary raw codewords')
        coded=coded.astype(np.uint8);decoded=decoded.astype(np.uint8)
        if coded.shape!=decoded.shape or coded.shape!=(h.shape[1],):raise ValueError('codeword dimensions differ')
        if np.any(h@coded%2):raise ValueError('truth codeword illegal')
        bit_errors=int(np.count_nonzero(decoded!=coded));syndrome=int(np.count_nonzero(h@decoded%2))
        if syndrome!=row['final_syndrome']:raise ValueError('saved syndrome differs')
        acq=payload['acquisition'];covered=None
        if acq is not None:
            candidates=np.asarray(acq['candidates'])
            if not np.isin(candidates,(0,1)).all():raise ValueError('nonbinary candidates')
            candidates=candidates.astype(np.uint8)
            if candidates.ndim!=2 or candidates.shape[1]!=len(coded) or np.any(h@candidates.T%2):raise ValueError('candidate legality/dimensions')
            covered=bool(np.any(np.all(candidates==coded,axis=1)))
        records.append(dict(observation_id=row['observation_id'],policy=row['policy'],bit_errors=bit_errors,error=bool(bit_errors),undetected_error=bool(bit_errors and not syndrome),acquisition_executed=acq is not None,candidate_covered=covered,candidate_selected_correct=not bit_errors if acq is not None else None,receiver_ready_seconds=row['receiver_ready_seconds'],complete_seconds=row['complete_seconds']))
    summary={}
    for policy in manifest['registration']['policies']:
        r=[x for x in records if x['policy']==policy];a=[x for x in r if x['acquisition_executed']]
        timing=np.asarray([x['receiver_ready_seconds'] for x in r])
        summary[policy]=dict(frames=len(r),errors=sum(x['error'] for x in r),undetected_errors=sum(x['undetected_error'] for x in r),bit_errors=sum(x['bit_errors'] for x in r),acquisition_calls=len(a),covered=sum(x['candidate_covered'] for x in a),selected_correct=sum(x['candidate_selected_correct'] for x in a),mean_ready_seconds=float(timing.mean()),p95_ready_seconds=float(np.quantile(timing,.95)))
    report=dict(scope='offline whole-codeword saved-output count; confidence intervals/multiplicity are protocol analysis tasks',result_sha256=sha256(run/'result.json'),truth_seal_sha256=sha256(truthroot/'truth_seal.json'),summary=summary,records=records)
    write_json(output,report)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--truth',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.baseline/'src'))
    import evidence
    cache=a.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    h=np.load(cache)['H'];report=score(a.run,a.truth,evidence,h,output=a.output);print(json.dumps(report['summary'],indent=2))

if __name__=='__main__':main()
