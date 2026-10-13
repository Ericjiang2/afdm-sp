# F2 domain failure: proposed remaining comparison

**Proposal only; not a new launch authorization or a completed result.** The original seven-policy run ended with exit1 after498s:19 attempts,18 successes, one failed `s650_f0004/F2E_LOCAL` call, four complete policy frames, no truth access. See the [terminal receipt](population_launch_v1/final_failure_snapshot.json) and [failure traceback](population_v1/failure.json). No partial-population FER is admissible.

The observed F2 state contains two same-delay15 atoms at Doppler0.4842091048886865 and0.48420910489879293 (gap about1.01e−11). F2's fixed top155 independent grid evolution has no separation constraint. Both frozen LOCAL and CSTATE require same-delay separation at least1e−6. Their adapter therefore does not cover this legal F2 output. Removing the check, moving/merging/deleting atoms or changing their priors would change a frozen method or representation; none is proposed.

The following full-population comparison remains independently meaningful:

| Policy | Existing unchanged receiver operation |
| --- | --- |
| F0 | Original acquisition and two TF/LDPC rounds |
| B | F0 followed by CSTATE on its original40 nonzero-syndrome frames |
| F0_LOCAL | Same40 frames, matched LOCAL continuation |
| F2T | Same40 frames, corrected F2 update and the frozen extra coded round |
| F2E | Corrected early F2, its full155-slot representation and two coded rounds |

Proposed new registration: all1024 existing6.5dB observations, same physical sources, fixed parameters, shared-prefix/cost/deadline rules and no truth before observed Git. Five logical policies give5120 rows;2048 prefixes plus120 F0-triggered continuations give2168 actual calls. The failed19 calls stay charged separately (2187 total across the two attempts), with no reuse or selective replacement of their outputs. Every new numerical/schema/domain failure still stops the new run; there is no per-frame fallback or automatic retry.

F2E+LOCAL and F2E+CSTATE would be explicitly **not admitted under the frozen interface**, for the entire cohort. They are not assigned zero harm, a successful prefix substitute, or a conditional performance score from only legal frames. Their missing comparison remains a stated limitation. The existing Stage-A F1-after-strong-front-end comparison remains a separate result, not a substitute labeled as F2.

This requires an explicit scope decision because the request names F2E+LOCAL as a minimum comparator; its conditional CSTATE clause does not silently authorize dropping LOCAL. If accepted, prepare and review a new five-policy producer/analysis registration before any additional call. Preserve the original frozen source and failed attempt unchanged. Capacity planning is roughly5h from the first five observed prefixes plus the prior F2T qualification, not a completion guarantee; retain a bounded operational timeout. No new method, TF/CSTATE change, parameter tuning or Monte Carlo observation is included.
