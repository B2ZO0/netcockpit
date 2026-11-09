"""Chargement de la configuration (config/cockpit.yml + variables d'environnement)."""
import ipaddress
import logging
import os
from pathlib import Path

import yaml

log = logging.getLogger("cockpit.config")

ENV = os.environ.get
PORT = int(ENV("COCKPIT_PORT", "8088"))
CONFIG_PATH = Path(ENV("COCKPIT_CONFIG", "/config/cockpit.yml"))
TARGETS_DIR = Path(ENV("COCKPIT_TARGETS_DIR", "/targets"))
DATA_DIR = Path(ENV("COCKPIT_DATA_DIR", "/data"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

PROM_URL = ENV("PROMETHEUS_URL", "http://127.0.0.1:9090").rstrip("/")
ALERTMANAGER_URL = ENV("ALERTMANAGER_URL", "http://127.0.0.1:9093").rstrip("/")
LOKI_URL = ENV("LOKI_URL", "http://127.0.0.1:3100").rstrip("/")
GRAFANA_URL = ENV("GRAFANA_PUBLIC_URL", "").rstrip("/")
ALERTMANAGER_PUBLIC_URL = ENV("ALERTMANAGER_PUBLIC_URL", "").rstrip("/")

ZABBIX_URL = ENV("ZABBIX_URL", "").rstrip("/")            # accès interne (API)
ZABBIX_PUBLIC_URL = ENV("ZABBIX_PUBLIC_URL", "").rstrip("/")
ZABBIX_ADMIN_PASSWORD = ENV("ZABBIX_ADMIN_PASSWORD", "")
ZABBIX_GRAFANA_PASSWORD = ENV("ZABBIX_GRAFANA_PASSWORD", "")

VCENTER_URL = ENV("VCENTER_URL", "")
VCENTER_USER = ENV("VCENTER_USER", "")
VCENTER_PASSWORD = ENV("VCENTER_PASSWORD", "")
VCENTER_VERIFY_TLS = (ENV("VCENTER_VERIFY_TLS", "") or "").strip().lower() in ("1", "true", "yes", "on")

SNMP_COMMUNITY_ENV = ENV("SNMP_COMMUNITY", "")

AI_PROVIDER = (ENV("AI_PROVIDER", "") or "").lower()       # anthropic | openai | ""
AI_API_KEY = ENV("AI_API_KEY", "")
AI_MODEL = ENV("AI_MODEL", "")
AI_BASE_URL = ENV("AI_BASE_URL", "").rstrip("/")

INSTALL_DIR = ENV("COCKPIT_INSTALL_DIR", "")              # dossier de NetCockpit sur l'hôte (affiché dans « Mise en route »)
SCAN_OVERRIDE = ENV("COCKPIT_SCAN")  # "0" pour désactiver (tests)


def _list(v):
    return [x for x in (v or []) if x is not None]


def load():
    try:
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        log.warning("config %s absente : valeurs par défaut", CONFIG_PATH)
        cfg = {}
    except yaml.YAMLError as e:
        log.error("config %s illisible : %s", CONFIG_PATH, e)
        cfg = {}

    scan = cfg.get("scan") or {}
    scan.setdefault("enabled", True)
    scan.setdefault("interval_minutes", 30)
    scan.setdefault("netbios", True)
    scan["ports"] = _list(scan.get("ports")) or [22, 23, 53, 80, 88, 135, 161, 389, 443, 445, 902, 3389,
                                                  5985, 8006, 8080, 8443, 9100]
    scan["exclude"] = [str(x) for x in _list(scan.get("exclude"))]

    # Sites (bâtiments) : chacun avec ses réseaux
    sites = []
    for s in _list(cfg.get("sites")):
        nets = []
        for n in _list(s.get("subnets")):
            try:
                nets.append(str(ipaddress.ip_network(str(n), strict=False)))
            except ValueError:
                log.warning("réseau invalide ignoré : %s", n)
        sites.append({"name": str(s.get("name") or "Site"), "subnets": nets, "color": s.get("color")})
    legacy = [str(ipaddress.ip_network(str(n), strict=False)) for n in _list(scan.get("subnets"))]
    if legacy:
        known = {n for s in sites for n in s["subnets"]}
        extra = [n for n in legacy if n not in known]
        if extra:
            sites.append({"name": "Réseau", "subnets": extra, "color": None})

    names = cfg.get("names") or {}
    names["dns_servers"] = [str(x) for x in _list(names.get("dns_servers"))]
    names["strip_domain"] = names.get("strip_domain", True)

    snmp = cfg.get("snmp") or {}
    snmp["community"] = str(snmp.get("community") or SNMP_COMMUNITY_ENV or "")
    snmp["devices"] = [str(x) for x in _list(snmp.get("devices"))]
    snmp.setdefault("try_discovered", False)

    word = cfg.get("site_word") or {}
    out = {
        "site_word": {"one": str(word["one"]), "many": str(word.get("many") or word["one"])} if word.get("one") else None,
        "sites": sites,
        "scan": scan,
        "names": names,
        "snmp": snmp,
        "traceroute_targets": [str(x) for x in _list(cfg.get("traceroute_targets"))],
        "internet_targets": _list(cfg.get("internet_targets")),
        "watch": _list(cfg.get("watch")),
        "http_checks": _list(cfg.get("http_checks")),
        "dns_checks": _list(cfg.get("dns_checks")) or _list(cfg.get("dns_servers")),
        "subnet_names": {str(k): v for k, v in (cfg.get("subnet_names") or {}).items()},
        "overrides": {str(k): v for k, v in (cfg.get("overrides") or {}).items()},
    }
    if not out["internet_targets"]:
        out["internet_targets"] = [{"name": "Cloudflare", "ip": "1.1.1.1"}, {"name": "Google", "ip": "8.8.8.8"}]
    if not out["traceroute_targets"]:
        out["traceroute_targets"] = [str(t["ip"]) for t in out["internet_targets"][:1]]
    return out


def site_of(cfg, ip):
    """Nom du site et réseau contenant l'IP (ou (None, /24 déduit))."""
    try:
        a = ipaddress.ip_address(ip)
    except (ValueError, TypeError):
        return None, None
    for s in cfg["sites"]:
        for n in s["subnets"]:
            if a in ipaddress.ip_network(n):
                return s["name"], n
    return None, str(ipaddress.ip_network(f"{ip}/24", strict=False))


def all_subnets(cfg):
    return [n for s in cfg["sites"] for n in s["subnets"]]
