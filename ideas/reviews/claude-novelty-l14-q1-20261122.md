# Claude 定向补查新：I-20261122-l14 的 q = 1 全局最优（2026-11-22，本地第 3 轮；claude -p --no-session-persistence --model opus，代替无额度的 Astra；提示 ~/.cache/idea-funnel/afdm-20261122-l3/nov_l14_claude.prompt）

**结论：PARTLY。** 两段常数本身是经典值：它们等于"周期、零均值"版本问题的已知极值。不过本卡在区间上减去一次拟合的版本比周期版更强，能推出周期版，反过来推不出。这个区间版本我没有在文献里查到。以下推导是我自己做的；检索只确认了文献存在，没有读到任何一篇原文的对应定理。

**1. MRI 梯度波形（只读摘要或检索片段）**
- 最近的先例是 Aliotta–Wu–Ennis，CODE，MRM 2017；以及 Bernstein–Shimakawa–Pelc，JMRI 1992。两者都是在限幅、限斜率下把梯度矩归零，再用数值方法最大化 b 值或缩短 TE，没有给闭式全局最优。
- 等价关系：把波形对应到本卡，M0、M1 同时归零等价于 q(0)=q(T)=0 且 ∫q=0，此时 b ∝ ∫q²。只限幅时，四瓣 +−−+（每瓣 T/4）给出 b = G²T³/48，就是本卡的 η²/48。只有 M0 归零的双极波形给 G²T³/12，对应 q=0 的静态最优。两者相差 4 倍，正是卡里的 6.02 dB。
- 可推方向：本卡定理能推出"+−−+ 是这个 MRI 问题的最优"，反过来不行。MRI 要钉住两端，本卡两端自由，但要额外减去线性项。
- MRI 一般不加 |q| ≤ 常数，所以文献里没有 η > 2 那一段。

**2. 动态解耦（只读摘要）**
- Uhrig PRL 2007；Uhrig–Pasini NJP 2010。它们的目标是让切换函数的低阶时间矩归零。切换函数恒为 ±1，L2 能量固定，不存在"最大化去趋势后残差"这个问题，所以不等价。
- 唯一的重合：η→∞ 时本卡 U 形的两个切换点是 T/4 和 3T/4，也就是 CPMG/UDD₂ 的切换时刻。

**3. 逼近论与样条（凭记忆，未读原文，这一类最接近）**
- **η ≤ 2 的周期版是经典结果。** 周期为 1、零均值、|f′| ≤ η 时，‖f‖₂ 的最大值由三角波（一次 Euler 完美样条）取到，值为 η²/48。来源是 Kolmogorov 比较定理和 Favard 型不等式。
- **η > 2 的周期版我判断也有经典对应，但不确定。** 加上 |f| ≤ 1/2，相当于连续模 ω(δ) = min(ηδ, 1)。按 Korneichuk 的 H^ω 极函数，最优是梯形波，方差为 1/4 − 1/(3η)，与本卡第二段完全相同。我没有核对 Korneichuk 原书是否覆盖 L2 情形。
- **η²/48 疑似还有一个宽度解释，不确定。** 它疑似等于 W¹_∞ 在 L2 中的 Kolmogorov 2-宽度的平方：二分段常数子空间给出上界 η²/(12n²)，n=2 时恰为 η²/48；对应的极函数就是卡里的 V 形。若成立，本卡等于证明了一次多项式空间 P₁ 也是最优 2 维子空间。作为对照，q=2 的低速值 0.00981η² 大于 1/108 ≈ 0.00926η²，说明 P₂ 不再是最优子空间。这个宽度公式我没有查到原文确认（应在 Micchelli–Pinkus 的工作或 Pinkus 1985 那本书里）。
- **本卡定理能推出周期版。** 把任一周期函数做循环平移，总能找到一个平移量使它与 t − 1/2 正交（平移量的连续性加上平均为零），此时 R1 就等于它的 ∫f²。所以周期版是本卡的推论。
- **反向推不出。** 区间端点自由、只减去线性项的情形，必须用交错定理加穿越耗时；这个形式的命题我在检索中没有找到。

**4. 时分复用 MIMO 雷达（只经二手评审转述）**
- Rambach–Vogel–Yang，ISSPIT 2014。它在固定的离散虚拟阵元位置上优化发射顺序，切换是瞬时的，没有速度或切换时间的约束。不等价。

**成文时需要做的：** 引周期版的 Favard/Kolmogorov/Korneichuk 结果，把本卡写成"非周期、带线性去趋势"的推广；并点明 η²/48 就是只限幅时 M1 归零的最大 b 值。两段常数不能再当作新结果来写。

NOVELTY I-20261122-l14 (q=1): PARTLY — 两段常数及其极值波形在周期、零均值版本中是经典结果（Favard/Kolmogorov 三角波、Korneichuk 梯形波，并等于只限幅时 M1 归零的 MRI 最大 b 值）；本卡端点自由、减去一次拟合的区间版本严格强于周期版且未查到先例，但需要请懂逼近论的人对照 Korneichuk 与 Pinkus 的原书最终确认。

Sources:
- [Uhrig–Pasini, arXiv:0906.3605](https://ar5iv.labs.arxiv.org/html/0906.3605)
- [CODE (Aliotta et al.)](https://escholarship.org/content/qt7tx4q6hj/qt7tx4q6hj.pdf?t=ol00fz)
- [ODGD ISMRM abstract](https://uvadoc.uva.es/bitstream/handle/10324/31375/ISMRM_ODGD_FINAL.pdf?sequence=3)
- [Pinkus, n-widths of Sobolev spaces](https://pinkus.net.technion.ac.il/files/2021/02/sobolev.pdf)
- [Pinkus, On n-widths of periodic functions](https://pinkus.net.technion.ac.il/files/2021/02/periodnwidth.pdf)
