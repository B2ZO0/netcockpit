"""Zabbix : configuration automatique (idempotente) + lecture des problèmes en cours."""
import logging
import time

import requests

import config as C

log = logging.getLogger("cockpit.zabbix")

SEVERITY = {0: "info", 1: "info", 2: "warning", 3: "warning", 4: "critical", 5: "critical"}
SEVERITY_LABEL = {0: "Non classé", 1: "Information", 2: "Avertissement", 3: "Moyen", 4: "Élevé", 5: "Désastre"}


class ZabbixError(Exception):
    pass


class Zabbix:
    def __init__(self, url, password):
        self.url = url.rstrip("/") + "/api_jsonrpc.php"
        self.password = password
        self.token = None
        self.state = {"up": False, "error": "pas encore interrogé", "problems": [], "version": None,
                      "configured": False, "updated": 0}
        self._id = 0
        self._session = requests.Session()
        self._session.trust_env = False

    def call(self, method, params=None):
        self._id += 1
        headers = {"Content-Type": "application/json-rpc"}
        if self.token and method not in ("user.login", "apiinfo.version"):
            headers["Authorization"] = f"Bearer {self.token}"
        r = self._session.post(self.url, json={"jsonrpc": "2.0", "method": method, "params": params or {}, "id": self._id},
                               headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise ZabbixError(f"{method}: {data['error'].get('message')} {data['error'].get('data')}")
        return data["result"]

    def login(self):
        self.state["version"] = self.call("apiinfo.version")
        target = self.password or "zabbix"
        try:
            self.token = self.call("user.login", {"username": "Admin", "password": target})
            return
        except ZabbixError:
            if target == "zabbix":
                raise
        self.token = self.call("user.login", {"username": "Admin", "password": "zabbix"})
        uid = self.call("user.get", {"output": ["userid"], "filter": {"username": "Admin"}})[0]["userid"]
        self.call("user.update", {"userid": uid, "passwd": target, "current_passwd": "zabbix"})
        self.token = self.call("user.login", {"username": "Admin", "password": target})
        log.info("mot de passe Admin de Zabbix changé (ZABBIX_ADMIN_PASSWORD)")

    # ------------------------------------------------------------ helpers
    def _group(self, name):
        r = self.call("hostgroup.get", {"output": ["groupid"], "filter": {"name": name}})
        return r[0]["groupid"] if r else self.call("hostgroup.create", {"name": name})["groupids"][0]

    def _template(self, *names):
        for n in names:
            r = self.call("template.get", {"output": ["templateid"], "filter": {"name": n}})
            if r:
                return r[0]["templateid"]
        log.warning("template Zabbix introuvable : %s", " / ".join(names))
        return None

    def _action(self, name, eventsource, conditions, operations, enabled=True):
        body = {"name": name, "filter": {"evaltype": 0, "conditions": conditions}, "operations": operations}
        r = self.call("action.get", {"output": ["actionid"], "filter": {"name": name}})
        if r:
            body["actionid"] = r[0]["actionid"]
            self.call("action.update", body)
        else:
            body.update(eventsource=eventsource, status=0 if enabled else 1)
            self.call("action.create", body)

    # ------------------------------------------------------------ configuration automatique
    def configure(self, cfg):
        self.login()
        # agent du conteneur pour l'hôte "Zabbix server"
        hosts = self.call("host.get", {"output": ["hostid"], "filter": {"host": "Zabbix server"},
                                       "selectInterfaces": ["interfaceid", "type", "useip", "dns"]})
        for itf in (hosts[0]["interfaces"] if hosts else []):
            if itf["type"] == "1" and (itf["useip"] != "0" or itf["dns"] != "zabbix-agent"):
                self.call("hostinterface.update", {"interfaceid": itf["interfaceid"], "useip": 0, "dns": "zabbix-agent"})

        community = cfg["snmp"]["community"] or "public"
        r = self.call("usermacro.get", {"output": ["globalmacroid"], "globalmacro": True,
                                        "filter": {"macro": "{$SNMP_COMMUNITY}"}})
        if r:
            self.call("usermacro.updateglobal", {"globalmacroid": r[0]["globalmacroid"], "value": community})
        else:
            self.call("usermacro.createglobal", {"macro": "{$SNMP_COMMUNITY}", "value": community})

        g_vmware = self._group("VMware")
        g_net = self._group("Équipements réseau")

        # VMware natif : un hôte "vCenter" avec le template VMware, Zabbix découvre ESXi et VM tout seul
        if C.VCENTER_URL and C.VCENTER_PASSWORD:
            tpl = self._template("VMware", "VMware FQDN")
            macros = [{"macro": "{$VMWARE.URL}", "value": C.VCENTER_URL if C.VCENTER_URL.endswith("/sdk") else C.VCENTER_URL.rstrip("/") + "/sdk"},
                      {"macro": "{$VMWARE.USERNAME}", "value": C.VCENTER_USER},
                      {"macro": "{$VMWARE.PASSWORD}", "value": C.VCENTER_PASSWORD, "type": 1}]
            r = self.call("host.get", {"output": ["hostid"], "filter": {"host": "vCenter"}})
            body = {"host": "vCenter", "groups": [{"groupid": g_vmware}], "macros": macros,
                    "templates": [{"templateid": tpl}] if tpl else []}
            if r:
                body["hostid"] = r[0]["hostid"]
                self.call("host.update", body)
            else:
                body["interfaces"] = [{"type": 1, "main": 1, "useip": 1, "ip": "127.0.0.1", "dns": "", "port": "10050"}]
                self.call("host.create", body)

        # Découverte SNMP des équipements réseau (utile dès que le prestataire ouvre le SNMP)
        if cfg["snmp"]["community"]:
            subnets = ",".join(n for s in cfg["sites"] for n in s["subnets"])
            r = self.call("drule.get", {"output": ["druleid"], "filter": {"name": "Équipements SNMP"}})
            if r:
                druleid = r[0]["druleid"]
                self.call("drule.update", {"druleid": druleid, "iprange": subnets})
            else:
                druleid = self.call("drule.create", {"name": "Équipements SNMP", "iprange": subnets, "delay": "1h",
                                                     "dchecks": [{"type": 11, "key_": "1.3.6.1.2.1.1.5.0",
                                                                  "snmp_community": "{$SNMP_COMMUNITY}", "ports": "161"}]})["druleids"][0]
            tpl = self._template("Network Generic Device by SNMP")
            ops = [{"operationtype": 2}, {"operationtype": 4, "opgroup": [{"groupid": g_net}]}]
            if tpl:
                ops.append({"operationtype": 6, "optemplate": [{"templateid": tpl}]})
            self._action("Découverte : équipements SNMP", 1,
                         [{"conditiontype": 18, "operator": 0, "value": druleid},
                          {"conditiontype": 10, "operator": 0, "value": "0"}], ops)

        # Compte lecture seule pour Grafana
        if C.ZABBIX_GRAFANA_PASSWORD:
            rights = [{"id": g["groupid"], "permission": 2} for g in self.call("hostgroup.get", {"output": ["groupid"]})]
            r = self.call("usergroup.get", {"output": ["usrgrpid"], "filter": {"name": "Grafana (lecture)"}})
            if r:
                ugid = r[0]["usrgrpid"]
                self.call("usergroup.update", {"usrgrpid": ugid, "hostgroup_rights": rights})
            else:
                ugid = self.call("usergroup.create", {"name": "Grafana (lecture)", "hostgroup_rights": rights})["usrgrpids"][0]
            role = self.call("role.get", {"output": ["roleid"], "filter": {"name": "User role"}})
            roleid = role[0]["roleid"] if role else "1"
            r = self.call("user.get", {"output": ["userid"], "filter": {"username": "grafana"}})
            body = {"passwd": C.ZABBIX_GRAFANA_PASSWORD, "roleid": roleid, "usrgrps": [{"usrgrpid": ugid}]}
            if r:
                self.call("user.update", dict(body, userid=r[0]["userid"]))
            else:
                self.call("user.create", dict(body, username="grafana"))
        self.state["configured"] = True
        log.info("Zabbix configuré (VMware : %s, SNMP : %s)", bool(C.VCENTER_URL and C.VCENTER_PASSWORD),
                 bool(cfg["snmp"]["community"]))

    # ------------------------------------------------------------ équipements du cockpit dans Zabbix
    SYNC_ROLES = {"firewall": "Réseau", "router": "Réseau", "gateway": "Réseau", "switch": "Réseau", "network": "Réseau",
                  "wifi": "Wi-Fi", "dc": "Serveurs", "server": "Serveurs", "nas": "Stockage", "printer": "Imprimantes",
                  "camera": "Caméras", "hypervisor": "Serveurs", "phone": "Téléphonie"}

    def sync_hosts(self, nodes):
        """Déclare dans Zabbix les équipements importants vus par le cockpit (ping), rangés par site et par type.
        Les VM et l'ESXi sont gérés par le template VMware ; leurs problèmes de ping ne sont pas renvoyés au cockpit
        (déjà surveillés par Prometheus) pour éviter les doublons de notification."""
        if not self.token:
            self.login()
        tpl = self._template("ICMP Ping")
        existing = {h["host"]: h for h in self.call("host.get", {
            "output": ["hostid", "host", "name"], "search": {"host": "nm-"}, "startSearch": True,
            "selectInterfaces": ["interfaceid", "ip"]})}
        wanted = {}
        for n in nodes:
            ip = n.get("ip")
            cat = self.SYNC_ROLES.get(n.get("role"))
            if not ip or not cat or n.get("vm") or n.get("esxi"):
                continue
            tech = "nm-" + ip.replace(".", "-")
            name = n.get("name") or ip
            wanted[tech] = {"ip": ip, "name": f"{name} ({ip})" if name != ip else ip,
                            "group": f"{n.get('site') or 'Autres réseaux'}/{cat}", "role": n.get("role_label") or n.get("role"),
                            "site": n.get("site") or ""}
        groups = {}
        created = updated = 0
        for tech, w in wanted.items():
            if w["group"] not in groups:
                groups[w["group"]] = self._group(w["group"])
            body = {"name": w["name"], "groups": [{"groupid": groups[w["group"]]}],
                    "tags": [{"tag": "source", "value": "cockpit"}, {"tag": "type", "value": w["role"]}, {"tag": "site", "value": w["site"]}],
                    "templates": [{"templateid": tpl}] if tpl else []}
            h = existing.get(tech)
            try:
                if h:
                    if h["name"] != w["name"] or not h.get("interfaces") or h["interfaces"][0]["ip"] != w["ip"]:
                        self.call("host.update", dict(body, hostid=h["hostid"]))
                        if h.get("interfaces") and h["interfaces"][0]["ip"] != w["ip"]:
                            self.call("hostinterface.update", {"interfaceid": h["interfaces"][0]["interfaceid"], "ip": w["ip"]})
                        updated += 1
                else:
                    self.call("host.create", dict(body, host=tech, interfaces=[
                        {"type": 1, "main": 1, "useip": 1, "ip": w["ip"], "dns": "", "port": "10050"}]))
                    created += 1
            except ZabbixError as e:
                log.warning("Zabbix : impossible de déclarer %s : %s", w["name"], e)
        gone = [h["hostid"] for t, h in existing.items() if t not in wanted]
        if gone:
            self.call("host.delete", gone)
        log.info("Zabbix : %d équipement(s) du cockpit (%d ajouté(s), %d mis à jour, %d retiré(s))",
                 len(wanted), created, updated, len(gone))

    # ------------------------------------------------------------ problèmes en cours
    def poll(self):
        try:
            if not self.token:
                self.login()
            trig = self.call("trigger.get", {
                "output": ["triggerid", "description", "priority", "lastchange", "comments"],
                "filter": {"value": 1}, "monitored": True, "skipDependent": True, "expandDescription": True,
                "min_severity": 2, "selectHosts": ["host", "name"],
                "selectLastEvent": ["eventid", "acknowledged", "clock"], "sortfield": "priority", "sortorder": "DESC"})
            problems = []
            for t in trig:
                host = (t.get("hosts") or [{}])[0]
                if str(host.get("host", "")).startswith("nm-"):
                    continue   # ping des équipements du cockpit : déjà alerté par Prometheus
                prio = int(t.get("priority", 0))
                ev = t.get("lastEvent") or {}
                problems.append({"host": host.get("name") or host.get("host"), "problem": t["description"],
                                 "priority": prio, "severity": SEVERITY.get(prio, "warning"),
                                 "severity_label": SEVERITY_LABEL.get(prio), "since": int(ev.get("clock") or t.get("lastchange") or 0),
                                 "acknowledged": ev.get("acknowledged") == "1", "eventid": ev.get("eventid")})
            self.state.update(up=True, error="", problems=problems, updated=time.time())
        except Exception as e:
            self.token = None
            self.state.update(up=False, error=str(e)[:200])
            log.warning("Zabbix injoignable : %s", e)
        return self.state
