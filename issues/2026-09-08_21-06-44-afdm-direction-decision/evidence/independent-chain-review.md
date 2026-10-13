# AUDIT-00 独立实现链审查

审查者：独立子代理 `/root/csv_review`；gpt-6-astra，low；模型独立上下文审查（未参与这些模块实现）。主会话仅提供范围与原始证据位置。审查没有运行实验、没有访问 D_test。

结论：通过 source-runtime-v3 的生成→估计→取消→真实 BP/LDPC 实现链审核。不是全工作区运行验收，不支持单帧 FER 收益或 A2 成本门。

入口：`CampaignData.make_frame` → `budgeted_support_eval.make_frame`；`ObservedReceiver.run` → `ClassicalJointUnrolled` → `y-Hhat@pilot` → `terminal_decode` → `mp_detect_bp_torch` → `demap_llr/decode_llr`。可部署入口实际只传 y/pilot/sigma2/constellation；真值留在离线审计。

初查三项问题及闭环：
1. 确认锁原接受任意64位hash：现实际读取manifest及授权文件、核hash，绑定协议/方法/各SNR n；未产生真实确认集。
2. 单任务预算不能约束累计：共享flock账本预留/失败结算；硬终止保留reservation。后续多key API复核无新旁路。
3. 小稠密测试原只测枚举自己：现实际调用BP并保存精确LLR与近似差值、旋转对照，不要求近似相等。

原始证据：`numerical-contract-tests-v3.log` 的实际命令与 exit status=0，21项测试OK；`dense-likelihood-bp-v3.json`；`engineering-smoke-v3/complete.json`、`frame-000000-b0-s1.json`；`real-data-pairing-v3.json`；`source-snapshot-runtime-v3.json`。审查者实际读取并核验帧hash、协议hash、核心源码hash一致。

真实工程运行：1次尝试/1次完成；10 outer BP+1 final BP，支撑≤40，真实LDPC syndrome通过。取消相对误差2.05e-16、残差闭合1.93e-16、信道误差闭合3.88e-16。实际生成器6次N1024生成/0接收，跨SNR配对、重复一致、split分离。

版本边界：review时当前logging/run/budget较v3已有新修改，独立review明确不将v3 smoke外推到后续修改；v4日志离线重放与新增预算测试另见`log-budget-v4-audit.json`。后续成本微测和批量run必须保留自己的源码快照与运行证据。
