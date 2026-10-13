"""Estimated-covariance adaptation of Li's public FSPAI reference algorithm.

Author source, commit 3a144fbe4dc92a607b3d1dca0868ebd270421f0a, and full
MIT license are retained in trans-next/research/di-s-mmse-author-source.
Geometry adjacency and candidate traversal differ; this is not an OTFS replay.

Copyright (c) 2023 Haotian Li
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to
do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import numpy as np
from scipy import sparse
from scipy.linalg import solve


def factorized_sparse_precision(H, variance, sigma2, *, graph_tol=.001,
                                degree_cutoff=3, max_added=8, selection_tol=.001):
    """Return C and lower sparse L with C^-1 approximately L L^H.

    H is the caller's estimated channel. SPD is provided by nonnegative
    symbol variances and strictly positive noise; no true path metadata is
    accepted. The author low-degree rule is retained literally. Candidate
    indices are sorted for deterministic ties, not OTFS geometry traversal.
    """
    H = sparse.csc_matrix(H, dtype=np.complex128, copy=True)
    H.sum_duplicates()
    H.eliminate_zeros()
    variance = np.asarray(variance)
    n = H.shape[0]
    if (n == 0 or H.shape[1] == 0 or variance.shape != (H.shape[1],)
            or np.iscomplexobj(variance) or not np.isfinite(variance).all()
            or np.any(variance < 0) or not np.isfinite(H.data).all()
            or isinstance(sigma2, (bool, np.bool_)) or not np.isscalar(sigma2)
            or np.iscomplexobj(sigma2) or not np.isfinite(sigma2) or sigma2 <= 0):
        raise ValueError('finite estimated H, nonnegative variances and positive noise required')
    if (type(degree_cutoff) is not int or degree_cutoff < 0
            or type(max_added) is not int or not 0 <= max_added < n
            or any(type(v) not in (int, float) or not np.isfinite(v) or v < 0
                   for v in (graph_tol, selection_tol))):
        raise ValueError('invalid FSPAI sparsification controls')
    C = (H@sparse.diags(variance.astype(float))@H.conj().T
         +float(sigma2)*sparse.eye(n, format='csc')).tocsc()
    C.sum_duplicates()
    C.eliminate_zeros()
    diagonal = C.diagonal()
    if (not np.isfinite(C.data).all() or np.any(diagonal.real <= 0)
            or np.any(abs(diagonal.imag) > 1e-12*np.maximum(1., diagonal.real))):
        raise FloatingPointError('constructed covariance lost positive real diagonal')
    diagonal = diagonal.real
    adjacency, before = [], 0
    for j in range(n):
        rows = C.indices[C.indptr[j]:C.indptr[j+1]]
        values = C.data[C.indptr[j]:C.indptr[j+1]]
        neighbors = sorted(int(i) for i, v in zip(rows, values)
                           if i != j and abs(v)/np.sqrt(diagonal[i]*diagonal[j]) > graph_tol)
        edges = [j]+neighbors
        before += len(edges)
        adjacency.append([j] if len(edges) <= degree_cutoff else edges)
    row_ids, col_ids, values, records = [], [], [], []
    small_solves = 0
    for j in range(n):
        selected = [j]
        column = np.array([1/np.sqrt(diagonal[j])], dtype=np.complex128)
        reason = 'column_budget'
        evaluated = 0
        while len(selected)-1 < max_added:
            candidates = sorted({i for k in selected for i in adjacency[k] if i > j and i not in selected})
            if not candidates:
                reason = 'empty_neighborhood'
                break
            sub = C[selected, :][:, candidates].toarray()
            eta = abs(sub.conj().T@column)**2/diagonal[j]
            evaluated += len(candidates)
            choice = int(np.argmax(eta))
            if eta[choice] <= selection_tol:
                reason = 'selection_tolerance'
                break
            selected.append(candidates[choice])
            off = selected[1:]
            rhs = C[off, j].toarray().ravel()
            solution = solve(C[off, :][:, off].toarray(), rhs, assume_a='pos', check_finite=True)
            small_solves += 1
            schur = diagonal[j]-np.vdot(rhs, solution)
            if (not np.isfinite(schur) or schur.real <= 0
                    or abs(schur.imag) > 1e-10*max(1., diagonal[j])):
                raise FloatingPointError('FSPAI column lost positive Schur complement')
            scale = 1/np.sqrt(schur.real)
            column = np.concatenate(([scale], -scale*solution))
        row_ids.extend(selected)
        col_ids.extend([j]*len(selected))
        values.extend(column)
        records.append(dict(column=j, added=len(selected)-1, candidate_evaluations=evaluated, stop=reason))
    L = sparse.csc_matrix((values, (row_ids, col_ids)), shape=(n, n))
    if not np.isfinite(L.data).all():
        raise FloatingPointError('nonfinite sparse precision factor')
    return dict(covariance=C, factor=L, columns=records, small_solves=small_solves,
        factor_nnz=L.nnz, covariance_nnz=C.nnz, graph_edges_before_prune=before,
        graph_edges_after_prune=sum(map(len, adjacency)),
        precision_semantics='L L^H; approximate except when qualified against exact solve',
        adjacency='estimated covariance support; sorted candidates; author low-degree pruning')
