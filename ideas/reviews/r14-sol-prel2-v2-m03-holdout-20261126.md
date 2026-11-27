## Blocking

- **逐帧恰好 5 倍时，Fieller 置信区间仍可能排除 `5.0`。** 用 `Adj_R5` 的两层各 60 帧，令每层参考误符数循环取 `1, 2, 3, 4`，再把第一层首帧从 `1` 改为 `3`，逐帧令 `ka = 5 × kb`。整数比例检查正确地将残差置零，但两个浮点均值相除后，区间变成 `[4.999999999999999, 4.999999999999999]`，而配对差判据 `D(5)` 的下限为 `0.0`，判定通过。内存复测中，直接用误符总数 `1510 / 302` 计算区间中心，两端均恢复为 `5.0`。 [ideas/l2/l2_m_r12_m03_delay_holdout.py:619](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_delay_holdout.py:619)

## Non-blocking

- **8 参数定样接口仍有浮点抵消。** 原 120 帧反例投影到同样帧数时，8 参数调用给出约 `6.74e−10` 的 Fieller 对数半宽，满足有限值要求。定样脚本使用的 10 参数调用给出精确的 `0.0`。 [ideas/probes/m_dev_r12_m03_holdout_sizing.py:47](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/probes/m_dev_r12_m03_holdout_sizing.py:47)
- **上轮两项均已关闭。** 合成帧写入内存 JSON，确认全局汇总将 `5` 次奇异值分解回退计为 `2` 个受影响帧，与预注册一致。独立复算的零命中 Clopper–Pearson 二项置信区间半宽，与表中的 `≈ 0.914` 和 `≈ 1.514` 个百分点一致。 [ideas/l2/l2_m_r12_m03_delay_holdout.py:943](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_delay_holdout.py:943) · [ideas/l2/PREDICTIONS_m_r12_m03_delay_holdout.md:18](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r12_m03_delay_holdout.md:18) · [ideas/l2/PREDICTIONS_m_r12_m03_delay_holdout.md:53](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r12_m03_delay_holdout.md:53)

## 已核实

- 两处求根均使用指定的移位二次式，`A_q > 0` 时判别式非负。原 `[6, 7, 8, 9]` 反例在 `N=120` 和 `N=60` 均得到 `[5.0, 5.0]`，上界有限，对数半宽为 `0.0`，门限通过。两种定样调用均返回有限值。 [ideas/l2/l2_m_r12_m03_delay_holdout.py:621](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_delay_holdout.py:621) · [ideas/probes/m_dev_r12_m03_holdout_sizing.py:49](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/probes/m_dev_r12_m03_holdout_sizing.py:49)
- 用指定的单线程 Python 核对了 `A_q > 0`、`A_q < 0`、`mb == 0` 和 `ma == 0`。重建的 `Adj_R4`、`Adj_R5` 合成反例均复现了置信下限由合并计算为正、分层计算为负的翻转。 [ideas/l2/l2_m_r12_m03_delay_holdout.py:603](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_delay_holdout.py:603) · [ideas/reviews/r14-sol-prel2-m03-holdout-20261126.md:13](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/reviews/r14-sol-prel2-m03-holdout-20261126.md:13)
- 冻结接收机的 MD5 校验值仍为 `7d174070e3b640583e8ec0e03d948cd1`。提交差异未改动正式种子配置。本轮只用了合成数据，两个正式种子区间均未运行。 [ideas/l2/l2_m_r12_m03_modtest.py:1](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_modtest.py:1) · [ideas/l2/l2_m_r12_m03_delay_holdout.py:871](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r12_m03_delay_holdout.py:871)

BLOCK_FOR_FIX