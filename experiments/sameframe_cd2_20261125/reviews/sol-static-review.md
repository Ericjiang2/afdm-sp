OpenAI Codex v0.170.0
--------
workdir: /tmp
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20e7a-d98e-7802-8cfa-bd422a12851c
--------
user
You are Sol performing a concise (<= 3 min) pre-launch static review of the new experiment at:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/`

Files to inspect:
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/PROTOCOL.md`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/test_sameframe_cd2.py`
- `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/launch.sh`

Check specifically:
1. Part A (`CD2`, `CD2e8` on frames `41000-41399`, rho `{100,150,200,250}`, `stageA.SNRS`):
   - Exact reuse of `sameframe_hg_20261124/sameframe.py` and `stageA`/`stageA2`/`stageA3` without touching frozen files.
   - Untriggered keys take `stageA` `arms.base.f0_errors`; triggered keys assert F0 `syndrome`/`f0_errors` parity and `CD2` pass-1 `errors == arms.base.errors`.
   - Primary `P1' = min CD2 (100..250) - min s100 (100..200)`: joint paired frame bootstrap (`2000` draws, seed `20261125`), 95% CI, censoring safety, `DOPPLER-LINE` (`>= 0.5`) / `STOP-LINE` (`< 0.5`) / `INCONCLUSIVE`.
2. Part B (quiet single-core timing on two panels: `rho=.20, 4.5 dB` and `rho=.30, 5.0 dB`, 100 triggered + 50 untriggered F0 each, `CD`, `CD2`, `CD2e8`, `HG`, `HGint`, plus `HG1`):
   - Pre-pinned `taskset` single idle core, decision-ready timing boundary matching `hs_arms`, per-scenario balanced 5-arm rotation, archive `decoded_sha` verification, scenario-stratified amortization, raw rows MD5 recorded.
3. Gates G1–G3, budget (`<= 6.0` core-hours at `1.3×`, drop `CD2e8` from Part A first if over), deinlab rules (`cd /data/guoyikun/00inbox/AFDM-channel-estimation`, AFDM python, single-thread env, `CUDA_VISIBLE_DEVICES=""`, `<= 32` workers, `/data/guoyikun/tmp`, zero `/dev/shm`), `_argv`/`_config`, atomic writes.
4. Any crash bugs, schema mismatches, or silent fallbacks.

Be concise and end with `VERDICT: PASS` or `VERDICT: FIX`.

warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
hook: SessionStart
hook: SessionStart Completed
codex
自检：1 个红项（纠正记录（自检故障））；自查信号待复核 84 项，最早 2026-11-19，说“跑一次 L2”处理。等你处理：4 个红项（L0、Vault 工作树、复盘证据 等 4 项）（决定项见最近系统报告 2026-11-18）。详情见 vault 的 系统状态.md

我会用 `research-checkpoint` 做启动前静态审查，先对照协议和冻结实现，再核查门禁与启动脚本。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md' in /tmp
 succeeded in 0ms:
---
name: research-checkpoint
description: Use at four moments in any research project — (1) before freezing an experiment protocol or launching a pre-registered run, (2) before reporting results or writing/accepting a result card, (3) when a result contradicts expectation or you are about to explain a result, (4) when choosing or changing research direction or the paper's main line. Gives a short checklist for each moment.
---

# Research checkpoint

These are short checklists. Do the one for the current moment, write its answers into the artifact (protocol, card,
report or decision brief), then continue. Background: `../../docs/methods-handbook.md`
and `../../RULES_MAP.md` (relative to this skill's source directory; resolve its symlink first).

## 1. Before freezing a protocol or launching a pre-registered run

1. **Competing hypotheses.** Write down 2–3 alternatives and what each predicts for every arm. If all of them predict the
   same thing, the experiment cannot discriminate: redesign or drop it.
2. **Design validity, four questions.**
   - (a) Does each contrast change exactly one factor? If the conclusion will credit a component (a term, a module, a prior),
     is there an arm that removes it entirely, and is the simplest baseline in? If not, write why. The external design review
     (item 5) checks this too. Handbook A12.
   - (b) Leverage: from existing data or gate units only, is the expected difference clearly above noise? If a hypothesis
     predicts no difference, write an equivalence prediction.
   - (c) Statistical unit: cluster at the level where randomness is shared.
   - (d) What exactly does every proxy or oracle mean?
3. **Premortem.** If the result came out opposite to expectation, what is the most likely reason, and does the design
   already rule it out?
4. **Prediction ledger.** Record your own predictions with probabilities.
5. If the conclusion will be stated as a **mechanism**, get one short external review of the design and decision rule,
   using a different model, before freezing.
6. Verify every gate statement against the code. Commit before running. Run long jobs as one unattended chain with a cost
   stop and a DONE/STOPPED status line, and do not poll.
7. Optional, judge per case: would a small slice answer the decision question earlier? If the run is costly or its
   answer may change the plan, offer a staged look (pilot slice where events are dense, stop at the first useful result,
   report). Not for confirmatory claims. See `docs/methods-handbook.md` B8.

## 2. Before reporting results or writing a result card

- Report in three layers:
  1. observation (numbers);
  2. pre-registered verdict, stated as frozen and never relabelled;
  3. candidate explanation, marked *untested* with an H/M/L confidence.
- Credit an effect to a component only against a neutral control (its removal or the simplest working baseline), and only
  if the comparator is not worse than no intervention; otherwise say "A beats B", not "X causes it". When removal is
  ill-defined, say why and use the simplest working baseline.
- Say "unified", "proven" or "refuted" only after a pre-registered or prospective test has passed.
- Correct earlier findings with explicit correction notes; never rewrite them silently.
- Score the prediction-ledger entries for this run.
- Before writing shared records (IDs, state files, indexes), check what is already there.

## 3. When a result contradicts expectation

1. **Audit before explaining**: check data consistency across experiments, confounds and the statistical unit. If the
   surprise is a difference between two pipelines, first list every stage that differs and toggle the unintended ones
   (handbook B9).
2. Offer at most **one** new explanation, together with its cheapest falsifying test. Do not stack explanations on
   untested ones.
3. Optionally, ask a different model for up to two explanations without showing it yours, then compare.

## 4. When choosing or changing direction or the main line

1. Write your own assessment and commit it first.
2. Ask a different model for an independent assessment. Give it an input bundle: the goal, the primary evidence (result cards
   including drafts, open anomalies, the negative-results ledger) and nothing of your assessment or framing. It states the
   problem in its own words first, and gives at least one rival explanation that needs neither the main component nor the
   main claim. Trigger an extra outside audit on events, not on a calendar: a premise of the main claim is falsified, the
   claim survives only by narrowing twice, an unexplained tie or reversal stays open, and once before writing starts.
   Choose the model by capability for the task.
3. When you relay other models' analyses, list each source's own conclusion and every point with its source, and state
   adopt / modify / reject with a reason before merging; afterwards check that every point appears or is marked rejected.
   Then make the divergence table. The user decides. Do not run multi-round debates.
4. Value decisions (starting a line, changing direction, calling a result Transactions-level or a principle), handbook A13:
   - Headroom first: in the target regime, measure the simplest sane baseline, our method and a genie or bound. Look for a
     principle only where the baseline is clearly short of the genie and fails for a nameable reason.
   - Who already does it: a table of the 5–10 closest papers, one plain sentence each with equation or section location;
     the user spot-checks two rows against the source. A "nobody does X" claim lists its search terms and the three closest
     papers.
   - Case for and case against, by two different models from the same bundle, each citing checkable evidence and stating
     what would change its mind. A third pass names only the 1–3 factual cruxes and the cheapest check for each. Decide by
     checking the cruxes, not by which case reads better. Offer 「白话」 for all three.
   - A "no" parks the idea in the open-threads list with a revival condition; a "yes" passes a cheap kill test before
     large investment.
   - Suggest showing the three plain sentences to the advisor or a senior student.
   Not for routine experiments, status reports or small decisions inside a settled direction.
5. Use the top-level checks: importance (Hamming), feasibility × interest (Alon), Heilmeier questions, and the outside
   view (base rates).
6. Every recommendation gives the strongest alternative, the evidence that would change it, and a confidence level.

exec
/bin/zsh -lc 'nl -ba PROTOCOL.md && nl -ba launch.sh' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
exec
/bin/zsh -lc "wc -l *.py && rg -n '"'^(def|class|from|import)|G[123]|md5|atomic|bootstrap|taskset|budget'"' *.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
 succeeded in 0ms:
    1186 sameframe_cd2.py
      68 test_sameframe_cd2.py
    1254 total
test_sameframe_cd2.py:1:"""Unit tests for sameframe_cd2.py P1' verdict rules, joint bootstrap, and 5-arm timing rotation."""
test_sameframe_cd2.py:2:from __future__ import annotations
test_sameframe_cd2.py:4:import math
test_sameframe_cd2.py:5:import sys
test_sameframe_cd2.py:6:from pathlib import Path
test_sameframe_cd2.py:7:import numpy as np
test_sameframe_cd2.py:13:import sameframe_cd2 as sc  # noqa: E402
test_sameframe_cd2.py:14:import stageA2  # noqa: E402
test_sameframe_cd2.py:17:def _make_fail(curves: dict[int, list[float]], n: int = 200, seed: int = 7) -> np.ndarray:
test_sameframe_cd2.py:30:def test_p1p_verdict_boundaries():
test_sameframe_cd2.py:39:def test_analyze_partA_and_rotation():
sameframe_cd2.py:2:from __future__ import annotations
sameframe_cd2.py:4:import argparse
sameframe_cd2.py:5:import gzip
sameframe_cd2.py:6:import hashlib
sameframe_cd2.py:7:import json
sameframe_cd2.py:8:import math
sameframe_cd2.py:9:import os
sameframe_cd2.py:10:from pathlib import Path
sameframe_cd2.py:11:import platform
sameframe_cd2.py:12:import re
sameframe_cd2.py:13:import shutil
sameframe_cd2.py:14:import sys
sameframe_cd2.py:15:import time
sameframe_cd2.py:16:from time import perf_counter
sameframe_cd2.py:17:from typing import Any
sameframe_cd2.py:19:import numpy as np
sameframe_cd2.py:31:import hs_analysis as an  # noqa: E402
sameframe_cd2.py:32:import hs_arms as ar  # noqa: E402
sameframe_cd2.py:33:import sameframe as sf  # noqa: E402
sameframe_cd2.py:60:def own_md5() -> dict[str, str]:
sameframe_cd2.py:61:    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}
sameframe_cd2.py:64:def verify_sameframe_hg_manifest() -> dict[str, str]:
sameframe_cd2.py:78:        actual = ar.md5_file(p)
sameframe_cd2.py:88:def verify_all_archives() -> dict[str, dict[str, str]]:
sameframe_cd2.py:94:def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
sameframe_cd2.py:115:    for name, exp_md5 in live_own.items():
sameframe_cd2.py:122:        if hashlib.md5(blob.stdout).hexdigest() != exp_md5:
sameframe_cd2.py:127:def run_cd_timed(
sameframe_cd2.py:188:# --------------------------------------------------------------------------- Gates G1-G3
sameframe_cd2.py:189:def _g1_g2_worker(in_path: str, out_path: str):
sameframe_cd2.py:200:            raise AssertionError(f'G1 F0 mismatch at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})')
sameframe_cd2.py:204:                f'G2 CD2 pass-1 errors mismatch vs stageA base at {(s, rho, snr, frame)}: '
sameframe_cd2.py:218:    ar.atomic_write_text(Path(out_path), json.dumps(res))
sameframe_cd2.py:221:def _g3_cost_worker(in_path: str, out_path: str):
sameframe_cd2.py:233:            raise AssertionError(f'G3 key untriggered: {(s, rho, snr, frame)}')
sameframe_cd2.py:238:            raise AssertionError(f'G3 CD2 pass-1 drift at {(s, rho, snr, frame)}')
sameframe_cd2.py:247:    ar.atomic_write_text(Path(out_path), json.dumps(res))
sameframe_cd2.py:250:def cmd_gate(args):
sameframe_cd2.py:274:    # 20 keys for G1+G2: 5 per rho in 100..250, guaranteeing U/G, low/mid, and both pass-1 pass & fail
sameframe_cd2.py:303:        print('Running G1+G2 (20 low-pilot stageA F0 + CD2 pass-1 + CD2e8 keys)...', flush=True)
sameframe_cd2.py:309:            raise AssertionError(f'G2 did not cover pass-1 and pass-2: p1={cd2_p1}, p2={cd2_p2}, e8_p2={e8_p2}')
sameframe_cd2.py:310:        print(f'G1+G2 PASS (20/20; cd2_p1={cd2_p1}, cd2_p2={cd2_p2}, cd2e8_p2={e8_p2})', flush=True)
sameframe_cd2.py:312:        print(f'Running G3 stratified cost projection ({len(g3_jobs)} Part-A keys)...', flush=True)
sameframe_cd2.py:341:            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
sameframe_cd2.py:346:    selected = next((c for c in candidates if c['within_budget']), None)
sameframe_cd2.py:356:            own_md5=own_md5(),
sameframe_cd2.py:357:            frozen_extra_md5=helpers['extra_md5'],
sameframe_cd2.py:358:            p1_source_md5=ar.frozen_p1_md5(ctx),
sameframe_cd2.py:369:        G1=dict(passed=len(g12_rows) == 20, keys_checked=len(g12_rows)),
sameframe_cd2.py:370:        G2=dict(passed=True, keys_checked=len(g12_rows), cd2_p1=cd2_p1, cd2_p2=cd2_p2, cd2e8_p2=e8_p2, rows=g12_rows),
sameframe_cd2.py:371:        G3=dict(
sameframe_cd2.py:373:            budget_cap_core_hours=BUDGET_CAP_HOURS,
sameframe_cd2.py:380:    ar.atomic_write_text(out_dir / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
sameframe_cd2.py:390:def _partA_shard_worker(
sameframe_cd2.py:428:    sf._write_gzip_jsonl_atomic(final_path, out_lines)
sameframe_cd2.py:432:def p1p_verdict(ci_lo: float, ci_hi: float) -> str:
sameframe_cd2.py:440:def analyze_partA(
sameframe_cd2.py:449:    """Joint paired physical-frame bootstrap analysis for P1' (frames 41000-41399, seed 20261125)."""
sameframe_cd2.py:544:def render_results_md(res: dict[str, Any]) -> str:
sameframe_cd2.py:604:            for arm in ('CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint'):
sameframe_cd2.py:617:def _do_read_partA(
sameframe_cd2.py:620:    gate_md5: str,
sameframe_cd2.py:623:    raw_md5: dict[str, str],
sameframe_cd2.py:635:    for fname, expected in raw_md5.items():
sameframe_cd2.py:636:        if ar.md5_file(raw_dir / fname) != expected:
sameframe_cd2.py:647:    # Load archived sameframe_hg Part 1 (HG, HG1, HGint)
sameframe_cd2.py:648:    hg_arms = ('HG', 'HG1', 'HGint')
sameframe_cd2.py:757:            own_md5=own_md5(),
sameframe_cd2.py:758:            gate_md5=gate_md5,
sameframe_cd2.py:764:            raw_rows_md5=raw_md5,
sameframe_cd2.py:770:            G1_keys=gate['G1']['keys_checked'],
sameframe_cd2.py:771:            G2_keys=gate['G2']['keys_checked'],
sameframe_cd2.py:772:            G3_projected_hours=gate['selected']['projected_hours_with_margin'],
sameframe_cd2.py:778:    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
sameframe_cd2.py:779:    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
sameframe_cd2.py:789:def cmd_run_partA(args):
sameframe_cd2.py:806:    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
sameframe_cd2.py:810:    live_own = own_md5()
sameframe_cd2.py:812:    if gate['_config']['own_md5'] != live_own:
sameframe_cd2.py:813:        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
sameframe_cd2.py:819:    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
sameframe_cd2.py:820:        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
sameframe_cd2.py:821:    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
sameframe_cd2.py:822:        raise RuntimeError('p1_source_md5 mismatch vs gate.json')
sameframe_cd2.py:839:    raw_md5 = {}
sameframe_cd2.py:842:        raw_md5[p.name] = ar.md5_file(p)
sameframe_cd2.py:843:    ar.atomic_write_text(
sameframe_cd2.py:845:        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
sameframe_cd2.py:855:        out_dir, gate, gate_md5, args.freeze_commit, runtime_info, raw_md5,
sameframe_cd2.py:861:def _latency(values: list[float]) -> dict[str, Any]:
sameframe_cd2.py:871:def _load_huang_and_cd2_archives_for_panels(target_pairs: set[tuple[int, int]]):
sameframe_cd2.py:872:    """Load archived decoded_sha for HG/HG1/HGint (huang_steelman) and CD2/CD2e8 (sameframe_hg) on target (rho, snr)."""
sameframe_cd2.py:891:def cmd_timing(args):
sameframe_cd2.py:902:        raise RuntimeError(f'timing must be pre-pinned to 1 CPU via taskset, got affinity={aff}')
sameframe_cd2.py:911:    verify_freeze_commit_if_git(args.freeze_commit, own_md5())
sameframe_cd2.py:917:    # Verify cumulative budget before starting timing
sameframe_cd2.py:947:    all_report_arms = ('CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint')
sameframe_cd2.py:1034:                            or out['HG1']['decoded_sha'] != hga['HG1']['decoded_sha']):
sameframe_cd2.py:1035:                        raise AssertionError(f'Timing HG/HG1 drift at {key}')
sameframe_cd2.py:1037:                    sec_map['HG1'] = out['HG1']['seconds']
sameframe_cd2.py:1039:                    passes_map['HG1'] = 1
sameframe_cd2.py:1110:    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
sameframe_cd2.py:1111:    timing_rows_md5 = ar.md5_file(timing_rows_path)
sameframe_cd2.py:1113:    # Append timing_rows.jsonl MD5 into REMOTE_ROWS_MD5.txt atomically
sameframe_cd2.py:1114:    md5_map = {}
sameframe_cd2.py:1118:            md5_map[n] = d
sameframe_cd2.py:1119:    md5_map[timing_rows_path.name] = timing_rows_md5
sameframe_cd2.py:1120:    ar.atomic_write_text(
sameframe_cd2.py:1122:        ''.join(f'{d}  {n}\n' for n, d in sorted(md5_map.items())),
sameframe_cd2.py:1140:            timing_rows_md5=timing_rows_md5,
sameframe_cd2.py:1148:    ar.atomic_write_text(out_dir / 'timing_summary.json', json.dumps(timing_payload, indent=2, allow_nan=False) + '\n')
sameframe_cd2.py:1153:    results['_config']['raw_rows_md5'] = md5_map
sameframe_cd2.py:1154:    ar.atomic_write_text(results_path, json.dumps(results, indent=2, allow_nan=False) + '\n')
sameframe_cd2.py:1155:    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
sameframe_cd2.py:1165:def main():

 succeeded in 0ms:
     1	# 低导频第 0 轮多普勒余量再判（以 CD2 为新基线）与安静计时面板协议（`sameframe_cd2_20261125`）
     2	
     3	**状态**：冻结前稿（待 Sol 静态审查通过后冻结并提交 `Before ...`）
     4	**承接**：[sameframe_hg_20261124/READOUT.md](../sameframe_hg_20261124/READOUT.md)。此前 P1 对 `HG` 为 `INCONCLUSIVE`（`+0.7333 [+0.4549, +1.0396] dB`），而 P2 表明两遍局部交换 `CD2` 在黄帧 `5400–5799` 上已追平并微幅超过 `HG`（`−0.1246 dB`），因此当前正确基线转为 `CD2`。
     5	
     6	---
     7	
     8	## 1. 核心问题
     9	
    10	1. **Part A（主裁决 `P1'`，低导频帧 `41000–41399`）**：以两遍局部交换 `CD2` 为基线后，在低导频比例下，更优第 0 轮多普勒估计（代理 `s100`：真时延 + 高斯多普勒误差 $\sigma = 0.10$ bin，实测第 0 轮均值 $|\Delta\nu|\approx 0.080$ bin，导频 LS 增益）是否仍留有 $\ge 0.5$ dB 的 1% FER 余量？同时在同帧补测 `CD2e8` 并与已归档的 `HG`/`HGint`/`s050`/`ldop`/`full`/`delay`/`base` 联合配对比较。
    11	2. **Part B（安静单核计时面板，描述性无裁决，论文表格用）**：在 `HG`/`CD2` 共同最优点 $(\rho=0.20, 4.5\text{ dB})$ 与历史连续点 $(\rho=0.30, 5.0\text{ dB})$ 上，于 `taskset` 绑定单空闲核上以统一决策就绪边界实测 `CD`、`CD2`、`CD2e8`、`HG`（含 `HG1`）、`HGint` 的单触发延迟、第二遍比例、全帧摊销耗时及相对 `CD` 比值。
    12	
    13	---
    14	
    15	## 2. 实验设计与代码复用（不改任何冻结文件）
    16	
    17	所有逻辑直接复用已有模块：`experiments/sameframe_hg_20261124/sameframe.py`（`load_stage_runtime`、`run_cd_two_pass`、`load_stageA_base`、`verify_manifest`、`_select_balanced_keys`、`_spawn_map`、`_run_sharded_phase`、`_write_gzip_jsonl_atomic`、`crossing_bounds_stageA2`）、`experiments/huang_steelman_20261124/hs_arms.py`（`run_hg_arm`、`fine_grid`、`coarse_grid`、`load_archived_rho_sweep`）、`experiments/data_pilot_fer_20261121/{stageA,stageA2,stageA3}.py`。
    18	
    19	### Part A（帧 `41000–41399`，场景 U/G）
    20	- **网格**：$\rho \in \{100, 150, 200, 250\}$ permille，`SNR = stageA.SNRS`（3..12 dB 共 13 点）；总计 41,600 键，其中归档 `stageA` `arms.base.syndrome != 0` 的触发键共 **13,735** 键。
    21	- **逐键规则**：
    22	  - 未触发键（`arms.base.syndrome == 0`）：不重跑，直接取 `arms.base.f0_errors`。
    23	  - 触发键：重跑 `f0_state`，断言实时 `syndrome == arms.base.syndrome` 与 `f0_errors == arms.base.f0_errors`；随后运行 `CD2`（`arm_spec='A1'`，第 1 遍断言 `errors == arms.base.errors`；若第 1 遍 `syndrome != 0` 则按与 `HG` 相同的 `r1_*` 消息更新跑第 2 遍，校验通过提前停止）与 `CD2e8`（运行时 `A1e8` 克隆包装，`max_edits=8`，同两遍早停规则）。均禁用静默回退（`numerical_fallback=True` 或非有限值直接抛错）。
    24	- **同帧归档对照（不重跑，全部 MD5 校验）**：
    25	  - `stageA`（`base`/`delay`）、`stageA2`（`full`/`ldop`）、`stageA3`（`s025`/`s050`/`s100`/`s200`）、`sameframe_hg_20261124` Part 1（`HG`/`HG1`/`HGint`，清单 SHA-256 `7cac38cd7cc8fa610ddf8c0b5908b62c668901cf5b72756889c1fd6a0f6b435f`）。
    26	- **代理局限说明（跑前写定）**：`s100`/`s050` 为**带真时延**的高斯多普勒注入；Stage A3 已表明真实导频多普勒误差比同均值高斯误差温和，而未知时延下的真实半盲估计又会带来额外损失，故 `s100` 是结构化代理而非端到端估计器。
    27	
    28	### Part B（安静单核计时面板，黄帧 `5400–5799`，不设裁决）
    29	- **两组工况**（均从 `rho_sweep_20261119` 按帧号升序抽取）：
    30	  1. **最优点面板**（$\rho=0.20, 4.5\text{ dB}$）：前 50 U + 前 50 G 触发键（100 键）+ 前 25 U + 前 25 G 未触发 F0 键（50 键）。归档总触发率 U `199/400 (49.75%)`、G `227/400 (56.75%)`。
    31	  2. **连续性面板**（$\rho=0.30, 5.0\text{ dB}$）：前 50 U + 前 50 G 触发键（100 键）+ 前 25 U + 前 25 G 未触发 F0 键（50 键）。归档总触发率 U `88/400 (22.00%)`、G `110/400 (27.50%)`。
    32	- **计时臂与顺序**：5 臂 `('CD', 'CD2', 'CD2e8', 'HG', 'HGint')`（同时由 `HG` 第 1 遍免费记录 `HG1`）；按场景 U/G 分别维护轮换位置 `scenario_pos[s] % 5`，使两场景内每臂在 5 个顺序位各出现 10 次。
    33	- **计时边界与一致性**：统一采用 `hs_arms` 的**决策就绪边界**（从分支消息准备/入口开始，到最终 `syndrome_weight` 结束立即停表；真值计分与哈希置于停表之后）。每个计时键逐位核验 `decoded_sha` 与归档一致（`F0`/`CD` 核 `rho_sweep`，`HG`/`HG1`/`HGint` 核 `huang_steelman`，`CD2`/`CD2e8` 核 `sameframe_hg` Part 2）。
    34	- **隔离与绑核**：启动 Python 前扫描 `/proc/stat` 选出最空闲单核并用 `taskset -c <CPU>` 绑定运行，记录启动前空闲利用率和起止系统负载。原始逐键计时写入远端 `out/raw/timing_rows.jsonl` 并记录 MD5。
    35	
    36	---
    37	
    38	## 3. 门禁与预算（G1–G3，写入 `out/gate.json`）
    39	
    40	- **G1（Part A F0 复现）**：20 个 `stageA` 触发键（4 个 $\rho$ 各 5 键，覆盖 U/G 与高/低 SNR），实时 `f0_state` 与归档 `syndrome`/`f0_errors` 20/20 一致。
    41	- **G2（Part A `CD2` 首遍复现 + 两遍/多换冒烟）**：20 个低导频 `stageA` 触发键上，`CD2` 第 1 遍逐键复现 `stageA` `arms.base.errors`（20/20）；验证 `CD2` 与 `CD2e8` 均实际触发了第 1 遍早停与第 2 遍续跑路径，且全程无 `numerical_fallback` 与非有限值。
    42	- **G3（分层成本外推，×1.3 余量，$\le 6.0$ 核时）**：在 Part A 全部 8 个 $(\rho, \text{SNR 层})$ 各抽 4 键（共 32 键，U/G 平衡、内分位点）实测 `f0 + CD2 + CD2e8` CPU 时间，按精确触发键数（13,735）加权求和，加上 Part B 计时预留（`0.18 h`）及读写汇总余量（`0.12 h`），乘 `1.3×`。
    43	  - **预算顺序**：若含 `CD2e8` 外推 $\le 6.0$ 核时则全量运行；若超限则首先从 Part A 去掉 `CD2e8` 重算（Part B 仍保留全部 5 臂以保证论文计时表完整）；若仍超 `6.0` 核时则立即停机（`GATE_STATUS=FAIL_BUDGET`）并向 Eric 汇报。运行中硬停上限为累计 `6.0` 核时（触发写 `STATUS=STOPPED_BUDGET`）。
    44	
    45	---
    46	
    47	## 4. 冻结判读规则（跑后永不改标）
    48	
    49	### 主检验 `P1'`（帧 `41000–41399`）
    50	- **穿越点**：沿用 `stageA2.crossing(fer, snrs)` 在各臂自有 SNR 网格计算 1% 信息位 FER 穿越点，U/G 算术平均。
    51	- **估计量**：$D' = \min_{\rho \in \{100,150,200,250\}} c_{\mathrm{CD2}}(\rho) - \min_{\rho \in \{100,150,200\}} c_{\mathrm{s100}}(\rho)$（正值表示 `s100` 优于 `CD2`，即仍剩多普勒余量）。
    52	- **自助法**：物理帧配对重采样（`2,000` 次，**`seed = 20261125`**），联合重采样 `stageA`、`stageA2`、`stageA3`、`sameframe_hg` Part 1 与本实验 Part A；取 **95% 百分位区间**（`[2.5, 97.5]`；若出现截断抽样则用保守最近秩界并汇报 `censored_draw_fraction`）。
    53	- **唯一互斥判定表**：
    54	  - `DOPPLER-LINE`：95% CI 下界 $\ge 0.5$ dB
    55	  - `STOP-LINE`：95% CI 上界 $< 0.5$ dB
    56	  - `INCONCLUSIVE`：其余情况
    57	
    58	### 次要读数（描述性）
    59	- Part A：同口径下 `CD2e8 − s100`（若保留）、`CD2 − s050`、`CD2 − ldop`、`CD2 − full`、`CD2 − delay`、`CD2 − base`、`CD2 − HG`、`CD2e8 − HG`、`CD2e8 − CD2`；全部臂的逐 $\rho$ 穿越点表与各自最优 $\rho$；`CD2`/`CD2e8` 的第 2 遍救回率与平均换径次数。
    60	- Part B：两组工况下 5 臂（含 `HG1`）单触发均值/中位数/p95、第 2 遍比例、分场景摊销全帧均值耗时，以及相对 `CD` 的均值比、配对中位比与 `CD` 更快占比。
    61	
    62	---
    63	
    64	## 5. 跑前预测（冻结前记入 `research-assets/prediction-ledger.md`）
    65	
    66	- **Claude**：
    67	  - `CD2-C1`（`P1'` 判定）：`DOPPLER-LINE` .25 / `INCONCLUSIVE` .50 / `STOP-LINE` .25（点估计约 `0.6 dB`）
    68	  - `CD2-C2`（计时）：`CD2` 两遍单触发均值耗时低于 `HG` 均值耗时：.80（按主工作点 $\rho=.20, 4.5\text{ dB}$ 计分，并在读出中同时报告 $\rho=.30, 5.0\text{ dB}$）
    69	- **agy（Gemini 4 Neon）**：
    70	  - `CD2-G1`（`P1'` 判定）：`DOPPLER-LINE` .20 / `INCONCLUSIVE` .65 / `STOP-LINE` .15
    71	  - `CD2-G2`（计时）：`CD2` 两遍单触发均值耗时低于 `HG` 均值耗时（主工作点 $\rho=.20, 4.5\text{ dB}$）：.90
    72	
    73	---
    74	
    75	## 6. deinlab 执行规范
    76	
    77	- 工作目录：`cd /data/guoyikun/00inbox/AFDM-channel-estimation`；仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`，每份日志第 1 行打印 `sys.executable`）。
    78	- 环境变量：6 个线程变量全设 1、`CUDA_VISIBLE_DEVICES=""`、`PYTHONDONTWRITEBYTECODE=1`、`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；不写 `/tmp` 或 `/home/guoyikun`。
    79	- 并发与会话：Part A 使用 `24` 进程（$\le 32$，兼顾 16 核漏斗），Part B `taskset` 绑定单空闲核；`tmux` 会话名 `g_cd2`。
    80	- 产物留存：大原始分片（`out/raw/partA_shard*.jsonl.gz`、`out/raw/timing_rows.jsonl`）留在 deinlab，MD5 写入本地 `out/REMOTE_ROWS_MD5.txt`；本地保存小汇总（`gate.json`、`results.json`（含 `_argv`/`_config`）、`timing_summary.json`、`RESULTS.md`、`READOUT.md`、`STATUS` 与日志）。
     1	#!/usr/bin/env bash
     2	set -euo pipefail
     3	
     4	if [ "$#" -ne 2 ]; then
     5	    echo "Usage: $0 MODE FREEZE_COMMIT   (MODE = gate | run)" >&2
     6	    exit 2
     7	fi
     8	MODE="$1"
     9	FREEZE_COMMIT="$2"
    10	
    11	REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
    12	HERE="$REPO/experiments/sameframe_cd2_20261125"
    13	OUT="$HERE/out"
    14	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
    15	
    16	LOCKDIR="$OUT/.lock"
    17	if ! mkdir "$LOCKDIR" 2>/dev/null; then
    18	    echo "ERROR: lock $LOCKDIR already held" >&2
    19	    exit 1
    20	fi
    21	
    22	cd "$REPO"
    23	set +u
    24	source /opt/anaconda3/etc/profile.d/conda.sh
    25	conda activate AFDM
    26	set -u
    27	
    28	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    29	if [ "$(which python)" != "$PY" ]; then
    30	    rmdir "$LOCKDIR" 2>/dev/null || true
    31	    echo "ERROR: active python $(which python) != $PY" >&2
    32	    exit 1
    33	fi
    34	
    35	export PYTHONDONTWRITEBYTECODE=1
    36	export CUDA_VISIBLE_DEVICES=""
    37	export TMPDIR="/data/guoyikun/tmp"
    38	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
    39	export OMP_NUM_THREADS=1
    40	export OPENBLAS_NUM_THREADS=1
    41	export MKL_NUM_THREADS=1
    42	export NUMEXPR_NUM_THREADS=1
    43	export BLIS_NUM_THREADS=1
    44	export VECLIB_MAXIMUM_THREADS=1
    45	
    46	if [ "$MODE" = "gate" ]; then
    47	    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    48	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gate_cpu.txt" \
    49	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/sameframe_cd2.py" \
    50	        gate --out "$OUT" --workers 16 \
    51	        > "$OUT/gate.log" 2>&1
    52	    exit $?
    53	fi
    54	
    55	if [ "$MODE" = "run" ]; then
    56	    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/partA_shard*.jsonl* >/dev/null 2>&1; then
    57	        rmdir "$LOCKDIR" 2>/dev/null || true
    58	        echo "ERROR: $OUT/raw already contains shards; refuse to overwrite" >&2
    59	        exit 1
    60	    fi
    61	    status=STOPPED
    62	    cleanup() {
    63	        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    64	        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    65	        rmdir "$LOCKDIR" 2>/dev/null || true
    66	    }
    67	    trap cleanup EXIT
    68	
    69	    # Part A: Python enforces cumulative CPU <= 6.0 core-hours; wall cap 1800s outer safety net
    70	    set +e
    71	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/partA_cpu.txt" \
    72	        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/sameframe_cd2.py" \
    73	        partA --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    74	        > "$OUT/partA.log" 2>&1
    75	    rc=$?
    76	    set -e
    77	    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    78	        status=STOPPED_BUDGET
    79	        exit 124
    80	    fi
    81	    if [ "$rc" -ne 0 ]; then
    82	        exit "$rc"
    83	    fi
    84	    test -s "$OUT/results.json"
    85	
    86	    # Part B: Pick quietest idle CPU BEFORE starting Python, then pin via taskset
    87	    read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
    88	import os, time
    89	from pathlib import Path
    90	def rd():
    91	    d = {}
    92	    for ln in Path("/proc/stat").read_text().splitlines():
    93	        n, *v = ln.split()
    94	        if n.startswith("cpu") and n[3:].isdigit():
    95	            f = [int(x) for x in v[:8]]
    96	            d[int(n[3:])] = (sum(f), f[3] + f[4])
    97	    return d
    98	a = rd(); time.sleep(1.0); b = rd()
    99	u = {c: 100.0 * ((b[c][0]-a[c][0]) - (b[c][1]-a[c][1])) / max(b[c][0]-a[c][0], 1) for c in os.sched_getaffinity(0)}
   100	best = min(u, key=lambda c: (u[c], c))
   101	print(best, f"{u[best]:.2f}")
   102	')
   103	    export HS_QUIET_CPU_UTIL="$QUIET_UTIL"
   104	
   105	    set +e
   106	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
   107	        timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/sameframe_cd2.py" \
   108	        timing --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
   109	        > "$OUT/timing.log" 2>&1
   110	    trc=$?
   111	    set -e
   112	    if [ "$trc" -eq 124 ] || [ "$trc" -eq 137 ]; then
   113	        status=STOPPED_BUDGET
   114	        exit 124
   115	    fi
   116	    if [ "$trc" -ne 0 ]; then
   117	        exit "$trc"
   118	    fi
   119	    test -s "$OUT/timing_summary.json"
   120	    test -s "$OUT/RESULTS.md"
   121	    status=DONE
   122	    exit 0
   123	fi
   124	
   125	rmdir "$LOCKDIR" 2>/dev/null || true
   126	echo "Unknown MODE: $MODE" >&2
   127	exit 2

exec
/bin/zsh -lc 'ls -a && ls -a experiments && git status --short' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 397ms:
.
..
.DS_Store
.agents
.aris
.claude
.codex
.commandcode
.devin
.gitattributes
.gitignore
.mission
.mypy_cache
.obsidian
.pytest_cache
.ruff_cache
.trellis
.vscode
AFDM_UWA_acoustic.m
AFDM_claim_audit_bundle_20260726.zip
AGENTS.md
CLAUDE.md
DERIVATION_PACKAGE.md
FROZEN_DEPENDENCIES.md
Final Report Template-and-requirements
README.md
STATE-history.md
STATE.md
_archive
_claim_audit_bundle_20260726
_claim_audit_bundle_v2
afdm_sp_joint_unrolled
ana-html
experiments
figures
frozen-i1-smoke-fixture-v1.json
fyp_new_short
ideas
issues
learning
legacy_for_ablation
matlab
novelty
oracle_io
paper
paper-tmlcn
paper_figure_code
papers
pelican-bike.html
refer_paper
requirements.txt
research-assets
results
review-stage
run_frozen_i1_smoke.py
standalone
tcom_plan
tests
tools
.
..
.DS_Store
__pycache__
admission_law_20261118
afdm_acquisition_n128_20261007
afdm_acquisition_optimized_20261007
afdm_acquisition_performance_20261007
afdm_acquisition_screen128_20261007
afdm_acquisition_shortburst_20261007
afdm_code_design_20261007
afdm_coherent_structure_20261006
afdm_collision_resolution
afdm_deep_principles_20261006
afdm_efficient_information
afdm_higher_order_information
afdm_inference_causal_20261002
afdm_method_advantage
afdm_phase_budget_20261007
afdm_phase_information_20261006
afdm_shared_channel_20261004
afdm_sp_fractional_20261007
afdm_sp_fractional_receiver_20261007
afdm_structured_inference_20261003
afdm_usable_inference_20261006
cstate_codelay_sbl_stage3_20261118
cstate_first_step_attribution
cstate_method_closure_20260928
cstate_necessity_stageA_20260928
cstate_necessity_stageB_20260928
cstate_necessity_stageB_resume_20260928
cstate_score_update_20261111
cstate_sparse_doublet_screen_20261118
data_autocorr_acq_20261121
data_pilot_fer_20261121
detector_gain_lead_20261019
doublet_conflict_20261119
dpss_block_rescue_20261110
dpss_cluster_narrow_20261110
dpss_j4_width_20261110
dpss_p1_narrow_20261110
dpss_p1_pilot_20261110
dpss_paired_screen_20261111
dpss_shrink_pilot_20261110
edit_budget_lowrho_20261119
f0_round_budget_20261118
gamma0_exchange_20261120
gamma0_mixed8_20261120
gamma0_mixed8_rep_20261120
gate_sbl_test_20261119
gate_screen_20261119
generator_snr_audit_20261019
grid_eta_dual_20261119
headroom_ladder_20261008
huang_steelman_20261124
lowpilot_missed_readout_20261120
lowpilot_support_right_20261120
matched_ldpc_20261122
oamp_ldpc_20261109
pilot_acquisition_calc_20261120
posthoc_rank_inversion_20261019
ratio_sweep_20261118
readout_batch_20261119
rho_sweep_20261119
sameframe_cd2_20261125
sameframe_hg_20261124
sbl_freeze_replay_20261020
sbl_joint_detector_20261019
sbl_residual_gap_20261119
sbl_spectral_split_20261119
sbl_split_diagnostic_20261118
sbl_three_mode_20261020
sigma2_dd_20261118
sigma2_stein_20261121
slot_mismatch_20261019
sp_afdm_frozen_20260920
sp_afdm_frozen_reviewed_20260921
sp_afdm_native_joint_20260921
sp_afdm_native_joint_reviewed_20260921
stein_sigma2_readout_20261120
tail_check_20261121
tcom_channel_crb_20261016
tcom_genie_support_20261016
tcom_reference_frame_20261015
tf_cgr_mechanism_20260923
tf_cgr_mechanism_20260923_v2
tf_cgr_offline_mechanism_20260923
tf_cgr_prospective_mechanism_20260923
tf_covariance_audit_20261018
tf_cstate_e1_20261017
tf_cstate_e2_20261017
tf_cstate_prospective_20260923
tf_cstate_validation_20260922
tf_e3_sbl_20261017
tf_e3b_offgrid_20261017
tf_e3c_shrink_20261018
tf_geometry_reopen_20260922
tf_gso_20261018
tf_mm_gamma_20261018
tf_production_gap_audit_20260922
tf_research_discovery_historical_20260923.py
tf_research_discovery_pack_20260923
tf_split_prosp_20261018
unified_cov_prospective_20261119
zero_sim_readouts_20261119
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-KiIV4KoU' (errno=Operation not permitted)
 M ../../.gitignore
 M .claude/settings.json
 M .gitignore
 M .trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md
 M .trellis/tasks/09-22-tf-production-gap-audit/research/oamp-ldpc-screen-20261109.md
 M .trellis/tasks/09-22-tf-production-gap-audit/task.json
 M .trellis/tasks/11-21-data-pilot-fer/task.json
 M .trellis/workspace/guoyikun/journal-1.md
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\270\255\345\233\275\345\274\217\347\216\260\344\273\243\345\214\226/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/\345\206\231\344\275\234\346\217\220\347\272\262.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\275\277\347\224\250\350\257\264\346\230\216.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\277\241\345\217\267\346\243\200\346\265\213\344\270\216\344\274\260\350\256\241/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/PIPELINE.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/runner-goal.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\200\344\274\230\345\214\226\347\220\206\350\256\272\344\270\216\345\272\224\347\224\250/\351\224\231\351\242\230\346\234\254.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\237\346\234\253\346\211\247\350\241\214\347\211\210.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\237\346\234\253\350\256\241\345\210\222.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\254\345\221\250.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/BRIEF.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/PIPELINE.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/REUSE.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/ideas/Codex-dialogue.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/README.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/\351\224\231\351\242\230\346\234\254.md"
 M "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/README.md"
 ? ../../01_Projects/afdm_end_to_end/Deepcom
 m ../../01_Projects/afdm_end_to_end/marble-end-to-end
 m ../../03_Resources/ofdm-plutosdr-pytorch
?? ../../.agents/
?? ../../.claude/commands/context-pack.md
?? ../../.claude/commands/finance-news.md
?? ../../.claude/commands/git-worktrees.md
?? ../../.claude/commands/json-canvas.md
?? ../../.claude/commands/obsidian-bases.md
?? ../../.claude/commands/obsidian-markdown.md
?? ../../.claude/commands/restructure-doc.md
?? ../../.claude/commands/skill-creator.md
?? ../../.claude/commands/stock-fund-data.md
?? ../../.claude/commands/systematic-debugging.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/contribution-framing-process-20261109.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-claude-20261108.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-codex-20261109.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-divergence-20261109.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-process-20261110.md
?? .trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md
?? .trellis/tasks/11-18-admission-law-test/research/sol-freeze-run-last-message.md
?? .trellis/tasks/11-18-admission-law-test/research/sol-phase1-last-message.md
?? .trellis/tasks/11-18-sigma2-dd/research/sol-freeze-run-last-message.md
?? .trellis/tasks/11-18-sigma2-dd/research/sol-phase1-last-message.md
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_exit_code
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_run.log
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v1/
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v2/
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v2_exit_code
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v2_run.log
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v3/
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v3_exit_code
?? afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/structured_stop_v3_run.log
?? experiments/cstate_first_step_attribution/PROTOCOL.md
?? experiments/cstate_sparse_doublet_screen_20261118/out/
?? experiments/data_autocorr_acq_20261121/astra-review.err
?? experiments/dpss_block_rescue_20261110/PROTOCOL.md
?? experiments/dpss_block_rescue_20261110/RESULTS.md
?? experiments/dpss_block_rescue_20261110/block.py
?? experiments/dpss_block_rescue_20261110/gate.py
?? experiments/dpss_block_rescue_20261110/launch.py
?? experiments/dpss_block_rescue_20261110/out/
?? experiments/dpss_cluster_narrow_20261110/
?? experiments/dpss_j4_width_20261110/
?? experiments/dpss_p1_narrow_20261110/
?? experiments/dpss_p1_pilot_20261110/
?? experiments/dpss_shrink_pilot_20261110/
?? experiments/oamp_ldpc_20261109/STRUCTURED_STOP_RESULTS.md
?? experiments/sameframe_cd2_20261125/
?? experiments/tf_covariance_audit_20261018/forensic_config.py
?? experiments/tf_covariance_audit_20261018/forensic_config_local.json
?? experiments/tf_covariance_audit_20261018/forensic_synthetic.py
?? experiments/tf_covariance_audit_20261018/forensic_synthetic_local.json
?? experiments/tf_covariance_audit_20261018/schema_samples.json
?? ../LDS_OTFS_conference/
?? ../LEO/
?? ../cps_lab_26/
?? "../\347\247\221\347\240\224\345\267\245\344\275\234\346\261\207\346\212\245_20260908/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/.trellis/tasks/11-12-matrix-round2-problem-selection/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/tools/report-runs/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\270\255\345\233\275\345\274\217\347\216\260\344\273\243\345\214\226/\347\233\270\345\205\263\345\217\202\350\200\203/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/RUN_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/RUN_STATUS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/audit/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/runner-goal.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/\346\212\245\345\221\212/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\272\222\350\201\224\347\275\221\345\256\211\345\205\250\351\200\211\344\277\256\350\257\276/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\277\241\345\217\267\346\243\200\346\265\213\344\270\216\344\274\260\350\256\241/\350\256\250\350\256\272\351\242\230/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\344\277\241\345\217\267\346\243\200\346\265\213\344\270\216\344\274\260\350\256\241/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/AUDIT_SUMMARY.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/CLAIMS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/MISSION_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/PREDICTIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/figures/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/ideas/Claude-dialogue.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/ideas/Codex-dialogue.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/CITATION_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/CLAIM_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/DERIVATION_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/OUTLINE.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/RUBRIC_REVIEW.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.bbl"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.blg"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.fdb_latexmk"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.fls"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/main.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/refs.bib"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/paper/sections/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/refine-logs/FINAL_PROPOSAL.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/results/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/src/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/theory/THEORY.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\345\207\270\344\274\230\345\214\226/project/theory/THEORY_AUDIT.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-18-muse-8c637bf3-ae87-46e2-92f3-86f35ab48726.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-19-chatgpt-b8d4e19a-6c3f-4b82-9a15-7e2d4c8f1b30.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-20-chatgpt-d4f8a21c-7e3b-49a5-8c12-6b9e0f3a5d72.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\227\245\345\277\227/2026-11-22-chatgpt-a3c7e914-5b2d-4f8a-9c16-3e8d0b4a7f52.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\200\344\274\230\345\214\226\347\220\206\350\256\272\344\270\216\345\272\224\347\224\250/\350\256\262\350\247\243/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\346\234\200\344\274\230\345\214\226\347\220\206\350\256\272\344\270\216\345\272\224\347\224\250/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/RUN_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/RUN_STATUS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/audit/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/checks/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/deliverables/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/ideas/Claude-dialogue.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/notes/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277_\344\277\256\346\224\271\350\256\260\345\275\225.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/2404.10232.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/2404.10232_src.tar.gz"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/2404.10232_src/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/papers/arxiv_meta.xml"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/runner-goal.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v1.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v2.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.aux"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.log"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.out"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/2404.10232_zh_v3.tex"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/translation/figures/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277_v2.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\345\256\232\347\250\277_v3.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\350\215\211\347\250\277.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/project/\345\260\217\345\210\233\346\226\260\351\252\250\346\236\266.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\347\237\251\351\230\265\347\220\206\350\256\272/\350\265\204\346\226\231/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/RUN_DECISIONS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/RUN_STATUS.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/audit/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/deliverables/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/runner-goal.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/sources/"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2541\347\253\240\357\274\2102\346\254\241\350\257\276\357\274\21124.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2542\347\253\240\357\274\2102.5\346\254\241\350\257\276\357\274\211.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2543\347\253\240\357\274\2103.5\346\254\241\350\257\276\357\274\211new.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\254\2544\347\253\240\357\274\2102\346\254\241\350\257\276\357\274\211.pdf"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\345\210\235\347\211\210.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\217\220\347\272\262.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\255\243\346\226\207.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\255\243\346\226\207_v2.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\346\255\243\346\226\207_v3.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\256\272\346\226\207\345\206\231\344\275\234/\347\273\274\350\277\260\350\260\203\347\240\224\347\250\277.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\257\276\347\250\213\350\265\204\346\226\231\347\264\242\345\274\225.md"
?? "../../01_Projects/2026\347\247\213\346\234\237\346\234\253/\350\265\204\346\226\231\346\235\245\346\272\220/"
?? ../../01_Projects/pindou/
?? ../../01_Projects/stock/

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba sameframe_cd2.py | sed -n '390,860p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
 succeeded in 0ms:
   390	def _partA_shard_worker(
   391	    shard_idx: int,
   392	    frames: tuple[int, ...],
   393	    trig_by_frame: dict[int, list[tuple[str, int, int, int, int, int]]],
   394	    include_cd2e8: bool,
   395	    raw_dir: Path,
   396	):
   397	    C, _, _, helpers = sf.load_stage_runtime()
   398	    stage3, ctx = C['stage3'], C['ctx']
   399	    final_path = raw_dir / f'partA_shard{shard_idx:03d}.jsonl.gz'
   400	    out_lines: list[str] = []
   401	    for frame in frames:
   402	        items = trig_by_frame.get(frame, [])
   403	        grouped: dict[tuple[str, int], list[tuple[int, int, int, int]]] = {}
   404	        for s, rho, snr, exp_syn, exp_f0_err, exp_base_err in items:
   405	            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err, exp_base_err))
   406	        for (s, rho), grp in sorted(grouped.items()):
   407	            base = stage3.inputs(ctx, frame, s, rho)
   408	            for snr, exp_syn, exp_f0_err, exp_base_err in sorted(grp):
   409	                _, obs, truth = stage3.observed(ctx, base, rho, snr)
   410	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   411	                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   412	                if int(syn) != exp_syn or f0_err != exp_f0_err:
   413	                    raise RuntimeError(
   414	                        f'PartA F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
   415	                    )
   416	                cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
   417	                if int(cd2['pass1_errors']) != exp_base_err:
   418	                    raise RuntimeError(
   419	                        f'PartA CD2 pass-1 drift vs stageA base at {(s, rho, snr, frame)}: '
   420	                        f'{cd2["pass1_errors"]} != {exp_base_err}'
   421	                    )
   422	                arms_rec = dict(CD2=cd2)
   423	                if include_cd2e8:
   424	                    arms_rec['CD2e8'] = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   425	                out_lines.append(json.dumps(dict(
   426	                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
   427	                ), allow_nan=False) + '\n')
   428	    sf._write_gzip_jsonl_atomic(final_path, out_lines)
   429	    print(f'PartA shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   430	
   431	
   432	def p1p_verdict(ci_lo: float, ci_hi: float) -> str:
   433	    if ci_lo >= P1P_THRESHOLD_DB:
   434	        return 'DOPPLER-LINE'
   435	    if ci_hi < P1P_THRESHOLD_DB:
   436	        return 'STOP-LINE'
   437	    return 'INCONCLUSIVE'
   438	
   439	
   440	def analyze_partA(
   441	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   442	    include_cd2e8: bool,
   443	    crossing_fn,
   444	    diag_stats: dict[str, Any],
   445	    *,
   446	    boot_draws: int = BOOT_DRAWS,
   447	    boot_seed: int = BOOT_SEED,
   448	) -> dict[str, Any]:
   449	    """Joint paired physical-frame bootstrap analysis for P1' (frames 41000-41399, seed 20261125)."""
   450	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   451	    rng = np.random.default_rng(boot_seed)
   452	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   453	    weights[0] = 1.0 / n_frames
   454	    for b in range(1, boot_draws + 1):
   455	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   456	
   457	    arm_lo: dict[str, np.ndarray] = {}
   458	    arm_hi: dict[str, np.ndarray] = {}
   459	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   460	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   461	    arm_best_lo: dict[str, np.ndarray] = {}
   462	    arm_best_hi: dict[str, np.ndarray] = {}
   463	    arm_best_rho: dict[str, int] = {}
   464	
   465	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   466	        n_r = len(rhos)
   467	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   468	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   469	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   470	        scen_pt = {'U': {}, 'G': {}}
   471	        for ri, rho in enumerate(rhos):
   472	            for bi in range(boot_draws + 1):
   473	                u_lo, u_hi = sf.crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   474	                g_lo, g_hi = sf.crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   475	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   476	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   477	                if bi == 0:
   478	                    scen_pt['U'][str(rho)] = sf._rep(u_lo) if u_lo == u_hi else [sf._rep(u_lo), sf._rep(u_hi)]
   479	                    scen_pt['G'][str(rho)] = sf._rep(g_lo) if g_lo == g_hi else [sf._rep(g_lo), sf._rep(g_hi)]
   480	        arm_lo[arm] = lo_arr
   481	        arm_hi[arm] = hi_arr
   482	        arm_scen_pt[arm] = scen_pt
   483	        arm_mean_pt[arm] = {
   484	            str(rho): (sf._rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [sf._rep(lo_arr[0, ri]), sf._rep(hi_arr[0, ri])])
   485	            for ri, rho in enumerate(rhos)
   486	        }
   487	        if arm in ('delay', 'full', 'ldop'):
   488	            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
   489	        else:
   490	            sub_idx = list(range(n_r))
   491	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   492	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   493	        arm_best_rho[arm] = int(rhos[sub_idx[int(np.argmin(hi_arr[0, sub_idx]))]])
   494	
   495	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   496	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   497	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   498	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   499	        if cens_frac == 0.0:
   500	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   501	        else:
   502	            lo = an._nearest_rank(d_lo[1:], 0.025)
   503	            hi = an._nearest_rank(d_hi[1:], 0.975)
   504	        pt = sf._rep(d_lo[0]) if d_lo[0] == d_hi[0] else [sf._rep(d_lo[0]), sf._rep(d_hi[0])]
   505	        return dict(
   506	            point_db=pt,
   507	            ci95_db=[sf._rep(lo), sf._rep(hi)],
   508	            censored_draw_fraction=cens_frac,
   509	            arm_a_best_db=sf._rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [sf._rep(arm_best_lo[arm_a][0]), sf._rep(arm_best_hi[arm_a][0])],
   510	            arm_a_best_rho=arm_best_rho[arm_a],
   511	            arm_b_best_db=sf._rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [sf._rep(arm_best_lo[arm_b][0]), sf._rep(arm_best_hi[arm_b][0])],
   512	            arm_b_best_rho=arm_best_rho[arm_b],
   513	        )
   514	
   515	    p1p = contrast('CD2', 's100')
   516	    lo_val = float(p1p['ci95_db'][0]) if isinstance(p1p['ci95_db'][0], float) else (-math.inf if p1p['ci95_db'][0] == '-inf' else math.inf)
   517	    hi_val = float(p1p['ci95_db'][1]) if isinstance(p1p['ci95_db'][1], float) else (-math.inf if p1p['ci95_db'][1] == '-inf' else math.inf)
   518	    p1p['verdict'] = p1p_verdict(lo_val, hi_val)
   519	
   520	    sec = {}
   521	    for comp in ('s050', 'ldop', 'full', 'delay', 'base', 'HG', 'HGint'):
   522	        if comp in fail_by_arm:
   523	            sec[f'CD2_minus_{comp}'] = contrast('CD2', comp)
   524	    if include_cd2e8 and 'CD2e8' in fail_by_arm:
   525	        for comp in ('s100', 's050', 'ldop', 'full', 'HG', 'HGint', 'CD2'):
   526	            if comp in fail_by_arm:
   527	                sec[f'CD2e8_minus_{comp}'] = contrast('CD2e8', comp)
   528	    sec['HG_minus_s100'] = contrast('HG', 's100')
   529	
   530	    return dict(
   531	        boot_draws=boot_draws,
   532	        boot_seed=boot_seed,
   533	        partA_rhos=list(PARTA_RHOS),
   534	        include_cd2e8=include_cd2e8,
   535	        primary_P1_prime=p1p,
   536	        secondary_contrasts=sec,
   537	        mean_crossing=arm_mean_pt,
   538	        crossings_by_scenario=arm_scen_pt,
   539	        best_rho=arm_best_rho,
   540	        diagnostics=diag_stats,
   541	    )
   542	
   543	
   544	def render_results_md(res: dict[str, Any]) -> str:
   545	    pA = res['partA']
   546	    p1p = pA['primary_P1_prime']
   547	
   548	    def fval(x):
   549	        if isinstance(x, list):
   550	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
   551	        return x if isinstance(x, str) else f'{x:.4f}'
   552	
   553	    lines = [
   554	        '# Same-Frame CD2 Headroom & Quiet Timing Results (`sameframe_cd2_20261125`)',
   555	        '',
   556	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
   557	        f'- Part A CPU: **{res["runtime"]["partA_total_core_hours"]:.4f} core-hours** (cap {res["runtime"]["cpu_cap_core_hours"]:.1f} h; wall {res["runtime"]["partA_wall_seconds"]:.1f} s)',
   558	        '',
   559	        '## Primary Verdict P1\' (Pre-Registered, Frames 41000–41399)',
   560	        '',
   561	        '| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |',
   562	        '|---|---:|---|---|',
   563	        f'| `min CD2 (100..250) − min s100 (100..200)` | **{fval(p1p["point_db"])}** | **[{fval(p1p["ci95_db"][0])}, {fval(p1p["ci95_db"][1])}]** | **{p1p["verdict"]}** |',
   564	        '',
   565	        '## Part A: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
   566	        '',
   567	    ]
   568	    arms_order = [a for a in ('base', 'delay', 'HG', 'HGint', 'CD2', 'CD2e8', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in pA['mean_crossing']]
   569	    rhos_all = ('50', '100', '150', '200', '250', '300')
   570	    lines.append('| Arm | ' + ' | '.join(f'ρ={int(r)/1000:.2f}' for r in rhos_all) + ' | Best ρ |')
   571	    lines.append('|---|' + '---:|' * len(rhos_all) + '---:|')
   572	    for a in arms_order:
   573	        cells = [fval(pA['mean_crossing'][a][r]) if r in pA['mean_crossing'][a] else '—' for r in rhos_all]
   574	        lines.append(f'| {a} | ' + ' | '.join(cells) + f' | {pA["best_rho"][a]/1000:.2f} |')
   575	
   576	    lines += ['', '### Part A Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
   577	    for name, c in pA['secondary_contrasts'].items():
   578	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')
   579	
   580	    lines += ['', '### Part A Pass-2 Diagnostics', '']
   581	    for arm, d in pA['diagnostics'].items():
   582	        lines.append(
   583	            f'- `{arm}`: pass-1 stop {d["pass1_early_stop"]}/{d["triggered"]}, '
   584	            f'pass-2 ran {d["pass2_ran"]} (rescued {d["pass2_rescued"]}), '
   585	            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}'
   586	        )
   587	
   588	    timing = res.get('timing')
   589	    if timing:
   590	        lines += ['', '## Part B: Quiet Single-Core Timing Panels (Huang Frames 5400–5799)', '']
   591	        lines.append(
   592	            f'- Pinned CPU: `{timing["cpu"]["idle_cpu"]}` (pre-start util `{timing["cpu"]["measured_utilization_pct"]:.1f}%`, '
   593	            f'wall `{timing["wall_seconds"]:.1f} s`, timing CPU `{timing["timing_cpu_hours"]:.4f} core-hours`)'
   594	        )
   595	        for pname, pdata in timing['panels'].items():
   596	            lines += [
   597	                '',
   598	                f'### Panel `{pname}` (ρ={pdata["rho_permille"]/1000:.2f}, SNR={pdata["snr_centi_db"]/100:.1f} dB; '
   599	                f'100 triggered + 50 untriggered F0; shared F0 median {1000*pdata["f0"]["median"]:.2f} ms)',
   600	                '',
   601	                '| Arm | Mean (ms) | Median (ms) | p95 (ms) | Pass-2 Rate | Ratio of Means vs CD | Median Paired Ratio vs CD | Amortized Full-Frame (ms) |',
   602	                '|---|---:|---:|---:|---:|---:|---:|---:|',
   603	            ]
   604	            for arm in ('CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint'):
   605	                b = pdata['branches'][arm]
   606	                p2r = pdata['pass2_rate'].get(arm, 0.0)
   607	                rm = 1.0 if arm == 'CD' else pdata['relative_to_cd'][arm]['ratio_of_means']
   608	                mp = 1.0 if arm == 'CD' else pdata['relative_to_cd'][arm]['median_paired_ratio']
   609	                am = pdata['amortized_full_frame_mean_seconds'][arm]
   610	                lines.append(
   611	                    f'| {arm} | {1000*b["mean"]:.2f} | {1000*b["median"]:.2f} | {1000*b["p95"]:.2f} | '
   612	                    f'{100*p2r:.1f}% | {rm:.3f}× | {mp:.3f}× | {1000*am:.2f} |'
   613	                )
   614	    return '\n'.join(lines) + '\n'
   615	
   616	
   617	def _do_read_partA(
   618	    out_dir: Path,
   619	    gate: dict[str, Any],
   620	    gate_md5: str,
   621	    freeze_commit: str,
   622	    runtime_info: dict[str, Any],
   623	    raw_md5: dict[str, str],
   624	    *,
   625	    enforce_cpu_cap: bool = False,
   626	    wall_start: float | None = None,
   627	):
   628	    import stageA  # noqa: E402
   629	    import stageA2  # noqa: E402
   630	    import stageA3  # noqa: E402
   631	
   632	    include_cd2e8 = bool(gate['selected']['include_cd2e8'])
   633	    raw_dir = out_dir / 'raw'
   634	    verify_all_archives()
   635	    for fname, expected in raw_md5.items():
   636	        if ar.md5_file(raw_dir / fname) != expected:
   637	            raise RuntimeError(f'PartA raw shard MD5 mismatch {fname}')
   638	
   639	    # Load stageA, stageA2, stageA3 archived failure grids
   640	    fa, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)
   641	    fa2, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
   642	    fa3, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)
   643	
   644	    stageA_base = sf.load_stageA_base(PARTA_RHOS)
   645	    fi = {f: i for i, f in enumerate(PARTA_FRAMES)}
   646	
   647	    # Load archived sameframe_hg Part 1 (HG, HG1, HGint)
   648	    hg_arms = ('HG', 'HG1', 'HGint')
   649	    hg_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in hg_arms}
   650	    hg_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
   651	    for (s, rho, snr, f), b in stageA_base.items():
   652	        if b['syndrome'] == 0:
   653	            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
   654	            ef = b['f0_errors'] > 0
   655	            for a in hg_arms:
   656	                hg_fail[a][ix] = ef
   657	            hg_seen[ix] = True
   658	    for idx in range(N_SHARDS):
   659	        sp = SAMEFRAME_HG_DIR / 'out' / 'raw' / f'part1_shard{idx:03d}.jsonl.gz'
   660	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   661	            for line in fh:
   662	                r = json.loads(line)
   663	                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
   664	                if hg_seen[ix]:
   665	                    raise RuntimeError(f'Duplicate sameframe_hg key {r}')
   666	                for a in hg_arms:
   667	                    hg_fail[a][ix] = int(r['arms'][a]['errors']) > 0
   668	                hg_seen[ix] = True
   669	    if not hg_seen.all():
   670	        raise RuntimeError('Incomplete sameframe_hg Part 1 grid')
   671	
   672	    # Load new Part A (CD2, optional CD2e8)
   673	    new_arms = ('CD2',) + (('CD2e8',) if include_cd2e8 else ())
   674	    pA_fail = {a: np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool) for a in new_arms}
   675	    pA_seen = np.zeros((len(PARTA_FRAMES), 2, len(PARTA_RHOS), len(PARTA_SNRS)), dtype=bool)
   676	    for (s, rho, snr, f), b in stageA_base.items():
   677	        if b['syndrome'] == 0:
   678	            ix = (fi[f], ar.SCENARIOS.index(s), PARTA_RHOS.index(rho), PARTA_SNRS.index(snr))
   679	            ef = b['f0_errors'] > 0
   680	            for a in new_arms:
   681	                pA_fail[a][ix] = ef
   682	            pA_seen[ix] = True
   683	
   684	    diag_acc = {a: dict(triggered=0, pass1_early_stop=0, pass2_ran=0, pass2_rescued=0, p1_edits=[], p2_edits=[]) for a in new_arms}
   685	    trig_count = 0
   686	    for idx in range(N_SHARDS):
   687	        sp = raw_dir / f'partA_shard{idx:03d}.jsonl.gz'
   688	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   689	            for line in fh:
   690	                r = json.loads(line)
   691	                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), PARTA_RHOS.index(int(r['rho'])), PARTA_SNRS.index(int(r['snr'])))
   692	                if pA_seen[ix]:
   693	                    raise RuntimeError(f'Duplicate PartA key {r}')
   694	                for a in new_arms:
   695	                    rec = r['arms'][a]
   696	                    pA_fail[a][ix] = int(rec['errors']) > 0
   697	                    d = diag_acc[a]
   698	                    d['triggered'] += 1
   699	                    d['p1_edits'].append(int(rec['pass1_edits']))
   700	                    if int(rec['passes_used']) == 1:
   701	                        d['pass1_early_stop'] += 1
   702	                    else:
   703	                        d['pass2_ran'] += 1
   704	                        d['p2_edits'].append(int(rec['pass2_edits']))
   705	                        if int(rec['pass1_errors']) > 0 and int(rec['errors']) == 0:
   706	                            d['pass2_rescued'] += 1
   707	                pA_seen[ix] = True
   708	                trig_count += 1
   709	    if not pA_seen.all():
   710	        raise RuntimeError(f'Incomplete PartA grid: missing {int((~pA_seen).sum())}')
   711	
   712	    diag_stats = {
   713	        a: dict(
   714	            triggered=d['triggered'],
   715	            pass1_early_stop=d['pass1_early_stop'],
   716	            pass2_ran=d['pass2_ran'],
   717	            pass2_rescued=d['pass2_rescued'],
   718	            mean_pass1_edits=float(np.mean(d['p1_edits'])) if d['p1_edits'] else 0.0,
   719	            mean_pass2_edits_when_ran=float(np.mean(d['p2_edits'])) if d['p2_edits'] else 0.0,
   720	        )
   721	        for a, d in diag_acc.items()
   722	    }
   723	
   724	    fail_by_arm = {
   725	        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
   726	        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
   727	        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
   728	        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
   729	    }
   730	    for i, a in enumerate(stageA3.ARMS):
   731	        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
   732	    for a in hg_arms:
   733	        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, hg_fail[a])
   734	    for a in new_arms:
   735	        fail_by_arm[a] = (PARTA_RHOS, PARTA_SNRS, pA_fail[a])
   736	
   737	    print(f'Analyzing Part A ({int(pA_seen.sum())} keys, {trig_count} triggered, seed={BOOT_SEED})...', flush=True)
   738	    partA_out = analyze_partA(fail_by_arm, include_cd2e8, stageA2.crossing, diag_stats)
   739	
   740	    if enforce_cpu_cap:
   741	        final_cpu = sf._used_cpu_seconds()
   742	        if final_cpu >= BUDGET_CAP_SEC:
   743	            print(f'STOPPED_BUDGET after Part A analysis ({final_cpu/3600:.3f} core-hours)', flush=True)
   744	            sys.exit(BUDGET_EXIT_CODE)
   745	        runtime_info = dict(
   746	            runtime_info,
   747	            partA_analysis_cpu_hours=max(0.0, final_cpu / 3600.0 - runtime_info['partA_workers_core_hours']),
   748	            partA_total_core_hours=final_cpu / 3600.0,
   749	            partA_wall_seconds=(time.monotonic() - wall_start) if wall_start is not None else runtime_info['partA_wall_seconds'],
   750	        )
   751	
   752	    results = dict(
   753	        _argv=sys.argv,
   754	        _config=dict(
   755	            freeze_commit=freeze_commit,
   756	            python_executable=sys.executable,
   757	            own_md5=own_md5(),
   758	            gate_md5=gate_md5,
   759	            partA_rhos=list(PARTA_RHOS),
   760	            include_cd2e8=include_cd2e8,
   761	            partA_frames=[PARTA_FRAMES[0], PARTA_FRAMES[-1]],
   762	            partA_triggered_keys=trig_count,
   763	            raw_output_dir=str(raw_dir),
   764	            raw_rows_md5=raw_md5,
   765	            sameframe_hg_manifest_sha256=SAMEFRAME_HG_MANIFEST_SHA256,
   766	        ),
   767	        gates=dict(
   768	            all_passed=gate['all_passed'],
   769	            selected=gate['selected'],
   770	            G1_keys=gate['G1']['keys_checked'],
   771	            G2_keys=gate['G2']['keys_checked'],
   772	            G3_projected_hours=gate['selected']['projected_hours_with_margin'],
   773	        ),
   774	        runtime=runtime_info,
   775	        partA=partA_out,
   776	        timing=None,
   777	    )
   778	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
   779	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
   780	    print(
   781	        f'PARTA_DONE P1_prime={partA_out["primary_P1_prime"]["verdict"]} '
   782	        f'point={partA_out["primary_P1_prime"]["point_db"]:.4f} '
   783	        f'ci={partA_out["primary_P1_prime"]["ci95_db"]} '
   784	        f'cpu_hours={runtime_info["partA_total_core_hours"]:.4f}',
   785	        flush=True,
   786	    )
   787	
   788	
   789	def cmd_run_partA(args):
   790	    print(sys.executable, flush=True)
   791	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   792	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   793	    ar.check_thread_env()
   794	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   795	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   796	    if not 1 <= args.workers <= 32:
   797	        raise ValueError('workers must be in 1..32')
   798	
   799	    out_dir = args.out.resolve()
   800	    raw_dir = out_dir / 'raw'
   801	    raw_dir.mkdir(parents=True, exist_ok=True)
   802	    if list(raw_dir.glob('partA_shard*.jsonl*')):
   803	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   804	
   805	    gate_bytes = (out_dir / 'gate.json').read_bytes()
   806	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   807	    gate = json.loads(gate_bytes.decode('utf-8'))
   808	    if not gate.get('all_passed') or not gate.get('selected'):
   809	        raise RuntimeError('Refusing to run without passing gate.json')
   810	    live_own = own_md5()
   811	    verify_freeze_commit_if_git(args.freeze_commit, live_own)
   812	    if gate['_config']['own_md5'] != live_own:
   813	        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
   814	
   815	    include_cd2e8 = bool(gate['selected']['include_cd2e8'])
   816	    wall_start = time.monotonic()
   817	    verify_all_archives()
   818	    C, _, _, helpers = sf.load_stage_runtime()
   819	    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
   820	        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
   821	    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
   822	        raise RuntimeError('p1_source_md5 mismatch vs gate.json')
   823	
   824	    stageA_base = sf.load_stageA_base(PARTA_RHOS)
   825	    trig_by_frame: dict[int, list[tuple[str, int, int, int, int, int]]] = {}
   826	    n_trig = 0
   827	    for (s, rho, snr, f), b in stageA_base.items():
   828	        if b['syndrome'] != 0:
   829	            trig_by_frame.setdefault(f, []).append((s, rho, snr, b['syndrome'], b['f0_errors'], b['errors']))
   830	            n_trig += 1
   831	    jobs = [
   832	        (idx, tuple(PARTA_FRAMES[idx::N_SHARDS]), {f: trig_by_frame.get(f, []) for f in PARTA_FRAMES[idx::N_SHARDS]}, include_cd2e8, raw_dir)
   833	        for idx in range(N_SHARDS)
   834	    ]
   835	    print(f'Launching Part A: {n_trig} triggered keys on {args.workers} workers (include_cd2e8={include_cd2e8})...', flush=True)
   836	    sf._run_sharded_phase(_partA_shard_worker, jobs, args.workers, BUDGET_CAP_SEC)
   837	    workers_cpu = sf._used_cpu_seconds()
   838	
   839	    raw_md5 = {}
   840	    for idx in range(N_SHARDS):
   841	        p = raw_dir / f'partA_shard{idx:03d}.jsonl.gz'
   842	        raw_md5[p.name] = ar.md5_file(p)
   843	    ar.atomic_write_text(
   844	        out_dir / 'REMOTE_ROWS_MD5.txt',
   845	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
   846	    )
   847	
   848	    runtime_info = dict(
   849	        partA_workers_core_hours=workers_cpu / 3600.0,
   850	        partA_total_core_hours=workers_cpu / 3600.0,
   851	        partA_wall_seconds=time.monotonic() - wall_start,
   852	        cpu_cap_core_hours=BUDGET_CAP_HOURS,
   853	    )
   854	    _do_read_partA(
   855	        out_dir, gate, gate_md5, args.freeze_commit, runtime_info, raw_md5,
   856	        enforce_cpu_cap=True, wall_start=wall_start,
   857	    )
   858	
   859	
   860	# --------------------------------------------------------------------------- Part B: quiet single-core timing

exec
/bin/zsh -lc "nl -ba sameframe_cd2.py | sed -n '1,388p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
 succeeded in 0ms:
     1	"""Part A (CD2/CD2e8 on low-pilot frames 41000-41399) + Part B (quiet single-core dual-panel timing)."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	import gzip
     6	import hashlib
     7	import json
     8	import math
     9	import os
    10	from pathlib import Path
    11	import platform
    12	import re
    13	import shutil
    14	import sys
    15	import time
    16	from time import perf_counter
    17	from typing import Any
    18	
    19	import numpy as np
    20	
    21	HERE = Path(__file__).resolve().parent
    22	EXP = HERE.parent
    23	SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'
    24	DATA_PILOT_DIR = EXP / 'data_pilot_fer_20261121'
    25	HUANG_DIR = EXP / 'huang_steelman_20261124'
    26	
    27	sys.path.insert(0, str(SAMEFRAME_HG_DIR))
    28	sys.path.insert(0, str(DATA_PILOT_DIR))
    29	sys.path.insert(0, str(HUANG_DIR))
    30	
    31	import hs_analysis as an  # noqa: E402
    32	import hs_arms as ar  # noqa: E402
    33	import sameframe as sf  # noqa: E402
    34	
    35	PARTA_RHOS = sf.PART1_RHOS
    36	PARTA_SNRS = sf.PART1_SNRS
    37	PARTA_FRAMES = sf.PART1_FRAMES
    38	BOOT_DRAWS = 2000
    39	BOOT_SEED = 20261125
    40	P1P_THRESHOLD_DB = 0.5
    41	WORKERS = 24
    42	N_SHARDS = 24
    43	BUDGET_CAP_HOURS = 6.0
    44	BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
    45	COST_MARGIN = 1.3
    46	TIMING_ALLOWANCE_HOURS = 0.18
    47	IO_ALLOWANCE_HOURS = 0.12
    48	BUDGET_EXIT_CODE = 124
    49	TIMING_BUDGET_SEC = 1740.0
    50	
    51	SAMEFRAME_HG_MANIFEST_SHA256 = '7cac38cd7cc8fa610ddf8c0b5908b62c668901cf5b72756889c1fd6a0f6b435f'
    52	OWN_FILES = ('PROTOCOL.md', 'sameframe_cd2.py', 'test_sameframe_cd2.py', 'launch.sh')
    53	TIMING_PANELS = (
    54	    ('rho200_snr450', 200, 450),
    55	    ('rho300_snr500', 300, 500),
    56	)
    57	TIMING_BRANCHES = ('CD', 'CD2', 'CD2e8', 'HG', 'HGint')
    58	
    59	
    60	def own_md5() -> dict[str, str]:
    61	    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}
    62	
    63	
    64	def verify_sameframe_hg_manifest() -> dict[str, str]:
    65	    manifest = SAMEFRAME_HG_DIR / 'out' / 'REMOTE_ROWS_MD5.txt'
    66	    got_sha = ar.sha256_file(manifest)
    67	    if got_sha != SAMEFRAME_HG_MANIFEST_SHA256:
    68	        raise RuntimeError(f'sameframe_hg manifest SHA-256 mismatch: {got_sha} != {SAMEFRAME_HG_MANIFEST_SHA256}')
    69	    raw_dir = SAMEFRAME_HG_DIR / 'out' / 'raw'
    70	    out: dict[str, str] = {}
    71	    for line in manifest.read_text(encoding='utf-8').splitlines():
    72	        if not line.strip():
    73	            continue
    74	        digest, fname = line.split()
    75	        p = raw_dir / fname
    76	        if not p.is_file():
    77	            raise FileNotFoundError(f'Missing sameframe_hg shard {p}')
    78	        actual = ar.md5_file(p)
    79	        if actual != digest:
    80	            raise RuntimeError(f'sameframe_hg shard MD5 mismatch {p}: {actual} != {digest}')
    81	        out[fname] = actual
    82	    disk_shards = {p.name for p in raw_dir.glob('part*_shard*.jsonl.gz')}
    83	    if disk_shards != set(out):
    84	        raise RuntimeError(f'sameframe_hg shard set mismatch on disk: {sorted(disk_shards ^ set(out))}')
    85	    return out
    86	
    87	
    88	def verify_all_archives() -> dict[str, dict[str, str]]:
    89	    res = {name: sf.verify_manifest(name) for name in sf.ARCHIVE_MANIFESTS}
    90	    res['sameframe_hg'] = verify_sameframe_hg_manifest()
    91	    return res
    92	
    93	
    94	def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
    95	    import subprocess
    96	
    97	    repo_root = EXP.parent
    98	    probe = subprocess.run(
    99	        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
   100	        capture_output=True, text=True, check=False,
   101	    )
   102	    if probe.returncode != 0 or probe.stdout.strip() != 'true':
   103	        return False
   104	    check = subprocess.run(
   105	        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'{freeze_commit}^{{commit}}'],
   106	        capture_output=True, text=True, check=False,
   107	    )
   108	    if check.returncode != 0:
   109	        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo')
   110	    top = Path(subprocess.run(
   111	        ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
   112	        capture_output=True, text=True, check=True,
   113	    ).stdout.strip())
   114	    rel_dir = HERE.relative_to(top)
   115	    for name, exp_md5 in live_own.items():
   116	        blob = subprocess.run(
   117	            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
   118	            capture_output=True, check=False,
   119	        )
   120	        if blob.returncode != 0:
   121	            raise RuntimeError(f'freeze_commit {freeze_commit} missing {name}')
   122	        if hashlib.md5(blob.stdout).hexdigest() != exp_md5:
   123	            raise RuntimeError(f'Live {name} differs from freeze_commit {freeze_commit}')
   124	    return True
   125	
   126	
   127	def run_cd_timed(
   128	    ctx,
   129	    helpers: dict[str, Any],
   130	    obs: dict[str, Any],
   131	    arrays: dict[str, Any],
   132	    truth: dict[str, Any],
   133	    *,
   134	    arm_spec: str,
   135	    max_passes: int,
   136	) -> dict[str, Any]:
   137	    """Decision-ready timed 1-or-2-pass CODELAY (same timer boundary as hs_arms.run_hg_arm)."""
   138	    stage3 = helpers['stage3']
   139	    cd = helpers['cd_e8'] if arm_spec == 'A1e8' else helpers['cd']
   140	
   141	    t0 = perf_counter()
   142	    ar._require_finite(arrays['r1_check'], f'{arm_spec}.p1.r1_check')
   143	    ar._require_finite(arrays['r1_app'], f'{arm_spec}.p1.r1_app')
   144	    br1 = stage3.e1.run_branch(ctx, cd, obs, arrays, arm_spec)
   145	    dec1 = br1['decoder']
   146	    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))
   147	    if syn1 == 0 or max_passes == 1:
   148	        sec = perf_counter() - t0
   149	        res1 = br1['result']
   150	        if bool(res1.diagnostics.get('numerical_fallback')):
   151	            raise FloatingPointError(f'numerical_fallback in {arm_spec} p1')
   152	        ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
   153	        ar._require_finite(br1['detector']['extrinsic'], f'{arm_spec}.p1.extrinsic')
   154	        d1 = stage3.decoded(ctx, dec1, truth)
   155	        return dict(
   156	            errors=d1['errors'], decoded_sha=d1['decoded_sha'], syndrome=syn1,
   157	            passes_used=1, seconds=float(sec),
   158	        )
   159	
   160	    res1 = br1['result']
   161	    arrays2 = dict(
   162	        r1_delays=np.array([int(p.delay) for p in res1.paths], dtype=int),
   163	        r1_dopplers=np.array([float(p.doppler) for p in res1.paths], dtype=float),
   164	        r1_gains=np.asarray(res1.gains, dtype=complex),
   165	        r1_check=dec1['raw_check_extrinsic'],
   166	        r1_app=dec1['raw_app'],
   167	    )
   168	    br2 = stage3.e1.run_branch(ctx, cd, obs, arrays2, arm_spec)
   169	    dec2 = br2['decoder']
   170	    syn2 = int(ctx.hd.syndrome_weight(ctx, dec2['decoded']))
   171	    sec = perf_counter() - t0
   172	
   173	    res2 = br2['result']
   174	    if bool(res1.diagnostics.get('numerical_fallback')) or bool(res2.diagnostics.get('numerical_fallback')):
   175	        raise FloatingPointError(f'numerical_fallback in {arm_spec}')
   176	    ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
   177	    ar._require_finite(res2.gains, f'{arm_spec}.p2.gains')
   178	    ar._require_finite(br2['detector']['extrinsic'], f'{arm_spec}.p2.extrinsic')
   179	    ar._require_finite(dec2['raw_check_extrinsic'], f'{arm_spec}.p2.raw_check_extrinsic')
   180	    ar._require_finite(dec2['raw_app'], f'{arm_spec}.p2.raw_app')
   181	    d2 = stage3.decoded(ctx, dec2, truth)
   182	    return dict(
   183	        errors=d2['errors'], decoded_sha=d2['decoded_sha'], syndrome=syn2,
   184	        passes_used=2, seconds=float(sec),
   185	    )
   186	
   187	
   188	# --------------------------------------------------------------------------- Gates G1-G3
   189	def _g1_g2_worker(in_path: str, out_path: str):
   190	    C, _, _, helpers = sf.load_stage_runtime()
   191	    stage3, ctx = C['stage3'], C['ctx']
   192	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   193	    res = []
   194	    for s, rho, snr, frame, exp_syn, exp_f0_err, exp_base_err in jobs:
   195	        base = stage3.inputs(ctx, frame, s, rho)
   196	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   197	        dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   198	        f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   199	        if int(syn) != int(exp_syn) or f0_err != int(exp_f0_err) or int(syn) == 0:
   200	            raise AssertionError(f'G1 F0 mismatch at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})')
   201	        cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
   202	        if int(cd2['pass1_errors']) != int(exp_base_err):
   203	            raise AssertionError(
   204	                f'G2 CD2 pass-1 errors mismatch vs stageA base at {(s, rho, snr, frame)}: '
   205	                f'{cd2["pass1_errors"]} != {exp_base_err}'
   206	            )
   207	        cd2e8 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   208	        res.append(dict(
   209	            key=[s, rho, snr, frame],
   210	            f0_ok=True,
   211	            cd2_pass1_ok=True,
   212	            cd2_passes=cd2['passes_used'],
   213	            cd2_p1_err=cd2['pass1_errors'],
   214	            cd2_final_err=cd2['errors'],
   215	            cd2e8_passes=cd2e8['passes_used'],
   216	            cd2e8_final_err=cd2e8['errors'],
   217	        ))
   218	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   219	
   220	
   221	def _g3_cost_worker(in_path: str, out_path: str):
   222	    C, _, _, helpers = sf.load_stage_runtime()
   223	    stage3, ctx = C['stage3'], C['ctx']
   224	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   225	    res = []
   226	    for s, rho, snr, frame, band, exp_base_err in jobs:
   227	        t0 = time.process_time()
   228	        base = stage3.inputs(ctx, frame, s, rho)
   229	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   230	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   231	        t_f0 = time.process_time() - t0
   232	        if int(syn) == 0:
   233	            raise AssertionError(f'G3 key untriggered: {(s, rho, snr, frame)}')
   234	        t1 = time.process_time()
   235	        cd2 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1')
   236	        t_cd2 = time.process_time() - t1
   237	        if int(cd2['pass1_errors']) != int(exp_base_err):
   238	            raise AssertionError(f'G3 CD2 pass-1 drift at {(s, rho, snr, frame)}')
   239	        t2 = time.process_time()
   240	        cd2e8 = sf.run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   241	        t_cd2e8 = time.process_time() - t2
   242	        res.append(dict(
   243	            key=[s, rho, snr, frame], rho=rho, band=band,
   244	            f0_cpu=t_f0, cd2_cpu=t_cd2, cd2e8_cpu=t_cd2e8,
   245	            cd2_passes=cd2['passes_used'], cd2e8_passes=cd2e8['passes_used'],
   246	        ))
   247	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   248	
   249	
   250	def cmd_gate(args):
   251	    print(sys.executable, flush=True)
   252	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   253	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   254	    thread_env = ar.check_thread_env()
   255	    started = time.monotonic()
   256	
   257	    out_dir = args.out.resolve()
   258	    out_dir.mkdir(parents=True, exist_ok=True)
   259	    stale = out_dir / 'gate.json'
   260	    if stale.exists():
   261	        stale.unlink()
   262	
   263	    manifests = verify_all_archives()
   264	    C, _, _, helpers = sf.load_stage_runtime()
   265	    ctx = C['ctx']
   266	
   267	    stageA_base = sf.load_stageA_base(PARTA_RHOS)
   268	    pA_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   269	    for k, v in stageA_base.items():
   270	        if v['syndrome'] != 0:
   271	            band = 'low' if k[2] <= 400 else 'mid'
   272	            pA_strata.setdefault((k[1], band), []).append(k)
   273	
   274	    # 20 keys for G1+G2: 5 per rho in 100..250, guaranteeing U/G, low/mid, and both pass-1 pass & fail
   275	    g12_jobs = []
   276	    for rho in PARTA_RHOS:
   277	        all_r = sorted(pA_strata[(rho, 'low')] + pA_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   278	        picks = []
   279	        for band in ('low', 'mid'):
   280	            for scen in ('U', 'G'):
   281	                pool = sorted((k for k in pA_strata[(rho, band)] if k[0] == scen), key=lambda k: (k[2], k[3]))
   282	                picks.append(pool[len(pool) // 2])
   283	        # 5th key: ensure a pass-1 rescue (base errors == 0) in mid band if available
   284	        rescued = [k for k in pA_strata[(rho, 'mid')] if stageA_base[k]['errors'] == 0 and k not in picks]
   285	        if rescued:
   286	            picks.append(sorted(rescued, key=lambda k: (k[2], k[3]))[len(rescued) // 2])
   287	        else:
   288	            picks.append(next(k for k in all_r if k not in picks))
   289	        for s, r, snr, f in picks:
   290	            v = stageA_base[(s, r, snr, f)]
   291	            g12_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors'], v['errors']])
   292	
   293	    g3_picks = sf._select_balanced_keys(pA_strata, per_stratum=4)  # 4 rhos * 2 bands * 4 = 32 keys
   294	    g3_jobs = [
   295	        [s, r, snr, f, band, stageA_base[(s, r, snr, f)]['errors']]
   296	        for s, r, snr, f, band in g3_picks
   297	    ]
   298	
   299	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   300	    ipc_dir = tmp_root / f'sameframe_cd2_gates_ipc_{os.getpid()}'
   301	    ipc_dir.mkdir(parents=True, exist_ok=True)
   302	    try:
   303	        print('Running G1+G2 (20 low-pilot stageA F0 + CD2 pass-1 + CD2e8 keys)...', flush=True)
   304	        g12_rows = sf._spawn_map(_g1_g2_worker, g12_jobs, args.workers, ipc_dir, 'g12')
   305	        cd2_p1 = sum(1 for x in g12_rows if x['cd2_passes'] == 1)
   306	        cd2_p2 = sum(1 for x in g12_rows if x['cd2_passes'] == 2)
   307	        e8_p2 = sum(1 for x in g12_rows if x['cd2e8_passes'] == 2)
   308	        if not (cd2_p1 > 0 and cd2_p2 > 0 and e8_p2 > 0):
   309	            raise AssertionError(f'G2 did not cover pass-1 and pass-2: p1={cd2_p1}, p2={cd2_p2}, e8_p2={e8_p2}')
   310	        print(f'G1+G2 PASS (20/20; cd2_p1={cd2_p1}, cd2_p2={cd2_p2}, cd2e8_p2={e8_p2})', flush=True)
   311	
   312	        print(f'Running G3 stratified cost projection ({len(g3_jobs)} Part-A keys)...', flush=True)
   313	        g3_rows = sf._spawn_map(_g3_cost_worker, g3_jobs, args.workers, ipc_dir, 'g3')
   314	    finally:
   315	        shutil.rmtree(ipc_dir, ignore_errors=True)
   316	
   317	    counts = {k: len(v) for k, v in pA_strata.items()}
   318	
   319	    def project(include_cd2e8: bool) -> dict[str, Any]:
   320	        pA_sec = 0.0
   321	        detail = {}
   322	        for rho in PARTA_RHOS:
   323	            for band in ('low', 'mid'):
   324	                sub = [x for x in g3_rows if x['rho'] == rho and x['band'] == band]
   325	                mean_cpu = float(np.mean([
   326	                    x['f0_cpu'] + x['cd2_cpu'] + (x['cd2e8_cpu'] if include_cd2e8 else 0.0)
   327	                    for x in sub
   328	                ]))
   329	                cnt = counts[(rho, band)]
   330	                pA_sec += mean_cpu * cnt
   331	                detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   332	        raw_h = pA_sec / 3600.0 + TIMING_ALLOWANCE_HOURS + IO_ALLOWANCE_HOURS
   333	        marg_h = raw_h * COST_MARGIN
   334	        return dict(
   335	            include_cd2e8=include_cd2e8,
   336	            partA_raw_hours=pA_sec / 3600.0,
   337	            timing_allowance_hours=TIMING_ALLOWANCE_HOURS,
   338	            io_allowance_hours=IO_ALLOWANCE_HOURS,
   339	            raw_total_hours=raw_h,
   340	            projected_hours_with_margin=marg_h,
   341	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   342	            strata=detail,
   343	        )
   344	
   345	    candidates = [project(True), project(False)]
   346	    selected = next((c for c in candidates if c['within_budget']), None)
   347	    gate_cpu_h = sf._used_cpu_seconds() / 3600.0
   348	    all_passed = bool(len(g12_rows) == 20 and cd2_p1 > 0 and cd2_p2 > 0 and e8_p2 > 0 and selected is not None)
   349	
   350	    payload = dict(
   351	        _argv=sys.argv,
   352	        _config=dict(
   353	            python_executable=sys.executable,
   354	            threads=thread_env,
   355	            workers=args.workers,
   356	            own_md5=own_md5(),
   357	            frozen_extra_md5=helpers['extra_md5'],
   358	            p1_source_md5=ar.frozen_p1_md5(ctx),
   359	            archive_shards_verified={k: len(v) for k, v in manifests.items()},
   360	            sameframe_hg_manifest_sha256=SAMEFRAME_HG_MANIFEST_SHA256,
   361	        ),
   362	        all_passed=all_passed,
   363	        selected=None if selected is None else dict(
   364	            partA_rhos=list(PARTA_RHOS),
   365	            include_cd2e8=selected['include_cd2e8'],
   366	            projected_hours_with_margin=selected['projected_hours_with_margin'],
   367	            raw_total_hours=selected['raw_total_hours'],
   368	        ),
   369	        G1=dict(passed=len(g12_rows) == 20, keys_checked=len(g12_rows)),
   370	        G2=dict(passed=True, keys_checked=len(g12_rows), cd2_p1=cd2_p1, cd2_p2=cd2_p2, cd2e8_p2=e8_p2, rows=g12_rows),
   371	        G3=dict(
   372	            passed=selected is not None,
   373	            budget_cap_core_hours=BUDGET_CAP_HOURS,
   374	            margin=COST_MARGIN,
   375	            candidates=candidates,
   376	        ),
   377	        gate_cpu_hours=gate_cpu_h,
   378	        gate_wall_seconds=time.monotonic() - started,
   379	    )
   380	    ar.atomic_write_text(out_dir / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
   381	    print(
   382	        f'GATE_STATUS={"PASS" if all_passed else "FAIL_BUDGET"} '
   383	        f'selected={payload["selected"]} cpu_hours={gate_cpu_h:.4f}',
   384	        flush=True,
   385	    )
   386	    sys.exit(0 if all_passed else 1)
   387	
   388	

exec
/bin/zsh -lc "nl -ba sameframe_cd2.py | sed -n '861,1186p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
exec
/bin/zsh -lc "nl -ba PROTOCOL.md | sed -n '12,35p'; nl -ba test_sameframe_cd2.py" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
 succeeded in 0ms:
   861	def _latency(values: list[float]) -> dict[str, Any]:
   862	    arr = np.asarray(values, dtype=float)
   863	    return dict(
   864	        n=int(len(arr)),
   865	        mean=float(arr.mean()),
   866	        median=float(np.median(arr)),
   867	        p95=float(np.percentile(arr, 95)),
   868	    )
   869	
   870	
   871	def _load_huang_and_cd2_archives_for_panels(target_pairs: set[tuple[int, int]]):
   872	    """Load archived decoded_sha for HG/HG1/HGint (huang_steelman) and CD2/CD2e8 (sameframe_hg) on target (rho, snr)."""
   873	    hg_map: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   874	    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
   875	        with p.open('r', encoding='utf-8') as fh:
   876	            for line in fh:
   877	                r = json.loads(line)
   878	                if (int(r['rho_permille']), int(r['snr_centi_db'])) in target_pairs:
   879	                    hg_map[ar.row_key(r)] = r['arms']
   880	    cd2_map: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   881	    for idx in range(N_SHARDS):
   882	        sp = SAMEFRAME_HG_DIR / 'out' / 'raw' / f'part2_shard{idx:03d}.jsonl.gz'
   883	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
   884	            for line in fh:
   885	                r = json.loads(line)
   886	                if (int(r['rho_permille']), int(r['snr_centi_db'])) in target_pairs:
   887	                    cd2_map[ar.row_key(r)] = r['arms']
   888	    return hg_map, cd2_map
   889	
   890	
   891	def cmd_timing(args):
   892	    print(sys.executable, flush=True)
   893	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   894	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   895	    thread_env = ar.check_thread_env()
   896	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   897	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   898	    proc_start = perf_counter()
   899	
   900	    aff = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else [0]
   901	    if platform.system() == 'Linux' and len(aff) != 1:
   902	        raise RuntimeError(f'timing must be pre-pinned to 1 CPU via taskset, got affinity={aff}')
   903	    cpu_info = dict(
   904	        idle_cpu=int(aff[0]),
   905	        measured_utilization_pct=float(os.environ.get('HS_QUIET_CPU_UTIL', '-1.0')),
   906	        load=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [],
   907	    )
   908	    print(f'Quiet timing running on pre-pinned CPU {cpu_info}', flush=True)
   909	
   910	    out_dir = args.out.resolve()
   911	    verify_freeze_commit_if_git(args.freeze_commit, own_md5())
   912	    results_path = out_dir / 'results.json'
   913	    results = json.loads(results_path.read_text(encoding='utf-8'))
   914	    if results['_config']['freeze_commit'] != args.freeze_commit:
   915	        raise RuntimeError('timing freeze-commit differs from results.json')
   916	
   917	    # Verify cumulative budget before starting timing
   918	    partA_cpu_h = float(results['runtime']['partA_total_core_hours'])
   919	    remaining_cpu_sec = min(TIMING_BUDGET_SEC, BUDGET_CAP_SEC - partA_cpu_h * 3600.0)
   920	    if remaining_cpu_sec <= 60.0:
   921	        print(f'STOPPED_BUDGET before timing (partA_cpu={partA_cpu_h:.4f}h)', flush=True)
   922	        sys.exit(BUDGET_EXIT_CODE)
   923	
   924	    verify_all_archives()
   925	    C, _, _, helpers = sf.load_stage_runtime()
   926	    stage3, ctx = C['stage3'], C['ctx']
   927	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   928	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   929	
   930	    archived_rows, _ = ar.load_archived_rho_sweep()
   931	    target_pairs = {(rho, snr) for _, rho, snr in TIMING_PANELS}
   932	    hg_arch, cd2_arch = _load_huang_and_cd2_archives_for_panels(target_pairs)
   933	
   934	    # Prewarm on smoke frame 5800 (not measured)
   935	    warm_base = stage3.inputs(ctx, 5800, 'U', 200)
   936	    _, warm_obs, warm_truth = stage3.observed(ctx, warm_base, 200, 450)
   937	    _, warm_arr, _, _ = stage3.e1.f0_state(ctx, warm_obs)
   938	    run_cd_timed(ctx, helpers, warm_obs, warm_arr, warm_truth, arm_spec='A1', max_passes=1)
   939	    ar.run_hg_arm(
   940	        ctx, helpers, warm_obs, warm_arr, warm_truth,
   941	        ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   942	        max_passes=1, record_match=False,
   943	    )
   944	
   945	    rows_lines: list[str] = []
   946	    panels_summary: dict[str, Any] = {}
   947	    all_report_arms = ('CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint')
   948	
   949	    for panel_name, rho, snr in TIMING_PANELS:
   950	        trig_by_s = {}
   951	        untrig_by_s = {}
   952	        for s in ar.SCENARIOS:
   953	            trig_by_s[s] = sorted(
   954	                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and k[2] == snr and r['triggered']),
   955	                key=lambda k: k[3],
   956	            )
   957	            untrig_by_s[s] = sorted(
   958	                (k for k, r in archived_rows.items() if k[0] == s and k[1] == rho and k[2] == snr and not r['triggered']),
   959	                key=lambda k: k[3],
   960	            )
   961	            if len(trig_by_s[s]) < 50 or len(untrig_by_s[s]) < 25:
   962	                raise RuntimeError(f'Insufficient keys for {panel_name}/{s}: trig={len(trig_by_s[s])}, untrig={len(untrig_by_s[s])}')
   963	
   964	        panel_keys = [k for pair in zip(trig_by_s['U'][:50], trig_by_s['G'][:50], strict=True) for k in pair]
   965	        untrig_keys = [k for pair in zip(untrig_by_s['U'][:25], untrig_by_s['G'][:25], strict=True) for k in pair]
   966	
   967	        untrig_f0_sec: dict[str, list[float]] = {'U': [], 'G': []}
   968	        for key in untrig_keys:
   969	            s, r_, snr_, frame = key
   970	            arch = archived_rows[key]
   971	            base = stage3.inputs(ctx, frame, s, r_)
   972	            _, obs, truth = stage3.observed(ctx, base, r_, snr_)
   973	            t_f0 = perf_counter()
   974	            dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
   975	            f0_sec = perf_counter() - t_f0
   976	            f0 = stage3.decoded(ctx, dec, truth)
   977	            if syn != 0 or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
   978	                raise AssertionError(f'Timing untriggered F0 drift at {key}')
   979	            untrig_f0_sec[s].append(float(f0_sec))
   980	            rows_lines.append(json.dumps(dict(
   981	                panel=panel_name, kind='untriggered_f0', key=list(key), f0_seconds=float(f0_sec),
   982	            ), allow_nan=False) + '\n')
   983	            if perf_counter() - proc_start >= remaining_cpu_sec:
   984	                sys.exit(BUDGET_EXIT_CODE)
   985	
   986	        timed_rows = []
   987	        scen_pos = {'U': 0, 'G': 0}
   988	        for idx, key in enumerate(panel_keys):
   989	            s, r_, snr_, frame = key
   990	            arch = archived_rows[key]
   991	            hga = hg_arch[key]
   992	            cd2a = cd2_arch[key]
   993	            base = stage3.inputs(ctx, frame, s, r_)
   994	            _, obs, truth = stage3.observed(ctx, base, r_, snr_)
   995	
   996	            t_f0 = perf_counter()
   997	            dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   998	            f0_sec = perf_counter() - t_f0
   999	            f0 = stage3.decoded(ctx, dec, truth)
  1000	            if syn != arch['syndrome'] or f0['decoded_sha'] != arch['arms']['F0']['decoded_sha']:
  1001	                raise AssertionError(f'Timing F0 drift at {key}')
  1002	
  1003	            offset = scen_pos[s] % len(TIMING_BRANCHES)
  1004	            scen_pos[s] += 1
  1005	            order = TIMING_BRANCHES[offset:] + TIMING_BRANCHES[:offset]
  1006	            sec_map: dict[str, float] = {}
  1007	            passes_map: dict[str, int] = {}
  1008	            for arm in order:
  1009	                if arm == 'CD':
  1010	                    out = run_cd_timed(ctx, helpers, obs, arrays, truth, arm_spec='A1', max_passes=1)
  1011	                    if out['decoded_sha'] != arch['arms']['CD']['decoded_sha']:
  1012	                        raise AssertionError(f'Timing CD drift at {key}')
  1013	                    sec_map['CD'] = out['seconds']
  1014	                    passes_map['CD'] = 1
  1015	                elif arm == 'CD2':
  1016	                    out = run_cd_timed(ctx, helpers, obs, arrays, truth, arm_spec='A1', max_passes=2)
  1017	                    if out['decoded_sha'] != cd2a['CD2']['decoded_sha']:
  1018	                        raise AssertionError(f'Timing CD2 drift at {key}')
  1019	                    sec_map['CD2'] = out['seconds']
  1020	                    passes_map['CD2'] = out['passes_used']
  1021	                elif arm == 'CD2e8':
  1022	                    out = run_cd_timed(ctx, helpers, obs, arrays, truth, arm_spec='A1e8', max_passes=2)
  1023	                    if out['decoded_sha'] != cd2a['CD2e8']['decoded_sha']:
  1024	                        raise AssertionError(f'Timing CD2e8 drift at {key}')
  1025	                    sec_map['CD2e8'] = out['seconds']
  1026	                    passes_map['CD2e8'] = out['passes_used']
  1027	                elif arm == 'HG':
  1028	                    out = ar.run_hg_arm(
  1029	                        ctx, helpers, obs, arrays, truth,
  1030	                        ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
  1031	                        max_passes=2, record_match=False,
  1032	                    )
  1033	                    if (out['HG']['decoded_sha'] != hga['HG']['decoded_sha']
  1034	                            or out['HG1']['decoded_sha'] != hga['HG1']['decoded_sha']):
  1035	                        raise AssertionError(f'Timing HG/HG1 drift at {key}')
  1036	                    sec_map['HG'] = out['HG']['seconds']
  1037	                    sec_map['HG1'] = out['HG1']['seconds']
  1038	                    passes_map['HG'] = out['HG']['passes_used']
  1039	                    passes_map['HG1'] = 1
  1040	                elif arm == 'HGint':
  1041	                    out = ar.run_hg_arm(
  1042	                        ctx, helpers, obs, arrays, truth,
  1043	                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
  1044	                        max_passes=2, record_match=False,
  1045	                    )
  1046	                    if out['HG']['decoded_sha'] != hga['HGint']['decoded_sha']:
  1047	                        raise AssertionError(f'Timing HGint drift at {key}')
  1048	                    sec_map['HGint'] = out['HG']['seconds']
  1049	                    passes_map['HGint'] = out['HG']['passes_used']
  1050	
  1051	            row = dict(
  1052	                panel=panel_name, kind='triggered_panel', key=list(key), order=list(order),
  1053	                f0_seconds=float(f0_sec), passes_used=passes_map, branch_seconds=sec_map,
  1054	            )
  1055	            rows_lines.append(json.dumps(row, allow_nan=False) + '\n')
  1056	            timed_rows.append(row)
  1057	
  1058	            elapsed = perf_counter() - proc_start
  1059	            if elapsed >= remaining_cpu_sec:
  1060	                print(f'STOPPED_BUDGET in timing {panel_name} at {idx+1}/100 ({elapsed:.1f}s)', flush=True)
  1061	                sys.exit(BUDGET_EXIT_CODE)
  1062	            if (idx + 1) % 25 == 0:
  1063	                print(f'Timing [{panel_name}] {idx+1}/100 done in {elapsed:.1f}s', flush=True)
  1064	
  1065	        cd_arr = np.array([r['branch_seconds']['CD'] for r in timed_rows], dtype=float)
  1066	        f0_arr = np.array([r['f0_seconds'] for r in timed_rows], dtype=float)
  1067	        branches = {}
  1068	        rel_cd = {}
  1069	        pass2_rate = {}
  1070	        for arm in all_report_arms:
  1071	            arr = np.array([r['branch_seconds'][arm] for r in timed_rows], dtype=float)
  1072	            branches[arm] = _latency(arr.tolist())
  1073	            pass2_rate[arm] = float(np.mean([r['passes_used'][arm] == 2 for r in timed_rows]))
  1074	            if arm != 'CD':
  1075	                rel_cd[arm] = dict(
  1076	                    ratio_of_means=float(arr.mean() / cd_arr.mean()),
  1077	                    median_paired_ratio=float(np.median(arr / cd_arr)),
  1078	                    cd_faster_fraction=float(np.mean(cd_arr < arr)),
  1079	                )
  1080	
  1081	        p_trig_by_s = {s: len(trig_by_s[s]) / 400.0 for s in ar.SCENARIOS}
  1082	        amortized_by_s = {}
  1083	        for s in ar.SCENARIOS:
  1084	            s_rows = [r for r in timed_rows if r['key'][0] == s]
  1085	            p_s = p_trig_by_s[s]
  1086	            f0_u = float(np.mean(untrig_f0_sec[s]))
  1087	            f0_t = float(np.mean([r['f0_seconds'] for r in s_rows]))
  1088	            amortized_by_s[s] = {
  1089	                arm: float((1.0 - p_s) * f0_u + p_s * (f0_t + float(np.mean([r['branch_seconds'][arm] for r in s_rows]))))
  1090	                for arm in all_report_arms
  1091	            }
  1092	        amortized_mean = {arm: 0.5 * (amortized_by_s['U'][arm] + amortized_by_s['G'][arm]) for arm in all_report_arms}
  1093	
  1094	        panels_summary[panel_name] = dict(
  1095	            rho_permille=rho,
  1096	            snr_centi_db=snr,
  1097	            keys=len(timed_rows),
  1098	            untriggered_f0_keys=len(untrig_keys),
  1099	            f0=_latency(f0_arr.tolist()),
  1100	            f0_untriggered={s: _latency(untrig_f0_sec[s]) for s in ar.SCENARIOS},
  1101	            branches=branches,
  1102	            pass2_rate=pass2_rate,
  1103	            relative_to_cd=rel_cd,
  1104	            trigger_rate_by_scenario=p_trig_by_s,
  1105	            amortized_full_frame_mean_by_scenario=amortized_by_s,
  1106	            amortized_full_frame_mean_seconds=amortized_mean,
  1107	        )
  1108	
  1109	    timing_rows_path = out_dir / 'raw' / 'timing_rows.jsonl'
  1110	    ar.atomic_write_text(timing_rows_path, ''.join(rows_lines))
  1111	    timing_rows_md5 = ar.md5_file(timing_rows_path)
  1112	
  1113	    # Append timing_rows.jsonl MD5 into REMOTE_ROWS_MD5.txt atomically
  1114	    md5_map = {}
  1115	    for line in (out_dir / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8').splitlines():
  1116	        if line.strip():
  1117	            d, n = line.split()
  1118	            md5_map[n] = d
  1119	    md5_map[timing_rows_path.name] = timing_rows_md5
  1120	    ar.atomic_write_text(
  1121	        out_dir / 'REMOTE_ROWS_MD5.txt',
  1122	        ''.join(f'{d}  {n}\n' for n, d in sorted(md5_map.items())),
  1123	    )
  1124	
  1125	    wall = perf_counter() - proc_start
  1126	    timing_cpu_h = sf._used_cpu_seconds() / 3600.0
  1127	    if partA_cpu_h + timing_cpu_h >= BUDGET_CAP_HOURS:
  1128	        print(f'STOPPED_BUDGET after timing (total={partA_cpu_h + timing_cpu_h:.4f}h)', flush=True)
  1129	        sys.exit(BUDGET_EXIT_CODE)
  1130	
  1131	    timing_payload = dict(
  1132	        _argv=sys.argv,
  1133	        _config=dict(
  1134	            freeze_commit=args.freeze_commit,
  1135	            python_executable=sys.executable,
  1136	            threads=thread_env,
  1137	            timing_boundary='decision-ready (after syndrome check, before truth scoring/hashing)',
  1138	            branches=list(TIMING_BRANCHES),
  1139	            timing_rows_path=str(timing_rows_path),
  1140	            timing_rows_md5=timing_rows_md5,
  1141	        ),
  1142	        cpu=cpu_info,
  1143	        end_load=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [],
  1144	        wall_seconds=float(wall),
  1145	        timing_cpu_hours=float(timing_cpu_h),
  1146	        panels=panels_summary,
  1147	    )
  1148	    ar.atomic_write_text(out_dir / 'timing_summary.json', json.dumps(timing_payload, indent=2, allow_nan=False) + '\n')
  1149	
  1150	    results['timing'] = timing_payload
  1151	    results['runtime']['timing_cpu_hours'] = float(timing_cpu_h)
  1152	    results['runtime']['total_core_hours'] = float(partA_cpu_h + timing_cpu_h)
  1153	    results['_config']['raw_rows_md5'] = md5_map
  1154	    ar.atomic_write_text(results_path, json.dumps(results, indent=2, allow_nan=False) + '\n')
  1155	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
  1156	    p20 = panels_summary['rho200_snr450']['branches']
  1157	    print(
  1158	        f'TIMING_DONE wall={wall:.1f}s cpu={timing_cpu_h:.4f}h '
  1159	        f'rho200_mean: CD={1000*p20["CD"]["mean"]:.1f}ms CD2={1000*p20["CD2"]["mean"]:.1f}ms '
  1160	        f'HG={1000*p20["HG"]["mean"]:.1f}ms HGint={1000*p20["HGint"]["mean"]:.1f}ms',
  1161	        flush=True,
  1162	    )
  1163	
  1164	
  1165	def main():
  1166	    ap = argparse.ArgumentParser(description=__doc__)
  1167	    sub = ap.add_subparsers(dest='mode', required=True)
  1168	    g = sub.add_parser('gate')
  1169	    g.add_argument('--out', type=Path, required=True)
  1170	    g.add_argument('--workers', type=int, default=16)
  1171	
  1172	    r = sub.add_parser('partA')
  1173	    r.add_argument('--out', type=Path, required=True)
  1174	    r.add_argument('--freeze-commit', required=True)
  1175	    r.add_argument('--workers', type=int, default=WORKERS)
  1176	
  1177	    t = sub.add_parser('timing')
  1178	    t.add_argument('--out', type=Path, required=True)
  1179	    t.add_argument('--freeze-commit', required=True)
  1180	
  1181	    args = ap.parse_args()
  1182	    dict(gate=cmd_gate, partA=cmd_run_partA, timing=cmd_timing)[args.mode](args)
  1183	
  1184	
  1185	if __name__ == '__main__':
  1186	    main()

 succeeded in 0ms:
    12	
    13	---
    14	
    15	## 2. 实验设计与代码复用（不改任何冻结文件）
    16	
    17	所有逻辑直接复用已有模块：`experiments/sameframe_hg_20261124/sameframe.py`（`load_stage_runtime`、`run_cd_two_pass`、`load_stageA_base`、`verify_manifest`、`_select_balanced_keys`、`_spawn_map`、`_run_sharded_phase`、`_write_gzip_jsonl_atomic`、`crossing_bounds_stageA2`）、`experiments/huang_steelman_20261124/hs_arms.py`（`run_hg_arm`、`fine_grid`、`coarse_grid`、`load_archived_rho_sweep`）、`experiments/data_pilot_fer_20261121/{stageA,stageA2,stageA3}.py`。
    18	
    19	### Part A（帧 `41000–41399`，场景 U/G）
    20	- **网格**：$\rho \in \{100, 150, 200, 250\}$ permille，`SNR = stageA.SNRS`（3..12 dB 共 13 点）；总计 41,600 键，其中归档 `stageA` `arms.base.syndrome != 0` 的触发键共 **13,735** 键。
    21	- **逐键规则**：
    22	  - 未触发键（`arms.base.syndrome == 0`）：不重跑，直接取 `arms.base.f0_errors`。
    23	  - 触发键：重跑 `f0_state`，断言实时 `syndrome == arms.base.syndrome` 与 `f0_errors == arms.base.f0_errors`；随后运行 `CD2`（`arm_spec='A1'`，第 1 遍断言 `errors == arms.base.errors`；若第 1 遍 `syndrome != 0` 则按与 `HG` 相同的 `r1_*` 消息更新跑第 2 遍，校验通过提前停止）与 `CD2e8`（运行时 `A1e8` 克隆包装，`max_edits=8`，同两遍早停规则）。均禁用静默回退（`numerical_fallback=True` 或非有限值直接抛错）。
    24	- **同帧归档对照（不重跑，全部 MD5 校验）**：
    25	  - `stageA`（`base`/`delay`）、`stageA2`（`full`/`ldop`）、`stageA3`（`s025`/`s050`/`s100`/`s200`）、`sameframe_hg_20261124` Part 1（`HG`/`HG1`/`HGint`，清单 SHA-256 `7cac38cd7cc8fa610ddf8c0b5908b62c668901cf5b72756889c1fd6a0f6b435f`）。
    26	- **代理局限说明（跑前写定）**：`s100`/`s050` 为**带真时延**的高斯多普勒注入；Stage A3 已表明真实导频多普勒误差比同均值高斯误差温和，而未知时延下的真实半盲估计又会带来额外损失，故 `s100` 是结构化代理而非端到端估计器。
    27	
    28	### Part B（安静单核计时面板，黄帧 `5400–5799`，不设裁决）
    29	- **两组工况**（均从 `rho_sweep_20261119` 按帧号升序抽取）：
    30	  1. **最优点面板**（$\rho=0.20, 4.5\text{ dB}$）：前 50 U + 前 50 G 触发键（100 键）+ 前 25 U + 前 25 G 未触发 F0 键（50 键）。归档总触发率 U `199/400 (49.75%)`、G `227/400 (56.75%)`。
    31	  2. **连续性面板**（$\rho=0.30, 5.0\text{ dB}$）：前 50 U + 前 50 G 触发键（100 键）+ 前 25 U + 前 25 G 未触发 F0 键（50 键）。归档总触发率 U `88/400 (22.00%)`、G `110/400 (27.50%)`。
    32	- **计时臂与顺序**：5 臂 `('CD', 'CD2', 'CD2e8', 'HG', 'HGint')`（同时由 `HG` 第 1 遍免费记录 `HG1`）；按场景 U/G 分别维护轮换位置 `scenario_pos[s] % 5`，使两场景内每臂在 5 个顺序位各出现 10 次。
    33	- **计时边界与一致性**：统一采用 `hs_arms` 的**决策就绪边界**（从分支消息准备/入口开始，到最终 `syndrome_weight` 结束立即停表；真值计分与哈希置于停表之后）。每个计时键逐位核验 `decoded_sha` 与归档一致（`F0`/`CD` 核 `rho_sweep`，`HG`/`HG1`/`HGint` 核 `huang_steelman`，`CD2`/`CD2e8` 核 `sameframe_hg` Part 2）。
    34	- **隔离与绑核**：启动 Python 前扫描 `/proc/stat` 选出最空闲单核并用 `taskset -c <CPU>` 绑定运行，记录启动前空闲利用率和起止系统负载。原始逐键计时写入远端 `out/raw/timing_rows.jsonl` 并记录 MD5。
    35	
     1	"""Unit tests for sameframe_cd2.py P1' verdict rules, joint bootstrap, and 5-arm timing rotation."""
     2	from __future__ import annotations
     3	
     4	import math
     5	import sys
     6	from pathlib import Path
     7	import numpy as np
     8	
     9	HERE = Path(__file__).resolve().parent
    10	sys.path.insert(0, str(HERE))
    11	sys.path.insert(0, str(HERE.parent / 'data_pilot_fer_20261121'))
    12	
    13	import sameframe_cd2 as sc  # noqa: E402
    14	import stageA2  # noqa: E402
    15	
    16	
    17	def _make_fail(curves: dict[int, list[float]], n: int = 200, seed: int = 7) -> np.ndarray:
    18	    rng = np.random.default_rng(seed)
    19	    u = rng.random((n, 2))
    20	    rhos = sorted(curves)
    21	    n_s = len(next(iter(curves.values())))
    22	    out = np.zeros((n, 2, len(rhos), n_s), dtype=bool)
    23	    for ri, r in enumerate(rhos):
    24	        for si in range(2):
    25	            for ji, p in enumerate(curves[r]):
    26	                out[:, si, ri, ji] = u[:, si] < p
    27	    return out
    28	
    29	
    30	def test_p1p_verdict_boundaries():
    31	    assert sc.p1p_verdict(0.5, 0.9) == 'DOPPLER-LINE'
    32	    assert sc.p1p_verdict(0.501, 0.9) == 'DOPPLER-LINE'
    33	    assert sc.p1p_verdict(0.1, 0.499) == 'STOP-LINE'
    34	    assert sc.p1p_verdict(-0.2, 0.499) == 'STOP-LINE'
    35	    assert sc.p1p_verdict(0.499, 0.5) == 'INCONCLUSIVE'
    36	    assert sc.p1p_verdict(-math.inf, math.inf) == 'INCONCLUSIVE'
    37	
    38	
    39	def test_analyze_partA_and_rotation():
    40	    snrs_a = (300, 400, 500, 600, 700)
    41	    snrs_a3 = (200, 250, 300, 400, 500, 600, 700)
    42	    c_cd2 = {100: [0.8, 0.4, 0.05, 0.005, 0.0], 150: [0.5, 0.2, 0.02, 0.002, 0.0], 200: [0.4, 0.1, 0.005, 0.0, 0.0], 250: [0.5, 0.2, 0.01, 0.0, 0.0]}
    43	    c_s100 = {100: [0.6, 0.2, 0.05, 0.005, 0.0, 0.0, 0.0], 150: [0.7, 0.3, 0.08, 0.01, 0.0, 0.0, 0.0], 200: [0.8, 0.4, 0.1, 0.02, 0.005, 0.0, 0.0]}
    44	    fail_by_arm = {
    45	        'CD2': ((100, 150, 200, 250), snrs_a, _make_fail(c_cd2, seed=2)),
    46	        'HG': ((100, 150, 200, 250), snrs_a, _make_fail(c_cd2, seed=2)),
    47	        's100': ((100, 150, 200), snrs_a3, _make_fail(c_s100, seed=2)),
    48	    }
    49	    res = sc.analyze_partA(fail_by_arm, False, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)
    50	    assert res['primary_P1_prime']['verdict'] == 'DOPPLER-LINE'
    51	    assert res['secondary_contrasts']['CD2_minus_HG']['ci95_db'] == [0.0, 0.0]
    52	
    53	    # Verify per-scenario 5-arm rotation puts each arm first exactly 10 times for U and 10 times for G
    54	    first_counts = {'U': {}, 'G': {}}
    55	    scen_pos = {'U': 0, 'G': 0}
    56	    for i in range(100):
    57	        s = 'U' if i % 2 == 0 else 'G'
    58	        off = scen_pos[s] % len(sc.TIMING_BRANCHES)
    59	        scen_pos[s] += 1
    60	        first = sc.TIMING_BRANCHES[off]
    61	        first_counts[s][first] = first_counts[s].get(first, 0) + 1
    62	    assert all(len(d) == 5 and all(v == 10 for v in d.values()) for d in first_counts.values()), first_counts
    63	
    64	
    65	if __name__ == '__main__':
    66	    test_p1p_verdict_boundaries()
    67	    test_analyze_partA_and_rotation()
    68	    print('ALL_SAMEFRAME_CD2_UNIT_TESTS_PASS')

exec
/bin/zsh -lc "rg -n 'deinlab|/dev/shm|sameframe' AGENTS.md STATE.md && ls -a .trellis && git status --short -- experiments/sameframe_hg_20261124 experiments/huang_steelman_20261124 experiments/matched_ldpc_20261122 experiments/sameframe_cd2_20261125" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
STATE.md:26:- 11-25 同帧检验（冻结 `918a24747`，10.9 核时）：**更正上一条**——轮数对齐后两遍 CD 追平 HG（−0.12 [−0.55, +0.08]，`CATCHES_UP`；换 8 条版 −0.19 [−0.58, −0.01]），"局部交换不如全局重找"不成立，HG 的 0.65 dB 来自多一轮；耗时未测。低导频帧上 HG 之后第 0 轮多普勒余量 0.73 [0.45, 1.04] dB（0.08 bin 口径，`INCONCLUSIVE`，下界差 0.05 未过 0.5），0.04 bin 口径 1.12 dB；对两遍 CD 的余量未测（[读数](experiments/sameframe_hg_20261124/READOUT.md)）。
STATE.md:56:- 11-11 deinlab 新帧块对照与方向 A 2×2（探索性，整数时延）：[配对结果与局限](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)。
STATE.md:66:1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
STATE.md:96:10. 本地多余的原始行副本（`experiments/slot_mismatch_20261019/out/pilot*/rows_shard*`，原件在 deinlab）是否删除。
.
..
.DS_Store
.backup-2026-09-08T12-56-43
.backup-2026-09-08T12-56-59
.developer
.gitignore
.runtime
.template-hashes.json
.version
agents
config.yaml
research-project-scaffold.json
research-project.json
scripts
spec
tasks
workflow.md
workspace
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Eg4jTdw1' (errno=Operation not permitted)
?? experiments/sameframe_cd2_20261125/

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n 'PART1_|N_SHARDS|"'^def |part2_shard|numerical_fallback|rho_permille|cd2_e8|pass1_edits|RUSAGE'"' sameframe.py; ls out; cat out/REMOTE_ROWS_MD5.txt | head -5" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124
exec
/bin/zsh -lc "rg -n '"'^def |decoded_sha|pass.*seconds|t0 =|return |numerical_fallback'"' hs_arms.py; rg -n '_nearest_rank|censor|inf' hs_analysis.py; ls out" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124
exec
/bin/zsh -lc "nl -ba sameframe_cd2.py | sed -n '737,825p'; ls -la" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125
 succeeded in 0ms:
36:PART1_RHOS = (100, 150, 200, 250)
37:PART1_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
38:PART1_FRAMES = tuple(range(41000, 41400))
39:PART1_BOOT_DRAWS = 2000
40:PART1_BOOT_SEED = 20261124
58:N_SHARDS = 24
62:def own_md5() -> dict[str, str]:
66:def verify_manifest(name: str) -> dict[str, str]:
94:def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
128:def _make_cd_e8_kernel(cd):
156:def load_stage_runtime():
186:def run_cd_two_pass(
204:    if bool(res1.diagnostics.get('numerical_fallback')):
205:        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 1')
228:            pass1_edits=len(res1.edits),
230:            numerical_fallback=False,
242:    if bool(res2.diagnostics.get('numerical_fallback')):
243:        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 2')
259:        pass1_edits=len(res1.edits),
261:        numerical_fallback=False,
265:def load_stageA_base(rhos: tuple[int, ...] = PART1_RHOS) -> dict[tuple[str, int, int, int], dict[str, int]]:
283:    expected = len(PART1_FRAMES) * 2 * len(rhos) * len(PART1_SNRS)
289:def _used_cpu_seconds() -> float:
290:    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
294:def _active_pids_cpu(pids: list[int]) -> float:
306:def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
336:def _g1_worker(in_path: str, out_path: str):
355:def _g2_worker(in_path: str, out_path: str):
388:def _g3_worker(in_path: str, out_path: str):
411:            cd2e8_p1_edits=cd2e8['pass1_edits'],
418:def _g4_part1_worker(in_path: str, out_path: str):
455:def _g4_part2_worker(in_path: str, out_path: str):
482:def _select_balanced_keys(
504:def cmd_gate(args):
522:    stageA_base = load_stageA_base(PART1_RHOS)
537:                        key=[r['scenario'], int(r['rho_permille']), int(r['snr_centi_db']), int(r['frame'])],
562:    for rho in PART1_RHOS:
678:        project(PART1_RHOS, True),
729:def _write_gzip_jsonl_atomic(final_path: Path, lines: list[str]):
740:def _part1_shard_worker(
805:def _part2_shard_worker(
813:    final_path = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
819:            grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
841:                    scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=int(syn),
848:def _run_sharded_phase(target_fn, job_args: list[tuple[Any, ...]], max_workers: int, cpu_cap_sec: float):
885:def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
895:def p1_verdict(ci_lo: float, ci_hi: float) -> str:
903:def p2_verdict(ci_lo: float, ci_hi: float) -> str:
911:def _rep(v: float) -> Any:
919:def analyze_part1(
925:    boot_draws: int = PART1_BOOT_DRAWS,
926:    boot_seed: int = PART1_BOOT_SEED,
1031:def analyze_part2(
1135:            mean_pass1_edits=float(np.mean([r['arms'][arm]['pass1_edits'] for r in trig_rows])),
1155:def render_results_md(res: dict[str, Any]) -> str:
1214:            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}; '
1223:def _do_read(
1258:    fi = {f: i for i, f in enumerate(PART1_FRAMES)}
1259:    p1_fail = {a: np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool) for a in new_p1_arms}
1260:    p1_seen = np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool)
1265:            ix = (fi[f], ar.SCENARIOS.index(s), part1_rhos.index(rho), PART1_SNRS.index(snr))
1273:    for shard_idx in range(N_SHARDS):
1278:                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), part1_rhos.index(int(r['rho'])), PART1_SNRS.index(int(r['snr'])))
1297:        fail_by_arm[a] = (part1_rhos, PART1_SNRS, p1_fail[a])
1312:    for shard_idx in range(N_SHARDS):
1313:        sp = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
1331:                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
1341:                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
1370:            part1_frames=[PART1_FRAMES[0], PART1_FRAMES[-1]],
1400:def cmd_run(args):
1448:        (idx, tuple(PART1_FRAMES[idx::N_SHARDS]), {f: p1_trig_by_frame.get(f, []) for f in PART1_FRAMES[idx::N_SHARDS]}, include_hgint, raw_dir)
1449:        for idx in range(N_SHARDS)
1467:        (idx, tuple(ar.MAIN_FRAMES[idx::N_SHARDS]), {f: p2_trig_by_frame.get(f, []) for f in ar.MAIN_FRAMES[idx::N_SHARDS]}, raw_dir)
1468:        for idx in range(N_SHARDS)
1472:    _run_sharded_phase(_part2_shard_worker, p2_jobs, args.workers, BUDGET_CAP_SEC)
1479:        for idx in range(N_SHARDS):
1503:def cmd_read(args):
1518:def main():
REMOTE_ROWS_MD5.txt
RESULTS.md
STATUS
gate.json
gate.log
gate_cpu.txt
results.json
run.log
run_cpu.txt
09d59b9ec5ba7663bccd9166645ec597  part1_shard000.jsonl.gz
08c23ccd454ce0276306211e119aa7ac  part1_shard001.jsonl.gz
3f851b7b1a00ddc4af1de97ed7a94026  part1_shard002.jsonl.gz
3573b7de48504f7ad6cc8fa4581bf86d  part1_shard003.jsonl.gz
69303777aa05dbd9aac746941eb6770e  part1_shard004.jsonl.gz

 succeeded in 0ms:
66:def frozen_p1_md5(ctx) -> dict[str, str]:
68:    return {k: v for k, v in ctx.source_md5.items() if k not in OWN_MODULE_NAMES}
71:def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
81:        return False
104:    return True
107:def md5_file(path: Path) -> str:
112:    return h.hexdigest()
115:def sha256_file(path: Path) -> str:
120:    return h.hexdigest()
123:def own_md5() -> dict[str, str]:
130:    return out
133:def atomic_write_text(path: Path, text: str):
143:def check_thread_env() -> dict[str, str]:
149:    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}
152:def verify_frozen_extra_md5() -> dict[str, str]:
159:    return extra_md5
162:def _load_module(name: str, path: Path):
166:    return mod
169:def load_context():
196:    return ctx, helpers
199:def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
203:    return np.repeat(delays, len(dopplers)), np.tile(dopplers, len(delays))
206:def coarse_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
210:    return np.repeat(delays, len(dopplers)), np.tile(dopplers, len(delays))
213:def _require_finite(arr, label: str):
218:def omp_reacquire(
251:        return (*out, A)
252:    return out
255:def match_paths_1to1(fit_delays, fit_dopplers, truth) -> dict[str, Any]:
296:    return dict(
307:def match_omp_nominated(omp_delays, omp_dopplers, truth) -> dict[str, Any]:
318:    return dict(
326:def _decision_record(res) -> list[list[Any]]:
329:        return None if rec is None else [int(rec['slot']), rec[field]]
330:    return [
336:def run_hg_arm(
411:            pass_seconds=float(pass_sec),
421:    return dict(
424:            decoded_sha=p1['decoded_sha'],
427:            seconds=p1['pass_seconds'],
433:            decoded_sha=final['decoded_sha'],
437:            pass1_seconds=p1['pass_seconds'],
445:def _run_exchange_arm(
460:    t0 = perf_counter()
467:    if bool(res.diagnostics.get('numerical_fallback')):
468:        raise FloatingPointError(f'Geometry numerical_fallback triggered in {arm_name}')
490:        numerical_fallback=False,
494:    return out
497:def run_z_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
498:    return _run_exchange_arm(ctx, helpers, helpers['z_kernel'], 'Z', obs, arrays, truth, record_match=record_match)
501:def run_cd_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
502:    return _run_exchange_arm(ctx, helpers, helpers['cd'], 'CD', obs, arrays, truth, record_match=record_match)
505:def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
506:    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))
509:def load_archived_rho_sweep(
547:                    f0_out = (r['arms']['F0']['errors'], r['arms']['F0']['decoded_sha'])
548:                    cd_out = (r['arms']['CD']['errors'], r['arms']['CD']['decoded_sha'])
566:    return rows, verified_md5
59:def _nearest_rank(draws: np.ndarray, probability: float) -> float:
67:        _nearest_rank(bounds.lower[1:], alpha / 2.0),
68:        _nearest_rank(bounds.upper[1:], 1.0 - alpha / 2.0),
73:    if np.isposinf(value):
74:        return '+inf'
75:    if np.isneginf(value):
76:        return '-inf'
85:        np.where(status == p1_agg.LOW, -np.inf, x),
86:        np.where(status == p1_agg.HIGH, np.inf, x),
100:    """Compute censor-aware 1% FER crossings using one shared physical-frame bootstrap."""
143:                    left_censored_draws=int(np.isneginf(b.lower[1:]).sum()),
144:                    right_censored_draws=int(np.isposinf(b.upper[1:]).sum()),
196:    censored_frac = float(np.mean(~(np.isfinite(per_draw.lower[1:]) & np.isfinite(per_draw.upper[1:]))))
206:        censored_draw_fraction=censored_frac,
222:    censored_frac = float(np.mean(~(np.isfinite(diff.lower[1:]) & np.isfinite(diff.upper[1:]))))
229:        censored_draw_fraction=censored_frac,
296:        # Point argmin on upper bound then lower bound (handles right-censoring cleanly)
REMOTE_ROWS_MD5.txt
RESULTS.md
STATUS
gate.json
gates.log
gates_cpu.txt
main.log
main_cpu.txt
resume.log
resume_cpu.txt
summary.json
timing.log
timing_cpu.txt
timing_summary.json

 succeeded in 0ms:
   737	    print(f'Analyzing Part A ({int(pA_seen.sum())} keys, {trig_count} triggered, seed={BOOT_SEED})...', flush=True)
   738	    partA_out = analyze_partA(fail_by_arm, include_cd2e8, stageA2.crossing, diag_stats)
   739	
   740	    if enforce_cpu_cap:
   741	        final_cpu = sf._used_cpu_seconds()
   742	        if final_cpu >= BUDGET_CAP_SEC:
   743	            print(f'STOPPED_BUDGET after Part A analysis ({final_cpu/3600:.3f} core-hours)', flush=True)
   744	            sys.exit(BUDGET_EXIT_CODE)
   745	        runtime_info = dict(
   746	            runtime_info,
   747	            partA_analysis_cpu_hours=max(0.0, final_cpu / 3600.0 - runtime_info['partA_workers_core_hours']),
   748	            partA_total_core_hours=final_cpu / 3600.0,
   749	            partA_wall_seconds=(time.monotonic() - wall_start) if wall_start is not None else runtime_info['partA_wall_seconds'],
   750	        )
   751	
   752	    results = dict(
   753	        _argv=sys.argv,
   754	        _config=dict(
   755	            freeze_commit=freeze_commit,
   756	            python_executable=sys.executable,
   757	            own_md5=own_md5(),
   758	            gate_md5=gate_md5,
   759	            partA_rhos=list(PARTA_RHOS),
   760	            include_cd2e8=include_cd2e8,
   761	            partA_frames=[PARTA_FRAMES[0], PARTA_FRAMES[-1]],
   762	            partA_triggered_keys=trig_count,
   763	            raw_output_dir=str(raw_dir),
   764	            raw_rows_md5=raw_md5,
   765	            sameframe_hg_manifest_sha256=SAMEFRAME_HG_MANIFEST_SHA256,
   766	        ),
   767	        gates=dict(
   768	            all_passed=gate['all_passed'],
   769	            selected=gate['selected'],
   770	            G1_keys=gate['G1']['keys_checked'],
   771	            G2_keys=gate['G2']['keys_checked'],
   772	            G3_projected_hours=gate['selected']['projected_hours_with_margin'],
   773	        ),
   774	        runtime=runtime_info,
   775	        partA=partA_out,
   776	        timing=None,
   777	    )
   778	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
   779	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
   780	    print(
   781	        f'PARTA_DONE P1_prime={partA_out["primary_P1_prime"]["verdict"]} '
   782	        f'point={partA_out["primary_P1_prime"]["point_db"]:.4f} '
   783	        f'ci={partA_out["primary_P1_prime"]["ci95_db"]} '
   784	        f'cpu_hours={runtime_info["partA_total_core_hours"]:.4f}',
   785	        flush=True,
   786	    )
   787	
   788	
   789	def cmd_run_partA(args):
   790	    print(sys.executable, flush=True)
   791	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   792	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   793	    ar.check_thread_env()
   794	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
   795	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
   796	    if not 1 <= args.workers <= 32:
   797	        raise ValueError('workers must be in 1..32')
   798	
   799	    out_dir = args.out.resolve()
   800	    raw_dir = out_dir / 'raw'
   801	    raw_dir.mkdir(parents=True, exist_ok=True)
   802	    if list(raw_dir.glob('partA_shard*.jsonl*')):
   803	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
   804	
   805	    gate_bytes = (out_dir / 'gate.json').read_bytes()
   806	    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
   807	    gate = json.loads(gate_bytes.decode('utf-8'))
   808	    if not gate.get('all_passed') or not gate.get('selected'):
   809	        raise RuntimeError('Refusing to run without passing gate.json')
   810	    live_own = own_md5()
   811	    verify_freeze_commit_if_git(args.freeze_commit, live_own)
   812	    if gate['_config']['own_md5'] != live_own:
   813	        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
   814	
   815	    include_cd2e8 = bool(gate['selected']['include_cd2e8'])
   816	    wall_start = time.monotonic()
   817	    verify_all_archives()
   818	    C, _, _, helpers = sf.load_stage_runtime()
   819	    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
   820	        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
   821	    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
   822	        raise RuntimeError('p1_source_md5 mismatch vs gate.json')
   823	
   824	    stageA_base = sf.load_stageA_base(PARTA_RHOS)
   825	    trig_by_frame: dict[int, list[tuple[str, int, int, int, int, int]]] = {}
total 152
drwxr-xr-x@   8 guoyikun  staff    256 Nov 25 00:54 .
drwxr-xr-x@ 105 guoyikun  staff   3360 Nov 25 00:53 ..
-rw-r--r--@   1 guoyikun  staff   9359 Nov 25 00:53 PROTOCOL.md
drwxr-xr-x@   4 guoyikun  staff    128 Nov 25 00:54 __pycache__
-rwxr-xr-x@   1 guoyikun  staff   3769 Nov 25 00:53 launch.sh
drwxr-xr-x@   3 guoyikun  staff     96 Nov 25 00:54 reviews
-rw-r--r--@   1 guoyikun  staff  54640 Nov 25 00:53 sameframe_cd2.py
-rw-r--r--@   1 guoyikun  staff   2842 Nov 25 00:53 test_sameframe_cd2.py

exec
/bin/zsh -lc "rg -n '"'^def (load|crossing|f0_state|run_branch|decoded)|''^(ARMS|RHOS|SNRS|FRAMES)|numerical_fallback|r1_check|r1_app'"' stageA*.py; ls out" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121
 succeeded in 0ms:
stageA3.py:20:RHOS = (100, 150, 200)
stageA3.py:21:SNRS = stageA2.SNRS
stageA3.py:23:ARMS = tuple(f's{s:03d}' for s in SIGMAS)
stageA3.py:24:FRAMES_PER_SHARD, WORKERS = 5, 32
stageA.py:22:FRAMES = range(41000, 41400)
stageA.py:24:RHOS = (50, 100, 150, 200, 250, 300)
stageA.py:25:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
stageA.py:26:ARMS = ('base', 'delay')
stageA.py:27:FRAMES_PER_SHARD = 5
stageA.py:184:def crossing(fer):
stageA2.py:22:RHOS = (50, 100, 150, 200)
stageA2.py:23:SNRS = (200, 250) + stageA.SNRS
stageA2.py:24:ARMS = ('full', 'ldop')
stageA2.py:25:FRAMES_PER_SHARD, WORKERS = 5, 32
stageA2.py:158:def crossing(fer, snrs):
stageA2.py:170:def load(out, arms, rhos, snrs):
stageA4.py:25:FRAMES = range(41000, 41100)
stageA4.py:26:RHOS = (100, 150, 200)
stageA4.py:27:SNRS = (300, 400, 500)
stage0.json
stage0b.json
stageA
stageA2
stageA2_gate.json
stageA3
stageA3_gate.json
stageA4
stageA4_gate.json
stageA_gate.json

exec
/bin/zsh -lc "sed -n '1,90p' AGENTS.md; sed -n '1,60p' .trellis/workflow.md; ls -a .trellis/.runtime; rg -n 'deinlab|/dev/shm' .trellis/spec -g '*.md' -m 2" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

- 流程从简：只做必要检查，避免重复审查和过度文档化，尽快执行并汇报结果；服务器规则照常严格遵守。
- 记录去处（结果、线索、预测、待办写在哪）以项目 `CLAUDE.md` 的"记录系统"表为准；Codex 同样遵守，不另建记录文件。

## 子代理使用与上下文复用（2026-10-28 更新）

- 主会话负责一次性加载 Trellis 生命周期、当前任务及服务器规则。子代理不重复运行 trellis-start、get_context.py、task.py current，不重新分类或创建任务。
- 每次分派提供紧凑交接：任务/CSV 路径、子任务目标、文件所有权、验收条件、必需约束与待读文件。已注入内容不再读一遍；缺少具体约束时只补读对应文件或向主会话索取。
- 同一子代理优先复用；follow-up 只发送变化、证据与下一步，子代理保留已读上下文。新代理仍须获得必要代码规范和科学/服务器安全边界，不把未读取的内容谎报为已加载。
- 是否委派及模型选择遵循全局 Personal Agent Rules（唯一来源：`~/projects/personal-ai-workflow/templates/personal/personal-rules.md`）：默认主会话推进，Trellis 的实现与独立检查也按需委派，拿不准先问 Eric；确需 Codex 子代理时默认用 GPT-6.1 Sol。已有代理按当前工作收尾，保留前任代码、结果、审计记录；不因换模型重新仿真。

## GitHub 只读镜像（2026-10-13）

- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `trans/tcom-main` 已提交的本目录，排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 按需同步：仅当用户明确说「推 GitHub / 同步镜像」时，先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得主动推送，不得把 vault 本身推到该仓库。
# Development Workflow

---

## Core Principles

1. **Plan before code** — figure out what to do before you start
2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
3. **Persist everything** — research, decisions, and lessons all go to files; conversations get compacted, files don't
4. **Incremental development** — one task at a time
5. **Capture learnings** — after each task, review and write new knowledge back to spec

---

## Trellis System

### Developer Identity

On first use, initialize your identity:

```bash
python3 ./.trellis/scripts/init_developer.py <your-name>
```

Creates `.trellis/.developer` (gitignored) + `.trellis/workspace/<your-name>/`.

### Spec System

`.trellis/spec/` holds coding guidelines organized by package and layer.

- `.trellis/spec/<package>/<layer>/index.md` — entry point with **Pre-Development Checklist** + **Quality Check**. Actual guidelines live in the `.md` files it points to.
- `.trellis/spec/guides/index.md` — cross-package thinking guides.

```bash
python3 ./.trellis/scripts/get_context.py --mode packages   # list packages / layers
```

**When to update spec**: new pattern/convention found · bug-fix prevention to codify · new technical decision.

### Task System

Every task has its own directory under `.trellis/tasks/{MM-DD-name}/` holding `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, optional `research/`, and context manifests (`implement.jsonl`, `check.jsonl`) for sub-agent-capable platforms.

```bash
# Task lifecycle
python3 ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]
python3 ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
python3 ./.trellis/scripts/task.py current --source      # show active task and source
python3 ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
python3 ./.trellis/scripts/task.py archive <name>        # move to archive/{year-month}/
python3 ./.trellis/scripts/task.py list [--mine] [--status <s>]
python3 ./.trellis/scripts/task.py list-archive

# Code-spec context (injected into implement/check agents via JSONL).
# `implement.jsonl` / `check.jsonl` are seeded on `task create` for sub-agent-capable
# platforms; the AI curates real spec + research entries during planning when needed.
python3 ./.trellis/scripts/task.py add-context <name> <action> <file> <reason>
python3 ./.trellis/scripts/task.py list-context <name> [action]
python3 ./.trellis/scripts/task.py validate <name>

.
..
sessions
update-check-claude_020c3dc0-58dd-4eb3-9df5-b0cb1732c022.marker
update-check-claude_027913cf-ec11-48fd-98ad-5f07dc6b8b7f.marker
update-check-claude_040c7d8d-c74c-4c2e-9e98-283134234e5d.marker
update-check-claude_0652265a-765c-4549-aa46-45b0061559e9.marker
update-check-claude_0653d486-340c-40f8-adcc-8995b67d4b62.marker
update-check-claude_072bf7af-6536-49c4-8062-b89c39388cf2.marker
update-check-claude_07712de2-9ca0-4895-8c21-dfa51ae35840.marker
update-check-claude_07d81109-6cb6-4a8c-bb34-a27191ccd604.marker
update-check-claude_09398837-3505-46ce-969e-fdf989cc7357.marker
update-check-claude_09c7c687-1391-480d-8fdf-c5e7af35bc9d.marker
update-check-claude_0a967c55-7f9a-4d28-ac75-4575b9f91285.marker
update-check-claude_0ae939dc-49cc-4dc8-9179-dbf0ff74bccc.marker
update-check-claude_0b82758b-8666-49ee-a412-4ba978c94d7c.marker
update-check-claude_0c2406c0-4a02-4c33-a88a-fdb0aedab52a.marker
update-check-claude_0cfbd4cc-16f6-4620-a6f7-e416ef0d36ff.marker
update-check-claude_0f3d4613-6120-4e7e-970f-2ae1003ed8a7.marker
update-check-claude_0f623c58-0bf3-410d-ac38-32e3bfd2510d.marker
update-check-claude_1022dec9-885d-4f2b-ac26-aa47acdfcbcb.marker
update-check-claude_111c7a1e-cef0-4f06-b49b-1a0ee9c3e5d7.marker
update-check-claude_11b58612-28ed-4c95-8baa-1316e030c7b8.marker
update-check-claude_123fd0ef-deaf-48be-a863-f44cd57b8a40.marker
update-check-claude_1287d68e-c504-4905-8d28-69c063deeaa0.marker
update-check-claude_12e81fd4-3f66-4cac-afe7-c3d386faba8a.marker
update-check-claude_15757c4a-07ec-4270-9641-de49e21751be.marker
update-check-claude_180e6709-9b03-4efc-ab09-e4e059fafdd7.marker
update-check-claude_1a65c9e2-0265-459d-a16e-e46b9f54768f.marker
update-check-claude_1b5c9963-082d-4594-ae4a-b760062add71.marker
update-check-claude_1d5f2723-b9a7-4fab-8dad-cf9f5ba51c6d.marker
update-check-claude_1d997342-861e-44e8-af4a-8d6289e53d85.marker
update-check-claude_1df0c290-bcb2-4315-bf4d-01fb4e5d3c9a.marker
update-check-claude_20de4e9c-2fc3-4e34-97bb-5cddfcb0a573.marker
update-check-claude_2431feb8-bd32-45cf-8e26-c774a31921c9.marker
update-check-claude_24451300-a340-467f-b29e-d81fc5160ae3.marker
update-check-claude_2987487c-1c15-42e8-8077-0d03dc1024a8.marker
update-check-claude_2b530201-94bc-47db-99ce-802ad8bb96af.marker
update-check-claude_2ba97862-e7d3-4dfd-a302-138ad0c99dbe.marker
update-check-claude_2bba4485-a1f9-4a98-9c90-1b3ad66dd547.marker
update-check-claude_2e328a8f-eb97-4126-91e5-613a4563bf5e.marker
update-check-claude_321105a2-1baa-4f3c-a289-c83aa8d2d47c.marker
update-check-claude_333e43d8-ae97-4776-9ee4-34454be9c951.marker
update-check-claude_3361e9a3-b931-4b0b-8b14-2bd1986913ca.marker
update-check-claude_336e27f9-13b1-44ae-8034-649b5ab0748c.marker
update-check-claude_344cf691-0753-4ae6-b9f3-d138a0afd8fd.marker
update-check-claude_34ac466e-70f3-43dc-bed7-2b9c94e02578.marker
update-check-claude_35388521-876f-4d57-be81-3511f7bbf368.marker
update-check-claude_387d7f50-4392-4b19-9bc1-a7a787acd6f5.marker
update-check-claude_38e6414a-e091-46e8-b77b-cc65cee4b35c.marker
update-check-claude_3b8164e5-1514-41a6-94d4-6a75e9336cde.marker
update-check-claude_3be16b95-d225-40c9-a512-f07e18c77945.marker
update-check-claude_3d2a447e-00f7-4fa3-8e54-0f79a4a506e4.marker
update-check-claude_3f55338f-342b-45fc-8d94-c72d1e6079c0.marker
update-check-claude_404c184e-68e6-4300-9b9b-a88c4ceb4567.marker
update-check-claude_40da0f68-b57a-46e5-9eab-58993499949f.marker
update-check-claude_416ce653-9483-4a68-9805-d7c8db06bbe8.marker
update-check-claude_443d862c-adc8-453e-99d3-bf4be4686464.marker
update-check-claude_4488cbc0-36fa-4e05-a725-1a4ed06fdde6.marker
update-check-claude_466647fa-fc13-45c9-b940-c791defbbbdf.marker
update-check-claude_47d44e10-9059-4f61-b61b-6398f9c8e7b0.marker
update-check-claude_4ce6377f-dbb6-4c33-adbf-3b6931d2e404.marker
update-check-claude_4e5cc91e-864d-4310-8726-6a68fb873b1c.marker
update-check-claude_50c05802-43d3-49b2-b874-ade57e359b4a.marker
update-check-claude_512809b5-35df-4ef1-b802-9b761d49ff5c.marker
update-check-claude_516adc32-c2f7-44c9-b75b-8ae5a549d7cf.marker
update-check-claude_52840c72-4d44-4d57-b385-d149c08df954.marker
update-check-claude_52853bfa-a46b-4616-88da-9505e3d5df2a.marker
update-check-claude_52f69e78-472f-4908-9d8a-6f3c511d7d94.marker
update-check-claude_5951db9f-66f5-4dd8-becf-5de102e4df14.marker
update-check-claude_596cc8da-d84d-4d07-9b5c-56aeaac65578.marker
update-check-claude_5c33c71f-debd-40d5-a69b-bd2227742eee.marker
update-check-claude_5c458b56-03f7-4760-a81c-fa284a11d0b1.marker
update-check-claude_5dd5604e-b6d4-4b7f-9932-aa4cd3e4f1eb.marker
update-check-claude_5df1404c-b6be-47ee-b30c-82af1a7030bf.marker
update-check-claude_5e26079f-f3a1-4e5b-ba0e-07e94f555ce4.marker
update-check-claude_5e43a5c6-24f5-4007-aae3-40dd3d81cb92.marker
update-check-claude_5f47a485-f591-456f-adf5-e853d6487dc9.marker
update-check-claude_5fb8daa2-9aa0-4129-aaa0-942c18af5529.marker
update-check-claude_60bac1fd-82f5-4d74-96b1-9d9953278b15.marker
update-check-claude_60d5eebf-4d3f-49d5-96e9-711cd542b550.marker
update-check-claude_61ded872-a27c-4203-91e6-b62084928ced.marker
update-check-claude_634ff841-4255-4f76-85d9-71af50b79f61.marker
update-check-claude_645b0457-2ef0-4781-9ca5-d27608d43fed.marker
update-check-claude_64bdf000-ef85-4a9b-8a8f-8c1cc28dec5d.marker
update-check-claude_65ac98ec-795f-4d22-b308-f260da2dc9fb.marker
update-check-claude_65dec62c-aa0d-4096-854d-824d6f100717.marker
update-check-claude_65e2571b-0e5d-4c22-b025-61da58336280.marker
update-check-claude_65ebd572-2118-46d6-a8b3-05a09578c620.marker
update-check-claude_67a9aad4-42c4-4b7b-8f91-bbf2fdd67e53.marker
update-check-claude_68d906a3-ddd6-4373-9576-b55a49e98473.marker
update-check-claude_6951fc3f-6131-4ba9-a6ae-d10c8700924b.marker
update-check-claude_6f4095f6-ae1f-47f6-81f4-c8135c806b70.marker
update-check-claude_703896a7-55c9-48c1-8bc8-34e6e167c60e.marker
update-check-claude_71f3f94f-6cd6-479d-8092-fe5ecdd9f9ab.marker
update-check-claude_7275a050-a5a7-4195-9626-1a97506b20f8.marker
update-check-claude_7284bd7d-7e19-4fa4-8628-416af83e61aa.marker
update-check-claude_752e8392-b7b7-45e5-bc22-c51071b989f3.marker
update-check-claude_75a6de58-aabd-4f90-9fc9-886a3fa69932.marker
update-check-claude_75bd7a6e-d629-4152-ba15-e1a1dafda888.marker
update-check-claude_76c1f0fd-e544-4701-8441-7ad247442ddc.marker
update-check-claude_7720af2b-7f76-43fa-bc35-4be63053903b.marker
update-check-claude_77a81aca-f1ad-428b-bb48-3a3b52b12a57.marker
update-check-claude_783f5a6a-91e4-489c-bb8a-fca5dae2819d.marker
update-check-claude_7b167cc9-1556-4770-8f92-e52080fdcc0c.marker
update-check-claude_7b64d07f-ec10-4a84-94d4-b2a104cdb5dc.marker
update-check-claude_7dac8970-effc-452a-997d-c9a8716ccfb9.marker
update-check-claude_813ab0a9-80b3-41df-991b-4af5495804ef.marker
update-check-claude_84272a28-9582-49fd-9a89-fcc3ad74c2d1.marker
update-check-claude_879dfe6d-8f6d-4856-be39-60974aee094d.marker
update-check-claude_90d93b86-c1c8-48a6-951c-2db15e56d2c5.marker
update-check-claude_92b4ee7f-b30e-408a-a884-9f645759e5b0.marker
update-check-claude_94ea8c8a-ea64-4fc9-8914-2a51d91ea967.marker
update-check-claude_97823d74-1560-472d-8041-4b13aa5e17bb.marker
update-check-claude_98192468-d271-43e1-a402-9bab5425a661.marker
update-check-claude_9941f35b-03aa-4a3c-810f-a55240381243.marker
update-check-claude_99569d01-14b2-4372-aa69-28b1d444f3f3.marker
update-check-claude_9bc2c342-8038-4232-9ce9-9330c2b31182.marker
update-check-claude_9c6ecf89-cb1a-4a2f-9444-79865d68b523.marker
update-check-claude_9c75b327-0c70-457f-9aa9-f323afc7d06c.marker
update-check-claude_9cb21066-ee58-47fd-b0fd-ba16d82ddd9a.marker
update-check-claude_9d60f282-cd4c-405c-b9a9-6d5646c2821b.marker
update-check-claude_a05b8225-25ce-444d-a563-0dec31cf9160.marker
update-check-claude_a07f60f9-d451-40d8-9a7f-70ce3a334f29.marker
update-check-claude_a2df2b10-f1ef-44d1-b09f-c1b1dd16e2ae.marker
update-check-claude_a3dc1d54-ce81-4ecd-8d9f-90753fa55bb3.marker
update-check-claude_a3fc65b5-7467-48cf-8db8-81c6dd239105.marker
update-check-claude_a4c81ede-6ced-4a71-80bf-714a5e40d381.marker
update-check-claude_a7e48af6-08d4-42e5-9661-0f4ce5b5173c.marker
update-check-claude_a959e847-fbfe-4027-a860-fcf549d7d291.marker
update-check-claude_a9fe2c75-b3e3-4be6-9f55-8180554b6b81.marker
update-check-claude_aaf11cc3-c9e2-4412-981c-d591e18136c4.marker
update-check-claude_ab414ab6-d3e5-460b-86e3-0200d272090d.marker
update-check-claude_acdcbf30-0e6a-4600-a382-31d6f91ebfba.marker
update-check-claude_af6d7344-a989-4dac-bda5-4f3416e15fca.marker
update-check-claude_b30ae848-27d6-40d1-b4b4-41aa65a00a51.marker
update-check-claude_b5dbb1ce-1cfa-4ff8-bf35-95d067834c69.marker
update-check-claude_b7682795-5999-47ae-a0f0-e659a3b39528.marker
update-check-claude_b97e21ed-f425-4bb3-a1ac-57e9cb478f07.marker
update-check-claude_baf4eb08-e60b-476d-b709-3eeba5db54e5.marker
update-check-claude_bc06362a-b45d-4f66-88d3-2131c0626b2e.marker
update-check-claude_bc9f9b75-fdf4-427f-bab1-e9cc849a27df.marker
update-check-claude_bcc3d08b-5802-4ae7-a8c1-18fb08ab715c.marker
update-check-claude_bd9bb2a4-5ccf-407b-96b1-f02e5fe6ae22.marker
update-check-claude_bde6e689-b056-4fb6-a4de-35cb8a1e349d.marker
update-check-claude_c05d4f4c-63e6-4ff7-9a5d-dee5d5f46dc5.marker
update-check-claude_c106f9ca-5d5d-487a-9b7a-6a8ef46b78eb.marker
update-check-claude_c11aa1b8-6ea8-498c-a817-7884d8891055.marker
update-check-claude_c158e7dd-261a-4ec5-a2a1-bd6adebe8ca4.marker
update-check-claude_c190e1b1-ff5e-4b0f-b1d2-81090a97a9b4.marker
update-check-claude_c24c6694-11c0-4fe2-b8c8-9c61bc3162ce.marker
update-check-claude_c3665cbc-97ab-433a-ac8d-c1edd5dc8e72.marker
update-check-claude_c6f84454-385f-49fe-af2c-7d5e36c30d5e.marker
update-check-claude_c7a195a2-259a-4f1d-a02f-98c22646ecc5.marker
update-check-claude_c9ae3782-2eca-4757-8d00-c53370d908df.marker
update-check-claude_ca509c52-d9ca-4bcb-9573-b1d93d2679bd.marker
update-check-claude_cbd60135-df42-438f-ab2b-fabb5ee17465.marker
update-check-claude_cc4d94f8-152b-4c2c-aed3-d951791277b6.marker
update-check-claude_cc7c7691-66a1-47b0-8985-cdc57029dcde.marker
update-check-claude_ce997bff-28a8-4f1d-8ced-bc61c6882c95.marker
update-check-claude_d0f79571-42e3-4d16-98ca-b87cb95cbd34.marker
update-check-claude_d16ef72b-b8de-441c-a0d8-44f083dd4679.marker
update-check-claude_d1fe7a35-4e4b-406f-9f2f-0025c6af4ece.marker
update-check-claude_d2747433-2601-4e6e-aa4d-47bbca477f13.marker
update-check-claude_d3da7f78-e9eb-471a-a6ab-05a634fbdac2.marker
update-check-claude_d44dbced-77d6-4eb5-af35-901535a4d11e.marker
update-check-claude_d5eaa866-75b2-4522-925c-1d2a0e757d76.marker
update-check-claude_d653a80b-dfc8-481e-b464-d5f42c707ebe.marker
update-check-claude_d67e9249-a9cb-4c61-a088-1fa975eb4719.marker
update-check-claude_d6c2f0ac-70e5-456a-99d6-b2a974f77eb5.marker
update-check-claude_d9deac01-8d16-4c56-a01a-80adc495e34c.marker
update-check-claude_da2e3930-c18d-4f15-9c42-5ffead3dcfd5.marker
update-check-claude_dab53947-09ea-425a-b6e8-7239768dbe86.marker
update-check-claude_dbfd3e20-a45b-47f7-a5df-a9d902a8b6fb.marker
update-check-claude_df70db89-9733-4fef-a26e-5c760858ac02.marker
update-check-claude_e1a7566a-b726-4faa-bd1f-ffde40a285d4.marker
update-check-claude_e25a6ee6-79b7-4814-b70b-514f6ac84e78.marker
update-check-claude_e3b40fdb-320c-4e7c-8480-35d2d059970e.marker
update-check-claude_e4025871-a0c8-4157-9e4d-40f933700122.marker
update-check-claude_e5cdf072-cffc-4aaa-9b70-5970f987bec6.marker
update-check-claude_e69ecd0f-aad9-4b55-a071-ea407bae445b.marker
update-check-claude_e7723957-f3cd-4603-86e6-300903df6914.marker
update-check-claude_e8bfcde3-3ed6-43bf-81b9-c05a969f0684.marker
update-check-claude_e9298694-a56b-46d1-8c7e-2e890f6f92c1.marker
update-check-claude_eb31c388-a3e5-43f5-a506-1e0c04b8f1a4.marker
update-check-claude_ec8e3bf0-049e-4ebd-8e77-f9f9807662a3.marker
update-check-claude_eff6499c-2202-409e-918e-dea509ba93d8.marker
update-check-claude_f15a7964-e8e6-4be3-9e06-48c0ac83a93d.marker
update-check-claude_f22be84f-b8d0-40b0-858b-e70e656fdc7d.marker
update-check-claude_f3e1abe9-cbd3-4b72-9693-2d9640b7a320.marker
update-check-claude_f4296592-1e00-4ee0-8130-c404572c07ed.marker
update-check-claude_f4cc3f80-b132-4a52-84e2-6001e164ff7f.marker
update-check-claude_f559e588-488b-44ce-83e5-2c7765cee800.marker
update-check-claude_f593bee7-6c25-41ea-a9a1-8a5a1847ed0d.marker
update-check-claude_f73b724a-8404-4a2e-acaf-89e192ee989f.marker
update-check-claude_f80bc9f8-8471-4531-a727-a0506c6aba36.marker
update-check-claude_fb01203e-1964-4fa1-8af8-f5d377380db4.marker
update-check-claude_fb3b582e-cdf4-48c8-9167-5ffad6f7adc7.marker
update-check-claude_fb595493-31e2-4672-9547-7fde9551076c.marker
update-check-claude_fb95ad6a-8246-47aa-8313-5a404b78aab1.marker
update-check-claude_fbd427e0-f747-40b9-a57a-a247c98f2d62.marker
update-check-claude_fc19a130-d9f3-4f50-9e06-39390ce35770.marker
update-check-claude_fcea44fb-6124-4ef0-861a-ef28ebd65b0d.marker
update-check-claude_fe503d29-4a70-40c7-9e4d-c76ec1360ec7.marker
update-check-claude_fe6f9eef-d1e0-430d-935b-865522f5741d.marker
update-check-codex_01a071db-1910-7ba1-8650-9599767c12df.marker
update-check-codex_01a07421-9eb1-7b53-bd41-9c8f04d88198.marker
update-check-codex_01a0749d-19ed-7d61-9287-6a819d468864.marker
update-check-codex_01a07bba-b722-7313-8f78-13a068bcc8ad.marker
update-check-codex_01a0804b-73b8-7913-91f2-3dbb4de58e08.marker
update-check-codex_01a08118-e24d-7f32-96df-5748ebc058d7.marker
update-check-codex_01a08add-2b68-7c93-80f8-a34bbd4673f9.marker
update-check-codex_01a09043-1ed4-7251-b41b-317fff7089a8.marker
update-check-codex_01a0947a-5cb2-7863-b383-e6adee4eabdf.marker
update-check-codex_01a094a0-d161-7ac1-82ce-728c34c615e9.marker
update-check-codex_01a0967d-ce96-7803-a4d8-97386893d991.marker
update-check-codex_01a0987b-e395-7560-805a-3c1a81bf733c.marker
update-check-codex_01a09a35-ba2f-7de3-a2b2-3f152141f2c9.marker
update-check-codex_01a09df0-f011-7243-b163-d238ec59cd50.marker
update-check-codex_01a09df6-3c30-7f32-a797-9a1639698743.marker
update-check-codex_01a09e01-8242-7403-bc9c-dd867dd4a73e.marker
update-check-codex_01a09e63-f42a-7453-b9e5-341827df0063.marker
update-check-codex_01a09f4b-8f49-7f60-bb58-abebe4a02ee4.marker
update-check-codex_01a09f7b-714f-7b91-b500-b9d30aa2aaa9.marker
update-check-codex_01a0a06b-20f3-7fc2-a8ee-6c4547735fe4.marker
update-check-codex_01a0a074-3a5a-7633-8f70-b8c67ee36af9.marker
update-check-codex_01a0a34d-d520-7552-a3d6-f6f545886b62.marker
update-check-codex_01a0a5a0-7304-7313-a4d9-460abc86d922.marker
update-check-codex_01a0ae1a-44b9-77d1-b344-7ba69889f209.marker
update-check-codex_01a0c1d9-d092-70b1-9536-7112676570a5.marker
update-check-codex_01a0c707-d89d-7e02-bbed-5724996cfa31.marker
update-check-codex_01a0c893-394d-7e73-9994-ca6ded334bbd.marker
update-check-codex_01a0cddf-699f-7752-8b21-fc2a9ff0023f.marker
update-check-codex_01a0f27b-e6d2-74b1-be7c-5f2995ea31dc.marker
update-check-codex_01a1007e-b82a-70c0-bcb2-fec08e9b17cc.marker
update-check-codex_01a1050f-6f58-7f70-a176-82412e47ce0f.marker
update-check-codex_01a13824-86ea-7163-b58e-254d1006b3d2.marker
update-check-codex_01a13e4d-4a9a-7422-a10c-35b928a24106.marker
update-check-codex_01a145f2-18fb-7ec0-ab17-02f0bb258dcd.marker
update-check-codex_01a148b2-837a-72c2-a685-3719b0f6ddf8.marker
update-check-codex_01a14ae6-b956-7d61-997e-eed79edba150.marker
update-check-codex_01a15890-3bd9-7e52-a8e6-98319932f8a9.marker
update-check-codex_01a16c24-e555-7412-bea6-e001b1d05247.marker
update-check-codex_01a181db-4c5f-7e12-9a0a-5a9d1cceb9cc.marker
update-check-codex_01a1be2b-a7bd-72f1-a53b-6a417f86aa2f.marker
update-check-codex_01a1c497-e07f-7992-9620-d3de9e3860cc.marker
update-check-codex_01a1c814-c66d-7ed2-a595-bb3d95f4c1b5.marker
update-check-codex_01a1c8cb-78aa-7e02-8b2c-e44d65398f4c.marker
update-check-codex_01a1c8da-1df8-78a1-8295-d01e1dcfa8d6.marker
update-check-codex_01a1ea38-a19b-7710-8d13-3ec7ac28b467.marker
update-check-codex_01a1ed69-1fee-79b1-9b85-488414ad6229.marker
update-check-codex_01a203f4-514a-7302-bca7-47b0914d80e9.marker
update-check-ppid-82064.marker
update-check-ppid-86554.marker
.trellis/spec/backend/research-diagnostics.md:955:On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
.trellis/spec/backend/research-diagnostics.md:1024:deinlab, record its SSH root and verify it before deleting task-created local

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '42,91p;150,335p;482,504p;795,918p'; nl -ba experiments/data_pilot_fer_20261121/stageA2.py | sed -n '154,211p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    42	P2_THRESHOLD_DB = 0.2
    43	
    44	ARCHIVE_MANIFESTS = {
    45	    'stageA': (DATA_PILOT_DIR / 'out' / 'stageA', '30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68'),
    46	    'stageA2': (DATA_PILOT_DIR / 'out' / 'stageA2', '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354'),
    47	    'stageA3': (DATA_PILOT_DIR / 'out' / 'stageA3', '6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a'),
    48	    'rho_sweep': (RHO_SWEEP_DIR / 'out' / 'main_20261119', ar.RHO_ARCHIVE_MD5_SHA256),
    49	    'huang': (HUANG_DIR / 'out', 'b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc'),
    50	}
    51	OWN_FILES = ('PROTOCOL.md', 'sameframe.py', 'test_sameframe.py', 'launch.sh')
    52	WORKERS = 24
    53	BUDGET_CAP_HOURS = 16.0
    54	BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
    55	COST_MARGIN = 1.3
    56	OVERHEAD_HOURS = 0.25
    57	BUDGET_EXIT_CODE = 124
    58	N_SHARDS = 24
    59	CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100
    60	
    61	
    62	def own_md5() -> dict[str, str]:
    63	    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}
    64	
    65	
    66	def verify_manifest(name: str) -> dict[str, str]:
    67	    base_dir, expected_sha = ARCHIVE_MANIFESTS[name]
    68	    manifest = base_dir / 'REMOTE_ROWS_MD5.txt'
    69	    got_sha = ar.sha256_file(manifest)
    70	    if got_sha != expected_sha:
    71	        raise RuntimeError(f'{name} manifest SHA-256 mismatch: {got_sha} != {expected_sha}')
    72	    raw_dir = base_dir / 'raw' if name == 'huang' else base_dir
    73	    out: dict[str, str] = {}
    74	    for line in manifest.read_text(encoding='utf-8').splitlines():
    75	        if not line.strip():
    76	            continue
    77	        digest, fname = line.split()
    78	        p = raw_dir / fname
    79	        if not p.is_file():
    80	            raise FileNotFoundError(f'Missing archive shard {p}')
    81	        actual = ar.md5_file(p)
    82	        if actual != digest:
    83	            raise RuntimeError(f'Archive shard MD5 mismatch {p}: {actual} != {digest}')
    84	        out[fname] = actual
    85	    disk_shards = {p.name for p in raw_dir.glob('rows_shard*.jsonl*')}
    86	    if disk_shards != set(out):
    87	        raise RuntimeError(
    88	            f'{name} shard set mismatch on disk vs manifest: extra={sorted(disk_shards - set(out))}, '
    89	            f'missing={sorted(set(out) - disk_shards)}'
    90	        )
    91	    return out
   150	        cd.reopen_geometry.__name__,
   151	        cd.reopen_geometry.__defaults__,
   152	    )
   153	    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen_e8)
   154	
   155	
   156	def load_stage_runtime():
   157	    """Verify frozen MD5s first, then initialize via stageA.setup() and build hs_arms helpers."""
   158	    extra_md5 = ar.verify_frozen_extra_md5()
   159	    import stageA  # noqa: E402
   160	    import stageA2  # noqa: E402
   161	
   162	    C = stageA.setup()
   163	    stage3 = C['stage3']
   164	    # Register A1e8 (max_edits=8, local_passes=2, full Gamma) at runtime without modifying frozen files
   165	    stage3.e1.ARM_SPECS['A1e8'] = dict(gamma_mode='full', max_edits=8, local_passes=2)
   166	    cd_e8 = _make_cd_e8_kernel(C['cd'])
   167	
   168	    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
   169	    from messages import moments
   170	    from physical import Channel
   171	    from twofft import time_refine
   172	
   173	    helpers = dict(
   174	        stage3=stage3,
   175	        cd=C['cd'],
   176	        cd_e8=cd_e8,
   177	        BaselineInitializer=BaselineInitializer,
   178	        Channel=Channel,
   179	        moments=moments,
   180	        time_refine=time_refine,
   181	        extra_md5=extra_md5,
   182	    )
   183	    return C, stageA, stageA2, helpers
   184	
   185	
   186	def run_cd_two_pass(
   187	    ctx,
   188	    helpers: dict[str, Any],
   189	    obs: dict[str, Any],
   190	    arrays: dict[str, Any],
   191	    truth: dict[str, Any],
   192	    *,
   193	    arm_spec: str,
   194	    expected_pass1: dict[str, Any] | None = None,
   195	) -> dict[str, Any]:
   196	    """Run 1-to-2-pass CODELAY local exchange with syndrome early stop (same inter-pass update as HG)."""
   197	    stage3 = helpers['stage3']
   198	    cd = helpers['cd_e8'] if arm_spec == 'A1e8' else helpers['cd']
   199	    ar._require_finite(arrays['r1_check'], f'{arm_spec}.p1.r1_check')
   200	    ar._require_finite(arrays['r1_app'], f'{arm_spec}.p1.r1_app')
   201	
   202	    br1 = stage3.e1.run_branch(ctx, cd, obs, arrays, arm_spec)
   203	    res1 = br1['result']
   204	    if bool(res1.diagnostics.get('numerical_fallback')):
   205	        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 1')
   206	    ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
   207	    ar._require_finite(br1['detector']['extrinsic'], f'{arm_spec}.p1.extrinsic')
   208	    dec1 = br1['decoder']
   209	    ar._require_finite(dec1['raw_check_extrinsic'], f'{arm_spec}.p1.raw_check_extrinsic')
   210	    ar._require_finite(dec1['raw_app'], f'{arm_spec}.p1.raw_app')
   211	    d1 = stage3.decoded(ctx, dec1, truth)
   212	    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))
   213	
   214	    if expected_pass1 is not None:
   215	        if d1['errors'] != int(expected_pass1['errors']) or d1['decoded_sha'] != expected_pass1['decoded_sha']:
   216	            raise RuntimeError(
   217	                f'{arm_spec} pass-1 mismatch vs archived CD: got {d1}, expected {expected_pass1}'
   218	            )
   219	
   220	    if syn1 == 0:
   221	        return dict(
   222	            errors=d1['errors'],
   223	            decoded_sha=d1['decoded_sha'],
   224	            syndrome=0,
   225	            passes_used=1,
   226	            pass1_errors=d1['errors'],
   227	            pass1_syndrome=0,
   228	            pass1_edits=len(res1.edits),
   229	            pass2_edits=0,
   230	            numerical_fallback=False,
   231	        )
   232	
   233	    arrays2 = dict(
   234	        r1_delays=np.array([int(p.delay) for p in res1.paths], dtype=int),
   235	        r1_dopplers=np.array([float(p.doppler) for p in res1.paths], dtype=float),
   236	        r1_gains=np.asarray(res1.gains, dtype=complex),
   237	        r1_check=dec1['raw_check_extrinsic'],
   238	        r1_app=dec1['raw_app'],
   239	    )
   240	    br2 = stage3.e1.run_branch(ctx, cd, obs, arrays2, arm_spec)
   241	    res2 = br2['result']
   242	    if bool(res2.diagnostics.get('numerical_fallback')):
   243	        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 2')
   244	    ar._require_finite(res2.gains, f'{arm_spec}.p2.gains')
   245	    ar._require_finite(br2['detector']['extrinsic'], f'{arm_spec}.p2.extrinsic')
   246	    dec2 = br2['decoder']
   247	    ar._require_finite(dec2['raw_check_extrinsic'], f'{arm_spec}.p2.raw_check_extrinsic')
   248	    ar._require_finite(dec2['raw_app'], f'{arm_spec}.p2.raw_app')
   249	    d2 = stage3.decoded(ctx, dec2, truth)
   250	    syn2 = int(ctx.hd.syndrome_weight(ctx, dec2['decoded']))
   251	
   252	    return dict(
   253	        errors=d2['errors'],
   254	        decoded_sha=d2['decoded_sha'],
   255	        syndrome=syn2,
   256	        passes_used=2,
   257	        pass1_errors=d1['errors'],
   258	        pass1_syndrome=syn1,
   259	        pass1_edits=len(res1.edits),
   260	        pass2_edits=len(res2.edits),
   261	        numerical_fallback=False,
   262	    )
   263	
   264	
   265	def load_stageA_base(rhos: tuple[int, ...] = PART1_RHOS) -> dict[tuple[str, int, int, int], dict[str, int]]:
   266	    """Load archived stageA arms.base (syndrome, f0_errors, errors) for requested rhos."""
   267	    base_dir = DATA_PILOT_DIR / 'out' / 'stageA'
   268	    out: dict[tuple[str, int, int, int], dict[str, int]] = {}
   269	    for p in sorted(base_dir.glob('rows_shard*.jsonl.gz')):
   270	        with gzip.open(p, 'rt', encoding='utf-8') as fh:
   271	            for line in fh:
   272	                r = json.loads(line)
   273	                rho = int(r['rho'])
   274	                if rho not in rhos:
   275	                    continue
   276	                k = (r['scenario'], rho, int(r['snr']), int(r['frame']))
   277	                b = r['arms']['base']
   278	                out[k] = dict(
   279	                    syndrome=int(b['syndrome']),
   280	                    f0_errors=int(b['f0_errors']),
   281	                    errors=int(b['errors']),
   282	                )
   283	    expected = len(PART1_FRAMES) * 2 * len(rhos) * len(PART1_SNRS)
   284	    if len(out) != expected:
   285	        raise RuntimeError(f'stageA base count mismatch: got {len(out)}, expected {expected}')
   286	    return out
   287	
   288	
   289	def _used_cpu_seconds() -> float:
   290	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   291	    return time.process_time() + ch.ru_utime + ch.ru_stime
   292	
   293	
   294	def _active_pids_cpu(pids: list[int]) -> float:
   295	    total = 0.0
   296	    for pid in pids:
   297	        try:
   298	            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
   299	            after = raw[raw.rfind(')') + 2:].split()
   300	            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
   301	        except OSError:
   302	            pass
   303	    return total
   304	
   305	
   306	def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
   307	    """File-IPC spawn worker pool (zero /dev/shm named semaphores)."""
   308	    n_workers = min(max_workers, max(1, len(items)))
   309	    buckets = [items[i::n_workers] for i in range(n_workers)]
   310	    mp_ctx = multiprocessing.get_context('spawn')
   311	    out_files = []
   312	    procs = []
   313	    for wi, bucket in enumerate(buckets):
   314	        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
   315	        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
   316	        in_f.write_text(json.dumps(bucket), encoding='utf-8')
   317	        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
   318	        p.start()
   319	        procs.append((wi, p))
   320	        out_files.append(out_f)
   321	    for wi, p in procs:
   322	        p.join()
   323	        code = p.exitcode
   324	        p.close()
   325	        if code != 0:
   326	            raise RuntimeError(f'Gate worker {tag}/{wi} exited with code {code}')
   327	    merged: list[tuple[int, Any]] = []
   328	    for wi, out_f in enumerate(out_files):
   329	        chunk = json.loads(out_f.read_text(encoding='utf-8'))
   330	        for pos, val in enumerate(chunk):
   331	            merged.append((wi + pos * n_workers, val))
   332	    merged.sort(key=lambda x: x[0])
   333	    return [v for _, v in merged]
   334	
   335	
   482	def _select_balanced_keys(
   483	    keys_by_stratum: dict[tuple[int, str], list[tuple[str, int, int, int]]],
   484	    per_stratum: int,
   485	) -> list[tuple[str, int, int, int, str]]:
   486	    """Select balanced U/G and interior SNR-quantile keys per (rho, band) deterministically."""
   487	    selected = []
   488	    for (rho, band), ks in sorted(keys_by_stratum.items()):
   489	        u_ks = sorted((k for k in ks if k[0] == 'U'), key=lambda k: (k[2], k[3]))
   490	        g_ks = sorted((k for k in ks if k[0] == 'G'), key=lambda k: (k[2], k[3]))
   491	        n_each = per_stratum // 2
   492	        picks = []
   493	        for pool in (u_ks, g_ks):
   494	            if len(pool) < n_each:
   495	                raise RuntimeError(f'Insufficient keys in stratum {(rho, band)}: {len(pool)} < {n_each}')
   496	            # Use interior quantiles (q = (i + 0.5) / n_each) so n_each=1 hits median and n_each=2 hits 25%/75%
   497	            idxs = [min(len(pool) - 1, int((i + 0.5) * len(pool) / n_each)) for i in range(n_each)]
   498	            picks.extend(pool[i] for i in idxs)
   499	        for s, r, snr, f in picks:
   500	            selected.append((s, r, snr, f, band))
   501	    return selected
   502	
   503	
   504	def cmd_gate(args):
   795	                        syndrome=hgint_out['HG']['syndrome'],
   796	                        passes_used=hgint_out['HG']['passes_used'],
   797	                    )
   798	                out_lines.append(json.dumps(dict(
   799	                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
   800	                ), allow_nan=False) + '\n')
   801	    _write_gzip_jsonl_atomic(final_path, out_lines)
   802	    print(f'Part1 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   803	
   804	
   805	def _part2_shard_worker(
   806	    shard_idx: int,
   807	    frames: tuple[int, ...],
   808	    trig_by_frame: dict[int, list[dict[str, Any]]],
   809	    raw_dir: Path,
   810	):
   811	    C, _, _, helpers = load_stage_runtime()
   812	    stage3, ctx = C['stage3'], C['ctx']
   813	    final_path = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
   814	    out_lines: list[str] = []
   815	    for frame in frames:
   816	        items = trig_by_frame.get(frame, [])
   817	        grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
   818	        for item in items:
   819	            grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
   820	        for (s, rho), grp in sorted(grouped.items()):
   821	            base = stage3.inputs(ctx, frame, s, rho)
   822	            for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
   823	                snr = int(item['snr_centi_db'])
   824	                raw, obs, truth = stage3.observed(ctx, base, rho, snr)
   825	                if stage3.input_record(raw, obs) != item['inputs']:
   826	                    raise RuntimeError(f'Part2 input mismatch at {(s, rho, snr, frame)}')
   827	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   828	                f0 = stage3.decoded(ctx, dec, truth)
   829	                if int(syn) != int(item['syndrome']) or f0 != dict(
   830	                    errors=int(item['arms']['F0']['errors']),
   831	                    decoded_sha=item['arms']['F0']['decoded_sha'],
   832	                ):
   833	                    raise RuntimeError(f'Part2 F0 drift at {(s, rho, snr, frame)}')
   834	                arch_cd = dict(
   835	                    errors=int(item['arms']['CD']['errors']),
   836	                    decoded_sha=item['arms']['CD']['decoded_sha'],
   837	                )
   838	                cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
   839	                cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   840	                out_lines.append(json.dumps(dict(
   841	                    scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=int(syn),
   842	                    arms=dict(CD2=cd2, CD2e8=cd2e8),
   843	                ), allow_nan=False) + '\n')
   844	    _write_gzip_jsonl_atomic(final_path, out_lines)
   845	    print(f'Part2 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   846	
   847	
   848	def _run_sharded_phase(target_fn, job_args: list[tuple[Any, ...]], max_workers: int, cpu_cap_sec: float):
   849	    """Run up to max_workers spawned processes concurrently with live CPU budget check."""
   850	    mp_ctx = multiprocessing.get_context('spawn')
   851	    pending = list(job_args)
   852	    running = {}
   853	    budget_hit = False
   854	    try:
   855	        while pending or running:
   856	            while pending and len(running) < max_workers:
   857	                args = pending.pop(0)
   858	                proc = mp_ctx.Process(target=target_fn, args=args)
   859	                proc.start()
   860	                running[proc.sentinel] = (args[0], proc)
   861	            ready = wait(running, timeout=10.0)
   862	            for r in ready:
   863	                idx, proc = running.pop(r)
   864	                proc.join()
   865	                code = proc.exitcode
   866	                proc.close()
   867	                if code != 0:
   868	                    raise RuntimeError(f'Worker shard {idx:03d} failed with exit code {code}')
   869	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   870	            if live_cpu >= cpu_cap_sec:
   871	                budget_hit = True
   872	                break
   873	    finally:
   874	        for _, proc in running.values():
   875	            proc.terminate()
   876	        for _, proc in running.values():
   877	            proc.join()
   878	            proc.close()
   879	    if budget_hit or _used_cpu_seconds() >= cpu_cap_sec:
   880	        print(f'STOPPED_BUDGET: CPU limit reached ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   881	        sys.exit(BUDGET_EXIT_CODE)
   882	
   883	
   884	# --------------------------------------------------------------------------- Analysis (P1 & P2)
   885	def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
   886	    """Wrap stageA2.crossing into conservative (lo, hi) bounds so censored draws never silently yield NaN."""
   887	    c = float(crossing_fn(fer, snrs))
   888	    if math.isfinite(c):
   889	        return c, c
   890	    if c < 0:
   891	        return -math.inf, float(snrs[0]) / 100.0
   892	    return float(snrs[-1]) / 100.0, math.inf
   893	
   894	
   895	def p1_verdict(ci_lo: float, ci_hi: float) -> str:
   896	    if ci_lo >= P1_THRESHOLD_DB:
   897	        return 'DOPPLER-LINE'
   898	    if ci_hi < P1_THRESHOLD_DB:
   899	        return 'WRITE-A'
   900	    return 'INCONCLUSIVE'
   901	
   902	
   903	def p2_verdict(ci_lo: float, ci_hi: float) -> str:
   904	    if ci_lo > P2_THRESHOLD_DB:
   905	        return 'STILL_BEHIND'
   906	    if ci_hi < P2_THRESHOLD_DB:
   907	        return 'CATCHES_UP'
   908	    return 'MIXED'
   909	
   910	
   911	def _rep(v: float) -> Any:
   912	    if math.isinf(v):
   913	        return '+inf' if v > 0 else '-inf'
   914	    if math.isnan(v):
   915	        raise FloatingPointError('NaN encountered in readout')
   916	    return float(v)
   917	
   918	
   154	    (out / 'STATUS').write_text((f'DONE {done} {hours:.4f}' if done == len(jobs) else f'STOPPED incomplete {hours:.4f}') + '\n')
   155	    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))
   156	
   157	
   158	def crossing(fer, snrs):
   159	    """stageA.crossing on an arbitrary SNR grid (dB)."""
   160	    x = np.asarray(snrs) / 100; lf = np.log10(np.maximum(fer, 1e-4))
   161	    if fer[0] <= .01:
   162	        return -np.inf
   163	    for i in range(1, len(x)):
   164	        if fer[i] <= .01:
   165	            t = (lf[i - 1] + 2) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
   166	            return x[i - 1] + t * (x[i] - x[i - 1])
   167	    return np.inf
   168	
   169	
   170	def load(out, arms, rhos, snrs):
   171	    fi = {f: i for i, f in enumerate(FRAMES)}
   172	    fail = np.zeros((len(FRAMES), len(arms), len(SCENARIOS), len(rhos), len(snrs)), bool); seen = np.zeros_like(fail)
   173	    diag = []
   174	    for p in sorted(Path(out).glob('rows_shard*.jsonl.gz')):
   175	        with gzip.open(p, 'rt') as fh:
   176	            for line in fh:
   177	                r = json.loads(line)
   178	                if r['rho'] not in rhos or r['snr'] not in snrs:
   179	                    continue
   180	                for a, arm in enumerate(arms):
   181	                    j = (fi[r['frame']], a, SCENARIOS.index(r['scenario']), rhos.index(r['rho']), snrs.index(r['snr']))
   182	                    fail[j] = r['arms'][arm]['errors'] > 0; seen[j] = True
   183	                if 'full' in arms and r['arms']['full']['errors'] > 0:
   184	                    f = r['arms']['full']['final']
   185	                    diag.append(dict(support_right=f['support_right'], doppler_err=f['doppler_err'] or 0.,
   186	                                     r0_fail=r['arms']['full']['r0_errors'] > 0))
   187	    if not seen.all():
   188	        raise ValueError(f'incomplete grid in {out}')
   189	    return fail, diag
   190	
   191	
   192	def read(out):
   193	    out = Path(out); status = (out / 'STATUS').read_text().split()
   194	    if status[0] != 'DONE':
   195	        raise ValueError(status)
   196	    fa, _ = load(out.parent / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)       # base, delay
   197	    fb, diag = load(out, ARMS, RHOS, SNRS)                                            # full, ldop
   198	    lo_idx = [stageA.RHOS.index(r) for r in RHOS]
   199	
   200	    def table(w):
   201	        def m(fail, snrs):
   202	            fer = np.tensordot(w, fail, axes=(0, 0)) / w.sum()
   203	            return np.apply_along_axis(crossing, -1, fer, snrs)                  # arms x scen x rho
   204	        ca, cb = m(fa, stageA.SNRS), m(fb, SNRS)
   205	        return ca, cb, ca.mean(axis=1), cb.mean(axis=1)
   206	
   207	    def stats(ma, mb):
   208	        delay_best = np.min(ma[1][lo_idx]); full_best = np.min(mb[0]); base_best = np.min(ma[0])
   209	        return delay_best - full_best, base_best - full_best, delay_best, full_best, base_best
   210	
   211	    w = np.ones(len(FRAMES)); ca, cb, ma, mb = table(w); g = stats(ma, mb)

exec
/bin/zsh -lc "ls experiments/data_pilot_fer_20261121/out/stageA; rg -n 'deinlab|/dev/shm|AFDM/bin/python' CLAUDE.md .trellis/spec/backend/research-diagnostics.md -m 14; rg -n 'HGint|CD2e8|13,735|13735' experiments/{sameframe_hg_20261124,huang_steelman_20261124}/out/{results,summary,gate}.json -m 3" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 2 in 0ms:
REMOTE_ROWS_MD5.txt
RUN_CONFIG.json
STATUS
results.json
run.log
.trellis/spec/backend/research-diagnostics.md:955:On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
.trellis/spec/backend/research-diagnostics.md:1024:deinlab, record its SSH root and verify it before deleting task-created local
CLAUDE.md:101:- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
CLAUDE.md:106:- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
CLAUDE.md:107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
CLAUDE.md:119:  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`
CLAUDE.md:123:- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
rg: experiments/sameframe_hg_20261124/out/summary.json: No such file or directory (os error 2)
rg: experiments/huang_steelman_20261124/out/results.json: No such file or directory (os error 2)
experiments/sameframe_hg_20261124/out/results.json:33:    "part1_triggered_keys": 13735,
experiments/sameframe_hg_20261124/out/results.json:223:      "HGint_minus_s100": {
experiments/sameframe_hg_20261124/out/results.json:235:      "HGint_minus_s050": {
experiments/huang_steelman_20261124/out/summary.json:68:      "HGint"
experiments/huang_steelman_20261124/out/summary.json:625:      "HGint_minus_HG": {
experiments/huang_steelman_20261124/out/summary.json:660:      "HGint_minus_CD": {

exec
/bin/zsh -lc "nl -ba experiments/huang_steelman_20261124/hs_arms.py | sed -n '125,199p;336,495p;509,570p'; nl -ba experiments/huang_steelman_20261124/hs_analysis.py | sed -n '36,90p'; rg -n 'def (run_branch|f0_state|inputs|observed)|dictionary_limit' experiments/f0_round_budget_20261118 experiments/gamma0_exchange_20261120 experiments/huang_steelman_20261124 --glob '*.py' " in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   125	    for name in OWN_SOURCE_FILES:
   126	        p = HERE / name
   127	        if not p.is_file():
   128	            raise FileNotFoundError(f'Missing own experiment file: {p}')
   129	        out[name] = md5_file(p)
   130	    return out
   131	
   132	
   133	def atomic_write_text(path: Path, text: str):
   134	    """Write via temporary .part file + fsync + atomic os.replace."""
   135	    partial = path.with_suffix(path.suffix + f'.{os.getpid()}.part')
   136	    with partial.open('w', encoding='utf-8') as handle:
   137	        handle.write(text)
   138	        handle.flush()
   139	        os.fsync(handle.fileno())
   140	    os.replace(partial, path)
   141	
   142	
   143	def check_thread_env() -> dict[str, str]:
   144	    bad = [k for k in THREADS if os.environ.get(k) != '1']
   145	    if bad:
   146	        raise RuntimeError(f'Single-thread env vars must be 1, bad={bad}')
   147	    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
   148	        raise RuntimeError('CUDA_VISIBLE_DEVICES must be empty string for CPU-only execution')
   149	    return {k: os.environ[k] for k in (*THREADS, 'CUDA_VISIBLE_DEVICES')}
   150	
   151	
   152	def verify_frozen_extra_md5() -> dict[str, str]:
   153	    extra_md5 = {}
   154	    for rel, expected in FROZEN_EXTRA_MD5.items():
   155	        actual = md5_file(EXPERIMENTS / rel)
   156	        if actual != expected:
   157	            raise RuntimeError(f'Frozen source MD5 mismatch for {rel}: {actual} != {expected}')
   158	        extra_md5[rel] = actual
   159	    return extra_md5
   160	
   161	
   162	def _load_module(name: str, path: Path):
   163	    spec = importlib.util.spec_from_file_location(name, path)
   164	    mod = importlib.util.module_from_spec(spec)
   165	    spec.loader.exec_module(mod)
   166	    return mod
   167	
   168	
   169	def load_context():
   170	    """Verify frozen MD5s BEFORE importing, then load Stage 3 context + zero_variance wrapper."""
   171	    extra_md5 = verify_frozen_extra_md5()
   172	    if str(STAGE3) not in sys.path:
   173	        sys.path.insert(0, str(STAGE3))
   174	    stage3 = _load_module('hs_stage3_run', STAGE3 / 'run.py')
   175	    ctx, full, cd, e1_checks = stage3.context()
   176	    paired = _load_module('hs_gamma0_paired', GAMMA0 / 'paired.py')
   177	    z_kernel = paired.zero_variance(cd)
   178	
   179	    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
   180	    from messages import moments
   181	    from physical import Channel
   182	    from twofft import time_refine
   183	
   184	    helpers = dict(
   185	        stage3=stage3,
   186	        full=full,
   187	        cd=cd,
   188	        z_kernel=z_kernel,
   189	        BaselineInitializer=BaselineInitializer,
   190	        Channel=Channel,
   191	        moments=moments,
   192	        time_refine=time_refine,
   193	        e1_checks=e1_checks,
   194	        extra_md5=extra_md5,
   195	    )
   196	    return ctx, helpers
   197	
   198	
   199	def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
   336	def run_hg_arm(
   337	    ctx,
   338	    helpers: dict[str, Any],
   339	    obs: dict[str, Any],
   340	    arrays: dict[str, Any],
   341	    truth: dict[str, Any],
   342	    *,
   343	    ls: np.ndarray,
   344	    ks: np.ndarray,
   345	    recipe: str = 'B0-p2-s0.5',
   346	    dictionary_limit: int = 2575,
   347	    max_passes: int = 2,
   348	    record_match: bool = True,
   349	) -> dict[str, Any]:
   350	    """Run Huang-2010-style global OMP re-acquisition (1..max_passes, syndrome early stop).
   351	
   352	    Decision-ready timing boundary: starts before message prep and stops immediately after
   353	    syndrome check on each pass (excludes truth scoring, hashing, and match diagnostics).
   354	    """
   355	    stage3 = helpers['stage3']
   356	    moments = helpers['moments']
   357	    time_refine = helpers['time_refine']
   358	    system = ctx.system
   359	    native = ctx.native
   360	    pd = 1.0 - system.rho  # 0.5 in normalized observe() convention
   361	
   362	    t_branch0 = perf_counter()
   363	    _require_finite(arrays['r1_check'], 'HG.pass1.r1_check')
   364	    _require_finite(arrays['r1_app'], 'HG.pass1.r1_app')
   365	    prior = np.clip(arrays['r1_check'], -20.0, 20.0)
   366	    mu, v, _ = moments(np.clip(arrays['r1_app'], -20.0, 20.0), pd)
   367	    prep_sec = perf_counter() - t_branch0
   368	
   369	    pass_raw = []
   370	    decision_total_sec = 0.0
   371	    for p_idx in range(max_passes):
   372	        tp0 = perf_counter()
   373	        x_ref = obs['pilot'] + mu
   374	        _, omp_l, omp_k, omp_g = omp_reacquire(
   375	            obs['y'], x_ref, ls, ks, system, float(obs['sigma2']), helpers,
   376	            recipe=recipe, dictionary_limit=dictionary_limit,
   377	        )
   378	        c, _detail = time_refine(
   379	            obs['y'], obs['pilot'], mu, v, omp_l, omp_k, omp_g,
   380	            system.c1, system.c2, float(obs['sigma2']),
   381	            mode='soft', max_paths=8, rounds=2,
   382	        )
   383	        _require_finite(c.dopplers, f'HG.pass{p_idx+1}.time_refine.dopplers')
   384	        _require_finite(c.gains, f'HG.pass{p_idx+1}.time_refine.gains')
   385	        o = native.scalar_joint(
   386	            obs['y'], obs['pilot'], c, float(obs['sigma2']),
   387	            pd=pd, prior=prior, iterations=20, damping=0.3, gain_mode='joint',
   388	        )
   389	        _require_finite(o['extrinsic'], f'HG.pass{p_idx+1}.scalar_joint.extrinsic')
   390	        dec = native.decoder_messages(ctx.code, np.clip(o['extrinsic'], -20.0, 20.0), maxiter=50)
   391	        _require_finite(dec['raw_check_extrinsic'], f'HG.pass{p_idx+1}.ldpc.raw_check_extrinsic')
   392	        _require_finite(dec['raw_app'], f'HG.pass{p_idx+1}.ldpc.raw_app')
   393	        syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   394	        pass_sec = (prep_sec if p_idx == 0 else 0.0) + (perf_counter() - tp0)
   395	        decision_total_sec += pass_sec
   396	        pass_raw.append((dec, syn, c, omp_l, omp_k, pass_sec))
   397	        if syn == 0 or p_idx == max_passes - 1:
   398	            break
   399	        tp_upd = perf_counter()
   400	        prior = np.clip(dec['raw_check_extrinsic'], -20.0, 20.0)
   401	        mu, v, _ = moments(np.clip(dec['raw_app'], -20.0, 20.0), pd)
   402	        decision_total_sec += perf_counter() - tp_upd
   403	
   404	    # Post-timing scoring and diagnostics
   405	    pass_records = []
   406	    for dec, syn, c, omp_l, omp_k, pass_sec in pass_raw:
   407	        rec = dict(
   408	            **stage3.decoded(ctx, dec, truth),
   409	            syndrome=syn,
   410	            ldpc_iters=int(dec['iterations']),
   411	            pass_seconds=float(pass_sec),
   412	            paths=[[int(d), float(nu)] for d, nu in zip(c.delays, c.dopplers, strict=True)],
   413	        )
   414	        if record_match:
   415	            rec['match_omp'] = match_omp_nominated(omp_l, omp_k, truth)
   416	            rec['match_refined'] = match_paths_1to1(c.delays, c.dopplers, truth)
   417	        pass_records.append(rec)
   418	
   419	    p1 = pass_records[0]
   420	    final = pass_records[-1]
   421	    return dict(
   422	        HG1=dict(
   423	            errors=p1['errors'],
   424	            decoded_sha=p1['decoded_sha'],
   425	            syndrome=p1['syndrome'],
   426	            ldpc_iters=p1['ldpc_iters'],
   427	            seconds=p1['pass_seconds'],
   428	            paths=p1['paths'],
   429	            **(dict(match_omp=p1['match_omp'], match_refined=p1['match_refined']) if record_match else {}),
   430	        ),
   431	        HG=dict(
   432	            errors=final['errors'],
   433	            decoded_sha=final['decoded_sha'],
   434	            syndrome=final['syndrome'],
   435	            ldpc_iters=final['ldpc_iters'],
   436	            passes_used=len(pass_records),
   437	            pass1_seconds=p1['pass_seconds'],
   438	            seconds=float(decision_total_sec),
   439	            paths=final['paths'],
   440	            **(dict(match_omp=final['match_omp'], match_refined=final['match_refined']) if record_match else {}),
   441	        ),
   442	    )
   443	
   444	
   445	def _run_exchange_arm(
   446	    ctx,
   447	    helpers: dict[str, Any],
   448	    kernel,
   449	    arm_name: str,
   450	    obs: dict[str, Any],
   451	    arrays: dict[str, Any],
   452	    truth: dict[str, Any],
   453	    *,
   454	    record_match: bool = True,
   455	) -> dict[str, Any]:
   456	    """Run local exchange branch (Z or CD) with strict numerical-fallback and decision-ready timing."""
   457	    stage3 = helpers['stage3']
   458	    _require_finite(arrays['r1_check'], f'{arm_name}.r1_check')
   459	    _require_finite(arrays['r1_app'], f'{arm_name}.r1_app')
   460	    t0 = perf_counter()
   461	    branch = stage3.e1.run_branch(ctx, kernel, obs, arrays, 'A1')
   462	    dec = branch['decoder']
   463	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   464	    sec = perf_counter() - t0
   465	
   466	    res = branch['result']
   467	    if bool(res.diagnostics.get('numerical_fallback')):
   468	        raise FloatingPointError(f'Geometry numerical_fallback triggered in {arm_name}')
   469	    _require_finite(res.gains, f'{arm_name}.geometry.gains')
   470	    _require_finite(branch['detector']['extrinsic'], f'{arm_name}.detector.extrinsic')
   471	
   472	    delays = [int(p.delay) for p in res.paths]
   473	    dopplers = [float(p.doppler) for p in res.paths]
   474	    paths = [[d, nu] for d, nu in zip(delays, dopplers, strict=True)]
   475	    state = dict(
   476	        paths=paths,
   477	        gains_sha=stage3.digest(res.gains),
   478	        gamma_sha=stage3.digest(res.diagnostics['gamma']),
   479	        objective=float(res.objective_after),
   480	    )
   481	    out = dict(
   482	        **stage3.decoded(ctx, dec, truth),
   483	        syndrome=syn,
   484	        ldpc_iters=int(dec['iterations']),
   485	        seconds=float(sec),
   486	        paths=paths,
   487	        state=state,
   488	        n_edits=len(res.edits),
   489	        decision=_decision_record(res),
   490	        numerical_fallback=False,
   491	    )
   492	    if record_match:
   493	        out['match_refined'] = match_paths_1to1(delays, dopplers, truth)
   494	    return out
   495	
   509	def load_archived_rho_sweep(
   510	    archive_dir: Path = RHO_ARCHIVE_DIR,
   511	    md5_manifest: Path = RHO_ARCHIVE_MD5,
   512	) -> tuple[dict[tuple[str, int, int, int], dict[str, Any]], dict[str, str]]:
   513	    """Pin manifest SHA-256, verify all 24 shard MD5s, validate 62,400 keys, 18,009 triggers, and invariants."""
   514	    manifest_sha = sha256_file(md5_manifest)
   515	    if manifest_sha != RHO_ARCHIVE_MD5_SHA256:
   516	        raise RuntimeError(f'Archive manifest SHA-256 mismatch: {manifest_sha} != {RHO_ARCHIVE_MD5_SHA256}')
   517	
   518	    expected_md5: dict[str, str] = {}
   519	    for line in md5_manifest.read_text(encoding='utf-8').splitlines():
   520	        if not line.strip():
   521	            continue
   522	        digest, name = line.split()
   523	        expected_md5[name] = digest
   524	    if len(expected_md5) != 24:
   525	        raise RuntimeError(f'Expected 24 archived shards in manifest, got {len(expected_md5)}')
   526	
   527	    rows: dict[tuple[str, int, int, int], dict[str, Any]] = {}
   528	    verified_md5: dict[str, str] = {}
   529	    stratum_counts: dict[tuple[int, str], int] = {(r, b): 0 for r in RHOS for b in ('low', 'mid')}
   530	    for name, exp in sorted(expected_md5.items()):
   531	        path = archive_dir / name
   532	        if not path.is_file():
   533	            raise FileNotFoundError(f'Missing archived shard {path}')
   534	        actual = md5_file(path)
   535	        if actual != exp:
   536	            raise RuntimeError(f'Archived shard MD5 mismatch for {name}: {actual} != {exp}')
   537	        verified_md5[name] = actual
   538	        with path.open('r', encoding='utf-8') as handle:
   539	            for line in handle:
   540	                r = json.loads(line)
   541	                k = row_key(r)
   542	                if k in rows:
   543	                    raise RuntimeError(f'Duplicate archived key {k}')
   544	                if bool(r['triggered']) != bool(r['syndrome']):
   545	                    raise RuntimeError(f'Archive invariant triggered != bool(syndrome) at {k}')
   546	                if not r['syndrome']:
   547	                    f0_out = (r['arms']['F0']['errors'], r['arms']['F0']['decoded_sha'])
   548	                    cd_out = (r['arms']['CD']['errors'], r['arms']['CD']['decoded_sha'])
   549	                    if f0_out != cd_out:
   550	                        raise RuntimeError(f'Untriggered CD != F0 in archive at {k}')
   551	                else:
   552	                    band = 'low' if k[2] in LOW_SNRS else 'mid'
   553	                    stratum_counts[(k[1], band)] += 1
   554	                rows[k] = r
   555	
   556	    expected_keys = {
   557	        (s, rho, snr, frame)
   558	        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
   559	    }
   560	    if rows.keys() != expected_keys:
   561	        missing = len(expected_keys - rows.keys())
   562	        extra = len(rows.keys() - expected_keys)
   563	        raise RuntimeError(f'Archived key inventory mismatch: missing={missing}, extra={extra}')
   564	    if sum(stratum_counts.values()) != EXPECTED_TOTAL_TRIGGERS or stratum_counts != EXPECTED_TRIGGERS_BY_STRATUM:
   565	        raise RuntimeError(f'Archived trigger strata mismatch: {stratum_counts} != {EXPECTED_TRIGGERS_BY_STRATUM}')
   566	    return rows, verified_md5
    36	    """Parallel lower/upper arrays; index 0 is the full-sample point estimate, 1: are bootstrap draws."""
    37	    lower: np.ndarray
    38	    upper: np.ndarray
    39	
    40	
    41	def _difference(first: Bounds, second: Bounds) -> Bounds:
    42	    return Bounds(first.lower - second.upper, first.upper - second.lower)
    43	
    44	
    45	def _mean(bounds_list: list[Bounds]) -> Bounds:
    46	    return Bounds(
    47	        np.mean([b.lower for b in bounds_list], axis=0),
    48	        np.mean([b.upper for b in bounds_list], axis=0),
    49	    )
    50	
    51	
    52	def _minimum(bounds_list: list[Bounds]) -> Bounds:
    53	    return Bounds(
    54	        np.min([b.lower for b in bounds_list], axis=0),
    55	        np.min([b.upper for b in bounds_list], axis=0),
    56	    )
    57	
    58	
    59	def _nearest_rank(draws: np.ndarray, probability: float) -> float:
    60	    n = len(draws)
    61	    rank = min(n - 1, max(0, math.ceil(n * probability) - 1))
    62	    return float(np.partition(draws, rank)[rank])
    63	
    64	
    65	def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
    66	    return (
    67	        _nearest_rank(bounds.lower[1:], alpha / 2.0),
    68	        _nearest_rank(bounds.upper[1:], 1.0 - alpha / 2.0),
    69	    )
    70	
    71	
    72	def _represent(value: float) -> Any:
    73	    if np.isposinf(value):
    74	        return '+inf'
    75	    if np.isneginf(value):
    76	        return '-inf'
    77	    if np.isnan(value):
    78	        raise FloatingPointError('NaN encountered in crossing bound')
    79	    return float(value)
    80	
    81	
    82	def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
    83	    x, status = p1_agg.crossing(fer, frame_count, np.asarray(snrs_centi, dtype=float) / 100.0)
    84	    return Bounds(
    85	        np.where(status == p1_agg.LOW, -np.inf, x),
    86	        np.where(status == p1_agg.HIGH, np.inf, x),
    87	    )
    88	
    89	
    90	def compute_crossings(
experiments/huang_steelman_20261124/hs_arms.py:228:    dictionary_limit: int = 2575,
experiments/huang_steelman_20261124/hs_arms.py:239:    est = BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=dictionary_limit)
experiments/huang_steelman_20261124/hs_arms.py:346:    dictionary_limit: int = 2575,
experiments/huang_steelman_20261124/hs_arms.py:376:            recipe=recipe, dictionary_limit=dictionary_limit,
experiments/huang_steelman_20261124/run_main.py:85:                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
experiments/huang_steelman_20261124/run_main.py:111:                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
experiments/huang_steelman_20261124/timing.py:129:        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
experiments/huang_steelman_20261124/timing.py:192:                    ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
experiments/huang_steelman_20261124/timing.py:204:                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
experiments/gamma0_exchange_20261120/phase1.py:179:            def observed_reopen(y, geometry_mean, variance, initial, **kwargs):
experiments/huang_steelman_20261124/gates.py:158:                helpers, recipe='B0-p2-s0.5', dictionary_limit=515,
experiments/huang_steelman_20261124/gates.py:184:        recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine), return_phi=True,
experiments/huang_steelman_20261124/gates.py:238:        helpers, recipe=recipe, dictionary_limit=len(ls_fine),
experiments/huang_steelman_20261124/gates.py:270:        helpers, recipe=recipe, dictionary_limit=len(ls_fine), return_phi=True,
experiments/huang_steelman_20261124/gates.py:350:                    ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int), max_passes=2,
experiments/huang_steelman_20261124/gates.py:360:                        ls=ls_fine, ks=ks_fine, recipe=rec_name, dictionary_limit=len(ls_fine), max_passes=2,

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/huang_steelman_20261124/run_main.py | sed -n '56,126p'; nl -ba experiments/huang_steelman_20261124/hs_arms.py | sed -n '22,65p'; nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '752,803p'; sed -n '96,150p' CLAUDE.md" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    56	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
    57	    shard_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl'
    58	    count = 0
    59	    with publish(shard_path, buffering=1) as handle:
    60	        for frame in frames:
    61	            items = triggered_by_frame.get(frame, [])
    62	            grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    63	            for item in items:
    64	                grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
    65	            for (s, rho), grp in sorted(grouped.items()):
    66	                base = stage3.inputs(ctx, frame, s, rho)
    67	                for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
    68	                    snr = int(item['snr_centi_db'])
    69	                    key = (s, rho, snr, frame)
    70	                    t_key = time.process_time()
    71	                    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    72	                    inp = stage3.input_record(raw, obs)
    73	                    if inp != item['inputs']:
    74	                        raise RuntimeError(f'Input fingerprint mismatch vs archive at {key}')
    75	                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
    76	                    f0 = stage3.decoded(ctx, dec, truth)
    77	                    if syn != int(item['syndrome']) or f0 != dict(
    78	                        errors=int(item['arms']['F0']['errors']),
    79	                        decoded_sha=item['arms']['F0']['decoded_sha'],
    80	                    ):
    81	                        raise RuntimeError(f'Live F0 diverged from archive at {key}')
    82	
    83	                    hg_out = ar.run_hg_arm(
    84	                        ctx, helpers, obs, arrays, truth,
    85	                        ls=ls_fine, ks=ks_fine, recipe=hg_recipe, dictionary_limit=len(ls_fine),
    86	                        max_passes=2, record_match=True,
    87	                    )
    88	                    z_out = ar.run_z_arm(ctx, helpers, obs, arrays, truth, record_match=True)
    89	
    90	                    arch_cd = item['arms']['CD']
    91	                    cd_paths = arch_cd['state']['paths']
    92	                    cd_match = ar.match_paths_1to1(
    93	                        [p[0] for p in cd_paths], [p[1] for p in cd_paths], truth,
    94	                    )
    95	
    96	                    arm_records = dict(
    97	                        F0=f0,
    98	                        CD=dict(
    99	                            errors=int(arch_cd['errors']),
   100	                            decoded_sha=arch_cd['decoded_sha'],
   101	                            paths=cd_paths,
   102	                            match_refined=cd_match,
   103	                        ),
   104	                        HG=hg_out['HG'],
   105	                        HG1=hg_out['HG1'],
   106	                        Z=z_out,
   107	                    )
   108	                    if include_hgint:
   109	                        hgint_out = ar.run_hg_arm(
   110	                            ctx, helpers, obs, arrays, truth,
   111	                            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   112	                            max_passes=2, record_match=True,
   113	                        )
   114	                        arm_records['HGint'] = hgint_out['HG']
   115	
   116	                    row = dict(
   117	                        scenario=s,
   118	                        rho_permille=rho,
   119	                        snr_centi_db=snr,
   120	                        frame=frame,
   121	                        syndrome=int(syn),
   122	                        triggered=True,
   123	                        cpu_seconds=float(time.process_time() - t_key),
   124	                        arms=arm_records,
   125	                    )
   126	                    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
    22	RHO_ARCHIVE_DIR = RHO_SWEEP / 'out' / 'main_20261119'
    23	RHO_ARCHIVE_MD5 = RHO_ARCHIVE_DIR / 'REMOTE_ROWS_MD5.txt'
    24	RHO_ARCHIVE_MD5_SHA256 = '98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd'
    25	
    26	SCENARIOS = ('U', 'G')
    27	RHOS = (150, 200, 250, 300, 400, 500)
    28	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    29	LOW_SNRS = (300, 400)
    30	MAIN_FRAMES = tuple(range(5400, 5800))
    31	SMOKE_FRAMES = tuple(range(5800, 5840))
    32	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    33	THREADS = (
    34	    'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
    35	    'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
    36	)
    37	EXPECTED_TOTAL_TRIGGERS = 18009
    38	EXPECTED_TRIGGERS_BY_STRATUM = {
    39	    (150, 'low'): 1462, (150, 'mid'): 2186,
    40	    (200, 'low'): 1443, (200, 'mid'): 1174,
    41	    (250, 'low'): 1501, (250, 'mid'): 807,
    42	    (300, 'low'): 1569, (300, 'mid'): 791,
    43	    (400, 'low'): 1600, (400, 'mid'): 1419,
    44	    (500, 'low'): 1600, (500, 'mid'): 2457,
    45	}
    46	
    47	# Frozen dependencies verified identical between local vault and deinlab BEFORE importing.
    48	FROZEN_EXTRA_MD5 = {
    49	    'cstate_codelay_sbl_stage3_20261118/run.py': 'bbeccc203f8dcb0d262c44142cd422f8',
    50	    'cstate_codelay_sbl_stage3_20261118/codelay.py': 'e6d6e21b02295affbd6b05902a820c2b',
    51	    'tf_cstate_e1_20261017/e1_driver.py': '01c0701b0291a7c04d222007175ad8ec',
    52	    'tf_cstate_e1_20261017/geometry_validation_variant.py': '26571aa84e39097d264421a90bab23df',
    53	    'tf_cstate_e1_20261017/geometry_reopen_variant.py': 'f513f8d3decf529e741298462eeaef1d',
    54	    'gamma0_exchange_20261120/paired.py': '7fca5747930a2dafca8fd1deb753e5d9',
    55	    'tcom_reference_frame_20261015/p1_agg.py': '047bd512a1c5c3bc437a334a54b075e7',
    56	}
    57	OWN_SOURCE_FILES = (
    58	    'PROTOCOL.md', 'hs_arms.py', 'hs_analysis.py', 'test_analysis.py',
    59	    'gates.py', 'run_main.py', 'timing.py', 'launch_main.sh',
    60	)
    61	OWN_MODULE_NAMES = frozenset({
    62	    'hs_arms', 'hs_analysis', 'test_analysis', 'gates', 'run_main', 'timing', 'hs_p1_agg',
    63	})
    64	
    65	
   752	    out_lines: list[str] = []
   753	    for frame in frames:
   754	        items = trig_by_frame.get(frame, [])
   755	        grouped: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
   756	        for s, rho, snr, exp_syn, exp_f0_err in items:
   757	            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err))
   758	        for (s, rho), grp in sorted(grouped.items()):
   759	            base = stage3.inputs(ctx, frame, s, rho)
   760	            for snr, exp_syn, exp_f0_err in sorted(grp):
   761	                _, obs, truth = stage3.observed(ctx, base, rho, snr)
   762	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   763	                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   764	                if int(syn) != exp_syn or f0_err != exp_f0_err:
   765	                    raise RuntimeError(
   766	                        f'Part1 F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
   767	                    )
   768	                hg_out = ar.run_hg_arm(
   769	                    ctx, helpers, obs, arrays, truth,
   770	                    ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   771	                    max_passes=2, record_match=False,
   772	                )
   773	                arms_rec = dict(
   774	                    HG=dict(
   775	                        errors=hg_out['HG']['errors'],
   776	                        decoded_sha=hg_out['HG']['decoded_sha'],
   777	                        syndrome=hg_out['HG']['syndrome'],
   778	                        passes_used=hg_out['HG']['passes_used'],
   779	                    ),
   780	                    HG1=dict(
   781	                        errors=hg_out['HG1']['errors'],
   782	                        decoded_sha=hg_out['HG1']['decoded_sha'],
   783	                        syndrome=hg_out['HG1']['syndrome'],
   784	                    ),
   785	                )
   786	                if include_hgint:
   787	                    hgint_out = ar.run_hg_arm(
   788	                        ctx, helpers, obs, arrays, truth,
   789	                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   790	                        max_passes=2, record_match=False,
   791	                    )
   792	                    arms_rec['HGint'] = dict(
   793	                        errors=hgint_out['HG']['errors'],
   794	                        decoded_sha=hgint_out['HG']['decoded_sha'],
   795	                        syndrome=hgint_out['HG']['syndrome'],
   796	                        passes_used=hgint_out['HG']['passes_used'],
   797	                    )
   798	                out_lines.append(json.dumps(dict(
   799	                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
   800	                ), allow_nan=False) + '\n')
   801	    _write_gzip_jsonl_atomic(final_path, out_lines)
   802	    print(f'Part1 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   803	
- 本地镜像：`/Users/guoyikun/Downloads/share/claode_birain/afdm-sp-mirror/`（bare `repo.git` + `sync.sh`）。内容 = vault `main` 已提交的本目录（2026-11-21 前为 `trans/tcom-main`），排除 `.mission/`（保留 `*.csv`）、`.claude/` `.codex/` `.agents/`、不可读二进制、>50MB 文件。
- 同步：Eric 2026-11-21 授权由 Claude 负责推送镜像（idea 漏斗每轮开始前、或 Eric 要求时）；先确认相关改动已在 vault commit，再运行 `sync.sh`（会 push）。不得把 vault 本身推到该仓库。
- 例外：`funnel/*` 分支由 idea 漏斗的云端 runner 写入，只改 `ideas/`；`main` 只由 `sync.sh` 更新。

## Remote Server
- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
- Login landing: `/home/guoyikun`，登录后需 `cd /data/guoyikun/`
- GPU: RTX 4090 单卡，约 5 位活跃用户共享
- Working dir: `/data/guoyikun/`
- Code dir: `/data/guoyikun/00inbox/AFDM-channel-estimation/`
- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。

### 实验结果回传规则（2026-07-26 起）
- 新实验的远程 run 结束后，**小结果文件**（`results.json`、`*_run.log`、表格 md、launcher `.sh`）回传到本地该实验的 `experiments/<experiment>/out/`；既有 run 仍回传到其记录的同名历史 `afdm_sp_joint_unrolled/outputs_*/`，不搬已有证据。文件若被忽略，按具体小文件显式 whitelist；Git 纳入/提交仍遵守当次授权，大文件不因新位置变成可提交。
- **大文件**（npz/ckpt/per-frame dump >10MB）留远程不回传，但其**完整远程路径 + md5** 必须记入对应 asset card 的 provenance 或任务 notes——路径丢了等于数据丢了
- CPU 并行原则：单 job 线程数超过 ~32 后收益递减，多 job 并行吃满整机比单 job 独占 128 核吞吐更高；共享机器上合计留 ~16 核余量

## ⚠️ 硬性约束
- 禁止 `sudo` / `apt` 安装任何软件，无权限
- 所有文件必须在 `/data/<username>/` 下，其他目录会被定期清理
- 运行训练前必须先执行 `nvidia-smi` 检查 GPU 占用
- 远程执行 conda 相关命令需用登录 shell，否则会 `conda: command not found`，例：
  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`

### 共享目录禁用清单（**任何文件都不能写进去**）
严禁向以下位置写任何文件，包括中间产物 / 日志 / 临时 pickle：
- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
- `/home/guoyikun/` — 主目录虽属于本人但非项目空间，项目数据集中放 `/data/guoyikun/`
- `/opt/`、`/usr/`、`/root/` — 系统目录，权限错误或越权
- 其他用户 home：`/home/<他人>/`、`/data/<他人>/` — 越权

### 规范的落盘位置
| 文件类型 | 正确位置 |
|---|---|
| 新实验的 `run.log` / `tee` 输出 / 结果 JSON | `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/<experiment>/out/`；已有 run 仍按记录的历史 `afdm_sp_joint_unrolled/outputs_*/` 原地保存，不覆写冻结证据 |
| 需要快速丢弃的 scratch 文件、smoke test 日志、跨项目临时 pickle | **`/data/guoyikun/tmp/`** ← 项目专用 tmp 目录，取代系统 `/tmp` |
| 跨天保留的抢救件 | `/data/guoyikun/00inbox/AFDM-channel-estimation/_tmp_rescue_YYYYMMDD/` |

**规则**：所有原本想写到系统 `/tmp/` 的操作，都改写到 `/data/guoyikun/tmp/`。
例外：tmux 自己的运行时 socket `/tmp/tmux-<uid>/` 由 tmux 管理，不要动。

## GPU 使用
- 运行前 `nvidia-smi` 查看占用
- **不要求独占 GPU**：只要没有"强烈碰撞"，可并行跑合适规模的进程
- "强烈碰撞"经验阈值（**同时满足**才算冲突，避让或延后）：
  - 已用显存 > 18 GB（剩余 < ~6 GB，新进程极可能 OOM）
  - **且** GPU-Util 长期 > 90%（他人任务已吃满算力）
- 任一条件未满足 → 可以启动任务，但应主动控制 batch size / 显存占用
- 若必须跑大任务且他人占用高 → 先询问我（用户）沟通或延后
- 长任务用 tmux 防止 SSH 断开

### tmux 命名规范
- 所有 session 名以 `g_` 开头（例：`g_train_afdm`、`g_debug`），避免与他人撞名


exec
/bin/zsh -lc "rg -n 'fin(.|al)_.*cross|\"s100\"|\"s025\"|\"CD2\"|\"include_hgint\"|\"part1_rhos\"' experiments/sameframe_hg_20261124/out/results.json -m 15; rg -n 'B0-p2-s0.5|hg_recipe|HGI?nt' experiments/huang_steelman_20261124/out/{main.log,resume.log,summary.json} -m 4; rg -n 'AFDM|status' experiments/sameframe_hg_20261124/launch.sh -m 10" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
22:    "part1_rhos": [
28:    "include_hgint": true,
101:      "part1_rhos": [
107:      "include_hgint": true,
130:    "part1_rhos": [
136:    "include_hgint": true,
328:      "s025": {
338:      "s100": {
471:      "s025": {
495:      "s100": {
576:      "s025": 100,
578:      "s100": 100,
911:      "CD2": {
1287:      "CD2": 200,
1295:      "CD2": {
experiments/huang_steelman_20261124/out/summary.json:32:    "hg_recipe": "B0-p2-s0.5",
experiments/huang_steelman_20261124/out/summary.json:223:      "hg_recipe": "B0-p2-s0.5",
experiments/huang_steelman_20261124/out/summary.json:238:      "B0-p2-s0.5": {
experiments/huang_steelman_20261124/out/summary.json:264:      "recipe": "B0-p2-s0.5",
experiments/huang_steelman_20261124/out/main.log:11:Validated archive, gate binding, and frozen sources. Launching 24 workers on 18009 triggered keys (recipe=B0-p2-s0.5, include_hgint=True, rhos=(150, 200, 250, 300, 400, 500)).
11:REPO="/data/guoyikun/00inbox/AFDM-channel-estimation"
25:conda activate AFDM
28:PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
61:    status=STOPPED
63:        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
78:        status=STOPPED_BUDGET
86:    status=DONE

exec
/bin/zsh -lc "rg -n 'def (run_branch|f0_state|inputs|observed)|def setup|set_num_threads' experiments/data_pilot_fer_20261121 experiments/gamma0_exchange_20261120 experiments/cstate_codelay_sbl_stage3_20261118 experiments/f0_round_budget_20261118 experiments/huang_steelman_20261124 --glob '*.py'; ls -l experiments/sameframe_cd2_20261125/reviews; python3 -B .trellis/scripts/task.py current --source; shasum -a 256 experiments/sameframe_hg_20261124/out/REMOTE_ROWS_MD5.txt" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/data_pilot_fer_20261121/stageA.py:34:def setup():
experiments/gamma0_exchange_20261120/phase1.py:179:            def observed_reopen(y, geometry_mean, variance, initial, **kwargs):
experiments/cstate_codelay_sbl_stage3_20261118/run.py:69:def inputs(ctx, frame, scenario, rho):
experiments/cstate_codelay_sbl_stage3_20261118/run.py:74:def observed(ctx, base, rho, snr):
experiments/data_pilot_fer_20261121/stage0.py:28:def setup():
total 432
-rw-r--r--@ 1 guoyikun  staff  216776 Nov 25 00:55 sol-static-review.md
Current task: (none)
Source: none
7cac38cd7cc8fa610ddf8c0b5908b62c668901cf5b72756889c1fd6a0f6b435f  experiments/sameframe_hg_20261124/out/REMOTE_ROWS_MD5.txt

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '/def f0_state/,/def /p; /def run_branch/,/"'^def /p'"' | head -150; nl -ba experiments/data_pilot_fer_20261121/stageA.py | sed -n '16,108p'; nl -ba experiments/cstate_codelay_sbl_stage3_20261118/run.py | sed -n '45,97p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   169	def f0_state(ctx, obs):
   170	    return receive_state(ctx, obs, 2)
   171	
   172	
   173	def run_a7(ctx, obs, arrays_ref):
   191	def run_branch(ctx, kvar, obs, arrays, arm):
   192	    """run_validation._branch (CSTATE20) with per-arm parameters; exclusive-stage timing kept.  A5 skips geometry entirely."""
   193	    from messages import moments
   194	    from physical import Channel, daft
   195	
   196	    spec, system, native = ARM_SPECS[arm], ctx.system, ctx.native
   197	    stamp = time.perf_counter()
   198	    app = np.clip(arrays['r1_app'], -20, 20)
   199	    check = np.clip(arrays['r1_check'], -20, 20)
   200	    if spec is None:
   201	        if len(arrays['r1_delays']) != len(arrays['r1_gains']):
   202	            raise ValueError('native physical slot count differs')
   203	        message_end = time.perf_counter()
   204	        channel = Channel(len(obs['y']), system.c1, system.c2, arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains'])
   205	        channel_end = time.perf_counter()
   206	        result, initial = None, None
   207	        stages = dict(message_handling=message_end - stamp, y_transform=0., **{k: 0. for k in GEOMETRY_STAGES},
   208	                      geometry_wrapper_overhead=0., wrapper_validation=0., channel_construction=channel_end - message_end)
   209	        mu = v = None
   210	    else:
   211	        mu, v, _ = moments(app, 1 - system.rho)
   212	        initial = [kvar.Path(int(delay), float(nu)) for delay, nu in zip(arrays['r1_delays'], arrays['r1_dopplers'])]
   213	        if len(initial) != len(arrays['r1_gains']):
   214	            raise ValueError('native physical slot count differs')
   215	        message_end = time.perf_counter()
   216	        Y = daft(obs['y'], system.c1, system.c2, True)
   217	        transform_end = time.perf_counter()
   218	        result = kvar.reopen_geometry(
   219	            Y, obs['pilot'] + mu, v, initial, c1=system.c1, c2=system.c2, ridge=float(obs['sigma2']),
   220	            max_delay=system.l_max_cap, doppler_min=-3., doppler_max=3., grid_step=.25, max_edits=spec['max_edits'], chunk_size=64,
   221	            local_passes=spec['local_passes'], local_halfwidth=.75, local_max_evals=16, duplicate_tolerance=1e-6, top_k=20,
   222	            strategy='compact', gamma_mode=spec['gamma_mode'])
   223	        geometry_end = time.perf_counter()
   224	        if len(result.paths) != len(initial):
   225	            raise ValueError('geometry changed physical slot count')
   226	        stage = result.diagnostics['stage_timing']
   227	        exclusive = stage['exclusive_seconds']
   228	        if set(exclusive) != set(GEOMETRY_STAGES) or any(not np.isfinite(x) or x < 0 for x in exclusive.values()):
   229	            raise ValueError('kernel exclusive-stage classification differs')
   230	        if not np.isclose(sum(exclusive.values()), stage['total_seconds'], rtol=0, atol=1e-6):
   231	            raise ValueError('kernel exclusive stages do not sum to geometry total')
   232	        overhead = geometry_end - transform_end - stage['total_seconds']
   233	        if overhead < 0:
   234	            raise ValueError('kernel stage total exceeds wrapper geometry wall time')
   235	        validation_end = time.perf_counter()
   236	        channel = Channel(len(obs['y']), system.c1, system.c2, [p.delay for p in result.paths], [p.doppler for p in result.paths],
   237	                          result.gains)
   238	        channel_end = time.perf_counter()
   239	        stages = dict(message_handling=message_end - stamp, y_transform=transform_end - message_end, **exclusive,
   240	                      geometry_wrapper_overhead=overhead, wrapper_validation=validation_end - geometry_end,
   241	                      channel_construction=channel_end - validation_end)
   242	    detector = native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - system.rho, prior=check,
   243	                                   iterations=20, damping=.3, gain_mode='joint')
   244	    tf_end = time.perf_counter()
   245	    decoder = native.decoder_messages(ctx.code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
   246	    decision_end = time.perf_counter()
   247	    stages.update(tf=tf_end - channel_end, ldpc=decision_end - tf_end)
   248	    decision = decision_end - stamp
   249	    if not np.isclose(sum(stages.values()), decision, rtol=0, atol=1e-7):
   250	        raise ValueError('decision-ready exclusive stage sum differs')
   251	    return dict(result=result, detector=detector, decoder=decoder, app_input=app, check_prior=check, ce_mu=mu, ce_variance=v,
   252	                initial_paths=initial, exclusive_stages=stages, branch_decision_seconds=decision)
   253	
   254	
   255	def arm_record(ctx, truth, br, arrays):
   256	    dec = br['decoder']['decoded']
   257	    res = br['result']
   258	    r1_delays = [int(x) for x in np.asarray(arrays['r1_delays'])]
   259	    if res is None:
   260	        d, nu = r1_delays, [float(x) for x in np.asarray(arrays['r1_dopplers'])]
   261	        edits, top5, extra = [], [], {}
   262	    else:
   263	        d, nu = [int(p.delay) for p in res.paths], [float(p.doppler) for p in res.paths]
   264	        edits = [dict(step=int(e['step']), slot=int(e['slot']), old=e['old'], new=e['new'], decrease=float(e['decrease']))
   265	                 for e in res.edits]
   266	        trace = res.global_trace
   267	        top5 = [dict(rank=int(t['rank']), slot=int(t['slot']), replacement=t['replacement'], score=float(t['frozen_score']))
   268	                for t in (trace[0]['top_k'][:5] if trace else [])]
   269	        extra = dict(objective_before=float(res.objective_before), objective_after=float(res.objective_after),
   270	                     numerical_fallback=bool(res.diagnostics['numerical_fallback']), condition_number=float(res.condition_number))
   271	    errors = gd.score(ctx, dec, truth)
   272	    return dict(status='ok', fer=int(errors > 0), info_errors=int(errors), syndrome=int(ctx.hd.syndrome_weight(ctx, dec)),
   273	                decoded_sha256=gd.bits_sha(dec), ldpc_iters=int(br['decoder']['iterations']),
   274	                final_delays=d, final_dopplers=nu,
   275	                n_support_changes=len(set(d) ^ set(r1_delays)), n_delay_replacements=len(set(d) - set(r1_delays)),
   276	                n_edits=len(edits), edits=edits, top5_step1=top5, seconds=float(br['branch_decision_seconds']),
   277	                stages={k: float(x) for k, x in br['exclusive_stages'].items()}, **extra)
   278	
   279	
   280	def a7_record(ctx, truth, br, arrays_ref, f0_seconds):
   281	    dec = br['decoder']['decoded']
   282	    a3 = br['arrays']
   283	    r1_delays = [int(x) for x in np.asarray(arrays_ref['r1_delays'])]
   284	    d, nu = [int(x) for x in np.asarray(a3['r2_delays'])], [float(x) for x in np.asarray(a3['r2_dopplers'])]
   285	    errors = gd.score(ctx, dec, truth)
   286	    return dict(status='ok', fer=int(errors > 0), info_errors=int(errors), syndrome=int(br['syndrome']), decoded_sha256=gd.bits_sha(dec),
   287	                ldpc_iters=int(br['decoder']['iterations']), final_delays=d, final_dopplers=nu,
   288	                n_support_changes=len(set(d) ^ set(r1_delays)), n_delay_replacements=len(set(d) - set(r1_delays)), n_edits=0, edits=[],
   289	                top5_step1=[], seconds=float(br['seconds']), seconds_minus_f0=float(br['seconds'] - f0_seconds),
   290	                stages={'receive_rounds3': float(br['seconds'])}, g5_ok=not br['g5_diff'], g5_keys=len(br['g5_keys']),
   291	                r1_decoded_sha256=gd.bits_sha(a3['r1_decoded']))
   292	
   293	
   294	def err_record(error):
   295	    return dict(status='error', error=repr(error), trace=traceback.format_exc()[-1500:])
   296	
   297	
   298	# ----------------------------------------------------------------------------- run mode
   299	def run_mode(args, argv):
   300	    ctx = p1ctx.load()
   301	    kvar = load_variant()
   302	    out = args.out.resolve()
   303	    out.mkdir(parents=True, exist_ok=True)
   304	    keys = json.loads(Path(args.keys).read_text())['units']
   305	    units = keys[args.shard::args.nshard]
   306	    if args.max_units:  # smoke: round-robin over SNR levels (ascending), so low and high SNR units are both exercised
   307	        levels = sorted({u['snr_centi_db'] for u in units})
   308	        per = [[u for u in units if u['snr_centi_db'] == s] for s in levels]
   309	        units = [per[i % len(levels)][i // len(levels)] for i in range(args.max_units) if i // len(levels) < len(per[i % len(levels)])]
   310	    write_config(out, args.shard, argv, args, ctx)
   311	    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
   312	    done = gd.load_done(jsonl)
   313	    started = time.perf_counter()
   314	    n_new = 0
   315	    with jsonl.open('a') as handle:
   316	        for u in units:
   317	            k = (u['scenario'], u['rho_permille'], u['snr_centi_db'], u['frame'])
   318	            if k in done:
   319	                continue
   320	            rho = u['rho_permille'] / 1000
   321	            g0 = time.perf_counter()
   322	            raw_base, diag_base = p1ctx.base(ctx, u['scenario'], rho, u['frame'])
   323	            raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, u['snr_centi_db'])
   324	            gen_seconds = time.perf_counter() - g0
   325	            dec0, arrays, syn, f0_seconds = f0_state(ctx, obs)
   326	            g4a_ok = syn != 0
   327	            ledger = {x: u[x] for x in ('triggered', 'f0_syndrome', 'b_sha', 'b_info_errors', 'b_fer', 'f0_sha', 'f0_info_errors', 'f0_fer')}
   328	            f0_info = gd.score(ctx, dec0['decoded'], truth)
   329	            row = dict(scenario=u['scenario'], rho=float(rho), rho_permille=u['rho_permille'], snr_centi_db=u['snr_centi_db'],
   330	                       snr_db=u['snr_centi_db'] / 100, frame=u['frame'], sigma2=float(raw['sigma2']), gen_seconds=gen_seconds,
   331	                       f0=dict(syndrome=syn, info_errors=int(f0_info), decoded_sha256=gd.bits_sha(dec0['decoded']),
   332	                               ldpc_iters=int(dec0['iterations']), seconds=f0_seconds),
   333	                       g4a_ok=bool(g4a_ok), ledger=ledger,
   334	                       f0_matches_ledger=bool(gd.bits_sha(dec0['decoded']) == u['f0_sha'] and syn == u['f0_syndrome']),
   335	                       r1=dict(delays=[int(x) for x in np.asarray(arrays['r1_delays'])],
    16	
    17	HERE = Path(__file__).resolve().parent
    18	EXP = HERE.parent
    19	sys.path.insert(0, str(EXP / 'unified_cov_prospective_20261119'))
    20	sys.path.insert(0, str(EXP / 'sp_afdm_frozen_20260920' / 'src'))
    21	
    22	FRAMES = range(41000, 41400)
    23	SCENARIOS = ('U', 'G')
    24	RHOS = (50, 100, 150, 200, 250, 300)
    25	SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    26	ARMS = ('base', 'delay')
    27	FRAMES_PER_SHARD = 5
    28	WORKERS = 32
    29	TAU = 0.2
    30	BOOT, SEED, GATE_DB = 2000, 20261121, 0.3
    31	_C = None
    32	
    33	
    34	def setup():
    35	    global _C
    36	    if _C is None:
    37	        import cstate
    38	        from physical import regressors
    39	        ctx, full, cd, _ = cstate.context()
    40	        s = ctx.system; lmax = int(s.l_max_cap)
    41	        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
    42	        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
    43	        _C = dict(stage3=cstate.stage3, ctx=ctx, cd=cd, U=U / np.linalg.norm(U, axis=0, keepdims=True),
    44	                  lmax=lmax, orig_front=ctx.native.pilot_front)
    45	    return _C
    46	
    47	
    48	def f0(C, obs, inject=None):
    49	    """F0 with an optional round-0 support override; the native module's pilot_front is restored afterwards."""
    50	    ctx, orig = C['ctx'], C['orig_front']
    51	    if inject is None:
    52	        return C['stage3'].e1.f0_state(ctx, obs)
    53	
    54	    def front(observed, system, code):
    55	        s = orig(observed, system, code)
    56	        ls, ks, gs = inject
    57	        gs = np.ones(len(ls), complex) if gs is None else np.asarray(gs, complex)
    58	        return dict(s, delays=np.asarray(ls, int), dopplers=np.asarray(ks, float), gains=gs)
    59	    ctx.native.pilot_front = front
    60	    try:
    61	        return C['stage3'].e1.f0_state(ctx, obs)
    62	    finally:
    63	        ctx.native.pilot_front = orig
    64	
    65	
    66	def support_stats(delays, dopplers, truth, sigma2):
    67	    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.abs(np.asarray(truth['g_i'])) ** 2
    68	    rel = g >= TAU * sigma2
    69	    have = set(int(d) for d in delays)
    70	    miss = float(sum(g[i] for i in range(len(l)) if rel[i] and l[i] not in have))
    71	    err, wsum = 0.0, 0.0
    72	    for i in range(len(l)):
    73	        if l[i] in have:
    74	            cand = [float(dopplers[k]) for k, d in enumerate(delays) if int(d) == l[i]]
    75	            err += g[i] * min(abs(c - nu[i]) for c in cand); wsum += g[i]
    76	    return dict(missing_power=miss, doppler_err=err / wsum if wsum else None,
    77	                support_right=bool(all(l[i] in have for i in range(len(l)) if rel[i])))
    78	
    79	
    80	def one_arm(C, obs, truth, inject):
    81	    ctx, stage3 = C['ctx'], C['stage3']
    82	    dec, arrays, syndrome, _ = f0(C, obs, inject)
    83	    s2 = float(obs['sigma2'])
    84	    rec = dict(syndrome=int(syndrome),
    85	               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
    86	               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
    87	               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
    88	               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    89	    if syndrome:
    90	        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
    91	        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    92	        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    93	    else:
    94	        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    95	    return rec
    96	
    97	
    98	def genie_inject(C, obs, truth):
    99	    z5 = (np.abs(C['U'].conj().T @ obs['y']) ** 2).reshape(C['lmax'] + 1, 5)
   100	    ls = [int(d) for d in truth['l_i']]
   101	    return ls, [int(np.argmax(z5[d])) - 2 for d in ls], None
   102	
   103	
   104	def run_key(C, base, s_, rho, snr, frame):
   105	    stage3 = C['stage3']
   106	    raw, obs, truth = stage3.observed(C['ctx'], base, rho, snr)
   107	    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
   108	                arms=dict(base=one_arm(C, obs, truth, None), delay=one_arm(C, obs, truth, genie_inject(C, obs, truth))))
    45	        for line in handle:
    46	            yield json.loads(line)
    47	
    48	
    49	def context():
    50	    ctx = e1.p1ctx.load()
    51	    checked = e1.check_frozen_md5(ctx)
    52	    if any(r['status'] != 'ok' for r in checked.values()):
    53	        raise AssertionError('E-1 source inventory did not pass')
    54	    if {name: ctx.source_md5[name] for name in P1_MD5} != P1_MD5:
    55	        raise AssertionError('P1 imports differ from the historical SBL archives')
    56	    full = e1.load_variant()
    57	    route = codelay.load(full)
    58	    return ctx, full, route, checked
    59	
    60	
    61	def key_of(row):
    62	    return tuple(row[field] for field in e1.KEY_FIELDS)
    63	
    64	
    65	def main_keys():
    66	    return {(s, rho, snr, frame) for frame in MAIN_FRAMES for s, rho in CELLS for snr in GRID[rho]}
    67	
    68	
    69	def inputs(ctx, frame, scenario, rho):
    70	    raw, diag = e1.p1ctx.base(ctx, scenario, rho/1000, frame)
    71	    return raw, diag
    72	
    73	
    74	def observed(ctx, base, rho, snr):
    75	    raw, obs, truth = e1.gd.observe(ctx, *base, rho/1000, snr)
    76	    return raw, obs, truth
    77	
    78	
    79	def digest(a):
    80	    a = np.asarray(a)
    81	    h = hashlib.sha256()
    82	    h.update(str(a.dtype).encode())
    83	    h.update(repr(a.shape).encode())
    84	    h.update(np.ascontiguousarray(a).tobytes())
    85	    return h.hexdigest()
    86	
    87	
    88	def truth_record(obs, truth):
    89	    return dict(sigma2=float(obs['sigma2']), delays=truth['l_i'].tolist(),
    90	                dopplers=truth['k_real'].tolist(),
    91	                gains=[[float(g.real), float(g.imag)] for g in truth['g_i']])
    92	
    93	
    94	def decoded(ctx, output, truth):
    95	    bits = output['decoded']
    96	    errors = e1.gd.score(ctx, bits, truth)
    97	    return dict(errors=int(errors), decoded_sha=e1.gd.bits_sha(bits))

exec
/bin/zsh -lc "sed -n '1,120p' experiments/huang_steelman_20261124/out/timing.log; sed -n '1,60p' experiments/sameframe_hg_20261124/out/run.log; sed -n '1,65p' experiments/sameframe_hg_20261124/out/results.json; rg -n '13,735|13735|LOW_SNRS' experiments/sameframe_hg_20261124/{PROTOCOL.md,sameframe.py}" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
/home/guoyikun/.conda/envs/AFDM/bin/python
Quiet timing running on pre-pinned CPU {'idle_cpu': 0, 'measured_utilization_pct': 0.0, 'load': [2.705078125, 3.826171875, 5.935546875]}
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Timing 25/100 done in 63.1s
Timing 50/100 done in 98.5s
Timing 75/100 done in 134.4s
Timing 100/100 done in 171.8s
TIMING_DONE wall=171.8s CD_med=158.8ms HG_med=523.5ms HG/CD_med_ratio=3.310x
/home/guoyikun/.conda/envs/AFDM/bin/python
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Launching Part 1: 13735 triggered keys on 24 workers (rhos=(100, 150, 200, 250), hgint=True)...
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Part1 shard 020 done (481 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Part1 shard 011 done (533 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Part1 shard 023 done (530 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
Part1 shard 017 done (554 triggered keys)
AFDM System initialized: N_total=1024 subcarriers (from 32x32)
  Chirp parameters: c1=0.002441, c2=0.000000
  Caps: l_max=15, k_max=2, delta_max=77 < N=1024: OK
  UWA params: fc=12.0 kHz, B=4.0 kHz, fs=8.0 kHz, Ts=125.0 us
  UWA channel: P=10, tau_spread=10.0 ms, v_mean=2.00 m/s, v_std=0.50 m/s
  Supported AFDM delay window: 1.0 ms
  Backward-compat speed cap: 12.6 km/h
  Channel matrix size: 1024x1024
[_make_system_variable_N] N_total=1024  l_max=102  k_max=4  δ_max=922  < N: True  c1=0.004395  c2=1.98e-07
{
  "_argv": [
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py",
    "run",
    "--out",
    "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/out",
    "--freeze-commit",
    "918a24747f7c37490b78df6b0754a70323bae9b2",
    "--workers",
    "24"
  ],
  "_config": {
    "freeze_commit": "918a24747f7c37490b78df6b0754a70323bae9b2",
    "python_executable": "/home/guoyikun/.conda/envs/AFDM/bin/python",
    "own_md5": {
      "PROTOCOL.md": "f781574e46f2a19c1536e492f601e2de",
      "sameframe.py": "01197778b2ec3cf7f37719ca3b192152",
      "test_sameframe.py": "4fbfdd1bbe562680828bd92f649daf71",
      "launch.sh": "99bd9c215f5d86024c15aae64d291abe"
    },
    "gate_md5": "cef0f75f495ecd75a6494a95fa64af7f",
    "part1_rhos": [
      100,
      150,
      200,
      250
    ],
    "include_hgint": true,
    "part1_frames": [
      41000,
      41399
    ],
    "part1_triggered_keys": 13735,
    "part2_frames": [
      5400,
      5799
    ],
    "part2_triggered_keys": 18009,
    "archive_manifest_sha256": {
      "stageA": "30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68",
      "stageA2": "5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354",
      "stageA3": "6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a",
      "rho_sweep": "98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd",
      "huang": "b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc"
    },
    "raw_output_dir": "/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/out/raw",
    "raw_rows_md5": {
      "part1_shard000.jsonl.gz": "09d59b9ec5ba7663bccd9166645ec597",
      "part1_shard001.jsonl.gz": "08c23ccd454ce0276306211e119aa7ac",
      "part1_shard002.jsonl.gz": "3f851b7b1a00ddc4af1de97ed7a94026",
      "part1_shard003.jsonl.gz": "3573b7de48504f7ad6cc8fa4581bf86d",
      "part1_shard004.jsonl.gz": "69303777aa05dbd9aac746941eb6770e",
      "part1_shard005.jsonl.gz": "15fa8d2d1f8c18f1a11b31c34071226b",
      "part1_shard006.jsonl.gz": "1853c44b15cae7a6a8929f3053dad791",
      "part1_shard007.jsonl.gz": "d89cb1768402105a29d47600986e81ac",
      "part1_shard008.jsonl.gz": "2f40e260b416afa395cfaf31dcab0121",
      "part1_shard009.jsonl.gz": "e1a826f534b5e6cf1a928ec780f9ed21",
      "part1_shard010.jsonl.gz": "bb5190c29ef44009e09bbac3df74798f",
      "part1_shard011.jsonl.gz": "21d8bc0b7f40599b26e1a294af906b8e",
      "part1_shard012.jsonl.gz": "3ff280398625bd144338dda6ad133e23",
      "part1_shard013.jsonl.gz": "0811b488889abda5501a0a6e62e20f84",
      "part1_shard014.jsonl.gz": "3ef8f8391122bf6248bdfef3be557077",
      "part1_shard015.jsonl.gz": "122d9e5c4b00d9cb7bc69ddeacdb92ff",
      "part1_shard016.jsonl.gz": "00633d963647616ca7647b3cd5063d9b",
      "part1_shard017.jsonl.gz": "75f76cd274ee7da62236c1c0965b1fbe",
experiments/sameframe_hg_20261124/PROTOCOL.md:21:  - Grid: $\rho \in \{100, 150, 200, 250\}$ permille, `SNR = stageA.SNRS` (`300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200` centi-dB; 13 points). Total 41,600 keys; `13,735` archived F0-triggered keys (`rho=100: 5,676; 150: 3,526; 200: 2,377; 250: 2,156`).
experiments/sameframe_hg_20261124/PROTOCOL.md:47:- **G4 (Stratified cost projection, 30% margin, $\le 16$ core-hours)**: Measure real CPU time on stratified triggered keys in Part 1 (`4 rhos × 2 SNR bands × 4 keys = 32` keys, balanced U/G at interior SNR quantiles) and Part 2 (`6 rhos × 2 SNR bands × 4 keys = 48` keys, balanced U/G at interior SNR quantiles), weighted by the exact archived stratum trigger counts (`13,735` Part-1 + `18,009` Part-2), plus `0.25` core-hours I/O & analysis allowance, multiplied by `1.3×`.

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '142,171p'; nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '556,596p;958,1004p'; rg -n -C 1 '\"stageA["'^" ]*"|"sameframe.py"'"' experiments/sameframe_hg_20261124/out/gate.json experiments/data_pilot_fer_20261121/out/stageA*/RUN_CONFIG.json -m 5" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   142	    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
   143	    frames = set(range(args.frame_offset, args.frame_offset + args.frames))
   144	    ledger = load_ledger(args.p1_rows, frames, set(snr_cells))
   145	    keys = sorted(k for k, v in ledger.items() if v['triggered'])
   146	    table = {}
   147	    for k in keys:
   148	        cell = f'{k[0]}_rho{k[1]}'
   149	        table.setdefault(cell, {}).setdefault(str(k[2]), 0)
   150	        table[cell][str(k[2])] += 1
   151	    files = sorted(glob.glob(str(Path(args.p1_rows) / 'rows_shard*.jsonl.gz')))
   152	    out = dict(_argv=list(argv), snr_cells=snr_cells, frames=[args.frame_offset, args.frame_offset + args.frames],
   153	               ledger_scanned_rows=len(ledger), n_triggered=len(keys), per_cell_snr=table,
   154	               ledger_files_md5={Path(p).name: e1_lib.md5_file(p) for p in files},
   155	               units=[dict(scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3], **ledger[k]) for k in keys])
   156	    args.out.mkdir(parents=True, exist_ok=True)
   157	    (args.out / 'triggered_keys.json').write_text(json.dumps(out, indent=1) + '\n')
   158	    print(f'select: {len(keys)} triggered of {len(ledger)} ledger rows; per cell/snr {json.dumps(table)}')
   159	
   160	
   161	# ----------------------------------------------------------------------------- F0 state + branch
   162	def receive_state(ctx, obs, rounds):
   163	    t0 = time.perf_counter()
   164	    dec, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=rounds, iterations=20, ce_mode='soft', gain_mode='joint')
   165	    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
   166	    return dec, arrays, syn, time.perf_counter() - t0
   167	
   168	
   169	def f0_state(ctx, obs):
   170	    return receive_state(ctx, obs, 2)
   171	
   556	    p1_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   557	    for k, v in stageA_base.items():
   558	        if v['syndrome'] != 0:
   559	            band = 'low' if k[2] <= 400 else 'mid'
   560	            p1_strata.setdefault((k[1], band), []).append(k)
   561	    g1_jobs = []
   562	    for rho in PART1_RHOS:
   563	        picks = []
   564	        for band in ('low', 'mid'):
   565	            for scen in ('U', 'G'):
   566	                pool = sorted((k for k in p1_strata[(rho, band)] if k[0] == scen), key=lambda k: (k[2], k[3]))
   567	                picks.append(pool[len(pool) // 2])
   568	        # 5th key from mid band (higher SNR interior)
   569	        extra_pool = sorted(p1_strata[(rho, 'mid')], key=lambda k: (k[2], k[3]))
   570	        picks.append(next(k for k in extra_pool[len(extra_pool) * 3 // 4:] if k not in picks))
   571	        for s, r, snr, f in picks:
   572	            v = stageA_base[(s, r, snr, f)]
   573	            g1_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors']])
   574	
   575	    # G3: 20 triggered rho_sweep keys across all 6 rhos (mix of CD pass-1 pass and fail)
   576	    p2_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   577	    for k, r in rho_arch.items():
   578	        if r['triggered']:
   579	            band = 'low' if k[2] <= 400 else 'mid'
   580	            p2_strata.setdefault((k[1], band), []).append(k)
   581	    g3_jobs = []
   582	    for rho in ar.RHOS:
   583	        all_r = sorted(p2_strata[(rho, 'low')] + p2_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   584	        fails = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) > 0]
   585	        passes = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) == 0]
   586	        picks = [fails[0], fails[len(fails) // 2], passes[0]] + ([passes[-1]] if rho in (200, 300) else [])
   587	        for k in picks:
   588	            cd_arch = rho_arch[k]['arms']['CD']
   589	            g3_jobs.append(dict(
   590	                key=list(k),
   591	                CD=dict(errors=int(cd_arch['errors']), decoded_sha=cd_arch['decoded_sha']),
   592	            ))
   593	    g3_jobs = g3_jobs[:20]
   594	
   595	    # G4 stratified samples (4 per stratum = 2 U + 2 G at 25%/75% SNR quantiles for BOTH Part 1 and Part 2)
   596	    g4_p1_picks = _select_balanced_keys(p1_strata, per_stratum=4)  # 4 rhos * 2 bands * 4 = 32 keys
   958	                u_lo, u_hi = crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   959	                g_lo, g_hi = crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   960	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   961	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   962	                if bi == 0:
   963	                    scen_pt['U'][str(rho)] = _rep(u_lo) if u_lo == u_hi else [_rep(u_lo), _rep(u_hi)]
   964	                    scen_pt['G'][str(rho)] = _rep(g_lo) if g_lo == g_hi else [_rep(g_lo), _rep(g_hi)]
   965	        arm_lo[arm] = lo_arr
   966	        arm_hi[arm] = hi_arr
   967	        arm_scen_pt[arm] = scen_pt
   968	        arm_mean_pt[arm] = {
   969	            str(rho): (_rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [_rep(lo_arr[0, ri]), _rep(hi_arr[0, ri])])
   970	            for ri, rho in enumerate(rhos)
   971	        }
   972	        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; full/ldop/delay over 100..200; base over all
   973	        if arm in ('delay', 'full', 'ldop'):
   974	            sub_idx = [i for i, r in enumerate(rhos) if 100 <= r <= 200]
   975	        else:
   976	            sub_idx = list(range(n_r))
   977	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   978	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   979	        best_pos = int(np.argmin(hi_arr[0, sub_idx]))
   980	        arm_best_rho[arm] = int(rhos[sub_idx[best_pos]])
   981	
   982	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   983	        # D = min_rho arm_a - min_rho arm_b (conservative bounds; collapses to exact diff when finite)
   984	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   985	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   986	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   987	        if cens_frac == 0.0:
   988	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   989	        else:
   990	            lo = an._nearest_rank(d_lo[1:], 0.025)
   991	            hi = an._nearest_rank(d_hi[1:], 0.975)
   992	        pt = _rep(d_lo[0]) if d_lo[0] == d_hi[0] else [_rep(d_lo[0]), _rep(d_hi[0])]
   993	        return dict(
   994	            point_db=pt,
   995	            ci95_db=[_rep(lo), _rep(hi)],
   996	            censored_draw_fraction=cens_frac,
   997	            arm_a_best_db=_rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [_rep(arm_best_lo[arm_a][0]), _rep(arm_best_hi[arm_a][0])],
   998	            arm_a_best_rho=arm_best_rho[arm_a],
   999	            arm_b_best_db=_rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [_rep(arm_best_lo[arm_b][0]), _rep(arm_best_hi[arm_b][0])],
  1000	            arm_b_best_rho=arm_best_rho[arm_b],
  1001	        )
  1002	
  1003	    primary_p1 = contrast('HG', 's100')
  1004	    p1_lo = float(primary_p1['ci95_db'][0]) if isinstance(primary_p1['ci95_db'][0], float) else (-math.inf if primary_p1['ci95_db'][0] == '-inf' else math.inf)
experiments/data_pilot_fer_20261121/out/stageA2/RUN_CONFIG.json-2- "_argv": [
experiments/data_pilot_fer_20261121/out/stageA2/RUN_CONFIG.json:3:  "stageA2.py",
experiments/data_pilot_fer_20261121/out/stageA2/RUN_CONFIG.json-4-  "run",
--
experiments/data_pilot_fer_20261121/out/stageA/RUN_CONFIG.json-2- "_argv": [
experiments/data_pilot_fer_20261121/out/stageA/RUN_CONFIG.json:3:  "stageA.py",
experiments/data_pilot_fer_20261121/out/stageA/RUN_CONFIG.json-4-  "run",
--
experiments/sameframe_hg_20261124/out/gate.json-23-      "PROTOCOL.md": "f781574e46f2a19c1536e492f601e2de",
experiments/sameframe_hg_20261124/out/gate.json:24:      "sameframe.py": "01197778b2ec3cf7f37719ca3b192152",
experiments/sameframe_hg_20261124/out/gate.json-25-      "test_sameframe.py": "4fbfdd1bbe562680828bd92f649daf71",
--
experiments/sameframe_hg_20261124/out/gate.json-107-      "run_validation": "3bf475ab8e15d855e7bfbefd387bfdac",
experiments/sameframe_hg_20261124/out/gate.json:108:      "stageA": "17be1c3e75e07fb9a4dec1b3774c54aa",
experiments/sameframe_hg_20261124/out/gate.json:109:      "stageA2": "01a72e6942ec39de99c0e788b3b5b0a9",
experiments/sameframe_hg_20261124/out/gate.json-110-      "structured_ep": "19194ff3dbd3ddda4923cf247ba92c9a",
--
experiments/sameframe_hg_20261124/out/gate.json-113-    "archive_manifest_sha256": {
experiments/sameframe_hg_20261124/out/gate.json:114:      "stageA": "30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68",
experiments/sameframe_hg_20261124/out/gate.json:115:      "stageA2": "5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354",
experiments/sameframe_hg_20261124/out/gate.json:116:      "stageA3": "6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a",
--
experiments/data_pilot_fer_20261121/out/stageA4/RUN_CONFIG.json-2- "_argv": [
experiments/data_pilot_fer_20261121/out/stageA4/RUN_CONFIG.json:3:  "stageA4.py",
experiments/data_pilot_fer_20261121/out/stageA4/RUN_CONFIG.json-4-  "run",
--
experiments/data_pilot_fer_20261121/out/stageA3/RUN_CONFIG.json-2- "_argv": [
experiments/data_pilot_fer_20261121/out/stageA3/RUN_CONFIG.json:3:  "stageA3.py",
experiments/data_pilot_fer_20261121/out/stageA3/RUN_CONFIG.json-4-  "run",

exec
/bin/zsh -lc "nl -ba experiments/sameframe_cd2_20261125/launch.sh | sed -n '12,50p;60,123p'; rg -n 'USE_SHM|SharedMemory|mp\\.(Pool|Queue|Manager)|mp_context\\.(Pool|Queue|Manager)' experiments/sameframe_cd2_20261125 experiments/sameframe_hg_20261124 -g '*.py'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 exited 1 in 0ms:
    12	HERE="$REPO/experiments/sameframe_cd2_20261125"
    13	OUT="$HERE/out"
    14	mkdir -p "$OUT" /data/guoyikun/tmp/.cache/torch/kernels
    15	
    16	LOCKDIR="$OUT/.lock"
    17	if ! mkdir "$LOCKDIR" 2>/dev/null; then
    18	    echo "ERROR: lock $LOCKDIR already held" >&2
    19	    exit 1
    20	fi
    21	
    22	cd "$REPO"
    23	set +u
    24	source /opt/anaconda3/etc/profile.d/conda.sh
    25	conda activate AFDM
    26	set -u
    27	
    28	PY="/home/guoyikun/.conda/envs/AFDM/bin/python"
    29	if [ "$(which python)" != "$PY" ]; then
    30	    rmdir "$LOCKDIR" 2>/dev/null || true
    31	    echo "ERROR: active python $(which python) != $PY" >&2
    32	    exit 1
    33	fi
    34	
    35	export PYTHONDONTWRITEBYTECODE=1
    36	export CUDA_VISIBLE_DEVICES=""
    37	export TMPDIR="/data/guoyikun/tmp"
    38	export XDG_CACHE_HOME="/data/guoyikun/tmp/.cache"
    39	export OMP_NUM_THREADS=1
    40	export OPENBLAS_NUM_THREADS=1
    41	export MKL_NUM_THREADS=1
    42	export NUMEXPR_NUM_THREADS=1
    43	export BLIS_NUM_THREADS=1
    44	export VECLIB_MAXIMUM_THREADS=1
    45	
    46	if [ "$MODE" = "gate" ]; then
    47	    trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
    48	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/gate_cpu.txt" \
    49	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/sameframe_cd2.py" \
    50	        gate --out "$OUT" --workers 16 \
    60	    fi
    61	    status=STOPPED
    62	    cleanup() {
    63	        printf "%s\n" "$status" > "$OUT/STATUS.$$.part"
    64	        mv -f -- "$OUT/STATUS.$$.part" "$OUT/STATUS"
    65	        rmdir "$LOCKDIR" 2>/dev/null || true
    66	    }
    67	    trap cleanup EXIT
    68	
    69	    # Part A: Python enforces cumulative CPU <= 6.0 core-hours; wall cap 1800s outer safety net
    70	    set +e
    71	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/partA_cpu.txt" \
    72	        timeout --kill-after=5s 1800s "$PY" -B -u "$HERE/sameframe_cd2.py" \
    73	        partA --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    74	        > "$OUT/partA.log" 2>&1
    75	    rc=$?
    76	    set -e
    77	    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    78	        status=STOPPED_BUDGET
    79	        exit 124
    80	    fi
    81	    if [ "$rc" -ne 0 ]; then
    82	        exit "$rc"
    83	    fi
    84	    test -s "$OUT/results.json"
    85	
    86	    # Part B: Pick quietest idle CPU BEFORE starting Python, then pin via taskset
    87	    read -r QUIET_CPU QUIET_UTIL < <("$PY" -c '
    88	import os, time
    89	from pathlib import Path
    90	def rd():
    91	    d = {}
    92	    for ln in Path("/proc/stat").read_text().splitlines():
    93	        n, *v = ln.split()
    94	        if n.startswith("cpu") and n[3:].isdigit():
    95	            f = [int(x) for x in v[:8]]
    96	            d[int(n[3:])] = (sum(f), f[3] + f[4])
    97	    return d
    98	a = rd(); time.sleep(1.0); b = rd()
    99	u = {c: 100.0 * ((b[c][0]-a[c][0]) - (b[c][1]-a[c][1])) / max(b[c][0]-a[c][0], 1) for c in os.sched_getaffinity(0)}
   100	best = min(u, key=lambda c: (u[c], c))
   101	print(best, f"{u[best]:.2f}")
   102	')
   103	    export HS_QUIET_CPU_UTIL="$QUIET_UTIL"
   104	
   105	    set +e
   106	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/timing_cpu.txt" \
   107	        timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/sameframe_cd2.py" \
   108	        timing --out "$OUT" --freeze-commit "$FREEZE_COMMIT" \
   109	        > "$OUT/timing.log" 2>&1
   110	    trc=$?
   111	    set -e
   112	    if [ "$trc" -eq 124 ] || [ "$trc" -eq 137 ]; then
   113	        status=STOPPED_BUDGET
   114	        exit 124
   115	    fi
   116	    if [ "$trc" -ne 0 ]; then
   117	        exit "$trc"
   118	    fi
   119	    test -s "$OUT/timing_summary.json"
   120	    test -s "$OUT/RESULTS.md"
   121	    status=DONE
   122	    exit 0
   123	fi

codex
**先修再启动。** 静态核对确认 Part A 的帧、网格、未触发键取值和触发键逐键断言符合协议。主检验共用同一组物理帧做 2,000 次配对重采样，种子 `20261125`，两侧最优导频比例范围和 `0.5 dB` 判定边界正确。Part B 的两组抽样、分场景五臂轮换、解码哈希比对和摊销公式也符合协议。

1. **截断结果会使 Part A 崩溃。** 主估计量触及信噪比网格边界时，`point_db` 可以是区间，完成日志却用 `:.4f` 格式化它。结果文件写出后仍会抛出 `TypeError`，导致启动脚本跳过 Part B。现有测试只覆盖有限点估计。 [完成日志](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:778) · [测试](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/test_sameframe_cd2.py:39)
2. **G2 可以漏测 `CD2e8` 的首遍早停。** 门禁只要求 `CD2e8` 至少跑过一次第二遍，即使 20 键全跑两遍也能通过。应对两个实验臂分别断言两条路径都走过。 [G2 判定](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:304)
3. **6 核时上限可以被越过。** G3 的 `1.3×` 外推和先从 Part A 去掉 `CD2e8` 的顺序正确。运行时，分片每 10 秒查一次，汇总结束后才查预算，Part B 也要等整帧测完才查。接近上限时均可先超支再退出。启动脚本还会把普通墙钟超时标成预算耗尽。 [分片预算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:848) · [汇总检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:737) · [退出状态](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/launch.sh:69)
4. **计时还有两处口径偏差。** `taskset` 在 Python 启动前绑定单核，但即使所有核都很忙，仍会选占用最低的核继续。`CD` 的计时还纳入了输入有限性检查，冻结计时器把这两项放在起表前。应明确空闲判定并统一起表位置。 [选核](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/launch.sh:86) · [新计时器](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:141) · [冻结计时器](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:456)
5. **部署可以静默跳过冻结提交校验。** 远端若没有 Git 工作树，校验函数返回 `False`，调用方仍继续。应在该部署路径核对冻结文件清单，至少覆盖新实验文件及直接复用的 `sameframe.py`、`stageA*`。 [冻结校验](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:94)

工作目录、AFDM 解释器、单线程与禁用 GPU 配置、16/24 进程及文件式进程通信均符合启动约束。`_argv`、`_config`、原始计时行的 MD5 和原子替换写入均有实现。此次只做静态审查，远端原始分片和实际计时未运行核验。

VERDICT: FIX
hook: Stop
hook: Stop Completed
tokens used
113,209
**先修再启动。** 静态核对确认 Part A 的帧、网格、未触发键取值和触发键逐键断言符合协议。主检验共用同一组物理帧做 2,000 次配对重采样，种子 `20261125`，两侧最优导频比例范围和 `0.5 dB` 判定边界正确。Part B 的两组抽样、分场景五臂轮换、解码哈希比对和摊销公式也符合协议。

1. **截断结果会使 Part A 崩溃。** 主估计量触及信噪比网格边界时，`point_db` 可以是区间，完成日志却用 `:.4f` 格式化它。结果文件写出后仍会抛出 `TypeError`，导致启动脚本跳过 Part B。现有测试只覆盖有限点估计。 [完成日志](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:778) · [测试](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/test_sameframe_cd2.py:39)
2. **G2 可以漏测 `CD2e8` 的首遍早停。** 门禁只要求 `CD2e8` 至少跑过一次第二遍，即使 20 键全跑两遍也能通过。应对两个实验臂分别断言两条路径都走过。 [G2 判定](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:304)
3. **6 核时上限可以被越过。** G3 的 `1.3×` 外推和先从 Part A 去掉 `CD2e8` 的顺序正确。运行时，分片每 10 秒查一次，汇总结束后才查预算，Part B 也要等整帧测完才查。接近上限时均可先超支再退出。启动脚本还会把普通墙钟超时标成预算耗尽。 [分片预算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:848) · [汇总检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:737) · [退出状态](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/launch.sh:69)
4. **计时还有两处口径偏差。** `taskset` 在 Python 启动前绑定单核，但即使所有核都很忙，仍会选占用最低的核继续。`CD` 的计时还纳入了输入有限性检查，冻结计时器把这两项放在起表前。应明确空闲判定并统一起表位置。 [选核](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/launch.sh:86) · [新计时器](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:141) · [冻结计时器](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/hs_arms.py:456)
5. **部署可以静默跳过冻结提交校验。** 远端若没有 Git 工作树，校验函数返回 `False`，调用方仍继续。应在该部署路径核对冻结文件清单，至少覆盖新实验文件及直接复用的 `sameframe.py`、`stageA*`。 [冻结校验](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_cd2_20261125/sameframe_cd2.py:94)

工作目录、AFDM 解释器、单线程与禁用 GPU 配置、16/24 进程及文件式进程通信均符合启动约束。`_argv`、`_config`、原始计时行的 MD5 和原子替换写入均有实现。此次只做静态审查，远端原始分片和实际计时未运行核验。

VERDICT: FIX
