# CORE-03 先验域与完整标签验收

actual RUN-01完成400个独立IID QPSK帧，完整真值复系数合并、精确零阈值、物理与展开参数、固定身份、输入和配置hash通过完整校验。实际load_prior以nomination40/direct40成功消费。旧nom8及没有完整schema的nom40缓存均被测试拒绝，未按文件名放宽。

run_frame初始H0的host OMP与receiver内部OMP共用resolve_receiver_capacity，direct40均40/extension0；合成runner→真实forward测试记录两处40，真实N1024 A2接线同时验证初始化40、临时44/48在登记48上限内、每outer/最终≤40。物理生成k_leak2不变。

可部署scorer只接收观测OMP H0与冻结build_fine_prior统计lookup，未读当前帧真值。truth保留在离线harvest/observer记录；当前评估帧与prior seed碰撞检查通过。

证据：RUN-01.md、prior400-runtime-validation.json、a0-a2-wire-runtime.json、test_prior_manifest.py、test_direct_wiring.py、test_budgeted_support_eval.py；16项相关本地测试通过并实际N1024 GPU/LDPC两帧接线通过。此行完成不代表FER或B2候选覆盖结论。
