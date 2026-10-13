# 已保存反馈接口诊断

512个BP/SISO检查点均验证decoder输入等于channel LLR、raw APP等于channel加原始extrinsic、实际交付prior等于extrinsic截断到[-20,20]。将原始APP与channel加截断prior比较，512个检查点均无符号翻转；其中247个syndrome合法检查点也无翻转。

包含7 dB BP固定刷新中块0、9、26的四个合法检查点。它们后来终端译码失败，但本次结果不支持“反馈截断翻转符号导致失败”。有限符号方差的微小变化不能单独建立因果关系。停止该具体符号翻转假设，保留原始结果。

分析仅读取既有数组，没有新F/T/LDPC调用。远端exit0；结果JSON逐字节回收，SHA256为5786f206befa95319c17be1476709199c05d628a7aa17e6d07c21a33f2ad83e4，脚本哈希记录于JSON。源脚本analyze-feedback-interface-v1.py。

新问题：当前BP终端默认不传码先验，而SISO终端传入最后一次check-extrinsic。代码差异尚未证明这三次失败的原因。下一步仅用保存的最终H、观测、噪声和prior，运行受控终端重放；真值只作外部评分。此为强参考匹配问题，不预称新颖方法。
