"""Interrogation de Proxmox VE (lecture seule, jeton d'API) : nœuds, VM QEMU, conteneurs LXC, stockages.

L'état produit a la même forme que celui de vcenter.py (hosts, vms, datastores, alarms), pour que la carte,
la vue Virtualisation, les métriques et les alertes fonctionnent de la même façon avec les deux plateformes.
"""
import logging
import re
import time
from urllib.parse import urlparse

import requests

log = logging.getLogger("cockpit.proxmox")
GB = 1073741824
OSTYPES = {"l26": "Linux", "l24": "Linux", "win11": "Windows 11 / Server 2022", "win10": "Windows 10 / Server 2016-2019",
           "win8": "Windows 8 / Server 2012", "win7": "Windows 7 / Server 2008 R2", "wxp": "Windows XP", "w2k": "Windows 2000",
           "w2k3": "Windows Server 2003", "w2k8": "Windows Server 2008", "wvista": "Windows Vista", "solaris": "Solaris", "other": ""}
MAC_RE = re.compile(r"(?:^|[=,])((?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})(?:,|$)")


def _pct(used, total):
    return round(used / total * 100, 1) if total else None


class Proxmox:
    def __init__(self, url, token_id, token_secret, verify_tls=False, timeout=8):
        u = urlparse(url if "://" in url else f"https://{url}")
        self.host = u.hostname
        self.base = f"{u.scheme}://{u.hostname}:{u.port or 8006}/api2/json"
        self.http = requests.Session()
        self.http.headers["Authorization"] = f"PVEAPIToken={token_id}={token_secret}"
        self.http.verify = verify_tls
        self.timeout = timeout
        self._guest_cache = {}      # (type, vmid) -> (date, {"macs", "os", "ips"})
        self.state = {"up": False, "error": "pas encore interrogé", "hosts": [], "vms": [], "datastores": [],
                      "alarms": [], "links": [], "updated": 0}
        if not verify_tls:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:  # pragma: no cover
                pass

    def _get(self, path):
        r = self.http.get(self.base + path, timeout=self.timeout)
        if r.status_code == 401:
            raise RuntimeError("jeton d'API refusé (401) : vérifie PROXMOX_TOKEN_ID et PROXMOX_TOKEN_SECRET")
        if r.status_code == 403:
            raise RuntimeError(f"droits insuffisants (403) sur {path} : donne le rôle PVEAuditor au jeton")
        r.raise_for_status()
        return r.json().get("data")

    # ------------------------------------------------------------ détails d'une VM ou d'un conteneur (cache 10 min)
    def _guest(self, kind, node, vmid, running):
        key = (kind, vmid)
        cached = self._guest_cache.get(key)
        if cached and time.time() - cached[0] < 600 and cached[1].get("running") == running:
            return cached[1]
        info = {"macs": [], "ips": [], "os": "", "running": running}
        try:
            conf = self._get(f"/nodes/{node}/{kind}/{vmid}/config") or {}
            for k, v in conf.items():
                if re.fullmatch(r"net\d+", k) and isinstance(v, str):
                    info["macs"] += [m.lower() for m in MAC_RE.findall(v)]
            info["os"] = OSTYPES.get(conf.get("ostype"), conf.get("ostype") or "") if kind == "qemu" \
                else (str(conf.get("ostype") or "Linux").capitalize() + " (LXC)")
        except Exception as e:
            log.debug("config %s/%s : %s", kind, vmid, e)
        if running:
            try:
                if kind == "lxc":
                    for itf in self._get(f"/nodes/{node}/lxc/{vmid}/interfaces") or []:
                        ip = (itf.get("inet") or "").split("/")[0]
                        if ip and not ip.startswith("127."):
                            info["ips"].append(ip)
                else:   # agent invité QEMU : facultatif (droit VM.Monitor / VM.GuestAgent.Audit et agent installé)
                    res = self._get(f"/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces") or {}
                    for itf in res.get("result") or []:
                        for a in itf.get("ip-addresses") or []:
                            ip = a.get("ip-address") or ""
                            if a.get("ip-address-type") == "ipv4" and not ip.startswith(("127.", "169.254.")):
                                info["ips"].append(ip)
            except Exception as e:  # pas d'agent ou pas le droit : la carte retrouvera l'IP par l'adresse MAC
                log.debug("IP %s/%s : %s", kind, vmid, e)
        self._guest_cache[key] = (time.time(), info)
        return info

    # ------------------------------------------------------------ collecte (2 min)
    def poll(self):
        try:
            resources = self._get("/cluster/resources") or []
            cluster_name, node_ips = None, {}
            try:
                for c in self._get("/cluster/status") or []:
                    if c.get("type") == "cluster":
                        cluster_name = c.get("name")
                    elif c.get("type") == "node" and c.get("ip"):
                        node_ips[c.get("name")] = c["ip"]
            except Exception as e:
                log.debug("cluster/status : %s", e)
            hosts = []
            for n in (r for r in resources if r.get("type") == "node"):
                name = n.get("node")
                online = n.get("status") == "online"
                cores = n.get("maxcpu") or 0
                model = version = ""
                mhz = 0.0
                if online:
                    try:
                        st = self._get(f"/nodes/{name}/status") or {}
                        ci = st.get("cpuinfo") or {}
                        model = ci.get("model") or ""
                        mhz = float(ci.get("mhz") or 0) * (ci.get("cpus") or cores)
                        pv = (st.get("pveversion") or "").split("/")
                        version = f"Proxmox VE {pv[1]}" if len(pv) > 1 else "Proxmox VE"
                    except Exception as e:
                        log.debug("nodes/%s/status : %s", name, e)
                ip = node_ips.get(name)
                if not ip and len([r for r in resources if r.get("type") == "node"]) == 1 and re.fullmatch(r"[\d.]+", self.host or ""):
                    ip = self.host
                cpu = n.get("cpu") or 0
                mem, maxmem = n.get("mem") or 0, n.get("maxmem") or 0
                hosts.append({
                    "platform": "proxmox", "moid": f"pve/node/{name}", "name": name, "ips": [ip] if ip else [],
                    "state": "connected" if online else "disconnected", "maintenance": False,
                    "power": "poweredOn" if online else "unknown", "health": "green" if online else "red",
                    "model": model, "version": version or "Proxmox VE", "cluster": cluster_name, "cores": cores,
                    "cpu_mhz_total": round(mhz), "cpu_mhz_used": round(cpu * mhz),
                    "cpu_pct": round(cpu * 100, 1) if online else None,
                    "mem_gb": round(maxmem / GB, 1), "mem_used_gb": round(mem / GB, 1),
                    "mem_pct": _pct(mem, maxmem) if online else None, "uptime_s": n.get("uptime"),
                })
            vms, seen = [], set()
            for g in (r for r in resources if r.get("type") in ("qemu", "lxc")):
                if g.get("template"):
                    continue
                kind, vmid, node = g["type"], g.get("vmid"), g.get("node")
                running = g.get("status") == "running"
                seen.add((kind, vmid))
                info = self._guest(kind, node, vmid, running)
                maxmem = g.get("maxmem") or 0
                vms.append({
                    "platform": "proxmox", "kind": kind, "vmid": vmid, "moid": f"pve/{kind}/{vmid}",
                    "name": g.get("name") or f"{kind}-{vmid}", "ips": list(info["ips"]), "macs": list(info["macs"]),
                    "power": "poweredOn" if running else "poweredOff", "host": node, "hostname": None, "os": info["os"],
                    "tools": "", "health": "green", "vcpu": g.get("maxcpu") or 0, "mem_gb": round(maxmem / GB, 1),
                    "cpu_pct": round((g.get("cpu") or 0) * 100, 1) if running else None,
                    "mem_pct": _pct(g.get("mem") or 0, maxmem) if running else None,
                    "disk_gb": round((g.get("maxdisk") or 0) / GB, 1), "uptime_s": g.get("uptime") if running else None,
                })
            for key in [k for k in self._guest_cache if k not in seen]:
                del self._guest_cache[key]
            stores = {}
            for s in (r for r in resources if r.get("type") == "storage"):
                shared = bool(s.get("shared"))
                label = s.get("storage") if shared else f"{s.get('storage')} ({s.get('node')})"
                cap, used = s.get("maxdisk") or 0, s.get("disk") or 0
                d = stores.setdefault(label, {"platform": "proxmox", "name": label, "type": s.get("plugintype") or "",
                                              "accessible": False, "capacity_gb": 0, "free_gb": 0, "used_pct": None, "hosts": []})
                d["hosts"].append(s.get("node"))
                if s.get("status") == "available" and cap >= d["capacity_gb"] * GB:
                    d.update(accessible=True, capacity_gb=round(cap / GB), free_gb=round((cap - used) / GB), used_pct=_pct(used, cap))
            datastores = [dict(d, hosts=sorted(h for h in d["hosts"] if h)) for d in stores.values() if d["capacity_gb"] or not d["accessible"]]
            alarms = [{"entity": d["name"], "alarm": "Stockage indisponible / storage unavailable", "status": "red", "acknowledged": False}
                      for d in datastores if not d["accessible"]]
            self.state.update(up=True, error="", hosts=hosts, vms=vms, datastores=datastores, alarms=alarms, updated=time.time())
            log.info("Proxmox : %d nœud(s), %d VM/conteneur(s), %d stockage(s)", len(hosts), len(vms), len(datastores))
        except Exception as e:  # réseau, jeton, droits...
            log.warning("Proxmox injoignable : %s", e)
            self.state.update(up=False, error=str(e)[:200])
        return self.state


def merge_states(states):
    """Fusionne les états vCenter et Proxmox en un seul (mêmes objets : le modèle les retrouve par identité)."""
    states = [s for s in states if s]
    if not states:
        return None
    if len(states) == 1:
        return states[0]
    out = {"up": any(s["up"] for s in states), "error": " · ".join(s["error"] for s in states if s.get("error")),
           "updated": max(s.get("updated") or 0 for s in states)}
    for k in ("hosts", "vms", "datastores", "alarms", "links"):
        out[k] = [x for s in states for x in (s.get(k) or [])]
    return out
