"""Sessions and the cockpit web server under hostile or careless clients."""
import json
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cockpit" / "app"))
from test_auth import load  # noqa: E402


class MachineAccess(unittest.TestCase):
    """/metrics and the Grafana node graph: open to Prometheus and Grafana (local Docker networks), not to people."""

    def test_reverse_proxy_on_this_host_does_not_open_the_inventory(self):
        a = load()
        self.assertFalse(a.allowed("/metrics", "127.0.0.1", None))

    def test_requests_relayed_by_a_proxy_need_a_session(self):
        a = load()
        for h in ("X-Forwarded-For", "Forwarded", "X-Real-IP", "X-Forwarded-Proto", "X-Forwarded-Host"):
            self.assertFalse(a.allowed("/metrics", "172.18.0.5", None, forwarded=True), h)
        self.assertTrue(a.allowed("/metrics", "172.18.0.5", None))

    def test_grafana_node_graph_works_with_login_on(self):
        a = load()
        self.assertTrue(a.allowed("/api/nodegraph", "172.18.0.5", None))
        self.assertFalse(a.allowed("/api/nodegraph", "192.0.2.50", None))
        self.assertFalse(a.allowed("/api/inventory", "172.18.0.5", None))

    def test_metrics_networks_still_open_metrics(self):
        a = load(COCKPIT_METRICS_NETWORKS="127.0.0.1/32")
        self.assertTrue(a.allowed("/metrics", "127.0.0.1", None))


class SessionEnd(unittest.TestCase):
    def test_logout_ends_the_session_for_good(self):
        a = load()
        token, _ = a.new_session()
        a.revoke(token)
        self.assertFalse(a.valid(token))

    def test_new_password_ends_older_sessions(self):
        token, _ = load(COCKPIT_PASSWORD="old-password").new_session()
        self.assertFalse(load(COCKPIT_PASSWORD="new-password").valid(token))
        self.assertTrue(load(COCKPIT_PASSWORD="old-password").valid(token))

    def test_session_key_comes_from_a_slow_password_hash(self):
        # the password only enters the session key through scrypt, never through a fast hash
        src = (Path(__file__).resolve().parent.parent / "cockpit" / "app" / "auth.py").read_text(encoding="utf-8")
        self.assertIn("hashlib.scrypt(PASSWORD.encode()", src)
        self.assertNotRegex(src, r"hmac\.new\([^)]*PASSWORD")

    def test_garbage_cookies_are_refused_without_error(self):
        a = load()
        for token in ("².ab", "1" * 40 + ".ab", "9999999999.éé", ".", "12.", "-5.ab", None, ""):
            self.assertFalse(a.valid(token), repr(token))


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth = load()                 # login on
        import main
        cls.main = main
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), main.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        load(COCKPIT_AUTH="off")

    def raw(self, request: bytes, wait=4):
        with socket.create_connection(("127.0.0.1", self.port), timeout=wait) as s:
            s.sendall(request)
            try:
                return s.recv(200).decode(errors="replace")
            except socket.timeout:
                return "TIMEOUT"

    def test_body_of_an_unauthenticated_post_is_not_read(self):
        # The request announces a body, then sends nothing: refuse at once instead of waiting for it.
        reply = self.raw(b"POST /api/rescan HTTP/1.1\r\nHost: x\r\nContent-Length: 500000\r\n\r\n")
        self.assertTrue(reply.startswith("HTTP/1.0 401"), reply)

    def test_negative_length_is_refused(self):
        reply = self.raw(b"POST /api/login HTTP/1.1\r\nHost: x\r\nContent-Length: -1\r\n\r\n")
        self.assertTrue(reply.startswith("HTTP/1.0 400"), reply)

    def test_login_body_that_is_not_an_object(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/login", data=b"[]", method="POST",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(e.exception.code, 401)

    def test_garbage_cookie_gets_an_answer(self):
        reply = self.raw(b"GET /api/features HTTP/1.1\r\nHost: x\r\nCookie: nc_session=\xb2.ab\r\n\r\n")   # "²": a digit for isdigit()
        self.assertTrue(reply.startswith("HTTP/1.0 401"), reply)

    def test_logout_cookie_no_longer_works(self):
        def call(path, cookie=None, body=b"{}"):
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, method="POST",
                                         headers={"Content-Type": "application/json", **({"Cookie": cookie} if cookie else {})})
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return r.status, r.headers.get("Set-Cookie", "")
            except urllib.error.HTTPError as e:
                return e.code, ""
        status, set_cookie = call("/api/login", body=json.dumps({"password": "s3cret"}).encode())
        self.assertEqual(status, 200)
        cookie = set_cookie.split(";", 1)[0]
        self.assertEqual(call("/api/rescan", cookie)[0], 202)
        self.assertEqual(call("/api/logout", cookie)[0], 200)
        self.assertEqual(call("/api/rescan", cookie)[0], 401)

    def test_idle_connections_are_closed(self):
        self.assertTrue(0 < (self.main.Handler.timeout or 0) <= 60)
        start = time.time()
        with socket.create_connection(("127.0.0.1", self.port), timeout=90) as s:
            old, self.main.Handler.timeout = self.main.Handler.timeout, 1
            try:
                s2 = socket.create_connection(("127.0.0.1", self.port), timeout=10)
                self.assertEqual(s2.recv(10), b"")        # server gave up on the silent client
                s2.close()
            finally:
                self.main.Handler.timeout = old
        self.assertLess(time.time() - start, 10)


if __name__ == "__main__":
    unittest.main()
