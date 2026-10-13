# 积分已可靠完成，当前连续后验未取得额外接收收益

2026-10-07，RECEIVER-ADAPT-01。工程回归与独立原始证据审计通过，预登记性能–成本筛选失败。
保留经典连续频率推断和自适应求积的 AFDM 适配实现；不宣称首创、完整性能优势或 Trans 目标达成。

## 同一观测下的完整接收比较

N1024、真实连续多径 G1/CPP、SP pilot/data=.5/.5、未编码 QPSK。
复用原4个独立blocks在6/8dB的8份观测，0新观测、0新独立blocks、0decoder。
三arm分别执行自己的F1获取，共24/24完整输出；全部raw封口后才读取truth数组评分。
原固定求积的8次失败仍保留，本轮不能把旧失败改写为通过。

| 接收方法 | 错误/16384 bits | 6dB错误 | 8dB错误 | 中位完整接收时间 |
|---|---:|---:|---:|---:|
| F1 + scalar joint | 1755 | 1043 | 712 | 0.593222 s |
| 同更新的point消融 | 1684 | 1045 | 639 | 1.643653 s |
| 连续后验 + adaptive GK | 1684 | 1046 | 638 | 7.571292 s |

continuous相对point改变14个硬判，纠正7个、引入7个，净变化0；并不是输出完全相同。
全部16384个LLR的数值均不同，但绝大多数未跨越判决边界。
continuous中位完整耗时为scalar的12.763倍、point的4.606倍。
point相对scalar总错误减少约4.05%，但6dB略差且耗时2.771倍，只保留为有限开发观察。

原筛选门槛要求continuous错误≤point的90%、不多于scalar、中位完整时间≤scalar1.25倍。
完整性门通过，额外误码改善和完整时间门均未通过。原门槛未放宽。
这4个blocks已经用于开发，不能按比特独立做确认性置信推断；coded、强基线和held-out均未完成。

## 工程及数值事实

共享GK核心逐值复现原8个保存势：输出phi/logZ差为0，分裂、面板和计数相同。
13个原组件fixtures、21项保存矩检查/9个数据步、2个明确mocked的计数边界检查通过。
mock只验证控制流，不算真实密度求值或有效接收样本。

完整开发中1280次连续更新全部完成，累计628950次密度求值、41930次中心导数；
单因子300–840个密度点，均低于冻结1020点上限。局部预算、sweep与总账一致。
这解决了本轮数值执行问题，但嵌入差仍是误差估计，不是全区间严格误差证书。

全部data-step equation (8)、独立objective、回溯、full gain covariance、20 sweeps和
每sweep3数据步保持。失败/拒绝证据不删除。没有引入Taylor代理、压缩或缓存优化。

## 完整资源和可复核来源

| 阶段 | stage wall / CPU | process wall / CPU | 最大RSS | 原件数 / 字节 |
|---|---|---|---:|---:|
| engineering | 11.226110 / 7.431526 s | 14.23 / 10.44 s | 460341248 | 761 / 34092563 |
| development | 89.043468 / 88.101430 s | 91.87 / 90.94 s | 606064640 | 185 / 105183757 |

完整接收时间包含各自F1、加载、初始化、全部推断/检查、raw保存与必要封口工作。
阶段另计population原字节复制、统一封口与评分；不是只测backend。
单CPU、CUDA隐藏，两个阶段均正常退出，未自动重试。大规模重计算均在SSH完成。

源码 `7757cd504c2a9539efb1b20e49a87f8a4a74120a`；准入 `2debb5cb`；
snapshot `df5fd3e47e3425836b3bf347878e3be06a2ce4a2`；源码归档SHA256
`c67d9a83700b61285a8c01c2585e26495a4ed81d484703131a62c59102f95abe`。

- ENG远端：`/data/guoyikun/afdm_sp_receiver_20261007_adapt_eng01_7757cd50/artifact`。
- DEV远端：`/data/guoyikun/afdm_sp_receiver_20261007_adapt_dev01_7757cd50/artifact`。
- 本地raw：`.mission/20261007-sp-fractional-trans/evidence-receiver-adaptive-{engineering,development}/artifact`。
- ENG manifest SHA256：`7d86b64c43706149f94f2fdc5a296a6d31dc5911ed9501f2a03847325e2a27bf`。
- DEV manifest SHA256：`1778ea6196f0c37869d88245fa9f42685b0bd40517dfe6115d4847e1016fd94c`。
- ENG archive SHA256：`22b3dbfaa6b7c7c2de9e64318b9c3db65264211c77d6084f497341bcbe68a591`，
  MD5 `9d277b7bd23671f45d054fe64eaebf2d`。
- DEV archive SHA256：`6bcd023869b722dad8eb471ce43ecd59772607c36fa50ed288eb9edf88250a1a`，
  MD5 `2efe13ae3603e74b28e705b2450786e0`。

独立审计见任务研究目录 `ADAPTIVE_RECEIVER_RAW_REVIEW.md`：全部文件SHA/MD5/size、
source快照、24输出封口、49152次LLR重判、局部计费和进程资源均核对通过。
本目录的scores、launcher、resource与manifest是原件副本，NPZ不入Git。

## 下一步的科学判断

当前证据不足以支持继续仅优化积分器来追求误码收益。精确矩/源统计复用仍可作为工程候选保留，
但它不会改变本算法已保存的判决。下一步先核查gain–Doppler独立近似对相位参考时刻的依赖，
把模型/变分族问题与积分误差分开；该假设尚未被当前失败证实。
