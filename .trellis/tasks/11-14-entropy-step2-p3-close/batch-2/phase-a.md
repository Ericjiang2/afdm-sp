# SP stage-3 close-out: second read-only batch

2026-11-15; Codex. D18/Claude authorises at most eight largest whole-P3 groups across all three containers. No Phase B/C, vault staging/commit, disposal, move, source edit, project check, simulation, MATLAB or remote access. The first batch remains unchanged.

## Result

Reviewed **8 groups / 26,963 files / 3,497,467,848 logical bytes** (3.50 GB). Six result/output groups are retained; two mixed Mission groups remain under review. **Proposed reduction and actual reduction: 0 files / 0 bytes.** The inventory identifies bulk and partial bindings and measures branch-recoverable source copies. It does not establish an eligible disposal list.

| Group | Files | Bytes | Recommendation |
|---|---:|---:|---|
| results/afdm_efficient_information | 4,286 | 1,273,118,615 | 保留 |
| .mission/20261007-sp-fractional-trans | 4,745 | 555,312,468 | 继续待审 |
| results/afdm_higher_order_information | 4,233 | 495,552,950 | 保留 |
| afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909 | 6,152 | 339,538,509 | 保留 |
| results/afdm_method_advantage | 2,713 | 311,222,252 | 保留 |
| .mission/20260907_23-36-31-afdm-causal-plan-v3 | 2,451 | 190,899,972 | 继续待审 |
| afdm_sp_joint_unrolled/outputs_acquisition_n128_20261007 | 1,826 | 176,552,341 | 保留 |
| results/tf_cgr_mechanism_20260923_v2 | 557 | 155,270,741 | 保留 |

Five-destination totals are in `disposition-summary.csv`: retain 6 / 19,767 files / 2,751,255,408 bytes; review 2 / 7,196 files / 746,212,440 bytes; all other destinations zero. Whole-group retention in this batch does not declare every child permanently necessary.

## Selection and binding boundaries

Fresh recount retains 136 actual directories: 72 whole-P3, 59 mixed/unresolved, five non-P3 under the existing inferred per-file phase model. Sort whole-P3 groups by bytes and take eight after excluding R3 dependencies. `skipped-r3.csv` records the higher-order-information Mission, shared-channel-followup Mission and innovation-space Mission as retained without further review; their complete groups are excluded even where only a descendant is loaded. No experiment directory is reviewed for disposal.

The first batch was selected from prior current-root zero-hit candidates; it was not a random or whole-volume sample. This batch deliberately removes that candidate restriction and takes the largest eligible groups. It does not assume large means disposable.

`review.csv` has one full review row per group: date/experiment, current tracked/ignored/untracked counts, binding evidence, unresolved-prefix status, reachable tracked revision, recovery limits, writer uncertainty, disposition/confidence and zero reduction. `bindings.csv` records literal references and their immediate target scopes. Its 37,124 occurrences include repeated manifest entries and copied records; they are **not** 37,124 independent consumers or observed runtime reads.

- Efficient/higher-order/method outputs are linked from STATE/research evidence and their generation/audit records. For these three, every immediate child bucket is specifically named within the stated text coverage. This does not prove every byte must stay forever, but a whole-group “unbound” verdict is false.
- Comprehensive supplement includes frozen-pilot/source ancestry, Mission evidence, audit and timing harvests. The current frozen receiver handoff still names its pilot definition. A whole-group move cannot be justified by duplicate-code volume alone.
- Acquisition n128 has a directly imported dispatch helper and a result-card provenance pointer. The diagnosis's unresolved remote-root path intersects this exact group. That record remains a disposal blocker, not an ignored remote duplicate assumption.
- CGR v2 is a sealed historical result with STATE and explicit observed-input readers. Original/r2/prebind records remain separate; this inventory does not re-evaluate its scientific findings.
- The two Mission groups mix bound evidence, source/launcher copies, literature and a third-party dependency distribution. They are not classified as disposable process history.

## One-level partial view

`children.csv` contains **173 immediate-child/root-file buckets**, with files/bytes/Git states, direct child reference counts and scope limits. Only one level was split. A root-file reference is kept distinct from a group-level link; a concrete child directory need not end in `/` to be recognised.

| Group | Bytes in specifically named child buckets | Bytes with no child-specific literal binding found |
|---|---:|---:|
| efficient_information | 1,273,118,615 | 0 |
| fractional-trans Mission | 484,168,832 | 71,143,636 |
| higher_order_information | 495,552,950 | 0 |
| comprehensive supplement | 225,901,499 | 113,637,010 |
| method_advantage | 311,222,252 | 0 |
| causal-plan-v3 Mission | 189,038,254 | 1,861,718 |
| acquisition_n128 | 84,564,677 | 91,987,664 |
| CGR v2 | 154,607,374 | 663,367 |

The second column is a literal-target classification, not a completeness verdict. The **279,293,395 bytes** in the last column are **not proposed savings**: group-level/implicit/dynamic/source-manifest reach and retention purposes remain unresolved. For example, comprehensive's timing harvest, fractional engineering evidence and acquisition execution payloads cannot be declared unused merely because no direct child path was found. Source-gap protection is not narrowed to only already-proven consumers.

## Mission source equality against branch-reachable Git content

Scope: regular source files with the diagnosis's source suffix set, including launchers/tests/notebooks, excluding symlinks and binary payloads. Enumerated all local `refs/heads` ancestry with Git's object traversal. Content identity keys avoid an expensive all-pairs scan; **every hit was then read from Git and compared byte-for-byte with the current file**. This is not merely a digest match. No source was imported/executed or restored. Branch tips/method are in `mission-source-summary.json`; per-file recovery objects and roles are in `mission-source-equality.csv`.

| Mission | Source files / bytes | Byte-equal reachable files / bytes | No byte-equal branch-reachable source / bytes |
|---|---:|---:|---:|
| fractional-trans | 1,265 / 21,962,031 | 1,241 / 21,901,617 | 24 / 60,414 |
| causal-plan-v3 | 986 / 19,860,902 | 38 / 0 | 948 / 19,860,902 |

The 38 matches in causal-plan-v3 are empty files. Of its 948 nonmatching source files, **934 belong to local-deps/scipy**, 12 to evidence, and two are root builder/validator scripts. “Unique relative to branch-reachable Git blobs” is not scientific originality or proof no copy exists elsewhere. The 24 fractional nonmatches are launchers/dispatch/test code and remain preserved. Reachable source copies account for only 21,901,617 bytes, not the full Mission payloads or a demonstrated removable subset.

Recovery of currently tracked unchanged files is supported by main/HEAD. Whole-group recovery including ignored/untracked data is not established. Numerical regeneration is **未验证**, and remote copies/writers are **没查**. Historical launcher destinations are visible, but no absence of running local/remote producers is asserted. No old source contract is treated as a successful regeneration attempt.

## Unresolved coverage and validation

`unresolved-intersections.csv` records 15 group intersections: an exact acquisition result-card prefix plus broad core-output/Mission globs. Storage-location documentation and generic namespace patterns do not prove actual consumption, but were not silently discarded. The 4,714 diagnosis records without a visible prefix remain a global residual risk. The eight results-area unresolved records still name prospective/Stage-A/Stage-B-resume groups outside this batch, as checked in the first batch.

The initial all-tracked Git grep was too broad and was stopped after inspecting its own child process. Final coverage uses tracked text suffixes outside bulk results/core-output payloads, plus current protocol/source/asset/task/entry text including untracked/ignored documents. It includes historical cards, reports and Mission records; binary documents, bulk numerical payload references and arbitrary dynamic/basename-only loads are not fully parsed. This narrower coverage is stated explicitly and is not used to prove that unmentioned children are unused.

Before handoff, validate selection order/exclusions, exactly eight unique whole-P3 groups, child/group/summary arithmetic, source-match counts and original-branch reachability metadata, actual reference-file paths, and unchanged Git status/index. These are inventory/metadata invariants, not project tests or numerical reproduction. Final result and elapsed time are in `validation.json`. No Phase B decision time has occurred. Stop here; a narrower child disposition still needs evidence and Eric's Phase B approval. No extra batch or execution plan is started.
