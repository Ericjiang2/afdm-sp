#!/usr/bin/env python
"""F3 vs F1 pairing checks on the common (config, snr, frame) A3 rows.
usage: check_pairing_f3.py <mode: realized|expected> <f1_dir> <f3_dir> <out.json>
realized: all of KEYS+VALS bit-identical, logloss within 1e-9 (old mode reproduces F1 end-to-end).
expected: channel_seed/info_sha256/noise_sha256/tap_delays/rays_per_tap equal; cl_energy_per_dim(F3)/cl_norm_factor(F1)^2
          == cl_energy_per_dim(F1) (rtol 1e-9); cl_sum_g2(F3) == cl_norm_factor(F1)^2 (rtol 1e-12).
"""
import glob
import json
import sys

KEYS = ('channel_seed', 'physical_gains_sha256', 'info_sha256', 'noise_sha256', 'tap_delays', 'rays_per_tap')
VALS = ('info_errors', 'coded_errors', 'syndrome', 'ldpc_iters')


def load(path, snrs=None):
    out = {}
    for f in sorted(glob.glob(path + '/rows_shard*.jsonl')):
        for line in open(f):
            r = json.loads(line)
            if r['status'] != 'ok' or r['arm'] != 'A3':
                continue
            if snrs is not None and r['snr_centi_db'] not in snrs:
                continue
            out[(r['config'], r['snr_centi_db'], r['frame'])] = r
    return out


def main():
    mode, f1_dir, f3_dir, out = sys.argv[1:5]
    b = load(f3_dir)
    a = load(f1_dir, {k[1] for k in b})
    common = sorted(set(a) & set(b))
    bad, maxd = [], 0.
    for k in common:
        ra, rb = a[k], b[k]
        if mode == 'realized':
            diff = [x for x in KEYS + VALS if ra[x] != rb[x]]
            d = abs(ra['logloss_bits'] - rb['logloss_bits'])
            maxd = max(maxd, d)
            if d > 1e-9:
                diff.append('logloss_bits')
        else:
            diff = [x for x in ('channel_seed', 'info_sha256', 'noise_sha256', 'tap_delays', 'rays_per_tap')
                    if ra[x] != rb[x]]
            f2 = ra['cl_norm_factor'] ** 2
            e = rb['cl_energy_per_dim'] / f2 / ra['cl_energy_per_dim'] - 1
            maxd = max(maxd, abs(e))
            if abs(e) > 1e-9:
                diff.append('energy_ratio')
            if abs(rb['cl_sum_g2'] / f2 - 1) > 1e-12:
                diff.append('sum_g2')
        if diff:
            bad.append(dict(key=list(k), fields=diff))
    res = dict(mode=mode, n_f3_rows=len(b), n_f1_rows_same_snr=len(a), n_common=len(common), n_mismatch=len(bad),
               max_metric=maxd, common_configs=sorted({k[0] for k in common}),
               common_snr_centi=sorted({k[1] for k in common}), mismatches=bad[:20])
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'mismatches'}), flush=True)
    if bad or not common:
        raise SystemExit(f'{len(bad)} paired rows differ (common={len(common)}): {bad[:3]}')


if __name__ == '__main__':
    main()
