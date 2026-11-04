# Cas pratiques

Chaque infrastructure est différente. Trouve la situation qui ressemble à la tienne : pour chacune, ce qu'il faut répondre à l'assistant (`./setup.sh --configure`), ce que tu verras, et les limites à connaître.

> 🇬🇧 English version: [scenarios.md](scenarios.md) · Première installation : [guide pas à pas](demarrage.md)

Dans le cockpit, l'écran **Mise en route** (le drapeau dans la barre de gauche) te dit à tout moment ce qui est en place et ce qu'il reste à faire, avec les commandes prêtes à copier.

**Sommaire**

| Ta situation | Recette |
|---|---|
| Une seule adresse, un seul réseau | [Petite structure](#petite-structure-un-seul-réseau) |
| Plusieurs bâtiments ou VLAN sur le même site | [Plusieurs bâtiments, un seul site](#plusieurs-bâtiments-ou-vlan-sur-un-même-site) |
| Plusieurs sites reliés par VPN, fibre ou MPLS | [Multi-sites](#plusieurs-sites-reliés-vpn-fibre-mpls) |
| Switchs et firewall gérés par un prestataire | [Réseau externalisé](#réseau-géré-par-un-prestataire) |
| Pas de domaine Active Directory | [Sans AD](#sans-active-directory) |
| Hyper-V, Proxmox ou serveurs physiques | [Sans VMware](#sans-vmware-hyper-v-proxmox-serveurs-physiques) |
| Plusieurs ESXi sans vCenter | [Plusieurs ESXi](#plusieurs-esxi-sans-vcenter) |
| Switchs Ubiquiti UniFi, Cisco, autres | [Switchs](#voir-les-switchs-port-par-port) |
| Changement de plan d'adressage | [Ré-adressage](#changement-dadressage) |
| Petite VM, homelab | [Peu de RAM](#petite-machine-ou-homelab) |
| Où placer la machine de supervision, quels flux ouvrir | [Placement et flux](#où-placer-la-machine-de-supervision) |
| Écran mural, accès pour l'équipe | [Écran mural et accès](#écran-mural-et-accès-de-léquipe) |

---

## Petite structure, un seul réseau

*Un seul réseau (par exemple 192.168.1.0/24), une box ou un firewall, quelques serveurs.*

- **Dans l'assistant** : Entrée à presque tout. Le réseau, la passerelle et les DNS détectés sont les bons. Nomme ton site (« Siège », « Bureau »…), puis Entrée à « Ajouter un autre … ? ».
- **Ensuite** : installe l'agent sur tes serveurs (écran *Mise en route*, étape 4) et branche Telegram (étape 5).
- **Tu verras** : la passerelle, tes serveurs, les PC, imprimantes et bornes Wi-Fi, avec leurs noms.

## Plusieurs bâtiments ou VLAN sur un même site

*Bâtiment A en 192.168.1.0/24, bâtiment B en 192.168.40.0/24, ou un VLAN par usage (serveurs, postes, téléphonie, Wi-Fi).*

- **Dans l'assistant** : choisis **1) Bâtiment**. Pour le bâtiment où est la machine, garde le réseau détecté et ajoute les autres VLAN de ce bâtiment, séparés par des virgules (`192.168.1.0/24, 192.168.2.0/24`). Puis « Ajouter un autre bâtiment ? » : son nom et ses réseaux.
- **Comment trouver les réseaux** : `ipconfig` sur un PC de chaque bâtiment (adresse IPv4 et masque), ou la liste des étendues dans la console DHCP.
- **Vérifie** depuis la machine de supervision : `ping <une adresse de l'autre bâtiment>`. Si ça ne répond pas, un firewall entre les VLAN bloque le ping : demande l'ouverture depuis l'IP de la supervision.
- **Tu verras** : un filtre par bâtiment en haut du cockpit, une branche par bâtiment dans la topologie, et un regroupement par bâtiment dans Zabbix.

## Plusieurs sites reliés (VPN, fibre, MPLS)

*Un siège et des agences, reliés par un VPN site à site ou un réseau opérateur.*

- **Une seule machine de supervision suffit**, au siège, si elle peut joindre les réseaux des agences.
- **Dans l'assistant** : choisis **2) Site** (ou **3) Agence**). Déclare chaque site avec ses réseaux.
- **À ouvrir dans le VPN ou le firewall**, depuis l'IP de la supervision vers les agences : ICMP (ping) et les ports TCP de détection (liste dans `config/cockpit.yml`, section `scan.ports`). NetBIOS (UDP 137) donne les noms des PC Windows à travers les routeurs.
- **Agents dans les agences** : ils envoient vers la supervision en TCP 9090 et 3100. Ces ports doivent passer dans le VPN.
- **Limite** : si un site n'a aucune route vers la supervision, il n'est pas visible. Une seconde installation dans ce site reste possible, mais les deux cockpits sont alors indépendants.

## Réseau géré par un prestataire

*C'est le cas de départ de NetCockpit : pas d'accès aux switchs, au firewall, ni aux routeurs.*

- **Tout fonctionne sans accès** : scan, noms, VMware, agents, alertes.
- **Les switchs** sont reconnus via les ESXi (CDP/LLDP des cartes réseau) et via les serveurs Linux équipés de l'agent.
- **À demander au prestataire** pour aller plus loin :
  1. une communauté **SNMP v2c en lecture seule** depuis l'IP de la supervision : carte complète port par port, trafic, erreurs ;
  2. l'envoi des **logs syslog** vers la supervision (port 514) ;
  3. **LLDP ou CDP actif** sur les ports des serveurs ;
  4. son **accord pour le scan** (ping et quelques ports toutes les 30 minutes).
- Une fois la communauté SNMP obtenue, relance l'assistant et donne-la avec les IP des switchs et du firewall.

## Sans Active Directory

*Groupe de travail, petite entreprise sans domaine, homelab.*

- **Dans l'assistant** : laisse les DNS internes **vides** (Entrée sur une valeur vide, ou efface la valeur proposée).
- **Les noms** viennent alors de NetBIOS (PC Windows), de VMware (VM) et des agents (serveurs).
- **Pour les autres** (imprimantes, caméras, NAS), donne-leur un nom à la main dans `config/cockpit.yml` :
  ```yaml
  overrides:
    192.168.1.30: { name: NAS-Sauvegarde, role: nas }
    192.168.1.50: { name: Imprimante-Accueil, role: printer }
  ```
  puis `docker compose restart cockpit`.

## Sans VMware (Hyper-V, Proxmox, serveurs physiques)

- **Dans l'assistant** : Entrée à la question VMware.
- **Hyper-V** : installe l'agent Windows sur l'hôte Hyper-V et dans les VM importantes. Tu as CPU, RAM, disques et journaux de chacun.
- **Proxmox** : installe l'agent Linux sur l'hôte Proxmox (c'est une Debian) et dans les VM importantes.
- **Serveurs physiques** : l'agent suffit. Sur Linux, il lit aussi le LLDP et sait sur quel switch et quel port le serveur est branché.
- **Limite** : sans VMware, la topologie ne dessine pas le lien « VM → hôte ». L'inventaire Hyper-V et Proxmox est prévu dans la feuille de route.

## Plusieurs ESXi sans vCenter

- **Aujourd'hui, NetCockpit se connecte à une seule adresse VMware.** Avec un vCenter, tous les hôtes remontent. Avec plusieurs ESXi autonomes, donne l'ESXi le plus important à l'assistant.
- **Les autres ESXi** restent visibles comme équipements (ping, port 443), et **Zabbix** peut les superviser nativement : dans Zabbix, crée un hôte par ESXi avec le modèle « VMware » et les macros `{$VMWARE.URL}` (`https://<ESXi>/sdk`), `{$VMWARE.USERNAME}` et `{$VMWARE.PASSWORD}`.
- Le support de plusieurs ESXi est prévu dans la feuille de route.

## Voir les switchs port par port

| Matériel | Comment activer le SNMP en lecture seule |
|---|---|
| Ubiquiti UniFi | *UniFi Network → Settings → CyberSecure → Traffic Logging* : active SNMP v1/v2c, change la communauté `public`. Les USW Flex et Ultra ne gèrent pas le SNMP. |
| Cisco (IOS) | `snmp-server community <communauté> RO <ACL>`, avec une ACL limitée à l'IP de la supervision. |
| HPE Aruba, Netgear, D-Link, TP-Link… | Menu *SNMP* de l'interface web : crée une communauté v2c en lecture seule. |
| Géré par un prestataire | Demande-lui une communauté v2c en lecture seule depuis l'IP de la supervision. |

Puis relance l'assistant : donne la communauté, puis les IP des switchs et du firewall. Sans SNMP, les switchs restent visibles via les ESXi (CDP/LLDP) et l'agent Linux (lldpd).

## Changement d'adressage

*Exemple : passage de 192.168.x.x à 10.x.x.x.*

1. **Avant la bascule**, relance l'assistant et ajoute les nouveaux réseaux **à côté** des anciens, pour chaque bâtiment : `192.168.1.0/24, 10.1.0.0/24`.
2. **Pendant la bascule**, les équipements qui changent d'adresse apparaissent sous leur nouvelle IP. Leur ancienne adresse passe en gris (*absent*), sans fausse alerte.
3. **Après la bascule**, relance l'assistant et retire les anciens réseaux. Mets aussi à jour les DNS et la passerelle s'ils ont changé.
4. **Si la machine de supervision change elle-même d'adresse** : relance `./setup.sh` après le changement, puis réinstalle l'agent sur les serveurs avec la nouvelle adresse (ou modifie l'adresse dans leur configuration Alloy).

## Petite machine ou homelab

- **Moins de 8 Go de RAM** : réponds **n** à la question Zabbix. Tout le reste fonctionne avec 4 à 6 Go.
- **Homelab** : la démo (`docker compose -f docker-compose.demo.yml up`) permet d'essayer sans rien toucher. Pour ton vrai réseau, procède comme pour une [petite structure](#petite-structure-un-seul-réseau).
- **Réduire l'historique** : `RETENTION=15d` dans `.env`, puis `./setup.sh`.

## Où placer la machine de supervision

- **Le meilleur endroit** : le VLAN des serveurs, avec une adresse IP fixe.
- **Flux sortants** depuis la supervision : ICMP et les ports de détection vers tous les réseaux surveillés, TCP 443 vers vCenter ou ESXi, UDP 161 vers les switchs (si SNMP), UDP 137 vers les PC (NetBIOS).
- **Flux entrants** vers la supervision : TCP 9090 et 3100 depuis les serveurs équipés de l'agent, UDP/TCP 514 depuis les firewalls et switchs (syslog), TCP 8088, 3000 et 8081 depuis les postes des administrateurs.
- **Ne publie jamais** ces ports sur Internet : plusieurs n'ont pas d'authentification.

## Écran mural et accès de l'équipe

- **Écran mural** : ouvre la **Topologie**, coche **Problèmes seulement**, puis passe le navigateur en plein écran (F11). Le thème nuit se lit bien de loin.
- **Accès de l'équipe** : le cockpit n'a pas encore de comptes utilisateurs. Limite l'accès au port 8088 aux postes des administrateurs (règle sur le firewall ou ACL du VLAN). Grafana et Zabbix ont leurs propres comptes.
- **Chacun choisit sa langue et son thème** en bas de la barre de gauche : le choix est mémorisé par navigateur.

---

Une situation qui n'est pas dans cette liste ? Ouvre une [issue](https://github.com/B2ZO0/netcockpit/issues) ou une [discussion](https://github.com/B2ZO0/netcockpit/discussions) : la réponse rejoindra cette page.
