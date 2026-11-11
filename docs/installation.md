# Installation

## Requirements

| | Minimum | Recommended (20–100 servers, 30 days of history) |
|---|---|---|
| OS | Debian 12 / Ubuntu 22.04+ | Debian 12 / Ubuntu 24.04 |
| CPU / RAM | 2 vCPU / 4 GB (`ENABLE_ZABBIX=false`) | 4 vCPU / 8 GB |
| Disk | 30 GB | 60–100 GB |
| Software | Docker Engine + compose plugin, Python 3 | |

The monitoring VM must reach every network you want to see (ICMP + a few TCP ports), the vCenter/ESXi API (TCP 443), and be reachable by the agents (TCP 9090 and 3100).

## Steps

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/B2ZO0/netcockpit.git
cd netcockpit
./setup.sh
```

On the first run `setup.sh`:

1. creates `.env` from `.env.example`, with random passwords and your IP as `PUBLIC_HOST`;
2. starts the **setup assistant**, which detects the local network, gateway and DNS servers and asks for your buildings, other networks, VMware, SNMP, Telegram and Zabbix (walkthrough: [getting-started.md](getting-started.md#3-answer-the-setup-assistant));
3. renders `alertmanager/alertmanager.yml` and `snmp/auth.yml` from `.env`, and the Grafana dashboards;
4. downloads the ready-made cockpit image matching your version from GitHub Container Registry (nothing to build), or builds it on the host when it is not available, then starts the stack (`docker compose up -d`). See [Ready-made image](#ready-made-cockpit-image).

Re-run the assistant at any time with `./setup.sh --configure` (add a building, change addressing, connect VMware). `./setup.sh --yes` skips the questions and uses the detected values.

Advanced settings live in two files, both yours and never overwritten:

- `config/cockpit.yml`: buildings, networks, critical equipment, websites, SNMP devices ([reference](configuration.md#configcockpityml));
- `.env`: vCenter/ESXi, notifications, AI, Zabbix on/off ([reference](configuration.md#env)).

`setup.sh` is idempotent. When a new version adds settings to `.env.example`, it appends them to your `.env` without touching existing values.

## First minutes

| When | What happens |
|---|---|
| 0–1 min | Containers start; the cockpit writes initial probe targets |
| 1–5 min | First scan (ping sweep, ports, NetBIOS, DNS, traceroute) |
| 2–3 min | Zabbix creates its database, then the cockpit configures it (password, VMware host, SNMP discovery, Grafana user) |
| + 30 min | Devices discovered by the cockpit are declared in Zabbix (then every 30 min) |

```bash
docker compose ps
docker compose logs -f cockpit
```

## Upgrading (your settings are never lost)

```bash
git pull            # or unzip the new release over the folder
./setup.sh
```

What is yours stays yours:

| Your data | Where it lives | On upgrade |
|---|---|---|
| Passwords, vCenter, notifications, AI | `.env` | Never overwritten. New settings are appended with their default value. |
| Sites, networks, equipment, websites, SNMP | `config/cockpit.yml` | Not versioned, never overwritten. The repository only ships `config/cockpit.example.yml`. |
| History (metrics, logs, scans), Zabbix database, Grafana | Docker volumes | Kept. `docker compose down` keeps them too; only `down -v` deletes them. |

Before doing anything, `./setup.sh` copies `.env` and `config/*.yml` to `backups/<date>/` (the last 10 are kept). To roll back a setting: `cp backups/<date>/.env .`.

## Ready-made cockpit image

The cockpit is published as a Docker image on GitHub Container Registry, `ghcr.io/b2zo0/netcockpit`, for amd64 and arm64. Installing and upgrading therefore download it instead of compiling it on the host: faster, and nothing to install besides Docker.

- **Always the right version.** The image tag is the git hash of the `cockpit/` folder (`tree-<hash>`): `./setup.sh` downloads exactly the image built from the code it has. `python3 scripts/cockpit_image.py` prints which one.
- **Never stuck.** If the image cannot be downloaded (no access to `ghcr.io`, a version published a few minutes ago and still being built, a CPU other than amd64/arm64), `./setup.sh` says so and builds it on the host, as before.
- **Your own changes are respected.** If you edited files in `cockpit/`, or installed from an archive without git, the image is built on the host from your files.
- **`COCKPIT_IMAGE` in `.env`**: `auto` (default), `build` to always build on the host, or the name of your own registry mirror (`registry.example.local/netcockpit`, the tag is still chosen automatically).
- Released versions are also tagged `X.Y.Z`, `X.Y` and `latest`, and `main` follows the main branch.

> Dashboards are provisioned from `grafana/dashboards/` and regenerated on every run: to customise one, use **Save as** in Grafana to keep your own copy.
> Upgrading from 1.0 (when the cockpit was called `netmap`)? `./setup.sh` renames `config/netmap.yml` to `config/cockpit.yml` and moves the history volume for you. If `git pull` refuses because you edited `config/netmap.yml`, run `mv config/netmap.yml config/cockpit.yml` first.

## Uninstalling

```bash
docker compose down        # stop, keep data
docker compose down -v     # stop and delete all data (volumes)
```

## Ports

| Port | Service |
|---|---|
| 8088 | Cockpit (host network) |
| 3000 | Grafana |
| 8081 | Zabbix web (`ZABBIX_WEB_PORT`) |
| 9090 / 9093 | Prometheus (agents push metrics) / Alertmanager (host only) |
| 3100 | Loki (agents push logs) |
| 514 UDP+TCP | Syslog receiver |
| 10051 | Zabbix trapper (optional Zabbix agents) |
