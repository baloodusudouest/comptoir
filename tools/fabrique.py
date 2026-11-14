"""Livres EPUB inventés pour les tests et la démonstration. Aucune recette d'un vrai livre.

- livre_scriptorium() : comme ceux que fabrique Scriptorium (0.2.2) — un fichier par page, repère
  epub:type="pagebreak" et petit « p. 12 » visible en tête de page, liste des pages dans la navigation.
- livre_sans_reperes() : un livre « du commerce » — chapitres, titres h2, listes à puces, étapes numérotées.
"""
from __future__ import annotations

import io
import zipfile

from PIL import Image, ImageDraw



def _ecrire(z: zipfile.ZipFile, nom, contenu, compress_type: int = zipfile.ZIP_DEFLATED) -> None:
    """Chaque fichier de l'archive porte la même date : deux fabrications du même livre donnent les mêmes octets
    (sinon l'empreinte change d'une seconde à l'autre et le test de doublon échoue au hasard)."""
    info = nom if isinstance(nom, zipfile.ZipInfo) else zipfile.ZipInfo(nom)
    info.date_time = (2026, 1, 1, 0, 0, 0)
    info.compress_type = compress_type
    z.writestr(info, contenu)

def _image(couleur: tuple[int, int, int]) -> bytes:
    im = Image.new("RGB", (480, 360), couleur)
    d = ImageDraw.Draw(im)
    d.ellipse((150, 70, 330, 290), fill=tuple(min(255, c + 60) for c in couleur))
    t = io.BytesIO()
    im.save(t, "JPEG", quality=80)
    return t.getvalue()


def _epub(titre: str, auteur: str, pages: list[tuple[str, str]], images: dict[str, bytes], liste_pages: list[tuple[str, str]] | None = None) -> bytes:
    """pages : (nom du fichier, corps XHTML). Archive EPUB 3 minimale et valide (mimetype en tête, non compressé)."""
    t = io.BytesIO()
    with zipfile.ZipFile(t, "w") as z:
        _ecrire(z, zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        _ecrire(z, "META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>""")
        manif = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
        spine = []
        for i, (nom, corps) in enumerate(pages):
            manif.append(f'<item id="p{i}" href="{nom}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="p{i}"/>')
            _ecrire(z, f"EPUB/{nom}", f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="fr"><head><title>{titre}</title></head>
<body>{corps}</body></html>""")
        for j, (nom, octets) in enumerate(images.items()):
            manif.append(f'<item id="img{j}" href="images/{nom}" media-type="image/jpeg"/>')
            _ecrire(z, f"EPUB/images/{nom}", octets)
        pl = ""
        if liste_pages:
            pl = '<nav epub:type="page-list" hidden=""><ol>' + "".join(f'<li><a href="{h}">{n}</a></li>' for h, n in liste_pages) + "</ol></nav>"
        _ecrire(z, "EPUB/nav.xhtml", f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Sommaire</title></head>
<body><nav epub:type="toc"><ol><li><a href="{pages[0][0]}">Début</a></li></ol></nav>{pl}</body></html>""")
        _ecrire(z, "EPUB/content.opf", f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">urn:uuid:essai-{abs(hash(titre)) % 10**8}</dc:identifier>
<dc:title>{titre}</dc:title><dc:creator>{auteur}</dc:creator><dc:language>fr</dc:language></metadata>
<manifest>{''.join(manif)}</manifest><spine>{''.join(spine)}</spine></package>""")
    return t.getvalue()


def _page(numero: int, corps: str) -> str:
    return (f'<span epub:type="pagebreak" role="doc-pagebreak" id="page-{numero}" title="{numero}"></span>'
            f'<p class="page-originale">p. {numero}</p>{corps}')


def livre_scriptorium() -> bytes:
    pages = [
        (10, "<h1>Les classiques</h1><p>Un chapitre d'introduction, sans recette. On y parle de shakers et de glace.</p>"),
        (11, '<h1>Daïquiri de la maison</h1><p><img src="images/daiquiri.jpg" alt=""/></p>'
             "<p>Créé à La Havane au début du siècle dernier, dans un bar du port.</p>"
             "<p>6 cl de rhum blanc</p><p>3 cl de jus de citron vert</p><p>2 cl de sirop de sucre</p>"
             "<p>Secouer longuement avec de la glace et filtrer dans une coupe bien froide.</p>"),
        # Recette à cheval sur les pages 12 et 13
        (12, "<h1>Mexican Mule</h1><p>Une variante épicée de la mule.</p>"
             "<p>5 cl de tequila</p><p>1 cl de jus de citron vert</p>"),
        (13, "<p>12 cl de ginger beer</p><p>Un quartier de citron vert pour décorer</p>"
             "<p>Verser la tequila et le citron sur la glace, allonger de ginger beer.</p>"),
        (14, "<h1>Négroni</h1><p>3 cl de gin</p><p>3 cl de vermouth rouge</p><p>3 cl de Campari</p>"
             "<p>Un zeste d'orange</p><p>Remuer dans un verre à mélange, servir sur un gros glaçon.</p>"),
        (15, "<h1>Fleur des prés</h1><p>4 cl de gin</p><p>2 cl de liqueur de pissenlit</p><p>1 cl de jus de citron</p>"
             "<p>Secouer et servir dans une coupe.</p>"),
        (16, "<h1>Brouillon du barman</h1><p>2 cl de quelque chose</p>"),   # recette douteuse : une seule ligne, sans préparation
        (17, "<h1>Virgin Mojito</h1><p>8 feuilles de menthe</p><p>2 cl de sirop de sucre</p><p>3 cl de jus de citron vert</p>"
             "<p>Eau gazeuse</p><p>Piler la menthe avec le sirop et le citron, ajouter la glace pilée et allonger d'eau gazeuse.</p>"),
    ]
    fichiers = [(f"p{i + 1:04d}.xhtml", _page(n, corps)) for i, (n, corps) in enumerate(pages)]
    liste = [(f"p{i + 1:04d}.xhtml#page-{n}", str(n)) for i, (n, _) in enumerate(pages)]
    return _epub("Cocktails du port", "Auteur Inventé", fichiers, {"daiquiri.jpg": _image((180, 120, 70))}, liste)


def livre_deux_colonnes() -> bytes:
    """Livre inventé mis en page comme une bible du bar : quantités puis noms en colonnes, rubriques, étoiles,
    un « conseil du barman » et une légende des notes répétée sur chaque page (qui ne doit pas devenir un conseil)."""
    legende = "<h2>APPRÉCIATION DES COCKTAILS</h2><p>★★★★★ EXCELLENT</p><p>BON</p><p>PASSABLE</p>"
    pages = [
        (30, legende + "<h1>TRIANGLE DU PORT</h1><ul><li>30 ml</li><li>15 ml</li><li>2 traits</li></ul>"
             "<p>de rhum ambré</p><p>de jus d'ananas</p><p>d'Angostura</p>"
             "<p>MÉTHODE : FRAPPER tous les ingrédients avec de la glace et filtrer dans le verre refroidi.</p>"
             "<p>VERRE : coupe</p><p>DÉCO : zeste d'orange</p><p>MON AVIS : un cocktail inventé pour les essais, rond et fruité.</p>"
             "<p>ORIGINE : créé en 2020 au bar des quais (Bordeaux, France).</p><p>★★★★☆</p>"),
        (31, legende + "<h2>CONSEIL DU BARMAN POUR LA GLACE</h2>"
             "<p>Une glace bien froide et bien sèche dilue moins le cocktail : on la sort du congélateur au dernier moment, "
             "on remplit le shaker aux deux tiers et on ne garde jamais la glace qui a déjà servi pour frapper.</p>"
             "<p>Pour un verre servi sur glace, un gros glaçon fond plus lentement que plusieurs petits.</p>"),
        (32, legende + "<h1>VERT DES QUAIS</h1><ul><li>45 ml</li><li>15 ml</li></ul><p>de gin</p><p>de sirop de sucre</p>"
             "<p>MÉTHODE : REMUER avec de la glace et filtrer.</p><p>VERRE : coupe</p><p>★★★☆☆</p>"),
        # Note et « 0 » écrits comme des titres sous le nom ; nom en paragraphe ; note sans aucun nom au-dessus
        (33, "<h2>ROSE DU MÔLE</h2><h3>0</h3><h3>★★★★☆</h3><p>VERRE : coupe</p>"
             "<ul><li>40 ml de gin</li><li>20 ml de jus de citron</li></ul><p>MÉTHODE : FRAPPER avec de la glace et filtrer.</p>"
             "<p>BRISE DU LARGE</p><p>O-E</p><h3>★★★★★</h3><ul><li>50 ml de rhum blanc</li><li>20 ml de jus de citron vert</li></ul>"
             "<p>MÉTHODE : FRAPPER avec de la glace et filtrer.</p>"
             "<p><img src=\"images/vague.jpg\" alt=\"\"/></p><p>Une phrase de fin de page qui n'est pas un nom de cocktail, bien plus longue.</p>"
             "<h3>★★☆☆☆</h3><ul><li>30 ml de vodka</li><li>90 ml de jus de cranberry</li></ul><p>MÉTHODE : VERSER sur la glace.</p>"),
        # Variantes entre parenthèses sous le nom (en titre puis en paragraphe), rubrique mise en titre,
        # et un « conseil du barman » dont une ligne commence par une quantité (ce n'est pas une recette pour autant)
        (34, "<h2>GRAND LARGE</h2><h3>(RECETTE DE LA MAISON)</h3><h3>★★★★☆</h3><h4>VERRE : coupe</h4>"
             "<ul><li>40 ml de gin</li><li>20 ml de jus de citron</li></ul><p>MÉTHODE : FRAPPER avec de la glace et filtrer.</p>"
             "<h2>GRAND LARGE</h2><p>(FORMULE CLASSIQUE)</p><p>★★★☆☆</p><p>VERRE : coupe</p>"
             "<ul><li>50 ml de gin</li><li>10 ml de jus de citron</li></ul><p>MÉTHODE : REMUER avec de la glace et filtrer.</p>"
             "<h2>CONSEIL DU BARMAN POUR L'ORDRE DE PRÉPARATION</h2>"
             "<p>Comme en cuisine, un cocktail se prépare dans un certain ordre : les ingrédients les moins chers d'abord, "
             "pour qu'une erreur de dosage coûte peu, puis les spiritueux, et la glace tout à la fin pour limiter la dilution.</p>"
             "<p>1 trait d'amer se verse en dernier, juste avant de frapper, sinon son parfum se perd dans le shaker.</p>"),
    ]
    fichiers = [(f"p{i + 1:04d}.xhtml", _page(n, corps)) for i, (n, corps) in enumerate(pages)]
    liste = [(f"p{i + 1:04d}.xhtml#page-{n}", str(n)) for i, (n, _) in enumerate(pages)]
    return _epub("Bible du port", "Auteur Inventé", fichiers, {"vague.jpg": _image((60, 110, 160))}, liste)


def livre_sans_reperes() -> bytes:
    corps1 = """<h1>Chapitre un : la soirée</h1><p>Quelques recettes pour commencer.</p>
<h2>Manhattan</h2><ul><li>5 cl de rye</li><li>2 cl de vermouth rouge</li><li>2 traits d'Angostura</li><li>Une cerise au marasquin</li></ul>
<ol><li>Remuer tous les ingrédients avec de la glace dans un verre à mélange.</li><li>Filtrer dans une coupe et décorer d'une cerise.</li></ol>
<h2>Paloma</h2><p><img src="images/paloma.jpg" alt=""/></p><ul><li>5 cl de tequila</li><li>10 cl de soda au pamplemousse</li><li>1 pincée de sel</li></ul>
<ol><li>Givrer le verre de sel, verser la tequila sur la glace et allonger.</li></ol>"""
    corps2 = """<h1>Chapitre deux : sans alcool</h1>
<h2>Citronnade pétillante</h2><ul><li>4 cl de jus de citron</li><li>2 cl de sirop de sucre</li><li>Eau gazeuse</li></ul>
<ol><li>Mélanger le citron et le sirop, ajouter la glace et allonger d'eau gazeuse.</li></ol>"""
    return _epub("Le bar à la maison", "Autre Auteur", [("ch1.xhtml", corps1), ("ch2.xhtml", corps2)],
                 {"paloma.jpg": _image((200, 90, 110))})


def livre_drm() -> bytes:
    t = io.BytesIO(livre_sans_reperes())
    with zipfile.ZipFile(t, "a") as z:
        _ecrire(z, "META-INF/encryption.xml", '<encryption><EncryptedData><EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/></EncryptedData></encryption>')
    return t.getvalue()
