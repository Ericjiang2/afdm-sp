# One decisive CGR mechanism experiment

## Purpose and claim

Test whether a deterministic same-delay gain self-reaction omission explains a useful
part of the remaining TF+CSTATE failures. This is NOT a prospective FER study or a claim
that restoring this known pre-asymptotic contraction is a new AMP family.

There is one proposed arm: CGR. BLOCK and SHAM are mechanistic controls.
No hyperparameter search, new radio observation, new path search, extra decoder round,
noise inflation, clipping change or update damping is authorized by this protocol.

## 0. Targeted witness pack: existing files only

Use `witness_manifest.json`. It binds 25 unique observations and 93 existing per-frame
NPZ artifacts by their exact cold relative paths and SHA256. Do not resolve these textual
frame IDs in any older experiment: the campaign/observation hashes are part of identity.

Cold root:
`deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_research_discovery_20260923/COLD_ARCHIVE/`

Retrieve the original observation, TF checkpoint trace, CSTATE landscape when one exists,
and separately tagged truth payload. Also return the eight target-failure JSON dossiers,
source_evidence_manifest.json and artifact_hashes.json. Validate their packet hashes.
Keep the source prior/generator/noise/code mapping frozen. Supply original NPZ key lists;
do not guess field aliases silently. No unavailable per-iteration vectors should be
represented as historical data. Newly instrumented replays are separately labeled.

Target failures (8):
- all six fresh 6.5-dB remaining failures: s650_f0390, s650_f0415, s650_f0718,
  s650_f0720, s650_f0770, s650_f0996;
- two high in-span-excess examples: s600_f0600, s700_f0732.

Matched rescued controls (7 unique, inherited from the packet):
s600_f0958, s650_f0127, s650_f0413, s650_f0519, s650_f0761, s650_f0797, s700_f0184.

Matched easy controls (7 unique):
s600_f0985, s650_f0190, s650_f0198, s650_f0563, s650_f0631, s650_f0838, s700_f0436.

Distinct-working-delay remaining-failure controls (3):
s600_f0087, s600_f0552, s700_f0509.

Cohort selection is outcome-dependent diagnostic design. It is not an online selector
or a representative FER sample. The actual CGR receiver uses no cohort or truth label.

## 1. Numerical qualification, no tuning

Run `verify_reference.py` and `verify_reaction.py`. Qualify the production adapter against
the original TF on distinct-delay fixtures and against the common-state delta formula:

dh = -alpha*N*vx/(P+1/vq) * (R-I) @ hbar.

Use the actual reciprocal floor through vq. Check complex transpose signs and all-I/all-Q.
Native TF's required matrix is the physical operator Gram R, not B(x)^H B(x).

`make_production_variant.py` creates a SEPARATE source module and refuses a different
source hash or overwriting the frozen file. If the current source identity differs,
resolve the source/equation reconciliation before running; do not bypass the guard.

For every production frame verify R=R^H, diag(R)=1, PSD to the ordinary qualification
tolerance; record group multiplicities, max within-group coherence and eigenvalues.
Qualify field reconstruction against dense small-CPP fixtures, including same-delay
fractional paths and nonuniform symbol variances. The included references pass 73 checks.

## 2. Four fixed complete wrappers: 25 frames x 4 = 100 calls

BASE: original frozen TF+CSTATE, including its original fallback and stop behavior.
CGR: identical original first two rounds and CSTATE/refit. In the existing final TF20
     batch replace only alpha*N*vx*hbar by alpha*N*vx*R@hbar.
SHAM: identical to CGR except use Rsham=D^H R D only in that gain reaction. D is fixed
      diagonal +/-1, with signs alternating within each same-delay group in stored slot
      order. Keep the real forward operators and true working R everywhere else.
      This preserves reaction-matrix diagonal/eigenvalues but corrupts its phase alignment.
BLOCK: identical prefix and geometry; replace the final TF20 with the already archived
       full Gaussian gain-block map, all corresponding mean/covariance contractions,
       Cg=I/P, same damping, same QPSK interface and same one LDPC50 call.
       `receive(mode='full')` is independently qualified against `block_bilinear.block_amp`.

Do not regroup the final working geometry into one path per delay. No CSTATE re-selection
or geometry optimization is changed. Repeated slots retain their original prior convention.
All 100 wrapper prefixes must match BASE through the final post-refit entering state.

Nontriggered easy frames return the original fallback for every arm, with no new branch.
Their lack of harm is inherited operational behavior, not evidence that a forced extra
update is safe. The seven previously rescued triggered controls are the meaningful harm
challenge. Distinct-delay triggered failures qualify specificity for CGR/SHAM; BLOCK is
not expected to equal scalar TF on those frames.

Use deterministic balanced arm interleaving, one identical CPU/thread/runtime setup and
identical evidence instrumentation. Log any numerical failure with charged cost; return
the original already-available fallback rather than hiding failure or retuning.

## 3. Measurements

Primary paired decisions: exact information-bit mapping from G/free_cols, coded errors,
syndrome, valid-but-wrong cases, and rescues/harms versus BASE. Do not assume the first
1024 coded positions are information bits. Produce pairwise overlaps of all four arms.

Complete wrapper and branch mean/p95/max times; final-decision ready times; correctness
available by 0.5s and 1.0s, preserving earlier ready decisions. Do not combine original
historical timing with the current execution into a prospective latency distribution.

New diagnostic trace in the post-CSTATE batch: pre/post h, hbar, vx, alpha, vq,
||xbar||^2, physical R, output/data variances and final LLRs. On the eight target
witnesses retain full newly executed x/mu/v/s snapshots; on controls scalar/path traces
are sufficient. Match instrumentation across arms. Its cost is not removed from timings.

At BASE states record the predicted common-state correction dh above, and
  physical correction norm squared = dh^H R dh.
Normalizing Euclidean gain norm alone can falsely report invisible null-direction motion.

After observed outputs are sealed, compute physical mismatch of each gain iterate,
selected-geometry optimal projection, and the signed common-state physical effect
  ||Htrue-H(hBASE)||F^2 - ||Htrue-H(hBASE+dh)||F^2.
This is offline diagnosis; neither truth nor its favorable sign is an online acceptance
rule. Keep operator Gram and waveform response Gram separate. Also report the frozen
working moment matrix's same-delay entries vs N*vx*R numerically.

## 4. Fixed interpretation gates

These are small-study engineering continuation criteria, not confidence intervals.

- CGR must rescue at least 2/8 target failures versus BASE, with 0 losses of the seven
  already-rescued controls and no newly valid-but-wrong output.
- CGR must be numerically identical to BASE (qualified tolerances and final bits) when
  the entering geometry has distinct delays. Failure means implementation/identity error.
- Correctly aligned CGR must have at least one more net correct target outcome than SHAM;
  physical trace evidence must support the proposed direction, not merely a changed runtime.
- The CGR added-branch mean must be <=1.10 times matched BASE added-branch mean on these
  triggered observations; all complete/tail/deadline measurements remain visible.
- If BLOCK materially outperforms CGR (at least 2 additional net correct targets), the
  minimal-mean-completion claim fails. Do not promote CGR merely because it is cheaper.

Failure of a gate stops this candidate configuration. Do not optimize constants, add
iterations or swap target frames. If traces show the omitted physical reaction is tiny
or points the wrong way, this particular mechanism is weakened/killed; this is NOT proof
that no better receiver exists.

Passing authorizes consideration of a fresh registered confirmation and a deeper
novelty audit; it is not itself a Transactions-level result. The known pre-asymptotic
cross term and archived broader maps must remain explicit closest-art controls.
