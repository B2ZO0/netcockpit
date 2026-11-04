# Security policy

Please report vulnerabilities **privately**, through GitHub's "Report a vulnerability" (Security tab), not in a public issue. You will get an answer within a few days.

## Deployment recommendations

- Deploy on an internal network only. Prometheus remote-write (9090), Loki push (3100) and syslog (514) are unauthenticated by design.
- For remote access, use a VPN or a reverse proxy with authentication and HTTPS in front of the cockpit (8088) and Grafana (3000).
- Use **read-only** accounts: vCenter/ESXi "Read-only" role, SNMP read-only community.
- `.env` holds all secrets (mode 600). Never commit it.
- The internal scan uses nmap (ping, a few TCP ports, NetBIOS). Get the network owner's approval and use `scan.exclude` for fragile devices.
- The optional AI feature sends the analysed device's data (name, IP, alerts, log excerpts) to the configured provider. Use a local model (`AI_PROVIDER=openai` + Ollama) if that is not acceptable.
