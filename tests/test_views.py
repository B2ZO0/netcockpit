"""API views follow the building filter the same way on every screen."""
import json
import os
import sys
import threading
import time
import types
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


if __name__ == "__main__":
    unittest.main()
