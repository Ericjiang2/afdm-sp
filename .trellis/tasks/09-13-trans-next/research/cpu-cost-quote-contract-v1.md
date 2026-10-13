# 完整CPU成本报价合同

复用既有8个开发块、7/8dB，两臂均保留终端码先验并使用普通syndrome早停；只改变外层BP的dense/整数COO表示。2次配对重复，按块/SNR/重复序号交替顺序，共64F；另在块0、7dB先做4F预热。单一进程、同一receiver实例贯穿预热和测量。N=1024、CPU单线程、gels；所有前序作业退出且raw PASS后准入。600秒、4GiB，另68次最终LDPC回放在全部计时调用完成后执行。

计时边界为公开run_arm(audit=False)完整调用，含OMP/CE/BP/译码/控制器；不装OperatorProfile、不保留完整图/CE/反馈审计数组。记录序列化、回读、离线评分及最后68D不计入接收机时延；setup单列，冷进程启动由launcher wall体现，不混入稳态均值。RSS是共享Linux进程高水位，不能解释为每臂新增内存。重复计时不算独立信道样本，不生成新CONF。

每条结果保存并回读全部返回数组，全部13个公开数值字段和外层BP调度须与已raw PASS的稠密保留+早停参考精确一致；观测前后哈希相等、原始外生输入/LDPC/源码/合同哈希绑定。最终LLR按原clip20/maxiter50重译码，decoded/info/syndrome必须相等。保留失败和实际预约。

现有receiver_resources依赖audit图/CE数组，audit=False会漏计CE且终端非空时索引失败。本报价不调用它；完整算子次数只引用已审计参考并标明来源，外层调度为本次实际记录。正式COST仍需补齐廉价实际CE和终端计数。本批仅给出全流程优化量级及后续样本/规模报价，不能据8块宣布正式成本门或Trans贡献。
