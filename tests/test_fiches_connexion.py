"""Fiches « Connexion » communes (contrat 3, socle 0.11.0) : forme de /api/maison/services, accès par session ou
ANNEAU_CLE seulement (jamais MAISON_JETON), « Vérifier » d'un service pas relié n'essaie rien, copies non retouchées
du module commun et de l'interface commune."""
from pathlib import Path

from app import maison
from app.config import APPLI
from tests.conftest import MDP, fabriquer_client

RACINE = Path(__file__).resolve().parent.parent
CLE = "cle-anneau-de-test-1234567890"
IDS = ["wikidata", "mistral"]


def connecter(client):
    assert client.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200


CHAMPS = {"id", "nom", "genre", "cible", "etat", "lit", "ecrit", "reglage", "detail", "verifie_le", "guide",
          "derniere_ecriture", "gestes"}


def test_forme_du_contrat_3(client):
    connecter(client)
    r = client.get("/api/maison/services")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    corps = r.json()
    assert corps["contrat"] == 3 and corps["appli"] == APPLI and corps["simule"] is False
    assert [s["id"] for s in corps["services"]] == IDS
    for s in corps["services"]:
        assert set(s) == CHAMPS and s["lit"] and s["ecrit"] and s["etat"] in maison.ETATS_SERVICE
        assert len(s["gestes"]) <= 1
        if s["etat"] == "pas_relie":
            assert s["reglage"]


def test_acces_session_ou_cle_anneau(tmp_path, faux, monkeypatch):
    with fabriquer_client(tmp_path, faux) as client:                     # sans session
        _acces(client, monkeypatch)


def _acces(client, monkeypatch):
    assert client.get("/api/maison/services").status_code == 401
    assert client.post("/api/maison/services/wikidata/verifier").status_code == 401
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test-12345")
    entete = {"Authorization": "Bearer jeton-commun-de-test-12345"}
    assert client.get("/api/maison/services", headers=entete).status_code == 401
    monkeypatch.setenv("ANNEAU_CLE", CLE)
    assert client.get("/api/maison/services", headers={"Authorization": f"Bearer {CLE}"}).status_code == 200
    assert client.get("/api/maison/services", headers={"Authorization": "Bearer mauvaise"}).status_code == 401


def test_verifier_inconnu_et_pas_relie(client):
    connecter(client)
    assert client.post("/api/maison/services/inconnu/verifier").status_code == 404
    for s in client.get("/api/maison/services").json()["services"]:
        if s["etat"] == "pas_relie":
            apres = client.post(f"/api/maison/services/{s['id']}/verifier").json()
            assert apres["etat"] == "pas_relie" and apres["verifie_le"] is None


def test_copies_communes_non_retouchees():
    assert maison.CONTRAT == 3 and maison.VERSION_SOCLE == "0.11.1"
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()
    for nom in maison.FICHIERS_INTERFACE:
        ecrite, calculee = maison.empreinte_interface(RACINE / "frontend" / "src" / "lib" / "services" / nom)
        assert ecrite and ecrite == calculee, nom


# ---------------------------------------------------------------- propres à Comptoir (0.8.0)

def test_verifier_lit_sans_rien_ecrire(client, faux):
    """Wikidata : une lecture (siteinfo) ; Mistral : la liste des modèles (gratuite), aucune recette envoyée."""
    w = client.post("/api/maison/services/wikidata/verifier").json()
    assert w["etat"] == "repond" and w["detail"] == "Wikidata répond." and w["verifie_le"]
    assert all(d.method == "GET" for d in faux["wikidata"].demandes)
    m = client.post("/api/maison/services/mistral/verifier").json()
    assert m["etat"] == "repond" and m["detail"] == "Mistral répond et accepte la clé."
    assert [d.url.path.rsplit("/", 1)[-1] for d in faux["mistral"].demandes] == ["models"]
    assert all(d.method == "GET" for d in faux["mistral"].demandes)
    n = len(faux["mistral"].demandes)                                     # au plus un essai toutes les 30 s
    assert client.post("/api/maison/services/mistral/verifier").json()["verifie_le"] == m["verifie_le"]
    assert len(faux["mistral"].demandes) == n


def test_cle_refusee_par_mistral(client, faux):
    faux["mistral"].statut = 401
    m = client.post("/api/maison/services/mistral/verifier").json()
    assert m["etat"] == "ne_repond_pas" and m["detail"] == "Mistral refuse la clé."


def test_textes_repris_de_l_ancien_ecran(client):
    """Mêmes phrases que l'ancienne route /api/sources (gardée en 0.8.0) ; le rôle passe dans la note de la fiche."""
    anciens = {s["id"]: s for s in client.get("/api/sources").json()}
    for s in client.get("/api/maison/services").json()["services"]:
        assert s["lit"] == anciens[s["id"]]["lit"] and s["ecrit"] == anciens[s["id"]]["ecrit"]
        assert s["guide"] == {"reglages": [], "allumer": [], "pannes": [], "une_fois": [], "terminal": "",
                              "note": anciens[s["id"]]["role"]}
        assert s["gestes"] == [] and s["genre"] == "exterieur"


def test_pas_relie_recherche_coupee_et_sans_cle(tmp_path, faux):
    with fabriquer_client(tmp_path, faux, recherche_web=False, mistral_cle="") as c:
        connecter(c)
        fiches = {s["id"]: s for s in c.get("/api/maison/services").json()["services"]}
        assert fiches["wikidata"]["etat"] == "pas_relie"
        assert fiches["wikidata"]["reglage"] == "Réglages › Recherche d'origine dans Wikidata"
        assert fiches["mistral"]["etat"] == "pas_relie" and fiches["mistral"]["reglage"] == "COMPTOIR_MISTRAL_CLE"
        c.post("/api/maison/services/wikidata/verifier")
        c.post("/api/maison/services/mistral/verifier")
        assert faux["wikidata"].demandes == [] and faux["mistral"].demandes == []    # rien n'est essayé
        c.put("/api/reglages", json={"recherche_web": True})                      # le réglage suit tout de suite
        assert c.get("/api/maison/services").json()["services"][0]["etat"] == "relie"
