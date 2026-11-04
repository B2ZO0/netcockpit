"""Notes de release GitHub depuis CHANGELOG.md : python3 scripts/release_notes.py 1.2.0"""
import re
import sys
from pathlib import Path

version = sys.argv[1]
changelog = Path(__file__).resolve().parent.parent.joinpath("CHANGELOG.md").read_text(encoding="utf-8")
m = re.search(rf"^## {re.escape(version)}\s*\n(.*?)(?=^## |\Z)", changelog, re.S | re.M)
if not m:
    sys.exit(f"version {version} absente de CHANGELOG.md")

print(f"""**Your whole infrastructure, live, in one cockpit.** English · Français

![NetCockpit](https://raw.githubusercontent.com/B2ZO0/netcockpit/main/docs/images/demo.gif)

### What's new in {version}

{m.group(1).strip()}

### Try it in one minute

```bash
git clone https://github.com/B2ZO0/netcockpit.git && cd netcockpit
docker compose -f docker-compose.demo.yml up --build   # http://localhost:8088
```

### Upgrade

```bash
git pull && ./setup.sh
```

Your `.env` and `config/cockpit.yml` are never overwritten, and `setup.sh` backs them up to `backups/` first.

⭐ If NetCockpit saves you time, a star helps other admins find it.""")
