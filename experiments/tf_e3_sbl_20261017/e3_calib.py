"""E-3 SNR-grid calibration rule (design.md section 4, frozen).  Pure python; used by e3_driver.py and tested in test_e3_agg.py."""
CAL_SNRS = tuple(range(4, 15))   # candidate SNR grid {4, 5, ..., 14} dB
FER_LIMIT = .9
GRID_LEN = 6                      # {s0, s0+1, ..., s0+5}
SNR_CAP = 14


def decide_grid(fer_by_snr):
    """Per (scenario, rho) cell, from the L-hard unconditional FER only: s0 = smallest candidate SNR with FER <= .9;
    grid {s0, ..., s0+5} truncated at 14 dB; UNINFORMATIVE (no main run for the cell) when the FER at 14 dB is still > .9."""
    if fer_by_snr[SNR_CAP] > FER_LIMIT:
        return dict(status='UNINFORMATIVE', s0=None, grid_db=[])
    s0 = min(s for s in CAL_SNRS if fer_by_snr[s] <= FER_LIMIT)
    return dict(status='OK', s0=int(s0), grid_db=[s for s in range(s0, s0 + GRID_LEN) if s <= SNR_CAP])


# ----------------------------------------------------------------------------- R-iter robustness check (PROTOCOL.md section 11, O2): the frozen 200-key subsample
CELLS = (('U', 300), ('U', 500), ('G', 300), ('G', 500))
MAIN_FRAMES = (4000, 4400)
RITER_N = 200
RITER_SEED = 20261017
RITER_MAX_ITER = 400


def riter_sample(grid_cells, n=RITER_N, seed=RITER_SEED, frames=MAIN_FRAMES):
    """200 keys stratified evenly over the (cell, SNR) strata of the main run.  grid_cells: {'U_300': [grid SNR dB, ...], ...} (informative cells only).
    Strata = cells in CELLS order x ascending grid SNR.  Every stratum gets n // S keys; the n % S strata that get one more are drawn with
    np.random.default_rng(seed).choice(S, n % S, replace=False); then, stratum by stratum in order, its keys are drawn without replacement from
    the main frames with the same generator.  Returns [(scenario, rho_permille, snr_centi_db, frame)] in stratum order, ascending frame."""
    import numpy as np
    strata = [(sc, rho, int(round(float(s) * 100))) for sc, rho in CELLS for s in sorted(grid_cells.get(f'{sc}_{rho}', []))]
    if not strata:
        return []
    base, rem = divmod(n, len(strata))
    rng = np.random.default_rng(seed)
    extra = set(int(i) for i in rng.choice(len(strata), rem, replace=False)) if rem else set()
    pool = np.arange(frames[0], frames[1])
    out = []
    for i, (sc, rho, snr) in enumerate(strata):
        pick = np.sort(rng.choice(pool, base + (i in extra), replace=False))
        out += [(sc, rho, snr, int(f)) for f in pick]
    return out
