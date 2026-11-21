"""Pair sealed E-3/E-3b rows and compute censor-aware frame-bootstrap bounds."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.special import gammaln, logsumexp

from run import ARMS, CELLS, EXP, GRID, MAIN_FRAMES, key_of, main_keys, read_rows, write_json
from p1_agg import HIGH, LOW, crossing

SBL_GRID = tuple(range(600, 1101, 100))
E3 = ('tf_e3_sbl_20261017', '88fed65d4c6fc38daa92af6d56d6eba8163aa7ea24457007d9bb94fd015385fe')
E3B = ('tf_e3b_offgrid_20261017', 'b2dcc9350fa4fa2629c92ae23974680623a857e219368ff65af2ec242bf8bd89')
N_BOOT = 20000
BOOT_SEED = 20261118


def archives():
    specifications = [(E3, ('L-hard','L-diag'), CELLS, MAIN_FRAMES),
                      (E3B, ('diag-off',), (('U',300),('G',300)), range(4000,4200))]
    archived, gates = {}, {}
    for (name, manifest_sha), arms, cells, frames in specifications:
        base = EXP/name/'out/main'
        manifest = (base/'REMOTE_ROWS_MD5.txt').read_bytes()
        assert hashlib.sha256(manifest).hexdigest() == manifest_sha
        entries = [line.split() for line in manifest.decode().splitlines()]
        assert len({file for _, file in entries}) == len(entries)
        rows = {}
        config_count = 0
        for md5, filename in entries:
            blob = (base/filename).read_bytes()
            assert hashlib.md5(blob).hexdigest() == md5, filename
            if filename.endswith('.json'):
                config_count += 1
                continue
            for line in gzip.decompress(blob).splitlines():
                r = json.loads(line)
                k = key_of(r)
                assert k not in rows and not r.get('smoke') and r.get('status') != 'error'
                truth = r['truth']
                vals = {}
                for a in arms:
                    item = r['variants'][a]
                    assert item['fer'] == (item['info_errors'] > 0)
                    vals[a] = dict(errors=item['info_errors'], decoded_sha=item['decoded_sha256'])
                rows[k] = dict(truth=dict(sigma2=r['sigma2'], delays=truth['delays'],
                                           dopplers=truth['dopplers'], gains=truth['gains']), arms=vals)
        assert rows.keys() == {(s,rho,snr,f) for s,rho in cells for snr in SBL_GRID for f in frames}
        for a in arms:
            archived[a] = rows
        gates[name] = dict(keys=len(rows), data_shards=len(entries)-config_count,
                           config_shards=config_count, manifest_sha256=manifest_sha)
    return archived, gates


def load_main(out):
    rows = {}
    draws = {}
    for path in sorted(out.glob('main-*.jsonl')):
        for r in read_rows(path):
            k = key_of(r)
            assert k not in rows and set(r['arms']) == set(ARMS), k
            rows[k] = r
            physical = (k[0], k[1], k[3])
            hashes = tuple(r['inputs'][f] for f in ('info','coded','noise','pilot','data'))
            if physical in draws:
                assert draws[physical] == hashes, k
            else:
                draws[physical] = hashes
            if not r['syndrome']:
                assert r['arms']['F0'] == r['arms']['FULL'] == r['arms']['CODELAY']
    assert rows.keys() == main_keys(), (len(rows), len(main_keys()))
    return rows


def weights(n):
    return np.random.default_rng(BOOT_SEED).multinomial(n, np.full(n, 1/n), size=N_BOOT).astype(float)


def ordered(values, p):
    rank = math.ceil(len(values) * p) - 1
    return float(np.partition(values, rank)[rank])


def represent(x):
    return ('+inf' if x > 0 else '-inf') if np.isinf(x) else float(x)


def interval(lower, upper):
    return [represent(ordered(lower, .025)), represent(ordered(upper, .975))]


def curve(fer, snrs, n):
    x, status = crossing(fer, n, np.asarray(snrs) / 100.)
    lo = np.where(status == LOW, -np.inf, x)
    hi = np.where(status == HIGH, np.inf, x)
    return lo, hi, status


def crossing_summary(delta_left, delta_right):
    """Crossing difference left minus right. The arrays start with the point estimate."""
    a0, a1, sa = delta_left
    b0, b1, sb = delta_right
    lo, hi = a0 - b1, a1 - b0
    # At least one bound from each crossing is finite, so no inf-inf subtraction.
    return dict(point=[represent(lo[0]),represent(hi[0])], interval95=interval(lo[1:], hi[1:]),
                left=dict(point=[represent(a0[0]),represent(a1[0])],
                          left_censored=int((sa[1:] == LOW).sum()), right_censored=int((sa[1:] == HIGH).sum())),
                right=dict(point=[represent(b0[0]),represent(b1[0])],
                           left_censored=int((sb[1:] == LOW).sum()), right_censored=int((sb[1:] == HIGH).sum())))


def failure_matrix(rows, arm, cell, snrs, frames):
    s,rho = cell
    return np.array([[rows[s,rho,snr,f]['arms'][arm]['errors'] > 0 for snr in snrs]
                     for f in frames], dtype=np.int8)


def all_curve(samples, snrs, boot):
    return curve(np.vstack([samples.mean(axis=0), boot @ samples / len(samples)]), snrs, len(samples))


def log_p_two_sided(a,b):
    n = a + b
    tail = np.arange(min(a,b) + 1)
    logtail = logsumexp(gammaln(n+1) - gammaln(tail+1) - gammaln(n-tail+1) - n*np.log(2.))
    return min(0., float((logtail + np.log(2.)) / np.log(10.)))


def paired(a,b,boot):
    delta = a - b
    harms = int((delta > 0).sum())
    rescues = int((delta < 0).sum())
    samples = boot @ delta.sum(axis=1) / a.size
    return dict(keys=a.size, first_failed=int(a.sum()), second_failed=int(b.sum()),
                delta=float(delta.mean()), discordance=dict(only_first_failed=harms, only_second_failed=rescues),
                log10_p_mcnemar_two_sided=log_p_two_sided(harms,rescues), interval95=interval(samples,samples))


def main_analysis(out):
    ours = load_main(out)
    archive, provenance = archives()
    for baseline in ('L-hard','diag-off'):
        for k,x in archive[baseline].items():
            assert ours[k]['truth'] == x['truth'], (baseline,k)
    boot400, boot200 = weights(400), weights(200)
    overall = {a: np.concatenate([failure_matrix(ours,a,c,GRID[c[1]],MAIN_FRAMES) for c in CELLS], axis=1)
               for a in ARMS}
    replacement = paired(overall['CODELAY'], overall['FULL'], boot400)
    replacement['hash_disagreements'] = sum(r['arms']['CODELAY']['decoded_sha'] != r['arms']['FULL']['decoded_sha']
                                            for r in ours.values())
    clusters = {k[-1] for k,r in ours.items() if (r['arms']['CODELAY']['errors']>0) != (r['arms']['FULL']['errors']>0)}
    replacement['discordant_clusters'] = len(clusters)
    if not clusters:
        replacement['zero_discordant_cluster_rate_exact_upper95'] = 1-.05**(1/len(MAIN_FRAMES))
    replacement['pass'] = replacement['interval95'][1] <= .002
    cells = {}
    for c in CELLS:
        snrs = GRID[c[1]]
        matrix = {a: failure_matrix(ours,a,c,snrs,MAIN_FRAMES) for a in ARMS}
        cross = {a: all_curve(x,snrs,boot400) for a,x in matrix.items()}
        test = crossing_summary(cross['CODELAY'],cross['FULL'])
        up = test['interval95'][1]
        test['pass'] = up != '+inf' and (up == '-inf' or up <= .05)
        test['inconclusive_upper_unbounded'] = up == '+inf'
        cells[f'{c[0]}_{c[1]}'] = dict(
            own_fer={str(snr): {a:int(m[:,i].sum()) for a,m in matrix.items()} for i,snr in enumerate(snrs)},
            thresholds={a:[represent(x[0][0]),represent(x[1][0])] for a,x in cross.items()},
            codelay_minus_full=test)
    comparison = {}
    for baseline, baseline_rows in archive.items():
        subset, boot = (range(4000,4200),boot200) if baseline == 'diag-off' else (MAIN_FRAMES,boot400)
        cell_comparisons = {}
        all_ours, all_baseline = [], []
        for c in CELLS:
            if baseline == 'diag-off' and c[1] != 300:
                continue
            base = failure_matrix(baseline_rows,baseline,c,SBL_GRID,subset)
            matched = {a:failure_matrix(ours,a,c,SBL_GRID,subset) for a in ARMS}
            extended = failure_matrix(ours,'CODELAY',c,GRID[c[1]],subset)
            b_cross = all_curve(base,SBL_GRID,boot)
            all_ours.append(matched['CODELAY'])
            all_baseline.append(base)
            cell_comparisons[f'{c[0]}_{c[1]}'] = dict(
                by_snr={str(snr):dict(failed={**{a:int(m[:,i].sum()) for a,m in matched.items()},
                                                          baseline:int(base[:,i].sum())},
                                      codelay_vs_baseline=paired(matched['CODELAY'][:,i:i+1],base[:,i:i+1],boot))
                        for i,snr in enumerate(SBL_GRID)},
                sbl_minus_codelay_separate_grid=crossing_summary(b_cross,all_curve(extended,GRID[c[1]],boot)),
                sbl_minus_codelay_shared_grid=crossing_summary(b_cross,all_curve(matched['CODELAY'],SBL_GRID,boot)))
        comparison[baseline] = dict(cells=cell_comparisons,
                                    paired_codelay_vs_baseline=paired(np.concatenate(all_ours,axis=1),
                                                                    np.concatenate(all_baseline,axis=1), boot))
    refs = {}
    for k,r in ours.items():
        s,rho,snr,f = k
        if rho != 300 or not ((snr in (600,700) and f < 4025) or (snr == 500 and f < 4050)):
            continue
        old = {a:archive[a][k]['arms'][a] for a in ('L-hard','diag-off') if k in archive[a]}
        refs[k] = dict(key=k, syndrome=r['syndrome'], inputs=r['inputs'], arms=dict(r['arms'],**old))
    assert len(refs) == 200
    summary = dict(keys=len(ours), by_arm={a:int(x.sum()) for a,x in overall.items()},
                   triggered=sum(r['syndrome'] != 0 for r in ours.values()), source=provenance,
                   bootstrap=dict(draws=N_BOOT,seed=BOOT_SEED), codelay_minus_full=replacement, cells=cells,
                   codelay_selection_pass=replacement['pass'] and all(c['codelay_minus_full']['pass'] for c in cells.values()),
                   sbl=comparison)
    write_json(out/'timing_reference.json',list(refs.values()))
    write_json(out/'accuracy.json',summary)
    print(f'Main pair verified: {len(ours)} keys, {summary["triggered"]} triggers, '
          f'gate {summary["codelay_selection_pass"]}',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out',type=Path)
    main_analysis(parser.parse_args().out)
