# (b) collaboration plan — owners, files, handoffs (2026-10-13)

| owner | does | writes ONLY | never |
|---|---|---|---|
| Sonnet (Claude subagent, xhigh) | driver --shuffle-arms flag + smoke; DATA GENERATION on deinlab (TRAIN8, CAL, later TEST, quiet subset); copy back small outputs | driver_c1esc.py (flag only), out/c1apb_train8/, out/c1apb_cal/, out/c1apb_test/, out/c1apb_quiet/ | analysis code, git, protocol changes, TEST before seal commit |
| Codex (gpt-6.1-sol xhigh, one task at a time, session 01a132fc…) | L = literature follow-up (read-only, now); IMPL = write + test ALL analysis code and run stage 1 / stage 2 on deinlab (network enabled for scp/ssh; no data-generation launches); A = results audit after TEST | c1apb_lib.py, c1apb_stage1.py, c1apb_stage2.py, unit_check_c1apb.py, out/c1apb/ (seal, analysis), research/codex-*.md | driver/data runs, git, protocol changes, TEST analysis before seal commit |
| Claude main (Opus) | decisions, freezes, commits, reads Codex/Sonnet summaries (≤10 lines each) + spot-checks flagged items | manifest, research notes, STATE, result card | duplicate a check already owned by Codex/Sonnet |

Handoffs (revised 2026-10-13, user: Codex writes code): Sonnet data (TRAIN8+CAL) || Codex IMPL code+unit checks -> Codex stage 1
-> seal -> Claude spot-check + commit seal -> Sonnet TEST data -> Codex stage 2 -> Claude result card. Review independence:
Sonnet (or Claude) spot-checks Codex code on leakage/causal replay before the seal (no duplicate full review). Every Codex task ends with a ≤10-line caveman summary (last message file) for Claude.

## Storage hygiene (user, 2026-10-13)
- Raw rows only on deinlab (/data/guoyikun); vault gets small summaries + REMOTE_ROWS_MD5.txt only. No large raw data locally.
- Scratch deleted as soon as it has served its purpose (owner cleans its own: Sonnet data smokes/sampler, Codex dry runs/unit
  outputs); anything that is evidence moves into the campaign out/ dir, not tmp.
- Finished evidence rows are gzip -9 compressed in place after their analysis/audit; md5 of the uncompressed rows stays the
  reference (verify with zcat | md5sum). Re-analysis: decompress first (scripts read rows_shard*.jsonl).
- Done 2026-10-13: deleted tmp/c1sg_smoke, tmp/c1esc_smoke, tmp/c1apb_smoke_off; gzipped out/c1rt (50M -> 13M) and out/c1sg
  (19M -> 5.2M) rows, md5 verified. Pending: after seal -> move tmp/c1apb_smoke anchors to out/c1apb/anchors, delete Codex
  dry runs (tmp/c1apb_dryrun*, tmp/c1apb_unit*.json); after stage 2 + audit -> gzip out/c1esc, out/c1apb_* rows, delete
  sampler script. Older scratch from earlier sessions in tmp/: not touched without user OK.

## Next workstreams (2026-10-13 after (b) screening; user: M1 check + B derivation, and A in parallel)
| stream | owner | writes ONLY | stop point |
|---|---|---|---|
| M1 upper-bound check | Sonnet (resumed a58a73ff) | research/m1-beta-dispersion-20261013.md; remote scratch /data/guoyikun/tmp/m1_beta (delete after) | report vs frozen rule below |
| B correction derivation | Codex KR session (resume 01a1339e) | research/codex-B-derivation-20261013.md | derivation + test plan; no code, no runs |
| A transfer-test protocol | Codex main session (resume 01a132fc) | research/aprime-A-transfer-protocol-20261013.md | protocol only; Claude freezes before any run |
M1 frozen decision rule (Claude, before data): r_{l,d} = beta_{l,d}/||x||^2 with beta_{l,d} = sum_k |m_d[k]|^2 |x_t[(k-l) mod N]|^2.
If the 99th percentile of |r - 1| <= .05 in every case -> the M1 approximation is bounded small: drop M1 as a method item (keep
as a methods caveat). If > .20 in any case -> proceed to a receiver-level M1 arm test. Otherwise: report; Claude decides.
Rows of finished campaigns are gzipped on deinlab (rows_shard*.jsonl.gz; md5 refers to uncompressed content).

## Decisions after M1 / B / A reports (Claude, 2026-10-13 18:30)
- M1 (m1-beta-dispersion-20261013.md): middle branch. r is zero-mean (per-d mean .995-1.009), typical |r-1| .005 (pilot only)
  to .02-.03 (with data), p99 .11 under ideal feedback, max .158. Decision: drop M1 as a standalone method item (second-order
  effect of a zero-mean per-column precision error); its in-receiver effect is measured by B's RAW20 control arm.
- B (codex-B-derivation-20261013.md): run B0 (contract, <= 12 smoke calls) and B1/B2 (mechanism screen, 6 cells x 32 frames x
  6 arms, R = 1) exactly as written there, frozen now; B3/B4 load screen only if B1/B2 pass. Novelty risk: OAMP-JED (arXiv
  2606.25420) closest; GLOB20 arm is the global-extrinsic control. Owner end-to-end: Codex KR session (01a1339e) — kernel
  variant in a NEW module (frozen dpss_rx untouched), driver, B0-B2 runs on deinlab (network on, <= 32 shards, load guard,
  /data/guoyikun only, gzip rows after), analysis. B3/B4 data (if reached) -> Sonnet.
- A (aprime-A-transfer-protocol-20261013.md): frozen as written (archival transfer screen with unlabelled round-1 probes;
  zero new simulation; A0-A4 gates; K-A1..K-A4 kill rules). Owner: Codex main session (01a132fc): implement, seal predictions,
  then unseal truth and evaluate.
