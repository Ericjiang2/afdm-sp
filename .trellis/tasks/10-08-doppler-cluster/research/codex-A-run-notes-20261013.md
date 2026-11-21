# A-RUN — frozen archival transfer，2026-10-13

标记：[F] fact；[D] definition/derivation；[I] inference；[S] speculation。Caveman on。

## 1. Authority / boundary

[F] Frozen protocol：[aprime-A-transfer-protocol-20261013.md](aprime-A-transfer-protocol-20261013.md)，commit `d65137de`（用户提供；未跑git），MD5 `104e980ade8969d3ab77217df289f3d6`。用户授权新analysis code＋deinlab analysis；零simulation。仅新增 `c1A_io.py / c1A_stats.py / c1A_transfer.py / unit_check_c1A.py`、本notes、compact `out/c1A/`。旧c1apb_*与drivers不改。

[D] SOURCE=OLD frames200–599，四cell×E10/E0×Rc1–10，32000 endpoints；400 parents。TARGET=OLD frames0–199；主36cell×T2×Rc4=288配置；unseen forecast204配置。长budget60＋closure40→共388配置。Closure T40来自c1ib2_r10 L16/20；c1g_r10lo仅T20。23design tasks；200 paired parents。

[F] 历史archive/部分aggregate此前已见；本轮archival/transductive screening，非prospective trial。每target cell需200×(20+40)=12000 probe inner updates；deployment overhead不为零。Cost主币=T×Rc，非wall time。

## 2. Implementation corrections before seal

[F] 续接半成品；仅新A files修正：

- `_load_archive`：原archive600/300帧≠selected400/200帧。校验selected subset，不误报配置帧数不符。
- SOURCE不一定有n_cols；必检K=8L，有n_cols时再检。支持旧sp_cfgs.SPg_flat与新sp_cfg；numeric/checkpoint context一致。
- T20与T40首轮输出可不同；取消跨T syn/dsha同prefix假设。仍必检exogenous fingerprints；同T aliases首轮prelabel、完整四轮post-seal核验。
- 必核REMOTE_ROWS_MD5 reference；plain/gzip双份只计同uncompressed bytes一次；冲突STOP。
- SOURCE先project metadata、排除0–199后再decode truth；target prelabel仅allowlist projection。info/noise fingerprints实际集合必须SOURCE/TARGET不交。
- stats原未完成。补冻结B20000/seed20261017、五family宏平均、23task J、draw内重选panel/selector/oracle、CP288统一带、A0–A4、K-A1–K-A4。仅Kc用PAVA，不改主Pe/design。
- empty/sparse reliability bins保留；bootstrap空bin→CI undefined，不删样本或虚构bound。
- predictions replay/MD5/code/input guards放在首个target truth decode之前；所有输出带_argv/_config、code/input MD5。

[F] 无protocol/grid/label/threshold更改。当前未seal，未解封真实target labels。

## 3. Unit checks

[F] deinlab，AFDM Python -B；OPENBLAS/OMP/MKL/NUMEXPR各1 thread；stdin DEVNULL；TMPDIR=/data/guoyikun/tmp/g_codex_c1A_20261013。17/17 synthetic tests通过（0.288s）。无receiver调用。

[F] 覆盖：opaque target truth/future lexer；SOURCE excluded truth不解析；fixed endpoint与syndrome隔离；gzip/plain digest冲突；receiver-unit features、constant-column deletion、C sign bounds；groupCV/λ tie；truth/future scramble、row order invariance；wrong seal先拒绝；margin/tie；unsafe/give-up式混淆拒绝；parent-sync bootstrap与重选；CP edges/population oracle带；PAVA/censor；counts/weights；null-effect smoke不冒PASS。

## 4. Seal chronology

[F] Prelabel exit=0，26.433s；seal JSON MD5 **`80285a76f951c0f9ee0219b522f87589`**。此条写入时真实target truth仍未decode、evaluate尚未启动。Remote=`out/c1A/seal/seal.json`；全部388配置×200帧×4model的predictions及models已冻结。

[F] 本条写入→下一步才启动evaluate；提供同seal MD5；code/input/NPZ/封存prediction replay先guard，后解封。模型/预测冻结后不refit、reselect hyperparameters、recalibrate、删cell或改δ/m。Feature out-of-SOURCE ranges仅记录，不clip/删格。L-nearest的80 SOURCE rates同时入seal。

[F] Seal UTC=`2026-10-13T15:55:51.418043+00:00`；915 input/config/ledger entries；SOURCE/target info/noise集合不交；全部metadata/numeric context与同T首轮aliases检查通过。完整未来prefix checks留到post-seal。A/G/C独立CV均选λ=.001；SOURCE CV Brier依次`.111874 / .116815 / .160867`；final optimizer成功，35/14/15 iterations。非target scores。

[F] 封存code MD5：io=`da07ebde541bd5018e01158218b0c4d6`；stats=`09f5dc86666d3027907a15c4c8a0611d`；transfer=`574eff22b71529338912ea1022319a06`；unit=`8df72145fb6d1a7a9828fc3241f43848`。再次unit17/17（.295s）；local code/seal与remote hash一致。seal.json 461773B，seal.md 200405B；已copy back。pred_q.npz只留remote，MD5见seal。

[F] prelabel range audit：A target中K/N低于SOURCE12800 records、高于6400；ln v低于22400；log1p(syn1)高于118。包括全部388配置×200；不是独立样本数。无裁剪、无删格、无target-derived标准化。

## 5. Evaluation

[F] evaluate exit=0，21.041s；独立tmux `g_c1A_evaluate`；同seal/code，B=20000、seed20261017、同步200parent IDs。未来alias syn/ierr/cerr/dsha1–4全一致，完整388×200 endpoints解封成功。无post-seal code修改、refit、feature补丁、阈值调整。

[F] Verdict **KILL_A_PREFIX7**。范围=此一次校准A-prefix7 fixed-endpoint criterion；非“全部A理论已否定”。

| gate | result | decisive fact |
|---|---|---|
| A0 | PASS | digest/numeric context、partition fingerprints、aliases、truth隔离、seal guards通过 |
| A1 | NO_PASS | ECE=.0505948>.05；E_delta=.0549358>.05；abs error≤.05仅47/70=.671429<.8 |
| A2 | PASS | 三Brier gains均positive且simultaneous lower>0；vsG gain=.0156208≥.005 |
| A3 | NO_PASS | J_A=.571429>.10；J≤.10仅9/23；vsG/C point design gains为负 |
| A4 | POPULATION_DESIGN_INCONCLUSIVE | certified5/23=.217391；全为certified non-operable，无A推荐获risk/near-optimal证书 |

[F] ECE_A descriptive 95% cluster CI `[.0477562,.0534234]`；ECE point微过线不单独强kill。五family observed−predicted bias H1–H5=`−.0196261,+.0055940,−.0256452,−.0233337,−.0033087`，点值全≤.05。E_delta kill lower=.0484442≤.05，同样不单独强kill。

| comparator | Brier_comp−Brier_A，point [simultaneous bounds] | J_comp−J_A，point [simultaneous bounds] |
|---|---|---|
| G | .0156208 [.0141685,.0170638] | −.0908289 [−.2463286,.0564374] |
| L | .1151081 [.1116351,.1186686] | .0793651 [−.0370370,.2045855] |
| C | .0531245 [.0489447,.0574731] | −.1358025 [−.2045855,.0864198] |

[F] Brier_A=.0567751；G=.0723959、L=.1718831、C=.1098996。J_A descriptive 95% CI `[.451499,.640212]`。Six-gain bounds为paired-parent approximate simultaneous bounds，每tail .04/12；非普通95%CI，也非population最优证书。

| kill | triggered | exact reason |
|---|---|---|
| K-A1 | YES | false-feasible11/23=.478261；negative-family lower8/23=.347826>.20（tail=.05/7） |
| K-A2 | NO | Brier gain vsG upper=.0170638，不小于.005 |
| K-A3 | NO | J gain vsG upper=.0564374仍≥.05；A/G原始choices一致12/23=.521739<.90 |
| K-A4 | NO_OBJECT_CROSSING_USED | 全部δ概率/配置已预先预测；无future/truth/per-cell fit或Kc救主门 |

[D] K-A4冻结规则无独立“Kc成功”数值门；未创造一个。其“只能讲Kc”分支执行为禁止secondary rescue/跨对象宣称，而非另凭事后Kc比例生成positive/negative新门。主失效已由K-A1判定；K-A4未触发不表示δ预测可靠。

## 6. What result supports

[F] A比G/L/C的平均概率分数明显好；tail/design失效仍大。11 unsafe picks中10个Rc1、1个Rc2。例：

- 6.5dB ρ.2 L4 T20 Rc1：sealed Pe_pred=.0439317；Pe_obs=.235。
- 8dB ρ.2 L16 T20 Rc1：.0764826 vs .470。
- 9.5dB ρ.3 L24 T20 Rc1：.0730649 vs .655。

[I] SOURCE四cell训练的load/noise/effort surrogate有可迁移平均信息；它没有保住低FER设计tail，尤其Rc1 nowcast。主Brier只评Rc2–4，设计候选按冻结规则含Rc1→赢Brier不能推出安全选配置。此处不移除Rc1重跑、不加target calibration救门。

[F] Optional Kc：40curves全部列出；39uncensored paired，29个abs log error≤.15，conditional比例.743590；另1censor记录保留。Secondary δ=.20时J_A=.602293；均不救主失败。Kc不替代δ=.10 tail。

[I] 保留“load/budget-aware probability diagnostic”证据；drop此variant作为已验证的5(c)设计criterion。K-A1按预登记approximate cluster lower触发；不是所有推荐的population FER已获否定证书。A4只认证5个拒绝task非operable，其他population statements保持unresolved。

## 7. Artifacts / hygiene

[F] Compact local/remote同relative路径：`experiments/headroom_ladder_20261008/out/c1A/seal/{seal.json,seal.md}`、`analysis/{analysis.json,analysis.md}`、`unit_check.json`、`prelabel_exit.json`、`evaluate_exit.json`。每个<1MB；无raw rows复制，无simulation。NPZ/phase logs留deinlab。

[F] analysis.json MD5=`12cb60b280452a4ef8b377c42881ecb4`（589861B）；analysis.md=`5f36e9bbcf2f8b2bf9c11f3e3eb7aed3`（145014B）；seal最终MD5仍`80285a76f951c0f9ee0219b522f87589`。旧c1apb_lib/stage1/stage2、driver_c1esc/driver_c1ib2、frozen protocol MD5与本轮前快照一致。Local AST、unit、完整prelabel/evaluate、copy-back hashes通过。未跑git。

[F] 已清自有`/data/guoyikun/tmp/g_codex_c1A_20261013`与私有tmux socket；核验无live sessions后清理。证据保留remote out/c1A，封存四code副本在source_snapshot。七个compact artifacts的remote/local MD5一致；sealed code最终未改。
