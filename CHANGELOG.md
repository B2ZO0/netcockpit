# Changelog

## 1.1.0

- New interface with its own identity: icon rail, plain-language status headline, Internet route drawn as a magenta line, live mini topology, single instrument strip, B612 typeface (made for aircraft cockpit screens).
- Night and day themes, following the system setting by default.
- English and French interface, following the browser language by default; AI answers follow the interface language.
- The cockpit service, folder, config file and metrics are renamed from `netmap` to `cockpit` (`config/cockpit.yml`, `cockpit_*` metrics). `./setup.sh` migrates an existing install automatically, history included.
- Safe upgrades: `config/cockpit.yml` is no longer versioned (the repository ships `config/cockpit.example.yml`, copied once by `setup.sh`), and `setup.sh` backs up `.env` and `config/*.yml` to `backups/` before every run.
- Removed the optional third-party IPAM module.

## 1.0.0

First public release.

- Cockpit with overview, live hierarchical topology (groups, per-site filter, problems-only mode, PNG export), VMware, switches, inventory (CSV), alerts, services and device sheets.
- Discovery: nmap, NetBIOS, AD reverse DNS with domain controller auto-detection, traceroute, new-device detection, absent-vs-down status logic.
- VMware through vCenter or standalone ESXi: hosts, VMs, datastores, alarms, CDP/LLDP of host NICs.
- SNMP topology: LLDP/CDP neighbours, MAC and ARP tables, port status and traffic (snmp_exporter).
- Zabbix 7.0 auto-configuration: VMware template, SNMP discovery, Grafana user, cockpit devices synchronised by site and type.
- Prometheus, Alertmanager (Telegram / Discord / email), Loki with syslog receiver, Blackbox, Grafana (7 dashboards), Alloy agents for Linux and Windows served by the cockpit.
- Optional AI analysis (Anthropic API or any OpenAI-compatible endpoint).
- Built-in demo with a simulated two-site network.
