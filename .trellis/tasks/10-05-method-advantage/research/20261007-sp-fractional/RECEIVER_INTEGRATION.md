# Continuous multipath SP 接收机接入研究

日期：2026-10-07。所属任务：`.trellis/tasks/10-05-method-advantage`；执行状态仍以 `.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv` 为准。

本文是源码接口研究，不是实验准入、接收机实现或性能结论。本轮只读源码、写本文；没有导入接收机运行，没有本地/远端仿真、SSH 或 commit。数学模块六文件已提交于 `c639a4b0`，本轮未修改。

## 1. 结论与最小接入链路

已有真实连续多径 SP 帧生成、观察量隔离、F1 保槽前端、完整点几何接收机、LDPC 消息和证据保存接口。最小可解释原型应复用以下链路：

1. 冻结 `make_frame` 按原生产规律生成 G0 归一化物理增益和消息/噪声；`physical_observation` 沿用这些增益，生成 G1 全 CPP、未截断分数 Doppler 观测。
2. 生成进程分别保存 observed 与 truth；接收入口严格只收 `y/pilot/sigma2`。所有接收结果保存后，评分进程才打开 truth。
3. `PhysicalF1.acquire` 从同一 observed pilot 得到至多 8 个物理槽，允许相同 delay 上存在不同 Doppler；初始数据均值为 0、方差为 0.5、bit prior 为 0。
4. 新候选在这些 observed 槽上接入连续 Doppler 因子、联合复 Gaussian gain 工作因子和数据更新。现有 `PathMoments` 只提供矩计算；积分、完整迭代、KL-MM 数据更新与停止规则尚需另行实现和冻结。
5. 机制对照保持相同槽、gain/data 因子、反馈和预算，只把 Doppler 因子限制成点值。另运行完整 `receive_f1` 与 native joint20 作为强接收基线。现有 scalar joint 仅有标量 gain variance，不能充当“只改变 Doppler 不确定性”的完全匹配消融。
6. coded 入口使用真实 LDPC 消息；纯 uncoded 入口只调用 detector，decoder 调用数必须为 0。双方计入全部前端、内循环、反馈、失败、初始化及证据保存成本。

固定槽是观测驱动的候选族，不是已知真实 support。这里不借 truth 初始化路径数、delay、Doppler、gain 或消息，也不把数学核验中的有限节点诊断分布当成生产先验。

## 2. 路径索引与真实生成接口

以下路径均相对项目根。为缩短接口表，使用这些别名：

| 别名 | 源码目录 |
| --- | --- |
| FROZEN | `experiments/sp_afdm_frozen_20260920` |
| UP | `experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff` |
| NATIVE | `experiments/sp_afdm_native_joint_20260921` |
| F1 | `experiments/cstate_necessity_stageA_20260928` |
| STRUCT | `experiments/afdm_structured_inference_20261003` |
| OLD | `.mission/20261001_23-33-35-afdm-innovation-space/experiments` |

冻结规模为 N=1024、rho=0.5、AF 域 QPSK、delay cap=102、integer Doppler cap=2。bit 顺序为 all-I then all-Q；LDPC 为 n=2048、dv=3、dc=6、seed=20260726。

| 接口 | 返回与复用边界 |
| --- | --- |
| `UP/run_frozen_i1_smoke.py: build(args)` | 返回 `(system, model, code, header)`。调用 `_make_config_a(1024, 2., 8, 10., 4.)`，构建冻结 C2-rel 模型、LDPC 并检查身份。 |
| `UP/afdm_sp_joint_unrolled/loop9_cache_features.py: _make_config_a(n_total, v_mean, p_paths, tau_ms, fs_factor=2.0)` | 建立真实 UWA/DAFT 配置，保留 dense `system._A/_A_H`。生成/bootstrap 进程不能因此宣称整体 O(NP) 内存。 |
| `UP/afdm_sp_joint_unrolled/budgeted_support_eval.py: make_frame(system, code, replicate, index, snr, uncoded=False, *, split=1, rng_factory=None)` | 返回 y/H/params/info/coded/data/pilot/noise/sigma2 及种子标识。component 1/2/3 分别控制 channel/message/noise。 |
| `UP/afdm_sp_joint_unrolled/supplement_g1.py: physical_observation(raw, system, *, prefix_length)` | 返回 `(out, diagnostics)`；替换 H/y/params、保留 `g0_reference`。G1 dense H 与实际 CPP 传播的相对误差须通过 1e-10 检查。 |
| 同文件 `reuse_at_snr(raw, diagnostics, snr)` | 同一 exogenous block 重缩放噪声；不产生新的独立 channel，不能增加独立样本计数。 |
| `OLD/generate.py: generate(rt, allocation_path, split, out, registration)` | 已有独立生成与封口范式：校验 registration/allocation SHA、固定分离随机流、恢复全局 RNG、observed/truth 分目录。其旧注册和种子空间不直接移用到新任务。 |

`make_frame` 使用 `data=sqrt(1-rho)*qpsk_map(coded, scale=1)`、`pilot=sqrt(rho)*system._zc_seq`、`sigma2=10**(-snr/10)` 和复单位方差噪声。`uncoded=True` 时发送长度 2048 的随机 uncoded bits；不是先发送码字再事后称作 uncoded 实验。

G0 包含五系数 Dirichlet 尾的局部归一化、integer Doppler 裁剪、0.01 pruning 和 G0 Frobenius 归一化。最终物理 gain 可写成 `h = raw / sqrt(rawᴴ R_G0 raw)`。G1 必须沿用此 h，不再次归一化；源码 `GAIN_RULE` 为 `reuse_g0_physical_gains_without_rescaling`。真实 gain、Doppler 与潜在 PDP 的耦合约束不能被独立 Gaussian 工作先验悄悄替代后仍称相同生成规律。

不要复用旧 `budgeted_support_eval.run_frame(...)` 作为新 observed-only harness：它读取 `frame['params']['P_actual']`，并有 truth observer/oracle support 路径。`FROZEN/src/run_local.py:_load_or_create_frame` 也同时返回 observed/truth，observed 含 seed，必须显式抽出三字段；其 `same_delay_collision` 分支修改 delay，不代表未经改动的生产生成 law。

## 3. 无 truth 初始化与点几何强基线

### F1：推荐的 observed 槽初始化

`F1/f1.py` 提供：

```python
PhysicalF1(n, c1, c2, lmax)
PhysicalF1.acquire(y, pilot, sigma2) -> dict
```

前端使用 103×25=2575 个 full-CPP atoms，搜索 Doppler 网格 [-3,3]、步长 0.25，最多选 8 个槽。每新增路径进行 coordinate/cyclic refinement；局部连续 bracket 为中心 ±0.75。它保留同 delay 的不同 Doppler 槽，只拒绝同 delay 上距离小于 1e-6 的近重合槽。此搜索范围和局部 bracket 是算法配置，不能直接解释成原生成先验支持。

返回字段包括 `channel/delays/dopplers/gains/bank_centers/stopping_reason/objective_history/counters/pilot_energy/bank_build_seconds/acquisition_seconds`。计数器包含 `bank_scans/bank_scores/coordinate_scores/newton_steps/joint_solves/coordinate_visits/accepted_coordinates`。病态系统、求解残差越界或无合法槽通过 `NumericalFailure` 显式失败；没有 truth fallback。

已有完整强基线：

```python
# F1/native_f1.py
receive_f1(observation, system, code, *, checkpoint_sink=None, record_states=False)
# -> decoder, arrays, timing

# F1/keep_slots.py
time_refine_keep_slots(y, pilot, mu, v, ls, ks, gs, c1, c2, noise,
                      mode='soft', max_paths=8, rounds=2)
# -> Channel, detail
```

`receive_f1` 严格检查三字段输入和冻结 N/rho/delay cap。它执行一次 F1 acquisition，随后两轮 `time_refine_keep_slots` → `scalar_joint(iterations=20, damping=.3, gain_mode='joint')` → `decoder_messages(maxiter=50)`。keep-slots refit 保留 ordered slots，并在 soft CE 的 Gram/trace 目标中保留跨路径项；条件数和求解失败显式抛出。它不是新 continuous-posterior 算法。

同一 acquisition 结果可用于机制对照以隔离后端差异；完整耗时比较中，每个 arm 必须计自己前端的真实完整调用成本。不能从 F1 第二轮最终状态免费起步，再与 F1 从头运行的耗时相比。

### Native：保留现有完整接收机锚点

```python
# FROZEN/src/receiver.py
pilot_front(observed, system, code)

# NATIVE/src/twofft.py
time_refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise,
            mode='soft', max_paths=8, rounds=2)
scalar_joint(y, pilot, c, noise, pd=.5, prior=None, iterations=20,
             damping=.3, gain_mode='joint', record_states=False,
             observation_domain='time')

# NATIVE/src/native_twofft.py
receive(observation, system, code, rounds=2, iterations=20,
        ce_mode='soft', gain_mode='joint', checkpoint_sink=None, record_states=False)
# -> decoder, arrays, timing
```

`pilot_front` 用 515 列 pilot regressors 和冻结 `BaselineInitializer('B0-p2-s0.5', lstsq_driver='gels')` 产生 40 个候选，无 truth。后续 native `time_refine` 对 delays 做 `np.unique`，最多保留 8 个 delay group，每个 delay 只有一个中心。这正是优先采用 F1 保槽前端的理由。

`scalar_joint` 使用 full CPP，无 fractional-tail deletion；在一次 detector batch 内 Doppler 为点值，gain mean 可更新，gain variance 为标量。其 `CN(0,I/P)` 是工作 gain prior，observed gain 是初始化。第二轮 `raw_check_extrinsic` 替换 bit prior，`raw_app` 形成 CE 数据矩；这些均来自同一 y，不是新增独立观测。

更强推断对照已有核心，可在后续冻结预算允许时通过相同前端/反馈调度接入：

```python
# FROZEN/src/structured_ep.py
ep_t(ydata, c, noise, pd=.5, prior=None, iterations=8, damping=.3)
# ydata = y - c.apply(pilot)

# FROZEN/src/bilinear.py
pbigabp(y, pilot, c, noise, pd=.5, prior=None, iterations=8,
        damping=.3, gain_prior_variance=None)
```

`NATIVE/tests/screen_fair_controls.py` 展示共同 time-refine、两轮 coded 调度及 EP/PBiGaBP 接线。此文件有顶层 warmup、仿真和写结果行为，不能当无副作用工具模块 import。F1/native 足以作最小接入锚点，但不能替代后续面向最强已知基线的性能论证。

## 4. 数学模块与消息接口的实际边界

冻结的新矩模块位于 `experiments/afdm_sp_fractional_20261007/moments.py`：

```python
PathMoments(n, c1, c2, delays, doppler_nodes, weights, gain_mean, gain_cov)
prepare_source(pilot, data_mean, data_variance)  # -> SourceMoments
expected_quadratic(y, source)
coordinate_coefficients(y, source)
gain_statistics(y, source)                    # -> expected Gram, matched vector
gram_matvec(value)
gram_diagonal()
mean_adjoint(y)
coordinate_log_density(coefficients, nodes, noise_variance, log_prior)
```

除构造函数和末行模块函数，其余均为 `PathMoments` 方法。`SourceMoments` 绑定创建它的具体对象；gain/Doppler 状态改变后不能把旧 source 直接传给新对象。gain covariance 是完整 P×P 复协方差。节点/权重形状为 P×K，权重严格正、各行和为 1；有限节点 law 的矩精确，不等于已证明连续积分精度。单节点是合法退化因子，可服务点值机制消融。

`coordinate_log_density` 只在给定节点计算未归一化连续坐标 log-density；调用者提供原先验 log-density，它不积分、不选支持、不生成 data-dependent prior。`gain_statistics` 不执行 gain 更新。矩模块尚不能直接产生完整 decoder LLR，也没有完整 KL-MM 接收循环。真实生产先验与 Gaussian/独立 Doppler 工作因子的差别必须保留在模型说明中。

`FROZEN/src/messages.py` 的可复用接口是：

```python
alphabet(pd)                          # -> symbols, bits
logprior(L, pd)
moments(L, pd)                        # -> mu, variance, pseudo
marginal(likelihood, prior, pd)       # -> extrinsic, app, mu, variance
```

输入 LLR 为 all-I then all-Q，正值表示 bit 0。`marginal` 接收 N×4 log-likelihood scores，计算 `extrinsic=app-prior`，只扣目标 bit 自身 prior，保留另一 bit prior。新 CAVI/KL-MM 势是否构成可送 decoder 的 extrinsic 需要在新调度中定义；不能因函数名叫 marginal 就声称它是原真实 posterior 的精确外信息。

```python
# UP/afdm_sp_joint_unrolled/supplement_messages.py
decoder_messages(code, incoming_llr, *, maxiter=50)
```

返回 `decoded/decode_ok/iterations/incoming_llr/raw_app/raw_check_extrinsic` 和消息语义、耗时、hash、熵等 metadata。现有 native/F1 在送 decoder 前将 LLR clip 到 ±20，并将 check-only 消息作为下一轮 prior；复用时不要再额外调用一次 decoder 来重建证据。

`UP/afdm_sp_joint_unrolled/e1_ldpc.py` 还提供 `encode(code, info_bits)`、`extract_info(code, coded_bits)`、`qpsk_map(bits, scale=1.0)`、`decode_soft_messages(code, llr, maxiter=50)`。评分应区分：

- coded：完整 decoder 输出、coded bit/frame errors、info bit/frame errors、syndrome、undetected errors、迭代数；`STRUCT/pipeline_screen.py:scores(decoder, truth, code)` 可作为 coded scorer 参考，并保存 logscore/Brier。
- coded 帧的 decoder 前 BER：对 detector LLR 做 `(llr < 0).astype(uint8)`，与发送码字比较，分母 2N；这仍是 coded 发送下的 raw BER。
- 真 uncoded：`make_frame(..., uncoded=True)`，只跑 detector/prior0，不调用 decoder；hard bits 与长度 2N 的 uncoded truth 比较。不能直接套用以 `free_cols` 抽取信息位的 coded scorer，也不能先跑 decoder 再扣除其耗时。

## 5. 依赖、身份绑定与完整计数

### 最小数学依赖与生产 runtime 不是同一层

矩模块直接依赖 NumPy 和冻结 `physical.daft`；相关物理/推断核心使用 NumPy/SciPy。`experiments/afdm_inference_causal_20261002/oracle_comparison.py:load_frozen()` 可轻量加载冻结 physical/messages/twofft 并检查模块路径，但不构建真实 system、LDPC、checkpoint 或生产接收 runtime。

已有生产复用入口为 `OLD/wrapper.py:bootstrap(project=PROJECT, source=None, baseline=None)`。它保护 frozen namespace，构建 `receiver.context()`，返回 `rt.system/rt.code/rt.native/rt.receive_f1/rt.evidence/rt.setup/rt.header/rt.required_sources` 等。`context()` 即使调用方不用 C2-rel model，仍支付冻结模型构建成本。该 wrapper 还载入旧 acquisition、CSTATE、geometry 等模块，属于宽依赖的可靠现成入口，不能称作新候选的最小依赖。

最小生产接入应复用 frozen loader 的路径/身份检查、context、F1/native 与消息闭包；若直接用旧 bootstrap，就完整记录它实际加载的闭包和 setup 成本。不要调用旧 `wrapper.receive(...)` 代替单纯 F1/native anchor：它包含额外 cascade/CSTATE/acquisition 策略。

静态读源码尚不足以宣称已得到完整动态依赖清单。正式运行前，主线程须冻结实际 source manifest、运行参数与环境；尤其避免 top-level `physical` 与 package-qualified `experiments...physical` 成为不同模块/类对象，导致计数器漏记。

资产身份（已有 `STRUCT/pipeline_screen.py:check_cache()` 检查值）：

| 资产 | SHA-256 / 约束 |
| --- | --- |
| `UP/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz` | `cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052` |
| `UP/07_checkpoint/frozen-c2rel-checkpoint.pt` | `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91` |
| LDPC `G` bytes | `bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af` |
| LDPC `H` | shape `(1026, 2048)` |

`build_code(n=2048, d_v=3, d_c=6, seed=20260726, cache_dir=None)` 在缓存缺失时可能重新生成并写入。新运行应预检存在/hash，缺失时明确失败，不默默重建。`bootstrap` 后还需按既有修复设置 `rt.environment['effective_blas_post_bootstrap']=blas_binding()`，再执行 `verify_effective(rt)`；见 `experiments/afdm_shared_channel_20261004/production_diagnostic.py:prepare_runtime()`。

### 完整工作量与保存协议

`STRUCT/pipeline_screen.py:observe_operations(native, candidate)` 已示范实际包装 pilot front、CE、detector、decoder、Channel regressors/apply/adjoint、TimePathOps、FFT/IFFT、solve/Cholesky，并在退出时恢复包装。它硬编码旧 Gaussian-pair candidate，不能原样作为新算法通用计数器。`STRUCT/local_receiver.py:receive(..., enabled=False, rounds=2, iterations=20, block_size=2)` 可借鉴严格三字段 schema 与 disabled 路径；不要改变其 `enabled=True` 已有候选含义。

新完整计数至少需要以下可分解字段，不仅是 detector 自报的 `fft_count`：

- 样本与调用：独立 channel/exogenous blocks、各 SNR 复用、arm、started/completed/failed、重试、decoder calls/iterations、outer/inner iterations。
- 前端与算子：F1 bank 构建/扫描/打分、continuous coordinate evaluations、CE visits/solves、regressor 列数、H/Hᴴ 调用、FFT/IFFT 的向量变换数及长度。批处理按实际轴长度计算 transform 数，避免一次 Python 调用冒充一次 FFT。
- 新方法：每个 Doppler 因子的积分节点与 refinement、log-density evaluations、目标函数和 line-search evaluations、KL-MM steps、`gram_matvec/gram_diagonal/mean_adjoint` 次数、P×P gain solve 次数与维数。失败的 proposal/line-search 也计入。
- 时间/内存：冷启动与 setup、bank build、每轮 CE/detector/decoder、receiver ready、完整保存后的 wall/CPU、峰值内存；说明 dense 生成资产是否常驻。缓存构建和预计算单列并纳入可比较总账，不把缓存免费化。
- 原始输出：每轮 entering geometry、gain mean/covariance 或 variance、Doppler law/积分诊断、数据矩、prior/input/app/check LLR、硬判决、目标/停止原因、全部计数、source/config/environment/observation hash。

`PathMoments.work_counts` 只记录其 `_daft/_fft` 路径，不涵盖前端、积分指数计算、线搜索、LDPC、bootstrap 或保存；应与实际调用覆盖核对，不能把它当完整计算量。若同时记录外层 FFT 拦截计数，区分逻辑 DAFT 次数与底层 FFT 次数，避免相加造成重复计数。

`FROZEN/src/evidence.py:save_artifact(path, payload, identity)` 返回 SHA，`load_artifact(path, expected_identity=None)` 校验结构化 NPZ 身份，是可复用的保存原语。`checkpoint_sink` 可保留上一完成轮，后续异常必须继续传播；checkpoint 保存成本属于完整调用成本，失败 checkpoint 不能计成成功 frame。沿用 production diagnostic 的顺序：只打开 observed → 验证 hash → 实际计数包裹完整接收 → 保存 raw → 记录 wall/CPU；所有调用完成/封口后再开 truth。新任务使用新的输出目录、注册和 seed namespace。

## 6. 已有失败事实与比较约束

以下均来自已有落盘材料，本轮没有复跑；小样本与旧数据复用不构成新确认：

| 已有证据 | 对本次接入的意义 |
| --- | --- |
| `FROZEN/README.md`：旧 sparse-innovation campaign 84 个独立观测、260 个 Stage 1/256 个 Stage 2 调用。8 dB 的 P_M24_I20 为 FE 0/32，对照 EP 为 1/32，但完整中位时间 1.219 s 对 0.494 s；6 dB 为 30/32 对 32/32、1.213 s 对 0.535 s，未满足继续开发规则。 | 少量 FE 改善不足以抵消完整成本；不能只报告核内时间。 |
| 同 campaign 的 PBiGaBP 在 6 dB 为 FE 24/32、13.773 s。历史 corrected source `31d5ec0d` 当时未在本地挂载。 | 保留强准确率参考及 deadline 约束；不能宣称当前源码能 bit-exact 回放该历史结果。 |
| `NATIVE/docs/RESEARCH_VERDICT.md`：旧 8 帧（6/7 dB 各 4 帧）scalar joint20 soft 为 FE 1/4、0/4；full gain covariance block 未改帧失败模式。抑制 gain variance 而保留 mean update 仍为 1/4、0/4；fixed gain 同 soft CE 更差，为 4/4、2/4。 | 联合 gain mean 更新已有明确作用；full covariance 或 uncertainty 不能单凭数学丰富度声称增益。 |
| 同 native 记录：动态 joint tangent/relinearization 曾造成损伤，冻结后未产生新的 rescue。 | tangent、relinearization 或 gain covariance 不是可重新包装的未试机制。 |
| `experiments/afdm_shared_channel_20261004/PRODUCTION.md`：6 个保存观测（三 channel clusters × 10/20 dB），native joint20 FE 0/6；joint1、pair、fixed1、fixed20 均 FE 6/6；pair 共 1252 coded bit errors；observed_H_pair FE 3/6。native 一/两 outer 均为 0/6。 | 一 outer 内含 20 detector steps，不是“一次 detector 更新就成功”。旧 Gaussian-pair 不能作为唯一或强基线。 |
| 同 production：v1 bootstrap 缺 `effective_blas_post_bootstrap`，0 receiver/decoder calls；v2 修调用方后 36 calls 完成，保留 v1 成本。 | runtime 核证失败是实际失败；不得吞掉、静默回退或从总账删除。 |

更详细的生成/先验依据见 `experiments/afdm_shared_channel_20261004/PRODUCTION_PRIOR.md`；消息和 working-model 边界见 `STRUCT/MODEL_CONTRACT.md`。本文没有为 F1 或新 continuous 候选补造未执行的性能数据。

## 7. 主线程仍须冻结的事项

接入路径已确定，尚不能直接启动真实效果实验。以下决定不能从现有数学 fixture 或历史实验偷偷继承：

1. 连续 Doppler 原先验/支持、observed 槽族与局部窗限制的解释；gain 工作先验协方差与真实归一化先验的差异。
2. 积分方案、节点/refinement 精度与失败门限；不能只采用 MATH 的三节点诊断 law 就称 continuous posterior。
3. gain/Doppler/data 更新顺序、KL-MM bound/line-search/停止规则，以及 decoder 外信息与同观测重复使用的工作因子解释。
4. 匹配的点 Doppler 消融、完整 F1/native anchors、EP/PBiGaBP 的后续比较范围；共同预算和完整计算成本定义。
5. coded/uncoded 输出协议、样本/独立 block 数、SNR、seed、选择与确认分离、性能接受门限及失败/重试记账。
6. 新接收入口及操作计数覆盖、动态 source/assets manifest、环境/线程/远端准入。研究数值执行仍仅可在主线程按服务器规则准入后的 deinlab 进行。

这些是接入实现与实验注册的剩余工作，不是本轮待补的仿真结果。
