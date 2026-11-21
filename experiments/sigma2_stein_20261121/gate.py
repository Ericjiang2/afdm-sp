"""Gate before launch (PROTOCOL.md section Qualification). Run on deinlab in the frozen environment.

  python gate.py --frozen-slot <slot>/experiments/slot_mismatch_20261019 --archive <sigma2_dd main dir> --out out/gate.json
G-A: unpatched DD reproduces the archived DD rows on frames 11000-11001, all SNRs (B dict, exact JSON).
G-B: patched Stein arm keeps every round-1 quantity of the archived DD row (round-1 geometry, residual and
     uncertainty power) and its estimate equals the formula applied to those archived powers.
Also records per-key CPU time for the cost projection and the qualified source/environment inventory.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import stein

FRAMES = (11000, 11001)
SNRS = tuple(range(450, 801, 50))


def archived(archive):
    rows = {}
    with gzip.open(Path(archive) / 'rows_shard000.jsonl.gz', 'rt') as fh:
        for line in fh:
            r = json.loads(line)
            if r['frame'] in FRAMES:
                rows[r['frame'], r['snr_centi_db']] = r
    return rows


def run(study, rows, label):
    q, ctx = study[:2]
    out, seconds = [], []
    for frame in FRAMES:
        base, diag = q.sm.p1ctx.base(ctx, rs_scenario(), rs_rho(), frame)
        for snr in SNRS:
            _, actual, truth = q.sm.gd.observe(ctx, base, diag, rs_rho(), snr)
            t = time.process_time()
            b, supplied, _ = stein.rs.evaluate_b(study, 'DD', actual, truth)
            a3 = stein.rs.evaluate_a3(study, supplied, truth)
            seconds.append(time.process_time() - t)
            exp = rows[frame, snr]['arms']['DD']['B']
            if label == 'DD':
                ok = json.dumps(b, sort_keys=True) == json.dumps(exp, sort_keys=True)
            else:
                n, e = b['noise'], exp['noise']
                formula, _ = stein.stein(e['residual_power'], e['uncertainty_power'])
                ok = (b['round1_delays'] == exp['round1_delays'] and b['round1_dopplers'] == exp['round1_dopplers']
                      and n['residual_power'] == e['residual_power'] and n['uncertainty_power'] == e['uncertainty_power']
                      and n['first_round'] == e['first_round'] and n['raw'] == formula)
            out.append(dict(frame=frame, snr_centi_db=snr, ok=ok, a3_errors=a3['info_errors'],
                            info_errors=b['info_errors'], ratio=b['noise']['ratio']))
    return out, seconds


def rs_scenario():
    return stein.rs.SCENARIO


def rs_rho():
    return stein.rs.RHO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frozen-slot', required=True, type=Path)
    ap.add_argument('--archive', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    rows = archived(a.archive)
    study = stein.load(a.frozen_slot, patch=False)  # the frozen context can be built once per process
    dd_keys, dd_sec = run(study, rows, 'DD')
    study[3].estimate_dd = stein.estimate_stein
    st_keys, st_sec = run(study, rows, 'Stein')
    ctx = study[1]
    own = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
           for d in (stein.HERE, stein.DD_DIR) for p in sorted(d.glob('*.py'))}
    status = 'PASS' if all(k['ok'] for k in dd_keys + st_keys) else 'FAIL'
    per_key = sum(st_sec) / len(st_sec)
    result = dict(status=status, G_A=dd_keys, G_B=st_keys, stein_cpu_seconds_per_key=per_key,
                  projected_core_hours_8000_keys=per_key * 8000 / 3600 * 1.3,
                  _config=dict(source_md5=ctx.source_md5, source_paths=ctx.source_paths,
                               environment=ctx.environment, own_sha256=own, frozen_slot=str(a.frozen_slot)))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1, default=str))
    print(status, 'G_A', sum(k['ok'] for k in dd_keys), '/', len(dd_keys), 'G_B', sum(k['ok'] for k in st_keys), '/',
          len(st_keys), 'projected core-hours', round(result['projected_core_hours_8000_keys'], 2))


if __name__ == '__main__':
    main()
