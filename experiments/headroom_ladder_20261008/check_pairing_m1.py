#!/usr/bin/env python
"""M1 vs F2 pairing check.  Every M1 row (arms P*/GX) must carry the same frame fingerprint (channel_seed,
physical_gains_sha256, info_sha256, noise_sha256) as the F2 A3 row of the same (config, snr, frame); GX rows (exact taps through the
general-tap operator) must reproduce A3 (info_errors, coded_errors, syndrome, ldpc_iters equal; |logloss diff| <= 1e-9).
Also reports the matrix cross-check (misfit_matrix_abs_diff) of the M1 rows that have it.
usage: check_pairing_m1.py <out.json> <f2_dir>[,<f2_dir>...] <m1_dir> [<m1_dir>...]
"""
import glob
import json
import sys

KEYS = ('channel_seed', 'physical_gains_sha256', 'info_sha256', 'noise_sha256')
VALS = ('info_errors', 'coded_errors', 'syndrome', 'ldpc_iters')


def rows(path):
    for f in sorted(glob.glob(path + '/rows_shard*.jsonl')):
        for line in open(f):
            yield json.loads(line)


def main():
    out, f2dirs, m1dirs = sys.argv[1], sys.argv[2].split(','), sys.argv[3:]
    m1 = {}
    for d in m1dirs:
        for r in rows(d):
            m1.setdefault((r['config'], r['snr_centi_db'], r['frame']), []).append(r)
    want = set(m1)
    a3 = {}
    for d in f2dirs:
        for r in rows(d):
            k = (r['config'], r['snr_centi_db'], r['frame'])
            if r['arm'] == 'A3' and r['status'] == 'ok' and k in want:
                a3[k] = r
    n_rows = n_missing = n_fp_bad = n_gx = n_gx_bad = n_err = 0
    max_llr, mm_max, mm_n = 0., 0., 0
    bad = []
    for k, rs in m1.items():
        ref = a3.get(k)
        for r in rs:
            n_rows += 1
            if r['status'] != 'ok':
                n_err += 1
                continue
            if 'misfit_matrix_abs_diff' in r:
                mm_n += 1
                mm_max = max(mm_max, r['misfit_matrix_abs_diff'])
            if ref is None:
                n_missing += 1
                continue
            if any(r[x] != ref[x] for x in KEYS):
                n_fp_bad += 1
                bad.append(dict(key=list(k), arm=r['arm'], what='fingerprint'))
            if r['arm'] == 'GX':
                n_gx += 1
                diff = [x for x in VALS if r[x] != ref[x]]
                d = abs(r['logloss_bits'] - ref['logloss_bits'])
                max_llr = max(max_llr, d)
                if d > 1e-9:
                    diff.append('logloss_bits')
                if diff:
                    n_gx_bad += 1
                    bad.append(dict(key=list(k), arm='GX', what=diff))
    res = dict(n_m1_rows=n_rows, n_m1_error_rows=n_err, n_cells=len(m1), n_cells_with_f2_a3=len(a3),
               n_rows_without_f2_a3=n_missing, n_fingerprint_mismatch=n_fp_bad, n_gx_rows=n_gx,
               n_gx_mismatch_vs_a3=n_gx_bad, max_abs_logloss_diff_gx_vs_a3=max_llr,
               n_matrix_checks=mm_n, max_matrix_misfit_abs_diff=mm_max, mismatches=bad[:20])
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'mismatches'}), flush=True)
    if bad or n_missing or n_err:
        raise SystemExit(f'pairing check failed: {len(bad)} mismatches, {n_missing} rows without F2 A3, {n_err} error rows')


if __name__ == '__main__':
    main()
