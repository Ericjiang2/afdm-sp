"""AST-whitelisted 0..197 prefix of the frozen Stage-B producer.

This module contains no receiver implementation. It executes the hash-bound
original producer with only the enumerated prefix/budget/result-label edits.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import signal


ORIGINAL_SHA = "fc1ed8087533f916d5892764f1a04d15168bf52c37ec4f83178de773ab7c1566"
STAGE_B_MANIFEST_SHA = "3de51a884015d39deec052efd932e92cd40e0e951b4ea6b76c8eb090acafd85b"
DIAGNOSTIC_SCHEMA = "cstate-necessity-stage-b-prefix-diagnostic/1"
FRAME_COUNT = 198
CALL_LIMIT = 409
PATCH_NAMES = ("manifest_label_budget", "prefix_slice", "attempt_cap",
               "final_count", "diagnostic_completion")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _keyword(call: ast.Call, name: str) -> ast.keyword:
    matched = [keyword for keyword in call.keywords if keyword.arg == name]
    if len(matched) != 1:
        raise ValueError(f"frozen producer keyword {name} differs")
    return matched[0]


def _constant(keyword: ast.keyword, expected: object, replacement: object) -> None:
    if not isinstance(keyword.value, ast.Constant) or keyword.value.value != expected:
        raise ValueError(f"frozen producer value {keyword.arg} differs")
    keyword.value = ast.Constant(replacement)


def _call_at(function: ast.FunctionDef, line: int) -> ast.Call:
    matches = [node.value for node in ast.walk(function)
               if isinstance(node, ast.Expr) and node.lineno == line
               and isinstance(node.value, ast.Call)]
    if len(matches) != 1 or not isinstance(matches[0].func, ast.Name) or \
            matches[0].func.id != "write_json_exclusive":
        raise ValueError(f"frozen producer write at line {line} differs")
    return matches[0]


def _write_call(function: ast.FunctionDef, line: int, filename: str) -> tuple[ast.Call, ast.Call]:
    call = _call_at(function, line)
    if len(call.args) != 2 or not isinstance(call.args[0], ast.BinOp) or \
            not isinstance(call.args[0].op, ast.Div) or \
            not isinstance(call.args[0].right, ast.Constant) or \
            call.args[0].right.value != filename or \
            not isinstance(call.args[1], ast.Call) or \
            not isinstance(call.args[1].func, ast.Name) or call.args[1].func.id != "dict":
        raise ValueError(f"frozen producer output at line {line} differs")
    return call, call.args[1]


def rewrite(original: bytes) -> tuple[ast.Module, dict]:
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA:
        raise ValueError("original Stage-B producer SHA differs")
    tree = ast.parse(original.decode(), filename="f1_run_stage_b.py")
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "run"]
    if len(functions) != 1:
        raise ValueError("frozen run function inventory differs")
    function = functions[0]

    _, manifest = _write_call(function, 193, "manifest.json")
    schema = _keyword(manifest, "schema")
    if not isinstance(schema.value, ast.Name) or schema.value.id != "SCHEMA":
        raise ValueError("frozen running schema differs")
    schema.value = ast.Constant(DIAGNOSTIC_SCHEMA)
    _constant(_keyword(manifest, "expected_calls"), 2112, CALL_LIMIT)
    _constant(_keyword(manifest, "reference_subset"),
              "frame_index%16==0 (64 IDs)", "frame_index%16==0 (13 IDs among 0..197)")
    manifest.keywords.append(ast.keyword(arg="diagnostic_manifest_sha256",
        value=ast.Attribute(value=ast.Name(id="args", ctx=ast.Load()),
                            attr="diagnostic_manifest_sha256", ctx=ast.Load())))

    loops = [node for node in ast.walk(function) if isinstance(node, ast.For)
             and node.lineno == 214]
    if len(loops) != 1 or ast.unparse(loops[0].iter) != "enumerate(bound['selected'])":
        raise ValueError("frozen population loop differs")
    loops[0].iter = ast.parse("enumerate(bound['selected'][:198])", mode="eval").body

    for line, label in ((219, "attempt cap"), (381, "final count")):
        conditions = [node for node in ast.walk(function) if isinstance(node, ast.If)
                      and node.lineno == line]
        if len(conditions) != 1 or not isinstance(conditions[0].test, ast.Compare):
            raise ValueError(f"frozen {label} differs")
        condition = conditions[0].test
        if (len(condition.comparators) != 1 or
                not isinstance(condition.left, ast.Name) or condition.left.id != "calls" or
                not isinstance(condition.comparators[0], ast.Constant) or
                condition.comparators[0].value != 2112 or
                len(condition.ops) != 1 or
                type(condition.ops[0]) is not (ast.Gt if line == 219 else ast.NotEq)):
            raise ValueError(f"frozen {label} expression differs")
        condition.comparators[0] = ast.Constant(CALL_LIMIT)

    complete, completion = _write_call(function, 385, "observed_seal.json")
    complete.args[0].right = ast.Constant("diagnostic_prefix.json")
    finish_schema = _keyword(completion, "schema")
    if not isinstance(finish_schema.value, ast.Name) or finish_schema.value.id != "SCHEMA":
        raise ValueError("frozen completion schema differs")
    finish_schema.value = ast.Constant(DIAGNOSTIC_SCHEMA)
    for name, before, after in (("status", "pass", "diagnostic-prefix"),
                                ("observations", 1024, FRAME_COUNT),
                                ("calls", 2112, CALL_LIMIT),
                                ("reference_subset_calls", 64, 13)):
        _constant(_keyword(completion, name), before, after)
    completion.keywords.append(ast.keyword(arg="diagnostic_manifest_sha256",
        value=ast.Attribute(value=ast.Name(id="args", ctx=ast.Load()),
                            attr="diagnostic_manifest_sha256", ctx=ast.Load())))

    ast.fix_missing_locations(tree)
    return tree, {"patches": list(PATCH_NAMES), "frames": FRAME_COUNT,
                  "maximum_attempts": CALL_LIMIT, "reference_subset": 13,
                  "source_sha256": ORIGINAL_SHA,
                  "rewritten_ast_sha256": hashlib.sha256(ast.dump(tree).encode()).hexdigest(),
                  "population_seal_written": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--diagnostic-manifest", type=Path)
    parser.add_argument("--diagnostic-manifest-sha256")
    parser.add_argument("--registration-commit")
    for name in ("registration", "protocol", "stage-a-registration",
                 "stage-a-observed", "population-observed", "source", "baseline", "out"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--seconds-limit", type=float)
    args = parser.parse_args()
    original = Path(__file__).resolve().parents[1] / \
        "cstate_necessity_stageB_20260928/f1_run_stage_b.py"
    tree, audit = rewrite(original.read_bytes())
    if args.audit_only:
        print(json.dumps(audit, sort_keys=True))
        return
    if any(getattr(args, name.replace("-", "_")) is None for name in
           ("diagnostic-manifest", "diagnostic-manifest-sha256", "registration-commit",
            "registration", "protocol", "stage-a-registration", "stage-a-observed",
            "population-observed", "source", "baseline", "out", "seconds-limit")):
        parser.error("all frozen production arguments are required")
    if (args.seconds_limit != 2400.0 or
            not re.fullmatch(r"[0-9a-f]{40}", args.registration_commit)):
        raise ValueError("frozen Stage-B registration/time interface differs")
    if (sha(args.registration) != STAGE_B_MANIFEST_SHA or
            sha(args.diagnostic_manifest) != args.diagnostic_manifest_sha256):
        raise ValueError("old/new diagnostic registration SHA differs")
    manifest = json.loads(args.diagnostic_manifest.read_text())
    if (manifest.get("schema") != DIAGNOSTIC_SCHEMA or manifest.get("status") != "locked"
            or manifest.get("original_registration_commit") != args.registration_commit
            or manifest.get("original_registration_sha256") != STAGE_B_MANIFEST_SHA
            or manifest.get("original_runner_sha256") != ORIGINAL_SHA
            or manifest.get("adapter_sha256") != sha(Path(__file__))
            or manifest.get("patches") != audit["patches"]
            or manifest.get("maximum_attempts") != CALL_LIMIT
            or manifest.get("hard_wall_seconds") != 300):
        raise ValueError("diagnostic registration differs from audited AST/budget")
    expected_out = Path("/data/guoyikun/00inbox/AFDM-channel-estimation/results/"
                        "cstate_necessity_stageB_resume_20260928/prefix_history_v1")
    if args.out.exists() or args.out.resolve() != expected_out:
        raise ValueError("diagnostic output must be the new fixed prefix root")
    namespace = {"__name__": "stage_b_prefix_diagnostic", "__file__": str(original)}
    exec(compile(tree, str(original), "exec"), namespace)
    signal.signal(signal.SIGALRM,
                  lambda *_: (_ for _ in ()).throw(TimeoutError("diagnostic 295-second guard")))
    signal.alarm(295)
    try:
        namespace["run"](args)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
