#!/usr/bin/env bash
# NetCockpit : installation, configuration et mise à jour. Relançable à volonté, ne perd jamais tes réglages.
#   ./setup.sh               installe ou met à jour (l'assistant se lance tout seul la première fois)
#   ./setup.sh --update      télécharge la dernière version puis met à jour, sans toucher à tes réglages ni à l'historique
#   ./setup.sh --configure   relance l'assistant : ajouter un bâtiment, changer d'adressage, connecter VMware...
#   ./setup.sh --yes         sans questions (valeurs détectées automatiquement)
#   ./setup.sh --fresh       repart de zéro même si une ancienne installation existe (déconseillé)
set -euo pipefail
cd "$(dirname "$0")"

FR=""; [[ "${LANG:-}${LANGUAGE:-}" == fr* ]] && FR=1
say() { if [[ -n "$FR" ]]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }
ok() { printf '\033[32m✔\033[0m %s\n' "$(say "$1" "$2")"; }
warn() { printf '\033[33m!\033[0m %s\n' "$(say "$1" "$2")"; }
die() { printf '\n\033[31m✖\033[0m %s\n\n' "$(say "$1" "$2")"; exit 1; }

CONFIGURE=""; YES=""; FRESH=""; UPDATE=""; REST=()
for a in "$@"; do
  case "$a" in
    --update) UPDATE=1 ;;
    --configure) CONFIGURE=1; REST+=("$a") ;;
    --yes|-y) YES=1; REST+=("$a") ;;
    --fresh) FRESH=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) die "Option inconnue : $a (voir ./setup.sh --help)" "Unknown option: $a (see ./setup.sh --help)" ;;
  esac
done

command -v docker >/dev/null || die "Docker manque : curl -fsSL https://get.docker.com | sh" "Docker is missing: curl -fsSL https://get.docker.com | sh"
docker compose version >/dev/null 2>&1 || die "Le plugin « docker compose » manque." "The docker compose plugin is missing."
command -v python3 >/dev/null || die "python3 manque : apt install python3" "python3 is missing: apt install python3"

# ------------------------------------------------------------------ --update : récupère la dernière version, puis relance ce script (nouvelle version)
# Tes réglages (.env, config/cockpit.yml) ne font pas partie du dépôt : git ne peut pas les écraser. L'historique est dans des volumes Docker.
if [[ -n "$UPDATE" ]]; then
  command -v git >/dev/null || die "git manque : apt install git" "git is missing: apt install git"
  [[ -d .git ]] || die "Ce dossier n'a pas été installé avec git clone : télécharge la nouvelle version, décompresse-la DANS ce dossier, puis lance ./setup.sh" \
                       "This folder was not installed with git clone: download the new version, extract it INTO this folder, then run ./setup.sh"
  OLD=$(git rev-parse HEAD)
  if ! git pull --ff-only; then
    die "La mise à jour n'a pas pu être téléchargée (voir le message de git ci-dessus). Rien n'a été modifié.
  Cause fréquente : un fichier du projet a été modifié à la main. « git status » les liste ; « git stash » les met de côté, puis relance ./setup.sh --update" \
        "The update could not be downloaded (see git's message above). Nothing was changed.
  Usual cause: a project file was edited by hand. \"git status\" lists them; \"git stash\" puts them aside, then run ./setup.sh --update again"
  fi
  NEW=$(git rev-parse HEAD)
  if [[ "$OLD" == "$NEW" ]]; then ok "Déjà à jour : je vérifie simplement que tout tourne" "Already up to date: just checking that everything runs"
  else
    ok "Nouvelle version téléchargée ($(git log --oneline "$OLD..$NEW" | wc -l | tr -d ' ') changement(s)). Nouveautés : CHANGELOG.md" \
       "New version downloaded ($(git log --oneline "$OLD..$NEW" | wc -l | tr -d ' ') change(s)). What's new: CHANGELOG.md"
    git log --format='    - %s' "$OLD..$NEW" | head -15
  fi
  exec ./setup.sh ${REST[@]+"${REST[@]}"}
fi

HOST_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' || true)
rand() { python3 -c "import secrets,string;print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(24)))"; }
envget() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']\$//"; }
HERE=$(pwd -P)
PROJ=$(docker compose config 2>/dev/null | awk '/^name:/{print $2; exit}' || true)
PROJ=${PROJ:-$(basename "$HERE" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}

# ------------------------------------------------------------------ garde-fous : ne jamais écraser une installation existante
for svc in cockpit netmap; do
  other=$(docker ps -a --filter "label=com.docker.compose.service=$svc" --format '{{.Label "com.docker.compose.project.working_dir"}}' 2>/dev/null | sort -u | grep -vxF "$HERE" | head -1 || true)
  if [[ -n "$other" && -z "$FRESH" ]]; then
    die "NetCockpit tourne déjà depuis le dossier $other.
  Pour mettre à jour, décompresse la nouvelle version DANS ce dossier-là (il contient ton .env et ta config), puis lance ./setup.sh depuis ce dossier.
  Ce dossier-ci ($HERE) n'a pas été modifié." \
        "NetCockpit is already running from $other.
  To upgrade, extract the new version INTO that folder (it holds your .env and your config) and run ./setup.sh from there.
  This folder ($HERE) was not changed."
  fi
done
if [[ ! -f .env && -z "$FRESH" ]] && docker volume ls -q 2>/dev/null | grep -qE "^${PROJ}_(zabbix-db|grafana-data|prometheus-data|cockpit-data|netmap-data)$"; then
  die "Une installation existe déjà (volumes Docker « ${PROJ}_… »), mais ce dossier n'a pas de fichier .env.
  Pour ne rien casser, je m'arrête : démarrer maintenant créerait de nouveaux mots de passe et une config vierge.
  → Remets ici ton ancien .env et ta config (config/cockpit.yml ou config/netmap.yml), depuis l'ancien dossier ou depuis backups/<date>/, puis relance ./setup.sh
  → Pour vraiment repartir de zéro : ./setup.sh --fresh (les anciens mots de passe Zabbix et Grafana ne fonctionneront plus)" \
      "An installation already exists (Docker volumes \"${PROJ}_…\") but this folder has no .env file.
  Stopping so that nothing breaks: starting now would create new passwords and an empty configuration.
  → Put your previous .env and config (config/cockpit.yml or config/netmap.yml) back here, from the old folder or from backups/<date>/, then run ./setup.sh again
  → To really start from scratch: ./setup.sh --fresh (the old Zabbix and Grafana passwords will no longer work)"
fi

# ------------------------------------------------------------------ 0. migration depuis la 1.0 (le cockpit s'appelait « netmap »)
if [[ -f config/netmap.yml && ! -f config/cockpit.yml ]]; then mv config/netmap.yml config/cockpit.yml; ok "config/netmap.yml renommé en config/cockpit.yml" "config/netmap.yml renamed to config/cockpit.yml"; fi
if [[ -f .env ]]; then sed -i -E '/^(NETMAP_[A-Z_]+|ENABLE_IPAM|IPAM_[A-Z_]+)=/d; /^# --- xoriin/d' .env; fi
if docker volume inspect "${PROJ}_netmap-data" >/dev/null 2>&1 && ! docker volume inspect "${PROJ}_cockpit-data" >/dev/null 2>&1; then
  docker volume create --label com.docker.compose.project="$PROJ" --label com.docker.compose.volume=cockpit-data "${PROJ}_cockpit-data" >/dev/null
  docker run --rm -v "${PROJ}_netmap-data:/from:ro" -v "${PROJ}_cockpit-data:/to" alpine sh -c 'cp -a /from/. /to/' >/dev/null 2>&1 \
    && ok "Historique du cockpit repris" "Cockpit history carried over" || true
fi

# ------------------------------------------------------------------ sauvegarde de tes réglages (10 dernières dans backups/)
if [[ -f .env ]]; then
  BK="backups/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$BK"; chmod 700 backups
  cp -a .env "$BK"/; cp -a config/*.yml "$BK"/ 2>/dev/null || true
  ls -1d backups/*/ 2>/dev/null | head -n -10 | xargs -r rm -rf
  ok "Réglages sauvegardés dans $BK" "Settings backed up to $BK"
fi

# ------------------------------------------------------------------ 1. .env : création, ou ajout des nouveaux réglages (tes valeurs ne sont jamais modifiées)
FIRST_RUN=""
[[ -f .env ]] || { touch .env; chmod 600 .env; FIRST_RUN=1; }
MANAGED='COMPOSE_PROFILES|GRAFANA_PUBLIC_URL|COCKPIT_PUBLIC_URL|ALERTMANAGER_PUBLIC_URL|ZABBIX_PUBLIC_URL|COCKPIT_ZABBIX_URL|COCKPIT_INSTALL_DIR'
sed -i -E "/^# --- (géré par setup.sh|managed by setup.sh)/d; /^(${MANAGED})=/d" .env
added=0
while IFS= read -r line; do
  [[ "$line" =~ ^([A-Z0-9_]+)=(.*)$ ]] || continue
  key="${BASH_REMATCH[1]}"; val="${BASH_REMATCH[2]}"
  grep -qE "^${key}=" .env && continue
  [[ "$val" == "__RANDOM__" ]] && val=$(rand)
  [[ "$key" == "PUBLIC_HOST" && -n "${HOST_IP:-}" ]] && val="$HOST_IP"
  echo "${key}=${val}" >> .env; added=$((added + 1))
done < .env.example
[[ $added -gt 0 ]] && ok "${added} réglage(s) ajouté(s) au .env" "${added} setting(s) added to .env"
# une clé présente deux fois : on garde la dernière valeur non vide (celle que tu as ajoutée), à sa place
python3 - <<'PY'
import re
lines = open(".env", encoding="utf-8").read().splitlines()
last = {}
for i, l in enumerate(lines):
    m = re.match(r"^([A-Z0-9_]+)=(.*)$", l)
    if m and (m.group(2).strip() or m.group(1) not in last):
        last[m.group(1)] = i
out = [l for i, l in enumerate(lines) if not (re.match(r"^([A-Z0-9_]+)=", l) and last.get(l.split("=", 1)[0]) != i)]
open(".env", "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
chmod 600 .env

# la machine a changé d'adresse (ré-adressage) : PUBLIC_HOST suit, sauf si c'est un nom DNS
PH=$(envget PUBLIC_HOST)
if [[ -n "${HOST_IP:-}" && "$PH" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && "$PH" != "$HOST_IP" ]] && ! ip -4 addr 2>/dev/null | grep -q "inet ${PH}/"; then
  sed -i "s/^PUBLIC_HOST=.*/PUBLIC_HOST=${HOST_IP}/" .env
  warn "Cette machine a changé d'adresse : ${PH} → ${HOST_IP} (PUBLIC_HOST mis à jour). Réinstalle l'agent des serveurs avec la nouvelle adresse, ou utilise un nom DNS (voir docs/cas-pratiques.md)." \
       "This machine's address changed: ${PH} → ${HOST_IP} (PUBLIC_HOST updated). Reinstall the server agents with the new address, or use a DNS name (see docs/scenarios.md)."
fi

# ------------------------------------------------------------------ image du cockpit : téléchargée toute prête si possible, sinon construite ici
# scripts/cockpit_image.py donne l'image qui correspond exactement au code de ce dossier (COCKPIT_IMAGE dans .env, auto par défaut).
IMAGE_READY=""
cockpit_image() {
  [[ -n "$IMAGE_READY" ]] && return 0
  local ref t=()
  ref=$(COCKPIT_IMAGE="$(envget COCKPIT_IMAGE)" python3 scripts/cockpit_image.py 2>/dev/null || true)
  command -v timeout >/dev/null && t=(timeout 600)
  if [[ -n "$ref" ]]; then
    say "Téléchargement de l'image du cockpit…" "Downloading the cockpit image…"
    if ${t[@]+"${t[@]}"} docker pull -q "$ref" >/dev/null 2>&1 && docker tag "$ref" netcockpit/cockpit:local; then
      ok "Image du cockpit téléchargée, rien à construire ($ref)" "Cockpit image downloaded, nothing to build ($ref)"
      IMAGE_READY=1; return 0
    fi
    warn "Image toute prête indisponible (pas encore publiée, pas d'accès à ghcr.io, ou processeur non pris en charge) : construction sur cette machine" \
         "Ready-made image unavailable (not published yet, no access to ghcr.io, or unsupported CPU): building it on this machine"
  fi
  say "Construction de l'image du cockpit (quelques minutes la première fois)…" "Building the cockpit image (a few minutes the first time)…"
  docker compose build -q cockpit
  IMAGE_READY=1
}

# ------------------------------------------------------------------ 2. assistant : la première fois, sur demande, ou si la config est encore l'exemple
NEED_WIZARD=""
[[ ! -f config/cockpit.yml || -n "$CONFIGURE" ]] && NEED_WIZARD=1
grep -q "Site A (servers)" config/cockpit.yml 2>/dev/null && NEED_WIZARD=1
if [[ -n "$NEED_WIZARD" ]]; then
  say "Préparation de l'assistant…" "Preparing the setup assistant…"
  cockpit_image
  tty=(-i); [[ -t 0 && -z "$YES" ]] && tty=(-it)
  wl="en"; [[ -n "$FR" ]] && wl="fr"
  docker run --rm "${tty[@]}" --network host --user "$(id -u):$(id -g)" -v "$HERE:/work" -w /work \
    netcockpit/cockpit:local python /app/app/configure.py --lang "$wl" ${YES:+--yes} \
    || { [[ -f config/cockpit.yml ]] || die "Configuration annulée : rien n'a été démarré." "Setup cancelled: nothing was started."; }
fi

# ------------------------------------------------------------------ 3. valeurs calculées (bloc régénéré à chaque lancement)
PUBLIC_HOST=$(envget PUBLIC_HOST); PUBLIC_HOST=${PUBLIC_HOST:-${HOST_IP:-localhost}}
ZPORT=$(envget ZABBIX_WEB_PORT); ZPORT=${ZPORT:-8081}
profiles=()
[[ "$(envget ENABLE_ZABBIX)" == "true" ]] && profiles+=(zabbix)
ZURL=""; [[ " ${profiles[*]} " == *" zabbix "* ]] && ZURL="http://127.0.0.1:${ZPORT}"
{
  echo "# --- managed by setup.sh: the lines below are rewritten on every run (your own settings above are never touched) ---"
  echo "COMPOSE_PROFILES=$(IFS=,; echo "${profiles[*]}")"
  echo "GRAFANA_PUBLIC_URL=http://${PUBLIC_HOST}:3000"
  echo "COCKPIT_PUBLIC_URL=http://${PUBLIC_HOST}:8088"
  echo "ALERTMANAGER_PUBLIC_URL="   # Alertmanager n'écoute plus qu'en local (sécurité)
  echo "ZABBIX_PUBLIC_URL=$([[ -n "$ZURL" ]] && echo "http://${PUBLIC_HOST}:${ZPORT}")"
  echo "COCKPIT_ZABBIX_URL=${ZURL}"
  echo "COCKPIT_INSTALL_DIR=${HERE}"
} >> .env

# ------------------------------------------------------------------ 4. configurations générées
python3 scripts/render_config.py
COCKPIT_PUBLIC_URL="http://${PUBLIC_HOST}:8088" python3 scripts/gen_dashboards.py >/dev/null
mkdir -p data/targets
for f in icmp tcp http dns snmp; do [[ -s data/targets/$f.json ]] || echo "[]" > "data/targets/$f.json"; done
if [[ -n "$(envget VCENTER_URL)" && -n "$(envget VCENTER_PASSWORD)" ]]; then ok "VMware configuré ($(envget VCENTER_URL))" "VMware configured ($(envget VCENTER_URL))"
elif [[ -z "$(envget PROXMOX_URL)" ]]; then warn "Ni VMware ni Proxmox configuré : ./setup.sh --configure pour en connecter un" "Neither VMware nor Proxmox configured: ./setup.sh --configure to connect one"; fi
[[ -n "$(envget PROXMOX_URL)" && -n "$(envget PROXMOX_TOKEN_SECRET)" ]] && ok "Proxmox configuré ($(envget PROXMOX_URL))" "Proxmox configured ($(envget PROXMOX_URL))"
[[ " ${profiles[*]} " == *" zabbix "* ]] && ok "Zabbix activé (port ${ZPORT})" "Zabbix enabled (port ${ZPORT})"

# ------------------------------------------------------------------ 5. démarrage
cockpit_image
docker compose up -d --remove-orphans
docker compose restart prometheus alertmanager cockpit >/dev/null 2>&1 || true

echo
ok "NetCockpit démarré" "NetCockpit is running"
if [[ -n "$FR" ]]; then cat <<EOF

  Cockpit (carte, VMware, switchs, inventaire, alertes)   http://${PUBLIC_HOST}:8088   mot de passe : $(envget COCKPIT_PASSWORD)
  Grafana (historique)                                     http://${PUBLIC_HOST}:3000   admin / GRAFANA_ADMIN_PASSWORD (dans .env)
$([[ -n "$ZURL" ]] && echo "  Zabbix                                                   http://${PUBLIC_HOST}:${ZPORT}   Admin / ZABBIX_ADMIN_PASSWORD (dans .env)")

  Premier scan : 2 à 5 minutes. Zabbix : 2 à 3 minutes de plus au premier démarrage.
  Ajouter un bâtiment, changer d'adressage, connecter VMware, Proxmox ou Telegram :  ./setup.sh --configure
  Mettre à jour plus tard, sans rien perdre :  ./setup.sh --update
  Guide pas à pas : docs/demarrage.md · selon ta situation : docs/cas-pratiques.md
  Dans le cockpit, l'écran « Mise en route » (le drapeau) montre ce qu'il reste à faire.
EOF
else cat <<EOF

  Cockpit (map, VMware, switches, inventory, alerts)       http://${PUBLIC_HOST}:8088   password: $(envget COCKPIT_PASSWORD)
  Grafana (history)                                        http://${PUBLIC_HOST}:3000   admin / GRAFANA_ADMIN_PASSWORD (in .env)
$([[ -n "$ZURL" ]] && echo "  Zabbix                                                   http://${PUBLIC_HOST}:${ZPORT}   Admin / ZABBIX_ADMIN_PASSWORD (in .env)")

  First scan: 2 to 5 minutes. Zabbix: 2 to 3 more minutes on first start.
  Add a building, change addressing, connect VMware, Proxmox or Telegram:  ./setup.sh --configure
  Update later, without losing anything:  ./setup.sh --update
  Step-by-step guide: docs/getting-started.md · by situation: docs/scenarios.md
  In the cockpit, the "Setup" screen (the flag) shows what is left to do.
EOF
fi
