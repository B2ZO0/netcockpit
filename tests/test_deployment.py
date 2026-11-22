"""Deployment files: what the stack exposes on the network stays limited to what NetCockpit needs."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def compose():
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    unittest.main()
