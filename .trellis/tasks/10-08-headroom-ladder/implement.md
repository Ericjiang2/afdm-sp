# Implement plan

1. Driver `experiments/headroom_ladder_20261008/driver.py` + `arms.py` (A1 refine) + `analyze.py`
   -> verify: local AST/ruff; remote unit test: A1 refine Q PSD + finite objective on 3 frames;
      A1 with genie = acquired geometry reproduces native time_refine within tolerance on 1 frame.
2. Commit "before headroom ladder smoke".
3. Smoke on deinlab: rho {.2,.5} x snr {6.5} x 10 frames, all arms + one forced CSTATE trigger at rho .2
   -> verify: asserts pass, pairing hashes equal across rho, F0/B on prospective frames bit-match stored
      prospective decisions for >= 10 frames (A0 reproducibility).
4. E-ladder full (3072 frames) -> results.json + table.
5. E-rho full -> results.json + FER curves.
6. analyze.py: dB shifts + bootstrap + P1-P3 checks -> RESULTS.md.
7. Commit "after headroom ladder / rho sweep: <finding>"; draft res card; route decision in prd.md.
Rollback: outputs in new dirs only; nothing frozen touched.
