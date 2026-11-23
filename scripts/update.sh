#!/usr/bin/env bash
# Télécharge la nouvelle version du code (appelé par ./setup.sh --update, qui relance ensuite l'installation).
#   bash scripts/update.sh          passe à la dernière version publiée (dernier tag vX.Y.Z), jamais au travail en cours
#   bash scripts/update.sh --edge   suit la branche main (testeurs), comme avant : git pull --ff-only
# Ne revient jamais en arrière : si la dernière version publiée n'est pas plus récente que ce qui est installé, rien ne change.
# Code de sortie : 0 = le code est prêt (changé ou non), 1 = rien n'a été modifié à cause d'un problème expliqué.
set -euo pipefail
cd "$(dirname "$0")/.."

FR=""; [[ "${LANG:-}${LANGUAGE:-}" == fr* ]] && FR=1
say() { if [[ -n "$FR" ]]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }
ok() { printf '\033[32m✔\033[0m %s\n' "$(say "$1" "$2")"; }
warn() { printf '\033[33m!\033[0m %s\n' "$(say "$1" "$2")"; }
die() { printf '\n\033[31m✖\033[0m %s\n\n' "$(say "$1" "$2")"; exit 1; }

EDGE=""
for a in "$@"; do
  case "$a" in
    --edge) EDGE=1 ;;
    *) die "Option inconnue : $a" "Unknown option: $a" ;;
  esac
done

command -v git >/dev/null || die "git manque : apt install git" "git is missing: apt install git"
git rev-parse --git-dir >/dev/null 2>&1 || die "Ce dossier n'a pas été installé avec git clone : télécharge la nouvelle version, décompresse-la DANS ce dossier, puis lance ./setup.sh" \
                                                "This folder was not installed with git clone: download the new version, extract it INTO this folder, then run ./setup.sh"

LOCAL_EDITS_FR="Cause fréquente : un fichier du projet a été modifié à la main. « git status » les liste ; « git stash » les met de côté, puis relance ./setup.sh --update"
LOCAL_EDITS_EN="Usual cause: a project file was edited by hand. \"git status\" lists them; \"git stash\" puts them aside, then run ./setup.sh --update again"

OLD=$(git rev-parse HEAD)

report() {  # $1 = nouveau commit, $2 = nom de la version (facultatif)
  local new=$1 name=${2:-}
  local n; n=$(git rev-list --count "$OLD..$new")
  if [[ -n "$name" ]]; then
    ok "Version $name téléchargée ($n changement(s)). Nouveautés : CHANGELOG.md" "Version $name downloaded ($n change(s)). What's new: CHANGELOG.md"
  else
    ok "Nouvelle version de test téléchargée ($n changement(s)). Nouveautés : CHANGELOG.md, section Unreleased" \
       "New test version downloaded ($n change(s)). What's new: CHANGELOG.md, Unreleased section"
  fi
  git log --no-merges -n 15 --format='    - %s' "$OLD..$new"   # -n, not | head: with pipefail, head closing the pipe failed the update
}

# ------------------------------------------------------------------ --edge : la branche main, travail en cours compris
if [[ -n "$EDGE" ]]; then
  git symbolic-ref -q HEAD >/dev/null || die "Ce dossier n'est sur aucune branche (version figée). Pour suivre main : git checkout main, puis ./setup.sh --update --edge" \
                                             "This folder is not on a branch (pinned version). To follow main: git checkout main, then ./setup.sh --update --edge"
  warn "Mode test (--edge) : tu reçois le travail en cours de main, pas encore publié. À éviter sur une supervision de production." \
       "Test mode (--edge): you get main's work in progress, not released yet. Avoid it on a production monitoring host."
  git pull --ff-only || die "La mise à jour n'a pas pu être téléchargée (voir le message de git ci-dessus). Rien n'a été modifié.
  $LOCAL_EDITS_FR" "The update could not be downloaded (see git's message above). Nothing was changed.
  $LOCAL_EDITS_EN"
  NEW=$(git rev-parse HEAD)
  if [[ "$OLD" == "$NEW" ]]; then ok "Déjà à jour : je vérifie simplement que tout tourne" "Already up to date: just checking that everything runs"
  else report "$NEW"; fi
  exit 0
fi

# ------------------------------------------------------------------ par défaut : la dernière version publiée
REMOTE=$(git config "branch.$(git symbolic-ref -q --short HEAD 2>/dev/null || echo none).remote" 2>/dev/null || true)
[[ -n "$REMOTE" ]] || REMOTE=$(git remote | grep -x origin || git remote | head -1 || true)
[[ -n "$REMOTE" ]] || die "Ce dossier ne sait pas d'où télécharger NetCockpit (aucun dépôt distant). Rien n'a été modifié." \
                          "This folder does not know where to download NetCockpit from (no git remote). Nothing was changed."

git fetch --quiet --tags --force "$REMOTE" || die "La liste des versions n'a pas pu être téléchargée (voir le message de git ci-dessus). Rien n'a été modifié." \
                                                  "The list of versions could not be downloaded (see git's message above). Nothing was changed."
# Seules les versions encore publiées comptent (une étiquette supprimée sur GitHub peut rester dans ce dossier).
TAG=$(git ls-remote --tags --refs "$REMOTE" 'v*' | awk '{sub("refs/tags/", "", $2); print $2}' \
      | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1 || true)
if [[ -z "$TAG" ]]; then
  warn "Aucune version publiée pour l'instant : rien n'a changé, je vérifie simplement que tout tourne." \
       "No published version yet: nothing changed, just checking that everything runs."
  exit 0
fi
TARGET=$(git rev-parse "refs/tags/$TAG^{commit}")

if [[ "$TARGET" == "$OLD" ]]; then
  ok "Déjà à jour ($TAG, la dernière version publiée) : je vérifie simplement que tout tourne" \
     "Already up to date ($TAG, the latest published version): just checking that everything runs"
  exit 0
fi

if ! git merge-base --is-ancestor "$OLD" "$TARGET"; then
  # Jamais en arrière : ce qui est installé n'est pas contenu dans la dernière version publiée.
  if git merge-base --is-ancestor "$TARGET" "$OLD"; then
    ok "Ce dossier est déjà plus récent que la dernière version publiée ($TAG) : rien n'a changé.
  Il passera tout seul à la prochaine version publiée. Pour suivre le travail en cours (testeurs) : ./setup.sh --update --edge" \
       "This folder is already newer than the latest published version ($TAG): nothing changed.
  It will move to the next published version by itself. To follow work in progress (testers): ./setup.sh --update --edge"
  else
    warn "Ce dossier contient des changements qui ne sont pas dans la dernière version publiée ($TAG) : rien n'a changé, pour ne pas les perdre.
  « git log --oneline $TAG..HEAD » les liste." \
         "This folder holds changes that are not in the latest published version ($TAG): nothing changed, so they are not lost.
  \"git log --oneline $TAG..HEAD\" lists them."
  fi
  exit 0
fi

# Avance rapide jusqu'à la version : la branche reste la même, rien n'est réécrit, les fichiers modifiés à la main bloquent.
git -c advice.detachedHead=false merge --quiet --ff-only "$TARGET" || die "La version $TAG n'a pas pu être installée (voir le message de git ci-dessus). Rien n'a été modifié.
  $LOCAL_EDITS_FR" "Version $TAG could not be installed (see git's message above). Nothing was changed.
  $LOCAL_EDITS_EN"
report "$TARGET" "$TAG"
