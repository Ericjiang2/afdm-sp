# 非圆邻域：合法而保守的固定信道参考

目标是补验旧 BLOCK 坐标错误不能排除的局部方向；不是提出新 widely-linear 理论。
冻结 CSTATE 输出信道 A，原第三轮 check prior，y=A(p+d)+w，w~CN(0,σ²I)，E[wwᵀ]=0，独立于工作数据 prior；σ²是每个复观测的噪声方差。
A=Â(y)是固定估计量，使用的是 plug-in working likelihood，不是声称真实 p(y|d,Â(y)) 有该形式。
所有比特 ALL-I THEN ALL-Q，正 LLR 表示0，幅度 a=√(pd/2)。

μI=a tanh(LI/2)，μQ=a tanh(LQ/2)，vI=a² sech²(LI/2)，vQ=a² sech²(LQ/2)。
v=vI+vQ，伪方差 c=vI−vQ；独立比特先验使 I/Q 交叉协方差为零。
非圆性不进入 E‖y−A(p+d)‖² 的额外项：该复二次期望只需要 Hermitian 协方差。
因此不能靠把伪方差机械加进 Γ 改善 CSTATE 目标。

增广实模型 B=[Re A,−Im A; Im A,Re A]，D=diag(vI,vQ)，噪声 σ²I/2。
Gaussian 工作分布的精确后验：

C=BDBᵀ+σ²I/2；m⁺=m+DBᵀC⁻¹(r−Bm)；Σ⁺=D−DBᵀC⁻¹BD，r=[Re(y−Ap);Im(y−Ap)]。

逐坐标 marginal Gaussian 除去工作 prior 后自然参数 ηj=mj⁺/Σjj⁺−mj/Djj，
BPSK likelihood LLR=2aηj。不是将原离散 prior LLR简单再加一次。
ordinary proper 版本用 v 与复矩阵 C=A diag(v)Aᴴ+σ²I，η=μ⁺/v⁺−μ/v，
LLR=4a[Re η;Im η]。圆性极限 vI=vQ 时两者一致。

这是固定估计信道下的一次 Gaussian SISO/EP 式信息提取，忽略信道估计不确定性；
不等于离散后验精确推断、不等于完整非圆 TF，也不证明所用 Gaussian extrinsic 外信息独立。
两臂只隔离非圆工作 prior 的差异。完整 scalar3 先运行，仅 syndrome非零才调用该参考；
不使用真值选帧或选动作。原128开发集已暴露，不能用于总体优越性结论。

验证：test_noncircular_siso.py 以三种小维度检查直接 precision-form 后验、圆性等价、
单位信道下精确 likelihood LLR。实际 N=1024 smoke另对完整矩阵与冻结Channel.apply核对。
任何 inverse/Cholesky失败直接报错，不能用无声数值回退伪装成功。
