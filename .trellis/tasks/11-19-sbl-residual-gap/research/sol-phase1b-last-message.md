Phase 1b completed in `2c10dc43`. Confirmed `model: gpt-6.2-sol`.

| Gate | Result |
|---|---|
| G1 | PASS. R0 and U2 matched all 20 archived keys exactly. |
| G2 | PASS. K’s spectrum matched the target, and KM reused K’s fit bit for bit before scalar refinement. |
| Positive semidefiniteness | PASS. The smallest normalized eigenvalue was 0.50564 across 12 smoke keys. The gate rejected the indefinite synthetic case. |
| G3 | PASS. All five arms repeated exactly apart from timings on 12 smoke keys. |

Conditional on archived discordances, the 200-frame 97.5% intervals were [−0.458, +0.458] percentage points at the half-gap cutoff and [−0.385, +0.406] at the quarter-gap cutoff.  
The audit cleared 4800–4999. §7.7 selects **4600–4799, 2,400 keys at 12.964 core-hours**, because 4,800 keys project to 25.929 core-hours with 1.3× headroom.  
The protocol remains in DRAFT with §7’s paired inference rules, narrower verdicts and unclipped recovery ratios. All nine synthetic verdict tests passed.