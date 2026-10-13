# CORE-03 / WIRE-01 / OPS-01 实现进展（非验收完成）

新固定prior保存全部复系数合并标签、物理/展开参数、身份、输入hash和配置。direct40 loader拒绝旧nomination域及不完整schema；CLI明确传shell/cap/extension并允许纯A0无prior。

恢复失败复现：session58820，run_harvest不接受resume。当前同一run_harvest已加入显式恢复：全manifest不变，source/config/identity匹配后复用完整帧；只算缺失帧；不可变torch产物通过fsync+hardlink发布；flock拒绝相同输出并发。

session59676：14项针对性CPU测试通过（0.184s），覆盖缓存重建不调用harvest、只缺frame1时恰好调用其stream9 seed且frame0字节不变、配置改变拒绝、重复锁拒绝、复杂合并/零系数标签、direct40真实forward和A0旁路。fixture为合成系统，未证明真实N1024 prior400、GPU或LDPC完成。

未完成：完整400帧prior真实运行、CLI/GPU/LDPC烟测；OPS外层持久launcher、预算消费、截止、接收帧恢复与资源隔离。三个CSV行保持进行中。新增provenance当前独占创建；中途失败历史与源hash完整性还需完成审查。
