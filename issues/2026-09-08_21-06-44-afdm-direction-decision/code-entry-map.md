# 现有入口定位（Luna low，只读）

本表是源码导航，不是 Phase 0 结果或独立实现验收。未调用接收机，未读取封存 D_test。未来先核对 B0/A2 的真实版本，不能把 standalone 或旧 E1 自动视为当前 B0。

| 入口 | 定位与接线风险 |
|---|---|
| `standalone/joint_omp_bpmp_afdm.py:136` | 整数(l,k,g)构建DAFT域H；K_factor与字典K约定需一致。 |
| `standalone/joint_omp_bpmp_afdm.py:335` | 分数Doppler展开、泄漏、归一化与prune；P_phys与有效tap数不同。 |
| `standalone/joint_omp_bpmp_afdm.py:375` | build_channel生成H_eff/H_time；物理路径元数据是否丢失须P0-02核查。 |
| `standalone/joint_omp_bpmp_afdm.py:446` | 导频字典与(l,k)列元数据；冻结列序和归一化。 |
| `standalone/joint_omp_bpmp_afdm.py:471` | OMP/LS/停止；后续496处重建H，518处DA-LS列。 |
| `standalone/joint_omp_bpmp_afdm.py:639` | 联合外环；736取消、746更新sigma、758停止。standalone返回不足以直接满足新快照协议。 |
| `afdm_sp_joint_unrolled/afdm_env.py:760` | adaptive/fixed噪声方差；值和提交时刻一起核验。 |
| `afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py:232` | LDPC构造；331配置指纹；467/515解调及译码。 |
| `afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py:422` | 编码数据与y生成；429处burn旧data draw会影响共享RNG，拆新流时检查配对。 |
| `afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py:505` | Gate臂额外final BP；不得漏计或默认与classical成本相同。 |
| `afdm_sp_joint_unrolled/budgeted_support_eval.py:240` | 现有B0/反馈执行入口；323 terminal_observer可复用；326最终BP/LDPC。 |
| `afdm_sp_joint_unrolled/budgeted_support_eval.py:342` | 错误/译码/耗时/支撑/图/输出hash；不同arm准备开销不对称。 |
| `afdm_sp_joint_unrolled/budgeted_support_eval.py:382` | 当前feedback声明LDPC terminal；不是decoder-in-loop。 |
| `afdm_sp_joint_unrolled/v3_protocol.py:12` | v3常量与manifest；新campaign须新数据流协议，不能借旧holdout注册或额度。 |

Luna未做完整源码审计；上述入口作为CSV refs，正式AUDIT-00仍需核验真实生成→估计→取消→检测链。每次接收机更新同时检查H_cancel/H_data/H_cov与所有依赖缓存。
