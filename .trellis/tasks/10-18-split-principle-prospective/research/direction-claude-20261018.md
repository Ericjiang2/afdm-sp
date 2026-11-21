# Direction round, orchestrator's independent assessment of the paper main line (2026-10-18)

Written and committed **before** reading the external (Codex) assessment, under the "independent first, then compare"
rule in research-protocol.md. Confidence labels (H/M/L) follow the prediction-ledger finding that my new post hoc
explanations were overconfident.

## 1. Main claim

On long-delay SP-AFDM channels, where embedded pilots do not fit, a deployable decoder-aided support-reopening receiver
(F0+CSTATE) recovers most of the gap to genie CSI at about half the cost of a stronger front end. Its gain comes from
discrete support swaps whose scoring uses the decoder-uncertainty covariance. The remaining gap sits in support
acquisition.

## 2. Contributions, ranked

| # | Contribution | Type | Evidence status | Cards | Confidence |
|---|---|---|---|---|---|
| C1 | F0+CSTATE beats F0, a stronger front end (F1), embedded pilots and a ported published SP-AFDM baseline; FER/cost Pareto among the compared methods | system result | pre-registered (P1: H1 formally INCONCLUSIVE in one cell) | 15-02, 15-03, 16-01 | H |
| C2 | Three-layer reference: FER, constrained MCRB, genie-support audit. The residual gap is support acquisition | analysis | NMSE part pre-registered; FER attribution post hoc | 16-02, 16-03 | H (NMSE) / M (FER) |
| C3 | Mechanism: the rescue comes from support swaps (not an extra round); swap decisions need the full covariance; on clustered channels a co-delay ban fails while full Γ works | mechanism | pre-registered + prospective replication (18-04 P4) | 17-01, 17-02, 18-04 | H |
| C4 | Boundary: how the uncertainty covariance should be treated depends on the estimator; in a Luo-style data-aided SBL the scalar version decodes better | boundary / discussion | pre-registered observations; cause unidentified | 17-03, 18-01, 18-03, 18-04 | H for the observation, L for any explanation |
| C5 | Restricted covariance-compatibility theorem plus the "splitting incentive" algebra as the explanatory link for C3 | theory (supporting) | proven within restrictions; link to FER is empirical | theorem text; 17-01 | M |

## 3. Drop or demote

- Any "unified principle" for covariance use: the split principle was refuted prospectively (18-04), and the Berkson
  reading by GSO (18-03).
- "Full Γ is universally better" (17-03), and "the scalar-data model is a field-wide defect".
- "The interpolation explanation is rejected" (17-04): confounded by the gain-estimator switch, see 18-01.
- The learning-receiver story and the C1 load-cliff line: discussion material at most.
- Novelty claims about decoder-aided re-acquisition as a method class (Kanazawa 2501.15935, Luo 2607.18881, Zheng).

## 4. Missing evidence a TCOM reviewer would demand (by necessity)

1. Statistics: recompute the CIs of E-1, E-2, E-3 and E-3b with frame-level clustering (shared RNG across scenario, ρ
   and SNR). Point estimates stand; intervals and p-values do not, as they are.
2. Baselines: at least two more strong recent receivers. Candidates are Ranasinghe et al. (TWC'25, PBiGaBP), Wang et al.
   (2610.09970, model-order-adaptive), a faithful Luo D-GESBL, and a Kanazawa-style threshold re-acquisition. Without
   them "beats published baselines" rests on one ported baseline.
3. A complexity and runtime table on equal footing.
4. Scope: ρ grid, a second channel family. The Jakes-cluster collapse must be disclosed as a limitation.
5. Headline curves on fresh frames for the C1 comparisons.

## 5. Venue and risk

- **Venue:** IEEE TCOM regular paper (TWC as an alternative). Not TSP: the theory is restricted and supporting.
- **Biggest risk:** the method class is crowded (decoder-aided support re-acquisition exists). A reviewer may judge the
  contribution incremental unless C3's mechanism evidence and C2's attribution are presented as the scientific core,
  and the baseline set is broadened.

## 6. Heilmeier

- **What:** a deployable SP-AFDM receiver for long-delay channels, and an explanation of where its gain comes from.
- **Today:** SP-AFDM JCED with scalar data-interference models and fixed support. EP is infeasible at long delay.
- **New:** pre-registered, prospectively replicated evidence that the gain is the covariance-scored support swaps. Exact
  reference layers locate the remaining gap.
- **Who cares:** designers of SP-OTFS/AFDM receivers on long-delay, high-Doppler links.
- **Risk:** novelty versus Kanazawa, Luo and Zheng; limited baselines.
- **Mid-term exam:** frame-cluster CIs plus two added baselines. **Final exam:** C1–C3 survive both.

## 7. Alternative main line considered and rejected

"Covariance-aware discrete support decisions" as a standalone mechanism paper. Rejected because the effect is
estimator-dependent (C4), the general principle is known from EIV regression, and no unifying principle survived the
prospective test. It is better used as the scientific core of the system paper than as a paper on its own.
