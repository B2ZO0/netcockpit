"""Connexion à l'interface : mot de passe unique, session signée (HMAC) dans un cookie.

COCKPIT_PASSWORD           mot de passe (généré par setup.sh)
COCKPIT_AUTH               on (défaut) | off
COCKPIT_SECRET             clé de signature des sessions (générée par setup.sh)
COCKPIT_TRUSTED_NETWORKS   réseaux autorisés sans connexion (écran mural), ex. "192.0.2.50/32,10.0.9.0/24"
COCKPIT_SESSION_HOURS      durée d'une session (défaut 12)
"""
import hashlib
import hmac
import ipaddress
import os
import secrets
import threading
import time

COOKIE = "nc_session"
PASSWORD = os.environ.get("COCKPIT_PASSWORD", "")
ENABLED = os.environ.get("COCKPIT_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")
SECRET = (os.environ.get("COCKPIT_SECRET") or secrets.token_hex(32)).encode()
HOURS = float(os.environ.get("COCKPIT_SESSION_HOURS", "12") or 12)
TRUSTED = []
for _n in (os.environ.get("COCKPIT_TRUSTED_NETWORKS") or "").replace(";", ",").split(","):
    if _n.strip():
        try:
            TRUSTED.append(ipaddress.ip_network(_n.strip(), strict=False))
        except ValueError:
            pass

# Chemins accessibles sans connexion : page de connexion et ses ressources, santé,
# métriques pour Prometheus, scripts d'installation des agents (publics de toute façon).
PUBLIC_PREFIXES = ("/login", "/api/login", "/health", "/-/healthy", "/metrics", "/agents/",
                   "/lib/fonts/", "/style.css", "/i18n.js", "/favicon")

_fails: dict[str, list[float]] = {}
_lock = threading.Lock()


def active() -> bool:
    """La connexion est exigée seulement si elle est activée ET qu'un mot de passe existe."""
    return ENABLED and bool(PASSWORD)


def misconfigured() -> bool:
    """Connexion demandée mais aucun mot de passe : on refuse tout plutôt que d'ouvrir."""
    return ENABLED and not PASSWORD


def _sign(expiry: int) -> str:
    mac = hmac.new(SECRET, f"{expiry}".encode(), hashlib.sha256).hexdigest()
    return f"{expiry}.{mac}"


def new_session() -> tuple[str, int]:
    expiry = int(time.time() + HOURS * 3600)
    return _sign(expiry), int(HOURS * 3600)


def valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, _, mac = token.partition(".")
    if not exp.isdigit() or int(exp) < time.time():
        return False
    return hmac.compare_digest(_sign(int(exp)), token)


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


def allowed(path: str, ip: str, cookie_header: str | None) -> bool:
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
