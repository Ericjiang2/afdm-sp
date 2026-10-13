# 四臂完整报价：硬输出一致性被反例推翻

冻结源码087b4c81、合同3ce0718f，作业737780在88.257秒以exit1终止，未超时。75F已落盘、0D、无完整summary；原600秒/136F136D合同不变，不重启、不汇总被中止的成本样本作为收益。

只读逐条校验全部75份raw、外生哈希及参考，前74条硬输出相同；第75条为开发块4、7dB、第一次DENSE_QPSK。所有连续量满足预注册rtol1e-5/atol1e-6，LLR相对误差8.9342e-8、最大绝对差2.8918e-6，H相对误差5.8423e-8。support、x_hard、decode_ok一致；decoded在447/1761两位置不同，info_hat在785一位置不同。两者FER均1、校验均失败，信息位错误60→59；码字错误总数均124。两者均执行10外层BP、120次外层迭代、9CE、4LDPC和1次20迭代终端BP。

这是否定“完整有限精度码链接收机逐bit无损”的实际反例，不是否定QPSK矩公式的数学恒等性，也不能从一位改变宣称可靠性收益。此前两工程块的组合资格和旧QPSK开发资格仍只对各自已验证输入/终端先验成立，不能外推至全部retained STOP输入。实现未改；原硬一致合同未放宽。

下一诊断合同projection-sensitive-replay-v1：固定同一开发块4/7dB，2F（DENSE_QPSK、INTEGER_QPSK，audit=True）与4D（旧参考、失败输出及两新输出的各自LLR精确回放），120秒、1GiB、1CPU。检查新QPSK和整数组合是否精确重现失败输出、仪表化是否改变数值、各自译码是否确定。不是新独立样本、性能或成本准入。原始报告在Mission exact-harvest-v1/evidence/cpu-cost-factorial-v1-failure-localization.json。

## 定点复现闭合

PID738605以exit0结束，10.290秒，2F4D完整落盘。DENSE_QPSK和INTEGER_QPSK的13个公开数值字段均精确重现失败输出；各有11个审计图、9个CE状态，资源计数相等；旧参考、旧失败和两新输出的各自LLR回放均精确。6个raw逐条读取通过，summary SHA 6ec5b47dee1d22fdef28cea66d1ef459e18dc851fdbe4a84cfa261e9e1ec16ea。

保留精确整数图路线；QPSK组合不再按逐bit无损计算优化准入。若以后重新研究其可靠性，须作为有限精度不同实现独立确认，不能删除这个反例或以放宽原合同掩盖。下一规模工程使用原投影，仅比较DENSE/INTEGER。
