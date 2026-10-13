# M 路线经典对照契约（LIT-01）

日期：2026-09-09。范围：M 已选后的来源、信息条件和实现契约。状态：**来源静态核查完成；下述部署对照均为 planned，未运行、未验证效果，不据此关闭 M-03。** 本文不改变 CSV 或实验预算。

## 一手来源及适配边界

| 方法 | 核查证据 | 允许的结论与限制 |
|---|---|---|
| Group lasso | Ming Yuan and Yi Lin, *Model selection and estimation in regression with grouped variables*, JRSS B 68(1), 49–67, **2006**。 [原文 PDF](https://sites.stat.washington.edu/courses/stat527/s13/readings/yuanlin07.pdf)，§1 模型、§2 式 (2.1)–(2.4)，PDF pp. 1–5。文件名 yuanlin07 不代表出版年份。 | 组范数惩罚支持组级稀疏；原文选择 K_j=p_j I，并在组内正交设计下给出 shooting 更新。AFDM 复数相关字典不能直接套该闭式更新；拟用一般矩阵的复数近端梯度求同一类目标，属于适配实现，非作者代码复现。 |
| Separable nonlinear least squares / variable projection | G. H. Golub and V. Pereyra, *The Differentiation of Pseudo-Inverses and Nonlinear Least Squares Problems Whose Variables Separate*, SIAM J. Numer. Anal. 10(2), 413–432, 1973, [DOI / 出版社](https://doi.org/10.1137/0710036)。本次直接核对出版社摘要及书目信息，未获取付费全文。 | 线性增益可由最小二乘消去，优化投影残差；出版社明确伪逆/投影导数推导要求恒秩。当前模板有 round、剪枝和截断，不能直接声称该光滑导数理论适用；拟用固定域无导数残差查询，标为 variable-projection-inspired 适配。 |

先前已核查的 R2 HiHTP、R3 NOMP、R9 SP/MMV-SBL、R10 pulse-shaped AFDM 见 [classical-source-precheck.md](classical-source-precheck.md)。这些记录的核查深度按原注保留：保护导频、MMV/多天线、译码反馈和脉冲模型不能迁移成当前同信息保证。R3 的单次局部 AFDM 试探不能叫完整 NOMP 复现。未在本次重新全面审核 R1–R12，亦不据此宣称新颖性。

补充物理方法原文核查：O’Leary 与 Rust，*Variable Projection for Nonlinear Least Squares Problems*，[作者全文](https://www.cs.umd.edu/~oleary/software/varpro/varpro.pdf)，§2、§2.1–2.3（PDF pp. 3–8）直接核读。文中每次非线性评价均消去线性系数，采用 SVD 处理病态线性子问题；外层可带参数上下界。其样例实现不对线性系数施加约束。本文读取的是作者稿，未将其占位卷期当正式出版信息。

公开代码核查：[作者官方入口](https://www.cs.umd.edu/~oleary/software/varpro/) 链接的 [varpro.m](https://www.cs.umd.edu/~oleary/software/varpro/varpro.m) 已通过 curl 只读获取并核对主入口、f_lsq、formJacobian：调用 lsqnonlin；SVD 以 m*eps 相对最大奇异值判秩；逐次重算最小范数增益及残差，记录 exitflag/rank；有导数时组合 Jacobian 两项，无导数时交由外层处理。未执行 MATLAB、未验证其复数 AFDM 适用性，未核验许可证；组稀疏作者代码仍未取得/执行核验。非光滑 AFDM 模板继续采用本项目有界无导数适配，不称作者软件或 NOMP 复现。拟实现必须记录为本项目独立适配。原有 `fit_physical_cluster` 和 `fit_local_physical_cluster` 接受 oracle 几何，不能直接作为合法部署接口。

## 相同信息与容量

所有部署比较由同一 B_star 终端快照开始，共用 raw y、pilot、冻结 S0（|S0|≤40）以及该快照已有 x_soft；允许已登记的系统参数、噪声规则和接收机估计。禁止真数据、I、真分组、真 eta、真增益、真径几何、额外天线/MMV、新增译码反馈。真值只能由隔离 evaluator 评分。

观测方程已核实 `afdm_sp_joint_unrolled/direction_cancel_receiver.py:30–38`：`A = construct_sensing_matrix(..., pilot+x_soft, ...)[:, S0]`，拟合右端为 raw y。pilot 与 x_soft 已按 rho 缩放，不得再乘 sqrt(rho) 或 sqrt(1-rho)。该接收机取消项为 `y-H@pilot`；结构拟合使用 raw y，不混用取消残差。所有比较臂使用同一观测、字典及冻结噪声规则。完整 H 从 S0 内虚拟抽头生成；支持可缩小而不可扩池。

组由 S0 的接收机可见 delay 标签形成互不重叠分区；同 delay 不等于真物理分组，不借用 oracle。物理中心仅从已有 OMP/S0 估计及固定去重规则获得；候选数 P 不超过预先冻结的接收机中心数，不读取生成器真径数，也不增加径数。分组、中心排序、平局和空组规则须在看结果前冻结。

## 两种 planned 对照

**组稀疏：** 最小化 0.5||y-Ah||² + lambda Σ_g sqrt(|g|)||h_g||₂；复数梯度 Aᴴ(Ah-y)，组近端收缩。使用一般相关 A 的谱范数步长/已登记回溯，不能将原文组内正交更新直接用于原字典。预先冻结 lambda 网格、初始化、尺度和停止准则；仅 D_design 调参。零范数安全分支、非有限值和 KKT/近端残差应可审计。数值奇异不能静默转成成功。

**物理参数化：** 构造 W(theta) 后 B=A W，a_hat=B†y，h=W a_hat；最小化实际 ||y-Ba_hat||²。先按生成器惯例形成完整截断、归一化 Dirichlet 模板，再取 S0 行；取行后不再归一化，不补 oracle 行。重叠列以复数叠加；固定 SVD/LS rcond，报告 rank、零列、奇异值。模板边界/阈值跳变时评价真实目标，不伪造光滑 Newton 梯度。预算臂只能采用预列固定局部模板查询或一次有界局部步；高计算参考可在同中心/同局部域重复无导数精化，但须独立列成本，不能扩 S0 或增加 P。不得将有限格点结果称连续全局最优。

## 文献合理设置与同预算双协议

| 协议 | Group lasso | 物理参数化 |
|---|---|---|
| 文献合理/充分求解参考 | planned：在冻结同一目标上迭代到登记的相对近端/KKT 容差或合理上限；报告所有 lambda 开发成本。 | planned：同域多轮无导数精化及每次增益 LS，停止于登记残差/步长条件或上限；不承诺全局收敛。 |
| 同预算部署 | planned：按目标端实测总接收时延和运算/迭代额度冻结迭代上限，沿用公平开发选择。 | planned：固定候选/局部查询次数或一次局部步，所有 LS、模板和检测重建计成本。 |

M-03 运行前必须将具体数值（lambda 网格、容差、最大迭代、中心数、局部边界、查询数、rcond、硬件、时延测量规则）写入同一配置并记录 SHA256；本文不把尚未测量的迭代数称“同预算”。两个协议均报告 B_star、经典组稀疏、预算内参数化和原型；高计算参数化单列。不得用确认集挑配置。

预算耗尽/未收敛/秩亏/空模板/异常逐帧落盘，包括退出原因、目标轨迹、查询/迭代数、实际总时延和回退原因。有限预算输出可用于该预算下比较，但**不能把刻意截断未收敛当作全面击败经典方法**。仅允许预先登记并显式标注的经典收缩或 B_star 回退；不得删失败帧或静默返回成功。原型优势须同时交代充分求解参考结果及预算差。

## 静态证据和验收交接

本次未运行任何实验或新增算法。使用 `rg` 定位 CSV 的 LIT-01/M-03，读取两份 precheck 和 `budgeted_support_diagnostics.py:80` 起权重/LS/局部函数；成功的读取与 SHA256 命令退出码 0。初次误用仓库根 evidence 路径的读取退出 1，已通过 `rg --files` 定位正确目录，不作为证据缺失掩盖。

源码静态快照 HEAD：`21b37637794b9605b9f975e377b367e00485e864`。`git rev-parse` 返回 0，但系统报告只读沙箱阻止 xcrun 临时缓存；未影响所返回 HEAD，不据此声称工作树干净。

SHA256（本次读取时）：

- `afdm_sp_joint_unrolled/budgeted_support_diagnostics.py`：`616cc4f6fc8e4230f528e1c6c72e225ed336cdfa69d45cf4b882d30a3bedbf05`
- `evidence/classical-source-precheck.md`：`2ca582b1ba4240e5a2f6b946df51a9cb72717b0b5c0bbd815a1b55f11d3bbdbf`
- `evidence/physical-bridge-code-precheck.md`：`2e21ffc9585314890c326674afa0f0b2e485119d1c40f3d50918fe1bd1dcef76`

网络证据：2026-09-09 用 web.open 读取上述 PDF 原文和 DOI 出版社页面，web.find 定位摘要与卷期；工具返回成功，不适用 shell 退出码。链接为原始来源路径；本次没有保存原始 PDF 字节，故不提供虚构下载哈希。新增算法配置/源码哈希、双协议真实输出、时延、终端检测和支持/信息隔离测试仍须由 M-03 落入 `physical-prototype-tests.json` 及对应原始日志。LIT-01 当前交付的是静态来源及接口契约，不能替代实现验收。

补查审计：2026-09-09，通过官方入口点击获得正确作者稿路径（`software/varpro/varpro.pdf`）；直接访问少一层 varpro 的 PDF 地址失败，未采用该失败页面为证据。web 点击 varpro.m 失败后，`curl -fsSL https://www.cs.umd.edu/~oleary/software/varpro/varpro.m` 成功，退出码 0，只读获取未执行；`rg -n` 检查 direction_cancel_receiver.py 的 sensing/pilot/x_soft 成功，退出码 0。物理方法原文与官方核心代码静态核查已补齐；具体参数数值冻结、实现/运行及代码复现验证仍由 M-03 负责。未另存远程字节，不虚构源码下载哈希。

M-03 numerical freeze: `physical-algorithm-preregister.json` selects the existing general-matrix ADMM group-lasso solver instead of adding an equivalent proximal-gradient implementation. The objective remains the stated disjoint-delay group lasso; the registered fixed lambda, residual tolerances and convergence diagnostics are reused. This avoids duplicate solvers and does not assert author-code reproduction.
