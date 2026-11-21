# Independent Opus5.5 high opinion on the Gemini/Codex disputes

Date: 2026-10-21. User-authorized one-round external review. Model usage reports `claude-opus-5-5`; explicit CLI effort high. No tools or scientific calls. Original response and full packet: [archive](../../../../_archive/external_reviews/20261021-sbl-gram-opus55/README.md), [response](../../../../_archive/external_reviews/20261021-sbl-gram-opus55/response.md).

## Agreement and divergence
| Dispute | Claude's opinion | Project assessment |
|---|---|---|
| Replacing native point identifies a unique cause / defect-free support | Not established: gain update changes several coupled ingredients; decoding success does not prove support completeness | Agree; retain bounded operational findings |
| Uniform-copy prior scaling is a loophole | Incorrect objection: preserve induced prior; nonuniform exact copies can also work with cluster-adjusted priors | Agree; no extension claim for actual near-duplicates |
| ExtraFFT is freely reusable | Incorrect: FFT(v) differs from mean transforms; forming B^H B costs O(NP^2), not just O(P^3) solves | Agree; speed requires profiling and matched parity |
| Exact VEM/CAVI / mandatory covariance propagation | Only the declared local quadratic solve is exact; global CAVI/EM guarantees and covariance transport are unestablished | Agree with qualification below |
| Up/downstream equivalence theorem / oracle / arbitrary production gates | Unsupported; engineering utility, novelty, reliability and cost are separate questions | Agree; no direction or claim change |

## Reviewer's useful additions
The normal-matrix construction cost must be included, not only FFT counts and small solves. Nonuniform exact duplication can preserve the physical prior using per-copy variance1/(P*k_p), a theoretical extension rather than a change to the frozen implementation. The reviewer prioritizes saved-support geometry checks and prior-preserving duplicate interventions for identifying native instability, while proposing no-Gamma / scalar-variance physical-Gamma / full-Gamma controls for engineering questions. These are suggestions, not authorized experiments.

## Corrections and non-adopted statements
- The statement that the initial variance is uniform does not hold generally with the saved decoder check prior. Direct QPSK moments for the predetermined U/.3/7dB/9100 key give v_pre min.00048116, max.49900637, std.11655537. This was a read-only calculation from saved priors, not a receiver run. Uniform-v Gamma=(sum v)R remains a valid approximation/control, not an exact initial-state shortcut here.
- Reusing the same observation is not by itself an EM/VI defect. The unestablished issue is a common objective/message derivation for the retained memories and lagged soft moments. Replace claims about ANY ELBO being impossible with the narrower statement that no such derivation has been provided.
- Full-BHB + diag-Gamma is mathematically unambiguous and directly isolates the off-diagonals of Gamma within this new gain-update family. Its loss of duplicate invariance is a consequence to interpret, not a reason an ablation is invalid. It cannot uniquely identify why the original native update fails. Priority depends on whether the target question is receiver engineering or native causal mechanism; no universal best-test verdict is adopted.
- For nonuniform v, Gamma contains cross-delay terms too. An O(N^-1/2) relative-size assertion requires assumptions on v and geometry. For example v_j=c+a*cos(2*pi*d*j/N),0<a<c, has Fourier coefficient magnitude aN/2 at lag d, not an O(sqrt(N)) bound; the full Gamma also multiplies the geometric kernel. No general same-delay-only interpretation is justified.
- The displayed missing-path residual inequality omits observation noise and possible other omitted components. The always-valid projection bound is ||Y-B_S h|| >= ||(I-Pi_BS)Y||. A nonzero isolated missing-path lower bound needs additional conditions. The simpler physical statement that a true operator outside the chosen span cannot be recovered exactly remains valid.
- The .990782 qualification number compares duplicate and original representations of the predetermined scalar-upstream case, not full-versus-scalar upstream quality. Claude correctly identifies this Gemini misreading. The NMSE numbers quoted by Gemini are real audited cohort means; Claude had not been provided their original raw/summary tables, so its inability to verify them is a context limit rather than a data contradiction.
- Earlier project records already contain co-delay pair evidence (Pilot5 summary); a new geometry audit should reuse that information and clearly distinguish this200-key subset and correlation from causal manipulation. No fresh scientific result is claimed here.

## Next decision boundary
No additional Gemini/Claude debate or automatic multi-arm expansion. Gamma-only ablation remains valid for its narrow uncertainty-coupling question; support geometry / duplicate interventions address different questions. User chooses the immediate target and experiment scope before implementation. Existing cohort verdicts and all C1-C3 predictions remain unchanged. No asset promotion or archive of the active task.
