"""Réglages dans l'appli, sauvegarde pour l'Anneau et restauration (contrat de sauvegarde 1). Aucun réseau :
l'Anneau est imité par main.ETAT["lire_anneau"] (argument « lire » de maison.lire_sauvegarde)."""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from app import main
from tests.conftest import MDP, fabriquer_client

JETON = "jeton-commun-de-test"


def connecter(c):
    assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200


# ---------------------------------------------------------------- reprise depuis la stack, puis écran Réglages

def test_reprise_au_premier_demarrage_puis_variable_ignoree(tmp_path, faux, monkeypatch):
    monkeypatch.setenv("COMPTOIR_RECHERCHE_WEB", "non")              # stack actuelle
    with fabriquer_client(tmp_path, faux) as c:
        connecter(c)
        assert c.get("/api/reglages").json() == {"recherche_web": False}
        assert c.get("/api/session").json()["recherche_web"] is False
        lignes = [j for j in c.get("/api/journal").json() if j["action"] == "reglage"]
        assert len(lignes) == 1 and "COMPTOIR_RECHERCHE_WEB" in lignes[0]["detail"]
    assert json.loads((tmp_path / "data" / "reglages.json").read_text()) == {"recherche_web": False}
    monkeypatch.setenv("COMPTOIR_RECHERCHE_WEB", "oui")              # second démarrage : la variable n'est plus lue
    with fabriquer_client(tmp_path, faux) as c:
        connecter(c)
        assert c.get("/api/reglages").json() == {"recherche_web": False}
        assert len([j for j in c.get("/api/journal").json() if j["action"] == "reglage"]) == 1


def test_sans_variable_valeur_par_defaut(tmp_path, faux, monkeypatch):
    monkeypatch.delenv("COMPTOIR_RECHERCHE_WEB", raising=False)
    with fabriquer_client(tmp_path, faux) as c:
        connecter(c)
        assert c.get("/api/reglages").json() == {"recherche_web": True}
        assert not [j for j in c.get("/api/journal").json() if j["action"] == "reglage"]


def test_changer_un_reglage(tmp_path, faux, monkeypatch):
    monkeypatch.delenv("COMPTOIR_RECHERCHE_WEB", raising=False)
    with fabriquer_client(tmp_path, faux) as c:
        assert c.get("/api/reglages").status_code == 401                      # session demandée
        assert c.put("/api/reglages", json={"recherche_web": False}).status_code == 401
        connecter(c)
        assert c.put("/api/reglages", json={"recherche_web": False}).json() == {"recherche_web": False}
        assert main.ETAT["travail"].a_chercher() is None                      # la tâche de fond suit tout de suite
        assert c.post("/api/sources/wikidata/verifier").json()["ok"] is False
        assert any(j["action"] == "reglage" and "oui → non" in j["detail"] for j in c.get("/api/journal").json())
        for mauvais in ({"recherche_web": "peut-être"}, {"recherche_web": 1}, {"recherche_web": None}, {"inconnu": True}, {}):
            r = c.put("/api/reglages", json=mauvais)
            assert r.status_code == 400 and r.json()["detail"], mauvais
        assert c.get("/api/reglages").json() == {"recherche_web": False}       # rien n'a bougé


# ---------------------------------------------------------------- porte de l'Anneau : GET /externe/sauvegarde

def test_sauvegarde_jeton_commun_seulement(tmp_path, faux, monkeypatch):
    monkeypatch.setenv("COMPTOIR_MISTRAL_CLE", "valeur-secrete-mistral")
    monkeypatch.delenv("MAISON_JETON", raising=False)
    monkeypatch.delenv("MAISON_JETON_ANCIEN", raising=False)
    monkeypatch.setenv("COMPTOIR_JETON", "ancien-jeton-par-paire")            # ancien style : n'ouvre rien
    monkeypatch.setenv("ANNEAU_JETON_COMPTOIR", "ancien-jeton-par-paire")
    with fabriquer_client(tmp_path, faux) as c:
        assert c.get("/externe/sauvegarde").status_code == 404                # MAISON_JETON vide : porte fermée
        assert c.get("/externe/sauvegarde", headers={"Authorization": "Bearer ancien-jeton-par-paire"}).status_code == 404
        monkeypatch.setenv("MAISON_JETON", JETON)
        assert c.get("/externe/sauvegarde").status_code == 401
        assert c.get("/externe/sauvegarde", headers={"Authorization": "Bearer ancien-jeton-par-paire"}).status_code == 401
        connecter(c)                                                           # la session n'ouvre pas la porte
        assert c.get("/externe/sauvegarde").status_code == 401
        r = c.get("/externe/sauvegarde", headers={"Authorization": f"Bearer {JETON}"})
        assert r.status_code == 200
        s = r.json()
        assert s["contrat"] == 1 and s["appli"] == "comptoir" and s["reglages"] == {"recherche_web": True}
        assert set(s) == {"contrat", "appli", "version", "le", "reglages", "ecartes"}
        texte = r.text
        for interdit in ("valeur-secrete-mistral", MDP, JETON, "mistral_cle", "password", str(tmp_path), "/data"):
            assert interdit not in texte
        assert c.get("/externe/sauvegarde", headers={"X-Maison-Jeton": JETON}).status_code == 200


def test_sauvegarde_exclus_explicites():
    from app import maison
    from app.config import EXCLUS_SAUVEGARDE
    sortie = maison.sauvegarde("comptoir", "0", {"recherche_web": True, "mistral_cle": "x", "mistral_url": "y", "data": "/z"},
                               exclus=EXCLUS_SAUVEGARDE)
    assert sortie["reglages"] == {"recherche_web": True}


# ---------------------------------------------------------------- restaurer depuis l'Anneau

class FauxAnneau:
    def __init__(self, sauvegardes=None, panne=None):
        self.sauvegardes = sauvegardes or {}
        self.panne = panne
        self.demandes = []

    def __call__(self, adresse, jeton):
        self.demandes.append((adresse, jeton))
        if self.panne:
            raise self.panne
        if "?le=" in adresse:
            le = adresse.split("?le=")[1]
            if le not in self.sauvegardes:
                raise urllib.error.HTTPError(adresse, 404, "Not Found", {}, io.BytesIO(b"{}"))
            return {"le": le, "version": "0.6.0", "reglages": self.sauvegardes[le]}
        return {"dates": sorted(self.sauvegardes, reverse=True)}


def test_restaurer_dates_differences_application(tmp_path, faux, monkeypatch):
    monkeypatch.delenv("COMPTOIR_RECHERCHE_WEB", raising=False)
    monkeypatch.setenv("MAISON_JETON", JETON)
    anneau = FauxAnneau({"2026-11-14": {"recherche_web": False, "cle_inconnue": 3, "mistral_cle": "fuite"},
                         "2026-11-15": {"recherche_web": True}})
    with fabriquer_client(tmp_path, faux) as c:
        main.ETAT["lire_anneau"] = anneau
        assert c.get("/api/restaurer").status_code == 401
        connecter(c)
        assert c.get("/api/restaurer").json() == {"dates": ["2026-11-15", "2026-11-14"]}
        assert anneau.demandes[-1] == ("http://anneau:8094/externe/sauvegardes/comptoir", JETON)
        assert c.get("/api/restaurer", params={"le": "2026-11-15"}).json()["differences"] == []
        r = c.get("/api/restaurer", params={"le": "2026-11-14"}).json()
        assert r["version"] == "0.6.0"
        assert [(d["cle"], d["actuel"], d["sauve"]) for d in r["differences"]] == [("recherche_web", True, False)]
        assert c.get("/api/restaurer", params={"le": "14/11/2026"}).status_code == 400
        assert c.post("/api/restaurer", json={"le": "2026-11-14"}).json() == {"reglages": {"recherche_web": False}, "changes": 1}
        assert c.get("/api/reglages").json() == {"recherche_web": False}
        assert json.loads((tmp_path / "data" / "reglages.json").read_text()) == {"recherche_web": False}
        j = [x for x in c.get("/api/journal").json() if x["action"] == "restauration_reglages"]
        assert len(j) == 1 and "oui → non" in j[0]["detail"] and "2026-11-14" in j[0]["cible"]
        assert c.post("/api/restaurer", json={"le": "2026-11-14"}).json()["changes"] == 0   # déjà à jour
        r = c.post("/api/restaurer", json={"le": "2026-11-01"})                            # jour absent
        assert r.status_code == 404 and "aucune sauvegarde" in r.json()["detail"]


@pytest.mark.parametrize("panne", [urllib.error.URLError("refusé"), TimeoutError(), ValueError("json")])
def test_restaurer_anneau_injoignable(tmp_path, faux, panne):
    with fabriquer_client(tmp_path, faux) as c:
        main.ETAT["lire_anneau"] = FauxAnneau(panne=panne)
        connecter(c)
        for r in (c.get("/api/restaurer"), c.get("/api/restaurer", params={"le": "2026-11-14"}),
                  c.post("/api/restaurer", json={"le": "2026-11-14"})):
            assert r.status_code == 503 and "Anneau" in r.json()["detail"]
        assert c.get("/api/reglages").json() == {"recherche_web": True}


def test_restaurer_rien_chez_l_anneau(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        main.ETAT["lire_anneau"] = FauxAnneau(panne=urllib.error.HTTPError("x", 404, "Not Found", {}, io.BytesIO(b"")))
        connecter(c)
        r = c.get("/api/restaurer")
        assert r.status_code == 404 and "aucune sauvegarde" in r.json()["detail"]
        main.ETAT["lire_anneau"] = FauxAnneau()
        assert c.get("/api/restaurer").json() == {"dates": []}


def test_sante_inchangee(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        r = c.get("/health")
        assert r.status_code == 200 and set(r.json()) <= {"ok", "version", "faisables", "a_traiter"}
