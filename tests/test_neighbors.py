"""CDP/LLDP neighbours: an IP phone is a phone, not a switch."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cockpit", "app"))
os.environ.setdefault("COCKPIT_SCAN", "0")


class PhoneNeighbour(unittest.TestCase):
    def build(self, links):
        import config as C
        import model as M
        vc = {"up": True, "hosts": [{"name": "esx1.example.local", "ips": ["192.0.2.10"]}], "vms": [], "datastores": [],
              "alarms": [], "links": links}
        scan = {"last_scan": 1000, "devices": {"192.0.2.10": {"last_seen": 1000, "ports": [443]}}}
        return M.build(C.load(), scan, vc, {}, [], [], now=1000)

    def test_yealink_seen_by_an_esxi_is_a_phone_and_not_its_uplink(self):
        mdl = self.build([{"host": "esx1.example.local", "nic": "vmnic1", "proto": "CDP", "switch": "T54W805E0C0DA173",
                           "port": "WAN PORT", "switch_ip": "198.51.100.71", "platform": "Yealink SIP-T54W"}])
        phone = next(n for n in mdl.nodes.values() if n.get("name") == "T54W805E0C0DA173")
        self.assertEqual(phone["role"], "phone")
        esx = next(n for n in mdl.nodes.values() if n.get("ip") == "192.0.2.10")
        self.assertNotEqual(esx.get("parent"), phone["id"])
        self.assertNotIn(phone["id"], mdl.switch_ports)

    def test_phone_recognised_by_its_name_alone(self):
        mdl = self.build([{"host": "esx1.example.local", "nic": "vmnic1", "proto": "LLDP", "switch": "T46U805E0C112233",
                           "port": "WAN PORT", "switch_ip": None, "platform": None}])
        self.assertEqual(next(n for n in mdl.nodes.values() if n.get("name") == "T46U805E0C112233")["role"], "phone")

    def test_a_real_switch_stays_a_switch(self):
        mdl = self.build([{"host": "esx1.example.local", "nic": "vmnic0", "proto": "CDP", "switch": "SW-CORE",
                           "port": "Gi1/0/1", "switch_ip": "192.0.2.2", "platform": "cisco WS-C2960X-48FPD-L"}])
        sw = next(n for n in mdl.nodes.values() if n.get("ip") == "192.0.2.2")
        self.assertEqual(sw["role"], "switch")
        self.assertIn(sw["id"], mdl.switch_ports)


if __name__ == "__main__":
    unittest.main()
