# 真实 pilot 工程证据（范围受限）

第一隔离快照 v2_pilot-1788677090：CPU16—19 的2帧N1024 prior成功，约0.319s/frame，实际整作业3.879s。完整标签验证通过，合并truth数分别见prior-pilot-runtime.json，固定rep40/stream9与配置hash留存。A0最初因部署缺子包导入失败，退出1；费用保留。

新隔离快照 v2_pilot-1788677090-retry1：补完整Python包清单，未覆盖旧快照；只重试A0原2帧，沿用同360s绝对截止。CUDA A0整作业4.948s，退出0，采样总显存峰值648MiB。真实checkpoint SHA256与历史记录052ecfab...2a91相同，经过N1024 CUDA receiver、最终BP与LDPC。2帧info_errors均0，不支持FER改善结论。

主会话读取逐帧记录并断言：shell direct40、extension0、nomination40、初始化/10个outer/最终均40唯一原子；support_repair_enabled=false；scorer准备0；coding=LDPC，finite=true，decode_ok为bool。原始status、帧输入/源码hash和轨迹见a0-coded-pilot-runtime.json。

两次SSH发车后均断开，重连从queue-status/PID身份/退出码/完整帧取证，未重复启动存活任务。外层start_new_session、子进程组、四线程/独立核、原绝对截止与不可变manifest均有记录。

仍待：A2完整400 prior消费、缺帧恢复真实测试、receiver恢复入口、deadline主动触发与完整OPS闭环。CORE-03、WIRE-01、OPS-01、RUN-01/02仍未代签完成。

真实恢复增补：v2_recovery-1788677625 的同一N1024 A0 CLI首次与--resume均退出0；第二次computed_frames=0、restored_frames=2，完整输入hash/契约校验通过。两次整进程分别4.955s/3.224s；采样显存峰值648MiB。原导出和状态备份保留。source snapshot与120s原截止见recovery-1788677625-packet.json。

截止夹具：子进程退出-15，/proc不存在；初版观察到结束超出绝对截止约0.414s，未隐去。新版将6s清理时间计入费用并在截止前6s停止工作；本地费用契约测试通过，远程修正复测仍待完成。
