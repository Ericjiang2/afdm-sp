You are an independent area-chair adjudicator executing Step 8 Beat 2 (`REVIEWER_BIAS_GUARD`) in `--sandbox read-only`. You are NOT the defender. Perform a fresh, zero-context adjudication from the listed files alone (do NOT consult prior review files under `ideas/reviews/`, and do NOT modify any workspace files).

Files (absolute paths, read-only):
- Card 1 (`I-20261125-g01`):
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-g01.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/g_l2_r11_g01.py`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/summary_g_r11_g01.json`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_g_r12_g01_cut.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/g_l2_r12_g01_cut.py`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_g_r12_g01_cut/diag_g_r12_g01_cut.json`
- Card 2 (`I-20261125-h02`):
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-h02.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_h_r12_h02_conf.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/h_l2_r12_h02_conf.py`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_h_r11_h02/summary_h_r11_h02.json`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_h_r12_h02/summary_h_r12_h02_conf.json`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_h_r12_h02_p4.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/h_l2_r12_h02_p4.py`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_h_r12_h02_p4/diag_h_r12_h02_p4.json`
- Funnel rules:
  - `/Users/guoyikun/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md`
  - `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md`

## Beat-1 Rejection Memos (Verbatim)
> ## I-20261125-g01
>
> The decisive experiment never evaluates the standalone window-local receiver the card claims. Before any window is disconnected, every arm receives the same noise estimate. Computing that estimate invokes full cross-window whitening twice, refits the paths under those weights, and projects the resulting residual to estimate noise power (`g_l2_r11_g01.py:453,466–468`; `g_l2_r12_g01_cut.py:520–531`). The reported 6.96× bit-error-rate reduction therefore answers a narrower question: given a noise estimate already obtained with full covariance, does retaining within-window correlations improve the subsequent fit? The answer says nothing about the cost or accuracy of removing cross-window processing throughout the receiver (`diag_g_r12_g01_cut.json:194–201`). Even the purported three-block implementation assembles the full covariance, masks it, and passes the full-size matrix to one Cholesky factorization (`g_l2_r12_g01_cut.py:125–132,147–152,202–208`). The card presents a lossless replacement of a 295-dimensional factorization by three smaller ones. Its reported receiver still pays for full-window processing, and its experiment never measures the proposed replacement (`I-20261125-g01.md:42–44`).
>
> ## I-20261125-h02
>
> The surviving communication result does not isolate an advantage against channel aging. The 3.01% versus 17.47% symbol-error comparison changes maximum Doppler, within-cluster Doppler spread, and angular spread together between the static and dynamic regimes. It cannot determine how much of the waveform gap already exists within one freshly sounded block (`I-20261125-h02.md:44–47`; `h_l2_r12_h02_conf.py:1169–1173`). The only 16-block control that varies sounding age alone runs on the rival zero-forcing precoder (`h_l2_r12_h02_conf.py:709–714,888–897`). That rival discards its estimated path gains and Dopplers after pilot subtraction and equalizes its payload with one scalar. The proposed receiver uses those estimates to equalize the entire block (`h_l2_r12_h02_conf.py:501–505,535–549`). Thus the 41.07% versus 3.05% follow-up compares two different transmitter–receiver designs, while the paired radar localization difference is exactly zero (`diag_h_r12_h02_p4.json:318–340,368–379`). Neither comparison measures whether increasing sounding age enlarges the proposed receiver’s advantage over a matched tracker. The card’s headline cause remains unidentified.

## Neutral Output Schema
Adjudicate `I-20261125-g01` and `I-20261125-h02` in two sections (`## I-20261125-g01 裁决` and `## I-20261125-h02 裁决`) following `SKILL.md` Step 8 (`SKILL.md:283-294`). For each card:
1. Decompose the Beat-1 memo into 3-5 atomic points:
   `### Point P_n: <label>`
   - `Attack claim` (~30 words)
   - `Verdict`: `answered_by_evidence` | `partially_answered` | `still_unresolved`
   - `Evidence` (exact `file:line` or JSON keys, ~50 words)
   - `Severity if unresolved`: `critical` | `major` | `minor`
   - `Cheapest fix or decisive test` (one sentence)
2. Provide verdict counts and a one-paragraph net assessment (under `SKILL.md:288-291`, any `major` or `critical` `still_unresolved` point on a retained claim precludes `PASS`, and evaluate whether the evidence-consistent residual claim after narrowing still clears an open ledger over the matched-information control).
3. End the entire output with these exact four lines:
`STEP8 I-20261125-g01: PASS | REVISE | KILL`
`WORTH_DOING_AFTER_NARROWING I-20261125-g01: YES | NO`
`STEP8 I-20261125-h02: PASS | REVISE | KILL`
`WORTH_DOING_AFTER_NARROWING I-20261125-h02: YES | NO`

Output in Simplified Chinese except labels, file paths, JSON keys, and code identifiers.
