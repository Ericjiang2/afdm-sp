# Round 8 (runner l) read-only probe, draft 26 (de-prior ledger): the receiver is not given a bound on the common frequency offset.
# A chirp pilot cannot tell (delay l, Doppler nu) from (l - m, nu - K*m): an offset beyond K/2 bins folds every path along that ridge.
# The pilot-only fit is still perfect, but the model is wrong for the data.  Existing parts: test the few ridge shifts c with a blind
# constellation metric after equalization (modulus dispersion of the DAFT-domain outputs).  Does that already remove the prior?
# N=1024, K=5, 6 paths (count known), per-path Doppler +-1.5 bins, common offset uniform in +-6 bins, rho=0.3, 5 dB.  Writes nothing.
import numpy as np, time
import l_probe_r8_pn_joint as m

N, K, P, RHO, LW = m.N, m.K, m.P, m.RHO, m.LW; n = m.n; CH = m.CH; S2 = m.S2; G = m.G

def estimate(yv, reg):
    dl = np.arange(-3, LW + 3); R = np.stack([np.conj(np.roll(reg, int(l))) for l in dl], 0); ls, nus = [], []; res = yv.copy()
    for _ in range(P):
        C = abs(np.fft.fft(res[None, :] * R, 2 * N, axis=1)); C[:, 6:2 * N - 5] = 0
        i, k = np.unravel_index(int(np.argmax(C)), C.shape); f = k / 2.0; f = f - N if f > N / 2 else f
        ls.append(int(dl[i])); nus.append(m.zoom(res, reg, int(dl[i]), f)); h, res = m.fit(yv, reg, ls, nus)
    return h, np.array(ls), np.array(nus)

def frame(rng):
    l = np.sort(rng.choice(LW, P, replace=False)); nu = rng.uniform(-1.5, 1.5, P); f0 = rng.uniform(-6, 6)
    pw = 10 ** (-rng.uniform(0, 10, P) / 10); h = np.sqrt(pw / pw.sum()) * np.exp(2j * np.pi * rng.random(P))
    x = (rng.integers(0, 2, N) * 2 - 1 + 1j * (rng.integers(0, 2, N) * 2 - 1)) / np.sqrt(2)
    d = CH * np.fft.ifft(x) * np.sqrt(N); pil = np.sqrt(RHO) * CH; s = pil + np.sqrt(1 - RHO) * d
    truth = m.apply(h, l, nu + f0, s); y = truth + np.sqrt(S2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N)); den = np.sum(abs(truth) ** 2)
    L = lambda est: 10 * np.log10(1 + G * np.sum(abs(truth - m.apply(est[0], est[1], est[2], s)) ** 2) / den)
    gen = estimate(y * np.exp(-2j * np.pi * f0 * n / N), pil); gen = (gen[0], gen[1], gen[2] + f0)       # receiver told the offset
    est = estimate(y, pil); out = {"GEN": L(gen), "FOLD": L(est)}; best = None
    for c in range(-2, 3):
        cand = (est[0] * np.exp(2j * np.pi * (K * c) * 0), est[1] + c, est[2] + K * c)
        hh, _ = m.fit(y, pil, cand[1], cand[2]); cand = (hh, cand[1], cand[2])                             # pilot fit is equally good for every c
        Hm = np.stack([m.apply(cand[0], cand[1], cand[2], np.roll(np.eye(N)[0], j)) for j in range(0, 1)], 1)  # placeholder to keep shapes simple
        Hd = sum(cand[0][p] * np.exp(2j * np.pi * cand[2][p] * n / N)[:, None] * np.roll(np.eye(N), int(cand[1][p]), axis=0) for p in range(P))
        r = y - m.apply(cand[0], cand[1], cand[2], pil)
        dh = Hd.conj().T @ np.linalg.solve((1 - RHO) * Hd @ Hd.conj().T + S2 * np.eye(N), r)
        xh = np.fft.fft(np.conj(CH) * dh) / np.sqrt(N); a = abs(xh) ** 2; disp = np.var(a) / np.mean(a) ** 2
        if best is None or disp < best[0]: best = (disp, c, cand)
    out["TEST"] = L(best[2]); out["mtrue"] = int(np.round(f0 / K)); out["c"] = best[1]
    return out

if __name__ == "__main__":
    t0 = time.time(); rng = np.random.default_rng(11); rs = [frame(rng) for _ in range(10)]
    md = lambda k: float(np.median([r[k] for r in rs]))
    ok = np.mean([r["TEST"] - r["GEN"] < 0.5 for r in rs]); folded = np.mean([r["mtrue"] != 0 for r in rs])
    print(f"SINR loss dB (median over 10 frames): told the offset {md('GEN'):.2f} | folded estimate used as is {md('FOLD'):.2f} | 5-way ridge test with blind modulus metric {md('TEST'):.2f}")
    print(f"frames with offset beyond K/2: {folded:.0%}; test within 0.5 dB of the told-offset receiver in {ok:.0%} of frames; chosen c vs round(f0/K): {[(r['c'], r['mtrue']) for r in rs]}")
    print("elapsed %.1f s" % (time.time() - t0))
