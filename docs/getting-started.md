# Getting started, step by step

From an empty VM to a cockpit showing your buildings, your VMware and your alerts on Telegram. Allow about an hour, most of it waiting for the first scan.

> 🇫🇷 Version française : [demarrage.md](demarrage.md) · Different situation (multi-site, no AD, no VMware, homelab…)? [Scenarios](scenarios.md)
>
> In the cockpit, the **Setup** screen (the flag in the left rail) tracks your progress and gives commands ready to copy.

**Contents**

1. [Prepare the monitoring host](#1-prepare-the-monitoring-host)
2. [Install NetCockpit](#2-install-netcockpit)
3. [Answer the setup assistant](#3-answer-the-setup-assistant)
4. [Tour of the cockpit](#4-tour-of-the-cockpit)
5. [Add a building or change addressing](#5-add-a-building-or-change-addressing)
6. [Connect VMware (vCenter or standalone ESXi)](#6-connect-vmware-vcenter-or-standalone-esxi)
7. [Zabbix](#7-zabbix)
8. [Install the server agents](#8-install-the-server-agents)
9. [Get alerts on Telegram](#9-get-alerts-on-telegram)
10. [See switch ports (SNMP, Ubiquiti UniFi)](#10-see-switch-ports-snmp-ubiquiti-unifi)
11. [Upgrade without losing anything](#11-upgrade-without-losing-anything)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prepare the monitoring host

A Debian 12 or Ubuntu 24.04 VM is enough: **4 vCPU, 8 GB RAM, 60 GB disk** (6 GB RAM without Zabbix).

It must reach **every network you want to monitor** (ping and a few ports), your **vCenter or ESXi API** (port 443), and be reachable by the agents (ports 9090 and 3100). Give it a fixed IP: it is the address you will open in your browser.

```bash
apt update && apt install -y curl git unzip python3
curl -fsSL https://get.docker.com | sh
```

> Tell your network provider before the first scan: a ping and a few ports every 30 minutes, so they do not mistake it for an attack.

## 2. Install NetCockpit

```bash
cd /opt                      # or any folder you like: always keep the same one
git clone https://github.com/B2ZO0/netcockpit.git
cd netcockpit
./setup.sh
```

No git? Download the zip of the latest version from the *Releases* page, extract it and run `./setup.sh` from that folder.

`setup.sh` checks Docker, generates random passwords in `.env`, then starts the **setup assistant**.

## 3. Answer the setup assistant

The assistant detects the host's network, gateway and DNS servers, then asks a few questions. The suggested value is in brackets: **press Enter to accept it**.

```text
  NetCockpit setup assistant
  Detected on this machine: network 192.168.10.0/24 · gateway 192.168.10.254 · DNS 192.168.10.11, 192.168.10.12

What do you call your locations?  1) Building  2) Site  3) Branch  [1]:
Name of the building where this machine is [Building 1]: HQ
Networks of "HQ" (comma-separated) [192.168.10.0/24]:
Add another building? Its name (Enter to finish): Warehouse
Networks of "Warehouse" (e.g. 10.20.0.0/24): 192.168.20.0/24
Add another building? Its name (Enter to finish):
Internal DNS servers (domain controllers), comma-separated [192.168.10.11, 192.168.10.12]:
Gateway / firewall address [192.168.10.254]:
VMware: vCenter or ESXi address (IP or name, Enter to skip): 192.168.10.5
Read-only user: monitoring
Password of that user (nothing is shown):
Switches and firewall: read-only SNMP community (Enter to skip):
Telegram notifications: bot token (Enter to skip):
Install Zabbix (native VMware, SNMP discovery, ~1.5 GB RAM)? y/n [y]:
```

What each answer changes:

| Question | What it is for |
|---|---|
| Building, site or branch | The word shown everywhere in the interface ("All buildings"). |
| Buildings and networks | What gets scanned, and how inventory and topology are grouped. A building can have several networks. Write a network as `192.168.20.0/24` (or `192.168.20.0`: `/24` is added). |
| Internal DNS | Machine names (Active Directory) instead of IP addresses. Leave empty if you have none: domain controllers are detected anyway. |
| Gateway / firewall | Monitored as critical: if it goes down, everything behind it turns grey instead of firing 80 alerts. |
| VMware, SNMP, Telegram | Optional: press Enter to skip, you can add them later. |

Then `setup.sh` starts everything and prints the addresses:

```text
  Cockpit    http://192.168.10.50:8088
  Grafana    http://192.168.10.50:3000   admin / GRAFANA_ADMIN_PASSWORD (in .env)
  Zabbix     http://192.168.10.50:8081   Admin / ZABBIX_ADMIN_PASSWORD (in .env)
```

To find a password again: `grep PASSWORD .env`.

## 4. Tour of the cockpit

Open `http://<host IP>:8088`. The first scan takes **2 to 5 minutes**.

| Screen | What you find there |
|---|---|
| Overview | One sentence saying whether all is well, the route to the Internet, a mini topology, open problems, your buildings. |
| Topology | The full tree: Internet → firewall → buildings → networks → switches → servers → VMs. "Problems only" for a wall screen. |
| VMware | Every ESXi host, its VMs, datastores, alarms. |
| Switches | What is plugged into which port (through ESXi hosts, Linux servers or SNMP). |
| Inventory | Every device, filterable, CSV export. |
| Alerts | Everything that is wrong, whatever the source (Prometheus, logs, Zabbix). |

At the bottom of the left rail: the **sources light** (green = connected, red = error, with the reason), the rescan button, the day/night theme and the language.

If an orange box says "Networks seen but not declared yet", the cockpit met devices in a network that belongs to no building. Add it with the next step.

## 5. Add a building or change addressing

Everything goes through the assistant again:

```bash
cd /opt/netcockpit           # your installation folder
./setup.sh --configure
```

It starts from your current configuration: Enter keeps each value, you only change what changes.

**Moving to a new addressing plan** (for example from `192.168.x` to `10.x`): re-run the assistant and replace each building's networks. During the transition, list both, comma-separated (`192.168.10.0/24, 10.1.0.0/24`), then remove the old one once the move is done. Devices that no longer answer on their old address turn grey (*absent*), not red.

For fine-tuning (forced names, critical equipment, websites to watch), edit `config/cockpit.yml` by hand, then `docker compose restart cockpit`. Every option is described in [configuration.md](configuration.md).

## 6. Connect VMware (vCenter or standalone ESXi)

NetCockpit only needs a **read-only** account.

**With vCenter**: *Administration → Single Sign On → Users and Groups*, create `monitoring@vsphere.local`. Then on the inventory root: *Permissions → Add*, role **Read-only**, tick *Propagate to children*.

**With a standalone ESXi** (no vCenter), in the ESXi Host Client:

1. *Manage → Security & users → Users → Add user*: `monitoring` and a password.
2. *Host* (right-click) *→ Permissions → Add user*: `monitoring`, role **Read-only**, propagate to all children.

Then `./setup.sh --configure` and answer the VMware question with the ESXi or vCenter IP. In the cockpit the **vCenter** light turns green and the VMware screen fills within a minute.

Bonus: the cockpit reads **CDP/LLDP from the ESXi host NICs**, so it knows which switch and port each host is plugged into, without any switch access.

## 7. Zabbix

Zabbix is installed and **configured automatically**: native VMware template, SNMP discovery, and every important device found by the cockpit is declared in it, grouped by building and type (every 30 minutes).

- Address: `http://<host IP>:8081`, user `Admin`, password `ZABBIX_ADMIN_PASSWORD` in `.env`.
- On **first start** Zabbix creates its database: allow **2 to 3 minutes** before it answers. Meanwhile the Zabbix light is red, which is expected.
- If it stays red, open the sources light: the reason is shown under "Zabbix". Then see [Troubleshooting](#12-troubleshooting).
- Don't need Zabbix? Answer `n` in the assistant: you save 1.5 GB of RAM and everything else works the same.

## 8. Install the server agents

Agents report CPU, RAM, disks, services and logs. The cockpit serves the install scripts itself.

**Windows** (PowerShell **as administrator**, on the server):

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr http://<host IP>:8088/agents/windows/install.ps1 -OutFile $env:TEMP\install.ps1 -UseBasicParsing
& $env:TEMP\install.ps1 -Server <host IP>
```

**Linux**:

```bash
curl -fsSL http://<host IP>:8088/agents/linux/install.sh | sudo bash -s <host IP>
```

The server shows up in "Servers with agent" within a minute. Details: [agents.md](agents.md).

## 9. Get alerts on Telegram

1. In Telegram, message **@BotFather**: `/newbot`, pick a name. It gives you a **token** (`123456789:AA…`).
2. Send a first message to your new bot (or add it to your team group).
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser: the number after `"chat":{"id":` is your **chat id** (negative for a group).
4. `./setup.sh --configure`, answer the Telegram questions.

Discord or email: set `DISCORD_WEBHOOK_URL` or `ALERT_EMAIL_TO` and `SMTP_*` in `.env`, then `./setup.sh`.

## 10. See switch ports (SNMP, Ubiquiti UniFi)

Out of the box, the cockpit recognises switches seen by ESXi hosts (CDP/LLDP) and by Linux servers running the agent. For the **full port-by-port map** (what is plugged where, traffic, errors), it needs **read-only SNMP**:

- **Switches managed by a provider**: ask for a read-only SNMP v2c community, allowed from the monitoring host's IP.
- **Ubiquiti UniFi**: in *UniFi Network → Settings → CyberSecure → Traffic Logging*, enable **SNMP** v1/v2c and set a community (change `public`). **USW Flex and Ultra switches do not support SNMP** ([Ubiquiti documentation](https://help.ui.com/hc/en-us/articles/33502980942615-SNMP-Monitoring-in-UniFi-Network)). UniFi switches also announce their neighbours over LLDP, which the cockpit reads through the ESXi hosts.
- **Cisco**: `snmp-server community <community> RO` (ideally with an ACL limited to the monitoring host's IP).

Then `./setup.sh --configure`: answer the SNMP question with the community, then the switch and firewall IPs. The **Switches** screen shows every port within 5 minutes.

## 11. Upgrade without losing anything

```bash
cd /opt/netcockpit           # ALWAYS the folder where NetCockpit is already installed
git pull                     # or extract the new version INTO that same folder
./setup.sh
```

- Your `.env` (passwords, VMware, Telegram) and your `config/cockpit.yml` (buildings, networks) are **never overwritten**: they are not part of the downloaded project.
- `setup.sh` copies them to `backups/<date>/` before every run (the last 10 copies are kept).
- History, the Zabbix database and Grafana live in Docker volumes: they stay.
- If you extract the upgrade into **another folder** by mistake, `setup.sh` detects it and stops without changing anything, and tells you the right folder.

## 12. Troubleshooting

| What you see | Likely cause and fix |
|---|---|
| The cockpit shows "Site A", "10.10.0.x", DC01, DC02 | That is the demo's example configuration. Run `./setup.sh --configure`. |
| A network does not appear | It is not declared in any building: `./setup.sh --configure`. Also check the host reaches it: `ping <an IP in that network>`. |
| Zabbix light red right after install | Zabbix is creating its database: wait 3 minutes. |
| Zabbix light red and never turns green | The password in `.env` no longer matches the database, usually because `.env` was recreated (install in another folder). Put the previous `.env` back from `backups/<date>/` or the old folder, then `./setup.sh`. Otherwise: `docker compose logs --tail 50 zabbix-server zabbix-web`. |
| vCenter light red | The reason is shown under the light. Most often: wrong password, or account without the propagated Read-only role. `docker compose logs cockpit \| grep -i vcenter`. |
| VMware "not configured" although it was | `grep ^VCENTER .env`: if empty, restore the previous `.env` from `backups/<date>/`, or run `./setup.sh --configure` again. |
| Machines shown by IP | No reverse DNS zone: enter your internal DNS servers in the assistant. Windows PCs are named through NetBIOS anyway. |
| A Windows server shown down although it runs | It blocks ping: the agent installer opens the "Echo Request" rule. |
| `setup.sh` stops with "NetCockpit is already running from …" | You ran it from another folder: go to the one shown and run it there. |

Still stuck? Open an [issue](https://github.com/B2ZO0/netcockpit/issues) with the output of `docker compose ps` and `docker compose logs --tail 50 cockpit` (without passwords or public IPs).
