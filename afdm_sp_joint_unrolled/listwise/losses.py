#!/usr/bin/env python
"""listwise/losses.py — listwise ranking losses for the C2-rel head.

The deployed receiver picks candidates by top-K_add ranking on the head's
logits: at inference, only the relative order of logits matters. The original
BCE + pairwise rank-hinge training objective optimizes pointwise probability
and a single hardest-pos vs hardest-neg margin -- neither directly aligns with
what deployment does.

This file provides two listwise alternatives that DO align:

  listnet_kl_loss     -- Cao 2007 ListNet, softmax-CE form. KL(target || pred)
                          where target = labels / sum(labels) (uniform mass over
                          positives) and pred = softmax(logits). 4-line core,
                          empirically strong as a starting point.

  soft_topk_recall_loss -- NeuralSort-relaxed Recall@K (Grover 2019 / Plackett-
                          Luce). For each frame, compute soft permutation
                          P_hat in (B, M, M); the top-K row sums give a soft
                          top-K indicator m in [0,1]^M; loss = BCE(m, labels).
                          As tau -> 0, m -> exact top-K indicator and the loss
                          becomes the deployment objective.

Both reduce per-frame and accept a frame_weight scalar matching the existing
loop9_train_c2rel.py weighting protocol (SNR balance + 2x for nonzero
classical BER frames).

Usage in train_listwise.py:
    from afdm_sp_joint_unrolled.listwise.losses import (
        listnet_kl_loss, soft_topk_recall_loss,
    )
    loss = listnet_kl_loss(logits, labels, frame_weight)
    # or:
    loss = soft_topk_recall_loss(logits, labels, k=4, tau=0.1,
                                  frame_weight=frame_weight)
    loss.backward()

Run as a script for the smoke test:
    python -m afdm_sp_joint_unrolled.listwise.losses
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def listnet_kl_loss(logits: torch.Tensor,
                    labels: torch.Tensor,
                    frame_weight: torch.Tensor | None = None,
                    eps: float = 1e-12) -> torch.Tensor:
    """ListNet listwise KL loss (Cao et al. 2007).

    logits : (B, M) real
    labels : (B, M) {0, 1} multi-hot
    frame_weight : (B,) per-frame nonnegative weight (default uniform 1).

    Frames with no positives are skipped (loss=0 contribution).
    """
    if frame_weight is None:
        frame_weight = torch.ones(logits.shape[0], device=logits.device,
                                   dtype=logits.dtype)
    label_sum = labels.sum(dim=-1).clamp_min(eps)            # (B,)
    target = labels / label_sum.unsqueeze(-1)                # (B, M)
    log_pred = F.log_softmax(logits, dim=-1)                 # (B, M)
    per_frame = -(target * log_pred).sum(dim=-1)             # (B,)
    valid = (label_sum > eps).float()                        # (B,)
    weighted = per_frame * frame_weight * valid
    denom = (frame_weight * valid).sum().clamp_min(eps)
    return weighted.sum() / denom


def neural_sort(scores: torch.Tensor, tau: float = 1.0) -> torch.Tensor:
    """NeuralSort soft permutation matrix (Grover et al. 2019).

    scores : (B, M)
    Returns P_hat : (B, M, M) where P_hat[b, k, j] is the (relaxed) probability
    that element j has rank k under descending sort of scores[b, :].
    Rows of P_hat are normalized via softmax with temperature tau.

    For tau -> 0, P_hat -> hard permutation. For tau -> inf, P_hat ->
    uniform (no signal).
    """
    B, M = scores.shape
    # |s_i - s_j| pairwise abs diff: (B, M, M)
    A_s = torch.abs(scores.unsqueeze(-1) - scores.unsqueeze(-2))
    one = torch.ones(M, 1, device=scores.device, dtype=scores.dtype)
    sum_abs = A_s @ one                                      # (B, M, 1)
    arange = torch.arange(M, device=scores.device, dtype=scores.dtype) + 1
    scaling = (M + 1 - 2 * arange)                           # (M,)
    # C[b, k, j] = (M+1-2k) * scores[b, j]. Want logits for "position k goes
    # to which j": logits_k_j = scaling[k] * scores[b, j] - sum_abs[b, j].
    logits_kj = scaling.view(1, -1, 1) * scores.unsqueeze(-2)   # (B, M, M)
    logits_kj = logits_kj - sum_abs.transpose(-1, -2)        # (B, M, M)
    return F.softmax(logits_kj / tau, dim=-1)


def soft_topk_recall_loss(logits: torch.Tensor,
                          labels: torch.Tensor,
                          k: int,
                          tau: float = 0.1,
                          frame_weight: torch.Tensor | None = None,
                          eps: float = 1e-12) -> torch.Tensor:
    """NeuralSort-relaxed Recall@K loss.

    Builds a soft top-K indicator m_j in [0, 1] via P_hat sum over rows 0..k-1,
    then BCE(m, labels) per frame.

    logits : (B, M)
    labels : (B, M) {0, 1}
    k : int, top-K size
    tau : NeuralSort temperature (smaller = sharper top-K but harder to optimize).
    """
    if frame_weight is None:
        frame_weight = torch.ones(logits.shape[0], device=logits.device,
                                   dtype=logits.dtype)
    P_hat = neural_sort(logits, tau=tau)                      # (B, M, M)
    soft_topk = P_hat[:, :k, :].sum(dim=-2).clamp(eps, 1.0 - eps)  # (B, M)
    bce = -(labels * torch.log(soft_topk) +
            (1.0 - labels) * torch.log(1.0 - soft_topk))     # (B, M)
    per_frame = bce.mean(dim=-1)                              # (B,)
    weighted = per_frame * frame_weight
    return weighted.sum() / frame_weight.sum().clamp_min(eps)


# --------------------------------------------------------------------- smoke
def _smoke():
    """Smoke test: gradient direction + tau-limit sanity."""
    torch.manual_seed(0)
    B, M, K = 4, 16, 3
    # Synthetic: positives at indices [0, 5, 10], negatives elsewhere
    labels = torch.zeros(B, M)
    labels[:, [0, 5, 10]] = 1
    # Initial logits: random
    logits = torch.randn(B, M, requires_grad=True)
    fw = torch.ones(B)

    # ListNet
    l_listnet = listnet_kl_loss(logits, labels, fw)
    g_listnet = torch.autograd.grad(l_listnet, logits, retain_graph=True)[0]
    # Gradient at positives should be NEGATIVE (loss decreases when logit goes up)
    grad_pos = g_listnet[:, [0, 5, 10]].mean().item()
    grad_neg = g_listnet[:, [1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15]].mean().item()
    print(f'ListNet: loss = {l_listnet.item():.4f}')
    print(f'  grad at positives  : {grad_pos:+.4f} (expect negative)')
    print(f'  grad at negatives  : {grad_neg:+.4f} (expect positive)')
    assert grad_pos < 0 and grad_neg > 0, 'ListNet gradient direction wrong'

    # SoftTopK Recall (tau=0.5)
    logits2 = torch.randn(B, M, requires_grad=True)
    l_topk = soft_topk_recall_loss(logits2, labels, k=K, tau=0.5,
                                    frame_weight=fw)
    g_topk = torch.autograd.grad(l_topk, logits2)[0]
    grad_pos2 = g_topk[:, [0, 5, 10]].mean().item()
    grad_neg2 = g_topk[:, [1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15]].mean().item()
    print(f'\nSoftTopK Recall (tau=0.5, k={K}): loss = {l_topk.item():.4f}')
    print(f'  grad at positives  : {grad_pos2:+.4f} (expect negative)')
    print(f'  grad at negatives  : {grad_neg2:+.4f} (expect positive)')
    assert grad_pos2 < 0 and grad_neg2 > 0, 'SoftTopK gradient direction wrong'

    # tau-limit: at very small tau, NeuralSort should be near-hard (top-K
    # mask close to 0/1).
    with torch.no_grad():
        s = torch.tensor([[5.0, 4.0, 3.0, 2.0, 1.0, 0.0]])
        for tau in (1.0, 0.1, 0.01):
            P = neural_sort(s, tau=tau)
            top3 = P[:, :3, :].sum(dim=-2).squeeze(0)
            print(f'\ntau={tau}: soft top-3 mask = {top3.numpy().round(3)}')
            # at small tau, expect mask ~= [1, 1, 1, 0, 0, 0]
        # Worst case (tau=0.01) should be sharp
        assert top3[0] > 0.95 and top3[5] < 0.05, 'tau-limit wrong'

    print('\nSMOKE OK')


if __name__ == '__main__':
    _smoke()
