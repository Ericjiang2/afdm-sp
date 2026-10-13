# GOV-03 随机流契约

主会话用实际dev_rng重算全部1168个预登记seed，与研究manifest逐条相等；四组内部唯一且两两无碰撞。只预登记validation身份，未生成其观测。完整既有记录范围与N8合成make_frame身份fixture见父research/mission-rng-evidence-20260906.md及mission-rng-identities-20260906.json；fixture不是物理帧或接收E2E。

新prior唯一规则冻结为split2/rep40/frame0..399/stream9逐帧派生，固定seed清单为GOV-03-prior-manifest.json。CORE-03必须逐条消费且不得失败后另抽替换。prior使用现有harvest内部随机生成规则；fit/validation保持make_frame的stream1 channel、stream2 bits、stream3 noise，stream4只用于arm顺序。数据噪声序列不被算法内部随机数改写。

未来真实input hash在对应运行产生时检查，不提前访问validation/Dtest来制造hash证明。已使用Ddev重复是诊断重放，不是新独立样本。旧LDPC seed20260726及code hash契约保留，实际文件hash由RUN-02记录。

主会话审阅通过：命名域/原开发流保留、先验400与fit192/validation384范围明确、身份冲突检查有执行证据且范围限定；实际接收运行验收仍由后续行承担。
