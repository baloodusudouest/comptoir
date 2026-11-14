"""Base SQLite de Comptoir.

Fichiers : <data>/comptoir.db, <data>/livres/<id>.epub (le livre déposé), <data>/photos/<recette>.webp.
Un livre supprimé garde ses lignes et ses fichiers pendant la durée de la corbeille (supprime_le rempli),
puis tout est effacé par la tâche de fond.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS livre (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT NOT NULL,
    auteur TEXT NOT NULL DEFAULT '',
    fichier TEXT NOT NULL,
    empreinte TEXT NOT NULL UNIQUE,
    a_reperes_page INTEGER NOT NULL DEFAULT 0,
    importe_le TEXT NOT NULL,
    supprime_le TEXT                       -- rempli : le livre est dans la corbeille
);
CREATE TABLE IF NOT EXISTS recette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    livre_id INTEGER NOT NULL REFERENCES livre(id) ON DELETE CASCADE,
    ordre INTEGER NOT NULL,
    titre TEXT NOT NULL,
    page_debut TEXT,
    page_fin TEXT,
    chapeau TEXT NOT NULL DEFAULT '',
    etapes TEXT NOT NULL DEFAULT '[]',     -- JSON : liste de phrases
    texte_original TEXT NOT NULL DEFAULT '',
    photo INTEGER NOT NULL DEFAULT 0,
    confiance REAL NOT NULL DEFAULT 1,
    etat TEXT NOT NULL DEFAULT 'valide',   -- a_verifier, valide, ignore
    source TEXT NOT NULL DEFAULT 'regles', -- regles, mistral, main
    modifie_le TEXT
);
CREATE TABLE IF NOT EXISTS ligne (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recette_id INTEGER NOT NULL REFERENCES recette(id) ON DELETE CASCADE,
    ordre INTEGER NOT NULL,
    texte TEXT NOT NULL,
    quantite REAL,
    unite TEXT NOT NULL DEFAULT '',
    nom TEXT NOT NULL DEFAULT '',
    ingredient TEXT,                       -- identifiant de l'arbre ; vide : ingrédient inconnu
    facultatif INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS alias (          -- noms vus dans les livres, rattachés à la main
    texte TEXT PRIMARY KEY,
    ingredient TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingredient_ajoute (   -- ingrédients créés dans l'appli (en plus de l'arbre livré)
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    parent TEXT NOT NULL,
    niveau TEXT NOT NULL DEFAULT 'variante'
);
CREATE TABLE IF NOT EXISTS equivalence (
    a TEXT NOT NULL,
    b TEXT NOT NULL,
    PRIMARY KEY (a, b)
);
CREATE TABLE IF NOT EXISTS bar (
    ingredient TEXT PRIMARY KEY,
    ajoute_le TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS frais (          -- « à racheter souvent »
    ingredient TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS favori (
    recette_id INTEGER PRIMARY KEY REFERENCES recette(id) ON DELETE CASCADE,
    ajoute_le TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lieu_recette (
    recette_id INTEGER NOT NULL REFERENCES recette(id) ON DELETE CASCADE,
    lieu TEXT NOT NULL,
    sorte TEXT NOT NULL,                   -- cree_a, evoque
    etat TEXT NOT NULL DEFAULT 'sur',      -- sur, valide
    source TEXT NOT NULL,                  -- livre, wikidata, regle, main
    preuve TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (recette_id, sorte, lieu)
);
CREATE TABLE IF NOT EXISTS a_traiter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,                    -- recette, ingredient, origine, evoque
    recette_id INTEGER REFERENCES recette(id) ON DELETE CASCADE,
    cle TEXT NOT NULL DEFAULT '',          -- pour « ingredient » : le nom lu, une seule question par nom
    donnees TEXT NOT NULL DEFAULT '{}',
    cree_le TEXT NOT NULL,
    resolu_le TEXT
);
CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    le TEXT NOT NULL,
    action TEXT NOT NULL,
    cible TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    avant TEXT,                            -- JSON, pour « Annuler »
    annule INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS appel_externe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    le TEXT NOT NULL,
    service TEXT NOT NULL,
    cible TEXT NOT NULL,
    statut TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cache_web (
    cle TEXT PRIMARY KEY,
    contenu TEXT NOT NULL,
    le TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS recette_livre ON recette(livre_id);
CREATE INDEX IF NOT EXISTS ligne_recette ON ligne(recette_id);
"""


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Base:
    def __init__(self, data: Path):
        self.data = data
        self._verrou = threading.RLock()
        self._cnx = sqlite3.connect(data / "comptoir.db", check_same_thread=False)
        self._cnx.row_factory = sqlite3.Row
        self._cnx.execute("PRAGMA foreign_keys = ON")
        self._cnx.execute("PRAGMA journal_mode = WAL")
        self._cnx.executescript(SCHEMA)
        self._cnx.commit()

    def lire(self, sql: str, *args) -> list[dict]:
        with self._verrou:
            return [dict(r) for r in self._cnx.execute(sql, args).fetchall()]

    def un(self, sql: str, *args) -> dict | None:
        r = self.lire(sql, *args)
        return r[0] if r else None

    def ecrire(self, sql: str, *args) -> int:
        with self._verrou:
            c = self._cnx.execute(sql, args)
            self._cnx.commit()
            return c.lastrowid

    def transaction(self):
        """« with base.transaction() as cnx: » : plusieurs écritures d'un coup, tout ou rien."""
        base = self

        class _T:
            def __enter__(self):
                base._verrou.acquire()
                return base._cnx

            def __exit__(self, typ, *_):
                try:
                    base._cnx.rollback() if typ else base._cnx.commit()
                finally:
                    base._verrou.release()
        return _T()

    def fermer(self) -> None:
        with self._verrou:
            self._cnx.close()

    def noter(self, action: str, cible: str = "", detail: str = "", avant: str | None = None) -> int:
        return self.ecrire("INSERT INTO journal (le, action, cible, detail, avant) VALUES (?, ?, ?, ?, ?)",
                           maintenant(), action, cible, detail, avant)
