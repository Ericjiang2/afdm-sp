# REP-01 representation_ledger 独立只读审查（2026-09-06）

审查文件：`afdm_sp_joint_unrolled/representation_ledger.py`、`test_representation_ledger.py`，并核对`loop9_cache_features._merged_dictionary_coefficients`及现repair事件。未改实现、未运行测试；下面反例为静态可推导，不冒称运行复现。主会话BP图观察器接线不在此次审查范围。

## 结论

完整复系数合并与“关联而非因果”的核心方向正确。存在一项影响当前默认调用产物的具体缺口：没有物理估计器时提前返回，使真值碰撞信息也消失；建议修正后再将REP-01记为满足碰撞账本要求。输入验证和非默认分支有较小缺口，应按实际支持范围补契约或明确限制。

## 必修：[P2] 无物理估计器时丢失已知碰撞

`match_physical_slots`先验证truth，然后在estimated_slots=None时返回；Counter碰撞计算在返回后。`merged_truth_ledger`总是只传truth，因此当前真实runner使用路径不会产生`colliding_truth_slots`、可辨识分母或碰撞原因。`recall=None`是正确的，但它不应同时抹掉从truth位置已可识别的碰撞。

静态反例：`match_physical_slots([[0,0],[0,0],[1,1]])`返回无估计器，未列0、1碰撞槽。现测试只在提供estimate时检验碰撞，没覆盖默认实际调用。

最小修改：将truth碰撞/可辨识集合计算移到None分支之前，各返回分支统一保存这些truth账本字段；没有估计器仍返回recall=None和原reason。增加一个estimated=None且存在重复truth的测试，检查collision列表和无虚构recall共存。

## 完整truth合并：正确项与范围

- 以`bound=max(receiver k_max,max(abs(emitted doppler)))`调用现合并函数，避免原helper的Doppler mask删除域外条目；随后按扩大域解码成(delay,k)，只为接收Doppler域内条目生成接收列号。这个做法保留完整实际发射整数原子，不重复实现complex sum。
- 复系数先合并、后`abs(gain)>threshold`；完全抵消条目保留在K_unique_merged但不计K_true，正确。阈值单位标得明确；没有把系数权重命名物理能量。
- `K_true_in_receiver_doppler_domain`刻意只称Doppler域，未声称检查delay上限；这点诚实。后续接线若把它改叫“receiver完整域”，必须同时提供l_max并校验。当前`column`也可能对应超过接收delay上限的整数编码，消费者不能仅以非None判定全域合法。
- 参数验证尚未拒绝负delay、非法k_max或taps与l_i/k_real长度不一致。例如taps=3但只有一个物理slot可同时输出P_phys3及单槽匹配账本。实际生成器一般不会产生这种输入，但作为证据边界应拒绝不一致数据，而不是生成互相矛盾的账本。建议校验k_max为非负整数、delay非负、taps非负整数及slot长度一致；delay域外条目可保留并明确域标记，不能静默剪掉。
- 完整truth是“生成器实际截断/裁剪后发射条目”的完整合并；不代表未截断连续物理信道，这一范围要在最终报告保留。

## 物理一对一匹配

Hungarian分配使用dummy行列，合法距离≤2，未匹配代价为penalty、非法边4penalty；penalty随n+m足够大，确实优先最大匹配数量，再优化归一化距离和，不会让单个估计同时匹配两条truth。

精确重复truth全部排除、分母只用可辨识truth并显式scope，这是可接受的冻结协议，但需报告完整P_phys及排除量，不能只展示较高的过滤后recall。当前前述默认早返回破坏了排除量透明度。

其余应补边界说明：

- `estimated_slots.reshape(-1,2)`会把错误形状静默重排，例如2×3数组变3×2；建议仅接受原N×2或明确空列表，不把错误数据修造成合法估计。
- `ambiguous_truth_slots`仅标“一个truth有多个可行estimate”，未标“多个truth争同一个estimate”。例如truth(0,0)、(0,.4)，estimate(0,.2)同时覆盖两truth，匹配会正确只取一个，但ambiguity列表为空。若字段只意图多estimate邻接需改清晰名；若意图不可辨识应同时检查admissible列度并报告竞争truth。宽容差内有多解不必直接排除，但不能称全部唯一可辨识。
- 精确位置碰撞只是一个不可辨识来源，零增益/零贡献槽以及截断后相同基底不由这个位置API识别。当前scope有“exact collisions excluded”限定，不算冒称检测全部；报告不能进一步泛称所有不可辨识都已处理。可在调用层由已有物理参数单列零贡献状态，不扩展成物理路径估计器。
- (.5,.5)固定于模块，可作为预冻结delay/Doppler bin容差。需要在证据里明示单位为字典bin，并保持时间上先于评估数据；测试里确定常数不等于已有配置hash记录。
- “输入顺序保持tie”与SciPy固定输入通常一致，但尚未定义多最优时跨实现版本的完整tie规则；至少记录estimate排序规则与SciPy版本。无需另写匹配算法。

## 阶段丢失归因

当前函数返回truth_not_in_pool时减raw，避免把已在OMP支撑的真原子算作“候选生成漏检”，这是正确且测试覆盖的。selected_then_pruned与initially_true_then_pruned可重叠；scope明确不是因果分解，诚实。

它聚合所有事件的集合，故`selected_then_pruned`表示“曾选、曾剪”，不一定表示最终缺失；某原子后续再入选可同时出现在selected_then_pruned和final集合。当前字段没有声称最终互斥原因，属于合理历史关联；若最终图表将其标题改成“导致最终错误”，必须与final_missing交集或保留ever_pruned命名。不能把这些列表数量相加当总错误数量。

另外，`in_pool_not_selected`没有减raw/final，依赖算法pool只含当前非支撑原子的契约；后续新事务/多轮路线若使“曾在池但由其他途径最终保留”成立，需仍解释为事件历史而非最终漏选。无需为当前正常F2P过早复杂化。

事件读取仅支持pool/union/final_prune；当前F2P匹配这些stage。若defer_prune=False的中间剪枝不产final_prune事件，其损失会漏入历史pruned。新WIRE05事务的keep/reject/commit事件也不一定自动落入此schema。接线方需提供有类型的映射或明确支持路线，不能用空events默认为“没有损失”。这属于消费者覆盖验收，函数测试不等于已覆盖全部接收分支。

## 最小追加验证建议

只需针对真实缺口补测试：无估计器仍保留collision；恶形estimated形状拒绝；两truth争一个estimate且一对一分母正确并标竞争；taps/slot长度不一致拒绝；曾剪后重入的历史标记与final_missing区分。现取消/域外/一对一/原支撑不算漏池三项测试有价值，但不足以覆盖上述边界。

本次审查不重复BP图接线、不要求建立物理路径估计器，也不把纯假设的坏输入无限升级为运行阻塞。当前最直接影响REP-01承诺的是默认路径缺碰撞信息。
