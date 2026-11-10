"""Connecteur Proxmox VE : testé contre une fausse API (adresses de documentation, rien de réel)."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cockpit", "app"))
os.environ.setdefault("COCKPIT_CONFIG", os.path.join(ROOT, "config", "cockpit.example.yml"))
os.environ.setdefault("COCKPIT_DATA", tempfile.mkdtemp())

from proxmox import Proxmox, merge_states  # noqa: E402

GB = 1073741824
TOKEN = "PVEAPIToken=netcockpit@pve!cockpit=11111111-2222-3333-4444-555555555555"
API = {
    "/cluster/resources": [
        {"type": "node", "node": "pve1", "status": "online", "cpu": 0.25, "maxcpu": 8, "mem": 16 * GB, "maxmem": 32 * GB, "uptime": 86400},
        {"type": "node", "node": "pve2", "status": "offline", "maxcpu": 8, "maxmem": 32 * GB},
        {"type": "qemu", "vmid": 100, "name": "web01", "node": "pve1", "status": "running", "cpu": 0.5, "maxcpu": 2,
         "mem": 1 * GB, "maxmem": 4 * GB, "maxdisk": 32 * GB, "uptime": 3600},
        {"type": "qemu", "vmid": 101, "name": "win-test", "node": "pve1", "status": "stopped", "maxcpu": 4, "maxmem": 8 * GB, "maxdisk": 64 * GB},
        {"type": "qemu", "vmid": 9000, "name": "debian-template", "node": "pve1", "status": "stopped", "template": 1},
        {"type": "lxc", "vmid": 200, "name": "dns01", "node": "pve1", "status": "running", "cpu": 0.01, "maxcpu": 1,
         "mem": 128 * 1048576, "maxmem": 512 * 1048576, "maxdisk": 8 * GB, "uptime": 7200},
        {"type": "storage", "storage": "local-zfs", "node": "pve1", "status": "available", "plugintype": "zfspool", "disk": 90 * GB, "maxdisk": 100 * GB},
        {"type": "storage", "storage": "nas", "node": "pve1", "status": "available", "plugintype": "nfs", "shared": 1, "disk": 100 * GB, "maxdisk": 1000 * GB},
        {"type": "storage", "storage": "nas", "node": "pve2", "status": "unknown", "plugintype": "nfs", "shared": 1},
    ],
    "/cluster/status": [{"type": "cluster", "name": "lab"}, {"type": "node", "name": "pve1", "ip": "192.0.2.11"},
                        {"type": "node", "name": "pve2", "ip": "192.0.2.12"}],
    "/nodes/pve1/status": {"pveversion": "pve-manager/8.2.4/faa83925c9641325", "cpuinfo": {"model": "Intel(R) Xeon(R) E-2278G", "mhz": "3400.000", "cpus": 8}},
    "/nodes/pve1/qemu/100/config": {"ostype": "l26", "net0": "virtio=BC:24:11:AA:BB:01,bridge=vmbr0,firewall=1"},
    "/nodes/pve1/qemu/101/config": {"ostype": "win11", "net0": "e1000=BC:24:11:AA:BB:02,bridge=vmbr0"},
    "/nodes/pve1/lxc/200/config": {"ostype": "debian", "net0": "name=eth0,bridge=vmbr0,hwaddr=BC:24:11:AA:BB:03,ip=dhcp"},
    "/nodes/pve1/lxc/200/interfaces": [{"name": "lo", "inet": "127.0.0.1/8"}, {"name": "eth0", "inet": "192.0.2.53/24"}],
    # /nodes/pve1/qemu/100/agent/network-get-interfaces : absent exprès (pas d'agent invité) -> 500
}


class Fake(BaseHTTPRequestHandler):
    token = TOKEN

    def do_GET(self):
        path = self.path.replace("/api2/json", "", 1)
        if self.headers.get("Authorization") != self.token:
            return self._send(401, {"data": None})
        if path not in API:
            return self._send(500, {"data": None})
        self._send(200, {"data": API[path]})

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class ProxmoxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def pve(self, secret="11111111-2222-3333-4444-555555555555"):
        return Proxmox(self.url, "netcockpit@pve!cockpit", secret)

    def test_poll(self):
        st = self.pve().poll()
        self.assertTrue(st["up"], st["error"])
        hosts = {h["name"]: h for h in st["hosts"]}
        self.assertEqual(hosts["pve1"]["state"], "connected")
        self.assertEqual(hosts["pve1"]["ips"], ["192.0.2.11"])
        self.assertEqual(hosts["pve1"]["version"], "Proxmox VE 8.2.4")
        self.assertEqual(hosts["pve1"]["cpu_pct"], 25.0)
        self.assertEqual(hosts["pve1"]["mem_pct"], 50.0)
        self.assertEqual(hosts["pve1"]["cluster"], "lab")
        self.assertEqual(hosts["pve2"]["state"], "disconnected")
        vms = {v["name"]: v for v in st["vms"]}
        self.assertNotIn("debian-template", vms)
        self.assertEqual(vms["web01"]["power"], "poweredOn")
        self.assertEqual(vms["web01"]["macs"], ["bc:24:11:aa:bb:01"])
        self.assertEqual(vms["web01"]["ips"], [])                       # pas d'agent invité : pas d'erreur
        self.assertEqual(vms["web01"]["cpu_pct"], 50.0)
        self.assertEqual(vms["win-test"]["power"], "poweredOff")
        self.assertIn("Windows 11", vms["win-test"]["os"])
        self.assertEqual(vms["dns01"]["ips"], ["192.0.2.53"])
        self.assertEqual(vms["dns01"]["kind"], "lxc")
        ds = {d["name"]: d for d in st["datastores"]}
        self.assertEqual(ds["local-zfs (pve1)"]["used_pct"], 90.0)
        self.assertEqual(ds["nas"]["hosts"], ["pve1", "pve2"])         # stockage partagé : une seule ligne
        self.assertEqual(ds["nas"]["capacity_gb"], 1000)

    def test_bad_token(self):
        st = self.pve("wrong").poll()
        self.assertFalse(st["up"])
        self.assertIn("401", st["error"])

    def test_unreachable(self):
        st = Proxmox("http://127.0.0.1:9", "a@pve!b", "c", timeout=1).poll()
        self.assertFalse(st["up"])

    def test_merge(self):
        a = {"up": True, "error": "", "hosts": [{"name": "esx1"}], "vms": [], "datastores": [], "alarms": [], "links": [{"x": 1}], "updated": 1}
        b = self.pve().poll()
        self.assertIs(merge_states([a, None]), a)
        self.assertIsNone(merge_states([None, None]))
        m = merge_states([a, b])
        self.assertEqual(len(m["hosts"]), 3)
        self.assertIs(m["hosts"][1], b["hosts"][0])                     # mêmes objets : le modèle les retrouve
        self.assertEqual(m["links"], [{"x": 1}])

    def test_model(self):
        """Les nœuds et VM Proxmox entrent dans la carte ; une VM sans agent retrouve son IP par sa MAC."""
        import config as C
        import model as M
        cfg = C.load()
        st = self.pve().poll()
        scan = {"last_scan": 1000, "devices": {
            "192.0.2.80": {"mac": "bc:24:11:aa:bb:01", "last_seen": 1000, "ports": [22, 80]}}}
        mdl = M.build(cfg, scan, st, {}, [], [], now=1000)
        by_name = {(n.get("vm") or n.get("esxi") or {}).get("name"): n for n in mdl.nodes.values() if n.get("vm") or n.get("esxi")}
        self.assertEqual(by_name["pve1"]["role"], "hypervisor")
        self.assertEqual(by_name["web01"]["ip"], "192.0.2.80")
        self.assertEqual(by_name["web01"]["parent"], by_name["pve1"]["id"])
        self.assertEqual(sum(1 for n in mdl.nodes.values() if n.get("ip") == "192.0.2.80"), 1)   # pas de doublon
        for n in mdl.nodes.values():            # l'état en direct (Prometheus) n'est pas simulé ici
            n.setdefault("status", "up")
        view = M.vmware_view(mdl, st)
        self.assertEqual({h["name"]: len(h["vms"]) for h in view["hosts"]}, {"pve1": 3, "pve2": 0})


if __name__ == "__main__":
    unittest.main()
