# P-02 independent acceptance review

Verdict: **P-02 may close as the development execution/selection deliverable**, with the bounded claims and evidence limitations below. This does not close CONF-P, COST-02, G1/hardware validation, the research parent, or establish a pilot-gain claim. “Enter confirmation” is satisfied here as retaining both protocols, all three pilots and all three contrasts in the frozen selection handoff; it is not a claim that confirmation samples were executed.

This review independently recalculated identities, aggregate metrics,84 intervals, rankings, contract hashes and power denominators from local evidence. It did not run receivers or access remote files. None of the6336 original remote frame paths exists locally; consequently original NPZ decoding/error recount is supported by the bound completed raw-audit artifact and audited implementation, not repeated raw-file verification in this review.

## Acceptance mapping

| Original requirement | Evidence and result |
|---|---|
| Pfixed same receiver for all three pilots | Exact expected identities recovered: p0/p1/p2 ×192 blocks ×7/8/9dB, B0-p2-s0.5 throughout;1728F. |
| Pmatched same prelisted ≤8 recipe budget | Exact eight frozen recipe IDs for each pilot,192 blocks at8dB;4608F. No missing/duplicate identities or recipe-dependent denominator reduction. |
| Independent protocols/full ledger |6336 unique identities and record paths;25 proof batches sum6336F. Queue24 completed jobs sum6327F, plus the separately completed first9F.25 embedded batch canonical hashes and common frozen bindings independently match. |
| Raw error, pairing, truth boundary | Completed raw audit is hash-bound by selection (`6c5700a44b72920af810a14fe23d5c545a884c2b1a9bd35668308731c67ea523`), reports audit_F=0/audit_T=0 and6336 audited terminals. Its implementation loads terminal info/coded/decoded/hard decisions, recounts errors, checks H/sigma/input hashes and common exogenous pairing. Pilot runner passes only observations to BaselineReceiver; truth remains generation/offline scoring. This review reaggregated every audit row, rather than accepting summary counts. |
| Selection without confirmation access | Source selector validates the full6336 audit/frame/config chain and uses Pmatched192@8 only. Selection protocol hash matches the frozen local protocol; current selector bytes match recorded selector SHA. All three primary rankings were independently recalculated. No confirmation data appears in the inspected inputs. |
| Pairing/multiple comparisons | All84 unique within-pilot recipe pairs present. W/L were independently recounted from audited block FER, and each lower/upper interval recomputed via SciPy beta quantiles at tail=.05/(4×84), matching within1e-12. These are exploratory recipe comparisons, not confirmation pilot contrasts. |
| Both protocols/all confirmation contrasts retained | Output contains p1−p0, p2−p0, p1−p2 for both Pfixed and Pmatched, with all three pilot primaries preserved. Secondary/uncertain alternatives remain reported, not silently declared defeated. |
| Joint FER/power/peak/resources/cost report | All record costs retained and independently reconciled with24 Pmatched metric groups; all groups keep n=192. Complete-F source timing includes initializer/refit and final BP/LDPC. Power metadata and support/terminal resource evidence remain referenced. Cost limits below are explicit. |

## Selection and bounded observations

Pmatched primary/secondary:

- p0: B0-p2-s0.5 / bounded-param-p3-s1 (primary17/192 frame errors).
- p1: bounded-param-p3-s1 / B0-p2-s0.5 (primary22/192).
- p2: bounded-param-p3-s1 / B0-p2-s0.5 (primary25/192).

All24 recipe/pilot groups report zero runtime qualification failures and pass the provisional cost screen. Family representatives and all qualified/budget recipes not demonstrably worse remain in the selection output. The84-family analysis has21 intervals excluding zero; it does not establish that every unselected receiver is worse or that p1 is superior to p0. The slower bounded-param-p2-s1 configuration is not replaced or dropped from its denominator.

Pfixed frame errors at7/8/9dB are p0=(135,17,1), p1=(143,23,2), p2=(148,30,1), each denominator192. These are development observations, not simultaneous pilot-superiority conclusions.

Power audit:6336 call records contain zero declared power violations. They represent only576 unique block/pilot waveforms (192 per pilot), not6336 independent power trials. The repeated per-waveform power dictionaries match across recipes/modes/SNR; pilot and data energies each equal512 within1e-8. PAPR min/median/max dB: p0=6.611/7.950/10.363; p1=7.174/8.531/11.254; p2=6.981/8.714/10.575. Maximum peak power overall12.81472, below the declared16 bound; PAPR maximum11.25353dB, below12. No frame filtering or arm-specific renormalization is used. These are G0 simulation gates, not hardware amplifier or full fractional CPP propagation certification.

## Explicit evidence limitations, not new acceptance gates

1. Group and bounded-param refit diagnostics/stationarity were not saved by `pilot_run.make_record`. Eligibility is a frozen-source runtime assertion. For group, initial convergence plus true eligibility implies the refit *reported* convergence under that source; the optimizer trajectory was not independently recomputed. Bounded-param eligibility intentionally does not require stationarity. Missing stationarity must neither be invented nor turned into a new rejection rule.
2. Original raw frame/NPZ files are remote and were not reopened in this review. This review independently checks the local evidence chain and arithmetic; the completed raw-audit implementation/result supplies the original-terminal verification. Do not describe this review as a second independent raw-NPZ audit.
3. The reused original A2 quote has **n=1**, mean1.423828565 seconds. The1.1 comparison is the frozen provisional engineering screen; concurrent development costs are not isolated timing distributions or COST-02 acceptance. The selection file explicitly retains this restriction.
4. The frozen-source G0 geometry/power contract does not establish G1 untruncated fractional propagation equivalence or hardware deployability. Those remain distinct tasks; their absence is not a newly imposed P-02 development failure.
5. Independent confirmation is not completed by this artifact. The all-three-contrast handoff must remain intact when CONF-P freezes sample sizes and runs its separate data.

No new threshold, budget, qualification field or scientific gate was introduced by this review. Finite claims supported now are complete balanced development execution, source-bound operational receiver choices and satisfaction of the declared sampled G0 power constraints. Pilot improvement, cost equivalence and general physical/deployment claims remain unestablished.
