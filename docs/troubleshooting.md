# Troubleshooting

| Symptom | What to check |
|---|---|
| Empty map | First scan takes 2–5 min: `docker compose logs -f netmap`. |
| Devices shown by IP | No reverse DNS zone: set `names.dns_servers`; Windows PCs get NetBIOS names anyway; use `overrides:` for the rest. |
| No switch on the map | You need one of: vCenter/ESXi (CDP/LLDP seen by hosts), lldpd on physical Linux servers, or SNMP read access. |
| vCenter red in the sidebar | `docker compose logs netmap \| grep -i vcenter`: URL must end with `/sdk`, account needs Read-only on the root, propagated. |
| Zabbix red | It needs 2–3 min to create its database on first start, then `docker compose logs zabbix-server zabbix-web`. |
| Alert rules missing in Prometheus | `docker compose restart prometheus`, then `docker compose logs prometheus \| grep -i err`. |
| Windows server shown down although it runs | It blocks ping: re-run the agent installer (enables Echo Request), or add it to `watch:` with `port: 3389`. |
| Grafana node graph empty | The host firewall blocks Docker → port 8088: `ufw allow from 172.16.0.0/12 to any port 8088`. |
| AI button missing | `AI_PROVIDER` is empty in `.env`. |
| Port already in use | `ss -tulnp \| grep -E ':(8088\|3000\|8081\|9090\|9093\|3100\|514)\b'`, then change the left-hand port in `docker-compose.yml` (or `ZABBIX_WEB_PORT`). |
