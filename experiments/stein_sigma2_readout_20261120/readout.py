"""Zero-cost test of the external Stein-closure sigma^2 estimator (RULES.md). Standard library only; run on deinlab.
  python3 readout.py --rows ../sigma2_dd_20261118/out/main_20261118 --out out/result.json
"""
import argparse, glob, gzip, json, math, statistics, sys
from collections import defaultdict
from pathlib import Path


def closed(r, nu):
    arg = r * r + 4 * nu * (r - nu)
    return (r + math.sqrt(max(0.0, arg))) / 2, arg < 0


def opened(r, nu, s0):
    den = 1 - 2 * nu / (s0 + nu)
    return (r - nu) / den if den > 0 else None


def verdict(m):
    return 'supported' if 0.90 <= m <= 1.10 else ('refuted' if m < 0.75 or m > 1.25 else 'inconclusive')


def summary(rows):
    c = [x['closed'] for x in rows]
    o = [x['open'] for x in rows if x['open'] is not None]
    q = lambda v: [round(p, 3) for p in statistics.quantiles(v, n=4)] if len(v) >= 4 else None
    return dict(n=len(rows), closed_median=statistics.median(c), closed_quartiles=q(c),
                clipped_share=sum(x['clipped'] for x in rows) / len(rows),
                open_valid=len(o), open_median=statistics.median(o) if o else None,
                r_over_sigma2_median=statistics.median(x['r'] for x in rows),
                nu_over_sigma2_median=statistics.median(x['t'] for x in rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(str(Path(a.rows) / 'rows_shard*.jsonl.gz'))):
        with gzip.open(f, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                dd = r['arms']['DD']['B']
                nz = dd.get('noise') or {}
                if dd['f0']['syndrome'] == 0 or 'residual_power' not in nz:
                    continue
                s2 = r['sigma2']; res = nz['residual_power']; nu = nz['uncertainty_power']
                est, clip = closed(res, nu)
                op = opened(res, nu, nz['first_round']['estimate'])
                rows.append(dict(snr=r['snr_centi_db'] / 100, closed=est / s2, clipped=clip,
                                 open=None if op is None else op / s2, r=res / s2, t=nu / s2))
    by = defaultdict(list)
    for x in rows:
        by[x['snr']].append(x)
    main_s = summary(rows)
    sub = summary([x for x in rows if 4.5 <= x['snr'] <= 6.0])
    out = dict(_argv=sys.argv, rules='RULES.md', main=main_s, main_verdict=verdict(main_s['closed_median']),
               rf_subset=sub, rf_subset_verdict=verdict(sub['closed_median']),
               by_snr={str(k): summary(v) for k, v in sorted(by.items())})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
