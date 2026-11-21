#!/usr/bin/env python
"""Train the covariance-aware head MLP on cached (T_realiz/q_realiz + geom) feats.

v2: BCE(missed-atom label) + rank loss (per-frame pos>hard-neg margin) — the
head's job in F2-P is RANKING candidates, not just calibration, so the rank
term (the original loop9 head used it; covhead v1 dropped it) is the main lever
to reach/beat the analytical achievable-Λ. Frame-grouped via cached frame_id.

Deployed as an F2-P score_override (decision_gateA.make_covhead_scorer), so the
downstream is byte-identical to every other Gate A/B arm. Target: beat the
hand-tuned achievable-Λ. Ckpt stores state_dict + feat mean/std + arch dims.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn


class CovHeadMLP(nn.Module):
    def __init__(self, in_dim=8, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(),
            nn.Linear(hidden, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def _frame_groups(frame_id):
    order = np.argsort(frame_id, kind='stable')
    fids = frame_id[order]
    bounds = np.searchsorted(fids, np.unique(fids), side='left')
    groups = np.split(order, bounds[1:])
    return groups   # list of row-index arrays, one per frame


def _rank_loss(logit, y, margin=1.0):
    pos = logit[y > 0.5]
    neg = logit[y < 0.5]
    if pos.numel() == 0 or neg.numel() == 0:
        return logit.new_zeros(())
    neg_top = neg.max()
    return torch.nn.functional.softplus(neg_top - pos + margin).mean()


def recall_at_k(logit, y, snr, frac=0.05):
    out = {}
    for s in np.unique(snr):
        m = snr == s
        lg = logit[m]; yy = y[m]
        order = np.argsort(-lg)
        k = max(int(frac * len(order)), 1)
        out[int(s)] = round(float(yy[order[:k]].mean()), 4)
    return out


def run(cache, out, epochs, lr, wd, hidden, val_frac, lam_rank, seed):
    d = np.load(cache, allow_pickle=True)
    X = d['X'].astype(np.float64); Y = d['Y'].astype(np.float64)
    snr = d['snr']; fid = d['frame_id']
    groups = _frame_groups(fid)
    rng = np.random.default_rng(seed)
    gi = rng.permutation(len(groups))
    nval = int(val_frac * len(groups))
    val_g = [groups[i] for i in gi[:nval]]
    tr_g = [groups[i] for i in gi[nval:]]
    tr_rows = np.concatenate(tr_g); val_rows = np.concatenate(val_g)
    mu = X[tr_rows].mean(0); sd = X[tr_rows].std(0) + 1e-6
    Xn = (X - mu) / sd
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    Xt = torch.tensor(Xn, dtype=torch.float32, device=dev)
    Yt = torch.tensor(Y, dtype=torch.float32, device=dev)
    pos_w = torch.tensor([(Y[tr_rows] == 0).sum() / max((Y[tr_rows] == 1).sum(), 1)],
                         dtype=torch.float32, device=dev)
    model = CovHeadMLP(X.shape[1], hidden).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    bcef = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    g_tensors = [torch.tensor(g, device=dev) for g in tr_g]
    val_t = torch.tensor(val_rows, device=dev)
    fb = 128   # frames per minibatch
    print(f"[covhead-v2] dev={dev} frames={len(groups)} rows={len(Y)} "
          f"pos={int(Y.sum())} pos_w={float(pos_w):.1f} hidden={hidden} "
          f"lam_rank={lam_rank} feats={X.shape[1]}")
    for ep in range(epochs):
        model.train()
        order = torch.randperm(len(g_tensors))
        tb = tr_bce = tr_rk = 0.0
        for b in range(0, len(order), fb):
            opt.zero_grad()
            bce_acc = []; rk_acc = []
            for gi_ in order[b:b + fb]:
                rows = g_tensors[int(gi_)]
                lg = model(Xt[rows]); yy = Yt[rows]
                bce_acc.append(bcef(lg, yy))
                rk_acc.append(_rank_loss(lg, yy))
            bce = torch.stack(bce_acc).mean()
            rk = torch.stack(rk_acc).mean()
            loss = bce + lam_rank * rk
            loss.backward(); opt.step()
            tb += 1; tr_bce += float(bce); tr_rk += float(rk)
        sched.step()
        model.eval()
        with torch.no_grad():
            vl = float(bcef(model(Xt[val_t]), Yt[val_t]))
            lg = model(Xt[val_t]).cpu().numpy()
        rk = recall_at_k(lg, Y[val_rows], snr[val_rows])
        if ep % 5 == 0 or ep == epochs - 1:
            print(f"  ep{ep} bce={tr_bce/tb:.4f} rank={tr_rk/tb:.4f} "
                  f"val_bce={vl:.4f} top5%recall={rk}", flush=True)
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dict(state_dict=model.state_dict(), mean=mu, std=sd,
                    in_dim=X.shape[1], hidden=hidden,
                    feat_names=list(d['feat_names'])), str(out))
    print(f"[saved] {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--epochs', type=int, default=120)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--wd', type=float, default=1e-4)
    ap.add_argument('--hidden', type=int, default=64)
    ap.add_argument('--val-frac', type=float, default=0.2)
    ap.add_argument('--lam-rank', type=float, default=0.5)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()
    run(args.cache, args.out, args.epochs, args.lr, args.wd, args.hidden,
        args.val_frac, args.lam_rank, args.seed)


if __name__ == '__main__':
    main()
