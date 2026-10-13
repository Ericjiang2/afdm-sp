# MECH-01：离线机制分析口径的只读审查

2026-09-06；对象为 `issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/analyze_mechanism48.py`、CSV MECH-01/SEL-01/RUN-12/SEL-02 和 v2 B3/B5。应用 scientific-critical-thinking 技能。只核对可证伪问题与推断边界，不运行分析器、实验，不读取未完成结果来推断效果，不改代码/CSV。此记录不是结果验收，也不担任任务 checker。

## 当前判定

分析器的配对 FER、信息 bit 标签和按流内帧重采样的结构一致；它明确标注描述性开发证据，并没有自动颁发候选资格或科学 GO。拒绝分支若和共同 keep 输出不一致，代码会停止，未把该差异当作动作效果。

最初发现的三个缺口已由主会话补入代码，已读取更新部分确认，**不再作为未解决问题**：

- 为每个机制臂补充对 A0 与 `baseline`（真实 A2）的配对 FER/bit 对比；
- 补充信息位总净差、每帧平均净差及共享重采样索引的描述性区间；
- 保留逐臂 receiver_seconds 与 standalone_seconds_estimate，而非只有9臂总时间。

以下内容说明实际能够支持什么、哪些结论仍需额外输出或门控；没有据此断言本批数据阳性或阴性。

## 1. 配对单位与 FER/bit 标签

源码先将 frame 按 `(replicate,frame_index)` 排序，并断言恰好是3流×各16个预登记 ID；每个 frame 同时包含9臂。`matrix` 使用 `int(info_errors>0)`，因此 FER 定义是**信息位译码后至少一位错误**，不是 raw_errors>0，也不是 LDPC `decode_ok=False`。这个定义应在 MECH 报告表头中保留。

对 arm−keep：

- info_bit_delta=`E_arm−E_keep`；正数有害、负数有益、0同错误数。
- FER_harm=`E_keep=0且E_arm>0`；FER_benefit=`E_keep>0且E_arm=0`。
- raw_bit_delta 是 detector/uncoded-bit 层辅助指标，不应覆盖信息位或 FER 标签。

同一帧两臂都错误但信息错误数减少，可记 **bit beneficial、FER tie**；这不是标签矛盾。两臂错误数量相同不证明错误位置相同，也不证明软输出相同；标签应称“错误数无差异”。

已补充的 net_info_bit_delta 才是信息位净效果；不能用 beneficial 帧数多于 harmful 帧数替代净位收益。可证伪例：10帧各少1位、1帧多100位，受益帧更多但总净差为+90位。当前更新已避免只报次数造成的缺口。

FER 对 keep 的一致性检查可直接由现有输出复核：`delta_FER=(FER_harm−FER_benefit)/48`。建议最终表保留完整配对四格数，至少 n01/n10；原 `frame_records.info_errors` 足以导出，不能只给两个独立 FER 置信区间替代配对比较。

信息 bit 区间当前单位是“每帧错误位数差”，不是 BER 差。若需要 BER，必须除以每帧**信息位数**；runner 的 `bits_per_frame` 是 coded bits 长度，不能直接作为信息 BER 分母。

## 2. bootstrap 实际是固定三流内的成对帧重采样

更新代码为每条流产生一个 `(20000,16)` index 表，同一 index 同时索引所有9臂；FER 和 bit 也复用该表。随后三流均值等权平均。由于每流16帧，这与原48帧点估计权重一致，保持了臂间配对，也保持 FER/bit 联合抽样关系。

这应称 **按流分层的配对帧 bootstrap**，不能称“把3条流作为3个 cluster 重采样”：代码没有 resample stream IDs。区间刻画固定这三条生成流下的帧内采样不确定性，不能直接推断“任意新 seed/新场景的跨流变异”。若存在同一信道跨多帧相关，单帧重采样还需改成该相关块；当前 make_frame 的每个帧生成独立标识的 channel/noise/info，未发现代码把同一信道显式重复作为多个独立帧。

源码报告 per_stream 对比，因此三流方向应单独展示，不能用 pooled 结果遮住流间相反方向。仅3流的观测不应包装成跨场景稳健性证明。

`bootstrap95` 和 bit 的 percentile 区间没有多重比较或覆盖保证，代码已有此声明。2×2、protection、OLS、keep、A0/A2 多项对比均是探索性描述；不能挑一条未校正区间不跨0便称验证显著。interaction 的区间对应 `R11−R10−R01+R00`，是 FER 绝对差尺度上的交互，不是 odds/RR 的交互。

零不一致或零事件可能使 bootstrap 输出 `[0,0]`；这不是零风险或 G3 护栏通过。父 design 已明确禁止此推断。不能因为运行20000次重采样就声称稀有风险有高功效；重复次数提高的是数值稳定性，不增加原始48帧的信息量。

## 3. 拒绝分支与“有害提案”不能混为一谈

分析器约58–61行：若 `accepted=False`，先断言 committed==baseline，再断言 output H/x hash、sigma2、info_errors、raw_errors 与独立 GLS keep 完全相同。随后生成标签，因此通过该断言的拒绝帧必然是 bit tie/FER tie。这是**执行策略没有提交提案**的事实，不表示被否决提案如果实施也无害。

若任何上述一致性断言失败，应保留失败 frame/字段并报告 ENGINEERING_HOLD；不能删掉该帧、改成0差异，或直接把差异计为门控的科学收益/损害。此前 WIRE-05 已记录 soft μ/var/LLR 的GPU微小重复差异边界，当前分析器没有把它们加入 hash 相等要求；也不能把此前“软输出不同但bit相同”擅自扩展成“任意bit差异都是可忽略数值噪声”。

要判断“F gate 拒掉的是有害动作”，应在对应 `R00/R01` 或 `R10/R11` 中，先核实两臂**门控前 proposal 的实际 active IDs/gain/model identity一致**，再取无 F 臂执行该 proposal 对共同 keep 的完整 bit/FER 标签。若 pre-gate proposal 已不同，不能把无 F 臂的结果移贴到 gate 臂未执行的提案上。

当前分析器验证共同 reference/pool/prior，但没有输出或显式核对上述跨臂 proposal identity，故现有输出足以报告“整个 gate 策略的配对差异”，尚不足单凭该标签报告“被拒 proposal 的反事实有害率”。这是一个具体、可由 tx.proposal/hash 复核的剩余边界。

`actions` 的 beneficial/harmful/tie 当前分母为各臂全部48帧，包含 rejected keep。报告 accepted-only 标签可以作为补充，但不能替换全帧策略收益；只选 accepted 帧会引入按策略选择子集的条件化，不能用于与其他臂不同接受集作总体 FER 比较。应同时给 accepted、rejected、reason 分类数。

## 4. J2/J3/D4 的判定应分别落在已有对象上

- **J2 数值一致性**：依赖 MATH/SCORE 的独立数值契约，以及此次同模型/同数值 prior/同表接线证据。不是看 FER 优劣后决定恒等式是否成立。
- **J3 完整动作**：依赖 F 用实际提交增益、rank/容量/reject/keep 一致性。可报告 nongate 提交的负 delta 次数、gate 否决的 worse/critical 次数及相应完整 bit/FER结果。
- **D4 protection**：`r11_protect0−r11` 只回答当前固定 policy、模型和预算下取消保护的作用；不自动代表所有保护政策无用或必需。

当前 `frame_records.labels` 存有 reason/accepted/objective_delta，但汇总没有分出“目标逆转”与“实际 FER harmful”交叉表。若 MECH 正文要写“目标逆转减少但FER无益”，须从这些字段补出支持该句的计数，且区分拒绝 proposal 的 delta 与实际 committed 差异；不能以 accepted 总数或 bit-beneficial 数替代 J 改善证据。这是输出解释所需的有限补充，不要求另跑数据。

R00 共享最终 GLS、冻结表等新共同规则，不等于历史 A2。现在已补的 A0/A2 对比可以直接展示这种差距；不能在表格中将 r00 标签改成 baseline。与共同 keep 的改进说明本机制相对该共同初始状态的可利用空间，仍应报告相对已选真实 A2 的方向与区间。

## 5. 成本只用于此阶段预检，不冒称 G2

已补 per-arm receiver/standalone 费用，因此可以检查候选路线的完整接收费用和共享准备费用。9臂 total receiver_seconds 是本批诊断成本，不是单臂部署延迟。共同 keep 的反事实运行也属于诊断成本。

共享 scorer/mechanism preparation 在本批资源账本只计一次；评估单独部署一个候选时该候选必需的 preparation 不能除以9。runner 的 standalone_seconds_estimate 已提供相应估计，应注明包含 reference-table preparation/observer 的现行实现；不能删除准备阶段后声称成本可行。

本48帧、9臂诊断不满足正式 G2 的1000帧/预热/交错块/独占资源和同时区间要求。可用于排除显然不可行实现或登记后续费用，不得把此处最快臂直接标记 G2 PASS。拟合资格要求的是诚实的费用预检，而不是提前完成正式 G2。

## 6. 候选资格的最低证据与后续 fit 门

MECH-01 是 MANUAL 裁决，当前分析器没有自动 eligibility 字段是合理边界。若要登记本机制路线进入 SEL-01，至少要同时给出：

1. 候选是观测可实现、固定的具体配置，工程契约/共同状态/完整消费者通过，未处理的一致性失败不能被描述性统计绕过；
2. 完整48帧矩阵和失败分母保留，信息bit与FER净差、三流方向和描述性区间清楚；对共同keep、真实A0/A2的关系不混同；
3. 对该候选自身声称的 scoring/gate/protection 机制有对应有限证据，不借V或全池枚举代签；
4. 可实现净FER线索与完整成本预检共同支持继续投入，并说明哪些结果仍不确定；仅F改善、仅工程通过或仅raw bit/NMSE改善不够；
5. 在 validation 生成/读取前冻结候选ID、配置、必要证据、复杂度/ID破同分规则、截止点及预算。至多两个候选进入各192帧 fit，fit 后按FER优先只冻结一个进入新384帧 validation。

源方案**没有**为48帧机制筛选规定“CI必须排除0”或另一个任意 p 值门槛，不能审查时私加更严格门；同样不能将48帧最小点估计臂自动提升为候选。少错/区间过宽只能给不足或有限线索，需明确继续投入依据，不声称已验证获益。

`BASE-01.md` 已登记参考 A2、SNR*=8dB；本机制包不能因新方法在哪个点更好而改工作点，也不能看本48帧后换参考再用同一未来 validation 挑搭档。

SEL-02 的 RR≤0.90、至少两流改善、余流不退化及参考资格，是**后续独立 validation 的开发 GO 规则**，不是本48帧的正式科学门，也不是 G1/G3。validation 未GO不得在同一数据调参/追加至通过；未选路线若继续，需新登记独立验证流。若本机制证据不足，不代表未完成的独立反馈路线自动 NO-GO。

## 7. 一个有限溯源缺口

分析器将 smoke 的 `dev0-first` 复用为48帧中的第一帧，检查源码/checkpoint/calibration/LDPC/device与新批一致，且最终 frame ID 严格无重复；这是明确的复用方案。但输出的 `artifact_sha256` 目前仅覆盖 `raw.items()`，不覆盖提供9次复用接收的 `smoke` 归档内容。

因此仅拿生成的 validation JSON 不能对这9次复用原件逐成员核对 hash；应在交接中另列 smoke archive/hash或加上分前缀的 smoke member hashes。此缺口影响可追溯性，不依据它猜测复用数据错误。不同 packet 的 runtime torch版本/CPU线程等目前也未参与该相等断言；若报告跨packet费用可比，需沿status记录核对，不仅凭 source hash相同。

## 结束边界

以上仅为静态研究结论：统计单位与更新后的基本对比结构可解释；仍需约束拒绝提案反事实、描述性区间、候选资格与正式门的语言。未运行 `analyze_mechanism48.py`，未评价未完成48帧的实际方向、区间或候选胜负，未变更任何CSV状态。
