"""Data and errors coming back from integrations (AI provider, Zabbix, agents) are handled safely."""
import os
import sys
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cockpit" / "app"))


class Failing(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(503)
        self.send_header("Content-Length", "4")
        self.end_headers()
        self.wfile.write(b"busy")

    def log_message(self, *a):
        pass


class AiErrors(unittest.TestCase):
    def test_credentials_in_the_ai_url_never_reach_the_browser_or_the_logs(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Failing)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://ollama-user:Ollama-Pass@127.0.0.1:{srv.server_address[1]}/v1"
        try:
            import ai
            with mock.patch.multiple(ai.C, AI_PROVIDER="openai", AI_API_KEY="k", AI_MODEL="m", AI_BASE_URL=url):
                with self.assertLogs("cockpit.ai", level="WARNING") as logs:
                    out = ai.ask("t", "prompt")
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertIn("503", out["error"])
        self.assertNotIn("Ollama-Pass", out["error"])
        self.assertNotIn("Ollama-Pass", "\n".join(logs.output))


class ZabbixPassword(unittest.TestCase):
    def test_empty_admin_password_is_refused_not_left_at_the_default(self):
        import zabbix
        z = zabbix.Zabbix("http://127.0.0.1:9/api_jsonrpc.php", "")
        calls = []
        z.call = lambda method, params=None: calls.append(method) or ("7.0.0" if method == "apiinfo.version" else "tok")
        with self.assertRaises(zabbix.ZabbixError):
            z.login()
        self.assertNotIn("user.login", calls)


class Addresses(unittest.TestCase):
    def test_one_malformed_address_does_not_break_the_inventory(self):
        import model
        node = {"status": "up", "name": "x", "role_label": "Server", "role": "server", "category": "server",
                "sources": ["agent"], "alerts": [], "parent": None}
        nodes = {"a": dict(node, id="a", ip="1..2"), "b": dict(node, id="b", ip="192.0.2.20"), "c": dict(node, id="c", ip="192.0.2.3")}
        m = types.SimpleNamespace(nodes=nodes, switch_ports={})
        with mock.patch.object(model, "inventory", wraps=model.inventory):
            rows = model.inventory(m)
        self.assertEqual([r["ip"] for r in rows][:2], ["192.0.2.3", "192.0.2.20"])

    def test_only_real_addresses_become_probe_targets(self):
        import main
        self.assertTrue(main.probe_address("192.0.2.20"))
        for bad in ("1..2", "intranet.example.local", "192.0.2.1:22", "-oProxy", "", None):
            self.assertFalse(main.probe_address(bad), bad)


if __name__ == "__main__":
    unittest.main()
