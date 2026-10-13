# GATE-01 完整支撑事务组件

support_transaction.finalize_support_transaction接收共同保护/剪枝后的nomination，复用实际expand_cluster_support边界裁剪/去重，检查最终active cap，再调用projected_add_statistics(...,candidates=[])做完整GLS refit。baseline和proposal同一规则，J直接用实际待提交gain回代白化残差计算，并与投影目标核对。lambda=tau=0固定，其他值明确拒绝。无F门臂也不能绕过工程秩/容量检查。

只在最后选定baseline/proposal状态；返回committed完整独立副本，包括nomination、actual IDs、delay/doppler、gain、J/F、秩、dtype。拒绝时不泄漏临时gain。delta严格大于eta*max(1,|F前|,|F后|,||Wy||²)才接受；128/64分别1e-10/1e-5。一个提案预算=一次完整事务；拒绝后stop_reason是proposal_budget_exhausted，不声称其他候选无效。

真实组件集成：test_support_transaction调用实际F2P保护/剪枝得到提案，再经过实际扩展和GLS finalizer。K1,y=(1,.25,0)强制保护e2，纯加有利但最终交换变坏，拒绝且恢复gain1。扩展反例y=(1,3,2)，nom0→2、extension1，实际active{0,1}→{1,2}，J4→1，提交gain(3,2)，不能沿旧邻居零填充(0,2)。

5项事务测试+10项相关数学/评分测试通过，编译通过。尚不声明forward已消费committed状态；WIRE-05负责该真实接线及GPU/LDPC验收。实现没有第二套GLS解法或第二套支撑扩展；每状态一GLS refit及一次回代Cholesky，未宣称缓存优化。
