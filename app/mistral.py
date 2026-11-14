"""Une recette mal découpée, relue par Mistral, sur un clic. Tout l'appel tient dans cette fonction.

Mistral reçoit le texte brut de la recette (rien d'autre : ni le livre, ni le bar) et rend un JSON.
Le résultat n'est jamais enregistré seul : il est montré à côté de l'original, et validé à la main.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

CONSIGNE = """Tu reçois le texte d'une recette de cocktail extraite d'un livre en français, parfois mal découpée.
Rends uniquement un objet JSON, sans commentaire, de la forme :
{"titre": "...", "ingredients": ["4 cl de rhum blanc", "..."], "etapes": ["...", "..."], "chapeau": "...", "origine": "lieu de création s'il est écrit, sinon vide"}
Règles : recopie les mots du texte, n'invente aucun ingrédient ni aucune quantité, garde les unités telles qu'écrites.
Une ligne d'ingrédient par ingrédient. Si le texte n'est pas une recette, rends {"titre": "", "ingredients": [], "etapes": []}."""


@dataclass
class Relecture:
    titre: str
    ingredients: list[str]
    etapes: list[str]
    chapeau: str
    origine: str


class ErreurMistral(Exception):
    pass


def relire_recette(texte: str, cle: str, url: str, modele: str, client: httpx.Client | None = None) -> Relecture:
    if not cle:
        raise ErreurMistral("Aucune clé Mistral réglée dans la stack (COMPTOIR_MISTRAL_CLE).")
    propre = client or httpx.Client(timeout=60)
    try:
        r = propre.post(url, headers={"Authorization": f"Bearer {cle}"}, json={
            "model": modele, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": CONSIGNE}, {"role": "user", "content": texte[:6000]}]})
    except httpx.HTTPError as e:
        raise ErreurMistral(f"Mistral ne répond pas ({e.__class__.__name__}).") from e
    finally:
        if client is None:
            propre.close()
    if r.status_code in (401, 403):
        raise ErreurMistral("Mistral refuse la clé (COMPTOIR_MISTRAL_CLE) : vérifier qu'elle est valable.")
    if r.status_code == 429:
        raise ErreurMistral("Mistral demande d'attendre (trop de demandes) : réessayer dans une minute.")
    if r.status_code >= 400:
        raise ErreurMistral(f"Mistral a répondu {r.status_code}.")
    try:
        contenu = r.json()["choices"][0]["message"]["content"]
        d = json.loads(contenu)
    except (KeyError, IndexError, ValueError, TypeError) as e:
        raise ErreurMistral("La réponse de Mistral n'est pas un JSON lisible.") from e
    liste = lambda x: [str(v).strip() for v in (x or []) if str(v).strip()]   # noqa: E731
    return Relecture(str(d.get("titre") or "").strip(), liste(d.get("ingredients")), liste(d.get("etapes")),
                     str(d.get("chapeau") or "").strip(), str(d.get("origine") or "").strip())
