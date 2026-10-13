# TRAJECTORY-DIAG-01 独立轨迹原件审计

日期：2026-10-08。任务：`.trellis/tasks/10-05-method-advantage`。
CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

## 结论

**窄原件结果核验 PASS。** 240 个保存 sweep 末状态、24 个终态和90项聚合
全部独立复核通过。point 与 local 的前5轮在全部8个观察量上硬判逐bit相同：
40组×2048 bits，差异全0；不能把这一点扩大为软概率、目标或算法普遍相同。

point 第5→20轮：8/8观察量的完整 reduced F 提高、真值 symbol log loss
增加、q_d entropy 降低；误码5组增加、3组减少，合计1672→1684。
这是这些保存轨迹上的目标与风险分离，没有因果归因或可部署停止策略含义。
原DEV科学门FAIL不变，不进入CONF/Trans。

## 身份与核验边界

复用本人已完成的 `COLLAPSED_RECEIVER_DEV_RAW_REVIEW.md` 身份审计，
未重新审查212文件或receiver/source/ENG。只检查本次30输入与新分析输出绑定；
没有执行正式 `trajectory_audit.py`，没有生产import、SSH、receiver、
优化搜索、新仿真或物理basis计算。独立校验代码使用标准库NPY/ZIP读取、
复数Cholesky、小矩阵代数及保存logits上的求和。

| 材料 | SHA-256 |
| --- | --- |
| control-trajectory/contract.json | 6c531a63b243dbefd4d9551958a267824c38b75308c69012ecfc5a404a6004b9 |
| control-trajectory/trajectories.json | 24e19e23f43e238fbff3ccd8ac64d0aeb3e0353747666712f31e7a43bbde6819 |
| TRAJECTORY_OBJECTIVE.md | 2cff93f1a2a0be5716697d6ef93aad0ed3e5a54aadaf5a8ee4a8a32b5b822948 |
| 已登记 trajectory_audit.py | 18b712e31c02e5573d83986403fdfeb157dba3c8b3be3fecb2e4eecf63ff367a |
| DEV receiver_seal.json | 0ae8b5da0f8ddf15223a39b43c91bebe5202c6cf79b4d1a96f97e88ae94e933e |

control材料位于 `.mission/20261007-sp-fractional-trans/control-trajectory/`。
contract.local_stage 精确对应此前已审 COLLAPSED-RECEIVER-DEV-01；
30输入集合恰好为三VB臂24 calls、4 truth、scores、receiver_seal，无遗漏、
重复或额外源。全部SHA重新匹配；每个call还匹配seal记录。
trajectories绑定同一contract SHA；协议和脚本字节与合同登记SHA一致。
这只验证分析身份，不重新审查已获其他审查者PASS的脚本实现。

240 records恰好对应8×(20+5+5)，按block/SNR/arm/sweep唯一定位。
90 aggregates恰好覆盖30个arm/sweep的总体、6dB和8dB三种分组，
没有以重复聚合补足数量。来源仍为4 blocks、8 observations；
new_observations=receiver_calls=0。240个状态不是240个独立样本。

## 数学值独立复核

每个sweep均从原call的保存log_q读取1024×4有限、归一化log概率；
由QPSK顺序(00,01,10,11)重算all-I then all-Q LLR及硬判，
真值符号索引为2b_I+b_Q。逐项核对bit errors、2048分母、
symbol log loss、entropy，以及216个相邻sweep的硬判变化、
wrong→correct和correct→wrong。

普通point/local使用该sweep的gain_after_doppler；collapsed使用最后坐标
full winner。240个m均为8维、C均为完整8×8，独立复数Cholesky检查
Hermitian、正定及重构后恢复logdet；未用对角近似。逐状态计算

`KL_h = 8 tr(C) + 8 ||m||² − 8 − 8 log(8) − logdet(C)`

`F_reduced = data[-1].new_objective − KL_h`。

全部KL非负（容差1e-10）。完整gain项已计入F，D没有被当成跨sweep完整目标。
D本身沿用已封口data-step末objective，未通过重新执行物理残差算子核验；
结论限于保存D与gain/log_q一致性的审计。被省略的−Nlog(πσ²)在同一
observation内固定，F只在相同条件或固定观察量集合上比较变化。

与trajectories记录相比，按max(1,reference norm)归一的最大误差：

| 检查 | 最大误差 |
| --- | ---: |
| 每状态data objective | 0 |
| 每状态gain logdet | 0 |
| 每状态Gaussian KL | 1.6171950053801979e-16 |
| 每状态F_reduced | 1.9999884928028863e-16 |
| 每状态symbol log loss | 1.9984014443252818e-15 |
| 每状态entropy | 1.1102230246251565e-15 |
| 最终LLR相对误差 | 2.3146539823521617e-17 |
| 全部聚合F | 2.0371315075995496e-16 |

24个终态log_q与各backend最终log_q字节一致，重算硬判与原raw硬判精确相同；
终态错误与此前DEV scores逐case一致，最终三臂总错误为1684/1672/1661。
原输出登记的最终LLR最大绝对差为1.7763568394002505e-15；
独立稳定求和结果也满足1e-10阈值。Cholesky重构全部通过1e-10检查，
原登记最大factor residual为5.421010865997177e-20。
每条累计sweep seconds按保存秒数逐项相加，差异为0；不将其当作端到端成本。

## 全体保存轮次的总体曲线

每行固定8 observations，错误分母16384；log loss与entropy为每符号均值，
F为固定8条观察量上的和。分SNR的另外60项也已全量复核，
原完整90项聚合及240条逐case记录保留在上述SHA绑定的trajectories.json。

| 臂 | sweep | 错误数 | symbol log loss | entropy/symbol | F_reduced之和 |
| --- | ---: | ---: | ---: | ---: | ---: |
| point | 1 | 2931 | 0.803775377 | 0.639240532 | -24057.463422 |
| point | 2 | 2049 | 0.608014617 | 0.460315395 | -18834.809623 |
| point | 3 | 1787 | 0.551416979 | 0.374629977 | -17858.339015 |
| point | 4 | 1688 | 0.539454786 | 0.331189072 | -17585.298618 |
| point | 5 | 1672 | 0.542316023 | 0.307817386 | -17486.877722 |
| point | 6 | 1679 | 0.550273017 | 0.293043580 | -17442.850063 |
| point | 7 | 1677 | 0.559185305 | 0.283455144 | -17420.155867 |
| point | 8 | 1677 | 0.566293771 | 0.277027141 | -17407.131242 |
| point | 9 | 1685 | 0.571838775 | 0.272707852 | -17399.016818 |
| point | 10 | 1685 | 0.576221764 | 0.269603258 | -17393.564271 |
| point | 11 | 1683 | 0.579577804 | 0.267448874 | -17389.783510 |
| point | 12 | 1684 | 0.581842015 | 0.265891544 | -17386.836275 |
| point | 13 | 1680 | 0.583586486 | 0.264658850 | -17384.612133 |
| point | 14 | 1679 | 0.584741634 | 0.263698976 | -17382.947768 |
| point | 15 | 1684 | 0.585356000 | 0.263015930 | -17381.711739 |
| point | 16 | 1678 | 0.585628485 | 0.262460899 | -17380.667686 |
| point | 17 | 1677 | 0.585770835 | 0.261991907 | -17379.290480 |
| point | 18 | 1675 | 0.586081915 | 0.261422796 | -17377.774918 |
| point | 19 | 1681 | 0.586581225 | 0.260991159 | -17376.999088 |
| point | 20 | 1684 | 0.586954894 | 0.260651498 | -17376.516919 |
| local_point | 1 | 2931 | 0.803775695 | 0.639240564 | -24057.463593 |
| local_point | 2 | 2049 | 0.608015318 | 0.460315493 | -18834.807429 |
| local_point | 3 | 1787 | 0.551419796 | 0.374630078 | -17858.340483 |
| local_point | 4 | 1688 | 0.539459406 | 0.331189222 | -17585.302292 |
| local_point | 5 | 1672 | 0.542320519 | 0.307817537 | -17486.879720 |
| collapsed_point | 1 | 2923 | 0.804136128 | 0.639457674 | -24061.820526 |
| collapsed_point | 2 | 2061 | 0.608192846 | 0.461046067 | -18816.509390 |
| collapsed_point | 3 | 1783 | 0.550240072 | 0.374904391 | -17836.630215 |
| collapsed_point | 4 | 1684 | 0.537572466 | 0.330261384 | -17559.869438 |
| collapsed_point | 5 | 1661 | 0.541071977 | 0.305850771 | -17462.437330 |

point前5轮总错误曲线与local一致不是巧合的总数抵消：
每轮、每case的2048维硬判都相同。软分布不完全相同，例如第5轮平均log loss
point=0.5423160231565582、local=0.5423205187018016；
F和entropy也有小差异。因此本数据不支持把local相对point20少12错归因于
搜索改动的新增判决收益；同轮硬判比较已经显示point5也具有这些判决。
这不是一个经过端到端五轮复跑的新baseline或普适等价证明。

## point第5→20轮：逐case覆盖

Δ取第20轮减第5轮；第三列是point5对local5的硬判Hamming距离。
最后一列由两个端点硬判和同一truth直接计算，不是相邻轮次事件累加。

| block | SNR | point5/local5硬判差 | 错误5→20 | Δ错 | ΔF | Δlog loss | Δentropy | 纠正/新增错 |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 0 | 6 | 0 | 240→260 | +20 | +8.030462 | +0.042310553 | -0.059400248 | 19/39 |
| 0 | 8 | 0 | 154→151 | -3 | +15.188152 | +0.038048499 | -0.040066617 | 28/25 |
| 1 | 6 | 0 | 250→253 | +3 | +7.807739 | +0.003997012 | -0.031654663 | 20/23 |
| 1 | 8 | 0 | 170→159 | -11 | +20.118237 | +0.020466465 | -0.035609201 | 37/26 |
| 2 | 6 | 0 | 274→279 | +5 | +8.730904 | +0.068476880 | -0.055554501 | 30/35 |
| 2 | 8 | 0 | 164→165 | +1 | +15.585366 | +0.041207899 | -0.039151367 | 23/24 |
| 3 | 6 | 0 | 266→253 | -13 | +11.102469 | +0.042888451 | -0.067379742 | 40/27 |
| 3 | 8 | 0 | 154→164 | +10 | +23.797474 | +0.099715211 | -0.048510765 | 32/42 |

端点共470次硬判变化：纠正229、新增241，净增加12错。
6dB错误1030→1045（+15）；8dB错误642→639（−3）。
F总和增加110.36080287944787；平均log loss由0.5423160232升至0.5869548943，
entropy由0.3078173857降至0.2606514976。8个case的log loss都变差，
即使其中3个case的误比特减少；风险指标之间也不能互换。

point第4轮平均log loss为0.5394547857，第20轮为0.5869548943；
第4轮entropy为0.3311890716，第20轮为0.2606514976。
全部轮次列于上表，不从真值曲线为算法挑选停止点。

## 相邻轮次与解释边界

| 臂 | 相邻保存状态对 | F严格增加 | F增且误码增加 | F增且log loss增加 | entropy降低 |
| --- | ---: | ---: | ---: | ---: | ---: |
| point | 152 | 152 | 46 | 105 | 152 |
| local | 32 | 32 | 3 | 8 | 32 |
| collapsed | 32 | 32 | 2 | 9 | 32 |

216个相邻末态F全部严格提高，最小增量0.021704084412704105，
不是容差内的微小负值被记作单调。point第5轮以后120个相邻状态对中，
43对F提高且误码增加，97对F提高且log loss增加；不能声称风险每一步必然恶化。
本检查只覆盖保存的sweep末态，不对未保存的中间坐标/所有data-step概率补造证明。

这些事实支持“工作模型优化目标改善不保证保存真值上的预测风险改善”的
有限描述；熵下降不自动证明校准恶化的原因，不能据此确认错误delay、
漏路径、因子化、噪声模型或停止轮数是哪一个因果瓶颈。
相同4个blocks已用于开发，不能将诊断当成独立确认。
累计sweep seconds排除F1、初始化、最终导出和raw保存，
不能由point5的前缀秒数重新判定DEV性能–成本门。

## Findings (fixed)

无结果错误需要修复。只新建本报告；输入、输出、脚本、CSV和STATE均未修改。

## Findings (not fixed)

无原件核验阻塞。模型/effort元数据不可得，model parity unknown；
新方法、可部署停止策略和因果验证均不属于本次已获证据。

## Verification

- 30输入绑定、240状态完整性、24终态：PASS。
- Gaussian KL与F、LLR/错误、log loss/entropy、216相邻变化、90聚合：PASS。
- point/local前5轮40组逐bit比较：PASS，差异全0。
- Lint / TypeCheck：本轮仅审计Markdown，不适用。
- 科学执行：未生产import、未重跑正式脚本、未新仿真。
