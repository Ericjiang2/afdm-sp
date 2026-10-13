# FB-04 旧固定壳温度×V复用资格

2026-09-06，只读核对。实际用 `/opt/anaconda3/bin/python` 解析本地192条开发frames及对应status/calibration；未运行receiver、未连接远端、未改代码或CSV，未读取validation观测或Dtest。本报告是复用资格研究，不替代FB-04真实小批smoke。

## 已有三格符合旧壳复用范围，缺VT1

权威文件为 `.trellis/tasks/09-06-minimal-repair-mechanism/research/runtime/capacity-dev-rep{0,1,2}/` 各自的 `frames.jsonl`、`status.json`、`calibration.json`。三个rep各64条，frame_index逐项等于0…63，split均D_dev、SNR8，status complete=true。192个channel_seed唯一、192个y hash唯一，全部active_cap40/nomination_cap8。

同一帧内三格共享输入记录，全部包含y/H/noise/info/coded/pilot六项hash。**192帧的三臂初始support日志及F2P rounds逐项完全相等**，支持温度/V只改初始修复之后的反馈路径。各臂finite均true。三份完整source_sha256字典相同，checkpoint/prior/LDPC/反馈记录hash也全部相同。

| 旧格 | CLI arm | 记录dals_mode/T | 三rep帧错数 | 三rep信息bit错误数 |
|---|---|---|---|---|
| meanT1 | baseline | mean / 1 | 39,47,38（124/192） | 4446,5415,4210 |
| meanT2 | temperature_mean | mean / 2 | 40,48,41（129/192） | 4624,5639,4703 |
| VT2 | covariance | covariance / 2 | 44,53,48（145/192） | 5663,6887,6009 |
| VT1 | covariance + 固定T1记录 | 应为covariance / 1 | 本地原192帧尚无该格 | 待补 |

上表仅核对已有数据，不预判VT1或因果结论。逐帧raw/info计数、decode标志及H/x hash已保存，不能用表中总数替代回放比较；原档没有每bit错误mask。

本地runtime中满足split dev、rep0/1/2、cap40且含covariance的status仅上述三份，全部用T2。这支持本地原192帧缺VT1；没有做远端全盘检查，发车前仍须排除新提交的同名/等价作业。

## 精确配置、来源和hash

- 系统N1024、v_mean2、P_phys8、tau10ms、fs_factor4、rho0.5、物理k_leak2；旧receiver `K_prop=8`，extension2，active cap40。不能把receiver名称cap40误当nomination40。
- SNR8；split1/rep0,1,2/frame0…63。每帧stream1 channel、stream2 bits、stream3 noise、stream4 arm顺序；详见GOV-03身份报告。原arm列表为baseline temperature_mean covariance，soft-observe=true，coded（uncoded=false）。
- 冻结快照 `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906/source-v3`，由 `runtime/capacity-dev-batch.json` 和 `research/launch-capacity.py`记录。旧源接收器10outer×20BP，末次BP20、LDPC50，动态sigma2开启，early stop关闭。
- checkpoint路径 `afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk`（相对远端项目根），hash `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`。
- 旧prior路径 `outputs_budgeted_support_repair/s4_20260906/prior-cap40/cache_snr8.pt`，hash `2037a0a6f2179a7ca2630ee8be08bcc536775c8024f2ee7c9f58c597e52c6c03`；calibration.json明确nomination_cap8。不可换新400帧direct40 prior。
- 原T2记录 `runtime/fixed-feedback-calibration.json`，hash `f3e58959dd27b574b2a2e34b3e1f5587c5d77ed86d0c114de64c0e1c3d598922`；记录selected_temperature2，active_cap40/nomination8。温度只作用DA-LS p/mu/v；独立noise feedback仍T1，不能描述为所有软信息T2。
- LDPC n2048,dv3,dc6,seed20260726，hash `7be530177c11b398d4f362ae81a663e83dd03de0ffdcd9bf2dd42eb1418f08be`。
- 旧源码hash：budgeted_support_eval.py=`1a06c9ec49dc93528cbf3b219410d9f9b8b973cd5199d3afb0d6f57340f18284`；classical_joint_unrolled.py=`59af54ccdc830e5dfa69e8c88a004e7d0703f24793e7d6af0b26b6e81c282489`。完整表在每rep的status。
- 原frames.jsonl byte SHA256：rep0=`0b74f7758773ea8320042d1e06d78c5fb4066fdacccb57a6246f06d812d2abce`；rep1=`80d6844086b8ad6a1b689a33d3613886376c6079bb1b3eebbb67ed095d5e1747`；rep2=`16968195ba10a55170d20c9ab858c25087092b8b9d994dcb5f990adb2636119b`。

## VT1控制记录与最小命令

已有历史工程smoke `capacity-smoke40`用过 `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906/identity-temperature.json`，hash `add8e80917851686c435a21ef597c859f69ddd4f4c568e52593e0c5fd31ef34d`，其frames明确covariance/T1。可只读验证远端该文件确实是split D_cal、SNR8、selected_temperature1后复用为**固定T1归因控制**；它不是由原192帧重新选择的最佳温度。当前本地没该同名正文，不可仅凭文件名认定。若缺失，应另建带明确固定控制说明的T1配置并登记hash，不改原T2文件。

下面命令使用旧source-v3，因此不传新CLI的`--receiver-shell`；执行前核对资源、文件hash与输出名。原launch-capacity.py仅在len(arms)>1时传feedback-calibration，不能直接复用该helper运行单covariance臂，否则会缺必要配置。

```bash
AFDM_ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation
AFDM_OLD="$AFDM_ROOT/outputs_budgeted_support_repair/s4_20260906"
AFDM_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "$AFDM_OLD/source-v3"
"$AFDM_PY" -u -m afdm_sp_joint_unrolled.budgeted_support_eval \
  --ckpt "$AFDM_ROOT/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk" \
  --calibration "$AFDM_OLD/prior-cap40/cache_snr8.pt" \
  --feedback-calibration "$AFDM_OLD/identity-temperature.json" \
  --snr 8 --split dev --replicate 0 --start-frame 0 --frames 2 \
  --n-total 1024 --device cuda --active-cap 40 --arms covariance --soft-observe \
  --out "$AFDM_ROOT/outputs_budgeted_support_repair/fb04_legacy_vt1_smoke_rep0"
```

先对这两帧核查与原rep0前两条六项input hash、nomination、raw初始support、F2P rounds一致，且dals_temperature=1/dals_mode=covariance，真实末次BP/LDPC结果存在。三格mean/T2历史观测不需要重跑来“补第四格”。但只靠相同t0不能证明后续旧source兼容；必须核对真实加载的源码路径/hash。使用当前源码的legacy模式作为替代时，需先通过RUN-02旧源兼容回放，不能默认等价。

正式补192帧时，同一命令分别用rep0/1/2、start0、frames64，三个独立输出目录，例如`legacy-vt1-rep0/1/2`；其他参数保持。若smoke两帧通过并被冻结，可将其原样纳入rep0、正式仅补rep0 start2 frames62，加rep1/2各64，总计192唯一ID。若重跑rep0全64，则两帧额外工程成本单独计量，不能算194独立帧或择优选择重复结果。

## 复用资格仍需关闭的实际缺口

1. 本地三格完整性及配置/身份核对已满足；远端旧source/checkpoint/prior/T1文件完整性及当前加载路径尚需运行主会话确认。
2. FB-04需要真实VT1小批smoke，而本报告没有发车；RUN-10需要原192帧完整VT1结果、失败分母和费用记录，不能用旧rep997工程smoke替代原开发帧。
3. 新格补齐后只做旧壳温度×V配对归因：先每rep成对比较，再汇总；不并入新direct40壳，不作为独立确认。当前已有VT2更差不等于VT1必差，也不授权改变旧帧、prior或温度定义。
