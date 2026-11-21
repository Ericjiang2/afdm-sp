Phase 1 committed as `989b47d8cb2eba6e8b6c357809ca6574c4337f09`. Confirmed `model: gpt-6.2-sol` in Codex config.
Fresh MIXED8 frames 1000–1599 cleared the archive check and remained untouched. U ran only on synthetic inputs and smoke frames 200–207.

| Gate | Result |
|---|---|
| G1 | PASS. F0, A2 and screen CODELAY matched all 96 archived rows exactly. |
| G2 | PASS. τ=0 bit identity and doublet census verified. Across 1,250 brute-force score checks, maximum relative error was 2.60×10⁻¹⁶. |
| G3 | PASS. All five arms repeated exactly across eight smoke frames. |

**7 dB selected.** CD failure rates at 6/7/8/9/10/12 dB were 56.25% / 4.17% / 1.04% / 0% / 0% / 0%, each over 96 old frames.
Closed-form CD matched the screen’s constant-variance call path on all 96 G1 frames. Projected 600-frame cost with the 1.3 multiplier is **0.2534 core-hours**.
The protocol remains DRAFT. Amendments document frame guards, covariance call paths, readouts, interval details and trigger-weighted costing. All six synthetic verdict tests passed. [Protocol](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/doublet_conflict_20261119/PROTOCOL.md)