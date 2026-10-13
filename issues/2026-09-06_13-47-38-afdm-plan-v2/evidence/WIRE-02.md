# WIRE-02 — 真实入口验收

最终成功快照v2_repwiresets-1788686980/source；四个隔离作业(on/off/det_on/det_off)各A0/A2固定D_cal997帧，全exit0。10outer+final图齐全，final K均40，行列度和均等于E。显式导入既有loop9._fast_bp为runner.final_bp，消除全局afb赋值的导入顺序干扰；没有新增检测算法。

普通生产on/off：H、x、sigma、raw/info errors、decode_ok与完整译码比特hash精确一致，且与修改前全局绑定off一致。普通末次mu/var/LLR hash仍有已诊断GPU归约变化，不能声称普通所有soft数组一致。隔离确定性末次BP参考on/off全部soft与primary精确一致；参考仅作观察器工程验收，不替换科学试验/生产设置。此边界与WIRE-06一致。

失败全部保留：repwire-1788686663为实际最终适配器不接graph参数，on/det_on失败；repwirefix-1788686809为truth NumPy标量JSON失败；repwirejson-1788686884为阶段差集NumPy ID JSON失败。后两项均完成接收后写出失败，不当成零次运行。新增真实绑定及NumPy输入序列化回归。每批按8次receiver上限保守记，共32次工程尝试上限，非32个独立科学帧；均属允许小批工程验证、全部计S2，不冲减其他RUN配额。

四批queue分别12.129/20.587/19.480/20.069秒，进程总和136.294秒、4核约0.15144 core-hours；最高GPU1291MiB。连续S2预算另在stage-budget.json按全窗口扣除，不以这些较小忙时替换。graph_observer_seconds与offline_seconds单列；receiver_seconds仍含观察，未将其扣除声称部署速度。

验证：18项针对性测试与相关py_compile通过；analyze_repwire.py校验原始四批归档、配对输入、全部轮数、容量、独立密集LS、开关输出。仅一个固定工程帧，非收益或广泛可靠性结论。
