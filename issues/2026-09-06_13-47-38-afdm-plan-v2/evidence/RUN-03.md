# RUN-03 配对fit与暂定参考

真实N1024/RTX4090/LDPC，D_cal rep30/31/32各frame0..63，8dB，direct40，冻结prior400，共192帧×A0/A2=384次接收。三批均完整64帧且exit0；未读取validation或Dtest。

| rep | A0帧错/64 | A2帧错/64 |
|---|---:|---:|
|30|16|14|
|31|14|12|
|32|12|12|
|合计|42/192|38/192|

按预登记FER优先、并列A0，暂定参考A2。A0 FER0.21875，A2 FER0.1979166667；描述性Wilson95区间分别[0.166106,0.282427]、[0.147727,0.259957]，不是配对差异显著性结论。A2配对win9/harm5，净少4帧错；不得据此宣称方法优越性。工作点基于选中参考点估计在[0.05,0.20]，保留8dB锚点。

验证脚本analyze_fit192.py逐项检查全部身份、共同source/checkpoint/prior/LDPC哈希、192个不同y/channel seed、每帧两臂、finite、10outer/final和temporary容量。A0零scorer准备且无修补。输入共用同一frame对象；全部原始frames/status保存在fit192-runtime-validation.tar.gz及原服务器只读运行目录，逐文件哈希在JSON。

队列实际窗口约194.14秒，3路进程总约301.52秒、4核每路，观察GPU峰1295MiB；精确成本见JSON。初始启动器CLI错误未启动任何接收帧，原日志保留，修正后仍在原1200秒截止内完成；没有重置deadline或替换随机身份。该并行插桩时间不作G2证据。
