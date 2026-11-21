# SP-AFDM mainline from first principles (idea card, ccf-idea-optimizer, 2026-10-14)

Status: development proposal for the user; no run authorised by this file. Inputs: STATE.md, accepted cards
res-20261009-01 / -20261010-01 / -20261010-02 / -20261013-01, draft res-20261014-01, `remaining-directions-idea-review.md`
(other session, R1-R4), `ideation-v3.md` (C3), `codex-direction-brief-20261013.md` (D1).

## 1. Diagnosis: why the current mainline feels thin

Current skeleton (manuscript-skeleton-20261014.md) = "mechanism + negative results" around one receiver's load cliff:
MI-universal code threshold, return-map staircase, inner-budget law, ρ×T coupling, killed method candidates.
Missing piece: **no reference point**. Every number is relative to the same SP iterative receiver; nothing says how far
that receiver is from what SP-AFDM can support. A reviewer reads it as "characterising one receiver's failure".
The laws are solid assets; the frame is the problem, not the evidence.

## 2. First-principles object (mainline kept: SP-AFDM, doubly-selective, joint CE + detection)

Per frame the channel has K effective DoF (here K = 8L DPSS-BEM coefficients); N symbols carry data under SP.
Information budget for any receiver (identity, exact): `I(d;y) = I(d;y|h) - I(h;y|d) + I(h;y)`.
- `I(d;y|h)`: coherent rate (the margin above the code rate is the budget).
- `I(h;y|d)`: cost of learning the channel, ~ K log(1 + N SNR / K).
- `I(h;y)`: channel information available without the data; the pilot alone guarantees
  `I(h;y) >= K log(1 + N rho / (K (sigma2 + a)))` (LMMSE pilot-only estimate, max-entropy error).
So the supportable load K* solves `coh - learn(K) + pilot(K) = R_code` — a computable achievability bound (lower bound
on I(d;y)), the natural reference for the practical cliff Kc_Rr.

Rough evaluation (illustrative only: flat SINR a/sigma2, Gaussian learning cost, QPSK curve from T1): K* ≈ 236 at
6.5 dB rho .3 (practical Kc_R10 = 180 at T20, 214 at T40); 256 at 8 dB rho .3; 228 at 11 dB rho .3 where the practical R1
cliff is already ~220 -> the bound is loose at high SNR (Gaussian learning cost over-charges a discrete-input receiver).
Reading: practical SP receivers sit in the same range as a joint-decoding achievability bound; large algorithmic
headroom is **not** established, small headroom at low SNR is plausible.

## 3. Candidates

| ID | Parent / operation | Problem angle | Contribution type | Main risk |
|---|---|---|---|---|
| M1 | current skeleton / refine | why one SP receiver fails at a load cliff | mechanism + negative results | thin: no reference, prior EXIT/JED tools cover the generic part |
| **M2** | C3 + D1 + accepted cards / reframe | **channel-DoF load limit of SP-AFDM**: information-budget bound vs practical cliff, same axis for SP / EP (guard overhead) / DDST | theory (bound + K/N law + rho rule) + mechanism (cliff staircase as the practical side) | bound loose at high SNR; classical noncoherent theory (Hassibi-Hochwald, Liang-Veeravalli, Durisi) covers generic pre-log results |
| M3 | M2 / instrument | close the measured bootstrap gap: per-round model-order schedule under the staircase, multistart, DDST | method | only justified if M2 certifies headroom; may hit the same kills as C1 |
| M4 | R3 / independent | blind-acquisition minimax risk of quadratic vs general phase codes | theory | separate paper, not the SP mainline |

## 4. Recommended route: M2 (fallback M1 with M2's bound as one section)

Story: problem (how many channel DoF can zero-overhead SP support?) -> gap (SP-OTFS/AFDM work reports simulated
throughput only; arXiv 2501.15935 explicitly no DoF/load or bound analysis — partially searched) -> insight (the load
limit is an information budget: coherent margin must pay for channel learning not covered by the pilot) -> practical side
(the accepted cliff staircase is how an iterative receiver spends that budget round by round) -> evidence (bound vs
measured Kc_R1..R10 across SNR, rho, N; EP and DDST on the same axis) -> design rule (rho, R, T from K/N).
What changes vs the skeleton: every accepted law stays; it gains a reference and a design axis. Killed methods become
one negative-results paragraph, not the spine.

Closest-work delta to establish (needs Sonnet concept-aware search, then Opus judgment): finite-SNR achievability for
superimposed training with discrete inputs and iterative decoding (Coldrey-Bohlin SP vs TDT; Hassibi-Hochwald; SP
achievable-rate papers for OFDM/OTFS). Novelty status now: partially searched.

## 5. Minimum evidence (next step, zero new receiver runs)

Information-budget screen, frozen before computing:
1. Compute the bound properly per frame on the C1 BEM model: per-symbol LMMSE SINR with the true H (GMI with Gaussian
   metric, lower bound on I(d;y|h)), exact `log det` learning cost, exact pilot-only LMMSE information; 7 stored groups
   + N in {512, 1024, 2048}.
2. Report K*(SNR, rho, N) vs stored Kc_R1/R4/R10 and the true-H arm; K/N scaling of both.
3. Decision: headroom ratio H = K* / Kc_R10(T40). H >= 1.2 in the low-SNR groups -> M3 is justified as a targeted method;
   H in [0.9, 1.2) -> M2 as theory+mechanism paper, no new method; H < 0.9 everywhere -> bound too loose, tighten the
   learning cost (discrete-input / rate-distortion version) before any claim.

Owners: Opus (derivation, frozen rule, judgment) · Sonnet xhigh (code + run, CPU) · Codex (one pass on the bound
derivation only). Cost: CPU minutes to ~1 core-hour.

## 6. Decisions on the user's questions

- Gemini divergence: not now. The bottleneck is a missing reference number, not idea count; the last Gemini report
  misread project evidence. If used later: a narrow literature question (finite-SNR SP vs training achievable rates,
  load/DoF limits), not open ideation.
- DDST run: keep it running (cheap, frozen); do not wait on it. Under M2 it is one point on the load axis.
- Sunk cost: drop method tinkering on C1 (already terminated); keep the accepted laws as the practical half of M2.
