"""scripts/render_config.py: the secrets it generates from .env stay private to the host user."""
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import render_config  # noqa: E402


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


class SecretFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".env").write_text("TELEGRAM_BOT_TOKEN=123:abc\nTELEGRAM_CHAT_ID=-100123\n"
                                        "SNMP_COMMUNITY=s3cret-community\nAGENT_TOKEN=ci-agent-token-0123456789\n", encoding="utf-8")
        # copies written by earlier versions, readable by every local user
        (self.root / "alertmanager").mkdir()
        (self.root / "alertmanager" / "alertmanager.yml").write_text("old", encoding="utf-8")
        (self.root / "snmp").mkdir()
        (self.root / "snmp" / "auth.yml").write_text("old", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_secrets_live_in_a_private_folder(self):
        render_config.render(self.root)
        folder = self.root / "secrets"
        self.assertEqual(mode(folder), 0o700)
        am, snmp = folder / "alertmanager.yml", folder / "snmp-auth.yml"
        # the containers run as another user and read them through file bind mounts
        self.assertEqual(mode(am), 0o644)
        self.assertEqual(mode(snmp), 0o644)
        cfg = yaml.safe_load(am.read_text(encoding="utf-8"))
        self.assertEqual(cfg["receivers"][1]["telegram_configs"][0]["bot_token"], "123:abc")
        self.assertEqual(json.loads(snmp.read_text(encoding="utf-8").split("\n", 1)[1])["auths"]["site"]["community"],
                         "s3cret-community")

    def test_old_copies_are_removed(self):
        render_config.render(self.root)
        self.assertFalse((self.root / "alertmanager" / "alertmanager.yml").exists())
        self.assertTrue((self.root / "alertmanager").is_dir())      # message templates stay there
        self.assertFalse((self.root / "snmp").exists())

    def test_private_folder_is_fixed_on_every_run(self):
        folder = self.root / "secrets"
        folder.mkdir()
        folder.chmod(0o755)
        render_config.render(self.root)
        self.assertEqual(mode(folder), 0o700)


class Mounts(unittest.TestCase):
    def test_containers_read_the_secret_files_not_a_shared_folder(self):
        services = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
        wanted = {"alertmanager": "./secrets/alertmanager.yml", "snmp-exporter": "./secrets/snmp-auth.yml"}
        for svc, source in wanted.items():
            binds = [v for v in services[svc]["volumes"] if isinstance(v, dict) and v.get("source") == source]
            self.assertEqual(len(binds), 1, svc)
            self.assertTrue(binds[0]["read_only"], svc)
            self.assertFalse(binds[0]["bind"]["create_host_path"], svc)
            target = binds[0]["target"]
            self.assertIn(f"--config.file={target}", services[svc]["command"], svc)
        for svc, conf in services.items():
            for v in conf.get("volumes", []):
                if isinstance(v, str):
                    self.assertFalse(v.startswith(("./secrets:", "./snmp:")), f"{svc}: {v}")


if __name__ == "__main__":
    unittest.main()
