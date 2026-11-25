2026-11-24T15:42:16.535707Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/archive-doc/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T15:42:16.536606Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/context-pack/SKILL.md: missing YAML frontmatter delimited by ---
2026-11-24T15:42:16.536614Z ERROR codex_core::session::session: failed to load skill /Users/guoyikun/Downloads/share/claode_birain/my-vault/.agents/skills/restructure-doc/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.170.0
--------
workdir: /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
model: gpt-6.2-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 01a20e38-cd06-7b90-8359-fcb98fa0907b
--------
user
You are Sol performing a concise (<= 3 min) pre-launch static review of `experiments/sameframe_hg_20261124/`:
- `PROTOCOL.md`
- `sameframe.py`
- `test_sameframe.py`
- `launch.sh`

Please check specifically:
1. Reuse & fidelity:
   - Part 1 reuses `stageA.py` (`setup`), `stageA2.py` (`crossing`, `load`), `hs_arms.py` (`run_hg_arm`, `fine_grid`, `coarse_grid`) without modifying any frozen files; triggers gated by archived `stageA` `arms.base.syndrome`, live F0 verified against archived `syndrome` and `f0_errors`.
   - Part 2 implements `CD2` (pass 1 = archived `CD` bit-exact; pass 2 updates `r1_delays`, `r1_dopplers`, `r1_gains`, `r1_check`, `r1_app` from pass 1 `result`/`decoder`, early stop on `syndrome == 0`) and `CD2e8` (`max_edits=8`, runtime-only `e1.ARM_SPECS['A1e8']`), reusing `hs_analysis.py` crossing & 36-pair projected CI.
2. Statistical & verdict logic:
   - P1 (`min HG (100..250) - min s100 (100..200)`): joint paired frame bootstrap (2000 draws, seed 20261124), 95% CI, censoring safety, `DOPPLER-LINE` (`>= 0.5`) / `WRITE-A` (`< 0.5`) / `INCONCLUSIVE`.
   - P2 (`CD2 - HG` and `CD2e8 - HG`): 98.33% 36-pair projected CI (plus 95% reported alongside), `STILL_BEHIND` (`> 0.2`) / `CATCHES_UP` (`< 0.2`) / `MIXED`.
3. Gates G1–G4, budget (<= 12 core-hours, 30% margin, drop order `HGint` -> `rho=250` -> stop), deinlab rules (`cd /data/guoyikun/00inbox/AFDM-channel-estimation`, AFDM python, single-thread env, `CUDA_VISIBLE_DEVICES=""`, `<= 32` workers, `/data/guoyikun/tmp`, zero `/dev/shm` semaphores, atomic writes, `_argv`/`_config`).
4. Any crash bugs, subtle key/index/schema mismatches, or silent fallbacks.

Be concise and end with `VERDICT: PASS` or `VERDICT: FIX`.

warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
warning: Codex is ignoring 2 unrecognized configuration settings. Check for typos or deprecated settings.
  user (/Users/guoyikun/.codex/config.toml): `disable_response_storage` is ignored.
  user (/Users/guoyikun/.codex/config.toml): `mcp_servers.claude-review.type` is ignored.
hook: SessionStart
hook: SessionStart Completed
hook: UserPromptSubmit
hook: UserPromptSubmit Completed
codex
自检：1 个红项（纠正记录（自检故障））；自查信号待复核 84 项，最早 2026-11-19，说“跑一次 L2”处理。等你处理：4 个红项（L0、Vault 工作树、复盘证据 等 4 项）（决定项见最近系统报告 2026-11-18）。详情见 vault 的 系统状态.md

我会用 `trellis-start` 确认项目上下文，再对照协议、实现、测试和启动脚本，优先找出会阻止启动或改变结论的问题。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'nl -ba experiments/sameframe_hg_20261124/sameframe.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
exec
/bin/zsh -lc 'nl -ba experiments/sameframe_hg_20261124/PROTOCOL.md; nl -ba experiments/sameframe_hg_20261124/launch.sh; nl -ba experiments/sameframe_hg_20261124/test_sameframe.py' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Same-frame decisive check: Part 1 (HG/HGint on 41000-41399) + Part 2 (CD2/CD2e8 on 5400-5799)."""
     2	from __future__ import annotations
     3	
     4	import argparse
     5	import gzip
     6	import hashlib
     7	import json
     8	import math
     9	import multiprocessing
    10	from multiprocessing.connection import wait
    11	import os
    12	from pathlib import Path
    13	import platform
    14	import re
    15	import resource
    16	import shutil
    17	import sys
    18	import time
    19	from typing import Any
    20	
    21	import numpy as np
    22	
    23	HERE = Path(__file__).resolve().parent
    24	EXP = HERE.parent
    25	DATA_PILOT_DIR = EXP / 'data_pilot_fer_20261121'
    26	HUANG_DIR = EXP / 'huang_steelman_20261124'
    27	RHO_SWEEP_DIR = EXP / 'rho_sweep_20261119'
    28	
    29	sys.path.insert(0, str(DATA_PILOT_DIR))
    30	sys.path.insert(0, str(HUANG_DIR))
    31	
    32	import hs_analysis as an  # noqa: E402
    33	import hs_arms as ar  # noqa: E402
    34	
    35	PART1_RHOS = (100, 150, 200, 250)
    36	PART1_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    37	PART1_FRAMES = tuple(range(41000, 41400))
    38	PART1_BOOT_DRAWS = 2000
    39	PART1_BOOT_SEED = 20261124
    40	P1_THRESHOLD_DB = 0.5
    41	P2_THRESHOLD_DB = 0.2
    42	
    43	ARCHIVE_MANIFESTS = {
    44	    'stageA': (DATA_PILOT_DIR / 'out' / 'stageA', '30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68'),
    45	    'stageA2': (DATA_PILOT_DIR / 'out' / 'stageA2', '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354'),
    46	    'stageA3': (DATA_PILOT_DIR / 'out' / 'stageA3', '6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a'),
    47	    'rho_sweep': (RHO_SWEEP_DIR / 'out' / 'main_20261119', ar.RHO_ARCHIVE_MD5_SHA256),
    48	    'huang': (HUANG_DIR / 'out', 'b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc'),
    49	}
    50	OWN_FILES = ('PROTOCOL.md', 'sameframe.py', 'test_sameframe.py', 'launch.sh')
    51	WORKERS = 24
    52	BUDGET_CAP_HOURS = 12.0
    53	BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
    54	COST_MARGIN = 1.3
    55	OVERHEAD_HOURS = 0.25
    56	BUDGET_EXIT_CODE = 124
    57	N_SHARDS = 24
    58	CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100
    59	
    60	
    61	def own_md5() -> dict[str, str]:
    62	    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}
    63	
    64	
    65	def verify_manifest(name: str) -> dict[str, str]:
    66	    base_dir, expected_sha = ARCHIVE_MANIFESTS[name]
    67	    manifest = base_dir / 'REMOTE_ROWS_MD5.txt'
    68	    got_sha = ar.sha256_file(manifest)
    69	    if got_sha != expected_sha:
    70	        raise RuntimeError(f'{name} manifest SHA-256 mismatch: {got_sha} != {expected_sha}')
    71	    raw_dir = base_dir / 'raw' if name == 'huang' else base_dir
    72	    out: dict[str, str] = {}
    73	    for line in manifest.read_text(encoding='utf-8').splitlines():
    74	        if not line.strip():
    75	            continue
    76	        digest, fname = line.split()
    77	        p = raw_dir / fname
    78	        if not p.is_file():
    79	            raise FileNotFoundError(f'Missing archive shard {p}')
    80	        actual = ar.md5_file(p)
    81	        if actual != digest:
    82	            raise RuntimeError(f'Archive shard MD5 mismatch {p}: {actual} != {digest}')
    83	        out[fname] = actual
    84	    return out
    85	
    86	
    87	def load_stage_runtime():
    88	    """Verify frozen MD5s first, then initialize via stageA.setup() and build hs_arms helpers."""
    89	    extra_md5 = ar.verify_frozen_extra_md5()
    90	    import stageA  # noqa: E402
    91	    import stageA2  # noqa: E402
    92	
    93	    C = stageA.setup()
    94	    stage3 = C['stage3']
    95	    # Register A1e8 (max_edits=8, local_passes=2, full Gamma) at runtime without modifying frozen files
    96	    stage3.e1.ARM_SPECS['A1e8'] = dict(gamma_mode='full', max_edits=8, local_passes=2)
    97	
    98	    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
    99	    from messages import moments
   100	    from physical import Channel
   101	    from twofft import time_refine
   102	
   103	    helpers = dict(
   104	        stage3=stage3,
   105	        cd=C['cd'],
   106	        BaselineInitializer=BaselineInitializer,
   107	        Channel=Channel,
   108	        moments=moments,
   109	        time_refine=time_refine,
   110	        extra_md5=extra_md5,
   111	    )
   112	    return C, stageA, stageA2, helpers
   113	
   114	
   115	def run_cd_two_pass(
   116	    ctx,
   117	    helpers: dict[str, Any],
   118	    obs: dict[str, Any],
   119	    arrays: dict[str, Any],
   120	    truth: dict[str, Any],
   121	    *,
   122	    arm_spec: str,
   123	    expected_pass1: dict[str, Any] | None = None,
   124	) -> dict[str, Any]:
   125	    """Run 1-to-2-pass CODELAY local exchange with syndrome early stop (same inter-pass update as HG)."""
   126	    stage3 = helpers['stage3']
   127	    cd = helpers['cd']
   128	    ar._require_finite(arrays['r1_check'], f'{arm_spec}.p1.r1_check')
   129	    ar._require_finite(arrays['r1_app'], f'{arm_spec}.p1.r1_app')
   130	
   131	    br1 = stage3.e1.run_branch(ctx, cd, obs, arrays, arm_spec)
   132	    res1 = br1['result']
   133	    if bool(res1.diagnostics.get('numerical_fallback')):
   134	        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 1')
   135	    ar._require_finite(res1.gains, f'{arm_spec}.p1.gains')
   136	    ar._require_finite(br1['detector']['extrinsic'], f'{arm_spec}.p1.extrinsic')
   137	    dec1 = br1['decoder']
   138	    ar._require_finite(dec1['raw_check_extrinsic'], f'{arm_spec}.p1.raw_check_extrinsic')
   139	    ar._require_finite(dec1['raw_app'], f'{arm_spec}.p1.raw_app')
   140	    d1 = stage3.decoded(ctx, dec1, truth)
   141	    syn1 = int(ctx.hd.syndrome_weight(ctx, dec1['decoded']))
   142	
   143	    if expected_pass1 is not None:
   144	        if d1['errors'] != int(expected_pass1['errors']) or d1['decoded_sha'] != expected_pass1['decoded_sha']:
   145	            raise RuntimeError(
   146	                f'{arm_spec} pass-1 mismatch vs archived CD: got {d1}, expected {expected_pass1}'
   147	            )
   148	
   149	    if syn1 == 0:
   150	        return dict(
   151	            errors=d1['errors'],
   152	            decoded_sha=d1['decoded_sha'],
   153	            syndrome=0,
   154	            passes_used=1,
   155	            pass1_errors=d1['errors'],
   156	            pass1_syndrome=0,
   157	            pass1_edits=len(res1.edits),
   158	            pass2_edits=0,
   159	            numerical_fallback=False,
   160	        )
   161	
   162	    arrays2 = dict(
   163	        r1_delays=np.array([int(p.delay) for p in res1.paths], dtype=int),
   164	        r1_dopplers=np.array([float(p.doppler) for p in res1.paths], dtype=float),
   165	        r1_gains=np.asarray(res1.gains, dtype=complex),
   166	        r1_check=dec1['raw_check_extrinsic'],
   167	        r1_app=dec1['raw_app'],
   168	    )
   169	    br2 = stage3.e1.run_branch(ctx, cd, obs, arrays2, arm_spec)
   170	    res2 = br2['result']
   171	    if bool(res2.diagnostics.get('numerical_fallback')):
   172	        raise FloatingPointError(f'Geometry numerical_fallback in {arm_spec} pass 2')
   173	    ar._require_finite(res2.gains, f'{arm_spec}.p2.gains')
   174	    ar._require_finite(br2['detector']['extrinsic'], f'{arm_spec}.p2.extrinsic')
   175	    dec2 = br2['decoder']
   176	    d2 = stage3.decoded(ctx, dec2, truth)
   177	    syn2 = int(ctx.hd.syndrome_weight(ctx, dec2['decoded']))
   178	
   179	    return dict(
   180	        errors=d2['errors'],
   181	        decoded_sha=d2['decoded_sha'],
   182	        syndrome=syn2,
   183	        passes_used=2,
   184	        pass1_errors=d1['errors'],
   185	        pass1_syndrome=syn1,
   186	        pass1_edits=len(res1.edits),
   187	        pass2_edits=len(res2.edits),
   188	        numerical_fallback=False,
   189	    )
   190	
   191	
   192	def load_stageA_base(rhos: tuple[int, ...] = PART1_RHOS) -> dict[tuple[str, int, int, int], dict[str, int]]:
   193	    """Load archived stageA arms.base (syndrome, f0_errors, errors) for requested rhos."""
   194	    base_dir = DATA_PILOT_DIR / 'out' / 'stageA'
   195	    out: dict[tuple[str, int, int, int], dict[str, int]] = {}
   196	    for p in sorted(base_dir.glob('rows_shard*.jsonl.gz')):
   197	        with gzip.open(p, 'rt', encoding='utf-8') as fh:
   198	            for line in fh:
   199	                r = json.loads(line)
   200	                rho = int(r['rho'])
   201	                if rho not in rhos:
   202	                    continue
   203	                k = (r['scenario'], rho, int(r['snr']), int(r['frame']))
   204	                b = r['arms']['base']
   205	                out[k] = dict(
   206	                    syndrome=int(b['syndrome']),
   207	                    f0_errors=int(b['f0_errors']),
   208	                    errors=int(b['errors']),
   209	                )
   210	    expected = len(PART1_FRAMES) * 2 * len(rhos) * len(PART1_SNRS)
   211	    if len(out) != expected:
   212	        raise RuntimeError(f'stageA base count mismatch: got {len(out)}, expected {expected}')
   213	    return out
   214	
   215	
   216	def _used_cpu_seconds() -> float:
   217	    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
   218	    return time.process_time() + ch.ru_utime + ch.ru_stime
   219	
   220	
   221	def _active_pids_cpu(pids: list[int]) -> float:
   222	    total = 0.0
   223	    for pid in pids:
   224	        try:
   225	            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
   226	            after = raw[raw.rfind(')') + 2:].split()
   227	            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
   228	        except OSError:
   229	            pass
   230	    return total
   231	
   232	
   233	def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
   234	    """File-IPC spawn worker pool (zero /dev/shm named semaphores)."""
   235	    n_workers = min(max_workers, max(1, len(items)))
   236	    buckets = [items[i::n_workers] for i in range(n_workers)]
   237	    mp_ctx = multiprocessing.get_context('spawn')
   238	    out_files = []
   239	    procs = []
   240	    for wi, bucket in enumerate(buckets):
   241	        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
   242	        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
   243	        in_f.write_text(json.dumps(bucket), encoding='utf-8')
   244	        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
   245	        p.start()
   246	        procs.append((wi, p))
   247	        out_files.append(out_f)
   248	    for wi, p in procs:
   249	        p.join()
   250	        code = p.exitcode
   251	        p.close()
   252	        if code != 0:
   253	            raise RuntimeError(f'Gate worker {tag}/{wi} exited with code {code}')
   254	    merged: list[tuple[int, Any]] = []
   255	    for wi, out_f in enumerate(out_files):
   256	        chunk = json.loads(out_f.read_text(encoding='utf-8'))
   257	        for pos, val in enumerate(chunk):
   258	            merged.append((wi + pos * n_workers, val))
   259	    merged.sort(key=lambda x: x[0])
   260	    return [v for _, v in merged]
   261	
   262	
   263	def _g1_worker(in_path: str, out_path: str):
   264	    C, _, _, helpers = load_stage_runtime()
   265	    stage3, ctx = C['stage3'], C['ctx']
   266	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   267	    res = []
   268	    for s, rho, snr, frame, exp_syn, exp_f0_err in jobs:
   269	        base = stage3.inputs(ctx, frame, s, rho)
   270	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   271	        dec, _, syn, _ = stage3.e1.f0_state(ctx, obs)
   272	        f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   273	        ok = bool(int(syn) == int(exp_syn) and f0_err == int(exp_f0_err) and int(syn) != 0)
   274	        if not ok:
   275	            raise AssertionError(
   276	                f'G1 F0 mismatch at {(s, rho, snr, frame)}: live=({syn},{f0_err}) != stageA=({exp_syn},{exp_f0_err})'
   277	            )
   278	        res.append(dict(key=[s, rho, snr, frame], syndrome=int(syn), f0_errors=f0_err, ok=True))
   279	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   280	
   281	
   282	def _g2_worker(in_path: str, out_path: str):
   283	    C, _, _, helpers = load_stage_runtime()
   284	    stage3, ctx = C['stage3'], C['ctx']
   285	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   286	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   287	    res = []
   288	    for item in jobs:
   289	        s, rho, snr, frame = item['key']
   290	        base = stage3.inputs(ctx, frame, s, rho)
   291	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   292	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   293	        if int(syn) == 0:
   294	            raise AssertionError(f'G2 key not triggered: {item["key"]}')
   295	        out = ar.run_hg_arm(
   296	            ctx, helpers, obs, arrays, truth,
   297	            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   298	            max_passes=2, record_match=False,
   299	        )
   300	        ok_hg = (
   301	            out['HG']['errors'] == item['HG']['errors']
   302	            and out['HG']['decoded_sha'] == item['HG']['decoded_sha']
   303	            and out['HG']['passes_used'] == item['HG']['passes_used']
   304	        )
   305	        ok_hg1 = (
   306	            out['HG1']['errors'] == item['HG1']['errors']
   307	            and out['HG1']['decoded_sha'] == item['HG1']['decoded_sha']
   308	        )
   309	        if not (ok_hg and ok_hg1):
   310	            raise AssertionError(f'G2 HG parity mismatch at {item["key"]}: got {out}, expected {item}')
   311	        res.append(dict(key=item['key'], passes_used=out['HG']['passes_used'], ok=True))
   312	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   313	
   314	
   315	def _g3_worker(in_path: str, out_path: str):
   316	    C, _, _, helpers = load_stage_runtime()
   317	    stage3, ctx = C['stage3'], C['ctx']
   318	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   319	    res = []
   320	    for item in jobs:
   321	        s, rho, snr, frame = item['key']
   322	        base = stage3.inputs(ctx, frame, s, rho)
   323	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   324	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   325	        if int(syn) == 0:
   326	            raise AssertionError(f'G3 key not triggered: {item["key"]}')
   327	        cd2 = run_cd_two_pass(
   328	            ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=item['CD'],
   329	        )
   330	        cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   331	        res.append(dict(
   332	            key=item['key'],
   333	            cd2_passes=cd2['passes_used'],
   334	            cd2_p1_err=cd2['pass1_errors'],
   335	            cd2_final_err=cd2['errors'],
   336	            cd2e8_passes=cd2e8['passes_used'],
   337	            cd2e8_final_err=cd2e8['errors'],
   338	            cd2e8_p1_edits=cd2e8['pass1_edits'],
   339	            cd2e8_p2_edits=cd2e8['pass2_edits'],
   340	            ok=True,
   341	        ))
   342	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   343	
   344	
   345	def _g4_part1_worker(in_path: str, out_path: str):
   346	    C, _, _, helpers = load_stage_runtime()
   347	    stage3, ctx = C['stage3'], C['ctx']
   348	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   349	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   350	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   351	    res = []
   352	    for s, rho, snr, frame, band in jobs:
   353	        t0 = time.process_time()
   354	        base = stage3.inputs(ctx, frame, s, rho)
   355	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   356	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   357	        t_f0 = time.process_time() - t0
   358	        if int(syn) == 0:
   359	            raise AssertionError(f'G4 part1 key untriggered: {(s, rho, snr, frame)}')
   360	        t1 = time.process_time()
   361	        hg = ar.run_hg_arm(
   362	            ctx, helpers, obs, arrays, truth,
   363	            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   364	            max_passes=2, record_match=False,
   365	        )
   366	        t_hg = time.process_time() - t1
   367	        t2 = time.process_time()
   368	        hgint = ar.run_hg_arm(
   369	            ctx, helpers, obs, arrays, truth,
   370	            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   371	            max_passes=2, record_match=False,
   372	        )
   373	        t_hgint = time.process_time() - t2
   374	        res.append(dict(
   375	            key=[s, rho, snr, frame], rho=rho, band=band,
   376	            f0_cpu=t_f0, hg_cpu=t_hg, hgint_cpu=t_hgint,
   377	            hg_passes=hg['HG']['passes_used'], hgint_passes=hgint['HG']['passes_used'],
   378	        ))
   379	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   380	
   381	
   382	def _g4_part2_worker(in_path: str, out_path: str):
   383	    C, _, _, helpers = load_stage_runtime()
   384	    stage3, ctx = C['stage3'], C['ctx']
   385	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   386	    res = []
   387	    for s, rho, snr, frame, band, arch_cd in jobs:
   388	        t0 = time.process_time()
   389	        base = stage3.inputs(ctx, frame, s, rho)
   390	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   391	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   392	        t_f0 = time.process_time() - t0
   393	        if int(syn) == 0:
   394	            raise AssertionError(f'G4 part2 key untriggered: {(s, rho, snr, frame)}')
   395	        t1 = time.process_time()
   396	        cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
   397	        t_cd2 = time.process_time() - t1
   398	        t2 = time.process_time()
   399	        cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   400	        t_cd2e8 = time.process_time() - t2
   401	        res.append(dict(
   402	            key=[s, rho, snr, frame], rho=rho, band=band,
   403	            f0_cpu=t_f0, cd2_cpu=t_cd2, cd2e8_cpu=t_cd2e8,
   404	            cd2_passes=cd2['passes_used'], cd2e8_passes=cd2e8['passes_used'],
   405	        ))
   406	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   407	
   408	
   409	def _select_balanced_keys(
   410	    keys_by_stratum: dict[tuple[int, str], list[tuple[str, int, int, int]]],
   411	    per_stratum: int,
   412	) -> list[tuple[str, int, int, int, str]]:
   413	    """Select balanced U/G and SNR-spread keys per (rho, band) deterministically."""
   414	    selected = []
   415	    for (rho, band), ks in sorted(keys_by_stratum.items()):
   416	        # Group by scenario and pick spread-out indices across sorted (snr, frame)
   417	        u_ks = sorted((k for k in ks if k[0] == 'U'), key=lambda k: (k[2], k[3]))
   418	        g_ks = sorted((k for k in ks if k[0] == 'G'), key=lambda k: (k[2], k[3]))
   419	        n_each = per_stratum // 2
   420	        picks = []
   421	        for pool in (u_ks, g_ks):
   422	            if len(pool) < n_each:
   423	                raise RuntimeError(f'Insufficient keys in stratum {(rho, band)}: {len(pool)} < {n_each}')
   424	            idxs = np.linspace(0, len(pool) - 1, n_each, dtype=int)
   425	            picks.extend(pool[int(i)] for i in idxs)
   426	        for s, r, snr, f in picks:
   427	            selected.append((s, r, snr, f, band))
   428	    return selected
   429	
   430	
   431	def cmd_gate(args):
   432	    print(sys.executable, flush=True)
   433	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   434	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   435	    thread_env = ar.check_thread_env()
   436	    started = time.monotonic()
   437	
   438	    manifests = {name: verify_manifest(name) for name in ARCHIVE_MANIFESTS}
   439	    C, _, _, helpers = load_stage_runtime()
   440	    ctx = C['ctx']
   441	
   442	    stageA_base = load_stageA_base(PART1_RHOS)
   443	    rho_arch, _ = ar.load_archived_rho_sweep()
   444	
   445	    # Load 5 archived huang_steelman HG keys (mix of U/G and 1-pass/2-pass stops)
   446	    g2_jobs = []
   447	    seen_p = set()
   448	    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
   449	        with p.open('r', encoding='utf-8') as fh:
   450	            for line in fh:
   451	                r = json.loads(line)
   452	                pu = int(r['arms']['HG']['passes_used'])
   453	                tag = (r['scenario'], pu)
   454	                if len(g2_jobs) < 5 and (tag not in seen_p or len(seen_p) >= 4):
   455	                    seen_p.add(tag)
   456	                    g2_jobs.append(dict(
   457	                        key=[r['scenario'], int(r['rho_permille']), int(r['snr_centi_db']), int(r['frame'])],
   458	                        HG=dict(
   459	                            errors=int(r['arms']['HG']['errors']),
   460	                            decoded_sha=r['arms']['HG']['decoded_sha'],
   461	                            passes_used=pu,
   462	                        ),
   463	                        HG1=dict(
   464	                            errors=int(r['arms']['HG1']['errors']),
   465	                            decoded_sha=r['arms']['HG1']['decoded_sha'],
   466	                        ),
   467	                    ))
   468	                if len(g2_jobs) >= 5:
   469	                    break
   470	        if len(g2_jobs) >= 5:
   471	            break
   472	    if len(g2_jobs) != 5:
   473	        raise RuntimeError(f'Expected 5 huang HG keys for G2, got {len(g2_jobs)}')
   474	
   475	    # G1: 20 triggered stageA keys (5 per rho in 100..250, balanced U/G & SNR)
   476	    p1_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   477	    for k, v in stageA_base.items():
   478	        if v['syndrome'] != 0:
   479	            band = 'low' if k[2] <= 400 else 'mid'
   480	            p1_strata.setdefault((k[1], band), []).append(k)
   481	    g1_jobs = []
   482	    for rho in PART1_RHOS:
   483	        trig = sorted(p1_strata[(rho, 'low')] + p1_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   484	        idxs = np.linspace(0, len(trig) - 1, 5, dtype=int)
   485	        for i in idxs:
   486	            s, r, snr, f = trig[int(i)]
   487	            v = stageA_base[(s, r, snr, f)]
   488	            g1_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors']])
   489	
   490	    # G3: 20 triggered rho_sweep keys across all 6 rhos (mix of CD pass-1 pass and fail)
   491	    p2_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   492	    for k, r in rho_arch.items():
   493	        if r['triggered']:
   494	            band = 'low' if k[2] <= 400 else 'mid'
   495	            p2_strata.setdefault((k[1], band), []).append(k)
   496	    g3_jobs = []
   497	    for rho in ar.RHOS:
   498	        all_r = sorted(p2_strata[(rho, 'low')] + p2_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   499	        fails = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) > 0]
   500	        passes = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) == 0]
   501	        picks = [fails[0], fails[len(fails) // 2], passes[0]] + ([passes[-1]] if rho in (200, 300) else [])
   502	        for k in picks:
   503	            cd_arch = rho_arch[k]['arms']['CD']
   504	            g3_jobs.append(dict(
   505	                key=list(k),
   506	                CD=dict(errors=int(cd_arch['errors']), decoded_sha=cd_arch['decoded_sha']),
   507	            ))
   508	    g3_jobs = g3_jobs[:20]
   509	
   510	    # G4 stratified samples
   511	    g4_p1_picks = _select_balanced_keys(p1_strata, per_stratum=4)  # 4 rhos * 2 bands * 4 = 32 keys
   512	    g4_p2_picks = _select_balanced_keys(p2_strata, per_stratum=2)  # 6 rhos * 2 bands * 2 = 24 keys
   513	    g4_p2_jobs = [
   514	        [s, r, snr, f, band, dict(
   515	            errors=int(rho_arch[(s, r, snr, f)]['arms']['CD']['errors']),
   516	            decoded_sha=rho_arch[(s, r, snr, f)]['arms']['CD']['decoded_sha'],
   517	        )]
   518	        for s, r, snr, f, band in g4_p2_picks
   519	    ]
   520	
   521	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   522	    ipc_dir = tmp_root / f'sameframe_gates_ipc_{os.getpid()}'
   523	    ipc_dir.mkdir(parents=True, exist_ok=True)
   524	    try:
   525	        print('Running G1 (20 stageA F0 replay keys)...', flush=True)
   526	        g1_rows = _spawn_map(_g1_worker, g1_jobs, args.workers, ipc_dir, 'g1')
   527	        print(f'G1 PASS ({len(g1_rows)}/20)', flush=True)
   528	
   529	        print('Running G2 (5 archived huang HG parity keys)...', flush=True)
   530	        g2_rows = _spawn_map(_g2_worker, g2_jobs, min(5, args.workers), ipc_dir, 'g2')
   531	        print(f'G2 PASS ({len(g2_rows)}/5)', flush=True)
   532	
   533	        print('Running G3 (20 CD2 pass-1 parity + CD2/CD2e8 smoke keys)...', flush=True)
   534	        g3_rows = _spawn_map(_g3_worker, g3_jobs, args.workers, ipc_dir, 'g3')
   535	        print(f'G3 PASS ({len(g3_rows)}/20)', flush=True)
   536	
   537	        print(f'Running G4 cost projection ({len(g4_p1_picks)} Part-1 + {len(g4_p2_jobs)} Part-2 keys)...', flush=True)
   538	        g4_p1_rows = _spawn_map(_g4_part1_worker, [list(x) for x in g4_p1_picks], args.workers, ipc_dir, 'g4p1')
   539	        g4_p2_rows = _spawn_map(_g4_part2_worker, g4_p2_jobs, args.workers, ipc_dir, 'g4p2')
   540	    finally:
   541	        shutil.rmtree(ipc_dir, ignore_errors=True)
   542	
   543	    # Compute stratified cost projections
   544	    p1_counts = {k: len(v) for k, v in p1_strata.items()}
   545	    p2_counts = {k: len(v) for k, v in p2_strata.items()}
   546	
   547	    def project(part1_rhos: tuple[int, ...], include_hgint: bool) -> dict[str, Any]:
   548	        p1_sec = 0.0
   549	        p1_detail = {}
   550	        for rho in part1_rhos:
   551	            for band in ('low', 'mid'):
   552	                sub = [x for x in g4_p1_rows if x['rho'] == rho and x['band'] == band]
   553	                mean_cpu = float(np.mean([
   554	                    x['f0_cpu'] + x['hg_cpu'] + (x['hgint_cpu'] if include_hgint else 0.0)
   555	                    for x in sub
   556	                ]))
   557	                cnt = p1_counts[(rho, band)]
   558	                p1_sec += mean_cpu * cnt
   559	                p1_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   560	        p2_sec = 0.0
   561	        p2_detail = {}
   562	        for rho in ar.RHOS:
   563	            for band in ('low', 'mid'):
   564	                sub = [x for x in g4_p2_rows if x['rho'] == rho and x['band'] == band]
   565	                mean_cpu = float(np.mean([x['f0_cpu'] + x['cd2_cpu'] + x['cd2e8_cpu'] for x in sub]))
   566	                cnt = p2_counts[(rho, band)]
   567	                p2_sec += mean_cpu * cnt
   568	                p2_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   569	        raw_h = p1_sec / 3600.0 + p2_sec / 3600.0 + OVERHEAD_HOURS
   570	        marg_h = raw_h * COST_MARGIN
   571	        return dict(
   572	            part1_rhos=list(part1_rhos),
   573	            include_hgint=include_hgint,
   574	            part1_raw_hours=p1_sec / 3600.0,
   575	            part2_raw_hours=p2_sec / 3600.0,
   576	            overhead_hours=OVERHEAD_HOURS,
   577	            raw_total_hours=raw_h,
   578	            projected_hours_with_margin=marg_h,
   579	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   580	            part1_strata=p1_detail,
   581	            part2_strata=p2_detail,
   582	        )
   583	
   584	    candidates = [
   585	        project(PART1_RHOS, True),
   586	        project(PART1_RHOS, False),
   587	        project((100, 150, 200), False),
   588	    ]
   589	    selected = next((c for c in candidates if c['within_budget']), None)
   590	    gate_cpu_h = _used_cpu_seconds() / 3600.0
   591	    all_passed = bool(len(g1_rows) == 20 and len(g2_rows) == 5 and len(g3_rows) == 20 and selected is not None)
   592	
   593	    out_dir = args.out.resolve()
   594	    out_dir.mkdir(parents=True, exist_ok=True)
   595	    payload = dict(
   596	        _argv=sys.argv,
   597	        _config=dict(
   598	            python_executable=sys.executable,
   599	            threads=thread_env,
   600	            workers=args.workers,
   601	            own_md5=own_md5(),
   602	            frozen_extra_md5=helpers['extra_md5'],
   603	            p1_source_md5=ar.frozen_p1_md5(ctx),
   604	            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
   605	            archive_shards_verified={k: len(v) for k, v in manifests.items()},
   606	        ),
   607	        all_passed=all_passed,
   608	        selected=None if selected is None else dict(
   609	            part1_rhos=selected['part1_rhos'],
   610	            include_hgint=selected['include_hgint'],
   611	            projected_hours_with_margin=selected['projected_hours_with_margin'],
   612	            raw_total_hours=selected['raw_total_hours'],
   613	        ),
   614	        G1=dict(passed=len(g1_rows) == 20, keys_checked=len(g1_rows), rows=g1_rows),
   615	        G2=dict(passed=len(g2_rows) == 5, keys_checked=len(g2_rows), rows=g2_rows),
   616	        G3=dict(passed=len(g3_rows) == 20, keys_checked=len(g3_rows), rows=g3_rows),
   617	        G4=dict(
   618	            passed=selected is not None,
   619	            budget_cap_core_hours=BUDGET_CAP_HOURS,
   620	            margin=COST_MARGIN,
   621	            overhead_hours=OVERHEAD_HOURS,
   622	            candidates=candidates,
   623	        ),
   624	        gate_cpu_hours=gate_cpu_h,
   625	        gate_wall_seconds=time.monotonic() - started,
   626	    )
   627	    ar.atomic_write_text(out_dir / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
   628	    print(
   629	        f'GATE_STATUS={"PASS" if all_passed else "FAIL_BUDGET"} '
   630	        f'selected={payload["selected"]} cpu_hours={gate_cpu_h:.4f}',
   631	        flush=True,
   632	    )
   633	    sys.exit(0 if all_passed else 1)
   634	
   635	
   636	def _write_gzip_jsonl_atomic(final_path: Path, lines: list[str]):
   637	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   638	    with part_path.open('wb') as raw_fh:
   639	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
   640	            for ln in lines:
   641	                gz.write(ln.encode('utf-8'))
   642	        raw_fh.flush()
   643	        os.fsync(raw_fh.fileno())
   644	    os.replace(part_path, final_path)
   645	
   646	
   647	def _part1_shard_worker(
   648	    shard_idx: int,
   649	    frames: tuple[int, ...],
   650	    trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]],
   651	    include_hgint: bool,
   652	    raw_dir: Path,
   653	):
   654	    C, _, _, helpers = load_stage_runtime()
   655	    stage3, ctx = C['stage3'], C['ctx']
   656	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   657	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   658	    final_path = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
   659	    out_lines: list[str] = []
   660	    for frame in frames:
   661	        items = trig_by_frame.get(frame, [])
   662	        grouped: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
   663	        for s, rho, snr, exp_syn, exp_f0_err in items:
   664	            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err))
   665	        for (s, rho), grp in sorted(grouped.items()):
   666	            base = stage3.inputs(ctx, frame, s, rho)
   667	            for snr, exp_syn, exp_f0_err in sorted(grp):
   668	                _, obs, truth = stage3.observed(ctx, base, rho, snr)
   669	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   670	                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   671	                if int(syn) != exp_syn or f0_err != exp_f0_err:
   672	                    raise RuntimeError(
   673	                        f'Part1 F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
   674	                    )
   675	                hg_out = ar.run_hg_arm(
   676	                    ctx, helpers, obs, arrays, truth,
   677	                    ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   678	                    max_passes=2, record_match=False,
   679	                )
   680	                arms_rec = dict(
   681	                    HG=dict(
   682	                        errors=hg_out['HG']['errors'],
   683	                        decoded_sha=hg_out['HG']['decoded_sha'],
   684	                        syndrome=hg_out['HG']['syndrome'],
   685	                        passes_used=hg_out['HG']['passes_used'],
   686	                    ),
   687	                    HG1=dict(
   688	                        errors=hg_out['HG1']['errors'],
   689	                        decoded_sha=hg_out['HG1']['decoded_sha'],
   690	                        syndrome=hg_out['HG1']['syndrome'],
   691	                    ),
   692	                )
   693	                if include_hgint:
   694	                    hgint_out = ar.run_hg_arm(
   695	                        ctx, helpers, obs, arrays, truth,
   696	                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   697	                        max_passes=2, record_match=False,
   698	                    )
   699	                    arms_rec['HGint'] = dict(
   700	                        errors=hgint_out['HG']['errors'],
   701	                        decoded_sha=hgint_out['HG']['decoded_sha'],
   702	                        syndrome=hgint_out['HG']['syndrome'],
   703	                        passes_used=hgint_out['HG']['passes_used'],
   704	                    )
   705	                out_lines.append(json.dumps(dict(
   706	                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
   707	                ), allow_nan=False) + '\n')
   708	    _write_gzip_jsonl_atomic(final_path, out_lines)
   709	    print(f'Part1 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   710	
   711	
   712	def _part2_shard_worker(
   713	    shard_idx: int,
   714	    frames: tuple[int, ...],
   715	    trig_by_frame: dict[int, list[dict[str, Any]]],
   716	    raw_dir: Path,
   717	):
   718	    C, _, _, helpers = load_stage_runtime()
   719	    stage3, ctx = C['stage3'], C['ctx']
   720	    final_path = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
   721	    out_lines: list[str] = []
   722	    for frame in frames:
   723	        items = trig_by_frame.get(frame, [])
   724	        grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
   725	        for item in items:
   726	            grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
   727	        for (s, rho), grp in sorted(grouped.items()):
   728	            base = stage3.inputs(ctx, frame, s, rho)
   729	            for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
   730	                snr = int(item['snr_centi_db'])
   731	                raw, obs, truth = stage3.observed(ctx, base, rho, snr)
   732	                if stage3.input_record(raw, obs) != item['inputs']:
   733	                    raise RuntimeError(f'Part2 input mismatch at {(s, rho, snr, frame)}')
   734	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   735	                f0 = stage3.decoded(ctx, dec, truth)
   736	                if int(syn) != int(item['syndrome']) or f0 != dict(
   737	                    errors=int(item['arms']['F0']['errors']),
   738	                    decoded_sha=item['arms']['F0']['decoded_sha'],
   739	                ):
   740	                    raise RuntimeError(f'Part2 F0 drift at {(s, rho, snr, frame)}')
   741	                arch_cd = dict(
   742	                    errors=int(item['arms']['CD']['errors']),
   743	                    decoded_sha=item['arms']['CD']['decoded_sha'],
   744	                )
   745	                cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
   746	                cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   747	                out_lines.append(json.dumps(dict(
   748	                    scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=int(syn),
   749	                    arms=dict(CD2=cd2, CD2e8=cd2e8),
   750	                ), allow_nan=False) + '\n')
   751	    _write_gzip_jsonl_atomic(final_path, out_lines)
   752	    print(f'Part2 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   753	
   754	
   755	def _run_sharded_phase(target_fn, job_args: list[tuple[Any, ...]], max_workers: int, cpu_cap_sec: float):
   756	    """Run up to max_workers spawned processes concurrently with live CPU budget check."""
   757	    mp_ctx = multiprocessing.get_context('spawn')
   758	    pending = list(job_args)
   759	    running = {}
   760	    budget_hit = False
   761	    try:
   762	        while pending or running:
   763	            while pending and len(running) < max_workers:
   764	                args = pending.pop(0)
   765	                proc = mp_ctx.Process(target=target_fn, args=args)
   766	                proc.start()
   767	                running[proc.sentinel] = (args[0], proc)
   768	            ready = wait(running, timeout=10.0)
   769	            for r in ready:
   770	                idx, proc = running.pop(r)
   771	                proc.join()
   772	                code = proc.exitcode
   773	                proc.close()
   774	                if code != 0:
   775	                    raise RuntimeError(f'Worker shard {idx:03d} failed with exit code {code}')
   776	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   777	            if live_cpu >= cpu_cap_sec:
   778	                budget_hit = True
   779	                break
   780	    finally:
   781	        for _, proc in running.values():
   782	            proc.terminate()
   783	        for _, proc in running.values():
   784	            proc.join()
   785	            proc.close()
   786	    if budget_hit or _used_cpu_seconds() >= cpu_cap_sec:
   787	        print(f'STOPPED_BUDGET: CPU limit reached ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   788	        sys.exit(BUDGET_EXIT_CODE)
   789	
   790	
   791	# --------------------------------------------------------------------------- Analysis (P1 & P2)
   792	def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
   793	    """Wrap stageA2.crossing into conservative (lo, hi) bounds so censored draws never silently yield NaN."""
   794	    c = float(crossing_fn(fer, snrs))
   795	    if math.isfinite(c):
   796	        return c, c
   797	    if c < 0:
   798	        return -math.inf, float(snrs[0]) / 100.0
   799	    return float(snrs[-1]) / 100.0, math.inf
   800	
   801	
   802	def p1_verdict(ci_lo: float, ci_hi: float) -> str:
   803	    if ci_lo >= P1_THRESHOLD_DB:
   804	        return 'DOPPLER-LINE'
   805	    if ci_hi < P1_THRESHOLD_DB:
   806	        return 'WRITE-A'
   807	    return 'INCONCLUSIVE'
   808	
   809	
   810	def p2_verdict(ci_lo: float, ci_hi: float) -> str:
   811	    if ci_lo > P2_THRESHOLD_DB:
   812	        return 'STILL_BEHIND'
   813	    if ci_hi < P2_THRESHOLD_DB:
   814	        return 'CATCHES_UP'
   815	    return 'MIXED'
   816	
   817	
   818	def _rep(v: float) -> Any:
   819	    if math.isinf(v):
   820	        return '+inf' if v > 0 else '-inf'
   821	    if math.isnan(v):
   822	        raise FloatingPointError('NaN encountered in readout')
   823	    return float(v)
   824	
   825	
   826	def analyze_part1(
   827	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   828	    part1_rhos: tuple[int, ...],
   829	    include_hgint: bool,
   830	    crossing_fn,
   831	    *,
   832	    boot_draws: int = PART1_BOOT_DRAWS,
   833	    boot_seed: int = PART1_BOOT_SEED,
   834	) -> dict[str, Any]:
   835	    """Paired physical-frame bootstrap analysis for P1 (frames 41000-41399).
   836	
   837	    fail_by_arm[arm] = (rhos_tuple, snrs_tuple, fail_bool_array[n_frames, 2, n_rhos, n_snrs]).
   838	    """
   839	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   840	    rng = np.random.default_rng(boot_seed)
   841	    # Draw exact multinomial weights once, shared across ALL arms (stageA, stageA2, stageA3, new)
   842	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   843	    weights[0] = 1.0 / n_frames
   844	    for b in range(1, boot_draws + 1):
   845	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   846	
   847	    # Compute U/G mean crossing bounds [boot_draws+1, n_rhos] for every arm
   848	    arm_lo: dict[str, np.ndarray] = {}
   849	    arm_hi: dict[str, np.ndarray] = {}
   850	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   851	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   852	    arm_best_lo: dict[str, np.ndarray] = {}
   853	    arm_best_hi: dict[str, np.ndarray] = {}
   854	    arm_best_rho: dict[str, int] = {}
   855	
   856	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   857	        n_r = len(rhos)
   858	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   859	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   860	        # fer[draw, scen, rho, snr]
   861	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   862	        scen_pt = {'U': {}, 'G': {}}
   863	        for ri, rho in enumerate(rhos):
   864	            for bi in range(boot_draws + 1):
   865	                u_lo, u_hi = crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   866	                g_lo, g_hi = crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   867	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   868	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   869	                if bi == 0:
   870	                    scen_pt['U'][str(rho)] = _rep(u_lo) if u_lo == u_hi else [_rep(u_lo), _rep(u_hi)]
   871	                    scen_pt['G'][str(rho)] = _rep(g_lo) if g_lo == g_hi else [_rep(g_lo), _rep(g_hi)]
   872	        arm_lo[arm] = lo_arr
   873	        arm_hi[arm] = hi_arr
   874	        arm_scen_pt[arm] = scen_pt
   875	        arm_mean_pt[arm] = {
   876	            str(rho): (_rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [_rep(lo_arr[0, ri]), _rep(hi_arr[0, ri])])
   877	            for ri, rho in enumerate(rhos)
   878	        }
   879	        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; others over their own grid (or <=200 for delay)
   880	        if arm == 'delay':
   881	            sub_idx = [i for i, r in enumerate(rhos) if r <= 200]
   882	        else:
   883	            sub_idx = list(range(n_r))
   884	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   885	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   886	        best_pos = int(np.argmin(hi_arr[0, sub_idx]))
   887	        arm_best_rho[arm] = int(rhos[sub_idx[best_pos]])
   888	
   889	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   890	        # D = min_rho arm_a - min_rho arm_b (conservative bounds; collapses to exact diff when finite)
   891	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   892	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   893	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   894	        if cens_frac == 0.0:
   895	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   896	        else:
   897	            lo = an._nearest_rank(d_lo[1:], 0.025)
   898	            hi = an._nearest_rank(d_hi[1:], 0.975)
   899	        pt = _rep(d_lo[0]) if d_lo[0] == d_hi[0] else [_rep(d_lo[0]), _rep(d_hi[0])]
   900	        return dict(
   901	            point_db=pt,
   902	            ci95_db=[_rep(lo), _rep(hi)],
   903	            censored_draw_fraction=cens_frac,
   904	            arm_a_best_db=_rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [_rep(arm_best_lo[arm_a][0]), _rep(arm_best_hi[arm_a][0])],
   905	            arm_a_best_rho=arm_best_rho[arm_a],
   906	            arm_b_best_db=_rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [_rep(arm_best_lo[arm_b][0]), _rep(arm_best_hi[arm_b][0])],
   907	            arm_b_best_rho=arm_best_rho[arm_b],
   908	        )
   909	
   910	    primary_p1 = contrast('HG', 's100')
   911	    p1_lo = float(primary_p1['ci95_db'][0]) if isinstance(primary_p1['ci95_db'][0], float) else (-math.inf if primary_p1['ci95_db'][0] == '-inf' else math.inf)
   912	    p1_hi = float(primary_p1['ci95_db'][1]) if isinstance(primary_p1['ci95_db'][1], float) else (-math.inf if primary_p1['ci95_db'][1] == '-inf' else math.inf)
   913	    primary_p1['verdict'] = p1_verdict(p1_lo, p1_hi)
   914	
   915	    sec_contrasts = {}
   916	    for comp in ('s050', 'ldop', 'full', 'delay', 'base'):
   917	        if comp in fail_by_arm:
   918	            sec_contrasts[f'HG_minus_{comp}'] = contrast('HG', comp)
   919	    sec_contrasts['HG1_minus_s100'] = contrast('HG1', 's100')
   920	    if include_hgint and 'HGint' in fail_by_arm:
   921	        for comp in ('s100', 's050', 'ldop', 'full', 'HG'):
   922	            if comp in fail_by_arm:
   923	                sec_contrasts[f'HGint_minus_{comp}'] = contrast('HGint', comp)
   924	
   925	    return dict(
   926	        boot_draws=boot_draws,
   927	        boot_seed=boot_seed,
   928	        part1_rhos=list(part1_rhos),
   929	        include_hgint=include_hgint,
   930	        primary_P1=primary_p1,
   931	        secondary_contrasts=sec_contrasts,
   932	        mean_crossing=arm_mean_pt,
   933	        crossings_by_scenario=arm_scen_pt,
   934	        best_rho=arm_best_rho,
   935	    )
   936	
   937	
   938	def analyze_part2(
   939	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
   940	    arms: tuple[str, ...],
   941	    *,
   942	    boot_draws: int = an.BOOT_DRAWS,
   943	    boot_seed: int = an.BOOT_SEED,
   944	) -> dict[str, Any]:
   945	    """Reuse hs_analysis crossing & 36-pair simultaneous projection for P2 (frames 5400-5799)."""
   946	    rhos = ar.RHOS
   947	    snrs = ar.SNRS
   948	    frames = ar.MAIN_FRAMES
   949	    errors_by_key = {k: {a: int(r['arms'][a]['errors']) for a in arms} for k, r in full_rows.items()}
   950	    crossings, cells = an.compute_crossings(
   951	        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
   952	    )
   953	    pooled = an.scene_means(crossings, rhos, arms)
   954	
   955	    def eval_p2(arm_a: str, arm_b: str) -> dict[str, Any]:
   956	        c98 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.PRIMARY_ALPHA)
   957	        c95 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.FAMILY_ALPHA)
   958	        _, _, lo98, hi98 = c98['_raw']
   959	        _, _, lo95, hi95 = c95['_raw']
   960	        return dict(
   961	            point_db=c98['point_db'],
   962	            ci9833_projected_db=c98['ci_projected_db'],
   963	            ci9833_per_draw_db=c98['ci_per_draw_db'],
   964	            ci95_projected_db=c95['ci_projected_db'],
   965	            ci95_per_draw_db=c95['ci_per_draw_db'],
   966	            censored_draw_fraction=c98['censored_draw_fraction'],
   967	            verdict=p2_verdict(lo98, hi98),
   968	            verdict_at_95_descriptive=p2_verdict(lo95, hi95),
   969	        )
   970	
   971	    p2_E = eval_p2('CD2', 'HG')
   972	    p2_E8 = eval_p2('CD2e8', 'HG')
   973	
   974	    # Per-scenario P2
   975	    by_scen = {}
   976	    for s in ar.SCENARIOS:
   977	        s_curves = {(r, a): crossings[s, r, a] for r in rhos for a in arms}
   978	        by_scen[s] = {}
   979	        for label, arm_a in (('E_CD2_minus_HG', 'CD2'), ('E8_CD2e8_minus_HG', 'CD2e8')):
   980	            c98 = an.projected_best_diff(s_curves, arm_a, 'HG', rhos, an.PRIMARY_ALPHA)
   981	            _, _, lo98, hi98 = c98['_raw']
   982	            by_scen[s][label] = dict(
   983	                point_db=c98['point_db'],
   984	                ci9833_projected_db=c98['ci_projected_db'],
   985	                verdict=p2_verdict(lo98, hi98),
   986	            )
   987	
   988	    # Secondary contrasts (95% projected CI)
   989	    sec = {}
   990	    for name, a1, a2 in (
   991	        ('CD2_minus_CD', 'CD2', 'CD'),
   992	        ('CD2e8_minus_CD', 'CD2e8', 'CD'),
   993	        ('CD2e8_minus_CD2', 'CD2e8', 'CD2'),
   994	        ('CD2_minus_HGint', 'CD2', 'HGint'),
   995	        ('CD2e8_minus_HGint', 'CD2e8', 'HGint'),
   996	    ):
   997	        if a1 in arms and a2 in arms:
   998	            c = an.projected_best_diff(pooled, a1, a2, rhos, an.FAMILY_ALPHA)
   999	            sec[name] = {k: v for k, v in c.items() if k != '_raw'}
  1000	
  1001	    # Scene-averaged crossing table
  1002	    pooled_table = {}
  1003	    best_rho = {}
  1004	    for a in arms:
  1005	        pooled_table[a] = {}
  1006	        best_val = math.inf
  1007	        best_r = rhos[0]
  1008	        for r in rhos:
  1009	            b = pooled[r, a]
  1010	            lo95, hi95 = an._interval(b, 0.05)
  1011	            pt_lo, pt_hi = float(b.lower[0]), float(b.upper[0])
  1012	            pooled_table[a][str(r)] = dict(
  1013	                point_db=[_rep(pt_lo), _rep(pt_hi)],
  1014	                ci95_db=[_rep(lo95), _rep(hi95)],
  1015	            )
  1016	            if pt_hi < best_val:
  1017	                best_val = pt_hi
  1018	                best_r = r
  1019	        best_rho[a] = int(best_r)
  1020	
  1021	    # Diagnostics on triggered keys
  1022	    trig_rows = [r for r in full_rows.values() if r['triggered']]
  1023	    diag = {}
  1024	    for arm in ('CD2', 'CD2e8'):
  1025	        p1_stop = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 1)
  1026	        p2_ran = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 2)
  1027	        p2_rescued = sum(
  1028	            1 for r in trig_rows
  1029	            if r['arms'][arm]['passes_used'] == 2 and r['arms'][arm]['pass1_errors'] > 0 and r['arms'][arm]['errors'] == 0
  1030	        )
  1031	        vs_hg = dict(
  1032	            arm_only=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] > 0),
  1033	            hg_only=sum(1 for r in trig_rows if r['arms']['HG']['errors'] == 0 and r['arms'][arm]['errors'] > 0),
  1034	            both=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] == 0),
  1035	            neither=sum(1 for r in trig_rows if r['arms'][arm]['errors'] > 0 and r['arms']['HG']['errors'] > 0),
  1036	        )
  1037	        diag[arm] = dict(
  1038	            triggered=len(trig_rows),
  1039	            pass1_early_stop=p1_stop,
  1040	            pass2_ran=p2_ran,
  1041	            pass2_rescued=p2_rescued,
  1042	            mean_pass1_edits=float(np.mean([r['arms'][arm]['pass1_edits'] for r in trig_rows])),
  1043	            mean_pass2_edits_when_ran=float(np.mean([r['arms'][arm]['pass2_edits'] for r in trig_rows if r['arms'][arm]['passes_used'] == 2])) if p2_ran else 0.0,
  1044	            paired_vs_hg=vs_hg,
  1045	        )
  1046	
  1047	    return dict(
  1048	        boot_draws=boot_draws,
  1049	        boot_seed=boot_seed,
  1050	        primary_alpha=an.PRIMARY_ALPHA,
  1051	        E_CD2_minus_HG=p2_E,
  1052	        E8_CD2e8_minus_HG=p2_E8,
  1053	        by_scenario=by_scen,
  1054	        secondary_contrasts_95=sec,
  1055	        pooled_crossings=pooled_table,
  1056	        best_rho=best_rho,
  1057	        diagnostics=diag,
  1058	        cells=cells,
  1059	    )
  1060	
  1061	
  1062	def render_results_md(res: dict[str, Any]) -> str:
  1063	    p1 = res['part1']
  1064	    p2 = res['part2']
  1065	    q1 = p1['primary_P1']
  1066	    e1 = p2['E_CD2_minus_HG']
  1067	    e8 = p2['E8_CD2e8_minus_HG']
  1068	
  1069	    def fval(x):
  1070	        if isinstance(x, list):
  1071	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
  1072	        return x if isinstance(x, str) else f'{x:.4f}'
  1073	
  1074	    lines = [
  1075	        '# Same-Frame Decisive Check Results (`sameframe_hg_20261124`)',
  1076	        '',
  1077	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
  1078	        f'- Cumulative CPU: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 12.0 h; wall {res["runtime"]["total_wall_seconds"]:.1f} s)',
  1079	        '',
  1080	        '## Primary Verdicts (Pre-Registered)',
  1081	        '',
  1082	        '| Test | Contrast | Point (dB) | Primary CI (dB) | Verdict |',
  1083	        '|---|---|---:|---|---|',
  1084	        f'| **P1** (95% paired) | `min HG (100..250) − min s100 (100..200)` | {fval(q1["point_db"])} | [{fval(q1["ci95_db"][0])}, {fval(q1["ci95_db"][1])}] | **{q1["verdict"]}** |',
  1085	        f'| **P2-E** (98.33% 36-pair proj) | `min CD2 − min HG` | {fval(e1["point_db"])} | [{fval(e1["ci9833_projected_db"][0])}, {fval(e1["ci9833_projected_db"][1])}] (95%: [{fval(e1["ci95_projected_db"][0])}, {fval(e1["ci95_projected_db"][1])}]) | **{e1["verdict"]}** |',
  1086	        f'| **P2-E8** (98.33% 36-pair proj) | `min CD2e8 − min HG` | {fval(e8["point_db"])} | [{fval(e8["ci9833_projected_db"][0])}, {fval(e8["ci9833_projected_db"][1])}] (95%: [{fval(e8["ci95_projected_db"][0])}, {fval(e8["ci95_projected_db"][1])}]) | **{e8["verdict"]}** |',
  1087	        '',
  1088	        '## Part 1: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
  1089	        '',
  1090	    ]
  1091	    p1_arms = [a for a in ('base', 'delay', 'HG', 'HG1', 'HGint', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in p1['mean_crossing']]
  1092	    all_p1_rhos = ('50', '100', '150', '200', '250', '300')
  1093	    lines.append('| Arm | ' + ' | '.join(f'ρ={int(r)/1000:.2f}' for r in all_p1_rhos) + ' | Best ρ |')
  1094	    lines.append('|---|' + '---:|' * len(all_p1_rhos) + '---:|')
  1095	    for a in p1_arms:
  1096	        row_cells = [fval(p1['mean_crossing'][a][r]) if r in p1['mean_crossing'][a] else '—' for r in all_p1_rhos]
  1097	        lines.append(f'| {a} | ' + ' | '.join(row_cells) + f' | {p1["best_rho"][a]/1000:.2f} |')
  1098	    lines += ['', '### Part 1 Secondary Contrasts (95% Paired Frame Bootstrap, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
  1099	    for name, c in p1['secondary_contrasts'].items():
  1100	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')
  1101	
  1102	    lines += ['', '## Part 2: 1% FER Crossings on Huang Frames (5400–5799, U/G Mean, dB)', '']
  1103	    p2_arms = [a for a in ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z') if a in p2['pooled_crossings']]
  1104	    lines.append('| ρ | ' + ' | '.join(p2_arms) + ' |')
  1105	    lines.append('|---:|' + '---|' * len(p2_arms))
  1106	    for r in ar.RHOS:
  1107	        cells_str = []
  1108	        for a in p2_arms:
  1109	            d = p2['pooled_crossings'][a][str(r)]
  1110	            cells_str.append(f'{fval(d["point_db"])} [{fval(d["ci95_db"][0])}, {fval(d["ci95_db"][1])}]')
  1111	        lines.append(f'| {r/1000:.2f} | ' + ' | '.join(cells_str) + ' |')
  1112	
  1113	    lines += ['', '### Part 2 Diagnostics & Secondary Contrasts', '']
  1114	    for arm in ('CD2', 'CD2e8'):
  1115	        d = p2['diagnostics'][arm]
  1116	        v = d['paired_vs_hg']
  1117	        lines.append(
  1118	            f'- `{arm}`: pass-1 stop {d["pass1_early_stop"]}/{d["triggered"]}, '
  1119	            f'pass-2 ran {d["pass2_ran"]} (rescued {d["pass2_rescued"]}), '
  1120	            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}; '
  1121	            f'vs HG: {arm}_only={v["arm_only"]}, HG_only={v["hg_only"]}, both={v["both"]}, neither={v["neither"]}'
  1122	        )
  1123	    lines += ['', '| Contrast | Point (dB) | 95% Projected CI (dB) |', '|---|---:|---|']
  1124	    for name, c in p2['secondary_contrasts_95'].items():
  1125	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci_projected_db"][0])}, {fval(c["ci_projected_db"][1])}] |')
  1126	    return '\n'.join(lines) + '\n'
  1127	
  1128	
  1129	def _do_read(out_dir: Path, gate: dict[str, Any], freeze_commit: str, runtime_info: dict[str, Any], raw_md5: dict[str, str]):
  1130	    import stageA  # noqa: E402
  1131	    import stageA2  # noqa: E402
  1132	    import stageA3  # noqa: E402
  1133	
  1134	    sel = gate['selected']
  1135	    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
  1136	    include_hgint = bool(sel['include_hgint'])
  1137	    raw_dir = out_dir / 'raw'
  1138	
  1139	    # Verify all manifests and our own raw shard MD5s
  1140	    for name in ARCHIVE_MANIFESTS:
  1141	        verify_manifest(name)
  1142	    for fname, expected in raw_md5.items():
  1143	        actual = ar.md5_file(raw_dir / fname)
  1144	        if actual != expected:
  1145	            raise RuntimeError(f'Raw shard MD5 mismatch {fname}: {actual} != {expected}')
  1146	
  1147	    # --- Load Part 1 arrays (archived stageA/A2/A3 + new Part 1) ---
  1148	    fa, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)
  1149	    fa2, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
  1150	    fa3, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)
  1151	
  1152	    stageA_base = load_stageA_base(part1_rhos)
  1153	    new_p1_arms = ('HG', 'HG1') + (('HGint',) if include_hgint else ())
  1154	    fi = {f: i for i, f in enumerate(PART1_FRAMES)}
  1155	    p1_fail = {a: np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool) for a in new_p1_arms}
  1156	    p1_seen = np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool)
  1157	
  1158	    # Fill untriggered keys from stageA_base
  1159	    for (s, rho, snr, f), b in stageA_base.items():
  1160	        if b['syndrome'] == 0:
  1161	            ix = (fi[f], ar.SCENARIOS.index(s), part1_rhos.index(rho), PART1_SNRS.index(snr))
  1162	            err_flag = b['f0_errors'] > 0
  1163	            for a in new_p1_arms:
  1164	                p1_fail[a][ix] = err_flag
  1165	            p1_seen[ix] = True
  1166	
  1167	    # Fill triggered keys from new Part-1 shards
  1168	    p1_trig_seen = 0
  1169	    for shard_idx in range(N_SHARDS):
  1170	        sp = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
  1171	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
  1172	            for line in fh:
  1173	                r = json.loads(line)
  1174	                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), part1_rhos.index(int(r['rho'])), PART1_SNRS.index(int(r['snr'])))
  1175	                if p1_seen[ix]:
  1176	                    raise RuntimeError(f'Duplicate Part1 key {r}')
  1177	                for a in new_p1_arms:
  1178	                    p1_fail[a][ix] = int(r['arms'][a]['errors']) > 0
  1179	                p1_seen[ix] = True
  1180	                p1_trig_seen += 1
  1181	    if not p1_seen.all():
  1182	        raise RuntimeError(f'Incomplete Part1 grid: missing {int((~p1_seen).sum())} keys')
  1183	
  1184	    fail_by_arm = {
  1185	        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
  1186	        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
  1187	        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
  1188	        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
  1189	    }
  1190	    for i, a in enumerate(stageA3.ARMS):
  1191	        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
  1192	    for a in new_p1_arms:
  1193	        fail_by_arm[a] = (part1_rhos, PART1_SNRS, p1_fail[a])
  1194	
  1195	    print(f'Analyzing Part 1 ({int(p1_seen.sum())} keys, {p1_trig_seen} triggered)...', flush=True)
  1196	    part1_out = analyze_part1(fail_by_arm, part1_rhos, include_hgint, stageA2.crossing)
  1197	
  1198	    # --- Load Part 2 rows (archived rho_sweep + huang_steelman + new CD2/CD2e8) ---
  1199	    rho_arch, _ = ar.load_archived_rho_sweep()
  1200	    huang_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1201	    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
  1202	        with p.open('r', encoding='utf-8') as fh:
  1203	            for line in fh:
  1204	                r = json.loads(line)
  1205	                huang_trig[ar.row_key(r)] = r
  1206	
  1207	    new_p2_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1208	    for shard_idx in range(N_SHARDS):
  1209	        sp = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
  1210	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
  1211	            for line in fh:
  1212	                r = json.loads(line)
  1213	                k = ar.row_key(r)
  1214	                if k in new_p2_trig:
  1215	                    raise RuntimeError(f'Duplicate Part2 key {k}')
  1216	                new_p2_trig[k] = r
  1217	    if len(new_p2_trig) != ar.EXPECTED_TOTAL_TRIGGERS or len(huang_trig) != ar.EXPECTED_TOTAL_TRIGGERS:
  1218	        raise RuntimeError(f'Part2 trigger count mismatch: new={len(new_p2_trig)}, huang={len(huang_trig)}')
  1219	
  1220	    p2_arms = ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z')
  1221	    full_p2: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1222	    for k, arch in rho_arch.items():
  1223	        if arch['triggered']:
  1224	            hr = huang_trig[k]['arms']
  1225	            nr = new_p2_trig[k]['arms']
  1226	            full_p2[k] = dict(
  1227	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
  1228	                triggered=True,
  1229	                arms=dict(
  1230	                    F0=hr['F0'], CD=hr['CD'], HG=hr['HG'], HG1=hr['HG1'], HGint=hr['HGint'], Z=hr['Z'],
  1231	                    CD2=nr['CD2'], CD2e8=nr['CD2e8'],
  1232	                ),
  1233	            )
  1234	        else:
  1235	            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
  1236	            full_p2[k] = dict(
  1237	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
  1238	                triggered=False,
  1239	                arms={a: f0 for a in p2_arms},
  1240	            )
  1241	
  1242	    print(f'Analyzing Part 2 ({len(full_p2)} keys, {len(new_p2_trig)} triggered)...', flush=True)
  1243	    part2_out = analyze_part2(full_p2, p2_arms)
  1244	
  1245	    results = dict(
  1246	        _argv=sys.argv,
  1247	        _config=dict(
  1248	            freeze_commit=freeze_commit,
  1249	            python_executable=sys.executable,
  1250	            own_md5=own_md5(),
  1251	            gate_md5=ar.md5_file(out_dir / 'gate.json'),
  1252	            part1_rhos=list(part1_rhos),
  1253	            include_hgint=include_hgint,
  1254	            part1_frames=[PART1_FRAMES[0], PART1_FRAMES[-1]],
  1255	            part1_triggered_keys=p1_trig_seen,
  1256	            part2_frames=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
  1257	            part2_triggered_keys=len(new_p2_trig),
  1258	            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
  1259	            raw_output_dir=str(raw_dir),
  1260	            raw_rows_md5=raw_md5,
  1261	        ),
  1262	        gates=dict(
  1263	            all_passed=gate['all_passed'],
  1264	            selected=gate['selected'],
  1265	            G1_keys=gate['G1']['keys_checked'],
  1266	            G2_keys=gate['G2']['keys_checked'],
  1267	            G3_keys=gate['G3']['keys_checked'],
  1268	            G4_projected_hours=sel['projected_hours_with_margin'],
  1269	        ),
  1270	        runtime=runtime_info,
  1271	        part1=part1_out,
  1272	        part2=part2_out,
  1273	    )
  1274	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
  1275	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
  1276	    print(
  1277	        f'DONE P1={part1_out["primary_P1"]["verdict"]} '
  1278	        f'P2_CD2={part2_out["E_CD2_minus_HG"]["verdict"]} '
  1279	        f'P2_CD2e8={part2_out["E8_CD2e8_minus_HG"]["verdict"]}',
  1280	        flush=True,
  1281	    )
  1282	
  1283	
  1284	def cmd_run(args):
  1285	    print(sys.executable, flush=True)
  1286	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
  1287	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
  1288	    ar.check_thread_env()
  1289	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
  1290	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
  1291	    if not 1 <= args.workers <= 32:
  1292	        raise ValueError('workers must be in 1..32')
  1293	
  1294	    out_dir = args.out.resolve()
  1295	    raw_dir = out_dir / 'raw'
  1296	    raw_dir.mkdir(parents=True, exist_ok=True)
  1297	    if list(raw_dir.glob('part*_shard*.jsonl*')):
  1298	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
  1299	
  1300	    gate = json.loads((out_dir / 'gate.json').read_text(encoding='utf-8'))
  1301	    if not gate.get('all_passed') or not gate.get('selected'):
  1302	        raise RuntimeError('Refusing to run without passing gate.json')
  1303	    if gate['_config']['own_md5'] != own_md5():
  1304	        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
  1305	
  1306	    sel = gate['selected']
  1307	    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
  1308	    include_hgint = bool(sel['include_hgint'])
  1309	
  1310	    wall_start = time.monotonic()
  1311	    for name in ARCHIVE_MANIFESTS:
  1312	        verify_manifest(name)
  1313	    C, _, _, helpers = load_stage_runtime()
  1314	    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
  1315	        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
  1316	    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
  1317	        raise RuntimeError('p1_source_md5 mismatch vs gate.json')
  1318	
  1319	    # --- Part 1 ---
  1320	    stageA_base = load_stageA_base(part1_rhos)
  1321	    p1_trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]] = {}
  1322	    p1_n_trig = 0
  1323	    for (s, rho, snr, f), b in stageA_base.items():
  1324	        if b['syndrome'] != 0:
  1325	            p1_trig_by_frame.setdefault(f, []).append((s, rho, snr, b['syndrome'], b['f0_errors']))
  1326	            p1_n_trig += 1
  1327	    p1_jobs = [
  1328	        (idx, tuple(PART1_FRAMES[idx::N_SHARDS]), {f: p1_trig_by_frame.get(f, []) for f in PART1_FRAMES[idx::N_SHARDS]}, include_hgint, raw_dir)
  1329	        for idx in range(N_SHARDS)
  1330	    ]
  1331	    print(f'Launching Part 1: {p1_n_trig} triggered keys on {args.workers} workers (rhos={part1_rhos}, hgint={include_hgint})...', flush=True)
  1332	    t_p1 = time.monotonic()
  1333	    _run_sharded_phase(_part1_shard_worker, p1_jobs, args.workers, BUDGET_CAP_SEC)
  1334	    p1_wall = time.monotonic() - t_p1
  1335	    p1_cpu = _used_cpu_seconds()
  1336	    print(f'Part 1 complete: wall={p1_wall:.1f}s, cumulative_cpu={p1_cpu/3600:.4f}h', flush=True)
  1337	
  1338	    # --- Part 2 ---
  1339	    rho_arch, _ = ar.load_archived_rho_sweep()
  1340	    p2_trig_by_frame: dict[int, list[dict[str, Any]]] = {}
  1341	    p2_n_trig = 0
  1342	    for k, r in rho_arch.items():
  1343	        if r['triggered']:
  1344	            p2_trig_by_frame.setdefault(k[3], []).append(r)
  1345	            p2_n_trig += 1
  1346	    p2_jobs = [
  1347	        (idx, tuple(ar.MAIN_FRAMES[idx::N_SHARDS]), {f: p2_trig_by_frame.get(f, []) for f in ar.MAIN_FRAMES[idx::N_SHARDS]}, raw_dir)
  1348	        for idx in range(N_SHARDS)
  1349	    ]
  1350	    print(f'Launching Part 2: {p2_n_trig} triggered keys on {args.workers} workers (CD2 + CD2e8)...', flush=True)
  1351	    t_p2 = time.monotonic()
  1352	    _run_sharded_phase(_part2_shard_worker, p2_jobs, args.workers, BUDGET_CAP_SEC)
  1353	    p2_wall = time.monotonic() - t_p2
  1354	    total_cpu = _used_cpu_seconds()
  1355	    print(f'Part 2 complete: wall={p2_wall:.1f}s, cumulative_cpu={total_cpu/3600:.4f}h', flush=True)
  1356	
  1357	    raw_md5 = {}
  1358	    for prefix in ('part1', 'part2'):
  1359	        for idx in range(N_SHARDS):
  1360	            p = raw_dir / f'{prefix}_shard{idx:03d}.jsonl.gz'
  1361	            raw_md5[p.name] = ar.md5_file(p)
  1362	    ar.atomic_write_text(
  1363	        out_dir / 'REMOTE_ROWS_MD5.txt',
  1364	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
  1365	    )
  1366	
  1367	    runtime_info = dict(
  1368	        part1_wall_seconds=p1_wall,
  1369	        part1_cpu_hours=p1_cpu / 3600.0,
  1370	        part2_wall_seconds=p2_wall,
  1371	        part2_cpu_hours=(total_cpu - p1_cpu) / 3600.0,
  1372	        total_wall_seconds=time.monotonic() - wall_start,
  1373	        total_core_hours=total_cpu / 3600.0,
  1374	        cpu_cap_core_hours=BUDGET_CAP_HOURS,
  1375	    )
  1376	    _do_read(out_dir, gate, args.freeze_commit, runtime_info, raw_md5)
  1377	    final_cpu = _used_cpu_seconds()
  1378	    if final_cpu >= BUDGET_CAP_SEC:
  1379	        print(f'STOPPED_BUDGET after read ({final_cpu/3600:.3f} core-hours)', flush=True)
  1380	        sys.exit(BUDGET_EXIT_CODE)
  1381	
  1382	
  1383	def cmd_read(args):
  1384	    out_dir = args.out.resolve()
  1385	    gate = json.loads((out_dir / 'gate.json').read_text(encoding='utf-8'))
  1386	    raw_md5 = {}
  1387	    for line in (out_dir / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8').splitlines():
  1388	        if line.strip():
  1389	            d, n = line.split()
  1390	            raw_md5[n] = d
  1391	    prev = json.loads((out_dir / 'results.json').read_text(encoding='utf-8')) if (out_dir / 'results.json').is_file() else {}
  1392	    runtime_info = prev.get('runtime', dict(total_core_hours=0.0, total_wall_seconds=0.0, cpu_cap_core_hours=BUDGET_CAP_HOURS))
  1393	    _do_read(out_dir, gate, args.freeze_commit, runtime_info, raw_md5)
  1394	
  1395	
  1396	def main():
  1397	    ap = argparse.ArgumentParser(description=__doc__)
  1398	    sub = ap.add_subparsers(dest='mode', required=True)
  1399	    g = sub.add_parser('gate')
  1400	    g.add_argument('--out', type=Path, required=True)
  1401	    g.add_argument('--workers', type=int, default=16)
  1402	
  1403	    r = sub.add_parser('run')
  1404	    r.add_argument('--out', type=Path, required=True)
  1405	    r.add_argument('--freeze-commit', required=True)
  1406	    r.add_argument('--workers', type=int, default=WORKERS)
  1407	
  1408	    rd = sub.add_parser('read')
  1409	    rd.add_argument('--out', type=Path, required=True)
  1410	    rd.add_argument('--freeze-commit', required=True)
  1411	
  1412	    args = ap.parse_args()
  1413	    dict(gate=cmd_gate, run=cmd_run, read=cmd_read)[args.mode](args)
  1414	
  1415	
  1416	if __name__ == '__main__':
  1417	    main()

 succeeded in 0ms:
     1	# Same-Frame Decisive Check: HG vs Round-0 Doppler Headroom & Two-Pass CD (`sameframe_hg_20261124`)
     2	
     3	**Status**: PRE-FREEZE (to be frozen after Sol static review and before launching on deinlab)
     4	**Decision context**: [route-after-huang-divergence-20261124.md](../../.trellis/tasks/09-22-tf-production-gap-audit/research/route-after-huang-divergence-20261124.md), [huang_steelman_20261124/READOUT.md](../huang_steelman_20261124/READOUT.md).
     5	
     6	---
     7	
     8	## 1. Research Questions
     9	
    10	1. **P1 (Same-frame headroom after HG, frames `41000–41399`)**: After two-pass Huang-2010-style data-aided global OMP re-acquisition (`HG`), does a realistic round-0 Doppler improvement (`s100`: true delays + Gaussian Doppler error $\sigma = 0.10$ bin, measured round-0 mean $|\Delta\nu| \approx 0.080$ bin, pilot-LS gains) still leave $\ge 0.5$ dB of 1% FER headroom at low pilot fraction?
    11	2. **P2 (Round-count & edit-budget symmetry, frames `5400–5799`)**: When local exchange `CD` is given the same 2 continuation passes as `HG` (4 total rounds: `CD2` with `max_edits=2` per pass, and `CD2e8` with `max_edits=8` per pass), does local exchange catch up to `HG` or remain behind?
    12	
    13	---
    14	
    15	## 2. Experimental Design (Reuse, Do Not Reimplement)
    16	
    17	All pipelines reuse frozen upstream code without modifying any frozen file:
    18	- **Part 1 (`41000–41399`, scenarios U/G)**:
    19	  - Pipeline/context: `experiments/data_pilot_fer_20261121/stageA.py::setup()` (`cstate -> stage3.context()`), `stageA2.py::crossing()`, `stageA2.py::load()`, and `experiments/huang_steelman_20261124/hs_arms.py::{run_hg_arm, fine_grid, coarse_grid, omp_reacquire}`.
    20	  - Grid: $\rho \in \{100, 150, 200, 250\}$ permille, `SNR = stageA.SNRS` (`300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200` centi-dB; 13 points). Total 41,600 keys; `13,735` archived F0-triggered keys (`rho=100: 5,676; 150: 3,526; 200: 2,377; 250: 2,156`).
    21	  - Arms run live on triggered keys:
    22	    - `HG`: `run_hg_arm(..., ls=fine_grid, recipe='B0-p2-s0.5', dictionary_limit=2575, max_passes=2)` (also logs `HG1` pass 1 at zero extra compute).
    23	    - `HGint`: `run_hg_arm(..., ls=coarse_grid, recipe='B0-p2-s0.5', dictionary_limit=515, max_passes=2)` (subject to G4 budget rule).
    24	  - Trigger gating & parity: read archived `experiments/data_pilot_fer_20261121/out/stageA/rows_shard*.jsonl.gz` (verified against `out/stageA/REMOTE_ROWS_MD5.txt`, SHA-256 `30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68`). If `arms.base.syndrome == 0`, set `HG`/`HGint` errors = `arms.base.f0_errors` without running. Otherwise regenerate `(raw, obs, truth)` and `f0_state`, assert live `syndrome == arms.base.syndrome` and live `f0_errors == arms.base.f0_errors`, then run `HG` and `HGint` on those F0 arrays.
    25	  - Archived comparators on the exact same frames and observations (do not rerun; MD5-verified):
    26	    - `stageA` (`out/stageA`): `base` (`CD`), `delay` (true delays + best pilot-MF integer Doppler), $\rho \in \{50..300\}$, `stageA.SNRS`.
    27	    - `stageA2` (`out/stageA2`, manifest SHA-256 `5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354`): `full` (true round-0 channel), `ldop` (true delays+Doppler, pilot-LS gains), $\rho \in \{50, 100, 150, 200\}$, `stageA2.SNRS = (200, 250) + stageA.SNRS`.
    28	    - `stageA3` (`out/stageA3`, manifest SHA-256 `6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a`): `s025`, `s050`, `s100`, `s200` (true delays + true Doppler + Gaussian error $\sigma \in \{0.025, 0.05, 0.10, 0.20\}$ bin, pilot-LS gains; measured round-0 mean-abs Doppler error: `s050` $\approx 0.040$ bin, `s100` $\approx 0.080$ bin), $\rho \in \{100, 150, 200\}$, `stageA2.SNRS`.
    29	  - **Caveat (explicitly recorded before running)**: `s050` and `s100` are Gaussian Doppler injections that **also assume true delays**; Stage A3 previously showed that real pilot Doppler error hurts less than i.i.d. Gaussian error of the same mean, while unknown delays in a real semi-blind estimator add extra loss. Therefore the `s100` threshold is a structured proxy (strict on Doppler noise shape, optimistic on true delays), not a real end-to-end estimator.
    30	
    31	- **Part 2 (`5400–5799`, scenarios U/G, all 6 $\rho \in \{150, 200, 250, 300, 400, 500\}$, 13 SNRs, `18,009` archived F0-triggered keys)**:
    32	  - Archived rows reused (MD5-verified): `rho_sweep_20261119/out/main_20261119` (manifest SHA-256 `98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd`) for untriggered keys, `F0`, and archived `CD`; `huang_steelman_20261124/out/raw` (manifest SHA-256 `b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc`) for archived `HG`, `HG1`, `HGint`, `Z`.
    33	  - New live arms on the `18,009` archived F0-triggered keys:
    34	    - `CD2`: Pass 1 calls `stage3.e1.run_branch(ctx, cd, obs, arrays, 'A1')` and asserts exact bit-parity (`errors` and `decoded_sha`) with archived `CD` on every key. If pass-1 `syndrome != 0`, Pass 2 calls `run_branch(..., 'A1')` on updated arrays (`r1_delays`, `r1_dopplers` from `result.paths`; `r1_gains = result.gains`; `r1_check = decoder['raw_check_extrinsic']`; `r1_app = decoder['raw_app']`, identical to `HG`'s inter-pass message update rule). Early stop on `syndrome == 0`.
    35	    - `CD2e8`: Same two-pass schedule using runtime-registered `e1.ARM_SPECS['A1e8'] = dict(gamma_mode='full', max_edits=8, local_passes=2)` (never edits any frozen file).
    36	    - Both arms enforce finite outputs and explicitly raise on `numerical_fallback=True` (no silent fallback).
    37	
    38	---
    39	
    40	## 3. Pre-Execution Gates (G1–G4, written to `out/gate.json`)
    41	
    42	All four gates must pass before launching any evaluation run; if any gate fails, stop and report:
    43	- **G1 (Part-1 F0 replay parity)**: On 20 triggered `stageA` keys (5 per $\rho \in \{100, 150, 200, 250\}$, balanced across U/G and low/mid SNR), live `f0_state` reproduces `arms.base.syndrome` and `arms.base.f0_errors` identically (20/20).
    44	- **G2 (HG wrapper parity)**: On 5 archived `huang_steelman_20261124` triggered keys (spanning U/G and 1-pass + 2-pass stops), calling `hs_arms.run_hg_arm` through the `stageA.setup()` context reproduces archived `HG` and `HG1` `errors` and `decoded_sha` bit-exactly (5/5).
    45	- **G3 (CD2 pass-1 parity + CD2/CD2e8 smoke)**: On 20 archived `rho_sweep_20261119` triggered keys (spanning U/G and all 6 $\rho$, including pass-1 failures), `CD2` pass 1 reproduces archived `CD` `errors` and `decoded_sha` bit-exactly (20/20); both `CD2` pass 2 and `CD2e8` execute cleanly with finite outputs and zero `numerical_fallback`.
    46	- **G4 (Stratified cost projection, 30% margin, $\le 12$ core-hours)**: Measure real CPU time on stratified triggered keys in Part 1 (`4 rhos × 2 SNR bands × 4 keys = 32` keys, balanced U/G) and Part 2 (`6 rhos × 2 SNR bands × 2 keys = 24` keys, balanced U/G), weighted by the exact archived stratum trigger counts (`13,735` Part-1 + `18,009` Part-2), plus `0.25` core-hours I/O & analysis allowance, multiplied by `1.3×`.
    47	  - Budget selection order:
    48	    1. Keep all arms (`HG` + `HGint` on $\rho \in \{100, 150, 200, 250\}$, plus `CD2` + `CD2e8` on all 6 $\rho$) if projected $\le 12.0$ core-hours.
    49	    2. Else drop `HGint` first and recompute; retain if $\le 12.0$ core-hours.
    50	    3. Else also drop $\rho = 250$ from Part 1 and recompute; retain if $\le 12.0$ core-hours.
    51	    4. Else stop immediately (`GATE_STATUS=FAIL_BUDGET`) and report to Eric.
    52	
    53	---
    54	
    55	## 4. Frozen Readout & Verdict Rules (Never Relabel After Running)
    56	
    57	### Primary P1 (Frames `41000–41399`)
    58	- **Crossing**: 1% info-FER via `stageA2.crossing(fer, snrs)` on each arm's own SNR grid (`stageA.SNRS` for `HG`/`HGint`/`base`/`delay`; `stageA2.SNRS` for `full`/`ldop`/`s025`/`s050`/`s100`/`s200`), arithmetic mean over scenarios U and G.
    59	- **Estimand**: $D = \min_{\rho \in \mathcal{R}_1} c_{\mathrm{HG}}(\rho) - \min_{\rho \in \{100, 150, 200\}} c_{\mathrm{s100}}(\rho)$, where $\mathcal{R}_1 = \{100, 150, 200, 250\}$ (or $\{100, 150, 200\}$ if G4 drops $\rho=250$). Positive $D$ means `s100` beats `HG` (remaining round-0 Doppler headroom).
    60	- **Bootstrap**: Paired physical-frame bootstrap (`2,000` draws, `seed = 20261124`) jointly resampling frames `41000–41399` across `stageA`, `stageA2`, `stageA3`, and new Part-1 rows; **95% percentile CI** (`[2.5, 97.5]`). Censoring safety: if any bootstrap draw is left/right censored (`-inf`/`+inf`), apply conservative interval bounds `[-inf, x_min]` / `[x_max, +inf]` without dropping draws and report `censored_draw_fraction` (when all draws are finite, reduces identically to `np.percentile(D_boot, [2.5, 97.5])`).
    61	- **Mutually exclusive verdict table**:
    62	  - `DOPPLER-LINE`: CI lower $\ge 0.5$ dB
    63	  - `WRITE-A`: CI upper $< 0.5$ dB
    64	  - `INCONCLUSIVE`: otherwise (including unbounded/censored CIs straddling `0.5` dB)
    65	- **Secondary P1 readouts (descriptive)**: same paired `D` and 95% CI replacing `s100` with `s050`, `ldop`, `full`; replacing `HG` with `HGint` (if retained) and `HG1`; full per-$\rho$ crossing table of all arms; point optimal $\rho$ of `HG` (and `HGint`).
    66	
    67	### Primary P2 (Frames `5400–5799`)
    68	- **Crossing & CI**: Exact `hs_analysis.py` pipeline (`p1_agg.crossing`, `50,000` paired physical-frame bootstrap draws, `seed = 20261124`, 36-pair simultaneous confidence projection `projected_best_diff` over all 6 $\rho \in \{150, 200, 250, 300, 400, 500\}$).
    69	- **Estimands**:
    70	  - $E = \min_{\rho} c_{\mathrm{CD2}}(\rho) - \min_{\rho} c_{\mathrm{HG}}(\rho)$
    71	  - $E_8 = \min_{\rho} c_{\mathrm{CD2e8}}(\rho) - \min_{\rho} c_{\mathrm{HG}}(\rho)$
    72	  (Positive values mean `HG` requires lower SNR than `CD2`/`CD2e8`, i.e., local exchange remains behind.)
    73	- **Frozen verdict confidence level**: **98.33% 36-pair projected CI** ($\alpha = 0.05/3$, matching the primary Huang readout and stricter than 2-test Bonferroni $\alpha = 0.025$). Both **98.33%** and **95%** 36-pair projected CIs (plus per-draw CIs) are reported side by side.
    74	- **Mutually exclusive verdict table (applied identically to `E` and `E8` on the 98.33% projected CI)**:
    75	  - `STILL_BEHIND`: CI lower $> 0.2$ dB
    76	  - `CATCHES_UP`: CI upper $< 0.2$ dB
    77	  - `MIXED`: otherwise
    78	- **Secondary P2 readouts**: per-$\rho$ crossing table (`F0`, `CD`, `CD2`, `CD2e8`, `HG`, `HG1`, `HGint`, `Z`); `CD2 − CD`, `CD2e8 − CD`, `CD2 − HGint`, `CD2e8 − HGint`; pass-2 rescue counts and pass-1/pass-2 edit counts for `CD2` and `CD2e8`.
    79	
    80	---
    81	
    82	## 5. Pre-Registered Forecasts (Recorded in `research-assets/prediction-ledger.md` Before Running)
    83	
    84	- **Claude**:
    85	  - `SF-C1` (P1 verdict): `DOPPLER-LINE` .35 / `INCONCLUSIVE` .40 / `WRITE-A` .25
    86	  - `SF-C2` (P2 `CD2` verdict): `STILL_BEHIND` .65 / `MIXED` .25 / `CATCHES_UP` .10
    87	- **agy (Gemini 4 Neon)**:
    88	  - `SF-G1` (P1 verdict): `DOPPLER-LINE` .25 / `INCONCLUSIVE` .45 / `WRITE-A` .30
    89	  - `SF-G2` (P2 `CD2` verdict): `STILL_BEHIND` .45 / `MIXED` .45 / `CATCHES_UP` .10
    90	  - `SF-G3` (P2 `CD2e8` verdict): `STILL_BEHIND` .20 / `MIXED` .45 / `CATCHES_UP` .35
    91	
    92	---
    93	
    94	## 6. Execution & Provenance Rules (deinlab)
    95	
    96	- Working directory: `cd /data/guoyikun/00inbox/AFDM-channel-estimation`; conda env `AFDM` (`/home/guoyikun/.conda/envs/AFDM/bin/python`, printed as line 1 of every log).
    97	- Thread & scratch isolation: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `BLIS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, `CUDA_VISIBLE_DEVICES=""`, `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR=/data/guoyikun/tmp`, `XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`. Never write to `/tmp` or `/home/guoyikun`.
    98	- Workers: `24` ($\le 32$, respecting concurrent funnel workload on the 128-core host); `tmux` session `g_sameframe`.
    99	- Hard budget stop: live cumulative CPU monitoring capped at `12.0` core-hours (`STOPPED_BUDGET` on breach).
   100	- Large raw JSONL.gz shards stay on deinlab (`experiments/sameframe_hg_20261124/out/raw/`) with MD5 recorded locally in `out/REMOTE_ROWS_MD5.txt`. Small outputs (`gate.json`, `results.json` with `_argv` & `_config`, `RESULTS.md`, `REMOTE_ROWS_MD5.txt`, `STATUS`, logs) copied locally.
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
    12	HERE="$REPO/experiments/sameframe_hg_20261124"
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
    49	        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/sameframe.py" \
    50	        gate --out "$OUT" --workers 16 \
    51	        > "$OUT/gate.log" 2>&1
    52	    exit $?
    53	fi
    54	
    55	if [ "$MODE" = "run" ]; then
    56	    if [ -d "$OUT/raw" ] && ls "$OUT/raw"/part*_shard*.jsonl* >/dev/null 2>&1; then
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
    69	    # Python enforces live cumulative CPU <= 12.0 core-hours; wall timeout 2700s is outer safety net
    70	    set +e
    71	    /usr/bin/time -q -f '%U %S %e' -o "$OUT/run_cpu.txt" \
    72	        timeout --kill-after=5s 2700s "$PY" -B -u "$HERE/sameframe.py" \
    73	        run --out "$OUT" --freeze-commit "$FREEZE_COMMIT" --workers 24 \
    74	        > "$OUT/run.log" 2>&1
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
    85	    test -s "$OUT/RESULTS.md"
    86	    status=DONE
    87	    exit 0
    88	fi
    89	
    90	rmdir "$LOCKDIR" 2>/dev/null || true
    91	echo "Unknown MODE: $MODE" >&2
    92	exit 2
     1	"""Unit tests for sameframe.py P1/P2 crossing, censoring, joint bootstrap, and verdict rules."""
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
    13	import sameframe as sf  # noqa: E402
    14	import stageA2  # noqa: E402
    15	
    16	
    17	def _make_fail_array(curves: dict[int, list[float]], n_frames: int = 200, seed: int = 7) -> np.ndarray:
    18	    rng = np.random.default_rng(seed)
    19	    u = rng.random((n_frames, 2))
    20	    rhos = sorted(curves)
    21	    n_snrs = len(next(iter(curves.values())))
    22	    out = np.zeros((n_frames, 2, len(rhos), n_snrs), dtype=bool)
    23	    for ri, r in enumerate(rhos):
    24	        for si in range(2):
    25	            for ji, p in enumerate(curves[r]):
    26	                out[:, si, ri, ji] = u[:, si] < p
    27	    return out
    28	
    29	
    30	def test_verdict_boundaries():
    31	    assert sf.p1_verdict(0.5, 0.9) == 'DOPPLER-LINE'
    32	    assert sf.p1_verdict(0.51, 0.9) == 'DOPPLER-LINE'
    33	    assert sf.p1_verdict(0.1, 0.499) == 'WRITE-A'
    34	    assert sf.p1_verdict(-0.2, 0.499) == 'WRITE-A'
    35	    assert sf.p1_verdict(0.499, 0.5) == 'INCONCLUSIVE'
    36	    assert sf.p1_verdict(-math.inf, math.inf) == 'INCONCLUSIVE'
    37	
    38	    assert sf.p2_verdict(0.201, 0.8) == 'STILL_BEHIND'
    39	    assert sf.p2_verdict(0.2, 0.8) == 'MIXED'
    40	    assert sf.p2_verdict(-0.3, 0.199) == 'CATCHES_UP'
    41	    assert sf.p2_verdict(-0.3, 0.2) == 'MIXED'
    42	    assert sf.p2_verdict(-math.inf, math.inf) == 'MIXED'
    43	
    44	
    45	def test_p1_joint_bootstrap_and_censoring():
    46	    snrs_a = (300, 400, 500, 600, 700)
    47	    snrs_a3 = (200, 250, 300, 400, 500, 600, 700)
    48	    # Identical curves shifted by 1.0 dB -> D = +1.0 dB -> DOPPLER-LINE
    49	    c_hg = {100: [0.8, 0.4, 0.05, 0.005, 0.0], 150: [0.5, 0.2, 0.02, 0.002, 0.0], 200: [0.4, 0.1, 0.005, 0.0, 0.0], 250: [0.5, 0.2, 0.01, 0.0, 0.0]}
    50	    c_s100 = {100: [0.6, 0.2, 0.05, 0.005, 0.0, 0.0, 0.0], 150: [0.7, 0.3, 0.08, 0.01, 0.0, 0.0, 0.0], 200: [0.8, 0.4, 0.1, 0.02, 0.005, 0.0, 0.0]}
    51	    fail_by_arm = {
    52	        'HG': ((100, 150, 200, 250), snrs_a, _make_fail_array(c_hg, seed=1)),
    53	        'HG1': ((100, 150, 200, 250), snrs_a, _make_fail_array(c_hg, seed=1)),
    54	        's100': ((100, 150, 200), snrs_a3, _make_fail_array(c_s100, seed=1)),
    55	    }
    56	    res = sf.analyze_part1(fail_by_arm, (100, 150, 200, 250), False, stageA2.crossing, boot_draws=200, boot_seed=42)
    57	    p1 = res['primary_P1']
    58	    assert p1['verdict'] == 'DOPPLER-LINE', p1
    59	    assert p1['censored_draw_fraction'] == 0.0
    60	    assert p1['ci95_db'][0] >= 0.5
    61	
    62	    # Right-censored HG everywhere -> conservative interval [+inf] upper, finite positive lower
    63	    c_rc = {r: [0.9, 0.8, 0.6, 0.4, 0.2] for r in (100, 150, 200, 250)}
    64	    fail_rc = dict(fail_by_arm, HG=((100, 150, 200, 250), snrs_a, _make_fail_array(c_rc, seed=1)))
    65	    res_rc = sf.analyze_part1(fail_rc, (100, 150, 200, 250), False, stageA2.crossing, boot_draws=200, boot_seed=42)
    66	    assert res_rc['primary_P1']['ci95_db'][1] == '+inf'
    67	    assert res_rc['primary_P1']['verdict'] == 'DOPPLER-LINE'
    68	
    69	
    70	if __name__ == '__main__':
    71	    test_verdict_boundaries()
    72	    test_p1_joint_bootstrap_and_censoring()
    73	    print('ALL_SAMEFRAME_UNIT_TESTS_PASS')

exec
/bin/zsh -lc "cat .agents/skills/trellis-start/SKILL.md; git status --short -- experiments/sameframe_hg_20261124; rg --files experiments/sameframe_hg_20261124; rg --files | rg '/(stageA|stageA2|hs_arms|hs_analysis)\\.py"'$'"'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
---
name: trellis-start
description: "Initializes an AI development session by reading workflow guides, developer identity, git status, active tasks, and project guidelines from .trellis/. Classifies incoming tasks and routes to brainstorm, direct edit, or task workflow. Use when beginning a new coding session, resuming work, starting a new task, or re-establishing project context."
---

# Start Session

Initialize a Trellis-managed development session. This platform has no session-start hook, so manually load the equivalent compact context by following these steps.

---

## Step 1: Current state
Identity, git status, current task, active tasks, journal location.

```bash
python3 ./.trellis/scripts/get_context.py
```

If this output includes a line beginning `Trellis update available:`, copy the full line verbatim when summarizing session context. Do not shorten operational command hints.

## Step 2: Workflow overview
Compact Phase Index, request triage rules, planning artifact contract, and the step-detail command.

```bash
python3 ./.trellis/scripts/get_context.py --mode phase
```

Full guide in `.trellis/workflow.md` (read on demand).

## Step 3: Guideline indexes
Discover packages + spec layers, then read each relevant index file.

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
cat .trellis/spec/guides/index.md
cat .trellis/spec/<package>/<layer>/index.md   # for each relevant layer
```

Index files list the specific guideline docs to read when you actually start coding.

## Step 4: Decide next action
From Step 1 you know the current task and status. Check the task directory:

- **Active task status `planning` + no `prd.md`** → Phase 1.1. Load the `trellis-brainstorm` skill.
- **Active task status `planning` + `prd.md` exists** → stay in Phase 1. Lightweight tasks can be PRD-only; complex tasks need `design.md` + `implement.md`. Load the relevant Phase 1 step detail before `task.py start`.
- **Active task status `in_progress`** → Phase 2 step 2.1. Load the step detail:
  ```bash
  python3 ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex
  ```
- **No active task** → classify first. For simple conversation / small task, ask only whether this turn should create a Trellis task. For complex work, ask whether you may create a Trellis task and enter planning. If the user says no, skip Trellis for this session.

---

## Skill routing (quick reference)

| User intent | Skill |
|---|---|
| New feature / unclear requirements | `trellis-brainstorm` |
| About to write code | `trellis-before-dev` |
| Done coding / quality check | `trellis-check` |
| Stuck / fixed same bug multiple times | `trellis-break-loop` |
| Learned something worth capturing | `trellis-update-spec` |

Full rules + anti-rationalization table in `.trellis/workflow.md`.
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-NvXIQ9jS' (errno=Operation not permitted)
?? experiments/sameframe_hg_20261124/
experiments/sameframe_hg_20261124/PROTOCOL.md
experiments/sameframe_hg_20261124/reviews/sol-static-review.md
experiments/sameframe_hg_20261124/test_sameframe.py
experiments/sameframe_hg_20261124/sameframe.py
experiments/sameframe_hg_20261124/launch.sh
experiments/data_pilot_fer_20261121/stageA.py
experiments/data_pilot_fer_20261121/stageA2.py
experiments/huang_steelman_20261124/hs_arms.py
experiments/huang_steelman_20261124/hs_analysis.py

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '736,1085p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   736	                if int(syn) != int(item['syndrome']) or f0 != dict(
   737	                    errors=int(item['arms']['F0']['errors']),
   738	                    decoded_sha=item['arms']['F0']['decoded_sha'],
   739	                ):
   740	                    raise RuntimeError(f'Part2 F0 drift at {(s, rho, snr, frame)}')
   741	                arch_cd = dict(
   742	                    errors=int(item['arms']['CD']['errors']),
   743	                    decoded_sha=item['arms']['CD']['decoded_sha'],
   744	                )
   745	                cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
   746	                cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   747	                out_lines.append(json.dumps(dict(
   748	                    scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=int(syn),
   749	                    arms=dict(CD2=cd2, CD2e8=cd2e8),
   750	                ), allow_nan=False) + '\n')
   751	    _write_gzip_jsonl_atomic(final_path, out_lines)
   752	    print(f'Part2 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   753	
   754	
   755	def _run_sharded_phase(target_fn, job_args: list[tuple[Any, ...]], max_workers: int, cpu_cap_sec: float):
   756	    """Run up to max_workers spawned processes concurrently with live CPU budget check."""
   757	    mp_ctx = multiprocessing.get_context('spawn')
   758	    pending = list(job_args)
   759	    running = {}
   760	    budget_hit = False
   761	    try:
   762	        while pending or running:
   763	            while pending and len(running) < max_workers:
   764	                args = pending.pop(0)
   765	                proc = mp_ctx.Process(target=target_fn, args=args)
   766	                proc.start()
   767	                running[proc.sentinel] = (args[0], proc)
   768	            ready = wait(running, timeout=10.0)
   769	            for r in ready:
   770	                idx, proc = running.pop(r)
   771	                proc.join()
   772	                code = proc.exitcode
   773	                proc.close()
   774	                if code != 0:
   775	                    raise RuntimeError(f'Worker shard {idx:03d} failed with exit code {code}')
   776	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   777	            if live_cpu >= cpu_cap_sec:
   778	                budget_hit = True
   779	                break
   780	    finally:
   781	        for _, proc in running.values():
   782	            proc.terminate()
   783	        for _, proc in running.values():
   784	            proc.join()
   785	            proc.close()
   786	    if budget_hit or _used_cpu_seconds() >= cpu_cap_sec:
   787	        print(f'STOPPED_BUDGET: CPU limit reached ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   788	        sys.exit(BUDGET_EXIT_CODE)
   789	
   790	
   791	# --------------------------------------------------------------------------- Analysis (P1 & P2)
   792	def crossing_bounds_stageA2(fer: np.ndarray, snrs: tuple[int, ...], crossing_fn) -> tuple[float, float]:
   793	    """Wrap stageA2.crossing into conservative (lo, hi) bounds so censored draws never silently yield NaN."""
   794	    c = float(crossing_fn(fer, snrs))
   795	    if math.isfinite(c):
   796	        return c, c
   797	    if c < 0:
   798	        return -math.inf, float(snrs[0]) / 100.0
   799	    return float(snrs[-1]) / 100.0, math.inf
   800	
   801	
   802	def p1_verdict(ci_lo: float, ci_hi: float) -> str:
   803	    if ci_lo >= P1_THRESHOLD_DB:
   804	        return 'DOPPLER-LINE'
   805	    if ci_hi < P1_THRESHOLD_DB:
   806	        return 'WRITE-A'
   807	    return 'INCONCLUSIVE'
   808	
   809	
   810	def p2_verdict(ci_lo: float, ci_hi: float) -> str:
   811	    if ci_lo > P2_THRESHOLD_DB:
   812	        return 'STILL_BEHIND'
   813	    if ci_hi < P2_THRESHOLD_DB:
   814	        return 'CATCHES_UP'
   815	    return 'MIXED'
   816	
   817	
   818	def _rep(v: float) -> Any:
   819	    if math.isinf(v):
   820	        return '+inf' if v > 0 else '-inf'
   821	    if math.isnan(v):
   822	        raise FloatingPointError('NaN encountered in readout')
   823	    return float(v)
   824	
   825	
   826	def analyze_part1(
   827	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   828	    part1_rhos: tuple[int, ...],
   829	    include_hgint: bool,
   830	    crossing_fn,
   831	    *,
   832	    boot_draws: int = PART1_BOOT_DRAWS,
   833	    boot_seed: int = PART1_BOOT_SEED,
   834	) -> dict[str, Any]:
   835	    """Paired physical-frame bootstrap analysis for P1 (frames 41000-41399).
   836	
   837	    fail_by_arm[arm] = (rhos_tuple, snrs_tuple, fail_bool_array[n_frames, 2, n_rhos, n_snrs]).
   838	    """
   839	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   840	    rng = np.random.default_rng(boot_seed)
   841	    # Draw exact multinomial weights once, shared across ALL arms (stageA, stageA2, stageA3, new)
   842	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   843	    weights[0] = 1.0 / n_frames
   844	    for b in range(1, boot_draws + 1):
   845	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   846	
   847	    # Compute U/G mean crossing bounds [boot_draws+1, n_rhos] for every arm
   848	    arm_lo: dict[str, np.ndarray] = {}
   849	    arm_hi: dict[str, np.ndarray] = {}
   850	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   851	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   852	    arm_best_lo: dict[str, np.ndarray] = {}
   853	    arm_best_hi: dict[str, np.ndarray] = {}
   854	    arm_best_rho: dict[str, int] = {}
   855	
   856	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   857	        n_r = len(rhos)
   858	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   859	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   860	        # fer[draw, scen, rho, snr]
   861	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   862	        scen_pt = {'U': {}, 'G': {}}
   863	        for ri, rho in enumerate(rhos):
   864	            for bi in range(boot_draws + 1):
   865	                u_lo, u_hi = crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   866	                g_lo, g_hi = crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   867	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   868	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   869	                if bi == 0:
   870	                    scen_pt['U'][str(rho)] = _rep(u_lo) if u_lo == u_hi else [_rep(u_lo), _rep(u_hi)]
   871	                    scen_pt['G'][str(rho)] = _rep(g_lo) if g_lo == g_hi else [_rep(g_lo), _rep(g_hi)]
   872	        arm_lo[arm] = lo_arr
   873	        arm_hi[arm] = hi_arr
   874	        arm_scen_pt[arm] = scen_pt
   875	        arm_mean_pt[arm] = {
   876	            str(rho): (_rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [_rep(lo_arr[0, ri]), _rep(hi_arr[0, ri])])
   877	            for ri, rho in enumerate(rhos)
   878	        }
   879	        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; others over their own grid (or <=200 for delay)
   880	        if arm == 'delay':
   881	            sub_idx = [i for i, r in enumerate(rhos) if r <= 200]
   882	        else:
   883	            sub_idx = list(range(n_r))
   884	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   885	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   886	        best_pos = int(np.argmin(hi_arr[0, sub_idx]))
   887	        arm_best_rho[arm] = int(rhos[sub_idx[best_pos]])
   888	
   889	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   890	        # D = min_rho arm_a - min_rho arm_b (conservative bounds; collapses to exact diff when finite)
   891	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   892	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   893	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   894	        if cens_frac == 0.0:
   895	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   896	        else:
   897	            lo = an._nearest_rank(d_lo[1:], 0.025)
   898	            hi = an._nearest_rank(d_hi[1:], 0.975)
   899	        pt = _rep(d_lo[0]) if d_lo[0] == d_hi[0] else [_rep(d_lo[0]), _rep(d_hi[0])]
   900	        return dict(
   901	            point_db=pt,
   902	            ci95_db=[_rep(lo), _rep(hi)],
   903	            censored_draw_fraction=cens_frac,
   904	            arm_a_best_db=_rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [_rep(arm_best_lo[arm_a][0]), _rep(arm_best_hi[arm_a][0])],
   905	            arm_a_best_rho=arm_best_rho[arm_a],
   906	            arm_b_best_db=_rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [_rep(arm_best_lo[arm_b][0]), _rep(arm_best_hi[arm_b][0])],
   907	            arm_b_best_rho=arm_best_rho[arm_b],
   908	        )
   909	
   910	    primary_p1 = contrast('HG', 's100')
   911	    p1_lo = float(primary_p1['ci95_db'][0]) if isinstance(primary_p1['ci95_db'][0], float) else (-math.inf if primary_p1['ci95_db'][0] == '-inf' else math.inf)
   912	    p1_hi = float(primary_p1['ci95_db'][1]) if isinstance(primary_p1['ci95_db'][1], float) else (-math.inf if primary_p1['ci95_db'][1] == '-inf' else math.inf)
   913	    primary_p1['verdict'] = p1_verdict(p1_lo, p1_hi)
   914	
   915	    sec_contrasts = {}
   916	    for comp in ('s050', 'ldop', 'full', 'delay', 'base'):
   917	        if comp in fail_by_arm:
   918	            sec_contrasts[f'HG_minus_{comp}'] = contrast('HG', comp)
   919	    sec_contrasts['HG1_minus_s100'] = contrast('HG1', 's100')
   920	    if include_hgint and 'HGint' in fail_by_arm:
   921	        for comp in ('s100', 's050', 'ldop', 'full', 'HG'):
   922	            if comp in fail_by_arm:
   923	                sec_contrasts[f'HGint_minus_{comp}'] = contrast('HGint', comp)
   924	
   925	    return dict(
   926	        boot_draws=boot_draws,
   927	        boot_seed=boot_seed,
   928	        part1_rhos=list(part1_rhos),
   929	        include_hgint=include_hgint,
   930	        primary_P1=primary_p1,
   931	        secondary_contrasts=sec_contrasts,
   932	        mean_crossing=arm_mean_pt,
   933	        crossings_by_scenario=arm_scen_pt,
   934	        best_rho=arm_best_rho,
   935	    )
   936	
   937	
   938	def analyze_part2(
   939	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
   940	    arms: tuple[str, ...],
   941	    *,
   942	    boot_draws: int = an.BOOT_DRAWS,
   943	    boot_seed: int = an.BOOT_SEED,
   944	) -> dict[str, Any]:
   945	    """Reuse hs_analysis crossing & 36-pair simultaneous projection for P2 (frames 5400-5799)."""
   946	    rhos = ar.RHOS
   947	    snrs = ar.SNRS
   948	    frames = ar.MAIN_FRAMES
   949	    errors_by_key = {k: {a: int(r['arms'][a]['errors']) for a in arms} for k, r in full_rows.items()}
   950	    crossings, cells = an.compute_crossings(
   951	        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
   952	    )
   953	    pooled = an.scene_means(crossings, rhos, arms)
   954	
   955	    def eval_p2(arm_a: str, arm_b: str) -> dict[str, Any]:
   956	        c98 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.PRIMARY_ALPHA)
   957	        c95 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.FAMILY_ALPHA)
   958	        _, _, lo98, hi98 = c98['_raw']
   959	        _, _, lo95, hi95 = c95['_raw']
   960	        return dict(
   961	            point_db=c98['point_db'],
   962	            ci9833_projected_db=c98['ci_projected_db'],
   963	            ci9833_per_draw_db=c98['ci_per_draw_db'],
   964	            ci95_projected_db=c95['ci_projected_db'],
   965	            ci95_per_draw_db=c95['ci_per_draw_db'],
   966	            censored_draw_fraction=c98['censored_draw_fraction'],
   967	            verdict=p2_verdict(lo98, hi98),
   968	            verdict_at_95_descriptive=p2_verdict(lo95, hi95),
   969	        )
   970	
   971	    p2_E = eval_p2('CD2', 'HG')
   972	    p2_E8 = eval_p2('CD2e8', 'HG')
   973	
   974	    # Per-scenario P2
   975	    by_scen = {}
   976	    for s in ar.SCENARIOS:
   977	        s_curves = {(r, a): crossings[s, r, a] for r in rhos for a in arms}
   978	        by_scen[s] = {}
   979	        for label, arm_a in (('E_CD2_minus_HG', 'CD2'), ('E8_CD2e8_minus_HG', 'CD2e8')):
   980	            c98 = an.projected_best_diff(s_curves, arm_a, 'HG', rhos, an.PRIMARY_ALPHA)
   981	            _, _, lo98, hi98 = c98['_raw']
   982	            by_scen[s][label] = dict(
   983	                point_db=c98['point_db'],
   984	                ci9833_projected_db=c98['ci_projected_db'],
   985	                verdict=p2_verdict(lo98, hi98),
   986	            )
   987	
   988	    # Secondary contrasts (95% projected CI)
   989	    sec = {}
   990	    for name, a1, a2 in (
   991	        ('CD2_minus_CD', 'CD2', 'CD'),
   992	        ('CD2e8_minus_CD', 'CD2e8', 'CD'),
   993	        ('CD2e8_minus_CD2', 'CD2e8', 'CD2'),
   994	        ('CD2_minus_HGint', 'CD2', 'HGint'),
   995	        ('CD2e8_minus_HGint', 'CD2e8', 'HGint'),
   996	    ):
   997	        if a1 in arms and a2 in arms:
   998	            c = an.projected_best_diff(pooled, a1, a2, rhos, an.FAMILY_ALPHA)
   999	            sec[name] = {k: v for k, v in c.items() if k != '_raw'}
  1000	
  1001	    # Scene-averaged crossing table
  1002	    pooled_table = {}
  1003	    best_rho = {}
  1004	    for a in arms:
  1005	        pooled_table[a] = {}
  1006	        best_val = math.inf
  1007	        best_r = rhos[0]
  1008	        for r in rhos:
  1009	            b = pooled[r, a]
  1010	            lo95, hi95 = an._interval(b, 0.05)
  1011	            pt_lo, pt_hi = float(b.lower[0]), float(b.upper[0])
  1012	            pooled_table[a][str(r)] = dict(
  1013	                point_db=[_rep(pt_lo), _rep(pt_hi)],
  1014	                ci95_db=[_rep(lo95), _rep(hi95)],
  1015	            )
  1016	            if pt_hi < best_val:
  1017	                best_val = pt_hi
  1018	                best_r = r
  1019	        best_rho[a] = int(best_r)
  1020	
  1021	    # Diagnostics on triggered keys
  1022	    trig_rows = [r for r in full_rows.values() if r['triggered']]
  1023	    diag = {}
  1024	    for arm in ('CD2', 'CD2e8'):
  1025	        p1_stop = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 1)
  1026	        p2_ran = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 2)
  1027	        p2_rescued = sum(
  1028	            1 for r in trig_rows
  1029	            if r['arms'][arm]['passes_used'] == 2 and r['arms'][arm]['pass1_errors'] > 0 and r['arms'][arm]['errors'] == 0
  1030	        )
  1031	        vs_hg = dict(
  1032	            arm_only=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] > 0),
  1033	            hg_only=sum(1 for r in trig_rows if r['arms']['HG']['errors'] == 0 and r['arms'][arm]['errors'] > 0),
  1034	            both=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] == 0),
  1035	            neither=sum(1 for r in trig_rows if r['arms'][arm]['errors'] > 0 and r['arms']['HG']['errors'] > 0),
  1036	        )
  1037	        diag[arm] = dict(
  1038	            triggered=len(trig_rows),
  1039	            pass1_early_stop=p1_stop,
  1040	            pass2_ran=p2_ran,
  1041	            pass2_rescued=p2_rescued,
  1042	            mean_pass1_edits=float(np.mean([r['arms'][arm]['pass1_edits'] for r in trig_rows])),
  1043	            mean_pass2_edits_when_ran=float(np.mean([r['arms'][arm]['pass2_edits'] for r in trig_rows if r['arms'][arm]['passes_used'] == 2])) if p2_ran else 0.0,
  1044	            paired_vs_hg=vs_hg,
  1045	        )
  1046	
  1047	    return dict(
  1048	        boot_draws=boot_draws,
  1049	        boot_seed=boot_seed,
  1050	        primary_alpha=an.PRIMARY_ALPHA,
  1051	        E_CD2_minus_HG=p2_E,
  1052	        E8_CD2e8_minus_HG=p2_E8,
  1053	        by_scenario=by_scen,
  1054	        secondary_contrasts_95=sec,
  1055	        pooled_crossings=pooled_table,
  1056	        best_rho=best_rho,
  1057	        diagnostics=diag,
  1058	        cells=cells,
  1059	    )
  1060	
  1061	
  1062	def render_results_md(res: dict[str, Any]) -> str:
  1063	    p1 = res['part1']
  1064	    p2 = res['part2']
  1065	    q1 = p1['primary_P1']
  1066	    e1 = p2['E_CD2_minus_HG']
  1067	    e8 = p2['E8_CD2e8_minus_HG']
  1068	
  1069	    def fval(x):
  1070	        if isinstance(x, list):
  1071	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
  1072	        return x if isinstance(x, str) else f'{x:.4f}'
  1073	
  1074	    lines = [
  1075	        '# Same-Frame Decisive Check Results (`sameframe_hg_20261124`)',
  1076	        '',
  1077	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
  1078	        f'- Cumulative CPU: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 12.0 h; wall {res["runtime"]["total_wall_seconds"]:.1f} s)',
  1079	        '',
  1080	        '## Primary Verdicts (Pre-Registered)',
  1081	        '',
  1082	        '| Test | Contrast | Point (dB) | Primary CI (dB) | Verdict |',
  1083	        '|---|---|---:|---|---|',
  1084	        f'| **P1** (95% paired) | `min HG (100..250) − min s100 (100..200)` | {fval(q1["point_db"])} | [{fval(q1["ci95_db"][0])}, {fval(q1["ci95_db"][1])}] | **{q1["verdict"]}** |',
  1085	        f'| **P2-E** (98.33% 36-pair proj) | `min CD2 − min HG` | {fval(e1["point_db"])} | [{fval(e1["ci9833_projected_db"][0])}, {fval(e1["ci9833_projected_db"][1])}] (95%: [{fval(e1["ci95_projected_db"][0])}, {fval(e1["ci95_projected_db"][1])}]) | **{e1["verdict"]}** |',

exec
/bin/zsh -lc "nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '345,735p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   345	def _g4_part1_worker(in_path: str, out_path: str):
   346	    C, _, _, helpers = load_stage_runtime()
   347	    stage3, ctx = C['stage3'], C['ctx']
   348	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   349	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   350	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   351	    res = []
   352	    for s, rho, snr, frame, band in jobs:
   353	        t0 = time.process_time()
   354	        base = stage3.inputs(ctx, frame, s, rho)
   355	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   356	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   357	        t_f0 = time.process_time() - t0
   358	        if int(syn) == 0:
   359	            raise AssertionError(f'G4 part1 key untriggered: {(s, rho, snr, frame)}')
   360	        t1 = time.process_time()
   361	        hg = ar.run_hg_arm(
   362	            ctx, helpers, obs, arrays, truth,
   363	            ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   364	            max_passes=2, record_match=False,
   365	        )
   366	        t_hg = time.process_time() - t1
   367	        t2 = time.process_time()
   368	        hgint = ar.run_hg_arm(
   369	            ctx, helpers, obs, arrays, truth,
   370	            ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   371	            max_passes=2, record_match=False,
   372	        )
   373	        t_hgint = time.process_time() - t2
   374	        res.append(dict(
   375	            key=[s, rho, snr, frame], rho=rho, band=band,
   376	            f0_cpu=t_f0, hg_cpu=t_hg, hgint_cpu=t_hgint,
   377	            hg_passes=hg['HG']['passes_used'], hgint_passes=hgint['HG']['passes_used'],
   378	        ))
   379	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   380	
   381	
   382	def _g4_part2_worker(in_path: str, out_path: str):
   383	    C, _, _, helpers = load_stage_runtime()
   384	    stage3, ctx = C['stage3'], C['ctx']
   385	    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
   386	    res = []
   387	    for s, rho, snr, frame, band, arch_cd in jobs:
   388	        t0 = time.process_time()
   389	        base = stage3.inputs(ctx, frame, s, rho)
   390	        _, obs, truth = stage3.observed(ctx, base, rho, snr)
   391	        _, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   392	        t_f0 = time.process_time() - t0
   393	        if int(syn) == 0:
   394	            raise AssertionError(f'G4 part2 key untriggered: {(s, rho, snr, frame)}')
   395	        t1 = time.process_time()
   396	        cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
   397	        t_cd2 = time.process_time() - t1
   398	        t2 = time.process_time()
   399	        cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   400	        t_cd2e8 = time.process_time() - t2
   401	        res.append(dict(
   402	            key=[s, rho, snr, frame], rho=rho, band=band,
   403	            f0_cpu=t_f0, cd2_cpu=t_cd2, cd2e8_cpu=t_cd2e8,
   404	            cd2_passes=cd2['passes_used'], cd2e8_passes=cd2e8['passes_used'],
   405	        ))
   406	    ar.atomic_write_text(Path(out_path), json.dumps(res))
   407	
   408	
   409	def _select_balanced_keys(
   410	    keys_by_stratum: dict[tuple[int, str], list[tuple[str, int, int, int]]],
   411	    per_stratum: int,
   412	) -> list[tuple[str, int, int, int, str]]:
   413	    """Select balanced U/G and SNR-spread keys per (rho, band) deterministically."""
   414	    selected = []
   415	    for (rho, band), ks in sorted(keys_by_stratum.items()):
   416	        # Group by scenario and pick spread-out indices across sorted (snr, frame)
   417	        u_ks = sorted((k for k in ks if k[0] == 'U'), key=lambda k: (k[2], k[3]))
   418	        g_ks = sorted((k for k in ks if k[0] == 'G'), key=lambda k: (k[2], k[3]))
   419	        n_each = per_stratum // 2
   420	        picks = []
   421	        for pool in (u_ks, g_ks):
   422	            if len(pool) < n_each:
   423	                raise RuntimeError(f'Insufficient keys in stratum {(rho, band)}: {len(pool)} < {n_each}')
   424	            idxs = np.linspace(0, len(pool) - 1, n_each, dtype=int)
   425	            picks.extend(pool[int(i)] for i in idxs)
   426	        for s, r, snr, f in picks:
   427	            selected.append((s, r, snr, f, band))
   428	    return selected
   429	
   430	
   431	def cmd_gate(args):
   432	    print(sys.executable, flush=True)
   433	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
   434	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
   435	    thread_env = ar.check_thread_env()
   436	    started = time.monotonic()
   437	
   438	    manifests = {name: verify_manifest(name) for name in ARCHIVE_MANIFESTS}
   439	    C, _, _, helpers = load_stage_runtime()
   440	    ctx = C['ctx']
   441	
   442	    stageA_base = load_stageA_base(PART1_RHOS)
   443	    rho_arch, _ = ar.load_archived_rho_sweep()
   444	
   445	    # Load 5 archived huang_steelman HG keys (mix of U/G and 1-pass/2-pass stops)
   446	    g2_jobs = []
   447	    seen_p = set()
   448	    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
   449	        with p.open('r', encoding='utf-8') as fh:
   450	            for line in fh:
   451	                r = json.loads(line)
   452	                pu = int(r['arms']['HG']['passes_used'])
   453	                tag = (r['scenario'], pu)
   454	                if len(g2_jobs) < 5 and (tag not in seen_p or len(seen_p) >= 4):
   455	                    seen_p.add(tag)
   456	                    g2_jobs.append(dict(
   457	                        key=[r['scenario'], int(r['rho_permille']), int(r['snr_centi_db']), int(r['frame'])],
   458	                        HG=dict(
   459	                            errors=int(r['arms']['HG']['errors']),
   460	                            decoded_sha=r['arms']['HG']['decoded_sha'],
   461	                            passes_used=pu,
   462	                        ),
   463	                        HG1=dict(
   464	                            errors=int(r['arms']['HG1']['errors']),
   465	                            decoded_sha=r['arms']['HG1']['decoded_sha'],
   466	                        ),
   467	                    ))
   468	                if len(g2_jobs) >= 5:
   469	                    break
   470	        if len(g2_jobs) >= 5:
   471	            break
   472	    if len(g2_jobs) != 5:
   473	        raise RuntimeError(f'Expected 5 huang HG keys for G2, got {len(g2_jobs)}')
   474	
   475	    # G1: 20 triggered stageA keys (5 per rho in 100..250, balanced U/G & SNR)
   476	    p1_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   477	    for k, v in stageA_base.items():
   478	        if v['syndrome'] != 0:
   479	            band = 'low' if k[2] <= 400 else 'mid'
   480	            p1_strata.setdefault((k[1], band), []).append(k)
   481	    g1_jobs = []
   482	    for rho in PART1_RHOS:
   483	        trig = sorted(p1_strata[(rho, 'low')] + p1_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   484	        idxs = np.linspace(0, len(trig) - 1, 5, dtype=int)
   485	        for i in idxs:
   486	            s, r, snr, f = trig[int(i)]
   487	            v = stageA_base[(s, r, snr, f)]
   488	            g1_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors']])
   489	
   490	    # G3: 20 triggered rho_sweep keys across all 6 rhos (mix of CD pass-1 pass and fail)
   491	    p2_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   492	    for k, r in rho_arch.items():
   493	        if r['triggered']:
   494	            band = 'low' if k[2] <= 400 else 'mid'
   495	            p2_strata.setdefault((k[1], band), []).append(k)
   496	    g3_jobs = []
   497	    for rho in ar.RHOS:
   498	        all_r = sorted(p2_strata[(rho, 'low')] + p2_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   499	        fails = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) > 0]
   500	        passes = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) == 0]
   501	        picks = [fails[0], fails[len(fails) // 2], passes[0]] + ([passes[-1]] if rho in (200, 300) else [])
   502	        for k in picks:
   503	            cd_arch = rho_arch[k]['arms']['CD']
   504	            g3_jobs.append(dict(
   505	                key=list(k),
   506	                CD=dict(errors=int(cd_arch['errors']), decoded_sha=cd_arch['decoded_sha']),
   507	            ))
   508	    g3_jobs = g3_jobs[:20]
   509	
   510	    # G4 stratified samples
   511	    g4_p1_picks = _select_balanced_keys(p1_strata, per_stratum=4)  # 4 rhos * 2 bands * 4 = 32 keys
   512	    g4_p2_picks = _select_balanced_keys(p2_strata, per_stratum=2)  # 6 rhos * 2 bands * 2 = 24 keys
   513	    g4_p2_jobs = [
   514	        [s, r, snr, f, band, dict(
   515	            errors=int(rho_arch[(s, r, snr, f)]['arms']['CD']['errors']),
   516	            decoded_sha=rho_arch[(s, r, snr, f)]['arms']['CD']['decoded_sha'],
   517	        )]
   518	        for s, r, snr, f, band in g4_p2_picks
   519	    ]
   520	
   521	    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
   522	    ipc_dir = tmp_root / f'sameframe_gates_ipc_{os.getpid()}'
   523	    ipc_dir.mkdir(parents=True, exist_ok=True)
   524	    try:
   525	        print('Running G1 (20 stageA F0 replay keys)...', flush=True)
   526	        g1_rows = _spawn_map(_g1_worker, g1_jobs, args.workers, ipc_dir, 'g1')
   527	        print(f'G1 PASS ({len(g1_rows)}/20)', flush=True)
   528	
   529	        print('Running G2 (5 archived huang HG parity keys)...', flush=True)
   530	        g2_rows = _spawn_map(_g2_worker, g2_jobs, min(5, args.workers), ipc_dir, 'g2')
   531	        print(f'G2 PASS ({len(g2_rows)}/5)', flush=True)
   532	
   533	        print('Running G3 (20 CD2 pass-1 parity + CD2/CD2e8 smoke keys)...', flush=True)
   534	        g3_rows = _spawn_map(_g3_worker, g3_jobs, args.workers, ipc_dir, 'g3')
   535	        print(f'G3 PASS ({len(g3_rows)}/20)', flush=True)
   536	
   537	        print(f'Running G4 cost projection ({len(g4_p1_picks)} Part-1 + {len(g4_p2_jobs)} Part-2 keys)...', flush=True)
   538	        g4_p1_rows = _spawn_map(_g4_part1_worker, [list(x) for x in g4_p1_picks], args.workers, ipc_dir, 'g4p1')
   539	        g4_p2_rows = _spawn_map(_g4_part2_worker, g4_p2_jobs, args.workers, ipc_dir, 'g4p2')
   540	    finally:
   541	        shutil.rmtree(ipc_dir, ignore_errors=True)
   542	
   543	    # Compute stratified cost projections
   544	    p1_counts = {k: len(v) for k, v in p1_strata.items()}
   545	    p2_counts = {k: len(v) for k, v in p2_strata.items()}
   546	
   547	    def project(part1_rhos: tuple[int, ...], include_hgint: bool) -> dict[str, Any]:
   548	        p1_sec = 0.0
   549	        p1_detail = {}
   550	        for rho in part1_rhos:
   551	            for band in ('low', 'mid'):
   552	                sub = [x for x in g4_p1_rows if x['rho'] == rho and x['band'] == band]
   553	                mean_cpu = float(np.mean([
   554	                    x['f0_cpu'] + x['hg_cpu'] + (x['hgint_cpu'] if include_hgint else 0.0)
   555	                    for x in sub
   556	                ]))
   557	                cnt = p1_counts[(rho, band)]
   558	                p1_sec += mean_cpu * cnt
   559	                p1_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   560	        p2_sec = 0.0
   561	        p2_detail = {}
   562	        for rho in ar.RHOS:
   563	            for band in ('low', 'mid'):
   564	                sub = [x for x in g4_p2_rows if x['rho'] == rho and x['band'] == band]
   565	                mean_cpu = float(np.mean([x['f0_cpu'] + x['cd2_cpu'] + x['cd2e8_cpu'] for x in sub]))
   566	                cnt = p2_counts[(rho, band)]
   567	                p2_sec += mean_cpu * cnt
   568	                p2_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   569	        raw_h = p1_sec / 3600.0 + p2_sec / 3600.0 + OVERHEAD_HOURS
   570	        marg_h = raw_h * COST_MARGIN
   571	        return dict(
   572	            part1_rhos=list(part1_rhos),
   573	            include_hgint=include_hgint,
   574	            part1_raw_hours=p1_sec / 3600.0,
   575	            part2_raw_hours=p2_sec / 3600.0,
   576	            overhead_hours=OVERHEAD_HOURS,
   577	            raw_total_hours=raw_h,
   578	            projected_hours_with_margin=marg_h,
   579	            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
   580	            part1_strata=p1_detail,
   581	            part2_strata=p2_detail,
   582	        )
   583	
   584	    candidates = [
   585	        project(PART1_RHOS, True),
   586	        project(PART1_RHOS, False),
   587	        project((100, 150, 200), False),
   588	    ]
   589	    selected = next((c for c in candidates if c['within_budget']), None)
   590	    gate_cpu_h = _used_cpu_seconds() / 3600.0
   591	    all_passed = bool(len(g1_rows) == 20 and len(g2_rows) == 5 and len(g3_rows) == 20 and selected is not None)
   592	
   593	    out_dir = args.out.resolve()
   594	    out_dir.mkdir(parents=True, exist_ok=True)
   595	    payload = dict(
   596	        _argv=sys.argv,
   597	        _config=dict(
   598	            python_executable=sys.executable,
   599	            threads=thread_env,
   600	            workers=args.workers,
   601	            own_md5=own_md5(),
   602	            frozen_extra_md5=helpers['extra_md5'],
   603	            p1_source_md5=ar.frozen_p1_md5(ctx),
   604	            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
   605	            archive_shards_verified={k: len(v) for k, v in manifests.items()},
   606	        ),
   607	        all_passed=all_passed,
   608	        selected=None if selected is None else dict(
   609	            part1_rhos=selected['part1_rhos'],
   610	            include_hgint=selected['include_hgint'],
   611	            projected_hours_with_margin=selected['projected_hours_with_margin'],
   612	            raw_total_hours=selected['raw_total_hours'],
   613	        ),
   614	        G1=dict(passed=len(g1_rows) == 20, keys_checked=len(g1_rows), rows=g1_rows),
   615	        G2=dict(passed=len(g2_rows) == 5, keys_checked=len(g2_rows), rows=g2_rows),
   616	        G3=dict(passed=len(g3_rows) == 20, keys_checked=len(g3_rows), rows=g3_rows),
   617	        G4=dict(
   618	            passed=selected is not None,
   619	            budget_cap_core_hours=BUDGET_CAP_HOURS,
   620	            margin=COST_MARGIN,
   621	            overhead_hours=OVERHEAD_HOURS,
   622	            candidates=candidates,
   623	        ),
   624	        gate_cpu_hours=gate_cpu_h,
   625	        gate_wall_seconds=time.monotonic() - started,
   626	    )
   627	    ar.atomic_write_text(out_dir / 'gate.json', json.dumps(payload, indent=2, allow_nan=False) + '\n')
   628	    print(
   629	        f'GATE_STATUS={"PASS" if all_passed else "FAIL_BUDGET"} '
   630	        f'selected={payload["selected"]} cpu_hours={gate_cpu_h:.4f}',
   631	        flush=True,
   632	    )
   633	    sys.exit(0 if all_passed else 1)
   634	
   635	
   636	def _write_gzip_jsonl_atomic(final_path: Path, lines: list[str]):
   637	    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
   638	    with part_path.open('wb') as raw_fh:
   639	        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
   640	            for ln in lines:
   641	                gz.write(ln.encode('utf-8'))
   642	        raw_fh.flush()
   643	        os.fsync(raw_fh.fileno())
   644	    os.replace(part_path, final_path)
   645	
   646	
   647	def _part1_shard_worker(
   648	    shard_idx: int,
   649	    frames: tuple[int, ...],
   650	    trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]],
   651	    include_hgint: bool,
   652	    raw_dir: Path,
   653	):
   654	    C, _, _, helpers = load_stage_runtime()
   655	    stage3, ctx = C['stage3'], C['ctx']
   656	    ls_fine, ks_fine = ar.fine_grid(ctx.system.l_max_cap)
   657	    ls_int, ks_int = ar.coarse_grid(ctx.system.l_max_cap)
   658	    final_path = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
   659	    out_lines: list[str] = []
   660	    for frame in frames:
   661	        items = trig_by_frame.get(frame, [])
   662	        grouped: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
   663	        for s, rho, snr, exp_syn, exp_f0_err in items:
   664	            grouped.setdefault((s, rho), []).append((snr, exp_syn, exp_f0_err))
   665	        for (s, rho), grp in sorted(grouped.items()):
   666	            base = stage3.inputs(ctx, frame, s, rho)
   667	            for snr, exp_syn, exp_f0_err in sorted(grp):
   668	                _, obs, truth = stage3.observed(ctx, base, rho, snr)
   669	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   670	                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
   671	                if int(syn) != exp_syn or f0_err != exp_f0_err:
   672	                    raise RuntimeError(
   673	                        f'Part1 F0 drift at {(s, rho, snr, frame)}: ({syn},{f0_err}) != ({exp_syn},{exp_f0_err})'
   674	                    )
   675	                hg_out = ar.run_hg_arm(
   676	                    ctx, helpers, obs, arrays, truth,
   677	                    ls=ls_fine, ks=ks_fine, recipe='B0-p2-s0.5', dictionary_limit=len(ls_fine),
   678	                    max_passes=2, record_match=False,
   679	                )
   680	                arms_rec = dict(
   681	                    HG=dict(
   682	                        errors=hg_out['HG']['errors'],
   683	                        decoded_sha=hg_out['HG']['decoded_sha'],
   684	                        syndrome=hg_out['HG']['syndrome'],
   685	                        passes_used=hg_out['HG']['passes_used'],
   686	                    ),
   687	                    HG1=dict(
   688	                        errors=hg_out['HG1']['errors'],
   689	                        decoded_sha=hg_out['HG1']['decoded_sha'],
   690	                        syndrome=hg_out['HG1']['syndrome'],
   691	                    ),
   692	                )
   693	                if include_hgint:
   694	                    hgint_out = ar.run_hg_arm(
   695	                        ctx, helpers, obs, arrays, truth,
   696	                        ls=ls_int, ks=ks_int, recipe='B0-p2-s0.5', dictionary_limit=len(ls_int),
   697	                        max_passes=2, record_match=False,
   698	                    )
   699	                    arms_rec['HGint'] = dict(
   700	                        errors=hgint_out['HG']['errors'],
   701	                        decoded_sha=hgint_out['HG']['decoded_sha'],
   702	                        syndrome=hgint_out['HG']['syndrome'],
   703	                        passes_used=hgint_out['HG']['passes_used'],
   704	                    )
   705	                out_lines.append(json.dumps(dict(
   706	                    scenario=s, rho=rho, snr=snr, frame=frame, syndrome=int(syn), arms=arms_rec,
   707	                ), allow_nan=False) + '\n')
   708	    _write_gzip_jsonl_atomic(final_path, out_lines)
   709	    print(f'Part1 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   710	
   711	
   712	def _part2_shard_worker(
   713	    shard_idx: int,
   714	    frames: tuple[int, ...],
   715	    trig_by_frame: dict[int, list[dict[str, Any]]],
   716	    raw_dir: Path,
   717	):
   718	    C, _, _, helpers = load_stage_runtime()
   719	    stage3, ctx = C['stage3'], C['ctx']
   720	    final_path = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
   721	    out_lines: list[str] = []
   722	    for frame in frames:
   723	        items = trig_by_frame.get(frame, [])
   724	        grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
   725	        for item in items:
   726	            grouped.setdefault((item['scenario'], int(item['rho_permille'])), []).append(item)
   727	        for (s, rho), grp in sorted(grouped.items()):
   728	            base = stage3.inputs(ctx, frame, s, rho)
   729	            for item in sorted(grp, key=lambda x: int(x['snr_centi_db'])):
   730	                snr = int(item['snr_centi_db'])
   731	                raw, obs, truth = stage3.observed(ctx, base, rho, snr)
   732	                if stage3.input_record(raw, obs) != item['inputs']:
   733	                    raise RuntimeError(f'Part2 input mismatch at {(s, rho, snr, frame)}')
   734	                dec, arrays, syn, _ = stage3.e1.f0_state(ctx, obs)
   735	                f0 = stage3.decoded(ctx, dec, truth)

exec
/bin/zsh -lc "nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '1086,1420p'; nl -ba experiments/sameframe_hg_20261124/PROTOCOL.md | tail -38" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
  1086	        f'| **P2-E8** (98.33% 36-pair proj) | `min CD2e8 − min HG` | {fval(e8["point_db"])} | [{fval(e8["ci9833_projected_db"][0])}, {fval(e8["ci9833_projected_db"][1])}] (95%: [{fval(e8["ci95_projected_db"][0])}, {fval(e8["ci95_projected_db"][1])}]) | **{e8["verdict"]}** |',
  1087	        '',
  1088	        '## Part 1: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
  1089	        '',
  1090	    ]
  1091	    p1_arms = [a for a in ('base', 'delay', 'HG', 'HG1', 'HGint', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in p1['mean_crossing']]
  1092	    all_p1_rhos = ('50', '100', '150', '200', '250', '300')
  1093	    lines.append('| Arm | ' + ' | '.join(f'ρ={int(r)/1000:.2f}' for r in all_p1_rhos) + ' | Best ρ |')
  1094	    lines.append('|---|' + '---:|' * len(all_p1_rhos) + '---:|')
  1095	    for a in p1_arms:
  1096	        row_cells = [fval(p1['mean_crossing'][a][r]) if r in p1['mean_crossing'][a] else '—' for r in all_p1_rhos]
  1097	        lines.append(f'| {a} | ' + ' | '.join(row_cells) + f' | {p1["best_rho"][a]/1000:.2f} |')
  1098	    lines += ['', '### Part 1 Secondary Contrasts (95% Paired Frame Bootstrap, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
  1099	    for name, c in p1['secondary_contrasts'].items():
  1100	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')
  1101	
  1102	    lines += ['', '## Part 2: 1% FER Crossings on Huang Frames (5400–5799, U/G Mean, dB)', '']
  1103	    p2_arms = [a for a in ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z') if a in p2['pooled_crossings']]
  1104	    lines.append('| ρ | ' + ' | '.join(p2_arms) + ' |')
  1105	    lines.append('|---:|' + '---|' * len(p2_arms))
  1106	    for r in ar.RHOS:
  1107	        cells_str = []
  1108	        for a in p2_arms:
  1109	            d = p2['pooled_crossings'][a][str(r)]
  1110	            cells_str.append(f'{fval(d["point_db"])} [{fval(d["ci95_db"][0])}, {fval(d["ci95_db"][1])}]')
  1111	        lines.append(f'| {r/1000:.2f} | ' + ' | '.join(cells_str) + ' |')
  1112	
  1113	    lines += ['', '### Part 2 Diagnostics & Secondary Contrasts', '']
  1114	    for arm in ('CD2', 'CD2e8'):
  1115	        d = p2['diagnostics'][arm]
  1116	        v = d['paired_vs_hg']
  1117	        lines.append(
  1118	            f'- `{arm}`: pass-1 stop {d["pass1_early_stop"]}/{d["triggered"]}, '
  1119	            f'pass-2 ran {d["pass2_ran"]} (rescued {d["pass2_rescued"]}), '
  1120	            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}; '
  1121	            f'vs HG: {arm}_only={v["arm_only"]}, HG_only={v["hg_only"]}, both={v["both"]}, neither={v["neither"]}'
  1122	        )
  1123	    lines += ['', '| Contrast | Point (dB) | 95% Projected CI (dB) |', '|---|---:|---|']
  1124	    for name, c in p2['secondary_contrasts_95'].items():
  1125	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci_projected_db"][0])}, {fval(c["ci_projected_db"][1])}] |')
  1126	    return '\n'.join(lines) + '\n'
  1127	
  1128	
  1129	def _do_read(out_dir: Path, gate: dict[str, Any], freeze_commit: str, runtime_info: dict[str, Any], raw_md5: dict[str, str]):
  1130	    import stageA  # noqa: E402
  1131	    import stageA2  # noqa: E402
  1132	    import stageA3  # noqa: E402
  1133	
  1134	    sel = gate['selected']
  1135	    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
  1136	    include_hgint = bool(sel['include_hgint'])
  1137	    raw_dir = out_dir / 'raw'
  1138	
  1139	    # Verify all manifests and our own raw shard MD5s
  1140	    for name in ARCHIVE_MANIFESTS:
  1141	        verify_manifest(name)
  1142	    for fname, expected in raw_md5.items():
  1143	        actual = ar.md5_file(raw_dir / fname)
  1144	        if actual != expected:
  1145	            raise RuntimeError(f'Raw shard MD5 mismatch {fname}: {actual} != {expected}')
  1146	
  1147	    # --- Load Part 1 arrays (archived stageA/A2/A3 + new Part 1) ---
  1148	    fa, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)
  1149	    fa2, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
  1150	    fa3, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)
  1151	
  1152	    stageA_base = load_stageA_base(part1_rhos)
  1153	    new_p1_arms = ('HG', 'HG1') + (('HGint',) if include_hgint else ())
  1154	    fi = {f: i for i, f in enumerate(PART1_FRAMES)}
  1155	    p1_fail = {a: np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool) for a in new_p1_arms}
  1156	    p1_seen = np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool)
  1157	
  1158	    # Fill untriggered keys from stageA_base
  1159	    for (s, rho, snr, f), b in stageA_base.items():
  1160	        if b['syndrome'] == 0:
  1161	            ix = (fi[f], ar.SCENARIOS.index(s), part1_rhos.index(rho), PART1_SNRS.index(snr))
  1162	            err_flag = b['f0_errors'] > 0
  1163	            for a in new_p1_arms:
  1164	                p1_fail[a][ix] = err_flag
  1165	            p1_seen[ix] = True
  1166	
  1167	    # Fill triggered keys from new Part-1 shards
  1168	    p1_trig_seen = 0
  1169	    for shard_idx in range(N_SHARDS):
  1170	        sp = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
  1171	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
  1172	            for line in fh:
  1173	                r = json.loads(line)
  1174	                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), part1_rhos.index(int(r['rho'])), PART1_SNRS.index(int(r['snr'])))
  1175	                if p1_seen[ix]:
  1176	                    raise RuntimeError(f'Duplicate Part1 key {r}')
  1177	                for a in new_p1_arms:
  1178	                    p1_fail[a][ix] = int(r['arms'][a]['errors']) > 0
  1179	                p1_seen[ix] = True
  1180	                p1_trig_seen += 1
  1181	    if not p1_seen.all():
  1182	        raise RuntimeError(f'Incomplete Part1 grid: missing {int((~p1_seen).sum())} keys')
  1183	
  1184	    fail_by_arm = {
  1185	        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
  1186	        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
  1187	        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
  1188	        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
  1189	    }
  1190	    for i, a in enumerate(stageA3.ARMS):
  1191	        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
  1192	    for a in new_p1_arms:
  1193	        fail_by_arm[a] = (part1_rhos, PART1_SNRS, p1_fail[a])
  1194	
  1195	    print(f'Analyzing Part 1 ({int(p1_seen.sum())} keys, {p1_trig_seen} triggered)...', flush=True)
  1196	    part1_out = analyze_part1(fail_by_arm, part1_rhos, include_hgint, stageA2.crossing)
  1197	
  1198	    # --- Load Part 2 rows (archived rho_sweep + huang_steelman + new CD2/CD2e8) ---
  1199	    rho_arch, _ = ar.load_archived_rho_sweep()
  1200	    huang_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1201	    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
  1202	        with p.open('r', encoding='utf-8') as fh:
  1203	            for line in fh:
  1204	                r = json.loads(line)
  1205	                huang_trig[ar.row_key(r)] = r
  1206	
  1207	    new_p2_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1208	    for shard_idx in range(N_SHARDS):
  1209	        sp = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
  1210	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
  1211	            for line in fh:
  1212	                r = json.loads(line)
  1213	                k = ar.row_key(r)
  1214	                if k in new_p2_trig:
  1215	                    raise RuntimeError(f'Duplicate Part2 key {k}')
  1216	                new_p2_trig[k] = r
  1217	    if len(new_p2_trig) != ar.EXPECTED_TOTAL_TRIGGERS or len(huang_trig) != ar.EXPECTED_TOTAL_TRIGGERS:
  1218	        raise RuntimeError(f'Part2 trigger count mismatch: new={len(new_p2_trig)}, huang={len(huang_trig)}')
  1219	
  1220	    p2_arms = ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z')
  1221	    full_p2: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1222	    for k, arch in rho_arch.items():
  1223	        if arch['triggered']:
  1224	            hr = huang_trig[k]['arms']
  1225	            nr = new_p2_trig[k]['arms']
  1226	            full_p2[k] = dict(
  1227	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
  1228	                triggered=True,
  1229	                arms=dict(
  1230	                    F0=hr['F0'], CD=hr['CD'], HG=hr['HG'], HG1=hr['HG1'], HGint=hr['HGint'], Z=hr['Z'],
  1231	                    CD2=nr['CD2'], CD2e8=nr['CD2e8'],
  1232	                ),
  1233	            )
  1234	        else:
  1235	            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
  1236	            full_p2[k] = dict(
  1237	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
  1238	                triggered=False,
  1239	                arms={a: f0 for a in p2_arms},
  1240	            )
  1241	
  1242	    print(f'Analyzing Part 2 ({len(full_p2)} keys, {len(new_p2_trig)} triggered)...', flush=True)
  1243	    part2_out = analyze_part2(full_p2, p2_arms)
  1244	
  1245	    results = dict(
  1246	        _argv=sys.argv,
  1247	        _config=dict(
  1248	            freeze_commit=freeze_commit,
  1249	            python_executable=sys.executable,
  1250	            own_md5=own_md5(),
  1251	            gate_md5=ar.md5_file(out_dir / 'gate.json'),
  1252	            part1_rhos=list(part1_rhos),
  1253	            include_hgint=include_hgint,
  1254	            part1_frames=[PART1_FRAMES[0], PART1_FRAMES[-1]],
  1255	            part1_triggered_keys=p1_trig_seen,
  1256	            part2_frames=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
  1257	            part2_triggered_keys=len(new_p2_trig),
  1258	            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
  1259	            raw_output_dir=str(raw_dir),
  1260	            raw_rows_md5=raw_md5,
  1261	        ),
  1262	        gates=dict(
  1263	            all_passed=gate['all_passed'],
  1264	            selected=gate['selected'],
  1265	            G1_keys=gate['G1']['keys_checked'],
  1266	            G2_keys=gate['G2']['keys_checked'],
  1267	            G3_keys=gate['G3']['keys_checked'],
  1268	            G4_projected_hours=sel['projected_hours_with_margin'],
  1269	        ),
  1270	        runtime=runtime_info,
  1271	        part1=part1_out,
  1272	        part2=part2_out,
  1273	    )
  1274	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
  1275	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
  1276	    print(
  1277	        f'DONE P1={part1_out["primary_P1"]["verdict"]} '
  1278	        f'P2_CD2={part2_out["E_CD2_minus_HG"]["verdict"]} '
  1279	        f'P2_CD2e8={part2_out["E8_CD2e8_minus_HG"]["verdict"]}',
  1280	        flush=True,
  1281	    )
  1282	
  1283	
  1284	def cmd_run(args):
  1285	    print(sys.executable, flush=True)
  1286	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
  1287	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
  1288	    ar.check_thread_env()
  1289	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
  1290	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
  1291	    if not 1 <= args.workers <= 32:
  1292	        raise ValueError('workers must be in 1..32')
  1293	
  1294	    out_dir = args.out.resolve()
  1295	    raw_dir = out_dir / 'raw'
  1296	    raw_dir.mkdir(parents=True, exist_ok=True)
  1297	    if list(raw_dir.glob('part*_shard*.jsonl*')):
  1298	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
  1299	
  1300	    gate = json.loads((out_dir / 'gate.json').read_text(encoding='utf-8'))
  1301	    if not gate.get('all_passed') or not gate.get('selected'):
  1302	        raise RuntimeError('Refusing to run without passing gate.json')
  1303	    if gate['_config']['own_md5'] != own_md5():
  1304	        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
  1305	
  1306	    sel = gate['selected']
  1307	    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
  1308	    include_hgint = bool(sel['include_hgint'])
  1309	
  1310	    wall_start = time.monotonic()
  1311	    for name in ARCHIVE_MANIFESTS:
  1312	        verify_manifest(name)
  1313	    C, _, _, helpers = load_stage_runtime()
  1314	    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
  1315	        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
  1316	    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
  1317	        raise RuntimeError('p1_source_md5 mismatch vs gate.json')
  1318	
  1319	    # --- Part 1 ---
  1320	    stageA_base = load_stageA_base(part1_rhos)
  1321	    p1_trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]] = {}
  1322	    p1_n_trig = 0
  1323	    for (s, rho, snr, f), b in stageA_base.items():
  1324	        if b['syndrome'] != 0:
  1325	            p1_trig_by_frame.setdefault(f, []).append((s, rho, snr, b['syndrome'], b['f0_errors']))
  1326	            p1_n_trig += 1
  1327	    p1_jobs = [
  1328	        (idx, tuple(PART1_FRAMES[idx::N_SHARDS]), {f: p1_trig_by_frame.get(f, []) for f in PART1_FRAMES[idx::N_SHARDS]}, include_hgint, raw_dir)
  1329	        for idx in range(N_SHARDS)
  1330	    ]
  1331	    print(f'Launching Part 1: {p1_n_trig} triggered keys on {args.workers} workers (rhos={part1_rhos}, hgint={include_hgint})...', flush=True)
  1332	    t_p1 = time.monotonic()
  1333	    _run_sharded_phase(_part1_shard_worker, p1_jobs, args.workers, BUDGET_CAP_SEC)
  1334	    p1_wall = time.monotonic() - t_p1
  1335	    p1_cpu = _used_cpu_seconds()
  1336	    print(f'Part 1 complete: wall={p1_wall:.1f}s, cumulative_cpu={p1_cpu/3600:.4f}h', flush=True)
  1337	
  1338	    # --- Part 2 ---
  1339	    rho_arch, _ = ar.load_archived_rho_sweep()
  1340	    p2_trig_by_frame: dict[int, list[dict[str, Any]]] = {}
  1341	    p2_n_trig = 0
  1342	    for k, r in rho_arch.items():
  1343	        if r['triggered']:
  1344	            p2_trig_by_frame.setdefault(k[3], []).append(r)
  1345	            p2_n_trig += 1
  1346	    p2_jobs = [
  1347	        (idx, tuple(ar.MAIN_FRAMES[idx::N_SHARDS]), {f: p2_trig_by_frame.get(f, []) for f in ar.MAIN_FRAMES[idx::N_SHARDS]}, raw_dir)
  1348	        for idx in range(N_SHARDS)
  1349	    ]
  1350	    print(f'Launching Part 2: {p2_n_trig} triggered keys on {args.workers} workers (CD2 + CD2e8)...', flush=True)
  1351	    t_p2 = time.monotonic()
  1352	    _run_sharded_phase(_part2_shard_worker, p2_jobs, args.workers, BUDGET_CAP_SEC)
  1353	    p2_wall = time.monotonic() - t_p2
  1354	    total_cpu = _used_cpu_seconds()
  1355	    print(f'Part 2 complete: wall={p2_wall:.1f}s, cumulative_cpu={total_cpu/3600:.4f}h', flush=True)
  1356	
  1357	    raw_md5 = {}
  1358	    for prefix in ('part1', 'part2'):
  1359	        for idx in range(N_SHARDS):
  1360	            p = raw_dir / f'{prefix}_shard{idx:03d}.jsonl.gz'
  1361	            raw_md5[p.name] = ar.md5_file(p)
  1362	    ar.atomic_write_text(
  1363	        out_dir / 'REMOTE_ROWS_MD5.txt',
  1364	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
  1365	    )
  1366	
  1367	    runtime_info = dict(
  1368	        part1_wall_seconds=p1_wall,
  1369	        part1_cpu_hours=p1_cpu / 3600.0,
  1370	        part2_wall_seconds=p2_wall,
  1371	        part2_cpu_hours=(total_cpu - p1_cpu) / 3600.0,
  1372	        total_wall_seconds=time.monotonic() - wall_start,
  1373	        total_core_hours=total_cpu / 3600.0,
  1374	        cpu_cap_core_hours=BUDGET_CAP_HOURS,
  1375	    )
  1376	    _do_read(out_dir, gate, args.freeze_commit, runtime_info, raw_md5)
  1377	    final_cpu = _used_cpu_seconds()
  1378	    if final_cpu >= BUDGET_CAP_SEC:
  1379	        print(f'STOPPED_BUDGET after read ({final_cpu/3600:.3f} core-hours)', flush=True)
  1380	        sys.exit(BUDGET_EXIT_CODE)
  1381	
  1382	
  1383	def cmd_read(args):
  1384	    out_dir = args.out.resolve()
  1385	    gate = json.loads((out_dir / 'gate.json').read_text(encoding='utf-8'))
  1386	    raw_md5 = {}
  1387	    for line in (out_dir / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8').splitlines():
  1388	        if line.strip():
  1389	            d, n = line.split()
  1390	            raw_md5[n] = d
  1391	    prev = json.loads((out_dir / 'results.json').read_text(encoding='utf-8')) if (out_dir / 'results.json').is_file() else {}
  1392	    runtime_info = prev.get('runtime', dict(total_core_hours=0.0, total_wall_seconds=0.0, cpu_cap_core_hours=BUDGET_CAP_HOURS))
  1393	    _do_read(out_dir, gate, args.freeze_commit, runtime_info, raw_md5)
  1394	
  1395	
  1396	def main():
  1397	    ap = argparse.ArgumentParser(description=__doc__)
  1398	    sub = ap.add_subparsers(dest='mode', required=True)
  1399	    g = sub.add_parser('gate')
  1400	    g.add_argument('--out', type=Path, required=True)
  1401	    g.add_argument('--workers', type=int, default=16)
  1402	
  1403	    r = sub.add_parser('run')
  1404	    r.add_argument('--out', type=Path, required=True)
  1405	    r.add_argument('--freeze-commit', required=True)
  1406	    r.add_argument('--workers', type=int, default=WORKERS)
  1407	
  1408	    rd = sub.add_parser('read')
  1409	    rd.add_argument('--out', type=Path, required=True)
  1410	    rd.add_argument('--freeze-commit', required=True)
  1411	
  1412	    args = ap.parse_args()
  1413	    dict(gate=cmd_gate, run=cmd_run, read=cmd_read)[args.mode](args)
  1414	
  1415	
  1416	if __name__ == '__main__':
  1417	    main()
    63	  - `WRITE-A`: CI upper $< 0.5$ dB
    64	  - `INCONCLUSIVE`: otherwise (including unbounded/censored CIs straddling `0.5` dB)
    65	- **Secondary P1 readouts (descriptive)**: same paired `D` and 95% CI replacing `s100` with `s050`, `ldop`, `full`; replacing `HG` with `HGint` (if retained) and `HG1`; full per-$\rho$ crossing table of all arms; point optimal $\rho$ of `HG` (and `HGint`).
    66	
    67	### Primary P2 (Frames `5400–5799`)
    68	- **Crossing & CI**: Exact `hs_analysis.py` pipeline (`p1_agg.crossing`, `50,000` paired physical-frame bootstrap draws, `seed = 20261124`, 36-pair simultaneous confidence projection `projected_best_diff` over all 6 $\rho \in \{150, 200, 250, 300, 400, 500\}$).
    69	- **Estimands**:
    70	  - $E = \min_{\rho} c_{\mathrm{CD2}}(\rho) - \min_{\rho} c_{\mathrm{HG}}(\rho)$
    71	  - $E_8 = \min_{\rho} c_{\mathrm{CD2e8}}(\rho) - \min_{\rho} c_{\mathrm{HG}}(\rho)$
    72	  (Positive values mean `HG` requires lower SNR than `CD2`/`CD2e8`, i.e., local exchange remains behind.)
    73	- **Frozen verdict confidence level**: **98.33% 36-pair projected CI** ($\alpha = 0.05/3$, matching the primary Huang readout and stricter than 2-test Bonferroni $\alpha = 0.025$). Both **98.33%** and **95%** 36-pair projected CIs (plus per-draw CIs) are reported side by side.
    74	- **Mutually exclusive verdict table (applied identically to `E` and `E8` on the 98.33% projected CI)**:
    75	  - `STILL_BEHIND`: CI lower $> 0.2$ dB
    76	  - `CATCHES_UP`: CI upper $< 0.2$ dB
    77	  - `MIXED`: otherwise
    78	- **Secondary P2 readouts**: per-$\rho$ crossing table (`F0`, `CD`, `CD2`, `CD2e8`, `HG`, `HG1`, `HGint`, `Z`); `CD2 − CD`, `CD2e8 − CD`, `CD2 − HGint`, `CD2e8 − HGint`; pass-2 rescue counts and pass-1/pass-2 edit counts for `CD2` and `CD2e8`.
    79	
    80	---
    81	
    82	## 5. Pre-Registered Forecasts (Recorded in `research-assets/prediction-ledger.md` Before Running)
    83	
    84	- **Claude**:
    85	  - `SF-C1` (P1 verdict): `DOPPLER-LINE` .35 / `INCONCLUSIVE` .40 / `WRITE-A` .25
    86	  - `SF-C2` (P2 `CD2` verdict): `STILL_BEHIND` .65 / `MIXED` .25 / `CATCHES_UP` .10
    87	- **agy (Gemini 4 Neon)**:
    88	  - `SF-G1` (P1 verdict): `DOPPLER-LINE` .25 / `INCONCLUSIVE` .45 / `WRITE-A` .30
    89	  - `SF-G2` (P2 `CD2` verdict): `STILL_BEHIND` .45 / `MIXED` .45 / `CATCHES_UP` .10
    90	  - `SF-G3` (P2 `CD2e8` verdict): `STILL_BEHIND` .20 / `MIXED` .45 / `CATCHES_UP` .35
    91	
    92	---
    93	
    94	## 6. Execution & Provenance Rules (deinlab)
    95	
    96	- Working directory: `cd /data/guoyikun/00inbox/AFDM-channel-estimation`; conda env `AFDM` (`/home/guoyikun/.conda/envs/AFDM/bin/python`, printed as line 1 of every log).
    97	- Thread & scratch isolation: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `BLIS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, `CUDA_VISIBLE_DEVICES=""`, `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR=/data/guoyikun/tmp`, `XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`. Never write to `/tmp` or `/home/guoyikun`.
    98	- Workers: `24` ($\le 32$, respecting concurrent funnel workload on the 128-core host); `tmux` session `g_sameframe`.
    99	- Hard budget stop: live cumulative CPU monitoring capped at `12.0` core-hours (`STOPPED_BUDGET` on breach).
   100	- Large raw JSONL.gz shards stay on deinlab (`experiments/sameframe_hg_20261124/out/raw/`) with MD5 recorded locally in `out/REMOTE_ROWS_MD5.txt`. Small outputs (`gate.json`, `results.json` with `_argv` & `_config`, `RESULTS.md`, `REMOTE_ROWS_MD5.txt`, `STATUS`, logs) copied locally.

exec
/bin/zsh -lc "python3 .trellis/scripts/get_context.py --mode phase; sed -n '1,65p' STATE.md; rg -n 'deinlab|记录系统|/dev/shm' CLAUDE.md; git status --short -- experiments/data_pilot_fer_20261121 experiments/huang_steelman_20261124 experiments/rho_sweep_20261119" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
## Phase Index

```
Phase 1: Plan    → classify, get task-creation consent, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress
Phase 3: Finish  → verify, update spec, commit, and wrap up
```

### Request Triage

- Simple read-only work: execute directly with appropriate evidence and validation; do not create a Trellis task.
- Small bounded execution: work directly unless persistent task state is materially useful.
- Medium or long work: ask whether you may create a Trellis task and enter planning. If the user says no, do not do broad inline implementation; explain, clarify scope, or suggest a smaller split.
- User approval to create a task is not approval to start implementation. Planning still happens first.

### Planning Artifacts

- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
- `design.md` — technical design for complex tasks: boundaries, contracts, data flow, tradeoffs, compatibility, rollout / rollback shape.
- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
- `implement.jsonl` / `check.jsonl` — spec and research manifests for sub-agent context. They do not replace `implement.md`.
- Lightweight tasks may be PRD-only. Complex tasks must have `prd.md`, `design.md`, and `implement.md` before `task.py start`.

### Parent / Child Task Trees

Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.

Use child tasks for deliverables that can be planned, implemented, checked, and archived independently. Parent/child structure is not a dependency system: if one child must wait for another, write that ordering in the child `prd.md` / `implement.md` and keep each child's acceptance criteria testable.

Create new children with `task.py create "<title>" --slug <name> --parent <parent-dir>`. Link existing tasks with `task.py add-subtask <parent> <child>`, and unlink mistakes with `task.py remove-subtask <parent> <child>`.

<!-- Per-turn breadcrumb: shown when there is no active task (before Phase 1) -->


### Phase 1: Plan
- 1.0 Create task `[required · once]` (only after task-creation consent)
- 1.1 Requirement exploration `[required · repeatable]` (`prd.md`; complex tasks also need `design.md` + `implement.md`)
- 1.2 Research `[optional · repeatable]`
- 1.3 Configure context `[required · once]` — Claude Code, Cursor, OpenCode, Codex, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix (sub-agent-dispatch platforms only; inline platforms skip)
- 1.4 Activate task `[required · once]` (review gate, then `task.py start`; status → in_progress)
- 1.5 Completion criteria

<!-- Per-turn breadcrumb: shown throughout Phase 1 (status='planning') -->


<!-- Per-turn breadcrumb: shown throughout Phase 1 when codex.dispatch_mode=inline.
     Codex-only opt-in alternate to [workflow-state:planning]. The main agent
     edits code directly in Phase 2, so jsonl curation is skipped —
     the inline workflow loads `trellis-before-dev` instead of injecting JSONL
     into a sub-agent. -->


### Phase 2: Execute
- 2.1 Implement `[required · repeatable]`
- 2.2 Quality check `[required · repeatable]`
- 2.3 Rollback `[on demand]`

<!-- Per-turn breadcrumb: shown while status='in_progress'.
     Scope: all of Phase 2 + Phase 3.2-3.4 (status stays 'in_progress' from
     task.py start until task.py archive; only archive flips it). The body
     therefore must cover every required step from implementation through
     commit, including Phase 3.3 spec update and Phase 3.4 commit. -->

Sub-agent dispatch protocol applies to all platforms and all sub-agents, including class-2 Codex/Gemini/Qoder/Copilot/ZCode/Reasonix/Trae and `trellis-research`: every dispatch prompt starts with `Active task: <task path from task.py current>` before role-specific instructions.


<!-- Per-turn breadcrumb: shown while status='in_progress' when
     codex.dispatch_mode=inline. Codex-only opt-in alternate to
     [workflow-state:in_progress]. The main session edits code directly
     instead of dispatching sub-agents. -->


### Phase 3: Finish
- 3.2 Debug retrospective `[on demand]`
- 3.3 Spec update `[required · once]`
- 3.4 Commit changes `[required · once]`
- 3.5 Wrap-up reminder

> Note: step 3.1 was folded into 2.2 (last-iteration full-scope check) and 3.4 (commit preamble). Numbering kept stable to avoid breaking external references.

<!-- Per-turn breadcrumb: shown while status='completed'.
     Currently DEAD in normal flow: cmd_archive writes status='completed' in
     the same call that moves the task dir to archive/, so the active-task
     resolver loses the pointer and the hook never fires on archived tasks.
     Block preserved for a future status-transition redesign (e.g. an
     explicit in_progress→completed command). Edit through the same spec
     channel as the live blocks. -->


### Rules

1. Identify which Phase you're in, then continue from the next step there
2. Run steps in order inside each Phase; `[required]` steps can't be skipped
3. Phases can roll back (e.g., Execute reveals a prd defect → return to Plan to fix, then re-enter Execute)
4. Steps tagged `[once]` are skipped if the output already exists; don't re-run
5. Artifact presence informs the next step; missing `design.md` / `implement.md` is valid for lightweight tasks and incomplete planning for complex tasks.

### Active Task Routing

When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix, Trae]

- Planning or unclear requirements -> `trellis-brainstorm`.
- `in_progress` implementation/check -> dispatch `trellis-implement` / `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Reasonix, Trae]

[codex-inline, Kilo, Antigravity, Devin]

- Planning or unclear requirements -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/codex-inline, Kilo, Antigravity, Devin]

### Guardrails

- Task creation approval is not implementation approval; implementation waits for `task.py start` after artifact review.
- PRD-only is valid for lightweight tasks; complex tasks need `design.md` + `implement.md`.
- Planning must be persisted to task artifacts; checks must run before reporting completion.

### Loading Step Detail

At each step, run this to fetch detailed guidance:

```bash
python3 ./.trellis/scripts/get_context.py --mode phase --step <step>
# e.g. python3 ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

---
# STATE — AFDM-channel-estimation

> Project ID: `afdm-e2e-main`
>
> Title: AFDM Deep-Unfolded Joint Channel Estimation and Detection（历史项目名；论文标题禁用 learned/neural，见下方决定 1）
>
> Lifecycle stage: `contribution framing`（阶段 5：定贡献框架，尚未进入正式写论文阶段）
>
> 当前根：research-assets/index.md 中已接受的结果卡，加本文件“待办与开放线索”。目标期刊沿用已登记的 TCOM；paper/、fyp_new_short/、paper-tmlcn/ 是已结束阶段的旧稿，不带入新论文。开放线索不因登记而成为已接受结果。
>
> 2026-11-18 之前的完整记录逐字保存在 [STATE-history.md](STATE-history.md)（只读）。

## ▶ 接续入口（2026-11-22 更新；新会话先读这里）
- **11-22 Eric 确认（经白话剥壳后）：接收机幻影 / 协方差主线降级**（骨架 v1.4.2、`CODELAY` 与 Γ = 0 等效那条线）：不再是唯一推进线，但不锁死——现稿路线（11-20 定）与已接受卡照旧保留，随时可回来写。
- 当前重心：用 [idea 漏斗](ideas/FUNNEL.md) 找原理级、够 Trans 的新问题（[看板](ideas/BOARD.md)）；`11-21-data-pilot-fer`（低导频）状态不变。下面两条是 11-20 交接时的快照。
- **先读[交接笔记](.trellis/tasks/09-22-tf-production-gap-audit/research/handoff-20261120.md)**：Eric 想要什么（三条主线 + "大一统、妙的 idea"）、我们在追什么（"免费得到的预言"）、已试候选与结果、待他决定的 5 件事。
- 11-20 一句话（已被上面 11-22 两条取代）：原理主线已立（骨架 v1.4.2，前瞻检验支持）；"妙"还没拿到——交换预算预言成立但只是系统层规则（res-19-08），网格 η 预言失败（res-19-09）；写作任务未建。新会话先按交接笔记 §4 的建议顺序问 Eric：先建写作任务，还是先继续挖"妙"（挖哪一条）。
- 11-20 16-QAM 线三方评估后 **Eric 定：对本文关闭**（[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/16qam-line-divergence-20261120.md)）；σ² 判决导向"改符号"已零成本否定（负面台账）。
  待选候选：a₁ ∈ {0,1,5} chirp 临界检验（agy）、反相双径外移律（[Astra xhigh](.trellis/tasks/09-22-tf-production-gap-audit/research/miao-astra-scientist-20261120.md)，计数未复算）；Fable 第 1 轮押"自洽类定律"（`miao-fable-20261120.md`），第 2 轮（自定义"妙"）进行中。
- 11-20 Fable 预言前瞻应验：交换中删去 Γ（Γ = 0）幻影率与 CODELAY 同为 1.84%、救回等效，冻结判定 P-A SUPPORTED / P-B EQUIVALENT（[res-20261120-01](research-assets/res-20261120-01.md)，draft）。
  待 Eric 定：贡献框架是否从"需要精确同延块"改为"自洽性准则"（E-1 解读与骨架第 4 句的更正提议见卡片末节）。
- 11-20 MIXED8（真双径）：Γ = 0 无幻影、双径占位等效，FER 等效未成立（+1.00 pp，INCONCLUSIVE），[res-20261120-02](research-assets/res-20261120-02.md)（draft）；文献检查：分数 Doppler 支撑搜索里无人用对角模型（[lit](.trellis/tasks/11-20-gamma0-exchange/research/lit-diag-soft-variance-20261120.md)）。
- 11-20 MIXED8 重复检验（2,400 新帧）：Γ = 0 的 FER 与 CODELAY 在 ±1.5 pp 内等效，但 CODELAY 保留真近距双径更好（−1.54 pp），[res-20261120-03](research-assets/res-20261120-03.md)（draft）。三腿合起来待 Eric 定贡献框架。
- 11-20 **Eric 定论文路线**（采纳 Astra 版）：现稿以"译码失败后继续迭代还是重搜、各需多少时间"为中心，协方差陷阱降为一节，撤"精确协方差不可替代"；原目标另给两周只看低导频漏径（[分歧表与决定](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261120/divergence.md)）。依据：kill-argument（[报告](.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/KILL_ARGUMENT.md)）、L1 查新（[Gemini](.trellis/tasks/11-20-gamma0-exchange/research/novelty-gemini-20261120.md)：已知部件的新组合）、四份根因分析与 Astra 两步评估。
- 11-24 Huang-2010 式两遍全局重找径对照（冻结 `4772365c`，帧 5400–5799）：`HG_AHEAD`——两遍全局 OMP 最优 4.45 dB（ρ = .20）比局部交换 CD 最优 5.10（ρ = .30）好 0.65 [0.19, 0.97] dB，粗字典版耗时仅 1.07×；Γ = 0 与 CD 等效（+0.05）。现稿"局部交换胜过全局重找"不成立；CD 未给两遍外环（不对称未测）。路线待 Eric 定（[读数](experiments/huang_steelman_20261124/READOUT.md)；[路线分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/route-after-huang-divergence-20261124.md)：两方都否定现稿主张，Neon 默认写诚实系统论文，Claude 先做同帧检验再定）。
- 11-20 低导频漏径线**按停止条件 3 停**（Eric 选零成本探针后停；11-20 验收归档）：ρ = .15 的 CD4 失败帧残留弱径（中位 0.19σ²）、多搜找回 0/19；ρ = .30 失败帧不缺路径（0.012σ²），syndrome 已能预测（AUC .81）。[第一步读数](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/step1-readout-20261120.md)、[探针](.trellis/tasks/archive/2026-11/11-20-low-pilot-missed-path/research/visible-probe-readout-20261120.md)；台账已记，任务待 Eric 验收归档。
- 11-20 候选一（"有反馈时导频只管捕获"）第 0 步计算**未通过**冻结判读：首轮单次匹配滤波下 ZC 导频旁瓣主导弱径检测（80%），预言了不存在的崩塌；**Eric 11-21 停**，已记否定台账（[读数](experiments/pilot_acquisition_calc_20261120/READOUT.md)）。
- 11-20 外部候选三（Stein 闭合估噪）零成本读数：合并判据**成立**（σ̂²/σ² 中位 0.94），但偏差随 SNR 从 0.78 升到 2.66，只在 5.0–5.5 dB 校准；能否收回 1.64 dB 需端到端检验，待 Eric 定（[读数](experiments/stein_sigma2_readout_20261120/READOUT.md)）。
- 11-21 Stein 估噪端到端（冻结）：穿越点 5.46 dB，对已知 σ² 差 +0.31 [0.17, 0.48]（P1 不确定），好于 SF 0.93 [0.65, 1.39]（P2 BETTER），收回 DD 损失约 81%；Eric 11-21：暂不成卡，任务归档，结果留作论文"未知噪声"一节的备选（[读数](experiments/sigma2_stein_20261121/READOUT.md)）。
- 11-21 外部候选"数据当导频"（接收信号延迟–多普勒自相关找径）真实设定零接收机检验（Astra 审后冻结）：ρ = .15 有效弱径捕获 .948，补回导频漏掉的 .919，独立数据对照只有 .042，R1/R2/R3 全过；只证"看得见"，FER 是否移动与新意未检验（[读数](experiments/data_autocorr_acq_20261121/READOUT.md)）。
- 11-21 "数据当导频"查新（Gemini，两步）：(a) 数据二阶统计辨识时变信道、(b) 径对在差分时延–多普勒处恢复多径均**已被做过**（Tsatsanis–Giannakis、Cordes 闪烁弧、Ranieri 稀疏相位恢复、AFDM 上的 Ranasinghe 2407.05328 多帧协方差）；(c) 机制已有、新场景；只剩 (d) 单帧 + 编码 SP-AFDM 降导频交叉点为候选新意，端到端未证。Claude 抽查 2 篇：Ranasinghe 属实（但"T = 1 很差"原文未写），Cordes 差分时延–多普勒属实（全息表述待核 PDF）（[查新](experiments/data_autocorr_acq_20261121/novelty-gemini.md)）。
- 11-21 "数据当导频"第二步（去掉真锚、用导频消镜像，冻结）：R4/R5 全过，ρ = .15 锚正确 1.000，导频漏掉的弱径找回 .832；ρ = .05 第 0 轮覆盖从 .563 提到 .883。下一步只剩改接收机看 FER（决定性检验，待 Eric 定）（[读数](experiments/data_autocorr_acq_20261121/READOUT2.md)）。
- 11-21 建任务 `11-21-data-pilot-fer`（planning）：自相关候选进 F0 第 0 轮的 FER 决定性检验，分阶段 0 预检（只用观测量的选择器）→ A（真时延上界，配对余量门槛 0.3 dB）→ B；设计 v2 已过 Astra 审，待 Eric 批后实现（[设计](.trellis/tasks/11-21-data-pilot-fer/design.md)）。
- 11-21 data-pilot-fer 阶段 0（只用观测量的选择器，冻结）**PASS**：F0 第 0 轮实际漏掉的有效径，召回 .653；但候选精度只有 .192，阶段 B 的槽位规则要防假径（[读数](experiments/data_pilot_fer_20261121/STAGE0_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A（冻结，11.8 核时）**CONTINUE**：第 0 轮给真时延后，低导频最优 4.40 dB（ρ = .20）对基线最优 4.95 dB（ρ = .25），余量 0.55 [0.39, 0.76] dB；时延全对后仍失败的约一半与多普勒误差有关。0b 多锚打分 FALLBACK（[读数](experiments/data_pilot_fer_20261121/STAGEA_READOUT.md)）。
- 11-21 低导频"尾巴"只读检验（冻结）：ρ < .25 不是崩塌，是误帧率曲线尾巴变长（中位帧仍在变好）；ρ = .10–.20 的尾巴键，第 0 轮给真时延后 97% 以上解对。尾巴由信道还是由噪声决定未分开（所有键共用同一份噪声）（[读数](experiments/tail_check_20261121/READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A2（冻结，7.9 核时）**CONTINUE**：第 0 轮给全真信道后最优 3.45 dB（ρ = .10），比真时延上限 4.40 再好 0.95 [0.79, 1.07] dB，比基线最优好 1.51 dB；增益用导频 LS 结果几乎不变，值钱的是多普勒精度。ρ = .05 给全真信道也失败，原因是检测器联合增益重估失稳（探索性，20 键）（[读数](experiments/data_pilot_fer_20261121/STAGEA2_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A3（冻结，10.9 核时）**MIDDLE**：第 0 轮多普勒误差 σ ≤ 0.05 bin 时 A2 收益几乎全保住，σ = 0.1 保住 0.59 [0.33, 0.85]，σ = 0.2 崩掉；导频在 ρ = .10 的误差约 0.16。下一步按规则先算导频单独、导频加数据两种多普勒下界（[读数](experiments/data_pilot_fer_20261121/STAGEA3_READOUT.md)）。
- 11-21 data-pilot-fer 阶段 A4（冻结，1.7 核时）**SB-REACHABLE**：第 0 轮多普勒下界（功率加权平均绝对误差，4 dB）导频白噪声 .085/.068、最好纯导频 .074/.060、半盲 .040/.037、数据全知 .015（ρ .10/.15）；现有导频估计器比自身下界差 1.6–1.9 倍。半盲刚好够到 0.04，需要近乎有效的估计器（[读数](experiments/data_pilot_fer_20261121/STAGEA4_READOUT.md)）。
- 11-20 低导频"支撑已对仍失败"零成本读数：现象成立（ρ ≤ .20 干净区 4.4%，真信道下应 ≈ 0），导频每减半失败比 ×3.1 [1.3, 11]，Doppler 误差同格 AUC .82；ρ = .30、≥ 5.5 dB 时 0/105。候选解释"低导频 Doppler 精度不足"未检验，最便宜检验是真 Doppler 重放，待 Eric 定（[读数](experiments/lowpilot_support_right_20261120/READOUT.md)）。

## 待办与开放线索（唯一权威；2026-10-19 起）

> 当前所有待办与**开放线索**（有意思但未认证、值得追的发现）只在这里维护。已否定的线索写进
> [否定结果台账](.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)，
> 预测写进 [预测台账](research-assets/prediction-ledger.md)，只有会被引用的证据才写结果卡。journal 的 Next Steps、任务台账（如 ledger-20261019 的 B 部分）、各段里的"下一步"均为当时快照，不再更新。
> 完成或放弃一项时在此删除并在 journal 记一句。每条不超过 2 行，细节放进链接的文件；探索对话或评审的产出要在这里登记入口，否则后续会话找不到。

- 11-21 建 idea 漏斗（[看板](ideas/BOARD.md)）：首批 11 张，L1 淘汰 5、跨模型放行 1 张进 L3 等 Eric 看（I-20261121-01 导频比例与第 0 轮捕获门限），2 张待 L2、1 张停放。

**方向（贡献框架 D1，2026-11-09 登记，Eric 认可思路）**
- D1 流程：已验收卡拆要素 → 两模型独立提统一陈述 → 新颖性检查 → 审稿人攻击 → Eric 选定后预注册检验（[流程与工具选型](.trellis/tasks/09-22-tf-production-gap-audit/research/contribution-framing-process-20261109.md)）。第 4 步方向判断已做：Claude、Codex 首选 A（协方差感知的支撑获取），见[分歧表](.trellis/tasks/09-22-tf-production-gap-audit/research/direction-trans-contribution-divergence-20261109.md)。
- 当前骨架：[叙事骨架 v1.4.2（11-19 可辨识度准则版 + 措辞修正）](.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md)（Prop 1–3 证明 v2 已完成：Astra 撰写，Claude 与 agy 独立核查，修订后复核通过，剩 2(d) 单帧一处已声明的缺口；11-20 已编译 12 页，含秩注记；[证明与核查](.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/review-divergence-20261119.md)）；[4 篇 2026 预印本源码核对](.trellis/tasks/09-22-tf-production-gap-audit/research/recent-preprints-verification-20261118.md)。论文定位与科学验收待 Eric 定。
- 理论来源（11-10/11，写命题前必读）：[Fable 对话](.trellis/tasks/09-22-tf-production-gap-audit/research/fable-idea-dialogue.md)（拆分不变性、接纳定律及间隔更正）；[Astra 对话](.trellis/tasks/09-22-tf-production-gap-audit/research/astra-idea-dialogue.md)（式 3/8–10/12–14 决策边界定理链及末尾五个漏洞）；机器核验 [phantom_schur_audit_20261111.py](.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.py) / [.json](.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.json)。
- 11-11 deinlab 新帧块对照与方向 A 2×2（探索性，整数时延）：[配对结果与局限](.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)。
- 11-18 写稿前收口实证，主线新仿真至此停止（三张 draft 卡见下方第 6 项）。
- 开放线索（半盲重放完成，已于 11-19 接受）：幻影接纳定律的 M1/M2 冻结判据均为 SUPPORTED，覆盖 94.58%，A2 AUC .999385，窗口内外 A2 幻影率差 +21.98 pp。
  A2 与 A1c 的中位校准相对误差分别为 0.80% 和 90.03%。[res-20261118-06](research-assets/res-20261118-06.md)（已接受 11-19）。
- 11-19 过夜全自动推进（Eric 授权，Claude 代为冻结与启动；结果卡已于 11-19 收官时接受，见[收官验收包](.trellis/tasks/09-22-tf-production-gap-audit/research/wrapup-acceptance-20261119.md)）：[过程日志](.trellis/tasks/09-22-tf-production-gap-audit/research/autonomous-run-20261119.md)。
- 11-19 ρ 扫描（新帧 5400–5799，冻结后运行）：P1、P2、P3 均成立。`CODELAY` 相对 F0 的优势在 ρ = .30 比 .50 时更大，它自身在低导频比上也更好；各取最优点时领先 F0 约 1.1 dB。ρ = .25 不损失，ρ < .25 开始崩塌。U/.30 的穿越点已补齐。[res-20261119-06](research-assets/res-20261119-06.md)（已接受 11-19）。
- 11-18/19 野心探索：[综合稿](.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-synthesis-20261118.md)（§6 Gemini 第三轮核对，§7 现行优先级）。受控扫描任务 `.trellis/tasks/11-18-ratio-sweep`：
  v2（强制漏检）主跑完成：P3 SUPPORTED（`CODELAY` 不翻转），P2/P4 REFUTED（标量翻转点远低于闭式窗口）；事后审计显示弱径奖励被检测吸收，约降为模型的 1/4–1/2。[res-20261119-01](research-assets/res-20261119-01.md)（已接受 11-19，含更正）。

**研究（按优先级）**
1. SBL 排序反转（E-3/E-3b 中标量 Γ 反而更好）：领先候选是检测器增益接口（固定增益 vs 联合重估）与坐标增益更新不满足复制不变性，**仅探索性证据、未经前瞻确认**，论文只能写作候选机制。证据：[ledger-20261019 B1](.trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md)、[复盘](.trellis/tasks/09-22-tf-production-gap-audit/research/retrospective-20261019-sbl-reversal.md)、`experiments/detector_gain_lead_20261019/`、[SBL 检测器](experiments/sbl_joint_detector_20261019/SUMMARY.md)、[三模式](experiments/sbl_three_mode_20261020/SUMMARY.md)、冻结回放系列（[SUMMARY](experiments/sbl_freeze_replay_20261020/SUMMARY.md)、[RESTART_POINT](experiments/sbl_freeze_replay_20261020/RESTART_POINT_SUMMARY.md)、[TRAJECTORY](experiments/sbl_freeze_replay_20261020/TRAJECTORY_SUMMARY.md)、[REPRESENTATION](experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)、[GRAM_BLOCK](experiments/sbl_freeze_replay_20261020/GRAM_BLOCK_SUMMARY.md)、[GRAM_COHORT](experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)、[GAMMA_ABLATION](experiments/sbl_freeze_replay_20261020/GAMMA_ABLATION_SUMMARY.md)、[FRESH_COHORT](experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md)、[UNIFORM_GAMMA](experiments/sbl_freeze_replay_20261020/UNIFORM_GAMMA_SUMMARY.md)）、[Opus 评审核查](.trellis/tasks/10-20-sbl-freeze-replay/research/claude-opus55-review.md)、[定位稿](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning.md)及[核查](.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)、[operator-mapping](.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)。逐条历史见 STATE-history.md“研究”第 1 项。若该机制经前瞻确认，已验收的 res-20261017-03 解读第 2、4 条及 res-20261017-02 第 4 条的收窄须显式更正。11-18 旧键诊断（[草案 v2](.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md)，[RESULTS](experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md)）：`fixed`/`eG` 对精确复制严格不变、`point`/`joint` 不变 0/400；合并改算子 24%，按预定规则停止，第 4 句写作经验边界，机制未定。
9:## 记录系统（2026-07-26 起）
101:- SSH: `ssh deinlab`（别名，勿用硬编码 IP）
106:- SCP 上传文件或代码: `scp <file> deinlab:<directory>`
107:- `.trellis/`、`STATE.md`、`research-assets/` 的权威只在本地 vault，不同步 deinlab；jgw 仅接收经筛选、带源 commit 的只读阅读副本（入口与手动发布/学习回流见 `tools/web_access/README.md`）。
119:  `ssh deinlab "bash -lc 'conda activate AFDM && python xxx.py'"`
123:- `/tmp/`、`/var/tmp/`、`/dev/shm/` — 全局共享，系统定期清理，会污染其他用户视野
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-quLPR4wp' (errno=Operation not permitted)

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '826,1015p;1129,1282p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   826	def analyze_part1(
   827	    fail_by_arm: dict[str, tuple[tuple[int, ...], tuple[int, ...], np.ndarray]],
   828	    part1_rhos: tuple[int, ...],
   829	    include_hgint: bool,
   830	    crossing_fn,
   831	    *,
   832	    boot_draws: int = PART1_BOOT_DRAWS,
   833	    boot_seed: int = PART1_BOOT_SEED,
   834	) -> dict[str, Any]:
   835	    """Paired physical-frame bootstrap analysis for P1 (frames 41000-41399).
   836	
   837	    fail_by_arm[arm] = (rhos_tuple, snrs_tuple, fail_bool_array[n_frames, 2, n_rhos, n_snrs]).
   838	    """
   839	    n_frames = next(iter(fail_by_arm.values()))[2].shape[0]
   840	    rng = np.random.default_rng(boot_seed)
   841	    # Draw exact multinomial weights once, shared across ALL arms (stageA, stageA2, stageA3, new)
   842	    weights = np.empty((boot_draws + 1, n_frames), dtype=np.float64)
   843	    weights[0] = 1.0 / n_frames
   844	    for b in range(1, boot_draws + 1):
   845	        weights[b] = np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames).astype(np.float64) / n_frames
   846	
   847	    # Compute U/G mean crossing bounds [boot_draws+1, n_rhos] for every arm
   848	    arm_lo: dict[str, np.ndarray] = {}
   849	    arm_hi: dict[str, np.ndarray] = {}
   850	    arm_scen_pt: dict[str, dict[str, dict[str, Any]]] = {}
   851	    arm_mean_pt: dict[str, dict[str, Any]] = {}
   852	    arm_best_lo: dict[str, np.ndarray] = {}
   853	    arm_best_hi: dict[str, np.ndarray] = {}
   854	    arm_best_rho: dict[str, int] = {}
   855	
   856	    for arm, (rhos, snrs, fail) in fail_by_arm.items():
   857	        n_r = len(rhos)
   858	        lo_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   859	        hi_arr = np.empty((boot_draws + 1, n_r), dtype=np.float64)
   860	        # fer[draw, scen, rho, snr]
   861	        fer = np.tensordot(weights, fail.astype(np.float64), axes=(1, 0))
   862	        scen_pt = {'U': {}, 'G': {}}
   863	        for ri, rho in enumerate(rhos):
   864	            for bi in range(boot_draws + 1):
   865	                u_lo, u_hi = crossing_bounds_stageA2(fer[bi, 0, ri], snrs, crossing_fn)
   866	                g_lo, g_hi = crossing_bounds_stageA2(fer[bi, 1, ri], snrs, crossing_fn)
   867	                lo_arr[bi, ri] = 0.5 * (u_lo + g_lo)
   868	                hi_arr[bi, ri] = 0.5 * (u_hi + g_hi)
   869	                if bi == 0:
   870	                    scen_pt['U'][str(rho)] = _rep(u_lo) if u_lo == u_hi else [_rep(u_lo), _rep(u_hi)]
   871	                    scen_pt['G'][str(rho)] = _rep(g_lo) if g_lo == g_hi else [_rep(g_lo), _rep(g_hi)]
   872	        arm_lo[arm] = lo_arr
   873	        arm_hi[arm] = hi_arr
   874	        arm_scen_pt[arm] = scen_pt
   875	        arm_mean_pt[arm] = {
   876	            str(rho): (_rep(lo_arr[0, ri]) if lo_arr[0, ri] == hi_arr[0, ri] else [_rep(lo_arr[0, ri]), _rep(hi_arr[0, ri])])
   877	            for ri, rho in enumerate(rhos)
   878	        }
   879	        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; others over their own grid (or <=200 for delay)
   880	        if arm == 'delay':
   881	            sub_idx = [i for i, r in enumerate(rhos) if r <= 200]
   882	        else:
   883	            sub_idx = list(range(n_r))
   884	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   885	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   886	        best_pos = int(np.argmin(hi_arr[0, sub_idx]))
   887	        arm_best_rho[arm] = int(rhos[sub_idx[best_pos]])
   888	
   889	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   890	        # D = min_rho arm_a - min_rho arm_b (conservative bounds; collapses to exact diff when finite)
   891	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   892	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   893	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   894	        if cens_frac == 0.0:
   895	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   896	        else:
   897	            lo = an._nearest_rank(d_lo[1:], 0.025)
   898	            hi = an._nearest_rank(d_hi[1:], 0.975)
   899	        pt = _rep(d_lo[0]) if d_lo[0] == d_hi[0] else [_rep(d_lo[0]), _rep(d_hi[0])]
   900	        return dict(
   901	            point_db=pt,
   902	            ci95_db=[_rep(lo), _rep(hi)],
   903	            censored_draw_fraction=cens_frac,
   904	            arm_a_best_db=_rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [_rep(arm_best_lo[arm_a][0]), _rep(arm_best_hi[arm_a][0])],
   905	            arm_a_best_rho=arm_best_rho[arm_a],
   906	            arm_b_best_db=_rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [_rep(arm_best_lo[arm_b][0]), _rep(arm_best_hi[arm_b][0])],
   907	            arm_b_best_rho=arm_best_rho[arm_b],
   908	        )
   909	
   910	    primary_p1 = contrast('HG', 's100')
   911	    p1_lo = float(primary_p1['ci95_db'][0]) if isinstance(primary_p1['ci95_db'][0], float) else (-math.inf if primary_p1['ci95_db'][0] == '-inf' else math.inf)
   912	    p1_hi = float(primary_p1['ci95_db'][1]) if isinstance(primary_p1['ci95_db'][1], float) else (-math.inf if primary_p1['ci95_db'][1] == '-inf' else math.inf)
   913	    primary_p1['verdict'] = p1_verdict(p1_lo, p1_hi)
   914	
   915	    sec_contrasts = {}
   916	    for comp in ('s050', 'ldop', 'full', 'delay', 'base'):
   917	        if comp in fail_by_arm:
   918	            sec_contrasts[f'HG_minus_{comp}'] = contrast('HG', comp)
   919	    sec_contrasts['HG1_minus_s100'] = contrast('HG1', 's100')
   920	    if include_hgint and 'HGint' in fail_by_arm:
   921	        for comp in ('s100', 's050', 'ldop', 'full', 'HG'):
   922	            if comp in fail_by_arm:
   923	                sec_contrasts[f'HGint_minus_{comp}'] = contrast('HGint', comp)
   924	
   925	    return dict(
   926	        boot_draws=boot_draws,
   927	        boot_seed=boot_seed,
   928	        part1_rhos=list(part1_rhos),
   929	        include_hgint=include_hgint,
   930	        primary_P1=primary_p1,
   931	        secondary_contrasts=sec_contrasts,
   932	        mean_crossing=arm_mean_pt,
   933	        crossings_by_scenario=arm_scen_pt,
   934	        best_rho=arm_best_rho,
   935	    )
   936	
   937	
   938	def analyze_part2(
   939	    full_rows: dict[tuple[str, int, int, int], dict[str, Any]],
   940	    arms: tuple[str, ...],
   941	    *,
   942	    boot_draws: int = an.BOOT_DRAWS,
   943	    boot_seed: int = an.BOOT_SEED,
   944	) -> dict[str, Any]:
   945	    """Reuse hs_analysis crossing & 36-pair simultaneous projection for P2 (frames 5400-5799)."""
   946	    rhos = ar.RHOS
   947	    snrs = ar.SNRS
   948	    frames = ar.MAIN_FRAMES
   949	    errors_by_key = {k: {a: int(r['arms'][a]['errors']) for a in arms} for k, r in full_rows.items()}
   950	    crossings, cells = an.compute_crossings(
   951	        errors_by_key, arms, rhos, snrs, frames, boot_draws=boot_draws, boot_seed=boot_seed,
   952	    )
   953	    pooled = an.scene_means(crossings, rhos, arms)
   954	
   955	    def eval_p2(arm_a: str, arm_b: str) -> dict[str, Any]:
   956	        c98 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.PRIMARY_ALPHA)
   957	        c95 = an.projected_best_diff(pooled, arm_a, arm_b, rhos, an.FAMILY_ALPHA)
   958	        _, _, lo98, hi98 = c98['_raw']
   959	        _, _, lo95, hi95 = c95['_raw']
   960	        return dict(
   961	            point_db=c98['point_db'],
   962	            ci9833_projected_db=c98['ci_projected_db'],
   963	            ci9833_per_draw_db=c98['ci_per_draw_db'],
   964	            ci95_projected_db=c95['ci_projected_db'],
   965	            ci95_per_draw_db=c95['ci_per_draw_db'],
   966	            censored_draw_fraction=c98['censored_draw_fraction'],
   967	            verdict=p2_verdict(lo98, hi98),
   968	            verdict_at_95_descriptive=p2_verdict(lo95, hi95),
   969	        )
   970	
   971	    p2_E = eval_p2('CD2', 'HG')
   972	    p2_E8 = eval_p2('CD2e8', 'HG')
   973	
   974	    # Per-scenario P2
   975	    by_scen = {}
   976	    for s in ar.SCENARIOS:
   977	        s_curves = {(r, a): crossings[s, r, a] for r in rhos for a in arms}
   978	        by_scen[s] = {}
   979	        for label, arm_a in (('E_CD2_minus_HG', 'CD2'), ('E8_CD2e8_minus_HG', 'CD2e8')):
   980	            c98 = an.projected_best_diff(s_curves, arm_a, 'HG', rhos, an.PRIMARY_ALPHA)
   981	            _, _, lo98, hi98 = c98['_raw']
   982	            by_scen[s][label] = dict(
   983	                point_db=c98['point_db'],
   984	                ci9833_projected_db=c98['ci_projected_db'],
   985	                verdict=p2_verdict(lo98, hi98),
   986	            )
   987	
   988	    # Secondary contrasts (95% projected CI)
   989	    sec = {}
   990	    for name, a1, a2 in (
   991	        ('CD2_minus_CD', 'CD2', 'CD'),
   992	        ('CD2e8_minus_CD', 'CD2e8', 'CD'),
   993	        ('CD2e8_minus_CD2', 'CD2e8', 'CD2'),
   994	        ('CD2_minus_HGint', 'CD2', 'HGint'),
   995	        ('CD2e8_minus_HGint', 'CD2e8', 'HGint'),
   996	    ):
   997	        if a1 in arms and a2 in arms:
   998	            c = an.projected_best_diff(pooled, a1, a2, rhos, an.FAMILY_ALPHA)
   999	            sec[name] = {k: v for k, v in c.items() if k != '_raw'}
  1000	
  1001	    # Scene-averaged crossing table
  1002	    pooled_table = {}
  1003	    best_rho = {}
  1004	    for a in arms:
  1005	        pooled_table[a] = {}
  1006	        best_val = math.inf
  1007	        best_r = rhos[0]
  1008	        for r in rhos:
  1009	            b = pooled[r, a]
  1010	            lo95, hi95 = an._interval(b, 0.05)
  1011	            pt_lo, pt_hi = float(b.lower[0]), float(b.upper[0])
  1012	            pooled_table[a][str(r)] = dict(
  1013	                point_db=[_rep(pt_lo), _rep(pt_hi)],
  1014	                ci95_db=[_rep(lo95), _rep(hi95)],
  1015	            )
  1129	def _do_read(out_dir: Path, gate: dict[str, Any], freeze_commit: str, runtime_info: dict[str, Any], raw_md5: dict[str, str]):
  1130	    import stageA  # noqa: E402
  1131	    import stageA2  # noqa: E402
  1132	    import stageA3  # noqa: E402
  1133	
  1134	    sel = gate['selected']
  1135	    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
  1136	    include_hgint = bool(sel['include_hgint'])
  1137	    raw_dir = out_dir / 'raw'
  1138	
  1139	    # Verify all manifests and our own raw shard MD5s
  1140	    for name in ARCHIVE_MANIFESTS:
  1141	        verify_manifest(name)
  1142	    for fname, expected in raw_md5.items():
  1143	        actual = ar.md5_file(raw_dir / fname)
  1144	        if actual != expected:
  1145	            raise RuntimeError(f'Raw shard MD5 mismatch {fname}: {actual} != {expected}')
  1146	
  1147	    # --- Load Part 1 arrays (archived stageA/A2/A3 + new Part 1) ---
  1148	    fa, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)
  1149	    fa2, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA2', stageA2.ARMS, stageA2.RHOS, stageA2.SNRS)
  1150	    fa3, _ = stageA2.load(DATA_PILOT_DIR / 'out' / 'stageA3', stageA3.ARMS, stageA3.RHOS, stageA3.SNRS)
  1151	
  1152	    stageA_base = load_stageA_base(part1_rhos)
  1153	    new_p1_arms = ('HG', 'HG1') + (('HGint',) if include_hgint else ())
  1154	    fi = {f: i for i, f in enumerate(PART1_FRAMES)}
  1155	    p1_fail = {a: np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool) for a in new_p1_arms}
  1156	    p1_seen = np.zeros((len(PART1_FRAMES), 2, len(part1_rhos), len(PART1_SNRS)), dtype=bool)
  1157	
  1158	    # Fill untriggered keys from stageA_base
  1159	    for (s, rho, snr, f), b in stageA_base.items():
  1160	        if b['syndrome'] == 0:
  1161	            ix = (fi[f], ar.SCENARIOS.index(s), part1_rhos.index(rho), PART1_SNRS.index(snr))
  1162	            err_flag = b['f0_errors'] > 0
  1163	            for a in new_p1_arms:
  1164	                p1_fail[a][ix] = err_flag
  1165	            p1_seen[ix] = True
  1166	
  1167	    # Fill triggered keys from new Part-1 shards
  1168	    p1_trig_seen = 0
  1169	    for shard_idx in range(N_SHARDS):
  1170	        sp = raw_dir / f'part1_shard{shard_idx:03d}.jsonl.gz'
  1171	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
  1172	            for line in fh:
  1173	                r = json.loads(line)
  1174	                ix = (fi[int(r['frame'])], ar.SCENARIOS.index(r['scenario']), part1_rhos.index(int(r['rho'])), PART1_SNRS.index(int(r['snr'])))
  1175	                if p1_seen[ix]:
  1176	                    raise RuntimeError(f'Duplicate Part1 key {r}')
  1177	                for a in new_p1_arms:
  1178	                    p1_fail[a][ix] = int(r['arms'][a]['errors']) > 0
  1179	                p1_seen[ix] = True
  1180	                p1_trig_seen += 1
  1181	    if not p1_seen.all():
  1182	        raise RuntimeError(f'Incomplete Part1 grid: missing {int((~p1_seen).sum())} keys')
  1183	
  1184	    fail_by_arm = {
  1185	        'base': (stageA.RHOS, stageA.SNRS, fa[:, 0]),
  1186	        'delay': (stageA.RHOS, stageA.SNRS, fa[:, 1]),
  1187	        'full': (stageA2.RHOS, stageA2.SNRS, fa2[:, 0]),
  1188	        'ldop': (stageA2.RHOS, stageA2.SNRS, fa2[:, 1]),
  1189	    }
  1190	    for i, a in enumerate(stageA3.ARMS):
  1191	        fail_by_arm[a] = (stageA3.RHOS, stageA3.SNRS, fa3[:, i])
  1192	    for a in new_p1_arms:
  1193	        fail_by_arm[a] = (part1_rhos, PART1_SNRS, p1_fail[a])
  1194	
  1195	    print(f'Analyzing Part 1 ({int(p1_seen.sum())} keys, {p1_trig_seen} triggered)...', flush=True)
  1196	    part1_out = analyze_part1(fail_by_arm, part1_rhos, include_hgint, stageA2.crossing)
  1197	
  1198	    # --- Load Part 2 rows (archived rho_sweep + huang_steelman + new CD2/CD2e8) ---
  1199	    rho_arch, _ = ar.load_archived_rho_sweep()
  1200	    huang_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1201	    for p in sorted((HUANG_DIR / 'out' / 'raw').glob('rows_shard*.jsonl')):
  1202	        with p.open('r', encoding='utf-8') as fh:
  1203	            for line in fh:
  1204	                r = json.loads(line)
  1205	                huang_trig[ar.row_key(r)] = r
  1206	
  1207	    new_p2_trig: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1208	    for shard_idx in range(N_SHARDS):
  1209	        sp = raw_dir / f'part2_shard{shard_idx:03d}.jsonl.gz'
  1210	        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
  1211	            for line in fh:
  1212	                r = json.loads(line)
  1213	                k = ar.row_key(r)
  1214	                if k in new_p2_trig:
  1215	                    raise RuntimeError(f'Duplicate Part2 key {k}')
  1216	                new_p2_trig[k] = r
  1217	    if len(new_p2_trig) != ar.EXPECTED_TOTAL_TRIGGERS or len(huang_trig) != ar.EXPECTED_TOTAL_TRIGGERS:
  1218	        raise RuntimeError(f'Part2 trigger count mismatch: new={len(new_p2_trig)}, huang={len(huang_trig)}')
  1219	
  1220	    p2_arms = ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z')
  1221	    full_p2: dict[tuple[str, int, int, int], dict[str, Any]] = {}
  1222	    for k, arch in rho_arch.items():
  1223	        if arch['triggered']:
  1224	            hr = huang_trig[k]['arms']
  1225	            nr = new_p2_trig[k]['arms']
  1226	            full_p2[k] = dict(
  1227	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
  1228	                triggered=True,
  1229	                arms=dict(
  1230	                    F0=hr['F0'], CD=hr['CD'], HG=hr['HG'], HG1=hr['HG1'], HGint=hr['HGint'], Z=hr['Z'],
  1231	                    CD2=nr['CD2'], CD2e8=nr['CD2e8'],
  1232	                ),
  1233	            )
  1234	        else:
  1235	            f0 = dict(errors=int(arch['arms']['F0']['errors']), decoded_sha=arch['arms']['F0']['decoded_sha'])
  1236	            full_p2[k] = dict(
  1237	                scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3],
  1238	                triggered=False,
  1239	                arms={a: f0 for a in p2_arms},
  1240	            )
  1241	
  1242	    print(f'Analyzing Part 2 ({len(full_p2)} keys, {len(new_p2_trig)} triggered)...', flush=True)
  1243	    part2_out = analyze_part2(full_p2, p2_arms)
  1244	
  1245	    results = dict(
  1246	        _argv=sys.argv,
  1247	        _config=dict(
  1248	            freeze_commit=freeze_commit,
  1249	            python_executable=sys.executable,
  1250	            own_md5=own_md5(),
  1251	            gate_md5=ar.md5_file(out_dir / 'gate.json'),
  1252	            part1_rhos=list(part1_rhos),
  1253	            include_hgint=include_hgint,
  1254	            part1_frames=[PART1_FRAMES[0], PART1_FRAMES[-1]],
  1255	            part1_triggered_keys=p1_trig_seen,
  1256	            part2_frames=[ar.MAIN_FRAMES[0], ar.MAIN_FRAMES[-1]],
  1257	            part2_triggered_keys=len(new_p2_trig),
  1258	            archive_manifest_sha256={k: v[1] for k, v in ARCHIVE_MANIFESTS.items()},
  1259	            raw_output_dir=str(raw_dir),
  1260	            raw_rows_md5=raw_md5,
  1261	        ),
  1262	        gates=dict(
  1263	            all_passed=gate['all_passed'],
  1264	            selected=gate['selected'],
  1265	            G1_keys=gate['G1']['keys_checked'],
  1266	            G2_keys=gate['G2']['keys_checked'],
  1267	            G3_keys=gate['G3']['keys_checked'],
  1268	            G4_projected_hours=sel['projected_hours_with_margin'],
  1269	        ),
  1270	        runtime=runtime_info,
  1271	        part1=part1_out,
  1272	        part2=part2_out,
  1273	    )
  1274	    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
  1275	    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
  1276	    print(
  1277	        f'DONE P1={part1_out["primary_P1"]["verdict"]} '
  1278	        f'P2_CD2={part2_out["E_CD2_minus_HG"]["verdict"]} '
  1279	        f'P2_CD2e8={part2_out["E8_CD2e8_minus_HG"]["verdict"]}',
  1280	        flush=True,
  1281	    )
  1282	

exec
/bin/zsh -lc "rg -n '"'^def |ALPHA|N_BOOT|BOOT|SCENARIOS|RHOS|SNRS|ARM_SPECS|numerical_fallback'"' experiments/huang_steelman_20261124/{hs_analysis,hs_arms}.py experiments/data_pilot_fer_20261121/{stageA,stageA2}.py; rg --files experiments/{data_pilot_fer_20261121,huang_steelman_20261124,rho_sweep_20261119} | rg 'REMOTE_ROWS_MD5|rows_shard' | awk 'NR<=14'; sed -n '95,135p' CLAUDE.md; cat /Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md | sed -n '1,125p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/data_pilot_fer_20261121/stageA.py:23:SCENARIOS = ('U', 'G')
experiments/data_pilot_fer_20261121/stageA.py:24:RHOS = (50, 100, 150, 200, 250, 300)
experiments/data_pilot_fer_20261121/stageA.py:25:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
experiments/data_pilot_fer_20261121/stageA.py:30:BOOT, SEED, GATE_DB = 2000, 20261121, 0.3
experiments/data_pilot_fer_20261121/stageA.py:34:def setup():
experiments/data_pilot_fer_20261121/stageA.py:48:def f0(C, obs, inject=None):
experiments/data_pilot_fer_20261121/stageA.py:66:def support_stats(delays, dopplers, truth, sigma2):
experiments/data_pilot_fer_20261121/stageA.py:80:def one_arm(C, obs, truth, inject):
experiments/data_pilot_fer_20261121/stageA.py:98:def genie_inject(C, obs, truth):
experiments/data_pilot_fer_20261121/stageA.py:104:def run_key(C, base, s_, rho, snr, frame):
experiments/data_pilot_fer_20261121/stageA.py:111:def shard_job(job):
experiments/data_pilot_fer_20261121/stageA.py:118:            for s_ in SCENARIOS:
experiments/data_pilot_fer_20261121/stageA.py:119:                for rho in RHOS:
experiments/data_pilot_fer_20261121/stageA.py:121:                    for snr in SNRS:
experiments/data_pilot_fer_20261121/stageA.py:127:def gate(out):
experiments/data_pilot_fer_20261121/stageA.py:158:    res = dict(cpu_seconds_per_key=per_key, projected_core_hours=per_key * len(FRAMES) * 2 * len(RHOS) * len(SNRS) / 3600 * 1.3,
experiments/data_pilot_fer_20261121/stageA.py:165:def run(out):
experiments/data_pilot_fer_20261121/stageA.py:170:        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS), indent=1))
experiments/data_pilot_fer_20261121/stageA.py:184:def crossing(fer):
experiments/data_pilot_fer_20261121/stageA.py:186:    x = np.array(SNRS) / 100; lf = np.log10(np.maximum(fer, 1e-4))
experiments/data_pilot_fer_20261121/stageA.py:196:def read(out):
experiments/data_pilot_fer_20261121/stageA.py:202:    fail = np.zeros((len(FRAMES), len(ARMS), len(SCENARIOS), len(RHOS), len(SNRS)), bool)
experiments/data_pilot_fer_20261121/stageA.py:209:                ix = (fi[r['frame']], slice(None), SCENARIOS.index(r['scenario']), RHOS.index(r['rho']), SNRS.index(r['snr']))
experiments/data_pilot_fer_20261121/stageA.py:227:        b = np.min(m[0]); a = np.min(m[1][[RHOS.index(r) for r in RHOS if r <= 200]])
experiments/data_pilot_fer_20261121/stageA.py:232:    for _ in range(BOOT):
experiments/data_pilot_fer_20261121/stageA.py:242:    res = dict(crossings={arm: {s_: {str(r): float(cr[ai, si, ri]) for ri, r in enumerate(RHOS)}
experiments/data_pilot_fer_20261121/stageA.py:243:                                for si, s_ in enumerate(SCENARIOS)} for ai, arm in enumerate(ARMS)},
experiments/data_pilot_fer_20261121/stageA.py:244:               mean_crossing={arm: {str(r): float(m[ai, ri]) for ri, r in enumerate(RHOS)} for ai, arm in enumerate(ARMS)},
experiments/huang_steelman_20261124/hs_analysis.py:25:SCENARIOS = ('U', 'G')
experiments/huang_steelman_20261124/hs_analysis.py:26:ALL_RHOS = (150, 200, 250, 300, 400, 500)
experiments/huang_steelman_20261124/hs_analysis.py:27:ALL_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
experiments/huang_steelman_20261124/hs_analysis.py:28:BOOT_DRAWS = 50_000
experiments/huang_steelman_20261124/hs_analysis.py:29:BOOT_SEED = 20261124
experiments/huang_steelman_20261124/hs_analysis.py:30:FAMILY_ALPHA = 0.05
experiments/huang_steelman_20261124/hs_analysis.py:31:PRIMARY_ALPHA = FAMILY_ALPHA / 3.0
experiments/huang_steelman_20261124/hs_analysis.py:41:def _difference(first: Bounds, second: Bounds) -> Bounds:
experiments/huang_steelman_20261124/hs_analysis.py:45:def _mean(bounds_list: list[Bounds]) -> Bounds:
experiments/huang_steelman_20261124/hs_analysis.py:52:def _minimum(bounds_list: list[Bounds]) -> Bounds:
experiments/huang_steelman_20261124/hs_analysis.py:59:def _nearest_rank(draws: np.ndarray, probability: float) -> float:
experiments/huang_steelman_20261124/hs_analysis.py:65:def _interval(bounds: Bounds, alpha: float) -> tuple[float, float]:
experiments/huang_steelman_20261124/hs_analysis.py:72:def _represent(value: float) -> Any:
experiments/huang_steelman_20261124/hs_analysis.py:82:def _crossing(fer: np.ndarray, frame_count: int, snrs_centi: tuple[int, ...]) -> Bounds:
experiments/huang_steelman_20261124/hs_analysis.py:90:def compute_crossings(
experiments/huang_steelman_20261124/hs_analysis.py:97:    boot_draws: int = BOOT_DRAWS,
experiments/huang_steelman_20261124/hs_analysis.py:98:    boot_seed: int = BOOT_SEED,
experiments/huang_steelman_20261124/hs_analysis.py:106:        for s in SCENARIOS for rho in rhos for snr in snrs for f in frames
experiments/huang_steelman_20261124/hs_analysis.py:121:    for s in SCENARIOS:
experiments/huang_steelman_20261124/hs_analysis.py:150:def scene_means(
experiments/huang_steelman_20261124/hs_analysis.py:156:        (rho, arm): _mean([crossings[s, rho, arm] for s in SCENARIOS])
experiments/huang_steelman_20261124/hs_analysis.py:161:def projected_best_diff(
experiments/huang_steelman_20261124/hs_analysis.py:213:def single_rho_diff(
experiments/huang_steelman_20261124/hs_analysis.py:235:def verdict_q2(point_lo: float, point_hi: float, ci_lo: float, ci_hi: float) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_analysis.py:257:def verdict_q3(ci_lo: float, ci_hi: float) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_analysis.py:278:def _strip_raw(d: dict[str, Any]) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_analysis.py:282:def _unpaired_optimum_sets(
experiments/huang_steelman_20261124/hs_analysis.py:314:def paired_rescue_summary(
experiments/huang_steelman_20261124/hs_analysis.py:323:    for s in SCENARIOS:
experiments/huang_steelman_20261124/hs_analysis.py:370:def pass2_and_support_summary(triggered_rows: list[dict[str, Any]]) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_analysis.py:460:def analyze(
experiments/huang_steelman_20261124/hs_analysis.py:467:    boot_draws: int = BOOT_DRAWS,
experiments/huang_steelman_20261124/hs_analysis.py:468:    boot_seed: int = BOOT_SEED,
experiments/huang_steelman_20261124/hs_analysis.py:481:    q1 = single_rho_diff(pooled, 'HG', 'CD', 300, PRIMARY_ALPHA)
experiments/huang_steelman_20261124/hs_analysis.py:482:    q2 = projected_best_diff(pooled, 'HG', 'CD', rhos, PRIMARY_ALPHA)
experiments/huang_steelman_20261124/hs_analysis.py:483:    q3 = projected_best_diff(pooled, 'Z', 'CD', rhos, PRIMARY_ALPHA)
experiments/huang_steelman_20261124/hs_analysis.py:496:    for s in SCENARIOS:
experiments/huang_steelman_20261124/hs_analysis.py:498:        sq1 = single_rho_diff(sc, 'HG', 'CD', 300, PRIMARY_ALPHA)
experiments/huang_steelman_20261124/hs_analysis.py:499:        sq2 = projected_best_diff(sc, 'HG', 'CD', rhos, PRIMARY_ALPHA)
experiments/huang_steelman_20261124/hs_analysis.py:500:        sq3 = projected_best_diff(sc, 'Z', 'CD', rhos, PRIMARY_ALPHA)
experiments/huang_steelman_20261124/hs_analysis.py:547:        family_alpha=FAMILY_ALPHA,
experiments/huang_steelman_20261124/hs_analysis.py:548:        primary_alpha=PRIMARY_ALPHA,
experiments/huang_steelman_20261124/hs_analysis.py:557:        optimum_sets=_unpaired_optimum_sets(pooled, arms, rhos, PRIMARY_ALPHA),
experiments/huang_steelman_20261124/hs_analysis.py:564:def _fmt_pt(pt: list[Any]) -> str:
experiments/huang_steelman_20261124/hs_analysis.py:572:def _fmt_ci(ci: list[Any]) -> str:
experiments/huang_steelman_20261124/hs_analysis.py:578:def render_results_md(summary: dict[str, Any]) -> str:
experiments/huang_steelman_20261124/hs_analysis.py:605:    for s in SCENARIOS:
experiments/huang_steelman_20261124/hs_arms.py:26:SCENARIOS = ('U', 'G')
experiments/huang_steelman_20261124/hs_arms.py:27:RHOS = (150, 200, 250, 300, 400, 500)
experiments/huang_steelman_20261124/hs_arms.py:28:SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
experiments/huang_steelman_20261124/hs_arms.py:29:LOW_SNRS = (300, 400)
experiments/huang_steelman_20261124/hs_arms.py:66:def frozen_p1_md5(ctx) -> dict[str, str]:
experiments/huang_steelman_20261124/hs_arms.py:71:def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
experiments/huang_steelman_20261124/hs_arms.py:107:def md5_file(path: Path) -> str:
experiments/huang_steelman_20261124/hs_arms.py:115:def sha256_file(path: Path) -> str:
experiments/huang_steelman_20261124/hs_arms.py:123:def own_md5() -> dict[str, str]:
experiments/huang_steelman_20261124/hs_arms.py:133:def atomic_write_text(path: Path, text: str):
experiments/huang_steelman_20261124/hs_arms.py:143:def check_thread_env() -> dict[str, str]:
experiments/huang_steelman_20261124/hs_arms.py:152:def verify_frozen_extra_md5() -> dict[str, str]:
experiments/huang_steelman_20261124/hs_arms.py:162:def _load_module(name: str, path: Path):
experiments/huang_steelman_20261124/hs_arms.py:169:def load_context():
experiments/huang_steelman_20261124/hs_arms.py:199:def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
experiments/huang_steelman_20261124/hs_arms.py:206:def coarse_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
experiments/huang_steelman_20261124/hs_arms.py:213:def _require_finite(arr, label: str):
experiments/huang_steelman_20261124/hs_arms.py:218:def omp_reacquire(
experiments/huang_steelman_20261124/hs_arms.py:255:def match_paths_1to1(fit_delays, fit_dopplers, truth) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_arms.py:307:def match_omp_nominated(omp_delays, omp_dopplers, truth) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_arms.py:326:def _decision_record(res) -> list[list[Any]]:
experiments/huang_steelman_20261124/hs_arms.py:336:def run_hg_arm(
experiments/huang_steelman_20261124/hs_arms.py:445:def _run_exchange_arm(
experiments/huang_steelman_20261124/hs_arms.py:467:    if bool(res.diagnostics.get('numerical_fallback')):
experiments/huang_steelman_20261124/hs_arms.py:468:        raise FloatingPointError(f'Geometry numerical_fallback triggered in {arm_name}')
experiments/huang_steelman_20261124/hs_arms.py:490:        numerical_fallback=False,
experiments/huang_steelman_20261124/hs_arms.py:497:def run_z_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_arms.py:501:def run_cd_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
experiments/huang_steelman_20261124/hs_arms.py:505:def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
experiments/huang_steelman_20261124/hs_arms.py:509:def load_archived_rho_sweep(
experiments/huang_steelman_20261124/hs_arms.py:529:    stratum_counts: dict[tuple[int, str], int] = {(r, b): 0 for r in RHOS for b in ('low', 'mid')}
experiments/huang_steelman_20261124/hs_arms.py:552:                    band = 'low' if k[2] in LOW_SNRS else 'mid'
experiments/huang_steelman_20261124/hs_arms.py:558:        for s in SCENARIOS for rho in RHOS for snr in SNRS for frame in MAIN_FRAMES
experiments/data_pilot_fer_20261121/stageA2.py:20:from stageA import FRAMES, SCENARIOS, setup, support_stats
experiments/data_pilot_fer_20261121/stageA2.py:22:RHOS = (50, 100, 150, 200)
experiments/data_pilot_fer_20261121/stageA2.py:23:SNRS = (200, 250) + stageA.SNRS
experiments/data_pilot_fer_20261121/stageA2.py:26:BOOT, SEED, KILL_DB = 2000, 20261121, 0.15
experiments/data_pilot_fer_20261121/stageA2.py:29:def f0_true(C, obs, truth, gains):
experiments/data_pilot_fer_20261121/stageA2.py:51:def one_arm(C, obs, truth, gains):
experiments/data_pilot_fer_20261121/stageA2.py:69:def run_key(C, base, s_, rho, snr, frame):
experiments/data_pilot_fer_20261121/stageA2.py:75:def shard_job(job):
experiments/data_pilot_fer_20261121/stageA2.py:80:            for s_ in SCENARIOS:
experiments/data_pilot_fer_20261121/stageA2.py:81:                for rho in RHOS:
experiments/data_pilot_fer_20261121/stageA2.py:83:                    for snr in SNRS:
experiments/data_pilot_fer_20261121/stageA2.py:89:def gate(out):
experiments/data_pilot_fer_20261121/stageA2.py:136:                projected_core_hours=per_key * len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(SNRS) / 3600 * 1.3,
experiments/data_pilot_fer_20261121/stageA2.py:142:def run(out):
experiments/data_pilot_fer_20261121/stageA2.py:147:        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS), indent=1))
experiments/data_pilot_fer_20261121/stageA2.py:158:def crossing(fer, snrs):
experiments/data_pilot_fer_20261121/stageA2.py:170:def load(out, arms, rhos, snrs):
experiments/data_pilot_fer_20261121/stageA2.py:172:    fail = np.zeros((len(FRAMES), len(arms), len(SCENARIOS), len(rhos), len(snrs)), bool); seen = np.zeros_like(fail)
experiments/data_pilot_fer_20261121/stageA2.py:181:                    j = (fi[r['frame']], a, SCENARIOS.index(r['scenario']), rhos.index(r['rho']), snrs.index(r['snr']))
experiments/data_pilot_fer_20261121/stageA2.py:192:def read(out):
experiments/data_pilot_fer_20261121/stageA2.py:196:    fa, _ = load(out.parent / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)       # base, delay
experiments/data_pilot_fer_20261121/stageA2.py:197:    fb, diag = load(out, ARMS, RHOS, SNRS)                                            # full, ldop
experiments/data_pilot_fer_20261121/stageA2.py:198:    lo_idx = [stageA.RHOS.index(r) for r in RHOS]
experiments/data_pilot_fer_20261121/stageA2.py:204:        ca, cb = m(fa, stageA.SNRS), m(fb, SNRS)
experiments/data_pilot_fer_20261121/stageA2.py:213:    for _ in range(BOOT):
experiments/data_pilot_fer_20261121/stageA2.py:228:               mean_crossing=dict({arm: {str(r): float(ma[i, j]) for j, r in enumerate(stageA.RHOS)} for i, arm in enumerate(stageA.ARMS)},
experiments/data_pilot_fer_20261121/stageA2.py:229:                                  **{arm: {str(r): float(mb[i, j]) for j, r in enumerate(RHOS)} for i, arm in enumerate(ARMS)}),
experiments/data_pilot_fer_20261121/stageA2.py:230:               crossings={arm: {s_: {str(r): float(cb[i, k, j]) for j, r in enumerate(RHOS)} for k, s_ in enumerate(SCENARIOS)}
experiments/data_pilot_fer_20261121/out/stageA4/REMOTE_ROWS_MD5.txt
experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
experiments/data_pilot_fer_20261121/out/stageA3/REMOTE_ROWS_MD5.txt
experiments/data_pilot_fer_20261121/out/stageA2/REMOTE_ROWS_MD5.txt
experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt
experiments/data_pilot_fer_20261121/out/stageA/REMOTE_ROWS_MD5.txt
- `Ericjiang2/afdm-sp`（私有）= 本项目供网页 GPT 阅读的只读镜像，非备份、非协作仓库；不在其中直接改动。
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

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/data_pilot_fer_20261121/stageA2.py | sed -n '142,193p'; nl -ba experiments/data_pilot_fer_20261121/stageA.py | sed -n '30,66p;80,110p'; nl -ba experiments/huang_steelman_20261124/hs_analysis.py | sed -n '155,213p'; nl -ba experiments/huang_steelman_20261124/hs_arms.py | sed -n '26,72p;140,198p;336,444p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
   142	def run(out):
   143	    out = Path(out); out.mkdir(parents=True, exist_ok=False)
   144	    frames = list(FRAMES)
   145	    jobs = [(i, frames[k:k + FRAMES_PER_SHARD], str(out)) for i, k in enumerate(range(0, len(frames), FRAMES_PER_SHARD))]
   146	    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
   147	        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS), indent=1))
   148	    t0 = time.time(); done = 0
   149	    with get_context('spawn').Pool(WORKERS) as pool:
   150	        for idx, n in pool.imap_unordered(shard_job, jobs):
   151	            done += n > 0
   152	    ch = resource.getrusage(resource.RUSAGE_CHILDREN); hours = (ch.ru_utime + ch.ru_stime) / 3600
   153	    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
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
   109	
   110	
   155	    return {
   156	        (rho, arm): _mean([crossings[s, rho, arm] for s in SCENARIOS])
   157	        for rho in rhos for arm in arms
   158	    }
   159	
   160	
   161	def projected_best_diff(
   162	    curves: dict[tuple[int, str], Bounds],
   163	    arm_a: str,
   164	    arm_b: str,
   165	    rhos: tuple[int, ...],
   166	    alpha: float,
   167	) -> dict[str, Any]:
   168	    """36-pair simultaneous confidence projection for min_a c_A(a) - min_b c_B(b).
   169	
   170	    Uses the exact identity:
   171	      min_a c_A(a) - min_b c_B(b) = min_a max_b (c_A(a) - c_B(b)) = max_b min_a (c_A(a) - c_B(b)).
   172	    For all |R|^2 pairs (a, b), constructs simultaneous (1 - alpha) intervals [L(a,b), U(a,b)]
   173	    with Bonferroni alpha_pair = alpha / |R|^2, then projects:
   174	      L_proj = min_a max_b L(a,b),  U_proj = max_b min_a U(a,b).
   175	    Also reports the paired per-draw bootstrap interval as a secondary precision readout.
   176	    """
   177	    m = len(rhos)
   178	    alpha_pair = alpha / (m * m)
   179	    L_mat = np.empty((m, m), dtype=float)
   180	    U_mat = np.empty((m, m), dtype=float)
   181	    for i, ra in enumerate(rhos):
   182	        for j, rb in enumerate(rhos):
   183	            diff_ab = _difference(curves[ra, arm_a], curves[rb, arm_b])
   184	            lo, hi = _interval(diff_ab, alpha_pair)
   185	            L_mat[i, j] = lo
   186	            U_mat[i, j] = hi
   187	    L_proj = float(np.min(np.max(L_mat, axis=1)))
   188	    U_proj = float(np.max(np.min(U_mat, axis=0)))
   189	    if L_proj > U_proj + 1e-12:
   190	        raise AssertionError(f'Projected lower bound {L_proj} exceeds upper bound {U_proj}')
   191	
   192	    min_a = _minimum([curves[r, arm_a] for r in rhos])
   193	    min_b = _minimum([curves[r, arm_b] for r in rhos])
   194	    per_draw = _difference(min_a, min_b)
   195	    pd_lo, pd_hi = _interval(per_draw, alpha)
   196	    censored_frac = float(np.mean(~(np.isfinite(per_draw.lower[1:]) & np.isfinite(per_draw.upper[1:]))))
   197	
   198	    pt_lo = float(per_draw.lower[0])
   199	    pt_hi = float(per_draw.upper[0])
   200	    return dict(
   201	        point_db=[_represent(pt_lo), _represent(pt_hi)],
   202	        ci_projected_db=[_represent(L_proj), _represent(U_proj)],
   203	        ci_per_draw_db=[_represent(pd_lo), _represent(pd_hi)],
   204	        half_width_projected_db=_represent((U_proj - L_proj) / 2.0),
   205	        half_width_per_draw_db=_represent((pd_hi - pd_lo) / 2.0),
   206	        censored_draw_fraction=censored_frac,
   207	        alpha=float(alpha),
   208	        alpha_pair=float(alpha_pair),
   209	        _raw=(pt_lo, pt_hi, L_proj, U_proj),
   210	    )
   211	
   212	
   213	def single_rho_diff(
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
    66	def frozen_p1_md5(ctx) -> dict[str, str]:
    67	    """Return ctx.source_md5 restricted to external/frozen modules (independent of which own scripts are imported)."""
    68	    return {k: v for k, v in ctx.source_md5.items() if k not in OWN_MODULE_NAMES}
    69	
    70	
    71	def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
    72	    """When running inside a git checkout, verify freeze_commit exists and its own blobs match live_own_md5."""
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

exec
/bin/zsh -lc 'for f in experiments/data_pilot_fer_20261121/out/stageA{,2,3}/REMOTE_ROWS_MD5.txt experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt; do shasum -a 256 "$f"; head -2 "$f"; done; rg -n '"'"'^def (run_branch|decoded|f0_state|input_record)|ARM_SPECS ='"' experiments | head -32; nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '523,570p;750,790p;1310,1395p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 97ms:
30e5856e5e283da33c26bf2d4d799e61f2907609eabe7f14be672c3769dcda68  experiments/data_pilot_fer_20261121/out/stageA/REMOTE_ROWS_MD5.txt
4ff578d51d0de33f9d2a1187b2d3e30c  rows_shard000.jsonl.gz
d4b794f3d038fa2012ac5978c6c2d2db  rows_shard001.jsonl.gz
5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354  experiments/data_pilot_fer_20261121/out/stageA2/REMOTE_ROWS_MD5.txt
27b188b2c9606324ed31041f1c020249  rows_shard000.jsonl.gz
68f940c752f70281d569f3a2fcf7f57e  rows_shard001.jsonl.gz
6b02caffac6bd8825a05a18ff15c1b7ed7933cb362e40faa79b4120b6a8ce03a  experiments/data_pilot_fer_20261121/out/stageA3/REMOTE_ROWS_MD5.txt
ce023e54f6494292ef45a0e0db887f80  rows_shard000.jsonl.gz
dbc17b5040d70f9f8db8a8bd48d8d55c  rows_shard001.jsonl.gz
b325a788de50aa9ba252b199e9c6c2663c873bc22cf3bf93981a7994e8d64dfc  experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt
76f0b9d2d49ffcc496dc98d6d999c849  rows_shard000.jsonl
1fef60703783fe3ea0d595a1075ef41a  rows_shard001.jsonl
98952079a583b0f68e65c976eea2aacbd78f6d88f4dbc72cf5c6642fb91b53cd  experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt
950a3ce95f5775eefad6f221fa92652e  rows_shard000.jsonl
ccc3bc39c0952b457aec97a5c6e76479  rows_shard001.jsonl
experiments/slot_mismatch_20261019/sm_driver.py:114:def f0_state(ctx, vr, obs, s):
experiments/tf_cstate_e1_20261017/e1_driver.py:49:ARM_SPECS = {
experiments/tf_cstate_e1_20261017/e1_driver.py:169:def f0_state(ctx, obs):
experiments/tf_cstate_e1_20261017/e1_driver.py:191:def run_branch(ctx, kvar, obs, arrays, arm):
experiments/headroom_ladder_20261008/driver.py:424:def decoded_sha(decoded):
experiments/huang_steelman_20261124/reviews/sol-review-3-results.md:4628:def decoded(ctx, output, truth):
experiments/huang_steelman_20261124/reviews/sol-review-3-results.md:5130:def decoded_sha(decoded):
experiments/huang_steelman_20261124/reviews/sol-review-2b-verify.md:4675:    49	ARM_SPECS = {
experiments/sameframe_hg_20261124/reviews/sol-static-review.md:4192:/bin/zsh -lc 'for f in experiments/data_pilot_fer_20261121/out/stageA{,2,3}/REMOTE_ROWS_MD5.txt experiments/huang_steelman_20261124/out/REMOTE_ROWS_MD5.txt experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt; do shasum -a 256 "$f"; head -2 "$f"; done; rg -n '"'"'^def (run_branch|decoded|f0_state|input_record)|ARM_SPECS ='"' experiments | head -32; nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '523,570p;750,790p;1310,1395p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
experiments/tf_cstate_e2_20261017/e2_driver.py:56:ARM_SPECS = {
experiments/tf_cstate_e2_20261017/e2_driver.py:128:def run_branch(ctx, kvar, obs, arrays, arm):
experiments/ratio_sweep_20261118/forced_miss.py:89:def f0_state(study, obs, excluded_delay):
experiments/cstate_codelay_sbl_stage3_20261118/run.py:94:def decoded(ctx, output, truth):
experiments/cstate_codelay_sbl_stage3_20261118/run.py:116:def input_record(raw, obs):
experiments/tf_covariance_audit_20261018/recount.py:167:def decoded_record(record, label, *, has_fer=True, status=False):
   523	    ipc_dir.mkdir(parents=True, exist_ok=True)
   524	    try:
   525	        print('Running G1 (20 stageA F0 replay keys)...', flush=True)
   526	        g1_rows = _spawn_map(_g1_worker, g1_jobs, args.workers, ipc_dir, 'g1')
   527	        print(f'G1 PASS ({len(g1_rows)}/20)', flush=True)
   528	
   529	        print('Running G2 (5 archived huang HG parity keys)...', flush=True)
   530	        g2_rows = _spawn_map(_g2_worker, g2_jobs, min(5, args.workers), ipc_dir, 'g2')
   531	        print(f'G2 PASS ({len(g2_rows)}/5)', flush=True)
   532	
   533	        print('Running G3 (20 CD2 pass-1 parity + CD2/CD2e8 smoke keys)...', flush=True)
   534	        g3_rows = _spawn_map(_g3_worker, g3_jobs, args.workers, ipc_dir, 'g3')
   535	        print(f'G3 PASS ({len(g3_rows)}/20)', flush=True)
   536	
   537	        print(f'Running G4 cost projection ({len(g4_p1_picks)} Part-1 + {len(g4_p2_jobs)} Part-2 keys)...', flush=True)
   538	        g4_p1_rows = _spawn_map(_g4_part1_worker, [list(x) for x in g4_p1_picks], args.workers, ipc_dir, 'g4p1')
   539	        g4_p2_rows = _spawn_map(_g4_part2_worker, g4_p2_jobs, args.workers, ipc_dir, 'g4p2')
   540	    finally:
   541	        shutil.rmtree(ipc_dir, ignore_errors=True)
   542	
   543	    # Compute stratified cost projections
   544	    p1_counts = {k: len(v) for k, v in p1_strata.items()}
   545	    p2_counts = {k: len(v) for k, v in p2_strata.items()}
   546	
   547	    def project(part1_rhos: tuple[int, ...], include_hgint: bool) -> dict[str, Any]:
   548	        p1_sec = 0.0
   549	        p1_detail = {}
   550	        for rho in part1_rhos:
   551	            for band in ('low', 'mid'):
   552	                sub = [x for x in g4_p1_rows if x['rho'] == rho and x['band'] == band]
   553	                mean_cpu = float(np.mean([
   554	                    x['f0_cpu'] + x['hg_cpu'] + (x['hgint_cpu'] if include_hgint else 0.0)
   555	                    for x in sub
   556	                ]))
   557	                cnt = p1_counts[(rho, band)]
   558	                p1_sec += mean_cpu * cnt
   559	                p1_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   560	        p2_sec = 0.0
   561	        p2_detail = {}
   562	        for rho in ar.RHOS:
   563	            for band in ('low', 'mid'):
   564	                sub = [x for x in g4_p2_rows if x['rho'] == rho and x['band'] == band]
   565	                mean_cpu = float(np.mean([x['f0_cpu'] + x['cd2_cpu'] + x['cd2e8_cpu'] for x in sub]))
   566	                cnt = p2_counts[(rho, band)]
   567	                p2_sec += mean_cpu * cnt
   568	                p2_detail[f'{rho}/{band}'] = dict(triggers=cnt, mean_cpu_sec=mean_cpu, hours=mean_cpu * cnt / 3600.0)
   569	        raw_h = p1_sec / 3600.0 + p2_sec / 3600.0 + OVERHEAD_HOURS
   570	        marg_h = raw_h * COST_MARGIN
   750	                ), allow_nan=False) + '\n')
   751	    _write_gzip_jsonl_atomic(final_path, out_lines)
   752	    print(f'Part2 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
   753	
   754	
   755	def _run_sharded_phase(target_fn, job_args: list[tuple[Any, ...]], max_workers: int, cpu_cap_sec: float):
   756	    """Run up to max_workers spawned processes concurrently with live CPU budget check."""
   757	    mp_ctx = multiprocessing.get_context('spawn')
   758	    pending = list(job_args)
   759	    running = {}
   760	    budget_hit = False
   761	    try:
   762	        while pending or running:
   763	            while pending and len(running) < max_workers:
   764	                args = pending.pop(0)
   765	                proc = mp_ctx.Process(target=target_fn, args=args)
   766	                proc.start()
   767	                running[proc.sentinel] = (args[0], proc)
   768	            ready = wait(running, timeout=10.0)
   769	            for r in ready:
   770	                idx, proc = running.pop(r)
   771	                proc.join()
   772	                code = proc.exitcode
   773	                proc.close()
   774	                if code != 0:
   775	                    raise RuntimeError(f'Worker shard {idx:03d} failed with exit code {code}')
   776	            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
   777	            if live_cpu >= cpu_cap_sec:
   778	                budget_hit = True
   779	                break
   780	    finally:
   781	        for _, proc in running.values():
   782	            proc.terminate()
   783	        for _, proc in running.values():
   784	            proc.join()
   785	            proc.close()
   786	    if budget_hit or _used_cpu_seconds() >= cpu_cap_sec:
   787	        print(f'STOPPED_BUDGET: CPU limit reached ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
   788	        sys.exit(BUDGET_EXIT_CODE)
   789	
   790	
  1310	    wall_start = time.monotonic()
  1311	    for name in ARCHIVE_MANIFESTS:
  1312	        verify_manifest(name)
  1313	    C, _, _, helpers = load_stage_runtime()
  1314	    if gate['_config']['frozen_extra_md5'] != helpers['extra_md5']:
  1315	        raise RuntimeError('frozen_extra_md5 mismatch vs gate.json')
  1316	    if gate['_config']['p1_source_md5'] != ar.frozen_p1_md5(C['ctx']):
  1317	        raise RuntimeError('p1_source_md5 mismatch vs gate.json')
  1318	
  1319	    # --- Part 1 ---
  1320	    stageA_base = load_stageA_base(part1_rhos)
  1321	    p1_trig_by_frame: dict[int, list[tuple[str, int, int, int, int]]] = {}
  1322	    p1_n_trig = 0
  1323	    for (s, rho, snr, f), b in stageA_base.items():
  1324	        if b['syndrome'] != 0:
  1325	            p1_trig_by_frame.setdefault(f, []).append((s, rho, snr, b['syndrome'], b['f0_errors']))
  1326	            p1_n_trig += 1
  1327	    p1_jobs = [
  1328	        (idx, tuple(PART1_FRAMES[idx::N_SHARDS]), {f: p1_trig_by_frame.get(f, []) for f in PART1_FRAMES[idx::N_SHARDS]}, include_hgint, raw_dir)
  1329	        for idx in range(N_SHARDS)
  1330	    ]
  1331	    print(f'Launching Part 1: {p1_n_trig} triggered keys on {args.workers} workers (rhos={part1_rhos}, hgint={include_hgint})...', flush=True)
  1332	    t_p1 = time.monotonic()
  1333	    _run_sharded_phase(_part1_shard_worker, p1_jobs, args.workers, BUDGET_CAP_SEC)
  1334	    p1_wall = time.monotonic() - t_p1
  1335	    p1_cpu = _used_cpu_seconds()
  1336	    print(f'Part 1 complete: wall={p1_wall:.1f}s, cumulative_cpu={p1_cpu/3600:.4f}h', flush=True)
  1337	
  1338	    # --- Part 2 ---
  1339	    rho_arch, _ = ar.load_archived_rho_sweep()
  1340	    p2_trig_by_frame: dict[int, list[dict[str, Any]]] = {}
  1341	    p2_n_trig = 0
  1342	    for k, r in rho_arch.items():
  1343	        if r['triggered']:
  1344	            p2_trig_by_frame.setdefault(k[3], []).append(r)
  1345	            p2_n_trig += 1
  1346	    p2_jobs = [
  1347	        (idx, tuple(ar.MAIN_FRAMES[idx::N_SHARDS]), {f: p2_trig_by_frame.get(f, []) for f in ar.MAIN_FRAMES[idx::N_SHARDS]}, raw_dir)
  1348	        for idx in range(N_SHARDS)
  1349	    ]
  1350	    print(f'Launching Part 2: {p2_n_trig} triggered keys on {args.workers} workers (CD2 + CD2e8)...', flush=True)
  1351	    t_p2 = time.monotonic()
  1352	    _run_sharded_phase(_part2_shard_worker, p2_jobs, args.workers, BUDGET_CAP_SEC)
  1353	    p2_wall = time.monotonic() - t_p2
  1354	    total_cpu = _used_cpu_seconds()
  1355	    print(f'Part 2 complete: wall={p2_wall:.1f}s, cumulative_cpu={total_cpu/3600:.4f}h', flush=True)
  1356	
  1357	    raw_md5 = {}
  1358	    for prefix in ('part1', 'part2'):
  1359	        for idx in range(N_SHARDS):
  1360	            p = raw_dir / f'{prefix}_shard{idx:03d}.jsonl.gz'
  1361	            raw_md5[p.name] = ar.md5_file(p)
  1362	    ar.atomic_write_text(
  1363	        out_dir / 'REMOTE_ROWS_MD5.txt',
  1364	        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
  1365	    )
  1366	
  1367	    runtime_info = dict(
  1368	        part1_wall_seconds=p1_wall,
  1369	        part1_cpu_hours=p1_cpu / 3600.0,
  1370	        part2_wall_seconds=p2_wall,
  1371	        part2_cpu_hours=(total_cpu - p1_cpu) / 3600.0,
  1372	        total_wall_seconds=time.monotonic() - wall_start,
  1373	        total_core_hours=total_cpu / 3600.0,
  1374	        cpu_cap_core_hours=BUDGET_CAP_HOURS,
  1375	    )
  1376	    _do_read(out_dir, gate, args.freeze_commit, runtime_info, raw_md5)
  1377	    final_cpu = _used_cpu_seconds()
  1378	    if final_cpu >= BUDGET_CAP_SEC:
  1379	        print(f'STOPPED_BUDGET after read ({final_cpu/3600:.3f} core-hours)', flush=True)
  1380	        sys.exit(BUDGET_EXIT_CODE)
  1381	
  1382	
  1383	def cmd_read(args):
  1384	    out_dir = args.out.resolve()
  1385	    gate = json.loads((out_dir / 'gate.json').read_text(encoding='utf-8'))
  1386	    raw_md5 = {}
  1387	    for line in (out_dir / 'REMOTE_ROWS_MD5.txt').read_text(encoding='utf-8').splitlines():
  1388	        if line.strip():
  1389	            d, n = line.split()
  1390	            raw_md5[n] = d
  1391	    prev = json.loads((out_dir / 'results.json').read_text(encoding='utf-8')) if (out_dir / 'results.json').is_file() else {}
  1392	    runtime_info = prev.get('runtime', dict(total_core_hours=0.0, total_wall_seconds=0.0, cpu_cap_core_hours=BUDGET_CAP_HOURS))
  1393	    _do_read(out_dir, gate, args.freeze_commit, runtime_info, raw_md5)
  1394	
  1395	

codex
两组主比较的方向和判定阈值都对得上。我会按 `research-checkpoint` 的冻结前核查要求，继续追查归档字段、第二遍译码和预算停止路径。
hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '43,62p;160,228p'; nl -ba experiments/cstate_codelay_sbl_stage3_20261118/run.py | sed -n '40,130p'; nl -ba experiments/data_pilot_fer_20261121/cstate.py | sed -n '1,100p'; nl -ba experiments/huang_steelman_20261124/hs_arms.py | sed -n '445,565p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    43	from gs_driver import p1ctx  # noqa: E402
    44	
    45	P1_ROWS = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'out' / 'p1'
    46	DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'  # O1: full P1 grid is the primary unit set
    47	GATE_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
    48	ARMS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7')
    49	ARM_SPECS = {
    50	    'A1': dict(gamma_mode='full', max_edits=2, local_passes=2),
    51	    'A2': dict(gamma_mode='diag', max_edits=2, local_passes=2),
    52	    'A3': dict(gamma_mode='full', max_edits=0, local_passes=2),
    53	    'A4': dict(gamma_mode='diag', max_edits=0, local_passes=2),
    54	    'A5': None,
    55	    'A6': dict(gamma_mode='full', max_edits=0, local_passes=0),
    56	}
    57	A7_SPEC = 'native_twofft.receive rounds=3 iterations=20 ce_mode=soft gain_mode=joint from scratch; G5 compares all r0_*/r1_* arrays with the rounds=2 state'
    58	GEOMETRY_STAGES = ('geometry_setup', 'structural_field_build', 'structural_scoring', 'structural_selection_trace',
    59	                   'structural_refit_refresh', 'structural_fallback_direct', 'local_refinement', 'geometry_finalization')
    60	KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
    61	
    62	
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
   172	
   173	def run_a7(ctx, obs, arrays_ref):
   174	    """A7 = literal third F0 round (rounds=3 from scratch).  G5: every r0_*/r1_* array it exposes must equal the captured
   175	    rounds=2 state bitwise (r1_delays, r1_dopplers, r1_gains, r1_app, r1_check, r1_decoded, r1_input_llr, ce gains, moments, traces)."""
   176	    dec3, arrays3, syn3, seconds = receive_state(ctx, obs, 3)
   177	    keys = sorted(k for k in arrays_ref if k.startswith(('r0_', 'r1_')))
   178	    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
   179	    missing = sorted((required | set(keys)) - set(arrays3))
   180	    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
   181	            e1_lib.deep_equal({k: arrays_ref[k] for k in keys}, {k: arrays3[k] for k in keys}))
   182	    if not diff and gd.bits_sha(arrays3['r2_decoded']) != gd.bits_sha(dec3['decoded']):
   183	        diff = ['rounds=3 returned decoder differs from r2_decoded']
   184	    return dict(result=None, detector=None, decoder=dec3, arrays=arrays3, syndrome=syn3, seconds=seconds, g5_diff=diff, g5_keys=keys)
   185	
   186	
   187	def run_arm(ctx, kvar, obs, arrays, arm):
   188	    return run_a7(ctx, obs, arrays) if arm == 'A7' else run_branch(ctx, kvar, obs, arrays, arm)
   189	
   190	
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
    40	        handle.write('\n')
    41	
    42	
    43	def read_rows(path):
    44	    with path.open() as handle:
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
    98	
    99	
   100	def arm(ctx, kernel, obs, truth, arrays, syndrome, f0):
   101	    if not syndrome:
   102	        return f0, None
   103	    branch = e1.run_branch(ctx, kernel, obs, arrays, 'A1')
   104	    return decoded(ctx, branch['decoder'], truth), branch
   105	
   106	
   107	def path_records(branch):
   108	    if branch is None:
   109	        return None
   110	    res = branch['result']
   111	    return dict(paths=[[p.delay,p.doppler] for p in res.paths],
   112	                edits=[dict(slot=x['slot'], old=x['old'], new=x['new']) for x in res.edits],
   113	                fallback=bool(res.diagnostics['numerical_fallback']))
   114	
   115	
   116	def input_record(raw, obs):
   117	    return dict(y=digest(obs['y']), pilot=digest(obs['pilot']), info=digest(raw['info']),
   118	                coded=digest(raw['coded']), noise=digest(raw['noise']), data=digest(raw['data']))
   119	
   120	
   121	def one(ctx, full, route, base, s, rho, snr, frame):
   122	    raw, obs, truth = observed(ctx, base, rho, snr)
   123	    dec, arrays, syndrome, _ = e1.f0_state(ctx, obs)
   124	    f0 = decoded(ctx, dec, truth)
   125	    a, full_branch = arm(ctx, full, obs, truth, arrays, syndrome, f0)
   126	    b, codelay_branch = arm(ctx, route, obs, truth, arrays, syndrome, f0)
   127	    return dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame,
   128	                syndrome=syndrome, truth=truth_record(obs, truth), inputs=input_record(raw, obs),
   129	                arms=dict(F0=f0, FULL=a, CODELAY=b), full_geometry=path_records(full_branch),
   130	                codelay_geometry=path_records(codelay_branch))
nl: experiments/data_pilot_fer_20261121/cstate.py: No such file or directory
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
   496	
   497	def run_z_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
   498	    return _run_exchange_arm(ctx, helpers, helpers['z_kernel'], 'Z', obs, arrays, truth, record_match=record_match)
   499	
   500	
   501	def run_cd_arm(ctx, helpers, obs, arrays, truth, *, record_match: bool = True) -> dict[str, Any]:
   502	    return _run_exchange_arm(ctx, helpers, helpers['cd'], 'CD', obs, arrays, truth, record_match=record_match)
   503	
   504	
   505	def row_key(row: dict[str, Any]) -> tuple[str, int, int, int]:
   506	    return (row['scenario'], int(row['rho_permille']), int(row['snr_centi_db']), int(row['frame']))
   507	
   508	
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

exec
/bin/zsh -lc "nl -ba experiments/huang_steelman_20261124/hs_analysis.py | sed -n '1,150p'; nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '736,752p;1016,1126p;1284,1312p;1396,1417p'; ls -l /opt/anaconda3/bin/python; rg -n 'COREDUMP|NUM_THREADS|TORCH|sem|TMPDIR|timeout' experiments/huang_steelman_20261124/launch_main.sh" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Pre-registered statistical analysis, 36-pair simultaneous projection, and Markdown rendering."""
     2	from __future__ import annotations
     3	
     4	import hashlib
     5	import importlib.util
     6	import math
     7	from pathlib import Path
     8	from typing import Any, NamedTuple
     9	
    10	import numpy as np
    11	
    12	HERE = Path(__file__).resolve().parent
    13	EXPERIMENTS = HERE.parent
    14	P1_AGG_PATH = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'p1_agg.py'
    15	EXPECTED_P1_AGG_MD5 = '047bd512a1c5c3bc437a334a54b075e7'
    16	
    17	_p1_agg_md5 = hashlib.md5(P1_AGG_PATH.read_bytes()).hexdigest()
    18	if _p1_agg_md5 != EXPECTED_P1_AGG_MD5:
    19	    raise RuntimeError(f'Frozen p1_agg.py MD5 mismatch before import: {_p1_agg_md5} != {EXPECTED_P1_AGG_MD5}')
    20	
    21	_spec = importlib.util.spec_from_file_location('hs_p1_agg', P1_AGG_PATH)
    22	p1_agg = importlib.util.module_from_spec(_spec)
    23	_spec.loader.exec_module(p1_agg)
    24	
    25	SCENARIOS = ('U', 'G')
    26	ALL_RHOS = (150, 200, 250, 300, 400, 500)
    27	ALL_SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
    28	BOOT_DRAWS = 50_000
    29	BOOT_SEED = 20261124
    30	FAMILY_ALPHA = 0.05
    31	PRIMARY_ALPHA = FAMILY_ALPHA / 3.0
    32	EQUIV_MARGIN_DB = 0.5
    33	
    34	
    35	class Bounds(NamedTuple):
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
    91	    errors_by_key: dict[tuple[str, int, int, int], dict[str, int]],
    92	    arms: tuple[str, ...],
    93	    rhos: tuple[int, ...],
    94	    snrs: tuple[int, ...],
    95	    frames: tuple[int, ...],
    96	    *,
    97	    boot_draws: int = BOOT_DRAWS,
    98	    boot_seed: int = BOOT_SEED,
    99	) -> tuple[dict[tuple[str, int, str], Bounds], dict[str, dict[str, Any]]]:
   100	    """Compute censor-aware 1% FER crossings using one shared physical-frame bootstrap."""
   101	    if not frames or len(frames) != len(set(frames)):
   102	        raise ValueError('Frames must be non-empty and unique')
   103	    snrs = tuple(sorted(snrs))
   104	    expected = {
   105	        (s, rho, snr, f)
   106	        for s in SCENARIOS for rho in rhos for snr in snrs for f in frames
   107	    }
   108	    if errors_by_key.keys() != expected:
   109	        raise ValueError(
   110	            f'Key mismatch: missing={len(expected - errors_by_key.keys())}, '
   111	            f'extra={len(errors_by_key.keys() - expected)}'
   112	        )
   113	
   114	    n = len(frames)
   115	    rng = np.random.default_rng(boot_seed)
   116	    # Chunked matrix multiply keeps memory bounded (~40 MB per 10k chunk)
   117	    weights = rng.multinomial(n, np.full(n, 1.0 / n), size=boot_draws).astype(np.float64) / n
   118	
   119	    crossings: dict[tuple[str, int, str], Bounds] = {}
   120	    cells: dict[str, dict[str, Any]] = {}
   121	    for s in SCENARIOS:
   122	        for rho in rhos:
   123	            cell_id = f'{s}_{rho}'
   124	            cells[cell_id] = {}
   125	            for arm in arms:
   126	                failures = np.array(
   127	                    [[errors_by_key[s, rho, snr, f][arm] > 0 for snr in snrs] for f in frames],
   128	                    dtype=np.int8,
   129	                )
   130	                fer_pt = failures.mean(axis=0)
   131	                pt = _crossing(fer_pt, n, snrs)
   132	                dr = _crossing(weights @ failures, n, snrs)
   133	                b = Bounds(
   134	                    np.concatenate([pt.lower, dr.lower]),
   135	                    np.concatenate([pt.upper, dr.upper]),
   136	                )
   137	                crossings[s, rho, arm] = b
   138	                lo95, hi95 = _interval(b, 0.05)
   139	                cells[cell_id][arm] = dict(
   140	                    point_db=[_represent(b.lower[0]), _represent(b.upper[0])],
   141	                    ci95_db=[_represent(lo95), _represent(hi95)],
   142	                    half_width_db=_represent((hi95 - lo95) / 2.0),
   143	                    left_censored_draws=int(np.isneginf(b.lower[1:]).sum()),
   144	                    right_censored_draws=int(np.isposinf(b.upper[1:]).sum()),
   145	                    fer={str(snr): float(rate) for snr, rate in zip(snrs, fer_pt, strict=True)},
   146	                )
   147	    return crossings, cells
   148	
   149	
   150	def scene_means(
   736	                if int(syn) != int(item['syndrome']) or f0 != dict(
   737	                    errors=int(item['arms']['F0']['errors']),
   738	                    decoded_sha=item['arms']['F0']['decoded_sha'],
   739	                ):
   740	                    raise RuntimeError(f'Part2 F0 drift at {(s, rho, snr, frame)}')
   741	                arch_cd = dict(
   742	                    errors=int(item['arms']['CD']['errors']),
   743	                    decoded_sha=item['arms']['CD']['decoded_sha'],
   744	                )
   745	                cd2 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1', expected_pass1=arch_cd)
   746	                cd2e8 = run_cd_two_pass(ctx, helpers, obs, arrays, truth, arm_spec='A1e8')
   747	                out_lines.append(json.dumps(dict(
   748	                    scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=int(syn),
   749	                    arms=dict(CD2=cd2, CD2e8=cd2e8),
   750	                ), allow_nan=False) + '\n')
   751	    _write_gzip_jsonl_atomic(final_path, out_lines)
   752	    print(f'Part2 shard {shard_idx:03d} done ({len(out_lines)} triggered keys)', flush=True)
  1016	            if pt_hi < best_val:
  1017	                best_val = pt_hi
  1018	                best_r = r
  1019	        best_rho[a] = int(best_r)
  1020	
  1021	    # Diagnostics on triggered keys
  1022	    trig_rows = [r for r in full_rows.values() if r['triggered']]
  1023	    diag = {}
  1024	    for arm in ('CD2', 'CD2e8'):
  1025	        p1_stop = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 1)
  1026	        p2_ran = sum(1 for r in trig_rows if r['arms'][arm]['passes_used'] == 2)
  1027	        p2_rescued = sum(
  1028	            1 for r in trig_rows
  1029	            if r['arms'][arm]['passes_used'] == 2 and r['arms'][arm]['pass1_errors'] > 0 and r['arms'][arm]['errors'] == 0
  1030	        )
  1031	        vs_hg = dict(
  1032	            arm_only=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] > 0),
  1033	            hg_only=sum(1 for r in trig_rows if r['arms']['HG']['errors'] == 0 and r['arms'][arm]['errors'] > 0),
  1034	            both=sum(1 for r in trig_rows if r['arms'][arm]['errors'] == 0 and r['arms']['HG']['errors'] == 0),
  1035	            neither=sum(1 for r in trig_rows if r['arms'][arm]['errors'] > 0 and r['arms']['HG']['errors'] > 0),
  1036	        )
  1037	        diag[arm] = dict(
  1038	            triggered=len(trig_rows),
  1039	            pass1_early_stop=p1_stop,
  1040	            pass2_ran=p2_ran,
  1041	            pass2_rescued=p2_rescued,
  1042	            mean_pass1_edits=float(np.mean([r['arms'][arm]['pass1_edits'] for r in trig_rows])),
  1043	            mean_pass2_edits_when_ran=float(np.mean([r['arms'][arm]['pass2_edits'] for r in trig_rows if r['arms'][arm]['passes_used'] == 2])) if p2_ran else 0.0,
  1044	            paired_vs_hg=vs_hg,
  1045	        )
  1046	
  1047	    return dict(
  1048	        boot_draws=boot_draws,
  1049	        boot_seed=boot_seed,
  1050	        primary_alpha=an.PRIMARY_ALPHA,
  1051	        E_CD2_minus_HG=p2_E,
  1052	        E8_CD2e8_minus_HG=p2_E8,
  1053	        by_scenario=by_scen,
  1054	        secondary_contrasts_95=sec,
  1055	        pooled_crossings=pooled_table,
  1056	        best_rho=best_rho,
  1057	        diagnostics=diag,
  1058	        cells=cells,
  1059	    )
  1060	
  1061	
  1062	def render_results_md(res: dict[str, Any]) -> str:
  1063	    p1 = res['part1']
  1064	    p2 = res['part2']
  1065	    q1 = p1['primary_P1']
  1066	    e1 = p2['E_CD2_minus_HG']
  1067	    e8 = p2['E8_CD2e8_minus_HG']
  1068	
  1069	    def fval(x):
  1070	        if isinstance(x, list):
  1071	            return f'[{fval(x[0])}, {fval(x[1])}]' if x[0] != x[1] else fval(x[0])
  1072	        return x if isinstance(x, str) else f'{x:.4f}'
  1073	
  1074	    lines = [
  1075	        '# Same-Frame Decisive Check Results (`sameframe_hg_20261124`)',
  1076	        '',
  1077	        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
  1078	        f'- Cumulative CPU: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 12.0 h; wall {res["runtime"]["total_wall_seconds"]:.1f} s)',
  1079	        '',
  1080	        '## Primary Verdicts (Pre-Registered)',
  1081	        '',
  1082	        '| Test | Contrast | Point (dB) | Primary CI (dB) | Verdict |',
  1083	        '|---|---|---:|---|---|',
  1084	        f'| **P1** (95% paired) | `min HG (100..250) − min s100 (100..200)` | {fval(q1["point_db"])} | [{fval(q1["ci95_db"][0])}, {fval(q1["ci95_db"][1])}] | **{q1["verdict"]}** |',
  1085	        f'| **P2-E** (98.33% 36-pair proj) | `min CD2 − min HG` | {fval(e1["point_db"])} | [{fval(e1["ci9833_projected_db"][0])}, {fval(e1["ci9833_projected_db"][1])}] (95%: [{fval(e1["ci95_projected_db"][0])}, {fval(e1["ci95_projected_db"][1])}]) | **{e1["verdict"]}** |',
  1086	        f'| **P2-E8** (98.33% 36-pair proj) | `min CD2e8 − min HG` | {fval(e8["point_db"])} | [{fval(e8["ci9833_projected_db"][0])}, {fval(e8["ci9833_projected_db"][1])}] (95%: [{fval(e8["ci95_projected_db"][0])}, {fval(e8["ci95_projected_db"][1])}]) | **{e8["verdict"]}** |',
  1087	        '',
  1088	        '## Part 1: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)',
  1089	        '',
  1090	    ]
  1091	    p1_arms = [a for a in ('base', 'delay', 'HG', 'HG1', 'HGint', 's100', 's050', 'ldop', 'full', 's025', 's200') if a in p1['mean_crossing']]
  1092	    all_p1_rhos = ('50', '100', '150', '200', '250', '300')
  1093	    lines.append('| Arm | ' + ' | '.join(f'ρ={int(r)/1000:.2f}' for r in all_p1_rhos) + ' | Best ρ |')
  1094	    lines.append('|---|' + '---:|' * len(all_p1_rhos) + '---:|')
  1095	    for a in p1_arms:
  1096	        row_cells = [fval(p1['mean_crossing'][a][r]) if r in p1['mean_crossing'][a] else '—' for r in all_p1_rhos]
  1097	        lines.append(f'| {a} | ' + ' | '.join(row_cells) + f' | {p1["best_rho"][a]/1000:.2f} |')
  1098	    lines += ['', '### Part 1 Secondary Contrasts (95% Paired Frame Bootstrap, dB)', '', '| Contrast | Point (dB) | 95% CI (dB) |', '|---|---:|---|']
  1099	    for name, c in p1['secondary_contrasts'].items():
  1100	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci95_db"][0])}, {fval(c["ci95_db"][1])}] |')
  1101	
  1102	    lines += ['', '## Part 2: 1% FER Crossings on Huang Frames (5400–5799, U/G Mean, dB)', '']
  1103	    p2_arms = [a for a in ('F0', 'CD', 'CD2', 'CD2e8', 'HG', 'HG1', 'HGint', 'Z') if a in p2['pooled_crossings']]
  1104	    lines.append('| ρ | ' + ' | '.join(p2_arms) + ' |')
  1105	    lines.append('|---:|' + '---|' * len(p2_arms))
  1106	    for r in ar.RHOS:
  1107	        cells_str = []
  1108	        for a in p2_arms:
  1109	            d = p2['pooled_crossings'][a][str(r)]
  1110	            cells_str.append(f'{fval(d["point_db"])} [{fval(d["ci95_db"][0])}, {fval(d["ci95_db"][1])}]')
  1111	        lines.append(f'| {r/1000:.2f} | ' + ' | '.join(cells_str) + ' |')
  1112	
  1113	    lines += ['', '### Part 2 Diagnostics & Secondary Contrasts', '']
  1114	    for arm in ('CD2', 'CD2e8'):
  1115	        d = p2['diagnostics'][arm]
  1116	        v = d['paired_vs_hg']
  1117	        lines.append(
  1118	            f'- `{arm}`: pass-1 stop {d["pass1_early_stop"]}/{d["triggered"]}, '
  1119	            f'pass-2 ran {d["pass2_ran"]} (rescued {d["pass2_rescued"]}), '
  1120	            f'mean edits p1={d["mean_pass1_edits"]:.2f} p2={d["mean_pass2_edits_when_ran"]:.2f}; '
  1121	            f'vs HG: {arm}_only={v["arm_only"]}, HG_only={v["hg_only"]}, both={v["both"]}, neither={v["neither"]}'
  1122	        )
  1123	    lines += ['', '| Contrast | Point (dB) | 95% Projected CI (dB) |', '|---|---:|---|']
  1124	    for name, c in p2['secondary_contrasts_95'].items():
  1125	        lines.append(f'| {name} | {fval(c["point_db"])} | [{fval(c["ci_projected_db"][0])}, {fval(c["ci_projected_db"][1])}] |')
  1126	    return '\n'.join(lines) + '\n'
  1284	def cmd_run(args):
  1285	    print(sys.executable, flush=True)
  1286	    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
  1287	        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
  1288	    ar.check_thread_env()
  1289	    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
  1290	        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
  1291	    if not 1 <= args.workers <= 32:
  1292	        raise ValueError('workers must be in 1..32')
  1293	
  1294	    out_dir = args.out.resolve()
  1295	    raw_dir = out_dir / 'raw'
  1296	    raw_dir.mkdir(parents=True, exist_ok=True)
  1297	    if list(raw_dir.glob('part*_shard*.jsonl*')):
  1298	        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')
  1299	
  1300	    gate = json.loads((out_dir / 'gate.json').read_text(encoding='utf-8'))
  1301	    if not gate.get('all_passed') or not gate.get('selected'):
  1302	        raise RuntimeError('Refusing to run without passing gate.json')
  1303	    if gate['_config']['own_md5'] != own_md5():
  1304	        raise RuntimeError('gate.json own_md5 differs from current deployed files; re-run gates')
  1305	
  1306	    sel = gate['selected']
  1307	    part1_rhos = tuple(int(r) for r in sel['part1_rhos'])
  1308	    include_hgint = bool(sel['include_hgint'])
  1309	
  1310	    wall_start = time.monotonic()
  1311	    for name in ARCHIVE_MANIFESTS:
  1312	        verify_manifest(name)
  1396	def main():
  1397	    ap = argparse.ArgumentParser(description=__doc__)
  1398	    sub = ap.add_subparsers(dest='mode', required=True)
  1399	    g = sub.add_parser('gate')
  1400	    g.add_argument('--out', type=Path, required=True)
  1401	    g.add_argument('--workers', type=int, default=16)
  1402	
  1403	    r = sub.add_parser('run')
  1404	    r.add_argument('--out', type=Path, required=True)
  1405	    r.add_argument('--freeze-commit', required=True)
  1406	    r.add_argument('--workers', type=int, default=WORKERS)
  1407	
  1408	    rd = sub.add_parser('read')
  1409	    rd.add_argument('--out', type=Path, required=True)
  1410	    rd.add_argument('--freeze-commit', required=True)
  1411	
  1412	    args = ap.parse_args()
  1413	    dict(gate=cmd_gate, run=cmd_run, read=cmd_read)[args.mode](args)
  1414	
  1415	
  1416	if __name__ == '__main__':
  1417	    main()
lrwxr-xr-x  1 guoyikun  staff  10 Sep 19  2025 /opt/anaconda3/bin/python -> python3.13
37:export TMPDIR="/data/guoyikun/tmp"
39:export OMP_NUM_THREADS=1
40:export OPENBLAS_NUM_THREADS=1
41:export MKL_NUM_THREADS=1
42:export NUMEXPR_NUM_THREADS=1
43:export BLIS_NUM_THREADS=1
49:        timeout --kill-after=5s 900s "$PY" -B -u "$HERE/gates.py" \
73:        timeout --kill-after=5s 1650s "$PY" -B -u "$HERE/run_main.py" \
109:        timeout --kill-after=5s 1785s taskset -c "$QUIET_CPU" "$PY" -B -u "$HERE/timing.py" \

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "rg -n '"'^(import|from)|MD5|sha'"' experiments/data_pilot_fer_20261121/stageA*.py | head -60; rg -n 'fallback|finit|gain' experiments/cstate_codelay_sbl_stage3_20261118/codelay.py; nl -ba experiments/tf_cstate_e1_20261017/e1_driver.py | sed -n '225,270p'; rg -n 'CENSORED|point_db|per_draw' experiments/huang_steelman_20261124/out/results.json | head -12; cat experiments/sameframe_hg_20261124/PROTOCOL.md | tail -7" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
experiments/data_pilot_fer_20261121/stageA.py:12:import argparse, gzip, json, os, resource, sys, time
experiments/data_pilot_fer_20261121/stageA.py:13:from multiprocessing import get_context
experiments/data_pilot_fer_20261121/stageA.py:14:from pathlib import Path
experiments/data_pilot_fer_20261121/stageA.py:15:import numpy as np
experiments/data_pilot_fer_20261121/stageA.py:99:    z5 = (np.abs(C['U'].conj().T @ obs['y']) ** 2).reshape(C['lmax'] + 1, 5)
experiments/data_pilot_fer_20261121/stageA.py:111:def shard_job(job):
experiments/data_pilot_fer_20261121/stageA.py:114:    path = Path(out) / f'rows_shard{idx:03d}.jsonl'
experiments/data_pilot_fer_20261121/stageA.py:132:    with open(EXP / 'rho_sweep_20261119' / 'out' / 'main_20261119' / 'rows_shard000.jsonl') as fh:
experiments/data_pilot_fer_20261121/stageA.py:173:        for idx, n in pool.imap_unordered(shard_job, jobs):  # no in-run cost stop: cost is projected by the gate
experiments/data_pilot_fer_20261121/stageA.py:179:    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
experiments/data_pilot_fer_20261121/stageA.py:205:    for p in sorted(out.glob('rows_shard*.jsonl.gz')):
experiments/data_pilot_fer_20261121/stageA2.py:14:import argparse, gzip, json, os, resource, sys, time
experiments/data_pilot_fer_20261121/stageA2.py:15:from multiprocessing import get_context
experiments/data_pilot_fer_20261121/stageA2.py:16:from pathlib import Path
experiments/data_pilot_fer_20261121/stageA2.py:17:import numpy as np
experiments/data_pilot_fer_20261121/stageA2.py:19:import stageA
experiments/data_pilot_fer_20261121/stageA2.py:20:from stageA import FRAMES, SCENARIOS, setup, support_stats
experiments/data_pilot_fer_20261121/stageA2.py:75:def shard_job(job):
experiments/data_pilot_fer_20261121/stageA2.py:77:    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
experiments/data_pilot_fer_20261121/stageA2.py:95:    with gzip.open(Path(out).parent / 'stageA' / 'rows_shard000.jsonl.gz', 'rt') as fh:
experiments/data_pilot_fer_20261121/stageA2.py:150:        for idx, n in pool.imap_unordered(shard_job, jobs):
experiments/data_pilot_fer_20261121/stageA2.py:153:    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
experiments/data_pilot_fer_20261121/stageA2.py:174:    for p in sorted(Path(out).glob('rows_shard*.jsonl.gz')):
experiments/data_pilot_fer_20261121/stageA3.py:2:true Doppler plus Gaussian error sigma * z (z ~ N(0,1) per path, fixed per frame and scenario, shared across sigma,
experiments/data_pilot_fer_20261121/stageA3.py:11:import argparse, gzip, json, os, resource, sys, time
experiments/data_pilot_fer_20261121/stageA3.py:12:from multiprocessing import get_context
experiments/data_pilot_fer_20261121/stageA3.py:13:from pathlib import Path
experiments/data_pilot_fer_20261121/stageA3.py:14:import numpy as np
experiments/data_pilot_fer_20261121/stageA3.py:16:import stageA, stageA2
experiments/data_pilot_fer_20261121/stageA3.py:17:from stageA import FRAMES, SCENARIOS, setup, support_stats
experiments/data_pilot_fer_20261121/stageA3.py:18:from stageA2 import f0_true, crossing, load
experiments/data_pilot_fer_20261121/stageA3.py:58:def shard_job(job):
experiments/data_pilot_fer_20261121/stageA3.py:60:    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
experiments/data_pilot_fer_20261121/stageA3.py:77:    with gzip.open(Path(out).parent / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt') as fh:
experiments/data_pilot_fer_20261121/stageA3.py:112:        for idx, n in pool.imap_unordered(shard_job, jobs):
experiments/data_pilot_fer_20261121/stageA3.py:115:    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
experiments/data_pilot_fer_20261121/stageA3.py:123:    for p in sorted(Path(out).glob('rows_shard*.jsonl.gz')):
experiments/data_pilot_fer_20261121/stageA4.py:16:import argparse, gzip, json, os, resource, sys, time
experiments/data_pilot_fer_20261121/stageA4.py:17:from multiprocessing import get_context
experiments/data_pilot_fer_20261121/stageA4.py:18:from pathlib import Path
experiments/data_pilot_fer_20261121/stageA4.py:19:import numpy as np
experiments/data_pilot_fer_20261121/stageA4.py:21:import stageA
experiments/data_pilot_fer_20261121/stageA4.py:22:from stageA import SCENARIOS, setup
experiments/data_pilot_fer_20261121/stageA4.py:23:from physical import daft, regressors, Channel
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
rg: experiments/huang_steelman_20261124/out/results.json: IO error for operation on experiments/huang_steelman_20261124/out/results.json: No such file or directory (os error 2)
## 6. Execution & Provenance Rules (deinlab)

- Working directory: `cd /data/guoyikun/00inbox/AFDM-channel-estimation`; conda env `AFDM` (`/home/guoyikun/.conda/envs/AFDM/bin/python`, printed as line 1 of every log).
- Thread & scratch isolation: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `BLIS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, `CUDA_VISIBLE_DEVICES=""`, `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR=/data/guoyikun/tmp`, `XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`. Never write to `/tmp` or `/home/guoyikun`.
- Workers: `24` ($\le 32$, respecting concurrent funnel workload on the 128-core host); `tmux` session `g_sameframe`.
- Hard budget stop: live cumulative CPU monitoring capped at `12.0` core-hours (`STOPPED_BUDGET` on breach).
- Large raw JSONL.gz shards stay on deinlab (`experiments/sameframe_hg_20261124/out/raw/`) with MD5 recorded locally in `out/REMOTE_ROWS_MD5.txt`. Small outputs (`gate.json`, `results.json` with `_argv` & `_config`, `RESULTS.md`, `REMOTE_ROWS_MD5.txt`, `STATUS`, logs) copied locally.

exec
/bin/zsh -lc "nl -ba experiments/data_pilot_fer_20261121/stageA.py | head -34; nl -ba experiments/data_pilot_fer_20261121/stageA2.py | head -30; nl -ba experiments/data_pilot_fer_20261121/stageA3.py | head -64; nl -ba experiments/cstate_codelay_sbl_stage3_20261118/codelay.py | sed -n '1,150p'; rg -n '"'^def crossing|cut|0.01|1e-'"' experiments/tcom_reference_frame_20261015/p1_agg.py; rg -n 'row\\[.arms.|arms=dict|triggered|syndrome' experiments/huang_steelman_20261124/run_main.py | head -35; rg -n 'input_record|arms=dict|syndrome|triggered' experiments/rho_sweep_20261119/*.py | head -30" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Stage A (STAGEA_PROTOCOL.md): does a true-delay round-0 support let low pilot fractions beat the best baseline?
     2	
     3	Arms per key (same observation): base = F0 + CODELAY exchange (rho-sweep pipeline); delay = the same with the round-0
     4	support replaced by the 8 true delays (Doppler centers observable: best pilot-MF integer column at each delay).
     5	Injection replaces ctx.native.pilot_front only for the 'delay' F0 call; everything downstream is unchanged.
     6	Reuses unified_cov_prospective_20261119/cstate.py (context, stage3 inputs/observed/e1.f0_state/e1.run_branch).
     7	
     8	  python stageA.py gate  --out out/stageA_gate.json
     9	  python stageA.py run   --out out/stageA                 (rows + STATUS)
    10	  python stageA.py read  --out out/stageA                 (frozen readout -> results.json)
    11	"""
    12	import argparse, gzip, json, os, resource, sys, time
    13	from multiprocessing import get_context
    14	from pathlib import Path
    15	import numpy as np
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
     1	"""Stage A2 (STAGEA2_PROTOCOL.md): does a fully true round-0 channel (delays, Doppler, gains) beat the true-delay
     2	ceiling of stage A?  Copies stageA.one_arm/f0 with one change: the round-0 call of ctx.native.time_refine is replaced
     3	(stageA.f0 can only override pilot_front, whose Doppler/gains time_refine re-estimates from the pilot alone).
     4	
     5	Arms per key (same observation as stage A):
     6	  full = round 0 uses the true (l_i, k_real, g_i); round 1 and the CODELAY exchange unchanged.
     7	  ldop = round 0 uses the true (l_i, k_real); gains are the LS solution of time_refine at those values (no search).
     8	base / delay rows come from stage A (out/stageA, same frames, rho, SNR grid >= 3 dB, same observations).
     9	
    10	  python stageA2.py gate --out out/stageA2_gate.json
    11	  python stageA2.py run  --out out/stageA2
    12	  python stageA2.py read --out out/stageA2      (needs out/stageA rows next to it)
    13	"""
    14	import argparse, gzip, json, os, resource, sys, time
    15	from multiprocessing import get_context
    16	from pathlib import Path
    17	import numpy as np
    18	
    19	import stageA
    20	from stageA import FRAMES, SCENARIOS, setup, support_stats
    21	
    22	RHOS = (50, 100, 150, 200)
    23	SNRS = (200, 250) + stageA.SNRS
    24	ARMS = ('full', 'ldop')
    25	FRAMES_PER_SHARD, WORKERS = 5, 32
    26	BOOT, SEED, KILL_DB = 2000, 20261121, 0.15
    27	
    28	
    29	def f0_true(C, obs, truth, gains):
    30	    """F0 whose round-0 time_refine returns the true channel; gains='true' or 'ls'. Restores time_refine afterwards."""
     1	"""Stage A3 (STAGEA3_PROTOCOL.md): Doppler-error tolerance of the round-0 channel.  Round 0 gets the true delays and
     2	true Doppler plus Gaussian error sigma * z (z ~ N(0,1) per path, fixed per frame and scenario, shared across sigma,
     3	rho and SNR); gains are the pilot LS solution of time_refine at those values (stage A2 'ldop' with perturbed Doppler).
     4	one_arm is stageA2.one_arm with the truth passed to f0_true replaced by the perturbed one (stageA2.one_arm scores
     5	against the truth it injects, so it cannot be called directly).
     6	
     7	  python stageA3.py gate --out out/stageA3_gate.json   (needs out/stageA2 rows)
     8	  python stageA3.py run  --out out/stageA3
     9	  python stageA3.py read --out out/stageA3             (needs out/stageA and out/stageA2 rows)
    10	"""
    11	import argparse, gzip, json, os, resource, sys, time
    12	from multiprocessing import get_context
    13	from pathlib import Path
    14	import numpy as np
    15	
    16	import stageA, stageA2
    17	from stageA import FRAMES, SCENARIOS, setup, support_stats
    18	from stageA2 import f0_true, crossing, load
    19	
    20	RHOS = (100, 150, 200)
    21	SNRS = stageA2.SNRS
    22	SIGMAS = (25, 50, 100, 200)                      # Doppler error std in 1/1000 bin
    23	ARMS = tuple(f's{s:03d}' for s in SIGMAS)
    24	FRAMES_PER_SHARD, WORKERS = 5, 32
    25	BOOT, SEED = 2000, 20261121
    26	
    27	
    28	def z_paths(frame, s_, n):
    29	    return np.random.default_rng([SEED, frame, SCENARIOS.index(s_)]).standard_normal(n)
    30	
    31	
    32	def one_arm(C, obs, truth, sigma, z):
    33	    ctx, stage3 = C['ctx'], C['stage3']
    34	    pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + sigma / 1000 * z).tolist())
    35	    dec, arrays, syndrome, _ = f0_true(C, obs, pert, 'ls')
    36	    s2 = float(obs['sigma2'])
    37	    rec = dict(syndrome=int(syndrome),
    38	               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
    39	               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
    40	               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
    41	               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    42	    if syndrome:
    43	        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
    44	        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    45	        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    46	    else:
    47	        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    48	    return rec
    49	
    50	
    51	def run_key(C, base, s_, rho, snr, frame, sigmas=SIGMAS):
    52	    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    53	    z = z_paths(frame, s_, len(truth['l_i']))
    54	    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
    55	                arms={f's{s:03d}': one_arm(C, obs, truth, s, z) for s in sigmas})
    56	
    57	
    58	def shard_job(job):
    59	    idx, frames, out = job
    60	    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
    61	    with open(path, 'x') as fh:
    62	        for frame in frames:
    63	            for s_ in SCENARIOS:
    64	                for rho in RHOS:
     1	"""Narrow covariance binding over the immutable E-1 geometry source."""
     2	import hashlib
     3	from pathlib import Path
     4	from types import FunctionType
     5	
     6	import numpy as np
     7	
     8	# The E-1 selector has no covariance injection point. Instantiate its reviewed
     9	# source in a private namespace and replace only its two variance FFT bindings.
    10	E1_SOURCE_MD5 = '26571aa84e39097d264421a90bab23df'
    11	
    12	
    13	def _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel):
    14	    total, n = variance
    15	    i, j = np.nonzero(left_delay[:, None] == right_delay)
    16	    gamma = np.zeros((len(left_delay), len(right_delay)), dtype=complex)
    17	    gamma[i, j] = total * dkernel(right_nu[j] - left_nu[i], n)
    18	    return gamma
    19	
    20	
    21	def load(full):
    22	    from physical import dkernel
    23	
    24	    def cross(left, right, variance, _c1, gamma_mode='full'):
    25	        if gamma_mode != 'full':
    26	            raise ValueError('The closed-form kernel expects the full-path selector')
    27	        left_delay = np.fromiter((p.delay for p in left), dtype=int, count=len(left))
    28	        right_delay = np.fromiter((p.delay for p in right), dtype=int, count=len(right))
    29	        left_nu = np.fromiter((p.doppler for p in left), dtype=float, count=len(left))
    30	        right_nu = np.fromiter((p.doppler for p in right), dtype=float, count=len(right))
    31	        return _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel)
    32	
    33	    def projected_variance(v, delays, dopplers, _c1):
    34	        delays, dopplers = np.asarray(delays), np.asarray(dopplers)
    35	        gamma = _block(delays, dopplers, delays, dopplers, (float(v.sum()), len(v)), dkernel)
    36	        return (gamma + gamma.conj().T) * .5
    37	
    38	    p = Path(full.__file__)
    39	    source = p.read_bytes()
    40	    if hashlib.md5(source).hexdigest() != E1_SOURCE_MD5:
    41	        raise ValueError('E-1 geometry source differs from the reviewed binding')
    42	    original_line = b'vf = np.fft.fft(v)'
    43	    if source.count(original_line) != 2:
    44	        raise ValueError('Unexpected number of E-1 variance FFT paths')
    45	    source = source.replace(original_line, b'vf = (float(v.sum()), len(v))')
    46	    route = type(full)('stage3_codelay_geometry')
    47	    route.__file__ = str(p)
    48	    exec(compile(source, str(p), 'exec'), vars(route))
    49	    system = full._system
    50	    route._system = FunctionType(system.__code__,
    51	                                 dict(system.__globals__, projected_variance=projected_variance),
    52	                                 system.__name__, system.__defaults__)
    53	    route._gamma_cross = cross
    54	    return route
9:  H1  eligible SNR points: F0 FER in [1e-3, .5].  Per eligible point: one-sided exact paired McNemar (B better than F0),
10:      Holm over the eligible points of the cell, alpha .05.  Gain @FER 1e-2 = x(F0) - x(B) dB with a frame-block bootstrap
17:  H2  gap x(B) - x(A3) @1e-2 with CI; "within .5 dB" may be written for a cell only if the CI upper bound <= .5.
18:  H3  x(B) - x(C) @1e-2: PASS iff CI upper bound <= +.1 AND quiet mean time(B) <= .65 time(C) (--timing rows; PENDING-TIMING if absent).
42:TARGET = 1e-2
43:ELIGIBLE = (1e-3, .5)
78:def crossing(fer, n, snr, target=TARGET):
242:    res['crossing_1e-2'] = {a: dict(point=jf(X[a][0]), status=STATUS[int(ST[a][0])], ci=[jf(nearest_rank(X[a][1:], .025)), jf(nearest_rank(X[a][1:], .975))],
380:            L.append(f"- H1 **{h['label']}**: {h['n_significant']}/{h['n_eligible']} eligible points Holm-significant; gain @1e-2 = {h['gain_db']['point']} dB "
422:    check('mcnemar b=10,c=0 -> 2^-10', abs(mcnemar_one_sided(10, 0) - 2. ** -10) < 1e-15)
424:    check('mcnemar b=5,c=5 -> P(X>=5|10)', abs(mcnemar_one_sided(5, 5) - 0.623046875) < 1e-12)
425:    check('mcnemar two-sided symmetric', abs(mcnemar_two_sided(10, 0) - 2. ** -9) < 1e-15)
430:    check('crossing log-linear midpoint = 6.0', abs(x[0] - 6.0) < 1e-12 and st[0] == OK)
433:    check('crossing zero-FER floor 0.5/n', abs(x[0] - exp) < 1e-12 and st[0] == OK)
469:    check('H3 U300: B ~ C, ratio .5 -> PASS', c['H3']['label'] == 'PASS' and abs(c['H3']['quiet_time_ratio_B_over_C'] - .5) < 1e-9)
482:    # censored B (never reaches 1e-2): gain claim must not pass
486:    # F0 censored high (rho .5-like: F0 never reaches 1e-2 on the grid), B does: finite lower-bound gain
1:"""Execute the frozen Huang-2010-style steelman main run over all archived F0-triggered keys, then aggregate."""
48:    triggered_by_frame: dict[int, list[dict[str, Any]]],
61:            items = triggered_by_frame.get(frame, [])
77:                    if syn != int(item['syndrome']) or f0 != dict(
121:                        syndrome=int(syn),
122:                        triggered=True,
128:    print(f'Shard {shard_idx:03d} completed ({count} triggered keys)', flush=True)
203:    triggered_by_frame: dict[int, list[dict[str, Any]]] = {}
204:    n_triggered = 0
206:        if k[1] in retained_rhos and r['triggered']:
207:            triggered_by_frame.setdefault(k[3], []).append(r)
208:            n_triggered += 1
212:        f'{n_triggered} triggered keys (recipe={hg_recipe}, include_hgint={include_hgint}, rhos={retained_rhos}).',
222:            sub_trig = {f: triggered_by_frame.get(f, []) for f in frames}
255:    live_triggered: dict[tuple[str, int, int, int], dict[str, Any]] = {}
263:                if k in live_triggered:
264:                    raise RuntimeError(f'Duplicate live triggered row {k}')
265:                live_triggered[k] = row
267:    if len(live_triggered) != n_triggered:
268:        raise RuntimeError(f'Expected {n_triggered} triggered rows, got {len(live_triggered)}')
279:        if arch['triggered']:
280:            full_rows[k] = live_triggered[k]
285:                syndrome=0, triggered=False,
312:            triggered_keys=n_triggered,
313:            untriggered_keys=len(full_rows) - n_triggered,
experiments/rho_sweep_20261119/test_analysis.py:197:            triggered = len(set(counts.values())) > 1
experiments/rho_sweep_20261119/test_analysis.py:205:                    triggered=triggered, mechanism=diagnostic if triggered else None,
experiments/rho_sweep_20261119/test_mechanism.py:89:                triggered=diagnostic is not None, syndrome=int(diagnostic is not None),
experiments/rho_sweep_20261119/test_mechanism.py:126:    row['triggered'] = True
experiments/rho_sweep_20261119/test_mechanism.py:127:    with pytest.raises(ValueError, match='disagreement with syndrome'):
experiments/rho_sweep_20261119/test_mechanism.py:129:    row['syndrome'] = 1
experiments/rho_sweep_20261119/phase1b.py:49:        syndrome=0, triggered=False, mechanism=None,
experiments/rho_sweep_20261119/phase1b.py:50:        arms=dict(F0=row['arms']['F0'], A2=row['arms']['F0'], CD=row['arms']['CODELAY']))
experiments/rho_sweep_20261119/phase1b.py:57:    triggered = [key for key, row in stage.items() if row['syndrome']]
experiments/rho_sweep_20261119/phase1b.py:58:    live, _ = probe.evaluate(pool, triggered, probe.ARMS[1:], mechanism=True)
experiments/rho_sweep_20261119/phase1b.py:64:            if old['syndrome']:
experiments/rho_sweep_20261119/phase1b.py:69:                item.update(syndrome=row['syndrome'], triggered=True, mechanism=row['mechanism'],
experiments/rho_sweep_20261119/report_main.py:133:                  'Trigger percentages use all frames. Rescue and harm percentages use triggered frames. '
experiments/rho_sweep_20261119/report_main.py:157:                f"{cell['triggered']}/{cell['frames']} ({percent(cell['trigger_rate'])})",
experiments/rho_sweep_20261119/mechanism.py:84:    triggered = row['triggered']
experiments/rho_sweep_20261119/mechanism.py:85:    if type(triggered) is not bool or ('syndrome' in row and triggered != bool(row['syndrome'])):
experiments/rho_sweep_20261119/mechanism.py:86:        raise ValueError('Invalid trigger flag or disagreement with syndrome')
experiments/rho_sweep_20261119/mechanism.py:88:    if triggered != (diagnostic is not None):
experiments/rho_sweep_20261119/mechanism.py:91:    counter['triggered'] += triggered
experiments/rho_sweep_20261119/mechanism.py:96:        if not triggered:
experiments/rho_sweep_20261119/mechanism.py:121:    n, triggered = counter['frames'], counter['triggered']
experiments/rho_sweep_20261119/mechanism.py:125:        accepted = triggered - edits['no_edit']
experiments/rho_sweep_20261119/mechanism.py:130:            rescues=rescues, harms=harms, rescues_per_trigger=_rate(rescues, triggered),
experiments/rho_sweep_20261119/mechanism.py:131:            harms_per_trigger=_rate(harms, triggered),
experiments/rho_sweep_20261119/mechanism.py:138:    return dict(frames=n, triggered=triggered, trigger_rate=triggered / n, arms=by_arm)
experiments/rho_sweep_20261119/phase1.py:53:    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
experiments/rho_sweep_20261119/phase1.py:62:        if not syndrome:
experiments/rho_sweep_20261119/phase1.py:74:               syndrome=syndrome, triggered=bool(syndrome), u=u, n_symbols=len(variance),
experiments/rho_sweep_20261119/phase1.py:75:               truth=stage3.truth_record(obs, truth), inputs=stage3.input_record(raw, obs), arms=rows)
experiments/rho_sweep_20261119/phase1.py:78:        if syndrome:

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/unified_cov_prospective_20261119/cstate.py | sed -n '1,85p'; nl -ba experiments/sameframe_hg_20261124/sameframe.py | sed -n '409,428p;475,508p;879,923p'; git status --porcelain --untracked-files=normal -- experiments/{sameframe_hg_20261124,data_pilot_fer_20261121,huang_steelman_20261124,rho_sweep_20261119}" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
     1	"""Stage 3 continuation with trial-support spectral covariance."""
     2	
     3	import importlib.util
     4	import inspect
     5	from functools import lru_cache
     6	from pathlib import Path
     7	import sys
     8	import time
     9	from types import FunctionType, SimpleNamespace
    10	
    11	import numpy as np
    12	
    13	from projector import block_projector, low_projector
    14	
    15	STAGE3 = Path(__file__).resolve().parents[1] / 'cstate_codelay_sbl_stage3_20261118'
    16	sys.path.insert(0, str(STAGE3))
    17	spec = importlib.util.spec_from_file_location('stage3_codelay_run', STAGE3 / 'run.py')
    18	stage3 = importlib.util.module_from_spec(spec)
    19	spec.loader.exec_module(stage3)
    20	SPECTRAL_ARMS = ('U', 'C-hi', 'C-lo')
    21	ARMS = ('F0', 'A2', 'CD', *SPECTRAL_ARMS)
    22	TAU = .5
    23	
    24	
    25	def context():
    26	    return stage3.context()
    27	
    28	
    29	def _empty_census():
    30	    return dict(scored_trials=0, nonempty_scored_trials=0, valid_trials=0, nonempty_trials=0,
    31	                checked_trials=0, max_relative_score_error=0.)
    32	
    33	
    34	def _trial_projectors(delays, dopplers, slot, candidate_delays, candidate_dopplers, n, tau):
    35	    """Rebuild each changed co-delay block, retaining disjoint unchanged blocks."""
    36	    keep = np.flatnonzero(np.arange(len(delays)) != slot)
    37	    common = np.zeros((len(delays), len(delays)), dtype=complex)
    38	    common[np.ix_(keep, keep)] = low_projector(delays[keep], dopplers[keep], n, tau)
    39	    shape = (len(candidate_delays), *common.shape)
    40	    projectors = np.broadcast_to(common, shape).copy()
    41	    for delay in np.unique(delays[keep]):
    42	        rows = np.flatnonzero(candidate_delays == delay)
    43	        if not len(rows):
    44	            continue
    45	        members = keep[delays[keep] == delay]
    46	        # Match the per-support slot order used by _system at the threshold.
    47	        slots = np.sort(np.r_[slot, members])
    48	        block_dopplers = np.broadcast_to(dopplers[slots], (len(rows), len(slots))).copy()
    49	        block_dopplers[:, np.searchsorted(slots, slot)] = candidate_dopplers[rows]
    50	        projectors[np.ix_(rows, slots, slots)], _ = block_projector(block_dopplers, n, tau)
    51	    return projectors
    52	
    53	
    54	def _replace_spectrum(gamma, projector, total, arm):
    55	    if arm == 'U':
    56	        return gamma + total * projector
    57	    if arm == 'C-hi':
    58	        high = np.eye(gamma.shape[-1]) - projector
    59	        return high @ gamma @ high + total * projector
    60	    if arm == 'C-lo':
    61	        return projector @ gamma @ projector + total * (np.eye(gamma.shape[-1]) - projector)
    62	    raise ValueError(f'Unknown spectral covariance {arm}')
    63	
    64	
    65	def _reference_arm(arm, tau, total):
    66	    if arm in SPECTRAL_ARMS and (not tau or not total):
    67	        return 'A2' if arm == 'C-lo' else 'CD'
    68	    return arm
    69	
    70	
    71	def support_covariance(full, cd, v, delays, dopplers, c1, *, arm, tau=TAU):
    72	    """Actual covariance selected by the arm on a fresh support."""
    73	    system, mode = _support_system(full, cd, v, arm, tau)
    74	    gamma = system.__globals__['projected_variance'](v, delays, dopplers, c1)
    75	    return np.diag(np.diag(gamma)) if mode == 'diag' else gamma
    76	
    77	
    78	# Copy E-1 geometry_validation_variant.py::reopen_geometry to bind a new projector before each pass and check descent on that objective; the frozen interface lacks those callbacks.
    79	@lru_cache(maxsize=1)
    80	def _pass_code(reference):
    81	    source = inspect.getsource(reference)
    82	    guard = ('    if value > initial_value + 1e-8 * (1 + abs(initial_value)):\n'
    83	             '        raise AssertionError("frozen geometry objective increased")\n')
    84	    begins = '    for pass_index in range(local_passes):\n'
    85	    final = '    clock.enter("geometry_finalization")\n'
   409	def _select_balanced_keys(
   410	    keys_by_stratum: dict[tuple[int, str], list[tuple[str, int, int, int]]],
   411	    per_stratum: int,
   412	) -> list[tuple[str, int, int, int, str]]:
   413	    """Select balanced U/G and SNR-spread keys per (rho, band) deterministically."""
   414	    selected = []
   415	    for (rho, band), ks in sorted(keys_by_stratum.items()):
   416	        # Group by scenario and pick spread-out indices across sorted (snr, frame)
   417	        u_ks = sorted((k for k in ks if k[0] == 'U'), key=lambda k: (k[2], k[3]))
   418	        g_ks = sorted((k for k in ks if k[0] == 'G'), key=lambda k: (k[2], k[3]))
   419	        n_each = per_stratum // 2
   420	        picks = []
   421	        for pool in (u_ks, g_ks):
   422	            if len(pool) < n_each:
   423	                raise RuntimeError(f'Insufficient keys in stratum {(rho, band)}: {len(pool)} < {n_each}')
   424	            idxs = np.linspace(0, len(pool) - 1, n_each, dtype=int)
   425	            picks.extend(pool[int(i)] for i in idxs)
   426	        for s, r, snr, f in picks:
   427	            selected.append((s, r, snr, f, band))
   428	    return selected
   475	    # G1: 20 triggered stageA keys (5 per rho in 100..250, balanced U/G & SNR)
   476	    p1_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   477	    for k, v in stageA_base.items():
   478	        if v['syndrome'] != 0:
   479	            band = 'low' if k[2] <= 400 else 'mid'
   480	            p1_strata.setdefault((k[1], band), []).append(k)
   481	    g1_jobs = []
   482	    for rho in PART1_RHOS:
   483	        trig = sorted(p1_strata[(rho, 'low')] + p1_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   484	        idxs = np.linspace(0, len(trig) - 1, 5, dtype=int)
   485	        for i in idxs:
   486	            s, r, snr, f = trig[int(i)]
   487	            v = stageA_base[(s, r, snr, f)]
   488	            g1_jobs.append([s, r, snr, f, v['syndrome'], v['f0_errors']])
   489	
   490	    # G3: 20 triggered rho_sweep keys across all 6 rhos (mix of CD pass-1 pass and fail)
   491	    p2_strata: dict[tuple[int, str], list[tuple[str, int, int, int]]] = {}
   492	    for k, r in rho_arch.items():
   493	        if r['triggered']:
   494	            band = 'low' if k[2] <= 400 else 'mid'
   495	            p2_strata.setdefault((k[1], band), []).append(k)
   496	    g3_jobs = []
   497	    for rho in ar.RHOS:
   498	        all_r = sorted(p2_strata[(rho, 'low')] + p2_strata[(rho, 'mid')], key=lambda k: (k[0], k[2], k[3]))
   499	        fails = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) > 0]
   500	        passes = [k for k in all_r if int(rho_arch[k]['arms']['CD']['errors']) == 0]
   501	        picks = [fails[0], fails[len(fails) // 2], passes[0]] + ([passes[-1]] if rho in (200, 300) else [])
   502	        for k in picks:
   503	            cd_arch = rho_arch[k]['arms']['CD']
   504	            g3_jobs.append(dict(
   505	                key=list(k),
   506	                CD=dict(errors=int(cd_arch['errors']), decoded_sha=cd_arch['decoded_sha']),
   507	            ))
   508	    g3_jobs = g3_jobs[:20]
   879	        # Restrict best-rho range per arm: HG/HGint/HG1 over part1_rhos; others over their own grid (or <=200 for delay)
   880	        if arm == 'delay':
   881	            sub_idx = [i for i, r in enumerate(rhos) if r <= 200]
   882	        else:
   883	            sub_idx = list(range(n_r))
   884	        arm_best_lo[arm] = np.min(lo_arr[:, sub_idx], axis=1)
   885	        arm_best_hi[arm] = np.min(hi_arr[:, sub_idx], axis=1)
   886	        best_pos = int(np.argmin(hi_arr[0, sub_idx]))
   887	        arm_best_rho[arm] = int(rhos[sub_idx[best_pos]])
   888	
   889	    def contrast(arm_a: str, arm_b: str) -> dict[str, Any]:
   890	        # D = min_rho arm_a - min_rho arm_b (conservative bounds; collapses to exact diff when finite)
   891	        d_lo = arm_best_lo[arm_a] - arm_best_hi[arm_b]
   892	        d_hi = arm_best_hi[arm_a] - arm_best_lo[arm_b]
   893	        cens_frac = float(np.mean(~(np.isfinite(d_lo[1:]) & np.isfinite(d_hi[1:]))))
   894	        if cens_frac == 0.0:
   895	            lo, hi = (float(v) for v in np.percentile(d_lo[1:], [2.5, 97.5]))
   896	        else:
   897	            lo = an._nearest_rank(d_lo[1:], 0.025)
   898	            hi = an._nearest_rank(d_hi[1:], 0.975)
   899	        pt = _rep(d_lo[0]) if d_lo[0] == d_hi[0] else [_rep(d_lo[0]), _rep(d_hi[0])]
   900	        return dict(
   901	            point_db=pt,
   902	            ci95_db=[_rep(lo), _rep(hi)],
   903	            censored_draw_fraction=cens_frac,
   904	            arm_a_best_db=_rep(arm_best_lo[arm_a][0]) if arm_best_lo[arm_a][0] == arm_best_hi[arm_a][0] else [_rep(arm_best_lo[arm_a][0]), _rep(arm_best_hi[arm_a][0])],
   905	            arm_a_best_rho=arm_best_rho[arm_a],
   906	            arm_b_best_db=_rep(arm_best_lo[arm_b][0]) if arm_best_lo[arm_b][0] == arm_best_hi[arm_b][0] else [_rep(arm_best_lo[arm_b][0]), _rep(arm_best_hi[arm_b][0])],
   907	            arm_b_best_rho=arm_best_rho[arm_b],
   908	        )
   909	
   910	    primary_p1 = contrast('HG', 's100')
   911	    p1_lo = float(primary_p1['ci95_db'][0]) if isinstance(primary_p1['ci95_db'][0], float) else (-math.inf if primary_p1['ci95_db'][0] == '-inf' else math.inf)
   912	    p1_hi = float(primary_p1['ci95_db'][1]) if isinstance(primary_p1['ci95_db'][1], float) else (-math.inf if primary_p1['ci95_db'][1] == '-inf' else math.inf)
   913	    primary_p1['verdict'] = p1_verdict(p1_lo, p1_hi)
   914	
   915	    sec_contrasts = {}
   916	    for comp in ('s050', 'ldop', 'full', 'delay', 'base'):
   917	        if comp in fail_by_arm:
   918	            sec_contrasts[f'HG_minus_{comp}'] = contrast('HG', comp)
   919	    sec_contrasts['HG1_minus_s100'] = contrast('HG1', 's100')
   920	    if include_hgint and 'HGint' in fail_by_arm:
   921	        for comp in ('s100', 's050', 'ldop', 'full', 'HG'):
   922	            if comp in fail_by_arm:
   923	                sec_contrasts[f'HGint_minus_{comp}'] = contrast('HGint', comp)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-UfkYzOx9' (errno=Operation not permitted)
?? 00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/

exec
/bin/zsh -lc "rg -n 'retained|HGint|18,009|18009' experiments/huang_steelman_20261124/READOUT.md | head -18; rg -n '"'^def decoder_messages|raw_check_extrinsic|raw_app'"' experiments/sp_afdm_frozen_20260920/src | head -24; nl -ba experiments/huang_steelman_20261124/run_main.py | sed -n '75,126p'; nl -ba experiments/huang_steelman_20261124/hs_arms.py | sed -n '198,214p'; nl -ba experiments/tcom_reference_frame_20261015/p1_agg.py | sed -n '78,104p'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
7:  - 24 shards (`rows_shard000.jsonl`..`rows_shard023.jsonl`, 18,009 triggered rows total): MD5 manifest in [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt) and `summary.json._config.raw_rows_md5`
10:  - Gates G1–G4: `PASS` (`0.3294` core-hours), selecting `HG` recipe `B0-p2-s0.5`, retaining `HGint` and all 6 $\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$.
18:All numbers below come directly from [summary.json](out/summary.json) (62,400 total keys across 400 physical frames `5400–5799`, scenarios U/G, 6 $\rho$, 13 SNRs; 18,009 archived F0-triggered keys; 50,000 paired physical-frame bootstrap draws, seed `20261124`; Bonferroni $\alpha = 0.05/3$, 98.33% CIs for primary Q1/Q2/Q3; 95% CIs for secondary contrasts). Positive difference means `CD` requires lower SNR (better); negative means the comparator requires lower SNR.
30:| $\rho$ | `F0` | `CD` | `Z` | `HG1` (1-pass) | `HG` (2-pass) | `HGint` (2-pass coarse) | `HG − CD` (95% CI) |
39:- **Point optimal $\rho$**: `F0` = `0.40`, `CD` = `0.30`, `Z` = `0.30`, `HG1` = `0.30`, `HG` = **`0.20`**, `HGint` = **`0.20`**.
43:  - `HGint − HG`: **+0.0946 dB** `[−0.3182, +0.2704]` (coarse integer grid `[-2..2]` loses < 0.10 dB relative to the fine `0.25`-step grid).
44:  - `HGint − CD`: **−0.5587 dB** `[−0.8494, −0.2677]` (coarse integer-grid 2-pass `HGint` also beats `CD` by 0.56 dB).
47:### 1.3 Paired Rescues, Pass-2 & Support Diagnostics (18,009 Triggered Keys)
51:- **`HG` pass-2 diagnostics**: pass-1 early stop on `6,142 / 18,009` (`34.11%`); pass-2 ran on `11,867`, rescued `1,704` frames (`0` FER-harmed observed; note early stopping checks syndrome = 0 while FER scores information bits), bit-improved `7,711`, bit-worsened `3,405`.
68:| `HGint` | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× | 311.33 (1.025×) |
78:   - **Pre-registered meaning for the paper**: The published-style two-pass global OMP steelman (`HG`) beats local exchange (`CD`) on 1% FER accuracy. Even stronger, the coarse integer-grid variant (`HGint`) also beats `CD` (`−0.5587 dB [−0.8494, −0.2677]`) at nearly identical runtime (`1.066×` median per-trigger, `1.025×` amortized full-frame). Therefore, **local exchange (`CD`) cannot be framed as accuracy-superior or Pareto-dominant over Huang-2010-style data-aided global OMP re-acquisition** on this regime.
86:- **H-grid predictions**: **Not matched** (`HGint − HG = +0.0946 dB [−0.3182, +0.2704]` best-vs-best; `HGint − CD = −0.5587 dB [−0.8494, −0.2677]`).
96:3. **Why `HGint` captures almost all of `HG`'s gain at 1.07× `CD` latency [Confidence: H]**: Shrinking the OMP dictionary from 2,575 columns (`0.25` step on `[-3, 3]`) to 515 columns (`-2..2` integer grid, **1/5 the dictionary size**) still places atoms near the integer Doppler bin, after which `time_refine(mode='soft', max_paths=8, rounds=2)` performs continuous off-grid Doppler refinement; testing `HGint` without `time_refine` would be needed to confirm this separation.
97:4. **Why `Z` ($\Gamma = 0$) is equivalent to `CD` on 1% FER [Confidence: M]**: Earlier comparisons on the same `rho_sweep_20261119` archive contrasted `CD` against *diagonal* $\Gamma$ (`A2`), where `A2 − CD` was `+0.7864 dB` at $\rho=.30$ and `+1.3394 dB` at $\rho=.25$ ([rho_sweep RESULTS.md](../rho_sweep_20261119/out/main_20261119/RESULTS.md)) due to scalar/diagonal phantom-admission bias. Zeroing $\Gamma$ removes that diagonal phantom-admission bias altogether, leaving only a `0.0501 dB` (`+249` vs `+93` rescues on 18,009 keys) difference from the exact co-delay block covariance `CD` — a much smaller gap than previously seen against `A2`.
experiments/sp_afdm_frozen_20260920/src/receiver.py:40:            app=np.asarray(ctl.records[-1]['raw_app']);timeline.append(dict(iteration=iteration,ready_absolute=time.perf_counter(),decoded=(app<0).astype(np.uint8)))
experiments/sp_afdm_frozen_20260920/src/receiver.py:59:        arrays.update(final_llr=r['llr'],final_input=dec['incoming_llr'],final_app=dec['raw_app'],final_check=dec['raw_check_extrinsic'],final_detector_hard=r['x_hard'],final_detector_mu=r['mu'],final_detector_variance=r['var'])
experiments/sp_afdm_frozen_20260920/src/receiver.py:64:        dec=decoder_messages(code,np.clip(state['channel_llr'],-20,20),maxiter=50);prior=np.clip(dec['raw_check_extrinsic'],-20,20);mu,v,_=moments(np.clip(dec['raw_app'],-20,20),.5)
experiments/sp_afdm_frozen_20260920/src/receiver.py:66:        events.append(dict(stage='fresh_decoder',iterations=int(dec['iterations']),metadata=dec['metadata']));arrays.update(refresh_input=dec['incoming_llr'],refresh_app=dec['raw_app'],refresh_check=dec['raw_check_extrinsic'])
experiments/sp_afdm_frozen_20260920/src/receiver.py:104:    arrays.update(final_input=llr,final_app=dec['raw_app'],final_check=dec['raw_check_extrinsic'],final_detector_app=o['app'],final_detector_mu=o['mu'],final_detector_variance=o['variance'])
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
   198	
   199	def fine_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
   200	    """Global delay-Doppler grid matching CD resolution: l in 0..l_max_cap, nu in [-3, 3] step 0.25."""
   201	    dopplers = np.linspace(-3.0, 3.0, 25)
   202	    delays = np.arange(l_max_cap + 1, dtype=int)
   203	    return np.repeat(delays, len(dopplers)), np.tile(dopplers, len(delays))
   204	
   205	
   206	def coarse_grid(l_max_cap: int) -> tuple[np.ndarray, np.ndarray]:
   207	    """Original pilot_front integer Doppler grid: l in 0..l_max_cap, nu in {-2,-1,0,1,2}."""
   208	    dopplers = np.arange(-2, 3, dtype=float)
   209	    delays = np.arange(l_max_cap + 1, dtype=int)
   210	    return np.repeat(delays, len(dopplers)), np.tile(dopplers, len(delays))
   211	
   212	
   213	def _require_finite(arr, label: str):
   214	    if not np.isfinite(arr).all():
    78	def crossing(fer, n, snr, target=TARGET):
    79	    """fer (R, S) with snr ascending; returns x (R,) clipped to the grid and status (R,) in {OK, LOW, HIGH}."""
    80	    fer = np.atleast_2d(fer)
    81	    R, S = fer.shape
    82	    snr = np.asarray(snr, float)
    83	    below = fer <= target
    84	    has = below.any(1)
    85	    j = below.argmax(1)
    86	    status = np.zeros(R, int)
    87	    status[~has] = HIGH
    88	    status[has & (j == 0)] = LOW
    89	    x = np.where(status == HIGH, snr[-1], snr[0])
    90	    idx = np.flatnonzero(has & (j > 0))
    91	    if idx.size:
    92	        jj = j[idx]
    93	        f = np.where(fer == 0, .5 / n, fer)
    94	        y0, y1, yt = np.log10(f[idx, jj - 1]), np.log10(f[idx, jj]), math.log10(target)
    95	        res = (fer[idx, jj] == 0) & (y1 >= yt)  # zero-FER floor above the target: resolution-limited
    96	        t = np.where(res, 1., (yt - y0) / np.where(res, 1., y1 - y0))
    97	        x[idx] = snr[jj - 1] + t * (snr[jj] - snr[jj - 1])
    98	    return x, status
    99	
   100	
   101	def diff_gain(xa, sa, xb, sb):
   102	    """H1 gain = x_a - x_b (a = F0, b = B); lower-bound claim: -inf where clipping could inflate it."""
   103	    d = xa - xb
   104	    return np.where((sa == LOW) | (sb == HIGH), -np.inf, d)

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "nl -ba experiments/rho_sweep_20261119/phase1.py | sed -n '46,78p'; nl -ba experiments/huang_steelman_20261124/hs_arms.py | sed -n '71,106p'; rg -n 'numerical_fallback=' experiments/tf_cstate_e1_20261017/geometry_validation_variant.py; rg -n 'write|Log|error' experiments/sameframe_hg_20261124/PROTOCOL.md | tail -6" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
    46	# the frozen return omits the F0 symbol moments needed to log u on every key.
    47	def run_key(base, key, arms, *, mechanism=False):
    48	    from messages import moments
    49	
    50	    s, rho, snr, frame = key
    51	    start = time.process_time()
    52	    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    53	    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
    54	    f0 = dict(**stage3.decoded(ctx, dec, truth), first_edit_type=None, state=None, decision=[])
    55	    _, variance, _ = moments(np.clip(arrays['r1_app'], -20, 20), 1 - ctx.system.rho)
    56	    u = float(variance.sum())
    57	    rows = {'F0': f0}
    58	    if mechanism and set(arms) != set(BRANCHES):
    59	        raise ValueError('The mechanism diagnostic requires both continuation arms')
    60	    first_traces = {}
    61	    for arm in arms:
    62	        if not syndrome:
    63	            rows[arm] = f0
    64	            continue
    65	        branch = stage3.e1.run_branch(ctx, full if arm == 'A2' else cd, obs, arrays,
    66	                                      'A2' if arm == 'A2' else 'A1')
    67	        if not np.array_equal(branch['ce_variance'], variance):
    68	            raise AssertionError(f'{key} {arm}: branch moments differ from the F0 moments')
    69	        rows[arm] = dict(**stage3.decoded(ctx, branch['decoder'], truth),
    70	                         **cstate._geometry_record(branch['result']))
    71	        if mechanism:
    72	            first_traces[arm] = branch['result'].global_trace[0]
    73	    row = dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame,
    74	               syndrome=syndrome, triggered=bool(syndrome), u=u, n_symbols=len(variance),
    75	               truth=stage3.truth_record(obs, truth), inputs=stage3.input_record(raw, obs), arms=rows)
    76	    if mechanism:
    77	        row.update(mechanism=None, mechanism_cpu_seconds=0.0)
    78	        if syndrome:
    71	def verify_freeze_commit_if_git(freeze_commit: str, live_own_md5: dict[str, str]) -> bool:
    72	    """When running inside a git checkout, verify freeze_commit exists and its own blobs match live_own_md5."""
    73	    import subprocess
    74	
    75	    repo_root = EXPERIMENTS.parent
    76	    probe = subprocess.run(
    77	        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
    78	        capture_output=True, text=True, check=False,
    79	    )
    80	    if probe.returncode != 0 or probe.stdout.strip() != 'true':
    81	        return False
    82	    check_commit = subprocess.run(
    83	        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'{freeze_commit}^{{commit}}'],
    84	        capture_output=True, text=True, check=False,
    85	    )
    86	    if check_commit.returncode != 0:
    87	        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repository')
    88	    rel_dir = HERE.relative_to(Path(
    89	        subprocess.run(
    90	            ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
    91	            capture_output=True, text=True, check=True,
    92	        ).stdout.strip()
    93	    ))
    94	    for name, expected_md5 in live_own_md5.items():
    95	        blob = subprocess.run(
    96	            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
    97	            capture_output=True, check=False,
    98	        )
    99	        if blob.returncode != 0:
   100	            raise RuntimeError(f'freeze_commit {freeze_commit} missing committed file {name}')
   101	        got_md5 = hashlib.md5(blob.stdout).hexdigest()
   102	        if got_md5 != expected_md5:
   103	            raise RuntimeError(f'Live file {name} ({expected_md5}) differs from freeze_commit {freeze_commit} ({got_md5})')
   104	    return True
   105	
   106	
501:                       numerical_fallback=fallback_reason is not None,
29:  - **Caveat (explicitly recorded before running)**: `s050` and `s100` are Gaussian Doppler injections that **also assume true delays**; Stage A3 previously showed that real pilot Doppler error hurts less than i.i.d. Gaussian error of the same mean, while unknown delays in a real semi-blind estimator add extra loss. Therefore the `s100` threshold is a structured proxy (strict on Doppler noise shape, optimistic on true delays), not a real end-to-end estimator.
34:    - `CD2`: Pass 1 calls `stage3.e1.run_branch(ctx, cd, obs, arrays, 'A1')` and asserts exact bit-parity (`errors` and `decoded_sha`) with archived `CD` on every key. If pass-1 `syndrome != 0`, Pass 2 calls `run_branch(..., 'A1')` on updated arrays (`r1_delays`, `r1_dopplers` from `result.paths`; `r1_gains = result.gains`; `r1_check = decoder['raw_check_extrinsic']`; `r1_app = decoder['raw_app']`, identical to `HG`'s inter-pass message update rule). Early stop on `syndrome == 0`.
43:- **G1 (Part-1 F0 replay parity)**: On 20 triggered `stageA` keys (5 per $\rho \in \{100, 150, 200, 250\}$, balanced across U/G and low/mid SNR), live `f0_state` reproduces `arms.base.syndrome` and `arms.base.f0_errors` identically (20/20).
44:- **G2 (HG wrapper parity)**: On 5 archived `huang_steelman_20261124` triggered keys (spanning U/G and 1-pass + 2-pass stops), calling `hs_arms.run_hg_arm` through the `stageA.setup()` context reproduces archived `HG` and `HG1` `errors` and `decoded_sha` bit-exactly (5/5).
45:- **G3 (CD2 pass-1 parity + CD2/CD2e8 smoke)**: On 20 archived `rho_sweep_20261119` triggered keys (spanning U/G and all 6 $\rho$, including pass-1 failures), `CD2` pass 1 reproduces archived `CD` `errors` and `decoded_sha` bit-exactly (20/20); both `CD2` pass 2 and `CD2e8` execute cleanly with finite outputs and zero `numerical_fallback`.
97:- Thread & scratch isolation: `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `BLIS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, `CUDA_VISIBLE_DEVICES=""`, `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR=/data/guoyikun/tmp`, `XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`. Never write to `/tmp` or `/home/guoyikun`.

hook: PreToolUse
hook: PreToolUse Completed
exec
/bin/zsh -lc "python3 -B - <<'PY'
import ast, hashlib
from pathlib import Path
root = Path('experiments')
mod = ast.parse((root/'huang_steelman_20261124/hs_arms.py').read_text())
expected = next(ast.literal_eval(n.value) for n in mod.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FROZEN_EXTRA_MD5' for t in n.targets))
for name, digest in expected.items():
    actual = hashlib.md5((root/name).read_bytes()).hexdigest()
    print('OK' if actual == digest else f'MISMATCH {actual} "'!= {digest}'"', name)
PY
bash -n experiments/sameframe_hg_20261124/launch.sh" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
zsh:1: can't create temp file for here document: operation not permitted

hook: PreToolUse
hook: PreToolUse
hook: PreToolUse Completed
hook: PreToolUse Completed
exec
/bin/zsh -lc 'bash -n experiments/sameframe_hg_20261124/launch.sh' in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
exec
/bin/zsh -lc "python3 -B -c 'import ast,hashlib,pathlib; r=pathlib.Path(\"experiments\"); m=ast.parse((r/\"huang_steelman_20261124/hs_arms.py\").read_text()); h=next(ast.literal_eval(n.value) for n in m.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==\"FROZEN_EXTRA_MD5\" for t in n.targets)); print({p:hashlib.md5((r/p).read_bytes()).hexdigest()==d for p,d in h.items()})'" in /Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation
 succeeded in 0ms:
{'cstate_codelay_sbl_stage3_20261118/run.py': True, 'cstate_codelay_sbl_stage3_20261118/codelay.py': True, 'tf_cstate_e1_20261017/e1_driver.py': True, 'tf_cstate_e1_20261017/geometry_validation_variant.py': True, 'tf_cstate_e1_20261017/geometry_reopen_variant.py': True, 'gamma0_exchange_20261120/paired.py': True, 'tcom_reference_frame_20261015/p1_agg.py': True}

codex
**先修再启动。** 静态核对确认，两部分都复用了指定的上游实现。第一部分按归档触发并核对实时 F0 的校验值和错误数。第二部分逐键核验 `CD2` 首遍的错误数和译码哈希，正确传递五项状态并按校验通过提前停止。两组主比较的置信区间和判定阈值与协议一致。

- **G3 可能漏测第二遍。** 样本按首遍信息位错误数选取，实际续跑由校验值决定。门禁只数返回行数，未断言 `CD2` 和 `CD2e8` 都跑过第二遍，第二遍也漏查了两组原始译码消息是否有限。G1 同样未强制覆盖两种场景和两个信噪比分段。[门禁取样与判定](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:475)
- **G4 的降级顺序和 30% 余量正确，但 12 核时上限执行不完整。** 第二部分每个场景和分层固定取最低信噪比的首帧，再外推整个分层的成本。正式运行每 10 秒检查一次，汇总则写完结果才查预算，而且记录的总核时漏掉了汇总本身。[成本取样](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:409) · [预算检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:1367)
- **门禁和归档校验存在绕过路径。** 门禁重跑异常时会留下旧的通过记录，正式运行仍可接受它。冻结提交只校验字符串格式。Stage A 系列和 Huang 归档先校验清单，随后用通配符读取，额外分片可未经校验进入分析。[正式运行门禁](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:1284) · [归档读取](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:1139)
- **读出有两处范围偏差。** 丢弃 `ρ=250` 后，主表仍写 `HG (100..250)`。`full` 和 `ldop` 的次要对比把 `ρ=50` 纳入最小值，而协议写的是沿用主比较的 `100..200` 范围。[最小值与报告范围](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:879)

启动脚本语法检查通过。工作目录、解释器、单线程、禁用显卡、临时目录和启动器的进程数设置符合要求。核对了本地五份归档清单和七个固定依赖的哈希。远端门禁、单元测试和共享内存行为未实跑。

VERDICT: FIX
hook: Stop
hook: Stop Completed
tokens used
113,892
**先修再启动。** 静态核对确认，两部分都复用了指定的上游实现。第一部分按归档触发并核对实时 F0 的校验值和错误数。第二部分逐键核验 `CD2` 首遍的错误数和译码哈希，正确传递五项状态并按校验通过提前停止。两组主比较的置信区间和判定阈值与协议一致。

- **G3 可能漏测第二遍。** 样本按首遍信息位错误数选取，实际续跑由校验值决定。门禁只数返回行数，未断言 `CD2` 和 `CD2e8` 都跑过第二遍，第二遍也漏查了两组原始译码消息是否有限。G1 同样未强制覆盖两种场景和两个信噪比分段。[门禁取样与判定](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:475)
- **G4 的降级顺序和 30% 余量正确，但 12 核时上限执行不完整。** 第二部分每个场景和分层固定取最低信噪比的首帧，再外推整个分层的成本。正式运行每 10 秒检查一次，汇总则写完结果才查预算，而且记录的总核时漏掉了汇总本身。[成本取样](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:409) · [预算检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:1367)
- **门禁和归档校验存在绕过路径。** 门禁重跑异常时会留下旧的通过记录，正式运行仍可接受它。冻结提交只校验字符串格式。Stage A 系列和 Huang 归档先校验清单，随后用通配符读取，额外分片可未经校验进入分析。[正式运行门禁](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:1284) · [归档读取](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:1139)
- **读出有两处范围偏差。** 丢弃 `ρ=250` 后，主表仍写 `HG (100..250)`。`full` 和 `ldop` 的次要对比把 `ρ=50` 纳入最小值，而协议写的是沿用主比较的 `100..200` 范围。[最小值与报告范围](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sameframe_hg_20261124/sameframe.py:879)

启动脚本语法检查通过。工作目录、解释器、单线程、禁用显卡、临时目录和启动器的进程数设置符合要求。核对了本地五份归档清单和七个固定依赖的哈希。远端门禁、单元测试和共享内存行为未实跑。

VERDICT: FIX
