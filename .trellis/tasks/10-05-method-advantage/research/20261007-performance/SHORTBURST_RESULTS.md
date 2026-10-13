# 独立两帧获取实验：收益可见，筛选可靠性门未过

单径宽整数delay/CFO、N64、T2、SNR5dB，固定旧三码；seed2026100703的256组新配对观察。随机码SCREEN32错误60/256，调优二次码90/256，差11.71875个百分点，探索性配对95%区间[5.65497,17.78253]个百分点。随机码完整FULL/SCREEN32耗时比28.375687；完整联合门仍FAIL。

|方法|current错误|调优二次错误|随机码错误|
|---|---:|---:|---:|
|FOURTH|178|145|92|
|SCREEN32|171|90|60|
|FULL|170|90|57|

唯一失败门是筛选附加风险：随机码上SCREEN32错而FULL对3组，反方向0，单侧95%CP上界3.0007543%，超过2%要求。点估计1.17%不替代置信界。不能把四项通过记为整个方案成功。旧四帧FAIL完整保留。

源码e983beb53f4d84b2f47fccd28bc0a0b35ef050d3；独立远端快照11fe4e76a1b2ae6e033cff78392142b2858894b0。P/A均complete，launcher exit0，累计223.668748秒，峰值88109056 bytes；新增1536向量、98304复标量、2304获取调用，0新设计。1641份回传stage文件已按远端SHA256核对。

独立A重建所有Y、fourth分数、保存选择及计数；似然的显式混合公式只抽查24个候选，不冒称全量重新估计。Y最大差3.5839e-13，fourth1.2442e-11，mixture1.8190e-12；审计自身0新观察、0估计器调用。详见SHORTBURST_RESULT_REVIEW.md。

全部原始文件远端根 `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_acquisition_shortburst_20261007/`；每文件完整路径和MD5/SHA256见同名本地REMOTE_INVENTORY.json。小证据回传，NPZ不入Git。

科研直觉：缩短观察后，相位码的区分优势更明显，但便宜的四阶分数不能完全代替有限字母似然。固定扩大候选集是直接减少筛选遗漏的办法。SCREEN128_PROTOCOL.md冻结了新的1024组一次验证；不按旧miss rank择K、不池化旧数据、不换seed反复验到通过。

该成果保留为有用的OFDM→AFDM经典适配；随机码、FFT、QPSK四次幂均不声称首创。结论范围是盲delay/CFO获取，不是多径信道估计、连续CFO或BER优势。
