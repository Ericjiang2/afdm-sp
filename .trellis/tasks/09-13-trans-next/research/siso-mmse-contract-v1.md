# 公开近邻 SISO-MMSE 数值合同

REF-02 先构造精确求解校验参考，再处理作者稀疏近似及完整接收机适配。校验参考不是 DI-S-MMSE 仿真复现，不替代 REF-02 的最终验收。

作者代码：[固定提交 3a144fbe4dc92a607b3d1dca0868ebd270421f0a](https://github.com/Alga53/DISMMSE-Turbo-Equalizer-for-OTFS/tree/3a144fbe4dc92a607b3d1dca0868ebd270421f0a)，本目录 `di-s-mmse-author-source/` 保留 15 个原始文件、MIT 许可证、每文件 SHA256 与 Git blob。读取 `MMSE_estimator.m` 与 `DI_S_MMSE_Turbo.m`，未执行 MATLAB 仿真。

原实现使用单位能量 QPSK、逐符号交错 I/Q 比特和卷积码/BCJR，直接传入生成的 H/Tau/Nu。首轮 GMRES 解两个系统并近似共享 xi，后续 FSPAI 近似逆矩阵。适配不能接收真实 H 或 Tau/Nu，不能沿用其 Es=1 的 LLR 系数、共享 xi 近似或忽略近似求解状态。

## 精确 Gaussian SISO 参考

观测边界为已抵消导频的 z、估计 H、噪声复方差 sigma²、外部码先验。对 QPSK `x=a(s_I+i s_Q)`，独立比特先验的均值 m 与复方差 v 由 tanh 求得。令

`C = H diag(v) Hᴴ + sigma² I`，`r = z-Hm`，`xi_j = h_jᴴ C⁻¹ h_j`。

Sherman–Morrison 恒等式给去除整个符号 j Gaussian 先验后的似然自然参数

`eta_j = [h_jᴴ C⁻¹ r + xi_j m_j] / (1-v_j xi_j)`，`tau_j = xi_j/(1-v_j xi_j)`。

其中似然与 `exp(2 Re(eta_j* x_j)-tau_j |x_j|²)` 成比例。恒模 QPSK 的通道 LLR 为 `4a Re(eta_j)`、`4a Im(eta_j)`，按本项目 I-then-Q 输出。当前 a=.5，系数为 2；作者 Es=1、a=1/sqrt(2) 时为 sqrt(8)。这不是观察模型的精确离散边缘化，其他符号仍被 Gaussian 近似。

使用 complex128 Cholesky，一次分解、N+1 个 RHS，不使用逆矩阵近似或首列共享 xi。零列给零通道信息；有限饱和码先验允许 v=0；不加入隐藏 jitter。检查线性残差、杠杆量实数非负和外信息分母正性，失效直接抛错。全矩阵残差核验本身的计算成本计入此校验实现，不称免费。

## 验证

五项真实测试通过（deinlab 既有 AFDM 环境，0.071 秒）：逐符号单独剔除先验后的独立 solve；对角信道四星座枚举似然及两种功率尺度；自身符号先验变化不改变自身外信息；零信道/饱和先验；非法输入。源码快照 `source-siso-unit-v1` 的 SHA256 为 `74fe929bc1bba8d0d0ba41b9ffe776e002c1f02fe02c2527e093e90fcecf9656`。

本地 bundled Python 因缺 SciPy 在导入阶段失败，未运行数值测试；该失败单独保留，没有安装依赖。上述通过结果来自服务器实际执行，不来自静态检查。

下一工程仅复用已审计参考的终端 H/观测，先测 N=1024 求解可行性、原始重读与实际费用，再决定完整链适配的预算。它不代表联合 CE 性能，也不能把精确求解的性能或费用归给作者的稀疏实现。完整 REF-02 尚需稀疏近似合同及完整链对照。


## 完整链适配合同（实现前登记）

显式 `detector="siso_mmse"` 只用于 CPU 推断；默认 None 保留原 BP/PIC 数值路径。共同接收机的 CE、信道掩码、阻尼和残差噪声更新继续执行；SISO Gaussian 干扰矩只由当前 check-extrinsic 先验计算，不取已经看过 y 的检测后验充当独立先验。SISO 后验通过既有 CodeFeedback 捕获及 CE 消费路径交付。

完整外层要求启用既有 CodeFeedback、rho=.5，以共同接口交付 CE 矩；零码消息使用该接口的 zero 控制。完整链终端使用最后一次合法交付的 detector code prior；独立 terminal_decode 未提供先验时为零；共同 LDPC 消费 SISO 的 channel extrinsic LLR，不能把 posterior LLR 再送回同一译码器。该完整链与此前零先验缓存终端报价不同。每次返回分解/RHS/残差记录，audit 保存实际 H、取消后 y、sigma、prior 及 SISO 输出。SISO 不执行 BP 图扫描，拒绝 BP 调度/温度/非圆控制混用，不伪记 BP 次数。精确稠密参考仍不称作者稀疏算法复现。

先运行真实小码完整链，验证非零反馈进入下一 SISO 与终端、CE 消费一致性、默认链保持及非法组合拒绝，再单独冻结 N=1024 工程预算。

验证：v2 的26项真实测试通过（1.061秒），包括原始 frozen-forward 默认链比较；新增 run_arm 记账后 v3 的10项定向测试通过（0.209秒）。v1 的一个错误 dtype 断言和两个缺失协议文件错误完整保留，未改接收算法或放宽容差来消除失败。N=1024 20F工程尚未启动。


## 固定开发审计与比较（完成开发数据前登记）

128F开发批复用前32个开发外生块。全部SISO输入、输出、CE/码先验交付、真实LDPC重放和原始哈希均核验；独立逐符号cavity解的固定子集为每个完整接收机的外层0/2/9及终端，各检查符号0/512/1023，共1536个符号方程。其余SISO状态核对先验/后验矩、LLR/自然参数关系及生产者记录的实际残差，不把子集审计写成所有状态的独立重解。审计CPU单线程1800秒，新增输出1GiB以内，不生成新F。

开发风险比较预先固定：SISO_MEAN与SISO_REF47各自对BP MEAN和REFRESH47，在7/8dB共8个配对比较；记录救回/新增错块、exact McNemar及Holm8。跨SNR共享外生块，重复或跨SNR不得加作独立样本。只作开发判断，不更新正式CONF/COST或科学主张。精确SISO若没有实质收益，仍可作为强参考资格结果；它本身和标准FSPAI均不是本文新方法。


## 作者 FSPAI 适配边界

直接读取固定作者 `FSPAI.m`：先对协方差归一化阈值建边；当一个结点含自身的边数不大于 maxDeg 时，仅保留自身；每列从自身开始，选择下三角邻居中 `|A[J,c]ᴴL[J,j]|²/A[j,j]` 最大者，以小系统更新稀疏逆Cholesky列，最终精度近似为 `L Lᴴ`。这里 maxDeg 并非普通的“最多保留若干邻居”；不能凭名字反转作者条件。

AFDM适配从估计H和码先验方差构造 `C=H diag(v) Hᴴ+sigma²I`，按实际归一化C支持建邻接，不读取作者OTFS真Tau/Nu。列内候选按索引升序处理，平局确定性选首项；明确区别于原几何遍历顺序。先固定 graph_tol=.001、degree_cutoff=3、max_added=8、selection_tol=.001，只做小系统代数资格；max_added是本适配有限预算，不冒称与作者P完全相同。零阈值和足够列预算必须还原精确逆，有限预算仅为近似，必须保留失败与误差。构造SPD由合法H/非负v/正sigma提供，不用隐藏jitter或求解失败转精确的静默fallback。共享xi和GMRES另行资格，当前不启用。
