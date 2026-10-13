# WIRE-05 — 共同候选表与真实 GLS 消费者

工程接线通过；2026-09-06，deinlab RTX 4090，N=1024、direct40、D_cal rep997/frame0、SNR8，固定 prior400 SHA256 74f23844a95ea36ea90490f7aa5fca76bd14ff8a97f954f4387a4e85c852444e。不是 FER 收益证据。

六个机制控制加真正 A0/A2 共8臂。R00/R01 旧统计带 prior，R10/R11 投影统计带 prior；后缀分别关闭/启用 F 门。共用最终 GLS、两轮 F2P、一次完整事务和默认保护2；额外 R11 protect0、无 prior D 控制。R00不是历史 A2。各公式不同；单帧选择偶然相同不构成数学等价，不据此合并。

每帧先从观测 H0 形成共同 C，生成共同参考的两个96候选池和实际 pi/sh2。各臂仅过滤已 active ID，不补池；按候选原 ID 对齐 prior，支撑分叉显式记录。真正候选生成位置接受 frozen pool，默认路径保持原有生成/排序规则。

事务返回的完整 active IDs 和 GLS gains，逐项等于实际 t0 信道重建输入；之后保留原有阻尼、DA-LS、10轮检测以及最终 BP/LDPC。未将“t0 GLS 重建”误称为“10轮后的最终 H 不再变化”。拒绝动作完整 committed=baseline，keep参考的 H/x/sigma 与拒绝臂一致。小系统实际 BP spy 另核对消费输入。

实际八臂都完成且 finite，全部 final K≤40，temporary K≤48；两轮真实候选消费、prior数值和提交增益均由 analyze_wiremechanism.py 验证。on/off 八臂的 H/x hash、sigma、raw/info错误数完全一致。A0/A2以上字段亦与先前 direct40 固定帧回放完全一致。单帧全译码成功仅属 smoke，不推断收益或无害性。

## 浮点复现边界

相同最终 BP 的 y/H/sigma/constellation 和布局完全相同，但 GPU 普通重复调用的 μ 最大绝对差6.684427777288334e-16，var差1.1102230246251565e-16，hard符号差0。隔离探针启用 deterministic algorithms 后各4次重复完全一致；两个实际分支完整译码比特一致。证据与GPU归约非确定性一致，不支持事务状态泄漏。未改变生产后端/全局确定性设置，未以放宽容差替代逐元素验收。软 μ/var/LLR 不作逐位一致承诺；WIRE-02仍需独立处理此边界。

## 证据与费用

- `wiremechanism-runtime-validation.json`：可复算断言、原始归档hash、各臂结果、队列/峰值。
- `wiremechanism-runtime.tar.gz`：八臂观察开；进程12.181秒，峰值670MiB。
- `wireoff-runtime.tar.gz`：八臂观察关；进程11.939秒，峰值670MiB。
- `bprepeat-runtime.tar.gz`、`probe_final_bp.py`：同输入重复诊断；进程7.676秒，峰值668MiB；原始输出原样返回译码。
- 不可变源 `.../outputs_budgeted_support_repair/v2_wiremechanism-1788682223/source`，三个 packet 含实际源hash/CLI/预算。费用计入现有连续 S3S4 窗口，非正式时间比较。
- 已完成针对性组件和接线测试14项、此前数学/事务相关20项；本次追加只离线分析，执行分析器通过，Python编译检查通过。

人工代码检查：无真值进入机制评分/C构造，默认A0/A2算术保留；观察副本不能修改提交状态；仅预期秩失败转明确keep，其他错误传播；没有新增第二套剪枝器或零填增益覆盖。跨行J2/J3/D4科学主张保持pending，待RUN-09/MECH-01。
