# Implement (M2)
1. Code: experiments/headroom_ladder_20261008/{dpss_rx.py (basis, prior, band estimator, refine_override), driver_m2.py,
   launch_m2.sh} reusing TapChannel / driver_f2 / analyze.py. -> verify: unit checks (DPSS columns + exact coefficients
   reproduce oracle M1 results; joint mode with true band and oracle init ~ M1 P_D; prior variances finite/positive).
2. Dev tuning on frames 1000..1199 (N4b, J4, D1 at 8 dB) for band threshold + prior scale; freeze values in config.
3. Commit "before M2 run". Smoke (2 configs x 1 SNR x 8 frames all arms).
4. Full test run frames 0..999; analyze (B=20000); S1-S4 table; cost per arm.
5. Commit "after M2 run: <finding>"; update prd/RESULTS; res card draft.
