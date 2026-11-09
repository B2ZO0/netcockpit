"""Tests des règles de connexion et d'accès (cockpit/app/auth.py)."""
import importlib
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cockpit" / "app"))

IP_ADDR = json.dumps([
    {"ifname": "lo", "addr_info": [{"local": "127.0.0.1", "prefixlen": 8}]},
    {"ifname": "eth0", "addr_info": [{"local": "192.0.2.10", "prefixlen": 24}]},
    {"ifname": "docker0", "addr_info": [{"local": "172.17.0.1", "prefixlen": 16}]},
    {"ifname": "br-3f2a9c1d0e4b", "addr_info": [{"local": "172.18.0.1", "prefixlen": 16}]},
])


def load(**env):
    """Recharge le module avec un environnement donné (il lit ses réglages à l'import)."""
    base = {"COCKPIT_PASSWORD": "s3cret", "COCKPIT_SECRET": "k" * 64, "COCKPIT_AUTH": "on",
            "COCKPIT_TRUSTED_NETWORKS": "", "COCKPIT_METRICS_NETWORKS": "", "COCKPIT_SESSION_HOURS": "12"}
    base.update(env)
    with mock.patch.dict(os.environ, base):
        import auth
        mod = importlib.reload(auth)
    mod.docker_networks = lambda: mod._parse_docker_networks(IP_ADDR)
    return mod


class Sessions(unittest.TestCase):
    def test_new_session_is_valid(self):
        a = load()
        token, age = a.new_session()
        self.assertTrue(a.valid(token))
        self.assertEqual(age, 12 * 3600)

    def test_tampered_or_malformed_tokens_are_rejected(self):
        a = load()
        token, _ = a.new_session()
        exp, _, mac = token.partition(".")
        self.assertFalse(a.valid(f"{int(exp) + 3600}.{mac}"))   # durée rallongée à la main
        self.assertFalse(a.valid(exp + "." + "0" * len(mac)))
        for bad in (None, "", "abc", "12345", ".", "x.y"):
            self.assertFalse(a.valid(bad))

    def test_expired_token_is_rejected(self):
        a = load()
        self.assertFalse(a.valid(a._sign(int(time.time()) - 1)))

    def test_token_signed_with_another_secret_is_rejected(self):
        token, _ = load(COCKPIT_SECRET="a" * 64).new_session()
        self.assertFalse(load(COCKPIT_SECRET="b" * 64).valid(token))

    def test_cookie_value(self):
        a = load()
        self.assertEqual(a.cookie_value("x=1; nc_session=abc.def; y=2"), "abc.def")
        self.assertIsNone(a.cookie_value("x=1"))
        self.assertIsNone(a.cookie_value(None))


class Access(unittest.TestCase):
    def test_login_required_for_api_and_pages(self):
        a = load()
        self.assertFalse(a.allowed("/api/overview", "192.0.2.50", None))
        self.assertFalse(a.allowed("/", "192.0.2.50", None))
        token, _ = a.new_session()
        self.assertTrue(a.allowed("/api/overview", "192.0.2.50", f"nc_session={token}"))

    def test_public_paths(self):
        a = load()
        for path in ("/login", "/api/login", "/health", "/agents/linux/install.sh", "/style.css"):
            self.assertTrue(a.allowed(path, "192.0.2.50", None), path)

    def test_trusted_network_skips_login(self):
        a = load(COCKPIT_TRUSTED_NETWORKS="192.0.2.50/32, 10.0.9.0/24")
        self.assertTrue(a.allowed("/api/overview", "192.0.2.50", None))
        self.assertTrue(a.allowed("/api/overview", "10.0.9.7", None))
        self.assertFalse(a.allowed("/api/overview", "192.0.2.51", None))

    def test_auth_off_opens_everything(self):
        a = load(COCKPIT_AUTH="off")
        self.assertTrue(a.allowed("/api/overview", "192.0.2.50", None))
        self.assertTrue(a.allowed("/metrics", "192.0.2.50", None))

    def test_missing_password_closes_everything_but_public_pages(self):
        a = load(COCKPIT_PASSWORD="")
        self.assertTrue(a.misconfigured())
        self.assertFalse(a.allowed("/api/overview", "192.0.2.50", None))
        self.assertFalse(a.allowed("/api/login", "192.0.2.50", None))
        self.assertTrue(a.allowed("/login", "192.0.2.50", None))
        self.assertFalse(a.allowed("/metrics", "192.0.2.50", None))


class Metrics(unittest.TestCase):
    def test_lan_cannot_read_metrics_without_session(self):
        a = load()
        self.assertFalse(a.allowed("/metrics", "192.0.2.50", None))
        self.assertFalse(a.allowed("/metrics", "192.0.2.10", None))   # eth0 n'est pas une interface Docker

    def test_local_host_and_docker_networks_can_scrape(self):
        a = load()
        for ip in ("127.0.0.1", "172.17.0.2", "172.18.0.5"):
            self.assertTrue(a.allowed("/metrics", ip, None), ip)

    def test_only_metrics_is_opened_to_docker_networks(self):
        a = load()
        self.assertFalse(a.allowed("/api/inventory", "172.18.0.5", None))

    def test_extra_metrics_networks(self):
        a = load(COCKPIT_METRICS_NETWORKS="192.0.2.10/32")
        self.assertTrue(a.allowed("/metrics", "192.0.2.10", None))
        self.assertFalse(a.allowed("/metrics", "192.0.2.11", None))

    def test_session_and_trusted_network_still_work(self):
        a = load(COCKPIT_TRUSTED_NETWORKS="192.0.2.50/32")
        self.assertTrue(a.allowed("/metrics", "192.0.2.50", None))
        token, _ = a.new_session()
        self.assertTrue(a.allowed("/metrics", "192.0.2.99", f"nc_session={token}"))

    def test_bad_ip_json_is_ignored(self):
        a = load()
        self.assertEqual(a._parse_docker_networks("not json"), [])
        self.assertEqual(a._parse_docker_networks(""), [])


class BruteForce(unittest.TestCase):
    def test_five_failures_block_the_address(self):
        a = load()
        for _ in range(5):
            self.assertEqual(a.check_password("192.0.2.66", "wrong"), (False, 0))
        ok, wait = a.check_password("192.0.2.66", "s3cret")
        self.assertFalse(ok)
        self.assertGreater(wait, 0)
        self.assertEqual(a.check_password("192.0.2.67", "s3cret"), (True, 0))   # une autre adresse n'est pas bloquée

    def test_success_resets_the_counter(self):
        a = load()
        for _ in range(4):
            a.check_password("192.0.2.70", "wrong")
        self.assertEqual(a.check_password("192.0.2.70", "s3cret"), (True, 0))
        for _ in range(4):
            self.assertEqual(a.check_password("192.0.2.70", "wrong"), (False, 0))


if __name__ == "__main__":
    unittest.main()
