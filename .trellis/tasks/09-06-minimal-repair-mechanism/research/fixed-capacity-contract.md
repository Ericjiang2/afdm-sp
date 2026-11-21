# 固定容量适配首批（运行前登记）

S4 legacy-capacity结果：V为17/192，原28/192，三流6/6/5对10/8/10，11赢0害；G为94/192，停止G开发。下一步仅A2/V，同一有限容量下验证V方向，不把弱基线适配当强基线完成。

容量候选沿parent {8,16,24,32,40}，对应 K_prop=floor(K_cap/5)={1,3,4,6,8}。外部Hhat0 OMP与Torch OMP同时固定；protect_added=min(2,K_prop)。复用现有扩展，不新加剪枝；扩展后硬验证K_active<=K_cap，记录可能未用满上限。此保守适配不是最佳部署壳保证。

五组prior各400 iid-QPSK帧，原harvest/fine-prior流程，新增显式nomination_cap。所有cap使用同一独立Dcal seed_base=SeedSequence([20260905,2,20,0,9]).generate_state(1)[0]；标签仍取原完整展开真支撑，不能随K_prop截断。保留旧default路径并验证。CPU五个4线程槽，36–55核，各480秒限时，输出隔离。

容量选择：coded SNR8 Dcal rep20/21/22 frame0..15（48帧），每cap仅A2，记录18软观察事件。按fit FER→总info错误→更小K_cap选择容量；只从选定cap的fit基线轨迹按原5温度NLL规则选T。不查看其他cap温度表作为另一次选择。共5个运行容量配置+选定cap5个离线温度，<=12。

独立验证：rep20/21/22 frame16..31（48帧），冻结同cap/prior/T，A2/V两臂，完整闭环；不据validation重调。再Ddev3×64复用既定开发帧，明确非确认集。每一步先2帧真实smoke，容量、输入、源码/先验域及标签隔离通过才放行。原始失败保留，仍合用S3/S4 8小时预算。

选择结果读取前补充：若固定容量重新选出的T不等1，validation/dev自动加入temperature_mean臂，与V使用同T；否则只跑A2/V（既有严格回放已证明T1均值臂相同）。这样分开温度均值与协方差效果，不把二者混成V归因。该分支规则先于本批T结果冻结，不增加搜索集合。
