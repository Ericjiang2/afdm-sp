# 完整 SISO-MMSE CPU 工程与原始审计

20 次完整接收完成，外部耗时 127.20 秒。每次 10 轮外层、9 次 CE 和共同 LDPC；两条 SISO 链分别使用 checkpoint=1、checkpoint=1/4/7。终端继续消费最后交付的 check prior，LDPC 输入为 channel extrinsic LLR。此合同区别于此前零先验缓存终端报价。

| 检测与反馈 | 7 dB 错块/工程块 | 8 dB 错块/工程块 |
|---|---:|---:|
| BP MEAN | 1/2 | 0/2 |
| BP REFRESH47 | 1/2 | 0/2 |
| 精确 SISO MEAN | 1/2 | 0/2 |
| 精确 SISO REFRESH47 | 1/2 | 0/2 |

两个外生块跨 SNR/臂共享，重复臂不增加独立样本数。8 条 BP 与此前工程 NUMERIC_FIELDS 精确一致；4 对 SISO REFRESH47 重复精确一致。本批仅通过数值和接口工程资格，不证明 FER 等效或改善。

原始审计通过：4576 个数组、180 个 CE 状态、132 次 SISO、396 个预定符号的独立 Gaussian cavity 系统、20 次终端和28次反馈真实 LDPC 回放。逐符号排除自身干扰矩后直接解方程，避免生产者的 Sherman–Morrison 分母公式；通道 LLR 最大绝对差 1.42e−14。这里的“独立”指重算的数值方程，科学审查仍为主会话，独立性 weak。

实际资源合计：64 次 LDPC、132 次 SISO 分解及135300个RHS、80次外层BP（960迭代）与8次终端BP（160迭代）。SISO 每次约5.2–6.3秒，BP约1.5–2.2秒；这些计时包含残差检查、记录/哈希开销，非正式 COST。压缩记录 SISO 约8.8–9.2MB/次，BP约4.4–4.6MB/次。

失败完整保留：首次小码测试的错误dtype断言与缺失协议fixture；首次工程在F预约前因源码清单相对层级不符退出；首次审计在读取raw前因缓存目录缺失退出。修正后使用新快照/任务名，没有改旧结果、放宽数值阈值或重跑已完成工程。

下一步固定32个已公开开发块×7/8dB×两条SISO=128F，与保存的同块BP参考配对。预算1800秒、4GiB，源码仅允许修改执行调度入口；完整检测算法锁定工程版本。该开发比较仍不是独立确认。作者FSPAI/共享xi近似未适配，当前只能称精确稠密 Gaussian SISO 参考，不能称 DI-S-MMSE 原文复现；REF-02继续开放。

完整数值、调用和SHA256见 [siso-chain-engineering-v1.json](siso-chain-engineering-v1.json)。
