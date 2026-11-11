# Configuration

## `config/cockpit.yml`

Written by the setup assistant (`./setup.sh --configure`), which covers the common settings. Edit it by hand for the rest, then `docker compose restart cockpit`. Full example: [`config/cockpit.example.yml`](../config/cockpit.example.yml).

| Key | Description |
|---|---|
| `site_word` | Word shown for locations: `{ one: Building, many: Buildings }`. Default: Site / Sites. |
| `sites[]` | `name` + `subnets` (CIDR). Each site (building) is a node in the topology and a filter in the UI. Empty = the local network detected by the cockpit. |
| `scan.enabled` | Turn the active scan off (passive sources only). |
| `scan.interval_minutes` | Default 30. |
| `scan.netbios` | NetBIOS name query (UDP 137). Gives Windows names **and MACs** across routers. |
| `scan.ports` | TCP ports used to fingerprint devices (keep it short). |
| `scan.exclude` | IPs never scanned (fragile or provider-owned devices). |
| `names.dns_servers` | Internal DNS used for reverse lookups. Empty = domain controllers auto-detected (ports 53+88+389). |
| `names.strip_domain` | Show `FILESRV01` instead of `filesrv01.example.local`. |
| `snmp.community` | Read-only community (or `SNMP_COMMUNITY` in `.env`). |
| `snmp.devices` | IPs of switches / firewalls / routers to poll. |
| `snmp.try_discovered` | Also poll every discovered network device. |
| `traceroute_targets` | Used to discover the path to the Internet. |
| `internet_targets` | "Internet is down" = all of these stop answering. |
| `watch[]` | Critical equipment: `name`, `ip`, `role`, optional `port` (TCP check). Critical alert when down. |
| `http_checks[]` | `name`, `url`: availability, response time, HTTP code, certificate expiry. |
| `dns_checks[]` | `name`, `ip`: the DNS server must answer. |
| `overrides` | Per-IP corrections: `{ name: ..., role: ... }`. |
| `subnet_names` | Friendly names for networks. |

Roles: `firewall`, `router`, `gateway`, `switch`, `network`, `wifi`, `esxi`, `hypervisor`, `vm`, `server`, `dc`, `nas`, `windows`, `linux`, `printer`, `phone`, `camera`, `mobile`, `device`, `other`.

## `.env`

After any change: `./setup.sh`.

| Variable | Description |
|---|---|
| `PUBLIC_HOST` | IP or DNS name of the monitoring VM (links in alerts and between tools). |
| `COCKPIT_IMAGE` | `auto` (default): download the ready-made cockpit image matching your code from `ghcr.io/b2zo0/netcockpit`, build it on the host if unavailable. `build`: always build on the host. A registry mirror (`registry.example.local/netcockpit`): same automatic tag, from your registry. With a tag (`…/netcockpit:1.2`): that exact image. |
| `RETENTION` | Prometheus retention (default `30d`). Loki retention is in `loki/loki.yml`. |
| `GRAFANA_ADMIN_PASSWORD` | Grafana `admin` password. |
| `ENABLE_ZABBIX` | `true` / `false`. Zabbix uses ~1.5 GB of RAM. |
| `ZABBIX_WEB_PORT`, `ZABBIX_*_PASSWORD` | Zabbix web port and generated passwords. |
| `VCENTER_URL` | `https://vcenter.example.local/sdk` **or** a standalone ESXi: `https://10.10.0.5/sdk`. |
| `VCENTER_USER`, `VCENTER_PASSWORD` | Read-only account (see below). Quote values containing `$`: `'pa$$word'`. |
| `SNMP_COMMUNITY` | Read-only SNMP v2c community. |
| `AI_PROVIDER` | `anthropic` (Anthropic API) or `openai` (any OpenAI-compatible API, e.g. Ollama). Empty = disabled. |
| `AI_API_KEY`, `AI_MODEL`, `AI_BASE_URL` | e.g. Ollama: `AI_PROVIDER=openai`, `AI_BASE_URL=http://10.10.0.60:11434/v1`, `AI_MODEL=llama3.1`. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Bot from @BotFather; chat id from `https://api.telegram.org/bot<TOKEN>/getUpdates`. |
| `DISCORD_WEBHOOK_URL` | Channel settings → Integrations → Webhooks. |
| `ALERT_EMAIL_TO`, `SMTP_*` | Email notifications. |
| `NOTIFY_INFO` | Send "info" alerts (new device, reboot…). |

### Read-only VMware account

- **vCenter**: Administration → Single Sign-On → Users → add `monitoring@vsphere.local`; on the vCenter root object: Permissions → Add → that user, role **Read-only**, **Propagate to children**.
- **Standalone ESXi** (Host Client): Manage → Security & users → Users → add `monitoring`; then right-click **Host** → Permissions → Add user → role **Read-only**, propagate.
