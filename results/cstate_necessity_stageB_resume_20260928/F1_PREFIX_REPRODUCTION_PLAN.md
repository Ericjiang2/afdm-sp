# One faithful Stage-B process-prefix reproduction (not yet executed)

Purpose: test the only identified missing condition in earlier non-reproductions—the complete B/Cref/Cfast process history before the stopped `s650_f0197` fast call. The original attempt reached call 409 in 181.05 s. This is **one** separately registered diagnostic allocation, at most **409 complete wrappers / 300 s**. It uses existing observed frames 0–197, no truth or new observations, and stops at the first parity/integrity/numerical failure. No retry, parameter change, tolerance relaxation, or F2 call.

`f1_prefix_reproduce.py` verifies the exact original `f1_run_stage_b.py` SHA `fc1ed8087533f916d5892764f1a04d15168bf52c37ec4f83178de773ab7c1566` and original Stage-B registration SHA `3de51a884015d39deec052efd932e92cd40e0e951b4ea6b76c8eb090acafd85b`. It parses the frozen source as AST and requires these **five whitelisted sites** at their frozen line numbers before compiling in memory:

| Site | Sole diagnostic change |
| --- | --- |
| running manifest, line 193 | mark diagnostic schema; expected calls 2112→409, reference subset 64→13; add diagnostic-manifest SHA |
| population loop, line 214 | `enumerate(bound['selected'])` → `enumerate(bound['selected'][:198])` |
| attempt guard, line 219 | `calls > 2112` → `calls > 409` |
| completion count, line 381 | `calls != 2112` → `calls != 409` |
| successful ending, line 385 | write `diagnostic_prefix.json`, status `diagnostic-prefix`, 198 observations/409 calls/13 reference subset and diagnostic-manifest SHA; **never write `observed_seal.json`** |

All other original source, imports, preflight, `schedule(index)`, per-arm fresh receiver calls, B conditional CSTATE, Cref/Cfast native TF/LDPC, raw/checkpoint/decision serialization, historical B/C parity gates, failure journal, and failure stop remain unchanged. Frame indices divisible by 16 give 13 Cref calls; 198 B + 198 Cfast + 13 Cref = 409. The original registration still declares 2112; the separate diagnostic manifest binds adapter/launcher/original source bytes, five AST sites, original commit, allocation, and 300 s hard cap. The manifest and its actual Git blob must be reviewed and frozen before remote use.

`f1_prefix_launch_once.sh` uses one idle CPU, one thread, hidden CUDA, task-local `/data/guoyikun` scratch, and GNU timeout 295+5 s. The adapter also has an in-process 295 s alarm. It records argv/start/exit and does not resume an existing output. The output is a diagnostic prefix, not a sealed 1024-frame population or qualified F1 timing result. If the old 1002 counter appears, preserve the first failed raw/ledger/CP and compare only saved evidence; if it does not, record the one-round non-reproduction and stop further acquisition diagnostics pending a new cause-specific plan. The original invalid-partial Stage-B record stays immutable.
