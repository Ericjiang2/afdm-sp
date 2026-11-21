# AFDM web reading and learning

This checkout is `afdm-e2e-main`. Before writing, verify `PROJECT.json`, the
`/srv/git/afdm-sp.git` origin and the clone root
`/srv/agentdock/AgentDock/afdm-sp`. The separate AFWDM checkout is readable for
prerequisites, but AFDM work must never write there.

`RELEASE` names the immutable reading snapshot at
`/srv/share/afdm-sp/releases/<RELEASE>/`. Resolve that path once per evidence
question and use it for subsequent reads. The snapshot is selected, dated
evidence, not live experiment status or a complete runnable checkout. Start at
`ENTRY.md`, then follow the source's `STATE.md`, result cards and protocols.
If evidence is missing or stale, say so; do not infer acceptance from a copied
card or a saved log. Do not edit the snapshot, scientific records or source.

The only proposal path here is `learning/sp_minimal/`. Follow its `README.md`
and `/srv/share/personal/LEARNING_GUIDE.md` when Eric explicitly enters learning
mode. Read that guide's AI introduction first, then only the needed indexed
sections. Use `/srv/share/personal/explaining-to-eric.md` for explanations.
Its AFWDM M3b prerequisite may be read at
`/srv/agentdock/AgentDock/afwdm/learning/ce_minimal/`; do not copy those notes
into AFDM or claim completion without evidence. Preserve the sealed exam
boundary. Learning scripts and notes belong only under AFDM
`learning/sp_minimal/`. Use `python3 learning_branch.py start` and
`python3 learning_branch.py end --message 'learning: ...'` for the branch flow.

Outside learning mode, answer Eric's question freely. No fixed conversation
format or mandatory recording workflow applies.
