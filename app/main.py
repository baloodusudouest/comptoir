"""Comptoir : les cocktails de la maison, depuis des livres EPUB.

Routes publiques : /health, /api/session, /api/connexion. Tout le reste demande la session.
Comptoir n'écrit chez aucun service extérieur : il lit Wikidata (origine) et, sur un clic, envoie le texte
d'une recette à Mistral. Tout ce qu'il écrit reste dans son dossier de données.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, epub, mistral
from .auth import COMMUN, DUREE, Sessions
from .base import Base, maintenant
from .calcul import Bar, calculer, manquants
from .config import APPLI, Config, charger
from .ingredients import Arbre, lire_ligne, normaliser, rapprocher
from .lieux import Lieux
from .travail import Travail

ETAT: dict = {}
PUBLIQUES = ("/api/connexion", "/api/session")
SEUIL_CONFIANCE = 0.6
TAILLE_MAX = 200 * 1024 * 1024


def _generation(cfg: Config) -> int:
    try:
        return int((cfg.data / "session_generation").read_text().strip())
    except (OSError, ValueError):
        return 0


@asynccontextmanager
async def cycle(app: FastAPI):
    cfg: Config = ETAT.get("cfg") or charger()
    for d in ("", "livres", "photos"):
        (cfg.data / d).mkdir(parents=True, exist_ok=True)
    base = Base(cfg.data)
    ETAT.update(cfg=cfg, base=base, sessions=Sessions(APPLI, cfg.password, _generation(cfg)), lieux=Lieux())
    recharger_arbre()
    travail = Travail(base, ETAT["lieux"], cfg, ETAT.get("client_wikidata"))
    ETAT["travail"] = travail
    if cfg.travail_auto:
        travail.demarrer()
    yield
    travail.arreter()
    base.fermer()


app = FastAPI(title=APPLI, version=__version__, lifespan=cycle, docs_url=None, redoc_url=None)


def B() -> Base:
    return ETAT["base"]


def recharger_arbre() -> Arbre:
    ETAT["arbre"] = Arbre(B().lire("SELECT * FROM ingredient_ajoute"), B().lire("SELECT * FROM alias"))
    return ETAT["arbre"]


# ================================================================ sécurité

@app.middleware("http")
async def garde(request: Request, appel):
    chemin = request.url.path
    if chemin.startswith("/api/") and chemin not in PUBLIQUES and not ETAT["sessions"].connecte(request.cookies):
        return JSONResponse({"detail": "Connexion nécessaire."}, status_code=401)
    reponse = await appel(request)
    if chemin.startswith("/api/") and "Cache-Control" not in reponse.headers:
        reponse.headers["Cache-Control"] = "no-store"
    return reponse


@app.get("/health")
def sante():
    """Public. Pour la tuile de l'Anneau : le nombre de cocktails faisables et de cas à traiter (aucun nom)."""
    try:
        c = _calcul()
        return {"ok": True, "version": __version__, "faisables": len(c["faisables"]), "a_traiter": _compte_a_traiter()}
    except Exception:   # la santé répond même si la base est occupée
        return {"ok": True, "version": __version__}


@app.get("/api/session")
def session(request: Request):
    cfg: Config = ETAT["cfg"]
    return {"connecte": ETAT["sessions"].connecte(request.cookies), "version": __version__,
            "mistral": bool(cfg.mistral_cle), "recherche_web": cfg.recherche_web}


@app.post("/api/connexion")
async def connexion(corps: dict = Body(...)):
    s = ETAT["sessions"]
    if ETAT["cfg"].attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict")
    return r


@app.post("/api/deconnexion")
def deconnexion():
    s = ETAT["sessions"]
    s.generation += 1
    try:
        (ETAT["cfg"].data / "session_generation").write_text(str(s.generation))
    except OSError:
        pass
    r = JSONResponse({"ok": True})
    r.delete_cookie(s.cookie)
    r.delete_cookie(COMMUN)
    return r


# ================================================================ outils communs

def cle_alpha(texte: str) -> str:
    """Clé de tri alphabétique à la française : « Écorce » avec les E, pas après le Z ; majuscules ignorées."""
    import unicodedata
    sans_accents = "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn").casefold()
    return sans_accents.lstrip("«»\"'“”‘’()[]#*-–— .")       # « Two Guns » Miller se range aux T


ACTIVES = "FROM recette r JOIN livre l ON l.id = r.livre_id WHERE l.supprime_le IS NULL AND r.etat != 'ignore'"


def _lignes_par_recette() -> dict[int, list[dict]]:
    res: dict[int, list[dict]] = {}
    for l in B().lire(f"SELECT g.* FROM ligne g JOIN recette r ON r.id = g.recette_id JOIN livre l ON l.id = r.livre_id "
                      f"WHERE l.supprime_le IS NULL AND r.etat != 'ignore' ORDER BY g.recette_id, g.ordre"):
        res.setdefault(l["recette_id"], []).append(l)
    return res


def _bar() -> Bar:
    return Bar(ETAT["arbre"], {r["ingredient"] for r in B().lire("SELECT ingredient FROM bar")},
               [(e["a"], e["b"]) for e in B().lire("SELECT a, b FROM equivalence")])


def _calcul() -> dict:
    return calculer(_bar(), _lignes_par_recette())


def _compte_a_traiter() -> int:
    return B().un(f"""SELECT COUNT(*) n FROM a_traiter t LEFT JOIN recette r ON r.id = t.recette_id LEFT JOIN livre l ON l.id = r.livre_id
                      WHERE t.resolu_le IS NULL AND (t.recette_id IS NULL OR (l.supprime_le IS NULL AND r.etat != 'ignore'))""")["n"]


def _sans_alcool(lignes: list[dict]) -> bool:
    """Sans alcool : chaque ligne non facultative est un ingrédient connu et sans alcool (un inconnu ne passe pas)."""
    arbre = ETAT["arbre"]
    utiles = [l for l in lignes if not l["facultatif"]]
    return bool(utiles) and all(l["ingredient"] in arbre.noeuds and arbre.noeuds[l["ingredient"]].sans_alcool for l in utiles)


def _base_alcool(lignes: list[dict]) -> str | None:
    """Spiritueux principal (la famille de la première ligne de spiritueux), pour le filtre « spiritueux »."""
    arbre = ETAT["arbre"]
    for l in lignes:
        n = arbre.noeuds.get(l["ingredient"] or "")
        if n and n.categorie == "spiritueux":
            return n.id if n.niveau == "famille" else n.parent
    return None


def _ecrire_lignes(cnx, recette_id: int, textes: list[str]) -> list[dict]:
    """Remplace les lignes d'une recette ; rend les noms d'ingrédients inconnus."""
    arbre = ETAT["arbre"]
    cnx.execute("DELETE FROM ligne WHERE recette_id = ?", (recette_id,))
    inconnus = []
    for i, t in enumerate(textes):
        l = lire_ligne(t)
        ing = rapprocher(arbre, l)
        facultatif = l.facultatif or (ing is not None and arbre.noeuds[ing].garniture)
        cnx.execute("INSERT INTO ligne (recette_id, ordre, texte, quantite, unite, nom, ingredient, facultatif) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (recette_id, i, l.texte, l.quantite, l.unite, l.nom, ing, int(facultatif)))
        if ing is None and l.nom:
            inconnus.append({"nom": l.nom, "texte": l.texte})
    return inconnus


def _question_ingredient(cnx, recette_id: int, inconnu: dict) -> None:
    """Une seule question par nom inconnu, quel que soit le nombre de recettes qui l'emploient."""
    cle = normaliser(inconnu["nom"])
    deja = cnx.execute("SELECT 1 FROM a_traiter WHERE type = 'ingredient' AND cle = ? AND resolu_le IS NULL", (cle,)).fetchone()
    if not deja:
        proposition = ETAT["arbre"].proposer(inconnu["nom"])
        cnx.execute("INSERT INTO a_traiter (type, recette_id, cle, donnees, cree_le) VALUES ('ingredient', ?, ?, ?, ?)",
                    (recette_id, cle, json.dumps({"nom": inconnu["nom"], "texte": inconnu["texte"], "proposition": proposition}, ensure_ascii=False), maintenant()))


def _lieux_recette(cnx, recette_id: int, titre: str, textes: str, rubrique_origine: str = "") -> None:
    lieux: Lieux = ETAT["lieux"]
    surs, ambigus = lieux.evoques(titre)
    for lieu in surs:
        cnx.execute("INSERT OR IGNORE INTO lieu_recette (recette_id, lieu, sorte, etat, source) VALUES (?, ?, 'evoque', 'sur', 'regle')", (recette_id, lieu))
    for lieu in ambigus:
        cnx.execute("INSERT INTO a_traiter (type, recette_id, donnees, cree_le) VALUES ('evoque', ?, ?, ?)",
                    (recette_id, json.dumps({"lieu": lieu, "chemin": lieux.chemin(lieu)}, ensure_ascii=False), maintenant()))
    for nom in epub.origine_ecrite(textes, rubrique_origine):
        mots = nom.split()
        # « Ritz de Paris » : le plus long groupe de mots qui soit un lieu connu
        groupes = [" ".join(mots[i:i + n]) for n in range(len(mots), 0, -1) for i in range(len(mots) - n + 1)]
        lieu = next((lieux.trouver_nom(g) for g in groupes if lieux.trouver_nom(g)), None)
        if lieu:
            cnx.execute("INSERT OR IGNORE INTO lieu_recette (recette_id, lieu, sorte, etat, source, preuve) VALUES (?, ?, 'cree_a', 'sur', 'livre', ?)",
                        (recette_id, lieu, f"« … {nom} »"))
            break


# ================================================================ livres

@app.get("/api/livres")
def livres():
    return B().lire("""SELECT l.id, l.titre, l.auteur, l.a_reperes_page, l.importe_le, l.supprime_le,
                              (SELECT COUNT(*) FROM recette r WHERE r.livre_id = l.id AND r.etat != 'ignore') recettes,
                              (SELECT COUNT(*) FROM recette r WHERE r.livre_id = l.id AND r.etat = 'a_verifier') a_verifier
                       FROM livre l WHERE l.supprime_le IS NULL ORDER BY l.titre""")


@app.post("/api/livres/import")
async def importer(request: Request, nom: str = "livre.epub"):
    contenu = await request.body()
    if not contenu:
        raise HTTPException(400, "Fichier vide.")
    if len(contenu) > TAILLE_MAX:
        raise HTTPException(413, "Fichier trop gros (200 Mo au plus).")
    empreinte = hashlib.sha256(contenu).hexdigest()
    deja = B().un("SELECT id, titre, supprime_le FROM livre WHERE empreinte = ?", empreinte)
    if deja and deja["supprime_le"]:
        return JSONResponse({"detail": f"« {deja['titre']} » est dans la corbeille : le restaurer plutôt que de l'importer à nouveau ?",
                             "corbeille": deja["id"]}, status_code=409)
    if deja:
        return JSONResponse({"detail": f"Ce livre est déjà importé (« {deja['titre']} »).", "deja": deja["id"]}, status_code=409)
    try:
        lu = epub.lire(contenu, ETAT["arbre"])
    except epub.LivreIllisible as e:
        raise HTTPException(422, str(e))
    cfg: Config = ETAT["cfg"]
    fichier = f"{empreinte[:16]}.epub"
    (cfg.data / "livres" / fichier).write_bytes(contenu)
    photos: list[tuple[int, str]] = []
    with B().transaction() as cnx:
        livre_id = cnx.execute("INSERT INTO livre (titre, auteur, fichier, empreinte, a_reperes_page, importe_le) VALUES (?, ?, ?, ?, ?, ?)",
                               (lu.titre, lu.auteur, fichier, empreinte, int(lu.a_reperes_page), maintenant())).lastrowid
        for i, r in enumerate(lu.recettes):
            etat = "valide" if r.confiance >= SEUIL_CONFIANCE else "a_verifier"
            rid = cnx.execute("""INSERT INTO recette (livre_id, ordre, titre, page_debut, page_fin, chapeau, etapes, texte_original, confiance, etat,
                                                      infos, note)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                              (livre_id, i, r.titre, r.page_debut, r.page_fin, r.chapeau, json.dumps(r.etapes, ensure_ascii=False),
                               r.texte_original, r.confiance, etat, json.dumps(r.infos, ensure_ascii=False), r.note)).lastrowid
            for inconnu in _ecrire_lignes(cnx, rid, r.lignes):
                _question_ingredient(cnx, rid, inconnu)
            if etat == "a_verifier":
                cnx.execute("INSERT INTO a_traiter (type, recette_id, donnees, cree_le) VALUES ('recette', ?, ?, ?)",
                            (rid, json.dumps({"raisons": r.raisons}, ensure_ascii=False), maintenant()))
            _lieux_recette(cnx, rid, r.titre, " ".join([r.chapeau, *r.etapes]), r.infos.get("Origine", ""))
            if r.image and r.image in lu.images:
                photos.append((rid, r.image))
        for i, c in enumerate(lu.conseils):
            cnx.execute("INSERT INTO conseil (livre_id, ordre, titre, theme, page_debut, page_fin, contenu) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (livre_id, i, c.titre, c.theme, c.page_debut, c.page_fin, json.dumps(c.contenu, ensure_ascii=False)))
    for rid, image in photos:
        if epub.ecrire_photo(lu.images[image], cfg.data / "photos" / f"{rid}.webp"):
            B().ecrire("UPDATE recette SET photo = 1 WHERE id = ?", rid)
    a_verifier = sum(1 for r in lu.recettes if r.confiance < SEUIL_CONFIANCE)
    B().noter("import", lu.titre, f"{len(lu.recettes)} recettes, dont {a_verifier} à vérifier, {len(lu.conseils)} conseils"
              + ("" if lu.a_reperes_page else " ; pas de repères de page"))
    return {"id": livre_id, "titre": lu.titre, "recettes": len(lu.recettes), "a_verifier": a_verifier, "conseils": len(lu.conseils),
            "a_reperes_page": lu.a_reperes_page, "nom_fichier": nom}


@app.get("/api/livres/{livre_id}/suppression")
def apercu_suppression(livre_id: int):
    """Ce que la suppression emporte, pour la confirmation."""
    l = B().un("SELECT id, titre FROM livre WHERE id = ? AND supprime_le IS NULL", livre_id)
    if not l:
        raise HTTPException(404, "Livre introuvable.")
    n = lambda sql: B().un(sql, livre_id)["n"]   # noqa: E731
    return {"titre": l["titre"], "recettes": n("SELECT COUNT(*) n FROM recette WHERE livre_id = ? AND etat != 'ignore'"),
            "favoris": n("SELECT COUNT(*) n FROM favori f JOIN recette r ON r.id = f.recette_id WHERE r.livre_id = ?"),
            "corrections": n("SELECT COUNT(*) n FROM recette WHERE livre_id = ? AND source != 'regles'"),
            "jours": ETAT["cfg"].corbeille_jours}


@app.delete("/api/livres/{livre_id}")
def supprimer_livre(livre_id: int):
    l = B().un("SELECT id, titre FROM livre WHERE id = ? AND supprime_le IS NULL", livre_id)
    if not l:
        raise HTTPException(404, "Livre introuvable.")
    B().ecrire("UPDATE livre SET supprime_le = ? WHERE id = ?", maintenant(), livre_id)
    B().noter("suppression", l["titre"], f"dans la corbeille pour {ETAT['cfg'].corbeille_jours} jours")
    return {"ok": True}


@app.get("/api/corbeille")
def corbeille():
    jours = ETAT["cfg"].corbeille_jours
    res = B().lire("""SELECT l.id, l.titre, l.auteur, l.supprime_le,
                             (SELECT COUNT(*) FROM recette r WHERE r.livre_id = l.id AND r.etat != 'ignore') recettes
                      FROM livre l WHERE l.supprime_le IS NOT NULL ORDER BY l.supprime_le DESC""")
    for r in res:
        r["efface_le"] = (datetime.fromisoformat(r["supprime_le"]) + timedelta(days=jours)).isoformat(timespec="seconds")
    return res


@app.delete("/api/corbeille/{livre_id}")
def effacer_livre(livre_id: int):
    """Efface tout de suite un livre de la corbeille (pour le réimporter à neuf après une nouvelle version du découpage)."""
    l = B().un("SELECT id, titre, fichier FROM livre WHERE id = ? AND supprime_le IS NOT NULL", livre_id)
    if not l:
        raise HTTPException(404, "Ce livre n'est pas dans la corbeille.")
    ETAT["travail"].effacer(l, "effacé à la main depuis la corbeille")
    return {"ok": True}


@app.post("/api/livres/{livre_id}/restaurer")
def restaurer_livre(livre_id: int):
    l = B().un("SELECT id, titre FROM livre WHERE id = ? AND supprime_le IS NOT NULL", livre_id)
    if not l:
        raise HTTPException(404, "Ce livre n'est pas dans la corbeille.")
    B().ecrire("UPDATE livre SET supprime_le = NULL WHERE id = ?", livre_id)
    B().noter("restauration", l["titre"], "sorti de la corbeille")
    return {"ok": True}


# ================================================================ recettes

def _resume(r: dict, lignes: list[dict], lieux_r: list[dict], favoris: set[int]) -> dict:
    return {"id": r["id"], "titre": r["titre"], "livre": r["livre"], "livre_id": r["livre_id"],
            "pages": epub.texte_pages(r), "photo": bool(r["photo"]), "favori": r["id"] in favoris, "note": r["note"],
            "etat": r["etat"], "sans_alcool": _sans_alcool(lignes), "base": _base_alcool(lignes),
            "evoque": [x["lieu"] for x in lieux_r if x["sorte"] == "evoque"],
            "cree_a": [x["lieu"] for x in lieux_r if x["sorte"] == "cree_a"]}


@app.get("/api/recettes")
def recettes():
    lignes = _lignes_par_recette()
    favoris = {f["recette_id"] for f in B().lire("SELECT recette_id FROM favori")}
    lieux_par: dict[int, list[dict]] = {}
    for x in B().lire("SELECT * FROM lieu_recette"):
        lieux_par.setdefault(x["recette_id"], []).append(x)
    liste = sorted(B().lire(f"SELECT r.*, l.titre livre {ACTIVES}"), key=lambda r: cle_alpha(r["titre"]))
    calc = calculer(_bar(), lignes)
    arbre = ETAT["arbre"]
    bases = sorted({b for b in (_base_alcool(lignes.get(r["id"], [])) for r in liste) if b}, key=lambda b: arbre.noeuds[b].nom)
    return {"recettes": [_resume(r, lignes.get(r["id"], []), lieux_par.get(r["id"], []), favoris) for r in liste],
            "faisables": calc["faisables"], "presque": calc["presque"], "debloque": calc["debloque"],
            "bases": [{"id": b, "nom": arbre.noeuds[b].nom} for b in bases]}


def _recette(recette_id: int) -> dict:
    r = B().un(f"SELECT r.*, l.titre livre, l.supprime_le FROM recette r JOIN livre l ON l.id = r.livre_id WHERE r.id = ?", recette_id)
    if not r or r["supprime_le"]:
        raise HTTPException(404, "Recette introuvable.")
    return r


@app.get("/api/recettes/{recette_id}")
def recette(recette_id: int):
    r = _recette(recette_id)
    arbre, lieux, bar = ETAT["arbre"], ETAT["lieux"], _bar()
    lignes = B().lire("SELECT * FROM ligne WHERE recette_id = ? ORDER BY ordre", recette_id)
    sorties = []
    for l in lignes:
        sorties.append({"texte": l["texte"], "quantite": l["quantite"], "unite": l["unite"], "nom": l["nom"],
                        "ingredient": l["ingredient"], "ingredient_nom": arbre.noeuds[l["ingredient"]].nom if l["ingredient"] in arbre.noeuds else None,
                        "facultatif": bool(l["facultatif"]), "present": bar.satisfait(l["ingredient"])})
    lieux_r = [{"lieu": x["lieu"], "sorte": x["sorte"], "source": x["source"], "preuve": x["preuve"],
                "chemin": lieux.chemin(x["lieu"])} for x in B().lire("SELECT * FROM lieu_recette WHERE recette_id = ?", recette_id)]
    return {"id": r["id"], "titre": r["titre"], "livre": r["livre"], "livre_id": r["livre_id"], "pages": epub.texte_pages(r),
            "photo": bool(r["photo"]), "chapeau": r["chapeau"], "etapes": json.loads(r["etapes"]), "lignes": sorties,
            "lieux": lieux_r, "favori": bool(B().un("SELECT 1 x FROM favori WHERE recette_id = ?", recette_id)),
            "etat": r["etat"], "source": r["source"], "texte_original": r["texte_original"],
            "infos": [{"nom": k, "texte": v} for k, v in json.loads(r["infos"] or "{}").items()], "note": r["note"],
            "manque": len(manquants(bar, lignes)), "sans_alcool": _sans_alcool(lignes)}


@app.post("/api/recettes/{recette_id}/favori")
def favori(recette_id: int, corps: dict = Body(...)):
    _recette(recette_id)
    if corps.get("favori"):
        B().ecrire("INSERT OR IGNORE INTO favori (recette_id, ajoute_le) VALUES (?, ?)", recette_id, maintenant())
    else:
        B().ecrire("DELETE FROM favori WHERE recette_id = ?", recette_id)
    return {"favori": bool(corps.get("favori"))}


@app.get("/api/photos/{recette_id}")
def photo(recette_id: int):
    r = _recette(recette_id)
    chemin = ETAT["cfg"].data / "photos" / f"{r['id']}.webp"
    if not r["photo"] or not chemin.is_file():
        raise HTTPException(404, "Pas de photo.")
    return FileResponse(chemin, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


@app.put("/api/recettes/{recette_id}")
def corriger(recette_id: int, corps: dict = Body(...)):
    """Correction à la main, ou validation de ce que Mistral a proposé (source = « mistral »)."""
    r = _recette(recette_id)
    titre = str(corps.get("titre") or r["titre"]).strip()
    lignes = [str(x).strip() for x in corps.get("lignes", []) if str(x).strip()]
    etapes = [str(x).strip() for x in corps.get("etapes", []) if str(x).strip()]
    if not lignes:
        raise HTTPException(400, "Une recette a au moins un ingrédient.")
    source = "mistral" if corps.get("source") == "mistral" else "main"
    avant = {"titre": r["titre"], "chapeau": r["chapeau"], "etapes": json.loads(r["etapes"]), "etat": r["etat"], "source": r["source"],
             "lignes": [l["texte"] for l in B().lire("SELECT texte FROM ligne WHERE recette_id = ? ORDER BY ordre", recette_id)]}
    with B().transaction() as cnx:
        cnx.execute("UPDATE recette SET titre = ?, chapeau = ?, etapes = ?, etat = 'valide', source = ?, modifie_le = ? WHERE id = ?",
                    (titre, str(corps.get("chapeau", r["chapeau"]) or "").strip(), json.dumps(etapes, ensure_ascii=False), source, maintenant(), recette_id))
        for inconnu in _ecrire_lignes(cnx, recette_id, lignes):
            _question_ingredient(cnx, recette_id, inconnu)
        cnx.execute("UPDATE a_traiter SET resolu_le = ? WHERE type = 'recette' AND recette_id = ? AND resolu_le IS NULL", (maintenant(), recette_id))
        if titre != r["titre"]:
            cnx.execute("DELETE FROM lieu_recette WHERE recette_id = ? AND sorte = 'evoque' AND source = 'regle'", (recette_id,))
            _lieux_recette(cnx, recette_id, titre, "")
    B().noter("correction", titre, "proposée par Mistral, validée" if source == "mistral" else "à la main",
              json.dumps({"recette": recette_id, **avant}, ensure_ascii=False))
    return recette(recette_id)


@app.post("/api/recettes/{recette_id}/ignorer")
def ignorer(recette_id: int):
    r = _recette(recette_id)
    B().ecrire("UPDATE recette SET etat = 'ignore', modifie_le = ? WHERE id = ?", maintenant(), recette_id)
    B().ecrire("UPDATE a_traiter SET resolu_le = ? WHERE recette_id = ? AND resolu_le IS NULL", maintenant(), recette_id)
    B().noter("ignore", r["titre"], "ce n'est pas une recette",
              json.dumps({"recette": recette_id, "etat": r["etat"]}, ensure_ascii=False))
    return {"ok": True}


@app.post("/api/recettes/{recette_id}/mistral")
def demander_mistral(recette_id: int):
    r = _recette(recette_id)
    cfg: Config = ETAT["cfg"]
    try:
        rel = mistral.relire_recette(r["texte_original"], cfg.mistral_cle, cfg.mistral_url, cfg.mistral_modele, ETAT.get("client_mistral"))
        statut = "ok"
    except mistral.ErreurMistral as e:
        B().ecrire("INSERT INTO appel_externe (le, service, cible, statut) VALUES (?, 'mistral', ?, ?)", maintenant(), r["titre"], "erreur")
        raise HTTPException(502, str(e))
    B().ecrire("INSERT INTO appel_externe (le, service, cible, statut) VALUES (?, 'mistral', ?, ?)", maintenant(), r["titre"], statut)
    return {"titre": rel.titre, "lignes": rel.ingredients, "etapes": rel.etapes, "chapeau": rel.chapeau, "origine": rel.origine}


# ================================================================ bar

@app.get("/api/bar")
def bar():
    """Les ingrédients que les livres emploient, rangés catégorie > famille, avec les variantes de chaque famille."""
    arbre = ETAT["arbre"]
    presents = {r["ingredient"] for r in B().lire("SELECT ingredient FROM bar")}
    frais = {r["ingredient"] for r in B().lire("SELECT ingredient FROM frais")}
    emplois: dict[str, int] = {}
    for l in B().lire(f"SELECT g.ingredient, COUNT(DISTINCT g.recette_id) n FROM ligne g JOIN recette r ON r.id = g.recette_id "
                      f"JOIN livre l ON l.id = r.livre_id WHERE l.supprime_le IS NULL AND r.etat != 'ignore' AND g.ingredient IS NOT NULL GROUP BY g.ingredient"):
        emplois[l["ingredient"]] = l["n"]
    familles: set[str] = set()
    for i in emplois:
        n = arbre.noeuds.get(i)
        if n and n.niveau != "categorie":
            familles.add(n.id if n.niveau == "famille" else n.parent)
    cats: dict[str, dict] = {}
    for f in familles:
        fam = arbre.noeuds[f]
        cat = arbre.noeuds[fam.categorie]
        items = [fam.id, *sorted(fam.enfants, key=lambda e: cle_alpha(arbre.noeuds[e].nom))]   # la famille, puis ses variantes de A à Z
        bloc = cats.setdefault(cat.id, {"id": cat.id, "nom": cat.nom, "familles": []})
        bloc["familles"].append({"id": fam.id, "nom": fam.nom, "ingredients": [
            {"id": i, "nom": arbre.noeuds[i].nom, "niveau": arbre.noeuds[i].niveau, "present": i in presents,
             "frais": i in frais, "frais_propose": arbre.noeuds[i].frais,
             "toujours_la": arbre.noeuds[i].toujours_la, "recettes": emplois.get(i, 0)} for i in items]})
    sortie = sorted(cats.values(), key=lambda c: cle_alpha(c["nom"]))
    for c in sortie:
        c["familles"].sort(key=lambda f: cle_alpha(f["nom"]))
    return {"categories": sortie, "faisables": len(_calcul()["faisables"])}


@app.post("/api/bar")
def cocher(corps: dict = Body(...)):
    ing = str(corps.get("ingredient", ""))
    if ing not in ETAT["arbre"].noeuds:
        raise HTTPException(404, "Ingrédient inconnu.")
    if corps.get("present"):
        B().ecrire("INSERT OR IGNORE INTO bar (ingredient, ajoute_le) VALUES (?, ?)", ing, maintenant())
    else:
        B().ecrire("DELETE FROM bar WHERE ingredient = ?", ing)
    return {"ok": True, "faisables": len(_calcul()["faisables"])}


@app.post("/api/frais")
def marquer_frais(corps: dict = Body(...)):
    ing = str(corps.get("ingredient", ""))
    if ing not in ETAT["arbre"].noeuds:
        raise HTTPException(404, "Ingrédient inconnu.")
    if corps.get("frais"):
        B().ecrire("INSERT OR IGNORE INTO frais (ingredient) VALUES (?)", ing)
    else:
        B().ecrire("DELETE FROM frais WHERE ingredient = ?", ing)
    return {"ok": True}


@app.get("/api/ingredients")
def ingredients():
    """Tout l'arbre, pour rattacher un nom inconnu ou créer une équivalence."""
    arbre = ETAT["arbre"]
    liste = [{"id": n.id, "nom": n.nom, "niveau": n.niveau, "chemin": arbre.chemin(n.id)} for n in arbre.noeuds.values()]
    return sorted(liste, key=lambda i: [cle_alpha(x) for x in i["chemin"]])        # catégorie, puis famille, puis variante


@app.get("/api/equivalences")
def equivalences():
    arbre = ETAT["arbre"]
    return [{"a": e["a"], "b": e["b"], "nom_a": arbre.noeuds[e["a"]].nom, "nom_b": arbre.noeuds[e["b"]].nom}
            for e in B().lire("SELECT * FROM equivalence") if e["a"] in arbre.noeuds and e["b"] in arbre.noeuds]


@app.post("/api/equivalences")
def ajouter_equivalence(corps: dict = Body(...)):
    a, b = str(corps.get("a", "")), str(corps.get("b", ""))
    if a == b or a not in ETAT["arbre"].noeuds or b not in ETAT["arbre"].noeuds:
        raise HTTPException(400, "Choisir deux ingrédients différents.")
    a, b = sorted((a, b))
    B().ecrire("INSERT OR IGNORE INTO equivalence (a, b) VALUES (?, ?)", a, b)
    B().noter("equivalence", f"{a} = {b}")
    return equivalences()


@app.delete("/api/equivalences/{a}/{b}")
def retirer_equivalence(a: str, b: str):
    a, b = sorted((a, b))
    B().ecrire("DELETE FROM equivalence WHERE a = ? AND b = ?", a, b)
    return equivalences()


# ================================================================ À traiter

TYPES = {"recette": "Recettes à vérifier", "ingredient": "Nouveaux ingrédients", "origine": "Origines à vérifier", "evoque": "Lieux évoqués ambigus"}


@app.get("/api/a-traiter")
def a_traiter():
    lieux = ETAT["lieux"]
    elements = B().lire("""SELECT t.*, r.titre recette_titre, r.texte_original, l.titre livre FROM a_traiter t
                           LEFT JOIN recette r ON r.id = t.recette_id LEFT JOIN livre l ON l.id = r.livre_id
                           WHERE t.resolu_le IS NULL AND (t.recette_id IS NULL OR (l.supprime_le IS NULL AND r.etat != 'ignore'))
                           ORDER BY t.id""")
    arbre = ETAT["arbre"]
    inconnus: dict[str, set[int]] = {}
    for l in B().lire("SELECT recette_id, nom FROM ligne WHERE ingredient IS NULL"):
        inconnus.setdefault(normaliser(l["nom"]), set()).add(l["recette_id"])
    for e in elements:
        e["donnees"] = json.loads(e["donnees"] or "{}")
        if e["type"] == "ingredient":
            p = e["donnees"].get("proposition")
            e["donnees"]["proposition_nom"] = " › ".join(arbre.chemin(p)) if p in arbre.noeuds else None
            e["recettes"] = len(inconnus.get(e["cle"], ()))
        if e["type"] == "origine":
            for c in e["donnees"].get("candidats", []):
                c["chemin"] = lieux.chemin(c["lieu"]) if c.get("lieu") else None
    tuiles = [{"type": t, "nom": nom, "nombre": sum(1 for e in elements if e["type"] == t)} for t, nom in TYPES.items()]
    return {"tuiles": tuiles, "elements": elements}


def _resoudre(id_: int) -> None:
    B().ecrire("UPDATE a_traiter SET resolu_le = ? WHERE id = ?", maintenant(), id_)


@app.post("/api/a-traiter/{id_}")
def resoudre(id_: int, corps: dict = Body(...)):
    t = B().un("SELECT * FROM a_traiter WHERE id = ? AND resolu_le IS NULL", id_)
    if not t:
        raise HTTPException(404, "Cette question est déjà réglée.")
    d = json.loads(t["donnees"] or "{}")
    arbre, lieux = ETAT["arbre"], ETAT["lieux"]
    action = corps.get("action")
    if t["type"] == "ingredient":
        if action == "ignorer":
            _resoudre(id_)
            return {"ok": True}
        ing = corps.get("ingredient")
        if action == "creer":
            parent = str(corps.get("parent", ""))
            nom = str(corps.get("nom") or d["nom"]).strip()
            if parent not in arbre.noeuds or arbre.noeuds[parent].niveau == "variante":
                raise HTTPException(400, "Choisir une catégorie ou une famille où ranger le nouvel ingrédient.")
            ing = "x-" + normaliser(nom).replace(" ", "-").replace("'", "")[:40]
            niveau = "famille" if arbre.noeuds[parent].niveau == "categorie" else "variante"
            B().ecrire("INSERT OR IGNORE INTO ingredient_ajoute (id, nom, parent, niveau) VALUES (?, ?, ?, ?)", ing, nom, parent, niveau)
        elif ing not in arbre.noeuds:
            raise HTTPException(400, "Choisir un ingrédient.")
        B().ecrire("INSERT OR REPLACE INTO alias (texte, ingredient) VALUES (?, ?)", t["cle"], ing)
        arbre = recharger_arbre()
        # Toutes les lignes qui portent ce nom, dans tous les livres, sont rattachées d'un coup
        lignes = [l for l in B().lire("SELECT id, nom FROM ligne WHERE ingredient IS NULL") if normaliser(l["nom"]) == t["cle"]]
        for l in lignes:
            B().ecrire("UPDATE ligne SET ingredient = ?, facultatif = facultatif OR ? WHERE id = ?", ing, int(arbre.noeuds[ing].garniture), l["id"])
        _resoudre(id_)
        B().noter("rattachement", d["nom"], f"→ {' › '.join(arbre.chemin(ing))} ({len(lignes)} ligne(s))",
                  json.dumps({"alias": t["cle"], "lignes": [l["id"] for l in lignes], "a_traiter": id_}, ensure_ascii=False))
        return {"ok": True, "lignes": len(lignes)}
    if t["type"] == "origine":
        lieu = corps.get("lieu")
        if lieu:
            if lieu not in lieux.lieux:
                raise HTTPException(400, "Lieu inconnu.")
            B().ecrire("INSERT OR REPLACE INTO lieu_recette (recette_id, lieu, sorte, etat, source, preuve) VALUES (?, ?, 'cree_a', 'valide', ?, ?)",
                       t["recette_id"], lieu, "main" if corps.get("saisi") else d.get("source", "wikidata"), corps.get("preuve", ""))
        _resoudre(id_)
        return {"ok": True}
    if t["type"] == "evoque":
        lieu = corps.get("lieu") or (d.get("lieu") if action == "oui" else None)
        if action in ("oui", "autre") and lieu:
            if lieu not in lieux.lieux:
                raise HTTPException(400, "Lieu inconnu.")
            B().ecrire("INSERT OR REPLACE INTO lieu_recette (recette_id, lieu, sorte, etat, source) VALUES (?, ?, 'evoque', 'valide', ?)",
                       t["recette_id"], lieu, "regle" if action == "oui" else "main")
        _resoudre(id_)
        return {"ok": True}
    if t["type"] == "recette" and action == "valider":
        B().ecrire("UPDATE recette SET etat = 'valide', modifie_le = ? WHERE id = ?", maintenant(), t["recette_id"])
        _resoudre(id_)
        return {"ok": True}
    raise HTTPException(400, "Action inconnue pour cette question.")


# ================================================================ lieux

@app.get("/api/lieux")
def lieux_connus():
    lieux: Lieux = ETAT["lieux"]
    actifs = {r["id"] for r in B().lire(f"SELECT r.id {ACTIVES}")}
    compte: dict[str, dict[str, set[int]]] = {}
    for x in B().lire("SELECT recette_id, lieu, sorte FROM lieu_recette"):
        if x["recette_id"] not in actifs or x["lieu"] not in lieux.lieux:
            continue
        for anc in lieux.ancetres(x["lieu"]):        # une recette de Manhattan compte aussi pour New York et les États-Unis
            compte.setdefault(anc, {"cree_a": set(), "evoque": set()})[x["sorte"]].add(x["recette_id"])
    sortie = []
    for id_, l in lieux.lieux.items():
        c = compte.get(id_, {"cree_a": set(), "evoque": set()})
        sortie.append({"id": id_, "nom": l.nom, "type": l.type, "parent": l.parent, "pays": l.pays, "lat": l.lat, "lon": l.lon,
                       "iso": l.iso, "chemin": lieux.chemin(id_), "cree_a": sorted(c["cree_a"]), "evoque": sorted(c["evoque"])})
    return sortie


# ================================================================ journal et sources

@app.get("/api/journal")
def journal():
    return B().lire("SELECT id, le, action, cible, detail, annule, avant IS NOT NULL annulable FROM journal ORDER BY id DESC LIMIT 200")


@app.post("/api/journal/{id_}/annuler")
def annuler(id_: int):
    j = B().un("SELECT * FROM journal WHERE id = ? AND annule = 0 AND avant IS NOT NULL", id_)
    if not j:
        raise HTTPException(404, "Rien à annuler.")
    avant = json.loads(j["avant"])
    if j["action"] == "correction":
        rid = avant["recette"]
        _recette(rid)
        with B().transaction() as cnx:
            cnx.execute("UPDATE recette SET titre = ?, chapeau = ?, etapes = ?, etat = ?, source = ?, modifie_le = ? WHERE id = ?",
                        (avant["titre"], avant["chapeau"], json.dumps(avant["etapes"], ensure_ascii=False), avant["etat"], avant["source"], maintenant(), rid))
            _ecrire_lignes(cnx, rid, avant["lignes"])
    elif j["action"] == "ignore":
        B().ecrire("UPDATE recette SET etat = ? WHERE id = ?", avant["etat"], avant["recette"])
    elif j["action"] == "rattachement":
        B().ecrire("DELETE FROM alias WHERE texte = ?", avant["alias"])
        for lid in avant["lignes"]:
            B().ecrire("UPDATE ligne SET ingredient = NULL WHERE id = ?", lid)
        B().ecrire("UPDATE a_traiter SET resolu_le = NULL WHERE id = ?", avant["a_traiter"])
        recharger_arbre()
    else:
        raise HTTPException(400, "Cette action ne s'annule pas.")
    B().ecrire("UPDATE journal SET annule = 1 WHERE id = ?", id_)
    B().noter("annulation", j["cible"], j["action"])
    return {"ok": True}


# ================================================================ conseils du livre

ORDRE_THEMES = ["Techniques", "Glace", "Verres", "Matériel", "Ingrédients", "Autres"]


@app.get("/api/conseils")
def conseils():
    """Passages des livres qui ne sont pas des recettes, rangés par thème (sans leur texte, pour la liste)."""
    liste = B().lire("""SELECT c.id, c.titre, c.theme, c.page_debut, c.page_fin, c.livre_id, l.titre livre, c.contenu
                        FROM conseil c JOIN livre l ON l.id = c.livre_id WHERE l.supprime_le IS NULL ORDER BY l.titre, c.ordre""")
    for c in liste:
        contenu = json.loads(c.pop("contenu"))
        premier = next((x["texte"] for x in contenu if x["sorte"] == "para"), "")
        c["apercu"] = premier[:160] + ("…" if len(premier) > 160 else "")
        c["pages"] = epub.texte_pages(c)
    themes = sorted({c["theme"] for c in liste}, key=lambda t: ORDRE_THEMES.index(t) if t in ORDRE_THEMES else 99)
    return {"conseils": liste, "themes": themes,
            "livres": B().un("SELECT COUNT(*) n FROM livre WHERE supprime_le IS NULL")["n"]}


@app.get("/api/conseils/{conseil_id}")
def conseil(conseil_id: int):
    c = B().un("""SELECT c.*, l.titre livre FROM conseil c JOIN livre l ON l.id = c.livre_id
                  WHERE c.id = ? AND l.supprime_le IS NULL""", conseil_id)
    if not c:
        raise HTTPException(404, "Conseil introuvable.")
    return {"id": c["id"], "titre": c["titre"], "theme": c["theme"], "livre": c["livre"], "livre_id": c["livre_id"],
            "pages": epub.texte_pages(c), "contenu": json.loads(c["contenu"])}


@app.get("/api/sources")
def sources():
    cfg: Config = ETAT["cfg"]
    derniers = {s: B().lire("SELECT le, cible, statut FROM appel_externe WHERE service = ? ORDER BY id DESC LIMIT 5", s) for s in ("wikidata", "mistral")}
    return [
        {"id": "wikidata", "nom": "Wikidata", "actif": cfg.recherche_web, "role": "Lit le pays ou le lieu de création des cocktails (lecture seule, une fois par recette).",
         "lit": "Le nom du cocktail et, s'il existe, son pays ou son lieu d'origine.",
         "ecrit": "Rien chez Wikidata. Un lieu sûr est posé dans Comptoir ; un doute part dans À traiter.",
         "reglage": "COMPTOIR_RECHERCHE_WEB", "derniers": derniers["wikidata"]},
        {"id": "mistral", "nom": "Mistral", "actif": bool(cfg.mistral_cle), "role": "Relit une recette mal découpée, seulement sur ton clic ; rien n'est enregistré sans ta validation.",
         "lit": "Le texte d'une seule recette, celle que tu lui envoies depuis À traiter.",
         "ecrit": "Rien : sa proposition attend que tu la valides ou la corriges.",
         "reglage": "COMPTOIR_MISTRAL_CLE", "derniers": derniers["mistral"]},
    ]


@app.post("/api/sources/{nom}/verifier")
def verifier_source(nom: str):
    cfg: Config = ETAT["cfg"]
    try:
        if nom == "wikidata":
            if not cfg.recherche_web:
                return {"ok": False, "message": "Recherche coupée dans la stack (COMPTOIR_RECHERCHE_WEB=non)."}
            client = ETAT.get("client_wikidata") or httpx.Client(timeout=10, headers={"User-Agent": "Comptoir (appli maison)"})
            r = client.get(cfg.wikidata_url, params={"action": "query", "meta": "siteinfo", "format": "json"})
            return {"ok": r.status_code == 200, "message": "Wikidata répond." if r.status_code == 200 else f"Wikidata a répondu {r.status_code}."}
        if nom == "mistral":
            if not cfg.mistral_cle:
                return {"ok": False, "message": "Aucune clé réglée (COMPTOIR_MISTRAL_CLE)."}
            client = ETAT.get("client_mistral") or httpx.Client(timeout=10)
            r = client.get(cfg.mistral_url.replace("/chat/completions", "/models"), headers={"Authorization": f"Bearer {cfg.mistral_cle}"})
            if r.status_code in (401, 403):
                return {"ok": False, "message": "Mistral refuse la clé."}
            return {"ok": r.status_code == 200, "message": "Mistral répond et accepte la clé." if r.status_code == 200 else f"Mistral a répondu {r.status_code}."}
    except httpx.HTTPError as e:
        return {"ok": False, "message": f"Pas de réponse ({e.__class__.__name__})."}
    raise HTTPException(404, "Source inconnue.")


# ================================================================ interface

@app.get("/{chemin:path}")
def interface(chemin: str):
    statique: Path = ETAT["cfg"].static
    fichier = (statique / chemin).resolve() if chemin else None
    if fichier and fichier.is_file() and statique.resolve() in fichier.parents:
        return FileResponse(fichier)
    index = statique / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Interface non compilée."}, status_code=404)
