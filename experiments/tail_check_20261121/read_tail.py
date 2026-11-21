"""RULES.md: read-only tail checks on stage A rows.  python read_tail.py ../data_pilot_fer_20261121/out/stageA out/result.json"""
import gzip, json, sys
from pathlib import Path
import numpy as np

rows = []
for p in sorted(Path(sys.argv[1]).glob('rows_shard*.jsonl.gz')):
    with gzip.open(p, 'rt') as fh:
        rows += [json.loads(l) for l in fh]
fail = {(r['scenario'], r['rho'], r['snr'], r['frame']): r['arms']['base']['errors'] > 0 for r in rows}

t1 = {s: float(np.mean([v for (s_, rho, snr, f), v in fail.items() if s_ == s and rho == 100 and snr == 1200])) for s in 'UG'}
t1['mean'] = (t1['U'] + t1['G']) / 2
H = [(s, rho, f) for (s, rho, snr, f), v in fail.items() if v and rho in (150, 200) and snr == 800]
both = sum(fail[(s, rho, 450, f)] for s, rho, f in H)
tail = [r for r in rows if r['rho'] <= 200 and r['snr'] >= 700 and r['arms']['base']['errors'] > 0]
res = dict(_argv=sys.argv, rules='RULES.md',
           T1=dict(fer_rho100_12dB=t1, verdict='PASS' if .01 <= t1['mean'] <= .10 else 'FAIL'),
           T2=dict(n_high_fail=len(H), overlap=both / len(H) if H else None,
                   verdict=('PASS' if H and both / len(H) > .8 else 'FAIL'), note='non-discriminating: shared noise vector'),
           tail=dict(n=len(tail),
                     by_rho={str(r): sum(x['rho'] == r for x in tail) for r in (50, 100, 150, 200)},
                     r0_missed_path=float(np.mean([x['arms']['base']['r0']['missing_power'] > 0 for x in tail])),
                     delay_arm_fixes=float(np.mean([x['arms']['delay']['errors'] == 0 for x in tail])),
                     by_rho_delay_fixes={str(r): float(np.mean([x['arms']['delay']['errors'] == 0 for x in tail if x['rho'] == r]))
                                         for r in (50, 100, 150, 200) if any(x['rho'] == r for x in tail)}))
Path(sys.argv[2]).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
