# RECEIVER-ADAPT-01 原始证据独立审计

2026-10-07。**ENG 工程回归 PASS；DEV 原始证据完整性 PASS，科学筛选 FAIL。**
24/24 接收完整，但 continuous 与 point 均为1684个错误，未达到≤point 90%的门槛；
continuous 完整接收中位时间7.571292秒，是 scalar 的12.762995倍，未达到≤1.25倍。
相对point，continuous改变14个硬判，纠正7个并新增7个错误，净收益为0。

复用已审源码、协议与部署准入，不重审GK数学，不重跑求积、fixture、接收机或仿真。
本轮使用标准库读取JSON/ZIP/NPY、校验哈希、比较保存数组，并对保存LLR、标签、
权重和标量账本做轻量代数核算；没有生产模块import、SSH、提交或修改原始证据。
NPY的dtype、shape和C/F布局均保留，不把存储顺序差异误当数值差异。

## 证据身份与完整性

源码commit：`7757cd504c2a9539efb1b20e49a87f8a4a74120a`；snapshot：
`df5fd3e47e3425836b3bf347878e3be06a2ce4a2`。两阶段实际contract、launcher、config、
imports字节均与已审冻结控制文件一致；registration中的config/_config、源码和输入
哈希、git_head与committed_project_sources相互一致。各输入快照均逐SHA核对。

证据目录均在 `.mission/20261007-sp-fractional-trans/`：

| 项目 | ENG | DEV |
|---|---:|---:|
| 目录 | evidence-receiver-adaptive-engineering | evidence-receiver-adaptive-development |
| 原件文件数 | 761 | 185 |
| 原件总bytes | 34092563 | 105183757 |
| attempt绑定文件数 | 750 | 174 |
| source_snapshot文件数（含合同） | 103 | 80 |
| SHA256/MD5/size逐文件核验 | PASS | PASS |
| 文件集合与manifest一致 | PASS | PASS |
| attempt/process exit | complete / 0 | complete / 0 |

DEV最大单文件7969326 bytes。两阶段均低于128 MiB输出限制；不存在缺失原件、
未绑定的执行目录文件或未完成调用替补。下面的artifact-small归档包含本次所有
manifest文件；本审计逐文件核验的是解包后的原件。

| 身份 | SHA256 |
|---|---|
| ENG artifact_manifest.json | `7d86b64c43706149f94f2fdc5a296a6d31dc5911ed9501f2a03847325e2a27bf` |
| ENG artifact-small.tar.gz | `22b3dbfaa6b7c7c2de9e64318b9c3db65264211c77d6084f497341bcbe68a591` |
| ENG attempt.json | `84e2329804d045cc5f11c3b8ff5f1878eabca8256e883ea4c1fc688ae5d195da` |
| ENG adaptive_engineering_summary.json | `049c7617f87a87ccdc44534d77c79f9ebd7c981fe0f24345812dc450467ba71f` |
| DEV artifact_manifest.json | `1778ea6196f0c37869d88245fa9f42685b0bd40517dfe6115d4847e1016fd94c` |
| DEV artifact-small.tar.gz | `6bcd023869b722dad8eb471ce43ecd59772607c36fa50ed288eb9edf88250a1a` |
| DEV attempt.json | `727d119974376da8f7516f8b4754d9b891cfc47e07481fd3714e10846f36ff38` |
| DEV receiver_seal.json | `bcf372e91d34f932ce8027379be764fb920704d32c329f64f776a0680bf27189` |
| DEV scores.json | `8f0f3b927ae0ae9f997c2ac703ae4b6921df814fba6cf648781297945d8be925` |

## ENG 实际结果

8个replay的输入、最终输出数组、全部trace和counts，逐项等于已保存QUAD-ADAPT-01
对应candidate；不仅采用summary中的PASS标记。最终phi数组字节与logZ标量精确相等，
差均为0。每例replay seal、SHA、reference_arrays_read=false与对应raw一致，参考身份
匹配原candidate；已审控制流保证先封口再读参考。

278个panel原件和278个started标记均核对到各replay内的panel；数值、边界、parent、
work_counts与旧ADAPT相同，保存/运行时间等元数据按各次实际记录保留。实际密度节点
分别为570、540、510、510、510、510、510、510，总4170；中心导数278，二分75，
聚合状态83。每因子≤1020/68，总≤8160/544，均未超配额。固定rule原件SHA与旧ADAPT
相同，为`5192cf17721439254b61499ce3574cb3a80f9e7b4003f09dda799903ad9645b2`。

8个导出DopplerFactor的节点等于retained mask筛选结果，权重和phi等于最终输出；
权重正且归一。以保存的reduced log kernel和权重独立核算Elog/KL，符合原常数项、
centered logZ与uniform基准语义；原系数、sigma2、trace与局部计数均一致。
这些是保存求积结果的代数审计，不是新的连续积分证书，certified=false保持原样。

- 原13 fixtures各执行1次，全部PASS且errors/failures列表为空。对应34条组件调用
  及counter_events累加值与保存counter总账一致。
- 组件负控制保留3条CoreFailure、2条TypeError、2条MemoryError和2条TimeoutError
  的预期失败证据。这些是测试内预期失败，没有被抹掉或改记成功调用。
- truth字段负控制的raw操作及组件账本为空，唯一receive计数为边界拒绝；有效
  payload/backend、新观测、新独立blocks、decoder全部为0。
- N=8/16/1024的21项保存矩检查，其computed数组/标量与原MATH arrays精确相同。
  9个数据步实际有14个proposal、5个reject；逐步核对接受位置、独立记录的目标增量、
  equation (8)残差与容差、全部接受检查及单调性，均符合保存账本。
- 两项mocked局部预算/TimeoutError fixture各执行1次并PASS。合成计数仍只在stub内，
  未进入上述4170/278真实回放计数。

## DEV 样本、封口与调用账本

原4个blocks、8个observed和4个truth原字节逐SHA相同；manifest/public与原DEV一致。
实际复制14个文件共348644 bytes，包括必要元数据；准备耗时0.017818703秒，CPU
0.017818695秒。准备记录的observed/truth解码数均为0，generator_calls、新观测、
新独立blocks均为0。数据仍来自同一开发切片，独立统计单位为4个blocks。

24条records精确符合block轮换arm顺序，每条started/outcome/raw/SHA均对应seal。
全部status=complete，没有fatal或未完成接收记录。seal声明truth_payloads_opened_for_scoring=0，
scores绑定同一seal SHA；已审路径先形成全部24条seal，再解码truth评分。
observed NPZ字段严格只有y/pilot/sigma2。每条raw都有自身acquisition及正的F1费用，
实际F1 response/refit计数为正；接收输出没有channel字段作为获取旁路。
guard实际账本为24 receive/24 payload、0 boundary/backend fixtures/decoder、新样本0。

两种VB各8次调用均保留20个sweeps、每sweep两次gain更新和3个数据步，gain covariance
保持完整8×8。point共635个data proposals，接受480、拒绝155；continuous共633个，
接受480、拒绝153。所有proposal的目标增量、equation (8)残差与容差及接受检查通过
保存标量核算；拒绝记录与累计账本一致，没有通过省略检查或失败制造费用差异。

continuous实际完成1280个Fourier坐标更新。逐因子局部adaptive_counts累加值精确
等于每sweep snapshot及最终receiver总账；每次调用另有8个原截断Gaussian初始化，
共64个，未冒充adaptive更新。8次receiver各验证一次固定GK表并保留37项验证记录。
1280个adaptive因子全部estimated_complete、有效分母、正权归一、phi约束与尾质量
检查通过；最终因子等于末sweep的记录。每个因子使用300–840密度节点、保留50–361
节点，均低于1020密度/68中心的局部上限。

| continuous真实工作项 | 总数 |
|---|---:|
| Fourier坐标更新 | 1280 |
| 密度节点 started/completed | 628950 / 628950 |
| panel及中心导数 started/completed | 41930 / 41930 |
| 二分 started/completed | 10725 / 10725 |
| 聚合状态 | 12005 |
| 构建phase entries | 644044800 |
| Fourier contraction terms | 643415850 |
| 面板特征函数 contraction terms | 944599040 |
| 最终特征函数 contraction terms | 98176000 |

这些是真实工作账本，不是严格误差界，也不能由其单独推导整机速度。

## 直接由保存LLR重计的误码与判决差异

每个raw的2048个LLR均有限，按LLR<0判1（零判0），重建全部49152个判位；
与保存hard_bits完全一致。再与原truth逐位比较，24条误码均与scores一致。
每arm分母为16384判位；同block的两个SNR相关，不能视为新增独立blocks。

“纠正”表示point错而continuous对；“新增”表示point对而continuous错。

| block | SNR | scalar错误 | point错误 | continuous错误 | 改变判位 | 纠正 | 新增 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 6 | 263 | 260 | 262 | 2 | 0 | 2 |
| 0 | 8 | 180 | 151 | 149 | 2 | 2 | 0 |
| 1 | 6 | 250 | 253 | 252 | 5 | 3 | 2 |
| 1 | 8 | 155 | 159 | 159 | 0 | 0 | 0 |
| 2 | 6 | 272 | 279 | 278 | 1 | 1 | 0 |
| 2 | 8 | 206 | 165 | 165 | 0 | 0 | 0 |
| 3 | 6 | 258 | 253 | 254 | 1 | 0 | 1 |
| 3 | 8 | 171 | 164 | 165 | 3 | 1 | 2 |
| 合计 | — | 1755 | 1684 | 1684 | 14 | 7 | 7 |

6dB错误为scalar1043、point1045、continuous1046；8dB为712、639、638。
point与continuous的全部16384个LLR数值均不同，但仅14个（约0.08545%）跨越判决边界。
逐case最大绝对LLR差范围0.0576611–1.2622825，RMS差范围0.0152831–0.0852147。
因此“总错误相等”不是复制point输出或所有LLR相等；此切片上的边际化数值变化
大多未改变硬判，发生的少量纠正与新增错误正好抵消。

## 完整费用、资源与筛选结论

每次完整接收计时包括该次F1、backend及原件保存等费用；三arm均为本次重新计时。
以下保存时间已包含于完整时间中，不能再相加或从准入指标中扣除。

| arm | 完整接收中位秒 | 8次完整wall秒 | 8次CPU秒 | 其中F1秒 | 其中raw保存秒 |
|---|---:|---:|---:|---:|---:|
| scalar | 0.593222198 | 4.745735324 | 4.578689499 | 3.088422910 | 0.393725934 |
| point | 1.643652558 | 13.161564077 | 12.861603214 | 3.088130909 | 1.573373680 |
| continuous | 7.571291955 | 60.702338554 | 60.234925994 | 3.093514846 | 8.307330763 |

24次完整接收wall总78.609637955秒、CPU77.675218707秒，与results总账一致。
population准备单列，源码/输入核验、评分、总结果保存等仍包含在阶段/进程费用中。

| 时间或资源窗口 | ENG | DEV |
|---|---:|---:|
| attempt wall秒 | 11.226109645 | 89.043467904 |
| attempt CPU秒 | 7.431526431 | 88.101429858 |
| actual_work callback wall秒 | 11.044766390 | 88.908314713 |
| actual_work callback CPU秒 | 7.254773702 | 87.972735318 |
| 完整进程wall秒（time -v） | 14.23 | 91.87 |
| 完整进程user+system CPU秒 | 10.44 | 90.94 |
| 完整进程峰值RSS KiB | 449552 | 591860 |
| 完整进程峰值RSS bytes | 460341248 | 606064640 |
| callback采样峰值RSS bytes | 430768128 | 606064640 |

两阶段实际NumPy/SciPy/OpenMP、torch intra/inter线程数均为1，CUDA隐藏；阶段、
进程、RSS、输出配额均未超限。ENG callback RSS与完整进程RSS窗口不同，不混用。
process stdout尾部wall包含少量记录收尾，与attempt的11.226109645/89.043467904秒
也不是同一采样点；未用其中较小值替代完整进程费用。

筛选逐项结果：24/24完整输出PASS；continuous不劣于scalar（1684≤1755）PASS；
continuous/point错误比1.0，要求≤0.9，FAIL；continuous/scalar中位完整延迟比
12.762995，要求≤1.25，FAIL。相对point的中位完整延迟比为4.606382。
这次接入修复了原continuous无法完成接收的问题，但在同一开发切片没有得到所需的
误码增益和完整成本优势。原RECEIVER-DEV-01的固定求积失败保留不改；本次不是新样本、
coded结果、强基线或held-out确认，也不支持将该切片结论推广为连续后验普遍无价值。

## 审计结论

未发现需要修改源码或原始证据的问题。工程通过、开发完成与科学筛选失败分别记录；
不将科学FAIL改成执行失败，也不以过程成功掩盖收益与成本门槛未达标。
本轮是保存证据审计，Lint/TypeCheck不适用；没有新的数值tests或生产运行。
