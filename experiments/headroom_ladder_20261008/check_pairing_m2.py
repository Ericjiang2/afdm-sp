#!/usr/bin/env python
"""M2 smoke vs F2 pairing / determinism check.
For every smoke row of the reference arms A0, F0, A3, PS0, PS that has an F2 row at the same (config, snr, frame):
  frame fingerprint (channel_seed, physical_gains_sha256, info_sha256, noise_sha256) identical, and the re-run is deterministic:
  info_errors, coded_errors, syndrome, ldpc_iters equal, |logloss_bits diff| <= 1e-9.
Every other smoke row (M arms, PB16) must carry the fingerprint of the F2 A3 row of its cell; rows of cells without F2 coverage (e.g. J8)
are counted, not compared.  All rows must have status ok.
--law expected (default): the smoke runs the EXPECTED-power law, so F2 (realized-law) rows can only share the draws: compared keys are
(channel_seed, info_sha256, noise_sha256); physical_gains_sha256 must DIFFER where the realized factor != 1 (reported, not asserted); no
value comparison.  --law realized: full fingerprint + deterministic re-run comparison as above.
usage: check_pairing_m2.py [--law expected|realized] <out.json> <f2_dir>[,<f2_dir>...] <smoke_dir> [<smoke_dir> ...]
"""
import glob
import json
import sys

KEYS = ('channel_seed', 'physical_gains_sha256', 'info_sha256', 'noise_sha256')
VALS = ('info_errors', 'coded_errors', 'syndrome', 'ldpc_iters')
REF_ARMS = ('A0', 'F0', 'A3', 'PS0', 'PS')


def rows(path):
    for f in sorted(glob.glob(path + '/rows_shard*.jsonl')):
        for line in open(f):
            if line.strip():
                yield json.loads(line)


def main():
    argv = sys.argv[1:]
    law = 'expected'
    if argv and argv[0] == '--law':
        law = argv[1]
        argv = argv[2:]
    out, f2dirs, smoke_dirs = argv[0], argv[1].split(','), argv[2:]
    keys = KEYS if law == 'realized' else ('channel_seed', 'info_sha256', 'noise_sha256')
    smoke = [r for d in smoke_dirs for r in rows(d)]
    cells = {(r['config'], r['snr_centi_db'], r['frame']) for r in smoke}
    ref = {}
    for d in f2dirs:
        for r in rows(d):
            k = (r['config'], r['snr_centi_db'], r['frame'])
            if k in cells and r['arm'] in REF_ARMS and r['status'] == 'ok':
                ref[(k, r['arm'])] = r
    n = dict(law=law, gains_hash_differs=0, rows=len(smoke), error_rows=0, ref_compared=0, fp_mismatch=0, value_mismatch=0, fp_only_compared=0, no_f2_cell=0)
    max_ll = 0.
    bad = []
    for r in smoke:
        k = (r['config'], r['snr_centi_db'], r['frame'])
        if r['status'] != 'ok':
            n['error_rows'] += 1
            continue
        a3 = ref.get((k, 'A3'))
        if a3 is None:
            n['no_f2_cell'] += 1
            continue
        if r['physical_gains_sha256'] != a3['physical_gains_sha256']:
            n['gains_hash_differs'] += 1
        if any(r[x] != a3[x] for x in keys):
            n['fp_mismatch'] += 1
            bad.append(dict(key=list(k), arm=r['arm'], what='fingerprint'))
        if r['arm'] in REF_ARMS and law == 'realized':
            f = ref.get((k, r['arm']))
            if f is None:
                continue
            n['ref_compared'] += 1
            diff = [x for x in VALS if r[x] != f[x]]
            d = abs(r['logloss_bits'] - f['logloss_bits'])
            max_ll = max(max_ll, d)
            if d > 1e-9:
                diff.append('logloss_bits')
            if diff:
                n['value_mismatch'] += 1
                bad.append(dict(key=list(k), arm=r['arm'], what=diff))
        else:
            n['fp_only_compared'] += 1
    res = dict(n, max_abs_logloss_diff_vs_f2=max_ll, mismatches=bad[:20])
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'mismatches'}), flush=True)
    if bad or n['error_rows']:
        raise SystemExit(f'pairing check failed: {len(bad)} mismatches, {n["error_rows"]} error rows')


if __name__ == '__main__':
    main()
