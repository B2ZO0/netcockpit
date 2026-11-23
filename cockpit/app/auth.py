"""Connexion à l'interface : mot de passe unique, session signée (HMAC) dans un cookie.

COCKPIT_PASSWORD           mot de passe (généré par setup.sh)
COCKPIT_AUTH               on (défaut) | off
COCKPIT_SECRET             clé de signature des sessions (générée par setup.sh)
COCKPIT_TRUSTED_NETWORKS   réseaux autorisés sans connexion (écran mural), ex. "192.0.2.50/32,10.0.9.0/24"
COCKPIT_SESSION_HOURS      durée d'une session (défaut 12)
COCKPIT_METRICS_NETWORKS   réseaux autorisés à lire /metrics sans connexion, en plus des réseaux Docker locaux
                           (d'où Prometheus et Grafana interrogent le cockpit), ex. "127.0.0.1/32" pour un Prometheus
                           installé directement sur la machine
"""
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import subprocess
import threading
import time

COOKIE = "nc_session"
PASSWORD = os.environ.get("COCKPIT_PASSWORD", "")
ENABLED = os.environ.get("COCKPIT_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")
SECRET = (os.environ.get("COCKPIT_SECRET") or secrets.token_hex(32)).encode()
HOURS = float(os.environ.get("COCKPIT_SESSION_HOURS", "12") or 12)


def _networks(value: str | None) -> list:
    nets = []
    for n in (value or "").replace(";", ",").split(","):
        if n.strip():
            try:
                nets.append(ipaddress.ip_network(n.strip(), strict=False))
            except ValueError:
                pass
    return nets


TRUSTED = _networks(os.environ.get("COCKPIT_TRUSTED_NETWORKS"))
METRICS_NETWORKS = _networks(os.environ.get("COCKPIT_METRICS_NETWORKS"))
DOCKER_IFACES = re.compile(r"^(docker\d*|br-)")
_docker = {"at": 0.0, "nets": []}

# Chemins accessibles sans connexion : page de connexion et ses ressources, santé,
# scripts d'installation des agents (publics de toute façon).
# /metrics n'en fait pas partie : il contient tout l'inventaire (voir metrics_source).
PUBLIC_PREFIXES = ("/login", "/api/login", "/health", "/-/healthy", "/agents/",
                   "/lib/fonts/", "/style.css", "/i18n.js", "/favicon", "/login.js", "/theme.js")

# Chemins lus par des machines (Prometheus, le graphe de Grafana) : ouverts aux réseaux Docker locaux et à
# COCKPIT_METRICS_NETWORKS, jamais à une requête relayée par un reverse proxy (voir allowed).
MACHINE_PATHS = ("/metrics", "/api/nodegraph")

_fails: dict[str, list[float]] = {}
_revoked: dict[str, float] = {}   # sessions fermées par « Se déconnecter » -> leur date d'expiration
_lock = threading.Lock()


def active() -> bool:
    """La connexion est exigée seulement si elle est activée ET qu'un mot de passe existe."""
    return ENABLED and bool(PASSWORD)


def misconfigured() -> bool:
    """Connexion demandée mais aucun mot de passe : on refuse tout plutôt que d'ouvrir."""
    return ENABLED and not PASSWORD


def _sign(expiry: int) -> str:
    # Le mot de passe entre dans la clé : en changer ferme toutes les sessions ouvertes avec l'ancien.
    key = hmac.new(SECRET, PASSWORD.encode(), hashlib.sha256).digest()
    mac = hmac.new(key, f"{expiry}".encode(), hashlib.sha256).hexdigest()
    return f"{expiry}.{mac}"


def new_session() -> tuple[str, int]:
    expiry = int(time.time() + HOURS * 3600)
    return _sign(expiry), int(HOURS * 3600)


def valid(token: str | None) -> bool:
    if not token or not token.isascii() or "." not in token:
        return False
    exp, _, _mac = token.partition(".")
    if not re.fullmatch(r"[0-9]{1,12}", exp) or int(exp) < time.time():
        return False
    with _lock:
        if token in _revoked:
            return False
    return hmac.compare_digest(_sign(int(exp)), token)


def revoke(token: str | None) -> None:
    """Déconnexion : ce cookie ne vaut plus rien, même copié ailleurs (jusqu'au redémarrage du cockpit)."""
    if not valid(token):
        return
    now = time.time()
    with _lock:
        for t, exp in list(_revoked.items()):
            if exp < now:
                del _revoked[t]
        _revoked[token] = float(token.partition(".")[0])


def cookie_value(cookie_header: str | None) -> str | None:
    for part in (cookie_header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE:
            return v
    return None


def trusted(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(a in n for n in TRUSTED)


def is_public(path: str) -> bool:
    return path.startswith(PUBLIC_PREFIXES)


def _parse_docker_networks(ip_addr_json: str) -> list:
    """Réseaux des interfaces Docker de la machine, d'après la sortie de `ip -j -4 addr`."""
    nets = []
    try:
        for iface in json.loads(ip_addr_json or "[]"):
            if not DOCKER_IFACES.match(iface.get("ifname", "")):
                continue
            for a in iface.get("addr_info", []):
                nets.append(ipaddress.ip_interface(f"{a['local']}/{a['prefixlen']}").network)
    except (ValueError, KeyError, TypeError):
        pass
    return nets


def docker_networks() -> list:
    """Réseaux Docker locaux, relus au plus une fois par minute (ils peuvent apparaître après le démarrage)."""
    now = time.time()
    with _lock:
        if now - _docker["at"] < 60:
            return _docker["nets"]
        _docker["at"] = now
    try:
        out = subprocess.run(["ip", "-j", "-4", "addr"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    nets = _parse_docker_networks(out)
    with _lock:
        _docker["nets"] = nets
    return nets


def metrics_source(ip: str) -> bool:
    """Qui peut lire /metrics sans connexion : les conteneurs Docker locaux (Prometheus, Grafana) et les réseaux de
    COCKPIT_METRICS_NETWORKS. Pas 127.0.0.1 : un reverse proxy installé sur la machine arrive de là."""
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if any(a in n for n in METRICS_NETWORKS):
        return True
    return any(a in n for n in docker_networks())


def allowed(path: str, ip: str, cookie_header: str | None, forwarded: bool = False) -> bool:
    """forwarded : la requête porte un en-tête de reverse proxy (X-Forwarded-For…). Prometheus et Grafana n'en
    envoient pas ; une personne passée par un proxy doit se connecter comme les autres."""
    if path in MACHINE_PATHS and not forwarded and metrics_source(ip):
        return True
    if misconfigured():
        return is_public(path) and path not in ("/api/login",)
    if not active() or is_public(path) or trusted(ip):
        return True
    return valid(cookie_value(cookie_header))


def check_password(ip: str, password: str) -> tuple[bool, int]:
    """Renvoie (ok, secondes d'attente). 5 essais ratés en 5 minutes : 5 minutes de blocage."""
    now = time.time()
    with _lock:
        recent = [t for t in _fails.get(ip, []) if now - t < 300]
        if len(recent) >= 5:
            _fails[ip] = recent
            return False, int(300 - (now - recent[0]))
        ok = bool(PASSWORD) and hmac.compare_digest(password.encode(), PASSWORD.encode())
        if ok:
            _fails.pop(ip, None)
        else:
            recent.append(now)
            _fails[ip] = recent
        return ok, 0
