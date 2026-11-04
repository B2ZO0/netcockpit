"""Clients Prometheus, Alertmanager et Loki (lecture seule)."""
import logging
import time

import requests

import config as C

log = logging.getLogger("netmap.sources")
_http = requests.Session()
_http.trust_env = False   # services locaux : pas de proxy


def prom(q):
    try:
        r = _http.get(f"{C.PROM_URL}/api/v1/query", params={"query": q}, timeout=8)
        r.raise_for_status()
        return r.json()["data"]["result"]
    except Exception as e:
        log.debug("Prometheus (%s) : %s", q[:70], e)
        return None


def prom_map(q, key="instance", strip_port=False):
    out = {}
    for r in prom(q) or []:
        k = r["metric"].get(key, "")
        if strip_port and k.count(":") == 1:
            k = k.split(":")[0]
        try:
            out[k] = float(r["value"][1])
        except (ValueError, IndexError, KeyError):
            pass
    return out


def prom_range(q, hours=24, step=None):
    end = time.time()
    start = end - hours * 3600
    step = step or max(60, int(hours * 3600 / 120))
    try:
        r = _http.get(f"{C.PROM_URL}/api/v1/query_range",
                      params={"query": q, "start": start, "end": end, "step": step}, timeout=10)
        r.raise_for_status()
        res = r.json()["data"]["result"]
    except Exception as e:
        log.debug("Prometheus range (%s) : %s", q[:70], e)
        return []
    out = []
    for s in res:
        out.append({"labels": s["metric"], "points": [[int(float(t)), float(v)] for t, v in s["values"]]})
    return out


def alertmanager_alerts():
    """Alertes actives non silencieuses/inhibées, avec annotations et date de début."""
    try:
        r = _http.get(f"{C.ALERTMANAGER_URL}/api/v2/alerts",
                      params={"active": "true", "silenced": "false", "inhibited": "false"}, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.debug("Alertmanager : %s", e)
        return None


def loki_logs(selector, hours=6, limit=40):
    end = time.time_ns()
    start = end - hours * 3600 * 10 ** 9
    try:
        r = _http.get(f"{C.LOKI_URL}/loki/api/v1/query_range",
                      params={"query": selector, "start": start, "end": end, "limit": limit, "direction": "backward"},
                      timeout=10)
        r.raise_for_status()
        lines = []
        for stream in r.json()["data"]["result"]:
            lab = stream.get("stream", {})
            for ts, line in stream.get("values", []):
                lines.append({"ts": int(ts) / 1e9, "line": line[:500], "level": lab.get("level"),
                              "unit": lab.get("unit") or lab.get("source") or lab.get("app")})
        lines.sort(key=lambda x: x["ts"], reverse=True)
        return lines[:limit]
    except Exception as e:
        log.debug("Loki (%s) : %s", selector, e)
        return []


def loki_count(expr):
    try:
        r = _http.get(f"{C.LOKI_URL}/loki/api/v1/query", params={"query": expr}, timeout=10)
        r.raise_for_status()
        res = r.json()["data"]["result"]
        return sum(float(x["value"][1]) for x in res) if res else 0
    except Exception:
        return None


# Expressions Linux + Windows communes (par instance)
CPU = ('(100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
       ' or (100 - avg by (instance) (rate(windows_cpu_time_total{mode="idle"}[5m])) * 100)')
MEM = ('max by (instance) ((1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)'
       ' or max by (instance) ((1 - max by (instance) (windows_memory_physical_free_bytes or windows_os_physical_memory_free_bytes)'
       ' / max by (instance) (windows_memory_physical_total_bytes or windows_cs_physical_memory_bytes)) * 100)')
DISK = ('max by (instance) ((1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"}'
        ' / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"}) * 100)'
        ' or max by (instance) ((1 - windows_logical_disk_free_bytes{volume!~"HarddiskVolume.*"}'
        ' / windows_logical_disk_size_bytes{volume!~"HarddiskVolume.*"}) * 100)')
UPTIME = 'max by (instance) (time() - (node_boot_time_seconds or windows_system_boot_time_timestamp_seconds))'
