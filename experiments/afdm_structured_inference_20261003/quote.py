"""Arithmetic quote only: never a receiver latency benchmark."""
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.afdm_structured_inference_20261003.common import run, dump

def calculate(output):
    import numpy as np
    rng = np.random.default_rng([20261003, 104129, 0])
    rows = []
    for n, p in [(8, 2), (1024, 8)]:
        b = rng.normal(size=(n,p)) + 1j*rng.normal(size=(n,p))
        x = rng.normal(size=n)+1j*rng.normal(size=n)
        start = time.perf_counter()
        for _ in range(20):
            g = b.conj().T @ b + np.eye(p)
            np.linalg.solve(g, b.conj().T @ x)
            np.fft.fft(x)
        rows.append(dict(n=n,p=p,repeats=20,seconds=time.perf_counter()-start))
    dump(output/'raw.json', rows)
    return dict(rows=rows, purpose='local solve/FFT quotation; no full-chain cost or FER',
                stage_caps='90s each algebra branch, 180s message, 300s learning CPU; one thread')

if __name__ == '__main__':
    run('quote_v1', dict(seed=[20261003,104129,0], repetitions=20), [__file__], calculate)
