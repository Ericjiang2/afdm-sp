# Bounded reproduction admission

Main reviewed the exact diagnostic source, launcher and plan before execution. Accepted: unchanged reference/fast receiver bytes; old input/source/helper/dependency SHA bindings; observed-only loading; one direct-fast, one full Cfast (two TF/LDPC rounds, no CSTATE), one reference; initial-fast 1002 selects two focused acquisitions, otherwise exactly eight prelude acquisitions plus f197. Maximum 12 F1 acquisitions / one complete wrapper. Calling ledger is fsynced before construction; existing output is rejected. CPU64, one thread, CUDA hidden, task scratch, 30-second child and 120-second aggregate hard bounds. Counter and atol=2e−10/rtol=0 gates unchanged. Wrapper stores downstream arrays and per-round/final bit comparisons. No success or root-cause conclusion follows from non-reproduction.

Implementation checks: pure scheduling test, critical Ruff, Python compile and shell syntax passed by Sol. This review did not run acquisition or access truth. Actual observed execution requires the accompanying registration and these source bytes to be committed first.

Source SHA256: `72a184db9c9b5b301fe7936799965a5d16fc3896e8c16223099e6b69bed530e0`; launcher SHA256: `40f5dc79c16d54bccc661e30768f4a283e4e4b904396073877f1efe176cb9e90`.
