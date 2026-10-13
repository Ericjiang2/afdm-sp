# Collapsed 接收路径：工程回放

2026-10-08，COLLAPSED-RECEIVER-ENG-01。一次冻结运行正常退出；注册检查全部通过。
独立原件审计 PASS，可准备 DEV；尚无 DEV 接收性能结果。

复用原 N8/N16/N1024、P1/P2 数学案例，未生成通信样本：45 次 score-only
候选、9 次完整 gain 恢复与旧封口原件比较通过；252 项比较与残差检查全部通过，
最大归一误差 2.3797078021e-16。候选 s/t/J 和完整 m/C 等对旧值的比较误差为零；
非零量来自完整求解的 precision residual，不是接收误码。

3 个原组件 fixtures 通过；两个确定性搜索检查均通过，各实际评分 24 次。
常数势保持原点，递增势选上端点。默认路径检查只覆盖配置和静态调用入口，
不能据此声明旧接收输出已经复现。真实旧基线复现留在 DEV 原件审计。

回放工作为 6 个 canonical/source、9 次坐标准备、6 次共享 Cholesky、
12 次共享三角求解、72 次候选三角求解、9 次完整协方差恢复；
21 次 inverse DAFT、6 次 FFT。fixtures 与搜索控制的工作另计。
0 physical basis、0 新 observations、0 receiver、0 decoder。

- recorder stage wall/CPU：1.123819 / 0.963964 秒。
- 完整进程 wall/CPU：4.02 / 3.87 秒；峰值 RSS：453382144 bytes。
- 133 个原件、3415291 bytes，全部回传 SHA-256/MD5/size 核对通过，无大件跳过。
- 源提交：`62508b84d64be5e3504ad9a2e14ea0e77a4fa60c`。
- snapshot：`36dc6e527df93fa7494436d1b47a1238fa4b4554`。
- 远端根：`/data/guoyikun/afdm_sp_collapsed_receiver_20261007_engineering_62508b84/artifact`。
- 本地原件：`.mission/20261007-sp-fractional-trans/evidence-collapsed-receiver-engineering/artifact`。

逐文件远端路径、MD5、SHA-256、大小见同目录 `collapsed_receiver_eng_manifest.json`。
合同、launcher、summary 与 resource 为回传原件副本。NPZ 不入 Git。
Gaussian 消元和 Schur 搜索属于经典方法适配；该工程结果不证明 BER、完整成本收益
或 Transactions 目标成立。

独立原件审计：`.trellis/tasks/10-05-method-advantage/research/20261007-sp-fractional/COLLAPSED_RECEIVER_ENG_RAW_REVIEW.md`，
SHA-256 `82ec09446ebdca18de88dede09b4cb6487a3d9d82664e32f00226cde7686c327`。
