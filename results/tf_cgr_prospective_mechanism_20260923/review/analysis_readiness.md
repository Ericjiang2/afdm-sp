# Post-seal reader readiness

The offline reader `experiments/tf_cgr_prospective_mechanism_20260923/analyze.py` is ready for the fixed 256-frame/768-attempt schema. It first verifies the registered source inventory, commit ancestry, committed observed seal blob, and all observed inventories; it opens or hashes truth artifacts only after the complete observed Git blob is proven. The output directory is rejected if it lies inside an observed, prediction, or truth seal tree.

For each frame it binds observed input, tagged truth, BASE/CGR/SHAM raw and decisions, prediction vectors, native prefixes, entering hashes, all saved checkpoints and 20-step triggered traces. It checks the actual cached H/G/free_cols, including `coded=(G@info) mod 2` and `H@coded=0`, verifies `incoming_llr=clip(extrinsic,-20,20)`, and recomputes I/M/U/L using the frozen frame-level tests, paired decisions, coded-bit log loss, deadlines and descriptive timing. The analyzer imports no receiver, generator, decoder, or optimizer.

The producer owner independently reviewed the actual artifact schema and the three last integrity fixes, finding no remaining reader/schema blocker. Five synthetic statistical/truth checks passed, as did critical Ruff and targeted mypy. Real observed data and truth have not yet been analyzed; scientific gates remain pending their committed seal and the independent recount.
