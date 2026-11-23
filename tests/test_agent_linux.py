"""Linux agent installer: the LLDP helper runs as root, so nothing the alloy user controls may steer its writes."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = (ROOT / "agents" / "linux" / "install.sh").read_text(encoding="utf-8")


def lldp2prom_source():
    return re.search(r"cat > /usr/local/lib/alloy-lldp/lldp2prom.py <<'EOF'\n(.*?)\nEOF\n", INSTALL, re.S).group(1)


class LldpTextfile(unittest.TestCase):
    def test_textfile_folder_belongs_to_root(self):
        folder = re.search(r"^TEXTFILE=(\S+)", INSTALL, re.M).group(1)
        self.assertFalse(folder.startswith("/var/lib/alloy/"), folder)   # the alloy user's own home
        self.assertNotRegex(INSTALL, r"chown[^\n]*alloy")                 # never handed over to the alloy user

    def test_a_planted_link_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "bin").mkdir()
            (tmp / "bin" / "lldpcli").write_text('#!/bin/sh\necho \'{"lldp":[{"interface":[{"name":"eth0","via":"LLDP",'
                                                  '"chassis":[{"name":[{"value":"sw1"}]}],"port":[{"id":[{"value":"Gi1/0/12"}]}]}]}]}\'\n')
            (tmp / "bin" / "lldpcli").chmod(0o755)
            (tmp / "lldp2prom.py").write_text(lldp2prom_source())
            out_dir = tmp / "textfile"
            out_dir.mkdir()
            victim = tmp / "victim"
            victim.write_text("root-only secret\n")
            victim.chmod(0o600)
            (out_dir / "lldp.prom.tmp").symlink_to(victim)          # what a compromised alloy user could plant
            env = dict(os.environ, PATH=f"{tmp / 'bin'}:{os.environ.get('PATH', '/usr/bin:/bin')}")
            subprocess.run([sys.executable, str(tmp / "lldp2prom.py"), str(out_dir / "lldp.prom")], check=True, env=env)
            self.assertEqual(victim.read_text(), "root-only secret\n")
            self.assertEqual(victim.stat().st_mode & 0o777, 0o600)
            prom = (out_dir / "lldp.prom").read_text()
            self.assertIn('chassis_name="sw1"', prom)
            self.assertEqual((out_dir / "lldp.prom").stat().st_mode & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
