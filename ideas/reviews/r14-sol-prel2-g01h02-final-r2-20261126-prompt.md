Re-verify ONLY the targeted fixes for the 1 blocking item on `H02` and the 2 non-blocking wording items on `G01` and `H02` (all inside this resumed read-only session; do not modify workspace files):
1. `H02` Blocking (`ideas/l2/h_l2_r12_h02_p4.py:545-568` & `ideas/l2/PREDICTIONS_h_r12_h02_p4.md:94-103`): both code and protocol now check `(not hw_055_ok) or (sp12_raw_catches_up and (not hw_sp12_eq10_ok)) -> INCONCLUSIVE_PRECISION_INSUFFICIENT` strictly BEFORE `elif not anchors_q2_ge_055_ok -> SHORT_WINDOW_ANCHOR_BELOW_055_RETRACT_CONFLICT`.
2. `H02` Non-blocking (`h_l2_r12_h02_p4.py:557` & `PREDICTIONS_h_r12_h02_p4.md:52,99`): renamed to `LITERAL_GE_055_UNDER_MAXSP6_ONLY_SP12_CATCHES_UP_RETRACT_CONFLICT` with explicit clarification that any residual positive gap inside `[0, 0.10]` is reported as-is.
3. `G01` Non-blocking (`ideas/l2/g_l2_r12_g01_cut.py:841-848` & `ideas/l2/PREDICTIONS_g_r12_g01_cut.md:29,48-52`): forecast partition explicitly includes `v_valid_formal`, and the `not v_cross_bin_gain` branch is named `WITHDRAW_WRAPAROUND_PRIMARY_CROSS_BIN_GATE_FAILED_SEE_INTRA_FIELD`.

Confirm frozen baseline files remain untouched and end with:
`VERDICT_G01: <GO | GO_WITH_NONBLOCKING | BLOCK_FOR_FIX>`
`VERDICT_H02: <GO | GO_WITH_NONBLOCKING | BLOCK_FOR_FIX>`
