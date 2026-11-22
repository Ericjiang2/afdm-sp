import glob, gzip, json, collections
import numpy as np
D = '/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017/out/main'
acc = collections.defaultdict(lambda: dict(v=[], d=[], c=[], r1=[]))
for p in sorted(glob.glob(D + '/rows_shard*.jsonl.gz')):
    with gzip.open(p, 'rt') as fh:
        for line in fh:
            r = json.loads(line)
            if r.get('status') == 'error':
                continue
            a = acc[(r['scenario'], r['rho_permille'], r['snr_centi_db'])]
            a['v'].append(r['mean_v']); a['d'].append(r['variants']['L-diag']['fer']); a['c'].append(r['variants']['L-cov']['fer']); a['r1'].append(r['round1']['syndrome'] == 0)
out = {}
for (s, rho, snr), a in sorted(acc.items()):
    out[f'{s}_{rho}_{snr}'] = dict(n=len(a['v']), mean_v_median=float(np.median(a['v'])), mean_v_mean=float(np.mean(a['v'])),
                                   fer_Ldiag=float(np.mean(a['d'])), fer_Lcov=float(np.mean(a['c'])), round1_zero_syndrome=float(np.mean(a['r1'])))
json.dump(out, open('/data/guoyikun/00inbox/AFDM-channel-estimation/ideas/l2/out_r4b6_u.json', 'w'), indent=1)
for k, v in out.items():
    print(k, {a: round(b, 4) for a, b in v.items()})
