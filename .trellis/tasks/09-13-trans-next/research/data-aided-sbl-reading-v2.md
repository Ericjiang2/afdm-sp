# Data-aided SBL: corrected comparison boundary

Source: Yirui Luo et al., *Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*, [arXiv:2607.18881v1](https://arxiv.org/html/2607.18881v1), 21 July 2026, preprint. Read Algorithm1, §II, §III-A/B, §V and §VI; no implementation reproduced.

| Evidence | Verified reading |
|---|---|
| Algorithm1 and §III-A, equations20–21 | LMMSE followed by hard demodulation/remodulation supplies the next sensing dictionary. |
| §III-B | Detection residual uses a scalar Gaussian approximation. |
| §II and §VI | Fractional delay/Doppler, multiple antennas; simulations use N256 and eight receive antennas. |
| §V | Reported timing compares channel-estimation iterations. |

The described feedback is not an explicit LDPC check-to-variable message interface. Treat the abstract’s “decoded” wording carefully. This narrows the prior abstract-only interpretation in post-terminal-reference-routing-v1.md; it does not establish novelty of coded feedback generally.

## Consequences for this project

Our current reference retains LDPC prior and uses physical terminal variance; REF-06 is ordinary baseline qualification, not a contribution. Comparing only against hard decision data assistance would omit that stronger internal reference. Any eventual method must survive both the enhanced classical reference and the relevant nearest-neighbor comparison.

Keep the approved discrete-estimation scope. Adapting dynamic-grid algorithms would change that boundary and is not the next implementation. Do not transfer the paper’s antenna gain or timing to our N1024 single-receiver CPU results.

G1 engineering provides only two old blocks. Neither their failures nor this literature distinction justify selecting a new method. First obtain the frozen32block propagation comparison, then use a distinct development stream for candidate design. No new F/T/D calls or claim admission arise from this note.

## Local interface lookup

The current build_receiver sets use_soft_decisions=True (budgeted_support_eval.py:96–110). The model constructor defaults it to False, but that default is not the active experiment setting. In classical_joint_unrolled.py:2081–2118, feedback-supplied CE moments take precedence; otherwise the soft/hard branch constructs the data part of the DA-LS design. The same constructor flag also controls PIC decisions at2375–2378. Thus changing it alone is not an isolated CE hard-decision intervention. BaselineReceiver has no public Mod-Demod-only arm.

CodeFeedback.after_detection (supplement_feedback.py:123–164) obtains LDPC check messages and CE moments. Detector prior delivery is explicit at classical_joint_unrolled.py:2359–2366. The shared word data-aided does not make these interfaces identical. If a future comparison requires a hard-feedback control, define its detector/CE consumers and numerical baseline first; no such implementation or experiment is admitted by this note. Lookup delegated to existing luna agent; interpretation and review by main session.
