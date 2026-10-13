# Stage-B systems arms and admission state

The current executable allocation is only the F1 efficiency phase, governed by [the equivalence/timing protocol](F1_EQUIVALENCE_TIMING_PROTOCOL.md) and its source-bound manifest when committed.

| Arm | Operational definition | Current allocation |
|---|---|---|
| B | Original F0 acquisition → two native TF/LDPC rounds → original syndrome-triggered CSTATE20 continuation | All archived 1,024 observations; exact original input/source/code binding. |
| Cfast | Semantics-preserving F1-fast acquisition → unchanged keep-slots TF/LDPC handoff | All 1,024; qualified timing requires complete equivalence with sealed Stage-A C. |
| Cref | Unmodified Stage-A F1 + TF/LDPC | Fixed 64 IDs divisible by 16, current matched clock/reproducibility control; archived reference outputs cover all 1,024. |
| A prefix | Original F0 + TF | Already executed within B; native component/prefix costs identified, no duplicate population arm. |
| F2E | Published-method SISO/integer-delay data-aided GAMP-GESBL → TF/LDPC | Not yet frozen or admitted. Paper-algebra corrections and numerical/support/feedback policies require explicit resolution. |
| F2EC / F2E LOCAL | Matched CSTATE / LOCAL continuation on every F2E native trigger | Conditional on an admitted F2E implementation and valid geometry interface; not run. |
| F2T / F0 LOCAL | F2 / LOCAL on exactly the original F0 syndrome triggers, compared with CSTATE using matched legal state and continuation | Not yet admitted; no inference from F1 results substitutes for this comparison. |

No F2 call is included in the 2,112-wrapper F1 manifest. Later F2 execution requires its own explicit frozen, source-bound allocation within this same task. No fresh observations, CSTATE retuning, CGR or extra method variants are authorized by these definitions.
