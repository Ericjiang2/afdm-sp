Active task: .trellis/tasks/09-22-tf-production-gap-audit

- Confirm first that this session's model is gpt-6.2-astra. If it is not, stop and tell me.
- Read-only. Do not write to the repo. Your final message is the deliverable.
- You may open repository files to check a claim (for example research-assets/*.md, the research/*.md notes in this task, or experiments/*/out/RESULTS.md). Do not read per-unit rows of any run.
- Where your idea rests on mathematics, sketch the derivation or the exact claim that would need proving.
- Mark every claim derived, numerically checked, assumed, confident or uncertain.
- Answer in English, at most 150 lines.

I am preparing an IEEE TCOM regular paper. Ignore effort, time and cost entirely: I want to know what the most ambitious version of this contribution would look like. Be blunt; no flattery; do not invent references (say "uncertain" instead).

Paper core (all verified):
- Superimposed-pilot AFDM, fractional Doppler, integer delays, P=8, QPSK/LDPC, one synthetic channel generator.
- Bottleneck: 73–81% of the gap to genie CSI is missed weak-delay paths.
- Cause (proved): when support is re-acquired using decoder soft symbols, the true data-uncertainty energy tr(H V H^H) is invariant to splitting a path into coincident atoms, while the natural diagonal approximation u·||h||² is not. As a result, the support search rewards same-delay "phantom" duplicates of strong paths over missing weak paths.
  - Closed-form decision window: 1 + 2E/(u+λ) < R < 1 + 2(E+u)/λ. Here E = pilot+soft-mean energy, u = total symbol variance, λ = noise, R = strong/weak path power ratio.
  - In receiver-internal units the window is effectively one-sided, with lower bound ≈ 1 + 2(1−x)/x, where x = 2(1−ρ)·v̄ is the unresolved data-uncertainty share. Lower pilot fraction therefore widens it.
- Proposition 1 (proved): in AFDM, the co-delay uncertainty block equals u·D_N(Δν) exactly for any heteroscedastic symbol variance. The same pathology appears in any modulation with continuous Doppler (OFDM, OTFS), but only AFDM's chirp makes the one-scalar fix exact and suppresses cross-delay terms.
- Fix: CODELAY, a one-scalar closed-form block.
  - It matches full covariance (0:0 FER discordance on 13,600 keys).
  - It beats Luo-style data-aided SBL ports by 1.3–5.3 dB and is 12–16× faster.
- Where the advantage shows: the CODELAY advantage is large at pilot fraction ρ=0.3 (rescue gap 43–50 pp) and small at ρ=0.5 (~7 pp). The window predicts this ordering but not its magnitude.
- Semi-blind replay on 7,667 real failed frames (aggregate outcomes were known in advance, per-unit quantities were not):
  - For the scalar arm, the closed-form phantom reward matches the receiver's measured reward with Spearman 0.999 and 0.8% median relative error.
  - The window stratifies phantom admission: 100% inside vs 78% outside.
  - For the CODELAY arm, the closed form does not predict its small residual phantom reward (90% median error), though CODELAY suppresses phantoms to 2.8% inside the window.
- Robustness:
  - Robust to over-estimating the path cap.
  - Degrades ~1.2 dB with a single-frame noise-variance estimate; a decision-directed estimate made it worse.
  - This sensitivity sits in the channel-estimation chain: the genie-channel receiver loses only 0.19 dB.
- SBL reversal (scalar beats full Γ under fixed gains): reported as a boundary with a provable interface-invariance property; mechanism unresolved.
- Learned variants gave ~zero gain (reported as a negative result).

Questions (ignore cost entirely):
1. What would turn this into an outstanding paper, one that reviewers would call a landmark rather than a solid contribution? Name the theory result and the experimental result that would do it.
2. What is the bigger question this work points to beyond this paper, and what would a multi-paper research program around it look like?
3. Which of your answers could realistically be achieved by a single PhD student, and which are fantasy? What early evidence would tell me a direction is real rather than wishful?
