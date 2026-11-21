"""Boundary tests using isolated temporary Git histories."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import learning_branch


SCRIPT = Path(__file__).with_name("web_access.py")
PREFIX = "00_Inbox/AFDM-channel-estimation"
REMOTE = "jgw:/srv/git/afdm-sp.git"
SERVER_REMOTE = "/srv/git/afdm-sp.git"


def run(cwd, *args, ok=True):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if ok and result.returncode:
        raise AssertionError(f"{args}: {result.stderr}")
    return result


class WebAccessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.vault = self.base / "vault"
        self.project = self.vault / PREFIX
        (self.project / "learning/sp_minimal").mkdir(parents=True)
        (self.project / "STATE.md").write_text("recorded state\n")
        (self.project / "learning/sp_minimal/README.md").write_text("learning base\n")
        run(self.vault, "git", "init", "-q")
        run(self.vault, "git", "config", "user.name", "Test")
        run(self.vault, "git", "config", "user.email", "test@example.invalid")
        run(self.vault, "git", "add", ".")
        run(self.vault, "git", "commit", "-qm", "base")
        self.ref = run(self.vault, "git", "rev-parse", "HEAD").stdout.strip()
        self.selection = self.base / "paths.txt"
        self.selection.write_text("STATE.md\nlearning/sp_minimal/README.md\n")

    def cli(self, *args, ok=True):
        return run(self.vault, sys.executable, str(SCRIPT), "--project-root", str(self.project), *args, ok=ok)

    def pack(self, name="stage", selection=None):
        output = self.base / name
        result = self.cli("pack", "--source-ref", self.ref, "--selection", str(selection or self.selection),
                          "--output", str(output))
        return output, json.loads(result.stdout)

    def exchange(self, stage):
        checkout = self.base / "external-exchange"
        run(self.base, "cp", "-R", str(stage / "exchange"), str(checkout))
        run(checkout, "git", "init", "-q")
        run(checkout, "git", "config", "user.name", "Test")
        run(checkout, "git", "config", "user.email", "test@example.invalid")
        run(checkout, "git", "remote", "add", "origin", REMOTE)
        run(checkout, "git", "add", ".")
        run(checkout, "git", "commit", "-qm", "owner main")
        main = run(checkout, "git", "rev-parse", "HEAD").stdout.strip()
        run(checkout, "git", "update-ref", "refs/remotes/origin/main", main)
        run(checkout, "git", "switch", "-qc", "chatgpt/learning")
        return checkout

    def review(self, checkout, apply=False, ok=True):
        run(checkout, "git", "update-ref", "refs/remotes/origin/chatgpt/learning", "HEAD")
        args = ["review", "--checkout", str(checkout), "--proposal", "origin/chatgpt/learning"]
        if apply:
            args.append("--apply")
        return self.cli(*args, ok=ok)

    def test_pack_uses_committed_bytes_and_is_idempotent(self):
        (self.project / "STATE.md").write_text("uncommitted state\n")
        first, a = self.pack()
        second, b = self.pack("stage-two")
        self.assertEqual(a["release_id"], b["release_id"])
        self.assertEqual((first / "release/STATE.md").read_text(), "recorded state\n")
        self.assertEqual((first / "exchange/RELEASE").read_text().strip(), a["release_id"])
        self.cli("verify", "--release", str(first / "release"))
        (first / "release/STATE.md").write_text("tampered\n")
        self.assertIn("payload mismatch", self.cli("verify", "--release", str(first / "release"), ok=False).stderr)
        (self.project / "STATE.md").write_text("recorded state\n")
        (self.project / "unselected.md").write_text("new commit\n")
        run(self.vault, "git", "add", ".")
        run(self.vault, "git", "commit", "-qm", "new attribution")
        self.ref = run(self.vault, "git", "rev-parse", "HEAD").stdout.strip()
        _, c = self.pack("new-source")
        self.assertNotEqual(a["release_id"], c["release_id"])
        self.assertEqual(json.loads((second / "release/manifest.json").read_text())["files"],
                         json.loads((self.base / "new-source/release/manifest.json").read_text())["files"])

    def test_rejects_wrong_root_unsafe_and_symlink_selection(self):
        wrong = self.base / "AFWDM_AFDM_CP"
        wrong.mkdir()
        result = run(self.vault, sys.executable, str(SCRIPT), "--project-root", str(wrong), "pack",
                     "--source-ref", self.ref, "--selection", str(self.selection),
                     "--output", str(self.base / "wrong"), ok=False)
        self.assertIn("wrong project root", result.stderr)
        unsafe = self.base / "unsafe.txt"
        unsafe.write_text(self.selection.read_text() + "learning/sp_minimal/exam/sealed_questions.md\n")
        self.assertIn("unsafe selected path", self.cli("pack", "--source-ref", self.ref,
                       "--selection", str(unsafe), "--output", str(self.base / "unsafe"), ok=False).stderr)
        (self.project / "link").symlink_to("STATE.md")
        run(self.vault, "git", "add", ".")
        run(self.vault, "git", "commit", "-qm", "link")
        self.ref = run(self.vault, "git", "rev-parse", "HEAD").stdout.strip()
        links = self.base / "links.txt"
        links.write_text(self.selection.read_text() + "link\n")
        self.assertIn("symlink", self.cli("pack", "--source-ref", self.ref,
                      "--selection", str(links), "--output", str(self.base / "link-stage"), ok=False).stderr)

    def test_verify_rejects_missing_and_extra_payload(self):
        stage, _ = self.pack()
        release = stage / "release"
        (release / "STATE.md").unlink()
        self.assertIn("file set mismatch", self.cli("verify", "--release", str(release), ok=False).stderr)
        (release / "STATE.md").write_text("recorded state\n")
        (release / "extra.md").write_text("unexpected\n")
        self.assertIn("file set mismatch", self.cli("verify", "--release", str(release), ok=False).stderr)

    def test_review_checks_scope_preimage_and_repeated_acceptance(self):
        stage, _ = self.pack()
        checkout = self.exchange(stage)
        (checkout / "learning/sp_minimal/note.md").write_text("new learning\n")
        run(checkout, "git", "add", ".")
        run(checkout, "git", "commit", "-qm", "learning note")
        self.assertIn("note.md", self.review(checkout).stdout)
        self.review(checkout, apply=True)
        self.assertEqual((self.project / "learning/sp_minimal/note.md").read_text(), "new learning\n")
        self.assertIn("Already accepted", self.review(checkout).stdout)

    def test_review_refuses_changed_mac_baseline_and_outside_path(self):
        stage, _ = self.pack()
        checkout = self.exchange(stage)
        (checkout / "learning/sp_minimal/README.md").write_text("proposal\n")
        run(checkout, "git", "add", ".")
        run(checkout, "git", "commit", "-qm", "proposal")
        (self.project / "learning/sp_minimal/README.md").write_text("Mac changed\n")
        self.assertIn("preimage differs", self.review(checkout, ok=False).stderr)
        (checkout / "RELEASE").write_text("wrong\n")
        run(checkout, "git", "add", ".")
        run(checkout, "git", "commit", "-qm", "outside")
        self.assertIn("outside", self.review(checkout, ok=False).stderr)
        self.assertIn("chatgpt/*", self.cli("review", "--checkout", str(checkout),
                                           "--proposal", "origin/main", ok=False).stderr)

    def test_review_refuses_unpublished_local_branch(self):
        stage, _ = self.pack()
        checkout = self.exchange(stage)
        (checkout / "learning/sp_minimal/note.md").write_text("local only\n")
        run(checkout, "git", "add", ".")
        run(checkout, "git", "commit", "-qm", "unpublished note")
        result = self.cli("review", "--checkout", str(checkout),
                          "--proposal", "chatgpt/learning", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origin/chatgpt/*", result.stderr)

    def test_old_learning_branch_survives_owner_update_and_acknowledgment(self):
        stage, _ = self.pack()
        checkout = self.exchange(stage)
        (checkout / "learning/sp_minimal/note.md").write_text("old release note\n")
        run(checkout, "git", "add", ".")
        run(checkout, "git", "commit", "-qm", "learning on old release")
        proposal = run(checkout, "git", "rev-parse", "HEAD").stdout.strip()
        run(checkout, "git", "update-ref", "refs/remotes/origin/chatgpt/learning", proposal)
        run(checkout, "git", "switch", "-qc", "owner", "origin/main")
        (checkout / "RELEASE").write_text("new-release-id\n")
        run(checkout, "git", "add", "RELEASE")
        run(checkout, "git", "commit", "-qm", "owner publishes a new release")
        owner = run(checkout, "git", "rev-parse", "HEAD").stdout.strip()
        run(checkout, "git", "update-ref", "refs/remotes/origin/main", owner)
        run(checkout, "git", "switch", "-q", "chatgpt/learning")
        self.assertIn("note.md", self.review(checkout).stdout)
        self.review(checkout, apply=True)
        self.assertEqual((self.project / "learning/sp_minimal/note.md").read_text(), "old release note\n")
        run(checkout, "git", "switch", "-q", "owner")
        run(checkout, "git", "merge", "--no-ff", "-qm", "accept learning", proposal)
        accepted = run(checkout, "git", "rev-parse", "HEAD").stdout.strip()
        run(checkout, "git", "update-ref", "refs/remotes/origin/main", accepted)
        result = self.cli("review", "--checkout", str(checkout),
                          "--proposal", "origin/chatgpt/learning")
        self.assertEqual(result.stdout, "No learning changes\n")


class LearningBranchTest(unittest.TestCase):
    def test_start_end_and_wrong_project_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bare = base / "afdm-sp.git"
            seed = base / "seed"
            clone = base / "afdm-sp"
            run(base, "git", "init", "--bare", "-q", "-b", "main", str(bare))
            run(base, "git", "init", "-q", "-b", "main", str(seed))
            run(seed, "git", "config", "user.name", "Test")
            run(seed, "git", "config", "user.email", "test@example.invalid")
            (seed / "learning/sp_minimal").mkdir(parents=True)
            (seed / "learning/sp_minimal/README.md").write_text("base\n")
            identity = {"project_id": "afdm-e2e-main", "source_prefix": PREFIX,
                        "mac_remote": REMOTE, "server_remote": str(bare)}
            (seed / "PROJECT.json").write_text(json.dumps(identity))
            (seed / "RELEASE").write_text("release-id\n")
            run(seed, "git", "add", ".")
            run(seed, "git", "commit", "-qm", "owner")
            run(seed, "git", "remote", "add", "origin", str(bare))
            run(seed, "git", "push", "-q", "origin", "main")
            run(base, "git", "clone", "-q", str(bare), str(clone))
            run(clone, "git", "config", "user.name", "Test")
            run(clone, "git", "config", "user.email", "test@example.invalid")
            with patch.object(learning_branch, "ROOT", clone.resolve()), patch.object(learning_branch, "REMOTE", str(bare)), \
                    patch.object(learning_branch, "IDENTITY", identity):
                learning_branch.start()
                (clone / "learning/sp_minimal/note.md").write_text("valid note\n")
                learning_branch.end("learning: note")
                self.assertEqual(run(bare, "git", "show", "refs/heads/chatgpt/learning:learning/sp_minimal/note.md").stdout,
                                 "valid note\n")
                (seed / "RELEASE").write_text("new-release-id\n")
                run(seed, "git", "add", "RELEASE")
                run(seed, "git", "commit", "-qm", "owner publishes newer evidence")
                run(seed, "git", "push", "-q", "origin", "main")
                learning_branch.start()
                self.assertEqual((clone / "RELEASE").read_text(), "new-release-id\n")
                self.assertEqual((clone / "learning/sp_minimal/note.md").read_text(), "valid note\n")
                learning_branch.end("learning: preserve note across owner update")
                run(clone, "git", "switch", "-q", "main")
                run(clone, "git", "branch", "-D", "chatgpt/learning")
                learning_branch.start()
                self.assertEqual((clone / "learning/sp_minimal/note.md").read_text(), "valid note\n")
                (clone / "RELEASE").write_text("wrong\n")
                with self.assertRaisesRegex(ValueError, "outside AFDM learning"):
                    learning_branch.end("learning: invalid")


if __name__ == "__main__":
    unittest.main()
