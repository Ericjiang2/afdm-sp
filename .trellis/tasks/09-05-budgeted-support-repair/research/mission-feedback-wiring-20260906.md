# FB-02/03、WIRE-06 最小反馈接线（2026-09-06，只读）

已读CSV及v2 130—147行。当前工作树没有`soft_feedback.py`；实际函数在`classical_joint_unrolled.py`，测试为`test_soft_feedback.py`，不应凭文件名另建第二套实现。以下只读设计，未运行实验或修改代码/CSV。

## 当前实现与可复用函数

- `_qpsk_soft_decision`（约371）：工作高斯方差 `v_n=sigma2/clamp(diag(HᴴH),1e-10)`→logits→有限星座p→mu；`return_variance=True`时以 `sum p|s-mu|²` 返回有限星座v。已有observer传detach/clone的logits/p/mu/input_variance/constellation，但没有把返回的有限v传入payload。
- `residual_data_covariance`（约281）：C=(H*v[None,:])Hᴴ+sigma2 I，已约束v非负有限，不再乘(1-rho)。`soft_gain_update`（约290）统一原均值近端解、Q目标或sigma2 C⁻¹加权解；C和Q互斥。
- DA-LS分支t≥1：用**进入本轮更新前的当前H_hat**生成p/mu/v，在同一H_hat上构C，然后调用一次soft_gain_update，更新gains_S。现`dals_mode`只有mean/jsoft/covariance，需要新增显式v策略，不重启J_soft。
- `diagnostic_data_override`只在DA-LS构造x_total前替换x_hard_scaled；runner现oracle_data已用此入口，真实缩放data没有直接送decoder。之后H/sigma/输出变化是该干预的自然闭环影响，不是oracle泄漏。
- `return_trajectory`现记录每outer结束H/x/sigma/resnorm，**不是**DA-LS输入边界；此时旧gain已被覆盖且sigma可能已更新。不能据它重建共同状态的旧g。
- `budgeted_support_diagnostics.feedback_statistics`已有NLL/Brier和温度扫描及绝对v分箱，但新协议要固定T1、分箱v/(1-rho)、高置信错误以及帧级FER关联，旧结果不能直接代签。

## 四臂只需要一个DA-LS消费者和一个v策略开关

建议显式字段 `dals_variance_policy={'none','uniform','dynamic'}`（命名可遵现主会话规范），与旧dals_mode兼容映射在一个入口集中验证，不在多处分叉：

| 臂 | mean来源/温度 | 近端目标权重 |
|---|---|---|
| F_mean | 当前有限星座mu，T1 | I |
| F_uniform | 同一mu，T1 | sigma² C_uniform⁻¹；C_uniform=H_current diag(v0)H_currentᴴ+sigma²I |
| F_dynamic | 同一mu，T1 | sigma² C_dynamic⁻¹；仅把v0换成当前p产生的v |
| O_data | 仅在DA-LS mean入口替换真实缩放data，T1其余原样 | I，与F_mean同路径 |

uniform v0由**实际已缩放星座**按均匀概率计算 `mean(|s-mean(s)|²)`，广播到N；对当前零均值QPSK它等于1-rho，不直接硬编码.5。uniform/dynamic都取本轮进入DA-LS时的H_current及sigma；不要uniform冻结H0或改温度，否则不是单策略差异。两者可复用residual_data_covariance+soft_gain_update全部代码。

CLI arm注册→run_frame映射→forward字段→DA-LS构C→soft_gain_update必须有实参证据，不只在JSON写不同arm名。原covariance臂可映射dynamic；旧temperature_mean及legacy研究结果保持自身配置，不把新T1硬改旧基线。四臂固定新壳/支持初始修复/检测器/LDPC接口，禁止同时挂新score×V矩阵。

uniform/dynamic自然闭环后H、sigma、mu会分化；仅“策略参数只不同v”成立，不得说每轮输入数值只有v不同。必须结合共同mean轨迹离线对照完成矩输入归因。

## 共同状态快照：在真实增益求解前一次采集

新增 `diagnostic_dals_observer=None`，触发位置在mu和A_total/lambda已确定、`g_new=soft_gain_update(...)`之前。仅F_mean记录共同轨迹；payload至少含：

- run/config/frame/arm身份及outer_iter，support有序delay/doppler与原子ID；
- H_current、mu、finite_v、working_gaussian_variance、sigma2_current、g_previous、lambda_ls；
- A_total、y_daft、x_pilot_scaled（或足够重建A的固定配置），星座、p/logits及其单位；
- 若误差方向需要H_true，只在runner离线分析层关联真值，forward不接收H_true。

必须在赋值gains_S前clone旧g；H也需要clone，不能保存会后续覆盖的引用。t0仅OMP/repair，没有DA-LS事件；10outer对应t1..9共9个DA-LS输入，不伪造第10个求解。noise_feedback另有stage，不能与dals_feedback混用；现其调用未传dals_temperature，保持T1并显式记录。

大Tensor快照若常规每帧全保存会很重，至少对固定48帧协议预估磁盘/拷贝费用；可以按矩阵hash去重静态y/pilot/support，并保留可重建的不可变完整内容。仅保存hash不能满足离线求解。先完成receiver后再离线统计，避免observer内部做三次额外求解干扰接收路径。

离线三目标共享同一A、y、旧g、lambda、H_current、sigma和mu：

J_unweighted(g)=||y-Ag||²+lambda||g-g_old||²；

J_uniform/dynamic(g)=sigma²(y-Ag)ᴴC⁻¹(y-Ag)+lambda||g-g_old||²。

分别调用现soft_gain_update求解；记录各目标对旧g/各解的评价、矩条件/谱范围、解差、残差方向及重建H误差。不同权重下目标数值不直接作为跨目标“更优”排名；使用同目标下降和共同物理误差评估。C一次求解内冻结，不能边求g边重算C；H0结构可另加离线标签，不能混入uniform主臂。离线解不经完整下游BP/LDPC，就不产生FER。矩运算成本独立记账。

## 三种方差与固定可靠性协议

1. BP Gaussian `var_post`：检测器posterior输出；outer当前只取mu_post，最终BP的var用于LLR。
2. working_gaussian_variance：_qpsk_soft_decision的sigma²/HH_diag，用来构造工作分布p。
3. finite_symbol_variance：由同一p和已缩放星座产生的sum p|s-mu|²，只有此v进入dynamic C。

三者不能字段复用。建议将现返回variance同时放到observer payload（同一计算结果），避免statistics再用`E|s|²-|mu|²`算出小负v并clamp而与消费者不一致。F_mean若原不算finite v，可在离线从保存p/constellation用同一稳定公式计算；不要为了观察无意改变主mean的GPU运算序列。

固定T1统计避免复用旧temperature_grid扫温度选择。可在实现前冻结归一化边界 `[0,.02,.05,.1,.2,.4,.7,1]`（这是建议协议，主会话正式写入manifest后才算冻结）；左闭右开、最后一箱含1，越界/非法项单列而不是clamp吞掉。0≤rho<1且星座能量匹配时归一化才有效，rho=1是无数据功率范围，显式拒绝或单独定义。

每stage/outer/bin报告符号count、sum v、sum|x_true-mu|²，汇总NLL/Brier；高置信集合max p≥.9，错误用argmax p对应符号与真值不等定义。保存高置信总数/错误数两分母（条件错误率、全符号高置信错误频率），以及该组v/实际误差；按frame_id关联**该臂真实最终FER**，不将符号当独立帧扩大样本量。至多3例按预设frame/symbol ID顺序取，不能按效果挑最好或最坏后当总体统计。

## 工程和无扰动验证边界

最小契约：均匀p时dynamic C与uniform C一致；点质量v=0时C=sigma²I、weighted soft_gain_update退化原unweighted；缩放星座v线性随功率变化，C不重复乘功率；固定H/mu/sigma/g的离线三目标解符合独立小矩阵dense参考；oracle只影响DA-LS的mean输入，scorer、noise反馈与decoder无直接truth实参；uniform/dynamic在同一快照上除v策略外配置及来源hash一致。

观察器开关必须在相同快照/设备/固定输入上比较H_est、x_soft、sigma、最终BP mu/var、LLR/decoded bits；不是只比FER或宽松allclose。已有CPU gelsy重复同输入会漂移，不能把CPU on/off差异直接归罪observer；也不能因此放宽真实GPU门。observer即使只clone/增加GPU操作也可能改变后续执行和浮点路径，需固定同设备回放及off/off控制；若off/off都不一致，先标数值不可判定，不报observer透明。

费用包含快照拷贝/同步，receiver完整elapsed保留，同时单列observer与离线三目标费用。真实GPU smoke应验证9个DA-LS边界、四臂实际消费者、oracle隔离、逐outer当前H/sigma变化；run条件不足明确未验，不能用本地函数测试关闭WIRE-06。
