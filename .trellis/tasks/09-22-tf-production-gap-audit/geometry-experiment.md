# Approved follow-up: observed-only geometry reopening

The user requested per-global-step top-K geometry/frozen-score logging and
post-freeze nearest-true-path rank analysis, then supplied CODEX_EXPERIMENT.md.
Its single production experiment is authorized; the earlier A+B+C stop was
honored and its artifacts remain immutable. No new method, sweep or paper claim.

## Frozen allocation and source

Use the original 6.5 dB Part-B, N=1024, source2d130b4d/dependency31d5ec0d.
Select by saved hard-vector syndrome using actual H: all43 nonzero and first32
zero by observation ID. Alternate arm order deterministically by sorted frame
index. LOCAL20 and GLOBAL20 each replay the unchanged first two native rounds
then add one native TF20/LDPC50 round: exactly150 wrapper calls, no extra replay.
Qualification uses synthetic fixtures and one saved checkpoint, no receiver call.
One CPU process, Torch/BLAS/OpenMP1, CUDA hidden. Engineering/production each
hard deadline3600s, output cap2GiB. All remote writes/tmp/cache/tmux socket remain
under /data/guoyikun. No installs or changes to frozen sources/data.

## Geometry and instrumentation

Follow the supplied protocol and hash-bound reference geometry_exchange.py.
Current P slots, repeated delays allowed, declared delay0..102 checked against
production context, Doppler -3:.25:3, chunk64, max_edits0/2, local_passes2,
halfwidth.75, tolerance.002/max16 trial evaluations. APP moments feed CE and
check-extrinsic feeds a fresh native detector. No old grouping after reopening.
The reference's 1e-10*(1+abs(J)) decrease guard is a numerical strict-decrease
guard, not a new acceptance/quality threshold; retain and disclose it.

For every attempted global step, including a rejected/no-improvement step,
save top20 full candidate geometries and frozen-objective scores, entering
geometry/incumbent, winning/accepted state, and counts. Additionally retain
compact scores and validity masks for ALL slot×grid proposals; this permits
exact offline ranks outside top20. Stable reporting order: score, slot, delay,
Doppler. Candidate logging must not change the actual decision trajectory.
Record all local trials, including rejected duplicates, and endpoints/bounds.
Original source artifacts and source-supplied reference bytes remain unchanged.

## Seal before truth

The online runner accepts only observed inputs and saved receiver outputs;
no compact truth files or previous oracle outcome tables. Preserve its two
baseline checkpoints, APP/check/mu/v, current slots and final decisions, costs,
and all candidate traces. Seal every output by hash, return and commit the
observed seal/ledger before invoking a separate truth analysis process.
Post-seal analysis writes elsewhere and revalidates every sealed hash.

Nearest-true-path ranks are descriptive: for each true path (keep path identity
and duplicate delays), use exact same delay and nearest grid Doppler by absolute
real distance, tie lower Doppler; report per-replacement-slot rank and minimum
global rank over valid slots, plus top1/10/20 presence. Invalid proposals have
no rank. Also report pre-step nearest represented path and accepted atom
distance; a nearest-grid rank does not establish path recovery or global MAP.

## Readout and stop

All43-trigger LOCAL/GLOBAL2x2, each vs frozenfallback, GLOBAL rescues among the
previous23 missed by both J40R2/J20R3, all32 forced-control harms/valid-wrong
words, full and added-branch mean/p95/max. At.5/1s retain latest available
checkpoint, never erase fallback. Truth mismatch uses exact G-derived code
covariance. Evaluate only the supplied ≥5 net additional /≥5 old23 rescue /
mean added branch≤.6s gates. Stop after this configuration, regardless of outcome.

Authoritative input bytes: results/tf_geometry_reopen_20260922/inputs/.
New implementation: experiments/tf_geometry_reopen_20260922/.
New evidence: results/tf_geometry_reopen_20260922/.
