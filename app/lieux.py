"""Lieux : ceux qu'évoque le nom d'un cocktail (par règles) et celui de sa création (livre, puis Wikidata).

Les lieux connus sont embarqués (donnees/lieux.yaml). Une forme « ambiguë » (Manhattan, Champagne, Martinez…)
ne pose jamais le lieu seule : elle devient une question dans « À traiter ».
La recherche dans Wikidata ne fait que lire ; elle est coupée par COMPTOIR_RECHERCHE_WEB=non.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml

from .ingredients import normaliser

FICHIER = Path(__file__).parent / "donnees" / "lieux.yaml"


@dataclass
class Lieu:
    id: str
    nom: str
    type: str                 # pays, region, ville
    pays: str                 # identifiant du pays (lui-même pour un pays)
    parent: str | None        # région ou pays au-dessus (ville → région si connue, sinon pays ; quartier → ville)
    lat: float
    lon: float
    iso: int | None = None


class Lieux:
    def __init__(self):
        donnees = yaml.safe_load(FICHIER.read_text(encoding="utf-8"))
        self.lieux: dict[str, Lieu] = {}
        self.formes: dict[str, tuple[str, bool]] = {}     # forme normalisée → (lieu, ambiguë)
        for p in donnees["pays"]:
            self._ajouter(Lieu(p["id"], p["nom"], "pays", p["id"], None, p["lat"], p["lon"], p.get("iso")), p, False)
        for r in donnees["regions"]:
            self._ajouter(Lieu(r["id"], r["nom"], "region", r["pays"], r["pays"], r["lat"], r["lon"]), r, bool(r.get("ambigu")))
        for v in donnees["villes"]:
            parent = v.get("ville") or v.get("region") or v["pays"]
            self._ajouter(Lieu(v["id"], v["nom"], "ville", v["pays"], parent, v["lat"], v["lon"]), v, bool(v.get("ambigu")))
        self._max_mots = max(len(f.split()) for f in self.formes)

    def _ajouter(self, lieu: Lieu, brut: dict, ambigu: bool) -> None:
        self.lieux[lieu.id] = lieu
        for f in [lieu.nom, *brut.get("formes", [])]:
            cle = normaliser(f)
            if cle and (cle not in self.formes or not ambigu):
                self.formes[cle] = (lieu.id, ambigu and cle in [normaliser(x) for x in brut.get("formes", [])] or ambigu)

    def chemin(self, id_: str) -> list[str]:
        """Du pays au lieu : ["États-Unis", "New York", "Manhattan"]."""
        noms, l = [], self.lieux.get(id_)
        while l:
            noms.insert(0, l.nom)
            l = self.lieux.get(l.parent) if l.parent else None
        return noms

    def ancetres(self, id_: str) -> list[str]:
        ids, l = [], self.lieux.get(id_)
        while l:
            ids.append(l.id)
            l = self.lieux.get(l.parent) if l.parent else None
        return ids

    def trouver_nom(self, texte: str) -> str | None:
        """Lieu dont un nom ou une forme correspond exactement au texte (« La Havane », « Cuba »)."""
        r = self.formes.get(normaliser(texte))
        return r[0] if r else None

    def evoques(self, titre: str) -> tuple[list[str], list[str]]:
        """Lieux évoqués par un nom de cocktail : (sûrs, ambigus). Les groupes de mots les plus longs d'abord."""
        mots = normaliser(titre).replace("-", " ").split()
        surs, ambigus, pris = [], [], set()
        for n in range(min(self._max_mots, len(mots)), 0, -1):
            for i in range(len(mots) - n + 1):
                if any(j in pris for j in range(i, i + n)):
                    continue
                for cle in (" ".join(mots[i:i + n]), "-".join(mots[i:i + n])):
                    if cle in self.formes:
                        lieu, ambigu = self.formes[cle]
                        (ambigus if ambigu else surs).append(lieu)
                        pris.update(range(i, i + n))
                        break
        return list(dict.fromkeys(surs)), [a for a in dict.fromkeys(ambigus) if a not in surs]


# ================================================================ Wikidata (lecture seule)

@dataclass
class Candidat:
    lieu: str | None          # lieu connu de Comptoir, ou None si le nom rendu n'est pas dans la liste
    libelle: str              # tel que Wikidata le nomme
    element: str              # identifiant Wikidata du cocktail (Q…)
    description: str


def chercher_origine(titre: str, lieux: Lieux, url: str, client: httpx.Client | None = None) -> list[Candidat]:
    """Cherche le cocktail dans Wikidata et lit son pays d'origine (P495) ou son lieu de création (P1071).
    Ne retient que les éléments décrits comme un cocktail. Lecture seule : uniquement des GET."""
    propre = client or httpx.Client(timeout=15, headers={"User-Agent": "Comptoir (appli maison auto-hébergée)"})
    try:
        r = propre.get(url, params={"action": "wbsearchentities", "search": titre, "language": "fr", "uselang": "fr",
                                    "type": "item", "limit": 7, "format": "json"})
        r.raise_for_status()
        trouves = [t for t in r.json().get("search", []) if "cocktail" in (t.get("description") or "").lower()]
        if not trouves:
            return []
        ids = "|".join(t["id"] for t in trouves)
        e = propre.get(url, params={"action": "wbgetentities", "ids": ids, "props": "claims|labels|descriptions",
                                    "languages": "fr|en", "format": "json"})
        e.raise_for_status()
        entites = e.json().get("entities", {})
        lieux_q: dict[str, str] = {}
        par_cocktail: dict[str, list[str]] = {}
        for qid, ent in entites.items():
            valeurs = []
            for prop in ("P1071", "P495"):
                for c in ent.get("claims", {}).get(prop, []):
                    v = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                    if isinstance(v, dict) and v.get("id"):
                        valeurs.append(v["id"])
            par_cocktail[qid] = valeurs
            lieux_q.update({v: "" for v in valeurs})
        if lieux_q:
            n = propre.get(url, params={"action": "wbgetentities", "ids": "|".join(lieux_q), "props": "labels",
                                        "languages": "fr|en", "format": "json"})
            n.raise_for_status()
            for qid, ent in n.json().get("entities", {}).items():
                lab = ent.get("labels", {})
                lieux_q[qid] = (lab.get("fr") or lab.get("en") or {}).get("value", "")
        candidats = []
        for t in trouves:
            for v in par_cocktail.get(t["id"], []):
                libelle = lieux_q.get(v, "")
                if libelle:
                    candidats.append(Candidat(lieux.trouver_nom(libelle), libelle, t["id"], t.get("description", "")))
        return candidats
    finally:
        if client is None:
            propre.close()


def candidats_json(c: list[Candidat]) -> str:
    return json.dumps([c_.__dict__ for c_ in c], ensure_ascii=False)


def nettoyer_titre(titre: str) -> str:
    """« Daïquiri de la maison » se cherche « Daïquiri » : on retire les compléments courants."""
    return re.split(r"\s+(?:de la maison|maison|à ma façon|revisité|du chef)\b", titre, flags=re.I)[0].strip()
