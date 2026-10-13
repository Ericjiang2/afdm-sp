# WIRE-06 — 真实反馈消费者

四个注册CLI arm→run_frame→forward.dals_mode→同一soft_gain_update→完整BP/LLR/LDPC已贯通。实参观察在求解前：当前H逐轮变化，C逐outer生成且内层不刷新，uniform/dynamic首轮H相同；uniform只改v策略，o_data只进入DA-LS mean。f_mean的H/x/sigma/错误数还与先前直接40基线A2校准帧一致。真值仅另在离线信道误差评价层使用。

最终固定源码 `.../v2_feedbackaudit-1788685100/source`，普通on/off和隔离确定性最终BP on/off四个独立进程均exit0、共16次校准帧接收，峰值1341MiB，整包17.3376秒。普通H/x/sigma/raw/info/decoded bits逐位一致；普通最终μ/var/LLR末位存在原后端非确定性，明确不作其逐位一致声明。仅隔离参考消除此已定位变化后，四臂全部软/硬输出逐位一致；生产设置保留。没有放宽数值容差或把隔离参考当作生产FER。

分析器analyze_feedbackaudit.py实查每臂9个DA-LS事件、实际C/方差及oracle标志、逐轮H、容量、可靠性分母、9个完整mean快照和27个离线自身目标下降。原始归档feedbackaudit-runtime.tar.gz、结果feedbackaudit-runtime-validation.json含hash/队列/费用/范围。前一版wire与det回放另保留feedbackwire/feedbackdet-runtime.tar.gz；det脚本首次路径导入失败保留feedbackdet-import-failure.tar.gz，未产生接收结果。所有批次计入连续S3S4窗口。

范围：反馈接线与受控观察透明性工程验收通过；普通GPU软数组无法保证逐位重复，这一实现边界保留。下一步RUN-11走普通后端，四臂开发48帧、离线矩费用独立记录；不能以本smoke判断必要性或可部署收益。
