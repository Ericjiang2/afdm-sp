# Final two-item method/theory closure

## 1. F1-fast equivalence: PASS on the frozen population

The admitted implementation is the already frozen **Ccompat**, not the earlier failed Cfast. An independent reader rehashed and compared both saved raw populations (1,024 Stage-A C and 1,024 Ccompat artifacts), matching all 1,024 input identities. Ordered geometry, counters/stopping, accepted objective history, controlled intermediate arrays and final bits pass the unchanged reference contract. All 444 reported numerical field maxima are **exactly zero**. This is a source/input/environment-bound population result, not universal bitwise determinism.

Ccompat restores the frozen reference response/scoring/coordinate/refit/summation order and retains cached bank conjugation plus the identical vectorized duplicate predicate. It changes implementation work, not the frozen F1 search algorithm. The original Cfast f197 count of 1,002 versus 995 violated its exact gate and remains inadmissible. Its first divergent intermediate state was not saved; no unique historical root cause can be recovered from the surviving final states. Floating-key evaluation counters can be sensitive to roundoff/order, but that mechanism is not a proved explanation of this particular failure.

Evidence: [independent full-population raw receipt](final_f1/independent/F1_CCOMPAT_RAW_EQUIVALENCE_RECOUNT.json), [original adjudication](../cstate_necessity_stageB_resume_20260928/F1_EQUIVALENCE_ADJUDICATION.md).

## 2. Matched timing and cost attribution

One process, CPU64, one thread, the same frozen software environment; 64 fixed archived observations (`frame_index % 16 == 0`), with deterministic rotating order among pure F0, reference F1 and Ccompat. **192/192 complete wrappers passed**. No F2, new observations, Monte Carlo, receiver-parameter changes or truth scoring. Full-population equivalence was admitted before this timing run. F0 here has no CSTATE continuation and is not the previous B policy.

Seconds; all rows use the same 64 observations:

| Implementation | Acquisition mean | Complete mean | Complete p95 |
|---|---:|---:|---:|
| F0 | 0.08255716382336686 | 0.34985430272718077 | 0.39794844487914816 |
| Frozen reference F1 | 0.36896069964859635 | 0.6521716056122386 | 0.7213418615050614 |
| Admitted F1-fast (Ccompat) | 0.2780263696949987 | 0.5596680669877969 | 0.5869535758974962 |

Measured removable acquisition excess:
`(mean Cref - mean Ccompat)/(mean Cref - mean F0)` = **0.31750421548247926** (31.7504%). Complete-latency reduction is **0.141839261060135** (14.1839%). Remaining measured acquisition excess is **0.6824957845175208** (68.2496%).

**Timing verdict: F1-UNRESOLVED — measurable implementation overhead removed; dominant Python-bound versus intrinsic-cost attribution remains unresolved.** The prior >50% acquisition-excess plus >=10% complete-improvement Python-bound rule is not met. F1 requires additional search/refit work by its frozen algorithm, but the residual runtime also can contain removable implementation overhead. It is not an identified intrinsic-cost lower bound, and no per-optimization causal split was measured.

Complete latency includes attempt recording, loading the saved observation, acquisition, unchanged downstream receiver/decoder, checkpoints, raw output and durable decision writing. Reference verification and ledger append are outside this clock; shared setup is recorded separately. Component clocks overlap and must not be summed. These are matched-64 developmental timing estimates, not population tail guarantees or timing comparable across different campaigns.

Independent saved-ledger recount verifies all 192 attempts, paired inputs and six rotating arm orders: **214 numerical fields exactly equal the frozen primary, maximum absolute difference 0**. This timing recount does not reopen raw/checkpoint arrays; the separate 1,024-frame raw equivalence proof establishes semantics.

[Full distributions and paired differences](final_f1/analysis_matched64_v2/report.json) · [CSV](final_f1/analysis_matched64_v2/timing.csv) · [registration](final_f1/F1_MATCHED64_TIMING_REGISTRATION.json).

## 3. Verified closure theorem and proof

For unitary path operators, let $M_{ij}=U_i^H U_j$ and $s=\operatorname{tr}V$. The equality $\Gamma(V)=sI$ for every covariance in a specified family holds iff each off-diagonal trace functional annihilates that family's real span. For the full families:

| Covariance family | Necessary and sufficient condition for each $i\ne j$ |
|---|---|
| Isotropic $V=vI$, $v\ge0$ | $\operatorname{tr}M_{ij}=0$ |
| Diagonal in a fixed unitary basis $B$ | $\operatorname{diag}(B^HM_{ij}B)=0$ |
| All complex Hermitian PSD matrices | $M_{ij}=0$, impossible for two or more unitary paths |

Proof: unitarity fixes every diagonal entry to $s$. Isotropic and coordinate rank-one covariances give the first two conditions. For all PSD matrices, test $V=xx^H$ with complex $x$: $x^HM_{ij}x=0$ for all $x$ forces $M_{ij}=0$ by testing $e_a$, $e_a+e_b$, and $e_a+i e_b$.

For frozen positive-Doppler AFDM/CPP and equal-delay doublets, $\rho=D_N(\nu_2-\nu_1)$, where

$$D_N(\delta)=\frac1N\sum_{n=0}^{N-1}e^{+2\pi i n\delta/N}.$$

The normalized $R$ has eigenvalues $1\pm|\rho|$, hence $\min_{c\in\mathbb C}\|R-cI\|_2=|\rho|$, attained at $c=1$. For the same-delay block with AF-diagonal covariance, $\Gamma=sR$ and the corresponding minimum is $s|\rho|$. The exact kernel is $e^{+\pi i(N-1)\delta/N}\operatorname{sinc}(\delta)/\operatorname{sinc}(\delta/N)$, extended by its finite sum at removable points; for fixed noninteger bin separation it tends to $e^{+\pi i\delta}\operatorname{sinc}(\delta)$.

**Boundary:** distinct delays guarantee $R=I$ and isotropic compatibility, not closure for nonuniform AF-diagonal covariance. No result implies FER, convergence, posterior-family reachability, global optimality or universal CSTATE necessity. See the [verified manuscript theorem and complete compact proof](final_theory/VERIFIED_THEOREM.md) and [independent review](final_theory/REVIEW_RECEIPT.json).

## 4. Exact manuscript-safe wording

> On the frozen 1,024-observation population, the conservative F1 implementation matched the reference under all registered semantic checks, with zero observed differences in the independently compared fields. On 64 fixed matched observations in a common single-thread environment, it reduced mean complete latency from 0.6522 s to 0.5597 s and removed 31.75% of the acquisition-time excess over F0. The remaining runtime gap cannot be uniquely attributed to intrinsic algorithmic work.

> The scalar covariance contraction is exact only when the path-overlap trace functionals annihilate the specified covariance family. Distinct-delay orthogonality establishes isotropic compatibility but does not generally remove cross-delay terms under nonuniform AF-coordinate covariance. The same-delay doublet bound quantifies a normalized matrix approximation error; it does not establish a receiver-performance or convergence guarantee.

## 5. Remaining limitations and stop

Only two forensic/attribution limits remain: the old Cfast first-divergence cause is not identifiable from its saved intermediates, and residual implementation cost versus intrinsic work is not quantitatively separated. Neither is hidden or replaced by a stronger claim. No mathematical gap remains within the stated theorem assumptions. This closes the requested method/theory stage; no further experiment, optimization branch or algorithmic contribution is proposed.

## 6. Provenance and recovery history

Registration Git `64dbd9904d060c17e5faff6bd9f64b8b323f5ca4`; observed Git `09abb05632a682176954250b783b787a5cfdddac`; primary timing Git `2f81d00514508d938202c1dfef2fb4026a2a1a40`. Actual Git blobs and ancestry were verified. Failures are separate: an independent NPZ-envelope reader failure before comparisons; a deployment omission before any receiver call; and the original timing analyzer's Git-prefix error before statistics. Their original artifacts and receipts remain preserved. The successful run used unchanged receiver sources and the original 192-call allocation.

[Artifact paths and hashes](FINAL_TWO_ITEM_HASHES.json) · [Independent timing recount](final_f1/independent/TIMING_RECOUNT.json) · [F1 report](final_f1/F1_RESULT.md).
