"""Claude's independent recomputation of the main readouts from raw rows (not the frozen verdict code).

Purpose: catch aggregation errors before the card is written. Point estimates must match RESULTS.md exactly; CIs use an
independent frame-cluster bootstrap (2,000 draws, seed 7) and need only agree approximately.
Usage on deinlab: python claude_check.py <dir with rows_shard*.jsonl>
"""
import glob
import gzip
import json
import sys

import numpy as np

SBL_ARMS = ('R0', 'R1', 'S-lo', 'S-hi', 'S-isolo', 'U2')
C_ARMS = ('F0', 'A2', 'CD', 'U', 'C-hi', 'C-lo')
ADM_ARMS = ('A2', 'CD', 'U', 'C-hi', 'C-lo')


def rows(directory):
    for path in sorted(glob.glob(f'{directory}/rows_shard*.jsonl*')):
        opener = gzip.open if path.endswith('.gz') else open
        with opener(path, 'rt') as handle:
            for line in handle:
                yield json.loads(line)


def load(directory):
    sbl, cst, adm = {}, {}, []
    triggered_mismatch = 0
    for r in rows(directory):
        key, row = tuple(r['key']), r['row']
        frame = key[3]
        if r['leg'] == 'sbl':
            sbl[key] = (frame, {a: int(row['variants'][a]['fer']) for a in SBL_ARMS})
        else:
            fail = {a: int(row['arms'][a]['errors'] > 0) for a in C_ARMS}
            cst[key] = (frame, fail)
            if not row['syndrome'] and len(set(fail.values())) > 1:
                triggered_mismatch += 1
            a = row.get('admission')
            if a:
                adm.append((frame, {x: int(a['by_arm'][x]['preference']) for x in ADM_ARMS}))
    return sbl, cst, adm, triggered_mismatch


def matrix(data, arms):
    frames = np.array([v[0] for v in data])
    values = np.array([[v[1][a] for a in arms] for v in data], float)
    return frames, values


def boot(frames, values, stat, n=2000, seed=7):
    uniq, inv = np.unique(frames, return_inverse=True)
    sums = np.zeros((len(uniq), values.shape[1]))
    np.add.at(sums, inv, values)
    counts = np.bincount(inv).astype(float)
    point = stat(sums.sum(0) / counts.sum())
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n):
        idx = rng.integers(0, len(uniq), len(uniq))
        draws.append(stat(sums[idx].sum(0) / counts[idx].sum()))
    draws = np.array(draws)
    return point, np.nanpercentile(draws, 2.5, axis=0), np.nanpercentile(draws, 97.5, axis=0)


def show(name, frames, values, arms, contrasts):
    print(f'== {name}: {len(values)} units, {len(np.unique(frames))} frames')
    print('   rate per arm:', {a: round(float(values[:, i].mean()), 5) for i, a in enumerate(arms)})
    idx = {a: i for i, a in enumerate(arms)}
    for label, f in contrasts.items():
        p, lo, hi = boot(frames, values, lambda m, f=f: f(m, idx))
        print(f'   {label}: {p:.4f} [{lo:.4f}, {hi:.4f}]')


def main(directory):
    sbl, cst, adm, mismatch = load(directory)
    print('keys: sbl', len(sbl), 'cstate', len(cst), 'admission units', len(adm),
          '| untriggered keys with differing arm outcomes:', mismatch)
    f, v = matrix(list(sbl.values()), SBL_ARMS)
    gb = lambda m, i: m[i['R1']] - m[i['R0']]
    phi = lambda arm: (lambda m, i: (m[i['R1']] - m[i[arm]]) / (m[i['R1']] - m[i['R0']]))
    show('SBL', f, v, SBL_ARMS, {
        'G_B = R1-R0': gb, 'phi_lo': phi('S-lo'), 'phi_hi': phi('S-hi'), 'phi_U2': phi('U2'),
        'Delta_lo = S-isolo - S-lo': lambda m, i: m[i['S-isolo']] - m[i['S-lo']],
        'H = U2 - S-lo': lambda m, i: m[i['U2']] - m[i['S-lo']],
        'S-lo - R0': lambda m, i: m[i['S-lo']] - m[i['R0']], 'U2 - R0': lambda m, i: m[i['U2']] - m[i['R0']]})
    f, v = matrix(list(cst.values()), C_ARMS)
    psi = lambda arm: (lambda m, i: (m[i['A2']] - m[i[arm]]) / (m[i['A2']] - m[i['CD']]))
    show('CSTATE', f, v, C_ARMS, {
        'A2 - CD': lambda m, i: m[i['A2']] - m[i['CD']], 'U - CD': lambda m, i: m[i['U']] - m[i['CD']],
        'U - A2': lambda m, i: m[i['U']] - m[i['A2']], 'C-hi - CD': lambda m, i: m[i['C-hi']] - m[i['CD']],
        'psi_C-hi': psi('C-hi'), 'psi_C-lo': psi('C-lo')})
    uc = v[:, C_ARMS.index('U')] != v[:, C_ARMS.index('CD')]
    print('   U vs CD discordant keys', int(uc.sum()), 'frames', len(np.unique(f[uc])))
    if adm:
        f, v = matrix(adm, ADM_ARMS)
        pi = lambda arm: (lambda m, i: (m[i['A2']] - m[i[arm]]) / (m[i['A2']] - m[i['CD']]))
        show('V5-adm', f, v, ADM_ARMS, {'pi_C-hi': pi('C-hi'), 'pi_C-lo': pi('C-lo')})


if __name__ == '__main__':
    main(sys.argv[1])
