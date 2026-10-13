# RUN-01 冻结400帧先验

真实deinlab CPU16—19、四线程、N1024/P8/fractional k_leak2、rho.5/SNR8、M96、nomination40，400帧IID QPSK。rep40/split2/stream9身份全部独立且与冻结manifest一致；400个逐帧文件、完整复系数合并标签/物理参数/input hash/config hash均通过validate_complete_prior。实际direct40 load_prior成功，未放宽400帧要求。

远端缓存：/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v2_prior400-1788678282/prior400/cache_snr8.pt

SHA256：74f23844a95ea36ea90490f7aa5fca76bd14ff8a97f954f4387a4e85c852444e

整进程128.316s，退出0，采集日志400/400、tries400，无替换样本；声明360s预留内完成。完整身份和输入hash/队列原件见prior400-runtime-validation.json。源码、参数和预算见prior400-1788678282-packet.json。当前固定先验冻结，后续不能利用机制/validation结果重训。尚未声称A2接收性能或正式结果。
