# 无审计调度仍建完整图账本：根因与修复

成本预检发现：`UniformBPSchedule` 原用 `scheduled_graph` 读取 `payload['edges']`，无论上层是否audit，都传入BP的graph observer。后者调用完整 `actual_bp_graph`，转换/哈希/扫描H并计算能量。整数COO路径还会为此物化H。因此 `audit=False` 未兑现完整图审计关闭的预期，不能在这个路径上判定结构优化的部署收益。

真实小接收机用会抛错的 `actual_bp_graph` 复现了该问题（v1）；另外v1测试传输脚本继承了旧“v1不覆盖direction_receiver”的历史条件，引入无关旧接口错误，失败保留。v2基于已资格整数图快照并显式包含全部接线文件，避免将部署脚本错配误作算法失败。

修复只分离计数接口：BP的 `edge_count_observer` 接收一次实际阈值后E，无完整图账本；调度器沿用原 requested/executed 字段，空图实际迭代为0。Gaussian/有限先验等消息算术不变。graph observer仍由显式audit控制，完整审计能力保留。

48项真实CPU回归通过（1.278秒）。包含dense/COO无audit时禁止完整ledger、相对audit=True的完整数值及schedule记录相等、空维/空图/阈值边计数和非法观察者。v2快照SHA256 `7b92866fcd5543450c3be973851eedea1ea485a8c61e5f75b2af51e33bf707e0`。尚需N1024原始复验与无audit完整成本报价；旧128F整数开发继续使用原始9f92efcf快照，未中途改源码。

公开 `run_arm(..., audit=False)` 接线与关闭反馈数组保留的数值不变性已加入真实测试：v3共49项通过（1.348秒），源码快照 `ec2fa90c33476dda21406be57843e3c5f601536ec35ea23963cd4641457f80dc`。默认audit=True保留。完整计时使用这一公开入口，不包裹OperatorProfile；计数修复的N1024 16F已完成，原始审计1980数组、114CE、52次LDPC通过。
