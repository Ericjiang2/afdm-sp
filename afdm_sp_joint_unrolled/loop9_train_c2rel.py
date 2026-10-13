#!/usr/bin/env python
"""Loop 9 — train CandidateActiveRelationHead (C2-rel) on cached features.

Per Oracle R1 recipe:
  - Loss = BCE_miss(label) + 0.5 * rank_loss(pos_score > hard_neg_score)
  - SNR weights: 10/15/20 -> 0.2/0.4/0.4
  - Frame weight x2 if classical frame_ber > 0
  - AdamW lr=1e-3 wd=1e-4, batch=512 cached frames, 4 epochs
  - Early stop after 2 flat val evals
  - Train/val split 90/10 by frame

Input: cache directory with cache_snr{10,15,20}.pt produced by
       loop9_cache_features.py.
Output: <out>/ckpt_c2rel.pt, <out>/train_log.json, <out>/config.json
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    CandidateActiveRelationHead,
)


def _load_cache(cache_dir: Path):
    """Load per-SNR cache files. Return dicts keyed by snr -> tensors.

    SNR=25 is optional: loaded only if cache_snr25.pt exists (Loop-13 4B
    add-on for high-SNR regularisation).
    """
    caches = {}
    for snr in (10, 15, 20):
        fp = cache_dir / f'cache_snr{snr}.pt'
        if not fp.exists():
            raise FileNotFoundError(f'missing cache: {fp}')
        caches[snr] = torch.load(fp, weights_only=False)
    fp25 = cache_dir / 'cache_snr25.pt'
    if fp25.exists():
        caches[25] = torch.load(fp25, weights_only=False)
    return caches


def _make_snr_weights(snrs: np.ndarray) -> np.ndarray:
    """Per-frame SNR weight.

    With 3-SNR cache: 10->0.2, 15->0.4, 20->0.4 (original Oracle R1 recipe).
    With 4-SNR cache (includes 25): 10->0.2, 15->0.3, 20->0.3, 25->0.2
    (regularises high-SNR behaviour; SNR=25 has sparse positive signal so
    weight is kept small).
    """
    has_25 = bool((snrs == 25).any())
    w = np.zeros(len(snrs), dtype=np.float32)
    if has_25:
        w[snrs == 10] = 0.2
        w[snrs == 15] = 0.3
        w[snrs == 20] = 0.3
        w[snrs == 25] = 0.2
    else:
        w[snrs == 10] = 0.2
        w[snrs == 15] = 0.4
        w[snrs == 20] = 0.4
    return w


def _frame_weights(frame_ber: np.ndarray) -> np.ndarray:
    """x2 frame weight if classical frame BER > 0, else 1."""
    return np.where(frame_ber > 0, 2.0, 1.0).astype(np.float32)


def _pair_dataset(caches, split='train', train_frac=0.9, seed=13579):
    """Concatenate per-SNR caches, assign per-frame weights, split by frame.

    Returns (u, v, mask, y, y_soft, w_frame, snr):
        u: (N, M, 7), v: (N, M, P_pad, 6), mask: (N, M, P_pad) bool,
        y: (N, M) int8 (binary), y_soft: (N, M) float32 ([0,1] gain weights),
        w: (N,), snr: (N,)

    y_soft is zero-filled if cache predates the gain-weighted upgrade
    (backward-compat). Training uses y_soft only when --use-soft-labels is set.
    """
    rng = np.random.default_rng(seed)
    all_u = []; all_v = []; all_m = []; all_y = []; all_ysoft = []
    all_w = []; all_snr = []
    for snr, c in caches.items():
        n = int(c['n'])
        snr_w = _make_snr_weights(np.full(n, snr, dtype=int))
        fw = _frame_weights(c['frame_ber'].cpu().numpy())
        w = snr_w * fw
        all_u.append(c['u'].cpu().numpy())
        all_v.append(c['v'].cpu().numpy())
        all_m.append(c['mask'].cpu().numpy())
        all_y.append(c['y'].cpu().numpy())
        if 'y_soft' in c:
            all_ysoft.append(c['y_soft'].cpu().numpy())
        else:
            all_ysoft.append(np.zeros((n, c['y'].shape[1]), dtype=np.float32))
        all_w.append(w)
        all_snr.append(np.full(n, snr, dtype=np.int32))
    u = np.concatenate(all_u, axis=0)
    v = np.concatenate(all_v, axis=0)
    m = np.concatenate(all_m, axis=0)
    y = np.concatenate(all_y, axis=0)
    y_soft = np.concatenate(all_ysoft, axis=0)
    w = np.concatenate(all_w, axis=0)
    snr = np.concatenate(all_snr, axis=0)
    N = u.shape[0]
    perm = rng.permutation(N)
    n_tr = int(round(train_frac * N))
    if split == 'train':
        idx = perm[:n_tr]
    else:
        idx = perm[n_tr:]
    return (u[idx], v[idx], m[idx], y[idx], y_soft[idx], w[idx], snr[idx])


def _bce_miss_weighted(logits, labels, w_frame):
    """Weighted BCE over (batch, M) logits. w_frame shape (batch,)."""
    loss_per = nn.functional.binary_cross_entropy_with_logits(
        logits, labels.float(), reduction='none'
    )                                                              # (B, M)
    loss_per_frame = loss_per.mean(dim=1)                           # (B,)
    return (loss_per_frame * w_frame).mean()


def _rank_loss_weighted(logits, labels, w_frame, eps=1e-6):
    """For each frame with at least one positive and one negative:
        rank = mean_{j:y=0} softplus(hard_neg_score - max_pos_score + 1)
      We pick hard_neg = top logit among negatives; positive anchor =
      min logit among positives. Hinge-ish margin = 1.
    """
    B, M = logits.shape
    losses = []
    for b in range(B):
        pos_mask = labels[b] > 0
        if pos_mask.any() and (~pos_mask).any():
            pos_score = logits[b, pos_mask].min()            # hardest positive
            neg_score = logits[b, ~pos_mask].max()            # hardest negative
            margin = 1.0
            loss_b = torch.nn.functional.softplus(neg_score - pos_score + margin)
            losses.append(w_frame[b] * loss_b)
    if not losses:
        return torch.zeros((), device=logits.device, dtype=logits.dtype)
    return torch.stack(losses).mean()


def _eval_loss_and_recall(model, u, v, mask, y, w_frame, K_list=(2, 4, 6),
                          batch=512, device='cuda'):
    """Compute BCE loss + recall@K on a validation split."""
    model.eval()
    N = u.shape[0]
    total_bce = 0.0; total_w = 0.0
    rec_totals = {K: dict(correct=0, missed=0, hit=0, frames=0) for K in K_list}
    with torch.no_grad():
        for s in range(0, N, batch):
            e = min(N, s + batch)
            u_b = torch.from_numpy(u[s:e]).to(device)
            v_b = torch.from_numpy(v[s:e]).to(device)
            m_b = torch.from_numpy(mask[s:e]).to(device)
            y_b = torch.from_numpy(y[s:e]).to(device).long()
            wf_b = torch.from_numpy(w_frame[s:e]).to(device)
            logits = model.score(u_b, v_b, mask=m_b)                # (B, M)
            B = logits.shape[0]
            loss_per = nn.functional.binary_cross_entropy_with_logits(
                logits, y_b.float(), reduction='none'
            ).mean(dim=1)
            total_bce += (loss_per * wf_b).sum().item()
            total_w += wf_b.sum().item()

            # Recall@K per frame
            for K in K_list:
                # Higher logit = better
                Kk = min(K, logits.shape[1])
                top = torch.topk(logits, k=Kk, dim=1).indices         # (B, Kk)
                for bi in range(B):
                    missed_mask = (y_b[bi] > 0)
                    n_miss = int(missed_mask.sum().item())
                    if n_miss == 0:
                        continue
                    top_bi = top[bi]
                    hit_count = int(missed_mask[top_bi].sum().item())
                    rec_totals[K]['correct'] += hit_count
                    rec_totals[K]['missed'] += n_miss
                    rec_totals[K]['hit'] += 1 if hit_count > 0 else 0
                    rec_totals[K]['frames'] += 1
    bce = total_bce / max(total_w, 1e-30)
    rec = {}
    for K, d in rec_totals.items():
        rec[str(K)] = dict(
            recall=(d['correct'] / max(d['missed'], 1)) if d['frames'] else 0.0,
            hit_any=(d['hit'] / max(d['frames'], 1)) if d['frames'] else 0.0,
            n_frames=d['frames'],
        )
    return dict(bce=bce, recall=rec)


def train_one_epoch(model, u_tr, v_tr, m_tr, y_tr, w_tr, optim, device,
                    batch=512, rank_weight=0.5, soft_labels=False):
    """Train one epoch. If soft_labels=True, y_tr is float32 in [0,1] (gain-
    weighted soft targets); BCE accepts continuous targets natively. Otherwise
    y_tr is int8 binary (default behaviour preserved)."""
    model.train()
    N = u_tr.shape[0]
    perm = np.random.permutation(N)
    total = 0.0; steps = 0
    for s in range(0, N, batch):
        idx = perm[s:s+batch]
        u_b = torch.from_numpy(u_tr[idx]).to(device)
        v_b = torch.from_numpy(v_tr[idx]).to(device)
        m_b = torch.from_numpy(m_tr[idx]).to(device)
        if soft_labels:
            y_b = torch.from_numpy(y_tr[idx]).to(device).float()
        else:
            y_b = torch.from_numpy(y_tr[idx]).to(device).long()
        wf_b = torch.from_numpy(w_tr[idx]).to(device)

        logits = model.score(u_b, v_b, mask=m_b)                    # (B, M)

        bce = _bce_miss_weighted(logits, y_b, wf_b)
        rank = _rank_loss_weighted(logits, y_b, wf_b)
        loss = bce + float(rank_weight) * rank
        optim.zero_grad()
        loss.backward()
        # Gradient clip for stability
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optim.step()
        total += loss.item()
        steps += 1
    return total / max(steps, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--wd', type=float, default=1e-4)
    ap.add_argument('--batch', type=int, default=512)
    ap.add_argument('--epochs', type=int, default=4)
    ap.add_argument('--rank-weight', type=float, default=0.5)
    ap.add_argument('--patience', type=int, default=2)
    ap.add_argument('--k-add-max', type=int, default=4)
    ap.add_argument('--train-frac', type=float, default=0.9)
    ap.add_argument('--seed', type=int, default=13579)
    ap.add_argument('--device', type=str, default='auto')
    ap.add_argument('--feature-mask', type=str, default='all',
                    choices=['all', 'no-residual-mf', 'no-pair-coh'],
                    help='Feature ablation. "all" (default) = canonical; '
                         '"no-residual-mf" zeros u[:,:,0:2] (log_mf, margin); '
                         '"no-pair-coh" zeros v[:,:,:,0:2] (coh, log_alpha_coh).'
                         ' Step 3 ablation B-reduced.')
    ap.add_argument('--use-soft-labels', action='store_true',
                    help='Use gain-weighted soft labels (cache field y_soft) '
                         'instead of binary y. y_soft is per-cand-atom |gain| '
                         'normalised to max-per-frame, range [0, 1]. Cache '
                         'must include y_soft (rebuild via loop9_cache_features.py'
                         ' 2026-05-09 onward).')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    device = ('cuda' if torch.cuda.is_available() else 'cpu') \
              if args.device == 'auto' else args.device
    print(f'[train_c2rel] device={device}  cache_dir={args.cache_dir}  '
          f'out={args.out}  lr={args.lr}  batch={args.batch}  '
          f'epochs={args.epochs}  rank_w={args.rank_weight}  '
          f'patience={args.patience}  seed={args.seed}', flush=True)

    caches = _load_cache(Path(args.cache_dir))
    totals = {snr: int(c['n']) for snr, c in caches.items()}
    print(f'[train_c2rel] cache sizes: {totals}', flush=True)

    # Frame-level split
    u_tr, v_tr, m_tr, y_tr, ysoft_tr, w_tr, snr_tr = _pair_dataset(
        caches, split='train', train_frac=args.train_frac, seed=args.seed)
    u_va, v_va, m_va, y_va, ysoft_va, w_va, snr_va = _pair_dataset(
        caches, split='val',   train_frac=args.train_frac, seed=args.seed)
    # If --use-soft-labels enabled, replace y with y_soft (which is in [0,1]
    # range; zero where binary y is zero, gain-magnitude-normalized where y=1).
    # BCE-with-logits accepts continuous targets natively.
    if args.use_soft_labels:
        # Validate: y_soft cache field must be non-zero somewhere
        if not (ysoft_tr.max() > 0):
            raise RuntimeError(
                'cache y_soft is all zeros — re-cache with the gain-weighted '
                'patch (loop9_cache_features.py 2026-05-09 onward) before '
                'using --use-soft-labels.')
        print(f'[soft-labels] using y_soft (max={ysoft_tr.max():.3f}, '
              f'mean={ysoft_tr.mean():.5f}, frac_pos='
              f'{(ysoft_tr > 0).mean():.5f})', flush=True)
        y_tr_train = ysoft_tr
        y_va_train = ysoft_va
    else:
        y_tr_train = y_tr.astype(np.float32)
        y_va_train = y_va.astype(np.float32)
    # Feature ablation (Step 3 B-reduced): zero out specific feature dims so
    # the head learns to ignore them. u[:,:,0:2] = (log_mf, margin) — residual
    # matched-filter features. v[:,:,:,0:2] = (coh, log_alpha_coh) — pair-
    # coherence features. Other dims (delays, Doppler, indicators) preserved.
    if args.feature_mask == 'no-residual-mf':
        u_tr[:, :, 0:2] = 0.0
        u_va[:, :, 0:2] = 0.0
        print('[feature-mask] no-residual-mf: zeroed u[:,:,0:2] (log_mf, margin)', flush=True)
    elif args.feature_mask == 'no-pair-coh':
        v_tr[:, :, :, 0:2] = 0.0
        v_va[:, :, :, 0:2] = 0.0
        print('[feature-mask] no-pair-coh: zeroed v[:,:,:,0:2] (coh, log_alpha_coh)', flush=True)
    print(f'[train_c2rel] train frames={len(u_tr)}  val frames={len(u_va)}  '
          f'P_pad={u_tr.shape[1] and v_tr.shape[2]}', flush=True)

    np.random.seed(args.seed); torch.manual_seed(args.seed)
    model = CandidateActiveRelationHead(top_m=u_tr.shape[1],
                                          k_add_max=args.k_add_max).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f'[train_c2rel] model params: {n_params}', flush=True)

    optim = torch.optim.AdamW(model.parameters(), lr=args.lr,
                                weight_decay=args.wd)
    best_bce = float('inf'); best_epoch = -1
    best_state = None; flat_count = 0
    log = []
    t0 = time.time()
    # Initial (pre-train) val
    pre = _eval_loss_and_recall(model, u_va, v_va, m_va, y_va, w_va,
                                 batch=args.batch, device=device)
    print(f'[pre-train] val_bce={pre["bce"]:.5f}  '
          f'recall@4={pre["recall"]["4"]["recall"]:.3f}  '
          f'recall@6={pre["recall"]["6"]["recall"]:.3f}  '
          f'hit@6={pre["recall"]["6"]["hit_any"]:.3f}', flush=True)
    log.append(dict(epoch=0, train_loss=None, **pre))

    for ep in range(1, args.epochs + 1):
        tr_loss = train_one_epoch(model, u_tr, v_tr, m_tr, y_tr_train, w_tr,
                                    optim, device, batch=args.batch,
                                    rank_weight=args.rank_weight,
                                    soft_labels=bool(args.use_soft_labels))
        val = _eval_loss_and_recall(model, u_va, v_va, m_va, y_va, w_va,
                                      batch=args.batch, device=device)
        dt = time.time() - t0
        r6 = val['recall']['6']
        print(f'[ep={ep:2d} t={dt:.0f}s] train_loss={tr_loss:.5f}  '
              f'val_bce={val["bce"]:.5f}  '
              f'r@2={val["recall"]["2"]["recall"]:.3f}  '
              f'r@4={val["recall"]["4"]["recall"]:.3f}  '
              f'r@6={r6["recall"]:.3f}  hit@6={r6["hit_any"]:.3f}',
              flush=True)
        log.append(dict(epoch=ep, train_loss=tr_loss, **val))

        if val['bce'] < best_bce - 1e-5:
            best_bce = val['bce']; best_epoch = ep
            best_state = {k: v.clone().cpu() for k, v in
                          model.state_dict().items()}
            flat_count = 0
        else:
            flat_count += 1
            if flat_count >= args.patience:
                print(f'[train_c2rel] Early stop at ep={ep} '
                      f'(flat_count={flat_count} >= patience={args.patience})',
                      flush=True)
                break

    if best_state is None:
        best_state = {k: v.clone().cpu() for k, v in model.state_dict().items()}
        best_epoch = args.epochs

    ckpt = dict(
        state_dict=best_state,
        best_epoch=int(best_epoch), best_bce=float(best_bce),
        args=vars(args),
        head_class='CandidateActiveRelationHead',
        head_config=dict(top_m=u_tr.shape[1], k_add_max=args.k_add_max),
    )
    ckpt_path = Path(args.out) / 'ckpt_c2rel.pt'
    torch.save(ckpt, ckpt_path)
    (Path(args.out) / 'train_log.json').write_text(json.dumps(log, indent=2))
    print(f'[train_c2rel] saved best ckpt -> {ckpt_path}  '
          f'best_epoch={best_epoch}  best_bce={best_bce:.5f}', flush=True)


if __name__ == '__main__':
    main()
