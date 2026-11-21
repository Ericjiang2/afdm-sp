# CPU 重复性恢复调查 — 2026-09-06

结论：已实测定位一个上游数值漂移来源：CPU `torch.linalg.lstsq` 默认 `gelsy` 对相同、未修改的 complex64 输入，重复调用可产生不同解。漂移发生在软反馈观察器之前的 OMP 阶段。因此，CPU 观察器哈希门失败不能归因于观察器。未证明这是所有最终 H/x 漂移的唯一来源；未定位 LAPACK 内部机制，也未修改生产求解器。

## 既有证据恢复

远端 S2 根目录：`/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s2_20260906`。
读取 `soft-cpu-repeat-investigation.json`；根目录未发现旧 probe/lstsq 探针结果。该记录同一帧运行顺序为 control/control/observed/control/observed：对照之间已出现 H 相对差 `4.0166e-7` 至 `1.3508e-6`，x 相对差 `4.2994e-7` 至 `1.1826e-6`，全部 raw/info errors 为 `314/119`。

## 探针约束和方法

- 冻结代码 `source-v4`，原 checkpoint，SNR 8 Dcal 缓存；Ddev `replicate=998, frame=0`，N=1024。
- deinlab，PyTorch `2.5.1+cu121`；`CUDA_VISIBLE_DEVICES=''`，CPU affinity 48–51，OMP/OPENBLAS 4。未占 GPU，未写远端代码/数据文件。
- 通过 SSH stdin 执行临时 Python，SSH keepalive 30 秒。第一探针 `timeout 60`，第二探针 `timeout 30`；实际 Python 内计时分别 `2.5963 s`、`1.4754 s`。两探针退出码均为 0。
- 第一探针只处理上述一帧 baseline，无观察器。包装 `torch.linalg.lstsq`：原始参数连续求解两次，比较 solution；接收器仍返回第一次原始结果。总共 37 个调用位置，33 个位置立即复算不逐位相同。
- 第二探针捕获 OMP 第一次 1024×2 输入，在进入后续接收器前退出。固定同一 A/b 张量，对各驱动及线程数执行 20 次求解；前后 A/b SHA256 完全相同。

首个差异：`classical_joint_unrolled.py:145` 的 `omp_sparse_torch`，由冻结源码 `forward:1564` 调用；A 为 1024×2 complex64。两次 rank 均为 2，解相对范数差 `4.4485784656e-7`。该帧所有 37 个比较的 rank 均一致；最大解相对差 `1.2281669797e-6`。漂移也出现在最终 OMP 重拟合、F2P 重拟合、`decision_gateA._resid_geom` 的同输入求解中。

第一探针最终 raw/info errors 仍为 `314/119`。这是单帧诊断，不能用于总体 FER 稳定性结论。

## 冻结算子重复结果

| 线程数 | driver | 20 次 solution 唯一哈希数 | 相对首解最大差 |
|---:|---|---:|---:|
| 4 | 默认 | 3 | 1.6632259303e-7 |
| 4 | gelsy | 2 | 1.6632259303e-7 |
| 4 | gels | 1 | 0 |
| 4 | gelsd | 1 | 0 |
| 4 | gelss | 1 | 0 |
| 1 | 默认 | 2 | 7.4381723891e-8 |
| 1 | gelsy | 2 | 7.4381723891e-8 |
| 1 | gels | 1 | 0 |
| 1 | gelsd | 1 | 0 |
| 1 | gelss | 1 | 0 |

运行时本地 `torch.linalg.lstsq.__doc__` 明确：CPU 默认 `gelsy`（带主元 QR），CUDA 默认 `gels`。单线程未消除此矩阵默认驱动漂移；不能简单归结为多线程规约。其他驱动仅在此矩阵上观察到稳定，不能据此认定全流程替换等价、稳定或保持历史基线。

## 可核对标识

```
frame y SHA256: 1bf7a66419cd5fbdaaea2802845058ffb5d6289e2713f974aac2d4035de49e56
frame H SHA256: 3fa0e57562cfcf73ccfc663fa74b95ad63fbf97a6b91f3f0df3964180b945fbd
frame coded SHA256: 551f8a79ea8400243d2195c4287ebffab4ff087e06b7d1152ddedaa017027eaf
1024×2 A SHA256: 626963a84a54847c0d416bc253e60eb2ac037a0cafe0ee84ec25d9d770ea53d3
b SHA256: 3d71f4e8558a85b651d69d406d36b6278d1669d775cfb23c123c01fc692f523f
```

第一探针核心（返回第一次原始解，不改算法）：

```python
original = torch.linalg.lstsq
def wrapped(a, b, *args, **kwargs):
    first = original(a, b, *args, **kwargs)
    second = original(a, b, *args, **kwargs)
    # Compare solution hashes, relative norms, ranks; record call site.
    return first
```

## 对当前计划的影响

保留失败 CPU 严格门及既有记录，不放宽为“误码相同即透明”。当前 GPU 同设备 v3/v4 严格重放及全部 192 帧 H/x/误码一致证据可继续独立使用。此次探针不替代 GPU 验证，不改变任何科学结论/预算。若未来需要 CPU 逐位重放，须单独冻结求解器契约并做整体回归；不能静默把 `gelsy` 改成其他驱动。
