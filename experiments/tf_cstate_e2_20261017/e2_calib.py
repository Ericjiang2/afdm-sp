"""E-2 C-family SNR-grid calibration rule (design.md section 3, frozen).  numpy-free; used by e2_driver.py and tested in test_e2.py."""
CAL_SNRS = (6, 8, 10, 12, 14, 16, 18, 20)
CAL_FER_LIMIT = .95
CAL_GRID_STEPS = (0, 2, 4, 6)
CAL_SNR_CAP = 20


def decide_grid(fer_by_snr):
    """s0 = smallest candidate SNR (dB) with F0 FER <= .95; grid {s0, s0+2, s0+4, s0+6}, each point capped at 20 dB (duplicates merged);
    UNINFORMATIVE (no main run for that rho) when the F0 FER at 20 dB is still > .95.  Looks at F0 only."""
    if fer_by_snr[CAL_SNR_CAP] > CAL_FER_LIMIT:
        return dict(status='UNINFORMATIVE', s0=None, grid_db=[])
    s0 = min(s for s in CAL_SNRS if fer_by_snr[s] <= CAL_FER_LIMIT)
    return dict(status='OK', s0=int(s0), grid_db=sorted({min(s0 + d, CAL_SNR_CAP) for d in CAL_GRID_STEPS}))
