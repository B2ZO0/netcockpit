# Agents

NetCockpit uses [Grafana Alloy](https://grafana.com/oss/alloy/) as a single agent for metrics **and** logs. Agents **push** to the monitoring VM (TCP 9090 and 3100): no inbound port has to be opened on the servers.

The cockpit serves the install scripts at `http://<host>:8088/agents/...`.

## Agent token

Agents send their metrics and logs with a token created by `./setup.sh` (`AGENT_TOKEN` in `.env`, also shown at the end of `./setup.sh`). The monitoring host refuses anything sent without it (HTTP 401), so another machine on the network cannot push fake metrics or fill the disk with logs. On each server, the token is stored in a file only the agent can read (`/etc/alloy/netcockpit-token`, or `C:\ProgramData\NetCockpit\agent-token` for SYSTEM and administrators), never in the Alloy configuration. The installer sends an empty test push at the end and stops with a clear message if the token is refused.

`AGENT_AUTH` in `.env` chooses what happens without the token:

| `AGENT_AUTH` | Agent without a token | Wrong token |
|---|---|---|
| `required` (new installs) | refused | refused |
| `optional` (set when updating from a version without the token) | accepted | refused |

After an update, reinstall each agent with the token, then set `AGENT_AUTH=required` in `.env` and run `./setup.sh`. The cockpit's "Setup" screen shows a step until it is done.

To change the token (for example after a server was decommissioned): delete the `AGENT_TOKEN=` line from `.env`, run `./setup.sh` (it creates a new one), then reinstall every agent.

## Windows (Server 2016+, Windows 10+)

```powershell
# Admin PowerShell on the server
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr http://<host>:8088/agents/windows/install.ps1 -OutFile $env:TEMP\install.ps1 -UseBasicParsing
& $env:TEMP\install.ps1 -Server <host> -Token '<AGENT_TOKEN>'

# Many servers at once, from an admin workstation (arguments: address, name — empty for the computer name —, token):
Invoke-Command -ComputerName DC01,FILESRV01,APPSRV01 -FilePath .\agents\windows\install.ps1 -ArgumentList <host>,'','<AGENT_TOKEN>'
```

What it does:
- downloads the latest Alloy installer from GitHub and installs it silently;
- stores the agent token in `C:\ProgramData\NetCockpit\agent-token`, readable by SYSTEM and administrators only;
- writes a config with the Windows exporter (CPU, memory, disks, network, services) and the **System** and **Application** event logs (level mapped from the numeric value, so it works with any Windows language);
- enables the "File and Printer Sharing (Echo Request)" firewall rule, so the cockpit can ping the server (`-NoPing` to skip).

## Linux (Debian, Ubuntu, RHEL, Rocky, Alma)

```bash
curl -fsSL http://<host>:8088/agents/linux/install.sh | sudo bash -s <host> --token '<AGENT_TOKEN>'
```

A display name can follow the address: `sudo bash -s <host> srv-app01 --token …`.

What it does:
- installs Alloy from the Grafana repository, plus **lldpd** (with CDP listening enabled);
- stores the agent token in `/etc/alloy/netcockpit-token` (owner root, readable by the `alloy` group only);
- exports node metrics (including systemd units) and journald logs;
- runs a 5-minute timer converting `lldpcli` neighbours into the `lldp_neighbor_info` metric. That is how the cockpit knows **which switch and port** each physical Linux server is plugged into.

### Removing the Linux agent

As root on the server (Debian/Ubuntu; on RHEL-like systems use `dnf remove alloy lldpd` and `/etc/yum.repos.d/grafana.repo`):

```bash
systemctl disable --now alloy alloy-lldp.timer lldpd
apt-get purge -y alloy lldpd
rm -f /etc/systemd/system/alloy-lldp.service /etc/systemd/system/alloy-lldp.timer \
      /etc/apt/sources.list.d/grafana.list /etc/apt/keyrings/grafana.gpg /etc/default/lldpd
rm -rf /etc/alloy /usr/local/lib/alloy-lldp /var/lib/alloy-lldp
systemctl daemon-reload && apt-get update -qq
```

Keep `lldpd` (leave it out of the first two lines) if it was already installed before the agent. The server disappears from "Servers with agent" within a few minutes; its history stays in Prometheus and Loki until retention removes it.

## Labels

Each agent sends `instance` (host name), `os` and `ip`. The cockpit uses `ip` to merge agent data with scan, DNS and vCenter data.
