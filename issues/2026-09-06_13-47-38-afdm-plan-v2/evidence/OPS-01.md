# OPS-01 开发队列与恢复验收

实际服务器证据：两次独立进程组的CPU prior/GPU A0 pilot，SSH退出后重连读取PID(start_ticks/boot_id)、退出码、日志及原始帧。每槽4线程，核16—19和20—23不重叠；GPU从不超过2个开发槽起，固定22GiB门和每作业预留。先导GPU采样峰值648MiB，不能冒充瞬时绝对峰值或正式计时。

不可变packet含完整Python子包源码hash、参数列表、样本manifest路径、预算/余量和绝对截止；source检查在发车前执行。checkpoint/prior/LDPC/hash进一步在receiver契约冻结。队列flock拒绝重入；旧存活PID同时比较boot_id和start_ticks；已尝试packet不隐式重发，主会话根据完整输出登记缺帧恢复。

prior恢复的单位是完整frame.pt：manifest/source/config/identity匹配、不可变发布、只补缺失、失败记录保留。CPU测试证明少一个frame只调用该seed，已存帧字节不变。receiver使用run-contract+原子frame JSON；JSONL只是顺序导出，旧状态和导出保留。真实CUDA coded CLI恢复computed_frames=0/restored_frames=2、退出0。错配置、损坏、重复发布及重入测试均显式拒绝。

截止实测：初版约0.414s清理超时保留；修正后将6s清理余量计入预留并提前停工，deadline-cleanup-regression.json证明在绝对截止前5.759s结束，子进程-15且/proc不存在。另一过期manifest在投递前已被拒绝，没有产生样本；不当作成功运行。

验证：16项本地契约测试+py_compile/diff检查；真实N1024 prior2、A0 coded2、receiver同帧恢复2、独立超时夹具。原始证据见pilot-engineering-20260906.md及同目录runtime JSON。科研400先验与A2结果仍由RUN-01/02验证。

条件边界：当前只开放S2/S3S4开发队列，S1和正式S5—S7被阶段校验拒绝；正式G2尚未激活，必须由TIME相关行落实GPU/CPU独占，不能将本队列并发耗时作为正式证据。没有实测收益前不开放3—4槽。local-actions旧枚举CLI暂不支持直接resume，后续动作任务需按不可变单动作/帧分片登记，不能盲重跑部分输出。
