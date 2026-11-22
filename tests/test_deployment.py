"""Deployment files: what the stack exposes on the network stays limited to what NetCockpit needs."""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def compose(name="docker-compose.yml"):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


class Deployment(unittest.TestCase):
    def test_prometheus_has_no_http_control_endpoints(self):
        # Agents only need remote write; setup.sh restarts Prometheus with docker compose.
        cmd = compose()["services"]["prometheus"]["command"]
        self.assertIn("--web.enable-remote-write-receiver", cmd)
        for flag in ("--web.enable-lifecycle", "--web.enable-admin-api"):
            self.assertNotIn(flag, cmd)

    def test_loki_refuses_log_deletion_but_keeps_retention(self):
        loki = yaml.safe_load((ROOT / "loki" / "loki.yml").read_text(encoding="utf-8"))
        self.assertEqual(loki["limits_config"].get("deletion_mode"), "disabled")
        self.assertTrue(loki["compactor"]["retention_enabled"])
        self.assertEqual(loki["limits_config"]["retention_period"], "30d")

    def test_alertmanager_listens_on_the_host_only(self):
        self.assertEqual(compose()["services"]["alertmanager"]["ports"], ["127.0.0.1:9093:9093"])


class LocalImages(unittest.TestCase):
    def test_images_built_here_can_only_come_from_this_machine(self):
        # "localhost/" is a registry name: no public registry can ever serve this image,
        # even to "docker compose pull" or an automatic image updater.
        for name in ("docker-compose.yml", "docker-compose.demo.yml"):
            for svc, conf in compose(name)["services"].items():
                if "build" in conf:
                    self.assertTrue(conf.get("image", "").startswith("localhost/"), f"{name}: {svc}")

    def test_setup_and_ci_use_the_local_only_name(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertIn('docker tag "$ref" localhost/netcockpit/cockpit:local', setup)
        self.assertIn("localhost/netcockpit/cockpit:local python /app/app/configure.py", setup)
        self.assertNotIn(" netcockpit/cockpit:local python", setup)
        wf = (ROOT / ".github" / "workflows" / "image.yml").read_text(encoding="utf-8")
        self.assertNotIn(" netcockpit/cockpit:test", wf)


class PinnedVersions(unittest.TestCase):
    """Every image of the stack has a tested version: an update moves to it, a new install gets it."""

    def test_no_image_defaults_to_latest(self):
        for svc, conf in compose()["services"].items():
            image = conf["image"]
            if "build" in conf:
                continue
            # ${PROMETHEUS_VERSION:-v3.16.0} -> v3.16.0 (what you get without a setting in .env)
            resolved = re.sub(r"\$\{[A-Z0-9_]+:-([^}]*)\}", r"\1", image)
            self.assertNotIn("${", resolved, f"{svc}: {image} has no default version")
            name, _, tag = resolved.rpartition(":")
            self.assertTrue(name and tag, f"{svc}: {image} has no tag")
            self.assertNotEqual(tag, "latest", f"{svc}: {image}")
            self.assertRegex(tag, r"\d", f"{svc}: {image}")

    def test_update_downloads_the_versions_of_the_release(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertIn("export NETCOCKPIT_UPDATING=1", setup)
        start = setup.index("# ------------------------------------------------------------------ 5. démarrage")
        pull = setup.index("docker compose pull --quiet --ignore-buildable", start)
        self.assertLess(pull, setup.index("docker compose up -d", start))


if __name__ == "__main__":
    unittest.main()
