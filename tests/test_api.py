"""Santé, garde des routes, connexion et déconnexion."""
import pytest

from tests.conftest import MDP, fabriquer_client


def test_sante_publique_sans_nom(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        r = c.get("/health").json()
        assert r["ok"] is True and "version" in r
        assert set(r) <= {"ok", "version", "faisables", "a_traiter"}


@pytest.mark.parametrize("chemin", ["/api/livres", "/api/recettes", "/api/bar", "/api/a-traiter", "/api/journal", "/api/corbeille"])
def test_tout_demande_la_session(tmp_path, faux, chemin):
    with fabriquer_client(tmp_path, faux) as c:
        assert c.get(chemin).status_code == 401


def test_connexion_et_deconnexion(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        assert c.post("/api/connexion", json={"mot_de_passe": "faux"}).status_code == 401
        assert c.post("/api/connexion", json={"mot_de_passe": MDP}).status_code == 200
        s = c.get("/api/session").json()
        assert s["connecte"] and s["mistral"] and s["recherche_web"]
        assert c.get("/api/livres").status_code == 200
        c.post("/api/deconnexion")
        assert c.get("/api/livres").status_code == 401


def test_mot_de_passe_trop_court(monkeypatch):
    from app.config import charger
    monkeypatch.delenv("MAISON_PASSWORD", raising=False)
    monkeypatch.setenv("COMPTOIR_PASSWORD", "court")
    with pytest.raises(SystemExit):
        charger()


def test_module_commun_maison(monkeypatch):
    """0.5 : copie non retouchée du module du socle ; MAISON_PASSWORD lu d'abord, COMPTOIR_PASSWORD en repli."""
    from app import maison
    from app.config import charger
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()
    monkeypatch.delenv("MAISON_PASSWORD", raising=False)
    monkeypatch.delenv("COMPTOIR_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match="MAISON_PASSWORD"):
        charger()
    monkeypatch.setenv("COMPTOIR_PASSWORD", "ancien-mot-de-passe")          # stack actuelle : ancien nom seul
    assert charger().password == "ancien-mot-de-passe"
    monkeypatch.setenv("MAISON_PASSWORD", "mot-de-passe-commun")            # le nom commun l'emporte
    assert charger().password == "mot-de-passe-commun"
    monkeypatch.setenv("MAISON_PASSWORD", "court")                          # trop court : refusé, même en commun
    with pytest.raises(SystemExit):
        charger()
