"""Browser-facing protections of the cockpit web server: headers and cross-site requests."""
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "cockpit" / "app"
sys.path.insert(0, str(APP))
os.environ.setdefault("COCKPIT_AUTH", "off")


def _main():
    import main  # noqa: E402  (reads its settings at import)
    return main


class WebSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib
        os.environ["COCKPIT_AUTH"] = "off"       # other tests may have loaded auth with a password
        import auth
        importlib.reload(auth)
        cls.main = _main()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls.main.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def req(self, path, method="GET", headers=None, body=None):
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                                   data=json.dumps(body or {}).encode() if method == "POST" else None,
                                   headers=dict({"Content-Type": "application/json"}, **(headers or {})))
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers)

    def test_headers_forbid_inline_scripts_and_framing(self):
        _, h = self.req("/health")
        csp = h.get("Content-Security-Policy", "")
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline' ; script", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertIn("frame-ancestors 'self'", csp)
        self.assertEqual(h.get("X-Content-Type-Options"), "nosniff")

    def test_no_inline_script_left_in_pages(self):
        static = APP.parent / "static"
        for page in ("index.html", "login.html"):
            html = (static / page).read_text(encoding="utf-8")
            self.assertNotIn("<script>", html, f"{page} has an inline script, blocked by the CSP")

    def test_cross_site_post_is_refused(self):
        code, _ = self.req("/api/rescan", "POST", {"Origin": "https://evil.example", "Host": f"127.0.0.1:{self.port}"})
        self.assertEqual(code, 403)
        code, _ = self.req("/api/rescan", "POST", {"Origin": "null"})
        self.assertEqual(code, 403)

    def test_same_site_and_non_browser_post_are_accepted(self):
        code, _ = self.req("/api/rescan", "POST", {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(code, 202)
        code, _ = self.req("/api/rescan", "POST")   # curl, scripts: no Origin header
        self.assertEqual(code, 202)


class NmapXml(unittest.TestCase):
    def test_entity_declarations_are_refused(self):
        import scanner
        bomb = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaaaaaa"><!ENTITY b "&a;&a;&a;&a;">]><nmaprun>&b;</nmaprun>'
        self.assertEqual(scanner.parse_nmap_xml(bomb), {})


if __name__ == "__main__":
    unittest.main()
