# Round 8 (runner l) read-only probe, follow-up to the Neon audit of dropped draft 1.
# Question: in the line-spectrum form of chirp-pilot AFDM channel estimation (integer delay, fractional Doppler:
# y[n] = sum_i h_i exp(j 2 pi f_i n) + w), does converged batch EM-SBL on a fine grid keep an accuracy edge
# (>= 0.5 dB reconstruction NMSE) over Newtonized OMP when paths sit closer than one resolution cell and the pilot SNR is low?
# If NOMP is within 0.2 dB, a near-linear same-accuracy rival exists and the compute-ledger draft stays dropped.
# Writes nothing. Run: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /opt/anaconda3/bin/python <file>
import numpy as np, time

def atoms(f, N):
    return np.exp(2j * np.pi * np.outer(np.arange(N), f)) / np.sqrt(N)

def nomp(y, s2, N, over=4, Rs=3, Rc=3, pfa=1e-2, kmax=16):
    n = np.arange(N); tau = s2 * (np.log(N) - np.log(np.log(1 / (1 - pfa))))
    def newton(f, r):
        for _ in range(Rs):
            e = np.exp(-2j * np.pi * f * n); c = np.sum(r * e); c1 = np.sum(-2j * np.pi * n * r * e); c2 = np.sum(-(2 * np.pi * n) ** 2 * r * e)
            S1 = 2 * np.real(np.conj(c) * c1); S2 = 2 * (abs(c1) ** 2 + np.real(np.conj(c) * c2))
            if S2 < 0: f = f - S1 / S2
        return f
    fs = []; g = np.zeros(0, complex); r = y.copy()
    while len(fs) < kmax:
        spec = np.fft.fft(r, over * N) / np.sqrt(N); k = int(np.argmax(abs(spec)))
        if abs(spec[k]) ** 2 < tau: break
        fs.append(newton(k / (over * N), r))
        for _ in range(Rc):
            A = atoms(np.array(fs), N); g = np.linalg.lstsq(A, y, rcond=None)[0]; r = y - A @ g
            for i in range(len(fs)):
                ri = r + g[i] * A[:, i]; fs[i] = newton(fs[i], ri); A[:, i] = atoms(np.array([fs[i]]), N)[:, 0]
                g[i] = np.vdot(A[:, i], ri); r = ri - g[i] * A[:, i]
        A = atoms(np.array(fs), N); g = np.linalg.lstsq(A, y, rcond=None)[0]; r = y - A @ g
    return (atoms(np.array(fs), N) @ g if fs else np.zeros(N, complex)), len(fs)

def sbl(y, s2, N, over=8, iters=300, rule="mackay"):
    # batch SBL on a fixed fine grid, known noise variance; rule = "em" (plain EM) or "mackay" (fixed-point, much faster to converge)
    G = over * N; Phi = atoms(np.arange(G) / G, N); gam = abs(Phi.conj().T @ y) ** 2 / N + 1e-12
    for it in range(iters):
        C = (Phi * gam) @ Phi.conj().T + s2 * np.eye(N)
        Ci = np.linalg.inv(C); mu = gam * (Phi.conj().T @ (Ci @ y))
        q = np.real(np.sum(Phi.conj() * (Ci @ Phi), axis=0))          # phi_g^H C^-1 phi_g
        new = abs(mu) ** 2 / np.maximum(gam * q, 1e-12) if rule == "mackay" else abs(mu) ** 2 + gam - gam ** 2 * q
        new = np.maximum(new, 1e-14)
        done = np.max(abs(new - gam)) < 1e-5 * np.max(gam); gam = new
        if done: break
    C = (Phi * gam) @ Phi.conj().T + s2 * np.eye(N); mu = gam * (Phi.conj().T @ np.linalg.solve(C, y))
    return Phi @ mu, int(np.sum(gam > 1e-3 * gam.max())), it + 1

if __name__ == "__main__":
    N, P, T = 64, 6, 24; t0 = time.time()
    print("N=%d P=%d trials=%d; NMSE of the reconstructed pilot response in dB (mean over trials); gap = NOMP - SBL" % (N, P, T))
    for sep in (0.4, 0.7, 2.0):
        for snr in (0, 5, 15):
            e = {"oracle": [], "nomp": [], "sbl": [], "em": []}; kn = []; ks = []; its = []
            for tr in range(T):
                rng = np.random.default_rng(1000 * tr + int(10 * sep) + snr)
                base = np.sort(rng.choice(np.arange(4, N - 4, 5), P // 2, replace=False)).astype(float) + rng.uniform(-.5, .5, P // 2)
                f = np.concatenate([base, base + sep * rng.choice([-1, 1], P // 2)]) / N     # P/2 pairs, each pair `sep` cells apart
                h = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2) * 10 ** (-rng.uniform(0, 10, P) / 20)
                s = atoms(f, N) @ h * np.sqrt(N); s2 = np.mean(abs(s) ** 2) / 10 ** (snr / 10)
                y = s + np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
                A = atoms(f, N); e["oracle"].append(np.sum(abs(A @ np.linalg.lstsq(A, y, rcond=None)[0] - s) ** 2) / np.sum(abs(s) ** 2))
                sn, k1 = nomp(y, s2, N); e["nomp"].append(np.sum(abs(sn - s) ** 2) / np.sum(abs(s) ** 2)); kn.append(k1)
                ss, k2, i2 = sbl(y, s2, N); e["sbl"].append(np.sum(abs(ss - s) ** 2) / np.sum(abs(s) ** 2)); ks.append(k2); its.append(i2)
                if tr < 6: se, _, _ = sbl(y, s2, N, iters=300, rule="em"); e["em"].append(np.sum(abs(se - s) ** 2) / np.sum(abs(s) ** 2))
            db = {k: 10 * np.log10(np.mean(v)) for k, v in e.items()}
            print(f"pair spacing {sep:.1f} cell, SNR {snr:2d} dB: oracle {db['oracle']:6.2f} | NOMP {db['nomp']:6.2f} (K={np.mean(kn):.1f}) | SBL-MacKay {db['sbl']:6.2f} (K={np.mean(ks):.1f}, {np.mean(its):.0f} it) | plain EM x300 (6 trials) {db['em']:6.2f} | NOMP - SBL {db['nomp']-db['sbl']:+.2f} dB")
    print("elapsed %.1f s" % (time.time() - t0))
