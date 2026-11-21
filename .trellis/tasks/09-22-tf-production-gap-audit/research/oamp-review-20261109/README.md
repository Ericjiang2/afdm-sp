# OAMP fairness and cost review

The user explicitly requested Claude Opus5.5 and then approved sending the prepared private implementation/results packet after automatic approval rejected the first call. The original rejection is in `review-call.json`. The authorized call and completed response are retained separately.

The bridge reports model `claude-opus-5-5`, thread `d5eaa866-75b2-4522-925c-1d2a0e757d76`, completed in180535ms. One completed supplied-material review, tools disabled, no follow-up round. Actual cost was not returned. The response's opening self-check/context-loading statement is reviewer text and was not independently verified.

## Findings checked by the main session

| Question | Reviewer assessment | Project evidence and disposition |
|---|---|---|
| Two rounds and fairness | Matched decoder caps do not establish comparable convergence. TF has20 discrete symbol updates before each decoder call, while this adapter has one linear update. | Code agrees. A separate same-adapter diagnostic reproduces the old first two checkpoints exactly, then recovers6/9/12/14/15 frames at rounds1/2/5/10/20. Twenty-round OAMP is not a matched-budget comparison against two-round TF. |
| Linear map | The trace-normalized LMMSE center, pseudo-variance, QPSK LLR coefficient, and scaled-identity limit are correct. | Direct algebra fixtures and real-frame dense/structured parity support the LE implementation. |
| Decoder feedback | Mapping bit-check-extrinsic LLRs to QPSK moments is a valid turbo convention. It differs from taking APP moments and then subtracting the Gaussian incoming precision. | Current code implements the first convention. No correction is made by blindly subtracting the LE message again from an already extrinsic bit message. Full OAMP nonlinear-module fidelity remains an open qualification question. |
| Rotation | An isotropic covariance is preserved by unitary DAFT. | Deterministic N1024 norm and roundtrip checks pass, relative norm error3.33e-16 and maximum roundtrip error1.38e-15. |
| Cost | Dense eigenvectors at N1024 can plausibly take about0.57s on one core. The exact cyclic-band solver can preserve the same scalar LE. | On the first triggered frame, three-trial medians are0.572533s dense and0.106803s structured, maximum center difference2.43e-13. This is one-update evidence only. The structured solver refactorizes as the scalar variance changes, whereas the dense eigenbasis was reused across rounds. |

The review was sent before the reviewer saw the20-round diagnostic or solver-microbenchmark outcome. Its initial packet contained only the original run and code.

## Readout corrections

The original screen remains a reproducible two-call budget point. It does not decide converged OAMP performance or intrinsic OAMP latency. Rename the tested algorithm descriptively as an undamped isotropic turbo-LMMSE adapter with an OAMP-form linear-extrinsic stage.

The same agent session verified returned compact trajectory rows and original prefix counts. This is separate code-path checking, not an independent model or a second raw-artifact audit. The earlier160-checkpoint raw audit applies to the original two-call run. New raw trajectories remain on deinlab under `outputs_oamp_ldpc_20261109/diagnostic_v1/`, each hash in `trajectory_seal.json`. New diagnostic work comprises800 detector updates and800 LDPC invocations, including80 repeated prefix checkpoints. The solver microbenchmark adds seven linear-update evaluations (one reference, three dense and three structured), with no extra decoder calls.

The reviewer proposes two prospective qualifications for a formal baseline: both arms' matched round/budget curves, and dense-versus-structured parity on every relevant frame/round followed by complete timing. Its broader assertion that one nonlinear convention outperforms the other in the literature was not source-verified here and is not adopted as a project fact.

## Primary references consulted

- [Ma and Ping, Orthogonal AMP](https://arxiv.org/html/1602.06509), especially LE choices and§V-B/V-C complexity.
- [Luo et al., AFDM-SCMA](https://arxiv.org/html/2312.11302), §IV-C Gaussian message exchange and§V-C iteration settings.
- [Huang et al., OAMP-JED for ODDM](https://arxiv.org/html/2606.25420), §III-D structured complexity and§IV convergence settings. Its ZP block structure is not asserted for this AFDM system.
