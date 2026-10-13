# Intake audit — 2026-09-21

Evidence class: read-only inventory and environment metadata. No scientific checks or experiments executed. Task remains planning.

## Documents and authority

Read all 318 lines of `/Users/guoyikun/Downloads/SP_AFDM_Frozen_Design_20260920.md` and all 120 lines of `/Users/guoyikun/Downloads/SP_AFDM_Frozen_Local_Protocol_20260920.md`. Frozen design is the primary scientific contract. Document historical test results are unverified locally. Embedded confirmation commands are outside the user-requested development/readiness endpoint.

## Package discovery

One explicitly requested GPT-5.6-luna xhigh read-only locator searched repository filenames including hidden paths, excluding forbidden docs/archive, and SP-AFDM/spafdm named Downloads paths/archives to depth six. It listed archives without extraction. Reported missing all expected fixed paths: seven tests/test_*.py qualification files, tests/benchmark_kernels.py, src/run_local.py, src/offgrid.py, src/bilinear.py, src/structured_ep.py, src/seal.py and protocol/configurations.json. This is a scoped search, not proof that no copy exists anywhere on either machine.

Available earlier candidates:

| Archive under /Users/guoyikun/Downloads | Inventory | Limitation |
| --- | --- | --- |
| spafdm_receiver_handoff_20260917.zip | 28 entries, 14 Python files | No frozen test/driver/protocol layout |
| spafdm_receiver_handoff_20260917-v2.zip | 54 entries, 33 Python files | Same missing later frozen package |
| spafdm_receiver_handoff_20260917-v3.zip | 107 entries, 86 Python files | Includes afdm_sp_joint_unrolled/run_frozen_i1_smoke.py, fixture, manifest, closure and checkpoint; no later suite/59-arm driver |
| SP_AFDM_Transactions_Manuscript_Package.zip | 231 entries, 111 Python files | Includes src/frozen_integration.py, frozen_integration CSV/JSON/log/NPZ, old handoff and inherited Certified_List_V4; not the 2026-09-20 executable delivery |

Two unrelated MATLAB SPAFDM.m files are not the frozen Python receiver. Existing repository results directories alone do not establish applicable SP-AFDM evidence.

## Deinlab environment

User explicitly authorized deinlab execution. Initial sandbox SSH attempt returned `Operation not permitted`; normal approval-policy escalation succeeded. This was not an automatic-review rejection. Only read-only remote commands ran.

- Host reports Linux 5.15 x86_64, 128 logical CPUs, about 490 GiB free and sampled load 0.07/0.05/0.01.
- System Python 3.10.12 lacks the four scientific dependencies; do not use it for the experiment.
- Existing `/home/guoyikun/.conda/envs/AFDM/bin/python`: Python 3.10.20; NumPy 1.26.4; SciPy 1.10.1; PyTorch 2.5.1+cu121; Matplotlib 3.7.1.
- Versions were read via importlib metadata, not numerical imports. CPU kernel functionality and effective thread settings remain unverified.
- Bounded search under remote home, depth four, excluding hidden/cache/env/archive directories, found no SP-AFDM-named package or run_local.py/configurations.json. Source may exist outside that scope.
- No remote file created, package installed, job stopped or experiment launched.

## Planning artifacts and validation

Created prd.md, design.md and implement.md in this task. `task.py validate` passed its context-file validation; inline mode requires no context JSONL entries. Separate static check confirmed all three documents are readable, contain no TBD and task.json remains planning. These are document checks only.

## Next required input

Location or attachment of the actual 2026-09-20 executable package, including upstream closure, tests, src and protocol registration. Earlier I1 archives may be reusable but cannot substantiate the frozen document's claimed existing implementation. Do not fabricate successful reproduction or silently reconstruct a different 59-arm experiment.

After source inspection, finalize exact affected-file list and present the planning review required by trellis-brainstorm before task.py start. Current platform prohibits implement/check sub-agent dispatch despite the user's explicit Sol high preference; only Luna discovery was delegated.
