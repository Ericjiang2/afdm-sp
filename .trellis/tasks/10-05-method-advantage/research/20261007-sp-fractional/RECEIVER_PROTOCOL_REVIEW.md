# RECEIVER_PROTOCOL 独立静态审查

2026-10-07。范围：全文审查 `SELECT.md`、`RECEIVER_PROTOCOL.md`，并定点核对
frozen `budgeted_support_eval.py:114–132` 的 `make_frame`。本报告不包含源码准入、
数值复算或接收机运行；不授予运行 GO，也不认定性能–成本目标已完成。

## 发现与修订核验

- **SNR 口径**：协议已补齐总符号能量 1、`sigma2=10**(-SNR_dB/10)`、
  proper 复噪声及禁止按 G1 实测能量缩放，与 frozen 生成入口一致。
  审查中曾建议额外乘 0.5，该建议错误且已撤回，不能用于实现。
- **比较完整性**：已明确 24/24 接收输出、失败不可删除或计零错误，三个 arm
  分别以自身 8 次完整调用取中位耗时；每次获取、预计算、失败 proposal、积分、
  输出保存均计费，另给含 setup 总账。
- **点坐标目标**：已将含混的“真实 likelihood”修订为冻结其它 q 因子的
  expected-log-likelihood 坐标势，不能解释为未知 QPSK 的精确边缘 likelihood。
- **误比特判决**：已统一 all-I then all-Q 映射顺序、bit-marginal LLR<0 判 1、
  LLR=0 判 0，避免 symbol-MAP 与 bit-MAP 混用改变 raw-bit-error 比较。

以上协议修订由主线程完成，本审查核对其最终文字；未修改实现代码。

## 科学与执行边界

- 生成模型明确为 N1024、SP 0.5/0.5、root7 ZC、完整 G1 CPP/连续多径，并复用
  G0 归一化 gain；工作 gain/Doppler/QPSK 先验与生成分布分开声明。F1 结果仅用于
  槽位获取与初始化，后续更新不重复乘入初始化分布。
- 三 arm 各自从公共观测获取槽位，continuous 与 point 的主要差异为 Doppler
  密度期望与连续点优化。Dirac 不被冒称为连续先验下有限 KL 的精确 VB；积分
  层间一致性仅作分辨率诊断，尾部删质量及矩扰动有显式界，不是严格积分误差证书。
- truth 仅在输出封口后评分；**源码准入仍须核对公共配置白名单**，确保真实路径
  数值、支持、gain 和生成 seed 不进入接收接口、初始化或求积自适应。
- 6/8 dB 配对共享外生随机量，因此只有 4 个独立 blocks，不能宣称 8 个独立样本。
  raw-bit-error 与耗时门槛可作为冻结的开发筛选，不能证明统计显著性；零 point
  错误、失败、分 SNR 恶化均有明确处理。后续 coded、强完整 F1/native 对照仍必需。

**结论：当前协议层未发现剩余阻塞，可继续实现。** OFDM/VALSE antecedent 与
AFDM+SP 的适配创新并不冲突，但不能据此提高首创声明。实际执行仍须冻结源码、
资产与 stage 合同并完成独立准入；本报告不要求原型事先证明收益。

## 核验记录

- 静态文本与 frozen SNR 入口核对：通过；未运行仿真、解码、SSH 或数值测试。
- Lint / TypeCheck：本次仅新增 Markdown，无适用代码检查；`git diff --check` 通过。
- 审查绑定 SHA256：
  - `SELECT.md`：`8167220dd7ba45283b98b78caba246e6b9515d2502a8aec412a171de2385b1d8`
  - `RECEIVER_PROTOCOL.md`：`2274fcbd5c7035336fcad927277471328523504b8b05dcc7a07b323191ef110a`
