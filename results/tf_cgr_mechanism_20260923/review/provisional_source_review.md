# Provisional source review, 2026-09-23

Scope: detector variants and synthetic qualification only. The wrapper, production binding, observed output, and truth analyzer have not been reviewed here. This is not permission to start production calls.

## Findings (fixed)

None in reviewer-owned files.

## Findings (not fixed)

- `qualify.py` checks the common-state formula using actual `vq`, but its 93-check receipt does not establish that the reciprocal floor was active in a test case. Implementer has been asked to add an active-floor fixture and assertion.
- BLOCK's archived-map comparison checks extrinsic, APP, moments, variance and gains, but omits returned gain covariance. Implementer has been asked to compare the covariance too.
- Saved scalar states mix post-update `x`, `mu`, `v`, `h` with pre-update `xbar`, `hbar`. Implementer has been asked to label these stages explicitly in target trace evidence.

## Verification

- Source comparison: generated BASE changes only instrumentation and matches frozen `twofft.py` in the nine synthetic fixtures; CGR and SHAM change the gain reaction only. SHAM signs alternate within stored same-delay slots. BLOCK mean and covariance contractions match the archived `block_amp` source by static inspection.
- Local receipt `qualification/local_20260923_v2/qualification.json`: 93 synthetic checks report pass, maximum recorded error `4.58e-14`; both archived reference verification scripts ran. The receipt is synthetic evidence, not a production call.
- Lint: critical Ruff rules `E9,F63,F7,F82` pass; broad Ruff flags inherited compact syntax in generated modules and intentional import ordering after path setup in `qualify.py`.
- TypeCheck: unavailable locally (`mypy` is not installed in the default Python environment).
- Compile: `python3 -m py_compile` passes for current variant modules.
- Tests: receipt inspected; local execution unavailable in default Python because NumPy is absent.
