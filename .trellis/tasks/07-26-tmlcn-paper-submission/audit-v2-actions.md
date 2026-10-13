# audit v2（AFDM_claim_audit_v2_20260726.html）行动清单

v2 = 对 07-26 晚中途简报的续判。核心裁决：机制预言 out-of-sample 命中（升级 firm-track）、E1 改口径被认可并加严、学习 null 维持零回潮、venue 维持 TCOM。以下为 v2 新增/确认的待办，与在跑实验的对照。

## 已覆盖（在跑/已做，无需新动作）

- coded 网格 {7-11}×800f、geom+ach 双臂：**在跑**（v2 只知道单臂，实际双臂并行，白化 coded 归因臂并未缺）
- E2 六臂 + serial 地板：**在跑**（v2 §2 负空间说 serial 缺——实际 serial 是第二段单独跑，v2 不知情）
- 单 harness 同帧配对（C2 规则）：已按此设计
- scorer 身份登记：SNR7 锚点 = geom 臂，已登记于 harvest 手册

## 新增（按 v2 §7 优先级）

1. **E1 PCSI coded 臂**（§3.6/§7-行动1）：`--with-pcsi` 代码在改（含 RNG 中性约束）；E1 双跑完成后同 seed 补跑。产出 dB-gap-to-PCSI@FER=1e-2
2. **E2 收尾 + bundle-v2 打包**（§7-行动2）：800f 完成后原始件入 `_claim_audit_bundle_v2/` 供外部逐帧重算——firm 引用的前置
3. **C1-①②③ + C3-②**（§7-行动3，0.5-1d）：
   - bit-exact 回放 gateA_s15firm classical+ach 前 50 帧（repo-only checkout）——**注意：原始 firm 大概率 GPU 产出，CPU 回放会因浮点差异误报失败 → 必须等 GPU 修复，与 E6 同批做**
   - 运行时检测器指纹进 results.json meta（`_detector_binding` + `_git`）：代码在加，PCSI 跑起将自带；已完成的跑补不了指纹，如实标注
   - import 守卫：断言 mp_detect_bp_torch 解析到 repo 路径（防 shim 回潮）——排入 C1 批次
4. **Cao 公平性附录**（§7-行动4，1d）：配置对齐表（文档，写作期做）+ dual-protocol 第二列（their-recommended settings 新跑，机器空后）+ 支撑翻转率 dump（instrumentation，加分项）
5. **缓**（§7-行动5，revision 弹药）：serial/OMP-(P+K) 进 E2 帧列、E3 SNR20 pool、E4 低 ρ 格、E5 壳消融

## 写作解禁与冻结（§7）

- **现在可写**：§I gap、§II 模型、§III descent（achiever=achievable-Λ）、§IV 理论、§V 接收机+复杂度、§VI uncoded 全部——全站 v1 firm 数据
- **冻结到 coded 800f + 原始件**：摘要 coded 句、§VI coded 小节数字、F4/T5、结论 coded 承诺
- 图表改判：删 SNR15 coded 柱；F2 waterfall 换 E2 同帧臂（LMMSE 只进表）；增 F3 raw/coded 双瀑布、F4 FER 瀑布四臂、T5 coded 数表、T6 Cao 对齐表
- 措辞新约束：机制律句一律加 "verified in the uncoded operating region"；"coded 错位 5dB" 只作方法论一句+图，不作贡献 bullet

## 提交 gate（§9-5）

coded 网格 800f + E2 800f + C1 bit-exact 回放，三者齐 → 可投。
