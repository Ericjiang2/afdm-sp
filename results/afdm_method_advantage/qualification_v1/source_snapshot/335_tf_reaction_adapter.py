"""Source-bound, one-assignment TF reaction intervention; no source files edited.

This is an experimental reaction ablation, not a derivation of matrix AMP.
The caller must register the selected source SHA and include this adapter's SHA
in its receiver manifest. Dependency import paths belong to that caller.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import types


MODES = ("identity", "coherent", "full")
_ORIGINAL = "h + vq * (Bb.conj().T @ st - hb * sv * n * vx)"
_REACTIONS = {
    "coherent": "h + vq * (Bb.conj().T @ st - sv * n * vx * (o.R @ hb))",
    "full": "h + vq * (Bb.conj().T @ st - sv * (c.gamma(v) @ hb))",
}


def load_variant(source: str | Path, *, expected_sha256: str, mode: str):
    """Return a private module with a registered scalar_joint variant.

    The input source must expose the frozen scalar_joint loop. Both the complete
    SHA and the unique old reaction expression are checked before compilation.
    identity compiles the original source byte-for-byte, without an AST rewrite.
    Physical Channel, noise, damping, gain prior, all variance equations, data
    reaction, and stopping behavior stay exactly as supplied by that source.
    """
    if mode not in MODES:
        raise ValueError(f"unknown reaction mode: {mode!r}")
    path = Path(source)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"TF source SHA mismatch: expected {expected_sha256}, got {digest}")
    text = raw.decode("utf-8")
    tree = ast.parse(text, filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "scalar_joint"]
    if len(functions) != 1:
        raise ValueError("expected exactly one scalar_joint definition")
    targets = [node for node in ast.walk(functions[0])
               if isinstance(node, ast.Assign) and len(node.targets) == 1
               and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "rh"]
    expected = ast.parse(_ORIGINAL, mode="eval").body
    if len(targets) != 1 or ast.dump(targets[0].value) != ast.dump(expected):
        raise ValueError("frozen TF reaction expression is absent or ambiguous")
    if mode == "identity":
        code = compile(text, str(path), "exec")
    else:
        targets[0].value = ast.copy_location(
            ast.parse(_REACTIONS[mode], mode="eval").body, targets[0].value)
        ast.fix_missing_locations(tree)
        code = compile(tree, str(path), "exec")
    module = types.ModuleType(f"tf_reaction_{mode}")
    module.__file__ = str(path)
    exec(code, module.__dict__)
    module.reaction_contract = {
        "mode": mode,
        "source_sha256": digest,
        "changed_assignment_count": int(mode != "identity"),
        "working_covariance": "AF-domain diagonal v at iteration entry",
        "claim": "single gain-reaction intervention; not consistent matrix AMP",
    }
    return module
