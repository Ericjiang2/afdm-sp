# v3 COLOR-01：实际编码二阶门与修订提案

## Target / Status

目标是验证实际coded SP与Gaussian对照二阶严格匹配；当前状态 **NOT YET COHERENT for registered proper-G**。原v3明确要求P非零则ENGINEERING_BLOCKED，不静默改IID。未运行COLOR科学矩阵，未消耗4224初始预算。

## Invariant Object / Assumptions

固定真实生成矩阵G、均匀独立信息bit、实际调制顺序[全部I码位,全部Q码位]和已含数据功率q=0.5的d。G行均非零，信息bit无额外偏置。全码字独立性不作假设。

## Notation / Strategy / Derivation Map

编码bit是GF(2)线性形式c_i=g_i u。令b_i=(-1)^{c_i}，B_ij=E[b_i b_j]。先求B，再通过实际QPSK映射求R=E[dd^H]与P=E[dd^T]，最后审查proper Gaussian能否匹配。

## Main Derivation

[命题] 非零g_i使E[b_i]=0；若g_i=g_j，则B_ij=1；否则g_i+g_j为非零线性形式，B_ij=0。均匀u是此步骤条件。

[恒等式] d=sqrt(q/2)(b_I+j b_Q)，所以
R=q/2(B_II+B_QQ+j(B_QI-B_IQ))，
P=q/2(B_II-B_QQ+j(B_IQ+B_QI))。

[实际原件] deinlab旧gainrest源码缓存，G形状2048×1024，SHA256 bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af。2048行非零，但2045唯一。重复行（零基索引）：[2046,2047]、[878,1566]、[66,932]。R相对0.5I的F范数偏差0.03827327723；R偏差6个非零项。P有6个非零项，F范数0.6123724357，最大绝对项0.25。

[推论] H sqrt(q) z在coded输入层的R/P均不正确；即使替换成HR^(1/2)z，proper z仍不能匹配非零P。此处不是采样误差，不能通过4096抽样检查掩盖。

## Remarks and Interpretation

4项小维工程unittest通过，包括穷举全部合法信息消息验证重复码位的R/P公式。它们不是完整实际码字总体枚举。实际矩阵只读核验；未修改编码器，也未把合法编码换IID。

## Boundaries and Non-Claims

原proper-G矩阵暂停。BASE、STAT、SIGMA、POOL在实际coded A上继续不受阻。此发现不证明终端故障由重复码位主导；不把3.827%矩阵偏差当性能损失。

## Open Risks / 具体待批准修订

建议保留真实码字，改用增广实Gaussian：x=[Re d;Im d]，Sigma_x=q/2 B，由唯一非零码位关系构因子L（每行在对应唯一关系列放sqrt(q/2)），令x_G=L xi，xi~N(0,I)。这保证R/P同时精确匹配，无jitter，复杂度接近当前逐码位生成；H作用后同样匹配。W保留proper各向同性同总期望功率参考，故G-W结论名称改为“完整二阶非各向同性影响”，不能再唯一称Hermitian协方差方向影响。A-G仍是匹配全部二阶后的分布差异。

保留原12单元、48H×4重复、工程与影子数量及全部预算上限；不新增科学比较。工程32探针的期望实协方差改为Sigma_x。主会话更新CSV/COLOR假设与判读，冻结后再发车。另一合法处置是本轮COLOR记ENGINEERING_BLOCKED，ROUTE中颜色因果证据不足，其他任务正常完成。此为科学对象修订，须用户确认，不能以远端上传授权代替。

执行授权：用户已明确确认「采用增广实 Gaussian 修订」。以上修订作为当前COLOR契约。原proper-G失败仅为历史发现；更新后须重新通过工程验收。

## 修订后工程验收

状态：COHERENT AFTER REFRAMING，用户已批准。增广实因子同时匹配R/P；complex128最大相对误差4.15e-16、complex64最大2.13e-7，均满足1e-10/1e-5。4096样本、32实探针的均值及方差共64个检验，family alpha=0.01，全部通过；未重抽样。输入零C、奇异C、非finite/负功率处理有单元覆盖。远端颜色与SPEC共9项测试通过0.260秒。独立原件G证据及ENGINEERING结果在mission/evidence下，工程不等于科学矩阵通过。
