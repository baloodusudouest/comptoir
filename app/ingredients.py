"""Arbre des ingrédients et lecture d'une ligne d'ingrédient (« 4 cl de rhum blanc »).

L'arbre livré (donnees/ingredients.yaml) est complété par les ingrédients créés dans l'appli et par les
noms rattachés à la main (table alias). Le rapprochement d'un nom lu : alias exact, puis l'alias le plus
long contenu dans le nom (mots entiers), puis une proposition par ressemblance (jamais posée seule).
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import yaml

FICHIER = Path(__file__).parent / "donnees" / "ingredients.yaml"


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, ligatures défaites, ponctuation en espaces."""
    t = (texte or "").replace("œ", "oe").replace("Œ", "oe").replace("æ", "ae").replace("’", "'")
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9' -]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Noeud:
    id: str
    nom: str
    niveau: str                  # categorie, famille, variante
    parent: str | None
    categorie: str
    sans_alcool: bool = False
    toujours_la: bool = False
    frais: bool = False
    garniture: bool = False
    enfants: list[str] = field(default_factory=list)


# Premier mot d'un nom écrit dans un livre → catégories où l'ingrédient peut se trouver. En français, ce premier mot dit
# ce qu'est le produit : « liqueur de pomme » est une liqueur, « soda au gingembre » un soda, « jus de pomme » un jus.
TETES = {
    "liqueur": {"liqueurs"}, "liqueurs": {"liqueurs"}, "creme": {"liqueurs"}, "cremes": {"liqueurs"},
    "sirop": {"sirops"}, "sirops": {"sirops"}, "cordial": {"sirops", "liqueurs"},
    "soda": {"sodas"}, "sodas": {"sodas"}, "limonade": {"sodas"},
    "jus": {"jus"}, "nectar": {"jus"}, "puree": {"jus", "sirops"},
    "bitter": {"amers"}, "bitters": {"amers"}, "amer": {"amers", "liqueurs"},
    "eau-de-vie": {"spiritueux"}, "eaux-de-vie": {"spiritueux"},
    "vin": {"vins"}, "vins": {"vins"}, "biere": {"vins", "sodas"},
}


class Arbre:
    def __init__(self, ajoutes: list[dict] | None = None, alias_base: list[dict] | None = None):
        self.noeuds: dict[str, Noeud] = {}
        self.alias: dict[str, str] = {}
        for cat in yaml.safe_load(FICHIER.read_text(encoding="utf-8")):
            drap = {k: bool(cat.get(k)) for k in ("sans_alcool", "garniture")}
            self._ajouter(Noeud(cat["id"], cat["nom"], "categorie", None, cat["id"], **drap))
            for fam in cat.get("familles", []):
                self._ajouter(Noeud(fam["id"], fam["nom"], "famille", cat["id"], cat["id"],
                                    toujours_la=bool(fam.get("toujours_la")), frais=bool(fam.get("frais")), **drap),
                              fam.get("alias", []))
                for var in fam.get("variantes", []):
                    self._ajouter(Noeud(var["id"], var["nom"], "variante", fam["id"], cat["id"],
                                        toujours_la=bool(var.get("toujours_la")), frais=bool(var.get("frais")), **drap),
                                  var.get("alias", []))
        for a in ajoutes or []:
            parent = self.noeuds.get(a["parent"])
            if parent and a["id"] not in self.noeuds:
                self._ajouter(Noeud(a["id"], a["nom"], a["niveau"], parent.id, parent.categorie,
                                    sans_alcool=parent.sans_alcool, garniture=parent.garniture), [a["nom"]])
        for a in alias_base or []:
            if a["ingredient"] in self.noeuds:
                self.alias[normaliser(a["texte"])] = a["ingredient"]
        # alias triés du plus long au plus court, pour « l'alias le plus long contenu dans le nom »
        self._par_longueur = sorted(self.alias, key=len, reverse=True)

    def _ajouter(self, n: Noeud, alias: list[str] | None = None) -> None:
        self.noeuds[n.id] = n
        if n.parent:
            self.noeuds[n.parent].enfants.append(n.id)
        for a in [n.nom, *(alias or [])]:
            self.alias.setdefault(normaliser(a), n.id)

    # ------------------------------------------------------------ parcours
    def descendants(self, id_: str) -> set[str]:
        res, pile = set(), [id_]
        while pile:
            for e in self.noeuds[pile.pop()].enfants:
                res.add(e)
                pile.append(e)
        return res

    def chemin(self, id_: str) -> list[str]:
        noms, n = [], self.noeuds.get(id_)
        while n:
            noms.insert(0, n.nom)
            n = self.noeuds.get(n.parent) if n.parent else None
        return noms

    # ------------------------------------------------------------ rapprochement d'un nom lu
    def trouver(self, nom: str) -> str | None:
        n = normaliser(nom)
        if not n:
            return None
        if n in self.alias:
            return self.alias[n]
        tete = n.split()[0]
        permises = TETES.get(tete)
        for a in self._par_longueur:
            if len(a) >= 3 and re.search(rf"(^|[ ']){re.escape(a)}($| )", n):
                trouve = self.alias[a]
                # « liqueur de pomme » contient « pomme » (le jus) : refusé, car une liqueur n'est pas un jus.
                # « liqueur Galliano » contient « galliano » (une liqueur) : accepté.
                # Un nom connu qui commence par le même mot (« crème liquide », « sirop de sucre ») est accepté, mais pas ce
                # mot seul : « crème » (la crème fraîche) ne doit pas prendre « crème de fraise ».
                if permises and not (a.startswith(tete + " ") or a == n) and self.noeuds[trouve].categorie not in permises:
                    continue
                return trouve
        return None

    def proposer(self, nom: str) -> str | None:
        """Proposition par ressemblance, pour la question « rattacher à… » (jamais posée seule)."""
        proches = difflib.get_close_matches(normaliser(nom), list(self.alias), n=1, cutoff=0.85)
        return self.alias[proches[0]] if proches else None


# ================================================================ lecture d'une ligne

FRACTIONS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3"}
NOMBRES = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "demi": 0.5, "demie": 0.5, "quelques": 2}
# unité écrite → (unité gardée, facteur vers cette unité)
UNITES = [
    (r"cl|centilitres?", "cl", 1), (r"ml|millilitres?", "cl", 0.1), (r"oz|onces?", "cl", 3),
    (r"c\.? ?(?:a|à) ?s\.?|cuill[eè]r[ée]?e?s? (?:a|à) soupe|cs", "cuillère à soupe", 1),
    (r"c\.? ?(?:a|à) ?c\.?|cuill[eè]r[ée]?e?s? (?:a|à) caf[eé]|cc", "cuillère à café", 1),
    (r"cuill[eè]r[ée]?e?s? de bar|bar ?spoons?", "cuillère de bar", 1),
    (r"cuill[eè]r[ée]es?|cuill[eè]res?", "cuillère", 1), (r"shots?", "shot", 1), (r"pintes?", "pinte", 1),
    (r"traits?|dash(?:es)?|giclées?", "trait", 1), (r"gouttes?|drops?", "goutte", 1),
    (r"zestes?", "zeste", 1), (r"feuilles?", "feuille", 1), (r"brins?|branches?", "brin", 1),
    (r"tranches?|rondelles?", "tranche", 1), (r"quartiers?", "quartier", 1), (r"pinc[ée]es?", "pincée", 1),
    (r"morceaux?", "morceau", 1), (r"verres?", "verre", 1), (r"tasses?", "tasse", 1),
]
FACULTATIF = re.compile(r"pour (?:la )?d[ée]cor|d[ée]coration|garniture|facultatif|optionnel|selon le go[uû]t|pour servir", re.I)
_UNITE_RE = re.compile(r"^(" + "|".join(u for u, _, _ in UNITES) + r")\b\.?\s*", re.I)
_NOMBRE_RE = re.compile(r"^(\d+(?:[.,]\d+)?\s*(?:à|-|–)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?(?:\s+\d/\d)?)\s*", re.I)


@dataclass
class Ligne:
    texte: str
    quantite: float | None
    unite: str
    nom: str
    facultatif: bool


def _nombre(texte: str) -> float | None:
    texte = texte.replace(",", ".").strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:à|-|–)\s*(\d+(?:\.\d+)?)$", texte)
    if m:   # « 2 à 3 » : on garde le plus petit
        return float(m.group(1))
    try:
        parts = texte.split()
        return float(sum(Fraction(p.replace(" ", "")) for p in parts))
    except (ValueError, ZeroDivisionError):
        return None


def commence_par_quantite(texte: str) -> bool:
    t = texte.strip()
    for k, v in FRACTIONS.items():
        t = t.replace(k, v)
    return bool(_NOMBRE_RE.match(t) or re.match(r"^(un|une|deux|trois|quatre|cinq|six|demi|quelques)\s+\S", t, re.I)
                and _UNITE_RE.match(re.sub(r"^\S+\s+", "", t)))


def lire_ligne(texte: str) -> Ligne:
    brut = re.sub(r"^[\-–•·*]\s*", "", (texte or "").strip())
    t = brut
    for k, v in FRACTIONS.items():
        t = t.replace(k, " " + v)
    t = t.strip()
    quantite = None
    m = _NOMBRE_RE.match(t)
    if m:
        quantite = _nombre(m.group(1))
        t = t[m.end():]
    else:
        m = re.match(r"^(un|une|deux|trois|quatre|cinq|six|demi|demie|quelques)\s+", t, re.I)
        if m:
            quantite = NOMBRES[m.group(1).lower()]
            t = t[m.end():]
    unite = ""
    m = _UNITE_RE.match(t)
    if m:
        for motif, garde, facteur in UNITES:
            if re.fullmatch(motif, m.group(1), re.I):
                unite = garde
                if quantite is not None:
                    quantite = round(quantite * facteur, 2)
                break
        t = t[m.end():]
    t = re.sub(r"^(?:compl[ée]ter|allonger|remplir|top(?:per)?|finir)\s+(?:avec\s+|de\s+)?", "", t.strip(), flags=re.I)
    nom = re.sub(r"^(?:de la |de l'|de l’|de |d'|d’|du |des )", "", t.strip(), flags=re.I)
    nom = re.sub(r"\s+fra[iî]chement\s+(?:press[ée]e?s?|moulue?s?|r[âa]p[ée]e?s?)|\s+press[ée]e?s?$", "", nom, flags=re.I)
    nom = re.sub(r"\([^)]*\)", "", nom)                      # précisions entre parenthèses
    facultatif = bool(FACULTATIF.search(brut))
    nom = re.split(r",| pour | \(", nom)[0].strip(" .;:")
    return Ligne(brut, quantite, unite, nom, facultatif)


UNITES_GARNITURE = ("zeste", "tranche", "quartier", "brin", "feuille")


def rapprocher(arbre: Arbre, ligne: Ligne) -> str | None:
    """Ingrédient de l'arbre pour une ligne lue. « Un zeste d'orange » est un zeste, pas du jus d'orange :
    pour ces unités, le nom complet (unité comprise) est essayé d'abord."""
    if ligne.unite in UNITES_GARNITURE:
        for essai in (f"{ligne.unite} de {ligne.nom}", f"{ligne.unite} d'{ligne.nom}"):
            trouve = arbre.trouver(essai)
            if trouve and arbre.noeuds[trouve].garniture:
                return trouve
        repli = {"zeste": "zeste", "tranche": "rondelle", "quartier": "rondelle"}.get(ligne.unite)
        if repli and repli in arbre.noeuds:
            return repli
    return arbre.trouver(ligne.nom)
