# Brief for Astra: review a two-stage experiment design before it is frozen (read-only)

Read `.trellis/tasks/11-21-data-pilot-fer/prd.md`, `design.md`, `implement.md`; the evidence they cite
(`experiments/data_autocorr_acq_20261121/READOUT.md`, `READOUT2.md`, `calc2.py`, `novelty-gemini.md`);
the receiver front end (`experiments/sp_afdm_native_joint_20260921/src/native_twofft.py`, `twofft.py` time_refine,
`experiments/sp_afdm_frozen_20260920/src/receiver.py` pilot_front); and the rho-sweep protocol and results
(`experiments/rho_sweep_20261119/PROTOCOL.md`, `out/main_20261119/RESULTS.md`). Also the low-pilot readouts in
`.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/` and `experiments/lowpilot_support_right_20261120/READOUT.md` if present.

Answer briefly (under ~700 words, English), citing file:line where useful:
1. Is round-0 top-8 selection really where the support is fixed (so injection there is the right place)? Anything
   downstream (round 1, CSTATE/CODELAY exchange) that would also need the candidates?
2. Is stage A (genie true delays at round 0) a valid upper bound for stage B, and are its stop/continue thresholds
   (system-optimum improvement > 0.3 dB with optimum rho <= .20) sensible given the rho-sweep precision? Would you
   change them?
3. Arms B-union vs B-rank: which is more likely to pass the candidates through, and is there a simpler or fairer
   injection? Any confound between the arms and the baseline (e.g. candidate count, compute)?
4. The competing hypotheses H-acq / H-est / H-loop: does the design discriminate them? What extra cheap readout would?
5. Biggest risk of a misleading result, and at most two concrete changes before freezing.
