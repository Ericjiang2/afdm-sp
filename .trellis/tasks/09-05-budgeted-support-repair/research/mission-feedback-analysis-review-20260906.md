# FB-05 / RUN-11 离线汇总有限检查清单

2026-09-06；只读研究。依据 v2 B4、CSV FB-05/RUN-11、已冻结 `evidence/feedback-protocol.json`、提交8705788对应的反馈实现进行静态核对。延用 scientific-critical-thinking 方法，不运行脚本或实验，不改代码/CSV，不猜测正在进行的48×4结果。以下不是运行验收，也不是候选或科学结论。

## 1. 四臂与最低对比口径

| 日志臂 | 实际入口 | 至少应给出的配对对比与边界 |
|---|---|---|
| f_mean | 原 mean DA-LS，T1 | 新壳共同参照；不是另一套冻结H0先验臂 |
| f_uniform | 当前H构造 `H diag(v0) H^H + sigma²I` | uniform−mean：先验数据功率的加权入口总闭环差异 |
| f_dynamic | 同求解器，消费当前有限星座v | dynamic−uniform：可靠性方差政策总闭环差异；另给dynamic−mean |
| o_data | 仅DA-LS输入mean替换真实缩放数据，权重仍I | o_data−mean：该单入口信息参考；非部署、非数学最优上界 |

`FEEDBACK_ARMS` 已显式映射 `o_data:'mean'`；真实数据只经 `diagnostic_data_override` 改变 `x_hard_scaled`，随后生成 A_total。不能将 o_data 的收益写成“oracle方差收益”“decoder反馈收益”或可实现增益。

输出完整四臂 FER 与信息bit汇总、三流方向、上述预定对比。FER仍按信息位译码后 `info_errors>0`；bit需给总净差/每帧均差，不能只给受益/有害帧数。若报告相对真实 A0/A2 的关系，应引用**同frame/config/hash匹配的既有记录**并明确复用；本四臂本身没有额外A0运行，不能假装已直接测得该对比。

自然闭环的 H、sigma 和软均值会随策略分化；dynamic与uniform初始只改v政策，不等于每一外轮双方H/A/sigma都相同。该局部归因必须结合下面共同mean轨迹的矩输入对照，不能把两条分叉轨迹的相关性当成“v单项的同状态因果效应”。

## 2. 完整数据与普通后端边界

离线汇总前有限检查：

- 恰好 D_dev rep0/1/2 各frame0..15，无重复/缺帧；每帧4臂，192次完整接收，不以软符号事件数替代接收数。
- 固定源/ckpt/prior/LDPC/protocol hash、8dB、direct40、T1与普通生产后端；无已隔离 deterministic-reference 数据混入本批性能估计。
- 每臂容量/finite/完整末次BP→LLR→LDPC成功；异常保留frame身份及失败原因，不删失败帧后重算FER。
- 每臂9个 DA-LS consumer（outer1..9）与18条可靠性记录（dals_feedback/noise_feedback 各9）齐全；按stage+outer匹配而非只验总条数。
- uniform消费的v0恒定且来自已缩放均匀星座；dynamic消费的v与同p计算的finite_variance一致；C只属于uniform/dynamic；o_data为唯一oracle_mean=true。

WIRE-06/FB-02已有观察透明性边界是：普通后端主要输出与译码bit精确一致，全部软数组精确一致仅在独立确定性参考中成立。此边界不是允许忽略新的info_errors差异的理由；本批不能用逐bit变化解释未复核的观察器污染。也不应为让数据对齐而静默更换生产后端。

## 3. 共同状态目标、NMSE与完整FER三层分开

`feedback_diagnostics.compare_frozen_state` 对**f_mean每帧每轮同一快照**的 A、y、g_previous、H、sigma、regularization，分别解 unweighted/uniform/dynamic；它没有执行后续receiver或译码。

其目标实际为：

\[
F_u(g)=\|y-Ag\|^2+\lambda\|g-g_{old}\|^2,
\]
\[
F_C(g)=\sigma^2(y-Ag)^HC^{-1}(y-Ag)+\lambda\|g-g_{old}\|^2.
\]

代码中的 sigma 变量就是噪声功率sigma²。比较时必须保持源码中的这个缩放因子，不能把目标误报为无sigma²因子的另一套GLS。C内层固定，每个快照按当时H/方差重新构造。

有限汇总应包括：

1. 每个目标自己的 before/after 与下降，检查解是否降低**该目标**；
2. `same_objective_at_all_solutions` 的同一行比较，即固定F_u或某个F_C时比较三个解；
3. 同支撑 `same_support_channel_nmse` 的 previous/unweighted/uniform/dynamic；按相同frame+outer配对；
4. 分外轮的误差方向与帧级汇总，不能把432个快照当432个独立样本。

不允许以 `F_dynamic(g_dynamic) < F_uniform(g_uniform)` 直接宣称dynamic更好，因为两边的权重/目标不同。可以报告数值，但必须标成各自目标，不作共同性能标尺。各解降低自己的目标也不保证true-channel NMSE或最终FER下降。

`same_support_channel_nmse` 将各gain在同support上重建H再与离线Htrue比较；这是估计误差的诊断，truth没有回注receiver。`previous` 也是由g_previous重建，**不一定等于快照输入H**，因为真实输入H此前经过阻尼/稀疏化。不要把这个字段改名为“此前实际BP信道NMSE”而不另算实际H的误差。

共同mean轨迹得到的低NMSE不能贴成完整dynamic臂的末端NMSE；离线三解也不生成三个FER。完整FER只能取本批四个真实receiver输出。

## 4. 可靠性分母：分箱、条件率与总体频率

冻结边界为 `v/(1-rho)` 的 `[0,.02,.05,.1,.2,.4,.7,1]`，左闭右开，最后含1，越界单列。p、mu、v必须来自同一个有限星座分布；v已经包含数据功率，C不再乘一次(1-rho)。工作高斯方差、BP Gaussian var_post、有限星座v不是同一个量。

每个 `(arm,stage,outer)` 先保存逐帧分子/分母，再聚合：

- bin平均v=`sum(sum_variance)/sum(count)`；bin实际误差=`sum(sum_actual_squared_error)/sum(count)`。
- bin错误率=`sum(wrong)/sum(count)`；空bin给null/无样本，不给0，不静默移除该bin。
- high-confidence conditional error rate=`sum(high_confidence_errors)/sum(high_confidence_count)`。
- high-confidence overall error frequency=`sum(high_confidence_errors)/sum(count)`。

不能把上述后两个率混名；没有高置信符号时条件率无定义，而总体错误频率仍可为0。不能先对各frame的条件率取无权均值，这会让1个高置信符号的帧和1024个高置信符号的帧权重相同。

stage/outer分开汇总是首要结果。48帧×1024个符号或48×9×1024次观测可作为描述分母，但同帧符号/多轮强相关；区间需按frame整块配对重采样。绝不能把这些事件都当独立样本得到极窄“可靠性显著性”。

NLL/Brier应按各记录count加权，有限星座Brier为4类概率平方差之和的每符号均值，不能改称bit Brier。NLL的自然对数单位需保留。源码用logits的logsumexp稳定计算NLL；即使舍入后的p_true=0，logits NLL可能仍有限，这是数值表达差异，应同时报告 `zero_true_probability_count`。若无logits且nll=None/infinite，不得把None填0或drop后求平均。

## 5. 高置信错误子组存在一项明确数据边界

当前 `reliability_statistics` 保存了高置信count/errors/条件率/总体频率及最多3个示例symbol IDs，但**没有保存高置信错误子组的 sum_variance 与 sum_actual_squared_error**。其bins的两个sum属于该bin全体符号，不能反推出 `max(p)>=.9且wrong` 子组的均v/实际误差。

v2明确要求“该组v/实际误差和后续FER”，所以离线报告不能用全bin平均值代签该字段：

- f_mean的DA-LS完整 `.pt` 快照有p/constellation，可在取得同冻结输入的truth并核对hash后恢复该组统计。仅快照hash并不包含truth原值；需要已有输入或按已登记生成器重建并核对。
- 其他臂的 `dals_consumers` 对大tensor只保留hash，p/v原值不可从hash恢复；noise_feedback也没有同等完整快照。当前代码证据不足以保证这些组的v/误差可以离线补齐。
- 如原始归档另有足够逐符号数据，可以引用其来源补算；若没有，应明确写“该子组矩未采集/未恢复”，不能猜值、造额外分母或把全体均值冒作子组均值。本研究不要求或授权追加receiver回放。

o_data的reliability p/mu在oracle mean替换**之前**计算；它描述该臂当时的工作概率，不是注入truth后的“零误差oracle概率”。同样，其噪声反馈并未直接使用truth替换。

## 6. 与后续FER关联及配对区间

每个可靠性事件绑定 `(replicate,frame_index,arm,stage,outer)`，其后续FER来自**该同frame同arm的最终LDPC输出**。若按“某组是否出现”汇总后续FER，分母是出现该组的唯一frame数；不能同一frame出现100个高置信错误就重复计100次独立FER。

也可定义符号加权的后续FER关联，但必须显式命名并仍按frame重采样；它不能替代frame-level FER，也不是局部因果效应。重复外轮的同一frame不能在总体计数中被当成多个独立译码结果。

建议离线区间沿MECH已确定方法：三流各抽16帧，四臂共享同一组index；FER、bit、NMSE、NLL/Brier以及bin/high-confidence分子分母共同按frame索引抽样。在每个bootstrap replicate里重新求比值，而不是直接对已有条件率抽均值；重采样后分母0的区间点应显式计数/标记，不悄悄置零。

三流内配对帧percentile区间仅作本批描述，不是跨随机流cluster稳健区间、同时多重比较区间或正式覆盖保证。汇报每流方向。零FER差/零harm造成[0,0]不支持等价或无害。

共同状态NMSE及目标的每轮配对区间可另列；若压缩成每frame一数，预先明确使用9轮平均或固定终轮，不能看完结果挑“最佳轮”。

## 7. 病例每组最多3例，不新增分母

协议规定 first lexicographic frame/symbol IDs，阈值固定0.9。建议使用原登记组（arm、stage、outer或固定bin/高置信错误组），按 `(replicate,frame_index,outer,symbol_id)` 的固定顺序取前3；组定义也不能看到结果后拆细来展示更多病例。

源码每条reliability记录已局部取前3 symbol，汇总仍须跨frame再次限额。不能把48帧各3例都展示为“每组至多3例”，也不能先按NMSE/FER效果排序再挑典型帧。

病例展示应链接原frame与最终FER，明确其是既有分母内的解释材料；组内只有1/2例就如实展示，不造满3例。若示例只存symbol ID而缺p/v/实际误差，则不能补出未采集的数值。

## 8. FB-05最低判定与成本预检

按本路线自身证据分别裁决，不借已完成MECH的HOLD关闭反馈线，也不等旧温度补格或无关枚举完成。

- dynamic与uniform未见可辨差异：不能主张动态V必要；宽区间时称不足/未检出，不称已证明等价或动态无用。
- 只有o_data提供完整FER线索：定位为DA-LS均值入口的信息可实现性缺口，不记可部署改进，也不声称oracle是数学最优上界。
- NLL/Brier或校准bin更好而完整FER无益：只支持校准层结果，不能靠可靠性指标替代coded FER候选收益。
- 可实现uniform/dynamic若有完整FER线索、工程合格且成本可行，可登记本路线候选资格；48帧本身不颁发后续独立validation GO或正式G门。

成本至少分为逐臂完整receiver→末次BP/LLR/LDPC、共享scorer准备、observer transfer、f_mean快照I/O和offline_matrix_seconds。离线三解矩计算不增加192次receiver数，但增加实际CPU/资源费；只归给诊断，不能把它加到dynamic部署latency再与mean不对称比较，也不能从总实验账本删掉。

当前receiver计时包含观察器内工作；可做现有实现的诚实成本预检，不是去观察器后的正式部署时延证明。共享准备在实验总账只计一次，单臂standalone需计其必需准备；4臂合计不是任何单臂latency。

候选进入SEL-01前冻结具体配置/必要证据/预算/复杂度破同分规则，最多两个192帧fit，之后唯一候选进入新384帧validation。源方案未要求本48帧所有CI排除0，不私加p值门；同样不能仅凭最小点估计、工程通过或oracle正面自动认定资格。正式G2仍需后续独占、预热、交错块、1000帧与资源区间，当前48帧不代签。

## 必须保留的范围声明

V直接进入DA-LS，BP经H/sigma间接变化；C每次内层固定、每outer刷新。LDPC仍只在末端译码，无SISO外信息回注，无turbo译码迭代。旧固定壳温度2×2单列结案，不和新壳四臂拼成同一确认样本。当前报告不得把尚未完成数据填成方向、区间或GO。

源码定位：`feedback_diagnostics.py::reliability_statistics/compare_frozen_state`；`budgeted_support_eval.py::FEEDBACK_ARMS/record_reliability/save_dals_state`；`classical_joint_unrolled.py::_qpsk_soft_decision/forward`；冻结口径：`evidence/feedback-protocol.json`。本记录未执行数据检查，所有“应检查”均交主会话离线汇总时落实。
