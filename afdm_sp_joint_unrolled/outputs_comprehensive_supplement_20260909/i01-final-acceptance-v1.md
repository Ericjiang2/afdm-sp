# I-01 final development acceptance v1

## Decision

**Accept and close CSV row I-01 at the development-row scope.** The three I-01
acceptance clauses are supported by complete, hash-bound evidence. This decision
does not close CONF-I, COST-02, Q04/Q23/Q24/Q25/Q26, or any scientific benefit,
equivalence, deployability, or optimality claim.

## Evidence integrity

All five artifacts registered by `evidence/i-01.json` exist locally and match
their registered byte counts and SHA-256 digests:

| Artifact | SHA-256 | Relevant result |
|---|---|---|
| `i01-development-full3456-raw-audit-v1.json` | `6933949e739be04f8929be6fe6d47f6abfb14937f368f1faea22f111d4b86fa5` | passed; 3456 F; 13 batches; audit F/T = 0/0 |
| `i01-development-full3456-actual-bindings-v1.json` | `db7c993f3fc7935547a5816eadd7fbf43f353c0824dd018ae726e7f04934c0be` | passed; 228 sources, four inputs per batch, 13 reservations |
| `i01-development-summary-v1.json` | `09f53a6c60490a696fcc12a2969bfab9e57dded4a3c59a13d1533092d3459515` | complete development summary; 192 blocks, 48 contrasts, m=66 |
| `i01-development-queue-result-v1.json` | `e40022aee1272395803441395a3d22f5e20945b82c2b832d94fbae2002fbed92` | complete; manager exit code 0; all ten queued jobs complete |
| `i01-development-queue-v1.exit` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` | `0` |

The raw audit proofs contain 3456 entries and 3456 unique identities. Their set
is exactly 192 design blocks x SNR `{7,8,9}` x the six registered arms. The 13
batch ranges cover `[0,192)` without overlap; their F counts are 18, eleven
times 288, and 270. Each arm therefore has the same 576-F development allocation.
The actual-bindings result is bound back to the raw audit digest and reports the
same 3456 identity union, 13 distinct reservation digests, all batch exits zero,
and exact source/input/ledger verification.

I independently reaggregated all proof error records. All 18 arm/SNR rows match
both `i01-development-summary-v1.json` and `evidence/i-01.json`, including their
frame, coded-bit, raw-bit, decoded-codeword-bit, and denominator totals.

## Acceptance clauses

### 1. Six arms and the frozen information point

The completed domain includes I0, Irealloc, Isham, I1, I2, and I2realloc on
every block/SNR. The protocol fixes zero-based checkpoint 1; the following CE
at outer iteration 2 is the declared intervention point. The reviewed runner
keeps legal feedback, zero feedback, fixed sham feedback, and diagnostic true
symbols in separate controller paths. The raw auditor verifies the actual ten
detector calls, nine post-initial CE records, eleven BP graph records, decoder
checkpoint records where enabled, and the single explicit oracle consumption
for I2/I2realloc. I0/I2 do not acquire legal decoder-feedback records.

The known generic `offline_truth_access` label is overwritten by the common
error scorer. The evidence correctly relies on `truth_access_level` and the
explicit diagnostic consumption record for the oracle boundary. This label
limitation is disclosed and does not conceal additional truth access.

### 2. Prelisted checkpoints, measured reallocation, and equal development budget

The cost protocol prelisted only checkpoints 1 and 4. Its audited 72-F CUDA
engineering quote used two fixed engineering blocks and complete receiver-call
times, without FER-based selection. At checkpoint 1, outer BP12 made each of
Irealloc, Isham, and I1 no slower in the measured two-block means than I0/BP20;
the shared reallocated schedule was also assigned to I2realloc. I0 and I2 retain
BP20. Every arm still receives 576 development F calls, ten outer stages,
terminal BP20, and final LDPC maxiter50.

The quote field `allocation_passed=false` means that not every prelisted
checkpoint obtained an admissible allocation: checkpoint 4 remained `null`.
It does not invalidate the admitted checkpoint-1 development schedule. The
failure was retained, no third checkpoint or FER-driven replacement was added,
and only checkpoint 1 was developed. This satisfies the row's “at most two”
condition and its requirement to retain failures.

The admission margin is small and based on two engineering blocks. It is a
development schedule admission, not a cost-equivalence result; complete
instrumented/concurrent development times remain outside COST-02.

### 3. Paired development results, actual consumers, and retained contrasts

The raw audit verifies every six-arm group has identical hashes for all seven
registered frame inputs at each `(block,SNR)`, and recounts FER/bit errors from
each terminal NPZ. It also validates recorded actual CE, detector, feedback,
schedule, graph, and oracle consumers. Thus the evidence is stronger than a
plan-only or aggregate-only result.

The frozen F_I analysis contains 45 unique pairwise contrasts and three unique
information-by-reallocation interactions at alpha `0.05/7`, with m=66 and no
alpha recycling. The four mandatory comparison families are present at all
three SNRs with explicit reference-minus-target signs:

- I1 versus Irealloc: `Irealloc - I1`;
- I1 versus Isham: `Isham - I1`;
- I2 versus I0: `I0 - I2`;
- I2realloc versus Irealloc: `Irealloc - I2realloc`.

These are retained for confirmation. They are not confirmation results. For
example, the 8 dB development point estimate for `Irealloc - I1` is 22/192, but
its corrected interval is approximately `[-0.01076, 0.23180]`; it cannot support
a confirmed benefit claim.

## Scope and remaining work

The development observations may be described, including I1's 8 dB error count
of 2/192 versus 17/192 for I0 and 24/192 for Irealloc. I2/I2realloc are one-CE
true-symbol diagnostics and are not optimal-receiver bounds. Isham is a negative
control, not a competitive baseline.

This acceptance relies on the completed raw audit and its independently reviewed
implementation; it does not repeat 3456 terminal-NPZ reads or reconstruct dense
CE matrices from their hashes. It independently checks the local evidence hashes,
identity domain, aggregate arithmetic, contrast inventory, queue completion, and
actual-binding result. The separately charged local smoke calls are excluded from
the 3456 development F and remain disclosed.

CSV I-01 may therefore move to completed/reviewed/committed through the owning
Mission workflow. CONF-I, COST-02, and the registered scientific questions remain
open and must not inherit this row-level acceptance.
