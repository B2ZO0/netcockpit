#!/usr/bin/env python3
"""Génère les tableaux de bord Grafana (grafana/dashboards/*.json). Relancer après modification."""
import json
import os
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "grafana" / "dashboards"
PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
NETMAP = {"type": "yesoreyeram-infinity-datasource", "uid": "netmap"}
MAP_URL = os.environ.get("NETMAP_PUBLIC_URL", "http://localhost:8088").rstrip("/")
GREEN, ORANGE, RED, BLUE, GREY = "#22c55e", "#f59e0b", "#ef4444", "#3b82f6", "#64748b"


class Dash:
    def __init__(self, uid, title, tags, variables=(), refresh="30s", time_from="now-6h"):
        self.d = {"uid": uid, "title": title, "tags": ["supervision"] + list(tags), "timezone": "browser",
                  "schemaVersion": 39, "version": 1, "editable": True, "graphTooltip": 1, "refresh": refresh,
                  "time": {"from": time_from, "to": "now"}, "templating": {"list": list(variables)},
                  "annotations": {"list": []}, "panels": [],
                  "links": [{"title": "Tableaux de bord", "type": "dashboards", "tags": ["supervision"],
                             "asDropdown": True, "includeVars": False, "keepTime": True}]}
        self.y = 0
        self.id = 0

    def add(self, panel, w, h, x=None, newrow=False):
        if not hasattr(self, "x") or newrow or (x is None and self.x + w > 24):
            self.x, self.y = 0, self.y + getattr(self, "rowh", 0)
            self.rowh = 0
        self.id += 1
        panel["id"] = self.id
        panel["gridPos"] = {"x": self.x if x is None else x, "y": self.y, "w": w, "h": h}
        self.x = (self.x if x is None else x) + w
        self.rowh = max(getattr(self, "rowh", 0), h)
        self.d["panels"].append(panel)
        return panel

    def row(self, title):
        self.add({"type": "row", "title": title, "collapsed": False, "panels": []}, 24, 1, newrow=True)
        self.x = 24

    def save(self, name):
        (OUT / name).write_text(json.dumps(self.d, ensure_ascii=False, indent=2), encoding="utf-8")


def q(expr, legend="", ref="A", instant=False, fmt="time_series", interval=""):
    t = {"refId": ref, "datasource": PROM, "expr": expr, "legendFormat": legend, "range": not instant,
         "instant": instant, "format": fmt, "editorMode": "code"}
    if interval:
        t["interval"] = interval
    return t


def lq(expr, ref="A", qtype="range"):
    return {"refId": ref, "datasource": LOKI, "expr": expr, "queryType": qtype, "editorMode": "code"}


def steps(*pairs, base=GREEN):
    s = [{"color": base, "value": None}] + [{"color": c, "value": v} for v, c in pairs]
    return {"mode": "absolute", "steps": s}


def stat(title, targets, unit="none", thresholds=None, mappings=None, desc="", color_mode="background", text_mode="value", decimals=None, links=None):
    d = {"unit": unit, "thresholds": thresholds or steps(), "mappings": mappings or [], "color": {"mode": "thresholds"}}
    if decimals is not None:
        d["decimals"] = decimals
    if links:
        d["links"] = links
    return {"type": "stat", "title": title, "description": desc, "datasource": PROM, "targets": targets,
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": color_mode, "graphMode": "none", "textMode": text_mode, "justifyMode": "center",
                        "orientation": "auto", "wideLayout": True}}


def ts(title, targets, unit="none", desc="", minv=None, maxv=None, thresholds=None, stack=False, fill=12, legend_calcs=("mean", "max", "lastNotNull"), legend="table", ds=PROM):
    d = {"unit": unit, "color": {"mode": "palette-classic"},
         "custom": {"drawStyle": "line", "lineWidth": 1, "fillOpacity": fill, "showPoints": "never", "spanNulls": True,
                    "gradientMode": "opacity", "stacking": {"mode": "normal" if stack else "none"},
                    "thresholdsStyle": {"mode": "dashed" if thresholds else "off"}}}
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    if thresholds:
        d["thresholds"] = thresholds
    return {"type": "timeseries", "title": title, "description": desc, "datasource": ds, "targets": targets,
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"legend": {"displayMode": legend, "placement": "right" if legend == "table" else "bottom",
                                   "calcs": list(legend_calcs) if legend == "table" else [], "showLegend": True},
                        "tooltip": {"mode": "multi", "sort": "desc"}}}


def bargauge(title, targets, unit="percent", thresholds=None, desc="", maxv=100):
    return {"type": "bargauge", "title": title, "description": desc, "datasource": PROM, "targets": targets,
            "fieldConfig": {"defaults": {"unit": unit, "min": 0, "max": maxv, "color": {"mode": "thresholds"},
                                         "thresholds": thresholds or steps((80, ORANGE), (90, RED))}, "overrides": []},
            "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True, "valueMode": "color",
                        "namePlacement": "left", "sizing": "auto", "minVizHeight": 12, "maxVizHeight": 22,
                        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}


def table(title, targets, overrides=(), transformations=(), desc="", sort=None, ds=PROM):
    p = {"type": "table", "title": title, "description": desc, "datasource": ds, "targets": targets,
         "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}, "filterable": True}},
                         "overrides": list(overrides)},
         "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
         "transformations": list(transformations)}
    if sort:
        p["options"]["sortBy"] = [{"displayName": sort[0], "desc": sort[1]}]
    return p


def ov(name, **props):
    """Surcharge de colonne : ov('Value', unit='percent', cell='color-background', thr=steps(...), width=120, name='CPU')."""
    p = []
    if "rename" in props:
        p.append({"id": "displayName", "value": props["rename"]})
    if "unit" in props:
        p.append({"id": "unit", "value": props["unit"]})
    if "decimals" in props:
        p.append({"id": "decimals", "value": props["decimals"]})
    if "thr" in props:
        p.append({"id": "thresholds", "value": props["thr"]})
        p.append({"id": "color", "value": {"mode": "thresholds"}})
    if "cell" in props:
        cell = {"type": props["cell"]}
        if props["cell"] == "gauge":
            cell.update(mode="gradient", valueDisplayMode="color")
        if props["cell"] == "color-background":
            cell["mode"] = "basic"
        p.append({"id": "custom.cellOptions", "value": cell})
    if "mappings" in props:
        p.append({"id": "mappings", "value": props["mappings"]})
    if "width" in props:
        p.append({"id": "custom.width", "value": props["width"]})
    if "min" in props:
        p.append({"id": "min", "value": props["min"]})
    if "max" in props:
        p.append({"id": "max", "value": props["max"]})
    if props.get("hidden"):
        p.append({"id": "custom.hidden", "value": True})
    if "link" in props:
        p.append({"id": "links", "value": [{"title": props["link"][0], "url": props["link"][1]}]})
    return {"matcher": {"id": "byName", "options": name}, "properties": p}


def vmap(*items):
    """vmap((valeur, texte, couleur), ...)"""
    return [{"type": "value", "options": {str(v): {"text": t, "color": c, "index": i}}} for i, (v, t, c) in enumerate(items)]


UP_MAP = vmap((1, "OK", GREEN), (0, "EN PANNE", RED))
SEV_MAP = vmap(("critical", "CRITIQUE", RED), ("warning", "ATTENTION", ORANGE), ("info", "INFO", BLUE))
HIDE_TIME = {"id": "organize", "options": {"excludeByName": {"Time": True, "__name__": True, "alertstate": True, "job": True}}}

# Expressions communes Linux + Windows
CPU = ('(100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"%s}[5m])) * 100)'
       ' or (100 - avg by (instance) (rate(windows_cpu_time_total{mode="idle"%s}[5m])) * 100)')
MEM = ('max by (instance) ((1 - node_memory_MemAvailable_bytes%s / node_memory_MemTotal_bytes%s) * 100)'
       ' or max by (instance) ((1 - max by (instance) (windows_memory_physical_free_bytes%s or windows_os_physical_memory_free_bytes%s)'
       ' / max by (instance) (windows_memory_physical_total_bytes%s or windows_cs_physical_memory_bytes%s)) * 100)')
DISKMAX = ('max by (instance) ((1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"%s}'
           ' / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"%s}) * 100)'
           ' or max by (instance) ((1 - windows_logical_disk_free_bytes{volume!~"HarddiskVolume.*"%s}'
           ' / windows_logical_disk_size_bytes{volume!~"HarddiskVolume.*"%s}) * 100)')


def sel(extra):
    return extra


def cpu(f=""):
    return CPU % (f, f)


def mem(f=""):
    b = "{" + f.lstrip(",") + "}" if f else ""
    return MEM % (b, b, b, b, b, b)


def diskmax(f=""):
    return DISKMAX % (f, f, f, f)


def build_overview():
    D = Dash("vue-ensemble", "Supervision · Vue d'ensemble", ["accueil"], refresh="30s", time_from="now-24h")
    D.add(stat("Équipements surveillés", [q('netmap_nodes{status="total"}', instant=True)], color_mode="none",
               desc="Tout ce qui est sur la carte : serveurs, VM, réseau, postes."), 3, 4)
    D.add(stat("En panne", [q('netmap_nodes{status="down"}', instant=True)], thresholds=steps((1, RED))), 3, 4)
    D.add(stat("Alertes actives", [q('count(ALERTS{alertstate="firing", severity=~"critical|warning"}) or vector(0)', instant=True)],
               thresholds=steps((1, ORANGE)), desc="Alertes critiques et warning en cours"), 3, 4)
    D.add(stat("Internet", [q('max(probe_success{job="blackbox_icmp", role="internet"})', instant=True)],
               mappings=UP_MAP, thresholds=steps((1, GREEN), base=RED)), 3, 4)
    D.add(stat("Latence Internet", [q('avg(probe_icmp_duration_seconds{job="blackbox_icmp", role="internet", phase="rtt"})', instant=True)],
               unit="s", thresholds=steps((0.05, ORANGE), (0.15, RED)), color_mode="value", decimals=1), 3, 4)
    D.add(stat("Serveurs avec agent", [q('count(up{job=~"node|windows"} == 1) or vector(0)', instant=True)], color_mode="none"), 3, 4)
    D.add(stat("Agents muets", [q('count(ALERTS{alertname="AgentMuet", alertstate="firing"}) or vector(0)', instant=True)],
               thresholds=steps((1, RED))), 3, 4)
    D.add(stat("vCenter", [q('max(netmap_vmware_up)', instant=True)], mappings=vmap((1, "OK", GREEN), (0, "INJOIGNABLE", RED)),
               thresholds=steps((1, GREEN), base=RED), desc="Vide si aucun vCenter n'est configuré"), 3, 4)

    ng = {"type": "nodeGraph", "title": f"Topologie en direct  ·  carte interactive : {MAP_URL}",
          "description": "Généré automatiquement par netmap (scan, traceroute, vCenter CDP/LLDP, agents). "
                         "Vert = OK, orange = alerte, rouge = en panne, gris = éteint/inconnu.",
          "datasource": NETMAP, "options": {"nodes": {"mainStatUnit": "none"}, "edges": {}},
          "targets": []}
    cols_nodes = [("id", "string"), ("title", "string"), ("subTitle", "string"), ("mainStat", "string"),
                  ("secondaryStat", "string"), ("detail__statut", "string"), ("detail__ip", "string")]
    for s in ("up", "warning", "critical", "down", "off", "unknown", "net"):
        cols_nodes += [(f"arc__{s}", "number"), (f"arc__{s}_color", "string")]
    for ref, fmt, root, cols in (("A", "node-graph-nodes", "nodes", cols_nodes),
                                 ("B", "node-graph-edges", "edges", [("id", "string"), ("source", "string"), ("target", "string"), ("mainStat", "string")])):
        ng["targets"].append({"refId": ref, "datasource": NETMAP, "type": "json", "source": "url", "format": fmt,
                              "url": "http://host.docker.internal:8088/api/nodegraph?hide_devices=$masquer_postes",
                              "url_options": {"method": "GET", "data": ""}, "root_selector": root,
                              "columns": [{"selector": c, "text": c, "type": t} for c, t in cols], "filters": []})
    D.add(ng, 16, 16, newrow=True)
    D.add(table("Problèmes en cours", [q('ALERTS{alertstate="firing", severity!="none"}', instant=True, fmt="table")],
                overrides=[ov("severity", rename="Gravité", cell="color-background", mappings=SEV_MAP, width=95),
                           ov("alertname", rename="Alerte"), ov("Value", hidden=True)],
                transformations=[HIDE_TIME, {"id": "organize", "options": {"indexByName": {"severity": 0, "alertname": 1}}}],
                desc="Toutes les alertes en cours (détail et historique : Alertmanager, port 9093)."), 8, 16)

    D.row("Disponibilité")
    D.add({"type": "state-timeline", "title": "Équipements critiques (firewalls, routeurs, ESXi, équipements prestataires)",
           "datasource": PROM, "targets": [q('max by (name) (probe_success{job="blackbox_icmp", critical="true", role!="internet"})', "{{name}}")],
           "fieldConfig": {"defaults": {"mappings": UP_MAP, "thresholds": steps((1, GREEN), base=RED), "color": {"mode": "thresholds"},
                                        "custom": {"fillOpacity": 85, "lineWidth": 0}}, "overrides": []},
           "options": {"showValue": "never", "rowHeight": 0.8, "mergeValues": True, "alignValue": "left",
                       "legend": {"showLegend": False}, "tooltip": {"mode": "single"}}}, 12, 9, newrow=True)
    D.add(ts("Latence vers les équipements critiques et Internet",
             [q('max by (name) (probe_icmp_duration_seconds{job="blackbox_icmp", critical="true", phase="rtt"})', "{{name}}")],
             unit="s", thresholds=steps((0.15, RED)), fill=0), 12, 9)

    D.row("Serveurs")
    D.add(table("Tous les serveurs", [
        q('max by (instance, os, ip) (up{job=~"node|windows"})', ref="A", instant=True, fmt="table"),
        q(cpu(), ref="B", instant=True, fmt="table"),
        q(mem(), ref="C", instant=True, fmt="table"),
        q(diskmax(), ref="D", instant=True, fmt="table"),
        q('max by (instance) (time() - (node_boot_time_seconds or windows_system_boot_time_timestamp_seconds))', ref="E", instant=True, fmt="table"),
    ], overrides=[ov("instance", rename="Serveur", link=("Détail", "/d/serveur?var-instance=${__value.raw}")),
                  ov("os", rename="OS", width=80), ov("ip", rename="IP", width=120),
                  ov("Value #A", rename="Agent", cell="color-background", mappings=UP_MAP, width=90),
                  ov("Value #B", rename="CPU", unit="percent", cell="gauge", min=0, max=100, thr=steps((70, ORANGE), (90, RED))),
                  ov("Value #C", rename="Mémoire", unit="percent", cell="gauge", min=0, max=100, thr=steps((80, ORANGE), (95, RED))),
                  ov("Value #D", rename="Disque le + plein", unit="percent", cell="gauge", min=0, max=100, thr=steps((80, ORANGE), (90, RED))),
                  ov("Value #E", rename="Allumé depuis", unit="s", decimals=0, width=120)],
        transformations=[{"id": "merge", "options": {}}, HIDE_TIME], sort=("CPU", True)), 24, 10, newrow=True)
    D.add(ts("CPU par serveur", [q(cpu(), "{{instance}}")], unit="percent", minv=0, maxv=100, fill=0), 12, 8, newrow=True)
    D.add(ts("Mémoire par serveur", [q(mem(), "{{instance}}")], unit="percent", minv=0, maxv=100, fill=0), 12, 8)

    D.row("Logs")
    D.add(ts("Volume d'erreurs dans les logs", [
        {**lq('sum by (host) (count_over_time({job=~"journal|windows", level=~"err|crit|alert|emerg|error|critical"} [$__auto]))'), "legendFormat": "{{host}}"}],
        ds=LOKI, stack=True, fill=60, legend="list"), 8, 10, newrow=True)
    D.add({"type": "logs", "title": "Dernières erreurs (tous serveurs)", "datasource": LOKI,
           "targets": [lq('{job=~"journal|windows", level=~"err|crit|alert|emerg|error|critical"}')],
           "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True,
                       "prettifyLogMessage": False, "dedupStrategy": "signature"}}, 16, 10)

    D.d["templating"]["list"] = [{"name": "masquer_postes", "label": "Masquer les postes OK", "type": "custom",
                                  "query": "Non : 0,Oui : 1", "current": {"text": "Oui", "value": "1"},
                                  "options": [{"text": "Non", "value": "0", "selected": False}, {"text": "Oui", "value": "1", "selected": True}],
                                  "hide": 0}]
    # le lien "Voir la carte" de la tuile "En panne"
    D.d["panels"][1]["fieldConfig"]["defaults"]["links"] = [{"title": "Ouvrir la carte du réseau", "url": f"{MAP_URL}/?problems=1", "targetBlank": True}]
    D.d["links"].insert(0, {"title": "Carte du réseau", "type": "link", "url": f"{MAP_URL}/", "targetBlank": True, "icon": "external link"})
    D.save("00-vue-ensemble.json")


def build_server():
    var = {"name": "instance", "label": "Serveur", "type": "query", "datasource": PROM,
           "query": {"query": 'label_values(up{job=~"node|windows"}, instance)', "refId": "v"},
           "definition": 'label_values(up{job=~"node|windows"}, instance)', "refresh": 2, "sort": 1, "hide": 0}
    D = Dash("serveur", "Supervision · Serveur", ["serveurs"], [var], time_from="now-6h")
    I = ',instance="$instance"'
    D.add(stat("Agent", [q('max(up{instance="$instance"})', instant=True)], mappings=UP_MAP, thresholds=steps((1, GREEN), base=RED)), 4, 4)
    D.add(stat("CPU", [q(cpu(I), instant=True)], unit="percent", thresholds=steps((70, ORANGE), (90, RED)), color_mode="value", decimals=0), 4, 4)
    D.add(stat("Mémoire", [q(mem(I), instant=True)], unit="percent", thresholds=steps((80, ORANGE), (95, RED)), color_mode="value", decimals=0), 4, 4)
    D.add(stat("Disque le plus plein", [q(diskmax(I), instant=True)], unit="percent", thresholds=steps((80, ORANGE), (90, RED)), color_mode="value", decimals=0), 4, 4)
    D.add(stat("Allumé depuis", [q('time() - (node_boot_time_seconds{instance="$instance"} or windows_system_boot_time_timestamp_seconds{instance="$instance"})', instant=True)],
               unit="s", color_mode="none", decimals=0), 4, 4)
    D.add(stat("Alertes", [q('count(ALERTS{alertstate="firing", instance="$instance"}) or vector(0)', instant=True)], thresholds=steps((1, ORANGE))), 4, 4)
    D.add(ts("CPU", [q(cpu(I), "CPU")], unit="percent", minv=0, maxv=100, thresholds=steps((90, RED)), legend="list"), 12, 8, newrow=True)
    D.add(ts("Mémoire", [q(mem(I), "Mémoire utilisée")], unit="percent", minv=0, maxv=100, thresholds=steps((95, RED)), legend="list"), 12, 8)
    D.add(bargauge("Disques", [
        q('(1 - node_filesystem_avail_bytes{instance="$instance", fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"} / node_filesystem_size_bytes{instance="$instance", fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"}) * 100', "{{mountpoint}}", instant=True),
        q('(1 - windows_logical_disk_free_bytes{instance="$instance", volume!~"HarddiskVolume.*"} / windows_logical_disk_size_bytes{instance="$instance", volume!~"HarddiskVolume.*"}) * 100', "{{volume}}", ref="B", instant=True)]), 8, 8, newrow=True)
    D.add(ts("Réseau", [
        q('rate(node_network_receive_bytes_total{instance="$instance", device!~"lo|veth.*|docker.*|br-.*|virbr.*"}[5m]) * 8', "{{device}} reçu"),
        q('-rate(node_network_transmit_bytes_total{instance="$instance", device!~"lo|veth.*|docker.*|br-.*|virbr.*"}[5m]) * 8', "{{device}} envoyé", ref="B"),
        q('rate(windows_net_bytes_received_total{instance="$instance", nic!~"isatap.*|Teredo.*"}[5m]) * 8', "{{nic}} reçu", ref="C"),
        q('-rate(windows_net_bytes_sent_total{instance="$instance", nic!~"isatap.*|Teredo.*"}[5m]) * 8', "{{nic}} envoyé", ref="D")],
        unit="bps", legend="list"), 8, 8)
    D.add(ts("Charge système (Linux) / file d'attente CPU (Windows)", [
        q('node_load1{instance="$instance"}', "load 1 min"), q('node_load15{instance="$instance"}', "load 15 min", ref="B"),
        q('windows_system_processor_queue_length{instance="$instance"}', "file d'attente CPU", ref="C")], legend="list"), 8, 8)
    D.add(table("Voisins switch (LLDP/CDP)", [q('lldp_neighbor_info{instance="$instance"}', instant=True, fmt="table")],
                overrides=[ov("interface", rename="Interface"), ov("chassis_name", rename="Switch"), ov("port_id", rename="Port"),
                           ov("port_descr", rename="Description port"), ov("mgmt_ip", rename="IP du switch"), ov("Value", hidden=True),
                           ov("instance", hidden=True), ov("ip", hidden=True), ov("os", hidden=True), ov("chassis_id", hidden=True)],
                transformations=[HIDE_TIME], desc="Sur quel switch et quel port ce serveur est branché (Linux avec lldpd)."), 12, 6, newrow=True)
    D.add(table("Services systemd en échec", [q('node_systemd_unit_state{instance="$instance", state="failed"} == 1', instant=True, fmt="table")],
                overrides=[ov("name", rename="Service"), ov("Value", hidden=True), ov("state", hidden=True), ov("type", hidden=True),
                           ov("instance", hidden=True), ov("ip", hidden=True), ov("os", hidden=True)],
                transformations=[HIDE_TIME]), 12, 6)
    D.add({"type": "logs", "title": "Logs du serveur", "datasource": LOKI, "targets": [lq('{host="$instance"}')],
           "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "enableLogDetails": True}}, 24, 12, newrow=True)
    D.save("serveur.json")


def build_network():
    var = {"name": "node", "label": "Équipement", "type": "query", "datasource": PROM,
           "query": {"query": 'label_values(probe_success{job="blackbox_icmp"}, node)', "refId": "v"},
           "definition": 'label_values(probe_success{job="blackbox_icmp"}, node)', "refresh": 2, "sort": 1, "hide": 0,
           "includeAll": True, "multi": True, "current": {"text": ["All"], "value": ["$__all"]}}
    D = Dash("reseau", "Supervision · Réseau et disponibilité", ["réseau"], [var], time_from="now-24h")
    D.add(stat("Équipements qui répondent", [q('count(max by (node) (probe_success{job=~"blackbox_icmp|blackbox_tcp"}) == 1)', instant=True)], color_mode="none"), 6, 4)
    D.add(stat("Équipements surveillés en panne", [q('count(max by (node) (probe_success{job=~"blackbox_icmp|blackbox_tcp", alert="true"}) == 0) or vector(0)', instant=True)], thresholds=steps((1, RED))), 6, 4)
    D.add(stat("Sites web en panne", [q('count(probe_success{job="blackbox_http"} == 0) or vector(0)', instant=True)], thresholds=steps((1, RED))), 6, 4)
    D.add(stat("Nouveaux équipements (24 h)", [q('count(netmap_device_first_seen_timestamp_seconds) or vector(0)', instant=True)], thresholds=steps((1, BLUE))), 6, 4)
    D.add({"type": "state-timeline", "title": "Disponibilité (ping ou port)", "datasource": PROM,
           "targets": [q('max by (name) (probe_success{job=~"blackbox_icmp|blackbox_tcp", node=~"$node", alert="true"})', "{{name}}")],
           "fieldConfig": {"defaults": {"mappings": UP_MAP, "thresholds": steps((1, GREEN), base=RED), "color": {"mode": "thresholds"},
                                        "custom": {"fillOpacity": 85, "lineWidth": 0}}, "overrides": []},
           "options": {"showValue": "never", "rowHeight": 0.85, "mergeValues": True, "legend": {"showLegend": False}}}, 24, 12, newrow=True)
    D.add(ts("Latence (ping)", [q('max by (name) (probe_icmp_duration_seconds{job="blackbox_icmp", phase="rtt", node=~"$node"})', "{{name}}")],
             unit="s", fill=0), 12, 9, newrow=True)
    D.add(ts("Taux de réponse sur 10 min (pertes de paquets)", [q('avg_over_time(probe_success{job="blackbox_icmp", node=~"$node", alert="true"}[10m]) * 100', "{{name}}")],
             unit="percent", minv=0, maxv=100, fill=0, thresholds=steps((90, RED), base=RED)), 12, 9)
    D.add(table("Sites et applications web", [
        q('probe_success{job="blackbox_http"}', ref="A", instant=True, fmt="table"),
        q('probe_duration_seconds{job="blackbox_http"}', ref="B", instant=True, fmt="table"),
        q('(probe_ssl_earliest_cert_expiry{job="blackbox_http"} - time()) / 86400', ref="C", instant=True, fmt="table"),
        q('probe_http_status_code{job="blackbox_http"}', ref="D", instant=True, fmt="table")],
        overrides=[ov("name", rename="Nom"), ov("instance", rename="URL"),
                   ov("Value #A", rename="État", cell="color-background", mappings=UP_MAP, width=100),
                   ov("Value #B", rename="Temps de réponse", unit="s", decimals=2),
                   ov("Value #C", rename="Certificat (jours)", decimals=0, cell="color-text", thr=steps((14, ORANGE), (30, GREEN), base=RED)),
                   ov("Value #D", rename="Code HTTP", width=100), ov("node", hidden=True)],
        transformations=[{"id": "merge", "options": {}}, HIDE_TIME]), 24, 7, newrow=True)
    D.add(table("Nouveaux équipements détectés (24 h)", [q('netmap_device_first_seen_timestamp_seconds * 1000', instant=True, fmt="table")],
                overrides=[ov("ip", rename="IP"), ov("mac", rename="MAC"), ov("vendor", rename="Constructeur"), ov("hostname", rename="Nom"),
                           ov("Value", rename="Vu la 1re fois", unit="dateTimeAsLocal"), ov("instance", hidden=True)],
                transformations=[HIDE_TIME]), 24, 6, newrow=True)
    D.add(table("Inventaire du réseau (découverte automatique)", [q('netmap_device_info', instant=True, fmt="table")],
                overrides=[ov("ip", rename="IP", width=130), ov("name", rename="Nom"), ov("dns", rename="DNS"), ov("netbios", rename="NetBIOS"),
                           ov("mac", rename="MAC", width=150), ov("vendor", rename="Constructeur"), ov("role", rename="Type", width=140),
                           ov("site", rename="Site"), ov("subnet", rename="Réseau", width=140), ov("os", rename="Système"),
                           ov("Value", hidden=True), ov("instance", hidden=True)],
                transformations=[HIDE_TIME], sort=("IP", False)), 24, 12, newrow=True)
    D.save("reseau.json")


def build_vmware():
    D = Dash("vmware", "Supervision · VMware vSphere", ["vmware"], time_from="now-24h")
    D.add(stat("ESXi connectés", [q('sum(netmap_vmware_host_connected)', instant=True)], color_mode="none"), 4, 4)
    D.add(stat("ESXi déconnectés", [q('count(netmap_vmware_host_connected == 0) or vector(0)', instant=True)], thresholds=steps((1, RED))), 4, 4)
    D.add(stat("En maintenance", [q('sum(netmap_vmware_host_maintenance) or vector(0)', instant=True)], thresholds=steps((1, BLUE))), 4, 4)
    D.add(stat("VM allumées", [q('sum(netmap_vmware_vm_powered_on)', instant=True)], color_mode="none"), 4, 4)
    D.add(stat("VM éteintes", [q('count(netmap_vmware_vm_powered_on == 0) or vector(0)', instant=True)], color_mode="none"), 4, 4)
    D.add(stat("Alarmes vCenter", [q('count(netmap_vmware_alarm) or vector(0)', instant=True)], thresholds=steps((1, ORANGE))), 4, 4)
    D.add(ts("CPU des ESXi", [q('netmap_vmware_host_cpu_percent', "{{host}}")], unit="percent", minv=0, maxv=100, fill=8,
             thresholds=steps((90, RED)), legend="list"), 12, 8, newrow=True)
    D.add(ts("Mémoire des ESXi", [q('netmap_vmware_host_mem_percent', "{{host}}")], unit="percent", minv=0, maxv=100, fill=8,
             thresholds=steps((92, RED)), legend="list"), 12, 8)
    D.add(bargauge("Datastores (espace utilisé)", [q('netmap_vmware_datastore_used_percent', "{{datastore}}", instant=True)],
                   thresholds=steps((80, ORANGE), (90, RED))), 8, 9, newrow=True)
    D.add(bargauge("Top 15 VM · CPU", [q('topk(15, netmap_vmware_vm_cpu_percent)', "{{vm}}", instant=True)],
                   thresholds=steps((70, ORANGE), (90, RED))), 8, 9)
    D.add(bargauge("Top 15 VM · mémoire", [q('topk(15, netmap_vmware_vm_mem_percent)', "{{vm}}", instant=True)],
                   thresholds=steps((85, ORANGE), (95, RED))), 8, 9)
    D.add(ts("Datastores : évolution", [q('netmap_vmware_datastore_used_percent', "{{datastore}}")], unit="percent",
             minv=0, maxv=100, fill=0, legend="list", desc="Pour anticiper un remplissage."), 12, 8, newrow=True)
    D.add(table("Alarmes vCenter en cours", [q('netmap_vmware_alarm', instant=True, fmt="table")],
                overrides=[ov("status", rename="Niveau", cell="color-background", mappings=vmap(("red", "CRITIQUE", RED), ("yellow", "ATTENTION", ORANGE)), width=110),
                           ov("alarm", rename="Alarme"), ov("entity", rename="Objet"), ov("Value", hidden=True), ov("instance", hidden=True)],
                transformations=[HIDE_TIME]), 12, 8)
    D.save("vmware.json")


def build_switches():
    var = {"name": "switch", "label": "Équipement", "type": "query", "datasource": PROM,
           "query": {"query": 'label_values(ifHCInOctets{job="snmp"}, instance)', "refId": "v"},
           "definition": 'label_values(ifHCInOctets{job="snmp"}, instance)', "refresh": 2, "sort": 1, "hide": 0,
           "includeAll": True, "multi": True, "current": {"text": ["All"], "value": ["$__all"]}}
    D = Dash("switchs", "Supervision · Switchs et ports (SNMP)", ["réseau", "snmp"], [var], time_from="now-6h")
    D.add({"type": "text", "title": "", "options": {"mode": "markdown", "content":
           "Ce tableau se remplit dès que le prestataire donne un **accès SNMP en lecture seule** : renseigne `SNMP_COMMUNITY` dans `.env` "
           "et les IP des équipements dans `config/netmap.yml` (`snmp.devices`), puis relance `./setup.sh`. "
           "Le détail port par port (qui est branché où) est dans le **cockpit**, vue *Switchs*."}}, 24, 3)
    D.add(stat("Équipements SNMP qui répondent", [q('count(up{job="snmp"} == 1) or vector(0)', instant=True)], color_mode="none"), 6, 4, newrow=True)
    D.add(stat("Ports actifs", [q('count(ifOperStatus{job="snmp", instance=~"$switch"} == 1) or vector(0)', instant=True)], color_mode="none"), 6, 4)
    D.add(stat("Ports en erreur (1 h)", [q('count(increase(ifInErrors{job="snmp", instance=~"$switch"}[1h]) > 0) or vector(0)', instant=True)], thresholds=steps((1, ORANGE))), 6, 4)
    D.add(stat("Port le plus chargé", [q('max(rate(ifHCInOctets{job="snmp", instance=~"$switch"}[5m]) * 8 / on (instance, ifIndex) (ifHighSpeed{job="snmp"} * 1e6 > 0)) * 100 or vector(0)', instant=True)],
               unit="percent", thresholds=steps((60, ORANGE), (85, RED)), color_mode="value", decimals=0), 6, 4)
    D.add(ts("Top 10 ports · trafic entrant", [q('topk(10, rate(ifHCInOctets{job="snmp", instance=~"$switch"}[5m]) * 8)', "{{name}} {{ifName}} {{ifAlias}}")],
             unit="bps", fill=6), 12, 9, newrow=True)
    D.add(ts("Top 10 ports · trafic sortant", [q('topk(10, rate(ifHCOutOctets{job="snmp", instance=~"$switch"}[5m]) * 8)', "{{name}} {{ifName}} {{ifAlias}}")],
             unit="bps", fill=6), 12, 9)
    D.add(table("Ports actifs", [
        q('ifOperStatus{job="snmp", instance=~"$switch"} == 1', ref="A", instant=True, fmt="table"),
        q('ifHighSpeed{job="snmp", instance=~"$switch"}', ref="B", instant=True, fmt="table"),
        q('rate(ifHCInOctets{job="snmp", instance=~"$switch"}[5m]) * 8', ref="C", instant=True, fmt="table"),
        q('rate(ifHCOutOctets{job="snmp", instance=~"$switch"}[5m]) * 8', ref="D", instant=True, fmt="table"),
        q('increase(ifInErrors{job="snmp", instance=~"$switch"}[1h])', ref="E", instant=True, fmt="table")],
        overrides=[ov("name", rename="Équipement"), ov("ifName", rename="Port"), ov("ifAlias", rename="Description"),
                   ov("Value #A", hidden=True), ov("Value #B", rename="Vitesse (Mb/s)"), ov("Value #C", rename="Entrant", unit="bps"),
                   ov("Value #D", rename="Sortant", unit="bps"), ov("Value #E", rename="Erreurs (1 h)", cell="color-text", thr=steps((1, ORANGE), (100, RED))),
                   ov("ifDescr", hidden=True), ov("ifIndex", hidden=True), ov("instance", rename="IP")],
        transformations=[{"id": "merge", "options": {}}, HIDE_TIME], sort=("Entrant", True)), 24, 12, newrow=True)
    D.save("switchs.json")


def build_zabbix():
    D = Dash("zabbix", "Supervision · Problèmes Zabbix", ["zabbix"], time_from="now-24h")
    ZDS = {"type": "alexanderzobnin-zabbix-datasource", "uid": "zabbix"}
    D.add(stat("Problèmes Zabbix en cours", [q('count(netmap_zabbix_problem) or vector(0)', instant=True)], thresholds=steps((1, ORANGE))), 8, 4)
    D.add(stat("Critiques", [q('count(netmap_zabbix_problem{severity="critical"}) or vector(0)', instant=True)], thresholds=steps((1, RED))), 8, 4)
    D.add(stat("Zabbix", [q('max(netmap_zabbix_up)', instant=True)], mappings=UP_MAP, thresholds=steps((1, GREEN), base=RED)), 8, 4)
    D.add({"type": "alexanderzobnin-zabbix-triggers-panel", "title": "Problèmes (VMware natif, SNMP, agents Zabbix)", "datasource": ZDS,
           "targets": [{"refId": "A", "queryType": "5", "datasource": ZDS, "group": {"filter": "/.*/"}, "host": {"filter": "/.*/"},
                        "proxy": {"filter": ""}, "application": {"filter": ""}, "trigger": {"filter": ""}, "tags": {"filter": ""},
                        "showProblems": "problems", "options": {"minSeverity": 2, "acknowledged": 2, "sortProblems": "default",
                                                                "showDisabledItems": False, "hostsInMaintenance": False, "limit": 1001}}],
           "options": {"layout": "table", "pageSize": 15, "showTags": True, "hostField": True, "severityField": True,
                       "statusField": True, "ackField": True, "ageField": True, "descriptionField": True}}, 24, 14, newrow=True)
    D.add(table("Problèmes (vus par le cockpit)", [q('netmap_zabbix_problem', instant=True, fmt="table")],
                overrides=[ov("severity", rename="Gravité", cell="color-background", mappings=SEV_MAP, width=110),
                           ov("problem", rename="Problème"), ov("host", rename="Hôte"), ov("priority", hidden=True),
                           ov("Value", hidden=True), ov("instance", hidden=True)], transformations=[HIDE_TIME]), 24, 8, newrow=True)
    D.save("zabbix.json")


def build_logs():
    host = {"name": "host", "label": "Serveur", "type": "query", "datasource": LOKI,
            "query": {"label": "host", "stream": "", "type": 1, "refId": "v"}, "definition": "label_values(host)",
            "refresh": 2, "sort": 1, "includeAll": True, "multi": True, "allValue": ".+",
            "current": {"text": ["All"], "value": ["$__all"]}, "hide": 0}
    level = {"name": "level", "label": "Niveau", "type": "custom", "multi": True, "includeAll": True, "allValue": ".*",
             "query": "emerg,alert,crit,critical,err,error,warning,notice,info,debug",
             "current": {"text": ["All"], "value": ["$__all"]}, "hide": 0}
    search = {"name": "recherche", "label": "Texte (regex)", "type": "textbox", "query": "", "current": {"text": "", "value": ""}, "hide": 0}
    D = Dash("logs", "Supervision · Logs", ["logs"], [host, level, search], time_from="now-3h")
    sel_ = '{host=~"$host", level=~"$level"} |~ "(?i)$recherche"'
    D.add(ts("Volume de logs par niveau", [{**lq(f'sum by (level) (count_over_time({sel_} [$__auto]))'), "legendFormat": "{{level}}"}],
             ds=LOKI, stack=True, fill=70, legend="list"), 16, 7)
    D.add(bargauge("Serveurs les plus bavards en erreurs", [{**lq('topk(10, sum by (host) (count_over_time({host=~"$host", level=~"err|crit|alert|emerg|error|critical"} [$__range])))', qtype="instant"), "legendFormat": "{{host}}"}],
                   unit="short", maxv=None, thresholds=steps((1, ORANGE), (100, RED))), 8, 7)
    D.d["panels"][-1]["datasource"] = LOKI
    D.add({"type": "logs", "title": "Logs", "datasource": LOKI, "targets": [lq(sel_)],
           "options": {"showTime": True, "showLabels": False, "wrapLogMessage": True, "sortOrder": "Descending",
                       "enableLogDetails": True, "dedupStrategy": "none"}}, 24, 18, newrow=True)
    D.save("logs.json")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_overview(); build_server(); build_network(); build_vmware(); build_switches(); build_zabbix(); build_logs()
    for f in sorted(OUT.glob("*.json")):
        d = json.loads(f.read_text())
        print(f"{f.name:24} {len(d['panels']):3} panneaux")
