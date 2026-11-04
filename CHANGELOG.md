# Changelog

## 1.0.0

First public release.

- Cockpit with overview, live hierarchical topology (groups, per-site filter, problems-only mode, PNG export), VMware, switches, inventory (CSV), alerts, services and device sheets.
- Discovery: nmap, NetBIOS, AD reverse DNS with domain controller auto-detection, traceroute, new-device detection, absent-vs-down status logic.
- VMware through vCenter or standalone ESXi: hosts, VMs, datastores, alarms, CDP/LLDP of host NICs.
- SNMP topology: LLDP/CDP neighbours, MAC and ARP tables, port status and traffic (snmp_exporter).
- Zabbix 7.0 auto-configuration: VMware template, SNMP discovery, Grafana user, cockpit devices synchronised by site and type.
- Prometheus, Alertmanager (Telegram / Discord / email), Loki with syslog receiver, Blackbox, Grafana (7 dashboards), Alloy agents for Linux and Windows served by the cockpit.
- Optional AI analysis (Claude API or any OpenAI-compatible endpoint).
- Built-in demo with a simulated two-site network.
