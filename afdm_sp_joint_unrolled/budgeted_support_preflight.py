"""Small numerical environment probe; CUDA is required unless CPU is explicit.

This validates the selected device, not the receiver or its performance. Output
is immutable: use a new path for every invocation, including failed attempts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import torch


def probe(device: str) -> dict:
    if device not in ('cpu', 'cuda'):
        raise ValueError(f'Unsupported device: {device}')
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA is required but torch.cuda.is_available() is False')
    result = {
        'device': device, 'python': sys.version, 'executable': sys.executable,
        'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
        'hostname': platform.node(), 'platform': platform.platform(),
        'cpu_threads': torch.get_num_threads(),
        'omp_num_threads': os.environ.get('OMP_NUM_THREADS'),
        'validation_scope': 'device linear algebra only; receiver not validated',
        'checks': [],
    }
    if device == 'cuda':
        smi = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu',
             '--format=csv,noheader'], check=True, capture_output=True, text=True,
        )
        result['nvidia_smi_before'] = smi.stdout.strip()
        result['gpu_name'] = torch.cuda.get_device_name(0)
        torch.cuda.reset_peak_memory_stats()

    rng = torch.Generator(device='cpu').manual_seed(20260905)
    source = torch.randn((32, 32), generator=rng, dtype=torch.complex128)
    a0 = source @ source.mH + 32 * torch.eye(32, dtype=torch.complex128)
    b0 = torch.randn((32, 4), generator=rng, dtype=torch.complex128)
    for dtype, tolerance in [(torch.complex128, 1e-10), (torch.complex64, 1e-4)]:
        a, b = a0.to(dtype=dtype, device=device), b0.to(dtype=dtype, device=device)
        reference_a, reference_b = a.cpu().to(torch.complex128), b.cpu().to(torch.complex128)
        reference_x = torch.linalg.solve(reference_a, reference_b)
        if device == 'cuda':
            torch.cuda.synchronize()
        started = time.perf_counter()
        product = a @ b
        x = torch.linalg.solve(a, b)
        if device == 'cuda':
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        residual = float((torch.linalg.vector_norm(a @ x - b) / torch.linalg.vector_norm(b)).cpu())
        error = float(torch.linalg.vector_norm(x.cpu().to(torch.complex128) - reference_x) / torch.linalg.vector_norm(reference_x))
        product_ref = reference_a @ reference_b
        product_error = float(torch.linalg.vector_norm(product.cpu().to(torch.complex128) - product_ref) / torch.linalg.vector_norm(product_ref))
        passed = bool(torch.isfinite(x).all().cpu()) and max(residual, error, product_error) <= tolerance
        result['checks'].append({
            'dtype': str(dtype), 'tensor_device': str(x.device),
            'relative_residual': residual, 'relative_solution_error': error,
            'relative_matmul_error': product_error, 'tolerance': tolerance,
            'seconds': elapsed, 'passed': passed,
        })
    if device == 'cuda':
        result['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
    result['passed'] = all(check['passed'] for check in result['checks'])
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        result = {'started_at': datetime.now(timezone.utc).isoformat()}
        try:
            result.update(probe(args.device))
        except Exception as error:
            result.update(passed=False, device=args.device,
                          error_type=type(error).__name__, error=str(error))
            json.dump(result, handle, indent=2)
            handle.write('\n')
            print(f'{type(error).__name__}: {error}', file=sys.stderr)
            return 1
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
