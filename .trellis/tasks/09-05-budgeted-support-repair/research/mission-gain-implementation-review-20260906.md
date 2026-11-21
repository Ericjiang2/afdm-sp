# RUN-04 terminal gain reference：实现只读核对

2026-09-06。只读检查 `final_support_gain_reference.py`、`evidence/gain192-protocol.json` 和 `mission-gain192-final-support-review-20260906.md`，以及原runner的final BP/LDPC调用；不运行receiver/测试，不改实现或CSV，不扩展研究。首个远端结果是否通过由主会话验收。

## 核对结论

实现保持“只替换terminal H”的既定边界：没有重新运行OMP/F2P/DA-LS或sigma更新；用原最终support与sigma，对再生的同一y进行终端BP→LLR→LDPC。真实 `e1.QPSK`、complex64注入边界和information-bit endpoint与原runner一致。交叉项的解析上界公式在已声明坐标支撑前提下成立。

没有发现把oracle传进decoder、把原raw_errors和新终端bit直接相减、或重新使用生成噪声sigma代替归档sigma的实现。下面是需要明确的有限漏洞/边界。

## 1. 明确输入漏洞：缺失outer trace会真空通过

`frozen_support` 目前仅对筛出的outer记录检查 `atom_ids!=final_ids`，不验证outer索引恰好0…9。因此只剩一条final记录、或漏掉改变support的某轮时，`any(...)`仍可为False，函数仍将“整个outer支撑固定”视为成立。

这可用不运行receiver的最小记录证伪：删掉test中的唯一outer项，只留40个final IDs与有效sigma，目前函数仍返回。该缺口不证明已归档192帧有遗漏——先前只读记录已经检查原归档完整；它说明当前新入口没有执行其注释依赖的全部约束。

适当边界：在读入归档时一次严格核对各frame outer0…9恰好各一条、final唯一、所有IDs按固定顺序一致，并记录对应archive/ref hash。新函数或外层导入器落实任一处即可，不必重复建立第二套状态验证。

同一入口还接受非整数数值ID，然后在返回时 `np.array(...,dtype=int64)` 截断；例如40个带.25的小数ID可无声变成另一组整数support。可信旧runner产物使用int，当前批未见该问题证据；但“冻结原support”契约要求显式整数/非负/真实Q域校验，不能以强制cast修复原件。

## 2. 坐标支撑证明仍依赖冻结原source，不只依赖trace

`frozen_support` 验证最终40原子循环位移 `(ID-k_max)%N` 无碰撞，且存在的outer支撑一致。这足以检查S几何，但**仅凭这些字段不保证原H_est在U坐标支撑内**：若原receiver曾加入H_corr/diagnostic channel override，即使support trace未变也能在U外产生非零项。

先前研究记录已列出原C2-rel仅启用cand_active_rel、H_corr关闭、无channel override、H从零开始、重构/阻尼/逐元素阈值保持坐标支撑的源码前提。新实现不重新运行原receiver，是合理的；交接须引用核验过的原source packet/checkpoint/arm配置与导出的reference hash，不能把当前 `frozen_support` 的成功解释为“已从归档H数组数值验证U外全零”，原H数组并不存在。

`main`当前记录reference JSON hash并校验LDPC hash；不是对原source/head约定的自足验证。只要外层reference生成记录已绑定上述证据，就应明确引用它，而不是声称这一前提仅由新代码自动证明。

## 3. effective excess与交叉项上界

记 T=H_true，P=complex128投影，A=不可取得原数组的实际H_est，R=T−P，U为原S的循环对角线。若A和P均为U外零：

\[
d=\|T-A\|^2-\|R\|^2
=\|A-P\|^2-2\Re\langle R,A-P\rangle.
\]

因此

\[
|d-\|A-P\|^2|
\le2\|R[U]\|\,\|A-P\|
\le2\epsilon(\sqrt{MSE_{old}}+\sqrt{\|R\|^2}).
\]

源码 `epsilon` 使用全部选定循环对角线的残差范数，且先拒绝shift collision，避免重复计坐标。`cross_bound` 正是该Cauchy–Schwarz/triangle上界，推导正确。没有要求A严格位于字典span，坐标支撑前提足够。

`effective_channel_excess_squared` 是归档NMSE恢复的MSE减最佳表示残差，可报告原值及误差范围；它不是raw final gain向量误差。若想把它解释为 `||A−P||²` 的估计，应同时给出cross bound；一个自然可解释区间是 `[max(0,d-bound),d+bound]`，不是只看d≥0就称精确分解。

### 有限数值边界

代码另加 `round_bound=64*eps(float64)*max(1,old_mse,repr_abs)`。这是明确的浮点容差，但目前没有针对N²项范数归约、旧NMSE除法与重乘等运算的误差推导或覆盖验证，**不能把cross_bound+round_bound称为已经证明的严格总数值上界**。解析cross项有证明；64eps部分应标为登记的numerical tolerance，或由主会话已有独立数值证据限定。

尤其阈值只检查 `excess < -(cross+round)`，是非负距离的必要一致性检查，不是证明已取得未知距离本身。如果旧NMSE/source与坐标支撑前提不符，正excess也可能通过；前提核验仍不能省略。

用于范数平方的旧nmse应显式有限且非负，denominator应正；sigma已有此检查，旧nmse目前没有。NaN会使负值比较不触发，直到写JSON的allow_nan=False才失败，甚至先运行终端BP。原生成器归一化通常保证非零真值，归档nmse有既有finite证据，但独立入口最好在receiver前拒绝不合法参考值，避免浪费登记次数。

## 4. 星座、dtype与终端链相符的精确范围

- 新实现 `const=sqrt(1-system.rho)*e1.QPSK`，与原 `budgeted_support_eval.run_frame` 同一导入对象和功率缩放；不能换成视觉上等价但浮点构造/排序不同的自造QPSK。
- demapper amplitude仍是 `sqrt((1-rho)/2)`；`decode_llr(maxiter=50)`后`extract_info`与同一frame.info比较。这是旧info_errors的同一endpoint。
- 原runner的raw_errors来自10outer后的x_soft，而非额外terminal BP；新结果没有拿它做paired raw BER，这点正确。
- 投影P在complex128计算，`injected=high.astype(complex64)`，随后 **`y-injected@pilot`和BP的H都使用同一injected**；不是用高精度P消导频而另用舍入H检测。源码分别保存E_repr和E_injected，避免二者混名。
- `_fast_bp`内部再把H转换到torch.complex128是原后端行为；它保留的是已经complex64舍入的值，不代表高精度P直接注入。protocol写“complex128 then complex64 at actual BP boundary”可更精确解释为“原runner外部H_est边界complex64，BP内部照原规则提升”。
- sigma直接取旧baseline.sigma2_final，没有换成frame.sigma2或重新估计。修改H后的消导频y_data必然相应改变，这是该terminal H干预的组成部分，不是另换观测。

目前保存的是外部注入Hhash、原Hhash及final LLR/decoded hashes；原末次mu/LLR缺失，无法逐数组复核旧terminal软结果，也无需声称已复核。真实小批应证明当前实际BP调用参数遵守该链，不能以新源码静态一致替代该运行证据。

## 5. 独立LS抽样范围和预算计数

`dense_check=n%64==0`按reference列表索引挑三处，不按 `(replicate,frame_index)` 直接判断。若reference严格按rep30/31/32、各0…63排序，则恰是每流frame0；应在外层确认完整192个唯一ID的排序，避免reference重排后把它仍称“各流首帧”。

其余帧仍执行解析projection并记录epsilon，但不做独立dense LS；结果字段`independent_dense=None`如实表明这一点。不能把三次参考核对写成“192帧全部独立密集验证”。若已有REP-02覆盖另有证据，可以引用，但范围分别记录。

protocol count_limit=192，而CLI按reference长度允许任意合法slice，未自行建立跨进程去重预算账。主会话应沿现有queue/CSV账本确保首帧试跑若合格则作为192内复用，后续从剩余索引开始；不能重复该帧后仍报告仅192次，也不能将终端反事实写成“192次完整10outer receiver重跑”。

preparation包含输入再生、投影及选定dense LS；terminal_seconds覆盖终端BP/LLR/LDPC及返回前少量报告计算，定义需照实保留。192个新terminal评估与原192个已归档完整闭环是不同费用项。

## 交给主会话的最小处置项

1. 验证完整outer0…9 trace与整数合法最终IDs，避免缺失trace/截断ID无声改变冻结S。
2. 在reference生成/交接证据绑定原source的无额外H项条件；只在这一条件下解释effective excess。
3. 将解析cross bound与64eps数值容差区分命名/说明；提前检查旧nmse与denominator合法。
4. 记录独立dense只抽三处，以及首试帧在192预算中的身份和复用情况。

没有提出新增receiver、改oracle入口或扩充模型；上述均可由有限输入核对、命名和既有证据补齐。未对未返回的远端结果作任何成功/失败判定。
