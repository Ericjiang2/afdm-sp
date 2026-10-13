# 固定强参考前缀的终端信道干预

先前32A结果不能从Frobenius误差直接推出译码原因。本批冻结所有既有32开发块、7dB、完整BP_RETAIN前缀（不使用STOP）及最后合法check先验、原sigma2_terminal。分别把终端H置为原估计、原观测支撑上的Frobenius最优投影、原始完整物理H；各自重新计算y-H pilot。

共96T后96D，600秒、8GiB输出、CPU单线程；BP温度2、20迭代、LDPC maxiter50、clip20、原有限字母分支不变。每块EST须先精确重现原七个终端字段，然后才执行两个oracle。所有终端原始状态重新回读，核验输入、导频抵消、实际消费先验、原始外信息/APP关系、算子调用与边计数；每个LLR独立重译码并收费D，192记录全部回读。使用既有接收机与共享回放原语，不改运行快照。

这只检验固定前缀、固定旧先验和方差时的干预效果。SUPPORT_ORACLE并非FER最优增益；TRUE_H仍面对旧先验/方差，因此不是全局可达性能上界。若oracle仍失败，不能否定重估先验/方差或全链改进。成功/失败块均保留，32旧开发块不构成新独立确认；不调参、不提前停止、不把oracle当部署方法。

合同：Mission `contracts/strong-terminal-oracles-v1.json`。原始源码清单2fd0beb6，投影summary fb231843，完整强参考summary 85672915。结果与自审证据待实际运行后另存。
