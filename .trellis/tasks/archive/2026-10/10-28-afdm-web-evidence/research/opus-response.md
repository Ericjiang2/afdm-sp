**Overall:** The plan is sound and properly scoped. Most of the risk sits in how the Git exchange relates to the evidence drop and the vault.

## Must-fix

**1. Give the exchange's `main` a continuous history and minimal content.**
The plan says `main` holds "the AFDM project export" and is "tied to the same manifest." If each release rebuilds `main` as a fresh `git archive` root, two things go wrong:
- `chatgpt/*` branches from an older release lose a usable merge-base.
- "Display only the learning diff" turns into `main..branch`, which pulls in every evidence change between releases.

Fix:
- Commit each release on top of the previous `main`, never as a new root.
- Compute the return diff as `merge-base(main, branch)..branch -- learning/`.
- Apply it to the vault with `git apply --check --directory=00_Inbox/AFDM-channel-estimation` against the recorded baseline commit.

**2. Exclude the sealed exam and bulk material from everything AgentDock can read.**
"Absent from the search index" only holds if the exam is absent from every path the `agentdock` user can read. That includes the `afdm-sp` clone's `main`, not just the drop. A full-subtree `main` would also put the sealed exam and about 1.3 GiB into the clone.

Fix:
- Assert that the exam paths are absent from both the release tree and the clone checkout.
- Make this a scripted check, not a reading-instruction promise.

**3. The identity and root assertions don't guard the writes that actually happen.**
Your glue runs on the Mac and at publish time. But ChatGPT writes through AgentDock's file tools, as the same uid that can write the `afwdm` clone. The existing `afwdm` hook would probably accept a stray AFDM note under `learning/` on a `chatgpt/*` branch. Nothing in this plan detects that.

Without adding isolation:
- Put the clone's absolute path and `afdm-e2e-main` identity in the AFDM reading instructions.
- Have the Mac return step reject any proposal file outside `learning/sp_minimal/` or lacking the AFDM identity file.
- In step 5, make "no AFWDM file changed" concrete. Snapshot `git status` and `chatgpt/*` refs in the `afwdm` clone and its bare repo before and after the smoke test.

**4. Mid-conversation release switches can mix evidence.**
"Resolve `current` once per operation" is undefined for a ChatGPT conversation that spans many tool calls. If `current` flips mid-session, answers can cite two releases.

Fix:
- After first resolution, instruct reading and citation through `releases/<id>/...` paths, never `current/...`.
- Have saved learning notes record that same ID.

**5. Make the switch actually atomic and actually read-only.**
- `ln -sfn` is not atomic. Create a temporary symlink, then `mv -T` it over `current`.
- After upload and hash verification, `chmod -R a-w` the release.
- Verify as the `agentdock` user that a write attempt fails. Inspecting modes alone isn't enough, since group membership changes after a restart could alter access.

## Largest avoidable complexity

The dual publication of evidence, once into the immutable drop and again into the Git exchange `main`, kept in sync per manifest. This duplication is what creates issues 1, 2 and the mixed-release concern.

**Simpler alternative:** the exchange `main` carries only:
- `learning/`
- an identity file
- a one-line `RELEASE` pointer naming the release ID

Evidence lives only in the drop. This gives you:
- No evidence in Git history.
- Tiny, clean diffs.
- No mixed-release state.
- A nearly trivial return path.

It uses only the paths you already planned and needs no new mechanism.

## Optional

- **Unresolved references:** triage the 193 candidates only for the nine entry seeds and the three required read paths. Leave the rest labeled "unverified" in the manifest rather than resolving them all before first use.
- **Duplicate releases:** skip creating a new release when the manifest hash is unchanged. Don't build further dedup logic.
- **AgentDock restart:** do the `setup-share.sh` group change once, in a scheduled window announced to AFWDM use. Engineering a no-restart group arrangement is likely more effort than it's worth.
- **CLAUDE.md:** write the jgw read-replica exception as one sentence under the existing deinlab line, not a new section.
- **Smoke test:** add one test of a stale-release learning note returning cleanly after a newer release. This exercises the merge-base fix from issue 1.

Nothing here argues for templates, new modes, or stronger isolation. The free-form conversation scope is correctly kept out of the glue.
