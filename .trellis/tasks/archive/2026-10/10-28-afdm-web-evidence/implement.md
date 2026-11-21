# Implementation plan — approved 2026-10-28

Eric approved implementation with "执行" after final design review. Deployment
uses the specified existing service and project paths; no source deletion.

1. Recheck source and targets.
   - Inspect vault status; choose and record the source commit explicitly.
   - Refresh `ssh jgw 'bash ~/host/bin/session-context.sh'` per the host rule;
     inspect whether `afdm-sp` paths/remote names already exist. Do not overwrite
     existing files or touch `afwdm`.
   - Validate current `setup-share.sh` behavior. It may restart AgentDock when
     adding a group; this could interrupt AFWDM. Schedule/approve that concrete
     shared-service interruption before applying it. Do not engineer extra
     permissions to avoid a one-time planned restart or restart silently.

2. Finalize the publication allowlist.
   - Review `research/initial-paths.txt`, entry dependencies, source-secret
     content and candidate missing links. The coarse scanner is not a publisher.
   - Preserve all selected source bytes; no deleting old tests or deduplicating
     frozen imports. Label remote-only, sealed and on-demand references.
   - Required read-path checks: current STATE -> result card -> protocol -> small
     result/limitation; learning README -> correct source file; recent mainline
     merge decision -> current evidence. No automatic reading of exam content.

3. Add the smallest project-local publication/return glue.
   - Explicit source ref, subtree export, project identity, manifest/hashes,
     dry-run path listing and immutable evidence. The exchange carries only
     unsealed `learning/sp_minimal/`, identity and `RELEASE`, on continuous main
     history; no evidence clone, GitHub push or whole-vault history.
   - Reuse Git/archive and the host exchange mechanism; no new user/service.
   - Assert project root, source prefix, remote and write paths before mutation.
   - Document the deinlab-only restriction / jgw-read-replica exception and
     AFWDM read-only prerequisite mapping. Do not add conversation templates.

4. Verify the glue locally, then provision the agreed host paths.
   - Wrong root/AFWDM remote, path traversal, outside-learning changes,
     uncommitted input and partial/hash-mismatched releases must fail explicitly.
   - A stale-release learning branch survives an owner update with a valid
     merge-base. Its diff is confined to `learning/sp_minimal/`; compare Mac
     preimages and use `git apply --check` at the authoritative project prefix.
     Already-accepted proposals produce no new patch. An identical selected
     content manifest should not create an unnecessary release.
   - Inspect destination permissions: AgentDock can read evidence but cannot
     change it (test as that user); can change AFDM learning; sync refuses
     AFWDM targets. Create then rename a temporary symlink for an atomic release
     switch, and keep multi-call reads on the resolved immutable release path.
   - Use bounded SSH operations; preserve the previous current release on error.

5. Deployment integrity and user acceptance.
   - Eric performs real ChatGPT acceptance manually, per "验证我手动来".
     Do not operate the browser or write official learning test notes.
   - Compare AFWDM working-tree status/diff and proposal refs before/after with
     optional Git index writes disabled. Preserve pre-existing edits exactly.
   - Verify release hashes, effective AgentDock read/write permissions, exchange
     identity and absence of exam paths. Temp-repository tests cover learning
     return/history and atomic-release checks; label them as local tests.
   - Provide the project entry and normal commands. No scientific calls.

6. Deliver.
   - Review actual changes against the requirement set, stage only task files,
     and commit with project convention. Record host changes in `~/host` and
     follow its existing push authorization. No project/GitHub push without the
     concrete deployment authorization that covers it.
   - Update task evidence with exact tests, limitations and return-flow receipt.
     Keep this research project's existing state/claim authority unchanged.

Potential interruption, external publish actions and exact destinations must
be concrete before final deployment approval; do not substitute a generic
"continue" for unresolved privileged/shared-service changes.
