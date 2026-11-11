"""Tests du choix de l'image toute prête du cockpit (scripts/cockpit_image.py), sur de faux dépôts git."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import cockpit_image  # noqa: E402

HAS_GIT = shutil.which("git") is not None


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.local",
                           "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(HAS_GIT, "git is not installed")
class FakeCheckout(unittest.TestCase):
    """Un petit dépôt qui ressemble à une installation faite avec git clone."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "cockpit" / "app").mkdir(parents=True)
        (self.repo / "cockpit" / "Dockerfile").write_text("FROM python:3.12-slim\n")
        (self.repo / "cockpit" / "app" / "main.py").write_text("print('cockpit')\n")
        (self.repo / "README.md").write_text("NetCockpit\n")
        (self.repo / ".gitignore").write_text("__pycache__/\n.env\n")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "first")

    def tearDown(self):
        self.tmp.cleanup()

    def tree(self):
        return "tree-" + git(self.repo, "rev-parse", "HEAD:cockpit")[:12]

    def test_auto_gives_the_official_image_tagged_with_the_cockpit_folder(self):
        for setting in ("auto", "", "  AUTO  ", None):
            self.assertEqual(cockpit_image.choose(setting, self.repo), f"ghcr.io/b2zo0/netcockpit:{self.tree()}")

    def test_tag_only_changes_when_the_cockpit_code_changes(self):
        before = cockpit_image.cockpit_tag(self.repo)
        (self.repo / "README.md").write_text("NetCockpit, docs only\n")
        git(self.repo, "commit", "-q", "-am", "docs")
        self.assertEqual(cockpit_image.cockpit_tag(self.repo), before)
        (self.repo / "cockpit" / "app" / "main.py").write_text("print('cockpit 2')\n")
        git(self.repo, "commit", "-q", "-am", "code")
        self.assertNotEqual(cockpit_image.cockpit_tag(self.repo), before)
        self.assertRegex(cockpit_image.cockpit_tag(self.repo), r"^tree-[0-9a-f]{12}$")

    def test_edited_or_added_cockpit_files_are_built_locally(self):
        (self.repo / "cockpit" / "app" / "main.py").write_text("print('edited by hand')\n")
        self.assertEqual(cockpit_image.choose("auto", self.repo), "")
        git(self.repo, "checkout", "--", "cockpit")
        (self.repo / "cockpit" / "app" / "extra.py").write_text("x = 1\n")
        self.assertEqual(cockpit_image.choose("auto", self.repo), "")

    def test_ignored_files_and_settings_do_not_force_a_build(self):
        (self.repo / "cockpit" / "app" / "__pycache__").mkdir()
        (self.repo / "cockpit" / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"\0")
        (self.repo / ".env").write_text("COCKPIT_IMAGE=auto\n")
        (self.repo / "README.md").write_text("edited outside cockpit/\n")
        self.assertEqual(cockpit_image.choose("auto", self.repo), f"ghcr.io/b2zo0/netcockpit:{self.tree()}")

    def test_build_always_builds(self):
        for setting in ("build", "BUILD", "local", "off", "false"):
            self.assertEqual(cockpit_image.choose(setting, self.repo), "")

    def test_own_registry_gets_the_same_tag(self):
        self.assertEqual(cockpit_image.choose("registry.example.local/netcockpit", self.repo),
                         f"registry.example.local/netcockpit:{self.tree()}")
        self.assertEqual(cockpit_image.choose("registry.example.local:5000/infra/netcockpit", self.repo),
                         f"registry.example.local:5000/infra/netcockpit:{self.tree()}")

    def test_explicit_tag_or_digest_is_used_as_is(self):
        (self.repo / "cockpit" / "app" / "main.py").write_text("print('edited')\n")
        self.assertEqual(cockpit_image.choose("ghcr.io/b2zo0/netcockpit:1.2", self.repo), "ghcr.io/b2zo0/netcockpit:1.2")
        self.assertEqual(cockpit_image.choose("registry.example.local:5000/netcockpit:main", self.repo),
                         "registry.example.local:5000/netcockpit:main")
        digest = "ghcr.io/b2zo0/netcockpit@sha256:" + "0" * 64
        self.assertEqual(cockpit_image.choose(digest, self.repo), digest)

    def test_command_line(self):
        script = ROOT / "scripts" / "cockpit_image.py"
        run = lambda *a, **env: subprocess.run([sys.executable, str(script), *a], cwd=self.repo, capture_output=True,
                                               text=True, env={**os.environ, **env})
        # the script looks at its own repository, so only check the output format here
        out = run("--tag")
        if out.returncode == 0:
            self.assertRegex(out.stdout.strip(), r"^tree-[0-9a-f]{12}$")
        self.assertEqual(run(COCKPIT_IMAGE="build").stdout.strip(), "")


class NotAGitCheckout(unittest.TestCase):
    def test_installed_from_an_archive_builds_locally(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "cockpit").mkdir()
            with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(Path(tmp).parent)}):
                self.assertIsNone(cockpit_image.cockpit_tag(tmp))
                self.assertEqual(cockpit_image.choose("auto", tmp), "")


class WiredIn(unittest.TestCase):
    """Les morceaux qui doivent rester d'accord entre eux."""

    def test_existing_installs_get_a_safe_default(self):
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("\nCOCKPIT_IMAGE=auto\n", env)

    def test_setup_downloads_then_falls_back_to_building(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/cockpit_image.py", setup)
        self.assertIn("docker tag \"$ref\" netcockpit/cockpit:local", setup)
        self.assertIn("docker compose build -q cockpit", setup)
        self.assertNotIn("up -d --build", setup)  # would rebuild over the downloaded image

    def test_compose_still_uses_the_local_tag(self):
        for f in ("docker-compose.yml", "docker-compose.demo.yml"):
            text = (ROOT / f).read_text(encoding="utf-8")
            self.assertIn("image: netcockpit/cockpit:local", text, f)
            self.assertIn("build: ./cockpit", text, f)

    def test_workflow_uses_the_same_tag_and_name(self):
        wf = (ROOT / ".github" / "workflows" / "image.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/cockpit_image.py --tag", wf)
        self.assertIn('ghcr.io/${GITHUB_REPOSITORY_OWNER,,}/netcockpit', wf)
        self.assertEqual(cockpit_image.DEFAULT_REPO, "ghcr.io/b2zo0/netcockpit")


if __name__ == "__main__":
    unittest.main()
