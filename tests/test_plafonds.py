"""0.6.5 (audit du 17/11/2026, M15 et M36) : un EPUB ne peut ni remplir la mémoire ni bloquer le serveur."""
from __future__ import annotations

import asyncio
import io
import zipfile

from PIL import Image

from app import epub, main
from tools.fabrique import livre_scriptorium


def importer(client, contenu, nom="livre.epub"):
    return client.post(f"/api/livres/import?nom={nom}", content=contenu)


def jpeg(taille=(60, 40)):
    b = io.BytesIO()
    Image.new("RGB", taille, "red").save(b, "JPEG")
    return b.getvalue()


def avec_fichier_en_plus(contenu: bytes, nom: str, octets: bytes) -> bytes:
    sortie = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(contenu)) as z, zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as w:
        for info in z.infolist():
            w.writestr(info, z.read(info))
        w.writestr(nom, octets)
    return sortie.getvalue()


# ---------------------------------------------------------------- M36 : contenu décompressé plafonné
def test_contenu_decompresse_plafonne(client, monkeypatch):
    """Une archive légère qui se décompresse en plus que la limite est refusée (ici limite baissée pour l'essai)."""
    livre = livre_scriptorium()
    monkeypatch.setattr(epub, "DECOMPRESSE_MAX", 2000)
    r = importer(client, livre)
    assert r.status_code == 422 and "décompressé" in r.json()["detail"]
    assert client.get("/api/livres").json() == []


def test_bombe_dans_une_seule_entree(client, monkeypatch):
    """Une seule entrée de 3 Mo de zéros (quelques Ko compressés) dépasse une limite de 1 Mo."""
    monkeypatch.setattr(epub, "DECOMPRESSE_MAX", 1024 * 1024)
    bombe = avec_fichier_en_plus(livre_scriptorium(), "EPUB/vide.xhtml", b"\0" * 3 * 1024 * 1024)
    assert len(bombe) < 100_000
    r = importer(client, bombe)
    assert r.status_code == 422 and "décompressé" in r.json()["detail"]


def test_limite_totale_sur_ce_qui_est_lu(monkeypatch):
    """Tout ce qui est lu est additionné : relire les fichiers ne contourne pas la limite totale."""
    a = epub.Archive(avec_fichier_en_plus(livre_scriptorium(), "EPUB/a.bin", b"a" * 4000))
    monkeypatch.setattr(epub, "DECOMPRESSE_MAX", 10_000)
    a.read("EPUB/a.bin")
    a.read("EPUB/a.bin")
    try:
        a.read("EPUB/a.bin")                   # 12 000 octets lus au total
    except epub.LivreIllisible as e:
        assert "décompressé" in str(e)
    else:
        raise AssertionError("limite totale non appliquée")


def test_images_non_placees_pas_lues():
    livre = avec_fichier_en_plus(livre_scriptorium(), "EPUB/images/inutile.jpg", jpeg())
    _, _, _, images = epub.lire_livre(livre)
    assert "EPUB/images/inutile.jpg" not in images
    assert "EPUB/images/daiquiri.jpg" in images            # celle de la recette, placée dans le texte


def test_import_hors_de_la_boucle(client, monkeypatch):
    """La lecture du livre tourne dans un fil à part : la boucle du serveur reste libre."""
    vu = {}
    lire = epub.lire

    def espion(contenu, arbre):
        try:
            asyncio.get_running_loop()
            vu["boucle"] = True
        except RuntimeError:
            vu["boucle"] = False
        return lire(contenu, arbre)

    monkeypatch.setattr(epub, "lire", espion)
    assert importer(client, livre_scriptorium()).status_code == 200
    assert vu == {"boucle": False}


def test_corps_trop_gros_refuse(client, monkeypatch):
    monkeypatch.setattr(main, "TAILLE_MAX", 1000)
    assert importer(client, b"x" * 5000).status_code == 413


# ---------------------------------------------------------------- M15 : plafond de pixels
def test_image_trop_grande_jamais_decodee(tmp_path, monkeypatch):
    monkeypatch.setattr(epub, "PIXELS_MAX", 1000)
    assert epub.ecrire_photo(jpeg((60, 40)), tmp_path / "p.webp") is False      # 2 400 pixels > 1 000
    assert not (tmp_path / "p.webp").exists()
    monkeypatch.setattr(epub, "PIXELS_MAX", 50_000_000)
    assert epub.ecrire_photo(jpeg((60, 40)), tmp_path / "p.webp") is True
