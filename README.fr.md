<div align="center">

<img src="docs/images/logo.svg" width="96" alt="Logo NetCockpit">

# NetCockpit

**Un cockpit de supervision en direct pour les équipes IT de PME, même quand les switchs et firewalls sont gérés par un prestataire.**

Topologie découverte automatiquement · VMware · switchs port par port · alertes · logs · diagnostic IA en option
Basé sur Prometheus, Loki, Alertmanager, Grafana et Zabbix. Installation en une commande.

[English](README.md) · [Démo en 1 minute](#-démo-en-1-minute) · [Installation](#-installation) · [Documentation](docs/)

<img src="docs/images/overview.png" alt="Vue d'ensemble NetCockpit" width="100%">

</div>

---

## Pourquoi NetCockpit ?

Beaucoup d'entreprises ont externalisé leur réseau. Le prestataire gère les switchs, le firewall et les routeurs, et l'équipe informatique interne n'a **aucun accès administrateur** dessus. Les outils classiques n'affichent alors qu'une liste d'adresses IP.

NetCockpit **croise toutes les sources auxquelles tu as accès** : scan réseau, DNS Active Directory, NetBIOS, traceroute, vCenter ou ESXi, agents sur les serveurs, et SNMP dès qu'il est disponible. Il en tire une **vraie carte hiérarchique de l'infrastructure, mise à jour en direct**, avec les problèmes affichés dessus.

- 🗺️ **Une vraie topologie, automatique** : Internet → opérateur → firewall → sites → réseaux → switchs → serveurs et ESXi → VM. Rien à dessiner à la main.
- 🔌 **Qui est branché sur quel port ?** NetCockpit lit le CDP/LLDP **via les ESXi** et les serveurs Linux, sans toucher aux switchs. Avec un accès SNMP en lecture seule, tu obtiens la carte complète, port par port.
- 🏷️ **De vrais noms, pas des IP** : DNS AD, NetBIOS (noms et MAC des PC Windows, même sur un site distant), noms vCenter et noms des agents.
- 🚨 **Pas de fausses alertes** : un portable parti le soir apparaît « absent », en gris. Le rouge est réservé aux serveurs, VM, hyperviseurs, firewalls, switchs et DC qui ne répondent plus.
- 🖥️ **Vue VMware** : chaque hôte, ses VM (CPU, RAM, IP, OS), les datastores et les alarmes. Fonctionne avec un **vCenter ou un ESXi seul**.
- 🔔 **Une seule chaîne d'alertes** : les alertes Prometheus, Loki et Zabbix passent toutes par Alertmanager, puis vers Telegram, Discord ou email. Elles sont regroupées et filtrées : si le firewall tombe, tu ne reçois pas 80 messages « injoignable ».
- 🤖 **Diagnostic IA (option)** : un bouton « Expliquer ce problème » sur chaque équipement et un résumé de la situation, avec Claude ou un **modèle local** (Ollama : rien ne sort du réseau).
- 📦 **Une seule commande** : `./setup.sh` génère les mots de passe et les configurations, puis démarre tout. Tu peux le relancer à volonté sans perdre tes réglages.

## 📸 Captures

| Topologie en direct | Problèmes seulement (écran mural) |
|---|---|
| ![Topologie](docs/images/topology.png) | ![Problèmes](docs/images/topology-problems.png) |
| **VMware** | **Switchs, port par port** |
| ![VMware](docs/images/vmware.png) | ![Switchs](docs/images/switches.png) |
| **Inventaire (export CSV)** | **Fiche équipement + analyse IA** |
| ![Inventaire](docs/images/inventory.png) | ![Fiche](docs/images/device-ai.png) |

> Toutes les captures viennent de la démo intégrée : tous les noms et toutes les adresses IP sont fictifs.

## ⚡ Démo en 1 minute

La démo simule un réseau complet sur deux sites : firewall, 2 ESXi, 11 VM, switchs, bornes Wi-Fi, imprimantes, téléphones IP, PC, et quelques pannes. **Rien n'est scanné, aucun identifiant n'est nécessaire.**

```bash
git clone https://github.com/<toi>/netcockpit.git && cd netcockpit
docker compose -f docker-compose.demo.yml up --build
```

Ouvre ensuite **http://localhost:8088**.

## 🚀 Installation

Il faut une VM Debian 12 ou Ubuntu 24.04 avec **4 vCPU, 8 Go de RAM** (6 Go sans Zabbix), 60 Go de disque, et Docker.

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/<toi>/netcockpit.git && cd netcockpit
./setup.sh                    # crée .env (mots de passe aléatoires) et démarre tout
nano config/netmap.yml        # sites, réseaux, équipements critiques, sites web
nano .env                     # vCenter/ESXi, notifications, IA
./setup.sh                    # applique
```

| Service | Adresse |
|---|---|
| **Cockpit** | `http://<IP>:8088` |
| Grafana | `http://<IP>:3000` (admin / `GRAFANA_ADMIN_PASSWORD`) |
| Zabbix | `http://<IP>:8081` (Admin / `ZABBIX_ADMIN_PASSWORD`) |

Ensuite, installe les agents. Le cockpit sert lui-même les scripts :

```powershell
# Windows (PowerShell administrateur, sur le serveur)
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr http://<IP>:8088/agents/windows/install.ps1 -OutFile $env:TEMP\install.ps1 -UseBasicParsing
& $env:TEMP\install.ps1 -Server <IP>
```
```bash
# Linux
curl -fsSL http://<IP>:8088/agents/linux/install.sh | sudo bash -s <IP>
```

Guides détaillés (en anglais) : [installation](docs/installation.md), [configuration](docs/configuration.md), [agents](docs/agents.md), [topologie](docs/topology.md), [alertes](docs/alerts.md), [dépannage](docs/troubleshooting.md).

## 📨 Ce qu'il est utile de demander au prestataire réseau

1. Un accès **SNMP v2c en lecture seule** sur les switchs, le firewall et les routeurs, depuis l'IP de la supervision. Il donne la carte complète port par port, le trafic et les erreurs.
2. L'**envoi des logs syslog** vers la supervision, sur le port 514.
3. **LLDP ou CDP activé** sur les ports des serveurs.
4. Son **accord pour le scan interne** (ping et quelques ports toutes les 30 minutes).

## 🙏 Remerciements

NetCockpit assemble d'excellents projets open source, présentés dans le [README anglais](README.md#-credits) : Prometheus, Grafana, Loki, Alloy, Zabbix, Cytoscape.js, Nmap, pyVmomi, lldpd, net-snmp, et [xoriin/NetMap](https://github.com/xoriin/NetMap) en module optionnel.

## 📄 Licence

[MIT](LICENSE). Si NetCockpit te fait gagner du temps, une ⭐ aide d'autres admins à le trouver.
