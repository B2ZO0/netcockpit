"""Assistant de configuration de NetCockpit (lancé par ./setup.sh, dans le conteneur du cockpit, réseau de l'hôte).

Détecte le réseau local, la passerelle et les DNS, pose quelques questions, puis écrit config/cockpit.yml
et complète .env (vCenter/ESXi, Telegram). Sans terminal (ou avec --yes), il prend les valeurs détectées.
Usage : python configure.py [--yes] [--lang fr|en]   (dossier de travail = dossier de NetCockpit)
"""
import getpass
import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path.cwd()
CONFIG = ROOT / "config" / "cockpit.yml"
ENVF = ROOT / ".env"
SKIP_IFACES = re.compile(r"^(lo|docker\d*|br-|veth|virbr|cni|flannel|cali|tun|tap|wg|tailscale|zt|kube)")

T = {
    "fr": {
        "title": "Assistant de configuration NetCockpit",
        "h_word": "Le mot affiché partout dans l'interface (« Tous les bâtiments »).",
        "h_nets": "Astuce : sur un PC de ce bâtiment, tape ipconfig. Adresse IPv4 192.168.5.37 et masque 255.255.255.0 donnent le réseau 192.168.5.0/24. Les étendues de la console DHCP les listent aussi. Plusieurs réseaux (VLAN serveurs, téléphonie, Wi-Fi) : sépare-les par des virgules.",
        "h_more": "Un autre bâtiment ou site relié (VPN, fibre, MPLS) ? Cette machine doit pouvoir le joindre : vérifie avec ping vers une adresse de là-bas.",
        "h_dns": "Astuce : ipconfig /all sur un PC du domaine, ligne « Serveurs DNS ». Sans Active Directory, laisse vide.",
        "h_gw": "Astuce : ipconfig, ligne « Passerelle par défaut ». C'est souvent le firewall ou la box.",
        "h_vc": "L'adresse que tu ouvres dans le navigateur pour gérer ton vCenter ou ton ESXi. Il faut un compte en lecture seule (guide docs/demarrage.md, section 6). Pas de VMware : Entrée.",
        "h_snmp": "La communauté SNMP est un mot de passe partagé en lecture seule, donné par ton prestataire ou réglé dans tes switchs (UniFi : Settings, CyberSecure, Traffic Logging). Pas d'accès : Entrée.",
        "h_tg": "Jeton donné par @BotFather dans Telegram (commande /newbot). Détails : docs/demarrage.md, section 9.",
        "h_zbx": "Zabbix ajoute la supervision VMware native et la découverte SNMP. Si cette machine a moins de 8 Go de RAM, réponds n.",
        "intro": "Valeur proposée entre crochets : Entrée pour l'accepter.",
        "detected": "Détecté sur cette machine",
        "net": "réseau", "gw": "passerelle", "dns": "DNS",
        "word": "Comment appelles-tu tes emplacements ?  1) Bâtiment  2) Site  3) Agence  [{d}] : ",
        "words": {"1": ("Bâtiment", "Bâtiments"), "2": ("Site", "Sites"), "3": ("Agence", "Agences")},
        "first": "Nom du {w} où se trouve cette machine",
        "rename": "Nom de ce {w}",
        "nets": "Réseaux de « {n} » (séparés par des virgules)",
        "more": "Ajouter un autre {w} ? Son nom (Entrée pour terminer) : ",
        "nets_req": "Réseaux de « {n} » (ex. 10.20.0.0/24) : ",
        "bad_net": "  Réseau invalide : {x} (exemple attendu : 10.20.0.0/24)",
        "dnsq": "Serveurs DNS internes (contrôleurs de domaine), séparés par des virgules",
        "gwq": "Adresse de la passerelle / du firewall",
        "gwname": "Passerelle / Firewall",
        "vc": "VMware : adresse du vCenter ou de l'ESXi (IP ou nom, Entrée pour passer)",
        "vc_keep": "VMware déjà configuré ({v}). Entrée pour garder, ou nouvelle adresse",
        "vcu": "Utilisateur en lecture seule (ex. supervision ou supervision@vsphere.local)",
        "vcp": "Mot de passe de cet utilisateur (rien ne s'affiche) : ",
        "snmp": "Switchs et firewall : communauté SNMP en lecture seule (Entrée pour passer)",
        "snmpd": "Adresses IP des switchs / firewall à interroger en SNMP, séparées par des virgules",
        "tg": "Notifications Telegram : jeton du bot (Entrée pour passer)",
        "tgc": "Telegram : identifiant de la conversation (chat id)",
        "zbx": "Installer Zabbix (VMware natif, découverte SNMP, ~1,5 Go de RAM) ? o/n",
        "summary": "Résumé",
        "save": "Enregistrer cette configuration ? [O/n] : ",
        "saved": "Configuration enregistrée : config/cockpit.yml et .env",
        "cancel": "Rien n'a été modifié.",
        "auto": "Pas de terminal interactif : configuration automatique avec les valeurs détectées.",
        "yes": ("o", "oui", "y", "yes"),
    },
    "en": {
        "title": "NetCockpit setup assistant",
        "h_word": "The word shown everywhere in the interface (\"All buildings\").",
        "h_nets": "Tip: on a PC in this building, run ipconfig. IPv4 address 192.168.5.37 with mask 255.255.255.0 means network 192.168.5.0/24. Your DHCP scopes list them too. Several networks (server VLAN, phones, Wi-Fi): separate them with commas.",
        "h_more": "Another building or site linked by VPN, fibre or MPLS? This machine must reach it: check with a ping to an address over there.",
        "h_dns": "Tip: ipconfig /all on a domain PC, line \"DNS Servers\". No Active Directory: leave empty.",
        "h_gw": "Tip: ipconfig, line \"Default Gateway\". Usually your firewall or router.",
        "h_vc": "The address you open in your browser to manage vCenter or ESXi. A read-only account is needed (docs/getting-started.md, section 6). No VMware: press Enter.",
        "h_snmp": "The SNMP community is a shared read-only password, given by your provider or set on your switches (UniFi: Settings, CyberSecure, Traffic Logging). No access: press Enter.",
        "h_tg": "Token given by @BotFather in Telegram (/newbot command). Details: docs/getting-started.md, section 9.",
        "h_zbx": "Zabbix adds native VMware monitoring and SNMP discovery. If this machine has less than 8 GB of RAM, answer n.",
        "intro": "Suggested value in brackets: press Enter to accept it.",
        "detected": "Detected on this machine",
        "net": "network", "gw": "gateway", "dns": "DNS",
        "word": "What do you call your locations?  1) Building  2) Site  3) Branch  [{d}]: ",
        "words": {"1": ("Building", "Buildings"), "2": ("Site", "Sites"), "3": ("Branch", "Branches")},
        "first": "Name of the {w} where this machine is",
        "rename": "Name of this {w}",
        "nets": "Networks of \"{n}\" (comma-separated)",
        "more": "Add another {w}? Its name (Enter to finish): ",
        "nets_req": "Networks of \"{n}\" (e.g. 10.20.0.0/24): ",
        "bad_net": "  Invalid network: {x} (expected something like 10.20.0.0/24)",
        "dnsq": "Internal DNS servers (domain controllers), comma-separated",
        "gwq": "Gateway / firewall address",
        "gwname": "Gateway / Firewall",
        "vc": "VMware: vCenter or ESXi address (IP or name, Enter to skip)",
        "vc_keep": "VMware already configured ({v}). Enter to keep, or a new address",
        "vcu": "Read-only user (e.g. monitoring or monitoring@vsphere.local)",
        "vcp": "Password of that user (nothing is shown): ",
        "snmp": "Switches and firewall: read-only SNMP community (Enter to skip)",
        "snmpd": "IP addresses of the switches / firewall to poll over SNMP, comma-separated",
        "tg": "Telegram notifications: bot token (Enter to skip)",
        "tgc": "Telegram: chat id",
        "zbx": "Install Zabbix (native VMware, SNMP discovery, ~1.5 GB RAM)? y/n",
        "summary": "Summary",
        "save": "Save this configuration? [Y/n]: ",
        "saved": "Configuration saved: config/cockpit.yml and .env",
        "cancel": "Nothing was changed.",
        "auto": "No interactive terminal: automatic configuration with the detected values.",
        "yes": ("y", "yes", "o", "oui"),
    },
}


# ------------------------------------------------------------------ détection
def _ip_json(*args):
    try:
        return json.loads(subprocess.run(["ip", "-j", *args], capture_output=True, text=True, timeout=5).stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def _private(ip):
    try:
        a = ipaddress.ip_address(ip)
        return a.version == 4 and a.is_private and not a.is_loopback
    except ValueError:
        return False


def detect():
    nets = []
    for itf in _ip_json("-4", "addr", "show"):
        if SKIP_IFACES.match(itf.get("ifname", "")):
            continue
        for a in itf.get("addr_info", []):
            try:
                n = ipaddress.ip_network(f"{a['local']}/{a['prefixlen']}", strict=False)
            except (KeyError, ValueError):
                continue
            if n.is_private and not n.is_loopback and n.prefixlen < 32 and str(n) not in nets:
                nets.append(str(n))
    gw = next((r.get("gateway") for r in _ip_json("-4", "route", "show", "default") if r.get("gateway")), None)
    dns, domain = [], None
    for f in ("/run/systemd/resolve/resolv.conf", "/etc/resolv.conf"):
        try:
            for line in Path(f).read_text().splitlines():
                p = line.split()
                if len(p) >= 2 and p[0] == "nameserver" and _private(p[1]) and p[1] not in dns:
                    dns.append(p[1])
                elif len(p) >= 2 and p[0] in ("search", "domain") and not domain:
                    domain = p[1]
        except OSError:
            pass
        if dns:
            break
    return {"nets": nets, "gw": gw, "dns": dns, "domain": domain}


# ------------------------------------------------------------------ .env
def env_read():
    out = {}
    if ENVF.exists():
        for line in ENVF.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def env_set(values):
    """Modifie des clés du .env en place (ou les ajoute), sans toucher au reste."""
    lines = ENVF.read_text(encoding="utf-8").splitlines() if ENVF.exists() else []
    for k, v in values.items():
        v = str(v)
        if any(c in v for c in " $#\"'"):
            v = "'" + v.replace("'", "") + "'"
        for i, line in enumerate(lines):
            if line.startswith(f"{k}="):
                lines[i] = f"{k}={v}"
                break
        else:
            lines.append(f"{k}={v}")
    ENVF.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(ENVF, 0o600)


# ------------------------------------------------------------------ questions
class Ask:
    def __init__(self, lang, interactive):
        self.s, self.i = T[lang], interactive

    def __call__(self, key, default="", **kw):
        q = self.s[key].format(**kw)
        if not self.i:
            return default
        sep = " : " if self.s is T["fr"] else ": "
        a = input(f"{q} [{default}]{sep}" if default else f"{q}{sep}").strip()
        return a or default

    def raw(self, text, default=""):
        if not self.i:
            return default
        return input(text).strip() or default

    def hint(self, key):
        """Astuce affichée (en gris) avant une question, pour savoir où trouver la réponse."""
        shown = self.__dict__.setdefault("_shown", set())
        if self.i and key not in shown:
            shown.add(key)
            import textwrap
            print("\n" + "\n".join("\033[2m  › " + l + "\033[0m" for l in textwrap.wrap(self.s[key], 92)))

    def secret(self, key):
        return getpass.getpass(self.s[key]) if self.i else ""


def parse_nets(text, s):
    out, bad = [], []
    for x in re.split(r"[,\s;]+", text or ""):
        if not x:
            continue
        try:
            out.append(str(ipaddress.ip_network(x if "/" in x else f"{x}/24", strict=False)))
        except ValueError:
            bad.append(x)
    for b in bad:
        print(s["bad_net"].format(x=b))
    return out, bad


def parse_ips(text):
    out = []
    for x in re.split(r"[,\s;]+", text or ""):
        try:
            out.append(str(ipaddress.ip_address(x)))
        except ValueError:
            pass
    return out


def is_example(cfg):
    names = {str(x.get("name")) for x in (cfg.get("sites") or [])}
    return "Site A (servers)" in names or any(str(x.get("ip")) == "10.10.0.10" and "DC01" in str(x.get("name")) for x in (cfg.get("watch") or []))


def main():
    args = sys.argv[1:]
    lang = "fr" if (os.environ.get("LANG", "") + os.environ.get("LANGUAGE", "")).lower().startswith("fr") else "en"
    if "--lang" in args:
        lang = args[args.index("--lang") + 1] if args.index("--lang") + 1 < len(args) else lang
    lang = lang if lang in T else "en"
    interactive = sys.stdin.isatty() and "--yes" not in args
    s, ask = T[lang], Ask(lang, interactive)

    try:
        cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {} if CONFIG.exists() else {}
    except yaml.YAMLError:
        cfg = {}
    if is_example(cfg):        # la config d'exemple (réseaux fictifs) ne doit jamais servir de base
        cfg = {}
    env = env_read()
    det = detect()

    print(f"\n  {s['title']}\n  {'─' * len(s['title'])}")
    print(f"  {s['detected']}{' :' if lang == 'fr' else ':'} {s['net']} {', '.join(det['nets']) or '?'} · {s['gw']} {det['gw'] or '?'} · {s['dns']} {', '.join(det['dns']) or '?'}")
    if not interactive:
        print(f"  {s['auto']}")
    else:
        print(f"  {s['intro']}\n")

    # mot pour les emplacements
    cur_word = (cfg.get("site_word") or {}).get("one")
    rev = {v[0]: k for k, v in s["words"].items()}
    dflt = rev.get(cur_word, "1")
    ask.hint("h_word")
    choice = ask.raw(s["word"].format(d=dflt), dflt)
    one, many = s["words"].get(choice, s["words"][dflt])
    w = one.lower()

    # emplacements et réseaux
    old_sites = [x for x in (cfg.get("sites") or []) if x.get("subnets")]
    sites = []
    ask.hint("h_nets")
    if old_sites:
        for x in old_sites:
            name = ask("rename", x["name"], w=w)
            nets_txt = ask("nets", ", ".join(map(str, x["subnets"])), n=name)
            nets, _ = parse_nets(nets_txt, s)
            if nets:
                sites.append({"name": name, "subnets": nets})
    else:
        name = ask("first", f"{one} 1", w=w)
        nets, _ = parse_nets(ask("nets", ", ".join(det["nets"]), n=name), s)
        sites.append({"name": name, "subnets": nets or det["nets"]})
    while interactive:
        ask.hint("h_more")
        name = ask.raw(s["more"].format(w=w))
        if not name:
            break
        while True:
            nets, bad = parse_nets(ask.raw(s["nets_req"].format(n=name)), s)
            if nets and not bad:
                break
        sites.append({"name": name, "subnets": nets})

    # DNS et passerelle
    old_dns = [str(x) for x in ((cfg.get("names") or {}).get("dns_servers") or [])]
    ask.hint("h_dns")
    dns = parse_ips(ask("dnsq", ", ".join(old_dns or det["dns"]))) or old_dns or det["dns"]
    watch = list(cfg.get("watch") or [])
    gw_old = next((x for x in watch if x.get("role") in ("firewall", "router", "gateway")), None)
    ask.hint("h_gw")
    gw_ip = ask("gwq", (gw_old or {}).get("ip") or det["gw"] or "")
    try:
        gw_ip = str(ipaddress.ip_address(gw_ip)) if gw_ip else None
    except ValueError:
        gw_ip = (gw_old or {}).get("ip") or det["gw"]

    # VMware, notifications, Zabbix (.env)
    env_new = {}
    vc_cur = env.get("VCENTER_URL", "")
    ask.hint("h_vc")
    host = ask("vc_keep", "", v=vc_cur) if vc_cur else ask("vc")
    if host:
        url = host if host.startswith("http") else f"https://{host}"
        url = url if url.rstrip("/").endswith("/sdk") else url.rstrip("/") + "/sdk"
        env_new["VCENTER_URL"] = url
        env_new["VCENTER_USER"] = ask("vcu", env.get("VCENTER_USER", ""))
        pw = ask.secret("vcp")
        if pw:
            env_new["VCENTER_PASSWORD"] = pw
    snmp_cfg = cfg.get("snmp") or {}
    ask.hint("h_snmp")
    community = ask("snmp", env.get("SNMP_COMMUNITY", "") or str(snmp_cfg.get("community") or ""))
    if community:
        if community != env.get("SNMP_COMMUNITY"):
            env_new["SNMP_COMMUNITY"] = community
        snmp_cfg["community"] = ""          # le secret reste dans .env
        snmp_cfg["devices"] = parse_ips(ask("snmpd", ", ".join(map(str, snmp_cfg.get("devices") or []))))
        snmp_cfg.setdefault("try_discovered", True)
        cfg["snmp"] = snmp_cfg
    ask.hint("h_tg")
    tg = ask("tg", env.get("TELEGRAM_BOT_TOKEN", ""))
    if tg and tg != env.get("TELEGRAM_BOT_TOKEN"):
        env_new["TELEGRAM_BOT_TOKEN"] = tg
        env_new["TELEGRAM_CHAT_ID"] = ask("tgc", env.get("TELEGRAM_CHAT_ID", ""))
    zcur = env.get("ENABLE_ZABBIX", "true") == "true"
    ask.hint("h_zbx")
    z = ask("zbx", ("o" if lang == "fr" else "y") if zcur else "n").lower()
    env_new["ENABLE_ZABBIX"] = "true" if z in s["yes"] else "false"

    # configuration finale (les autres sections de l'ancienne config sont gardées)
    cfg["site_word"] = {"one": one, "many": many}
    cfg["sites"] = [x for x in sites if x["subnets"]]     # vide = réseau local détecté au démarrage du cockpit
    names = cfg.get("names") or {}
    names["dns_servers"] = dns
    names.setdefault("strip_domain", True)
    cfg["names"] = names
    watch = [x for x in watch if x is not gw_old]
    if gw_ip:
        watch.insert(0, {"name": (gw_old or {}).get("name") or s["gwname"], "ip": gw_ip, "role": (gw_old or {}).get("role") or "firewall"})
    cfg["watch"] = watch
    old_checks = {str(x.get("ip")): x for x in (cfg.get("dns_checks") or [])}
    cfg["dns_checks"] = [old_checks.get(ip) or {"name": f"DNS {ip}", "ip": ip} for ip in dns]
    for k, v in (("scan", {"enabled": True, "interval_minutes": 30, "netbios": True}),
                 ("snmp", {"community": "", "devices": [], "try_discovered": False}),
                 ("http_checks", []), ("overrides", {}), ("subnet_names", {})):
        cfg.setdefault(k, v)

    print(f"\n  {s['summary']}")
    for x in sites:
        print(f"    {x['name']:<28} {', '.join(x['subnets'])}")
    print(f"    DNS {', '.join(dns) or '-'}   {s['gw']} {gw_ip or '-'}")
    if env_new.get("VCENTER_URL") or vc_cur:
        print(f"    VMware {env_new.get('VCENTER_URL') or vc_cur}")
    print(f"    Zabbix {env_new['ENABLE_ZABBIX']}")
    if interactive and ask.raw("\n" + s["save"], s["yes"][0]).lower() not in s["yes"]:
        print(s["cancel"])
        return 1

    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    head = ("# NetCockpit : what to discover and monitor (written by ./setup.sh --configure; you can edit it by hand)\n"
            "# Reference of every option: config/cockpit.example.yml and docs/configuration.md\n\n")
    CONFIG.write_text(head + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, default_flow_style=None, width=120),
                      encoding="utf-8")
    env_set(env_new)
    print(f"\n  ✔ {s['saved']}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(1)
