> Codex (gpt-6.1-sol, xhigh, --search, read-only) attack-only review of REPORT.md, one pass, 2026-10-17. Prompt: codex_attack_prompt.txt. Orchestrator spot-check: GS_RESULTS.md U rho.3 GS-set FER .0025 is at 6.0 dB, 0 from 6.5 dB (item 2 confirmed).

1. **WEAKENED — E11 fits means; it does not establish F0’s detection law.**

   - The PDP/Rayleigh normalization formulas match A1’s unit path power. Full channel equivalence is absent: `miss_law.py:14–34` omits velocity-adjusted delays and fractional Doppler present in [gen_fixed.py:145](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/gen_fixed.py:145).
   - The measured target is missing-delay energy, which F0 retains across rounds—not total pilot-estimation error ([res-20261016-02.md:56–65](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261016-02.md:56)). The simulated independent path tests do not reproduce F0’s search/grouping; production retains eight delays by grouped estimated energy (`twofft.py:87`).
   - Independent rerun reproduces max \(|\ln|=0.141\). But the same-cell-anchored \(m=.0201(x/x_0)^{3/2}\), \(x=(1-\rho+\sigma^2)/\rho\), achieves **0.084**; fitting its exponent gives 1.582 and **0.041**. These are also retrospective comparisons, but defeat identification of the Rician mechanism.
   - **Minimal fix:** Call E11 a retrodictive surrogate; withdraw predictive-law language.

2. **FALSE — E12’s crossover number and κ inference are unsupported.**

   - Using exactly `floor_check.py:10–18`, the proxy’s FER \(10^{-2}\) crossing is **5.777 dB**, not 4.9; at 4.9 its failure probability is **0.468**.
   - It retains full desired data power despite erasing channel energy. Merely replacing the numerator by \((1-\rho)(1-e)\) shifts that crossing to **6.196 dB**. Thus the discrepancy cannot identify loop amplification.
   - Both scripts generate synthetic tails from a mean-calibrated model; neither measures F0’s per-frame tail nor estimates κ.
   - `tail_check.py:2` assigns GS-set ≈.0025 to **U, ρ=.3, 6.5 dB**. The actual [GS_RESULTS.md:78](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_genie_support_20261016/out/analysis/GS_RESULTS.md:78) gives **zero** there; .0025 belongs to 6.0 dB. GS-set is also zero at 8 dB in both scenarios.
   - **Minimal fix:** Correct crossover/cell labels; withdraw κ≈1.8 and the claimed GS residual floor.

3. **WEAKENED — substantial method collision; the exact analytical delta remains unverified.**

   - [arXiv:2501.15935v3](https://arxiv.org/html/2501.15935v3), §III-C, explicitly discusses “failure to detect existing paths,” uses interference-scaled thresholds (22–25), and repeats support estimation after LDPC feedback (Algorithm 1). Decoder-aided support re-acquisition is already present; switching is iteration-scheduled, not syndrome-triggered. Its α selection is offline BER search.
   - [arXiv:2607.18881v1](https://arxiv.org/html/2607.18881v1), Algorithm 1, already rebuilds the sensing dictionary using detected/remodulated data and reruns sparse recovery. It supplies no identified missed-energy/floor law or support-probability ρ* rule. “Accepted by IEEE TCOM” is explicitly **author-reported** on [arXiv](https://arxiv.org/abs/2607.18881).
   - The bounded search found no verified support-detection-probability power rule. [arXiv:2010.15066v1](https://arxiv.org/html/2010.15066v1), §IV, optimizes SINR; its interference covariance (22) already contains the proposed denominator’s basic structure. Search absence does not certify novelty.
   - **Minimal fix:** Narrow novelty to the unestablished analytical claims. “Decode-certified” also overstates `p1_driver.py:153`: rescue triggers on **nonzero** syndrome.

4. **WEAKENED — M1 > M3 > M2 is a preference, not an evidence-derived ordering.**

   - M1’s decisive E11/E12 support weakens above; its converse and prospective predictions remain unperformed (`REPORT.md:249–267`).
   - M3’s existing **Bayes-average risk extension**, beyond the worst-case pair argument, is omitted ([res-20261007-01.md:8](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261007-01.md:8)). This can change an evidence/novelty ranking, although it does not establish TCOM applicability.
   - **Minimal fix:** Make the ordering explicitly conditional and include the omitted result.

Overall: M1 survives only as a hypothesis; its claimed detection law, κ inference, and evidence-backed #1 ranking do not.