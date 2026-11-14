"""Import, page du livre papier, bar et calcul, corbeille, À traiter, Mistral, Wikidata, journal."""
from __future__ import annotations

from datetime import datetime, timedelta

from app import main
from tools.fabrique import livre_drm, livre_sans_reperes, livre_scriptorium


def importer(client, contenu, nom="livre.epub"):
    return client.post(f"/api/livres/import?nom={nom}", content=contenu)


def par_titre(client):
    return {r["titre"]: r for r in client.get("/api/recettes").json()["recettes"]}


# ------------------------------------------------------------------ import et page du livre papier

def test_import_et_pages_du_livre_papier(client):
    r = importer(client, livre_scriptorium()).json()
    assert r["recettes"] == 6 and r["a_verifier"] == 1 and r["a_reperes_page"] is True
    recettes = par_titre(client)
    assert recettes["Daïquiri de la maison"]["pages"] == "p. 11"
    assert recettes["Mexican Mule"]["pages"] == "p. 12-13"          # à cheval sur deux pages (deux fichiers)
    assert recettes["Négroni"]["pages"] == "p. 14"
    assert "Les classiques" not in recettes                            # titre de chapitre, pas une recette
    # Le petit « p. 12 » visible de Scriptorium n'entre ni dans les ingrédients ni dans le texte
    mule = client.get(f"/api/recettes/{recettes['Mexican Mule']['id']}").json()
    assert all("p. 1" not in l["texte"] for l in mule["lignes"])
    assert [l["texte"] for l in mule["lignes"]][:3] == ["5 cl de tequila", "1 cl de jus de citron vert", "12 cl de ginger beer"]
    assert mule["lignes"][3]["facultatif"] is True                    # « … pour décorer »


def test_livre_sans_reperes_n_invente_pas_de_page(client):
    importer(client, livre_sans_reperes())
    recettes = par_titre(client)
    assert recettes["Manhattan"]["pages"] == "" and recettes["Paloma"]["pages"] == ""
    manhattan = client.get(f"/api/recettes/{recettes['Manhattan']['id']}").json()
    assert len(manhattan["etapes"]) == 2


def test_photo_reprise_du_livre(client):
    importer(client, livre_scriptorium())
    daiquiri = par_titre(client)["Daïquiri de la maison"]
    assert daiquiri["photo"] is True
    r = client.get(f"/api/photos/{daiquiri['id']}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp" and "private" in r.headers["cache-control"]
    assert client.get(f"/api/photos/{par_titre(client)['Négroni']['id']}").status_code == 404


def test_drm_et_doublon_refuses(client):
    r = importer(client, livre_drm())
    assert r.status_code == 422 and "DRM" in r.json()["detail"]
    assert importer(client, b"pas un epub").status_code == 422
    importer(client, livre_sans_reperes())
    assert importer(client, livre_sans_reperes()).status_code == 409


def test_origine_ecrite_dans_le_livre_et_lieux_evoques(client):
    importer(client, livre_scriptorium())
    importer(client, livre_sans_reperes())
    recettes = par_titre(client)
    assert recettes["Daïquiri de la maison"]["cree_a"] == ["la-havane"]   # « Créé à La Havane… »
    assert recettes["Mexican Mule"]["evoque"] == ["mexique"]
    assert recettes["Manhattan"]["evoque"] == []                          # ambigu : question, pas de lieu posé
    questions = client.get("/api/a-traiter").json()
    evoque = [e for e in questions["elements"] if e["type"] == "evoque"]
    assert [e["recette_titre"] for e in evoque] == ["Manhattan"]
    client.post(f"/api/a-traiter/{evoque[0]['id']}", json={"action": "oui"})
    assert par_titre(client)["Manhattan"]["evoque"] == ["manhattan"]
    lieux = {l["id"]: l for l in client.get("/api/lieux").json()}
    assert lieux["etats-unis"]["evoque"] == [par_titre(client)["Manhattan"]["id"]]   # compte aussi pour le pays
    assert lieux["cuba"]["cree_a"] == [recettes["Daïquiri de la maison"]["id"]]


# ------------------------------------------------------------------ bar et calcul

def test_bar_faisables_presque_et_deblocage(client):
    importer(client, livre_scriptorium())
    ids = {t: r["id"] for t, r in par_titre(client).items()}
    for ing in ("rhum-ambre", "citron-vert", "sirop-sucre"):      # rhum ambré : ne vaut pas pour « rhum blanc »
        client.post("/api/bar", json={"ingredient": ing, "present": True})
    d = client.get("/api/recettes").json()
    assert ids["Daïquiri de la maison"] not in d["faisables"]
    presque = {p["recette"]: [m["ingredient"] for m in p["manque"]] for p in d["presque"]}
    assert presque[ids["Daïquiri de la maison"]] == ["rhum-blanc"]
    client.post("/api/bar", json={"ingredient": "rhum-blanc", "present": True})
    client.post("/api/bar", json={"ingredient": "menthe", "present": True})
    d = client.get("/api/recettes").json()
    assert ids["Daïquiri de la maison"] in d["faisables"]
    assert ids["Virgin Mojito"] not in d["faisables"]                    # il manque l'eau gazeuse
    assert {x["ingredient"] for x in d["debloque"]} >= {"eau-gazeuse"}
    client.post("/api/bar", json={"ingredient": "eau-gazeuse", "present": True})
    d = client.get("/api/recettes").json()
    assert ids["Virgin Mojito"] in d["faisables"]
    assert par_titre(client)["Virgin Mojito"]["sans_alcool"] is True
    assert par_titre(client)["Daïquiri de la maison"]["sans_alcool"] is False


def test_famille_acceptee_par_une_variante_et_equivalence(client):
    importer(client, livre_scriptorium())
    ids = {t: r["id"] for t, r in par_titre(client).items()}
    for ing in ("gin-london-dry", "vermouth-rouge", "campari"):          # la recette demande « gin » (famille)
        client.post("/api/bar", json={"ingredient": ing, "present": True})
    assert ids["Négroni"] in client.get("/api/recettes").json()["faisables"]   # le zeste est facultatif
    client.post("/api/bar", json={"ingredient": "campari", "present": False})
    client.post("/api/bar", json={"ingredient": "aperol", "present": True})
    assert ids["Négroni"] not in client.get("/api/recettes").json()["faisables"]
    client.post("/api/equivalences", json={"a": "campari", "b": "aperol"})
    assert ids["Négroni"] in client.get("/api/recettes").json()["faisables"]


def test_mon_bar_range_par_famille(client):
    importer(client, livre_scriptorium())
    bar = client.get("/api/bar").json()
    cats = {c["id"]: c for c in bar["categories"]}
    rhum = next(f for f in cats["spiritueux"]["familles"] if f["id"] == "rhum")
    assert {"rhum-blanc", "rhum-ambre"} <= {i["id"] for i in rhum["ingredients"]}   # les variantes de la famille sont proposées
    client.post("/api/frais", json={"ingredient": "citron-vert", "frais": True})
    jus = next(f for f in cats["jus"]["familles"] if f["id"] == "citron-vert")
    assert jus["ingredients"][0]["frais_propose"] is True
    bar = client.get("/api/bar").json()
    cv = next(i for c in bar["categories"] for f in c["familles"] for i in f["ingredients"] if i["id"] == "citron-vert")
    assert cv["frais"] is True


# ------------------------------------------------------------------ corbeille

def test_suppression_corbeille_restauration(client):
    livre = importer(client, livre_scriptorium()).json()
    ids = {t: r["id"] for t, r in par_titre(client).items()}
    client.post(f"/api/recettes/{ids['Négroni']}/favori", json={"favori": True})
    client.post("/api/bar", json={"ingredient": "rhum-blanc", "present": True})
    apercu = client.get(f"/api/livres/{livre['id']}/suppression").json()
    assert apercu["recettes"] == 6 and apercu["favoris"] == 1 and apercu["jours"] == 30
    assert client.delete(f"/api/livres/{livre['id']}").json()["ok"]
    assert client.get("/api/recettes").json()["recettes"] == []          # disparu de partout
    assert client.get("/api/livres").json() == []
    assert client.get(f"/api/recettes/{ids['Négroni']}").status_code == 404
    assert client.get("/api/a-traiter").json()["elements"] == []
    assert client.get("/api/bar").json()["categories"] == []             # ingrédients masqués, pas supprimés
    assert client.get("/health").json()["faisables"] == 0
    corbeille = client.get("/api/corbeille").json()
    assert corbeille[0]["recettes"] == 6
    # Réimporter le même fichier pendant qu'il est dans la corbeille : on propose de le restaurer
    r = importer(client, livre_scriptorium())
    assert r.status_code == 409 and r.json()["corbeille"] == livre["id"]
    client.post(f"/api/livres/{livre['id']}/restaurer")
    recettes = par_titre(client)
    assert len(recettes) == 6 and recettes["Négroni"]["favori"] is True  # favoris gardés
    assert {r["ingredient"] for r in main.ETAT["base"].lire("SELECT ingredient FROM bar")} == {"rhum-blanc"}


def test_corbeille_videe_apres_30_jours(client):
    livre = importer(client, livre_scriptorium()).json()
    photo_id = par_titre(client)["Daïquiri de la maison"]["id"]
    client.post("/api/bar", json={"ingredient": "gin", "present": True})
    client.delete(f"/api/livres/{livre['id']}")
    base, cfg = main.ETAT["base"], main.ETAT["cfg"]
    assert main.ETAT["travail"].purger() == 0                            # pas encore
    vieux = (datetime.now().astimezone() - timedelta(days=31)).isoformat(timespec="seconds")
    base.ecrire("UPDATE livre SET supprime_le = ?", vieux)
    assert main.ETAT["travail"].purger() == 1
    assert base.lire("SELECT * FROM recette") == [] and base.lire("SELECT * FROM ligne") == []
    assert not (cfg.data / "photos" / f"{photo_id}.webp").exists()
    assert list((cfg.data / "livres").iterdir()) == []
    assert base.lire("SELECT ingredient FROM bar") == [{"ingredient": "gin"}]   # le bar ne bouge pas
    assert importer(client, livre_scriptorium()).status_code == 200      # importable de nouveau


# ------------------------------------------------------------------ À traiter, corrections, Mistral

def test_ingredient_inconnu_rattache_partout(client):
    importer(client, livre_scriptorium())
    q = [e for e in client.get("/api/a-traiter").json()["elements"] if e["type"] == "ingredient"]
    pissenlit = next(e for e in q if "pissenlit" in e["donnees"]["nom"])
    r = client.post(f"/api/a-traiter/{pissenlit['id']}", json={"action": "creer", "parent": "liqueurs", "nom": "Liqueur de pissenlit"})
    assert r.json()["lignes"] == 1
    fleur = client.get(f"/api/recettes/{par_titre(client)['Fleur des prés']['id']}").json()
    assert fleur["lignes"][1]["ingredient_nom"] == "Liqueur de pissenlit"
    # Annuler le rattachement depuis le journal : la question revient
    j = next(x for x in client.get("/api/journal").json() if x["action"] == "rattachement")
    client.post(f"/api/journal/{j['id']}/annuler")
    assert any("pissenlit" in e["donnees"].get("nom", "") for e in client.get("/api/a-traiter").json()["elements"])


def test_recette_douteuse_relue_par_mistral_puis_validee(client, faux):
    importer(client, livre_scriptorium())
    q = next(e for e in client.get("/api/a-traiter").json()["elements"] if e["type"] == "recette")
    assert q["recette_titre"] == "Brouillon du barman"
    proposition = client.post(f"/api/recettes/{q['recette_id']}/mistral").json()
    assert proposition["lignes"] == ["2 cl de gin", "1 cl de sirop de sucre"]
    envoye = faux["mistral"].demandes[-1].content.decode()
    assert "Brouillon du barman" in envoye and "Daïquiri" not in envoye   # seul le texte de la recette part
    assert client.get(f"/api/recettes/{q['recette_id']}").json()["etat"] == "a_verifier"   # rien d'enregistré seul
    r = client.put(f"/api/recettes/{q['recette_id']}", json={**proposition, "source": "mistral"}).json()
    assert r["etat"] == "valide" and r["source"] == "mistral" and len(r["lignes"]) == 2
    assert not [e for e in client.get("/api/a-traiter").json()["elements"] if e["type"] == "recette"]
    # Annuler la correction : la recette revient telle qu'elle était
    j = next(x for x in client.get("/api/journal").json() if x["action"] == "correction")
    client.post(f"/api/journal/{j['id']}/annuler")
    assert client.get(f"/api/recettes/{q['recette_id']}").json()["lignes"][0]["texte"] == "2 cl de quelque chose"


def test_mistral_refuse_la_cle(client, faux):
    importer(client, livre_scriptorium())
    faux["mistral"].statut = 401
    rid = par_titre(client)["Négroni"]["id"]
    r = client.post(f"/api/recettes/{rid}/mistral")
    assert r.status_code == 502 and "refuse la clé" in r.json()["detail"]


def test_ignorer_une_fausse_recette(client):
    importer(client, livre_scriptorium())
    rid = par_titre(client)["Brouillon du barman"]["id"]
    client.post(f"/api/recettes/{rid}/ignorer")
    assert "Brouillon du barman" not in par_titre(client)


# ------------------------------------------------------------------ Wikidata (lecture seule)

def test_origine_par_wikidata_sure_ou_a_verifier(client, faux):
    importer(client, livre_scriptorium())
    main.ETAT["base"].ecrire("DELETE FROM lieu_recette WHERE sorte = 'cree_a'")   # on oublie ce que dit le livre
    main.ETAT["travail"].tout_faire()
    recettes = par_titre(client)
    assert recettes["Daïquiri de la maison"]["cree_a"] == ["cuba"]       # un seul cocktail, un seul pays : posé
    assert recettes["Négroni"]["cree_a"] == []                            # deux candidats : question
    q = next(e for e in client.get("/api/a-traiter").json()["elements"] if e["type"] == "origine")
    assert {c["lieu"] for c in q["donnees"]["candidats"]} == {"italie", "paris"}
    client.post(f"/api/a-traiter/{q['id']}", json={"lieu": "italie"})
    assert par_titre(client)["Négroni"]["cree_a"] == ["italie"]
    assert all(d.method == "GET" for d in faux["wikidata"].demandes)     # lecture seule
    n = len(faux["wikidata"].demandes)
    main.ETAT["travail"].tout_faire()
    assert len(faux["wikidata"].demandes) == n                            # chaque recette n'est cherchée qu'une fois


def test_recherche_web_coupee(tmp_path, faux):
    from tests.conftest import MDP, fabriquer_client
    with fabriquer_client(tmp_path, faux, recherche_web=False) as c:
        c.post("/api/connexion", json={"mot_de_passe": MDP})
        importer(c, livre_scriptorium())
        main.ETAT["travail"].tout_faire()
        assert faux["wikidata"].demandes == []
        assert c.post("/api/sources/wikidata/verifier").json()["ok"] is False
