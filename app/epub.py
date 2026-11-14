"""Lecture d'un livre EPUB et découpage en recettes, par règles.

1. Le livre est mis à plat dans l'ordre de lecture (spine) : une suite de blocs (titre, paragraphe,
   élément de liste, image, repère de page). Une recette peut donc commencer à la fin d'un fichier et
   finir dans le suivant (Scriptorium fait un fichier par page).
2. Les repères de page EPUB 3 (epub:type="pagebreak" ou role="doc-pagebreak") donnent la page du livre
   papier. Le petit « p. 42 » visible que Scriptorium écrit en tête de page est retiré.
3. Une recette = un titre suivi de lignes d'ingrédients, puis d'une préparation. Le chapeau est ce qui
   sépare le titre des ingrédients.
"""
from __future__ import annotations

import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from lxml import etree, html as lhtml

from .ingredients import Arbre, commence_par_quantite, lire_ligne, normaliser, rapprocher


class LivreIllisible(Exception):
    """Le fichier n'est pas un EPUB lisible (ou il est protégé par DRM)."""


@dataclass
class Bloc:
    sorte: str            # titre, para, li_ul, li_ol, image, page
    texte: str = ""
    niveau: int = 0       # pour un titre : 1 à 6
    source: str = ""      # pour une image : chemin dans l'archive


@dataclass
class RecetteLue:
    titre: str
    lignes: list[str]
    etapes: list[str]
    chapeau: str
    page_debut: str | None
    page_fin: str | None
    image: str | None
    texte_original: str
    confiance: float
    raisons: list[str] = field(default_factory=list)
    infos: dict = field(default_factory=dict)      # rubriques du livre : Verre, Déco, Mon avis, Origine, Variante, Autre nom
    note: int | None = None                         # étoiles du livre (★★★★☆ → 4)


@dataclass
class ConseilLu:
    """Passage du livre qui n'est pas une recette : la glace, les verres, l'art de remuer…"""
    titre: str
    theme: str
    contenu: list[dict]                             # [{"sorte": "para" | "li_ul" | "li_ol" | "sous_titre", "texte": …}]
    page_debut: str | None = None
    page_fin: str | None = None
    niveau: int = 0


@dataclass
class LivreLu:
    titre: str
    auteur: str
    a_reperes_page: bool
    recettes: list[RecetteLue]
    images: dict[str, bytes]
    conseils: list[ConseilLu] = field(default_factory=list)


TITRES = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
# Rubriques d'une fiche (« VERRE : martini », « MÉTHODE : FRAPPER… ») : rangées à part, jamais prises pour des ingrédients
RUBRIQUES = [
    (r"verre", "Verre"), (r"d[ée]cor?", "Déco"), (r"m[ée]thode|pr[ée]paration", "Méthode"), (r"mon avis|avis", "Mon avis"),
    (r"origine?|histoire", "Origine"), (r"variantes?|autre possibilit[ée]", "Variante"), (r"pseudo|autres? noms?|alias", "Autre nom"),
]
RUBRIQUE = re.compile(r"^(" + "|".join(m for m, _ in RUBRIQUES) + r")\s*:\s*(.*)$", re.I | re.S)
NOTE = re.compile(r"^[★☆✩✭\*]{3,5}$")
QUANTITE_SEULE = re.compile(r"^(?:\d+(?:[.,]\d+)?|[½¼¾⅓⅔])(?:\s*(?:ml|cl|oz|traits?|dash(?:es)?|gouttes?|pinc[ée]es?|cuill[eè]r[ée]es?|shots?))?(?:\s+(?:de|d'|du))?$", re.I)
FIN_PHRASE = (".", "!", "?", "»", ":", "…")


def rubrique(texte: str) -> tuple[str, str] | None:
    m = RUBRIQUE.match(texte.strip())
    if not m:
        return None
    for motif, nom in RUBRIQUES:
        if re.fullmatch(motif, m.group(1), re.I):
            return nom, m.group(2).strip()
    return None


DEBUT_NOM = re.compile(r"^(?:de |d'|d’|du |des |de la |de l')", re.I)


def apparier_colonnes(blocs: list[Bloc]) -> list[Bloc]:
    """Livre en deux colonnes lu colonne par colonne : « 30 ml », « 15 ml », « 22,5 ml », puis « de rhum… »,
    « de xérès… », « de jus d'ananas ». Quand le nombre de quantités et le nombre de noms concordent, on les apparie
    dans l'ordre ; sinon on ne touche à rien (la recette part dans « À traiter » si elle est mal lue)."""
    sortie: list[Bloc] = []
    i, n = 0, len(blocs)
    texte = lambda b: b.sorte in ("para", "li_ul", "li_ol")   # noqa: E731
    while i < n:
        b = blocs[i]
        if not (texte(b) and QUANTITE_SEULE.match(b.texte.strip())):
            sortie.append(b)
            i += 1
            continue
        # une suite de quantités seules (les images et repères de page intercalés sont gardés à part)
        quantites, autres, j = [], [], i
        while j < n and (blocs[j].sorte in ("image", "page") or (texte(blocs[j]) and QUANTITE_SEULE.match(blocs[j].texte.strip()))):
            (quantites if texte(blocs[j]) else autres).append(blocs[j])
            j += 1
        if len(quantites) < 2 or j >= n or not (texte(blocs[j]) and DEBUT_NOM.match(blocs[j].texte.strip())):
            sortie.extend(blocs[i:j])
            i = j
            continue
        # les noms qui suivent : un nouveau nom commence par « de / d' / du… », le reste continue le nom en cours
        noms: list[str] = []
        k = j
        while k < n and blocs[k].sorte != "titre":
            c = blocs[k]
            if c.sorte in ("image", "page"):
                autres.append(c)
                k += 1
                continue
            ct = c.texte.strip()
            if rubrique(ct) or NOTE.match(ct) or (not noms and not DEBUT_NOM.match(ct)):
                break
            if DEBUT_NOM.match(ct) and not (noms and noms[-1].endswith(("/", "(", ","))):
                noms.append(ct)
            elif noms:
                noms[-1] = noms[-1] + ("" if noms[-1].endswith(("/", "(")) else " ") + ct
            k += 1
        if len(noms) == len(quantites):
            sortie.extend(Bloc("li_ul", f"{q.texte.strip()} {nom}") for q, nom in zip(quantites, noms))
            sortie.extend(autres)
            i = k
        else:
            sortie.extend(blocs[i:j])
            i = j
    return sortie


def recoller(blocs: list[Bloc]) -> list[Bloc]:
    """Recolle ce que la mise en page a coupé (livre en colonnes, lu page par page) :
    - « 15 ml » puis « de Velvet Falernum » : la quantité et le nom lus séparément ;
    - « 15 ml de sirop de sucre (2 parts de sucre/ » puis « 1 part d'eau) » : une ligne coupée en deux ;
    - « MÉTHODE : FRAPPER… avec », une image, puis « de la glace et filtrer… » : une phrase coupée par une image.
    Les images et les repères de page restent à leur place ; un titre arrête toujours le recollage."""
    sortie: list[Bloc] = []
    dernier = None                     # indice du dernier bloc de texte dans « sortie »
    for b in apparier_colonnes(blocs):
        if b.sorte in ("image", "page"):
            sortie.append(b)
            continue
        if b.sorte == "titre":
            sortie.append(b)
            dernier = None
            continue
        texte = b.texte.strip()
        if dernier is not None:
            p = sortie[dernier]
            pt = p.texte.rstrip()
            coupee = pt.endswith((",", "/", "(", "-", "–"))
            quantite_seule = bool(QUANTITE_SEULE.match(pt) or re.match(r"^\d+[.)]$", pt)) and not QUANTITE_SEULE.match(texte)
            coupee = coupee or bool(re.search(r"\s(?:de|d'|d’|du|des|la|le|à)$", pt)) or bool(re.match(r"^\d+\s+ans\b", texte))
            suite = (texte[:1].islower() or texte[:1] in "%)") and not pt.endswith(FIN_PHRASE) and not rubrique(texte) \
                and not NOTE.match(pt) and not commence_par_quantite(texte)
            if coupee or quantite_seule or suite:
                colle = "" if pt.endswith(("/", "(", "-")) else " "
                sorte = "li_ul" if quantite_seule else p.sorte
                sortie[dernier] = Bloc(sorte, (pt + colle + texte).strip())
                continue
        sortie.append(Bloc(b.sorte, texte, b.niveau, b.source))
        dernier = len(sortie) - 1
    return sortie


PETITS_MOTS = {"de", "du", "des", "la", "le", "les", "et", "à", "au", "aux", "en", "d'", "l'", "sur", "pour", "avec", "of", "the", "and", "a"}


def titre_propre(titre: str) -> str:
    """« DAIQUIRI N°1 (STYLE EL FLORIDITA) » → « Daiquiri N°1 (Style El Floridita) » ; un titre déjà en casse mixte est gardé."""
    lettres = [c for c in titre if c.isalpha()]
    if not lettres or not all(c.isupper() for c in lettres):
        return titre
    mots = titre.lower().split()
    res = []
    for i, m in enumerate(mots):
        if i and m in PETITS_MOTS:
            res.append(m)
            continue
        if i and re.match(r"^(d|l)['’]", m):          # « zeste d'orange » : l'élision reste en minuscule
            res.append(m[:2] + m[2:3].upper() + m[3:])
            continue
        j = next((k for k, c in enumerate(m) if c.isalpha()), None)
        if j is None:
            res.append(m)
        else:
            m = m[:j] + m[j].upper() + m[j + 1:]
            if re.match(r"^(d|l)['’]", m, re.I):       # « D'Artagnan »
                m = m[:2] + m[2:3].upper() + m[3:]
            res.append(m)
    return " ".join(res)


def etapes_methode(texte: str) -> list[str]:
    """« FRAPPER… et filtrer. COMPLÉTER avec du champagne. » → une étape par phrase."""
    phrases = re.split(r"(?<=[.!?])\s+(?=[A-ZÉÈÀÇ0-9«])", texte.strip())
    return [p.strip() for p in phrases if p.strip()]


ETIQUETTES = re.compile(r"^(ingr[ée]dients?|pr[ée]paration|m[ée]thode|recette|la recette|r[ée]alisation|"
                        r"pour \d+ (verres?|personnes?|cocktails?)|ustensiles?)\s*:?$", re.I)
EPUB_NS = "{http://www.idpf.org/2007/ops}type"
# Algorithmes d'obfuscation de polices : ce n'est pas une protection du texte
POLICES = ("http://www.idpf.org/2008/embedding", "http://ns.adobe.com/pdf/enc#RC")


# ================================================================ ouverture

def verifier_drm(contenu: bytes) -> None:
    try:
        z = zipfile.ZipFile(BytesIO(contenu))
    except zipfile.BadZipFile as e:
        raise LivreIllisible("Ce fichier n'est pas un EPUB (archive illisible).") from e
    noms = set(z.namelist())
    if "META-INF/rights.xml" in noms:
        raise LivreIllisible("Ce livre est protégé par DRM : il ne peut pas être lu.")
    if "META-INF/encryption.xml" in noms:
        xml = z.read("META-INF/encryption.xml").decode("utf-8", "replace")
        algos = re.findall(r'Algorithm="([^"]+)"', xml)
        if any(a not in POLICES for a in algos if "EncryptionMethod" in xml):
            raise LivreIllisible("Ce livre est protégé par DRM : il ne peut pas être lu.")


def _texte(el) -> str:
    return re.sub(r"\s+", " ", el.text_content() or "").strip()


def _est_repere(el) -> bool:
    types = (el.get(EPUB_NS) or el.get("epub:type") or "") + " " + (el.get("role") or "")
    return "pagebreak" in types


def _numero_repere(el) -> str:
    return (el.get("title") or _texte(el) or el.get("aria-label") or el.get("id") or "").replace("page-", "").strip()


def _blocs_document(contenu: bytes, chemin_doc: str) -> list[Bloc]:
    try:
        racine = lhtml.fromstring(contenu)
    except (etree.ParserError, ValueError):
        return []
    corps = racine.find(".//body")
    if corps is None:
        corps = racine
    dossier = posixpath.dirname(chemin_doc)
    blocs: list[Bloc] = []

    def image(el):
        src = el.get("src") or el.get("{http://www.w3.org/1999/xlink}href") or el.get("href") or ""
        if src and not src.startswith("data:"):
            blocs.append(Bloc("image", source=posixpath.normpath(posixpath.join(dossier, src))))

    def parcourir(el, dans_ol=False):
        if not isinstance(el.tag, str):
            return
        tag = el.tag.split("}")[-1].lower()
        if _est_repere(el):
            blocs.append(Bloc("page", _numero_repere(el)))
            return
        if tag in ("img", "image"):
            image(el)
            return
        if tag in ("script", "style", "nav"):
            return
        classes = (el.get("class") or "").split()
        if tag == "p" and "page-originale" in classes:   # repère visible de Scriptorium : jamais du texte
            return
        if tag in TITRES:
            t = _texte(el)
            if t:
                blocs.append(Bloc("titre", t, TITRES[tag]))
            for r in el.iter():
                if isinstance(r.tag, str) and _est_repere(r):
                    blocs.append(Bloc("page", _numero_repere(r)))
            return
        if tag in ("p", "li", "dd", "dt", "figcaption", "div") and not any(
                isinstance(e.tag, str) and e.tag.split("}")[-1].lower() in ("p", "li", "ul", "ol", "div", "table", "h1", "h2", "h3", "h4")
                for e in el.iterdescendants()):
            for i in el.iter("img", "image"):
                image(i)
            reperes = [r for r in el.iter() if isinstance(r.tag, str) and _est_repere(r)]
            for br in el.iter("br"):
                br.tail = "\n" + (br.tail or "")
            for r in reperes:            # le numéro du repère ne doit pas entrer dans le texte
                r.text = ""
            morceaux = [re.sub(r"\s+", " ", m).strip() for m in (el.text_content() or "").split("\n")]
            sorte = ("li_ol" if dans_ol else "li_ul") if tag == "li" else "para"
            for m in morceaux:
                if m:
                    blocs.append(Bloc(sorte, m))
            for r in reperes:
                blocs.append(Bloc("page", _numero_repere(r)))
            return
        for enfant in el:
            parcourir(enfant, dans_ol=(tag == "ol") or (dans_ol and tag != "ul"))

    parcourir(corps)
    return blocs


def lire_livre(contenu: bytes) -> tuple[str, str, list[Bloc], dict[str, bytes]]:
    """Titre, auteur, blocs dans l'ordre de lecture, et images (chemin → octets)."""
    verifier_drm(contenu)
    z = zipfile.ZipFile(BytesIO(contenu))
    try:
        conteneur = etree.fromstring(z.read("META-INF/container.xml"))
        opf_chemin = conteneur.find(".//{*}rootfile").get("full-path")
        opf = etree.fromstring(z.read(opf_chemin))
    except (KeyError, etree.XMLSyntaxError, AttributeError) as e:
        raise LivreIllisible("Ce fichier n'est pas un EPUB lisible (paquet introuvable).") from e
    base = posixpath.dirname(opf_chemin)
    titre = (opf.findtext(".//{http://purl.org/dc/elements/1.1/}title") or "Livre sans titre").strip()
    auteur = (opf.findtext(".//{http://purl.org/dc/elements/1.1/}creator") or "").strip()
    manifeste = {i.get("id"): (posixpath.normpath(posixpath.join(base, i.get("href"))), i.get("media-type") or "", i.get("properties") or "")
                 for i in opf.iter("{*}item")}
    blocs: list[Bloc] = []
    for ref in opf.iter("{*}itemref"):
        chemin, type_, props = manifeste.get(ref.get("idref"), ("", "", ""))
        if not chemin or "nav" in props.split() or "html" not in type_:
            continue
        try:
            blocs.extend(_blocs_document(z.read(chemin), chemin))
        except KeyError:
            continue
    images = {n: z.read(n) for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))}
    return titre, auteur, blocs, images


# ================================================================ découpage

def _est_ligne_ingredient(b: Bloc, arbre: Arbre, dans_suite: bool) -> bool:
    if b.sorte not in ("para", "li_ul", "li_ol"):
        return False
    t = b.texte
    if ETIQUETTES.match(t) or rubrique(t) or NOTE.match(t):
        return False
    if commence_par_quantite(t):
        return len(t) < 120
    if b.sorte == "li_ul" and len(t) < 70:
        return True
    # « Eau gazeuse », « Glace pilée » : sans quantité, seulement au milieu d'une suite d'ingrédients
    return dans_suite and len(t) <= 45 and not t.endswith(".") and arbre.trouver(lire_ligne(t).nom) is not None


ORIGINE = re.compile(
    r"(?i:\b(?:cr[ée]{2}e?s?|invent[ée]e?s?|n[ée]e?|imagin[ée]e?s?|mis au point|servie? pour la premi[èe]re fois))"
    r"(?:[^.]{0,80}?)\b(?:à|au|aux|en)\s+([A-ZÉÈÀ][\w'’\-]+(?:\s+(?:[A-ZÉÈÀ][\w'’\-]+|de|du|des|d'))*)", re.U)


def origine_ecrite(texte: str, rubrique_origine: str = "") -> list[str]:
    """Noms de lieux possibles pour la création, dans l'ordre où les essayer (vérifiés ensuite contre les lieux connus) :
    d'abord les parenthèses de la rubrique « ORIGINE » (« au Purple Bar (Londres, Angleterre) » → Londres, puis Angleterre),
    puis ce qui suit « créé à / inventé au … », dans la rubrique puis dans le chapeau ou la préparation."""
    noms = []
    for groupe in re.findall(r"\(([^()]{2,80})\)", rubrique_origine or ""):
        noms += [x.strip(" .") for x in groupe.split(",") if x.strip(" .")]
    for t in (rubrique_origine, texte):
        noms += [m.group(1).strip(" .,") for m in ORIGINE.finditer(t or "")]
    return noms


CONSEIL_MIN = 200          # caractères de texte au moins : écarte les encadrés répétés (« Appréciation des cocktails »)
PREFIXE_CONSEIL = re.compile(r"^conseils? du barman\s*(?:[-–:]\s*|(?:pour|sur)\s+)(?:les |le |la |l['’])?", re.I)
THEMES = [                 # (thème, mots cherchés dans le titre puis dans le début du texte)
    ("Verres", r"verres?\b|verrerie|coupe|flûte|tumbler|highball|old[- ]fashioned"),
    ("Matériel", r"matériel|ustensiles?|shaker boston|passoire|jigger|doseur|mesures?\b|doses?\b|cuill[eè]res?"),
    ("Techniques", r"technique|frapper|remuer|filtr|mélang|rolling|pilon|mixer|superpos|étages|shake|flamb|throwing|dilution"),
    ("Glace", r"glace|glaçons?"),
    ("Ingrédients", r"sirops?|jus|bitters?|amers?|liqueurs?|spiritueux|garnitures?|décor|sucre|œufs?|agrumes?"),
]


def titre_conseil(titre: str) -> str:
    """« CONSEIL DU BARMAN POUR LA GLACE » → « Glace » ; « LES VERRES » → « Les verres »."""
    t = PREFIXE_CONSEIL.sub("", titre.strip()) or titre.strip()
    lettres = [c for c in t if c.isalpha()]
    if lettres and all(c.isupper() for c in lettres):
        t = t.lower()
    return t[:1].upper() + t[1:]


def theme_conseil(titre: str, contenu: list[dict]) -> str:
    debut = " ".join(c["texte"] for c in contenu)[:400]
    for texte in (titre, debut):
        for nom, motif in THEMES:
            if re.search(motif, texte, re.I):
                return nom
    return "Autres"


def decouper(blocs: list[Bloc], arbre: Arbre) -> tuple[list[RecetteLue], bool]:
    recettes, a_reperes, _ = decouper_tout(blocs, arbre)
    return recettes, a_reperes


SANS_NOM = "Sans nom"


def _nom_au_dessus(sortie: list[Bloc]) -> int | None:
    """Le nom d'une recette au-dessus de sa note : un titre, ou un court paragraphe en capitales. Entre les deux, on
    passe les repères de page, les images et un seul petit paragraphe (« O-E » du scan, « (RECETTE … [1939]) »)."""
    petits = 0
    for i in range(len(sortie) - 1, max(-1, len(sortie) - 8), -1):
        x = sortie[i]
        if x.sorte in ("page", "image"):
            continue
        if x.sorte == "titre":
            return i
        texte = x.texte.strip()
        lettres = [c for c in texte if c.isalpha()]
        if x.sorte == "para" and 3 <= len(lettres) and len(texte) <= 60 and all(c.isupper() for c in lettres) \
                and not rubrique(texte) and not texte.startswith("("):
            return i
        if x.sorte == "para" and len(texte) <= 40 and petits == 0:
            petits += 1
            continue
        return None
    return None


def sans_faux_titres(blocs: list[Bloc]) -> list[Bloc]:
    """Certains livres mettent sous le nom du cocktail des titres sans lettre : la note (« ★★★★☆ ») et un « 0 ».
    Pris pour des titres, ils remplaçaient le nom de la recette.
    - la note juste sous un nom (seuls des repères de page entre les deux) redevient un paragraphe, lu comme note ;
    - une note sans nom au-dessus marque quand même le début d'une recette (sinon elle se fondrait dans la précédente) :
      elle devient un titre « Sans nom », et la recette part dans À traiter ;
    - les autres titres sans lettre (« 0 ») sont écartés."""
    sortie: list[Bloc] = []
    for b in blocs:
        if b.sorte == "titre" and not any(c.isalpha() for c in b.texte):
            if NOTE.match(b.texte.strip()):
                nom = _nom_au_dessus(sortie)
                if nom is None:
                    sortie.append(Bloc("titre", SANS_NOM, niveau=b.niveau))
                elif sortie[nom].sorte != "titre":       # « JUNGLE JUICE » écrit comme un paragraphe : c'est le nom
                    sortie[nom] = Bloc("titre", sortie[nom].texte, niveau=b.niveau)
                sortie.append(Bloc("para", b.texte.strip()))
            continue
        sortie.append(b)
    return sortie


def decouper_tout(blocs: list[Bloc], arbre: Arbre) -> tuple[list[RecetteLue], bool, list[ConseilLu]]:
    blocs = recoller(sans_faux_titres(blocs))
    a_reperes = any(b.sorte == "page" for b in blocs)
    page = None
    pages_avant: list[str | None] = []      # page courante avant chaque bloc
    for b in blocs:
        if b.sorte == "page" and b.texte:
            page = b.texte
        pages_avant.append(page)
    titres = [i for i, b in enumerate(blocs) if b.sorte == "titre"] + [len(blocs)]
    recettes: list[RecetteLue] = []
    conseils: list[ConseilLu] = []
    en_cours: ConseilLu | None = None       # passage hors recette en train d'être lu (ses sous-titres s'y ajoutent)
    for k in range(len(titres) - 1):
        debut, fin = titres[k], titres[k + 1]
        section = blocs[debut + 1:fin]
        idx_ing = []
        for j, b in enumerate(section):
            if _est_ligne_ingredient(b, arbre, dans_suite=bool(idx_ing) and idx_ing[-1] >= j - 2):
                idx_ing.append(j)
        if not idx_ing or not any(commence_par_quantite(section[j].texte) for j in idx_ing):
            # pas une recette : titre de chapitre, introduction, conseil du barman, page sur les verres…
            contenu = [{"sorte": b.sorte, "texte": b.texte.strip()} for b in section
                       if b.sorte in ("para", "li_ul", "li_ol") and b.texte.strip() and not NOTE.match(b.texte)
                       and not b.texte.lstrip().startswith(("★", "☆"))]
            if any(rubrique(c["texte"]) for c in contenu) or blocs[debut].texte.strip().endswith(":"):
                en_cours = None                # recette mal lue ou morceau de fiche : laissé de côté
                continue
            textes = [debut + 1 + j for j, b in enumerate(section) if b.sorte in ("para", "li_ul", "li_ol")]
            page_fin = pages_avant[textes[-1]] if (a_reperes and textes) else None
            niveau = blocs[debut].niveau
            if en_cours and niveau > en_cours.niveau and not PREFIXE_CONSEIL.match(blocs[debut].texte.strip()):
                en_cours.contenu += [{"sorte": "sous_titre", "texte": titre_conseil(blocs[debut].texte)}, *contenu]
                en_cours.page_fin = page_fin or en_cours.page_fin
            else:
                en_cours = ConseilLu(titre=titre_conseil(blocs[debut].texte), theme="", contenu=contenu,
                                     page_debut=pages_avant[debut] if a_reperes else None, page_fin=page_fin, niveau=niveau)
                conseils.append(en_cours)
            continue
        en_cours = None
        premier, dernier = idx_ing[0], idx_ing[-1]
        # Rubriques (« VERRE : », « MÉTHODE : », « MON AVIS : »…) et note en étoiles, où qu'elles soient dans la fiche
        infos: dict[str, str] = {}
        note = None
        rangees: set[int] = set()
        for j, b in enumerate(section):
            if b.sorte not in ("para", "li_ul", "li_ol"):
                continue
            r = rubrique(b.texte)
            if r:
                infos[r[0]] = (infos.get(r[0], "") + " " + r[1]).strip()
                rangees.add(j)
            elif NOTE.match(b.texte):
                note = b.texte.count("★") or b.texte.count("*") or None
                rangees.add(j)
        libre = lambda j, b: (b.sorte in ("para", "li_ul", "li_ol") and j not in rangees and not ETIQUETTES.match(b.texte)   # noqa: E731
                              and sum(c.isalpha() for c in b.texte) >= 3)      # « O-E » : parasite du scan
        chapeau = [b.texte for j, b in enumerate(section[:premier]) if libre(j, b)]
        lignes = [section[j].texte for j in idx_ing]
        if "Méthode" in infos:
            etapes = etapes_methode(infos.pop("Méthode"))
        else:
            etapes = [b.texte for j, b in enumerate(section) if j > dernier and libre(j, b)]
        # Lignes de texte glissées entre les ingrédients (« 3 physalis » sans quantité reconnue…) : gardées dans le chapeau
        chapeau += [section[j].texte for j in range(premier, dernier) if j not in idx_ing and section[j].sorte == "para" and libre(j, section[j])]
        # Fin de la recette : son dernier bloc de texte (la page des images ou des titres suivants ne compte pas)
        textes = [debut + 1 + j for j, b in enumerate(section) if b.sorte in ("para", "li_ul", "li_ol") and not NOTE.match(b.texte)]
        dernier_bloc = textes[-1] if textes else debut
        page_debut = pages_avant[debut] if a_reperes else None
        page_fin = pages_avant[dernier_bloc] if a_reperes else None
        images = [b.source for b in section if b.sorte == "image"]
        if not images and debut > 0 and blocs[debut - 1].sorte == "image":
            images = [blocs[debut - 1].source]
        raisons, confiance = [], 1.0
        titre = titre_propre(blocs[debut].texte)
        if titre == SANS_NOM:
            titre = f"{SANS_NOM}, p. {page_debut}" if page_debut else SANS_NOM
            confiance -= 0.5
            raisons.append("pas de nom dans le livre")
        if len(lignes) < 2:
            confiance -= 0.4
            raisons.append("une seule ligne d'ingrédient lue")
        if not etapes:
            confiance -= 0.3
            raisons.append("pas de préparation trouvée")
        illisibles = [l for l in lignes if not commence_par_quantite(l) and rapprocher(arbre, lire_ligne(l)) is None]
        if illisibles:
            confiance -= min(0.3, 0.15 * len(illisibles))
            raisons.append(f"{len(illisibles)} ligne(s) d'ingrédient sans quantité ni ingrédient reconnu")
        original = "\n".join([blocs[debut].texte, *[b.texte for b in section if b.sorte != "page" and b.texte]])
        recettes.append(RecetteLue(
            titre=titre, lignes=lignes, etapes=etapes, chapeau=" ".join(chapeau).strip(),
            page_debut=page_debut, page_fin=page_fin if page_fin != page_debut else None,
            image=images[0] if images else None, texte_original=original, confiance=round(max(confiance, 0), 2),
            raisons=raisons, infos=infos, note=note))
    # Conseils gardés : assez de texte, et pas deux fois le même encadré
    gardes: list[ConseilLu] = []
    par_titre: dict[str, int] = {}
    for c in conseils:
        deja, propre = set(), []
        for x in c.contenu:                    # une même ligne répétée (encadré de chaque page) n'est gardée qu'une fois
            cle_x = (x["sorte"], normaliser(x["texte"]))
            if cle_x not in deja:
                deja.add(cle_x)
                propre.append(x)
        c.contenu = propre
        texte = " ".join(x["texte"] for x in c.contenu if x["sorte"] != "sous_titre")
        if len(texte) < CONSEIL_MIN or not any(len(x["texte"]) >= 120 for x in c.contenu):
            continue                           # trop court, ou une simple légende (« EXCELLENT », « BON »…)
        if c.page_fin == c.page_debut:
            c.page_fin = None
        cle = normaliser(c.titre)
        if cle in par_titre:                   # même titre ailleurs dans le livre : on garde le plus complet
            i = par_titre[cle]
            ancien = sum(len(x["texte"]) for x in gardes[i].contenu)
            if len(texte) > ancien:
                c.theme = theme_conseil(c.titre, c.contenu)
                gardes[i] = c
            continue
        par_titre[cle] = len(gardes)
        c.theme = theme_conseil(c.titre, c.contenu)
        if c.page_fin == c.page_debut:
            c.page_fin = None
        gardes.append(c)
    return recettes, a_reperes, gardes


def lire(contenu: bytes, arbre: Arbre) -> LivreLu:
    titre, auteur, blocs, images = lire_livre(contenu)
    recettes, a_reperes, conseils = decouper_tout(blocs, arbre)
    return LivreLu(titre, auteur, a_reperes, recettes, images, conseils)


def texte_pages(r: RecetteLue | dict) -> str:
    """« p. 42 » ou « p. 42-43 » ; vide sans page."""
    debut = r.page_debut if isinstance(r, RecetteLue) else r.get("page_debut")
    fin = r.page_fin if isinstance(r, RecetteLue) else r.get("page_fin")
    if not debut:
        return ""
    return f"p. {debut}-{fin}" if fin and fin != debut else f"p. {debut}"


def nom_normalise(texte: str) -> str:
    return normaliser(texte)


def ecrire_photo(octets: bytes, chemin: Path, cote: int = 640) -> bool:
    """Vignette WebP carrée (recadrée au centre). Faux si l'image est illisible."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(BytesIO(octets))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, (cote, cote), method=Image.Resampling.LANCZOS)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        im.save(chemin, "WEBP", quality=82)
        return True
    except Exception:   # image abîmée ou format inconnu : la recette garde la vignette sobre
        return False
