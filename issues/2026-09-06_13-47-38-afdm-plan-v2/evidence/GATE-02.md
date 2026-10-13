# GATE-02 秩、反例和拒绝语义

复用projected_gls白化单位列秩策略10*max(N,K)*eps（K为实际被检验系统列数，增加候选时为原K+1）。当前秩失败返回hold_current_rank/无committed；提案失败reject_final_rank并保留baseline，重复输入列reject_final_columns，容量超限分别hold_current_capacity/reject_final_capacity，不静默删列或jitter。非法C明确抛错。

实际F2P保护反例和扩展邻居gain反例见GATE-01。其他测试覆盖None空池、同actual支撑、drop、topk无F否决、budget0、current/proposal秩亏、非法C、128/64 margin两侧、独立commit副本。同分排名由common_score的float64稳定ordinal规则测试；边界裁剪/邻居合并计数明确记录，容量超限不截断。

reason与action_kind独立：keep/drop/replace不等于判定理由，临界拒绝与变坏拒绝分开。数值模型输入错误保留为异常，不伪装科学拒绝；实际receiver错误传播由WIRE-05验收。仅工程与限定数值契约，不声称CFAR、防假新增、全局收敛或lambda识别。

验证：test_support_transaction 5项 + test_projected_gls 4项 + test_common_score 6项共15项通过，编译通过。良态系统范围，不宣称任意病态输入正确。
