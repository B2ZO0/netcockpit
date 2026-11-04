#!/usr/bin/env bash
# Installe l'agent Grafana Alloy (métriques + logs) et lldpd (voisins switch) sur un serveur Linux.
# Debian / Ubuntu / Rocky / Alma / RHEL. L'agent POUSSE ses données : rien à ouvrir sur le serveur.
#
#   sudo bash install.sh <IP_SUPERVISION> [nom]
set -euo pipefail

SERVER="${1:-}"
NAME="${2:-$(hostname -s)}"
[[ -z "$SERVER" ]] && { echo "Usage : sudo bash $0 <IP_DU_SERVEUR_DE_SUPERVISION> [nom]"; exit 1; }
[[ $EUID -ne 0 ]] && { echo "Lance ce script avec sudo."; exit 1; }

IP=$(ip -4 route get "$SERVER" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
. /etc/os-release
echo "==> ${PRETTY_NAME} · nom '${NAME}' · IP ${IP:-?} · supervision ${SERVER}"

# ------------------------------------------------------------ paquets
if command -v apt-get >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq gpg wget ca-certificates lldpd python3 >/dev/null
  mkdir -p /etc/apt/keyrings
  wget -qO- https://apt.grafana.com/gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/grafana.gpg
  echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" > /etc/apt/sources.list.d/grafana.list
  apt-get update -qq
  apt-get install -y -qq alloy >/dev/null
  echo 'DAEMON_ARGS="-c"' > /etc/default/lldpd           # écoute aussi CDP (switchs Cisco)
  ALLOY_ENV=/etc/default/alloy
elif command -v dnf >/dev/null || command -v yum >/dev/null; then
  PM=$(command -v dnf || command -v yum)
  cat > /etc/yum.repos.d/grafana.repo <<'EOF'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
  $PM install -y -q epel-release >/dev/null 2>&1 || true   # lldpd est dans EPEL
  $PM install -y -q alloy lldpd python3 >/dev/null
  echo 'LLDPD_OPTIONS="-c"' > /etc/sysconfig/lldpd
  ALLOY_ENV=/etc/sysconfig/alloy
else
  echo "Gestionnaire de paquets non géré."; exit 1
fi

# ------------------------------------------------------------ LLDP -> métrique lldp_neighbor_info
TEXTFILE=/var/lib/alloy/textfile
mkdir -p "$TEXTFILE" /usr/local/lib/alloy-lldp
cat > /usr/local/lib/alloy-lldp/lldp2prom.py <<'EOF'
#!/usr/bin/env python3
"""Convertit les voisins LLDP/CDP (lldpcli) en métriques Prometheus pour le collecteur textfile."""
import json, os, subprocess, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "/var/lib/alloy/textfile/lldp.prom"

def val(x):
    """Déroule les listes/objets {'value': ...} du format json0 de lldpcli."""
    while isinstance(x, list):
        x = x[0] if x else None
    if isinstance(x, dict):
        return x.get("value")
    return x

def esc(s):
    return str(s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

try:
    raw = subprocess.run(["lldpcli", "-f", "json0", "show", "neighbors"], capture_output=True, text=True, timeout=20).stdout
    data = json.loads(raw or "{}")
except Exception:
    data = {}
lines = ["# HELP lldp_neighbor_info Voisin LLDP/CDP vu sur une interface", "# TYPE lldp_neighbor_info gauge"]
for lldp in data.get("lldp", []) or []:
    for itf in lldp.get("interface", []) or []:
        ch = (itf.get("chassis") or [{}])[0]
        pt = (itf.get("port") or [{}])[0]
        labels = {
            "interface": itf.get("name"), "protocol": itf.get("via"),
            "chassis_name": val(ch.get("name")), "chassis_id": val(ch.get("id")),
            "mgmt_ip": val(ch.get("mgmt-ip")), "port_id": val(pt.get("id")), "port_descr": val(pt.get("descr")),
        }
        lines.append("lldp_neighbor_info{" + ",".join(f'{k}="{esc(v)}"' for k, v in labels.items()) + "} 1")
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    f.write("\n".join(lines) + "\n")
os.chmod(tmp, 0o644)
os.replace(tmp, OUT)
EOF
chmod 755 /usr/local/lib/alloy-lldp/lldp2prom.py

cat > /etc/systemd/system/alloy-lldp.service <<EOF
[Unit]
Description=Export des voisins LLDP/CDP pour Alloy
After=lldpd.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/alloy-lldp/lldp2prom.py ${TEXTFILE}/lldp.prom
EOF
cat > /etc/systemd/system/alloy-lldp.timer <<'EOF'
[Unit]
Description=Export LLDP toutes les 5 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
EOF

# ------------------------------------------------------------ configuration Alloy
cat > /etc/alloy/config.alloy <<EOF
// Généré par install.sh : supervision ${SERVER}

prometheus.exporter.unix "node" {
  enable_collectors = ["systemd"]
  textfile {
    directory = "${TEXTFILE}"
  }
}

discovery.relabel "node" {
  targets = prometheus.exporter.unix.node.targets
  rule {
    target_label = "instance"
    replacement  = "${NAME}"
  }
  rule {
    target_label = "job"
    replacement  = "node"
  }
}

prometheus.scrape "node" {
  targets         = discovery.relabel.node.output
  forward_to      = [prometheus.remote_write.main.receiver]
  scrape_interval = "30s"
}

prometheus.remote_write "main" {
  endpoint {
    url = "http://${SERVER}:9090/api/v1/write"
  }
  external_labels = {
    os = "linux",
    ip = "${IP}",
  }
}

loki.relabel "journal" {
  forward_to = []
  rule {
    source_labels = ["__journal__systemd_unit"]
    target_label  = "unit"
  }
  rule {
    source_labels = ["__journal_priority_keyword"]
    target_label  = "level"
  }
  rule {
    source_labels = ["__journal_syslog_identifier"]
    target_label  = "app"
  }
}

loki.source.journal "journal" {
  forward_to    = [loki.write.main.receiver]
  relabel_rules = loki.relabel.journal.rules
  max_age       = "12h"
  labels        = { job = "journal", host = "${NAME}", os = "linux" }
}

loki.write "main" {
  endpoint {
    url = "http://${SERVER}:3100/loki/api/v1/push"
  }
}
EOF

# Alloy doit pouvoir lire le journal système
usermod -aG systemd-journal,adm alloy 2>/dev/null || usermod -aG systemd-journal alloy || true
chown -R alloy: "$TEXTFILE" 2>/dev/null || true

systemctl daemon-reload
systemctl enable --now lldpd >/dev/null 2>&1 || true
systemctl restart lldpd || true
systemctl enable --now alloy-lldp.timer >/dev/null
systemctl enable alloy >/dev/null 2>&1
systemctl restart alloy
sleep 3
/usr/bin/python3 /usr/local/lib/alloy-lldp/lldp2prom.py "${TEXTFILE}/lldp.prom" || true

if systemctl is-active --quiet alloy; then
  echo "==> Alloy actif. '${NAME}' apparaîtra dans Grafana et sur la carte d'ici 1 minute."
  NB=$(grep -c '^lldp_neighbor_info' "${TEXTFILE}/lldp.prom" 2>/dev/null || echo 0)
  echo "    Voisins switch détectés pour l'instant : ${NB} (les switchs annoncent toutes les 30 s environ)"
else
  echo "!! Alloy ne démarre pas : journalctl -u alloy -n 50"
  exit 1
fi
