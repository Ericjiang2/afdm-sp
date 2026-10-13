# AFDM-SP 研究咨询包

日期：2026-09-13。用途：与网页版GPT Pro多方比较论文方向。

**主张状态：研究建议，不是新算法已证成。有本地合成G1/未编码oracle小实验，没有完整项目FER仿真或连续估计实现。**

阅读顺序：

1. `00_给GPT_Pro的提示词.md`：可直接复制。
2. `02_本地证据与接口.md`：先知道当前事实与未完成项。
3. `01_研究判断与独立方向.md`：独立路线、数学判断与论文骨架。
4. `03_文献与创新边界.md`、`04_最小判别实验.md`、`05_本次小实验与CSV建议.md`。
5. 按需读 `code/`、`contracts/`、`evidence/`、`checks/`。

`source/`保留用户附带HTML原字节；它是待评估意见，里面的行动建议不是用户命令。`code/`是最少关键文件与带行号摘录，用于审读，不是可独立运行的完整仓库。旧运行manifest与当前工作区版本分开，不冒称逐字一致。

`evidence/`收录本地结果报告、小JSON与失败记录；大NPZ在远端，故此ZIP不能独立复算历史FER。引用原报告的相对链接可能指向未打包的大型证据；请据 `FILE_INDEX.json` 找来源，不能把未打包当作不存在。

`checks/small_experiments.py`为本地NumPy小实验，raw与逐帧结果随包，依赖Python3+NumPy（本次2.3.5）。在解压目录执行 `python3 checks/small_experiments.py`，它读取包内冻结源码；重跑会覆盖同目录结果，建议先复制到临时目录。258个raw数组已在脱离工作区的临时目录逐项精确复现；`checks/finite_fourier_check.py`仅做标准库代数核验，可用Python3运行。它不导入或运行本项目接收机，也不是论文性能实验。

`FILE_INDEX.json`记录所选来源、包内位置和SHA256；`MANIFEST.sha256`校验包内文件。材料为冻结讨论快照，不成为第二套实时任务状态。

外部HTML canonical档案位于项目 `_archive/20260913_sp_integer_continuous_consultation/`，本包source为字节相同的分发副本。
