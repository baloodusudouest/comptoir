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


@dataclass
class LivreLu:
    titre: str
    auteur: str
    a_reperes_page: bool
    recettes: list[RecetteLue]
    images: dict[str, bytes]


TITRES = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
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
    if ETIQUETTES.match(t):
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


def origine_ecrite(texte: str) -> list[str]:
    """Noms de lieux après « créé à / inventé au … » dans le chapeau ou la préparation (vérifiés ensuite contre les lieux connus)."""
    return [m.group(1).strip(" .,") for m in ORIGINE.finditer(texte or "")]


def decouper(blocs: list[Bloc], arbre: Arbre) -> tuple[list[RecetteLue], bool]:
    a_reperes = any(b.sorte == "page" for b in blocs)
    page = None
    pages_avant: list[str | None] = []      # page courante avant chaque bloc
    for b in blocs:
        if b.sorte == "page" and b.texte:
            page = b.texte
        pages_avant.append(page)
    titres = [i for i, b in enumerate(blocs) if b.sorte == "titre"] + [len(blocs)]
    recettes: list[RecetteLue] = []
    for k in range(len(titres) - 1):
        debut, fin = titres[k], titres[k + 1]
        section = blocs[debut + 1:fin]
        idx_ing = []
        for j, b in enumerate(section):
            if _est_ligne_ingredient(b, arbre, dans_suite=bool(idx_ing) and idx_ing[-1] >= j - 2):
                idx_ing.append(j)
        if not idx_ing or not any(commence_par_quantite(section[j].texte) for j in idx_ing):
            continue                       # pas une recette (titre de chapitre, introduction…)
        premier, dernier = idx_ing[0], idx_ing[-1]
        chapeau = [b.texte for b in section[:premier] if b.sorte in ("para", "li_ul", "li_ol") and not ETIQUETTES.match(b.texte)]
        lignes = [section[j].texte for j in idx_ing]
        etapes = [b.texte for b in section[dernier + 1:] if b.sorte in ("para", "li_ol", "li_ul") and not ETIQUETTES.match(b.texte)]
        # Lignes de texte glissées entre les ingrédients (« Verre : coupe ») : gardées dans le chapeau
        chapeau += [section[j].texte for j in range(premier, dernier) if j not in idx_ing
                    and section[j].sorte in ("para",) and not ETIQUETTES.match(section[j].texte)]
        # Fin de la recette : son dernier bloc de texte (la page des images ou des titres suivants ne compte pas)
        textes = [debut + 1 + j for j, b in enumerate(section) if b.sorte in ("para", "li_ul", "li_ol")]
        dernier_bloc = textes[-1] if textes else debut
        page_debut = pages_avant[debut] if a_reperes else None
        page_fin = pages_avant[dernier_bloc] if a_reperes else None
        images = [b.source for b in section if b.sorte == "image"]
        if not images and debut > 0 and blocs[debut - 1].sorte == "image":
            images = [blocs[debut - 1].source]
        raisons, confiance = [], 1.0
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
            titre=blocs[debut].texte, lignes=lignes, etapes=etapes, chapeau=" ".join(chapeau).strip(),
            page_debut=page_debut, page_fin=page_fin if page_fin != page_debut else None,
            image=images[0] if images else None, texte_original=original, confiance=round(max(confiance, 0), 2),
            raisons=raisons))
    return recettes, a_reperes


def lire(contenu: bytes, arbre: Arbre) -> LivreLu:
    titre, auteur, blocs, images = lire_livre(contenu)
    recettes, a_reperes = decouper(blocs, arbre)
    return LivreLu(titre, auteur, a_reperes, recettes, images)


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
