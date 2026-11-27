You are performing a pre-run read-only static & synthetic-boundary verification (`--sandbox read-only`) in `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` before launching two formal Step-8 diagnostics on `deinlab`. Do not modify any workspace files and do not launch formal runs.

Audit BOTH items in this single batched pass:

### Item 1: `I-20261125-g01` (`g_l2_r12_g01_cut`)
- Prior pre-run review: `ideas/reviews/r14-sol-prel2-g01-v8b-20261126.md`
- Pre-registration: `ideas/l2/PREDICTIONS_g_r12_g01_cut.md`
- Script: `ideas/l2/g_l2_r12_g01_cut.py` (imports untouched `ideas/l2/g_l2_r11_g01.py`)
- Card: `ideas/cards/I-20261125-g01.md`

Check:
1. Whether Blocking #1 (`card_wraparound_narrative_action` vs `v_chordal` and `v_cross_bin_gain` / `VERDICT_INTRA_WINDOW_OVER_SPATIAL_3X` in both `g_l2_r12_g01_cut.py` and `PREDICTIONS_g_r12_g01_cut.md`) and Non-blocking #2–#3 (`diagnostic_failure_summary` on early Red-Line-1 failure, `--out` guard protecting `summary_g_r11_g01.json`, and `I-20261125-g01.md:48` wording) are cleanly resolved.
2. Whether any new side-information leak, seed overlap, or decision-branch contradiction was introduced, and whether `summary_g_r11_g01.json` and `g_l2_r11_g01.py` remain untouched.

### Item 2: `I-20261125-h02` (`h_l2_r12_h02_p4`)
- Prior pre-run review: `ideas/reviews/r12-sol-prel2-h02-p4-20261126.md`
- Pre-registration: `ideas/l2/PREDICTIONS_h_r12_h02_p4.md`
- Script: `ideas/l2/h_l2_r12_h02_p4.py` (imports untouched `ideas/l2/h_l2_r12_h02_conf.py`)
- Card: `ideas/cards/I-20261125-h02.md`

Check:
1. Whether all 5 blocking items (`B1` mixed straddle + `SP12` catch-up routing; `B2` separating pure `0.1375` half-width precision from short-window `Q=2` `>= 0.55` anchor effect gates; `B3` conditioning spatial-truncation attribution on `sp_trunc_effect_on_rival_Sp12_minus_MaxSp6`; `B4` explicit protocol declaration of pre-specified surveillance steering `PRE_SPECIFIED_SEARCH_THETA_DEG = 40.0` and interface decoupling of `theta_search_deg` from echo target truth `theta_tar_true_deg`; `B5` `_validate_out_path` refusing `summary_h_r11_h02.json` and `summary_h_r12_h02_conf.json`) and Non-blocking #6 (`G1` scope description) are cleanly resolved.
2. Whether any new side-information leak, seed overlap, parity discrepancy vs `h_l2_r12_h02_conf.py`, or decision-branch contradiction was introduced, and whether `h_l2_r12_h02_conf.py`, `ideas/l2/out_h_r11_h02/summary_h_r11_h02.json`, and `ideas/l2/out_h_r12_h02/summary_h_r12_h02_conf.json` remain untouched.

### Output Format
Write your concise findings in Simplified Chinese (citing exact file:line locations), classify any remaining issue strictly as `[Blocking]` or `[Non-blocking]`, and end with these exact two lines:
`VERDICT_G01: <GO | GO_WITH_NONBLOCKING | BLOCK_FOR_FIX>`
`VERDICT_H02: <GO | GO_WITH_NONBLOCKING | BLOCK_FOR_FIX>`
