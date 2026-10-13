# Phase-budget Q/A独立准入审查

2026-10-07。**最终数学审查：PASS；最终源码准入：GO，仅限冻结的Q/A确定性积分。** 初审六项问题及续审NaN问题已修复，过程记录保留如下；最终修订复核见末节。本审查未运行Q/A、科学积分、科学RNG或SSH。正式执行仍须先提交已审源码、打包并核独立快照；本报告不准入N128获取采样。

本审查者未编写06源码，独立审查主线程实现；复用了既有数学/任务上下文，并参与过05的audit，不宣称零上下文盲审。仅读取SCALING_REASONING、PHASE_BUDGET_PROTOCOL、新包、dispatch、启动脚本和直接复用的recorder/binding依赖；未重新加载Trellis生命周期。源码与协议仍归主线程所有，本轮只写本报告。

## 数学与归一化：已通过的部分

- `quadrature.phase_information`的Hermite规则权重为exp(−x²)/√π，节点对应实噪声方差1/2；`z=sqrt(gamma/2)+nodes`恰为单位复噪声CN(0,1)下的QPSK一个对称等价符号。`sqrt(2gamma)z=gamma+sqrt(gamma)Z`、Z~N(0,1)，没有遗漏√2或额外SNR因子。
- `logcosh`两项减`log I0(2sqrt(gamma)|z|)`正是QPSK相对圆化密度的log比。四个符号由符号翻转对称性给同一期望，使用一个符号不漏1/4权重。
- A的Rice密度写为`2u exp[−(u−sqrt(gamma))²] i0e(2sqrt(gamma)u)`，与`2u exp[−(u²+gamma)] I0(...)`相同；BPSK条件熵使用标准实高斯和`log(1+exp(−2gamma−2sqrt(gamma)Z))`。`2gamma−ElogI0−2I_BPSK`和`log(1+gamma)−2I_BPSK`与推导一致。
- ρ=1+x/4、GL权重除2对应Uniform[.75,1.25]；没有额外ρ Jacobian。Q在每个ρ先取Fano正部，再加权平均，次序正确。
- 理论共同Φ分解保留单个共享物理相位，不把实际channel改成独立逐坐标相位；B=1时J1=d_phase、标签信息为0的边界一致。附录的d_phase=gamma⁴/24、Gaussian预算=gamma⁴/6与径向gamma⁴/8首项相容；其尾部控制避免了不一致级数交换。它们不是当前gamma≈1.78…4.94的数值近似保证。
- genie-Fano对ρ逐点成立后取正部再积分，不要求当前48点估计器等变；上界预算和下界均不能给具体码的实际误差排序。本次确定性积分不构成N128样本准入或联合性能目标通过。

## 初审发现（修订前证据，保留追踪）

### 1. P0：缺seed，必在数值callback之前拒绝

`STUDY_CONFIG.json`没有seed，`study.py:17–18`只增加phase字段。调用链进入`afdm_efficient_information.protocol.run`后调用旧recorder的`_observations(config)`；后者在`afdm_higher_order_information/protocol.py`明确检查`'seed' not in config`并抛出`ValueError('config must declare seed')`。

修复：登记一个固定、仅为recorder合同使用的seed值，不引入RNG；增加不触发积分的注册字段检查。`imports`成功不能覆盖这条运行时准入分支。

### 2. P0：缺__init__.py，namespace import不能满足snapshot合同

新包当前无`__init__.py`。复用的efficient及higher_order recorder均无条件把`PACKAGE/'__init__.py'`加入committed-source/hash/source-snapshot集合；文件不存在会导致准入或读取失败，即使Python以namespace包成功导入study。

修复：添加真实包初始化文件并纳入提交和快照；通过源码清单断言它存在。无需为此执行任何积分。

### 3. P0：延迟thread_binding依赖未打入独立snapshot

`study.py`未预加载新包的thread_binding；当前`dispatch/import_paths.json`不含`experiments/afdm_coherent_structure_20261006/thread_binding.py`。新包binding却在recorder的`runpy.run_path`阶段导入该文件。pack_source只导出inventory和新包文件，因而即使解决前两项，独立snapshot仍缺这个上游模块；本地旧项目里文件存在会掩盖缺口。

修复：在冻结inventory前明确加载完整binding依赖，重新生成import_paths，并核对打包内容含上游binding。必须在实际numerical-library/thread inventory冻结前加载，而不靠远端旧项目的同名文件补齐。

### 4. P1：A未认证四分辨率、GL规则与完整状态清单

`audit.py:37`只检查records数量为4，完全不检查hermite_order，也不要求(rho_order,hermite_order)恰为64/128×80/120的四个组合。`rho`只被检查支持区间，`weights`只检查正值与和为1；未与规定的GL节点/权重比对。重复某个分辨率或换成另一套合法正权重先验可逃过这组检查。

`points`没有检查9个固定ρ、顺序和`gamma=a*rho²`；删除整个points列表会跳过该检查。`zip(record['values'], refs)`没有长度等式，删掉一个或所有保存values不会触发缺失错误；`bounds`也没有核对四个(samples,labels)与冻结cases的精确集合。

修复：先验证固定清单、形状、finite、唯一性和对应关系，再作数值比较；按独立GL构造或其节点/权重数学条件认证保存规则。增加删除/重复节点、换权重、漏values、错gamma和错case的零积分fixture。

### 5. P1：控制统计量没有独立重算，四分辨率收敛检查未直接覆盖Q结果

`radial`仅检查非负，不核`gaussian−phase`，points中的radial甚至不检查。`gaussian_fano`和`phase_average_first`只作单向不等式；例如把它们写成−1依然满足`phase_fano>=control`。A最后又把`records[-1]['bounds']`原样作为finest_bounds输出，因此未验证的控制值可随audit_pass传播。

`max_fano_resolution_change`来自独立radial/BPSK重积分的矩阵，它不依hermite_order，同一GL规则的两行必相同；这不是对Q保存的四档Fano值本身作收敛检查。若协议的“across all resolutions”是所有两两差，当前只与最后一行比较也不等同于该条件。

修复：独立重算所有输出标量与三类Fano值，核有限性、范围和等式；对已验证的四组Q Fano结果落实冻结收敛判据，并单独报告与独立积分的差。若采用“相对最细档”而非“两两最大差”，应在运行前明确写入协议。增加负控制值、错radial及错控制bound的拒绝fixture。数值容差仍需按协议声明为近似一致性，不能升级成严格区间证书。

### 6. P1：A没有把Q结果字节绑定回Q完成回执

`study.py:24–27`仅确认Q/attempt状态complete，然后把当前Q/results与attempt快照为A输入；未核Q/results实际SHA256等于Q/attempt里记录的artifact_sha256。把已完成Q的结果改写后再执行A，会被当作新的当前输入绑定，而不是首先拒绝破坏原完成回执的字节。

修复：在进入A数值积分前核Q的exit0、结果hash与完成attempt匹配，且Q注册配置符合本次冻结配置（phase允许Q/A差异）。用小型文件fixture验证损坏拒绝，不跑Q/A科学阶段。

## 已满足的控制与范围

启动脚本先Q后A、`set -euo pipefail`，导出单线程环境与空CUDA，临时写入均位于/data/guoyikun。60/60秒、总120秒、2GiB、20MiB、0新观察、0code-design geometry的run_contract与wrapper匹配。源码打包取已提交字节并核working tree，bootstrap独占snapshot并核manifest及外层launcher/control，harvest按Q/A phase字段收集；没有旧design_reference/optimized_reference的残留读取。

SciPy IntegrationWarning被提升为错误；报告明确数值近似不是严格有限小数证书。新包没有科学RNG调用，Q/A结果均声明0观察/获取/geometry；receiver/decoder未实现调用。固定seed修复仅满足记录合同，不改变这些限制。

## 初审验证与当时的放行条件

- 本审查实际运行：新包与dispatch的Ruff PASS；启动脚本bash −n PASS。
- 数值测试：主线程报告4个固定工程fixture通过；本审查未重跑含积分的fixture，不将静态审查称为运行验证。
- Q/A、科学积分、SSH：未运行。
- 类型检查：项目未配置独立类型检查，本次为源码准入，未冒称通过。
- 放行条件：以上六项修复及相应零科学执行的合同fixture通过，重新生成完整import/snapshot清单，复核变更后再提交冻结源码。当前NO-GO不否定数学公式；它阻止把一个无法启动或审计不完整的实现送到科学运行。

## 第一轮修订复核

已确认seed=0及协议元数据说明、真实__init__.py、study提前加载binding、上游binding进入新inventory；初审1–3关闭。A新增validate_structure，按冻结顺序检查四种分辨率、GL节点/权重、9个ρ与gamma、values长度、四种case；radial与两类控制bound已独立重算。

该轮仍NO-GO：Q结果尚未与完成attempt原hash绑定；收敛矩阵仍由不含Hermite差异的独立refs构成。另须显式检查points/values各标量finite：Python的`max(0., NaN)==0.`，当时以`max(phase差,gaussian差)`检查可漏掉第二项gaussian=NaN；仅校radial等式不能代替该finite检查。以上问题已发实现者，未自行改代码或运行积分。

## 最终修订复核：GO

已核读最终audit/study/config/tests/inventory，六项发现全部关闭：

|发现|最终处理|
|---|---|
|seed与初始化文件缺失|seed=0仅为元数据；真实__init__.py存在并随新包导出|
|binding依赖遗漏|study显式预加载binding；导出清单包含coherent上游binding|
|规则与状态不完整|validate_structure核四档、GL节点与权重、9个固定点/gamma、全部values和四个case|
|控制量与NaN漏检|phase/gaussian/radial及所有bound显式finite；radial与两类控制量均独立重算|
|保存分辨率收敛未覆盖|validate_convergence直接检查Q保存的四档、全部case和三类Fano量；独立积分变化另报|
|Q完成回执未绑定|validate_primary在A准入前及入口核complete/exit0、Q results与registration的原SHA、精确注册config；registration也纳入A输入快照|

**本次冻结的收敛定义：** 对phase_fano、gaussian_fano、phase_average_first及每个case，计算所有四档相对预先固定最细档 `(rho_order=128, hermite_order=120)` 的最大绝对差，要求≤3e-4；不是选择结果最有利的档位，也不是两两最大差。实现已经固定此定义，提交前协议已同步并经本审查核读。标量独立差≤2e-6、适应积分2e-11容差不变；这些仍只是数值近似一致性，不是严格区间证明。

本审查实际运行并通过四类**零积分**工程合同fixture：recorder metadata/package、预加载binding inventory、结构/NaN/收敛破坏拒绝、Q字节/注册config破坏拒绝。结构fixture只生成固定小阶GL规则与合成零值，不调用任何phase_information或scalar_reference积分。主线程另报告完整8个固定测试通过；二者来源分开。最终Ruff、bash −n和10个Python源码编译均PASS；无独立TypeCheck配置，不冒称类型检查通过。

最终审到的14个源码/控制文件组合指纹为 `badc3612a1f1d5b86d891c504ebfbea9580727803e501d587c353c6f483ed6d4`。生成方式：新包全部7个.py与STUDY_CONFIG、3个dispatch.py与import_paths、launch_v1.sh及run_contract，按路径排序生成逐文件SHA256映射，再对`json.dumps(mapping,sort_keys=True,separators=(',',':'))`取SHA256。关键文件：audit.py=`e3d180edd3054bdcfc5685bac79cb61e81d6caee30296df544c8870156a963db`，study.py=`29a4415c8de40eb7ed9aa54db3c93c2f95b9bd5bc1f8f629280ec1c0f1e72514`。此指纹不替代部署时对所有上游依赖的committed-source/manifest核验。

最终未发现其他源码阻断。GO只覆盖协议规定的Q60/A60、零观测/零获取/零设计geometry的单次积分；不预判数值界是否非零、不认证8.07等粗预算之外的新数值结论，也不准入共同未知相位惩罚的新积分、N128样本或其他端点。四轮性能FAIL和未完成的联合目标保持不变。
