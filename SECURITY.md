# Security policy

Please report vulnerabilities **privately**, through GitHub's "Report a vulnerability" (Security tab), not in a public issue. You will get an answer within a few days.

## Deployment recommendations

- **The cockpit asks for a password** (since this version). `./setup.sh` generates it, shows it at the end and keeps it in `.env` (`COCKPIT_PASSWORD`). Sessions are signed cookies (HttpOnly, SameSite) that end at sign-out and when the password changes, and repeated wrong passwords are slowed down (5 tries per 5 minutes per address).
  - Wall screen: list its address in `COCKPIT_TRUSTED_NETWORKS` instead of turning the login off.
  - `COCKPIT_AUTH=off` removes the login: only for a personal lab.
- **`/metrics` is no longer public**: it lists every device (IP, MAC, name, OS). Without a session it only answers the local Docker networks (where Prometheus and Grafana read it from), never a request relayed by a reverse proxy. An external Prometheus, or one installed directly on the host: add its address to `COCKPIT_METRICS_NETWORKS` (e.g. `127.0.0.1/32`).
- **Behind an HTTPS reverse proxy** that sends `X-Forwarded-Proto: https`, the session cookie is marked `Secure`.
- **vCenter certificate**: not verified by default (self-signed is common). Set `VCENTER_VERIFY_TLS=true` once vCenter has a certificate your system trusts.
- **Proxmox certificate**: not verified by default either. Set `PROXMOX_VERIFY_TLS=true` once Proxmox has a certificate your system trusts.
- **Alertmanager (9093) listens on the host only**: nobody on the network can silence alerts.
- **Ports 9090 and 3100 only accept what agents send**: a small gateway (nginx, service `agent-gateway`) forwards the metrics they push to Prometheus and the logs to Loki, and refuses everything else. Reading metrics or logs, and administering Prometheus or Loki, is only possible on the monitoring host itself (`127.0.0.1:9091` and `127.0.0.1:3101`; from your workstation: `ssh -L 9091:127.0.0.1:9091 <host>`, then http://localhost:9091) or through Grafana (Explore). Prometheus cannot be stopped or reloaded over HTTP either, and Loki refuses log deletion requests (logs are only removed by the retention period).
- **Agent pushes (9090, 3100), syslog (514) and the Zabbix trapper (10051) are not authenticated**: agents and devices push to them. Allow them **only from your server and device networks** with a firewall, for example:
  ```bash
  ufw allow from 192.0.2.0/24 to any port 9090,3100 proto tcp   # servers with an agent
  ufw allow from 192.0.2.0/24 to any port 514                    # syslog from network devices
  ufw allow from 198.51.100.0/24 to any port 8088,3000 proto tcp  # admin workstations
  ```
- **Agent scripts are downloaded from the cockpit over HTTP** on your internal network. If you do not trust that network path, download them over HTTPS from GitHub instead (`https://raw.githubusercontent.com/B2ZO0/netcockpit/main/agents/...`) and run them locally.
- **Remote access**: use a VPN, or a reverse proxy with HTTPS (Caddy, Nginx, Traefik) in front of the cockpit (8088) and Grafana (3000). Never publish them directly on the Internet.
- **Cockpit image**: `./setup.sh` downloads `ghcr.io/b2zo0/netcockpit`, built by GitHub Actions from this repository (workflow `image.yml`), tagged with the hash of the `cockpit/` folder it was built from. To build it yourself from the code you have instead: `COCKPIT_IMAGE=build` in `.env`.
- **The cockpit container** uses the host network (to see ARP, NetBIOS and traceroute) with only the raw-packet capability that nmap and traceroute need: it cannot change the host's interfaces, routes or firewall.
- Use **read-only** accounts: vCenter/ESXi "Read-only" role, SNMP read-only community.
- `.env` holds all secrets (mode 600) and `backups/` its previous versions (mode 700); the notification and SNMP settings generated from it live in `secrets/` (mode 700). Never commit them.
- The internal scan uses nmap (ping, a few TCP ports, NetBIOS). Get the network owner's approval and use `scan.exclude` for fragile devices.
- The optional AI feature sends the analysed device's data (name, IP, alerts, log excerpts) to the configured provider. Use a local model (`AI_PROVIDER=openai` + Ollama) if that is not acceptable.
