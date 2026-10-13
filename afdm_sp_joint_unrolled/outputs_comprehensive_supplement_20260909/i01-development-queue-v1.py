#!/usr/bin/env python3
"""Finite I-01 development queue; launches fixed batches and audits each once."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


R = Path("/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909")
SOCKET = "/data/guoyikun/tmp/g_afdm_supp0909.sock"
PYTHON = "/home/guoyikun/.conda/envs/AFDM/bin/python"
GPU = "GPU-fe13c694-2050-c9f0-2904-b806f6f6b0c2"
LAUNCHER = Path(__file__).with_name("launch-i01-development-v1.py")
AUDITOR = Path(__file__).with_name("audit-i01-development-v1.py")
RANGES = tuple((start, min(start + 16, 192)) for start in range(33, 192, 16))
OBSERVATION_FAILURE_LIMIT = 3
MIN_WORKER_WINDOW_SECONDS = 3600 + 15


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def atomic(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".pending", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def allowed(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(R.resolve()):
        raise ValueError("path outside fixed project output root")
    return resolved


def job_for(start, stop):
    name = f"i01-development-b{start:03d}-{stop:03d}-v1"
    return {
        "start": start,
        "stop": stop,
        "full_calls": (stop - start) * 18,
        "name": name,
        "session": "g_afdm_supp_" + name.replace("-", "_"),
        "out": str(R / name),
        "script": str(R / (name + ".sh")),
        "admission": str(R / (name + ".admission.json")),
        "log": str(R / (name + ".log")),
        "exit": str(R / (name + ".exit")),
        "audit": str(R / (name + ".audit.json")),
    }


def jobs():
    result = [job_for(*bounds) for bounds in RANGES]
    if sum(job["full_calls"] for job in result) != 2862:
        raise AssertionError("fixed remaining I-01 budget changed")
    return result


def validate_prior_audit(path):
    path = allowed(path)
    value = read(path)
    batches = value.get("batches")
    expected = {(0, 1, 18), (1, 17, 288), (17, 33, 288)}
    actual = (set() if not isinstance(batches, list) else
              {(row.get("start"), row.get("stop"), row.get("F_audited")) for row in batches})
    roots = (set() if not isinstance(batches, list) else
             {Path(row.get("root", "")).resolve() for row in batches})
    expected_roots = {(R / f"i01-development-b{start:03d}-{stop:03d}-v1").resolve()
                      for start, stop, _ in expected}
    if (value.get("schema") != "supplement-I01-development-raw-audit-v1" or
            value.get("status") != "passed" or value.get("F_audited") != 594 or
            value.get("batch_count") != 3 or not isinstance(batches, list) or len(batches) != 3 or
            actual != expected or roots != expected_roots or
            not isinstance(value.get("bindings"), dict) or not value["bindings"] or
            not isinstance(value.get("code_sha256"), dict) or not value["code_sha256"]):
        raise ValueError("prior 594-F raw audit has not passed the exact three bound batches")
    return path, sha(path), value["bindings"], value["code_sha256"]


def validate_job_audit(job, expected_bindings=None, expected_code=None):
    path = allowed(job["audit"])
    value = read(path)
    batches = value.get("batches")
    if (value.get("schema") != "supplement-I01-development-raw-audit-v1" or
            value.get("status") != "passed" or
            value.get("F_audited") != job["full_calls"] or
            value.get("batch_count") != 1 or not isinstance(batches, list) or
            len(batches) != 1 or batches[0].get("start") != job["start"] or
            batches[0].get("stop") != job["stop"] or
            batches[0].get("F_audited") != job["full_calls"] or
            Path(batches[0].get("root", "")).resolve() != Path(job["out"]).resolve() or
            (expected_bindings is not None and value.get("bindings") != expected_bindings) or
            (expected_code is not None and value.get("code_sha256") != expected_code)):
        raise ValueError("batch raw audit did not pass its exact identity domain")
    return {"audit_sha256": sha(path), "F_audited": value["F_audited"]}


def command(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)


def snapshot(run=command):
    response = run(["tmux", "-S", SOCKET, "list-panes", "-a", "-F",
                    "#{session_name}\t#{pane_pid}\t#{pane_dead}\t#{pane_id}"])
    if response.returncode:
        if "no server running" in response.stderr or "No such file or directory" in response.stderr:
            return {}
        raise RuntimeError("tmux observation failed: " + response.stderr)
    rows = {}
    for line in response.stdout.splitlines():
        name, pid, dead, pane = line.split("\t")
        if name in rows:
            raise RuntimeError("multiple panes in receiver session: " + name)
        rows[name] = {"pid": int(pid), "dead": bool(int(dead)), "pane": pane}
    return rows


def process_identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    fields = text[text.rfind(")") + 2:].split()
    if fields[0] == "Z":
        return None
    return {"pid": pid, "start_ticks": fields[19]}


def receiver_count(rows):
    return sum(name.startswith("g_afdm_supp_") and not row["dead"]
               for name, row in rows.items())


def gpu_ready(run=command):
    response = run(["nvidia-smi", "--query-gpu=uuid,memory.free,memory.used,utilization.gpu",
                    "--format=csv,noheader,nounits"])
    if response.returncode:
        raise RuntimeError("GPU observation failed: " + response.stderr)
    matches = []
    for line in response.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if fields and fields[0] == GPU:
            matches.append(fields)
    if len(matches) != 1 or len(matches[0]) != 4:
        raise RuntimeError("fixed GPU identity observation failed")
    _, free, used, utilization = matches[0]
    free, used, utilization = float(free), float(used), float(utilization)
    return free >= 6144 and not (used > 18432 and utilization > 90)


def validate_state(state, deadline, prior_audit_sha, launcher_sha, auditor_sha,
                   campaign_bindings, campaign_code):
    expected = {job["session"]: job for job in jobs()}
    if (state.get("schema") != "i01-development-queue-state-v1" or
            state.get("deadline_unix") != deadline or
            not state.get("started_unix", deadline) < deadline <= state.get("started_unix", 0) + 4 * 3600 or
            state.get("prior_audit_sha256") != prior_audit_sha or
            state.get("campaign_bindings") != campaign_bindings or
            state.get("campaign_code_sha256") != campaign_code or
            state.get("launcher_sha256") != launcher_sha or
            state.get("auditor_sha256") != auditor_sha or
            type(state.get("paused")) is not bool or type(state.get("failed")) is not bool or
            type(state.get("observation_failures")) is not int or
            not set(state.get("jobs", {})).issubset(expected)):
        raise ValueError("restart must preserve the exact finite queue state")
    for session, record in state["jobs"].items():
        if record.get("status") not in ("intent", "running", "audit_intent", "complete", "failed"):
            raise ValueError("unknown persisted job state")
        if record["status"] in ("running", "audit_intent", "complete"):
            identity = record.get("process_identity", {})
            if (type(record.get("pid")) is not int or identity.get("pid") != record["pid"] or
                    not re.fullmatch(r"[0-9]+", str(identity.get("start_ticks", ""))) or
                    not re.fullmatch(r"%[0-9]+", str(record.get("pane", "")))):
                raise ValueError("persisted process identity is incomplete")
        if (record["status"] == "complete" and record.get("proof") !=
                validate_job_audit(expected[session], campaign_bindings, campaign_code)):
            raise ValueError("completed audit proof changed")


class Queue:
    def __init__(self, state, save, prior_audit, run=command, now=time.time,
                 identity=process_identity):
        self.state = state
        self.save = save
        self.prior_audit = Path(prior_audit)
        self.run = run
        self.now = now
        self.identity = identity
        self.plan = jobs()

    def persist(self):
        self.save(self.state)

    def pause(self, message):
        self.state["paused"] = True
        self.state.setdefault("errors", []).append({"unix": self.now(), "message": str(message)})
        self.persist()

    def fail(self, record, message):
        record.update(status="failed", failure=str(message))
        self.state["failed"] = True
        self.state.setdefault("errors", []).append({"unix": self.now(), "message": str(message)})
        self.persist()

    def observation_failure(self, message):
        self.state["observation_failures"] += 1
        self.state["last_observation_error"] = {"unix": self.now(), "message": str(message)}
        if self.state["observation_failures"] >= OBSERVATION_FAILURE_LIMIT:
            self.pause("observation failure limit reached: " + str(message))
        else:
            self.persist()

    def audit_completed_process(self, job, record):
        exit_path = Path(job["exit"])
        if not exit_path.is_file():
            self.fail(record, "registered process missing without exit evidence")
            return
        text = exit_path.read_text().strip()
        record["exit"] = text
        if text != "0":
            self.fail(record, "batch exited nonzero: " + text)
            return
        audit_path = Path(job["audit"])
        if audit_path.exists():
            record["proof"] = validate_job_audit(
                job, self.state["campaign_bindings"], self.state["campaign_code_sha256"])
            record["status"] = "complete"
            self.persist()
            return
        record["status"] = "audit_intent"
        self.persist()
        response = self.run([PYTHON, str(AUDITOR), "--root", job["out"],
                             "--out", job["audit"], "--max-records", str(job["full_calls"])])
        record["audit_result"] = {"returncode": response.returncode,
                                  "stdout": response.stdout[-16384:],
                                  "stderr": response.stderr[-16384:]}
        if response.returncode:
            self.fail(record, "batch raw audit exited nonzero")
            return
        try:
            record["proof"] = validate_job_audit(
                job, self.state["campaign_bindings"], self.state["campaign_code_sha256"])
        except Exception as exc:
            self.fail(record, exc)
            return
        record["status"] = "complete"
        self.persist()

    def observe(self, rows):
        for job in self.plan:
            record = self.state["jobs"].get(job["session"])
            if not record or record["status"] in ("complete", "failed"):
                continue
            if record["status"] == "intent":
                self.pause("unresolved launcher intent; no automatic relaunch")
                return
            if record["status"] == "audit_intent":
                if Path(job["audit"]).is_file():
                    record["proof"] = validate_job_audit(
                        job, self.state["campaign_bindings"], self.state["campaign_code_sha256"])
                    record["status"] = "complete"
                    self.persist()
                else:
                    self.pause("unresolved audit intent; no automatic rerun")
                return
            current = rows.get(job["session"])
            actual = self.identity(record["pid"])
            if current and not current["dead"]:
                if (current["pid"] != record["pid"] or current["pane"] != record["pane"] or
                        actual != record["process_identity"]):
                    self.pause("registered tmux/process identity changed")
                    return
                record["last_process_state"] = {"unix": self.now(), **current}
                continue
            if actual is not None:
                raise RuntimeError("live registered process missing from tmux inventory")
            self.audit_completed_process(job, record)
            if self.state["failed"]:
                return

    def launch(self, job, rows):
        artifacts = ("out", "script", "admission", "log", "exit", "audit")
        if job["session"] in rows or any(Path(job[key]).exists() for key in artifacts):
            self.state["failed"] = True
            self.state.setdefault("errors", []).append(
                {"unix": self.now(), "message": "existing artifact/session; no retry " + job["session"]})
            self.persist()
            return rows
        record = {"status": "intent", "start": job["start"], "stop": job["stop"],
                  "full_calls": job["full_calls"], "intent_unix": self.now()}
        self.state["jobs"][job["session"]] = record
        self.persist()
        response = self.run([PYTHON, str(LAUNCHER), "--start", str(job["start"]),
                             "--stop", str(job["stop"])])
        record["launcher_result"] = {"returncode": response.returncode,
                                     "stdout": response.stdout[-16384:],
                                     "stderr": response.stderr[-16384:]}
        self.persist()
        if response.returncode:
            self.pause("launcher returned nonzero; launch state is uncertain")
            return rows
        fresh = snapshot(self.run)
        pane = fresh.get(job["session"])
        if not pane or pane["dead"]:
            self.pause("launcher succeeded without a live exact tmux pane")
            return fresh
        identity = self.identity(pane["pid"])
        if identity is None:
            self.pause("launched process identity unavailable")
            return fresh
        record.update(status="running", pid=pane["pid"], pane=pane["pane"],
                      process_identity=identity,
                      last_process_state={"unix": self.now(), **pane})
        self.persist()
        return fresh

    def step(self):
        if self.now() >= self.state["deadline_unix"]:
            self.pause("queue deadline reached; running jobs were not killed")
            return "deadline"
        if self.state["paused"]:
            return "paused"
        if self.state["failed"]:
            return "failed"
        try:
            if (sha(LAUNCHER) != self.state["launcher_sha256"] or
                    sha(AUDITOR) != self.state["auditor_sha256"]):
                self.pause("launcher or auditor changed after queue creation")
                return "paused"
        except Exception as exc:
            self.pause("cannot verify launcher/auditor identity: " + str(exc))
            return "paused"
        try:
            _, digest, bindings, code = validate_prior_audit(self.prior_audit)
            if digest != self.state["prior_audit_sha256"]:
                raise ValueError("prior audit changed after queue creation")
            if (bindings != self.state["campaign_bindings"] or
                    code != self.state["campaign_code_sha256"]):
                raise ValueError("prior campaign bindings changed")
            rows = snapshot(self.run)
            self.state["last_observation"] = {"unix": self.now(), "tmux": rows}
            self.persist()
            self.observe(rows)
        except Exception as exc:
            self.observation_failure(exc)
            return "paused" if self.state["paused"] else "wait"
        if self.state["paused"]:
            return "paused"
        if self.state["failed"]:
            return "failed"
        unfinished = any(record["status"] in ("intent", "running", "audit_intent")
                         for record in self.state["jobs"].values())
        pending = [job for job in self.plan if job["session"] not in self.state["jobs"]]
        if not pending:
            self.state["observation_failures"] = 0
            self.persist()
            return "wait" if unfinished else "complete"
        capacity = max(0, 2 - receiver_count(rows))
        if not capacity:
            self.state["observation_failures"] = 0
            self.persist()
            return "wait"
        if self.state["deadline_unix"] - self.now() < MIN_WORKER_WINDOW_SECONDS:
            self.pause("insufficient queue deadline remaining for one bounded worker")
            return "paused"
        try:
            ready = gpu_ready(self.run)
        except Exception as exc:
            self.observation_failure(exc)
            return "paused" if self.state["paused"] else "wait"
        self.state["observation_failures"] = 0
        self.state["last_gpu_ready"] = {"unix": self.now(), "ready": ready}
        self.persist()
        if not ready:
            return "wait"
        for job in pending[:capacity]:
            rows = self.launch(job, rows)
            if self.state["paused"] or self.state["failed"]:
                break
        if self.state["paused"]:
            return "paused"
        if self.state["failed"]:
            return "failed"
        return "wait"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-audit", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--deadline-unix", type=float, required=True)
    args = parser.parse_args()
    prior_audit, prior_sha, campaign_bindings, campaign_code = validate_prior_audit(args.prior_audit)
    state_dir = allowed(args.state_dir)
    state_dir.mkdir(exist_ok=True)
    launcher_sha, auditor_sha = sha(LAUNCHER), sha(AUDITOR)
    with (state_dir / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state_path = state_dir / "state.json"
        if state_path.exists():
            state = read(state_path)
            validate_state(state, args.deadline_unix, prior_sha, launcher_sha, auditor_sha,
                           campaign_bindings, campaign_code)
        else:
            now = time.time()
            if not now < args.deadline_unix <= now + 4 * 3600:
                raise ValueError("deadline must be finite, future, and within four hours")
            state = {"schema": "i01-development-queue-state-v1",
                     "started_unix": now, "deadline_unix": args.deadline_unix,
                     "prior_audit": str(prior_audit), "prior_audit_sha256": prior_sha,
                     "campaign_bindings": campaign_bindings,
                     "campaign_code_sha256": campaign_code,
                     "manager_session": "g_i01_development_queue_v1",
                     "launcher_sha256": launcher_sha, "auditor_sha256": auditor_sha,
                     "jobs": {}, "paused": False, "failed": False,
                     "observation_failures": 0, "errors": []}
            atomic(state_path, state)
        queue = Queue(state, lambda value: atomic(state_path, value), prior_audit)
        while True:
            status = queue.step()
            if status in ("complete", "failed", "paused", "deadline"):
                atomic(state_dir / "result.json", {
                    "status": status, "exitcode": 0 if status == "complete" else 1,
                    "state": state,
                    "policy": "no receiver kill, retry, restart, replacement, or quota reclaim"})
                return 0 if status == "complete" else 1
            time.sleep(min(30, max(0, args.deadline_unix - time.time())))


if __name__ == "__main__":
    raise SystemExit(main())
