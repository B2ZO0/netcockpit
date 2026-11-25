<#
  Installe l'agent Grafana Alloy (métriques + journaux d'événements) sur Windows Server 2016+ / Windows 10+.
  L'agent POUSSE ses données vers la supervision : aucun port à ouvrir sur le serveur.

  PowerShell en administrateur :
    Set-ExecutionPolicy -Scope Process Bypass
    .\install.ps1 -Server 10.10.0.50 -Token <JETON_DES_AGENTS>

  Options :
    -Token XXX        jeton des agents (AGENT_TOKEN du .env de la supervision, affiché à la fin de ./setup.sh)
    -Name SRV-XYZ     nom affiché (défaut : nom de l'ordinateur)
    -NoPing           ne pas autoriser le ping entrant (sinon la règle pare-feu "Echo Request" est activée)
#>
param(
  [Parameter(Mandatory = $true)][string]$Server,
  [string]$Name = $env:COMPUTERNAME,
  [string]$Token = $env:NETCOCKPIT_AGENT_TOKEN,
  [switch]$NoPing
)
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Error "Lance PowerShell en tant qu'administrateur."; exit 1 }
if (-not $Name) { $Name = $env:COMPUTERNAME }   # -ArgumentList <supervision>,'',<jeton> avec Invoke-Command
if ($Token -and $Token -notmatch '^[A-Za-z0-9_-]{16,128}$') {
  Write-Error "Jeton invalide. Remplace <AGENT_TOKEN> par le jeton des agents : sur la machine de supervision, grep AGENT_TOKEN= .env dans le dossier de NetCockpit (il est aussi affiché à la fin de ./setup.sh)."
  exit 1
}
if (-not $Token) { Write-Warning "Sans -Token : l'agent n'est accepté que si la supervision n'exige pas encore le jeton (AGENT_AUTH=optional)." }

# IP utilisée pour joindre la supervision
# -Server accepte une IP ou un nom DNS (pratique pour changer d'adresse sans réinstaller)
$target = $Server
if ($Server -notmatch '^\d+\.\d+\.\d+\.\d+$') {
  try { $target = ([System.Net.Dns]::GetHostAddresses($Server) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -First 1).IPAddressToString } catch { }
}
$ip = (Find-NetRoute -RemoteIPAddress $target -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress } | Select-Object -First 1).IPAddress
Write-Host "==> $Name ($ip) -> supervision $Server"

# 1. Téléchargement et installation silencieuse d'Alloy (dernière version GitHub)
$tmp = Join-Path $env:TEMP "alloy-install"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$zip = Join-Path $tmp "alloy.zip"
Write-Host "==> Téléchargement d'Alloy..."
Invoke-WebRequest -UseBasicParsing -OutFile $zip `
  -Uri "https://github.com/grafana/alloy/releases/latest/download/alloy-installer-windows-amd64.exe.zip"
Expand-Archive -Path $zip -DestinationPath $tmp -Force
$exe = Get-ChildItem $tmp -Filter "alloy-installer-windows-amd64.exe" -Recurse | Select-Object -First 1
Write-Host "==> Installation..."
$p = Start-Process -FilePath $exe.FullName -ArgumentList "/S", "/DISABLEREPORTING=yes" -Wait -PassThru
if ($p.ExitCode -ne 0) { Write-Error "Installation d'Alloy échouée (code $($p.ExitCode))"; exit 1 }

# 2. Jeton d'agent : dans un fichier lisible par SYSTEM (le service Alloy) et les administrateurs seulement
$tokenDir = Join-Path $env:ProgramData "NetCockpit"
$tokenFile = Join-Path $tokenDir "agent-token"
$auth = ""
if ($Token) {
  New-Item -ItemType Directory -Force -Path $tokenDir | Out-Null
  & icacls.exe $tokenDir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null
  [IO.File]::WriteAllText($tokenFile, $Token, (New-Object Text.UTF8Encoding $false))
  # le service Alloy tourne en principe sous SYSTEM ; s'il a son propre compte, ce compte peut lire le jeton
  $runAs = (Get-CimInstance Win32_Service -Filter "Name='Alloy'" -ErrorAction SilentlyContinue).StartName
  if ($runAs -and $runAs -notmatch '^(LocalSystem|NT AUTHORITY\\SYSTEM)$') { & icacls.exe $tokenFile /grant "${runAs}:R" | Out-Null }
  $auth = 'bearer_token_file = "' + ($tokenFile -replace '\\', '/') + '"'
} else {
  Remove-Item $tokenFile -Force -ErrorAction SilentlyContinue
}

# 3. Configuration
$cfgDir = Join-Path $env:ProgramFiles "GrafanaLabs\Alloy"
$cfg = @'
// Généré par install.ps1 : supervision __SERVER__

// "memory" n'est plus activé par défaut dans les versions récentes d'Alloy : sans lui, pas de RAM
prometheus.exporter.windows "default" {
  enabled_collectors = ["cpu", "logical_disk", "memory", "net", "os", "service", "system"]
}

discovery.relabel "win" {
  targets = prometheus.exporter.windows.default.targets
  rule {
    target_label = "instance"
    replacement  = "__NAME__"
  }
  rule {
    target_label = "job"
    replacement  = "windows"
  }
}

prometheus.scrape "win" {
  targets         = discovery.relabel.win.output
  forward_to      = [prometheus.remote_write.main.receiver]
  scrape_interval = "30s"
}

prometheus.remote_write "main" {
  endpoint {
    url = "http://__SERVER__:9090/api/v1/write"
    __AUTH__
  }
  external_labels = {
    os = "windows",
    ip = "__IP__",
  }
}

loki.source.windowsevent "system" {
  eventlog_name          = "System"
  use_incoming_timestamp = true
  forward_to             = [loki.process.win.receiver]
  labels                 = { job = "windows", host = "__NAME__", channel = "System" }
}

loki.source.windowsevent "application" {
  eventlog_name          = "Application"
  use_incoming_timestamp = true
  forward_to             = [loki.process.win.receiver]
  labels                 = { job = "windows", host = "__NAME__", channel = "Application" }
}

// Niveau numérique Windows -> libellé (indépendant de la langue du système)
loki.process "win" {
  forward_to = [loki.write.main.receiver]
  stage.json {
    expressions = { lvl = "level", source = "source", event_id = "event_id" }
  }
  stage.template {
    source   = "lvl"
    template = "{{ if eq .Value \"1\" }}critical{{ else if eq .Value \"2\" }}error{{ else if eq .Value \"3\" }}warning{{ else }}info{{ end }}"
  }
  stage.labels {
    values = { level = "lvl", source = "source" }
  }
  stage.structured_metadata {
    values = { event_id = "event_id" }
  }
}

loki.write "main" {
  endpoint {
    url = "http://__SERVER__:3100/loki/api/v1/push"
    __AUTH__
  }
}
'@
$cfg = $cfg.Replace('__SERVER__', $Server).Replace('__NAME__', $Name).Replace('__IP__', "$ip").Replace('__AUTH__', $auth)
# UTF-8 sans BOM (Alloy refuse le BOM de PowerShell 5)
[IO.File]::WriteAllText((Join-Path $cfgDir "config.alloy"), $cfg, (New-Object Text.UTF8Encoding $false))

# 4. Ping entrant autorisé (sinon le serveur apparaît "injoignable" sur la carte)
if (-not $NoPing) {
  Get-NetFirewallRule -Name "FPS-ICMP4-ERQ-In*" -ErrorAction SilentlyContinue | Enable-NetFirewallRule
}

# 5. Redémarrage du service
Restart-Service -Name "Alloy"
Start-Sleep -Seconds 4

# La supervision accepte-t-elle cet agent ? (un envoi vide, refusé avec 401 si le jeton manque ou ne correspond pas)
$headers = @{}
if ($Token) { $headers["Authorization"] = "Bearer $Token" }
try {
  Invoke-WebRequest -UseBasicParsing -Method Post -Uri "http://${Server}:3100/loki/api/v1/push" -Headers $headers `
    -ContentType "application/json" -Body '{"streams":[]}' -TimeoutSec 10 | Out-Null
} catch {
  $code = $null
  if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
  if ($code -eq 401) {
    Write-Error "La supervision refuse cet agent : jeton absent ou faux. Relance ce script avec -Token <AGENT_TOKEN> (sur la machine de supervision : grep AGENT_TOKEN= .env dans le dossier de NetCockpit)."
    exit 1
  } elseif (-not $code) {
    Write-Warning "${Server}:3100 injoignable depuis ce serveur : vérifie le pare-feu (sortie vers les ports 9090 et 3100)."
  }
}
$svc = Get-Service -Name "Alloy"
if ($svc.Status -eq "Running") {
  Write-Host "==> Alloy actif. '$Name' apparaîtra dans Grafana et sur la carte d'ici 1 minute." -ForegroundColor Green
} else {
  Write-Warning "Le service Alloy ne tourne pas. Journal : Observateur d'événements > Application (source Alloy)."
}
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
