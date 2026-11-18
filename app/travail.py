"""Tâches de fond : origine des cocktails dans Wikidata (une recette à la fois), et vidage de la corbeille.

Coupées dans les tests (travail_auto=False), qui appellent tout_faire() à la main.
0.7.0 (socle 0.9.0) : chaque tour est suivi dans maison.TACHES (« origine-wikidata », « purge-corbeille »), lu
par /health et la veille de l'Anneau ; les erreurs restent notées au journal et la boucle continue comme avant.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from datetime import datetime, timedelta

import httpx

from . import maison
from .base import Base, maintenant
from .lieux import Lieux, chercher_origine, nettoyer_titre

log = logging.getLogger("comptoir.travail")

# 0.7.0 : tâches suivies (nom, période en secondes). La boucle repasse toutes les 2 à 20 s, plus jusqu'à deux appels
# à Wikidata de 15 s chacun : 60 s évite de dire « bloquée » pendant un appel lent.
TACHE_ORIGINE, PERIODE_ORIGINE = "origine-wikidata", 60
TACHE_PURGE, PERIODE_PURGE = "purge-corbeille", 3600


class Travail:
    def __init__(self, base: Base, lieux: Lieux, cfg, reglages, client: httpx.Client | None = None):
        self.base, self.lieux, self.cfg = base, lieux, cfg
        self.reglages = reglages       # maison.Reglages : « recherche_web » se change dans l'écran Réglages
        self.client = client           # faux Wikidata dans les tests
        self._stop = threading.Event()
        self._fil: threading.Thread | None = None
        self._derniere_purge = 0.0

    def demarrer(self) -> None:
        maison.TACHES.declarer(TACHE_ORIGINE, PERIODE_ORIGINE)
        maison.TACHES.declarer(TACHE_PURGE, PERIODE_PURGE)
        self._fil = threading.Thread(target=self._boucle, name="comptoir-travail", daemon=True)
        self._fil.start()

    def arreter(self) -> None:
        self._stop.set()

    def _boucle(self) -> None:
        while not self._stop.is_set():
            try:
                with maison.TACHES.tour(TACHE_ORIGINE):
                    fait = self.une_origine()
            except Exception:      # une erreur ne doit jamais arrêter la tâche de fond
                log.exception("recherche d'origine en échec")
                fait = False
            try:                   # 0.6.1 : la purge de la corbeille ne dépend plus de Wikidata
                if time.monotonic() - self._derniere_purge > PERIODE_PURGE:
                    with maison.TACHES.tour(TACHE_PURGE):
                        self.purger()
                    self._derniere_purge = time.monotonic()
            except Exception:
                log.exception("purge de la corbeille en échec")
            self._stop.wait(2 if fait else 20)

    def tout_faire(self) -> None:
        while self.une_origine():
            pass
        self.purger()

    # ------------------------------------------------------------ origine (Wikidata)
    def a_chercher(self) -> dict | None:
        if not self.reglages.get("recherche_web"):
            return None
        return self.base.un(
            """SELECT r.id, r.titre FROM recette r JOIN livre l ON l.id = r.livre_id
               WHERE l.supprime_le IS NULL AND r.etat != 'ignore'
                 AND NOT EXISTS (SELECT 1 FROM lieu_recette x WHERE x.recette_id = r.id AND x.sorte = 'cree_a')
                 AND NOT EXISTS (SELECT 1 FROM cache_web c WHERE c.cle = 'origine:' || r.id)
               ORDER BY r.id LIMIT 1""")

    def une_origine(self) -> bool:
        r = self.a_chercher()
        if not r:
            return False
        titre = nettoyer_titre(r["titre"])
        cle_cache = "wikidata:" + titre.lower()
        en_cache = self.base.un("SELECT contenu FROM cache_web WHERE cle = ?", cle_cache)
        if en_cache:
            candidats = json.loads(en_cache["contenu"])
        else:
            try:
                trouves = chercher_origine(titre, self.lieux, self.cfg.wikidata_url, self.client)
                statut = "ok"
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:   # 0.6.1 : réponse non JSON comprise
                trouves, statut = None, f"erreur ({e.__class__.__name__})"
            self.base.ecrire("INSERT INTO appel_externe (le, service, cible, statut) VALUES (?, 'wikidata', ?, ?)",
                             maintenant(), titre, statut)
            if trouves is None:
                return False       # Wikidata muet : on réessaiera plus tard
            candidats = [c.__dict__ for c in trouves]
            self.base.ecrire("INSERT OR REPLACE INTO cache_web (cle, contenu, le) VALUES (?, ?, ?)",
                             cle_cache, json.dumps(candidats, ensure_ascii=False), maintenant())
        self.base.ecrire("INSERT OR REPLACE INTO cache_web (cle, contenu, le) VALUES (?, '', ?)", f"origine:{r['id']}", maintenant())
        connus = list(dict.fromkeys(c["lieu"] for c in candidats if c["lieu"]))
        elements = {c["element"] for c in candidats}
        if len(connus) == 1 and len(elements) == 1:
            c = next(c for c in candidats if c["lieu"])
            self.base.ecrire("INSERT OR IGNORE INTO lieu_recette (recette_id, lieu, sorte, etat, source, preuve) VALUES (?, ?, 'cree_a', 'sur', 'wikidata', ?)",
                             r["id"], connus[0], f"https://www.wikidata.org/wiki/{c['element']}")
        elif candidats:
            self.base.ecrire("INSERT INTO a_traiter (type, recette_id, donnees, cree_le) VALUES ('origine', ?, ?, ?)",
                             r["id"], json.dumps({"candidats": candidats, "source": "wikidata"}, ensure_ascii=False), maintenant())
        return True

    # ------------------------------------------------------------ corbeille
    def effacer(self, l: dict, raison: str) -> None:
        """Efface pour de bon un livre de la corbeille : lignes en base (recettes, conseils, favoris, lieux en cascade),
        EPUB déposé et photos."""
        photos = self.base.lire("SELECT id FROM recette WHERE livre_id = ? AND photo = 1", l["id"])
        self.base.ecrire("DELETE FROM livre WHERE id = ?", l["id"])
        for p in photos:
            (self.cfg.data / "photos" / f"{p['id']}.webp").unlink(missing_ok=True)
        (self.cfg.data / "livres" / l["fichier"]).unlink(missing_ok=True)
        self.base.noter("effacement", l["titre"], raison)

    def purger(self) -> int:
        limite = (datetime.now().astimezone() - timedelta(days=self.cfg.corbeille_jours)).isoformat(timespec="seconds")
        vieux = self.base.lire("SELECT id, fichier, titre FROM livre WHERE supprime_le IS NOT NULL AND supprime_le < ?", limite)
        for l in vieux:
            self.effacer(l, "corbeille vidée après 30 jours")
        if vieux:
            shutil.rmtree(self.cfg.data / "tmp", ignore_errors=True)
        return len(vieux)
