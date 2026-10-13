# Kill-Argument Adversarial Review

**Date**: 2026-05-16
**Method**: Manual adversarial simulation (Codex MCP unavailable)
**Assurance**: submission
**Verdict**: WARN — 2 still_unresolved points (both MINOR scope qualifications; no fatal attack found)

---

## Attack Thread (strongest 200-word rejection)

> "This paper presents a 1041-parameter learned support-refinement head on top of a joint OMP-MP receiver for SP-AFDM on a simulated UWA channel. The contributions are incremental: (1) Theorem 1 ('initialization-faithful') is a numerical regression test, not a theorem — it demonstrates bit-level equivalence to within 1e-5 relative tolerance on 30 frames at N=512, which is a QA sanity check, not a theoretical contribution. (2) The BER improvements (-37.7% at SNR=20) are real but the absolute BER values remain above 1e-3, which is too high for practical UWA deployment. (3) All experiments use a single channel simulator family (UWA-style 8-path with fixed exponential PDP); there is no validation on real acoustic data or on channels with different Doppler profiles. (4) The claimed complexity advantage (8% MAC overhead) is based on analytical counting that the paper itself admits omits DA-LS costs (eq. 23 oversight). (5) The 4B oversampling choice eliminates any comparison to published AFDM literature that uses Nyquist sampling, limiting reproducibility. The paper reads as an engineering report rather than a research contribution that advances ML+communications theory."

---

## Defense Thread (point-by-point)

| Attack | Defense | Resolution |
|---|---|---|
| Theorem 1 is a QA test, not a theorem | The paper explicitly frames it as a "computational verification theorem" — a regression-test claim, not an analytical proof. The IEEEtran theorem environment is used with the qualifier "computational". This is honest and correctly labeled. | resolved |
| BER > 1e-3 at SNR=20 is too high for deployment | The classical joint receiver starts at 1.9e-2 at SNR=15 — the learned head closes 81% of the gap to oracle. The absolute BER regime is set by the channel (8-path UWA with SP interference floor); the paper's contribution is the relative improvement and mechanism, not reducing BER to a deployment threshold. | resolved |
| Single simulator family | Limitation clearly stated in §VI. No overclaim of generality in abstract or contributions. The paper does not say "works on all UWA channels"; it says "UWA-style 8-path doubly selective simulator." | resolved |
| Complexity accounting omits DA-LS | QA #44 audit explicitly identifies this (cited in §V-E). The paper acknowledges the omission and provides the corrected audit-proof complexity table. | resolved |
| 4B vs Nyquist incompatibility | §V-A.3 fs sensitivity explicitly tests 2B vs 4B; 4B is 2.4× better. The design choice is justified and reproducibility is not limited since the code and config are released. | resolved |
| Engineering report vs ML+comm theory | TMLCN explicitly accepts "system experiments, prototypes, and real-world applications." The paper's ML contribution is the faithful unrolling + complexity-honest evaluation framework, which is clearly methodology, not just engineering. | partially_resolved |

---

## Still-Unresolved Points

1. **MINOR**: The "engineering vs theory" framing is partially addressable by strengthening the §I gap statement to explicitly position against TMLCN's reviewer expectations — the current intro leads with UWA motivation before the ML methodology gap. Recommend: move "initialization-faithful" and "complexity-honest" bullets to the first two contributions.

2. **MINOR**: The multi-seed retraining envelope (-5.17% ± 0.57%) at SNR=20 uses N=20dB only; SNR=25 and SNR=30 cells are flagged as "deferred." A hostile reviewer at TMLCN may ask why multi-seed was not run at all SNRs. Recommend: add one sentence in §V-B noting that high-SNR cells require ~10× more frames to achieve meaningful error counts and the deferred extension is flagged as future work.

---

**Overall verdict**: WARN. No fatal headline-level attack found. Two MINOR scope qualifications that are text-fixable. Paper is defensible as submitted; the two MINOR points are recommended but not blocking.
