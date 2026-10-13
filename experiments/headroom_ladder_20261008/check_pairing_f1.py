#!/usr/bin/env python
"""F2 vs F1 pairing check: for every (config, snr, frame) present in both runs, arms F0/A0/A3 must be bit-identical
(same frame fingerprint, info_errors, coded_errors, syndrome, ldpc_iters, logloss within 1e-9).
usage: check_pairing_f1.py <f1_dir> <f2_dir> <out.json>
"""
import glob
import json
import sys

KEYS = ('channel_seed', 'physical_gains_sha256', 'info_sha256', 'noise_sha256')
VALS = ('info_errors', 'coded_errors', 'syndrome', 'ldpc_iters')


def load(path, snrs=None):
    out = {}
    for f in sorted(glob.glob(path + '/rows_shard*.jsonl')):
        for line in open(f):
            r = json.loads(line)
            if r['status'] != 'ok' or r['arm'] not in ('F0', 'A0', 'A3'):
                continue
            if snrs is not None and r['snr_centi_db'] not in snrs:
                continue
            out[(r['config'], r['snr_centi_db'], r['frame'], r['arm'])] = r
    return out


def main():
    f1_dir, f2_dir, out = sys.argv[1:4]
    b = load(f2_dir)
    snrs = {k[1] for k in b}
    a = load(f1_dir, snrs)
    common = sorted(set(a) & set(b))
    bad, maxd = [], 0.
    for k in common:
        ra, rb = a[k], b[k]
        diff = [x for x in KEYS + VALS if ra[x] != rb[x]]
        d = abs(ra['logloss_bits'] - rb['logloss_bits'])
        maxd = max(maxd, d)
        if d > 1e-9:
            diff.append('logloss_bits')
        if diff:
            bad.append(dict(key=list(k), fields=diff))
    res = dict(n_f2_rows=len(b), n_f1_rows_same_snr=len(a), n_common=len(common), n_mismatch=len(bad),
               max_abs_logloss_diff=maxd, f2_snr_centi=sorted(snrs),
               common_snr_centi=sorted({k[1] for k in common}), mismatches=bad[:20])
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'mismatches'}), flush=True)
    if bad:
        raise SystemExit(f'{len(bad)} paired rows differ: {bad[:3]}')


if __name__ == '__main__':
    main()
