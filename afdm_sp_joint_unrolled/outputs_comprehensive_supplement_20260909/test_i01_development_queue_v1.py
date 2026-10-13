"""Synthetic I-01 queue state tests; no server or receiver participation."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "i01_queue", Path(__file__).with_name("i01-development-queue-v1.py"))
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


def response(code=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.root_patch = patch.object(q, "R", self.root)
        self.root_patch.start()
        self.prior_audit = self.root / "prior.audit.json"
        self.write_prior_audit()

    def tearDown(self):
        self.root_patch.stop()
        self.temporary.cleanup()

    def write_audit(self, path, start, stop):
        full_calls = (stop - start) * 18
        root = self.root / f"i01-development-b{start:03d}-{stop:03d}-v1"
        path.write_text(json.dumps({
            "schema": "supplement-I01-development-raw-audit-v1", "status": "passed",
            "F_audited": full_calls, "batch_count": 1,
            "batches": [{"root": str(root), "start": start, "stop": stop,
                         "F_audited": full_calls}],
            "bindings": {"files": {"fixture": "hash"}},
            "code_sha256": {"G": "g", "H": "h"}}))

    def write_prior_audit(self):
        batches = []
        for start, stop in ((0, 1), (1, 17), (17, 33)):
            root = self.root / f"i01-development-b{start:03d}-{stop:03d}-v1"
            root.mkdir(exist_ok=True)
            batches.append({"root": str(root), "start": start, "stop": stop,
                            "F_audited": (stop - start) * 18})
        self.prior_audit.write_text(json.dumps({
            "schema": "supplement-I01-development-raw-audit-v1", "status": "passed",
            "F_audited": 594, "batch_count": 3, "batches": batches,
            "bindings": {"files": {"fixture": "hash"}}, "code_sha256": {"G": "g", "H": "h"}}))

    def state(self, **changes):
        value = {"deadline_unix": 10000, "jobs": {}, "paused": False, "failed": False,
                 "observation_failures": 0, "errors": [],
                 "prior_audit_sha256": q.sha(self.prior_audit),
                 "campaign_bindings": {"files": {"fixture": "hash"}},
                 "campaign_code_sha256": {"G": "g", "H": "h"},
                 "launcher_sha256": q.sha(q.LAUNCHER), "auditor_sha256": q.sha(q.AUDITOR)}
        value.update(changes)
        return value

    def queue(self, state=None, run=None, identity=None):
        return q.Queue(state or self.state(), lambda _: None, self.prior_audit,
                       run=run or (lambda _: response()), now=lambda: 1,
                       identity=identity or (lambda _: None))

    def test_fixed_ranges_cover_exact_remaining_2862F(self):
        self.assertEqual(q.RANGES[0], (33, 49))
        self.assertEqual(q.RANGES[-1], (177, 192))
        self.assertEqual(len(q.RANGES), 10)
        self.assertEqual(sum(job["full_calls"] for job in q.jobs()), 2862)
        self.assertEqual(594 + sum(job["full_calls"] for job in q.jobs()), 3456)
        self.assertEqual(len({job["session"] for job in q.jobs()}), 10)

    def test_prior_three_batch_audit_is_a_hard_gate(self):
        _, digest, bindings, code = q.validate_prior_audit(self.prior_audit)
        self.assertEqual(digest, q.sha(self.prior_audit))
        self.assertEqual(bindings, self.state()["campaign_bindings"])
        self.assertEqual(code, self.state()["campaign_code_sha256"])
        value = json.loads(self.prior_audit.read_text())
        value["status"] = "failed"
        self.prior_audit.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            q.validate_prior_audit(self.prior_audit)

    def test_deadline_does_not_observe_launch_or_kill(self):
        queue = self.queue(self.state(deadline_unix=0), run=lambda _: self.fail("no command"))
        self.assertEqual(queue.step(), "deadline")
        self.assertTrue(queue.state["paused"])

    def test_insufficient_worker_window_creates_no_intent(self):
        state = self.state(deadline_unix=q.MIN_WORKER_WINDOW_SECONDS)
        queue = self.queue(state, run=lambda argv: response())
        self.assertEqual(queue.step(), "paused")
        self.assertFalse(state["jobs"])

    def test_three_observation_failures_pause_without_terminalizing_running_job(self):
        job = q.jobs()[0]
        state = self.state(jobs={job["session"]: {
            "status": "running", "pid": 10, "pane": "%1",
            "process_identity": {"pid": 10, "start_ticks": "5"}}})
        queue = self.queue(state, run=lambda _: response(1, stderr="permission denied"))
        self.assertEqual(queue.step(), "wait")
        self.assertEqual(queue.step(), "wait")
        self.assertEqual(queue.step(), "paused")
        self.assertEqual(state["jobs"][job["session"]]["status"], "running")

    def test_missing_process_without_exit_is_failed_and_never_audited(self):
        job = q.jobs()[0]
        state = self.state(jobs={job["session"]: {
            "status": "running", "pid": 10, "pane": "%1",
            "process_identity": {"pid": 10, "start_ticks": "5"}}})
        commands = []
        queue = self.queue(state, run=lambda argv: commands.append(argv) or response(),
                           identity=lambda _: None)
        queue.observe({})
        self.assertTrue(state["failed"])
        self.assertEqual(state["jobs"][job["session"]]["status"], "failed")
        self.assertFalse(any(str(q.AUDITOR) in command for argv in commands for command in argv))

    def test_zero_exit_runs_one_audit_then_completes(self):
        job = q.jobs()[0]
        Path(job["exit"]).write_text("0")
        state = self.state(jobs={job["session"]: {
            "status": "running", "pid": 10, "pane": "%1",
            "process_identity": {"pid": 10, "start_ticks": "5"}}})
        commands = []
        def run(argv):
            commands.append(argv)
            self.write_audit(Path(job["audit"]), job["start"], job["stop"])
            return response(stdout='{"status":"passed"}')
        queue = self.queue(state, run=run, identity=lambda _: None)
        queue.observe({})
        self.assertEqual(state["jobs"][job["session"]]["status"], "complete")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][1], str(q.AUDITOR))
        self.assertEqual(state["jobs"][job["session"]]["exit"], "0")

    def test_nonzero_exit_stops_without_audit(self):
        job = q.jobs()[0]
        Path(job["exit"]).write_text("124")
        state = self.state(jobs={job["session"]: {
            "status": "running", "pid": 10, "pane": "%1",
            "process_identity": {"pid": 10, "start_ticks": "5"}}})
        queue = self.queue(state, run=lambda _: self.fail("auditor must not run"),
                           identity=lambda _: None)
        queue.observe({})
        self.assertTrue(state["failed"])
        self.assertEqual(state["jobs"][job["session"]]["exit"], "124")

    def test_batch_audit_must_match_prior_campaign_bindings(self):
        job = q.jobs()[0]
        self.write_audit(Path(job["audit"]), job["start"], job["stop"])
        value = json.loads(Path(job["audit"]).read_text())
        value["bindings"] = {"files": {"fixture": "changed"}}
        Path(job["audit"]).write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            q.validate_job_audit(job, self.state()["campaign_bindings"],
                                 self.state()["campaign_code_sha256"])

    def test_launch_uses_only_existing_launcher_and_caps_at_two(self):
        sessions = {}
        commands = []
        def run(argv):
            commands.append(argv)
            if argv and argv[0] == "nvidia-smi":
                return response(stdout=f"{q.GPU}, 12000, 1000, 5")
            if argv[:2] == [q.PYTHON, str(q.LAUNCHER)]:
                start, stop = int(argv[-3]), int(argv[-1])
                job = q.job_for(start, stop)
                pid = 100 + len(sessions)
                sessions[job["session"]] = {"pid": pid, "dead": False,
                                             "pane": "%" + str(pid)}
                return response(stdout="launch admission")
            text = "\n".join(f"{name}\t{row['pid']}\t0\t{row['pane']}"
                             for name, row in sessions.items())
            return response(stdout=text)
        queue = self.queue(self.state(deadline_unix=10000), run=run,
                           identity=lambda pid: {"pid": pid, "start_ticks": "7"})
        self.assertEqual(queue.step(), "wait")
        self.assertEqual(len(queue.state["jobs"]), 2)
        self.assertTrue(all(record["status"] == "running"
                            for record in queue.state["jobs"].values()))
        launches = [argv for argv in commands if argv[:2] == [q.PYTHON, str(q.LAUNCHER)]]
        self.assertEqual(len(launches), 2)
        self.assertFalse(any("new-session" in argv for argv in launches))

    def test_busy_gpu_waits_without_creating_intent(self):
        def run(argv):
            if argv and argv[0] == "nvidia-smi":
                return response(stdout=f"{q.GPU}, 5000, 19000, 99")
            return response()
        state = self.state(deadline_unix=10000)
        queue = self.queue(state, run=run)
        self.assertEqual(queue.step(), "wait")
        self.assertFalse(state["jobs"])

    def test_changed_launcher_hash_pauses_before_observation(self):
        state = self.state(deadline_unix=10000, launcher_sha256="changed")
        queue = self.queue(state, run=lambda _: self.fail("must not observe"))
        self.assertEqual(queue.step(), "paused")
        self.assertFalse(state["jobs"])

    def test_unresolved_intent_pauses_without_relaunch(self):
        job = q.jobs()[0]
        state = self.state(jobs={job["session"]: {"status": "intent"}})
        queue = self.queue(state)
        queue.observe({})
        self.assertTrue(state["paused"])


if __name__ == "__main__":
    unittest.main()
