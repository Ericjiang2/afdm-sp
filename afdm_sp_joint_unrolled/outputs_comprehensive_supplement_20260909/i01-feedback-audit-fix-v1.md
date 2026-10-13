# I-01 反馈CE审计修复

真实N16 outer CE/BP + CodeFeedback(checkpoint0)启用diagnostic_dals_observer时，在读取dals_payload[probabilities]处复现KeyError。根因是反馈CE使用离散后验矩，而原审计强制要求旧Gaussian surrogate分支才产生的payload。

反馈分支现在记录实际CE均值/方差及moments_source；不伪造Gaussian工作方差或概率数组。原None路径与数值CE保持。两个suite共9测试通过，含checkpoint0/1真实反馈审计、实际A/均值/方差一致、observer开关完整链一致、disabled精确等价。

这是I-01集成前置修复，不是六臂实验完成。BaselineReceiver/ObservedReceiver接口透传、oracle隔离、成本重排、完整N1024与192块开发仍待实现和验收。没有部署到正在运行的导频源快照。
