# RUN-09 — 48帧机制包

真实完成432次receiver：split1/D_dev，rep0/1/2各frame0..15，N1024、SNR8、direct40、prior400。9次成功smoke复用首帧，后续423次，无帧替换或成功筛选。8个受控臂及独立共同GLS keep；keep直接提交baseline，不调用F2P/scorer，不冒称A0或旧keep。

三个后续进程均exit0；含成功smoke的进程时间合计589.0495秒（并行，非墙钟相加）。后续队列墙钟357.1152秒，显存峰值1339MiB；单独smoke峰值670MiB。2×4不重叠CPU核，两槽GPU，1200秒期限；成本留在连续S3S4账本。首次不完整源码包在导入时失败，2.204秒、没有receiver结果；原日志保留commonkeep-import-failure.tar.gz，修正rglob递归打包后仍用同预登记帧。自动审批首次拒绝目的地，核验账号/目录归属后同动作重试获批，见commonkeep-approval-resolution.md。

## 逐流错帧数（各16帧）

|rep|A0|A2|R00|R01|R10|R11|protect0|无prior|GLS keep|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|0|2|2|0|0|0|0|0|0|0|
|1|6|5|2|2|2|2|2|3|2|
|2|6|5|2|2|3|3|3|1|3|
|合计|14|12|4|4|5|5|5|4|5|

分析器验证全部身份、输入与冻结源/先验/LDPC，9×48有限输出，10outer/final容量、共用baseline、实际消费GLS gain、冻结prior逐ID一致、不补池。拒绝动作H/x/sigma/raw/info精确等于该帧独立keep。两组门前完整proposal含gain也逐项相同，允许将其无门控结果作对应提案反事实；并非只核对candidate池。

原始数据：mechanism48-runtime.tar.gz及commonkeep-smoke-runtime.tar.gz；分析器analyze_mechanism48.py；结果mechanism48-runtime-validation.json。结果含全部逐帧错误/动作、每臂费用、配对FER/信息bit区间，以及raw和复用smoke成员hash。20,000次配对帧重采样、每固定流内采样、seed2026090609，只有描述性区间，不用于正式覆盖率或无害保证。

代码变更：独立include-common-keep开关仅可在已注册机制包启用，受控臂≤8、不允许重复；共同keep走同一事务消费者并记录真实BP/LDPC。5项针对性测试、py_compile、diff检查通过；真实GPU验收上述432次完成。MECH-01单独裁决研究含义，不以运行完成代替收益。
