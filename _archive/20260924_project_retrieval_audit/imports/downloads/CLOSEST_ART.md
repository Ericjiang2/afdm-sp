# Primary-source novelty audit for this investigation

These sources were inspected as prior art, not as substitutes for private production evidence. The presence of a general optimization technique is not by itself disqualifying; the important match is the actual inference operation.

1. **Yi Sun et al., Trainable Joint Channel Estimation, Detection and Decoding for MIMO URLLC Systems**, 2024 preprint. https://arxiv.org/html/2404.07721v1
   Closest to the derived alternative: bit-level MAP under LDPC constraints; Gaussian channel elimination; penalized code-polytope relaxation; majorized ADMM bit updates; learned unrolling. Equations (9), (14)-(15), (19), (22). Their MIMO model differs from SP-AFDM; no identical implementation claim is made.

2. **Xishuo Liu and Stark C. Draper, The ADMM penalized decoder for LDPC codes**, 2014 preprint. https://arxiv.org/abs/1409.5140
   Nonconvex penalties to discourage fractional pseudocodeword solutions are established, not a new way to obtain code-aware reception in this project.

3. **Joint CFO, Gridless Channel Estimation and Data Detection for Underwater Acoustic OFDM Systems**, JCCD-VALSE. https://arxiv.org/html/2107.07101
   Soft coded reception, continuous parameter inference and support/model-order updates already coexist. This is not an SP-AFDM implementation, but it weakens a generic code-informed geometry-posterior claim.

4. **Graph Neural Network-based Joint Equalization and Decoding**, 2024. https://arxiv.org/html/2401.16187v1
   Shared equalization/code factor-graph variables and learned message passing are prior art. Simply connecting the channel graph and Tanner graph is not a demonstrated new delta.

5. **Jamison R. Ebert, Jean-Francois Chamberland and Krishna R. Narayanan, Sparse Regression LDPC Codes**, 2023 preprint. https://arxiv.org/abs/2311.07720
   BP on an LDPC graph inside each AMP iteration is explicitly used as a nonseparable denoiser. This work concerns a concatenated SPARC/nonbinary-LDPC system, not bilinear SP-AFDM. Its state-evolution assumptions must not be imported to the current physical operator, and neither "put LDPC inside AMP" nor "use a nonseparable code denoiser" is a new principle by itself.

6. **Xinjie Li et al., Learning-Aided Iterative Receiver for Superimposed Pilots: Design and Experimental Evaluation**, 2025 preprint. https://arxiv.org/abs/2507.10074
   SP MIMO-OFDM iterative JCED with variational and learned estimators; public abstract also reports over-the-air evaluation. It is not an AFDM comparator run in this project. Its relevance is that learned SP feedback itself is not a new mechanism.

7. **Efficient Least Residual Greedy Algorithms for Sparse Recovery**. https://arxiv.org/html/2004.06661
   Classical addition/deletion and OLS-replacement ancestry of the frozen CSTATE operation. This round does not repackage that result as a new method.

## Verdict

The most developed alternate algorithm in this investigation did not survive as a stronger new inference contribution. The remaining specific implementation difference would largely be full-fractional/CPP structured operator evaluation and small path-domain gain elimination. A useful new algorithm could still use ADMM, AMP, SBL, or learning, but it needs an additional failure-critical operation or demonstrable approximation beyond the matches above. This investigation did not establish such an operation.
