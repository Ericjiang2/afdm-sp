# E-3b：给 SBL 加连续 Doppler 细化，检验标量 Γ 的优势是否消失

## Goal

[res-20261017-03](../../../research-assets/res-20261017-03.md)（已接受）中，Luo 式 on-grid 数据辅助 SBL 的标量 Γ 版本（L-diag）比完整 Γ 版本（L-cov）FER 更低：.110 对 .149，ρ.3 时穿越点最多提前 2.3 dB。卡片给出的事后解释是：固定网格上，分数 Doppler 需要几个相邻的同时延原子来插值，标量模型奖励把增益摊开，这恰好起了有益的插值与收缩作用。而 CSTATE 做的是连续细化，同样的奖励在那里只会产生幻影。

E-3b 检验这个解释：给同一个 SBL 加上连续 Doppler 细化后，标量 Γ 的优势是否消失或反转。用户于 2026-10-17 指定，协议先冻结后跑，并要求用新的小代理执行。

## Requirements

- R1：细化机制复用 E-1 变体核 `geometry_reopen_variant._system(Y, xt, v, paths, c1, c2, ridge, gamma_mode)` 的目标函数（只读导入）。逐原子做连续 Doppler 搜索，再联合解增益，每个变体使用自己的数据模型（hard/genie 取 v = 0；diag/full 对应 gamma_mode）。SBL 部分逐位沿用 E-3（`tf_e3_sbl_20261017/sbl_rx.py`，只读导入或逐字复制并记录 md5）。
- R2：键取 E-3 主跑键的子集：U/G × ρ.3，6..11 dB，帧 4000..4199，共 2400 个键。on-grid 结果直接取 E-3 的行做配对，不重跑，但需用门核对确定性。
- R3：协议先冻结、提交，再跑；冻结源码一律不改；新代码放在 `experiments/tf_e3b_offgrid_20261017/`。
- R4：成本上限 30 core-h，同时最多 24 个进程。远程运行用 tmux 无人值守地串成一条链，执行代理不轮询、启动后立即返回。
- R5：行数据留在 deinlab；小文件回传并入 git；跑前、跑后各 commit 一次；结果只出 draft 卡。

## Acceptance Criteria

- [ ] 门全部通过（design §5），协议在跑前提交。
- [ ] 2400 个键四个变体全部跑完，0 失败；判定按冻结规则给出，并附 CI。
- [ ] draft 卡链接 res-20261017-03，明确标出事后解释是被支持还是被否定。

## Boundaries

- 不调 SBL 超参；细化超参冻结在 design 中。
- 不实现 Luo 的 Taylor off-grid 步：用连续一维搜索代替，在协议中声明为偏差。
- 结论只适用于本接收机、ρ.3、P1 信道。
