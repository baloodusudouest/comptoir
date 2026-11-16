"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import maison

APPLI = "comptoir"


def _oui(nom: str, defaut: str = "") -> bool:
    return os.environ.get(nom, defaut).strip().lower() in ("oui", "1", "true", "yes")


@dataclass(frozen=True)
class Config:
    password: str
    data: Path
    static: Path
    attente_connexion: bool = True        # délai anti-essais ; coupé dans les tests
    mistral_cle: str = ""                 # clé d'API Mistral ; vide : l'envoi d'une recette à Mistral n'est pas proposé
    mistral_url: str = "https://api.mistral.ai/v1/chat/completions"
    mistral_modele: str = "mistral-small-latest"
    recherche_web: bool = True            # origine des cocktails dans Wikidata / Wikipédia (lecture seule)
    wikidata_url: str = "https://www.wikidata.org/w/api.php"
    corbeille_jours: int = 30             # un livre supprimé reste restaurable ce nombre de jours
    travail_auto: bool = True             # tâches de fond (coupées dans les tests, qui les lancent à la main)


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe("COMPTOIR_PASSWORD")      # 0.5 : MAISON_PASSWORD, repli sur l'ancien nom
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD (ou COMPTOIR_PASSWORD) est absent ou trop court (12 caractères au moins) : "
                         "Comptoir ne démarre pas.")
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("COMPTOIR_DATA", "/data")),
        static=Path(__file__).parent / "static",
        mistral_cle=os.environ.get("COMPTOIR_MISTRAL_CLE", "").strip(),
        mistral_url=os.environ.get("COMPTOIR_MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions").strip(),
        mistral_modele=os.environ.get("COMPTOIR_MISTRAL_MODELE", "mistral-small-latest").strip(),
        recherche_web=_oui("COMPTOIR_RECHERCHE_WEB", "oui"),
    )
