# Terminal F1 score primitive check

The single frozen zero-acquisition check completed in 4 s (exit 0) on the AFDM runtime, CPU 64, with 0 acquisition/receiver/decoder calls and 0 truth reads. Eight saved final paths × four fixed pointer residues × six comparisons gave **192/192 bitwise-equal**, maximum absolute difference 0. This covered direct versus strided cached-base response and the actual `score`/`score_derivatives` `np.vdot` inputs `b`, `b′`, `b″`, and terminal `other`.

[Receipt](score_alignment_v1/receipt.json) SHA-256 `55554c802ac24f17a5d364d88d028a23fd19ac3a67f6044dc0426568a64ced87`; [launch argv/exit/hash inventory](score_alignment_launch_v1/sha256_inventory.txt) locally verified 5/5. Script SHA-256 `10b177220b3093ef5a96d32556bcc13849ba3b955f2e1fa166e442b5714ac686`; [plan](F1_SCORE_ALIGNMENT_PLAN.md) SHA-256 `0ded7022cf157e626a0dbd6b63dcbb12949b0e7b488cc432d5de45853140befa`. The prior bank/Gram/solve alignment check was not repeated.

The residual is reconstructed only at the saved **terminal** geometry. No earlier coordinate state or the stopped 1002-counter process was reproduced, so this result neither identifies nor repairs the original equivalence failure. The original Stage-B `invalid_partial` classification and exact counter gate remain unchanged.
