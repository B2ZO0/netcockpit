#!/usr/bin/env bash
# Installe / met à jour la supervision. Relançable à volonté (ne casse rien, complète le .env si besoin).
set -euo pipefail
cd "$(dirname "$0")"

ok() { printf '\033[32m✔\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!\033[0m %s\n' "$*"; }

command -v docker >/dev/null || { echo "Docker manque : curl -fsSL https://get.docker.com | sh"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Le plugin docker compose manque."; exit 1; }
command -v python3 >/dev/null || { echo "python3 manque (apt install python3)."; exit 1; }

HOST_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' || true)

rand() { python3 -c "import secrets,string;print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(24)))"; }
fernet() { python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"; }
envget() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']\$//"; }

# 1. .env : création, ou ajout des nouvelles variables (mise à jour depuis une version précédente)
[[ -f .env ]] || { touch .env; chmod 600 .env; FIRST_RUN=1; }
added=0
sed -i '/^# --- géré par setup.sh/,$d' .env
sed -i -E '/^(COMPOSE_PROFILES|GRAFANA_PUBLIC_URL|NETMAP_PUBLIC_URL|ALERTMANAGER_PUBLIC_URL|ZABBIX_PUBLIC_URL|NETMAP_ZABBIX_URL)=/d' .env
while IFS= read -r line; do
  [[ "$line" =~ ^([A-Z0-9_]+)=(.*)$ ]] || continue
  key="${BASH_REMATCH[1]}"; val="${BASH_REMATCH[2]}"
  grep -qE "^${key}=" .env && continue
  case "$val" in
    __RANDOM__) val=$(rand) ;;
    __FERNET__) val=$(fernet) ;;
  esac
  [[ "$key" == "PUBLIC_HOST" && -n "${HOST_IP:-}" ]] && val="$HOST_IP"
  echo "${key}=${val}" >> .env; added=$((added + 1))
done < .env.example
[[ $added -gt 0 ]] && ok "${added} réglage(s) ajouté(s) au .env"
chmod 600 .env

PUBLIC_HOST=$(envget PUBLIC_HOST); PUBLIC_HOST=${PUBLIC_HOST:-${HOST_IP:-localhost}}
ZPORT=$(envget ZABBIX_WEB_PORT); ZPORT=${ZPORT:-8081}
profiles=()
[[ "$(envget ENABLE_ZABBIX)" == "true" ]] && profiles+=(zabbix)
[[ "$(envget ENABLE_IPAM)" == "true" ]] && profiles+=(ipam)
ZURL=""; [[ " ${profiles[*]} " == *" zabbix "* ]] && ZURL="http://127.0.0.1:${ZPORT}"

# Valeurs calculées (bloc régénéré à chaque lancement)
{
  echo "# --- géré par setup.sh (ne pas modifier, régénéré à chaque lancement) ---"
  echo "COMPOSE_PROFILES=$(IFS=,; echo "${profiles[*]}")"
  echo "GRAFANA_PUBLIC_URL=http://${PUBLIC_HOST}:3000"
  echo "NETMAP_PUBLIC_URL=http://${PUBLIC_HOST}:8088"
  echo "ALERTMANAGER_PUBLIC_URL=http://${PUBLIC_HOST}:9093"
  echo "ZABBIX_PUBLIC_URL=$([[ -n "$ZURL" ]] && echo "http://${PUBLIC_HOST}:${ZPORT}")"
  echo "NETMAP_ZABBIX_URL=${ZURL}"
} >> .env

# 2. Configurations générées
python3 scripts/render_config.py
NETMAP_PUBLIC_URL="http://${PUBLIC_HOST}:8088" python3 scripts/gen_dashboards.py >/dev/null
mkdir -p data/targets
for f in icmp tcp http dns snmp; do [[ -s data/targets/$f.json ]] || echo "[]" > "data/targets/$f.json"; done
[[ -n "$(envget VCENTER_URL)" && -n "$(envget VCENTER_PASSWORD)" ]] && ok "vCenter configuré" || warn "vCenter non configuré (VCENTER_* dans .env)"
[[ " ${profiles[*]} " == *" zabbix "* ]] && ok "Zabbix activé (port ${ZPORT})"

# 3. Démarrage
docker compose up -d --build --remove-orphans
# redémarrage (plus fiable que le rechargement à chaud) pour appliquer règles et configs générées
docker compose restart prometheus alertmanager netmap >/dev/null 2>&1 || true

echo
ok "Supervision démarrée"
cat <<EOF

  Cockpit (carte, VMware, switchs, inventaire, alertes)   http://${PUBLIC_HOST}:8088
  Grafana (historique)                                     http://${PUBLIC_HOST}:3000   admin / GRAFANA_ADMIN_PASSWORD
$([[ -n "$ZURL" ]] && echo "  Zabbix                                                   http://${PUBLIC_HOST}:${ZPORT}   Admin / ZABBIX_ADMIN_PASSWORD")
$([[ " ${profiles[*]} " == *" ipam "* ]] && echo "  IPAM (xoriin/NetMap)                                     http://${PUBLIC_HOST}:$(envget IPAM_PORT)")
  Prometheus / Alertmanager                                http://${PUBLIC_HOST}:9090 · :9093

  Premier scan : 2 à 5 minutes. Zabbix : 2 minutes de plus au premier démarrage (création de sa base).
  Agents :  Linux   sudo bash agents/linux/install.sh ${PUBLIC_HOST}
            Windows .\\install.ps1 -Server ${PUBLIC_HOST}
EOF
if [[ -n "${FIRST_RUN:-}" ]]; then
  echo; warn "Complète .env (vCenter, notifications, IA) et config/netmap.yml (bâtiments, équipements), puis relance ./setup.sh"
fi
