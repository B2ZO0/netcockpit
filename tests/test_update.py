"""Tests de ./setup.sh --update (scripts/update.sh) sur de faux dépôts git : un « GitHub » local, le poste du
mainteneur qui publie des versions, et une installation faite avec git clone.

Règles vérifiées : --update passe à la dernière version publiée (tag vX.Y.Z), jamais au travail en cours de main,
ne revient jamais en arrière, et ne touche à rien quand il ne peut pas avancer ; --update --edge suit main."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAS_GIT = shutil.which("git") is not None and shutil.which("bash") is not None

# Le setup.sh « publié plus tard » : il dit seulement qu'il a été relancé, avec quelles options.
NEW_SETUP = '#!/usr/bin/env bash\necho "NEW SETUP RAN: $*"\n'


@unittest.skipUnless(HAS_GIT, "git or bash is not installed")
class UpdateFollowsReleases(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.home.mkdir()
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home), "LANG": "C", "LANGUAGE": "",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.local",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.local", "GIT_TERMINAL_PROMPT": "0",
        }
        self.origin = base / "origin.git"
        self.dev = base / "dev"
        self.install = base / "install"
        self.git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.git(base, "init", "-q", "-b", "main", str(self.dev))
        (self.dev / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "update.sh", self.dev / "scripts" / "update.sh")
        shutil.copy(ROOT / "setup.sh", self.dev / "setup.sh")
        (self.dev / "VERSION").write_text("1.0.0\n")
        self.git(self.dev, "add", "-A")
        self.git(self.dev, "commit", "-q", "-m", "First release")
        self.git(self.dev, "tag", "v1.0.0")
        self.git(self.dev, "remote", "add", "origin", str(self.origin))
        self.push()
        self.git(base, "clone", "-q", str(self.origin), str(self.install))

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------------ outils
    def git(self, where, *args):
        return subprocess.run(["git", "-C", str(where), *args], check=True, capture_output=True,
                              text=True, env=self.env).stdout.strip()

    def push(self):
        self.git(self.dev, "push", "-q", "origin", "main", "--tags")

    def commit(self, version, message, tag=None):
        (self.dev / "VERSION").write_text(version + "\n")
        self.git(self.dev, "commit", "-q", "-am", message)
        if tag:
            self.git(self.dev, "tag", "-a", tag, "-m", tag)
        return self.git(self.dev, "rev-parse", "HEAD")

    def update(self, *args, env=None):
        return subprocess.run(["bash", str(self.install / "scripts" / "update.sh"), *args], capture_output=True,
                              text=True, env=env or self.env, cwd=str(self.home))

    def head(self):
        return self.git(self.install, "rev-parse", "HEAD")

    def installed(self):
        return (self.install / "VERSION").read_text().strip()

    # ------------------------------------------------------------------ cas
    def test_a_release_with_many_changes_is_applied(self):
        # The list of changes is cut to 15 lines: that must never make the update itself fail.
        for i in range(300):
            (self.dev / "VERSION").write_text(f"1.1.0-{i}\n")
            self.git(self.dev, "commit", "-q", "-am", f"Change {i}")
        release = self.commit("1.1.0", "Big release", tag="v1.1.0")
        self.push()
        for _ in range(3):
            self.git(self.install, "reset", "-q", "--hard", "v1.0.0")
            r = self.update()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(self.head(), release)
            self.assertEqual(r.stdout.count("    - "), 15)

    def test_moves_to_the_latest_release_not_to_work_in_progress(self):
        release = self.commit("1.1.0", "Second release", tag="v1.1.0")
        self.commit("1.2.0-dev", "Work in progress")
        self.push()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), release)
        self.assertEqual(self.installed(), "1.1.0")
        self.assertIn("v1.1.0", r.stdout)
        self.assertIn("Second release", r.stdout)
        self.assertNotIn("Work in progress", r.stdout)
        # Toujours sur sa branche : --edge pourra avancer plus tard avec un simple git pull.
        self.assertEqual(self.git(self.install, "symbolic-ref", "--short", "HEAD"), "main")

    def test_already_on_the_latest_release(self):
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertIn("Already up to date (v1.0.0", r.stdout)

    def test_never_goes_back_when_the_install_is_newer_than_the_latest_release(self):
        # Les installations actuelles suivent main et sont plus récentes que la dernière version publiée.
        self.commit("1.1.0-dev", "Work in progress")
        self.push()
        self.git(self.install, "pull", "-q", "--ff-only")
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertEqual(self.installed(), "1.1.0-dev")
        self.assertIn("already newer than the latest published version (v1.0.0)", r.stdout)
        self.assertIn("--edge", r.stdout)

    def test_newer_install_moves_on_once_the_next_version_is_published(self):
        self.commit("1.1.0-dev", "Work in progress")
        self.push()
        self.git(self.install, "pull", "-q", "--ff-only")
        self.commit("1.1.0", "Finish 1.1", tag="v1.1.0")
        self.commit("1.2.0-dev", "Next work in progress")
        self.push()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.installed(), "1.1.0")

    def test_never_goes_back_to_a_release_that_does_not_contain_the_install(self):
        # Un correctif publié depuis une autre branche (v1.0.1 à partir de v1.0.0) alors que l'installation est ailleurs.
        self.commit("1.1.0-dev", "Work in progress")
        self.push()
        self.git(self.install, "pull", "-q", "--ff-only")
        self.git(self.dev, "checkout", "-q", "-b", "fix", "v1.0.0")
        self.commit("1.0.1", "Hotfix", tag="v1.0.1")
        self.git(self.dev, "push", "-q", "origin", "fix", "--tags")
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertIn("not in the latest published version (v1.0.1)", r.stdout)

    def test_local_commits_are_never_lost(self):
        (self.install / "VERSION").write_text("1.0.0-mine\n")
        self.git(self.install, "commit", "-q", "-am", "My own change")
        self.commit("1.1.0", "Second release", tag="v1.1.0")
        self.push()
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertEqual(self.installed(), "1.0.0-mine")

    def test_versions_are_compared_as_numbers_and_pre_releases_are_ignored(self):
        v19 = self.commit("1.9.0", "1.9", tag="v1.9.0")
        self.commit("1.10.0-rc1", "rc", tag="v1.10.0-rc1")
        self.git(self.dev, "tag", "nightly")
        self.push()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), v19)
        v110 = self.commit("1.10.0", "1.10", tag="v1.10.0")
        self.push()
        r = self.update()
        self.assertEqual(self.head(), v110, r.stdout + r.stderr)

    def test_a_tag_deleted_on_github_is_not_used(self):
        self.commit("1.1.0", "Withdrawn", tag="v1.1.0")
        self.push()
        self.git(self.install, "fetch", "-q", "--tags")
        self.git(self.dev, "push", "-q", "origin", ":refs/tags/v1.1.0")
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertEqual(self.installed(), "1.0.0")

    def test_no_published_version_changes_nothing(self):
        self.git(self.dev, "push", "-q", "origin", ":refs/tags/v1.0.0")
        self.git(self.install, "tag", "-d", "v1.0.0")
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertIn("No published version yet", r.stdout)

    def test_hand_edited_file_stops_without_changing_anything(self):
        self.commit("1.1.0", "Second release", tag="v1.1.0")
        self.push()
        (self.install / "VERSION").write_text("edited by hand\n")
        before = self.head()
        r = self.update()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.head(), before)
        self.assertEqual(self.installed(), "edited by hand")
        self.assertIn("git stash", r.stdout)

    def test_edge_follows_main(self):
        self.commit("1.1.0", "Second release", tag="v1.1.0")
        wip = self.commit("1.2.0-dev", "Work in progress")
        self.push()
        r = self.update("--edge")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.head(), wip)
        self.assertIn("Test mode (--edge)", r.stdout)
        self.assertIn("Work in progress", r.stdout)

    def test_edge_refuses_a_pinned_folder(self):
        self.git(self.install, "checkout", "-q", "--detach", "v1.0.0")
        r = self.update("--edge")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("git checkout main", r.stdout)

    def test_not_a_git_clone(self):
        shutil.rmtree(self.install / ".git")
        r = self.update()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("not installed with git clone", r.stdout)

    def test_messages_in_french(self):
        r = self.update(env={**self.env, "LANG": "fr_FR.UTF-8"})
        self.assertIn("Déjà à jour (v1.0.0", r.stdout)

    def test_setup_update_then_runs_the_new_setup(self):
        """./setup.sh --update télécharge la version publiée, puis relance le setup.sh de cette version."""
        (self.dev / "setup.sh").write_text(NEW_SETUP)
        self.commit("1.1.0", "Second release", tag="v1.1.0")
        self.push()
        fakebin = Path(self.tmp.name) / "bin"
        fakebin.mkdir()
        (fakebin / "docker").write_text("#!/bin/sh\nexit 0\n")
        (fakebin / "docker").chmod(0o755)
        env = {**self.env, "PATH": f"{fakebin}:{self.env['PATH']}"}
        r = subprocess.run(["bash", str(self.install / "setup.sh"), "--update", "--yes"], capture_output=True,
                           text=True, env=env, cwd=str(self.home))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.installed(), "1.1.0")
        self.assertIn("NEW SETUP RAN: --yes", r.stdout)

    def test_setup_help_lists_edge(self):
        r = subprocess.run(["bash", str(ROOT / "setup.sh"), "--help"], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--update --edge", r.stdout)


@unittest.skipUnless(HAS_GIT, "bash is not installed")
class ExistingInstallGuard(unittest.TestCase):
    def test_project_name_is_found_without_env_file(self):
        # Folder named like the git clone, no .env yet, docker unusable: the project is still "supervision",
        # so setup.sh recognises the volumes of an existing installation and stops instead of starting fresh.
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        start = setup.index("HERE=$(pwd -P)")
        lines = setup[start:setup.index("\n", setup.index("PROJ=${PROJ:-", start))]
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "netcockpit"
            (folder / "bin").mkdir(parents=True)
            shutil.copy(ROOT / "docker-compose.yml", folder / "docker-compose.yml")
            (folder / "bin" / "docker").write_text("#!/bin/sh\necho 'required variable is missing' >&2\nexit 1\n")
            (folder / "bin" / "docker").chmod(0o755)
            out = subprocess.run(["bash", "-c", "set -euo pipefail\n" + lines + '\necho "PROJ=$PROJ"'], cwd=folder,
                                 capture_output=True, text=True, env={"PATH": f"{folder / 'bin'}:/usr/bin:/bin"})
            self.assertIn("PROJ=supervision", out.stdout, out.stderr)


if __name__ == "__main__":
    unittest.main()
