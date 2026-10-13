# Research: 无观测码设计协议与源码准入

- Query: 固定 N=64、单初值、200 步 Adam 的 D/A-only 设计是否符合冻结协议，是否满足独立执行准入？
- Scope: internal；仅协议、源码和确定性工程证据，不运行科学优化或性能仿真。
- Date: 2026-10-07
- Status: **SOURCE ADMISSION PASS**。以下固定源码可进入冻结 D/A-only 运行；这不是科学结果、10% 资格达标或新性能实验授权。

## Findings

### 已核实的协议合同

冻结依据为同目录 `CODE_DESIGN_PROTOCOL.md`；理论依据为 `CODE_DESIGN_REASONING.md`。上下文交接已提供完整协议阅读记录，本次不重复加载 Trellis 生命周期。

1. 设计域固定为 `k=1..63, d=0..15`，共 1008 项；旧 `n64_random` 为唯一初值，旧 `codes.npz` SHA-256 固定为 `9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03`。
2. 使用共轭等价式 `A=N^-1 Σ_j w_j conj(w_(j-k)) exp(+2πi4dj/N)`，`w=exp(iθ)=v^4`。令被求和项为 `t_j`，则 `∂A/∂θ_r=(i/N)(t_r-t_(r+k))`；符号与旧方向的表达式相反，不能直接照搬。
3. `J=Σ|A|^16`、`L=J^(1/8)` 对应 `∂L/∂θ_r=2 J^(-7/8) Σ|A|^14 Re(conj(A) ∂A/∂θ_r)`。固定域上的正下界排除了有效状态中的零 J；非法状态应显式失败。
4. 恰好 200 次 Adam 更新，使用 checkpoint 0..199 的梯度；初值与每个更新后状态均计算 objective/gradient，包含 checkpoint 200，因此 201 次目标评估、202608 个标量 ambiguity probes 的设计计数成立。
5. 仅更新时屏蔽坐标 0，保存全部 64 维原始解析梯度；固定原始 θ[0]。偏差修正应按 t=1..200，学习率首末值分别为 .05 与 .001。
6. 在全部 201 checkpoint 中按实际 μ 最小选取，平局取最早。checkpoint 0 是 incumbent，因此选择保证不劣于数值初始化，但优化不保证严格改进。以 smooth loss 最小代替 μ 最小不符合合同。
7. 选中码采用 principal fourth root。旧初值文件的字节锁定与 `angle(v^4)`、指数重建的浮点一致性是两个合同；不得将正常舍入差误判成初值变更，也不得放宽旧文件哈希锁。
8. 资格门为 `selected_mu <= .9*initial_mu`、单位模误差 ≤ 1e-12、独立审计通过。资格不授权任何新性能 cohort；旧三个性能 FAIL 保持不变。
9. D/A 限额各 120 秒，单 CPU 线程、隐藏 CUDA、RSS 512 MiB、输出 64 MiB；0 新观测、0 获取、0 receiver/decoder/RNG。A 的独立重建不是新候选，但必须记录实际重建成本。

### 已完成的源码合同

- 核对 `experiments/afdm_code_design_20261007/` 的 core、study、audit、protocol、配置和线程约束。
- 核对唯一旧码源及哈希、201 状态和全梯度历史、200 Adam 更新、earliest-μ 选择、root/单位模和 10% 资格。
- 独立 A 须 dense 重建所有已保存状态、用直接求导和式核查梯度、重放更新，并核查 Q、受限能量恒等式与下界；不得调用优化器生成候选。
- 核对完整设计与审计成本、失败/partial 记录、源码绑定、资源约束以及统一确定性测试回执。完成情况和证据见下文。

### Files Found

- `.trellis/tasks/10-05-method-advantage/research/20261007-performance/CODE_DESIGN_PROTOCOL.md`：冻结的 D/A-only 数学目标、优化日程、计数、资格及资源合同。
- `.trellis/tasks/10-05-method-advantage/research/20261007-performance/CODE_DESIGN_REASONING.md`：受限能量恒等式、μ 下界、高阶目标和可主张边界。
- `experiments/afdm_code_design_20261007/`：本轮独立核查的实现目录，最终判定为源码准入 PASS。

### 首轮源码核查（不代替最终准入）

以下为静态源码核查；没有运行科学优化，亦没有将静态阅读描述成运行验证。

| 合同 | 源码证据 | 核查结果 |
|---|---|---|
| Ω、共轭方向和归一化 | `experiments/afdm_code_design_20261007/core.py:10` | `k=1..N-1`，`d=0..N/4-1`，相位字符 `exp(8πijd/N)`，除以 N；固定 N64 时为1008项。 |
| p=8 势及解析相位梯度 | `experiments/afdm_code_design_20261007/core.py:16` | squared 的8次方求和及1/8幂；`weighted=|A|^14 conj(A)/J^(7/8)`，`-2 Im(t_r-t_(r+k))/N` 与直接导数相符。正 J 和有限梯度均显式检查。 |
| 唯一旧初值 | `experiments/afdm_code_design_20261007/study.py:26` | 历史attempt须complete，codes.npz哈希须一致，读取 `n64_random` 的四次幂角度。无RNG调用。 |
| 201评估和200更新 | `experiments/afdm_code_design_20261007/study.py:39` | 每状态先评估/记录，index200才退出；两阶动量、偏差修正、学习率分母199、eps1e-8均一致。 |
| 全梯度与gauge | `experiments/afdm_code_design_20261007/study.py:42` | 先复制完整梯度进trace，更新副本才屏蔽第0维；每次更新精确检查θ[0]未变。 |
| earliest-μ 与root | `experiments/afdm_code_design_20261007/study.py:57` | NumPy argmin返回最早最小值；对选中phase取principal fourth root；10%和单位模门不修改旧性能结果。 |
| 完整与失败计数 | `experiments/afdm_code_design_20261007/study.py:64` | 成功按entered×1008记录；异常保留已完成trace及entered/completed分开计数，重新抛出异常。 |
| 配置字节与源码绑定 | `experiments/afdm_code_design_20261007/study.py:88`；`experiments/afdm_code_design_20261007/protocol.py:21` | 固定配置SHA；项目Python源码须与HEAD字节一致；后续recorder保存实际源码。审查本身未执行Git。 |
| D/A预算与单线程入口 | `afdm_sp_joint_unrolled/outputs_code_design_20261007/run_contract.json:2`；`afdm_sp_joint_unrolled/outputs_code_design_20261007/launch_v1.sh:10` | 120秒/阶段、240秒总额、202608新geometry、零新观测、512MiB/64MiB与协议一致；环境显式单线程、隐藏CUDA，AFDM环境运行D后A。 |
| 隔离快照与旧码复制 | `afdm_sp_joint_unrolled/outputs_code_design_20261007/dispatch/pack_source.py:18`；`afdm_sp_joint_unrolled/outputs_code_design_20261007/dispatch/bootstrap_remote.py:46` | 载荷使用已提交字节并生成SHA清单；新隔离目录排除覆盖；旧D结果只读复制并校验codes哈希，另存来源。 |

复用的资源与记录合同位于 `experiments/afdm_coherent_structure_20261006/protocol.py:49`：绑定私有recorder到本包和本artifact、累计预留geometry、核对实际计数、检查进程峰值RSS。`experiments/afdm_phase_information_20261006/protocol.py:30` 实施项目Python源码HEAD字节校验；`experiments/afdm_shared_channel_20261004/common.py:18` 使用exclusive写入和严格JSON，避免覆盖/NaN静默入账。

`experiments/afdm_code_design_20261007/test_core.py:10` 含固定N8有限差分与受限能量测试，另有CAZAC高旁瓣反例和非法phase检查。本审查只读测试内容；通过情况采用下方最终统一测试回执。

### 独立审计器源码核查

- `experiments/afdm_code_design_20261007/audit.py:38` 单独构造 `(k,d,j)` 稠密字符项，以直接求和重建 A；每坐标直接计算 `(i/N)(t_r-t_(r+k))` 后求导，没有调用 core、优化器、FFT 或 RNG。逐坐标循环包含第0维。
- `audit.py:64` 核查受限能量、两个 coherence 下界、p=8 norm 上下界、高阶能量下界与整体相位导数和为0；通用N表达在N64时精确退化为冻结理论合同。
- `audit.py:79` 只重放保存的转移。矩阵必须同形且有限，θ[0]须逐状态精确保持；更新使用保存梯度的屏蔽副本与固定200步学习率日程，不追加候选。主入口另将trace强制为201×64，因此这里的通用短trace接口不缩减科学审计数量。
- `audit.py:99` 核查最早最小μ、principal root和四次幂一致性；10%资格可为false而审计仍通过，正确区分一致性与科学设计目标达标。
- `audit.py:118` 要求历史D与新D complete，新D退出0且符合120秒/512MiB预算，不接受partial证据；校验关键artifact、当前本包源码对D源码记录、历史codes固定SHA，以及旧设计成本的来源字段。
- `audit.py:154` 精确验证trace字段、形状、实浮点/有限性及原始phase；对201状态独立重建全部loss/μ/Q/64维梯度及能量关系。随后重放200转移，并独立确认dense μ序列的最小checkpoint，读取码并核查选择字段。
- `audit.py:183` 严格检查D的整数成本：201目标评估、202608新geometry、0新观测/获取/receiver/decoder/RNG。A诚实记录201重建状态、12864未屏蔽导数、200转移和202608个已保存ambiguity值重建；A的新候选/geometry/观测均0。
- `experiments/afdm_code_design_20261007/test_audit.py:13` 覆盖独立有限差分、标量字符和、固定CAZAC/cubic反例、损坏能量、非法phase、手工Adam两步、gauge/转移损坏、最早平局与root、未达标但一致的checkpoint，以及hash损坏。
- `experiments/afdm_code_design_20261007/test_study.py:14` 检查配置SHA/固定预算，并通过mocked objective异常验证完整前缀trace与entered/completed计数分开保留；这是故障fixture，不是科学优化运行。

审计器作者 `important_final_review` 最后新增 `test_audit.py:81` 的固定200步合成保存轨迹，仅最后一步非零，直接核验学习率终点 .001；不求科学目标、不选新码。最终audit fixtures为11个，其余core/study为5个。

### 最终验证与结论

主会话 `/root` 提供最终统一回执，作用于本报告下列SHA版本：

- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m unittest discover -s experiments/afdm_code_design_20261007 -t .`：**16/16 PASS，0.035秒**。
- `ruff check experiments/afdm_code_design_20261007 afdm_sp_joint_unrolled/outputs_code_design_20261007/dispatch`：**PASS**。
- 启动脚本 `bash -n` 和只打印导入清单的 CLI 检查：主会话回执 **PASS**。其后仅新增测试，运行源未再修改；`dispatch/import_paths.json` 含14条实际项目源路径。
- `important_final_review` 提供源码compile通过回执。环境没有mypy/pyright及对应配置，因此未将compile称为类型检查。

独立审查者本轮亲自完成协议/源码只读核查、最终文件SHA计算及本报告写入；未重复运行主会话已通过的测试，未执行Git/SSH、科学D/A、观测生成或接收机。测试归属与静态阅读证据严格区分。

**结论：当前固定版本通过 D/A-only 源码准入，未发现阻断项。** 执行仍须使用既有deinlab/AFDM隔离快照及本预算；若源码或合同变化，当前哈希准入不自动延伸。科学资格须在实际D完成并经独立A通过后判定；即使资格通过，也不得自动追加性能cohort、改变旧三个性能FAIL或重启搜码。

### 最终源码与控制 SHA-256

前缀 `pkg/` 为 `experiments/afdm_code_design_20261007/`；`out/` 为 `afdm_sp_joint_unrolled/outputs_code_design_20261007/`。

| 文件 | SHA-256 |
|---|---|
| `pkg/__init__.py` | `f131c36bee96a92a1542cd01ff56ab3d6848e8fb3b765f78ff7c498975630ca3` |
| `pkg/audit.py` | `72d88f232cfe5bbdf13c8f6cd9c7ba34a426ffe8ba0075437638c2b917ffe890` |
| `pkg/core.py` | `41cda4120452d7aa650f48db9f854acca71a17bff786235153b9232b48e880e3` |
| `pkg/protocol.py` | `06244df92a1baf3ec32d01d5d6d523a0cc7f8059842a89a20ef9f5d50ed983b0` |
| `pkg/study.py` | `42ce75c4daaf1bcfecf06144a33f02e0efbd17b19527ca51aa45f467424b1245` |
| `pkg/test_audit.py` | `afa3e701c94807a31cee2bc60c9cfa3724ab5bffa28e53f045082c35996ee50c` |
| `pkg/test_core.py` | `1a01dc660f5cd58166799bbc64b49ad074d5df336ac17c3543cfb315540a9ebf` |
| `pkg/test_study.py` | `6b55f07723a8f36ebb4ec834f06959e31a18f543d02a137bde7a6e4f2fb22308` |
| `pkg/thread_binding.py` | `595aa7384f21e20ac23b965c9e6401a0290baf905207648a0dbfb344059bd13f` |
| `pkg/STUDY_CONFIG.json` | `65eec42c367a0de17a17377dec04cb6f65c17cc5a4329735571796492b8728e0` |
| `out/run_contract.json` | `6de4167a07c57982dcb914f28de402abf9fdd06fb76d0061008da8810e60d98d` |
| `out/launch_v1.sh` | `a65b7cbf7e5a08d9f00f7f2b2e4cde8c26c1cb730d912d89899efab9ddaa943e` |
| `out/dispatch/bootstrap_remote.py` | `666a544334e6ce8284fc9c39ba635c48b750f9d690634edb4035f916b45f387b` |
| `out/dispatch/harvest_remote.py` | `429cd694d9c2a2b195c9f72cb1941ce09c9b50c7f1ac53af486fb69d2b960032` |
| `out/dispatch/pack_source.py` | `6eb482a58af0d6e47681e8d1e5ccfdae60eeca9d003f240001ad012efefe26a5` |
| `out/dispatch/import_paths.json` | `de1d4186084ffc56c892dd77e58b90d49c6ddbb8378a61729e77cf8ab515189e` |

### External References

无。本次为内部冻结协议与源码合同核查，不引入外部算法或额外候选。

### Related Specs

本次适用的边界由主会话紧凑交接提供：仅写本报告，不修改代码、CSV、旧结果；不 Git、不 SSH、不科学运行、不搜 seed；沿用既有服务器隔离规则。未重新读取、亦不声称已重新读取其他规范。

## Caveats / Not Found

- 当前源码准入PASS不能写成科学结果或10%改进已实现；尚无本轮科学D/A输出可供结果审核。
- 本报告没有运行优化、观测生成或接收机；本地fixture和静态检查不能替代实际服务器运行证据。
- `μ≥1/√67` 是下界而非可达性结论；降低 μ 不自动推出既有低增益残余错误或 BER 的改善。
