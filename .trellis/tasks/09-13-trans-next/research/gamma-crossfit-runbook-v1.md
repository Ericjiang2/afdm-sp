# Γ crossfit 离线补充：单次运行合同

本脚本只读取已审计的 N1024 UWA 16A/64F 和原始 NPZ。目标物理信道的完整四条件、九 CE 状态不进入其 Γ 训练折；每折使用另外15个信道在同一 pilot/SNR/t 的误差。每状态建立一个固定 `C(mu)`，然后对固定索引0–39的实部±0.5候选做两次候选协方差计算。全程128折、128个固定协方差、10240个候选协方差、5120个候选差。信道0/1的640差是同一次运行内的工程门，不重复收费。

冻结 `gamma-crossfit-scope-v1.json`、本脚本和 `ce_synthesis_offline_v1.py` 的 SHA 后，运行前设置 `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=VECLIB_MAXIMUM_THREADS=1`，并把 `PYTHONPATH` 设为 scope 内的 `analysis_source_directory`。输出必须为原始 `outputs_ce_state_20260915` 根目录下全新目录，不覆盖既有结果。

```sh
python gamma_crossfit_v1.py --mode run --root /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_ce_state_20260915 --output-dir /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_ce_state_20260915/gamma-crossfit-v1 --scope gamma-crossfit-scope-v1.json --scope-sha256 <冻结scope SHA> --script-sha256 <冻结script SHA>
python gamma_crossfit_v1.py --mode audit --root /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_ce_state_20260915 --output-dir /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_ce_state_20260915/gamma-crossfit-v1 --scope gamma-crossfit-scope-v1.json --scope-sha256 <冻结scope SHA> --script-sha256 <冻结script SHA>
```

运行前 Linux `/proc/meminfo` 的 `MemAvailable` 须至少8GiB，保守过程峰值估算4GiB；运行中 `VmHWM` 与新增磁盘分别不得超过20GiB。内存预检值及过程峰值保存在 `summary.json`。

`run` 先验证 NSIZE 两阶段 summary/raw audit、16个物理 A 和64个 F 的原始哈希，再开始比较。`folds/*.npz` 保存15训练误差、均值和低秩因子；`folds.json` 保存训练 ID、来源和排除的目标条件；`comparisons.jsonl` 每行保存源 SHA、候选、六个原始分数标量、三项差分和符号选择；`evaluation.json` 只在全部候选分数落盘后用目标真数据评估实部错误；所有物理 H 预先载入作为其他目标的校准库，每个目标折与评分不消费自身 H/data；`summary.json` 是成本与源绑定。`audit` 重读原始 NPZ 和已存结果，重算128折数组、5120行标量闭合和离线真比特计数，**不重算候选协方差分数**；这些 audit 数学调用单独记录。异常留下 `failure.json`，不能把部分结果当完整结果。

Γ 来自其他信道真 H 的离线投影，属于 oracle 校准；目标的 `mu/g_solution/support` 仍依赖同一帧 `y`。评分定义省略候选先验，proper complex 模型忽略伪协方差。保存的 `||H-P_DH||_F²` 只度量字典表示尾项，不包含尾项候选响应或其他软数据误差。只报告这16个物理信道、固定候选下的离线实部选择与三项差分；不写 FER、CONF、真实后验或部署收益结论。
