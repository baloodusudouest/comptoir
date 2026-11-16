"""Configuration lue dans l'environnement du conteneur. Aucune valeur personnelle dans le code.

Les réglages d'usage (recherche d'origine dans Wikidata) ne sont plus ici depuis la 0.6 : ils vivent dans
<data>/reglages.json et se changent dans l'écran Réglages (voir REGLAGES ci-dessous et app/main.py).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import maison

APPLI = "comptoir"


# Réglages d'usage (contrat de sauvegarde 1) : valeur par défaut (son type fixe celui du réglage), et l'ancienne
# variable de la stack, lue une seule fois, au premier démarrage, pour reprendre la valeur ; ensuite seul l'écran
# Réglages fait foi.
REGLAGES = {"recherche_web": True}       # origine des cocktails dans Wikidata (lecture seule)
REPRISES = {"recherche_web": "COMPTOIR_RECHERCHE_WEB"}
# Clés qui ne sortent jamais dans une sauvegarde (aucune n'est un réglage aujourd'hui : garde-fou explicite)
EXCLUS_SAUVEGARDE = ("password", "mistral_cle", "mistral_url", "data")


@dataclass(frozen=True)
class Config:
    password: str
    data: Path
    static: Path
    attente_connexion: bool = True        # délai anti-essais ; coupé dans les tests
    mistral_cle: str = ""                 # clé d'API Mistral ; vide : l'envoi d'une recette à Mistral n'est pas proposé
    mistral_url: str = "https://api.mistral.ai/v1/chat/completions"
    mistral_modele: str = "mistral-small-latest"
    wikidata_url: str = "https://www.wikidata.org/w/api.php"
    corbeille_jours: int = 30             # un livre supprimé reste restaurable ce nombre de jours
    travail_auto: bool = True             # tâches de fond (coupées dans les tests, qui les lancent à la main)


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe()          # 0.6 : MAISON_PASSWORD seul (l'ancien nom n'est plus lu)
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD est absent ou trop court (12 caractères au moins) : Comptoir ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("COMPTOIR_DATA", "/data")),
        static=Path(__file__).parent / "static",
        mistral_cle=os.environ.get("COMPTOIR_MISTRAL_CLE", "").strip(),
        mistral_url=os.environ.get("COMPTOIR_MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions").strip(),
        mistral_modele=os.environ.get("COMPTOIR_MISTRAL_MODELE", "mistral-small-latest").strip(),
    )
