"""Frozen 32-channel paired pilot promotion evaluation from audited rows."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ARMS=('P02','P03','C33','P04','C54')
CONTRASTS=(('C33','P03'),('C33','P02'),('C54','P04'),('C54','P02'))
PREDICTION_SHA256='43af7798d79530dbab59ae61ee1fd8cec700bd273f4483eb7bca19cdafab6941'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(eng_rows,dev_rows,pilot_stage):
    if (pilot_stage['primary']!='per-channel equal mean of linear complete-H NMSE at 7 and 8dB'
            or pilot_stage['contrasts']!=[f'{a}-{b}' for a,b in CONTRASTS]
            or pilot_stage['bootstrap']!=dict(unit='32 channel clusters; both SNRs resampled together',
                draws=20000,seed=202609150402,method='percentile with Bonferroni four contrasts, simultaneous 95%')
            or pilot_stage['promotion']!='both relevant CI upper limits <0 and both SNR point differences nonpositive; engineering/raw checks pass'
            or pilot_stage['max_promotions']!=1
            or pilot_stage['signal_constraints']['native_payload_papr_db_max']!=12.
            or pilot_stage['signal_constraints']['native_payload_peak_power_max']!=16.):
        raise ValueError('frozen PILOT-02 promotion contract differs')
    rows=eng_rows+dev_rows
    by_key={(r['block'],r['snr'],r['arm']):r for r in rows}
    expected={(b,s,a) for b in range(32) for s in (7,8) for a in ARMS}
    if len(rows)!=320 or set(by_key)!=expected:
        raise ValueError('PILOT-02 paired 32-channel row inventory differs')
    for r in rows:
        if (not np.isfinite(r['H_NMSE']) or r['H_NMSE']<0
                or not np.isfinite(r['Hp_NMSE']) or r['Hp_NMSE']<0
                or not isinstance(r['native_gate'],bool)):
            raise ValueError('nonfinite pilot H/Hp score or waveform gate')
    scores={a:np.array([[by_key[b,s,a]['H_NMSE'] for s in (7,8)]
                         for b in range(32)],dtype=float) for a in ARMS}
    gate={a:sum(by_key[b,s,a]['native_gate'] for b in range(32) for s in (7,8))
          for a in ARMS}
    rng=np.random.default_rng(202609150402)
    indices=rng.integers(0,32,size=(20000,32))
    contrasts={}
    for a,b in CONTRASTS:
        difference=scores[a]-scores[b]
        per_channel=difference.mean(axis=1)
        bootstrap=per_channel[indices].mean(axis=1)
        lo,hi=np.quantile(bootstrap,(.00625,.99375),method='linear')
        contrasts[f'{a}-{b}']=dict(point_per_snr=difference.mean(axis=0).tolist(),
            point_channel_mean=float(per_channel.mean()),
            simultaneous_95_CI=[float(lo),float(hi)],
            ci_upper_below_zero=bool(hi<0),
            both_snr_nonpositive=bool(np.all(difference.mean(axis=0)<=0)))
    eligible={}
    for candidate in ('C33','C54'):
        relevant=[v for name,v in contrasts.items() if name.startswith(candidate+'-')]
        eligible[candidate]=bool(len(relevant)==2 and gate[candidate]==64 and
            all(v['ci_upper_below_zero'] and v['both_snr_nonpositive'] for v in relevant))
    supported=[a for a in ('C33','C54') if eligible[a]]
    primary={a:float(scores[a].mean()) for a in ARMS}
    selected=(min(supported,key=lambda a:(primary[a],0 if a=='C33' else 1))
              if supported else None)
    return dict(primary_mean_H_NMSE=primary,contrasts=contrasts,
        native_waveform_pass_count_of_64=gate,eligible=eligible,selected=selected,
        bootstrap_unit='channel cluster with both SNRs paired',bootstrap_draws=20000,
        bootstrap_seed=202609150402,interval_quantiles=[.00625,.99375],
        development_selection_only=True,max_promotions=1,
        new_initialization_CE=0,new_BP=0,new_LDPC=0,new_F=0)


def main(args):
    root=args.root.resolve(); prediction=args.prediction.resolve()
    if sha(Path(__file__))!=args.script_sha256 or sha(prediction)!=PREDICTION_SHA256:
        raise ValueError('promotion script/prediction SHA differs')
    stage=json.loads(prediction.read_text())['pilot_stage']
    eng=root/'evidence/pilot-initial-engineering-v1-engineering-raw-audit-v5.json'
    dev=root/'evidence/pilot-initial-development-v1-development-raw-audit.json'
    summary=root/'runs/pilot-initial-development-v1/development/summary.json'
    exit_path=root/'evidence/pilot-initial-development-v1-development-exit.json'
    e,d,s,x=(json.loads(p.read_text()) for p in (eng,dev,summary,exit_path))
    if (e['status']!='PASS' or d['status']!='PASS' or s['status']!='COMPLETE'
            or x['exit_code']!=0 or x['timed_out']
            or d['summary_sha256']!=sha(summary)
            or len(e['rows'])!=20 or len(d['rows'])!=300
            or d['audit_new_initialization_CE']!=0):
        raise ValueError('PILOT-02 producer/raw audit prerequisites differ')
    result=evaluate(e['rows'],d['rows'],stage)
    result.update(status='PASS',prediction_sha256=PREDICTION_SHA256,
        script_sha256=args.script_sha256,engineering_receipt_sha256=sha(eng),
        development_receipt_sha256=sha(dev),development_summary_sha256=sha(summary),
        producer_exit_sha256=sha(exit_path))
    with args.output.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result,allow_nan=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--prediction',type=Path,required=True)
    p.add_argument('--script-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
