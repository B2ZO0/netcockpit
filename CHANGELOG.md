# Changelog

## Unreleased

Not published yet: these changes will make the next release.

- Fix: the setup assistant silently removed apostrophes from passwords, and a password ending with a backslash made `.env` unreadable for Docker. It now keeps `$`, `#`, spaces and quotes as typed and asks again for a password it cannot store unchanged.
- Security (Linux agent): the LLDP export that runs as root now writes into a folder owned by root and never follows a file left there by another account. Re-run the agent installer on Linux servers to apply it.
- Security: errors from the AI provider no longer show its address, which can contain a user name and password. Zabbix is no longer configured when `ZABBIX_ADMIN_PASSWORD` is empty, instead of staying on its default password. Only real IP addresses become probe targets, and one malformed address sent by an agent no longer breaks the inventory. The SNMP community no longer appears in debug logs.
- Security: numbers read from the Proxmox API are checked to be numbers, and the interface escapes them like every other value. In the inventory CSV, names that would start like a spreadsheet formula are kept as plain text.
- Fix: `./setup.sh --update` could stop right after downloading a release with many changes, without restarting anything (so the new version was not applied). It now always goes on.
- Fix: when `.env` was missing next to an existing installation, setup.sh did not always recognise the installation and could start with new passwords; it now stops and explains, as intended.
- Security: signing out ends the session for good, and changing `COCKPIT_PASSWORD` ends every open session (everyone signs in again once after this update). `/metrics` and the Grafana node graph answer without a session only to the local Docker networks, never through a reverse proxy; a Prometheus installed on the host itself goes in `COCKPIT_METRICS_NETWORKS`. The web server frees silent connections after 30 s, refuses malformed request sizes and reads nothing from a client that is not signed in.
- Fix: the network graph of the Grafana overview dashboard stayed empty when the cockpit asked for a password.
- Fix: Grafana stopped once on its first start (the Zabbix plugin was configured before it was installed) and only worked after Docker restarted it.
- **Proxmox VE (experimental)**: nodes, QEMU VMs, LXC containers and storages in the map, the Virtualization screen, the metrics and the alerts, like VMware. Read-only API token (PVEAuditor role). VMware and Proxmox can be connected at the same time. VMs without a guest agent get their address from the network scan, matched by MAC address. Checked against a simulated Proxmox API in automated tests; not yet tested on a real Proxmox server — feedback welcome.
- **One-command update**: `./setup.sh --update` downloads the latest published version and updates everything. Settings (`.env`, `config/cockpit.yml`) and history are never touched; settings are backed up first. If a project file was edited by hand, it stops without changing anything and says what to do.
- **Updates follow releases**: `./setup.sh --update` moves to the latest published version (newest `vX.Y.Z` tag), never to work in progress on `main`, and never goes backwards: a folder already newer than the latest version (installs that followed `main`, newer than 1.1.0) or holding its own commits stays where it is and says why, then moves on with the next published version. Testers can keep following `main` with `./setup.sh --update --edge`. Release candidates (`v1.2.0-rc1`) and tags deleted on GitHub are ignored.
- **Hypervisors are detected**: the assistant looks for VMware and Proxmox on the local network, says what it found, and asks one question (VMware, Proxmox, both, none) with the answer pre-filled. In the cockpit, a hypervisor seen by the scan but not connected is flagged on the overview and the setup screen. With no hypervisor at all, the Virtualization entry disappears from the menu.
- The "VMware" screen is now "Virtualization" and its wording no longer assumes ESXi.
- Roadmap published in ROADMAP.md.
- **Security**: strict Content-Security-Policy (scripts only from the cockpit itself, no inline script, no framing by other sites) and a Permissions-Policy; requests started by another website are refused, including on trusted networks without login (CSRF).
- Fix: behind a reverse proxy that rewrites the `Host` header (nginx's default), signing in and every other action was refused as a cross-site request. The browser's own same-origin signal is now accepted; requests from other websites are still refused.
- Fix: the Alerts screen now follows the building filter like the overview; before, it listed every building's alerts and the alert counter in the menu changed from one screen to the other.
- On phones, the active building filter shows as a chip at the top; one tap goes back to all buildings. The agents card on the overview follows the building filter.
- Online demo: "Analyse with AI" works on every device and errors say why; agent install commands use a placeholder address instead of the address serving the demo; the new-device alert and the new devices panel agree.
- Lighter requirements, from real measurements: the whole stack including Zabbix uses about 1.2 GB of RAM in production on a company network (~230 devices across 2 buildings, 20 VMs, 8 servers with the agent). Minimum is now 2 vCPU and 4 GB RAM (was 4 vCPU and 8 GB); 8 GB stays recommended for several hundred devices. Zabbix is now listed at ~0.5 GB instead of 1.5 GB.
- **Ready-made Docker image**: the cockpit is published on GitHub Container Registry (`ghcr.io/b2zo0/netcockpit`, amd64 and arm64). `./setup.sh` and `./setup.sh --update` download the image built from exactly the code they have (tag = hash of the `cockpit/` folder) instead of compiling it on the host. If it cannot be downloaded (no access to ghcr.io, image still being built, other CPU), or if `cockpit/` was edited by hand, it is built locally as before. New `.env` setting `COCKPIT_IMAGE`: `auto` (default), `build`, or your own registry mirror. Released versions are also tagged `X.Y.Z`, `X.Y` and `latest`.
- Security: the cockpit now asks for a password. `./setup.sh` generates it (`COCKPIT_PASSWORD` in `.env`) and shows it at the end; signed session cookie, slowed-down brute force, sign-out button. Wall screens: `COCKPIT_TRUSTED_NETWORKS`. Personal lab: `COCKPIT_AUTH=off`.
- Security: Prometheus can no longer be stopped or reloaded over HTTP, and Loki refuses log deletion requests; logs are only removed by the retention period. The README now says which ports agents need open.
- Security: the cockpit image built or downloaded on the host is now named `localhost/netcockpit/cockpit:local`, a name that can only refer to an image of this machine: `docker compose pull` and automatic image updaters can never replace it with an image from a public registry. The previous local name is removed by `./setup.sh`.
- Security: Prometheus, Alertmanager, Loki, Grafana, Alloy and the exporters now use versions tested with this release instead of `latest`; `./setup.sh --update` downloads them, so these components receive their security fixes with each NetCockpit release, and PostgreSQL 16 and Zabbix 7.0 get their latest patch. CI checks that every pinned image exists.
- Security: the notification settings (Telegram, Discord, e-mail) and the SNMP community generated from `.env` now live in `secrets/`, a folder only your user can open; Alertmanager and the SNMP exporter read them through read-only file mounts. The copies left by earlier versions in `alertmanager/` and `snmp/` are removed by `./setup.sh`.
- Security: from the network, ports 9090 and 3100 now only accept what agents send (metrics for Prometheus, logs for Loki), through a small nginx gateway (`agent-gateway`). Reading metrics and logs, or administering Prometheus and Loki, is only possible on the monitoring host (`127.0.0.1:9091` and `127.0.0.1:3101`) or through Grafana. Agents keep the same address and ports: nothing to change on servers. CI starts the stack and checks it.
- Security: the cockpit container no longer has the NET_ADMIN capability, so it cannot change the host's interfaces, routes or firewall; discovery only needs raw packets (NET_RAW). CI runs ping/ARP, SYN, UDP and ICMP traceroute scans with exactly these capabilities.
- Security: Alertmanager only listens on the host, so nobody on the network can silence alerts. Security headers on every page; request bodies are size-limited.
- Security: `/metrics` (full inventory) now needs a session, except from the monitoring host and its local Docker networks, so Prometheus keeps working. External Prometheus: `COCKPIT_METRICS_NETWORKS`.
- Security: session cookie marked `Secure` behind an HTTPS reverse proxy; `VCENTER_VERIFY_TLS=true` verifies the vCenter certificate.
- Unit tests for the login and access rules, run in CI.
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
