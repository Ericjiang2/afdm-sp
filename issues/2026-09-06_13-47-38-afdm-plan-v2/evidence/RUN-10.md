# RUN-10 旧壳温度×V完整配对矩阵

原192帧D_dev rep0/1/2各frame0..63，旧nomination8/cap40，source-v3/旧prior/LDPC不变。复用FB-04冻结rep0前2帧，仅新运行其余190个身份，三路exit0；三格历史记录不重跑。

| rep | meanT1 | meanT2 | VT1 | VT2 |
|---|---:|---:|---:|---:|
|0|39|40|38|44|
|1|47|48|46|53|
|2|38|41|40|48|
|总帧错/192|124|129|124|145|

V在T1下FER差0，配对win3/harm3，描述性分层配对bootstrap95区间[-0.02604,0.02604]。V在T2下差+0.08333，[0.046875,0.125]；温度在mean下+0.02604，在V下+0.109375；差中差交互+0.08333，[0.03646,0.13021]。各流方向和主效应均保存在JSON。bootstrap20000次、固定seed2026090604，在各流内以四格同帧为一个重采样单元；区间未经多重校正，不作正式覆盖或确认性显著性结论。

处置：NEGATIVE_WITHIN_SCOPE。旧V(T1)没有净FER收益，旧VT2更差涉及温度与V交互，不能把VT2差距简单归因于V本身；不推断新direct40动态v或uniform-C结果。

analyze_vt1192.py逐帧断言六项input hash、身份、source/checkpoint/prior/LDPC、mode/T、finite、实际expanded<=40及共同初始支撑/F2P rounds。所有译码失败留在192分母，逐帧错误与decode标志完整保存；归档含真实frame/status，不能以文件名代验收。

新增190次接收累计子进程175.196s，队列窗口111.934s，CPU4核每进程合计0.19466 core-hour，GPU观察1279MiB。smoke另计4.918s，两次未启动receiver的前置失败保留。并行插桩费用不是G2。完整JSON与压缩归档见vt1192-runtime-validation.*，源目录及batch packet可追溯。
