# CORE-03 / WIRE-01 最小真实 CLI smoke（只读命令研究）

2026-09-06。本报告未启动任何命令所述作业、未访问validation/Dtest、未修改代码/CSV。以下按当前入口静态读取得到，主会话仍在恢复实现，发车前应以最终源码复核。没有声称下面新direct40 smoke已经通过。

## 最小可行顺序与硬依赖

1. N1024、2帧固定manifest prior pilot，验证真实信道/IID QPSK/nomination40/full labels/断点恢复产物；该CLI默认CPU，不执行BP/LDPC。
2. 独立A0单臂coded smoke，无需prior，但仍需真实C2-rel checkpoint。`--arms a0`才是当前合法名称。
3. 冻结400帧完整prior后，`--arms a0 baseline`跑同2帧coded smoke。`baseline`是当前CLI中A2对应臂；没有`a2`选项。2帧prior不能给A2使用，`load_prior`严格要求400帧，禁止放宽或填充缓存伪造通过。

当前 `decision_harvest.py:553–584` 没有 `--device` 参数，调用run_harvest默认`device='cpu'`。CPU prior不是GPU receiver smoke；不得写成“GPU harvest完成”。可用4个BLAS线程，但须按OPS登记和实际空闲资源调整。

checkpoint历史记录来自 `.trellis/tasks/09-06-minimal-repair-mechanism/research/runtime/capacity-smoke40/status.json`：

- 路径 `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk`
- SHA256 `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`
- 历史环境 `/home/guoyikun/.conda/envs/AFDM/bin/python`，PyTorch `2.5.1+cu121`。
- 本地不存在该checkpoint，故未执行strict load兼容验证，也未确认远端当前仍存在；发车前要只读核对路径/hash。

`budgeted_support_eval.py:64–79`始终按C2-rel构造，仅`cand_active_rel` head；从checkpoint读取pair_hidden/scorer_hidden（默认16），然后strict load。direct40只改nomination容量，不改这些权重形状。A0也装载checkpoint，只在forward bypass候选修复。因此不能把无checkpoint的随机初始化当等价A0。

## 拟执行命令

这些命令供已有授权及资源登记后的主会话执行。先检查目标目录/进程与GPU归属，同步最终源码及GOV-03 manifest到以下远端工作树。输出目录名称是本报告建议的新名，未实际创建或远端检查；存在则不得覆盖。

```bash
AFDM_ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation
AFDM_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
AFDM_RUN="$AFDM_ROOT/outputs_budgeted_support_repair/direct40_wire_20260906"
AFDM_CKPT="$AFDM_ROOT/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk"
AFDM_MANIFEST="$AFDM_ROOT/issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/GOV-03-prior-manifest.json"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "$AFDM_ROOT"
```

准备2帧pilot manifest，只取冻结400帧的前两条，保留原schema/root/seed_rule；不会生成任何信道观测。pilot和正式run输出隔离。manifest验证器现在要求frame0开始的连续列表，因此不能擅自给pilot使用rep41或frame400。

```bash
"$AFDM_PY" - "$AFDM_MANIFEST" "$AFDM_RUN" <<'PY'
import json, sys
from pathlib import Path
from afdm_sp_joint_unrolled.decision_harvest import validate_prior_manifest
source, run = Path(sys.argv[1]), Path(sys.argv[2])
manifest = json.loads(source.read_text())
validate_prior_manifest(manifest, 400)
pilot = dict(manifest, frames=manifest['frames'][:2])
validate_prior_manifest(pilot, 2)
run.mkdir(parents=True, exist_ok=False)
(run/'prior-pilot-manifest.json').write_text(json.dumps(pilot, indent=2)+'\n')
PY
```

真实2帧prior pilot（无需checkpoint/LDPC）：

```bash
"$AFDM_PY" -u -m afdm_sp_joint_unrolled.decision_harvest \
  --snr 8 --n-frames 2 --n-total 1024 --v-mean 2 --p-paths 8 \
  --tau-ms 10 --fs-factor 4 --rho 0.5 --M 96 --p-pad 64 \
  --nomination-cap 40 --print-every 1 \
  --frame-manifest "$AFDM_RUN/prior-pilot-manifest.json" \
  --out "$AFDM_RUN/prior-pilot2"
```

正式400帧prior（固定ID、失败不得补抽）：

```bash
"$AFDM_PY" -u -m afdm_sp_joint_unrolled.decision_harvest \
  --snr 8 --n-frames 400 --n-total 1024 --v-mean 2 --p-paths 8 \
  --tau-ms 10 --fs-factor 4 --rho 0.5 --M 96 --p-pad 64 \
  --nomination-cap 40 --print-every 1 \
  --frame-manifest "$AFDM_MANIFEST" \
  --out "$AFDM_RUN/prior400"
```

旧`--seed-base`在fixed manifest分支不决定实际逐帧seed，因此不必另设根整数；实际seed只能来自manifest。pilot两帧与正式前两帧重复计算属于工程先导费用，不能额外计成独立402帧prior。两个manifest/frame数不同，当前resume provenance不允许直接把pilot目录当400帧目录继续。

A0无prior、真实N1024 coded smoke：沿用历史smoke专用split2/rep997/frame0…1，明确标记工程重放，不属于fit/validation。与旧smoke相同物理身份使工程比较更容易。GPU选择须沿用主会话登记的CUDA_VISIBLE_DEVICES，下面不猜测GPU编号。

```bash
"$AFDM_PY" -u -m afdm_sp_joint_unrolled.budgeted_support_eval \
  --ckpt "$AFDM_CKPT" --snr 8 --replicate 997 --split cal \
  --start-frame 0 --frames 2 --n-total 1024 --device cuda \
  --receiver-shell direct40 --active-cap 40 --arms a0 \
  --out "$AFDM_RUN/a0-no-prior-smoke"
```

400帧prior完成且冻结后的A0/A2共同烟测：

```bash
"$AFDM_PY" -u -m afdm_sp_joint_unrolled.budgeted_support_eval \
  --ckpt "$AFDM_CKPT" --calibration "$AFDM_RUN/prior400/cache_snr8.pt" \
  --snr 8 --replicate 997 --split cal --start-frame 0 --frames 2 \
  --n-total 1024 --device cuda --receiver-shell direct40 --active-cap 40 \
  --arms a0 baseline --out "$AFDM_RUN/a0-a2-coded-smoke"
```

不要加`--uncoded`，否则明确跳过LDPC；不要用`keep`替代a0。不要把`--active-cap 40`单独使用：缺少direct40仍是legacy cluster-expansion模式。receiver输出目录必须不存在，因为CLI使用`mkdir(exist_ok=False)`；失败续跑应使用主会话认可的恢复入口/新输出名，不能盲目重用既有目录。

## 实际末端消费者和验收证据

当前源码链：CLI `:305,328–332` → `build_receiver :352–353` → `run_frame`容量解析 `:105–107` → receiver `:198` → `H_est :199` → 末次BP `:202–203` → demap `:204` → LDPC `:208`。最后BP是20迭代、threshold1e-4、damp0.5；LDPC maxiter50。内部outer是10轮、每轮BP20迭代、动态sigma2，soft decisions开启。a0-only在`:112`跳过runner OMP/H0/scorer准备；混合批次为A2准备scorer，A0仍须forward显式bypass。

LDPC由 `e1_ldpc.py:110–165` 的纯NumPy实现提供，不依赖pyldpc。N1024固定 n2048,dv3,dc6,seed20260726，缓存默认在模块目录；runner `:354–355`创建/读取并记录hash。历史缓存hash为 `7be530177c11b398d4f362ae81a663e83dd03de0ffdcd9bf2dd42eb1418f08be`。若缓存缺失会真实构建并原子保存；须将它记录为setup，不混入receiver时间。内容相同的npz重新打包可能字节hash变化，需要核对内部H/G/free_cols等，而不能仅凭seed宣称字节一致。

最小验收：prior cache完整schema/full-label/config与manifest hash验证通过、400身份无缺失；a0-only calibration记录unused且scorer准备时间0；每帧support ledger显示nomination40/extension0，各outer及最终唯一ID≤40；frames两条且finite；coded `info_errors`/`decode_ok`存在；末次H_est确实被BP/LDPC消费。`decode_ok=false`是合法科学失败，不等于工程崩溃，不得删除失败帧。支持bypass调用计数与末端参数插桩仍需主会话契约测试，status complete本身不能证明它们。

该2帧烟测只用于入口/数值/配置接线，不足以支持FER改善或正式统计结论。
