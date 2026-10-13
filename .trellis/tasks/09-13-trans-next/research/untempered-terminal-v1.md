# 未加温终端经典控制

源码核对：mp_detect_bp_torch的边消息距离除以temperature×var_ext，节点终端似然不直接除以temperature。有限先验分支内核默认temperature1，但terminal_decode为保持原终端分支比较显式默认2；当前强参考recipe的terminal_scale=.5。两处设计不是代数上可互换的一个比例，不判为代码错误，不改既有默认。

本批仅温度1、物理噪声方差；EST/TRUE_H×RETAIN/ZERO，共128T+128D，600s4GiB1CPU，全部旧32块7dB。对照前批同输入的温度2四格，不扫连续尺度、不复用旧确认，不重跑原始基准。来源绑定前两批raw PASS；实际H、prior、sigma、边数、LLR/APP、独立译码及256raw回读按已有合同执行。

这是经典有限BP参考资格与干预诊断，不是新方法或全链接收机对比；若有实质变化，还需独立整链成本/性能与相应强参考。H_true仍只用于诊断。
