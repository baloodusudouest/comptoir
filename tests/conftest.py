"""Un Comptoir de test : dossier temporaire, pas de tâche de fond, faux Wikidata et faux Mistral."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Config

MDP = "mot-de-passe-de-test"


class FauxWikidata:
    """Imite l'API de Wikidata (wbsearchentities, wbgetentities, siteinfo) ; relève chaque demande."""

    def __init__(self):
        self.demandes: list[httpx.Request] = []
        # Daïquiri : un seul cocktail, pays d'origine Cuba. Négroni : deux éléments « cocktail » aux origines différentes.
        self.recherches = {
            "Daïquiri": [{"id": "Q1", "description": "cocktail à base de rhum"}],
            "Négroni": [{"id": "Q2", "description": "cocktail italien"}, {"id": "Q3", "description": "cocktail, variante"}],
        }
        self.entites = {
            "Q1": {"claims": {"P495": [{"mainsnak": {"datavalue": {"value": {"id": "Q241"}}}}]}},
            "Q2": {"claims": {"P495": [{"mainsnak": {"datavalue": {"value": {"id": "Q38"}}}}]}},
            "Q3": {"claims": {"P1071": [{"mainsnak": {"datavalue": {"value": {"id": "Q90"}}}}]}},
            "Q241": {"labels": {"fr": {"value": "Cuba"}}},
            "Q38": {"labels": {"fr": {"value": "Italie"}}},
            "Q90": {"labels": {"fr": {"value": "Paris"}}},
        }

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.demandes.append(requete)
        p = dict(requete.url.params)
        if p.get("action") == "wbsearchentities":
            return httpx.Response(200, json={"search": self.recherches.get(p["search"], [])})
        if p.get("action") == "wbgetentities":
            return httpx.Response(200, json={"entities": {i: self.entites.get(i, {}) for i in p["ids"].split("|")}})
        if p.get("action") == "query":
            return httpx.Response(200, json={"query": {"general": {}}})
        return httpx.Response(400)


class FauxMistral:
    def __init__(self):
        self.demandes: list[httpx.Request] = []
        self.reponse = {"titre": "Brouillon du barman", "ingredients": ["2 cl de gin", "1 cl de sirop de sucre"],
                        "etapes": ["Remuer avec de la glace."], "chapeau": "", "origine": ""}
        self.statut = 200

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.demandes.append(requete)
        if requete.url.path.endswith("/models"):
            return httpx.Response(self.statut, json={"data": []})
        return httpx.Response(self.statut, json={"choices": [{"message": {"content": json.dumps(self.reponse)}}]})


@pytest.fixture
def faux():
    return {"wikidata": FauxWikidata(), "mistral": FauxMistral()}


def fabriquer_client(tmp_path, faux, **reglages):
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=tmp_path / "data", static=tmp_path / "static", attente_connexion=False,
                              travail_auto=False, mistral_cle=reglages.pop("mistral_cle", "cle-de-test"),
                              wikidata_url="https://wikidata.test/w/api.php", **reglages)
    main.ETAT["client_wikidata"] = httpx.Client(transport=httpx.MockTransport(faux["wikidata"]))
    main.ETAT["client_mistral"] = httpx.Client(transport=httpx.MockTransport(faux["mistral"]))
    return TestClient(main.app)


@pytest.fixture
def client(tmp_path, faux):
    with fabriquer_client(tmp_path, faux) as c:
        c.post("/api/connexion", json={"mot_de_passe": MDP})
        yield c
