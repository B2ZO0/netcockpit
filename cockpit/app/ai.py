"""Analyse IA optionnelle (Claude via l'API Anthropic, ou toute API compatible OpenAI : Ollama, LM Studio...)."""
import json
import logging
import time

import requests

import config as C

log = logging.getLogger("cockpit.ai")
_cache = {}

SYSTEM = (
    "Tu es un ingénieur système et réseau senior qui assiste l'équipe informatique d'une PME française. "
    "Tu analyses des données de supervision (Prometheus, Zabbix, vCenter, scan réseau, logs). "
    "Réponds en français, de façon concise et actionnable, en Markdown simple (titres ###, listes, `code`). "
    "Structure : ### Diagnostic (cause la plus probable, et pourquoi d'après les données), "
    "### Vérifications (3 à 6 actions concrètes, avec commandes Windows/Linux/ESXi si utile), "
    "### Impact (ce qui est touché). N'invente aucune donnée absente ; dis-le quand il manque une information. "
    "L'équipe n'a pas d'accès aux switchs/firewalls gérés par un prestataire : propose quoi demander au prestataire si besoin."
)


def enabled():
    if C.AI_PROVIDER == "anthropic":
        return bool(C.AI_API_KEY)
    if C.AI_PROVIDER == "openai":
        return bool(C.AI_BASE_URL or C.AI_API_KEY)
    return False


def info():
    if not enabled():
        return None
    model = C.AI_MODEL or ("claude-sonnet-5-5" if C.AI_PROVIDER == "anthropic" else "llama3.1")
    return {"provider": C.AI_PROVIDER, "model": model}


EN = (" IMPORTANT: the reader uses the English interface. Write the whole answer in English and translate the section titles "
      "(### Diagnosis, ### Checks, ### Impact; for a situation briefing: ### In short, ### Priorities, ### To watch).")


def _call(prompt, lang="fr"):
    model = info()["model"]
    system = SYSTEM + (EN if lang == "en" else "")
    if C.AI_PROVIDER == "anthropic":
        r = requests.post(C.AI_BASE_URL or "https://api.anthropic.com/v1/messages", timeout=90,
                          headers={"x-api-key": C.AI_API_KEY, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"},
                          json={"model": model, "max_tokens": 1500, "system": system,
                                "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    base = C.AI_BASE_URL or "https://api.openai.com/v1"
    headers = {"content-type": "application/json"}
    if C.AI_API_KEY:
        headers["authorization"] = f"Bearer {C.AI_API_KEY}"
    r = requests.post(f"{base}/chat/completions", timeout=120, headers=headers,
                      json={"model": model, "temperature": 0.2,
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def ask(key, prompt, ttl=300, lang="fr"):
    key = f"{lang}:{key}"
    if not enabled():
        return {"error": "Analyse IA non configurée (AI_PROVIDER / AI_API_KEY dans .env)."}
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return {"text": hit[1], "cached": True, **info()}
    try:
        text = _call(prompt, lang)
    except requests.HTTPError as e:
        body = e.response.text[:300] if e.response is not None else ""
        log.warning("IA : %s %s", e, body)
        return {"error": f"L'API IA a répondu une erreur : {e}. {body}"}
    except Exception as e:
        log.warning("IA : %s", e)
        return {"error": f"Impossible de joindre l'API IA : {e}"}
    _cache[key] = (time.time(), text)
    return {"text": text, "cached": False, **info()}


def explain_node(detail, lang="fr"):
    data = {k: detail.get(k) for k in ("name", "ip", "role_label", "status", "site", "subnet", "os", "vendor", "mac",
                                       "dns", "netbios", "ports", "latency_ms", "metrics", "sources", "details")}
    data["alertes"] = detail.get("alerts")
    data["disponibilite_24h_pct"] = detail.get("availability_24h")
    data["parent_topologie"] = detail.get("parent_name")
    data["lien"] = detail.get("link")
    if detail.get("vm"):
        data["vm_vcenter"] = {k: detail["vm"].get(k) for k in ("power", "host", "vcpu", "mem_gb", "cpu_pct", "mem_pct", "tools", "health")}
    if detail.get("esxi"):
        data["esxi_vcenter"] = {k: detail["esxi"].get(k) for k in ("state", "maintenance", "health", "cpu_pct", "mem_pct", "version", "model")}
    logs = detail.get("logs") or []
    prompt = (f"Analyse cet équipement et ses problèmes éventuels.\n\nDonnées de supervision (JSON) :\n"
              f"```json\n{json.dumps(data, ensure_ascii=False, default=str, indent=1)[:9000]}\n```\n")
    if logs:
        prompt += "\nDerniers logs (du plus récent au plus ancien) :\n```\n" + "\n".join(
            time.strftime("%d/%m %H:%M:%S", time.localtime(l["ts"])) + f" [{l.get('level') or '-'}] {l['line']}" for l in logs[:40]) + "\n```\n"
    if not detail.get("alerts") and detail.get("status") in ("up",):
        prompt += "\nAucune alerte en cours : fais un bilan de santé rapide et signale les points de vigilance."
    return ask(f"node:{detail.get('id')}:{detail.get('status')}:{len(detail.get('alerts') or [])}", prompt, lang=lang)


def summarize(overview, alerts, lang="fr"):
    data = {"compteurs": overview.get("stats"), "sites": [{k: s.get(k) for k in ("name", "stats", "alerts")} for s in overview.get("sites", [])],
            "chemin_internet": overview.get("internet_path"),
            "alertes": [{k: a.get(k) for k in ("severity", "name", "summary", "node_name", "node_ip", "site", "source", "since")} for a in alerts[:40]],
            "nouveaux_equipements": overview.get("new_devices", [])[:15]}
    prompt = ("Fais le point sur l'état de l'infrastructure pour l'équipe : ce qui est grave, ce qui peut attendre, "
              "les liens possibles entre les alertes (cause commune ?), et l'ordre d'intervention conseillé. "
              "Format : ### En bref (3 lignes max), ### Priorités, ### À surveiller.\n\n"
              f"```json\n{json.dumps(data, ensure_ascii=False, default=str, indent=1)[:12000]}\n```")
    key = "summary:" + ",".join(sorted(f"{a.get('name')}@{a.get('node')}" for a in alerts))
    return ask(key, prompt, ttl=600, lang=lang)
