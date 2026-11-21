# S2 剩余控制批次（运行前登记）

## 未编码高SNR

D_dev3流×64帧×SNR15/20，iid QPSK：数据流生成2048个独立比特，不经过LDPC编码；所有六臂共用信道、原始比特、单位噪声。主读数为接收器x_soft对应raw BER，不把编码帧的译码前错误冒充iid未编码结果。最后soft BP保留以给出bit NLL/Brier，但跳过LDPC；info_errors/decode_ok为null，禁止报告coded FER。D_cal两组各400帧先验仍使用原uncoded harvest，和coded SNR7–9使用同一配置契约。高低SNR共享外生随机流，汇总保留信道聚类。

先2帧GPU工程验证，确认路径没有调用LDPC、六臂有限；再运行3流固定分母，不按错误数追加样本。

## 已有保守加入

SNR8，3流各64帧，配对baseline与conservative。复用现有apply_sequential_add_test，原OMP起点、同achievable首轮池/分数、相对pilot残差下降阈值0.01、k_add_max原值4、gain_margin0，首拒停止，保留原列。它是原保守动作规则的achievable评分适配，不是等容量部署版。

通过诊断支撑回放接口执行，先前F2P计算与轨迹被丢弃，实际最终支撑另记录；计时包含这些诊断冗余，不用于G2。比较完整FER、实际扩展容量、有益/有害动作；不能把更大容量收益归给门控。
