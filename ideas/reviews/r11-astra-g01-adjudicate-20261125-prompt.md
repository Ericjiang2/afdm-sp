You are an independent area-chair adjudicator. A hostile reviewer wrote the rejection memo below against an idea card that passed a cheap L2 simulation. You are NOT the defender. Fresh, zero-context adjudication from the files alone.

Files (absolute paths, read-only):
- Card: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-g01.md
- Pre-registration: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_g_r11_g01.md
- L2 script: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/g_l2_r11_g01.py
- L2 summary: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/summary_g_r11_g01.json
- Funnel rules the card was judged under (group [放宽TWC], rival rule, red lines): /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md and /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/prompts/round-agy-extra.md

## Rejection memo
> Reject. The card attributes the weak user’s bit-error reduction to cancellation between the right guard and the frame-head pilot window. The experiment never isolates that connection. It changes the receiver’s channel model in the headline comparison and removes every cross-bin correlation in the test labeled “Cross-Window Causal Proof” (`I-20261125-g01.md:20`; `PREDICTIONS_g_r11_g01.md:42–43`).
> 
> In the primary three-user scenario, the reported gains are 57.8× over Yin, 37.6× over SAGE, and 35.4× over MatchedDir. Yin reconstructs integer-delay diagonals. SAGE fits and reconstructs an ideal Dirichlet response. MatchedDir uses the same ideal response with whitening disabled. The proposed receiver uses the simulated pulse response and full covariance. Even with exact path parameters, SAGE and MatchedDir would still hand the detector a mismatched channel matrix (`g_l2_r11_g01.py:58–66,646–662,699–707`; `summary_g_r11_g01.json:45–69`).
> 
> The decisive comparison would retain all correlations within each region and remove only those connecting the two named regions. Instead, the code retains covariance only between antennas at the **same bin**. Its 7.01× penalty therefore includes the loss of correlations between neighboring bins within either region (`g_l2_r11_g01.py:481–489`; `summary_g_r11_g01.json:139–145`). The headline ratios measure the cost of receiver mismatch. The remaining experiment gives no estimate of how much gain comes from the specific AFDM wraparound mechanism claimed as the contribution.
## Task
Decompose the memo into 3-7 atomic rejection points. For each, open the source and data, then output:
### Point P_n: <label>
Attack claim (~30 words) / Verdict: answered_by_evidence | partially_answered | still_unresolved / Evidence (file:line or JSON key, ~50 words) / Severity if unresolved: critical | major | minor / Cheapest fix or decisive test (one sentence).
Then: counts per verdict; a one-paragraph net assessment; and a final line "STEP8: PASS | REVISE | KILL" where PASS means the card may go to Eric as an L3 candidate, REVISE means one named decisive test must run first, KILL means the claim does not survive. Do not minimise. Output in Simplified Chinese except labels, file paths and code identifiers.
