"""Descriptive ranking analysis from independently audited saved profile rows."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PAIRS={(b,7) for b in (2,4,9,11,14,15,17,18,22,25,26,27,31)}|{(15,8),(25,8)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def classify(rows,name):
    selected=[(r['margins'][name],r['status'][name]) for r in rows]
    fixed=sum(m['fixed_true_preferred'] for m,_ in selected)
    profile=sum(m['profile_true_preferred'] for m,_ in selected)
    rescue=sum((not m['fixed_true_preferred']) and m['profile_true_preferred'] for m,_ in selected)
    worsen=sum(m['fixed_true_preferred'] and (not m['profile_true_preferred']) for m,_ in selected)
    return dict(n=len(selected),valid=sum(s['valid'] for _,s in selected),invalid=sum(not s['valid'] for _,s in selected),
        fixed_H_true_preferred=fixed,profile_true_preferred=profile,
        profile_ranking_rescue=rescue,profile_ranking_worsening=worsen,
        preexisting_true_preferred_both=sum(m['fixed_true_preferred'] and m['profile_true_preferred'] for m,_ in selected),
        fixed_H_margin_mean=sum(m['fixed_H_margin'] for m,_ in selected)/len(selected),
        profile_margin_mean=sum(m['profile_margin'] for m,_ in selected)/len(selected))


def analyze(old_root):
    run=old_root/'runs/codeword-profile-v1'
    summaries={stage:run/stage/'summary.json' for stage in ('engineering','development')}
    receipts={stage:run/'evidence'/f'codeword-profile-{stage}-raw-audit-v1.json'
              for stage in summaries}
    exits={name:old_root/'evidence'/f'codeword-profile-{name}-exit.json'
           for name in ('engineering-v1','engineering-raw-audit-v1',
                        'development-v1','development-raw-audit-v1')}
    rows=[];counts=0;sha_rows={}
    for stage,p in summaries.items():
        s=json.loads(p.read_text());a=json.loads(receipts[stage].read_text())
        if (s['status']!='COMPLETE' or a['status']!='PASS' or
            a['producer_summary_sha256']!=sha(p) or
            a['saved_profile_refits']!=s['actual_profile_refits'] or
            a['new_profile_refits']!=0 or s['new_receiver_CE']!=0 or
            a['contract_sha256']!=s['contract_sha256'] or
            a['script_sha256']!=s['script_sha256']):
            raise ValueError('producer/audit/cost source not jointly closed')
        rows.extend(s['rows']);counts+=s['actual_profile_refits']
        sha_rows[stage]=dict(summary_sha256=sha(p),raw_audit_sha256=sha(receipts[stage]))
    if len(rows)!=15 or {(r['block'],r['snr']) for r in rows}!=PAIRS or counts!=45:
        raise ValueError('15 frozen failure pairs or 45 refits differ')
    if not all(r['status']['true_c']['valid'] and r['status']['reencoded_info_hat']['valid']
               and r['status']['reencoded_info_hat']['information_bit_distance']>0 for r in rows):
        raise ValueError('truth/reencoded legality or information failure differs')
    exit_rows={}
    for name,p in exits.items():
        e=json.loads(p.read_text())
        if e['exit_code']!=0 or e['timed_out']:
            raise ValueError('direction B supervisor exit not successful')
        exit_rows[name]=dict(wall_seconds=e['wall_seconds'],exit_sha256=sha(p))
    ordered=sorted(rows,key=lambda r:(r['snr'],r['block']))
    detailed=[dict(block=r['block'],snr=r['snr'],decoded_raw_valid=r['status']['decoded_raw']['valid'],
        decoded_raw_fixed_H_margin=r['margins']['decoded_raw']['fixed_H_margin'],
        decoded_raw_profile_margin=r['margins']['decoded_raw']['profile_margin'],
        reencoded_fixed_H_margin=r['margins']['reencoded_info_hat']['fixed_H_margin'],
        reencoded_profile_margin=r['margins']['reencoded_info_hat']['profile_margin'],
        saved_t9_A_analysis_relative=r['saved_t9_A_analysis_relative'],
        actual_refits=r['actual_refits']) for r in ordered]
    return dict(schema='codeword-profile-analysis-v1',scope='posthoc descriptive 15 saved ridge failures; true codeword oracle only; no finite legal list tested',
        producer_and_audit_sha256=sha_rows,counts=dict(old_F_pairs_identity_checked=64,
        failed_workpoints=15,actual_new_linear_profile_refits=45,new_receiver_CE=0,
        new_F=0,new_BP=0,new_LDPC=0),
        by_candidate={'decoded_raw':classify(ordered,'decoded_raw'),
            'reencoded_info_hat':classify(ordered,'reencoded_info_hat')},
        max_saved_t9_A_analysis_relative=max(r['saved_t9_A_analysis_relative'] for r in ordered),
        supervisor_exits=exit_rows,
        supervisor_wall_seconds_total=sum(v['wall_seconds'] for v in exit_rows.values()),
        rows=detailed)


def main():
    p=argparse.ArgumentParser();p.add_argument('--old-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=analyze(args.old_root)
    if args.output.exists():raise FileExistsError('frozen analysis output already exists')
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(args.output)


if __name__=='__main__':main()
