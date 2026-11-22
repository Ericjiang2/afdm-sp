"""L2 runner c batch 1 (PREDICTIONS_c20261122_batch1.md): round-0 Doppler from pilot MF vs pilot + anchor data-lag
spectrum (card I-20261122-c02), injected with true delays into the project receiver.
  python l2_c02_fused.py run --out out_c20261122b1 ; python l2_c02_fused.py read --out out_c20261122b1"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
EXP = Path(__file__).resolve().parents[2] / 'experiments/data_pilot_fer_20261121'; sys.path.insert(0, str(EXP))
import stageA, stageA2
from physical import daft
RHO, SNRS, FRAMES, SCEN, WORKERS = 100, (450, 550), range(41000, 41060), ('U', 'G'), 9
PAD, GRID = 20, 3.0


def spec(v, n):
    F = np.fft.fft(v, n * PAD); fq = np.fft.fftfreq(n * PAD, 1 / n); m = np.abs(fq) <= GRID; o = np.argsort(fq[m])
    return fq[m][o], F[m][o]


def estimates(r, pt, l, n, c1):
    k = np.arange(n)
    cpp = lambda kk, ll: np.where(kk < ll, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (kk - ll))), 1.)
    mf = []
    for li in l:
        grid, F = spec(r * np.conj(cpp(k, li) * pt[(k - li) % n]), n); mf.append(np.abs(F) ** 2)
    mf = np.array(mf); ep = grid[np.argmax(mf, 1)]; a = int(np.argmax(mf.max(1))); ef = ep.copy()
    for i in range(len(l)):
        if i == a:
            continue
        Dl = l[i] - l[a]; z = np.conj(r) * np.roll(r, -Dl); dem = np.conj(np.conj(cpp(k, l[a])) * cpp((k + Dl) % n, l[i]))
        gl, L = spec(z * dem, n); Li = np.interp(grid - ep[a], gl, np.abs(L) ** 2, left=0, right=0)
        ef[i] = grid[np.argmax(mf[i] / np.median(mf[i]) + Li / np.median(np.abs(L) ** 2))]
    return ep, ef


def arm(C, obs, truth, nu):
    st, ctx = C['stage3'], C['ctx']
    pert = dict(truth, k_real=list(map(float, nu)))
    dec, arrays, syndrome, _ = stageA2.f0_true(C, obs, pert, 'ls')
    if syndrome:
        br = st.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1'); return int(st.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    return int(st.e1.gd.score(ctx, dec['decoded'], truth))


def job(args):
    frame, s_, snrs = args; C = stageA.setup(); st, ctx = C['stage3'], C['ctx']; c1, c2 = ctx.system.c1, ctx.system.c2
    base = st.inputs(ctx, frame, s_, RHO); rows = []
    for snr in snrs:
        raw, obs, truth = st.observed(ctx, base, RHO, snr)
        y = np.asarray(raw['y']); n = len(y); l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float)
        pw = np.abs(np.asarray(truth['g_i'])) ** 2
        ep, ef = estimates(daft(y, c1, c2, True), daft(np.asarray(raw['pilot']), c1, c2, True), l, n, c1)
        rec = dict(frame=frame, scenario=s_, snr=snr, err={}, r0={})
        for name, v in (('ldop', nu), ('pilot', ep), ('fused', ef)):
            rec['err'][name] = arm(C, obs, truth, v); rec['r0'][name] = float(np.sum(pw * np.abs(v - nu)) / pw.sum())
        rows.append(rec)
    return rows


def read(out):
    rows = [json.loads(x) for x in open(out / 'rows.jsonl')]; arms = ('ldop', 'pilot', 'fused')
    F = {a: np.array([r['err'][a] > 0 for r in rows], float) for a in arms}
    res = dict(n=len(rows), fer={a: F[a].mean() for a in arms}, r0={a: float(np.mean([r['r0'][a] for r in rows])) for a in arms})
    for snr in sorted({r['snr'] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r['snr'] == snr]; res[f'fer_{snr}'] = {a: F[a][idx].mean() for a in arms}
    rng = np.random.default_rng(20261122); B = rng.integers(0, len(rows), (2000, len(rows)))
    d = (F['pilot'][B] - F['fused'][B]).mean(1); gap = (F['pilot'][B] - F['ldop'][B]).mean(1)
    res['diff'] = float((F['pilot'] - F['fused']).mean()); res['diff_ci'] = np.percentile(d, [2.5, 97.5]).tolist()
    res['gap'] = float((F['pilot'] - F['ldop']).mean()); res['recovered'] = res['diff'] / res['gap'] if res['gap'] else None
    res['recovered_ci'] = np.percentile(d / np.maximum(gap, 1e-9), [2.5, 97.5]).tolist()
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--out', default='out_c20261122b1'); ap.add_argument('--snrs', default='450,550'); ap.add_argument('--frames', default='41000,41060'); a = ap.parse_args()
    SNRS = tuple(int(x) for x in a.snrs.split(',')); FRAMES = range(*map(int, a.frames.split(',')))
    out = Path(__file__).parent / a.out; out.mkdir(exist_ok=True)
    if a.cmd == 'run':
        with get_context('spawn').Pool(WORKERS) as p, open(out / 'rows.jsonl', 'w') as fh:
            for rows in p.imap_unordered(job, [(f, s, SNRS) for f in FRAMES for s in SCEN]):
                for r in rows:
                    print(json.dumps(r), file=fh, flush=True)
    read(out)
