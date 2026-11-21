# Implement — 10-16-tcom-channel-crb

1. [ ] `crb.py` + 本地 gate G2、G3、G4、G5、G5b → `out/gates_local/`。
2. [ ] deinlab：G1、G7、G8 + 20 帧 G6 + 单格计时 → `out/gates_remote/`；commit "before CRB run"。
3. [ ] deinlab 正式运行（tmux `g_crb`，≤ 30 分片），G6 全量核对；rows gzip + md5；回传小文件；commit "after CRB run"。
4. [ ] `crb_agg.py` → `out/analysis/{CRB_RESULTS.md, crb_results.json}`；draft 卡；STATE + index；commit。
回滚点：任一 gate 不过即停，报告用户，不改协议。
