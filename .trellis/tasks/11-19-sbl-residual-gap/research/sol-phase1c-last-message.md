Phase 1c passed on deinlab. Commit `c9e0c04a`. Confirmed `model: gpt-6.2-sol`.

| Gate | Result |
|---|---|
| G1 | R0 and U2 matched all 20 archived keys exactly. |
| G2 | The infinite cap matched U2 bit for bit, and KM′ reused K′’s EM fit bit for bit. The spectral bound and positive-semidefiniteness checks passed on all 12 smoke keys and three synthetic cases, including strong cross-delay coupling. |
| G3 | All non-timing fields repeated exactly on 12 smoke keys. |

K′ capped 2,262 of 7,542 modes and removed 39.105% of U2’s trace. The trimmed energy’s co-delay share was 99.961% at the median and 99.964% pooled.
Local and deinlab audits found zero P1 hits in 4800–4999. Phase 1c used 0.234 core-hours. The 2,400-key projection is 13.243 core-hours with 1.3× headroom. §8 remains in draft. [Receipts](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_residual_gap_20261119/out/phase1c_20261119/results.json)