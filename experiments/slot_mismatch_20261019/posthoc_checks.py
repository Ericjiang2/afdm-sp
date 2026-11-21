"""Post hoc, exploratory checks on saved rows (no receiver runs).

check1  E-2 family R rows: does a scalar-Gamma (A2) phantom edit hurt when it replaced a spurious slot
        (no true path displaced) as well as when it replaced a true-delay slot?  Harm = A2 fails while A5
        (no geometry change) succeeds.
check2  pilot2 rows: what the four extra F0 slots at cap 12 hold, and whether F0 recoveries at cap 12 come with
        more true delays in the r1 geometry.
check3  pilot2 rows: A1 at cap 12, failure rate with vs without a co-delay pair.
Usage: python posthoc_checks.py e2 '<glob of E-2 main_R rows>' | python posthoc_checks.py pilot '<glob of pilot2 rows>'
"""
import glob
import gzip
import json
import sys


def rows(pattern):
    for f in sorted(glob.glob(pattern)):
        for line in gzip.open(f, 'rt'):
            yield json.loads(line)


def phantom_edits(r1, edits, truth):
    """Replay accepted edits on r1; for each edit return (is_phantom, replaced_slot_was_true_delay)."""
    geo = list(r1)
    out = []
    for e in sorted(edits, key=lambda x: x['step']):
        s, new, old = e['slot'], e['new']['delay'], e['old']['delay']
        if geo[s] != old:
            raise ValueError('edit replay mismatch')
        geo[s] = new
        others = [d for j, d in enumerate(geo) if j != s]
        out.append((new in others, old in truth))
    return out


def has_pair(delays):
    return len(delays) != len(set(delays))


def tally(units):
    n = len(units)
    if not n:
        return dict(n=0)
    f = lambda key: round(sum(u[key] for u in units) / n, 4)
    return dict(n=n, **{k: f(k) for k in units[0] if k != 'cls'})


def check1(pattern):
    units = []
    for r in rows(pattern):
        if not r.get('triggered'):
            continue
        truth = set(r['truth']['delays'])
        a2, a5 = r['arms']['A2'], r['arms']['A5']
        ph = phantom_edits(r['r1']['delays'], a2['edits'], truth)
        phantoms = [t for p, t in ph if p]
        cls = 'no_phantom' if not phantoms else ('replaced_true' if any(phantoms) else 'replaced_spurious_only')
        units.append(dict(cls=cls, a2_fail=int(a2['info_errors'] > 0), a5_fail=int(a5['info_errors'] > 0),
                          harm=int(a2['info_errors'] > 0 and a5['info_errors'] == 0),
                          help=int(a2['info_errors'] == 0 and a5['info_errors'] > 0),
                          r1_complete=int(truth <= set(r['r1']['delays']))))
    return {c: tally([u for u in units if u['cls'] == c]) for c in ('no_phantom', 'replaced_spurious_only', 'replaced_true')}


def check23(pattern):
    k2 = dict(keys=0, extra_slots=0, extra_true=0, rec=0, rec_dT=0, other=0, other_dT=0, r1_8_subset_of_12=0)
    by_s = {}
    for r in rows(pattern):
        truth = set(r['truth']['delays'])
        f8, f12 = r['s']['8']['f0'], r['s']['12']['f0']
        d8, d12 = set(f8['r1_delays']), set(f12['r1_delays'])
        extra = d12 - d8
        k2['keys'] += 1
        k2['extra_slots'] += len(extra)
        k2['extra_true'] += len(extra & truth)
        k2['r1_8_subset_of_12'] += d8 <= d12
        dT = len(d12 & truth) - len(d8 & truth)
        if f8['info_errors'] > 0 and f12['info_errors'] == 0:
            k2['rec'] += 1
            k2['rec_dT'] += dT
        else:
            k2['other'] += 1
            k2['other_dT'] += dT
        for s in ('8', '12'):
            x = r['s'][s]
            if not x['triggered']:
                continue
            for arm in ('A1', 'A2'):
                a = x['arms'][arm]
                ph = phantom_edits(x['f0']['r1_delays'], a['edits'], truth)
                key = (s, arm, 'pair' if has_pair(a['final_delays']) else 'no_pair')
                b = by_s.setdefault(key, dict(n=0, fail=0, phantom_replaced_spurious_only=0, phantom_replaced_true=0))
                b['n'] += 1
                b['fail'] += a['info_errors'] > 0
                phantoms = [t for p, t in ph if p]
                if phantoms:
                    b['phantom_replaced_true' if any(phantoms) else 'phantom_replaced_spurious_only'] += 1
    k2['extra_true_share'] = round(k2['extra_true'] / max(k2['extra_slots'], 1), 4)
    k2['rec_mean_dT'] = round(k2['rec_dT'] / max(k2['rec'], 1), 3)
    k2['other_mean_dT'] = round(k2['other_dT'] / max(k2['other'], 1), 3)
    check3 = {'/'.join(k): dict(v, fail_rate=round(v['fail'] / v['n'], 4)) for k, v in sorted(by_s.items())}
    return dict(check2=k2, check3=check3)


if __name__ == '__main__':
    mode, pattern = sys.argv[1], sys.argv[2]
    print(json.dumps(check1(pattern) if mode == 'e2' else check23(pattern), indent=1))
