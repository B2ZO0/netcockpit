/* NetCockpit : interface bilingue (français / anglais). Ajouter une langue = ajouter un bloc. */
"use strict";
const I18n = (() => {
  const D = {
    fr: {
      "nav.overview": "Vue d'ensemble", "nav.topology": "Topologie", "nav.vmware": "VMware", "nav.switches": "Switchs",
      "nav.inventory": "Inventaire", "nav.alerts": "Alertes", "nav.services": "Services", "title.vmware": "VMware vSphere",
      "top.allSites": "Tous les sites", "top.search": "Chercher un équipement : nom, IP, MAC…", "top.ai": "Briefing IA",
      "top.live": "en direct", "top.lost": "connexion perdue",
      "rail.sources": "Sources de données", "rail.rescan": "Relancer la découverte du réseau", "rail.rescanStarted": "Découverte relancée",
      "rail.toDay": "Passer en thème jour", "rail.toNight": "Passer en thème nuit", "rail.toLang": "Switch to English", "rail.links": "Outils",
      "src.connected": "connecté", "src.error": "erreur", "src.off": "non configuré", "src.scan": "Scan réseau", "src.ai": "IA",
      "scan.running": "Scan en cours…", "scan.last": "Dernier scan à {t}",
      "loading": "Chargement…", "close": "Fermer",
      "status.up": "OK", "status.warning": "Alerte", "status.critical": "Critique", "status.down": "En panne", "status.off": "Éteint",
      "status.absent": "Absent", "status.unknown": "Inconnu", "status.net": "Réseau", "status.info": "Info",
      "sev.critical": "Critique", "sev.warning": "Attention", "sev.info": "Info",
      "time.now": "à l'instant", "time.min": "il y a {n} min", "time.h": "il y a {h} h {m}", "time.d": "il y a {n} j",
      "dur.dh": "{d} j {h} h", "dur.hm": "{h} h {m} min", "unit.gb": "Go", "unit.tb": "To",
      "chart.none": "Pas encore d'historique.", "chart.legend": "Actuel {c}, moyenne {a}, max {m}", "chart.span": "24 h",

      "ov.nominal": "Tout est nominal", "ov.problems_one": "1 problème demande ton attention",
      "ov.problems_other": "{n} problèmes demandent ton attention", "ov.outage": "Internet est coupé",
      "ov.facts_one": "{total} équipements sur 1 site, scan à {t}", "ov.facts_other": "{total} équipements sur {n} sites, scan à {t}",
      "ov.route": "Route vers Internet", "ov.routeHint": "latence mesurée en continu à chaque étape",
      "ov.mini": "Topologie en direct", "ov.openTopo": "Ouvrir la topologie",
      "g.devices": "Équipements", "g.online": "en ligne sur {n}", "g.down": "{n} en panne", "g.absentOff": "{a} absents, {o} éteints",
      "g.alerts": "Alertes", "g.alertsSub": "{c} critiques, {w} attention, {i} info",
      "g.internet": "Internet", "g.cut": "Coupé", "g.noPath": "chemin inconnu",
      "g.agents": "Serveurs avec agent", "g.silent": "{n} muet(s)", "g.allReport": "tous remontent", "g.noAgent": "aucun agent installé",
      "g.vmware": "VMware", "g.vmOn": "VM allumées sur {n}", "g.vmSub": "{ok}/{h} ESXi, datastore le plus plein {ds}",
      "g.vmAlarms": "{n} alarme(s)", "g.vmOff": "Non connecté", "g.vmHint": "Renseigne VCENTER_* dans .env",
      "g.zabbix": "Zabbix", "g.zProblems": "problème(s)", "g.zSub": "VMware natif et SNMP", "g.zDown": "injoignable",
      "g.lastScan": "Dernier scan", "g.scanDur": "durée {n} s",
      "ov.problemsTitle": "Problèmes en cours", "ov.seeAll": "Tout voir", "ov.noProblem": "Aucun problème en cours",
      "ov.sites": "Sites", "site.online": "{n} en ligne", "site.down": "{n} en panne", "site.alerts": "{n} alerte(s)",
      "site.noNets": "réseaux hors plages déclarées", "site.open": "Voir sur la topologie",
      "cat.down": "{n} en panne", "cat.warn": "{n} alerte", "cat.absent": "{n} absent(s)",
      "cat.servers": "Serveurs", "cat.workstations": "Postes", "cat.printers": "Imprimantes", "cat.phones": "Téléphones IP",
      "cat.cameras": "Caméras", "cat.network": "Réseau", "cat.mobile": "Mobiles", "cat.other": "Autres",
      "ov.busiest": "Serveurs les plus chargés", "ov.inventory": "Inventaire", "col.server": "Serveur", "col.disk": "Disque",
      "ov.noAgent": "Aucun agent installé pour l'instant : installe Alloy sur tes serveurs pour voir CPU, RAM, disques et logs ici.",
      "ov.new": "Nouveaux appareils sur 24 h", "ov.noNew": "Aucun nouvel appareil depuis 24 h.",
      "ov.web": "Services web", "ov.noWeb": "Ajoute tes sites web dans config/cockpit.yml (http_checks).", "ov.cert": "certificat {n} j",

      "d.ip": "Adresse IP", "d.dns": "Nom DNS", "d.netbios": "Nom NetBIOS", "d.mac": "Adresse MAC", "d.vendor": "Constructeur",
      "d.type": "Type", "d.os": "Système", "d.site": "Site", "d.subnet": "Réseau", "d.plugged": "Branché sur", "d.attached": "Rattaché à",
      "d.port": "port", "d.esxiHost": "Hôte ESXi", "d.ports": "Ports ouverts", "d.latency": "Latence", "d.avail": "Disponibilité sur 24 h",
      "d.sources": "Découvert par", "d.first": "Première détection", "d.last": "Dernière détection", "d.otherIps": "Autres IP",
      "d.identity": "Identité", "d.resources": "Ressources", "d.uptime": "Allumé depuis {d}", "d.disk": "Disque",
      "d.vm": "Machine virtuelle", "d.vmRes": "{c} vCPU, {m} Go de RAM, {d} de disque", "d.tools": "VMware Tools", "d.vmUp": "Allumée depuis",
      "d.hyp": "Hyperviseur", "d.model": "Modèle", "d.version": "Version", "d.cluster": "Cluster", "d.cpu": "Processeur",
      "d.cores": "{n} cœurs, {p} utilisés", "d.mem": "Mémoire", "d.state": "État", "d.maint": "maintenance",
      "d.disks": "Disques", "d.cpu24": "CPU sur 24 h", "d.lat24": "Latence sur 24 h", "d.vms": "Machines virtuelles",
      "d.children": "Équipements rattachés", "d.usedPorts": "Ports utilisés", "d.logs": "Derniers logs", "d.errors": "{n} erreur(s) en 24 h",
      "d.ai": "Analyser avec l'IA", "d.aiRunning": "Analyse en cours…", "d.aiErr": "L'analyse IA a échoué.", "d.open": "Ouvrir",
      "d.notFound": "Équipement introuvable.", "d.new": "Nouveau",
      "ai.meta": "Analyse générée par {p} ({m}){c}. À vérifier avant d'agir.", "ai.cached": ", résultat récent réutilisé",
      "ai.title": "Briefing de la situation", "ai.intro": "Toutes les alertes, l'état des sites et la route Internet sont envoyés à l'IA.", "ai.err": "Le briefing IA a échoué.",
      "search.none": "Aucun résultat",

      "vm.notTitle": "vCenter n'est pas encore connecté",
      "vm.notBody": "Avec un compte en <b>lecture seule</b>, le cockpit affiche chaque ESXi, ses VM (CPU, RAM, IP, OS), les datastores, les alarmes vCenter, et sur quel switch et quel port chaque ESXi est branché (CDP/LLDP).<ol><li>Dans vCenter, crée un utilisateur (par exemple <code>supervision@vsphere.local</code>) et donne-lui le rôle <b>Read-only</b> à la racine, propagé.</li><li>Dans <code>.env</code>, renseigne <code>VCENTER_URL=https://ton-vcenter/sdk</code>, <code>VCENTER_USER</code> et <code>VCENTER_PASSWORD</code>.</li><li>Relance <code>./setup.sh</code>.</li></ol>",
      "vm.sub": "{h} ESXi, {on}/{n} VM allumées", "vm.unreach": ", vCenter injoignable : {e}", "vm.off": "éteinte", "vm.noIp": "pas d'IP",
      "vm.line": "{ip}, {c} vCPU, {m} Go", "vm.cores": "{n} cœurs, {u} / {t} GHz", "vm.mem": "{u} / {t} Go, allumé depuis {d}",
      "vm.vmsOn": "{on} VM allumées sur {n}", "vm.ds": "Datastores", "vm.dsFree": "{f} libres sur {c}", "vm.noDs": "Aucun datastore",
      "vm.alarms": "Alarmes vCenter", "vm.noAlarm": "Aucune alarme vCenter", "vm.acked": "acquittée",

      "sw.sub": "{n} switch(s) cartographié(s)", "sw.snmp": ", SNMP actif", "sw.active": "actif", "sw.free": "libre",
      "sw.vms": "+ {n} VM derrière l'ESXi", "sw.unknownIp": "IP inconnue", "sw.connected": "{n} équipement(s)", "sw.seenBy": "vu par {s}",
      "sw.legDev": "équipement identifié", "sw.legUp": "liaison ou uplink", "sw.legActive": "actif, non identifié", "sw.legFree": "libre",
      "col.port": "Port", "col.plugged": "Branché", "col.desc": "Description", "col.speed": "Vitesse", "col.traffic": "Trafic", "col.source": "Source",
      "sw.detected": "Équipements réseau détectés sans détail de ports", "sw.noticeTitle": "Pour voir chaque port de chaque switch",
      "sw.noticeBody": "Aujourd'hui, les switchs sont reconnus grâce aux ESXi (CDP/LLDP via vCenter) et aux serveurs Linux (lldpd). Pour la carte complète (qui est branché sur quel port, trafic, ports en erreur), demande au prestataire un <b>accès SNMP v2c en lecture seule</b> depuis l'IP de la supervision, puis renseigne <code>snmp.community</code> et <code>snmp.devices</code> (IP des switchs et du firewall) dans <code>config/cockpit.yml</code>.",
      "sw.snmpErr": "Erreurs SNMP : ", "sw.none": "Aucun switch cartographié pour l'instant.",

      "inv.filter": "Filtrer : nom, IP, MAC, constructeur, OS…", "inv.allStates": "Tous les états", "inv.problems": "Problèmes",
      "inv.absent": "Absents ou éteints", "inv.new": "Nouveaux", "inv.allTypes": "Tous les types", "inv.count": "{n} équipement(s)",
      "inv.csv": "Exporter en CSV", "inv.newBadge": "nouveau",
      "col.status": "État", "col.name": "Nom", "col.ip": "IP", "col.mac": "MAC", "col.vendor": "Constructeur", "col.type": "Type",
      "col.os": "Système", "col.site": "Site", "col.switch": "Switch et port", "col.latency": "Latence", "col.seen": "Vu",

      "al.all": "Toutes ({n})", "al.critical": "Critiques ({n})", "al.warning": "Attention ({n})", "al.info": "Info ({n})",
      "al.silence": "Mettre en silence", "al.ai": "Briefing IA", "al.none": "Aucune alerte en cours", "al.noneFilter": "Aucune alerte pour ce filtre",

      "svc.web": "Sites et applications web", "col.response": "Réponse", "col.code": "Code", "col.cert": "Certificat",
      "svc.days": "{n} jours", "svc.noHttp": "Aucun contrôle HTTP : ajoute tes sites dans <code>config/cockpit.yml</code> (http_checks).",
      "svc.dns": "Serveurs DNS", "svc.none": "Aucun", "svc.inet": "Cibles Internet",

      "tp.group": "Regrouper les postes", "tp.vms": "VM", "tp.ips": "IP", "tp.problems": "Problèmes seulement", "tp.fit": "Recentrer",
      "tp.png": "Image PNG", "tp.legSeen": "lien observé (LLDP, CDP, SNMP)", "tp.legLan": "rattachement au réseau",
      "tp.hint": "Clic : fiche. Clic sur un groupe : déplier.", "tp.devices": "équipements", "tp.ok": "OK", "tp.down": "en panne",
      "tp.alerts": "alertes", "tp.absent": "absents", "tp.site": "Site : {s}", "tp.legAbsent": "Absent ou éteint",
      "grp.down": "{n} en panne", "grp.warn": "{n} alerte", "grp.absent": "{n} absent(s)",
      "grp.workstations": ["poste", "postes"], "grp.phones": ["téléphone IP", "téléphones IP"], "grp.printers": ["imprimante", "imprimantes"],
      "grp.mobile": ["mobile", "mobiles"], "grp.other": ["équipement", "équipements"], "grp.cameras": ["caméra", "caméras"],

      "role.internet": "Internet", "role.isp": "Opérateur", "role.gateway": "Passerelle", "role.firewall": "Firewall", "role.router": "Routeur",
      "role.switch": "Switch", "role.network": "Équipement réseau", "role.wifi": "Borne Wi-Fi", "role.esxi": "ESXi", "role.hypervisor": "Hyperviseur",
      "role.vm": "VM", "role.server": "Serveur", "role.dc": "Contrôleur de domaine", "role.windows": "Poste Windows", "role.linux": "Linux",
      "role.nas": "NAS", "role.printer": "Imprimante", "role.camera": "Caméra", "role.phone": "Téléphone IP", "role.mobile": "Mobile",
      "role.device": "Équipement", "role.site": "Site", "role.subnet": "Réseau", "role.group": "Groupe", "role.other": "Autre",
    },
    en: {
      "nav.overview": "Overview", "nav.topology": "Topology", "nav.vmware": "VMware", "nav.switches": "Switches",
      "nav.inventory": "Inventory", "nav.alerts": "Alerts", "nav.services": "Services", "title.vmware": "VMware vSphere",
      "top.allSites": "All sites", "top.search": "Find a device: name, IP, MAC…", "top.ai": "AI briefing",
      "top.live": "live", "top.lost": "connection lost",
      "rail.sources": "Data sources", "rail.rescan": "Rescan the network", "rail.rescanStarted": "Rescan started",
      "rail.toDay": "Switch to day theme", "rail.toNight": "Switch to night theme", "rail.toLang": "Passer en français", "rail.links": "Tools",
      "src.connected": "connected", "src.error": "error", "src.off": "not configured", "src.scan": "Network scan", "src.ai": "AI",
      "scan.running": "Scanning…", "scan.last": "Last scan at {t}",
      "loading": "Loading…", "close": "Close",
      "status.up": "OK", "status.warning": "Warning", "status.critical": "Critical", "status.down": "Down", "status.off": "Off",
      "status.absent": "Absent", "status.unknown": "Unknown", "status.net": "Network", "status.info": "Info",
      "sev.critical": "Critical", "sev.warning": "Warning", "sev.info": "Info",
      "time.now": "just now", "time.min": "{n} min ago", "time.h": "{h} h {m} ago", "time.d": "{n} d ago",
      "dur.dh": "{d} d {h} h", "dur.hm": "{h} h {m} min", "unit.gb": "GB", "unit.tb": "TB",
      "chart.none": "No history yet.", "chart.legend": "Now {c}, average {a}, max {m}", "chart.span": "24 h",

      "ov.nominal": "All systems nominal", "ov.problems_one": "1 problem needs attention",
      "ov.problems_other": "{n} problems need attention", "ov.outage": "Internet is down",
      "ov.facts_one": "{total} devices on 1 site, scanned at {t}", "ov.facts_other": "{total} devices across {n} sites, scanned at {t}",
      "ov.route": "Route to the Internet", "ov.routeHint": "latency measured continuously at each hop",
      "ov.mini": "Live topology", "ov.openTopo": "Open topology",
      "g.devices": "Devices", "g.online": "online of {n}", "g.down": "{n} down", "g.absentOff": "{a} absent, {o} off",
      "g.alerts": "Alerts", "g.alertsSub": "{c} critical, {w} warning, {i} info",
      "g.internet": "Internet", "g.cut": "Down", "g.noPath": "path unknown",
      "g.agents": "Servers with agent", "g.silent": "{n} silent", "g.allReport": "all reporting", "g.noAgent": "no agent installed",
      "g.vmware": "VMware", "g.vmOn": "VMs running of {n}", "g.vmSub": "{ok}/{h} ESXi, fullest datastore {ds}",
      "g.vmAlarms": "{n} alarm(s)", "g.vmOff": "Not connected", "g.vmHint": "Set VCENTER_* in .env",
      "g.zabbix": "Zabbix", "g.zProblems": "problem(s)", "g.zSub": "Native VMware and SNMP", "g.zDown": "unreachable",
      "g.lastScan": "Last scan", "g.scanDur": "took {n} s",
      "ov.problemsTitle": "Open problems", "ov.seeAll": "See all", "ov.noProblem": "No open problems",
      "ov.sites": "Sites", "site.online": "{n} online", "site.down": "{n} down", "site.alerts": "{n} alert(s)",
      "site.noNets": "networks outside declared ranges", "site.open": "Show on topology",
      "cat.down": "{n} down", "cat.warn": "{n} warning", "cat.absent": "{n} absent",
      "cat.servers": "Servers", "cat.workstations": "Workstations", "cat.printers": "Printers", "cat.phones": "IP phones",
      "cat.cameras": "Cameras", "cat.network": "Network", "cat.mobile": "Mobiles", "cat.other": "Other",
      "ov.busiest": "Busiest servers", "ov.inventory": "Inventory", "col.server": "Server", "col.disk": "Disk",
      "ov.noAgent": "No agent installed yet: install Alloy on your servers to see CPU, memory, disks and logs here.",
      "ov.new": "New devices in the last 24 h", "ov.noNew": "No new device in the last 24 h.",
      "ov.web": "Web services", "ov.noWeb": "Add your websites to config/cockpit.yml (http_checks).", "ov.cert": "certificate {n} d",

      "d.ip": "IP address", "d.dns": "DNS name", "d.netbios": "NetBIOS name", "d.mac": "MAC address", "d.vendor": "Vendor",
      "d.type": "Type", "d.os": "Operating system", "d.site": "Site", "d.subnet": "Network", "d.plugged": "Plugged into", "d.attached": "Attached to",
      "d.port": "port", "d.esxiHost": "ESXi host", "d.ports": "Open ports", "d.latency": "Latency", "d.avail": "Availability over 24 h",
      "d.sources": "Discovered by", "d.first": "First seen", "d.last": "Last seen", "d.otherIps": "Other IPs",
      "d.identity": "Identity", "d.resources": "Resources", "d.uptime": "Up for {d}", "d.disk": "Disk",
      "d.vm": "Virtual machine", "d.vmRes": "{c} vCPU, {m} GB memory, {d} disk", "d.tools": "VMware Tools", "d.vmUp": "Up for",
      "d.hyp": "Hypervisor", "d.model": "Model", "d.version": "Version", "d.cluster": "Cluster", "d.cpu": "CPU",
      "d.cores": "{n} cores, {p} used", "d.mem": "Memory", "d.state": "State", "d.maint": "maintenance",
      "d.disks": "Disks", "d.cpu24": "CPU over 24 h", "d.lat24": "Latency over 24 h", "d.vms": "Virtual machines",
      "d.children": "Attached devices", "d.usedPorts": "Ports in use", "d.logs": "Recent logs", "d.errors": "{n} error(s) in 24 h",
      "d.ai": "Analyse with AI", "d.aiRunning": "Analysing…", "d.aiErr": "The AI analysis failed.", "d.open": "Open",
      "d.notFound": "Device not found.", "d.new": "New",
      "ai.meta": "Generated by {p} ({m}){c}. Check before acting.", "ai.cached": ", recent result reused",
      "ai.title": "Situation briefing", "ai.intro": "All alerts, site status and the Internet route are sent to the AI.", "ai.err": "The AI briefing failed.",
      "search.none": "No results",

      "vm.notTitle": "vCenter is not connected yet",
      "vm.notBody": "With a <b>read-only</b> account, the cockpit shows every ESXi host, its VMs (CPU, memory, IP, OS), datastores, vCenter alarms, and which switch and port each host is plugged into (CDP/LLDP).<ol><li>In vCenter, create a user (for example <code>monitoring@vsphere.local</code>) and give it the <b>Read-only</b> role on the root, propagated.</li><li>In <code>.env</code>, set <code>VCENTER_URL=https://your-vcenter/sdk</code>, <code>VCENTER_USER</code> and <code>VCENTER_PASSWORD</code>.</li><li>Run <code>./setup.sh</code> again.</li></ol>",
      "vm.sub": "{h} ESXi, {on}/{n} VMs running", "vm.unreach": ", vCenter unreachable: {e}", "vm.off": "powered off", "vm.noIp": "no IP",
      "vm.line": "{ip}, {c} vCPU, {m} GB", "vm.cores": "{n} cores, {u} / {t} GHz", "vm.mem": "{u} / {t} GB, up for {d}",
      "vm.vmsOn": "{on} of {n} VMs running", "vm.ds": "Datastores", "vm.dsFree": "{f} free of {c}", "vm.noDs": "No datastore",
      "vm.alarms": "vCenter alarms", "vm.noAlarm": "No vCenter alarm", "vm.acked": "acknowledged",

      "sw.sub": "{n} switch(es) mapped", "sw.snmp": ", SNMP on", "sw.active": "active", "sw.free": "free",
      "sw.vms": "+ {n} VMs behind the ESXi host", "sw.unknownIp": "unknown IP", "sw.connected": "{n} device(s)", "sw.seenBy": "seen by {s}",
      "sw.legDev": "identified device", "sw.legUp": "link or uplink", "sw.legActive": "active, unidentified", "sw.legFree": "free",
      "col.port": "Port", "col.plugged": "Connected", "col.desc": "Description", "col.speed": "Speed", "col.traffic": "Traffic", "col.source": "Source",
      "sw.detected": "Network devices found without port detail", "sw.noticeTitle": "To see every port of every switch",
      "sw.noticeBody": "Right now, switches are recognised through the ESXi hosts (CDP/LLDP via vCenter) and Linux servers (lldpd). For the full map (what is plugged into which port, traffic, ports in error), ask your provider for <b>read-only SNMP v2c access</b> from the monitoring host's IP, then set <code>snmp.community</code> and <code>snmp.devices</code> (switch and firewall IPs) in <code>config/cockpit.yml</code>.",
      "sw.snmpErr": "SNMP errors: ", "sw.none": "No switch mapped yet.",

      "inv.filter": "Filter: name, IP, MAC, vendor, OS…", "inv.allStates": "All states", "inv.problems": "Problems",
      "inv.absent": "Absent or off", "inv.new": "New", "inv.allTypes": "All types", "inv.count": "{n} device(s)",
      "inv.csv": "Export to CSV", "inv.newBadge": "new",
      "col.status": "Status", "col.name": "Name", "col.ip": "IP", "col.mac": "MAC", "col.vendor": "Vendor", "col.type": "Type",
      "col.os": "OS", "col.site": "Site", "col.switch": "Switch and port", "col.latency": "Latency", "col.seen": "Seen",

      "al.all": "All ({n})", "al.critical": "Critical ({n})", "al.warning": "Warning ({n})", "al.info": "Info ({n})",
      "al.silence": "Silence", "al.ai": "AI briefing", "al.none": "No active alert", "al.noneFilter": "No alert for this filter",

      "svc.web": "Websites and web apps", "col.response": "Response", "col.code": "Code", "col.cert": "Certificate",
      "svc.days": "{n} days", "svc.noHttp": "No HTTP check yet: add your websites to <code>config/cockpit.yml</code> (http_checks).",
      "svc.dns": "DNS servers", "svc.none": "None", "svc.inet": "Internet targets",

      "tp.group": "Group workstations", "tp.vms": "VMs", "tp.ips": "IPs", "tp.problems": "Problems only", "tp.fit": "Fit",
      "tp.png": "PNG image", "tp.legSeen": "observed link (LLDP, CDP, SNMP)", "tp.legLan": "attached to network",
      "tp.hint": "Click: details. Click a group: expand.", "tp.devices": "devices", "tp.ok": "OK", "tp.down": "down",
      "tp.alerts": "warnings", "tp.absent": "absent", "tp.site": "Site: {s}", "tp.legAbsent": "Absent or off",
      "grp.down": "{n} down", "grp.warn": "{n} warning", "grp.absent": "{n} absent",
      "grp.workstations": ["workstation", "workstations"], "grp.phones": ["IP phone", "IP phones"], "grp.printers": ["printer", "printers"],
      "grp.mobile": ["mobile", "mobiles"], "grp.other": ["device", "devices"], "grp.cameras": ["camera", "cameras"],

      "role.internet": "Internet", "role.isp": "ISP", "role.gateway": "Gateway", "role.firewall": "Firewall", "role.router": "Router",
      "role.switch": "Switch", "role.network": "Network device", "role.wifi": "Wi-Fi access point", "role.esxi": "ESXi", "role.hypervisor": "Hypervisor",
      "role.vm": "VM", "role.server": "Server", "role.dc": "Domain controller", "role.windows": "Windows workstation", "role.linux": "Linux",
      "role.nas": "NAS", "role.printer": "Printer", "role.camera": "Camera", "role.phone": "IP phone", "role.mobile": "Mobile",
      "role.device": "Device", "role.site": "Site", "role.subnet": "Network", "role.group": "Group", "role.other": "Other",
    },
  };
  const pick = () => {
    try { const s = JSON.parse(localStorage.getItem("cockpit.lang")); if (D[s]) return s; } catch (e) { /* ignoré */ }
    return /^fr\b/i.test(navigator.language || "") ? "fr" : "en";
  };
  let lang = pick();
  function t(key, vars) {
    const dict = D[lang] || D.en;
    let k = key;
    if (vars && vars.n != null && dict[`${key}_one`] != null) k = `${key}_${Number(vars.n) === 1 ? "one" : "other"}`;
    let s = dict[k] ?? D.en[k] ?? key;
    if (typeof s === "string" && vars) s = s.replace(/\{(\w+)\}/g, (m, v) => (vars[v] ?? m));
    return s;
  }
  const role = (r, fallback) => (D[lang][`role.${r}`] ?? fallback ?? r);
  function set(l) { if (!D[l]) return; lang = l; try { localStorage.setItem("cockpit.lang", JSON.stringify(l)); } catch (e) { /* ignoré */ } document.documentElement.lang = l; }
  document.documentElement.lang = lang;
  // noms générés par le cockpit (« Opérateur (x) », « Passerelle x »…) : traduits à l'affichage
  const NAMES = [[/^Opérateur\b/, "ISP"], [/^Passerelle\b/, "Gateway"], [/^Routeur\b/, "Router"], [/^Autres réseaux$/, "Other networks"]];
  const name = (s) => (lang === "fr" || !s ? s : NAMES.reduce((a, [re, en]) => a.replace(re, en), String(s)));
  return { t, role, name, set, get lang() { return lang; }, get locale() { return lang === "fr" ? "fr-FR" : "en-GB"; }, langs: Object.keys(D) };
})();
const t = I18n.t;
