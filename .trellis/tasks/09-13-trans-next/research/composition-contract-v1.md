# 整数图与QPSK解析投影组合工程

复用trans-retained-stop-v1，仅新增显式bp_edge_projection=qpsk_tanh的工程准入；尚不支持开发阶段晋级。四臂为原BP_REF47、整数+解析投影BP_RETAIN完整链、该链普通早停及重复。2个既有工程块×7/8dB=16F，600秒、4GiB、1CPU线程。底层数值接线已存在，不复制消息算法。

与已raw PASS的旧整数图工程逐条比较：support/x_hard/decoded/info_hat/decode_ok精确，连续量rtol1e-5/atol1e-6；缺席终端sigma2_terminal必须双方同为None，不能拿数值替代。新完整链与旧外层+受控终端参考只作全链软/硬资格，不再把其内部轨迹描述为精确相等。新增完整链本身作为早停的精确前缀参照，重复所有数值精确。既有CE/反馈/LDPC回放、每次整数图完整H相等和实际工作计数保留。

共享projection_reference_records在runner和auditor绑定同一参考summary/raw audit，运行前后复核。v2共54项真实CPU回归通过（1.499秒），源dda768131432c43757e5a67034008a311d23f4b16e127aee47770d60ae2ae155。工程raw通过后才讨论组合完整成本报价。两项已有优化的组合不自动成为新颖贡献，单独整数图14%左右报价仍未达25%设计目标。
