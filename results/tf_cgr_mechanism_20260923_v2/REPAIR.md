# CGR v2: serialization repair prepared, no production retry

The first registered campaign (`producer` commit
`814f9eefea6919d7f2ef9754d3942b7fd2ea2a19`) stopped during wrapper 1,
`s650_f0390` / BASE. Both native rounds, the CSTATE continuation, TF20 and
LDPC50 had completed and three checkpoints were saved. The raw artifact was
not saved. `evidence.save_artifact` raised `TypeError: evidence metadata keys
must be strings` after 0.514756875 s of charged wrapper work. There is one
attempt, zero complete wrappers and no observed seal. The original remote
source/output and local recovered copy are retained unchanged at
`results/tf_cgr_mechanism_20260923/failed_attempt_20260923/`.

The violated invariant is recursive: `evidence._pack` accepts only string
dictionary keys, but the new `gram.group_multiplicities` used integer delay
keys. The v2 producer changes exactly one expression to `str(int(delay))`.
This preserves the integer counts and numerical detector path while making the
new evidence metadata valid. The old frozen producer bytes remain available.

Before the fix, the new synthetic N=1024 success-path regression failed at
`payload.gram.group_multiplicities: 3`. After the fix, eight real
`evidence.save_artifact` / `load_artifact` round trips passed for BASE, CGR,
SHAM and BLOCK, each with a full target trace and scalar control trace.
Each round trip also wrote and parsed its decision and ledger JSON. Recursive
metadata checks cover string keys and finite scalars/arrays. The existing 95
synthetic numerical checks, fallback/cap wrapper checks, compileall and a
clean 25-witness/100-call/115-source-file preflight also passed. These are
synthetic checks; no v2 production receiver call was made.

`registration.json` binds the canonical 25-witness manifest, unchanged witness
receipt, source-binding inventory and new qualification receipt. The prepared
`launch_observed.sh` targets a new `results/tf_cgr_mechanism_20260923_v2/observed`
directory. It has not been uploaded or executed. A v2 full run would add 100
new attempts to the preserved first attempt, for 101 total attempts across the
two campaigns; this exceeds the original single 100-attempt allocation and
requires explicit authorization before launch. The original attempt cannot be
converted into a complete wrapper offline because its raw final-batch trace
was not saved.
