# 水声 N256 关键结论迁移检验 v1

用户2026-09-14最新收窄为先只执行水声N256；普通RF版配置保留但暂缓，不运行接收实验。替换水声参数并运行少量关键对照，未见实质变化时不重跑全量。本合同冻结在新场景BER数据产生前；不解除独立CONF、正式COST暂停。

## 参数与模型

主场景UWA：N256，复基带Fb4000Hz，fc12000Hz，c1500m/s，τmax6ms，lmax24，vmax2m/s，νmax16Hz，kcap2，CPP32，rho.5。
暂缓配置RF（本批不执行）：N128，Fb10MHz，fc3.5GHz，c3e8m/s，TDL-C DS100ns，最大超额时延.86523us，lmax9，vmax120km/h，νmax388.8889Hz，kcap1，CPP16，rho.5。
均用c1=(2kcap+1)/(2N)、c2=(sqrt(2)-1)/(2N²)；保留整数时延／完整分数频移G1传播。水声不含宽带时间伸缩；RF是TDL-C功率时延表+有限振荡器近似Jakes+量化时延模型，不能称严格全连续3GPP模型或完整真实水声。这些限定必须跟随结果。

UWA生成8条物理路径：首条超额时延0，其余7条均匀于[0,6ms]；按最近整数映射Fb采样，路径平均功率正比exp(-τ/(2ms))后归一化，零均值复Gaussian增益；独立均匀角度生成ν=16cosθ，未补偿公共时间伸缩。此PDP／角度分布为明确建模选择，不冒充实测拟合。
RF使用3GPP38.901v18.0 Table7.7.2-3全部24tap归一化时延及功率，延迟乘DS100ns后最近整数映射，不删合并同延迟tap；每tap用16个均匀到达角和独立均匀初相的正弦分量近似Jakes，各分量幅度sqrt(tap_power/16)，不按瞬时实现额外归一化。两模型分别用固定新种子namespace[20260914,741031,domain,block,component]。本批仅生成UWA的16个独立信道；不同方法/pilot/SNR共享同一信道、数据和单位噪声。

N-dependent公开容量采用K=min(40,D//2)：UWA40/RF15；普通容量增强K+4=44/19。RF D30不能沿用非法K40，报告必须说明预算改变。这不是纯N因果实验，旧结论到新物理场景与公开预算的联合迁移。

## 对照

p0=同rho的ZC root7，pZ=sqrt(Nrho)*e0，等总pilot/data期望能量。F2P训练头保持冻结，无新训练；跨pilot/参数迁移失败仅约束该冻结配置，不能否定所有学习方法。
每pilot五臂：OMP_BASE软反馈、OMP_HARD硬反馈、OMP_PLUS4普通扩容、F2P_HEAD冻结头、F2P_RESID普通归一化残差。10 outer×20BP，cluster extension2，其余原receiver参数共享。数据为新iid未编码QPSK，分量±.5，无LDPC/码反馈，接收边界仅y,pilot,sigma2,constellation。真实信道/物理参数只能用于生成与外部评分；禁止读取真值路径数调容量。
SNR固定10/20dB（sigma2=10^-SNR/10），覆盖低/高两端；不根据结果追加SNR。报告组合波形CPP峰值和PAPR，无裁剪、无逐帧能量重标；新pilot不可用旧DAFT单位模接口直接判非法。

## 关键问题与判别

1. 同壳HEAD相对OMP_BASE及普通RESID的BER差方向是否保持；普通扩容是否可匹配；经典软反馈相对硬反馈关系是否改变。
2. pZ相对p0是否改写性能排序；代数核对同能量整数Gram正交，不将它等同G1 BER最优。
3. 每块总receive/每bit成本与实际活动原子、BP边数；setup及物理生成另报，不冒充正式COST。

冻结报告UWA全部2pilots×2SNR×5arms端点，按16信道配对，20k固定block bootstrap描述性95%区间。误差比特不足100的比较标注低错误量，尤其零错误不以退化bootstrap区间宣称等价。观察到排序反向必须明确列出；若HEAD减参照ΔBER的区间下端>0且ΔBER≥.002，标记明确实质退化。区间完整落于[-.002,.002]且错误量充分时，只称“本批未见超过0.002绝对BER的差异”；不能宣称普适等价。其余结果不确定或混合。阈值是本次有限诊断的约定，不是旧4%相对增量的独立确认门槛。

发现变化先检查物理难度／合法预算／模型迁移边界和工程错误；不依据想要的排序修改参数。没有明显变化也不重跑全量；这批不足以支撑正式统计结论时如实保留不确定性，不自动加样本。

## 工程、开发与证据

工程block0/1：UWA合计2A/40F，另block0的p0@20dB五臂分别重复5F，合计2A/45F/0D，时间上限900s、输出2GiB。核对新N、元数据、公开容量、checkpoint严格加载、全部有限值、5类完整接收和无编码调用；重复状态精确，物理CPP传播与独立显式矩阵误差≤1e-10。
工程通过后同配方block2..15：14A/280F/0D，上限1800s、输出4GiB；报价若无法满足上限则停在明确资源失败，不伪称完成。合计16A/325F/0D，320科学接收，5重复排除。只用已授权deinlab CPU单线程、/data/guoyikun范围和原哈希source/checkpoint；源码/合同/summary/raw SHA绑定。guard覆盖build_receiver及receive中已加载编码入口；模块定义导入不等于构造。

任务配置替换只在新场景入口完成；历史N1024数据和脚本冻结不覆盖。独立check审查实现与结果；日志追加、失败attempt保留、审计先等producer exit与summary。所有工程重复、失败调用计入真实成本。

### 启动前预审澄清（仍在新场景数据产生前）

固定domain ID：UWA=0、RF=1；component ID：delay1、gain2、angle3、phase4、bits5、noise6、arm_order7。禁止字符串hash作随机seed。arm order在该namespace后附snr和pilotID（p0=0、pZ=1）。
每domain/pilot/SNR固定五个比较：HEAD−BASE、RESID−BASE、HEAD−RESID、PLUS4−BASE、BASE−HARD；另对每domain/SNR/arm完整报告pZ−p0。低错误量定义为min(candidate_errors,reference_errors)<100。HEAD实质退化规则分别应用于BASE和RESID，任一触发均报告；其他比较只按原符号与区间描述，不事后选参照。无额外抽样消除不确定性。
guard覆盖build_receiver调用与receive；模块导入期未构建LDPC由冻结源码静态追踪支持，不能称guard测量。预审检查已确认top96内部限制候选池尺寸、RF容量合法、扩展support裁剪到kcap且比较唯一(delay,doppler)对。
