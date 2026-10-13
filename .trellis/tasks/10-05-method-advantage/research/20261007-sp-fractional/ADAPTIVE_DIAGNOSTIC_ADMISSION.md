# QUAD-ADAPT-01 独立准入

2026-10-07。协议、新单文件源码及部署字节审查已完成。
**准入 PASS；按文末生效条件，仅准许冻结的 QUAD-ADAPT-01 执行一次。**
未执行规则表核验、Fourier 求值、求积、接收机或 SSH；未修改旧源码/协议/raw。

## 协议边界

审查 `QUADRATURE_NEXT_STEP.md` 及其“主线程冻结的执行细节”，复用此前数学与
raw 审计上下文。只补读其直接引用的 `QUADRATURE_CONCENTRATION.md` 中连续
包络定义，以确认选择规则采用哪一组 L/U，没有重做旧数学审查。
被审协议 SHA256：`ce2af5075aaedabcb47e4af820e5390b64af05748033fa288b903b479a09e114`。

- 唯一候选为全支持 [-3,3] 的 GK15/G7、16 初始面板、最多 26 次二分。
  原 Fourier 系数与 sigma2 不变；不混入 Taylor 代理、矩压缩或接收机更新。
- 输入固定为原 RECEIVER-DEV-01 的 11 项输入，以及已审 QUAD-DIAG-01 的
  attempt/registration 与 8×2 个 4096/8192 level raw，即另 18 项参考输入。
  8 case 顺序和原系数提取路径复用已核准的诊断模块。
- 每个候选自己的运算、停止和最终输出须先保存/封口，之后才解析对应参考数组。
  在此前做原字节哈希核验/不可变 snapshot 拷贝不等于使用参考数值；候选不得由
  参考误差选择面板、决定停止、修正结果或重新开始。输入身份与参考准入依然须核对。
- 通过条件为 8/8 在预算内完成、各自对固定参考的 phi/logZ 均≤1e-6，并通过
  正权、有限性、归一化和离散 tail 检查。任一失败否决本固定候选，不删失败 case、
  调整配额/阈值或添加规则重试；这 8 例是已参与诊断的输入，不称独立泛化样本。

## 规则、选择与停止条件

1. 固定标准 GK15/G7，G7 复用嵌入节点；表的正权/对称性以及 G7 0–13 阶、
   K15 0–22 阶单项式精确性核验阈值为 1e-13。该核验需在本阶段计费回调内
   执行并留证，不能在 import-only 阶段悄悄执行；它不是通信观测或 receiver fixture。
2. 全部活动面板在同一 shift 下汇总未归一化质量和 Fourier 积分；规则差先按
   面板取绝对值/向量最大绝对值，再跨面板求和，避免通过抵消获得小估计。
3. E_A≥A 时不完成；否则 logZ 估计为 −log(1−E_A/A)，phi 估计为
   (E_A+E_B)/(A−E_A)。最终 K15 phi 再加离散删尾的 2 倍质量上界，logZ
   采用未删尾常数。原 1e-14 约定和两项 1e-6 完成门槛没有放宽。
4. 优先级固定为质量差/A、Fourier 差/A、max(U_i−A_i^K,0)/ΣL_i 三者最大值，
   最大者二分，精确并列取最左侧。只能替换该父面板为两个子面板，不能重算
   未变面板或漏掉端点/低质量区间。
5. 引用包络已唯一明确：面板中心 c、半宽 r 使用
   l=g(c)−|g′(c)|r−B2 r²/2、u=g(c)+|g′(c)|r+B2 r²/2，
   L=(2r/6)exp(l−C)、U=(2r/6)exp(u−C)。中心是已算 K15 节点；B2 每 case
   只算一次。包络风险、优先级与质量在 log 域处理，不把下溢/溢出或 NaN 变成零风险。
6. 完成估计达标即可封口，不要求包络额外收紧；因此始终标
   `certified_continuous_error=false`。这明确区分经验完成与严格证书；最终是否
   满足本次诊断精度由封口后的固定参考比较决定，源码不得私加第二个停止门槛。

上述定义可以直接落实为确定性算法，没有需要产品决定的剩余歧义。
局部规则差是误差估计；即使代入的归一化误差公式本身来自有效不等式，也不使
未经认证的局部 GK/G 差自动成为连续积分误差上界。

## 累计预算与失败行为

| 每 case 工作 | 上限 |
|---|---:|
| 初始密度节点 | 16×15=240 |
| 二分新增密度节点 | 26×30=780 |
| 累计密度节点 | 1020 |
| 创建面板/中心导数收缩 | 16+2×26=68 |
| 最终活动面板 / K15 节点 | 42 / 630 |
| 8 case 累计密度节点 / 中心导数 | 8160 / 544 |

G7 复用不新增密度点；父子节点不假装完全复用，已丢弃父面板成本保留。
参考数组读取与比较不增加候选密度评估数，但时间、内存、原始证据保存仍须计费。
phase、Fourier/导数收缩、B2、表核验、选择/包络、tail 与保存成本不能从总账中删除。

未达估计门槛且 26 次二分已用尽，保存 budget_failure 并继续其余固定 case。
程序/I/O/内存/超时按既有 fatal 语义传播，不能标成普通预算失败；保存已有父子
面板、选择轨迹、候选最终状态及实际消费，不以失败为由清空或重试。

全部通信/新观测/独立 blocks/有效 backend 配额为 0。复用 engineering 内核
wall/CPU 各 180 秒、完整进程 210 秒及 10 秒退出宽限、单 CPU/CUDA 隐藏、
RSS 4 GiB、输出 128 MiB。单文件新增 `adaptive_diagnostic.py`，旧 receiver 不动。

## 后续源码与字节准入

仅补核新文件实现上述冻结契约、固定表核验、候选封口与参考解析边界、完整计数/
异常证据，再核源码 commit/snapshot/archive、实际 imports/config、29 个固定输入、
合同、launcher 和一次执行条件。不因后续代码到位重审旧数学或重跑旧诊断。

## 新单文件源码审查

审查文件：`experiments/afdm_sp_fractional_receiver_20261007/adaptive_diagnostic.py`。
SHA256：`70f1b20b357d69fce9479491d77b7e4795ce553f0fc7cfa27d9357b6b427807e`。
未重审旧接收机、已通过的浓度/Taylor 数学或旧 raw。已定点确认四个直接复用模块
`continuous/quadrature_diagnostic/runtime/protocol` 无新增 diff。

- **入口/输入**：29 个固定外部输入由 `input_paths` 明确构成；原 11 项身份链
  复用原模块，参考 18 项校验 attempt、registration、artifact hashes，并核对
  参考确实来自相同原输入。参考预读只涉及哈希和配置/身份 JSON，不加载 level 数组。
  `--print-imports/config` 在 preload 后返回，不调用规则核验或候选。
- **固定表**：GK15 对称节点、K 权和嵌入 G7 的索引/权表静态对应标准规则。
  正权/对称性及 37 个单项式检查在 `calculate` 的计费回调内只运行一次，保存
  started、表和检查结果；失败显式记录并抛出。该审查没有运行表的数值核验。
- **log 域边界**：零局部差由 `log_nonnegative` 明确返回 −inf；非正 U−A_K
  由专用差函数返回 −inf，对应协议中的零风险。无效分母明确产生 +inf 估计并
  阻止完成；有效分母使用 expm1/log 形式，误差合并使用 logaddexp。
  NaN 显式失败，不设 probability floor；离散 exp 下溢被计数并保存 log 质量上界。
  包络风险在 log 域比较，不先指数化一个可能很大的优先级。
- **非有限值保存**：候选/面板 NPZ 经 `runtime.save_new → diagnostic_tree`，
  complete/summary JSON 也先通过 diagnostic_tree；正常的 −inf 零差和 +inf
  无效估计被显式编码，不写非法 JSON number 或伪造有限值。内存中的 trace/panel
  不因序列化而被改写，后续选择仍使用原 log 数值。此为静态数据流核对，未做运行测试。
- **选择/预算**：初始 16 面板；每次仅一个父面板被两个子面板替换，活动列表始终
  按左边界有序，`max` 对相等 score 取首个，因此 tie 为最左侧。全支持相邻边界
  每轮检查。未变面板复用，父 phase 缓存释放但已保存父记录不删。
  26 次 split 上限给 68 个创建面板、1020 密度点和 68 个中心导数，实际完成
  计数与 split 数交叉核验；8 case 总启动消费不超过 8160/544。
- **统计/输出**：局部 K/G 正权积分先在各自共同 local shift 下比较，再于全局
  log 域汇总；完成条件与冻结协议一致。最终活动 K15 节点统一归一化和按原约定
  删尾，logZ 使用未删尾常数；phi 用已存 phase 累加，未额外重评估密度。
  B2 每 case 一次，中心沿用原节点 phase；父子、导数、Fourier/特征函数累加、
  聚合、tail、缓存释放/复用、wall/CPU 及保存开销均保留。
- **封口/参考边界**：`candidate` 不接收 reference 路径/数组；case 先保存
  candidate NPZ，再保存其 SHA seal，之后才进入 `reference_comparison`。
  参考比较前后检查 candidate 文件 SHA，结果数组已设为只读，且没有再进入
  选择/求积循环。参考自身双 1e-9 门槛和 candidate 双 1e-6 门槛均参与判决。
- **失败**：budget_failure 保存最终规则并继续其余固定 case；算术错误保存已有
  panel/trace/counts 并使 case 不通过。程序、内存、超时和 I/O 仍按既有 fatal
  边界传播；参考读取失败单独留证并抛出。所有已开始/完成父子均保留记录，不能
  以最后失败为由丢掉前面已付成本。仅 8/8 candidate_completed 且固定参考通过
  才接受本候选，全部状态继续标 `certified_continuous_error=false`。

## 当前验证

- 新文件独立 Ruff：PASS。
- AST 解析与内存 compile：PASS，未执行编译后的代码。
- TypeCheck：未执行；AST/compile 不是类型检查。
- 数值表核验/tests/smoke/import/SSH：本轮未执行。
- 未发现需要修改的源码问题或协议偏离；无需重复审查旧数学。
  以下已补实际源码清单、commit/snapshot/archive、29 输入、合同与 launcher 字节准入。

## 最终部署字节窄核

- 原源码 commit：`af8fed05c5671e949e11e6b2a3b9874eeab6b950`。
- 独立 snapshot commit：`d2f03445291f5e444ab54544363473985e46100b`。
- archive：`.mission/20261007-sp-fractional-trans/dispatch/adapt-source-af8fed05.tar.gz`。
  SHA256：`3a8926f749134d6db2c2bbea3f9c15a0006c523dc2cbd1123f9afd9bd7fdf029`。
- 归档 60 个候选源码逐个与原 commit、snapshot Git tree/blob、当前文件和
  manifest SHA 相同；snapshot HEAD 正确，新单文件仍为本报告已审的 `70f1b20b…`。
  tar 共 275 成员，只含 `source/` 下普通文件/目录，无路径逃逸、重复成员、链接、
  特殊文件、setuid/setgid、Git alternates 或额外非 Git 载荷。
- 实际入口 inventory 为 **57 源码**，与合同相对路径集合及其哈希完全一致。
  归档另含旧数学包的 `protocol.py/thread_binding.py/verify.py` 三个未导入候选，
  不把它们冒称本入口实际运行依赖。
- **29 个固定外部输入**精确等于原 RECEIVER 的 11 项与 QUAD 参考的 18 项；
  每个合同 SHA 与已审本地原件相同，没有额外候选/观测。合同总计 **86 哈希**。
- remote-config 与合同 config 完全相等；remote-imports 为上述 57 项。
  回传部署 stdout 记录 archive 校验 OK 与正确 snapshot HEAD，stderr 为空。
  预检回执记录 86 项源码/输入已核验、BLAS/OpenMP/Torch 全部 1 线程、
  new_numerical_work=0。本代理读取回执及本地原件，未自行 SSH 或执行模块。
- 合同与已审协议/源码的规则、配额、优先级、封口边界及全零通信计数一致。
  内核 wall/CPU 各 180 秒，完整进程 210 秒、TERM 后 10 秒 KILL，RSS 4 GiB，
  输出 128 MiB。launcher `bash -n` PASS；独占 process 目录，保留 PID、
  start/end/exit、stdout 和 `/usr/bin/time -v` 的完整进程计费，不允许覆盖重跑。

控制文件位于 `.mission/20261007-sp-fractional-trans/control-adaptive/`：

| 文件 | SHA256 |
|---|---|
| `source_manifest.json` | `59c22cc41773ce070bb173a8c6fc39e5720042b1a783ffd7a9d1e39347aae720` |
| `run_contract.json` | `174a7fa05604f67fd75f689580ac401930c62a53cfd0997d5936d02633239e6f` |
| `launch.sh` | `95fce7ebf24af31be78803ac9c19a22dd33ee5e773785b315f253f18aa4f0f40` |
| `remote-imports.json` | `db82bae23d5e0ad2b29ff7f93b4b0c0003988a3222a02af09e1dea6ec2b351bc` |
| `remote-config.json` | `62d844ae0daced86f454121f17c870083258f4622ed18c1865c23fae50debe5f` |
| `thread-source-preflight.json` | `5b852307d5e8ea4dff8787f032222159b58179594cb870fc4d61ea570a168352` |

## 一次 GO 的生效条件

主线程在唯一目标根
`/data/guoyikun/afdm_sp_quadrature_20261007_adapt01_af8fed05`
最后确认上述源码/合同/launcher 与 29 输入未变、即时资源及单线程/CUDA 约束
仍满足，且 `artifact/process-QUAD-ADAPT-01` 和 `artifact/execution/QUAD-ADAPT-01`
尚不存在后，在已初始化 conda 的同一 shell 中使用 AFDM 环境执行冻结 launcher
**一次**。本次仅为保存势诊断，不重跑旧 receiver，也不生成通信观测。

任一预算、算术、参考精度或资源失败均保留首轮原件并按固定判决否决候选；
不重试、不追加分裂/规则/层级、不调容差、不挑选成功子集。
若 8/8 通过，结论仍只限于这组已参与诊断的输入，不构成严格连续积分证书、
任意势保证、BER/速度优势或后续接收机/代理实验的自动运行许可。
