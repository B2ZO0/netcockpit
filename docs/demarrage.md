# Guide pas à pas

De la VM vide au cockpit qui affiche tes bâtiments, ton VMware et tes alertes sur Telegram. Compte une heure, la plupart du temps passé à attendre le premier scan.

> 🇬🇧 English version: [getting-started.md](getting-started.md)

**Sommaire**

1. [Préparer la machine de supervision](#1-préparer-la-machine-de-supervision)
2. [Installer NetCockpit](#2-installer-netcockpit)
3. [Répondre à l'assistant](#3-répondre-à-lassistant)
4. [Découvrir le cockpit](#4-découvrir-le-cockpit)
5. [Ajouter un bâtiment ou changer d'adressage](#5-ajouter-un-bâtiment-ou-changer-dadressage)
6. [Connecter VMware (vCenter ou ESXi seul)](#6-connecter-vmware-vcenter-ou-esxi-seul)
7. [Zabbix](#7-zabbix)
8. [Installer les agents sur les serveurs](#8-installer-les-agents-sur-les-serveurs)
9. [Recevoir les alertes sur Telegram](#9-recevoir-les-alertes-sur-telegram)
10. [Voir les ports des switchs (SNMP, Ubiquiti UniFi)](#10-voir-les-ports-des-switchs-snmp-ubiquiti-unifi)
11. [Mettre à jour sans rien perdre](#11-mettre-à-jour-sans-rien-perdre)
12. [Dépannage](#12-dépannage)

---

## 1. Préparer la machine de supervision

Une VM Debian 12 ou Ubuntu 24.04 suffit : **4 vCPU, 8 Go de RAM, 60 Go de disque** (6 Go de RAM sans Zabbix).

Elle doit pouvoir joindre **tous les réseaux à surveiller** (ping et quelques ports), l'**API de ton vCenter ou de ton ESXi** (port 443), et être joignable par les agents (ports 9090 et 3100). Donne-lui une IP fixe : c'est l'adresse que tu taperas dans ton navigateur.

```bash
apt update && apt install -y curl git unzip python3
curl -fsSL https://get.docker.com | sh
```

> Préviens ton prestataire réseau avant le premier scan : un ping et quelques ports toutes les 30 minutes, pour qu'il ne le prenne pas pour une attaque.

## 2. Installer NetCockpit

```bash
cd /root                     # ou le dossier de ton choix : garde toujours le même
git clone https://github.com/B2ZO0/netcockpit.git
cd netcockpit
./setup.sh
```

Pas de git ? Télécharge le zip de la dernière version depuis la page *Releases*, décompresse-le, puis lance `./setup.sh` depuis le dossier obtenu.

`setup.sh` vérifie Docker, génère des mots de passe aléatoires dans `.env`, puis lance l'**assistant**.

## 3. Répondre à l'assistant

L'assistant détecte tout seul le réseau de la machine, sa passerelle et ses DNS, puis te pose quelques questions. La valeur proposée est entre crochets : **Entrée pour l'accepter**.

```text
  Assistant de configuration NetCockpit
  Détecté sur cette machine : réseau 192.168.10.0/24 · passerelle 192.168.10.254 · DNS 192.168.10.11, 192.168.10.12

Comment appelles-tu tes emplacements ?  1) Bâtiment  2) Site  3) Agence  [1] :
Nom du bâtiment où se trouve cette machine [Bâtiment 1] : Bâtiment A
Réseaux de « Bâtiment A » (séparés par des virgules) [192.168.10.0/24] :
Ajouter un autre bâtiment ? Son nom (Entrée pour terminer) : Bâtiment B
Réseaux de « Bâtiment B » (ex. 10.20.0.0/24) : 192.168.20.0/24
Ajouter un autre bâtiment ? Son nom (Entrée pour terminer) :
Serveurs DNS internes (contrôleurs de domaine) [192.168.10.11, 192.168.10.12] :
Adresse de la passerelle / du firewall [192.168.10.254] :
VMware : adresse du vCenter ou de l'ESXi (IP ou nom, Entrée pour passer) : 192.168.10.5
Utilisateur en lecture seule : supervision
Mot de passe de cet utilisateur (rien ne s'affiche) :
Switchs et firewall : communauté SNMP en lecture seule (Entrée pour passer) :
Notifications Telegram : jeton du bot (Entrée pour passer) :
Installer Zabbix (VMware natif, découverte SNMP, ~1,5 Go de RAM) ? o/n [o] :
```

Ce que chaque réponse change :

| Question | À quoi ça sert |
|---|---|
| Bâtiment, site ou agence | Le mot affiché partout dans l'interface (« Tous les bâtiments »). |
| Bâtiments et réseaux | Ce qui est scanné, et comment l'inventaire et la topologie sont regroupés. Un bâtiment peut avoir plusieurs réseaux. Un réseau s'écrit `192.168.20.0/24` (ou `192.168.20.0` : le `/24` est ajouté). |
| DNS internes | Les noms des machines (Active Directory) au lieu des adresses IP. Laisse vide si tu n'en as pas : les contrôleurs de domaine sont détectés tout seuls. |
| Passerelle / firewall | Surveillée en critique : si elle tombe, tout le reste est grisé au lieu de déclencher 80 alertes. |
| VMware, SNMP, Telegram | Optionnels : Entrée pour passer, tu pourras les ajouter plus tard. |

Ensuite `setup.sh` démarre tout et affiche les adresses :

```text
  Cockpit    http://192.168.10.50:8088
  Grafana    http://192.168.10.50:3000   admin / GRAFANA_ADMIN_PASSWORD (dans .env)
  Zabbix     http://192.168.10.50:8081   Admin / ZABBIX_ADMIN_PASSWORD (dans .env)
```

Pour retrouver un mot de passe : `grep PASSWORD .env`.

## 4. Découvrir le cockpit

Ouvre `http://<IP de la VM>:8088`. Le premier scan prend **2 à 5 minutes**.

| Écran | Ce que tu y trouves |
|---|---|
| Vue d'ensemble | Une phrase qui dit si tout va bien, la route vers Internet, une mini-topologie, les problèmes en cours, tes bâtiments. |
| Topologie | L'arbre complet : Internet → firewall → bâtiments → réseaux → switchs → serveurs → VM. « Problèmes seulement » pour un écran mural. |
| VMware | Chaque ESXi, ses VM, les datastores, les alarmes. |
| Switchs | Qui est branché sur quel port (via les ESXi, les serveurs Linux ou le SNMP). |
| Inventaire | Tous les équipements, filtrables, exportables en CSV. |
| Alertes | Tout ce qui ne va pas, quelle que soit la source (Prometheus, logs, Zabbix). |

En bas de la barre de gauche : la **pastille des sources** (vert = connecté, rouge = erreur, avec la raison), le bouton pour relancer un scan, le thème jour/nuit et la langue.

Si un encadré orange indique « Réseaux vus mais pas encore déclarés », le cockpit a croisé des équipements dans un réseau qui n'appartient à aucun bâtiment. Ajoute ce réseau avec l'étape suivante.

## 5. Ajouter un bâtiment ou changer d'adressage

Tout se fait en relançant l'assistant :

```bash
cd /root/netcockpit          # ton dossier d'installation
./setup.sh --configure
```

Il repart de ta configuration actuelle : Entrée garde chaque valeur, et tu ne modifies que ce qui change.

**Passage à un nouvel adressage** (par exemple de `192.168.x` à `10.x`) : relance l'assistant et remplace les réseaux de chaque bâtiment. Pendant la transition, mets l'ancien et le nouveau, séparés par une virgule (`192.168.10.0/24, 10.1.0.0/24`), puis retire l'ancien une fois la bascule terminée. Les équipements qui ne répondent plus à leur ancienne adresse passent en gris (*absents*), pas en rouge.

Pour les réglages fins (noms forcés, équipements critiques, sites web à surveiller), édite `config/cockpit.yml` à la main, puis `docker compose restart cockpit`. Toutes les options sont décrites dans [configuration.md](configuration.md).

## 6. Connecter VMware (vCenter ou ESXi seul)

NetCockpit n'a besoin que d'un compte en **lecture seule**.

**Avec un vCenter** : *Administration → Single Sign On → Users and Groups*, crée `supervision@vsphere.local`. Ensuite, sur la racine de l'inventaire : *Permissions → Add*, rôle **Read-only**, coche *Propagate to children*.

**Avec un ESXi seul** (sans vCenter), dans l'interface web de l'ESXi :

1. *Gérer → Sécurité et utilisateurs → Utilisateurs → Ajouter un utilisateur* : `supervision` et un mot de passe.
2. *Hôte* (clic droit) *→ Autorisations → Ajouter un utilisateur* : `supervision`, rôle **Lecture seule**, propager à tous les enfants.

Puis `./setup.sh --configure` et réponds à la question VMware avec l'IP de l'ESXi ou du vCenter. Dans le cockpit, la pastille **vCenter** passe au vert et l'écran VMware se remplit en une minute.

Bonus : le cockpit lit le **CDP/LLDP des cartes réseau des ESXi**, et sait ainsi sur quel switch et quel port chaque hôte est branché, sans accès aux switchs.

## 7. Zabbix

Zabbix est installé et **configuré automatiquement** : modèle VMware natif, découverte SNMP, et tous les équipements importants trouvés par le cockpit y sont déclarés, rangés par bâtiment et par type (toutes les 30 minutes).

- Adresse : `http://<IP de la VM>:8081`, utilisateur `Admin`, mot de passe `ZABBIX_ADMIN_PASSWORD` dans `.env`.
- Au **premier démarrage**, Zabbix crée sa base : compte **2 à 3 minutes** avant qu'il réponde. Pendant ce temps, la pastille Zabbix est rouge, c'est normal.
- Si elle reste rouge, ouvre la pastille des sources : la raison s'affiche sous « Zabbix ». Puis voir [Dépannage](#12-dépannage).
- Pas besoin de Zabbix ? Réponds `n` dans l'assistant : tu économises 1,5 Go de RAM, et le reste fonctionne pareil.

## 8. Installer les agents sur les serveurs

Les agents remontent CPU, RAM, disques, services et journaux. Le cockpit sert lui-même les scripts d'installation.

**Windows** (PowerShell **administrateur**, sur le serveur) :

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr http://<IP de la VM>:8088/agents/windows/install.ps1 -OutFile $env:TEMP\install.ps1 -UseBasicParsing
& $env:TEMP\install.ps1 -Server <IP de la VM>
```

**Linux** :

```bash
curl -fsSL http://<IP de la VM>:8088/agents/linux/install.sh | sudo bash -s <IP de la VM>
```

Le serveur apparaît dans « Serveurs avec agent » en une minute. Détails : [agents.md](agents.md).

## 9. Recevoir les alertes sur Telegram

1. Dans Telegram, écris à **@BotFather** : `/newbot`, choisis un nom. Il te donne un **jeton** (`123456789:AA…`).
2. Écris un premier message à ton nouveau bot (ou ajoute-le au groupe de l'équipe).
3. Ouvre `https://api.telegram.org/bot<JETON>/getUpdates` dans un navigateur : le nombre après `"chat":{"id":` est ton **chat id** (négatif pour un groupe).
4. `./setup.sh --configure`, réponds aux questions Telegram.

Discord ou email : renseigne `DISCORD_WEBHOOK_URL` ou `ALERT_EMAIL_TO` et `SMTP_*` dans `.env`, puis `./setup.sh`.

## 10. Voir les ports des switchs (SNMP, Ubiquiti UniFi)

Sans rien faire, le cockpit reconnaît les switchs vus par les ESXi (CDP/LLDP) et par les serveurs Linux équipés de l'agent. Pour la **carte complète port par port** (qui est branché où, trafic, erreurs), il faut un accès **SNMP en lecture seule** :

- **Switchs gérés par un prestataire** : demande-lui une communauté SNMP v2c en lecture seule, autorisée depuis l'IP de la VM.
- **Ubiquiti UniFi** : dans *UniFi Network → Settings → CyberSecure → Traffic Logging*, active **SNMP** en version v1/v2c et choisis une communauté (change `public`). Les switchs **USW Flex et Ultra ne gèrent pas le SNMP** ([documentation Ubiquiti](https://help.ui.com/hc/en-us/articles/33502980942615-SNMP-Monitoring-in-UniFi-Network)). Les switchs UniFi annoncent aussi leurs voisins en LLDP, ce que le cockpit lit via les ESXi.
- **Cisco** : `snmp-server community <communauté> RO` (avec une ACL limitée à l'IP de la VM, c'est mieux).

Puis `./setup.sh --configure` : réponds à la question SNMP avec la communauté, puis les IP des switchs et du firewall. L'écran **Switchs** affiche chaque port en moins de 5 minutes.

## 11. Mettre à jour sans rien perdre

```bash
cd /root/netcockpit          # TOUJOURS le dossier où NetCockpit est déjà installé
git pull                     # ou décompresse la nouvelle version DANS ce même dossier
./setup.sh
```

- Ton `.env` (mots de passe, VMware, Telegram) et ton `config/cockpit.yml` (bâtiments, réseaux) **ne sont jamais écrasés** : ils ne font pas partie du projet téléchargé.
- `setup.sh` les copie dans `backups/<date>/` avant chaque lancement (les 10 dernières copies sont gardées).
- L'historique, la base Zabbix et Grafana sont dans des volumes Docker : ils restent.
- Si tu décompresses par erreur la mise à jour dans **un autre dossier**, `setup.sh` le détecte et s'arrête sans rien modifier, en te donnant le bon dossier.

## 12. Dépannage

| Ce que tu vois | Cause probable et solution |
|---|---|
| Le cockpit affiche « Site A », « 10.10.0.x », DC01, DC02 | C'est la configuration d'exemple de la démo. Relance `./setup.sh --configure`. |
| Un réseau n'apparaît pas | Il n'est déclaré dans aucun bâtiment : `./setup.sh --configure`. Vérifie aussi que la VM le joint : `ping <une IP de ce réseau>`. |
| Pastille Zabbix rouge juste après l'installation | Zabbix crée sa base : attends 3 minutes. |
| Pastille Zabbix rouge qui ne passe jamais au vert | Le mot de passe de `.env` ne correspond plus à la base, souvent parce que `.env` a été recréé (installation dans un autre dossier). Remets l'ancien `.env` depuis `backups/<date>/` ou l'ancien dossier, puis `./setup.sh`. Sinon : `docker compose logs --tail 50 zabbix-server zabbix-web`. |
| Pastille vCenter rouge | Le motif s'affiche sous la pastille. Le plus souvent : mauvais mot de passe, ou compte sans le rôle Lecture seule propagé. `docker compose logs cockpit \| grep -i vcenter`. |
| VMware « non configuré » alors qu'il l'était | `grep ^VCENTER .env` : si c'est vide, remets l'ancien `.env` depuis `backups/<date>/`, ou refais `./setup.sh --configure`. |
| Des machines affichées par leur IP | Pas de zone DNS inverse : renseigne les DNS internes dans l'assistant. Les PC Windows sont nommés via NetBIOS de toute façon. |
| Un serveur Windows « en panne » alors qu'il tourne | Il bloque le ping : l'installeur de l'agent ouvre la règle « Echo Request ». |
| `setup.sh` s'arrête avec « NetCockpit tourne déjà depuis le dossier … » | Tu l'as lancé depuis un autre dossier : va dans celui indiqué et relance-le là. |

Toujours bloqué ? Ouvre une [issue](https://github.com/B2ZO0/netcockpit/issues) avec la sortie de `docker compose ps` et de `docker compose logs --tail 50 cockpit` (sans mots de passe ni IP publiques).
