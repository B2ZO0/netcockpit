# Roadmap · Feuille de route

NetCockpit grows one brick at a time: each version adds a small number of things, finished and documented, rather than everything at once. Dates are not promised; the order is.

*NetCockpit grandit une brique à la fois : chaque version ajoute peu de choses, finies et documentées, plutôt que tout en même temps. Les dates ne sont pas promises, l'ordre oui.*

Want something moved up, or want to help on one item? [Open an issue](https://github.com/B2ZO0/netcockpit/issues).
*Une idée, une priorité à changer, envie d'aider ? [Ouvre un ticket](https://github.com/B2ZO0/netcockpit/issues).*

## Calendar · Calendrier

A new piece lands every week as a pull request, with tests and docs. A version is published only after it has run on a real network.
*Une nouveauté arrive chaque semaine sous forme de pull request, avec tests et documentation. Une version n'est publiée qu'après avoir tourné sur un vrai réseau.*

| Weeks · Semaines | Version | Focus |
|---|---|---|
| Nov 2026 | **1.2** | Proxmox, one-command update, security hardening, ready-made Docker images |
| Dec 2026 | **1.3** | Setup from the browser, with a guide; compatibility reports |
| Jan 2027 | **1.4** | Connectors: firewalls, NAS, UPS, SNMPv3, menu that adapts |
| Feb 2027 | **1.5** | Library of ready-made checks, custom overview |
| Mar 2027 | **1.6** | Hyper-V, several hypervisor endpoints, single sign-on |

## 1.2 · Proxmox and painless updates *(in progress)*

- [x] **Proxmox VE**: nodes, VMs, LXC containers and storages, with a read-only API token. *Proxmox VE : nœuds, VM, conteneurs LXC et stockages, avec un jeton en lecture seule.*
- [x] **`./setup.sh --update`**: one command, settings and history kept. *Une commande, réglages et historique conservés.*
- [x] Hypervisors detected automatically; the menu hides what you do not have. *Hyperviseurs détectés automatiquement ; le menu masque ce que tu n'as pas.*
- [x] The VMware screen becomes a platform-neutral Virtualization screen. *L'écran VMware devient un écran Virtualisation.*
- [ ] Feedback from real Proxmox clusters (versions 7, 8, 9) *(maintainer test, not code)*. *Retours sur de vrais clusters Proxmox (test du mainteneur).*
- [x] Security: protected `/metrics`, Secure session cookie, optional vCenter TLS verification. *Sécurité : `/metrics` protégé, cookie sécurisé, vérification TLS de vCenter.*
- [x] Ready-made Docker image on GitHub Container Registry: nothing to build on the host, faster install and update. *Image Docker prête à l'emploi : rien à compiler, installation et mise à jour plus rapides.*
- [ ] **Updates follow releases**: `./setup.sh --update` moves to the latest published version, never to work in progress (`--update --edge` for testers). It never goes backwards. *Les mises à jour suivent les versions publiées : `--update` installe la dernière version publiée, jamais le travail en cours (`--edge` pour les testeurs), et ne revient jamais en arrière.*
- [ ] "New version available" notice in the cockpit, opt-in. *Bandeau « nouvelle version disponible », à activer.*

## 1.3 · Setup from the browser

Installing and configuring without editing a single file: what makes beginners give up today.
*Installer et configurer sans éditer un seul fichier : c'est ce qui fait abandonner les débutants aujourd'hui.*

- [ ] **Compatibility report**: `./setup.sh --report` prints what NetCockpit detected (hypervisors and versions, switches, SNMP), without addresses or names, ready to paste in an issue. *Rapport de compatibilité : ce que NetCockpit a détecté, sans adresses ni noms, prêt à coller dans un ticket.*
- [ ] **"Works on my setup" issue template**: 30 seconds to say what runs NetCockpit fine. *Modèle de ticket « Ça marche chez moi » : 30 secondes pour dire sur quoi NetCockpit tourne bien.*
- [ ] **"Tested with" table** in both READMEs (Proxmox, ESXi/vCenter, UniFi, Cisco, firewalls, NAS…), filled from the reports: tested, reported by a user, not tried yet. *Tableau « Testé avec » dans les deux README, rempli à partir des retours.*
- [ ] A guided screen to add or edit a source (VMware, Proxmox, SNMP switches, Zabbix, Telegram, e-mail): enter, test, save. *Un écran guidé pour ajouter ou modifier une source : saisir, tester, enregistrer.*
- [ ] Buildings and networks editable from the cockpit. *Bâtiments et réseaux modifiables depuis le cockpit.*
- [ ] Secrets stay in `.env`, never shown again once saved; only logged-in admins can change settings. *Les secrets restent dans `.env`, jamais réaffichés ; seuls les admins connectés modifient les réglages.*
- [ ] First-run guide in the browser after `./setup.sh`, instead of terminal questions (the terminal assistant stays available). *Guide de premier démarrage dans le navigateur ; l'assistant en terminal reste disponible.*
- [ ] **Network diagram export**: the topology as a draw.io file (editable) and SVG, by building. *Export du schéma réseau : la topologie en fichier draw.io (modifiable) et en SVG, par bâtiment.*
- [ ] **Network report**: one printable page (PDF from the browser) with inventory, address plan, VLANs, hypervisors and open problems, without secrets. *Rapport réseau : une page imprimable (PDF depuis le navigateur) avec inventaire, plan d'adressage, VLAN, hyperviseurs et problèmes en cours, sans secrets.*

## 1.4 · Connectors

Everything you can monitor becomes a connector you switch on. What is not switched on does not appear in the interface.
*Tout ce qui peut être supervisé devient un connecteur à activer. Ce qui n'est pas activé n'apparaît pas dans l'interface.*

- [ ] Existing sources reorganised as connectors: VMware, Proxmox, SNMP, Zabbix. *Les sources actuelles deviennent des connecteurs.*
- [ ] Menu and overview adapt to what is connected. *Le menu et la vue d'ensemble s'adaptent à ce qui est connecté.*
- [ ] Firewalls over SNMP (pfSense, OPNsense, FortiGate): WAN state, VPN tunnels. *Pare-feu en SNMP : état du WAN, tunnels VPN.*
- [ ] NAS over SNMP (Synology, TrueNAS): volumes, disk health. *NAS en SNMP : volumes, santé des disques.*
- [ ] UPS (NUT or SNMP): battery, load, runtime left. *Onduleurs (NUT ou SNMP) : batterie, charge, autonomie restante.*
- [ ] SNMPv3.
- [ ] **Zabbix templates suggested from what was detected**: when Zabbix is enabled, the cockpit proposes the official Zabbix template that matches each detected device (firewall, NAS, UPS, switch) and shows its results. NetCockpit reuses Zabbix's integrations instead of rewriting them. *Modèles Zabbix proposés selon les équipements détectés : le cockpit réutilise les intégrations officielles de Zabbix au lieu de les réécrire.*
- [ ] Hyper-V inventory. *Inventaire Hyper-V.*

## 1.5 · Your cockpit

- [ ] Choose which instruments the overview shows. *Choisir les instruments de la vue d'ensemble.*
- [ ] A library of ready-made checks to switch on (certificates, DNS, AD replication, backups). *Une bibliothèque de contrôles prêts à activer (certificats, DNS, réplication AD, sauvegardes).*
- [ ] **Your own icons**: upload an icon per device, type or brand; it is used on the map and in the inventory. NetCockpit ships no brand logos. *Tes propres icônes : une icône par équipement, type ou marque, sur la carte et dans l'inventaire. NetCockpit ne fournit aucun logo de marque.*
- [ ] **Themes**: choose the accent colour (including a black and red theme), with the same readability on a wall screen. Animations stay light and can be turned off. *Thèmes : choix de la couleur d'accent (dont un thème noir et rouge), aussi lisible sur un écran mural. Animations légères, désactivables.*
- [ ] More languages. *D'autres langues.*

## Later · Plus tard

- Several vCenter, ESXi or Proxmox endpoints. *Plusieurs vCenter, ESXi ou Proxmox.*
- Single sign-on (OIDC) in front of the cockpit. *Authentification unique (OIDC).*

## What NetCockpit will stay · Ce qui ne changera pas

- **Read-only**: it observes, it never changes your network or your hypervisors. *Lecture seule : il observe, il ne modifie rien.*
- **One screen first**: new features must not make the overview harder to read. *Un écran d'abord : une nouveauté ne doit pas rendre la vue d'ensemble moins lisible.*
- **Self-hosted, no account, no telemetry.** *Auto-hébergé, sans compte, sans télémétrie.*
