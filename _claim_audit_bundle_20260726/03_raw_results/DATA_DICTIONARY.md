# Raw results dictionary (start here for numbers)

> Field names can vary slightly by file. Always open the JSON and prefer keys actually present.
> When in doubt, recompute from counts: `errs`, `frames`, `bits`, paired ratios.

## A. F2-P firm multi-seed
Paths:
- `f2p_firm/s07/results.json`
- `f2p_firm/s08/results.json`
- `f2p_firm/s09/results.json`

Typical use:
- classical vs learned end-to-end under F2-P deployment
- **Warning:** this comparison alone does **not** isolate learning from F2-P shell

Look for:
- per-SNR BER / error counts
- `_argv` / `_config` fingerprints
- seed identifiers
- n_outer / fs / P / frames

## B. GateA ladder / bootstrap
Paths:
- `gateA*/**/*.json`
- `gateA_artifacts/*.json` (often richest)

Typical scorers:
- classical
- white / white-Λ
- geom / pure-geom
- head
- achievable / achievable-Λ
- genie / genie-Λ
- covhead v1/v2

Metrics to extract:
- absolute errs
- rel reduction vs classical
- paired ratio(a/b)
- CI95
- frames
- sign_p / bootstrap notes

**Controlled claim rule:**
Only comparisons with the **same F2-P deployment** and different `score_override` identify scorer value.

## C. Mechanism ρ-sweep + integer Doppler
Path:
- `mech/`

Expected:
- `mech_rho_snr15.json` (name may vary)
- per-ρ perframe npz/logs
- integer-Doppler control arm

Scientific questions:
- does achievable advantage grow as ρ decreases? (SP interference energy ↑)
- does advantage vanish when fractional Doppler is disabled?

## D. Self-suppression pool (SNR20)
Path:
- `selfsupp/`

Expected:
- pooled summary JSON
- shard02–08 perframe npz for achievable vs genie

Scientific question:
- can achievable beat genie at high SNR via self-suppression?
- or is genie still an upper/reference bound in aggregate?

## E. Complexity
Path:
- `complexity/`

Expected tables:
- dense Cholesky / structured solve time
- full receiver time
- ratio Λ_time / receiver_time
- condition numbers / diagonal population notes if present

Scientific question:
- is there a runtime reason to learn an amortizer for Λ?

## Pairing red flags
Mark analysis invalid if you observe:
- classical err counts disagree across arms that should share the same frames
- single-SNR reruns compared against multi-SNR-list runs (RNG alignment bug risk noted in prior writeups)
- SNR20 conclusions from tiny error counts without CI / pool
