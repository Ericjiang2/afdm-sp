# 未编码 G1 实现与证据审查

主会话按Trellis check自审；独立性weak。用户限定查找代理，未使用独立实现/审查代理。

- 任务批准后先登记UNCODED-01与协议，再写runner；生产接收机及旧snapshot未修改。来源提交85a4c855。
- 接收边界仅观测四字段，固定公开40/44提名；旧P_actual只存在父证据内，不流入receiver。F2P_HEAD使用冻结模型，普通F2P_RESID按独立残差公式核验。
- 真正独立比特替代旧码字，原pilot/信道/单位噪声复用，新CPP观测闭合；无伪称独立信道。
- CPU gels策略在隔离进程共享所有臂，退出恢复；loaded encoder/decoder aliases调用即失败。五个数值/边界单测PASS，AST2PASS。
- 工程2A/35F/37记录/327数组另进程回读PASS；每臂块0@15重复全状态精确；没有编码/译码调用。主摘要与原始输出、支撑、观测哈希绑定。
- 初始OMP、repair/head打分、LS及每轮CE/BP计数来自实际调用，不从预算推算。模型只含cand_active_rel learned head，普通臂不计算repair；不存在运行完再恢复旧support的伪成本参照。
- 同壳对照和硬反馈参照分列；旧achievable先验未加载，不能用本批替代历史achievable-Lambda完整复现。未覆盖reOMP和全部公开近邻。
- 单次计时含完整receive及轻量核验/计数，排除模型初始化、物理生成、保存与真值评分；属于开发报价，非正式COST。32块固定开发，重复调用不入科学分母。

开发已完成：32A/485F、517记录/4557数组完整raw回读PASS，15个端点、配对差及开发成本已出表，见uncoded-g1-v1-results.md。初次审计过早启动失败，attempt2只回读成功，失败记录保留。

独立只读check子代理补充检查了聚合公式、Zheng推导与build_receiver路径；发现setup元数据LDPC_constructed=False是literal。已将报告收窄为静态源码不构建LDPC、receive期所列入口实测0次；没有篡改冻结源码或environment。实验执行及raw审计仍主会话，不能将代码复核称为独立实验确认。

最终限定范围独立复核PASS：检查代理从480逐块行重算15个端点的计数／均值、15组配对差与20000次固定bootstrap，全部一致；517记录、4557数组、32A/485F/0D及attempt2日志对账一致。Zheng Z2–Z5、Z7–Z8代数通过。未访问服务器或重跑接收；这是独立代码／数学／本地汇总审查，不是独立CONF。
