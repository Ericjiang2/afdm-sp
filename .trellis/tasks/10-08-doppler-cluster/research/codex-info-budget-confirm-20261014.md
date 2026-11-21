行号均指[修订草稿](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/10-08-doppler-cluster/research/info-budget-screen-20261014.md)，只读核对一轮。
- **NOT FIXED｜T1一致性：** L26–27已正确，但L47仍称 empirical GMI有下界保证；改为“QR主项，经验GMI仅报告”。
- **OK｜样本/期望、逆序QR：** L37–39、70及56–57已修正。
- **NOT FIXED｜奇异支持：** L48已引入g，但L33–35、81仍用全空间熵及奇异logdet差；统一在g上写 \(I(h;y)=I(g;y)\ge-\log_2\det C_e=J\)。
- **OK｜U4统计方法：** 已改为带误差界求积；**NOT FIXED**：L170的X12仍写“配对差区间”，须同步改为确定性求积。
- **OK｜T2范围：** L110–111的β与能量上界正确。
- **OK｜Bernstein：** 系数、iid、n≥2、总风险预算及J误差项正确；新增文字错误：L109“two random terms”应为“three”。
- **OK｜CRITICAL分类：** L135–140已修复，指定五元组判WEAK。
- **OK｜随机延迟、Hermitian计算：** L37–39明确条件D并逐帧计算J；L147使用Q+C_p与Q。
- **NOT FIXED｜确认/删失：** 无通过点时的确认范围已补齐；新增错误：L116–117仅凭末点通过便右删失。须要求整个确认前缀通过，且尚未覆盖全网格；否则按首个失败点截断。
- **OK｜J新范围：** 在 \(\|p_t\|^2=N\rho\) 下，\(J\le N\log_2(1+\mathrm{tr}C_p/(N\sigma^2))\le N\log_2(1+\beta\rho/\sigma^2)\)；结构/细节总检仍未闭合。
**NOT**