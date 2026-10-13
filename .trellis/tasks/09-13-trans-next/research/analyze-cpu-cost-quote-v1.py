"""Descriptive full-call quote; repeated timings do not increase channel n."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(mission):
    e = mission/'evidence/exact-harvest-v1'
    summary_path = e/'runs/cpu-cost-quote-v1/quote/summary.json'
    audit_path = mission/'evidence/cpu-cost-quote-v1-raw-audit.json'
    summary = json.loads(summary_path.read_text())
    audit = json.loads(audit_path.read_text())
    assert audit['status'] == 'PASS' and audit['bindings']['summary'] == sha(summary_path)
    assert summary['calls'] == dict(F=68, D=68) and summary['status'] == 'COMPLETE'
    records = [r for r in summary['records'] if r['kind'] == 'F']
    rows = [r for r in records if r['phase'] == 'measurement']
    indexed = {(r['block'], r['snr'], r['repeat'], r['arm']): r for r in rows}
    assert set(indexed) == {(b,s,k,a) for b in range(8) for s in (7,8) for k in range(2) for a in ('DENSE','INTEGER')}
    table, pairs = [], []
    for snr in (7,8):
        group = {}
        for arm in ('DENSE','INTEGER'):
            times = [indexed[b,snr,k,arm]['seconds'] for b in range(8) for k in range(2)]
            cpu = [indexed[b,snr,k,arm]['CPU_seconds'] for b in range(8) for k in range(2)]
            group[arm] = statistics.mean(times)
            table.append(dict(snr=snr,arm=arm,independent_blocks=8,timing_calls=16,
                mean_seconds=group[arm],median_seconds=statistics.median(times),
                mean_CPU_seconds=statistics.mean(cpu),amortized_calls_per_second=1/group[arm]))
        pairs.append(dict(snr=snr,ratio_of_mean_full_times=group['INTEGER']/group['DENSE'],
                          reduction=1-group['INTEGER']/group['DENSE'],
                          below_25_percent_design_target=(1-group['INTEGER']/group['DENSE']) < .25))
    return dict(scope='descriptive 8 existing blocks, 2 repeats; not formal COST or independent confirmation',
                table=table,comparisons=pairs,setup_seconds=summary['setup_seconds'],
                warmup_receiver_seconds=sum(r['seconds'] for r in records if r['phase']=='warmup'),
                measured_receiver_seconds=sum(r['seconds'] for r in rows),
                process_peak_rss_KiB=summary['process_peak_rss_KiB'],
                bindings=dict(summary=sha(summary_path),audit=sha(audit_path),
                              source=summary['source_sha256'],contract=summary['contract_sha256']))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--mission',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();result=analyze(args.mission)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
