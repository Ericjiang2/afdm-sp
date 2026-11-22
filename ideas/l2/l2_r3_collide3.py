#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 step 3 for card I-20261122-l09 (2026-11-22, runner l, claude-fable-5.2): two-user joint
decoding after the split (card criterion ii).  Both users send the same 256-sample preamble AND postamble (the preamble
alone leaves the Doppler at .13 bin, about 1 rad of phase drift by the end of the data, so coherent detection cannot start).
Source: l2_r3_collide.py (draw), l2_r3_collide2.py (split imported; its acquire uses one marker, rewritten here for two),
l2_r3_marker.py (estimate), l2_l09_coded.py (setup, scale_of imported; its turbo is single-user, the two-user version is here).
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch16.md.
  python l2_r3_collide3.py smoke|run|read --out out_r3b16
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r3_collide as col  # noqa: E402
import l2_r3_collide2 as c2  # noqa: E402
import l2_r3_marker as mk  # noqa: E402
from l2_l09_coded import setup, SEED, scale_of  # noqa: E402

WORKERS, N, NP, LW = 12, c2.N, c2.NP, c2.LW
T0, OFF = NP + LW, NP + LW + N                       # first data sample (delay 0); start of the postamble
CFG = dict(frames=[57010, 57060], snrs_db=[8.0, 10.0, 12.0, 14.0], dps_db=[3.0, 6.0], eta=0.0, rounds=8, dec_iters=50, pd=0.5,
           kappa=12.0, max_paths=24, arms=['genie_part', 'par_abs', 'par', 'kmeans', 'capture_sic'])


def synth(l, nu, g, lab, s2, xs, rng):
    pre, post = (np.exp(2j * np.pi * rng.uniform(size=NP)) for _ in range(2))
    s = [np.r_[pre, x[-LW:], x, post] for x in xs]
    T = OFF + NP + LW; t = np.arange(T); y = np.zeros(T, complex)
    for li, vi, gi, u in zip(l, nu, g, lab):
        out = np.zeros(T, complex); out[li:li + len(s[u])] = s[u]; y += gi * out * np.exp(2j * np.pi * vi * t / N)
    return y + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T)), pre, post, t


def acquire(y, pre, post):
    """Path-by-path cancellation on the two marker windows (non-coherent sum of the two correlations picks the delay),
    then one joint Doppler / gain fit of all found paths on both windows."""
    tw = np.r_[np.arange(0, NP + LW), np.arange(OFF, OFF + NP + LW)]; W = NP + LW
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
        r = r - g1[0] * U1[0] * np.exp(2j * np.pi * v1[0] * tw / N); ls.append(c)
    if not ls:
        ls = [int(np.argmax(metric(y[tw])))]
    ls = np.array(sorted(ls), int); U = np.array([rep(c) for c in ls])
    nh, gh = mk.estimate(y[tw], U, tw, mk.CFG['grid'], 3)
    return ls, nh, gh


def build_h(ls, nh, gh):
    """Data-block channel of one stream for the project's symbols (power pd): column m = symbol m, cyclic through the prefix."""
    H = np.zeros((N, N), complex); n = np.arange(N)
    for c, v, g in zip(ls, nh, gh):
        H[n, (n - int(c)) % N] += g * np.exp(2j * np.pi * v * (T0 + n) / N)
    return H / np.sqrt(CFG['pd'])


def reest(yd, streams, soft, conf):
    """Decision-directed refit on the data block.  Each path keeps its delay; its Doppler is searched over the marker
    estimate plus whole ambiguity intervals (N / marker spacing) and +-0.04 around them; gains by projection.  Two passes
    over all paths (SAGE).  Only streams whose soft symbols are confident (conf) are refitted."""
    n = np.arange(N); tt = T0 + n; cyc = N / OFF
    cand = np.add.outer(cyc * np.arange(-2, 3), np.arange(-0.04, 0.0401, 0.01)).ravel()
    reg = lambda u, c: soft[u][(n - int(c)) % N] / np.sqrt(CFG['pd'])
    comp = lambda u, c, v, g: g * reg(u, c) * np.exp(2j * np.pi * v * tt / N)
    res = yd - sum(comp(u, c, v, g) for u, (L_, V_, G_) in enumerate(streams) for c, v, g in zip(L_, V_, G_))
    new = [(L_.copy(), V_.copy(), G_.copy()) for L_, V_, G_ in streams]
    for _ in range(2):
        for u, (L_, V0, _) in enumerate(streams):
            if not conf[u]:
                continue
            for i, c in enumerate(L_):
                r = reg(u, c); en = float(np.vdot(r, r).real)
                if en < 1e-9:
                    continue
                res = res + comp(u, c, new[u][1][i], new[u][2][i])
                vs = V0[i] + cand; corr = np.exp(-2j * np.pi * np.outer(vs, tt) / N) @ (np.conj(r) * res); k = int(np.argmax(np.abs(corr)))
                new[u][1][i] = vs[k]; new[u][2][i] = corr[k] / en
                res = res - comp(u, c, new[u][1][i], new[u][2][i])
    return new


def turbo2(C, streams, yd, s2, refit=True):
    """Soft-cancellation LMMSE over all streams at once, one LDPC decoder per stream; a stream whose syndrome checks is
    frozen at its decision.  streams: list of (delays, Dopplers, gains) from the markers; after every round the paths of
    confident streams are refitted on the data block from the decoders' a-posteriori soft symbols.
    Returns the decoded words (None if not decoded), the final a-posteriori soft symbols and the final path parameters."""
    from messages import moments
    ctx = C['ctx']; dec_fn = ctx.native.decoder_messages; pd = CFG['pd']; a = np.sqrt(pd / 2); K = len(streams)
    cur = [(np.asarray(L_, int), np.asarray(V_, float).copy(), np.asarray(G_, complex).copy()) for L_, V_, G_ in streams]
    pri = [np.zeros(2 * N) for _ in range(K)]; app = [np.zeros(2 * N) for _ in range(K)]; done = [None] * K
    for _ in range(CFG['rounds']):
        H = np.hstack([build_h(*c) for c in cur])
        mv = [moments(np.clip(p, -20, 20), pd) for p in pri]
        mu = np.concatenate([m[0] for m in mv]); v = np.concatenate([m[1] for m in mv])
        Fm = np.linalg.solve((H * v[None, :]) @ H.conj().T + s2 * np.eye(N), H)
        s = np.maximum(np.real(np.sum(H.conj() * Fm, axis=0)), 1e-12); z = mu + (Fm.conj().T @ (yd - H @ mu)) / s; eta = np.maximum(1 / s - v, 1e-9)
        for k in range(K):
            if done[k] is not None:
                continue
            zk, ek = z[k * N:(k + 1) * N], eta[k * N:(k + 1) * N]
            dec = dec_fn(ctx.code, np.clip(np.concatenate([4 * a * zk.real / ek, 4 * a * zk.imag / ek]), -20, 20), maxiter=CFG['dec_iters'])
            app[k] = np.asarray(dec['raw_app'], float)
            if bool(dec['decode_ok']):
                done[k] = dec['decoded']; pri[k] = 20 * np.sign(app[k]); app[k] = pri[k]
            else:
                pri[k] = np.asarray(dec['raw_check_extrinsic'], float)
        if all(d is not None for d in done):
            break
        if refit:
            soft = [moments(np.clip(x, -20, 20), pd)[0] for x in app]
            conf = [float(np.mean(np.abs(x) ** 2)) / pd >= 0.5 for x in soft]
            if any(conf):
                cur = reest(yd, [(c[0], st[1], c[2]) for c, st in zip(cur, streams)], soft, conf)
    soft = [moments(np.clip(x, -20, 20), pd)[0] for x in app]
    return done, soft, cur


def both_ok(C, done, truths):
    if any(d is None for d in done) or len(done) != 2:
        return 0
    gd = C['stage3'].e1.gd; ctx = C['ctx']; e = [[int(gd.score(ctx, d, tr)) for tr in truths] for d in done]
    return int((e[0][0] == 0 and e[1][1] == 0) or (e[0][1] == 0 and e[1][0] == 0))


def capture_sic(C, ls, nh, gh, yd, s2, truths):
    """Naive serial baseline, no split from second-order statistics: decode one stream through the sum channel (all found
    paths, refitted from its own soft symbols); if it decodes, subtract it, give the second stream the paths whose refitted
    gain fell below half of the marker gain, and decode that on the residual."""
    done1, soft1, cur1 = turbo2(C, [(ls, nh, gh)], yd, s2)
    if done1[0] is None:
        return 0
    fin = reest(yd, [(ls, nh, cur1[0][2])], soft1, [True])[0]
    yres = yd - build_h(*fin) @ soft1[0]
    keep = np.abs(fin[2]) < 0.5 * np.abs(gh)
    if not keep.any():
        return 0
    done2, _, _ = turbo2(C, [(ls[keep], nh[keep], gh[keep])], yres, s2)
    return both_ok(C, [done1[0], done2[0]], truths)


VARIANTS = dict(base={}, lowrate=dict(frames=[57100, 57130], snrs_db=[4.0, 6.0, 8.0], dps_db=[0.0, 3.0], dc=4))   # lowrate: PREDICTIONS_r3_batch18.md


def job(arg):
    frame, variant = arg if isinstance(arg, tuple) else (arg, 'base'); cfg = dict(CFG, **VARIANTS[variant])
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; rec = dict(frame=frame, cells={})
    if cfg.get('dc'):                                   # (3, d_c) code of the same length, built by l2_r3_rate.py gate
        from afdm_sp_joint_unrolled.e1_ldpc import build_code
        ctx.code = build_code(2048, d_v=3, d_c=cfg['dc'], seed=20260726, cache_dir=HERE / 'out_r3b17' / 'code-cache')
        ctx.H = np.asarray(ctx.code['H']).astype(np.int32); rec['k'] = int(ctx.code['k'])
    xs, truths = [], []
    for f in (frame, frame + 5000):
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, f, 'U', 100), 100, 500)
        xs.append(np.asarray(raw['data'], complex) / scale_of(raw, obs) / np.sqrt(CFG['pd'])); truths.append(truth)
    rec['x_power'] = [float(np.mean(np.abs(x) ** 2)) for x in xs]
    for snr in cfg['snrs_db']:
        for dp in cfg['dps_db']:
            rng = np.random.default_rng([SEED, 16, frame, int(snr * 10), int(dp * 10)]); s2 = 10 ** (-snr / 10)
            l, nu, g, lab = col.draw(rng, CFG['eta'], dp); p = np.abs(g) ** 2
            y, pre, post, t = synth(l, nu, g, lab, s2, xs, rng); yd = y[T0:T0 + N]
            ls, nh, gh = acquire(y, pre, post); labs = c2.split(y, t, ls, nh, gh, rng)
            pos = {int(c): i for i, c in enumerate(l)}; hit = [(k, pos[int(c)]) for k, c in enumerate(ls) if int(c) in pos]
            out = dict(n=int(len(ls)), false=int(len(ls) - len(hit)), missed=float(1 - sum(p[i] for _, i in hit) / p.sum()),
                       nu_mae_w=float(sum(p[i] * abs(nh[k] - nu[i]) for k, i in hit) / max(sum(p[i] for _, i in hit), 1e-12)))
            for name in ('par_abs', 'par', 'kmeans'):
                out['mis_' + name] = c2.score(ls, labs[name], l, lab, g)[0]
            def joint(L_, V_, G_, lb):
                lb = np.asarray(lb)
                return both_ok(C, turbo2(C, [(L_[lb == u], V_[lb == u], G_[lb == u]) for u in (0, 1)], yd, s2)[0], truths)
            kk = np.array([k for k, _ in hit], int); gl = np.array([lab[i] for _, i in hit], int)
            out['genie_part'] = joint(ls[kk], nh[kk], gh[kk], gl) if len(set(gl)) == 2 else 0
            out['cycle_wrong_power'] = float(sum(p[i] for k, i in hit if abs(nh[k] - nu[i]) > 0.3) / p.sum())
            for name in ('par_abs', 'par', 'kmeans'):
                out[name] = joint(ls, nh, gh, labs[name]) if len(set(labs[name])) == 2 else 0
            out['capture_sic'] = capture_sic(C, ls, nh, gh, yd, s2, truths)
            rec['cells'][f'{snr}|{dp}'] = out
    return [rec]


def run(out, variant='base'):
    cfg = dict(CFG, **VARIANTS[variant]); out.mkdir(parents=True, exist_ok=True); path = out / 'collide3_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, [(f, variant) for f in range(*cfg['frames'])]):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    chd = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'collide3_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(cfg, variant=variant, seed=SEED, workers=WORKERS, N=N, NP=NP, LW=LW), rows=nrow,
        core_hours=(chd.ru_utime + chd.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((chd.ru_utime + chd.ru_stime) / 3600, 3))


def read(out):
    rows = [json.loads(x) for x in gzip.open(out / 'collide3_rows.jsonl.gz', 'rt')]; n = len(rows); res = dict(frames=n, table={})
    keys = list(rows[0]['cells'])
    for k in keys:
        c = [r['cells'][k] for r in rows]
        res['table'][k] = dict(**{a: float(np.mean([x[a] for x in c])) for a in CFG['arms']}, n_found=float(np.mean([x['n'] for x in c])),
                               missed=float(np.median([x['missed'] for x in c])), cycle_wrong_power=float(np.mean([x['cycle_wrong_power'] for x in c])), nu_mae_w=float(np.mean([x['nu_mae_w'] for x in c])),
                               **{m: float(np.median([x[m] for x in c])) for m in ('mis_par_abs', 'mis_par', 'mis_kmeans')})
    ok = [k for k in keys if res['table'][k]['genie_part'] >= 0.70]
    pooled = {a: (float(np.mean([r['cells'][k][a] for r in rows for k in ok])) if ok else None) for a in CFG['arms']}
    res['cells_ok'] = ok; res['pooled_over_cells_ok'] = pooled
    if len(ok) < 2:
        res['verdict'] = 'UNDETERMINED_FEW_CELLS'
    else:
        best_base = max(pooled['kmeans'], pooled['capture_sic'])                       # primary arm: 'par' (see PREDICTIONS_r3_batch16.md)
        passed = pooled['par'] >= best_base + 0.35 and pooled['genie_part'] - pooled['par'] <= 0.10
        dead = pooled['genie_part'] - pooled['par'] > 0.25 or pooled['capture_sic'] >= pooled['par'] - 0.10
        res['verdict'] = 'PASS' if passed else 'KILL' if dead else 'UNDETERMINED'
    (out / 'collide3_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', default='out_r3b16'); ap.add_argument('--variant', default='base'); a = ap.parse_args()
    if a.mode == 'smoke':
        CFG['snrs_db'] = [12.0, 14.0]; CFG['dps_db'] = [6.0, 3.0]; t0 = time.process_time()
        for f in (57000, 57002):
            r = job(f)[0]; print(f, {k: {a: v[a] for a in CFG['arms'] + ['n', 'cycle_wrong_power']} for k, v in r['cells'].items()}, flush=True)
        print('cpu', time.process_time() - t0)
    else:
        run(HERE / a.out, a.variant) if a.mode == 'run' else read(HERE / a.out)
