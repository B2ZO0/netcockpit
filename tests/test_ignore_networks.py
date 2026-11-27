"""Networks seen but that are not a building: set in the assistant, no longer flagged as undeclared."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cockpit" / "app"))
os.environ.setdefault("COCKPIT_AUTH", "off")


class Assistant(unittest.TestCase):
    def run_assistant(self, answers, start=None):
        import configure
        with tempfile.TemporaryDirectory() as tmp:
            cfg, env = Path(tmp) / "cockpit.yml", Path(tmp) / ".env"
            if start is not None:
                cfg.write_text(yaml.safe_dump(start), encoding="utf-8")

            def reply(prompt=""):
                for key, value in answers.items():
                    if key in prompt:
                        return value
                return ""
            det = {"nets": ["192.0.2.0/24"], "gw": "192.0.2.1", "dns": ["192.0.2.10"]}
            with mock.patch.object(configure, "CONFIG", cfg), mock.patch.object(configure, "ENVF", env), \
                 mock.patch.object(configure, "detect", return_value=det), \
                 mock.patch.object(configure, "find_hypervisors", return_value={"vmware": [], "proxmox": []}), \
                 mock.patch("sys.stdin", SimpleNamespace(isatty=lambda: True)), \
                 mock.patch("builtins.input", side_effect=reply), mock.patch("builtins.print"), \
                 mock.patch.object(sys, "argv", ["configure.py", "--lang", "en"]):
                self.assertEqual(configure.main(), 0)
            return yaml.safe_load(cfg.read_text(encoding="utf-8"))

    def test_networks_to_ignore_are_saved(self):
        out = self.run_assistant({"Networks to ignore": "192.168.20.0/24, 10.100.18.0", "Save": "y"})
        self.assertEqual(out["ignore_networks"], ["192.168.20.0/24", "10.100.18.0/24"])

    def test_current_list_is_kept_with_enter(self):
        start = {"sites": [{"name": "Building 1", "subnets": ["192.0.2.0/24"]}], "ignore_networks": ["192.168.20.0/24"]}
        out = self.run_assistant({"Save": "y"}, start=start)
        self.assertEqual(out["ignore_networks"], ["192.168.20.0/24"])

    def test_no_key_when_nothing_is_ignored(self):
        self.assertNotIn("ignore_networks", self.run_assistant({"Save": "y"}))


class Undeclared(unittest.TestCase):
    def test_ignored_network_is_not_flagged(self):
        import main
        node = lambda ip: {"ip": ip, "site": "Autres réseaux", "role": "server"}   # noqa: E731
        mdl = SimpleNamespace(nodes={"a": node("192.168.20.2"), "b": node("10.100.18.71"), "c": node("172.16.5.9")})
        with mock.patch.dict(main.CFG, {"ignore_networks": ["192.168.20.0/24", "10.100.18.0/24"]}):
            self.assertEqual([u["subnet"] for u in main.undeclared(mdl)], ["172.16.5.0/24"])
        with mock.patch.dict(main.CFG, {"ignore_networks": []}):
            self.assertEqual(len(main.undeclared(mdl)), 3)

    def test_config_reads_and_checks_the_list(self):
        import config as C
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cockpit.yml"
            p.write_text("ignore_networks: [192.168.20.0/24, 10.100.18.5, not-a-network]\n", encoding="utf-8")
            with mock.patch.object(C, "CONFIG_PATH", p):
                self.assertEqual(C.load()["ignore_networks"], ["192.168.20.0/24", "10.100.18.5/32"])


if __name__ == "__main__":
    unittest.main()
