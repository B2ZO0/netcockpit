# Roadmap · Feuille de route

NetCockpit grows one brick at a time: each version adds a small number of things, finished and documented, rather than everything at once. Dates are not promised; the order is.

*NetCockpit grandit une brique à la fois : chaque version ajoute peu de choses, finies et documentées, plutôt que tout en même temps. Les dates ne sont pas promises, l'ordre oui.*

Want something moved up, or want to help on one item? [Open an issue](https://github.com/B2ZO0/netcockpit/issues).
*Une idée, une priorité à changer, envie d'aider ? [Ouvre un ticket](https://github.com/B2ZO0/netcockpit/issues).*

## 1.2 · Proxmox and painless updates *(in progress)*

- [x] **Proxmox VE**: nodes, VMs, LXC containers and storages, with a read-only API token. *Proxmox VE : nœuds, VM, conteneurs LXC et stockages, avec un jeton en lecture seule.*
- [x] **`./setup.sh --update`**: one command, settings and history kept. *Une commande, réglages et historique conservés.*
- [x] The VMware screen becomes a platform-neutral Virtualization screen. *L'écran VMware devient un écran Virtualisation.*
- [ ] Feedback from real Proxmox clusters (versions 7, 8, 9). *Retours sur de vrais clusters Proxmox.*
- [ ] "New version available" notice in the cockpit, opt-in. *Bandeau « nouvelle version disponible », à activer.*

## 1.3 · Connectors

Everything you can monitor becomes a connector you switch on. What is not switched on does not appear in the interface.
*Tout ce qui peut être supervisé devient un connecteur à activer. Ce qui n'est pas activé n'apparaît pas dans l'interface.*

- [ ] Existing sources reorganised as connectors: VMware, Proxmox, SNMP, Zabbix. *Les sources actuelles deviennent des connecteurs.*
- [ ] Menu and overview adapt to what is connected. *Le menu et la vue d'ensemble s'adaptent à ce qui est connecté.*
- [ ] Firewalls over SNMP (pfSense, OPNsense, FortiGate): WAN state, VPN tunnels. *Pare-feu en SNMP : état du WAN, tunnels VPN.*
- [ ] NAS over SNMP (Synology, TrueNAS): volumes, disk health. *NAS en SNMP : volumes, santé des disques.*
- [ ] SNMPv3.
- [ ] Hyper-V inventory. *Inventaire Hyper-V.*

## 1.4 · Setup from the browser

- [ ] A guided screen to add or edit a connector: enter, test, save. *Un écran guidé pour ajouter ou modifier un connecteur : saisir, tester, enregistrer.*
- [ ] Buildings and networks editable from the cockpit. *Bâtiments et réseaux modifiables depuis le cockpit.*
- [ ] Secrets stay in `.env`, never shown again once saved. *Les secrets restent dans `.env`, jamais réaffichés.*

## 1.5 · Your cockpit

- [ ] Choose which instruments the overview shows. *Choisir les instruments de la vue d'ensemble.*
- [ ] A library of ready-made checks to switch on (certificates, DNS, AD replication, backups). *Une bibliothèque de contrôles prêts à activer (certificats, DNS, réplication AD, sauvegardes).*
- [ ] More languages. *D'autres langues.*

## Later · Plus tard

- Several vCenter, ESXi or Proxmox endpoints. *Plusieurs vCenter, ESXi ou Proxmox.*
- Single sign-on (OIDC) in front of the cockpit. *Authentification unique (OIDC).*
- Ready-made Docker images, so nothing is built on the host. *Images Docker prêtes à l'emploi.*

## What NetCockpit will stay · Ce qui ne changera pas

- **Read-only**: it observes, it never changes your network or your hypervisors. *Lecture seule : il observe, il ne modifie rien.*
- **One screen first**: new features must not make the overview harder to read. *Un écran d'abord : une nouveauté ne doit pas rendre la vue d'ensemble moins lisible.*
- **Self-hosted, no account, no telemetry.** *Auto-hébergé, sans compte, sans télémétrie.*
