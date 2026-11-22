## I-20261121-l02

1. **最强反对意见。** 注入准确回答了“旧码多给的后验信息是否制造了启动优势”，但同一帧上，真实译码反馈会与接收机先前的观测误差相关，一致高斯注入没有复现这种相关性。这个差别在 C1 上有实测后果：即使模型逐帧预测能够启动，实际也只有 **29%–50%** 的帧译出，因此模型第 5 轮过线能支持构码检验，不能换算成误帧率收益。[项目结果卡](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261009-01.md)

2. **锚点与近邻。** 项目锚点成立：6.5 dB、导频功率占比 0.30、\(K=224\) 时，原规则码从导频起步跑十轮，误帧率为 **0.85**。Ma、Liang、Xu、Ping 已在叠加导频迭代接收机上，针对给定导频功率比例匹配不规则 LDPC（低密度奇偶校验码）的度分布，并比较不同功率比例，卡片将贡献收窄到 C1 有限码长的启动问题是恰当的。[项目实测](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261009-01.md) · [Ma et al., IEEE JSAC 2017，第 V 节](https://lsec.cc.ac.cn/~mjj/papers/Ma2017.pdf)

3. **注入与配对复算。** 四臂共用同一批 100 帧及逐帧噪声，在每对内固定检测器外信息，只改变供信道重估使用的后验增量；外信息实测分别为 **0.1292、0.3195**，对应后验分别为 **0.4510/0.5224、0.6162/0.6695**，与点名的两组目标相符。按“旧码配对减匹配码配对”复算，\(D_1=0.45158498-0.45130446=0.00028052\)，\(D_2=0.53632717-0.53632289=0.00000428\)；用所报逐帧差标准误算 \(\bar D\pm1.984\,SE\)，95% 区间分别为 \([0.0002422,0.0003189]\)、\([-0.0000074,0.0000159]\)，第一处效应虽小但可辨，第二处包含零，本地缺逐帧行，标准误本身未能独立重算。[注入实现](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver_c1e.py:157) · [四臂汇总](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out12/inject_summary.json)

4. **与现稿的关系。** 同码率、同码长、同十轮预算下，改变码的度分布能否降低启动失败率，是独立于现稿“失败后继续迭代还是重搜”和第 0 轮真值上限的问题。当前证据只覆盖一个导频比例和已知真实时延的接收机，最优导频比例是否下降仍是开放问题。[漏斗范围](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/FUNNEL.md)

5. **轨迹与放行。** 按预设规则从原传递曲线扣除分段线性配对差，复得匹配码外信息 **0.1276、0.3167、0.5782、0.9879、1.0000**，第 5 轮过线，原规则码十轮未过；另外把两处匹配臂的**实测绝对输出**直接插入原表，在实测外信息坐标上重算也仍是 **5 轮**。统一下移 0.005、0.01、0.02 分别需 **6、6、7 轮**，可用来衡量模型对整体偏差的敏感度；下移 0.03 时第十轮校验消息信息量已达 **0.999818**，仅低于预设门槛 **0.9999**，故这个读数不能解释为真实接收机启动失败或有限码长误差的上界。[预设判据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_batch20.md) · [调度计算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_exit_schedule.py)

VERDICT: PASS — 两处点名的后验配对差都不足以改变五轮过线的判断，值得交 Eric 决定是否投入 1–2 天构造码长 2048 的匹配码，在 C1 接收机上与原规则码同帧比较十轮误帧率。

## 合并与排序

第 1 位，也是本轮唯一放行项：**I-20261121-l02**。按“有限码长配码能否降低 C1 启动失败率”计一个独立问题，无需合并。
