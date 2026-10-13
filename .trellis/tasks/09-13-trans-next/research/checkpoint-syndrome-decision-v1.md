# 检查点有效码字与普通早停参考

读取四个已审计 BP/SISO MEAN/REF47 臂、32 个外生开发块、7/8 dB，共 256 条接收记录的保存译码 APP。按原校验图计算 `H_code (APP<0) mod 2`；未重新运行接收机或译码器。选定数组由既有 restore 校验形状/类型/哈希，完整 NPZ 文件哈希及字段库存也核验。分析耗时 5.83 秒。结果 [JSON](checkpoint-syndromes-v1.json)，SHA `1bad89858eb0b3a4e403104b4d619a5f187f4b0541dfe3a43924b63f10cff14f`。

| SNR/臂 | 首次零 syndrome：outer 1/4/7 | 终端前从未通过 | 通过后终端失败 |
|---|---|---:|---:|
| 7/BP MEAN | 1/0/0 | 31 | 0 |
| 7/BP REF47 | 1/17/7 | 7 | 3 |
| 7/SISO MEAN | 1/0/0 | 31 | 0 |
| 7/SISO REF47 | 1/17/7 | 7 | 0 |
| 8/BP MEAN | 9/0/0 | 23 | 0 |
| 8/BP REF47 | 9/23/0 | 0 | 0 |
| 8/SISO MEAN | 6/0/0 | 26 | 0 |
| 8/SISO REF47 | 6/25/1 | 0 | 0 |

零 syndrome 只证明合法码字。离线与真发送码字比较，本批保存检查点未发现合法但错误的码字；不能将 32 个块的观察推广为零未检测错误率。MEAN 只检查 outer1，不能把未保存的中间轮计为失败或从未可译。

BP_REF47 在 7 dB 的块 0、9 于 outer7、块 26 于 outer4 已译出正确码字，后来终端失败。这说明“固定继续直到终端”并非对所有开发轨迹都单调改善。它不证明新调度，也不直接给可部署成本。普通 syndrome 早停必须先作为强参考，不能把弥补这个缺口包装为新颖方法。

## REF-03 实现前合同

通过 CodeFeedback 的显式 `stop_on_valid_codeword=True` 开启，False 保持默认路径。仅 legal/both/active、非诊断反馈可用。使用已有 decoder 返回的实际 decoded、decode_ok 与最后 syndrome；不加新译码、不看真值、不积累 APP。检查点只在原固定 1/4/7 上触发。

成功后立即结束外层循环并跳过终端 BP/SISO/LDPC；实际 CE、检测和译码调用数量必须与停止前缀一致。返回当前 H、其检测噪声和成功检查点的有限矩、原 decoder 输入 LLR、decoded 与提取信息位。检查点 LLR 是原译码器实际使用的未截断 channel LLR，不能伪装成普通终端 clip20 LLR；明确记录 `decode_source=checkpoint`、`terminal_executed=False`。未早停时使用原终端路径。保留硬符号、均值、方差语义，真值仅供外部错误计分。

不运行停止后的符号/噪声更新或 learned 后处理；拒绝与不相容的轨迹/残差选择、refit、support exchange 或诊断控制混用。共同返回所需状态显式构建，不通过异常伪装成功。默认完整回放、真实小码成功/失败、末端调用被实际跳过及资源计数先验收，之后冻结 N1024 工程合同。当前没有新的统计确认准入。
