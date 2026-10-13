# OPS-01 最小可恢复队列设计（2026-09-06，只读研究）

当前结论：已有 launcher 的独立输出、进程组、超时和CPU亲和性可复用，但尚不支持新 OPS 完整恢复。`decision_harvest` 已有固定身份及逐帧产物，重启却会重新计算首帧后因文件已存在退出；接收评估 runner 目前拒绝已有目录。这是明确恢复缺口，不能将“不会覆盖”当成“能补缺”。本研究未改代码、未发车；路径/符号以本次工作树读取为准，主会话后续编辑可使行号变化。

## 当前可复用的单一实现

| 模块/符号 | 已提供的契约 | 缺口 |
|---|---|---|
| `decision_harvest.validate_prior_manifest`（52） | prior schema、root20260905、Dcal2/rep40/stream9、从0连续frame index、派生seed和去重 | 专用完整prior清单，不能拿任意缺失帧子集冒充完整新manifest；保留其身份规则 |
| `decision_harvest.prior_metadata_hash`（74） | sort_keys、禁止NaN的规范JSON内容hash | 当前逐帧.pt没有配置/源码/manifest hash绑定；hash只在最终cache形成 |
| `decision_harvest.validate_complete_prior`（78） | 全cache的身份、配置、完整真值合并、候选/标签/gain一致性 | 不应复制为另一个恢复校验器；宜抽出被它和恢复共同调用的单帧检查，或以相同核心校验复用 |
| `decision_harvest.harvest_frame`（237） | 给定seed生产单帧，完整truth/input hashes、固定nomination | 核心计算可原样复用，不在队列再写harvest |
| `decision_harvest.run_harvest`（367） | 固定manifest不替换失败帧，异常failure.json，成功保存frame-NNNN.pt，最终全量校验 | 所有缓冲初始为空，从0开始；已存在文件检查发生计算后；torch.save直写非原子；failure.json会覆盖旧失败；缺resume/status |
| `budgeted_support_eval.file_hash`（60）、`make_frame`（82）、`run_frame`（99） | 校验来源；固定split/rep/frame输入；成套arms、输入hash、错误、输出hash | CLI只支持连续区间；frames.jsonl行缺规范configuration hash绑定；配置存在status但不是完整不可变run契约 |
| `budgeted_support_eval.main`（289） | PID、config、设备/亲和性/线程、checkpoint/prior/source/LDPC hash，逐帧flush、异常记录 | out.mkdir(exist_ok=False)、frames.open('x')无resume；status直写；缺完整行校验/已完成集合重建/退出码与最终原子收尾 |
| `budgeted_support_diagnostics.dev_rng`（22）、`array_hash`（13） | 五元SeedSequence及数组dtype/shape/bytes hash | 保持原Ddev/Dcal字节；不以另一个RNG改恢复身份；尚不支持Dtest |
| 旧S2/S4 `launch-*.py` | Popen参数列表、taskset、start_new_session、独立日志/批次、deadline/timeout、仅kill自身进程组 | 无配置锁/PID创建时间、防双发、逐帧补缺、持久launcher验证、共享显存门及预算门；旧硬编码slots不符合新起步2槽 |

旧launcher具体位置见同目录 `mission-budget-evidence-20260906.md`。主实现应集中一个通用队列层处理运行生命周期，runner只负责自身帧恢复；不要再复制三套主循环。

## 最小数据与身份约定

1. 每批次先写不可变 `run-manifest.json`：schema、batch_id、stage、root/split/replicate/frame_index/SNR/arm集合、源码文件hash集合、checkpoint/prior/feedback/LDPC hash、系统/容量/dtype/算法参数、固定资源约束、绝对deadline、费用审批依据hash。保留原 `GOV-03-prior-manifest.json` 文件及语义hash，队列manifest引用它，不复制另一套prior种子真相。
2. `configuration_sha256` 仅覆盖会影响结果的语义配置、代码和依赖产物hash。out路径、PID、attempt编号、恢复时刻、运行计时不进入结果身份；资源约束另有execution配置hash并冻结。格式化变化可以改变文件hash而不改变语义hash，两者明确保存。
3. 一条接收帧的完成单元应是同一identity下所有冻结arms都完成，不能根据部分成功臂拼装不同输入的配对结果。必须校验arms集合、每臂finite/完整错误字段、input hashes、shell/cap、seed/identity与manifest一致。算法返回有效失败结果要保留为失败分母，不能只收成功帧。
4. mutable `status.json` 只是状态快照；真实完成集合由已校验持久帧产物派生。所有状态通过临时文件+fsync+同目录replace原子提交，不能吞解析失败后当空状态。失败尝试另记append-only attempts，避免覆盖历史失败费用。

## prior恢复：最小改 `run_harvest`，不造第二实现

新增显式resume入口，仍加载**完整原manifest**并要求配置/源码hash相同。启动即读写一次原子run契约；resume前先校验目录内声明及每个已有frame产物，再决定需要算什么。逐帧完成文件用临时文件保存、flush/fsync、原子发布；只有完整且hash匹配的final帧文件代表完成，临时残片归属原attempt并保留。

主循环按原manifest顺序：已有完整帧→验证→直接复用r；缺失帧→调用现harvest_frame→同一检查→持久化。两者进入**同一段现有buf累加逻辑**，最终仍调用validate_complete_prior并原子写唯一cache。不要仅跳过已有帧而忘记把其特征加回buf；不要对缺失子集调用validate_prior_manifest（它有连续从0身份约束）；不要将无法解析final.pt默默视作“没跑”。

若final文件损坏，明确记录 `artifact_corrupt` 并停止，保留证据；只有经既定恢复规则判定为未提交临时残片的帧可重新执行。同seed重试是原帧失败尝试的恢复，不是换样本，attempt和成本都保留。完全重复启动在完整cache校验通过后返回已有完成状态，不能重新采样。由于当前frame.pt没有来源hash绑定，新协议只能对新run直接恢复；旧partial需要完整来源可追溯后才可导入，不能凭文件名盲信。

## receiver恢复：保留现runner和帧函数

最小路径是在现main加显式resume及完整清单绑定，不复制make_frame/run_frame。连续manifest可继续使用start-frame+frames表达，恢复扫描已完成frame_index并只跑缺失身份；未来非连续分片可传frame清单，但原始完整身份不重新编号。

读取frames.jsonl必须验证完整JSON行和身份唯一性。尾部非换行或部分JSON是未提交帧，保存到原attempt残片文件后按协议修复；中间损坏、重复身份或配置不匹配必须显式报错，不能跳过。持久性更简单的方案是每帧原子JSON再最终按manifest生成frames.jsonl，但要保证现分析器仍读同一个最终格式，不增加两个权威完成账本。若继续JSONL，采用flush+fsync后才更新completed_frames，且恢复永远以完整行重建。

已经完成全部帧但status未置complete的崩溃点：重新全校验并补最终状态即可，不跑任何帧。已完成有效帧不因status计数落后而重复运行。

## launcher去重、截止与资源

- 同一run目录在发车前取得排他 `flock`，父launcher持有直到队列结束；锁句柄不可泄漏让无关子进程长期持有。启动前核对PID、host、boot_id和Linux `/proc/<pid>/stat` starttime、cmdline及run目录，防PID复用。已存在匹配活进程只报告/附着观察；PID不匹配不能杀掉它。完整产物直接返回completed；无活进程且有partial才进入resume。
- 外层launcher本身须持久化：stdin=DEVNULL、stdout/stderr独立日志、独立session，从远端启动后立即验证PID及已写run状态。SSH断连后只查询进程和产物；不能再发送同一启动命令赌幂等。SSH固定30/3保活及ControlMaster不承担任务持久性。
- 每个attempt记开始/结束、设备、CPU核集合/线程数、退出码、取消/超时原因、累计完成集合hash。绝对deadline在恢复时不重置；队列同时检查阶段保守余额、首包额度、预计剩余费用×至少1.2。到deadline先停止新帧/新作业，终止本任务进程组，超时部分保持失败证据。
- CPU先2作业×4线程，OMP/OPENBLAS/MKL线程约束与taskset一致；核集合从现有任务占用排除后分配，不盲用旧36—55。CPU runner显式CUDA_VISIBLE_DEVICES=''，保持现CPU保护逻辑。
- GPU开发先2槽；总显存预算22GiB包括其他进程和保留内存。启动前实测可用/总占用与每槽保守峰值估算；运行时轮询总显存和本任务进程，并记录峰值。采样峰值只是观测下界，不声称抓到瞬时绝对峰值；因此以预留余量和每任务PyTorch峰值共同约束，不等越界才当作成功。
- 未经新实测吞吐/显存验证不升3—4槽。外部作业突然进入使资源不满足时停止本任务新增调度、记录资源干扰；不得清理他人进程。正式G2模式要求GPU及约定CPU资源独占，不能沿用开发并发耗时作为G2证据。

## 最小有意义验证

无需远程实验即可先做：第2帧人为失败后恢复，只调用第2帧且完成结果与不中断运行逐帧一致；配置/hash变更拒绝恢复；重复PID/同run双启动只跑一次；status落后但帧完整不重算；尾部写一半的崩溃恢复保留残片；deadline恢复不延长；CPU核重叠/错误CUDA环境拒绝；模拟资源门超限不发车。prior另验证缓冲重建后full cache一致，不换seed、不删失败attempt。

上述本地验证只能验工程契约；OPS真实验收仍需预算允许后的小样本持久launcher与SSH断开/重连检查、真实PID/显存/亲和性和退出产物证据。它不要求新增S1正式计时包，但必须扣所属阶段余额。当前文档仅设计，不声称OPS通过。
