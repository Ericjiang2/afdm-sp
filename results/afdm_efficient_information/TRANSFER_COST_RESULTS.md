# 迁移、表示与完整成本结果

本轮使用预先指定的feature_control_v1/model_1_phase.npz及其efficient_beta，未按测试结果换模型。N=4/16/64各使用512条独立名义null校准观测，以及8情形×2假设×128条测试观测，共7,680条。重复使用同一测试分数比较两种阈值不产生新的独立组。

两种校准分别为原N4冻结阈值及每N独立名义校准；后者仍只校准nominal actual-uniform law，不保证pilot、偏置/相关输入、噪声或先验失配下统一控制虚警。实测超出.05的条件完整保留。没有对24个情形或48表行做多重比较校正。

四锚点推断在N>4丢弃其他坐标，只有经验迁移证据。完整O(N)相位代表元与NxN外积的等价另行验证，不能据此说四锚点或4维输出无损。0新生产receiver/decoder/确认流。

## 全部检测条件

每项false alarm/power分母均为128个独立帧，区间为Wilson95%；不同方法阈值行共享分数。

| N | 情形 | 阈值来源 | 阈值 | FA计数/128 (95%区间) | 检出计数/128 (95%区间) |
|---|---|---|---:|---|---|
| 4 | actual_uniform | frozen_N4_threshold | 1.618558 | 7/128 [0.02674, 0.10858] | 15/128 [0.07232, 0.18437] |
| 4 | actual_uniform | independent_nominal_N_calibration | 1.618558 | 7/128 [0.02674, 0.10858] | 15/128 [0.07232, 0.18437] |
| 4 | actual_pilot | frozen_N4_threshold | 1.618558 | 7/128 [0.02674, 0.10858] | 6/128 [0.02166, 0.09850] |
| 4 | actual_pilot | independent_nominal_N_calibration | 1.618558 | 7/128 [0.02674, 0.10858] | 6/128 [0.02166, 0.09850] |
| 4 | actual_biased | frozen_N4_threshold | 1.618558 | 9/128 [0.03743, 0.12823] | 11/128 [0.04866, 0.14734] |
| 4 | actual_biased | independent_nominal_N_calibration | 1.618558 | 9/128 [0.03743, 0.12823] | 11/128 [0.04866, 0.14734] |
| 4 | actual_repetition | frozen_N4_threshold | 1.618558 | 2/128 [0.00430, 0.05518] | 15/128 [0.07232, 0.18437] |
| 4 | actual_repetition | independent_nominal_N_calibration | 1.618558 | 2/128 [0.00430, 0.05518] | 15/128 [0.07232, 0.18437] |
| 4 | conditional_equal_pdp | frozen_N4_threshold | 1.618558 | 5/128 [0.01680, 0.08819] | 13/128 [0.06032, 0.16602] |
| 4 | conditional_equal_pdp | independent_nominal_N_calibration | 1.618558 | 5/128 [0.01680, 0.08819] | 13/128 [0.06032, 0.16602] |
| 4 | actual_noise_mismatch | frozen_N4_threshold | 1.618558 | 19/128 [0.09713, 0.22023] | 17/128 [0.08460, 0.20242] |
| 4 | actual_noise_mismatch | independent_nominal_N_calibration | 1.618558 | 19/128 [0.09713, 0.22023] | 17/128 [0.08460, 0.20242] |
| 4 | actual_g1 | frozen_N4_threshold | 1.618558 | 9/128 [0.03743, 0.12823] | 17/128 [0.08460, 0.20242] |
| 4 | actual_g1 | independent_nominal_N_calibration | 1.618558 | 9/128 [0.03743, 0.12823] | 17/128 [0.08460, 0.20242] |
| 4 | gaussian_control | frozen_N4_threshold | 1.618558 | 9/128 [0.03743, 0.12823] | 10/128 [0.04299, 0.13785] |
| 4 | gaussian_control | independent_nominal_N_calibration | 1.618558 | 9/128 [0.03743, 0.12823] | 10/128 [0.04299, 0.13785] |
| 16 | actual_uniform | frozen_N4_threshold | 1.618558 | 4/128 [0.01222, 0.07760] | 8/128 [0.03201, 0.11849] |
| 16 | actual_uniform | independent_nominal_N_calibration | 1.277766 | 5/128 [0.01680, 0.08819] | 10/128 [0.04299, 0.13785] |
| 16 | actual_pilot | frozen_N4_threshold | 1.618558 | 2/128 [0.00430, 0.05518] | 5/128 [0.01680, 0.08819] |
| 16 | actual_pilot | independent_nominal_N_calibration | 1.277766 | 4/128 [0.01222, 0.07760] | 8/128 [0.03201, 0.11849] |
| 16 | actual_biased | frozen_N4_threshold | 1.618558 | 7/128 [0.02674, 0.10858] | 15/128 [0.07232, 0.18437] |
| 16 | actual_biased | independent_nominal_N_calibration | 1.277766 | 9/128 [0.03743, 0.12823] | 18/128 [0.09084, 0.21135] |
| 16 | actual_repetition | frozen_N4_threshold | 1.618558 | 3/128 [0.00800, 0.06664] | 3/128 [0.00800, 0.06664] |
| 16 | actual_repetition | independent_nominal_N_calibration | 1.277766 | 4/128 [0.01222, 0.07760] | 5/128 [0.01680, 0.08819] |
| 16 | conditional_equal_pdp | frozen_N4_threshold | 1.618558 | 9/128 [0.03743, 0.12823] | 9/128 [0.03743, 0.12823] |
| 16 | conditional_equal_pdp | independent_nominal_N_calibration | 1.277766 | 10/128 [0.04299, 0.13785] | 10/128 [0.04299, 0.13785] |
| 16 | actual_noise_mismatch | frozen_N4_threshold | 1.618558 | 12/128 [0.05444, 0.15673] | 13/128 [0.06032, 0.16602] |
| 16 | actual_noise_mismatch | independent_nominal_N_calibration | 1.277766 | 15/128 [0.07232, 0.18437] | 18/128 [0.09084, 0.21135] |
| 16 | actual_g1 | frozen_N4_threshold | 1.618558 | 2/128 [0.00430, 0.05518] | 12/128 [0.05444, 0.15673] |
| 16 | actual_g1 | independent_nominal_N_calibration | 1.277766 | 6/128 [0.02166, 0.09850] | 15/128 [0.07232, 0.18437] |
| 16 | gaussian_control | frozen_N4_threshold | 1.618558 | 6/128 [0.02166, 0.09850] | 7/128 [0.02674, 0.10858] |
| 16 | gaussian_control | independent_nominal_N_calibration | 1.277766 | 7/128 [0.02674, 0.10858] | 12/128 [0.05444, 0.15673] |
| 64 | actual_uniform | frozen_N4_threshold | 1.618558 | 2/128 [0.00430, 0.05518] | 7/128 [0.02674, 0.10858] |
| 64 | actual_uniform | independent_nominal_N_calibration | 1.678344 | 2/128 [0.00430, 0.05518] | 7/128 [0.02674, 0.10858] |
| 64 | actual_pilot | frozen_N4_threshold | 1.618558 | 2/128 [0.00430, 0.05518] | 4/128 [0.01222, 0.07760] |
| 64 | actual_pilot | independent_nominal_N_calibration | 1.678344 | 2/128 [0.00430, 0.05518] | 4/128 [0.01222, 0.07760] |
| 64 | actual_biased | frozen_N4_threshold | 1.618558 | 3/128 [0.00800, 0.06664] | 29/128 [0.16263, 0.30643] |
| 64 | actual_biased | independent_nominal_N_calibration | 1.678344 | 3/128 [0.00800, 0.06664] | 29/128 [0.16263, 0.30643] |
| 64 | actual_repetition | frozen_N4_threshold | 1.618558 | 1/128 [0.00138, 0.04293] | 5/128 [0.01680, 0.08819] |
| 64 | actual_repetition | independent_nominal_N_calibration | 1.678344 | 1/128 [0.00138, 0.04293] | 5/128 [0.01680, 0.08819] |
| 64 | conditional_equal_pdp | frozen_N4_threshold | 1.618558 | 10/128 [0.04299, 0.13785] | 12/128 [0.05444, 0.15673] |
| 64 | conditional_equal_pdp | independent_nominal_N_calibration | 1.678344 | 10/128 [0.04299, 0.13785] | 11/128 [0.04866, 0.14734] |
| 64 | actual_noise_mismatch | frozen_N4_threshold | 1.618558 | 12/128 [0.05444, 0.15673] | 15/128 [0.07232, 0.18437] |
| 64 | actual_noise_mismatch | independent_nominal_N_calibration | 1.678344 | 11/128 [0.04866, 0.14734] | 15/128 [0.07232, 0.18437] |
| 64 | actual_g1 | frozen_N4_threshold | 1.618558 | 5/128 [0.01680, 0.08819] | 11/128 [0.04866, 0.14734] |
| 64 | actual_g1 | independent_nominal_N_calibration | 1.678344 | 5/128 [0.01680, 0.08819] | 11/128 [0.04866, 0.14734] |
| 64 | gaussian_control | frozen_N4_threshold | 1.618558 | 8/128 [0.03201, 0.11849] | 7/128 [0.02674, 0.10858] |
| 64 | gaussian_control | independent_nominal_N_calibration | 1.678344 | 7/128 [0.02674, 0.10858] | 7/128 [0.02674, 0.10858] |

## 合法输入与小N参考

pilot固定首个符号；biased使用合法非均匀QPSK概率；repetition按成对符号相等的受限码本。对应输入中心化covariance/pseudocovariance及rank全部保存，不能把它们当成同一盲输入族。下表完整保留N4密度资格；有限节点加密只作数值参考。

| 情形 | 合法码字数 | 中心化输入协方差rank | 最大logpdf加密误差 | 加密合格 | 规范表示logpdf误差 |
|---|---:|---:|---:|---|---:|
| actual_uniform | 256 | 4 | 0.0007852085 | True | 5.329071e-15 |
| actual_pilot | 64 | 3 | 0.001514332 | True | 7.105427e-15 |
| actual_biased | 256 | 4 | 0.000779095 | True | 3.552714e-15 |
| actual_repetition | 16 | 2 | 0.002085818 | True | 5.329071e-15 |
| conditional_equal_pdp | 256 | 4 | 0.001088323 | True | 8.881784e-15 |
| actual_noise_mismatch | 256 | 4 | 0.000579076 | True | 3.552714e-15 |
| actual_g1 | 256 | 4 | 0.0007003131 | True | 7.105427e-15 |
| gaussian_control | 256 | 4 | 不适用（解析增益消元） | 不适用 | 1.776357e-15 |

72个几何诊断含平台/边缘/谱退化与G0/G1，dense Gram误差与矩分类见geometry.json；identity失败为0。全部24组完整相位表示的dense重构/全局旋转检查无失败。

## 同对象表示成本

下面的wall每帧包含相同逆DAFT到完整表示的路径；是一次本机计时的描述量，不能当普遍加速保证。字节数包含规范锚点元数据，故不恰好等于N比例。N4规范代表元比小dense外积慢，N16/64的本次构造较快。它们编码同一相位轨道；学习score和完整likelihood并不是同精度对象。

| N | 情形 | 规范 µs/帧 | 外积 µs/帧 | 规范字节/256帧 | 外积字节/256帧 |
|---|---|---:|---:|---:|---:|
| 4 | actual_uniform | 0.157063 | 0.126789 | 18432 | 65536 |
| 4 | actual_pilot | 0.151691 | 0.11491 | 18432 | 65536 |
| 4 | actual_biased | 0.152668 | 0.115074 | 18432 | 65536 |
| 4 | actual_repetition | 0.142578 | 0.101074 | 18432 | 65536 |
| 4 | conditional_equal_pdp | 0.142902 | 0.111004 | 18432 | 65536 |
| 4 | actual_noise_mismatch | 0.151367 | 0.108398 | 18432 | 65536 |
| 4 | actual_g1 | 0.151043 | 0.11198 | 18432 | 65536 |
| 4 | gaussian_control | 0.144531 | 0.110023 | 18432 | 65536 |
| 16 | actual_uniform | 0.220379 | 0.388672 | 67584 | 1048576 |
| 16 | actual_pilot | 0.227703 | 0.421711 | 67584 | 1048576 |
| 16 | actual_biased | 0.204914 | 0.416016 | 67584 | 1048576 |
| 16 | actual_repetition | 0.234539 | 0.399578 | 67584 | 1048576 |
| 16 | conditional_equal_pdp | 0.205078 | 0.410805 | 67584 | 1048576 |
| 16 | actual_noise_mismatch | 0.224937 | 0.425617 | 67584 | 1048576 |
| 16 | actual_g1 | 0.192383 | 0.381672 | 67584 | 1048576 |
| 16 | gaussian_control | 0.236328 | 0.42627 | 67584 | 1048576 |
| 64 | actual_uniform | 0.522137 | 4.34619 | 264192 | 16777216 |
| 64 | actual_pilot | 0.544109 | 4.24707 | 264192 | 16777216 |
| 64 | actual_biased | 0.534504 | 4.35466 | 264192 | 16777216 |
| 64 | actual_repetition | 0.537273 | 4.30111 | 264192 | 16777216 |
| 64 | conditional_equal_pdp | 0.531086 | 4.30095 | 264192 | 16777216 |
| 64 | actual_noise_mismatch | 0.535484 | 4.27637 | 264192 | 16777216 |
| 64 | actual_g1 | 0.540039 | 4.28271 | 264192 | 16777216 |
| 64 | gaussian_control | 0.526203 | 4.27067 | 264192 | 16777216 |

## 全部登记阶段费用

cost_v1按其启动前冻结的8个科学stage读取费用；下面另列cost_v1自身。独立AUDIT及其失败尝试由最终AUDIT结果另外统计，不回改此冻结reader。wall是attempt记录的阶段计时，不含启动解释器；peakRSS是整个进程累计峰值，不能各stage相加。内部block费用不再次加到全阶段wall。

| 阶段 | 预约观测 | 预约wall秒 | 实测wall秒 | 实测CPU秒 | peakRSS字节 |
|---|---:|---:|---:|---:|---:|
| feature_actual_v1 | 1280 | 300 | 34.177884 | 33.962199 | 1609433088 |
| feature_control_v1 | 10240 | 300 | 0.650326 | 0.558671 | 95698944 |
| inference_actual_v1 | 12288 | 1800 | 198.920287 | 198.692934 | 1154220032 |
| inference_control_v1 | 49152 | 900 | 7.210565 | 7.080101 | 382091264 |
| prior_geometry_v1 | 0 | 120 | 0.854115 | 0.699565 | 293273600 |
| prior_information_v1 | 1536 | 900 | 46.059234 | 45.864655 | 2556035072 |
| prior_refinement_v1 | 0 | 900 | 47.238239 | 46.928924 | 1691549696 |
| transfer_v2 | 7680 | 900 | 4.937763 | 4.793224 | 919961600 |
| cost_v1 | 0 | 60 | 0.359364 | 0.214815 | 293191680 |

8个科学stage合计82,176条新观测、预约6,120秒、实测wall 340.048412623秒、CPU 338.580273秒，全部完成。cost_v1保留361条实测block记录；未知/未仪表化操作不填0。

控制teacher/inference中，reported covariance factorization字段只数Cholesky矩阵，源码还对同批cov作solve(cov,I)。控制inference分别15,360个Cholesky与15,360个通用solve矩阵；后者通常还含LU分解。原whole-stage计时已包含这些操作。独立AUDIT会补派生计数并区分报告原字段，避免把一个计数误作总成本。实际积分、Gram eigvalsh/eigh、正权节点构建、响应均值、component-observation pairs、教师训练、独立校准和完整推断分别保存；未仪表化内部操作不作精确FLOP声明。

同精度学习推断优势未成立，因而摊销门槛不可给出。只有同质量条件成立且c_ref>c_new，才可计算ceil(T_train/(c_ref-c_new))；不能用不同质量kernel时间制造优势。

## 失败、完整性与证据

首次transfer_v1在登记前因PyTorch虚拟namespace的相对__file__被误作本地源码路径而拒绝，0新观测、0预约，无stage目录。独立最小回归先失败再通过，11个transfer资格测试通过，修复提交57711201后以transfer_v2运行。拒绝记录见Mission/TRANSFER_ADMISSION_REJECTION.json。无样本选择、无阈值放宽。

本报告仅转录和汇总保存数据，未新生成观测或求积节点。全部真实raw哈希由各attempt记录；独立AUDIT结果作为后续复核证据。

### 转录来源SHA-256

- `results/afdm_efficient_information/cost_v1/attempt.json`：`fffb27501e9d05971c4824d9d4b11758a8ae0147ba0eeac717953a472a5e5b8d`
- `results/afdm_efficient_information/cost_v1/results.json`：`331c8905b80279e6c4b7768e9cd39cb66558023eff458efb9c342dda1e62f57a`
- `results/afdm_efficient_information/transfer_v2/costs.json`：`499ab50ff8e80157cc3aa96d32b7e39f98096dde1e1f953738874a38d2baa36a`
- `results/afdm_efficient_information/transfer_v2/geometry.json`：`f4c052ce5acabdf7684e7088a9d6b166124226e783ac225ea02c67082afb3a5d`
- `results/afdm_efficient_information/transfer_v2/performance.json`：`2e052df82239fdd24a4805e266e01369689248f40564a80da224b8e189a03c92`
- `results/afdm_efficient_information/transfer_v2/references.json`：`ed8eb817c1c8d3af9f3225f7f2ce84b063015276213a86f3d6eb6fb16259b5bd`
- `results/afdm_efficient_information/transfer_v2/representation_costs.json`：`b1022669b40152aa77af3b1e74c6b56da3864f98577d701386201ad1d913c6df`
- `results/afdm_efficient_information/transfer_v2/representations.json`：`fb36fb28a03d75c7aabd73d41ad7576b4eedcf826d6c61f741f9ea7c78dcc1ba`
- `results/afdm_efficient_information/transfer_v2/results.json`：`618930d3462a746597c117103729fc50c0d211fc675d35357f9eca86485e4ffe`
