# RECEIVER-ADAPT-01 独立审查

2026-10-07。复用已通过的 GK 数学、单因子实现/字节与 raw 上下文，完成协议和
7 文件窄源码审查及部署字节准入。**协议、源码静态与控制字节 PASS；ENG GO，
DEV conditional GO：仅在 ENG 完整通过且冻结字节不变后执行。**
未执行 import、数值、fixture、接收机或 SSH，未修改源码、协议或 raw。
被审协议 SHA256：`b3032c73c5bcbc1a73d47dc6ec6fe864853c25fa04ae57234ec5c7f3e95a3f97`。
该版本补充两项明确标为 mocked 的局部预算/TimeoutError fixture，已纳入本轮源码审查。

## 唯一变化与共享核心

- 只有 continuous 的 Fourier 求积从 fixed 切换到显式 adaptive 选项；默认 fixed、
  截断 Gaussian 初始化、数据先验、full gain covariance、更新顺序、3 数据步/
  20 sweeps、equation (8)、独立 objective 与回溯失败检查保持原行为。
- 从已有诊断提取一个 `adaptive.py` 核心，诊断和 receiver 必须消费同一实现，
  不保留第二套 GK/优先级逻辑。按主线程交接采用事件生成器：数值核心无 I/O callback
  或参考依赖；诊断消费者在事件间保存原完整 panel 证据，receiver 消费同一数值事件。
  消费者的 I/O 不得修改数组、分裂顺序或停止状态。
- 固定 GK15/G7、16 初始面板、26 次 split 上限、累计 1020 密度点/68 中心导数、
  原 tail 与 1e-6 估计保持不变；不混入代理、压缩、早停、路径裁剪或其它性能优化。
- 返回 DopplerFactor 必须保持正权节点、phi、原 coefficients/sigma2、logZ、
  expected log kernel、KL 和分辨率诊断的既有含义；预算失败向上传播为接收失败，
  不返回 point 替身。成功省略可重建的面板内部 B 向量可以减少重复证据，但完整
  选择边界/标量轨迹、实际消费、最终因子及失败 partial 不能丢失。

## 工程阶段验收

`RECEIVER-ADAPT-ENG-01` 必须先于开发执行并通过：

1. 用共享核心复现已保存的 8 个输入，先保存/封口本轮输出，再解析旧 ADAPT 参考。
   状态、分裂顺序、计数须一致，最终 phi/logZ 差≤1e-10。
   每因子和总节点/导数配额分别为 1020/68 与 8160/544；全部工作实际计费。
2. 原 13 个组件 fixtures 只运行一次。按主线程本次交接，如原 engineering 辅助流程
   同时执行 3 组已保存矩检查/9 个数据步，最终配置与账本必须明确列出，不能藏在
   “13 fixtures”一项里；对应旧数学输入也要加入清单绑定。不能将这些 fixture 运算
   加入 8 因子回放后却仍只报告回放计数。
3. 实际 receive 边界调用仅为一次应拒绝 truth 字段的负控制；有效 payload/backend、
   新观测、新独立 blocks 和 decoder 均为 0。该边界调用不是有效接收性能样本。
4. CPU/wall 各≤180 秒，完整进程≤210 秒加 10 秒退出宽限。
   任一工程失败或字节/配置漂移不得自动进入开发。

## 开发阶段验收

`RECEIVER-ADAPT-DEV-01` 只在工程通过且本阶段准入条件齐备后执行一次：

- 精确复用原 DEV-01 的 8 observed、4 truth 与必要 public/population 元数据，
  逐 SHA 绑定；不生成信道、消息、噪声或 G1，不增加统计样本量。
- truth 原字节可校验/复制，按主线程“全 seal 后解析 truth”的交接，源码必须在
  **全部 24 个预定调用输出（含实际失败记录）全局封口后**才解析 truth 数组评分。
  observed/public 边界不得因复用 population 而携入 channel/truth 字段。
- 保留原每 block 轮换的 arm 顺序，24 次独立 F1 获取与接收；三 arm 为
  f1_scalar/vb_point/vb_continuous，新合同显式将 continuous 设为 adaptive。
  不能复用另一 arm 的获取结果或用旧运行时间替代本次完整计时。
- 继续参数化现有 study/runtime 的接收、封口与评分流程，不新增平行 harness。
  旧生成器/默认配置应仍能复现；保存 population 的复制/加载费用单列并计入总账。
- 配额为 0 新观测、0 新独立 blocks、24 接收、0 decoder；统计单位仍是原 4 blocks。
  必须有 24/24 完整输出。continuous 总错误≤point 的90%、不多于 scalar，
  完整接收中位时间≤scalar 的1.25倍；point 零错为 inconclusive。门槛不改。
- CPU/wall 各≤1800 秒，完整进程≤1830 秒加 10 秒退出宽限。保留任何失败，
  不自动重试；旧 DEV 失败不被抹除。即使本轮通过也仍是同一开发切片的筛选，
  coded、强基线和 held-out 目标不能据此提前关闭。

两阶段各自绑定实际源码、commit/snapshot/archive、输入/配置/launcher，并保持
单 CPU、CUDA 隐藏、RSS 4 GiB、输出 128 MiB、全部远端写入 /data/guoyikun。
成功 trace 的序列化策略、初始化、获取、全部回溯/失败与检查费用均计入完整成本。

## 源码静态审查

审查源码 commit：`7757cd504c2a9539efb1b20e49a87f8a4a74120a`。
以下是实际代码路径审查，不是数值或接收性能验证。

1. **共享核心与提取等价：PASS。** 独立用标准库 AST 对比 `af8fed05` 的
   `validated_rule/log_nonnegative/log_positive_difference/scaled_exp/evaluate_panel/aggregate/final_output`
   与 `adaptive.py`：前四函数无 AST 差异，其余只改变动态 `n`、常量引用与将 guard
   移出数值函数。另逐段检查 `candidate_events`，初始16面板、累计26二分、原优先级、
   左侧 tie、左右子面板顺序、父缓存退役与最终计数核验保持原逻辑；新增输入检查要求
   有限系数、正噪声和空局部状态。诊断仅消费事件、保存证据并加入保存元数据，
   receiver 消费同一事件，不存在第二套数值实现或参考回灌。
2. **因子语义与失败账本：PASS。** `AdaptiveIntegrator` 继承原 `initial`；每次 Fourier
   更新新建局部 counts/panels/trace，预算不会被前一坐标的累计值污染。`finally` 将
   所有已消费局部计数合入全局 `adaptive_` 账本。`as_factor` 只接受 completed，
   预算耗尽抛 `CoreFailure`；TimeoutError 等资源异常经既有包装保持异常类别与 partial。
   导出保留正权节点、phi、原系数/噪声、uniform base、原常数项，使用
   `Elog = weights @ reduced + constant`、`KL = weights @ reduced - centered_logZ`，
   另检查尾质量及原 receiver 的 1e-12 特征函数约束。估计明确为 empirical、certified=false。
   成功保留所有边界和选择轨迹，失败保留 panel partial；不存在 point 替补。
3. **ENG：PASS。** 输入集合由10个 saved MATH 文件、11个原失败势/元数据和18个
   ADAPT 参考/封口文件组成，共39项。参考 bytes 可预先哈希，每例完成候选输出与
   SHA seal 后才解析对应参考；检查状态、counts、split/panel identity 精确一致，
   phi/logZ 阈值保持1e-10。8例真实回放累计上限8160/544，规则验证和factor导出另列。
   原13 fixtures、3组 saved MATH（21项算子检查）/9个数据步均显式列出。
   两项 mocked fixture 只调用合成事件/导出 stub，分别覆盖跨坐标预算隔离及
   TimeoutError 的已付计数/证据保存；其合成 counts 不进入真实回放总账。
   唯一 receive 调用仍是 truth 字段边界拒绝，有效 payload/backend、新观测、blocks、decoder为0。
4. **DEV：PASS。** 输入路径白名单精确为4个元数据、8个 observed、4个 truth，共16项；
   原 attempt/registration/config、manifest 和逐文件 SHA 均核验。population 准备仅
   哈希/复制 NPZ 原字节，既有 `_load_bound` 只向接收端提供 observed 的 y/pilot/sigma2。
   同一 `receive_population` 保留 block arm 轮换，每次 `receive_arm` 新建并执行自身F1，
   三arm均重测完整费用。24条raw（含可继续的数值失败）全部完成并全局seal之后，
   `score_population` 才解析truth；fatal错误中止，不进入评分。默认fixed/原生成器兼容，
   adaptive只复用population；新观测/blocks均为0，原4blocks统计单位和原screening门槛不变。

### 审查字节

路径均相对 `experiments/afdm_sp_fractional_receiver_20261007/`。

| 文件 | SHA256 |
|---|---|
| adaptive.py | `b34e4abe97f38c206c7e2678bd85667de5098b93724670f6cb303a19368ff50b` |
| adaptive_engineering.py | `dcc2ea3a47e4d00c49cbe3337ad7d413e1dd3125a6d9644fe60719f07f1c5dc2` |
| test_adaptive_contracts.py | `560f1fcb8f6a96a6620e9ba9c17b80dc5eb4a2d006624c12bf397ef1e422f29f` |
| adaptive_diagnostic.py | `de6caacf734f5b4227821cb012a29e8a43d014fe510a79929dfb65ae5fbd3394` |
| receiver.py | `e97dbb301e00a075b018668733437a98943a19e0c44825b04b979b6cde80a2f1` |
| runtime.py | `d2f26fea21cfb1971f7733c47c729c484e758ab64d314e93f4c78aaa270ffce0` |
| study.py | `5a991138661b8e7f2082b12fe92be54e5d243e07ac95f055b3821d70d356ff68` |

### 本轮验证与剩余范围

- 7文件 fresh `ruff check --no-cache`：PASS。
- 7文件标准库 AST 解析与内存 compile：PASS，未执行编译产物。
- `git diff --check 7757cd50^ 7757cd50`（限本package）：PASS。
- TypeCheck：未执行；环境未找到 mypy/pyright，项目未找到相应配置。AST/compile 不冒充类型检查。
- Tests/import/数值/build/smoke：本次均未执行；按交接留给隔离 import-only 和已限定的工程阶段。
- 未发现需要修复的问题。当前实验选项由task协议明确约束，不需扩展通用 `.trellis/spec/`。
- 后续部署窄核已在下一节完成；工程通过后方可按既有授权进入开发，不重复GK数学审查。

## 部署字节准入

本节仅补控制材料审查，未重审源码/GK数学或重算旧数据；使用标准库读取归档、
Git对象、JSON与哈希，未执行生产import、fixture、数值、SSH或提交。
控制目录：`.mission/20261007-sp-fractional-trans/control-receiver-adaptive/`。

- source commit：`7757cd504c2a9539efb1b20e49a87f8a4a74120a`。
- snapshot commit：`df5fd3e47e3425836b3bf347878e3be06a2ce4a2`。
- source archive：`receiver-adapt-source-7757cd50.tar.gz`，778560 bytes，SHA256
  `c67d9a83700b61285a8c01c2585e26495a4ed81d484703131a62c59102f95abe`。
- `source_manifest.json` SHA256：
  `916d5cec2c5259b0d57faac61dc51d867b19a27cc743e18c30cb42c62967da40`。

**身份与清单：PASS。** 独立解析归档内松散Git对象并核其SHA1，snapshot HEAD与ref
一致；63个归档工作文件逐SHA256等于snapshot Git tree、source commit、当前工作区
及manifest。两个remote-imports均精确覆盖这63文件，仅排除已声明的torch虚拟模块。
合同源码键按既有 `common.hashes` 约定使用项目相对路径，外部输入使用绝对路径；
ENG 63+39=102、DEV 63+16=79，无缺漏或额外输入。39/16个输入逐SHA与本地保留的
MATH-01、原RECEIVER-DEV-01、QUAD-ADAPT-01原件字节一致，未解析其NPZ数组。

**配置、资源与launcher：PASS。** 两个 `remote-config.json` 精确等于各自合同config；
阶段名、fixed/adaptive边界、fixture数、调用数、零新增样本、求积配额及screening阈值
均与已审协议一致。thread-source-preflight分别记录102/79项核验、new_numerical_work=0，
NumPy/SciPy/OpenMP与torch intra/inter均为1。两个部署回执均含archive OK及正确snapshot。
单CPU、CUDA隐藏、RSS4GiB、输出128MiB、阶段180/1800秒和完整进程210/1830秒加10秒
退出宽限均匹配；两个 `bash -n` 通过。launcher使用独立process目录并保留pid/start/end/
exit/resource，stdout及临时/cache写入均在各自 `/data/guoyikun` root；没有重试或自动DEV链。

ENG资源回执时间为2026-10-07T13:34:09Z，available memory 265482362880 bytes，
load 0.16/0.21/0.22，GPU 1 MiB/0%，用户进程清单无科学进程。唯一非空stderr为
tmux的“no server running”，表示无现有会话，不是实验失败。

### 冻结控制文件SHA256

| 文件 | ENG | DEV |
|---|---|---|
| run_contract.json | `f344f6c8da95760a6b1562394778bd3abda8546db40f41b4dbece6dd1aa4fe44` | `34c6c152060db2482cbf2d35c04c8f2bc26a1a388b2462e3bec0b77186dcdf27` |
| launch.sh | `75142e793f687337bb9a9a99cb01094bc2a25b229f8d1626c741d06615a49734` | `f719d4bab95d3f071f67f843d5ed045db021ba16022e9e289969d8b96816ae01` |
| remote-imports.json | `6205a72ecc59eca51cd4f7718df6e2534d4fa7c2c2c41397baa4d501c2eed90a` | `6205a72ecc59eca51cd4f7718df6e2534d4fa7c2c2c41397baa4d501c2eed90a` |
| remote-config.json | `cbf3873f60ebcfcb289eccc8aae77e812b8f137b4a13b51f00ce71afda07f255` | `6671196224709468300f8804a14c36e51ae2570cab30e6c3abd56f2d647537da` |
| thread-source-preflight.json | `140a6b14771955cfd91e2d5512b3f588ad187faf9026423124c9ce4bbca87542` | `64ad624456c25c1c6725be7911c5da0ac35207e1ba9433a169ec268a310e03bf` |

**准入结论：ENG GO；DEV conditional GO。** GO绑定上述精确字节及各自remote root，
ENG的 `final-byte-preflight.txt` 已补充并读核：远端contract/launcher的两个SHA256均与
上表相同；主线程同时确认该只读检查exit0、process/attempt尚不存在。ENG远端字节启动
条件已满足，可按既有授权只执行一次。该结论基于实际哈希回执，不是仅凭上传成功。
DEV须等待ENG的真实完整结果通过所有
8例回放、13原fixtures、3组保存矩/9数据步及2mock检查，且无资源超限/字节漂移；
随后完成本阶段启动前字节/资源核验，在同一冻结合同下仅执行一次24调用开发。
任一失败保留原件并停止，不自动重试。
本准入不代表工程或开发已运行、无新的性能结论，也不更改原DEV失败记录。
