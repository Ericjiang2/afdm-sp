# Claude → Codex 交接（2026-10-18）

用户决定（2026-10-18 选 A）：E-3c 交由 Codex 主会话（01a14ae6）继续，按 `continuation-contract.md` 执行。

## 所有权

- Codex 负责本任务的全部文件：prd/design/implement、`experiments/tf_e3c_shrink_20261018/`、`experiments/tf_covariance_audit_20261018/`。协议冻结、提交和远端启动也由 Codex 做。
- Claude 不再修改上述文件，只在结果出来后审查。

## 遗留文件

- `experiments/tf_e3c_shrink_20261018/` 下的 `e3c_lib.py`、`e3c_arms.py`、`e3c_budget.py`、`e3c_driver.py`、`test_e3c.py` 是 Claude 的执行代理被额度限制中断前写的，未经审查，也未提交。Codex 可以沿用，也可以丢弃。
- 那个执行代理已终止，不会再写入。

## Claude 接受的审查结论（逐条核对后成立）

1. E-3b 把"Doppler 移动"和"增益估计器从 SBL 后验换成 `_system` 的 ridge 最小二乘"混在了一起，缺少"几何固定、只重估增益"的对照。res-20261017-04 的"插值解释被否定"说法过强。
2. bootstrap 分簇应使用随机数域 / 帧（跨场景、ρ、SNR 共享输入），E-1/E-2/E-3/E-3b 的 CI 偏窄。点估计不受影响。
3. 真实误差剖面 v_o = |x − μ|² 不是后验协方差；Sh/Or 只能作描述性读数，不能用来做因果认证。
4. 把一条径拆成 m 个重合原子时，标量 Γ 的最小罚项是 s|h|²/m，完整 Γ 是 s|h|²。所以在"和方向"上，标量 Γ 的正则反而更弱；"更强 ridge"这种解释不完整。

## Claude 待办（等 Codex 的审计结果出来后再做，避免重复劳动）

- 按 Codex 的分簇复算结果，给 res-20261017-01/-02/-03 加显式的更正注记（不静默改写）。
- 收窄 res-20261017-04（仍为 draft）的结论措辞。
- E-3c 结果卡的审查。
