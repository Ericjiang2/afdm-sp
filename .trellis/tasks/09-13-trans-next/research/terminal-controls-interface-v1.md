# 公共终端参数接入

REF-06 将终端温度与物理噪声沿 BaselineReceiver → ObservedReceiver → 既有 terminal_decode 一条路径传递。None 保持默认键和数值；显式控制要求合法 retained-prior BP。物理方差取原 observed sigma2，不乘 recipe 的 0.5。STOP 成功没有终端调用、方差或消息消费；元数据分别登记请求与实际消费。

真实 CPU 新快照 5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0：82 项测试通过，测试本体2.026秒，含新增5项消费/默认/非法值/STOP检查与原77项回归。语法编译及 diff whitespace 检查通过。本次只涉及 Python 模块，没有独立构建包。主会话自审，独立性 weak。

red-v1 同时暴露缺失API和测试拦截不存在forward的问题；red-v2 改拦截实际 __call__ 后，失败仅为缺失API/未登记参数。两次失败快照与日志保留。工程派发初次因复制模板仍指向旧快照而在启动前拒绝，纠正为通过82项测试的新快照后启动；没有重复实验。只读观察脚本曾有占位符替换语法错误，修正后查询同一PID。

工程合同 terminal-controls-engineering-v1 预先固定旧块0/20、7/8dB、四臂16F+2T+18D、600秒/4GiB；使用同一新源码，完整校验和开发准入另记。此实现不改变正式CONF/COST或论文贡献判定。
