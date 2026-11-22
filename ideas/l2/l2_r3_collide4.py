#!/usr/bin/env python3
"""Idea-funnel local round 3, cheap check for a card draft (child of I-20261122-l09), 2026-11-22, runner l, claude-fable-5.2.
How many users colliding on one preamble can a single receive channel still tell apart?  K users (unknown K, 4-8 paths
each) send the same preamble and postamble; the receiver finds the paths, builds the path-coherence matrix from the data
segment, counts the eigenvalues above the noise edge (K-hat) and clusters the paths.
Source: l2_r3_collide3.py (synth / acquire copied with the data length as a parameter; turbo2, reest, build_h imported
for the decoding stage), l2_r3_collide2.py (split imported for the two-user baseline), l2_r3_marker.py (estimate).
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch21.md.
  python l2_r3_collide4.py smoke|part|readpart|dec|readdec --out out_r3b21
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r3_collide2 as c2  # noqa: E402
import l2_r3_marker as mk  # noqa: E402

SEED, WORKERS, NP, LW, NREF = 20261122, 12, c2.NP, c2.LW, 1024          # NREF: Doppler unit (bins of a 1024-sample frame)
CFG = dict(trials=100, ks=[1, 2, 3, 4, 5], nds=[512, 1024, 2048], snr_db=8.0, pmin=4, pmax=8, kappa=12.0, max_paths=48, edge_margin=1.15,
           dec=dict(frames=[57200, 57230], cells=[(1, 8.0), (3, 8.0), (3, 10.0), (4, 10.0)], dc=4))


def draw(rng, K):
    ps = rng.integers(CFG['pmin'], CFG['pmax'] + 1, K); n = int(ps.sum())
    l = rng.choice(103, n, replace=False); nu = rng.uniform(-1.62, 1.62, n); lab = np.repeat(np.arange(K), ps); g = np.zeros(n, complex)
    for u in range(K):
        x = rng.standard_normal(ps[u]) + 1j * rng.standard_normal(ps[u]); g[lab == u] = x / np.linalg.norm(x)
    return l, nu, g, lab


def synth(l, nu, g, lab, s2, xs, rng):
    nd = len(xs[0]); pre, post = (np.exp(2j * np.pi * rng.uniform(size=NP)) for _ in range(2))
    s = [np.r_[pre, x[-LW:], x, post] for x in xs]; T = NP + LW + nd + NP + LW; t = np.arange(T); y = np.zeros(T, complex)
    for li, vi, gi, u in zip(l, nu, g, lab):
        out = np.zeros(T, complex); out[li:li + len(s[u])] = s[u]; y += gi * out * np.exp(2j * np.pi * vi * t / NREF)
    return y + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T)), pre, post


def acquire(y, pre, post, nd):
    off = NP + LW + nd; W = NP + LW; tw = np.r_[np.arange(0, W), np.arange(off, off + W)]
    def rep(c):
        u = np.zeros(2 * W, complex); u[c:c + NP] = pre; u[W + c:W + c + NP] = post; return u
    def metric(r):
        return np.array([abs(np.vdot(pre, r[c:c + NP])) ** 2 + abs(np.vdot(post, r[W + c:W + c + NP])) ** 2 for c in range(LW + 1)])
    r = y[tw].copy(); ls = []
    while len(ls) < CFG['max_paths']:
        m = metric(r)
        if ls:
            m[np.array(ls)] = 0
        c = int(np.argmax(m))
        if m[c] < CFG['kappa'] * np.median(m[m > 0]):
            break
        U1 = rep(c)[None, :]; v1, g1 = mk.estimate(r, U1, tw, mk.CFG['grid'], 1)
        r = r - g1[0] * U1[0] * np.exp(2j * np.pi * v1[0] * tw / NREF); ls.append(c)
    if not ls:
        ls = [int(np.argmax(metric(y[tw])))]
    ls = np.array(sorted(ls), int); U = np.array([rep(c) for c in ls]); nh, gh = mk.estimate(y[tw], U, tw, mk.CFG['grid'], 3)
    return ls, nh, gh


def coherence(y, ls, nh, sh, nd):
    """A[r, q] = Re(M[r, q] conj(s_r) s_q) / (|s_r| |s_q|): about |g_r| |g_q| when r and q carry the same data stream, about 0
    otherwise.  Each user is a rank-one block whose eigenvalue is that user's captured power; the rest is a noise bulk whose
    edge is pw * sqrt(2 n / nd) (pw = mean received power on the data block)."""
    t0 = NP + LW; n = np.arange(nd); yd = y[t0:t0 + nd]
    Z = np.array([y[t0 + c + n] * np.exp(-2j * np.pi * v * (t0 + c + n) / NREF) for c, v in zip(ls, nh)])
    M = (Z @ Z.conj().T) / nd; a = np.abs(sh) + 1e-12
    A = np.real(M * np.outer(sh.conj(), sh)) / np.outer(a, a); np.fill_diagonal(A, a ** 2)
    return A, float(np.mean(np.abs(yd) ** 2))


def spectral_k(A, pw, nd, rng, k_force=None):
    n = len(A); w, V = np.linalg.eigh((A + A.T) / 2); w, V = w[::-1], V[:, ::-1]
    edge = pw * np.sqrt(2 * n / nd); k = int(np.sum(w > CFG['edge_margin'] * edge)) if k_force is None else int(k_force); k = max(1, min(k, n))
    if k == 1:
        return 1, np.zeros(n, int), [float(x) for x in w[:6]], float(edge)
    X = V[:, :k]; X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    return k, kmeans(X, k, rng), [float(x) for x in w[:6]], float(edge)


def kmeans(X, k, rng):
    best = None
    for _ in range(10):
        c = X[rng.choice(len(X), k, replace=False)]
        for _ in range(30):
            lab = np.argmin(((X[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
            c = np.array([X[lab == j].mean(0) if np.any(lab == j) else c[j] for j in range(k)])
        cost = ((X - c[lab]) ** 2).sum()
        if best is None or cost < best[0]:
            best = (cost, lab)
    return best[1]


def wrong_power(ls, lab_hat, l, lab, g):
    """1 - (true path power assigned to the right user under the best matching of clusters to users) / total power."""
    p = np.abs(g) ** 2; pos = {int(c): i for i, c in enumerate(l)}; K = int(lab.max()) + 1; Kh = int(np.max(lab_hat)) + 1 if len(lab_hat) else 1
    P = np.zeros((Kh, K))
    for c, lh in zip(ls, lab_hat):
        i = pos.get(int(c))
        if i is not None:
            P[lh, lab[i]] += p[i]
    r, cidx = linear_sum_assignment(-P)
    return float(1 - P[r, cidx].sum() / p.sum())


def part_trial(rng, K, nd):
    l, nu, g, lab = draw(rng, K); s2 = 10 ** (-CFG['snr_db'] / 10)
    xs = [(rng.choice([-1, 1], nd) + 1j * rng.choice([-1, 1], nd)) / np.sqrt(2) for _ in range(K)]
    y, pre, post = synth(l, nu, g, lab, s2, xs, rng); ls, nh, gh = acquire(y, pre, post, nd)
    A, pw = coherence(y, ls, nh, gh, nd); kh, lab_s, ev, edge = spectral_k(A, pw, nd, rng); _, lab_o, _, _ = spectral_k(A, pw, nd, rng, k_force=K)
    kc = max(1, int(round(len(ls) / 6.0))); X = np.c_[(ls - ls.mean()) / (ls.std() + 1e-9), (nh - nh.mean()) / (nh.std() + 1e-9)]
    lab_c = kmeans(X, min(kc, len(ls)), rng) if kc > 1 else np.zeros(len(ls), int)
    lab_2 = c2.split(y, None, ls, nh, gh, rng)['par'] if nd == c2.N and len(ls) >= 2 else None       # parent's two-user split (needs nd = 1024)
    p = np.abs(g) ** 2; found = set(int(c) for c in ls)
    out = dict(n=int(len(ls)), missed=float(sum(p[i] for i in range(len(l)) if int(l[i]) not in found) / p.sum()), k_hat=kh, k_count=kc, ev=ev, edge=edge,
               wrong_spec=wrong_power(ls, lab_s, l, lab, g), wrong_oracle_k=wrong_power(ls, lab_o, l, lab, g), wrong_count=wrong_power(ls, lab_c, l, lab, g))
    if lab_2 is not None:
        out['wrong_two'] = wrong_power(ls, np.asarray(lab_2), l, lab, g)
    return out


def part_cell(args):
    K, nd = args; rng = np.random.default_rng([SEED, 21, K, nd])
    return dict(K=K, nd=nd, rows=[part_trial(rng, K, nd) for _ in range(CFG['trials'])])


def run_part(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        cells = pool.map(part_cell, [(K, nd) for nd in CFG['nds'] for K in CFG['ks']], chunksize=1)
    (out / 'part_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED), cells=cells, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def read_part(out):
    R = json.loads((out / 'part_rows.json').read_text()); tab = {}; ok = {}
    for c in R['cells']:
        r = c['rows']; key = f"{c['nd']}|{c['K']}"
        tab[key] = dict(k_correct=float(np.mean([x['k_hat'] == c['K'] for x in r])), k_count_correct=float(np.mean([x['k_count'] == c['K'] for x in r])),
                        wrong_spec_median=float(np.median([x['wrong_spec'] for x in r])), wrong_oracle_k_median=float(np.median([x['wrong_oracle_k'] for x in r])),
                        wrong_count_median=float(np.median([x['wrong_count'] for x in r])), wrong_two_median=(float(np.median([x['wrong_two'] for x in r])) if 'wrong_two' in r[0] else None),
                        n_found=float(np.mean([x['n'] for x in r])), missed=float(np.median([x['missed'] for x in r])), k_hat_mean=float(np.mean([x['k_hat'] for x in r])),
                        ev_mean=[float(v) for v in np.mean([x['ev'][:6] + [0] * (6 - len(x['ev'][:6])) for x in r], axis=0)], edge_mean=float(np.mean([x['edge'] for x in r])))
        ok[key] = bool(tab[key]['k_correct'] >= 0.80 and tab[key]['wrong_spec_median'] <= 0.10)
    kmax = {str(nd): max([0] + [K for K in CFG['ks'] if all(ok[f'{nd}|{j}'] for j in CFG['ks'] if j <= K)]) for nd in CFG['nds']}
    t3, t1 = tab['1024|3'], tab['1024|1']
    res = dict(table=tab, ok=ok, k_max=kmax,
               direction=dict(k123_ok_at_1024=bool(all(ok[f'1024|{k}'] for k in (1, 2, 3))), two_user_method_fails_k3=bool(t3['wrong_two_median'] is not None and t3['wrong_two_median'] >= 0.25),
                              two_user_method_fails_k1=bool(t1['wrong_two_median'] is not None and t1['wrong_two_median'] >= 0.20)),
               scaling=dict(nondecreasing=bool(kmax['512'] <= kmax['1024'] <= kmax['2048']), gain_512_to_2048=int(kmax['2048'] - kmax['512'])))
    dead = tab['1024|3']['k_correct'] < 0.5 or tab['1024|3']['wrong_spec_median'] > 0.20
    d = res['direction']; s = res['scaling']
    res['verdict'] = 'KILL' if dead else 'PASS' if d['k123_ok_at_1024'] and d['two_user_method_fails_k3'] and s['nondecreasing'] and s['gain_512_to_2048'] >= 1 else 'UNDETERMINED'
    (out / 'part_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


# ---------------------------------------------------------------- decoding stage (project code, rate 1/4)
def dec_job(frame):
    import l2_r3_collide3 as c3
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    C = c3.setup(); stage3, ctx = C['stage3'], C['ctx']; nd = c3.N; cfg = CFG['dec']
    ctx.code = build_code(2048, d_v=3, d_c=cfg['dc'], seed=20260726, cache_dir=HERE / 'out_r3b17' / 'code-cache'); ctx.H = np.asarray(ctx.code['H']).astype(np.int32)
    gd = stage3.e1.gd; rec = dict(frame=frame, cells={})
    xs_all, truths_all = [], []
    for j in range(4):
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame + 5000 * j, 'U', 100), 100, 500)
        xs_all.append(np.asarray(raw['data'], complex) / c3.scale_of(raw, obs) / np.sqrt(c3.CFG['pd'])); truths_all.append(truth)
    for K, snr in cfg['cells']:
        rng = np.random.default_rng([SEED, 22, frame, K, int(snr * 10)]); s2 = 10 ** (-snr / 10)
        l, nu, g, lab = draw(rng, K); xs, truths = xs_all[:K], truths_all[:K]
        y, pre, post = synth(l, nu, g, lab, s2, xs, rng); yd = y[c3.T0:c3.T0 + nd]
        ls, nh, gh = acquire(y, pre, post, nd); A, pw = coherence(y, ls, nh, gh, nd); kh, lab_s, ev, edge = spectral_k(A, pw, nd, rng)
        pos = {int(c): i for i, c in enumerate(l)}; hit = [(k, pos[int(c)]) for k, c in enumerate(ls) if int(c) in pos]
        kk = np.array([k for k, _ in hit], int); gl = np.array([lab[i] for _, i in hit], int)
        def decode(L_, V_, G_, lb):
            lb = np.asarray(lb); streams = [(L_[lb == u], V_[lb == u], G_[lb == u]) for u in range(int(lb.max()) + 1) if np.any(lb == u)]
            done = c3.turbo2(C, streams, yd, s2)[0]
            got = set(j for d in done if d is not None for j, tr in enumerate(truths) if int(gd.score(ctx, d, tr)) == 0)
            return int(len(got) == K), len(got)
        out = dict(n=int(len(ls)), k_hat=kh, wrong_spec=wrong_power(ls, lab_s, l, lab, g))
        out['genie'], out['genie_n'] = decode(ls[kk], nh[kk], gh[kk], gl)
        out['spec'], out['spec_n'] = decode(ls, nh, gh, lab_s)
        if K != 2 and len(ls) >= 2:                                   # the parent's method assumes exactly two users
            out['two'], out['two_n'] = decode(ls, nh, gh, c2.split(y, None, ls, nh, gh, rng)['par'])
        rec['cells'][f'{K}|{snr}'] = out
    return [rec]


def run_dec(out):
    out.mkdir(parents=True, exist_ok=True); path = out / 'dec_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(dec_job, list(range(*CFG['dec']['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'dec_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=nrow, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read_dec(out):
    rows = [json.loads(x) for x in gzip.open(out / 'dec_rows.jsonl.gz', 'rt')]; res = dict(frames=len(rows), table={})
    for key in rows[0]['cells']:
        c = [r['cells'][key] for r in rows]
        res['table'][key] = {a: float(np.mean([x[a] for x in c])) for a in ('genie', 'spec', 'two', 'k_hat', 'wrong_spec', 'genie_n', 'spec_n', 'n') if a in c[0]}
        res['table'][key]['k_correct'] = float(np.mean([x['k_hat'] == int(key.split('|')[0]) for x in c]))
    k3 = [k for k in res['table'] if k.startswith('3|') and res['table'][k]['genie'] >= 0.80]
    if not k3:
        res['verdict'] = 'UNDETERMINED_GENIE_LOW'
    else:
        g = float(np.mean([res['table'][k]['genie'] for k in k3])); s = float(np.mean([res['table'][k]['spec'] for k in k3])); t = float(np.mean([res['table'][k].get('two', 0.0) for k in k3]))
        res['pooled_k3'] = dict(genie=g, spec=s, two=t)
        res['verdict'] = 'PASS' if s >= 0.60 and g - s <= 0.15 and s - t >= 0.35 else 'KILL' if g - s > 0.30 else 'UNDETERMINED'
    res['k1_false_split'] = 1 - res['table']['1|8.0']['k_correct'] if '1|8.0' in res['table'] else None
    (out / 'dec_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'part', 'readpart', 'dec', 'readdec')); ap.add_argument('--out', default='out_r3b21'); a = ap.parse_args(); o = HERE / a.out
    if a.mode == 'smoke':
        for K, nd in ((1, 1024), (3, 1024), (4, 1024)):
            rng = np.random.default_rng([7, K]); t0 = time.process_time(); r = [part_trial(rng, K, nd) for _ in range(6)]
            print(K, nd, 'cpu/trial', round((time.process_time() - t0) / 6, 2), 'k_hat', [x['k_hat'] for x in r], 'wrong spec', [round(x['wrong_spec'], 2) for x in r], 'two', [round(x.get('wrong_two', -1), 2) for x in r],
                  'count', [x['k_count'] for x in r], 'ev', [round(v, 2) for v in r[0]['ev'][:5]], 'edge', round(r[0]['edge'], 2))
    else:
        dict(part=run_part, readpart=read_part, dec=run_dec, readdec=read_dec)[a.mode](o)
