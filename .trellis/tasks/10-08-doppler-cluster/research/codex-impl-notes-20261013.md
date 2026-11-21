# TASK IMPL — (b) analysis；2026-10-13

## 1. Authority / delivery

**[F]** Authority：[manifest](aprime-b-manifest-20261013.md)，含A1；[R3 §6.1–6.5](codex-aprime-check-20261013.md)；[ownership](collab-plan-b-20261013.md)。用户本轮指定Codex分析代码；覆盖manifest旧“Sonnet implements”段。

**[F]** 写四文件：`experiments/headroom_ladder_20261008/{c1apb_lib.py,c1apb_stage1.py,c1apb_stage2.py,unit_check_c1apb.py}`。已scp同名remote目录。其余local写入仅本notes。driver、launcher、Sonnet data目录、git未动。无data-generation调用；无正式stage1；无TEST rows读取。CAL仅读一份config核kernel signature，未读outcomes。

**[F]** A1纳入：B5 direct rescue，加入B* union；G3对B3/B4/B5，each α=.05/3；KILL1增量检查三者。原任务B0–B4字样按最新manifest扩B5。

Authority md5：

```text
aprime-b-manifest-20261013.md  38a66ff9eef50cf8c203614b68079018
codex-aprime-check-20261013.md b8153136fb7f00a1aeb4b8787f9f6be7
```

## 2. Implementation / literal resolutions

**[F] G0。** 五臂完整frame集；error/duplicate/missing直接raise，禁止取交集删帧。核message/noise/channel fingerprints、schedule、Ee≤e的ierr/cerr/syn/dsha/decoder-iteration前缀；复算shuffle PRNG。核old configs无NEW digest。TRAIN/CAL/TEST/quiet跨批kernel/prior signature相同；只允许`driver_c1esc.py`的shuffle改动。绑定input/source开始、结束md5；分析中变化拒绝结果。

**[F] 边界。** Row无raw-y digest；报告写generator/message/noise/channel fingerprints，未冒称直接核raw-y bytes。正式stage1另要求`--shuffle-anchor-dir`：Sonnet保存的OLD namespace shuffled E10/E0 spot rows+configs；逐轮核旧out/c1esc anchors。至少一组完整E10/E0 pair；不新增scientific cell/frames。该artifact本轮未定位，主会话需传其目录。

**[F] 实际尺寸。** remote只构建既有context读取metadata，未run receiver：N=1024；H.shape=(1026,2048)，Mchecks=1026；G SHA256=`bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af`。`--mchecks`若非1026拒绝。不能用N或1024当syndrome分母。

**[F/D] noise列。** Row.sigma2是generator `10^(-SNR/10)`；receiver方差为row.sigma2/[2(1−ρ)]，ρ=.3。full A用后者log；不是noise realization。依据`driver.py:observe`、driver_c1的rho shim。

**[F] No leakage。** `Observations`只持syn/decoder counts、known K/σ²、time/frame/block；`Labels`独持ierr。`features/replay/qcache`不接Labels。z四列、generic七列/full十一列按R3固定。ierr只作TRAIN targets或终止score；cerr/dsha只作G0。无ll_in/eps_ce/true h/future statistics列。

**[F] Replay。** syndrome→cap→promotion→give-up。仅end r1–3升档，下一轮执行；后续真实Ee状态。give-up erasure恒fail；cap按当前ierr；syn0错码仍fail。promotion后同轮give-up，保持已执行E10路径，不支付未执行高档。r≥Rc无query；r>4无predictor decision。各class同stop/failure口径。

**[D] q对象。** 每live r<Rc label为对应fixed arm的syndrome-stop/cap终止失败；不是closed-loop adaptive Q。q20−qe仅在共同低档prefix比较。q准确时等于conditional rescue−harm；logistic近似不保证此identity的估计精度或逐state安全。B5直接拟合`1{Y20=1,Ye=0}`，同列/CV/ridge。

**[F] Fit。** TRAIN-only；frame mod5 CV；cells等权，每represented frame的arm/r/Rc记录总权重等额。标准化仅fit subset；mean weighted CE+λ||β||²/2，intercept不罚。λ={.001,.01,.1,1,10}，Brier选，数值tie到12位时更强ridge。constant-target fold显式Jeffreys-smoothed record事件率，保留counts；无balanced classes。pooled full/generic/rescue、LOCO full/generic、per-cell secondary皆保存；per-cell不替换primary。

**[F] B2 history。** “最近w次Δsyn”解析为最近w个单轮变化均≥−θd；需r>w，r1不给伪history。不是w-round总变化。所有frozen grids保留：P3520；B0 50；B1 6155（Rc1仅off占位）；B2 6000；B3 400；B4 880；B5 560。共17565/cell，B*不含P。

**[F] Selection。** CAL empirical FER/fullcost lower hull，P/B*对称；最多两端点，weights冻结。limit=ℓ−1.645√[ℓ(1−ℓ)/600]。mixture U=`SeedSequence(little-endian entropy words+[frame,L,int.from_bytes(b'mix','little')])`；每frame实际选一个policy，CP不吃fractional labels。q_cal取实际allocation的P/B* discordance，n规则逐字R3。nonoperable保留分母4；n=4000仅diagnostic，不能PASS。

**[F] Cost。** 实际路径t_cum，核首轮含pilot；加scalar feature/q/rescue/threshold/common-stop overhead，query按实际decision次数。setup/load排除，steady-state scope显式。预测器timer使用当前+前轮syn，不读truth。simple baseline亦收费。CAL collection共享一次；P/B* search分别计时，full q共同，rescue fit归B*；generic/LOCO/per-cell属research-only。stage2报Ccal、M=10³/10⁴/10⁵、Mbreak；shared collection总receiver elapsed不冒称64-shard walltime。

**[D] Tango。** failure sign `x+=P fail/B success`。给定δ，令s=x++x−、t=x+−x−、x0=n−s；受约束MLE候选满足：

```text
n q² − (s+δt)q + δt − x0δ² = 0,  |δ|≤q≤1.
```

取有效roots及boundary中最大trinomial loglik；反演score。discordance<20用CP upper(p+)−CP lower(p−)，each component α=.00625。整个切换方法仍标approximate coverage，未叫finite-sample NI theorem。

**[F/D] Bootstrap block解析。** block=实际acquisition shard。availability集合分层；先抽shard blocks，再抽block内整frame；层质量归一保留原frame数。全cell同步同frame weights；B20000/seed20261016。float64 shared views，max10000 union frames约1.6GB主weight矩阵；避免四份复制/反复dtype转换。假设shard足以描述timing相关性；共同host load可能仍相关，故coverage近似，quiet hook必要。

**[F] G1–G4。** CP98.75% upper两policy；Tango NI upper≤.01；Rhat≤.85且bootstrap upperR<1；≥3/4并含两SNR。G3四cell等权平均seconds/FER后取ratio，非按rows加权；α=.05/3。G4 LOCO frame-average Brier gain≥.005且95% lower>0，≥3cells；TRAIN cuts固定，TEST分cell/e/Rc报quintile net/rescue/harm。高低组空或bootstrap无live group→inconclusive，不跳掉后宣PASS。

**[F] Quiet literal。** first200 TEST IDs，8 shards；门用`|R_quiet−R_main(full TEST)|≤.03`。同200 main ratio另报diagnostic，不偷换更有利比较。未给quiet目录→PENDING_QUIET，不能PASS；数值states/labels或kernel不合→G0 invalid。

**[F/I] KILL解析。** KILL1只在reliability/NI有效时评“增量不足”；B3/B4/B5亦需可靠，避免unsafe便宜baseline撑kill。KILL2“generic同等”用已有5%工程线：P/generic saving upper<.05，generic NI/absolute可靠；LOCO gain upper<.005且Delta排序upper≤0，≥3cells。不是零差严格equivalence。

**[F/I] KILL3。** 所有CAL封存deterministic P candidates；Bonferroni每cell α=.0125/(3×3520)，CP/paired Tango harms及shard-cluster t对`E[Cπ−.85CB]`的bounds。cost/t/Tango近似，非distribution-free。只认证这些deterministic candidates；不把unsafe/无效益端点逐个判断冒称所有任意mixtures也不可能。输出明确`KILL3_mixture_family=NOT_CERTIFIED`。这是claim范围限制，非重新选TEST赢家。selected P* kill另走KILL1/G1。

**[F] KILL4。** full t_cum已含CE/LDPC；检查去掉predictor overhead才出现的优势。truth/future泄漏先invalid，不能叫物理机制kill。无遗漏组件的counterfactual证据，不编额外kill结论。

**[F] Seal。** JSON/MD均带_argv/_config/input md5s；models/means/std/λ/CV、policies/weights、CAL expected+actual FER/cost、q_cal/n_c、候选表/overhead/TRAIN cuts/source hashes齐全。stage2核seal digest、所有source/input hashes；`--seal-commit`是主会话pre-TEST commit attestation。代码不调用git，未冒称自动核真实commit/时间顺序。

## 3. Verification

**[F]** local Python无numpy；仅AST。remote AFDM Python3.10.20/numpy1.26.4，python -B，OPENBLAS/OMP/MKL/NUMEXPR=1。所有scratch在`/data/guoyikun/tmp`；dryrun tmux `g_c1apb_dryrun_codex_v2_20261013`，结束自动关闭。两CLI --help exit0；AST四文件PASS。

**[F] Unit final：**

```text
Ran 15 tests in 1.428s
OK
failures=0; errors=0; exit=0
```

覆盖：E10/Ee fixed/adaptive paths；give-up/cap/syn0错码；truth scramble决策不变/future feature不变；B2 history/strict >；CP/scipy+zero-event闭式；Tango独立数值MLE hand tables/zero-discordance/sign；hull+hash stream；bootstrap frame同步/availability/shared-memory；ridge/CV/constant labels；G3三contrast；G4空quintile；shuffle旧anchor一致/故意改dsha拒绝；exact grids；context只容shuffle改动。

**[F]** 初版4 tests报E4不存在：empty promotion mask仍计算索引。根因修为executing.any()才索引；全部contracts复测通过。未放宽规则。

**[F] TRAIN G0：** 6.5两cells各600frames，共6000rows；TRAIN8 C3/C4各600、五臂、shuffle64，fingerprints/prefix/RNG全部过。remote old config检查2393份，无NEW digest。抽取TRAIN6/TRAIN8/CAL config的kernel signature皆`d21cf11c7bc599d4f5d164c242850d1c1f9aad7c3b5b462a1ecd8bee6e13d9b1`；这项只读metadata。

## 4. Final DRYRUN — screening only

**[F]** `out/c1esc` OLD namespace：TRAIN0–299 fit，300–599作selection holdout；C1/C2各300 holdout。标DRYRUN；margin分母600保留frozen值，仅调试。未读真实CAL labels；LOCO此dryrun仅两cell，非正式四cellG4。总76.7528s；full/generic λ=.001，rescue λ=.01。

| cell | actual P FER / seconds | actual B* FER / seconds | B* endpoints | q_cal | diagnostic n |
|---|---|---|---|---|---|
| C1 | .083333 / 1.644141 | .083333 / 1.644141 | B4+B4 | 0 | 4000 |
| C2 | .176667 / 2.777118 | .186667 / 2.648333 | B5+B3 | .016667 | 4000 |

**[F]** C1实际mixture239/61；C2 P206/94、B*231/69。expected hull target与actual hash allocation分别记录，未按actual FER重调weights。两cell n_req3900、q_plan=.04；n_c floor4000。

**[I]** 强controls确实参与：C1 P与B4相同；C2 B5+B3更省时。只是TRAIN debug，不作A/one-object kill、不作G2/G3证据；真实四cellCAL/TEST还未分析。

Remote evidence：

```text
deinlab:/data/guoyikun/tmp/c1apb_unit_final.json
  md5 d9b3ab525405401b96e775a6bb1abd07
deinlab:/data/guoyikun/tmp/c1apb_dryrun_final_v2/dryrun.json
  md5 5f85881173d96c3b0071cb39b2e41567
deinlab:/data/guoyikun/tmp/c1apb_dryrun_final_v2/dryrun.md
  md5 db66f23222ac7bbca3f3111f83e26753
```

Local/remote/unit/DRYRUN code md5一致：

```text
c1apb_lib.py        6a958a71031d6a94ac288267e052b27e
c1apb_stage1.py     b9139c4b71adc3fd336093b27090137c
c1apb_stage2.py     a32097c43fb133ba44c52e2ee4ae1724
unit_check_c1apb.py 30571241caa18848f635d17aa1f02952
```

## 5. Main handoff — commands not executed

**[F]** 本轮止于implementation+unit+TRAIN dryrun；主会话按已授权顺序commit code/manifest、收齐CAL及Sonnet shuffle spot rows，再启动正式stage1。无新permission请求。

在remote code目录，environment同上；`SONNET_SAVED_SHUFFLE_DIR`替换真实saved rows目录：

```text
/home/guoyikun/.conda/envs/AFDM/bin/python -B c1apb_stage1.py
  --shuffle-anchor-dir SONNET_SAVED_SHUFFLE_DIR
  --manifest-md5 38a66ff9eef50cf8c203614b68079018
  --protocol-md5 b8153136fb7f00a1aeb4b8787f9f6be7
  --out out/c1apb/seal
```

主会话review+commit seal BEFORE Sonnet TEST。TEST/quiet完成后：

```text
/home/guoyikun/.conda/envs/AFDM/bin/python -B c1apb_stage2.py
  --seal out/c1apb/seal/seal.json
  --seal-md5 ACTUAL_SEAL_MD5 --seal-commit ACTUAL_PRETEST_COMMIT
  --quiet out/c1apb_quiet --out out/c1apb/analysis
```

**[F/I]** Stage2统计helpers已synthetic测试；完整真实TEST/CAL pipeline尚未运行。quiet、commit时间顺序及G5仍待对应证据；本次实现不宣TCOM达标。

## 6. S1 run — REAL，2026-10-13

**[F]** 用户报base commit=`c5c86f9b`；未用git核。Authority含A1/A2，manifest md5更新`ca422d9cb7dd249e1a3fb370c40f321f`。A2覆盖本notes §2旧quiet解释：现在比较同first200 TEST frames，full TEST R另报。

**[F] 代码改动，原因逐项：**

- `c1apb_stage2.py:quiet_validation`：gap从quiet−full TEST改quiet−matched200；`R_main`指matched，新增`R_main_full_TEST`。执行A2，未改协议。
- `c1apb_stage1.py`：metadata记A1/A2及matched quiet；修正旧calibration attribution文字，与已存在的per-class search/fit timers一致。无fit/selection改变。
- `c1apb_lib.py:fit_logistic`：L-BFGS-B maxls由默认20改100；保存iterations/loss/grad_inf/status。其余objective、weights、列、λ网格、CV、gtol=1e−8、ftol=1e−12不变。原失败仍raise，无隐藏fallback。
- `unit_check_c1apb.py`：新增A2匹配子集regression、convergence/显式failure contract。最终17/17，AST过。

**[F] 失败留档。** 初次G0通过，LOCO C4/generic/λ10/fold3 line-search失败，n=140956，events52454，nit10，loss=.5036210853229065，grad∞=1.480744762916153e−8。最小TRAIN-only复现：maxls20失败；maxls100 success、nit11、同loss，grad∞=1.4807447296094622e−8，停止原因为relative function reduction。未丢该λ/fold，未放宽threshold。首次尚无CAL selection/seal；`stage1.log`保留exit1。retry exit0，87.1937s；seal时间2026-10-13 07:10:02 UTC。

**[F] G0 PASS。** TRAIN四cell各600frames、五臂，共12000rows；CAL同规模。fingerprints/prefixes/context/RNG/64-shard single-thread/load记录通过；old configs2393份无NEW digest。anchors=`/data/guoyikun/tmp/c1apb_smoke`，两frame E10/E0共4配对，0 mismatch；Sonnet的0/10含五臂，我们直接核旧fixed anchors4配对。无raw-y digest，证据范围保持generator fingerprints。

**[F] 密封结果。** 下表FER/cost为实际hash allocation，seconds含overhead；不冒称TEST或confidence certificate。P tuple=`(Rc,τe,κ,τg)`；weights按所列端点顺序。

| cell | P* endpoints；weights | B* class / endpoints；weights | CAL actual FER P / B | CAL cost P / B (s) | n_c |
|---|---|---|---|---|---|
| C1 | none | none | NA / NA | NA / NA | 4000 diagnostic |
| C2 | (10,.2,0,.95)+(10,.2,0,.8)；.705880836/.294119164 | B4，同P参数/weights | .173333/.173333 | 3.910623/3.910623 | 4000 |
| C3 | (8,.2,0,.5)+(6,.3,0,.5)；.104411594/.895588406 | B4，同P参数/weights | .076667/.076667 | 3.647517/3.647517 | 4000 |
| C4 | (9,.2,0,.7)+(9,.2,0,.5)；.674509501/.325490499 | B3(E2,Rc9,τg.8)+B4(9,.2,0,.5)；.632352657/.367647343 | .170000/.166667 | 6.847072/6.797009 | 4000 |

**[F]** C2/C3/C4 q_cal=0/0/.023333333；q_plan=.04、n_req3900、floor n_c4000，无power cap。C1 q_cal未定义，非operable，4000仅diagnostic。pooled full/generic λ=.001，rescue λ=.01；LOCO/per-cell/CV/standardisation全部在seal。各cell17565 candidates，B5实际纳入union及secondary。

**[F]** C1 P及B*全候选min FER=52/600=.086667，超过CAL margin线.079852947；两者均无admissible point。该数仍低于原ℓ=.10：是本轮CAL-margin nonoperable，不能说真实target .10物理不可达。未抬target、未删cell。

**[D/I] 主要red flag：选中方案的G2覆盖不可达。** 令γ_j=coef_j/sd_j，低档同state的logit差：

```text
eta20−etae = γ_e (10−r)/10
             − [γ_B + γ_KB(K/N)] (Rc−r)/20.
```

z项、当前mode、σ²、Rc main effect抵消；sign不随frame state。密封C2 Rc10的r1–3差为2.7104/2.4092/2.1081；C3 Rc6为1.8620/1.5233/1.1846，Rc8为2.4552/2.1165/1.7778，全正。各端点κ=0，因此在可升档state，Δ门不增加筛选，P与B4同动作；weights也相同。按syn live1..1026、decoder iterations0..50的宽observable box，最大logit≤18.655；q20超过τe时无sigmoid saturation/underflow造成的分支差异。maxiter50见native_twofft.py:24及receiver.py:64/103。

**[F]** 重新replay密封CAL：C2/C3 path/fail/cost逐frame相同、R=1；C4 R=1.00736548。input/source hashes仍一致，q_cal及n规则复算一致，exit0。无refit/重选，无TEST读取。

**[I]** 在这个receiver/model/cost定义下，C2/C3的P*=B*等价延伸到future frames，无法满足Rhat≤.85；C1本已nonoperable。固定3/4 G2门无法由这份seal通过，至多C4可过。仅kill“这次密封方案达到该门”的可能性，非整个P family/任何action-value receiver不可能；不以CAL冒充TEST kill或TCOM结论。主会话应在TEST资源决定前读此red flag；本轮未启动TEST。

**[F/I] 另一数值/解释限制。** TRAIN所有live decoder_iters均50，该列无state信息。weighted mean舍入使full/generic sd=2.78959e−11（mean49.9999999999721）；rescue sd=3.58398e−11。其coef不可作“decoder progress重要性”解释；在当前live域该项仅constant offset。未见CAL结果后修改normalisation重选；需要transfer/不同decoder时另审。该限制不改变上面的正logit差/动作等价结论。

**[F] 回传完成。** local同路径`experiments/headroom_ladder_20261008/out/c1apb/seal/`保存完整22.9MB seal.json、seal.md、首次/重试stage1与unit logs、seal_verification.log；local/remote md5一致。remote根=`/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/`。tmux socket置`/data/guoyikun/tmp/g_codex_s1_tmux.sock`；无/tmp/home writes，无data generation、TEST、git。

```text
seal.json                 466a92d0fa371e7871c97c475ff0a906
seal.md                   1c76d2b877d3d59a29c9671b4c363904
stage1.log                5186ef4fe5f48e2b70ed370d2be75f24
stage1_retry.log          a00699072055e4e0c85ea463c3f4eb60
unit_check_s1.log         5832b34ded3d7d0773fb299289a8ab06
unit_check_s1_retry.log   0a6200b310fb8dcac5950d342ca02d80
seal_verification.log    37422e78049d7f4627a1ecd056ad5308

c1apb_lib.py             fcf122277f8b08a612339efcc6b5f5da
c1apb_stage1.py          5e344c405d9e29b6bb8d2d8f12b0096f
c1apb_stage2.py          edbbe5f9cc80578a993347408361aa61
unit_check_c1apb.py      6a664cce3c21be99260c89331d95709a
```

**[F]** 上述code已异于用户报的c5c86f9b，seal绑定新md5。若继续TEST，主会话需review并commit这些代码+seal BEFORE generation；Codex未执行git。当前artifacts保留原样，未为改善结果重调规则。

## 7. S2 run — SCREENING，2026-10-13

**[F] Authority。** 用户报seal commit `aec90696`、A3 commit `0c77ccea`；未用git核。A3 manifest md5=`37b8351a8e3a62ea98a899634c36e0fe`。TEST四cell各1000frames（600–1599，20000rows，64shards）；quiet各100（600–699，2000rows，8shards）。密封policy、mixture weights、q/rescue/LOCO models、standardisation均未变；无refit、reselection、data generation。旧n_c规划被A3覆盖；原primary不可达，保持denominator4。所有数均SCREENING，无NI certification/PASS/TCOM宣称。

**[F] 代码改动，仅evaluation与unit：**

- `c1apb_stage2.py:parse_args/screening_main`：新增显式`--screening`、A3/manifest attestations；读1000/100frames。只重放seal `choices`，不扫candidate family、不挑TEST winner。C1无CAL winner→NA。旧正式路径保留；SCREENING移除正式PASS/KILL判定。source digest例外仅stage2/unit；fit/replay source任何变化仍失败，例外旧/新MD5入`_config`。
- `screening_contrast/screening_pool`：各B1–B5、P、P_escalation_only vs密封B0 clock hull；seconds含密封overhead，另报inner updates。R、saving、d及paired frame/shard bootstrap endpoints入JSON。附加pool仅CAL已可评C2–C4，equal-cell mean cost再取ratio；非四cell G3替代，非primary分母改变。MD seconds列为saving=1−R；完整R/CI见JSON。
- `g4_mechanism/quintile_cluster_ci`：保留原LOCO Brier、TRAIN cuts、e/Rc strata及high−low汇总；补各quintile net/rescue/harm cluster CI。空组或任一bootstrap分母0→undefined，不删replicate/stratum、不加pseudocount。原G4 gate字段在SCREENING改名engineering indicator，非正式PASS。
- `screening_quiet`：A2/A3 matched100；并报full1000 ratio。P/B*及B4/B0两组；main/quiet syndrome、decoder-iterations、truth labels逐项一致后比较timing。
- `verify_sealed_inputs/--sealed-anchor-root`：处理已归档anchor路径，见下；只许原4个文件重定位，仍验原MD5，其他missing/digest变化仍失败。
- `unit_check_c1apb.py`：新增两种cost/d符号、固定CAL pool范围、空bootstrap、matched100两contrast、无正式G4 PASS标签、anchor重定位不放宽内容校验。远端首次21/21；加重定位contract后最终22/22，0failure/0error；local AST过。

**[F] 首次失败与修复。** `stage2.log` exit1，发生于seal输入复核、TEST载入前：旧`/data/guoyikun/tmp/c1apb_smoke/`不存在。直接找到`out/c1apb/anchors/c1apb_smoke/`；config/rows shard000/001四MD5全同seal。仅加显式路径重定位，不修改seal、复制raw、跳过校验或重跑receiver。全部2781个seal input重新验内容；新路径及原digest入analysis metadata。retry exit0，44.5157s。两次stage2及unit logs留remote `out/c1apb/analysis/`。

**[F] G0。** TEST/quiet新鲜five-arm fingerprints、E_e prefix、namespace/frame范围、shuffle、single-thread/shard/load及CAL kernel signature通过；raw-y digest未保存，仍限generator/message/noise/channel fingerprints。S1 old-config digest audit与anchor closure由密封结果及未变input hashes承接，不冒称重跑数据。

**[F] P* vs B*，98.75%单侧upper；bootstrap两端各alpha=.0125。**

| cell | FER P/B | R [bootstrap endpoints] | d | CP upper P/B | paired upper |
|---|---|---|---|---|---|
| C1 | NA | NA | NA | NA | 无CAL winner |
| C2 | .152/.152 | 1 [1,1] | 0 | .179239/.179239 | .005062，zero-discordance exact CP fallback |
| C3 | .101/.101 | 1 [1,1] | 0 | .124366/.124366 | .005062，同fallback |
| C4 | .172/.182 | .984941 [.962815,1.007735] | −.010 | .200458/.211018 | .001090，Tango score |

**[F] Practical B4=P vs B0。** 以下95%双侧cluster CI，未做多contrast调整；d=FER(P)−FER(B0)，pp=percentage points。

| cell | seconds saving % [CI95] | inner-update saving % [CI95] | d pp [CI95] |
|---|---|---|---|
| C2 | 11.104 [8.556,13.881] | 13.162 [10.412,16.172] | −.200 [−.901,.402] |
| C3 | 12.746 [10.345,15.204] | 15.766 [13.185,18.428] | 1.600 [−.199,3.414] |
| C4 | 8.845 [6.199,11.532] | 9.570 [6.712,12.442] | −1.300 [−2.982,.299] |
| CAL-eligible C2–C4 pool | 10.480 [8.940,12.039] | 12.389 [10.723,14.065] | .033 [−.830,.868] |

**[F]** 七class完整per-cell/pooled R、d、两种cost与CIs见`analysis.json:practical_vs_B0/practical_pooled`；B1/B2/B3/B5 pooled seconds saving=6.146/3.477/6.537/9.695%。密封P_escalation_only pooled saving=2.477% [1.701,3.257]，d=−.667pp [−1.300,−.100]。这些均预sealed winner的报告，非TEST重选。

**[F/I] G3。** P vsB4在三可评cell R=1、d=0、bootstrap saving endpoints=[0,0]。P vsB5：C2 saving3.057% [2.089,4.054]；C3 .163% [−.423,.763]；C4 −.008% [−.499,.340]。固定CAL-eligible pool vsB3 saving4.218% [2.978,5.478]；vsB4 0；vsB5 .869% [.505,1.209]、d=.100pp [0,.300]。G3两端alpha=.05/3，非普通双侧95%CI。四cell原G3不可评；action-value相对B4无增益，相对B5未见5%增益。只限本seal，不kill全部P family。

**[F] G4。** LOCO Brier full-A/generic（gain及冻结单侧95%两端，central90%）：C1 .044853/.052100（.007247 [.005855,.008719]）；C2 .068406/.078091（.009685 [.006318,.013128]）；C3 .063181/.072580（.009399 [.008635,.010150]）；C4 .106328/.112745（.006417 [.001949,.010821]）。4/4 point gain≥.005且lower>0。TRAIN-cut Delta quintiles：4×24strata×5组=480，全部非空、cluster CI定义；net=rescue−harm。四cell/stratum等权pooled Q5−Q1=.499617 [.477726,.520784]，冻结单侧95%两端。每组rescue/harm/net及双侧95%CI在`analysis.json:G4.delta_quintiles`。

**[I] G4判词。** 预测transfer、极端组net-rescue排序有信号；不证明独有net-value决策增益、全部quintile严格单调或policy zero-shot。例C4 e1/Rc10：Q4 net=.683908 > Q5 .532710。zero-event percentile CI=[0,0]不证明真实harm=0。P=B4、B5近似同收益，G4不能翻转increment结论。C3 FER=.101>ℓ=.10，P/B0 d upper=3.414pp；C4 P及B*的CP upper也>ℓ=.20。不能把描述性省时写成FER约束已获认证。

**[F] Quiet matched100。** P/B* gaps C2/C3/C4=0/0/.009350；B4/B0 gaps=.012220/.014659/.003568，均≤.03。C4 P/B* Rquiet=1.008920、Rmain-matched=1.018270、Rmain-full1000=.984941。C1保持NA；不把matched timing稳定当成PASS。

**[F] Storage/provenance。** 仅回传同路径compact `experiments/headroom_ladder_20261008/out/c1apb/analysis/{analysis.json,analysis.md}`；_argv/_config、input/source MD5全在两文件。local/remote digest一致；seal仍`466a92d0fa371e7871c97c475ff0a906`。raw/大seal/log留deinlab。已删本人3个`tmp/c1apb_dryrun*`目录、6个`tmp/c1apb_unit*.json`及本次stale tmux socket；归档anchor未删。无git、data generation、/tmp或HOME writes。

```text
analysis.json     468817 bytes  4976e2df36aaffbcd525223706c67b7d
analysis.md        47891 bytes  dce49afc919964e56b857c6a5651719d
c1apb_stage2.py                4e6f05f6828b75bcae7e1e05534d75b7
unit_check_c1apb.py             759c542ced23758dd43a16ba4f39d7fc
c1apb_lib.py                   fcf122277f8b08a612339efcc6b5f5da (seal同)
c1apb_stage1.py                5e344c405d9e29b6bb8d2d8f12b0096f (seal同)
```

**[I] 收束。** practical receiver节省成立为SCREENING观察；full-A预测器可保留为机制证据。当前“one object”的独有action-value增量未获支持；无需据此重调seal或扩大本轮。
