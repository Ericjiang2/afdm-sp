# CORE-02 A0真实绕过

forward(enable_support_repair=False)在候选feature/refinement之前跳过完整分支，拒绝非bool开关。新增可选a0 arm，默认旧arm列表不变；纯A0不构建host OMP、H0或scorer，混合批次A0独立成本不归入其他臂的scorer准备。旧keep仍保留“运行后覆盖”诊断语义。

失败复现：旧forward对enable_support_repair报TypeError；旧run_frame触发unused host OMP断言。修复后无head参考与A0实际CPU forward的H/x/gain/sigma一致；真实CPU runner+末次BP经过N16合成IID输入，host OMP/H0/scorer均被禁止调用。此fixture未跑LDPC，不是GPU/coded E2E。

MPLCONFIGDIR=/tmp/afdm-v2-mpl /opt/anaconda3/bin/python -m unittest afdm_sp_joint_unrolled.test_no_repair afdm_sp_joint_unrolled.test_budgeted_support_eval afdm_sp_joint_unrolled.test_direct_capacity：9项通过，Ran 9 tests in 0.031s，exit0（exec session15642）。同批py_compile对classical_joint_unrolled.py、budgeted_support_eval.py、test_no_repair.py通过。

本次提交接收机绕过增量、新runner消费者及其既有diagnostics模块依赖，保留原模块行为；未改变仿真器、噪声更新、LDPC或生成数据规则。WIRE-01负责新壳CLI/prior配置传递，RUN-02负责真实GPU/LDPC回放，尚未代签。
