# 合法抵消的结果后分账

在e1a-legal-response-v1全部工程和开发raw PASS后，读取已保存实际终端H及抵消向量，针对原A0与六个合法臂计算真实导频响应误差、检测算子误差、修正向量与原导频误差的内积。真值只进入外部离线评分；不反馈给方法、调参或选块。每个真实块1A，共32A、300秒、64MiB，CPU1，无新增CE/F/T/D或外生输入。

pilot_nmse=||Htrue p-cancellation||²/||Htrue p||²；operator_nmse=||Htrue-Hdet||F²/||Htrue||F²。alignment=Re<correction,original_error>/||original_error||²；correction_ratio=||correction||²/||original_error||²，检查new_error/original_error=1-2*alignment+correction_ratio。零原误差显式返回null比例，不添加epsilon改变定义。保存实际pilot误差向量及输入记录哈希，回读并重新计算所有指标。配对FER取已保存记录，不调用译码。跨SNR按共享块描述，不做独立确认；NMSE改善不等于FER因果或成本优势。

代码前核验：4项小型代数案例通过（半程正确修正、正交错误修正、原误差为零、零目标拒绝），AST通过。无物理样本或新估计。

恢复说明：v1完成32A后在整批回读失败（50.940秒）；hashes是扁平数组接口，嵌套dict/list被转成object数组后哈希了对象地址。对实际首记录深拷贝复现：浅哈希不等、flatten递归元数据相等；改一个数组元素被递归比较拒绝。v2复用既有flatten逐数组dtype/shape/hash及标量比较，0新增A/CE/F/T/D；冻结原32条记录、failure/exit/script哈希，不覆盖旧版本。最初只读定位误以为failure.json含records，查询报KeyError后改从32个-result.json恢复，没有实验调用。
