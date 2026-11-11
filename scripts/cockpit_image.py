#!/usr/bin/env python3
"""Choisit l'image toute prête du cockpit qui correspond au code de ce dossier (utilisé par setup.sh et par la CI).

  python3 scripts/cockpit_image.py         affiche l'image à télécharger, ou rien = construire l'image sur place
  python3 scripts/cockpit_image.py --tag   affiche seulement l'étiquette du dossier cockpit/ (tree-<empreinte>)

L'étiquette est l'empreinte git du dossier cockpit/ : elle ne change que si le code du cockpit change,
et la même empreinte donne toujours la même image. La CI publie chaque image sous cette étiquette.

Réglage COCKPIT_IMAGE (dans .env) :
  auto (défaut)                 image officielle si le dossier cockpit/ n'a pas été modifié, sinon construction locale
  build                         toujours construire sur cette machine (réseau sans accès à ghcr.io, code modifié…)
  registre/nom                  ton propre registre (miroir) ; l'étiquette est choisie automatiquement
  registre/nom:étiquette        cette image précise, telle quelle
Bibliothèque standard uniquement.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "ghcr.io/b2zo0/netcockpit"
BUILD_WORDS = {"build", "local", "off", "no", "false", "0"}


def _git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def cockpit_tag(root=ROOT):
    """Étiquette de l'image pour le dossier cockpit/ tel qu'il est dans le dernier commit, ou None (pas de git)."""
    tree = _git(root, "rev-parse", "HEAD:cockpit")
    if not tree or len(tree) < 12:
        return None
    return "tree-" + tree[:12]


def cockpit_unchanged(root=ROOT):
    """Vrai si le dossier cockpit/ est exactement celui du dernier commit (rien de modifié ni d'ajouté à la main)."""
    status = _git(root, "status", "--porcelain", "--untracked-files=all", "--", "cockpit")
    return status == ""


def choose(setting, root=ROOT):
    """Image à télécharger pour ce réglage COCKPIT_IMAGE, ou "" pour construire sur place."""
    value = (setting or "").strip() or "auto"
    if value.lower() in BUILD_WORDS:
        return ""
    if value.lower() == "auto":
        repo = DEFAULT_REPO
    else:
        last = value.rsplit("/", 1)[-1]
        if ":" in last or "@" in value:
            return value          # étiquette ou empreinte précise : utilisée telle quelle
        repo = value
    if not cockpit_unchanged(root):
        return ""                 # code du cockpit modifié ou pas installé avec git : l'image officielle ne lui correspondrait pas
    tag = cockpit_tag(root)
    return f"{repo}:{tag}" if tag else ""


def main(argv):
    if "--tag" in argv:
        tag = cockpit_tag()
        if not tag:
            print("cockpit_image: not a git checkout", file=sys.stderr)
            return 1
        print(tag)
        return 0
    print(choose(os.environ.get("COCKPIT_IMAGE", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
