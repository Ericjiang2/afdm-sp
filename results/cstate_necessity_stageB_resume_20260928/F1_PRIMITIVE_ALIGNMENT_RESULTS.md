# F1 zero-acquisition primitive alignment result

One CPU64 run exited 0 in 4 s. It read the sealed f197 observation and Stage-A C final geometry, checked the frozen source hashes, and called only the AFDM transform/response and NumPy bank, Gram, RHS, and solve primitives. It made **0 F1 acquisitions, 0 receiver/TF/decoder calls, and 0 truth reads**.

For byte-identical matrices at data-pointer residues 0/16/32/48 mod 64, preserving dtype, shape, C/F order and strides, all **28 comparisons were bitwise equal**: fresh and held bank-conjugate matvecs with initial and saved-final-state proxy residuals, plus selected-path Gram, RHS and ridge solve. Maximum absolute difference was zero. The fixed [plan](F1_PRIMITIVE_ALIGNMENT_PLAN.md), [numeric receipt](primitive_alignment_v1/receipt.json) (SHA-256 `5c1ec0f1ee4595b8d668b2430feb98b8d70465dee05982dfe7e677841fe1aa27`), [argv](primitive_alignment_launch_v1/argv.txt), and [exit](primitive_alignment_launch_v1/launch_exit.json) retain the scope. Five copied files were SHA-256 checked against the remote receipts.

This does not cover unsaved earlier residuals or the original 408-wrapper execution history. The stopped 995→1002 counter divergence remains **unresolved**. No F1-fast source or equivalence threshold changed, and Stage-B remains `invalid_partial`.
