# RUN-04 — 固定最终支撑的192帧增益桥接

原RUN03已用fit：D_cal rep30/31/32各frame0..63，原参考A2、SNR8。精确重生六项输入hash，锁定每帧原final40唯一S、原sigma2_final、原BP20iter/threshold1e-4/damp.5与LDPC50iter。只在终端消导频及BP输入把H换成给定S的H_true最小Frobenius投影；complex128参考转complex64供实际检测，记录两者误差。没有重跑上游10outer，没有更新sigma或读取新验证数据。

首帧gainpilot-1788687500成功复用，gainrest-1788687670仅运行余191。总192次终端反事实、0失败/0缺帧，不称192次完整上游重放。原译码错误帧38/192→2/192；三流14→0、12→0、12→2，36修复/0新增错误。FER配对差−0.1875，按三条固定流内配对bootstrap(20000,seed2026090613)95%区间[-0.244792,-0.135417]。信息位错误3025→157。旧raw_errors位于末次BP前，不与新终端raw BER混比。

E_repr均值0.00867954，最大0.02450162；原NMSE均值0.0366860。每流首帧独立生成器密集LS核对，全部rank40且投影差<1e-10；其余解析投影在同已核验整数域运行。实际注入精度导致E最大差7.18e-16。

原源码已按fit192 packet逐文件hash从不可变目录取回：C2-rel仅cand_active_rel，Hcorr禁用，无通道override；H初始零、固定S重构、标量阻尼与逐元素阈值不会引入S循环对角线外非零。192帧S全无位移碰撞，all outer0..9与final相同。由原NMSE及投影残差计算**有效通道超额误差**，均值归一化0.02800646；这包括阻尼/阈值/系数估计效应，不是原raw gain向量误差。原向量没有保存，不声称恢复。

selected residual给Cauchy/triangle交叉项界；另列64eps经验舍入余量，合计最大约1.28e-12；不是严格区间算术证明。既有全部实际数据为正，未clip负值掩盖问题。详细代数边界见mission-gain192-final-support-review、mission-gain-implementation-review与gain-frozen-source-proof.json。

费用：首批queue7.771秒，余批39.051秒；进程合计66.751秒(4核约0.0742 core-hours)，GPU峰1043MiB。观测/投影准备合计41.500秒，终端检测译码7.819秒；包含在连续S2窗口，不替换全窗口计费。末批新增十轮完整性检查和浮点界说明，数值路径相同；完成后又收紧整数ID/NMSE/分母输入拒绝，单测及全部192原记录检查通过，未再运行receiver。原始source hashes分批保留。

证据：gain192-runtime-validation.json、analyze_gain192.py、gain192-reference.json及两个runtime归档。原型输入测试通过，相关py_compile通过。此oracle诊断支持固定S上仍有改进空间，不是可实现算法收益或FER最优界。
