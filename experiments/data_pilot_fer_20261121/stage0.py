"""Stage 0 pre-check (STAGE0_RULES.md): an observable-only autocorrelation candidate selector, scored against the
delays the real F0 round 0 actually kept. F0 runs unchanged (rho-sweep pipeline) only to read its round-0 support.
Reuses unified_cov_prospective_20261119/cstate.py (context, stage3 inputs/observed/f0_state) and the autocorrelation
statistic of data_autocorr_acq_20261121/calc.py.
  python stage0.py --out out/stage0.json        |   python stage0.py --smoke --out out/stage0_smoke.json
"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / 'unified_cov_prospective_20261119'))
sys.path.insert(0, str(EXP / 'data_autocorr_acq_20261121'))
sys.path.insert(0, str(EXP / 'sp_afdm_frozen_20260920' / 'src'))

RHOS = (50, 100, 150)            # permille
SNR = 500                        # centi-dB
FRAMES = range(7000, 7200)
TAU = 0.2                        # relevant iff g >= TAU * sigma2 (internal), as in the readouts
TOP_PEAKS = 32                   # autocorrelation local peaks scanned, highest first
K_NEW = 8                        # new candidate delays kept (not in the F0 round-0 support, not the anchor)

_C = None


def setup():
    global _C
    if _C is None:
        import cstate
        from physical import daft, regressors
        from calc import FMAX, PAD, local_peaks
        ctx, _full, _cd, _ = cstate.context()
        s = ctx.system; lmax = int(s.l_max_cap)
        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
        U = U / np.linalg.norm(U, axis=0, keepdims=True)
        _C = dict(cstate=cstate, ctx=ctx, s=s, lmax=lmax, U=U, daft=daft, FMAX=FMAX, PAD=PAD, local_peaks=local_peaks)
    return _C


def select(y, C):
    """Observable only: anchor from the pilot MF, candidates from autocorrelation peaks (highest first)."""
    s, lmax, U, PAD = C['s'], C['lmax'], C['U'], C['PAD']
    z5 = (np.abs(U.conj().T @ y) ** 2).reshape(lmax + 1, 5)
    c = int(np.argmax(z5)); la, ka = c // 5, c % 5 - 2
    r = C['daft'](y, s.c1, s.c2, inverse=True); n = len(r)
    q = np.stack([r * np.conj(np.roll(r, d)) for d in range(1, lmax + 1)])
    spec = np.fft.fft(q, n=PAD * n, axis=1); f = np.fft.fftfreq(PAD * n, d=1.0 / n)
    keep = np.abs(f) <= C['FMAX']; f, P = f[keep], np.abs(spec[:, keep]) ** 2
    pk = np.argwhere(C['local_peaks'](P))
    order = np.argsort(-P[pk[:, 0], pk[:, 1]])[:TOP_PEAKS]

    def col(l, nu):
        return z5[l, int(np.clip(np.rint(nu), -2, 2)) + 2] if 0 <= l <= lmax else -np.inf

    cands = []
    for i in order:
        k, j = pk[i]; d, fo = int(k) + 1, float(f[j])
        lc = la + d if col(la + d, ka + fo) >= col(la - d, ka - fo) else la - d
        if lc != la and lc not in cands:
            cands.append(int(lc))
    return int(la), cands


def cell_rows(cell):
    s_, rho = cell
    C = setup(); ctx = C['ctx']; stage3 = C['cstate'].stage3
    out = []
    for frame in FRAMES:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, SNR)
        _dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
        r0 = set(int(v) for v in arrays['r0_delays'])
        l = np.asarray(truth['l_i'], int); g = np.abs(np.asarray(truth['g_i'])) ** 2
        relevant = [int(l[i]) for i in range(len(l)) if g[i] >= TAU * float(obs['sigma2'])]
        la, cands = select(obs['y'], C)
        new = [c for c in cands if c not in r0][:K_NEW]
        missed = [d for d in relevant if d not in r0]
        out.append(dict(frame=frame, scenario=s_, rho=rho, syndrome=int(syndrome), anchor_true=bool(la in set(l.tolist())),
                        missed=missed, recovered=[d for d in missed if d in new], new=new,
                        new_true=[c for c in new if c in set(l.tolist())]))
    return out


def summarize(rows):
    miss = sum(len(r['missed']) for r in rows); rec = sum(len(r['recovered']) for r in rows)
    new = sum(len(r['new']) for r in rows); tru = sum(len(r['new_true']) for r in rows)
    return dict(keys=len(rows), missed_relevant=miss, recovered=rec, recall=rec / miss if miss else None,
                new_candidates=new, precision=tru / new if new else None,
                anchor_true=float(np.mean([r['anchor_true'] for r in rows])),
                frames_with_miss=sum(bool(r['missed']) for r in rows), f0_fail=float(np.mean([r['syndrome'] > 0 for r in rows])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    global FRAMES
    if a.smoke:
        FRAMES = range(7000, 7002)
        rows = cell_rows(('U', 100))
        Path(a.out).write_text(json.dumps(dict(n=len(rows), example_keys=sorted(rows[0]))))
        print('SMOKE', len(rows), sorted(rows[0]))
        return
    cells = [(s_, r) for s_ in ('U', 'G') for r in RHOS]
    with get_context('spawn').Pool(len(cells)) as pool:
        res = pool.map(cell_rows, cells)
    rows = [x for part in res for x in part]
    by = {str(r): summarize([x for x in rows if x['rho'] == r]) for r in RHOS}
    pooled = summarize(rows)
    rc = pooled['recall']
    verdict = 'PASS' if rc is not None and rc >= .50 else 'STOP' if rc is None or rc < .25 else 'INCONCLUSIVE'
    out = dict(_argv=sys.argv, rules='STAGE0_RULES.md', frames=[FRAMES.start, FRAMES.stop - 1], snr_centi_db=SNR,
               top_peaks=TOP_PEAKS, k_new=K_NEW, tau=TAU, pooled=pooled, by_rho=by, verdict=verdict)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(verdict=verdict, pooled=pooled, by_rho=by), indent=1))


if __name__ == '__main__':
    main()
