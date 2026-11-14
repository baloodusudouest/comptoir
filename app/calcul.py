"""Ce que le bar permet : faisables, « il manque 1 ou 2 », et la bouteille qui en débloque le plus.

Règle : une ligne qui demande une famille (« rhum ») est satisfaite par la famille ou n'importe laquelle
de ses variantes ; une ligne qui demande une variante (« rhum blanc ») exige cette variante. Les
équivalences validées valent dans les deux sens. Les ingrédients « toujours là » (eau, glace, sucre, sel)
sont toujours présents. Une ligne facultative (garniture) ne compte pas. Un ingrédient inconnu manque.
"""
from __future__ import annotations

from collections import Counter

from .ingredients import Arbre


class Bar:
    def __init__(self, arbre: Arbre, presents: set[str], equivalences: list[tuple[str, str]]):
        self.arbre = arbre
        self.presents = set(presents) | {i for i, n in arbre.noeuds.items() if n.toujours_la}
        self.equiv: dict[str, set[str]] = {}
        for a, b in equivalences:
            self.equiv.setdefault(a, set()).add(b)
            self.equiv.setdefault(b, set()).add(a)

    def acceptes(self, ingredient: str) -> set[str]:
        """Ingrédients du bar qui satisfont une ligne demandant « ingredient »."""
        n = self.arbre.noeuds.get(ingredient)
        if not n:
            return set()
        ok = {ingredient}
        if n.niveau != "variante":
            ok |= self.arbre.descendants(ingredient)
        for e in list(ok):
            ok |= self.equiv.get(e, set())
        return ok

    def satisfait(self, ingredient: str | None, presents: set[str] | None = None) -> bool:
        if not ingredient:
            return False
        return bool(self.acceptes(ingredient) & (self.presents if presents is None else presents))


def nom_dans_phrase(l: dict) -> str:
    """« Il manque eau gazeuse » : la majuscule d'une ligne sans quantité (« Eau gazeuse ») n'est que celle du début de ligne.
    Un nom écrit avec sa majuscule au milieu d'une ligne (« 3 cl de Campari ») la garde."""
    nom = l["nom"] or l["texte"]
    if l.get("quantite") is None and l["texte"].startswith(nom) and len(nom) > 1 and nom[1:2].islower():
        return nom[0].lower() + nom[1:]
    return nom


def manquants(bar: Bar, lignes: list[dict]) -> list[dict]:
    """Lignes non facultatives que le bar ne satisfait pas."""
    return [l for l in lignes if not l["facultatif"] and not bar.satisfait(l["ingredient"])]


def calculer(bar: Bar, recettes: dict[int, list[dict]]) -> dict:
    """recettes : id → lignes (ingredient, facultatif, nom). Rend faisables, presque (1 ou 2 manquants) et déblocages."""
    faisables, presque = [], []
    for rid, lignes in recettes.items():
        m = manquants(bar, lignes)
        if not m:
            faisables.append(rid)
        elif len(m) <= 2:
            presque.append({"recette": rid, "manque": [{"ingredient": l["ingredient"], "nom": nom_dans_phrase(l)} for l in m]})
    # Bouteille qui débloque le plus : pour chaque ingrédient absent, les recettes qui deviennent faisables s'il arrive.
    gains: Counter = Counter()
    for p in presque:
        ids = {x["ingredient"] for x in p["manque"]}
        if len(ids) == 1 and None not in ids:
            gains[next(iter(ids))] += 1
    debloque = [{"ingredient": i, "nom": bar.arbre.noeuds[i].nom, "recettes": n} for i, n in gains.most_common(3) if i in bar.arbre.noeuds]
    return {"faisables": faisables, "presque": presque, "debloque": debloque}
