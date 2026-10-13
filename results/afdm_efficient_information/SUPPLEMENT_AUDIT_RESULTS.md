# Oracle 与可辨识性补充审计结果

`supplement_audit_v1` 正式完成，**126429 项比较全部通过，失败数 0**。
全部数值比较的最大绝对差为 **1.4210854715202004e-14**；原保存 likelihood
生成的目标矩阵与原目标、原各方法校准阈值的最大复算差均为 **0**。
这是对已保存补充结果的独立复算，不是新增观测、重积分或新的科学有效性证明。

源码冻结提交：`6bd9cba20cada401f77cdec2b773a9dab8b57c83`。
输入补充阶段为 `oracle_identifiability_v1`，其绑定注册及 attempt 哈希分别为：

- registration：`df69ea6637e29698671c18ebd2229d1a88d5784aa04ec82edae7d902a004d98c`
- attempt：`f2434b69441bbba4df5380c018260d951864758eb133e869dbeeb9b535f451cc`

## 全行覆盖

| 复算对象 | Gaussian 控制 | 实际先验 | 合计 |
|---|---:|---:|---:|
| known-eta NP oracle pair/R | 96 | 16 | 112 |
| 同组 oracle/原方法判决配对 | 1152 | 256 | 1408 |
| known-eta MLE condition/R | 120 | 32 | 152 |
| MLE 与原方法误差配对 | 720 | 256 | 976 |
| 原目标 argmin 歧义评价行 | 720 | 256 | 976 |
| moment 冻结准则等价方法 | 4 | 5 | 9 |

控制模型的 48 个同 nuisance null/alt 对、实际模型的 8 对以及全部原 R 均保留。
复算读取每个报告行及其全部保存组：NP LLR、独立 null 校准 rank/阈值、严格
拒绝判决、虚警/功效分母与 Wilson95、LLR mean/SE；known-eta MLE 的候选子集、
原 ID 顺序、原生坐标与 delta 误差、边界率；判决四格表、配对误差和 SE；全部
精确/机器容差 argmin 集合、兴趣参数/nuisance/逐坐标的不同值数量和完整数量分布。
9 个 moment 方法的系数、精确类、近邻矩阵及每候选近邻集全部复核。

原各方法的全部条件校准阈值和非随机判决均重新核对。信息无关随机基线沿用原保存
判决，不生成新硬币。原目标不可辨识的误差字段继续为 null。以上报告行复用了原数据；
特别是多个备择复用同一 null 组，不能把行数当作新增或相互独立的样本量。

## 哈希与费用

运行前后核对三个输入阶段：`oracle_identifiability_v1`、
`inference_control_v1`、`inference_actual_v1`。两次输入清单和费用完全一致：

| 校验类别 | 每轮计数 |
|---|---:|
| 冻结保护文件 | 4307 |
| 绑定 source 文件引用 | 380 |
| source snapshot 引用 | 380 |
| 完整 artifact 清单文件 | 2449 |
| 原提交 source blob | 24 |

source/snapshot/blob 数为各阶段引用的检查次数，不是去重文件数。
校验包括全部工件清单、绑定原提交、输入注册/attempt、记录的消费文件哈希和费用。
大型 raw 没有复制进本审计的 source snapshot；原始文件和冻结源码未修改。

费用取自本阶段 `attempt.json`，而非入口 stdout 的外围计时：

| 项目 | 记录 |
|---|---:|
| 状态 | complete |
| 实际 wall | 3.6260585830023047 秒 |
| 实际 CPU | 3.036335 秒 |
| 峰值 RSS | 186400768 字节 |
| wall 预约 | 60 秒 |
| 新观测预约 | 0 |
| 新科学节点 / 积分规则 | 0 / 0 |
| receiver / decoder 调用 | 0 / 0 |

输入阶段清单中的累计 wall 为 209.2856805830088 秒、CPU 为 208.825041 秒，
并记载原有 61440 个观测和 3000 秒预约；这些都是输入阶段已有费用，不是此次审计
新增费用。最终项目账本只另加此次审计的终态 attempt 一次，避免把输入费用重复相加。

## 与此前全量审计的区别及结论边界

此前 `audit_v1` 已对九个研究阶段完成 33278 项比较，最大绝对差
6.111804395914078e-10，失败数 0；其 wall 为 761.2979877920006 秒、CPU 为
757.512952 秒。它覆盖原特征、似然及规定积分范围等较昂贵的复核。本次只增加补充
oracle/歧义结果的统计读取器，没有重跑旧审计 adapters，没有再次进行密度积分。
两次审计的比较次数定义和覆盖对象不同，不能以次数多少衡量科学证据强弱。

本次通过说明补充统计、完整分母、机器容差判定和源数据绑定一致。它保留以下边界：

- 有限独立校准的经验 oracle 功效是参考结果，不是认证功效上界；理想准确 size
  的 NP 定理与本次有限校准数值结果分开。实际参考的求积资格继承原记录，没有新认证。
- 精确等价仅指经独立系数收缩核对后的保存浮点系数多项式。逐分量机器近邻不是
  传递等价关系，未作连通闭包。数值 argmin 集合不是统计置信集合。
- 样本并列、冻结评分准则等价与完整物理分布的结构不可辨识性分别标记。本次只
  核对已声明的继承解析标签，没有从有限数据推出新的结构可辨识性结论。

证据文件：[`supplement_audit.json`](supplement_audit_v1/supplement_audit.json)、
[`checks.json`](supplement_audit_v1/checks.json)、
[`attempt.json`](supplement_audit_v1/attempt.json)、
[`registration.json`](supplement_audit_v1/registration.json)。
