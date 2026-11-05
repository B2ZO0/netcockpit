# Changelog

## Unreleased

Not published yet: these changes will make the next release.

- Security: the cockpit now asks for a password. `./setup.sh` generates it (`COCKPIT_PASSWORD` in `.env`) and shows it at the end; signed session cookie, slowed-down brute force, sign-out button. Wall screens: `COCKPIT_TRUSTED_NETWORKS`. Personal lab: `COCKPIT_AUTH=off`.
- Security: Alertmanager only listens on the host, so nobody on the network can silence alerts. Security headers on every page; request bodies are size-limited.
- SECURITY.md: firewall examples for the ports agents push to (9090, 3100, 514) and HTTPS download of the agent scripts.
- Live demo in the browser, nothing to install: https://b2zo0.github.io/netcockpit/ (simulated network, rebuilt automatically on every change).
- Setup screen in the cockpit (flag in the rail): a checklist that ticks itself (buildings and networks, real names, VMware, server agents, notifications, Zabbix, SNMP, websites, AI), with what to do and commands ready to copy, including the install folder. The overview reminds how many essential steps are left.
- The setup assistant shows a tip under each question: where to find the value (ipconfig, DHCP console, provider, UniFi menu…).
- Scenario guides in English and French: one network, several buildings or VLANs, multi-site over VPN, provider-managed network, no Active Directory, no VMware (Hyper-V, Proxmox, physical), several ESXi hosts, switches (UniFi, Cisco, others), re-addressing, homelab, monitoring host placement and flows, wall screen.
- Fix: Windows servers showed no RAM. Recent Alloy versions no longer enable the memory collector by default; the agent installer now enables it, and until servers are updated the cockpit uses the memory reported by VMware.
- Setup assistant: `./setup.sh` detects the local network, gateway and DNS servers and asks for buildings, other networks, VMware, SNMP, Telegram and Zabbix, with defaults (Enter). Re-run it with `./setup.sh --configure`; `--yes` for unattended installs. No YAML to write, and the demo's example networks are never used as a real configuration.
- Choose the word shown for locations (Building, Site, Branch): "All buildings" across the interface.
- Without any declared network, the cockpit monitors the local network it detects; networks seen but not declared are shown on the overview with how to add them.
- The sources panel shows why vCenter or Zabbix is in error, with a link to the guide.
- Safer upgrades: `setup.sh` stops if NetCockpit already runs from another folder, or if `.env` is missing while an installation exists, and never deletes lines you added to `.env`.
- Step-by-step guides in English and French: install, buildings, VMware read-only account, Zabbix, agents, Telegram, switches (SNMP, Ubiquiti UniFi, Cisco), upgrade, troubleshooting.

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
