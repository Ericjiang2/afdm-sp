# Stage-A arms and common clocks

Authority: [current user request](USER_REQUEST.txt), [task execution contract](../../.trellis/tasks/09-22-tf-production-gap-audit/cstate-necessity-stageA.md), [frozen preregistration](../cstate_necessity_audit_20260925/STAGE_A_PREREGISTRATION.md). This is developmental reuse of the archived6.5-dB1024 population, not prospective confirmation.

|Arm|Independent complete wrapper|Branch trigger|
|---|---|---|
|A|Unchanged F0 pilot front, two native TF20/LDPC50 rounds|None|
|B|Same F0 native prefix, unchanged CSTATE20 continuation|Final native nonzero syndrome|
|C|Frozen F1 pilot acquisition, keep-slots refit in both native TF20/LDPC50 rounds|None|
|D|Same F1 comparator prefix, unchanged CSTATE20 continuation|Final comparator nonzero syndrome|
|E|Same F1 comparator prefix, matched original LOCAL20 continuation, no global replacements|Only all observations triggered in C; fixed before any Stage-A outcome|

A-D: exactly4096 scheduled wrappers. E: at most1024 additional, not an all-population fifth arm. No A/B or C/D prefix sharing, replacement observations, extra arms or tuning. Every attempt is charged. Actual component/kernel/decoder counts are retained independently of wrapper count.

Frame index modulo4 chooses cyclic arm order ABCD, BCDA, CDAB, DABC. Each main arm occupies every position256 times. E follows that frame's four main arms only when C triggers; its influence on later timing is disclosed. All wrappers use one CPU/BLAS/Torch thread and CUDA hidden in the same isolated numerical process.

Complete timing starts before each input load/hash and ends after durable decision/raw/checkpoint serialization. Ledger append is separately measured/declared. Both0.5s and1.0s deadline metrics use the latest actually ready decision, including explicit missing decisions in the full denominator. Source/context/cache preparation, per-frame acquisition, both refinements, TF, LDPC, structural/local branch, serialization and residual overhead are distinct; nested metrics must not be added twice. Historical timings are not comparison timings.

F0 retains its actual24 nominations/515 columns and native grouping; F1 has at most8 slots/2575 quarter-Doppler columns, wider initial support, ridge gain fitting and numerical safeguards. Dtype, actual path counts, preparation amortization and measured costs must accompany the nominal5/3 correlation-work upper-bound ratio. Frozen scalar TF/LDPC and CSTATE are not optimized.

The prior A4 lineage finding is descriptive, not a causal percentage. Only the frozen quantitative rules are machine-classified: no new thresholds for qualitative S/E wording. Original34 rescue absorption and D-versus-C incremental risk are analyzed after an observed-output Git seal; all outputs remain tied to input and source hashes.
