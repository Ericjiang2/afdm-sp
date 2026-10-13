# E1 Implement Plan

## 步骤（顺序执行，每步可验证）

1. `afdm_sp_joint_unrolled/e1_ldpc.py`：LDPC 工具模块（纯 numpy，无 torch 依赖）
   - `build_code(seed) -> (H, G, k)` + npz 缓存
   - `encode(info_bits) -> coded_bits(2048)`；`qpsk_map/…demap_llr(mu, var, scale) -> llr(2048)`
   - `decode_llr(H, llr, maxiter=50) -> (info_hat, ok)`（sum-product，syndrome 早停）
   - **验证**：`e1_ldpc_selftest.py` 纯本地单元测试——AWGN BPSK/QPSK 链路，rate 1/2 @ Eb/N0 2.5dB 译后 BER 明显低于译前；零噪声 roundtrip 精确恢复
2. `afdm_sp_joint_unrolled/e1_ldpc_coded_eval.py`：复制 paired_learned_eval 的主循环骨架（import 复用其 config/arm 构建函数，能 import 就不复制），改动：
   - 数据符号 = LDPC 码字（seed_fi 派生 info bits）
   - 每臂拿软后验（return_soft 路径）→ LLR → decode → info-bit errs
   - per-frame 数组 + `_argv`/`_config` 落 results.json
   - CLI 与 paired_learned_eval 对齐（--gateA-scorer geom|achievable 等），新增 --ldpc-seed
3. **验证**：本地 `python -m py_compile` 两个文件；selftest 本地跑通（只需 numpy/pyldpc 或纯自写 BP）
4. 远程 smoke（主会话做，不在本步）：2 帧 × 2 臂，OMP_NUM_THREADS=16（避让 E2）

## 回滚点

- 新文件独立，不改任何现有文件 → 回滚 = 删文件。若必须动 paired_learned_eval.py 才能复用（如函数不可 import），改为在 e1 脚本内复制所需函数并注明出处行号，仍不改原文件。
