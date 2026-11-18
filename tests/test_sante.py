"""0.7.0 (socle 0.9.0) : santé des tâches de fond dans /health et copie cohérente de la base."""
from __future__ import annotations

import sqlite3
import time

import pytest

from app import main, maison
from tests.conftest import MDP, fabriquer_client

JETON = "jeton-commun-essai"


@pytest.fixture(autouse=True)
def registre_neuf(monkeypatch):
    """Registre de tâches propre à chaque test (le vrai vit le temps du processus)."""
    monkeypatch.setattr(maison, "TACHES", maison.Taches())
    monkeypatch.setenv("MAISON_JETON", JETON)


def par_nom(sante):
    return {t["nom"]: t for t in sante["taches"]}


def test_health_porte_la_sante_sans_message_sans_jeton(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        main.ETAT["travail"].demarrer()            # tâche de fond (coupée dans les tests) : déclare ses tâches
        main.ETAT["travail"].arreter()
        r = c.get("/health").json()
        assert r["version_socle"] == "0.9.1"
        taches = par_nom(r)
        assert set(taches) == {"origine-wikidata", "purge-corbeille", "import-livre", "copie-des-bases"}
        assert taches["origine-wikidata"]["periode_s"] == 60 and taches["purge-corbeille"]["periode_s"] == 3600
        assert taches["import-livre"]["type"] == "demande" and taches["import-livre"]["etat"] == "jamais"
        assert taches["copie-des-bases"]["type"] == "reguliere" and taches["copie-des-bases"]["periode_s"] == 86400
        assert all("message" not in t for t in r["taches"])
        assert r["copie_base"] == {"le": None, "ok": False, "bases": ["comptoir.db"], "taille": 0}
        avec = c.get("/health", headers={"Authorization": f"Bearer {JETON}"}).json()
        assert all("message" in t for t in avec["taches"])
        assert all("message" not in t for t in c.get("/health", headers={"Authorization": "Bearer faux"}).json()["taches"])
        c.post("/api/connexion", json={"mot_de_passe": MDP})
        assert all("message" in t for t in c.get("/health").json()["taches"])


def test_tour_rate_de_la_boucle_passe_en_retard(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        travail = main.ETAT["travail"]

        def origine_cassee():
            travail.arreter()                      # un seul tour de boucle
            raise ValueError("réponse inattendue")
        travail.une_origine = origine_cassee
        travail._derniere_purge = time.monotonic() - 2 * 3600   # purge due à ce tour
        travail.demarrer()
        travail._fil.join(5)
        taches = par_nom(c.get("/health", headers={"Authorization": f"Bearer {JETON}"}).json())
        assert taches["origine-wikidata"]["etat"] == "en_retard"
        assert taches["origine-wikidata"]["message"] == "ValueError: réponse inattendue"
        assert taches["purge-corbeille"]["etat"] == "ok"   # la purge passe quand même (comportement d'avant)


def test_import_illisible_passe_en_erreur(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        c.post("/api/connexion", json={"mot_de_passe": MDP})
        assert c.post("/api/livres/import?nom=essai.epub", content=b"pas un livre").status_code == 422
        assert par_nom(c.get("/health").json())["import-livre"]["etat"] == "erreur"


def test_copie_de_la_base(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        r = maison.copier_bases([tmp_path / "data" / "comptoir.db"], tmp_path / "data" / "copies")
        assert r["ok"] and r["bases"] == ["comptoir.db"] and r["taille"] > 0
        assert c.get("/health").json()["copie_base"]["ok"] is True
    copie = sqlite3.connect(tmp_path / "data" / "copies" / "comptoir-derniere.db")
    try:
        assert copie.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        copie.close()
