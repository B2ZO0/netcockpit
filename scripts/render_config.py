#!/usr/bin/env python3
"""Génère, à partir du .env : secrets/alertmanager.yml et secrets/snmp-auth.yml (bibliothèque standard uniquement).
Les fichiers produits sont du JSON, qui est du YAML valide.

secrets/ est en 700 : les autres utilisateurs de la machine ne peuvent pas l'ouvrir. Les fichiers sont en 644 car les
conteneurs (Alertmanager, SNMP exporter) tournent sous un autre utilisateur et les lisent par un montage du fichier lui-même,
qui ne passe pas par le dossier."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path):
    env = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        env[k.strip()] = v
    return env


def build(env):
    receiver = {"name": "notifications"}
    channels = []
    global_cfg = {"resolve_timeout": "5m"}

    if env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID"):
        try:
            chat_id = int(env["TELEGRAM_CHAT_ID"])
        except ValueError:
            sys.exit("TELEGRAM_CHAT_ID doit être un nombre (ex. 123456789 ou -1001234567890)")
        receiver["telegram_configs"] = [{
            "bot_token": env["TELEGRAM_BOT_TOKEN"], "chat_id": chat_id, "parse_mode": "HTML",
            "message": '{{ template "telegram.msg" . }}', "send_resolved": True,
        }]
        channels.append("Telegram")

    if env.get("DISCORD_WEBHOOK_URL"):
        receiver["discord_configs"] = [{
            "webhook_url": env["DISCORD_WEBHOOK_URL"],
            "title": '{{ template "discord.title" . }}',
            "message": '{{ template "discord.msg" . }}', "send_resolved": True,
        }]
        channels.append("Discord")

    if env.get("ALERT_EMAIL_TO") and env.get("SMTP_SMARTHOST"):
        global_cfg.update({"smtp_smarthost": env["SMTP_SMARTHOST"],
                           "smtp_from": env.get("SMTP_FROM") or env["ALERT_EMAIL_TO"].split(",")[0],
                           "smtp_require_tls": not env["SMTP_SMARTHOST"].endswith(":25")})
        if env.get("SMTP_USER"):
            global_cfg.update({"smtp_auth_username": env["SMTP_USER"],
                               "smtp_auth_password": env.get("SMTP_PASSWORD", "")})
        receiver["email_configs"] = [{
            "to": env["ALERT_EMAIL_TO"], "send_resolved": True,
            "headers": {"Subject": '{{ template "email.subject" . }}'},
        }]
        channels.append("Email")

    notify_info = env.get("NOTIFY_INFO", "true").lower() == "true"
    config = {
        "global": global_cfg,
        "templates": ["/etc/alertmanager/templates/*.tmpl"],
        "route": {
            "receiver": "notifications",
            "group_by": ["alertname", "node", "instance"],
            "group_wait": "30s",
            "group_interval": "5m",
            "repeat_interval": "4h",
            "routes": [
                {"matchers": ['severity="none"'], "receiver": "null"},
                {"matchers": ['severity="info"'], "receiver": "notifications" if notify_info else "null",
                 "repeat_interval": "24h"},
            ],
        },
        "inhibit_rules": [
            # Un firewall/routeur critique tombe : on ne notifie pas tout ce qui est derrière
            {"source_matchers": ['alertname="EquipementCritiqueInjoignable"', 'role=~"firewall|router"'],
             "target_matchers": ['alertname=~"EquipementInjoignable|LatenceElevee|PertesDePaquets|AgentMuet"']},
            {"source_matchers": ['alertname="ESXiDeconnecte"'],
             "target_matchers": ['alertname=~"EquipementInjoignable|AgentMuet|VMEteinte"']},
            {"source_matchers": ['alertname="InternetCoupe"'],
             "target_matchers": ['alertname=~"LatenceElevee|PertesDePaquets"', 'role="internet"']},
            # Une alerte critique masque la même alerte en warning
            {"source_matchers": ['severity="critical"'], "target_matchers": ['severity="warning"'],
             "equal": ["alertname", "node", "instance"]},
        ],
        "receivers": [{"name": "null"}, receiver],
    }
    return config, channels


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o644)


def render(root):
    env_path = root / ".env"
    if not env_path.exists():
        sys.exit("Fichier .env introuvable : lance ./setup.sh")
    env = load_env(env_path)
    secrets = root / "secrets"
    secrets.mkdir(exist_ok=True)
    secrets.chmod(0o700)

    config, channels = build(env)
    _write(secrets / "alertmanager.yml", "# Généré par scripts/render_config.py à partir du .env : ne pas modifier à la main\n"
           + json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"Alertmanager configuré. Canaux : {', '.join(channels) if channels else 'aucun (renseigne le .env)'}")
    auth = {"auths": {"site": {"version": 2, "community": env.get("SNMP_COMMUNITY") or "public"}}}
    _write(secrets / "snmp-auth.yml", "# Généré par scripts/render_config.py (SNMP_COMMUNITY du .env)\n" + json.dumps(auth, indent=2) + "\n")

    # Copies des versions précédentes, lisibles par tous les utilisateurs de la machine : retirées.
    for old in (root / "alertmanager" / "alertmanager.yml", root / "snmp" / "auth.yml"):
        try:
            old.unlink(missing_ok=True)
        except OSError as e:
            print(f"! {old} n'a pas pu être supprimé ({e}) : supprime-le à la main, il contient des secrets")
    try:
        (root / "snmp").rmdir()
    except OSError:
        pass


def main():
    render(ROOT)

if __name__ == "__main__":
    main()
