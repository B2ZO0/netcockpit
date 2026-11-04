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
git clone https://github.com/<you>/netcockpit.git
cd netcockpit
./setup.sh
```

On the first run `setup.sh`:

1. creates `.env` from `.env.example`, with random passwords and your IP as `PUBLIC_HOST`;
2. renders `alertmanager/alertmanager.yml` and `snmp/auth.yml` from `.env`;
3. generates the Grafana dashboards with the right links;
4. builds the cockpit image and starts the stack (`docker compose up -d`).

Then edit the two configuration files and run `./setup.sh` again:

- `config/netmap.yml`: sites, networks, critical equipment, websites, SNMP devices ([reference](configuration.md#confignetmapyml));
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
docker compose logs -f netmap
```

## Upgrading

```bash
git pull            # or unzip the new release over the folder (your .env is kept)
./setup.sh
```

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
| 9090 / 9093 | Prometheus / Alertmanager |
| 3100 | Loki (agents push logs) |
| 514 UDP+TCP | Syslog receiver |
| 10051 | Zabbix trapper (optional Zabbix agents) |
| 8090 | Optional IPAM module (`ENABLE_IPAM=true`) |
