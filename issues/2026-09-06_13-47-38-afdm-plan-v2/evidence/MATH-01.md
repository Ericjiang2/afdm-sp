# MATH-01 固定模型投影恒等式验收

状态：COHERENT AS STATED。不变量 J(S)=min_g ||L^-1(y-Phi_S g)||²，C=LL^H。投影到当前白化支撑正交补后，新候选仅增加v方向；对复增益最小化||r-vh||²得h=(v^H r)/(v^H v)，下降D=|v^H r|²/(v^H v)。仅对冻结C/y/Phi/S的纯添加成立；不证明保护剪枝后的事务改善、FER单调、CFAR或真实后验校准。完整推导与排序反例见父research/mission-math-reference-20260906.md。

实现 projected_gls.py：Cholesky白化，单位列SVD秩契约，QR当前投影和增益；候选同时投影，返回D/q_perp及拒绝原因。当前秩不可靠HOLD；候选秩不可靠拒绝；C非法不加jitter。空支撑、活动冲突、重复ID和dtype/device均有显式边界。

独立参考 test_projected_gls.py 使用 NumPy Cholesky及逐列SVD全量重拟合，直接回代残差差值，不调用被测投影公式。16种良态组合/32个候选对照：complex128按max(1e-8*|Dref|,1e-10*E)，complex64按max(1e-3*|Dref|,1e-5*E)，E=max(1,||Wy||²)，全部通过。另含空S、有色/白C、复原子缩放、信号/协方差缩放、零下降、重复/近共线秩边界、非法C、白C单位范数复数排序反例。

实际命令：OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 /opt/anaconda3/bin/python -m unittest afdm_sp_joint_unrolled.test_projected_gls。4测试通过，最新session35081为0.040s/exit0；py_compile通过。最初缺少projected_gls模块的ImportError保留为实现前失败复现。

范围：真实Torch CPU数学组件与独立NumPy参考，非receiver/GPU/LDPC集成。SCORE-01负责冻结prior数值和Lambda装配，GATE行负责完整动作目标，WIRE负责实际消费者，均未被本行代签。
