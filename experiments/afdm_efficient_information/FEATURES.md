# 得分教师与嵌套观测特征

控制教师来自旧 `FiniteControl.uniform(N=4)` 的精确 256-word QPSK / Gaussian 增益边缘似然。路径共同 delay=0；A 为冻结 positive-chirp `Lambda(c2) F Lambda(c1)`，`c1=.37/N,c2=.13/N²`。实际归一化教师使用其自己的冻结输入变换，不能把仅相同 tau/noise 的实际样本称为完整教师匹配。

注册两个公开局部点 `(q,mu,tau,sigma2)=(0,0,1,.5)` 与 `(0,.4,1.3,.7)`，每点独立训练 2048、validation 1024、test 2048 帧，合计 10240。所有层使用相同观测。Ridge 候选 `[0,.0001,.01,.1,1]` 按 validation 的四得分标准化 MSE 选择；test 不能改变模型、层、点或超参数。正式配置为 `FEATURE_CONTROL_CONFIG.json`。

四个嵌套多项式层的 N4 维数为：总能量 1；旧 T 基 4；逐点功率与全功率交叉 18；相位及强度加权相干 90。冗余坐标有意保留以使嵌套关系和独立复算清晰，标准化 SVD 使用固定相对阈值 `1e-10` 并报告全部秩。额外的 gauge 层为 O(N) 全局相位规范的 2N 个实坐标，它是独立输入对照，不是假装成嵌套层。充分性及非圆对称反例见 `SCORE_THEORY.md`。

各层同时拟合完整四列得分，分别保存训练与 test MSE、test 批次标准误、validation 全部候选、训练/heldout 线性矩信息估计、heldout nuisance 重投影和 128 次 bootstrap 的估计分位区间。Bootstrap 反映 plug-in 的有限样本变化，不证明它是严格总体下界，也不证明真实 Phi Fisher 保留率。

训练冻结的 beta 用于单独记录 `s_q-beta_train^T s_eta` 回归误差和 test nuisance 残差。这个随机训练 beta 并不是已知总体有效投影，残差非零不能忽略；用于报告的 heldout 信息会在观测压缩实验内重新投影。该重新投影仅作局部教师诊断，不用于部署拟合或阈值选择。

预先指定的迁移模型是 point1 的 phase 层，选择发生在读 test 结果之前。`model_1_phase.npz` 保存完整标准化/系数、score scale、beta、公开 theta，以及教师的 `teacher_time_words` / `teacher_weights`。迁移复用文件哈希，不手动抄 beta，也不额外训练一份竞争模型。N4 教师匹配采样可直接复用这些时间字；更大 N 或不同 chirp 是单独迁移条件。

记录全部精确教师分解/分量-观测对数、数据生成、所有特征、ridge/SVD、bootstrap 与 test 预测成本。`features_study` 的非交换四状态基例没有随机观测。源码提交、主会话 GO 后才运行 `python -m experiments.afdm_efficient_information.features_study --stage feature_control_v1`。实际 prior 的教师与独立推断会另设阶段，本控制结果不关闭实际先验目标。
