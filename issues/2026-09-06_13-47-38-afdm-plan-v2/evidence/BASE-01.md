# BASE-01 条件处置

条件：RUN-03按FER选择A2，8dB下38/192=0.1979166667，处于预登记[0.05,0.20]闭区间。因此基线专属SNR搜索未触发。

not_applicable: true
execution_performed: false
selected_reference: A2
SNR_star: 8 dB
registered_guard_SNR: 7 dB / 9 dB

保留8dB结果，不搜索新方法收益更好的工作点。不声称半dB CLI已验证或额外SNR实验已运行。门按选定参考的点估计定义，不能看到其置信区间越界后改门。A0较弱基线42/192不改变既定参考选择规则。

证据：RUN-03.md、fit192-runtime-validation.json、完整原始artifact。后续候选仍受独立validation与正式门约束。
