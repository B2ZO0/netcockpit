# Agents

NetCockpit uses [Grafana Alloy](https://grafana.com/oss/alloy/) as a single agent for metrics **and** logs. Agents **push** to the monitoring VM (TCP 9090 and 3100): no inbound port has to be opened on the servers.

The cockpit serves the install scripts at `http://<host>:8088/agents/...`.

## Windows (Server 2016+, Windows 10+)

```powershell
# Admin PowerShell on the server
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr http://<host>:8088/agents/windows/install.ps1 -OutFile $env:TEMP\install.ps1 -UseBasicParsing
& $env:TEMP\install.ps1 -Server <host>

# Many servers at once, from an admin workstation:
Invoke-Command -ComputerName DC01,FILESRV01,APPSRV01 -FilePath .\agents\windows\install.ps1 -ArgumentList <host>
```

What it does:
- downloads the latest Alloy installer from GitHub and installs it silently;
- writes a config with the Windows exporter (CPU, memory, disks, network, services) and the **System** and **Application** event logs (level mapped from the numeric value, so it works with any Windows language);
- enables the "File and Printer Sharing (Echo Request)" firewall rule, so the cockpit can ping the server (`-NoPing` to skip).

## Linux (Debian, Ubuntu, RHEL, Rocky, Alma)

```bash
curl -fsSL http://<host>:8088/agents/linux/install.sh | sudo bash -s <host>
```

What it does:
- installs Alloy from the Grafana repository, plus **lldpd** (with CDP listening enabled);
- exports node metrics (including systemd units) and journald logs;
- runs a 5-minute timer converting `lldpcli` neighbours into the `lldp_neighbor_info` metric. That is how the cockpit knows **which switch and port** each physical Linux server is plugged into.

## Labels

Each agent sends `instance` (host name), `os` and `ip`. The cockpit uses `ip` to merge agent data with scan, DNS and vCenter data.
