# Codex independent derivation (gpt-6.1-sol, xhigh, read-only, did not read the Opus draft), 2026-10-14

**可以给出严格、可计算的互信息下界；但它不能单独认证“这套一帧 LDPC 的理想 FER=.5 负载”。** 以下区分严格结论与筛查用途，所有对数以 2 为底。

**1. 下界：先固定输入分布，避免偷换系统。**

固定接收机已知的真实 delay 集合，以下互信息均条件于它；设 \(F\) 为单位酉 IDAFT，\(w\sim\mathcal{CN}(0,\sigma^2I)\)，信道、数据、噪声相互独立。
令每 tap 序列为 \(M_lh_l\)，堆叠 \(h\)，定义
\[
B_x=[\,\operatorname{diag}(cp_l\odot S_lFx)M_l\,]_l,\qquad Y=B_{p+d}h+w=G_h(p+d)+w .
\]
假设 \(\mathbb E d=0\)，定义**实际先验二阶矩**，不是接收机估计误差：
\[
C=\mathbb E hh^\dagger,\quad P=B_pCB_p^\dagger,\quad R_d=\mathbb E_d B_dCB_d^\dagger,\quad Q=\mathbb E_d B_d^\dagger B_d,\quad R_z=\sigma^2I+R_d .
\]
以下恒等式不要求信道高斯：
\[
I(d;Y)=I(d;Y\mid h)-I(h;Y\mid d)+I(h;Y).
\]
若 \(h\sim\mathcal{CN}(0,C)\)，条件输出高斯，故 \(T:=I(h;Y\mid d)=\mathbb E_d\log\det(I+\sigma^{-2}B_{p+d}CB_{p+d}^\dagger)\) **精确**。
在**信道系数空间**用 Sylvester 恒等式和 log-det 凹性：
\[
T\le U:=\log\det\!\left[I+\sigma^{-2}C^{1/2}(B_p^\dagger B_p+Q)C^{1/2}\right].
\]
这个 \(U\) 对非高斯信道也有效：先用 Gaussian 最大熵上界条件输出熵，再做同一个 Jensen 步骤。
若整个 \(h\) 高斯，在其非零协方差子空间用 Gaussian 先验熵及 LMMSE 误差熵上界：
\[
I(h;Y)\ge J:=\log\det(I+R_z^{-1/2}PR_z^{-1/2}).
\]
具体是 \(h(h\mid Y)\le h(h-\widehat h_{\rm LMMSE})\le\log\det(\pi eC_e)\)。\(B_dh+w\) 与 \(h\) **不相关**即可；不需要它高斯或独立于 \(h\)，也没有独立训练观测。
离散输入相干项另作严格下界：对 \(G_h=VR\) 做 QR，按逆序链式分解并只保留第 \(i\) 个消除后续符号的观测，得到
\[
I(d;Y\mid h)\ge A(h):=\left[H(d)-2N+\sum_i J_{\rm QPSK}(a|R_{ii}|^2/\sigma^2)\right]_+ .
\]
这里假设各符号边缘均匀 QPSK；\(J_{\rm QPSK}(\gamma)=I(X;\sqrt\gamma X+Z)\) 是**精确四点输入 AWGN 互信息**。非均匀边缘改用实际标量条件熵；不能用 Gaussian-input log-det 替代。
独立 QPSK 时 \(H(d)=2N\)；真实一帧 LDPC 码字时 \(H(d)=N\)，因此相干下界必须减去 \(N\)，不能假装码字符号独立。
最终严格下界为
\[
\boxed{I(d;Y)\ge B_{\cal P}:=[\,\mathbb E_h A(h)-U+J\,]_+.}
\]
Gaussianity 只保障这里的完整 \(J\)；换成非高斯同协方差信道，没有互信息大小排序。低估干扰协方差可能使下界虚高；任意错配 \(C\) 也没有保证方向。
计算只需 QR、标量 QPSK 积分和矩阵分解；\(U\) 用 tap 分块与行列式引理可降至 \(N\) 阶。\(A(h)\in[0,H(d)]\)，Monte Carlo 可用同时单侧 Hoeffding 误差保证数值下界。
**不要在输出空间直接 Jensen：**那会给 \(U_{\rm out}=J+\log\det(I+R_d/\sigma^2)\)，而相干互信息不超过后一项，这套界必然退化为零。

**2. 两个参考及真实生成器的边界。**

(i) 接收机自身模型：\(M_l=\sqrt N V_8\)，\(V_8\) 为 \(W=2.5\) 的单位正交 DPSS，\(C=I_{8L}/(8L)\)。
若 \(\operatorname{Cov}(d)=aI\)，则 \(Q=aNI_K\)，但
\[
R_d=a\,\operatorname{diag}(q),\qquad q[n]=\frac N8\sum_{j=1}^8|V_8[n,j]|^2 .
\]
\(q[n]\) 不必等于 1；“总期望能量 1”不允许把它擅自替换成白色干扰。
(ii) 物理二阶统计的 Gaussian 参考：\(M_l=I_N\)，各 tap 独立，完整协方差为
\[
\boxed{\mathbb E[a_l[n]a_j[m]^*]=\frac{\delta_{lj}}LJ_0\!\left(\frac{4\pi(n-m)}N\right),\quad n,m=0,\ldots,N-1.}
\]
Poisson 射线数因 \(1/(LR)\) 归一化而消去；CPP 后的 tap 协方差是 \(\operatorname{diag}(cp_l)C_l\operatorname{diag}(cp_l)^\dagger\)。此时白输入给 \(Q=aI_{LN}\)、\(R_d=aI_N\)。
[实际生成器](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver_c1.py:108)仅条件于射线数和 Doppler 时高斯，整体是混合分布；(ii) 是替代概率律，不能自动证明原系统 headroom。
原射线律仍有严格版本：按原律平均 \(A(h)\)，保留 \(U\)，取 \(J=0\)；或利用确实高斯的 \(z=(a_l[0])_l\sim\mathcal{CN}(0,I_L/L)\)：
\[
I(h;Y)\ge I(z;Y)\ge J_z=\log\det C_z-\log\det(C_z-C_{zh}B_p^\dagger R_Y^{-1}B_pC_{hz}),\quad R_Y=P+R_z .
\]
\(C_{zh}\) 由上述 Bessel 协方差取得；\(z\) 只是证明工具，没有提供给接收机。真实码的 \(\operatorname{Cov}(d)=aI\) 要核验，不能仅凭码率断言。

**3. 门限选择：严格容量筛查用 1；1.154 只能另列经验筛查。**

独立 QPSK 的 \(B_{\rm iid}/N>1\) 支持同码率、跨独立帧随机编码的可达性；它不保证现有 \(n=2048\) LDPC 的 FER。
\(2I^*=1.154\) 属于该 BP 译码器的输入信息经验标尺；联合块互信息与 bit-metric 信息不是同一量，不能直接互换。[MI 与 GMI 的区别](https://arxiv.org/abs/2003.11694)。
真实码字的 \(I(d;Y)/N\le1\)，拿 1.154 作它的门限直接不合法；认证同一码的 FER=.5，需要实际 MAP 性能或有效的有限码错误概率界。
上面的下界是隐藏信道的 ensemble 量；按已知 delay 条件计算可以，不能把每个真实 \(h\) 的相干项当作未知信道单帧信息或 outage 判据。平均值也不能推出 50% 帧成功。

**4. 冻结筛查规则。**

冻结 SNR、\(\rho\)、同一 pilot、delay genie、负载网格和同时 95% 单侧误差；主门限 \(\tau=1\)，1.154 仅作为明确标注的经验附表。
定义 \(K^*\) 为沿冻结网格**连续通过** \(B_{\rm iid,LCB}/N>\tau\) 的最大负载，\(H=K^*/K_{c,\rm best}\)；不预设负载曲线单调，决策使用 \(H\) 的保守下限。
两 Gaussian 参考均 \(H_{\rm low}\ge1.25\)：允许优先验证更强接收机，称“参考模型下存在信息余量”；不称同码 FER 增益已证明。
\(1.10\le H_{\rm low}<1.25\)：弱信号，只支持小规模验证；低于 1.10、区间跨门限或两模型分歧：停止用此界裁决，不能据此否定算法余量。
同 \(\rho=.3\) 时给定最佳 \(K_c\) 为 6.5 dB 的 214、8 dB 的 269；9.5 dB 只有 \(K_c\ge320\)，分母未定位，不能认证正 headroom ratio。

**5. 最容易误导的地方。**

Gaussian 输入、高斯化数据干扰、对角化信道或忽略 DPSS 截断残差，都可能破坏方向；Gaussian 最坏噪声容量结果不能直接搬给固定 QPSK。[Hassibi–Hochwald](https://telin.ugent.be/~mm/Lennert/BER_degradation/01193803.pdf)。
在物理参考中 \(K=8L\) 只是比较横轴，绝不是物理信息维数。下界低于实测悬崖、全为零或没有可信通过区间，说明**界无力回答问题**，不说明理想接收机没有余量。
**严肃结论：这个屏幕可以筛研究优先级；仅凭两个 Gaussian 参考加 MI 门限，不能认证原射线信道、同一有限 LDPC 的算法 headroom。** 本次未数值估计 \(K^*\)，未读禁读文件、未写文件。
