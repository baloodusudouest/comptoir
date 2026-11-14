"""Tests d'écran : le serveur de démonstration (tools/demo.py) ouvert dans un vrai navigateur, sur PC et iPhone.

À chaque écran : aucune erreur de page, aucun débordement horizontal. Sautés si Playwright ou l'interface
compilée manquent (la CI les installe : voir .github/workflows/tests.yml).
Le serveur est partagé entre les deux tailles : un test qui change un état le remet comme il l'a trouvé.
"""
from __future__ import annotations

import os
import shutil
import socket
import threading
import time
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
STATIQUE = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"
pytestmark = pytest.mark.skipif(not STATIQUE.exists(), reason="interface non compilée (cd frontend && npx vite build)")

TAILLES = {"pc": {"width": 1366, "height": 900}, "iphone": {"width": 390, "height": 844}}


@pytest.fixture(scope="module")
def adresse(tmp_path_factory):
    from tools import demo
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    threading.Thread(target=demo.lancer, args=(port, tmp_path_factory.mktemp("demo")), daemon=True).start()
    import httpx
    for _ in range(200):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    return f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def navigateur():
    with pw.sync_playwright() as p:
        chrome = os.environ.get("CHROME") or shutil.which("google-chrome")
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch()
        yield b
        b.close()


def ouvrir(navigateur, adresse, taille):
    page = navigateur.new_page(viewport=TAILLES[taille])
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.goto(adresse + "/")
    page.fill("#mot-de-passe", "demo-demo-demo")
    page.click("button[type=submit]")
    page.locator("ul[aria-label='Faisables maintenant'] li").first.wait_for()
    return page, erreurs


def sans_debordement(page):
    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")


@pytest.mark.parametrize("taille", TAILLES)
def test_au_bar(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    faisables = page.locator("ul[aria-label='Faisables maintenant'] li")
    assert faisables.count() >= 3
    assert page.get_by_text("Cocktails du port, p. 11").first.is_visible()      # livre et page du livre papier
    page.get_by_text("Une bouteille pour en débloquer le plus").wait_for()
    page.get_by_text("Il manque ginger beer").wait_for()
    # Filtre « Sans alcool » : ne restent que les recettes sans alcool
    page.get_by_role("button", name="Sans alcool").click()
    page.wait_for_timeout(150)
    textes = faisables.all_inner_texts()
    assert textes and all("DAÏQUIRI" not in t for t in textes)
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_fiche_page_du_livre_et_preparer(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/cocktails")
    page.locator("ul[aria-label=Recettes] li").filter(has_text="Mexican Mule").click()
    page.get_by_text("p. 12-13").wait_for()                                     # recette à cheval sur deux pages
    page.get_by_text("Mexique").first.wait_for()
    page.get_by_role("button", name="Un verre de plus").click()
    page.get_by_text("10 cl").wait_for()                                         # 5 cl de tequila pour deux verres
    sans_debordement(page)
    page.get_by_role("link", name="Préparer").click()
    page.get_by_text("Étape 1 sur 1").wait_for()
    page.get_by_text("10 cl", exact=False).first.wait_for()                      # le nombre de verres suit
    case = page.get_by_role("checkbox").first
    case.click()
    assert case.get_attribute("aria-checked") == "true"
    assert page.get_by_role("navigation", name="Sections").count() == 0          # rien entre le pouce et le bouton
    sans_debordement(page)
    page.get_by_role("link", name="Quitter").click()
    page.get_by_role("button", name="Corriger").wait_for()
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_par_lieu_et_carte(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/cocktails/lieux")
    page.get_by_role("button", name="Mexique").click()
    page.locator("ul[aria-label='Recettes du lieu'] li").filter(has_text="Mexican Mule").wait_for()
    # Ouvrir le cocktail puis Retour : le pays reste choisi et ses cocktails restent affichés
    page.locator("ul[aria-label='Recettes du lieu'] a").filter(has_text="Mexican Mule").click()
    page.get_by_role("link", name="Retour").click()
    page.locator("ul[aria-label='Recettes du lieu'] li").filter(has_text="Mexican Mule").wait_for()
    assert page.get_by_role("button", name="Mexique").get_attribute("aria-pressed") == "true"
    page.get_by_role("button", name="Carte").click()
    carte = page.locator("svg[aria-label^='Carte du monde des cocktails']")
    carte.wait_for()
    assert carte.locator("path").count() > 100                                    # les pays sont dessinés, hors ligne
    assert carte.get_by_role("button", name="Mexique : 1").count() == 1           # le pays qui a un cocktail est cliquable
    # La carte s'est centrée sur le pays choisi : zoomée, avec les noms des pays
    page.locator("svg text").filter(has_text="Mexique").wait_for()
    page.get_by_role("button", name="Recentrer la carte").click()
    page.wait_for_function("document.querySelectorAll('svg text').length === 0")
    page.get_by_role("button", name="Zoomer", exact=True).click()
    page.get_by_role("button", name="Zoomer", exact=True).click()
    page.locator("svg text").first.wait_for()
    page.wait_for_timeout(600)                                                     # fin de l'animation du zoom
    zoom = carte.locator("g").first.get_attribute("transform")
    # Retour depuis une fiche avec la carte : carte toujours affichée, au même zoom
    page.locator("ul[aria-label='Recettes du lieu'] a").first.click()
    page.get_by_role("link", name="Retour").click()
    carte.wait_for()
    assert carte.locator("g").first.get_attribute("transform") == zoom
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_pastilles_faisable_et_favori(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    faisables = page.locator("ul[aria-label='Faisables maintenant'] li")
    assert faisables.first.get_by_text("Faisable avec ton bar").count() == 1
    page.goto(adresse + "/#/cocktails")
    daiquiri = page.locator("li").filter(has_text="Daïquiri de la maison").first
    daiquiri.get_by_text("Favori", exact=True).wait_for()                        # le favori de la démonstration
    assert daiquiri.get_by_text("Faisable avec ton bar").count() == 1
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_mon_bar_cocher(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/mon-bar")
    statut = page.get_by_role("status").first
    statut.wait_for()
    avant = statut.inner_text()
    case = page.locator("ul[aria-label='Apéritif amer']").get_by_role("checkbox", name="Campari")
    case.click()
    page.wait_for_function("(a) => document.querySelector('[role=status]').innerText !== a", arg=avant)
    case.click()                                                                  # remis comme avant
    page.wait_for_function("(a) => document.querySelector('[role=status]').innerText === a", arg=avant)
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_a_traiter_et_reglages(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/a-traiter")
    page.get_by_role("link", name="Nouveaux ingrédients").click()
    page.get_by_text("« liqueur de pissenlit »").wait_for()
    sans_debordement(page)
    page.goto(adresse + "/#/a-traiter/recette")
    page.get_by_text("Brouillon du barman", exact=True).wait_for()
    page.goto(adresse + "/#/reglages")
    page.get_by_text("Cocktails du port", exact=True).wait_for()
    page.get_by_role("button", name="Supprimer Cocktails du port").click()
    page.get_by_text("Supprimer « Cocktails du port » ?").wait_for()
    page.get_by_text("Le livre reste 30 jours dans la corbeille").wait_for()
    page.get_by_role("button", name="Garder").click()                            # rien n'est supprimé
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_connexion_des_services(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/connexion")
    page.get_by_role("heading", name="Connexion").wait_for()
    page.get_by_role("button", name="Wikidata").click()
    page.get_by_text("Ce qu'il écrit").wait_for()
    page.get_by_text("Rien chez Wikidata").wait_for()
    page.get_by_role("button", name="Vérifier").click()
    page.get_by_text("Wikidata répond.").wait_for()                              # le faux Wikidata de la démonstration
    page.get_by_role("button", name="Mistral").click()
    page.get_by_text("COMPTOIR_MISTRAL_CLE").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_conseils_et_rubriques_du_livre(navigateur, adresse, taille):
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/cocktails/conseils")
    page.get_by_role("heading", name="Glace", exact=True).wait_for()             # le thème
    sans_debordement(page)
    page.get_by_role("link", name="Glace").first.click()
    page.get_by_role("heading", name="Glace", level=2).wait_for()
    page.get_by_text("Bible du port, p. 31").wait_for()
    page.get_by_text("un gros glaçon fond plus lentement", exact=False).wait_for()
    sans_debordement(page)
    # La fiche montre la note du livre, le verre, la déco et ce que le livre en dit
    page.goto(adresse + "/#/cocktails")
    page.get_by_role("link", name="Triangle du Port").first.click()
    page.get_by_role("img", name="Note du livre : 4 sur 5").wait_for()
    page.get_by_text("zeste d'orange", exact=True).wait_for()               # mis en capitale par le CSS seulement
    page.get_by_role("heading", name="Dans le livre").wait_for()
    page.get_by_text("Mon avis").wait_for()
    sans_debordement(page)
    assert erreurs == []


@pytest.mark.parametrize("taille", TAILLES)
def test_redeposer_un_livre_deja_importe(navigateur, adresse, taille, tmp_path):
    """Redéposer un livre déjà là : le message propose « Réimporter à neuf » (pas cliqué ici : le serveur est partagé)."""
    from tools.fabrique import livre_scriptorium
    fichier = tmp_path / "cocktails-du-port.epub"
    fichier.write_bytes(livre_scriptorium())
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/reglages")
    page.get_by_text("Cocktails du port", exact=True).wait_for()
    page.locator("input[type=file]").set_input_files(str(fichier))
    page.get_by_text("Ce livre est déjà importé").wait_for()
    page.get_by_role("button", name="Réimporter à neuf").wait_for()
    sans_debordement(page)
    assert erreurs == []



@pytest.mark.parametrize("taille", TAILLES)
def test_preparer_en_litres(navigateur, adresse, taille):
    """Daïquiri de la maison : 6 + 3 + 2 = 11 cl par verre ; 1,1 litre = dix fois la recette (60 cl de rhum)."""
    page, erreurs = ouvrir(navigateur, adresse, taille)
    page.goto(adresse + "/#/cocktails")
    page.locator("ul[aria-label=Recettes] li").filter(has_text="Daïquiri de la maison").first.click()
    page.get_by_role("button", name="Litres").click()
    champ = page.get_by_label("Nombre de litres")
    champ.fill("1,1")
    champ.press("Enter")
    page.get_by_text("≈ 10 verres de 11 cl, avant la glace").wait_for()
    page.get_by_text("60 cl", exact=True).wait_for()
    page.get_by_role("button", name="Un quart de litre de plus").click()           # 1,35 l
    page.get_by_text("73,64 cl", exact=True).wait_for()
    for _ in range(3):
        page.get_by_role("button", name="Un quart de litre de plus").click()       # 2,1 l : les cl passent en litres
    page.get_by_text("1,15 l", exact=True).wait_for()
    sans_debordement(page)
    page.get_by_role("link", name="Préparer").click()                              # le volume suit dans Préparer
    page.get_by_text("1,15 l", exact=False).first.wait_for()
    assert page.get_by_label("Nombre de litres").input_value() == "2,1"
    sans_debordement(page)
    assert erreurs == []
