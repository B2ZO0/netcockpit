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
| Nov 2026 | **1.2** | Proxmox, one-command update that follows releases, agent install over HTTPS, security, ready-made Docker image |
| Dec 2026 | **1.3** | Network diagram export (draw.io, SVG), install test in CI, light install, compatibility reports |
| Jan–Feb 2027 | **1.4** | Setup from the browser, doctor, backup and restore, printable network report |
| Mar–Apr 2027 | **1.5** | Connectors: firewalls, NAS, UPS, SNMPv3, VLANs on links, what changed, Zabbix templates |
| Later | **1.6** | Your cockpit: layout, map, icons, themes, more languages |

## 1.2 · Proxmox and painless updates *(in progress)*

- [x] **Agents only push**: from the network, ports 9090 and 3100 only accept what agents send; Prometheus and Loki can only be read on the monitoring host or through Grafana. *Les agents ne font qu'envoyer : depuis le réseau, les ports 9090 et 3100 n'acceptent que les envois des agents ; Prometheus et Loki ne se consultent que sur la machine de supervision ou dans Grafana.*
- [ ] **Agent token**: agents send metrics and logs with a token created at install, so that only your servers can push. *Jeton d'agent : les agents envoient leurs métriques et leurs logs avec un jeton créé à l'installation, pour que seuls tes serveurs puissent envoyer.*
- [x] **Pinned stack versions**: Prometheus, Loki, Grafana, Alertmanager, Alloy and the exporters use tested versions, moved forward by `./setup.sh --update`. *Versions de la pile épinglées : des versions testées, mises à jour par `./setup.sh --update`.*
- [x] Notification and SNMP secrets readable only by the containers that use them. *Secrets de notification et SNMP lisibles uniquement par les conteneurs qui s'en servent.*
- [ ] Cockpit container with the fewest privileges it needs (non-root user, network capabilities checked on a real network). *Conteneur du cockpit avec le minimum de droits (utilisateur non root, capacités réseau vérifiées sur un vrai réseau).*
- [x] **Proxmox VE**: nodes, VMs, LXC containers and storages, with a read-only API token. *Proxmox VE : nœuds, VM, conteneurs LXC et stockages, avec un jeton en lecture seule.*
- [x] **`./setup.sh --update`**: one command, settings and history kept. *Une commande, réglages et historique conservés.*
- [x] Hypervisors detected automatically; the menu hides what you do not have. *Hyperviseurs détectés automatiquement ; le menu masque ce que tu n'as pas.*
- [x] The VMware screen becomes a platform-neutral Virtualization screen. *L'écran VMware devient un écran Virtualisation.*
- [ ] Feedback from real Proxmox clusters (versions 7, 8, 9) *(maintainer test, not code)*. *Retours sur de vrais clusters Proxmox (test du mainteneur).*
- [x] Security: protected `/metrics`, Secure session cookie, optional vCenter TLS verification. *Sécurité : `/metrics` protégé, cookie sécurisé, vérification TLS de vCenter.*
- [x] Ready-made Docker image on GitHub Container Registry: nothing to build on the host, faster install and update. *Image Docker prête à l'emploi : rien à compiler, installation et mise à jour plus rapides.*
- [x] **Updates follow releases**: `./setup.sh --update` moves to the latest published version, never to work in progress (`--update --edge` for testers). It never goes backwards. *Les mises à jour suivent les versions publiées : `--update` installe la dernière version publiée, jamais le travail en cours (`--edge` pour les testeurs), et ne revient jamais en arrière.*
- [ ] **Agent install over HTTPS**: install scripts and agent binaries served over HTTPS with the cockpit's certificate, and checked against a checksum before they run, so nobody on the network can swap them on the way. *Installation des agents en HTTPS : scripts et agents servis en HTTPS et vérifiés par une empreinte avant exécution, pour que personne sur le réseau ne puisse les remplacer en route.*

## 1.3 · Your network on paper

The map becomes something you can hand over: an editable diagram. And NetCockpit runs on small machines.
*La carte devient un document à remettre : un schéma modifiable. Et NetCockpit tourne sur de petites machines.*

- [ ] **Network diagram export**: the topology as a draw.io file (editable) and SVG, by building. *Export du schéma réseau : la topologie en fichier draw.io (modifiable) et en SVG, par bâtiment.*
- [ ] **Light install**: cockpit, scan and map only, for a Raspberry Pi or a small container; metrics, logs and Zabbix can be added later without reinstalling. *Installation légère : cockpit, scan et carte seulement, pour un Raspberry Pi ou un petit conteneur ; métriques, logs et Zabbix s'ajoutent plus tard sans réinstaller.*
- [ ] **Install test on every change**: CI installs NetCockpit from scratch on a clean Debian and a clean Ubuntu, starts it and checks that the cockpit answers; shell scripts are linted. A change that breaks the install cannot be merged. *Test d'installation à chaque changement : la CI installe NetCockpit de zéro sur un Debian et un Ubuntu propres et vérifie que le cockpit répond. Un changement qui casse l'installation ne peut pas être fusionné.*
- [ ] **Compatibility report**: `./setup.sh --report` prints what NetCockpit detected (hypervisors and versions, switches, SNMP), without addresses or names, ready to paste in an issue. *Rapport de compatibilité : ce que NetCockpit a détecté, sans adresses ni noms, prêt à coller dans un ticket.*
- [ ] **"Works on my setup" issue template**: 30 seconds to say what runs NetCockpit fine. *Modèle de ticket « Ça marche chez moi » : 30 secondes pour dire sur quoi NetCockpit tourne bien.*
- [ ] **"Tested with" table** in both READMEs (Proxmox, ESXi/vCenter, UniFi, Cisco, firewalls, NAS…), filled from the reports: tested, reported by a user, not tried yet. *Tableau « Testé avec » dans les deux README, rempli à partir des retours.*

## 1.4 · Setup from the browser

Installing and configuring without editing a single file: what makes beginners give up today.
*Installer et configurer sans éditer un seul fichier : c'est ce qui fait abandonner les débutants aujourd'hui.*

- [ ] A guided screen to add or edit a source (VMware, Proxmox, SNMP switches, Zabbix, Telegram, e-mail): enter, test, save. *Un écran guidé pour ajouter ou modifier une source : saisir, tester, enregistrer.*
- [ ] Buildings and networks editable from the cockpit. *Bâtiments et réseaux modifiables depuis le cockpit.*
- [ ] Secrets stay in `.env`, never shown again once saved; only logged-in admins can change settings. *Les secrets restent dans `.env`, jamais réaffichés ; seuls les admins connectés modifient les réglages.*
- [ ] First-run guide in the browser after `./setup.sh`, instead of terminal questions (the terminal assistant stays available). *Guide de premier démarrage dans le navigateur ; l'assistant en terminal reste disponible.*
- [ ] **`./setup.sh --doctor`**: checks containers, ports, disk space and each source, and says in plain words what to fix. *Vérifie les conteneurs, les ports, le disque et chaque source, et dit simplement quoi corriger.*
- [ ] **`./setup.sh --backup` and `--restore`**: one archive with settings and history, to move to another machine or come back after a mistake. *Une archive avec les réglages et l'historique, pour changer de machine ou revenir en arrière.*
- [ ] **Network report**: one printable page (PDF from the browser) with inventory, address plan, VLANs, hypervisors and open problems, without secrets. *Rapport réseau : une page imprimable (PDF depuis le navigateur) avec inventaire, plan d'adressage, VLAN, hyperviseurs et problèmes en cours, sans secrets.*
- [ ] "New version available" notice in the cockpit, opt-in. *Bandeau « nouvelle version disponible », à activer.*

## 1.5 · Connectors

Everything you can monitor becomes a connector you switch on. What is not switched on does not appear in the interface.
*Tout ce qui peut être supervisé devient un connecteur à activer. Ce qui n'est pas activé n'apparaît pas dans l'interface.*

- [ ] Existing sources reorganised as connectors: VMware, Proxmox, SNMP, Zabbix. *Les sources actuelles deviennent des connecteurs.*
- [ ] Menu and overview adapt to what is connected. *Le menu et la vue d'ensemble s'adaptent à ce qui est connecté.*
- [ ] Firewalls over SNMP (pfSense, OPNsense, FortiGate): WAN state, VPN tunnels. *Pare-feu en SNMP : état du WAN, tunnels VPN.*
- [ ] NAS over SNMP (Synology, TrueNAS): volumes, disk health. *NAS en SNMP : volumes, santé des disques.*
- [ ] UPS (NUT or SNMP): battery, load, runtime left. *Onduleurs (NUT ou SNMP) : batterie, charge, autonomie restante.*
- [ ] SNMPv3.
- [ ] **VLANs on links**: untagged and tagged VLANs shown on each link when the switch gives them (U10, T20,30). *VLAN sur les liens : VLAN non tagué et tagués affichés quand le switch les donne.*
- [ ] **What changed**: new devices, devices that disappeared, addresses that moved since yesterday; optional alert when an unknown device appears. *Ce qui a changé : nouveaux équipements, disparus, adresses déplacées depuis hier ; alerte possible quand un appareil inconnu apparaît.*
- [ ] **Simple findings**, read-only: Telnet open, default SNMP community, admin page without HTTPS, second DHCP server. *Constats simples, en lecture seule : Telnet ouvert, communauté SNMP par défaut, page d'admin sans HTTPS, second serveur DHCP.*
- [ ] **Zabbix templates suggested from what was detected**: when Zabbix is enabled, the cockpit proposes the official Zabbix template that matches each detected device (firewall, NAS, UPS, switch) and shows its results. NetCockpit reuses Zabbix's integrations instead of rewriting them. *Modèles Zabbix proposés selon les équipements détectés : le cockpit réutilise les intégrations officielles de Zabbix au lieu de les réécrire.*
- [ ] Hyper-V inventory. *Inventaire Hyper-V.*

## 1.6 · Your cockpit

Everything works without touching anything; all customisation lives in one "Customise" screen, and "Reset" brings back the defaults.
*Tout marche sans rien toucher ; toute la personnalisation est dans un seul écran « Personnaliser », et « Réinitialiser » remet les réglages d'origine.*

- [ ] Choose which instruments the overview shows, and arrange them by drag and drop. *Choisir les instruments de la vue d'ensemble et les placer par glisser-déposer.*
- [ ] **Map layout**: move nodes and keep their position, colour per building, labels shown or hidden. *Carte personnalisable : déplacer les éléments et garder leur place, couleur par bâtiment, étiquettes affichées ou non.*
- [ ] A library of ready-made checks to switch on (certificates, DNS, AD replication, backups). *Une bibliothèque de contrôles prêts à activer (certificats, DNS, réplication AD, sauvegardes).*
- [ ] **Your own icons**: upload an icon per device, type or brand; it is used on the map and in the inventory. NetCockpit ships no brand logos. *Tes propres icônes : une icône par équipement, type ou marque, sur la carte et dans l'inventaire. NetCockpit ne fournit aucun logo de marque.*
- [ ] **Themes**: choose the accent colour (including a black and red theme), with the same readability on a wall screen. Animations stay light and can be turned off. *Thèmes : choix de la couleur d'accent (dont un thème noir et rouge), aussi lisible sur un écran mural. Animations légères, désactivables.*
- [ ] **Theme files**: a theme is one small file you can import, export and share; a few ready-made themes ship with NetCockpit. *Fichiers de thème : un thème est un petit fichier à importer, exporter et partager ; quelques thèmes prêts à l'emploi sont fournis.*
- [ ] **More languages for the interface**, chosen by the size of the self-hosting and sysadmin communities: German, Spanish, Portuguese (Brazil), Simplified Chinese first; then Italian, Polish, Russian, Japanese. One file per language, picked from the browser language. Each language is marked "needs review" until a native speaker has checked it, and corrections are welcome as first contributions. Guides stay in English and French. *D'autres langues pour l'interface : allemand, espagnol, portugais (Brésil), chinois simplifié d'abord ; puis italien, polonais, russe, japonais. Chaque langue reste marquée « à relire » tant qu'un natif ne l'a pas vérifiée ; les corrections sont de bonnes premières contributions. Les guides restent en anglais et en français.*

## Ideas · Idées

Proposals not scheduled yet; they join a version once the maintainer agrees. *Propositions pas encore programmées ; elles entrent dans une version une fois validées par le mainteneur.*

- **`./setup.sh --update --check`**: says which published version an update would install and lists its changes, without downloading or restarting anything. For admins who plan upgrades in a maintenance window. *Dit quelle version publiée la mise à jour installerait et ses changements, sans rien télécharger ni redémarrer. Pour les admins qui planifient leurs mises à jour sur un créneau de maintenance.*

## Later · Plus tard

- Several vCenter, ESXi or Proxmox endpoints. *Plusieurs vCenter, ESXi ou Proxmox.*
- Single sign-on (OIDC) in front of the cockpit. *Authentification unique (OIDC).*

## What NetCockpit will stay · Ce qui ne changera pas

- **Read-only**: it observes, it never changes your network or your hypervisors. *Lecture seule : il observe, il ne modifie rien.*
- **One screen first**: new features must not make the overview harder to read. *Un écran d'abord : une nouveauté ne doit pas rendre la vue d'ensemble moins lisible.*
- **Self-hosted, no account, no telemetry.** *Auto-hébergé, sans compte, sans télémétrie.*
