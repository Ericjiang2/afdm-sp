# 补充实验工程成本口径

A2分母按direction_cost.py原合同恢复：direct40、achievable prior400、M96、两轮F2P。source-profile-v2观察适配器与旧run_frame在同一工程块上H/sigma相同、decoded逐位相同，LLR相对误差3.146e-16，通过预设1e-6门。

3个F、3个T、3个初估E实际完成。F耗时A2=1.42383s、B0=0.85517s、旧Bstar=0.76544s；T=0.05299—0.07068s，初估E=0.03165—0.03640s。单线程，峰值PyTorch显存117109248 bytes。同步算子计时包含字典、OMP、F2P白化、外环/终端BP、DA-LS、LLR与LDPC；嵌套时延不相加。

这是每臂一个独立工程块的含观测开销报价，不能判1.1×A2门、p95或FER。新物理重拟合/检测器/反馈/导频的成本未借用初估E代填，须各自有限pilot后准入。共享工程账本原子约束128F/256T/128E；11项远端合同测试通过。全部开发规模和未计价项见outputs_comprehensive_supplement_20260909/budget-plan-runtime.json；未生成确认数据。继续BASE-01新五族工程检查和开发批次报价。
