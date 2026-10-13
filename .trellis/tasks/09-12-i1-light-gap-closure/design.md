# Design

Trellis仅管理生命周期；Mission plan为本批设计/执行合同入口，CSV为唯一逐行状态。沿用父研究边界，不另建研究生命周期。

- 已完成pilot源码快照为隔离底包；只添加本批明确文件。旧开发NPZ和记录均只读且核SHA256，不能同步整个dirty科学工作树。
- 新输出根为 `afdm_sp_joint_unrolled/outputs_i1_light_gap_20260912/`，缓存也在新根；旧预算不复用。
- 首个模块仅用旧终端LLR调用现有LDPC译码器，新增D调用单独记账，实际F/T均为0。CPU单线程，不使用GPU。
- 后续支撑/推断/完整接收诊断分别追加冻结合同。物理N=1024、rho=0.5、码结构与观测功率保持一致。GPU环境不可用时可以显式登记CPU实现并先做基准回放；不能默默切换设备。
- 误差分解先用代数与小矩阵对照验证，再在实际开发块比较；输入、源码、输出、外生配对、失败预约分别核验。
- 不预先承诺哪个候选晋级。每个候选须有便宜经典控制；旧64块上的扫描只作开发诊断，新鲜块与正式确认分开。
- 每个单项预计超过30分钟时先拆分或放入重型登记；这是保守执行选择，不是用户给的全批30分钟预算。外部timeout约束每个实际阶段。
- 服务器只在 `/data/guoyikun/` 写文件；CPU留至少16核余量。GPU新运行需实际预检、单worker、25%显存上限。不改驱动，不安装系统软件。

## Continuation override

The v2 Mission plan governs new tests. CPU work starts with two single-thread workers, up to eight after measured resource checks. Continuous Doppler estimation is excluded; discrete support diagnostics remain in scope. The user explicitly authorized CSV amendment followed by execution without another approval.

Latest user override: implementation, validation and final review stay in the main session. Do not spawn agents or independent reviewer sessions. Label self-review honestly. CPU first; GPU-only work deferred.
