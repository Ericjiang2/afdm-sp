# AFDM 方向判别施工交工单

独立性：独立子代理 GPT-6（gpt-6-astra，low），未参与实现；直接阅读源方案、两张优先级/决策截图、源码和运行证据。本文由该审查者起草；未安装 humanizer-zh，未进行该工具润色。

## 总结

源方案承诺在固定 AFDM–SP 系统和有限预算内，先核验物理关系，再拆分取消、数据通道与检测器误差，建立强经典基线，只开发一条路线，最后给出明确动作；它没有保证新算法成功。本轮实际完成这些适用阶段，选择物理关系路线并运行唯一软约束原型。8 dB 的192个共同开发块上，基线、组稀疏、有界参数化、高计算参考、软原型分别错31、36、24、23、43帧。最终动作是记录这次软桥接的可实现性缺口，停止追加采样和第二原型；不主张新方法，也不证明物理一致性方向普遍不可行。正式性能、成本和反证门未通过验证，旧v3 HOLD及研究父任务保持原状态。[研究动作](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/research-action.md)

## 源目标对账

| 源目标 | 状态 | 实际作用 | 限制 |
|---|---|---|---|
| 核对来源和接收机身份 | 完成 | 区分B0、A2和未知的E2接收机；固定旧结论边界 | E2原件仍缺失，未冒充已读 |
| 查物理路径关系 | 完成 | 真实生成器单径、碰撞及秩检查支持归一化增益上的关系映射 | 不把原始增益经过全局归一化写成全局线性映射 |
| 拆分三条误差通路 | 完成 | 256块×3个SNR×8单元，保存取消、数据H及检测器效应 | 混合H和真值参考不可部署，EP10不是最优界 |
| 建立经典强比较 | 完成开发比较 | 八配置共1536次完整接收；保留SBL尺度0.5操作参考和未消除的成本档 | 小样本时延不等于正式A2成本合格 |
| 从结构oracle走向合法原型 | 完成，开发筛选未过 | 同一原支持集内实现组稀疏、两档参数化及唯一软原型 | oracle额外知道几何；不能把两套数据上的差值当因果部署差距 |
| 编码反馈、取消统计、导频备选 | 条件处置完成 | 必要取消校正三臂已测；反馈和导频未选 | 未测分支不能称无效；三种取消模型同错31帧也不证明等效 |
| 独立确认和两个反证场景 | 未启动，按条件排除 | 无合格候选，停止进入确认；两场景已事先登记 | 无正式优越性、邻点无伤害、成本或稳健性通过结论 |
| 落一个研究动作 | 完成 | 记录本次软桥接缺口，不再为该原型补样本 | 项目主张、主线变更和研究父任务仍待用户验收 |

## 施工细节

**生成与信息边界。** 原先沿用旧运行身份容易混淆接收机和留出集。现在以新campaign、独立split及channel/data/noise命名流产生数据，保持既有LDPC和恒等交织；预留流不冒充实际随机化。接收机只收到观测、已缩放导频、噪声及星座，真H和真比特留在离线评分接口。原型回调只接收已有支撑、增益和软信息，最多40个原子、8个由接收机选择的粗中心，不新增真值支持。[数据契约](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/split-truth-contract.json)

**取消与检测。** 导频已含功率缩放，实际取消为 `y-H@pilot`。八单元诊断每次重做取消并重建数据H对应的检测量，保留三个残差能量交叉项；基线正常输出单列。新增物理重拟合在末端替换H，然后同一个H进入取消及一次终端BP/LLR/LDPC，避免只改拟合结果却没有消费者。终端噪声尺度保持冻结，物理回调与取消变换互斥。[接口验证](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/candidate-e2e-smoke.json)

```mermaid
flowchart LR
 A[独立外生块与固定系统] --> B[仅观测的OMP及迭代接收]
 B --> C[冻结末态与原支持集]
 C --> D[唯一物理软约束或经典对照]
 D --> E[重建H并取消导频]
 E --> F[终端BP → LLR → LDPC]
 F --> G[配对错帧统计与预算结算]
 C --> O[隔离的真值诊断容器]
 O --> G
```

**物理结构与经典求解。** 共同交集支持上的自由、组、真实关系、错误关系四臂隔离“知道关系”的价值。为把已有工程拟合也计入3072次上限，在看到结构结果前统一冻结255块；实际结构主批有3060次拟合及3060次终端重放。8 dB自由臂21/255错帧、关系臂5/255，收益6.2745个百分点，同时区间[0.8273,11.3898]个百分点；相对组方法区间仍跨零。合法实现只在S0内限制模板，增益用SVD求解，组稀疏复用ADMM，软约束惩罚与拟合子空间正交的系数。高计算参考达到预登记有限网格坐标驻点，不代表连续全局最优。[结构结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/structure-oracle-results.json)、[算法配置](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/physical-algorithm-preregister.json)

**实现修复与精度边界。** 结构记录曾从基线复制CUDA标签，实际运行在CPU；已修正记录来源，并用原记录、命令和源码哈希约束历史更正，保留原文件，未重跑接收机。另一项跨版本工程回放的硬输出及H相同，软LLR最大差5.329e−15；原始逐数组bit-exact检查仍是失败，后诊断1e−12容差只是明确的工程例外。[设备修复](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/structure-device-correction-review.json)、[精度记录](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/physical-engineering-audit-v9-v3.json)

**开发裁决与共享接口。** 新四臂共768次完整接收全部完成，同192块B_star缓存只复用一次，不冒充新独立重复。原型对基线收益为−6.25个百分点，1个胜块、13个害块，同时区间[−13.614,1.637]个百分点；未达到预登记点估计筛选线，但区间跨零，不能宣布总体显著伤害。经典有界参数化虽少错7帧，也未证明同成本已解决。共享原子支撑、末态、记录schema及调用账本连贯；确认入口没有解锁。[开发裁决](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/prototype-development.json)

## 验证情况

已保存实际服务器运行及退出码：21项数值/契约测试，小模型精确枚举与真实BP差异，N1024工程生成和BP/LDPC链；后续物理模块14项测试与18次完整工程接收。八单元机制有768次正常接收、6144次终端检测；取消校正有576次完整开发接收。最终开发分析核验2304条记录元数据、960个相关快照及共同输入；独立审查阅读消费者源码和分析脚本，没有新增接收调用。[数值证据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/numerical-chain-tests.json)、[完整分析](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/physical-development-anchor-v10-v2.json)

最终服务器检查绑定198个源码文件和已完成输出，原工作进程均退出、GPU无运行应用、无预算预约。收尾结算后累计主机12212.194秒、GPU8168.335秒、CPU核11455.331秒，均在28800秒主机、28800秒GPU、460800秒CPU核上限内；工程完整接收额度128次已用满。[运行检查](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/final-runtime-audit.json)、[最终结算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/final-budget-settlement.json)

没有生成D_confirm，旧D_test没有进入新管线；正式A2成本计时、确认统计和反证场景运行均未开展。每臂3次物理微计时只能做工程描述。整数Doppler与重叠场景已登记，但128块连零不一致时也不足认证严格1%无伤害，不能把未跑或功效不足写成通过。没有另行运行完整论文理论、作者MATLAB代码或全部文献方法复现。

## 后续与复核入口

用户待验收的是上述有限研究动作及其对研究主线的影响；本交工单不自动更新STATE或关闭Trellis研究父任务。原始服务器目录为 `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908`，当前开发批次是 `physical-design-v10`，历史版本源码、原始帧JSON、NPZ和完整调用文件在同根目录。

以下命令只读取已存证据，不启动仿真；在项目根目录执行：

```bash
python3 -c 'import json,pathlib; p=pathlib.Path("issues/2026-09-08_21-06-44-afdm-direction-decision/evidence"); d=json.loads((p/"prototype-development.json").read_text()); print({k:(v["frame_errors"],v["n"]) for k,v in d["metrics"].items()}); print(d["screen"]); print(json.loads((p/"final-budget-settlement.json").read_text())["resources_used"])'
ssh deinlab 'cat /data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908/physical-design-v10/complete.json'
```

交接格式校验与CSV提交属于机械收尾，不增加实验或改变科学结论。
