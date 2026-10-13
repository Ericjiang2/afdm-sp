# GOV-03 随机身份与隔离核查（2026-09-06）

只读研究，未修改实现或 CSV。使用 `/opt/anaconda3/bin/python` 实际调用 `dev_rng`，并调用 `make_frame` 做 N=8 单位信道身份 fixture；没有运行物理实验、receiver、LDPC 或作业。没有访问 Dtest，没有生成/读取新 validation 的信道、数据、噪声或观测。旧 validation 仅读取 status 中的命名范围，不读取 frames。

机器证据：`mission-rng-identities-20260906.json`。其中含完整种子身份、摘要 hash、读取范围、源码 hash 和实际 fixture 断言。这里的 identity hash **不是未来观测 input hash**。

## 实际核查结果

| 分组 | 身份 | 数量/唯一seed | 与其他三组seed交集 |
|---|---|---|---|
| prior | split2 / rep40 / frame0…399 / stream9 | 400/400 | 0 |
| fit | split2 / rep30,31,32 / frame0…63 / stream1 | 192/192 | 0 |
| validation身份预登记 | split2 / rep30,31,32 / frame64…191 / stream1 | 384/384 | 0 |
| 旧Ddev | split1 / rep0,1,2 / frame0…63 / stream1 | 192/192 | 0 |

扫描两个相关历史任务 research/runtime 的 status，得到484个既有唯一帧身份。新 prior、fit、validation 身份及派生 channel seed均无冲突；Ddev192全部192个身份已使用，属于预期重放，不能标成新数据。已读取历史 calibration 元数据提供的2400个唯一seed也无新域交集。

进一步从已记录 harvest 命令重建 `seed_base+snr` RNG 的全部最多 `3*n` 次候选seed，共4800个唯一可能seed，与上述四组均无交集。该上界核查覆盖被旧harvest跳过而不进入calibration的可能seed，但不声称所有seed实际运行过。配方及来源保存在JSON中。

读取 `capacity-dev-rep0/1/2/frames.jsonl` 中192条旧开发记录：全部 channel_seed 与当前 dev_rng 推导一致，192个y hash唯一。记录摘要 `111e51c5eebf8d7ea90b3ceb56deef85fa3d75262d8960159d44e6423f9d83c4`。没有重新生成这些真实观测，故这里只证明已存身份与哈希记录一致，不是物理字节重放通过。

实际make_frame fixture通过：channel_seed派生一致、np.random全局channel流一致、IID数据stream2一致、噪声stream3一致；同一身份从8dB改12dB，H/data/noise相同且y不同。fixture禁止调用encoder。这是运行证据，但不是物理信道验证。

## 应冻结的唯一派生规则

建议新prior逐帧确定：

```python
seed_i = int(dev_rng(40, i, 9, split=2).integers(0, 2**31))
# i = 0 .. 399; i=0 gives 642963427
```

把 `(split=2, replicate=40, frame_index=i, stream=9, seed_i)` 显式交给 `harvest_frame`；其内部保留现有 `np.random.seed(seed_i)` 生成channel、`default_rng(seed_i)`依次生成IID QPSK和noise的规则。这里stream9是prior帧seed派生域，不能谎称harvest内部具有runner的独立stream1/2/3划分。

现有 `run_harvest` 是 `default_rng(seed_base+snr)` 顺序抽seed，且失败会跳过另抽，不会自动实现上述manifest。必须新增显式固定seed消费，并禁止失败替换成第401帧。若选择保留旧主RNG派生规则，须在运行前另行给出唯一精确定义并重新生成manifest/冲突核查；不能把本报告的逐帧seed清单标作旧主RNG产物。v1“继承harvest实际seed规则”的歧义应由主会话写回GOV-03契约，不能保留两个实现源。

fit/validation保持当前make_frame：stream1派生channel seed，stream2 bits，stream3 noise；run_frame stream4只用于arm顺序。SNR不进入身份，因此同一frame跨SNR复用channel/data/noise簇。Ddev24/48分别取既有Ddev192中每rep前8/16帧，不创建新命名空间。

## hash隔离边界

1. 当前可以冻结身份manifest及其hash；fit/validation用不相交frame范围，prior用独立rep和stream。已实际排除31-bit种子碰撞，不能仅凭根整数不同断言无冲突。
2. prior运行时另存完整实际input hash（channel参数、IID data、noise、pilot、y）、配置hash、固定LDPC身份如适用、truth merge规则/schema及逐帧成功/失败记录。400固定ID缺失或重复显式失败。
3. fit运行时保存现有input_hashes以及配置/源码/prior hash，并检查对prior和已有Ddev的实际hash隔离。validation在候选冻结前只保存身份，不生成input hash；获准打开后才生成并核对实际input hash，绝不能为提前“证明哈希隔离”而先生成validation观测。
4. 现有 `make_frame` 不包含receiver配置，因此direct40/extension0不应改变物理输入。旧补格保留旧源码/配置，只按旧192帧记录重放。

## 现存代码与可复用测试

- `budgeted_support_diagnostics.py:22–28`：SeedSequence `[20260905, split, replicate, frame, stream]`，仅允许split1/2。
- `budgeted_support_eval.py:70–84`：make_frame各随机流；`:110` arm顺序stream4；`:223` actual input_hashes；`:336–337`仅检查当前channel seed是否撞prior。
- `decision_harvest.py:148–160`：每帧seed内部语义；`:272–284`旧主RNG、最多3n尝试与跳帧；`:318–323`旧缓存seed/config。
- `test_soft_feedback.py:43–47`：split1旧流字节不变、split2隔离、split3拒绝。
- `test_budgeted_support_diagnostics.py:121–125`：可重现及rep/frame/stream变化。
- `test_budgeted_support_eval.py:15–24`：IID模式不调用encoder；可扩展为固定manifest与跨SNR输入簇测试。
- `test_fixed_capacity.py:15–25`：接收nomination与truth count分离，可扩展为prior固定400ID及无静默替换。

建议新增：对固定manifest全部帧ID/seed以及跨组seed交集做契约检查；harvest固定seed输入逐项消费、失败分母不替换；新prior manifest hash与配置不符拒绝；实际input hash互斥检查只在相应数据允许打开后运行。

本核查仅覆盖本地两个关联任务已有记录及其命令元数据，不声称扫描远端全部文件或未知命名空间。没有远端访问。
