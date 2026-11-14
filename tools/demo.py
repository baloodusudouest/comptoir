"""Serveur de démonstration : Comptoir avec les trois livres inventés importés et un bar à moitié rempli.

Sert aux tests d'écran et aux captures. Rien n'est demandé à Internet : Wikidata et Mistral sont simulés.
Usage : python -m tools.demo [port]   (mot de passe : demo-demo-demo)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import httpx
import uvicorn

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app import main  # noqa: E402
from app.config import Config  # noqa: E402
from tools.fabrique import livre_deux_colonnes, livre_sans_reperes, livre_scriptorium  # noqa: E402

MDP = "demo-demo-demo"


def faux_wikidata(requete: httpx.Request) -> httpx.Response:
    p = dict(requete.url.params)
    if p.get("action") == "wbsearchentities":
        trouves = {"Négroni": [{"id": "Q2", "description": "cocktail italien"}],
                   "Manhattan": [{"id": "Q4", "description": "cocktail au whisky"}]}.get(p["search"], [])
        return httpx.Response(200, json={"search": trouves})
    if p.get("action") == "wbgetentities":
        ent = {"Q2": {"claims": {"P495": [{"mainsnak": {"datavalue": {"value": {"id": "Q38"}}}}]}},
               "Q4": {"claims": {"P495": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}],
                                 "P1071": [{"mainsnak": {"datavalue": {"value": {"id": "Q60"}}}}]}},
               "Q38": {"labels": {"fr": {"value": "Italie"}}}, "Q30": {"labels": {"fr": {"value": "États-Unis"}}},
               "Q60": {"labels": {"fr": {"value": "New York"}}}}
        return httpx.Response(200, json={"entities": {i: ent.get(i, {}) for i in p["ids"].split("|")}})
    return httpx.Response(200, json={})


def faux_mistral(requete: httpx.Request) -> httpx.Response:
    contenu = {"titre": "Brouillon du barman", "ingredients": ["4 cl de gin", "2 cl de vermouth sec"],
               "etapes": ["Remuer avec de la glace et filtrer."], "chapeau": "", "origine": ""}
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(contenu)}}], "data": []})


def configurer(data: Path) -> None:
    main.ETAT.clear()
    main.ETAT["cfg"] = Config(password=MDP, data=data, static=RACINE / "app" / "static", attente_connexion=False,
                              travail_auto=False, mistral_cle="demo", wikidata_url="https://wikidata.demo/w/api.php")
    main.ETAT["client_wikidata"] = httpx.Client(transport=httpx.MockTransport(faux_wikidata))
    main.ETAT["client_mistral"] = httpx.Client(transport=httpx.MockTransport(faux_mistral))


def preparer(data: Path) -> None:
    from fastapi.testclient import TestClient
    configurer(data)
    with TestClient(main.app) as c:
        c.post("/api/connexion", json={"mot_de_passe": MDP})
        for livre in (livre_scriptorium(), livre_sans_reperes(), livre_deux_colonnes()):
            c.post("/api/livres/import", content=livre)
        for ing in ("rhum-blanc", "citron-vert", "sirop-sucre", "gin-london-dry", "vermouth-rouge", "tequila", "menthe", "citron", "rye", "eau-gazeuse", "angostura"):
            c.post("/api/bar", json={"ingredient": ing, "present": True})
        c.post("/api/frais", json={"ingredient": "citron-vert", "frais": True})
        recettes = {r["titre"]: r["id"] for r in c.get("/api/recettes").json()["recettes"]}
        c.post(f"/api/recettes/{recettes['Daïquiri de la maison']}/favori", json={"favori": True})
        main.ETAT["travail"].tout_faire()


def lancer(port: int = 8192, data: Path | None = None):
    data = data or Path(tempfile.mkdtemp(prefix="comptoir-demo-"))
    preparer(data)
    configurer(data)
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    lancer(int(sys.argv[1]) if len(sys.argv) > 1 else 8192)
