You are an independent area-chair adjudicator. A hostile reviewer wrote the rejection memo below against an idea card that passed a cheap L2 simulation. You are NOT the defender. Fresh, zero-context adjudication from the files alone.

Files (absolute paths, read-only):
- Card: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-k01.md
- Pre-registration: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_k_r10_k01.md
- L2 script: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/k_l2_r10_k01.py
- L2 summary: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_k_r10_k01/summary_k_r10_k01.json

## Rejection memo
> **Reject. The experiment never measures the false-alarm probability of the rule that produced its headline 98.3% detection rate.**
> 
> On target-free frames, the script divides each delay–Doppler cell’s power by the mean of the entire map. It pools those individual cell scores and takes their 99.9th percentile as the threshold (`k_l2_r10_k01.py:483–486, 634–639`). On target-present frames, it uses the simulated target’s true delay and Doppler to locate a 15-cell window, takes the **maximum** power in that window, and divides by a different background mean that excludes 153 cells around the target. It compares that score with the single-cell threshold (`k_l2_r10_k01.py:169–174, 248–254, 362–363, 488–489, 655–664`).
> 
> Even if the receiver knew which window to search, no target-free trial validates that window’s decision rule. For a blind search, the recorded AFDM threshold produces at least one crossing in **81 of 100 target-free maps** (`s1_pfa_validation.ridge_afdm.emp_map_exceed_rate_at_cell_thr`). The false-alarm rate for the 15-cell rule remains unmeasured for each waveform. The reported 98.3% versus 10.0% detection probabilities therefore cannot establish the equal-false-alarm advantage required by the pre-registration (`s1_primary_snr_m11db`; `PREDICTIONS_k_r10_k01.md:29–33`).

## Task
Decompose the memo into 3-7 atomic rejection points. For each, open the source and data, then output:
### Point P_n: <label>
Attack claim (~30 words) / Verdict: answered_by_evidence | partially_answered | still_unresolved / Evidence (file:line or JSON key, ~50 words) / Severity if unresolved: critical | major | minor / Cheapest fix or decisive test (one sentence).
Then: counts per verdict; a one-paragraph net assessment; and a final line "STEP8: PASS | REVISE | KILL" where PASS means the card may go to Eric as an L3 candidate, REVISE means one named decisive test must run first, KILL means the claim does not survive. Do not minimise. Output in Simplified Chinese except labels, file paths and code identifiers.
