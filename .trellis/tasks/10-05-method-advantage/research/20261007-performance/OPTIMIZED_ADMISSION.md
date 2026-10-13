# Research: 优化码三臂性能验证的协议与源码准入

- Query: 固定优化码的三臂配对性能协议是否保持模型、比较、公平计时、计数和探索性主张边界；源码能否进入冻结 P/A 运行？
- Scope: internal；协议、源码和确定性工程检查，不运行性能仿真、搜码或搜seed。
- Date: 2026-10-07
- Status: **SOURCE ADMISSION PASS**。本报告固定版本通过三臂 P/A 源码准入；不代表本轮性能已通过、优化优于旧random，亦不覆盖旧三个FAIL。

## Findings

### 协议合同核查

1. `OPTIMIZED_PROTOCOL.md:7` 将模型固定为此前 SCREEN128 的 N64/T2/SNR5、CP16/L80/s5、统一delay/CFO与共同gain分布、QPSK及已知nominal noise；仅增加一个预先冻结的优化码。SCREEN128和FULL的混合似然、48点gain网格及完整调用边界不变。
2. `OPTIMIZED_PROTOCOL.md:9` 固定旧codes SHA和优化code/D-results/D-attempt/A-results四个SHA。新P采样前须验证原始码源、新D complete、design_qualified以及独立A audit_pass；不得重新设计或按本批结果换checkpoint。
3. `OPTIMIZED_PROTOCOL.md:13` 固定seed2026100705和1024独立组。每组共享 l、ν、ρ、φ、QPSK状态及复噪声底层变量，形成三臂配对；组之间独立。顺序为六个完整调用按group mod6轮转，无warmup、无中途终点或seed重试。配对并不要求三种码的实际Y完全相同，而要求外生变量共同且每臂按自身码生成Y。
4. 新计数独立算术核验：1024×3=3072个波形数据集；×T2=6144个64维观测向量；×64=393216个复样本。每数据集两个方法，因此6144次完整调用。每数据集FULL1024+SCREEN128=1152个似然candidate，共3538944；×48gain=169869312次gain评估。
5. 新design/geometry/RNG-for-design均0；旧随机码、二次码以及本次优化码的历史设计成本均须单列。优化D/A的1.382412秒与202608geometry来自已完成历史记录，不重跑、不算成免费新设计。
6. 五项主门保持实质要求，只将待评价的proposed码指向optimized：完整合同/独立raw审计及FULL目标不劣于SCREEN128；完整累计速度比≥3；同码bad discordance的单侧95%CP上界≤.02；二次SCREEN128错误率减optimized SCREEN128错误率≥.10且探索性配对normal95%区间下界>0；optimized SCREEN128错误数≤256/1024。
7. 配对差应逐组取 d=error_quad−error_opt，SE=sqrt(samplevariance(d)/1024)，不能用两独立binomial方差替代。1024样本的10pp门相当于至少103个净减少错误；点估计和区间均使用本批数据。
8. 独立确定性SciPy核验 CP 边界：x=12时U=0.018917867089388803；x=13时U=0.02010854052334146。因此固定n1024的接受集合确为x≤12。反向discordance另报，不能用净错误差替换bad-discordance风险。
9. `OPTIMIZED_PROTOCOL.md:21` 要求本批optimized对oldrandom的配对对照。相对二次码通过主门不自动证明优化本身优于旧random；此前random273/1024属于另一批，不能当配对对照或归因依据。
10. 本次明确为第四个受先前结果启发的development配置，不是单个全局预注册5%确认性研究。旧三个FAIL保留，任一主门失败则本轮FAIL；不池化、不改门、不隐式追加。
11. P1500秒/A300秒、总1800秒、单CPU线程、CUDA隐藏、RSS2GiB、输出512MiB与范围一致。A须重建全部3072个Y及fourth-score、6144个选择/成本，24个显式混合似然spot=4组×3臂×2candidate；A不产生新观测或调用估计器。

### 已完成核查的源码合同

- 唯一固定配置、三个臂的reference与SHA资格检查必须发生在采样前。
- 复用已准入SCREEN128/FULL内核；完整调用内的变换、模板、打分和输出不得跨臂/方法借用缓存；不得泄露真值给估计器。
- 1024组、固定draw order、共享外生变量、六调用轮换和完整raw/score/choice/time保存；失败保留entered/completed计数及prefix。
- 主门只针对optimized，oldrandom效应使用本批paired difference；全部三臂的FULL/SCREEN128错误和成本可审计。
- A独立dense重建、全部选择/计数/区间/CP/门核查、24个mixture spots与旧新码来源；不调用runner或估计器补跑科学数据。
- source/attempt/runtime哈希、预算、单线程、隔离快照、统一确定性测试回执及最终源码SHA表。

### Files Found

- `.trellis/tasks/10-05-method-advantage/research/20261007-performance/OPTIMIZED_PROTOCOL.md`：本轮三臂固定性能合同。
- `.trellis/tasks/10-05-method-advantage/research/20261007-performance/SCREEN128_PROTOCOL.md`：继承的模型、完整调用、48点gain网格、五门与审计定义。
- `.trellis/tasks/10-05-method-advantage/research/20261007-performance/CODE_DESIGN_ADMISSION.md`：优化码D/A-only源码准入与原先科学边界。
- `experiments/afdm_acquisition_optimized_20261007/`：本轮三臂runner、配置、私有记录适配器和独立审计器；已完成首轮只读审查。

### 源码核查证据

以下路径前缀 `pkg/` 指 `experiments/afdm_acquisition_optimized_20261007/`，`out/` 指 `afdm_sp_joint_unrolled/outputs_acquisition_optimized_20261007/`。

| 合同 | 代码位置 | 结果 |
|---|---|---|
| 仅更换已知码臂 | `pkg/core.py:2` | 直接re-export旧SCREEN128的estimate/simulate，只将ARMS扩为三项，不另建估计器。 |
| 冻结reference在采样前 | `pkg/study.py:65` | 先校验旧D、旧codes SHA及优化四文件SHA/complete/qualified/A-pass，再于87行创建唯一固定seed RNG；无按性能换码路径。 |
| 共同外生变量与六调用 | `pkg/study.py:106` | draw顺序delay/CFO/rho/phase/states/real-noise/imag-noise固定；三臂共享同一states/noise/gain，按各自码生成Y；六方法循环按group mod6轮换。 |
| 完整调用边界 | `pkg/study.py:136` | perf_counter覆盖完整estimate(y, known-code, known-noise, method)，不传truth，不跨方法缓存；生成/I/O时间另列。 |
| 全raw与失败前缀 | `pkg/study.py:146`；`:176` | 完整保存各臂Y、底层变量、全profile/fourth、选择、cost、time和hash；异常保存已完成raw/estimate prefix、entered/completed计数后重新抛出。 |
| 主门与次对照 | `pkg/study.py:27` | 五门使用optimized，主差为quadratic−optimized；次差为本批random−optimized。全部三臂FULL/SCREEN错误与时间均进入cells。 |
| 配对方差 | `experiments/afdm_phase_information_20261006/study.py:32` | 被复用的paired_interval采用ddof1；本批单cell时SE精确为sqrt(samplevariance/1024)。 |
| 主统计独立重算 | `pkg/audit.py:130`；`:149`；`:159` | CP用binomial lower-tail二分而非复用beta.ppf；独立逐组配对方差、两个对照、optimized bad/reverse及全部五门，并检查x≤12与CP门等价。 |
| 优化码独立来源核查 | `pkg/audit.py:55` | 校验四SHA、D退出0、设计与A资格、旧码ancestry、固定checkpoint199、N64单位模；无设计重跑。 |
| 全样本独立重建 | `pkg/audit.py:243` | 1024组×三臂使用dense DFT重建Y与直接fourth，核全部六方法选择/稳定shortlist/tie/物理gain/错误与同候选FULL-SCREEN分数。 |
| 24个显式mixture spots | `pkg/audit.py:309` | 组0/256/512/768×三臂×FULL所选及下一candidate，以四Gaussian分量和48gain独立求和，不调用估计器。明确只是24点，不声称穷举重算所有profile。 |
| 完整成本 | `pkg/study.py:167`；`pkg/audit.py:317` | P严格检查6144vectors/calls等；A累加3538944 hypotheses与169869312 gains，并将旧D和优化D/A成本分别列为historical。 |
| 隔离与不可覆盖 | `pkg/protocol.py:21`；`out/dispatch/pack_source.py:18` | 复用不可变阶段记录器，HEAD源字节绑定和提交载荷导出；exclusive新snapshot/output。审查者只读源码，没有执行Git。 |
| 优化reference复制路径 | `out/dispatch/bootstrap_remote.py:60` | 将旧优化D/code、D/results、D/attempt和A/results原样复制；A/results在新reference中命名audit.json，其SHA和来源显式保存。无文件内容变换。 |
| 预算与回收 | `out/run_contract.json:2`；`out/launch_v1.sh:10` | P1500/A300、总1800、6144vectors、0geometry、2GiB/512MiB；AFDM/单线程/隐藏CUDA；harvest要求P和A完整并保留两类reference和全部阶段hash。 |

复用的 `experiments/afdm_acquisition_screen128_20261007/core.py` SHA为 `2b912f55370754f92f8021676ada1024f641e86837bdfeba0fb6700434e0bf4a`；底层 `experiments/afdm_acquisition_performance_20261007/core.py` SHA为 `68ecf535397c120e06b21f9a36d04794808d1c3e80cb4e80d6bfb82b1c9e777b`。两者均与旧 `SCREEN128_ADMISSION.md` 的准入哈希一致。此核验支持复用既有内核审查，无需重跑其科学实验。

测试源码已读：`pkg/test_config.py:10` 检查固定预算与私有适配器；`pkg/test_failure_records.py:44`/`:58` 用固定generator/故障注入检查partial证据；`pkg/test_audit.py:108` 明确覆盖次对照方向及其不改变主门，`:141` 覆盖四reference哈希与资格拒绝路径。测试运行结论采用下方最终统一回执。

### 最终验证与结论

主会话 `/root` 提供对冻结最终版本的统一回执：

- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m unittest discover -s experiments/afdm_acquisition_optimized_20261007 -t .`：**13/13 PASS**。
- `ruff check experiments/afdm_acquisition_optimized_20261007 afdm_sp_joint_unrolled/outputs_acquisition_optimized_20261007/dispatch`：**PASS**。
- launcher `bash -n`、CLI `--print-imports`：**PASS**；生成的导入清单含22个项目源路径。
- 审计器作者 `important_final_review` 另提供10个audit fixtures、ruff与compile通过回执；本次没有配置并运行类型检查，不将compile表述为typecheck。

独立审查者亲自完成协议/源码只读核查、固定CP端点和计数算术验证、最终源码SHA计算及本报告写入；未重复统一fixtures，未执行Git/SSH或科学P/A。固定fixture、source静态证据和实际科学运行严格区分。

**结论：当前固定源码通过 P/A-only 准入，未发现阻断项。** 运行必须继续使用冻结seed/三臂/1024组/6144vectors及deinlab/AFDM隔离快照、单线程和1800秒总预算；本结论不自动延伸至改动后的源码或另一批次。主要五门的联合结果须待完整P及独立A之后判定；具体归因于优化须同时查看本批optimized-vs-oldrandom配对证据。

### 最终源码与控制 SHA-256

| 文件 | SHA-256 |
|---|---|
| `pkg/__init__.py` | `70f22064d4bf4400c9f36d6e181a21317c707f3b7cbb03df54747a265133ac43` |
| `pkg/audit.py` | `4f57442cb4498aa0fce110987a85e8475a4ac96cbfd1bcf3bf0d717634ab280d` |
| `pkg/core.py` | `65b1e55d62185471c4aca3e3f71e74af7d3718293c35db1bd9d39653242ae718` |
| `pkg/protocol.py` | `91744a1e25eb15a9eb886e9ba178b694e7cb0c167f9d2d0528940eccf7504a7f` |
| `pkg/study.py` | `dc5f3986f77d2c5b962a1a040fd40251b3f6ded303cb41a58e26d025cd4b9500` |
| `pkg/test_audit.py` | `7e4397239d853f9d400fd5d8b3345bfa518af59ca31f79cae62c6e99f28775d5` |
| `pkg/test_config.py` | `13060f2e691c6553dd4ee63dc98ccf504a5b3cc36d4593da9790158c2f07bcaf` |
| `pkg/test_failure_records.py` | `5db5d43b8f0cb0b32c337b668b5e01ffa956f227fb855ac89eda49a074799075` |
| `pkg/thread_binding.py` | `595aa7384f21e20ac23b965c9e6401a0290baf905207648a0dbfb344059bd13f` |
| `pkg/STUDY_CONFIG.json` | `d2b3c6e2043b49d0c69aa861a674e728658eed01288de7767c96a2f847181f32` |
| `out/run_contract.json` | `9ef19b41a58a1b15f729899641228582b17320faec254eed9745d6de6b4df46e` |
| `out/launch_v1.sh` | `e4f3e1926d150481964bfda662679c3e479394da7d444e46632535e25056a911` |
| `out/dispatch/bootstrap_remote.py` | `58c2d32be640670c1d4faaae2bbcc27c60e45cf2fccc2e609810d03c9d48e854` |
| `out/dispatch/harvest_remote.py` | `27119c05ac15184870034f862f5311b9deee09d8d93c5b841e47b1a12ce0b230` |
| `out/dispatch/pack_source.py` | `b1eb8d02b0ce0974650e308a168bd0fdbf23ac501990b8e724d6df4977e035ae` |
| `out/dispatch/import_paths.json` | `af60268e1b596374b9abf278ce1531e444df5d2a66a7371c7710ddc6797c4577` |

### External References

无外部检索。仅通过现有 `/tmp/afdm-shared-channel-env/bin/python` 的 `scipy.stats.beta.ppf` 做固定n/x的确定性数值核验及整数计数核验，不运行科学P/A。

### Related Specs

沿用主会话交接的已加载任务与服务器约束；当前唯一写入所有权为本文件。未重载Trellis生命周期，未修改代码、CSV、旧结果，未执行Git/SSH。主会话提供D/A完成信息：μ从.3253236536113068降至.18375555862063078，checkpoint199；本协议准入不把这些几何结果当性能证据。

## Caveats / Not Found

- 当前SOURCE ADMISSION PASS只确认冻结实现可运行，不确认科学性能结果；本轮科学P/A尚未纳入此准入审查。
- “优化带来的性能改善”必须有同批optimized-vs-oldrandom支持；优化码相对二次码通过主门与此是不同结论。
- 保持有限48点gain-grid profile含义；不扩张为连续ML、Bayes MAP、BER、多径或continuous-CFO结论。
