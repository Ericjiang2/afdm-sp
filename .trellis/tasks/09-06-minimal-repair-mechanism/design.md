# S4 首批技术设计

入口：S2 SNR8 三流192帧 baseline=28帧错，真符号DA-LS=0，最佳实际支撑增益=2；这是离线选路信号。GPU纯观察192帧 H/x/误码全同；后期概率偏自信只用于诊断，不据此直接选温度。

## 第一步：有限星座与均值反馈

复数观测 z=a+CN(0,v)，均匀先验 p(a|z)∝exp(-|z-a|²/(T v))；mu=sum(p*a)，v_finite=sum(p*|a-mu|²)。所有数据星座已含 sqrt(1-rho)。用中心二阶矩避免减法产生伪负方差；不改变旧 T=1 算术分支。

在现有 _qpsk_soft_decision 增加 keyword-only temperature=1，T=1 不执行额外除法。forward 暴露 dals_temperature=1，仅 DA-LS 使用；noise_feedback、BP 与最后 LDPC 不变。普通标量配置不接受真值输入，观察器仍只读。

## 分割与选择（采集前冻结）

SeedSequence([20260905,split,rep,frame,stream])；dev=1 保持原字节序；cal=2。
D_cal 校准反馈数据：rep=10/11/12，fit frame0..31，validation32..63，SNR8，coded，每区96帧。旧400帧先验校准独立生成，逐种子和输入哈希查碰撞；smoke rep997 不纳入选择。

只在 baseline 轨迹上比较固定 T∈{.25,.5,1,2,4}，按 fit 全部DA-LS迭代等权平均symbol NLL选一个全局T，平分优先距离1最近。validation只报告，不重选。后续闭环反馈会改变分布，必须在D_dev三流验证FER，不把离线NLL改善称为闭环收益。

首批 D_dev SNR8 rep0/1/2，每流64帧，配对 baseline / temperature_mean。开发骨架仍沿用 expanded-count nomination；不称部署公平比较。温度配置和Dcal来源hash写入每个run。

## 后续入口

J_soft 的固定支撑目标应包含期望残差 trace 项；H V H^H 协方差入口需明确冻结H和噪声尺度。先做小N稠密参考与v=0退化、Hermitian正定和目标下降契约，再运行。联合入口不自动授权为最小版本，若执行须登记同一近似目标和额外消融。

## G/V 入口冻结补充（运行前）

M：温度有限均值，旧 proximal DA-LS。G：相同mu/v，最小化 ||y-A(mu)g||²+g^H Q(v)g+lambda||g-g_old||²，其中 Q_ij=tr(D_i^H D_j diag(v))。整数不同位移时Q=sum(v)I；同位移冲突组按实际相位加权Gram计算，不能静默用对角近似。只对该冻结增广目标声明局部下降，不宣称EM或跨外环单调。

V：冻结更新前H及mu/v，C=H diag(v)H^H+sigma²I；最小化 sigma²*(y-A(mu)g)^H C^-1(y-A(mu)g)+lambda||g-g_old||²。sigma²系数保留原lambda单位，使v=0精确退化为同mu的原proximal DA-LS。它是冻结C的GLS增益入口，不是改变scalar-BP噪声，也不与G的Q相加。用Cholesky同时解A/y，全部N×N成本记入计时。

初批M/G/V使用同一Dcal标量T、同支撑动作、同噪声更新和后续BP/LDPC，禁止联合入口。先2帧有限性/回放/成本smoke，再三流各64帧SNR8。若单帧成本或失败显示不可行，保留参考定位并按预算终止相应分支。
