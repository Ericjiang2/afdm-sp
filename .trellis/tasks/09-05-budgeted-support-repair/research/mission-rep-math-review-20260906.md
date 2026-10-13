# REP 数学与实际 BP 图的只读审查

2026-09-06。审查 `representation_ledger.py::representation_error/actual_bp_graph`，并读取其 Torch projector、生成器、BP 调用点与测试源码。只写研究记录，不修改实现/CSV，不运行测试或接收机；真实 smoke 与接线验收由主会话负责。本记录不推断尚未完成的结果。

## 1. 独立生成器 LS 的独立性成立于数值实现层

主投影来自 `budgeted_support_diagnostics.project_channel_on_support`：用整数 AFDM 原子正交性直接求 Frobenius correlation/N，再交给 `reconstruct_H_torch` 重建。

`dense_reference=True` 则逐个调用 **`system.gen_h_daft([1],[delay],[doppler])`** 生成 NumPy 密集单位原子，列向量化后调用 `np.linalg.lstsq(...,rcond=1e-12)`，最后比较重建矩阵与主投影。它没有调用主 projector 或 Torch reconstruction 生成参考 basis，也不是拿被测 D/投影公式自证；这满足独立数值实现的参考要求。

两个实现仍依赖同一整数AFDM数学约定；且 H_true 合并重建与独立 basis 都使用同一生成器。这不构成对生成器物理模型、连续delay/Doppler、外部论文/Matlab实现的独立验证。应写“独立生成器数值LS核对Torch解析投影”，而不是“独立真实信道模型验证”。

先将所有 emitted 同(delay,k)复系数合并，再调用生成器重建 H_true 的检查是必要的：完全相消项不再贡献H，仍在ledger entries中作为零项保留。`truth_error` 比较失败即抛错，没有把失败真值当参考继续计算；该失败应作为工程证据保留，不归为 receiver 表示误差高。

## 2. 当前应明确补齐的模型/域边界

### 2.1 生成器与解析原子使用了不同来源的位移系数

- `afdm_env.py::gen_h_daft` 使用 `K_factor=max(round(2*N*c1),1)`。
- `project_channel_on_support` 与 Torch reconstruction 使用 `2*k_max+1`。
- 生成器支持 `gen_h_daft_convention='matlab'`，主 projector 明确只支持 Python convention。

`representation_error` 当前未在入口明确验证 convention、`system.N_total==H.shape[0]`、`round(2*N*c1)==2*k_max+1`。正常当前配置可能满足这些约束，真实 smoke 是否满足由主会话核验；但公共helper不能把它们当隐含普遍事实。

可证伪检查：保持system.c1不变，改传k_max，取包含非零delay的support。dense=True时独立LS通常会揭示两个字典不一致；dense默认False时可能仅检查生成器自重建H成功后，静默输出另一个字典的E_repr。更明确的行为是前置拒绝不匹配模型，或将支持的约定作为有名参数并记录。

### 2.2 支撑域不是完整 receiver 域校验

当前ids检查1D、整数值、非负、唯一；主projector进一步要求 `0<=k_max<N/2`、`0<=delay<N`、`|doppler|<=k_max`。但没有用 `system.l_max_cap` 或显式receiver `Q` 限制最大delay。

因此某列可属于数学整数算子域，却已超出本receiver实际字典。`merged_truth_ledger` 的 `in_receiver_doppler_domain` 字段也**仅**检查Doppler，不能改名为完整 `in_receiver_domain`。若报告“receiver合法support”，需上游明确提供/检查真实Q、l_max；否则应保留上述较窄字段名。

当前k_max在ids解码之前未做类型/范围检查，NaN/非法值可能在整除/cast阶段才失败；H也允许空(0,0) square输入后在主projector报错。工程接口宜在解码之前明确验证正N、系统N、有限c1/c2、合法k_max，避免把模型无效与LS失败混淆。本记录不要求扩大到不支持的连续或域外模型。

## 3. 空支撑、零真值和秩

- 空S、非零H_true：主projector返回零H，E_repr应为1；dense basis为 `(N²,0)`，密集LS的rank=0，系数唯一性对空向量的判断为true。现有源码测试覆盖了该例，但本研究未执行。
- H_true=0且生成器合并真值确实相消为0：分母0，E_repr=None、ratio_status=zero_truth_undefined；残差应为0。不能把None改0后计入平均NMSE。若H_true传0但params仍重建非零H，应该由truth一致性检查拒绝。
- 空support与空物理truth slots不同；`match_physical_slots` 对无可辨真值分母应返回undefined，而不能借空系数向量的可辨识性作物理召回结论。
- 重复ID直接拒绝。当前主投影需要唯一有效整数原子，不能将重复ID产生的秩亏伪逆成功当合法support。

在上述合法整数域内，不同(delay,k)算子确有Frobenius正交结构：不同循环位移时元素位置不重叠；相同位移而delay不同，内积包含 `sum_n exp(j*2π*(delay1-delay2)*n/N)=0`；同delay的不同k因`2*k_max<N`不会产生同位移别名。每列范数平方为N。所以该域内的独立密集basis理论上满列秩，奇异值为sqrt(N)。

这解释了为什么正常测试rank=K，但**不证明任意非正交、连续或域外字典都可用 correlation/N**。若合法域内参考报告rank<K，首先应定位模型约定/数值/输入问题。若扩展模型确需秩亏，独立LS的投影仍可定义，但系数未必可辨识，现有解析helper不能直接外推；应单独保留该域外/不可辨识诊断而非静默删列。

`dense_reference` 记录rcond/rank/singular_values/columns，方向正确；它比较的是投影H而不是gain逐项相等，这对可能的不可辨识问题也更合适。目前先比较投影差并抛错，然后才形成rank记录；若出现差异失败，外层应保留错误上下文/原frame，不能只留下成功案例而宣称“无秩问题”。

## 4. 三种误差不能默认作可加分解

当前结果分别给：

1. E_repr=固定S空间上最小Frobenius残差/||H_true||²；
2. actual_channel_error_squared=||H_actual−H_true||²；
3. distance_actual_to_projection_squared=||H_actual−P_S H_true||²。

它们分别是表示误差、实际估计误差和实际H到最佳表示的距离。只有 **H_actual也在同一span(S)** 时，正交投影才给出 `actual_error²=projection_residual²+distance²`。

实际H经逐元素稀疏化/soft mask后未必留在该空间；其history/damping/correction也需核对。因此当前代码将它们称 separate associations 是合适的，不应在分析器中无条件把第三项命名为“可加的gain-only损失”，或断言E_repr必定是该实际H误差的下界。

同理，实际BP threshold_loss的分母是**实际送BP的H能量**，不是H_true能量；不能和E_repr直接相加。表示低误差也不保证FER好，Frobenius最优参考不是FER最优上界；只有后续固定support真实oracle增益桥接才能支持该support下存在可利用估计空间。

## 5. actual_bp_graph 的真实图口径

已读 `mp_detect_bp_torch` 调用点：H先经 `_t` 转内部dtype/device，再以 `H.abs()>=threshold` 建mask和nonzero(row,col)，将同一mask/edge list交给observer。该接入位置符合“实际图”，不用K_active推算边数，也不在原始complex64上重建一个不同图。测试源码亦预期graph记录complex128。

`edges=row_idx.numel()`，row/column degrees来自bincount；discarded_squared_frobenius取 `energy[~mask]`，即实际阈值删边H−H_mask的能量；threshold_loss=discarded/total。等于阈值的边被保留，字段operator='>='与BP一致。

有限断言：

- `sum(row_degrees)==sum(column_degrees)==edges==mask.sum()`；每个(row,col)在范围内、无重复并与mask相符；
- 每轮BP和末次BP都有stage/frame/input H hash；final_bp的hash应与**内部cast后的H**匹配，而不是要求与原始外部不同dtype数组hash相等；
- 对非零finite H：discarded在[0,total]，ratio在[0,1]（仅按数值容差解释）；
- H=0：total=discarded=0，ratio=None/zero_channel_undefined；正threshold通常无边，threshold=0时现有`>=`规则会把所有零元素也计为边，不能擅自改成“非零图”；
- 不能只验edge counts而忽略degree分布；mean/max可从记录向量汇总，不需再次从K推断。

helper本身未验证H有限性/shape、mask布尔形状、row/col对应关系或threshold有限非负。当前内部调用直接使用同一BP局部量，使这些大多是调用契约；若工具独立调用/未来改造，应明确验证或将其标为可信内部接口。NaN threshold/H不能输出status='defined'的NaN ratio后继续成为科学统计。无效graph输入应该是工程失败，不能当“阈值舍弃很大”。

N=0和E=0是已有BP提前返回分支；observer能记录图，不等于完整soft输出/BP/LDPC成功。特别是E=0时该detector原有返回不是完整soft tuple，runner是否支持由真实路径验收；不能靠graph record存在替代完整receiver检查。

## 6. 预算与科学口径

独立dense LS是离线诊断，不增加receiver evaluation数量，但会消耗CPU时间和内存。basis为 `(N²,K)` complex128，仅basis常驻内存 `16*N²*K` bytes；N=1024、K=40时约640MiB。当前list-of-unit-H→column_stack还可能同时持有一份单位原子列表及stack，峰值可超过basis本体；SVD有额外工作区。不能将“只是验证”从阶段成本账本排除。

runner当前表示诊断调用 `dense_reference=True`，所以实际每个被观察frame都承担该成本；必须按实际offline_seconds/峰值记录，不把某个小N单测时间外推为真实N成本。采样/减少验证范围如有需要须显式记录范围，不能默认全帧已独立验证。

graph_observer_seconds覆盖能量统计、CPU拷贝/hash等观察工作；GPU转标量/拷贝会同步，也可能等待此前排队工作，故它是观察路径墙钟费用，不是可精确从运行时长中相减得到“纯BP时间”的万能差值。正式时延仍需符合G2的独立计时协议。

BP图/表示/阶段集合统计是描述关联；不能将未入池、未选、被剪、gain差、threshold_loss百分比分别相加成因果损失分解。truth复系数平方不是物理路径能量；P_phys、K_emit、K_true、active列数和图edges继续分列。

## 7. 交给主会话的有限验证列表（未执行）

1. 正常Python约定、实际N/K_factor与receiver域吻合时，Torch投影对独立generator LS；空S和非零H应E_repr=1。
2. 两个emitted复系数精确相消，H_true=0得到ratio undefined；不一致params/H_true显式失败。
3. 改k_max但保留c1、Matlab convention、错误N、delay超receiver l_max但小于N：得到明确域/模型处置，不静默给receiver内结论。
4. 重复ID拒绝；记录合法域满秩与奇异值，并限定不覆盖连续/一般非正交模型；若rank/projection不一致，保留失败原件。
5. 阈值等号、零H、degree总和、cast后hash、每outer和最终BP；观察开关的真实接收输出按已登记普通后端透明性边界检查。
6. 对H_actual不在span(S)的例子，不以可加误差分解作断言；独立oracle桥接的FER仍由RUN-04提供。

现有test文件在源码层覆盖了complex cancellation、Doppler域外真值保留、物理碰撞、阈值边界、零图、独立密集LS与空support；未把“读到测试存在”当成测试已运行或真GPU已通过。

本记录只确认参考方法的实现独立性与有限数学边界，不关闭REP-01/02/WIRE-02，不给REP-03正负裁决。
