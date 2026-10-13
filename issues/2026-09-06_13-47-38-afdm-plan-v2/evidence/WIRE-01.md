# WIRE-01 真实CLI共同容量接线

真实CLI指定 --receiver-shell direct40 --active-cap40 --arms a0 baseline，并消费SHA256 74f23844a95ea36ea90490f7aa5fca76bd14ff8a97f954f4387a4e85c852444e 的400帧prior。build_receiver→run_frame→forward→H_est→末次BP→demap_llr→decode_llr完整运行，2帧/两臂退出0。代码与配置hash见a0-a2-wire-runtime.json，packet见a2wire-1788678714-packet.json。

主会话逐帧断言：nomination40/extension0；初始化及每轮/最终≤40；F2P临时44/48≤单独登记上限48。A0无修复且scorer准备0；A2启用修复。同一frame输入hash与此前A0-only完全一致，A0 H/x hash也完全相同，说明混合批次共享准备未改变A0行为。coded字段LDPC、decode_ok布尔、finite成立；两臂info_errors均0仅为工程烟测。

先前错误记录保留：初次top-level源码部署缺失cao_baseline导致import失败；完整子包隔离快照修复后通过。缺失prior、错误nomination/schema/CLI容量冲突显式拒绝。

边界：实际consumer接线通过；RUN-02仍负责关闭新路径的历史完整错误向量回放与复数求解门，不在此代签。后续评价不能拿2帧零错当方法通过。
