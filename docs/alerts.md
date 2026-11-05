# Alerts

Rules live in `prometheus/rules/*.yml` (metrics) and `loki/rules/fake/*.yml` (logs). Everything goes through Alertmanager, configured from `.env` by `scripts/render_config.py`.

| Group | Alerts |
|---|---|
| Network | Critical equipment down · device down (was up within 24 h) · Internet down · high latency · packet loss · website down · certificate expiring · DNS down · new device on the network |
| Servers | Agent silent · disk > 90 % · disk full within 24 h · CPU > 90 % for 15 min · RAM > 95 % · failed systemd unit · reboot · switch port changed (LLDP) |
| VMware | Host disconnected · vCenter alarm (red = critical) · VM just powered off · vCenter unreachable · datastore > 85 % / > 95 % · host CPU / RAM saturated |
| Zabbix | Every Zabbix problem (except pings already covered by Prometheus) · Zabbix unreachable |
| SNMP | Port saturated (> 85 % for 15 min) · port errors · SNMP device silent |
| Logs | SSH brute force · disk I/O errors · OOM killer · critical journald messages · critical Windows events |
| Self-monitoring | A monitoring component is down · discovery stuck · Watchdog (always firing, proves the pipeline works) |

## Anti-spam

- Grouping by alert, device and instance; repeat every 4 h; "info" alerts once a day (or never, with `NOTIFY_INFO=false`).
- Inhibitions: a critical firewall/router down mutes "device down", latency and silent-agent alerts behind it; an ESXi disconnected mutes its VMs; critical mutes the same warning.

## Silences

Alertmanager only listens on the monitoring host (nobody on the network can silence alerts). Open its UI through an SSH tunnel, then *New silence*:

```bash
ssh -L 9093:127.0.0.1:9093 user@monitoring-host   # then open http://localhost:9093
```
