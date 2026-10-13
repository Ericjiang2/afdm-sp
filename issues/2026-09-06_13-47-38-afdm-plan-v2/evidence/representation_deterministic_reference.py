"""Isolated observer check: deterministic final BP only, no production change.

The ordinary production on/off evidence is retained separately. This reference
removes the already diagnosed final scatter reduction variability so that soft
outputs can also be compared exactly. It is never a scientific trial replacement.
"""
import os
import sys
import torch
sys.path.insert(0, os.getcwd())  # Queue cwd is the hash-validated source snapshot.
from afdm_sp_joint_unrolled import budgeted_support_eval as runner

original = runner.final_bp


def deterministic_final(*args, **kwargs):
    previous = torch.are_deterministic_algorithms_enabled()
    warn = torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.use_deterministic_algorithms(True)
        return original(*args, **kwargs)
    finally:
        torch.use_deterministic_algorithms(previous, warn_only=warn)


if __name__ == '__main__':
    runner.final_bp = deterministic_final
    runner.main()
