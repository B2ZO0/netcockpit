"""Build the static online demo (GitHub Pages) from the simulated demo.

Runs demo/demo.py locally, records every API answer the interface needs, then writes
a static copy of the interface that reads those answers instead of a live server.

    python scripts/build_pages_demo.py [output_dir]      (default: _site)

Everything comes from the simulated network of demo/demo.py: fictitious names and addresses only."""
import json, os, shutil, subprocess, sys, time, urllib.request
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_site"))
PORT = "18088"
BASE = f"http://127.0.0.1:{PORT}/"
REPO = "https://github.com/B2ZO0/netcockpit"


def fnv(s):
    """FNV-1a 32 bits, identical to the JavaScript version in demo-shim.js."""
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def key(name, site="", id_="", lang=""):
    return fnv(f"{name}|{site}|{id_}|{lang}")


def get(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    env = dict(os.environ, COCKPIT_PORT=PORT)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "demo", "demo.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                f = json.loads(get("api/features"))
                if f.get("last_scan"):
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            sys.exit("demo did not start")
        time.sleep(20)  # second scan done: some devices show as absent, like a real network

        if os.path.isdir(OUT):
            shutil.rmtree(OUT)
        shutil.copytree(os.path.join(ROOT, "cockpit", "static"), OUT)
        data = os.path.join(OUT, "data")
        os.makedirs(data)
        os.makedirs(os.path.join(OUT, "api"))

        def save(k, raw):
            with open(os.path.join(data, k + ".json"), "wb") as fh:
                fh.write(raw)

        feats = json.loads(get("api/features"))
        sites = [""] + feats.get("sites", [])
        for name in ("overview", "graph", "inventory", "vmware", "switches", "alerts", "services", "setup", "features"):
            for s in sites:
                save(key(name, s), get(f"api/{name}" + (f"?site={quote(s)}" if s else "")))
        ids = [n["id"] for n in json.loads(get("api/graph"))["nodes"]]
        for i in ids:
            save(key("node", "", i), get(f"api/node?id={quote(i)}"))
            for lang in ("fr", "en"):
                save(key("ai/explain", "", i, lang), get("api/ai/explain", {"id": i, "lang": lang}))
        for lang in ("fr", "en"):
            save(key("ai/summary", "", "", lang), get("api/ai/summary", {"lang": lang}))
        with open(os.path.join(OUT, "api", "inventory.csv"), "wb") as fh:
            fh.write(get("api/inventory.csv"))
        with open(os.path.join(data, "meta.json"), "w") as fh:
            json.dump({"snapshot": feats["now"], "repo": REPO}, fh)

        html = open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
        shim = open(os.path.join(ROOT, "scripts", "demo-shim.js"), encoding="utf-8").read()
        html = html.replace('<script src="lib/cytoscape.min.js"></script>',
                            f"<script>\n{shim}\n</script>\n" + '<script src="lib/cytoscape.min.js"></script>', 1)
        open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
        open(os.path.join(OUT, ".nojekyll"), "w").close()
        print(f"static demo: {OUT} ({len(os.listdir(data))} answers, {len(ids)} devices)")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
