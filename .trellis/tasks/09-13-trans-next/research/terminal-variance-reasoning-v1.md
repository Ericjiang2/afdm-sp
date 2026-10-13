# 工作方差与有限迭代风险：下一机制的取舍依据

## 固定代数与解释边界

本项目生成器满足 y=H(p+x)+w。令 ΔH=H−Hhat，硬判决误差 e=x−xhat。残差更新实际使用

r=y−Hhat(p+xhat)=w+ΔH(p+x)+Hhat e。

因此逐样本恒等式为

||r||²=||w||²+||ΔH(p+x)||²+||Hhat e||²
+2 Re[wᴴΔH(p+x)+wᴴHhat e+(ΔH(p+x))ᴴHhat e]。

这里Hhat、xhat由同一y得到，交叉项不能凭独立噪声假设删去；残差功率也不必总是向上偏。源码采用0.7旧方差+0.3残差均方的EMA，再乘固定terminal_scale。该工作量可容纳模型失配与误判，未被证明等于物理噪声方差。

将终端H改成H_true后，原工作方差仍继承旧信道和判决路径。因此本轮H_true错1/32不能直接判为已知信道无法译码。先验也来自同一旧路径，需要在同一个有限字母BP分支中对照显式ZERO与RETAIN。MECH-03为这一操作性问题补齐2×2，而非以真值拟合最佳参数。

均方误差、边际NLL和有限LDPC FER的目标不同。原支撑投影救回2块却新增1块，已提供本数据上的直接反例；它还不能证明特定不确定性模型或风险度量有效。未来方法须在观测可用信息下预测何时保留/调整工作方差，并超越普通固定尺度基线。

## 新补充文献边界（2026-09-13）

- Szczecinski，*Linear Correction of Mismatched L-values in BICM receivers*，[作者全文](https://arxiv.org/html/1111.7265v1)，已读§I–II及§IV相关段落。统一正尺度不改变精确ML的码字排序，却可能改变迭代译码；该文比较PEP与GMI准则。因此LLR尺度修正及其译码收益不是新颖点，平均NLL/GMI也不能替代本项目有限LDPC FER。
- Jiang et al.，*Improved Frequency Domain Turbo Equalization with Expectation Propagation Interference Cancellation in Underwater Acoustic Communications*，Sensors23(18):7801，2023，[出版全文](https://www.mdpi.com/1424-8220/23/18/7801)，检索服务返回§III式(6)–(10)原文；直接PMC打开受CAPTCHA阻碍，未声称完整阅读。式(10)已讨论用软符号不确定性项修正残差噪声更新。直接照搬“残差减方差”不是创新，且其统计假设不能自动移植到同数据CE/BP循环。
- Martinez et al.，*Bit-Interleaved Coded Modulation Revisited: A Mismatched Decoding Perspective*，[作者摘要](https://arxiv.org/abs/0805.1327)，本轮只读元数据/摘要。摘要区分可达GMI与某些EXIT侧信息构造的pseudo-GMI；不能把复用译码反馈计算出的互信息自动当实际可达率。

本轮缺少本地papers/literature及arxiv_fetch.py，使用官方arXiv页面与出版原文检索结果。没有下载论文、复现上述算法或完成新方法的新颖性认证。

## 不预支结论的决策

若已知物理方差在EST中稳定改善，可将其纳入更强经典参考并验证全链接口；这种简单修正本身不作为Transactions贡献。若只在H_true有效，说明需要先处理模型误差；不可从oracle收益推断观测侧同样可得。若零先验普遍变差，停止以“先验旧”为由整体清零；应保持合法保留参考。若差异集中在特定码字，进一步诊断码约束方向需先证明其观测可测性，再设独立预测验证，不能按真值挑失败块。
