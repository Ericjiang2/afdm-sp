#!/usr/bin/env python
"""train_listwise.py — fork of loop9_train_c2rel with listwise loss substitution.

Same cache I/O, same dataset split, same eval (BCE + recall@K),
same checkpoint format. Only the per-batch loss is swapped:

  --loss listnet       Cao 2007 ListNet (default)
  --loss soft_topk     NeuralSort-relaxed Recall@K

Multi-seed orchestration: pass --seed for each run; checkpoints land in
distinct --out dirs. A driver script (run_listwise_5seed.sh) sweeps seeds.

Usage:
    python afdm_sp_joint_unrolled/listwise/train_listwise.py \
        --cache-dir afdm_sp_joint_unrolled/outputs_loop9_c2rel_cache \
        --out afdm_sp_joint_unrolled/outputs_listwise_seed20260507/ \
        --loss listnet --epochs 8 --seed 20260507
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import numpy as np
import torch

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    CandidateActiveRelationHead,
)
from afdm_sp_joint_unrolled.listwise.losses import (
    listnet_kl_loss,
    soft_topk_recall_loss,
)
from afdm_sp_joint_unrolled.loop9_train_c2rel import (
    _eval_loss_and_recall,
    _load_cache,
    _pair_dataset,
)


def train_one_epoch_listwise(model, u_tr, v_tr, m_tr, y_tr, w_tr,
                              optim, device, loss_name, loss_kwargs,
                              batch=512):
    model.train()
    N = u_tr.shape[0]
    perm = np.random.permutation(N)
    total = 0.0; steps = 0
    for s in range(0, N, batch):
        idx = perm[s:s + batch]
        u_b = torch.from_numpy(u_tr[idx]).to(device)
        v_b = torch.from_numpy(v_tr[idx]).to(device)
        m_b = torch.from_numpy(m_tr[idx]).to(device)
        y_b = torch.from_numpy(y_tr[idx]).to(device).float()
        wf_b = torch.from_numpy(w_tr[idx]).to(device)

        logits = model.score(u_b, v_b, mask=m_b)              # (B, M)

        if loss_name == 'listnet':
            loss = listnet_kl_loss(logits, y_b, wf_b)
        elif loss_name == 'soft_topk':
            loss = soft_topk_recall_loss(
                logits, y_b,
                k=int(loss_kwargs['k']),
                tau=float(loss_kwargs['tau']),
                frame_weight=wf_b,
            )
        else:
            raise ValueError(f'unknown --loss: {loss_name}')

        optim.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optim.step()
        total += loss.item()
        steps += 1
    return total / max(steps, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--loss', choices=['listnet', 'soft_topk'], default='listnet')
    ap.add_argument('--topk', type=int, default=4,
                    help='K for --loss soft_topk')
    ap.add_argument('--tau', type=float, default=0.1,
                    help='NeuralSort temperature for --loss soft_topk')
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--wd', type=float, default=1e-4)
    ap.add_argument('--batch', type=int, default=512)
    ap.add_argument('--epochs', type=int, default=8)
    ap.add_argument('--patience', type=int, default=3)
    ap.add_argument('--k-add-max', type=int, default=4)
    ap.add_argument('--train-frac', type=float, default=0.9)
    ap.add_argument('--seed', type=int, default=20260507)
    ap.add_argument('--device', type=str, default='auto')
    ap.add_argument('--pair-hidden', type=int, default=16,
                    help='Pair-MLP hidden width (default 16 = canonical 1041-param head). '
                         '64 → ~10K-param head for axis B3 capacity test.')
    ap.add_argument('--scorer-hidden', type=int, default=16,
                    help='Scorer-MLP hidden width (default 16 = canonical).')
    args = ap.parse_args()

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    device = (('cuda' if torch.cuda.is_available() else 'cpu')
              if args.device == 'auto' else args.device)
    print(f'[train_listwise] device={device}  loss={args.loss}  '
          f'epochs={args.epochs}  seed={args.seed}  out={args.out}', flush=True)

    caches = _load_cache(pathlib.Path(args.cache_dir))
    print(f'[train_listwise] cache sizes: {{snr: c["n"] for snr, c in '
          f'caches.items()}}: '
          f'{ {snr: int(c["n"]) for snr, c in caches.items()} }', flush=True)

    u_tr, v_tr, m_tr, y_tr, w_tr, snr_tr = _pair_dataset(
        caches, split='train', train_frac=args.train_frac, seed=args.seed)
    u_va, v_va, m_va, y_va, w_va, snr_va = _pair_dataset(
        caches, split='val',   train_frac=args.train_frac, seed=args.seed)
    print(f'[train_listwise] train frames={len(u_tr)}  '
          f'val frames={len(u_va)}', flush=True)

    np.random.seed(args.seed); torch.manual_seed(args.seed)
    if device == 'cuda':
        torch.cuda.manual_seed_all(args.seed)
    model = CandidateActiveRelationHead(
        top_m=u_tr.shape[1], k_add_max=args.k_add_max,
        pair_hidden=args.pair_hidden, scorer_hidden=args.scorer_hidden).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f'[train_listwise] model params: {n_params}', flush=True)

    optim = torch.optim.AdamW(model.parameters(), lr=args.lr,
                               weight_decay=args.wd)
    best_bce = float('inf'); best_epoch = -1
    best_state = None; flat_count = 0
    log = []
    pre = _eval_loss_and_recall(model, u_va, v_va, m_va, y_va, w_va,
                                 batch=args.batch, device=device)
    print(f'[pre-train] val_bce={pre["bce"]:.5f}  '
          f'r@4={pre["recall"]["4"]["recall"]:.3f}  '
          f'r@6={pre["recall"]["6"]["recall"]:.3f}', flush=True)
    log.append(dict(epoch=0, train_loss=None, **pre))

    loss_kwargs = dict(k=args.topk, tau=args.tau)
    t0 = time.time()
    for ep in range(1, args.epochs + 1):
        tr = train_one_epoch_listwise(
            model, u_tr, v_tr, m_tr, y_tr, w_tr, optim, device,
            args.loss, loss_kwargs, batch=args.batch)
        val = _eval_loss_and_recall(model, u_va, v_va, m_va, y_va, w_va,
                                     batch=args.batch, device=device)
        dt = time.time() - t0
        print(f'[ep={ep:2d} t={dt:.0f}s] tr={tr:.5f}  '
              f'val_bce={val["bce"]:.5f}  '
              f'r@2={val["recall"]["2"]["recall"]:.3f}  '
              f'r@4={val["recall"]["4"]["recall"]:.3f}  '
              f'r@6={val["recall"]["6"]["recall"]:.3f}', flush=True)
        log.append(dict(epoch=ep, train_loss=tr, **val))
        if val['bce'] < best_bce - 1e-5:
            best_bce = val['bce']; best_epoch = ep
            best_state = {k: v.clone().cpu() for k, v in
                          model.state_dict().items()}
            flat_count = 0
        else:
            flat_count += 1
            if flat_count >= args.patience:
                print(f'[train_listwise] early stop ep={ep}', flush=True)
                break

    if best_state is None:
        best_state = {k: v.clone().cpu() for k, v in model.state_dict().items()}
        best_epoch = args.epochs

    # paired_learned_eval.py loads into ClassicalJointUnrolled, which has the
    # head as a submodule keyed under 'cand_active_rel.'. Prefix the keys so
    # the listwise ckpt is a drop-in replacement for ckpt_c2rel_force_topk.pt.
    best_state_prefixed = {f'cand_active_rel.{k}': v
                            for k, v in best_state.items()}

    ckpt = dict(
        state_dict=best_state_prefixed, best_epoch=int(best_epoch),
        best_bce=float(best_bce), args=vars(args),
        head_class='CandidateActiveRelationHead',
        head_config=dict(top_m=u_tr.shape[1], k_add_max=args.k_add_max,
                         pair_hidden=args.pair_hidden,
                         scorer_hidden=args.scorer_hidden),
        loss_used=args.loss,
    )
    ckpt_path = out / 'ckpt_listwise.pt'
    torch.save(ckpt, ckpt_path)
    (out / 'train_log.json').write_text(json.dumps(log, indent=2))
    print(f'[done] saved -> {ckpt_path}  best_epoch={best_epoch}  '
          f'best_bce={best_bce:.5f}', flush=True)


if __name__ == '__main__':
    main()
