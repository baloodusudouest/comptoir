# Reprise — Comptoir

À lire en premier ; mis à jour dans le même commit que le code.

## État (22/11/2026) — 0.8.2 : barre d'onglets collée en bas sur iPhone (`App.svelte`, classes du socle 0.12.1 : `fixed inset-x-0 bottom-0 … pb-[calc(0.375rem+env(safe-area-inset-bottom))]`, `md:right-auto md:justify-start`). Jamais essayé sur la vraie installation.

## État (20/11/2026)
- **0.8.1 (20/11/2026)** : copies communes du socle 0.11.1 (titre « Pour le relier » quand le réglage est dans l'appli).
- **0.8.0** (20/11/2026) : fiches « Connexion » communes (contrat 3, socle 0.11.0) : `SERVICES` dans `main.py` (section « fiches Connexion » : `wikidata`, `mistral`, textes communs dans `TEXTES_SOURCES`), `maison.monter_services` après la garde, écran `$lib/services/Services.svelte` (commun, signé : ne pas le retoucher ici, `python3 tools/diffuser_maison.py ../comptoir` depuis le socle). `ANNEAU_CLE` (facultative) ouvre les seules fiches à l'Anneau. Ancienne `GET /api/sources` et `POST /api/sources/{nom}/verifier` à retirer en 0.9.0. Les livres EPUB restent dans Réglages (dossier de données), pas dans Connexion. **Jamais essayé sur la vraie installation.**

## État (18/11/2026)
- **0.7.0** (18/11/2026) : santé des tâches de fond (socle 0.9.0, `app/maison.py` copie signée non retouchée).
  Tâches dans `maison.TACHES` : `origine-wikidata` (régulière 60 s) et `purge-corbeille` (régulière 3 600 s), déclarées par
  `Travail.demarrer` (rien quand `travail_auto` est coupé) ; `import-livre` (à la demande, route d'import) ; `copie-des-bases`
  (régulière 86 400 s, `maison.planifier_copie` lancée dans `cycle`, annulée à l'arrêt). Copie de `comptoir.db` à 02:10 heure
  de Paris dans `<data>/copies` (`comptoir-derniere.db`, `copie.json`). `/health` ajoute `version_socle`, `taches`, `copie_base`
  (messages seulement avec `MAISON_JETON` ou une session). Un seul worker uvicorn. Tests : `tests/test_sante.py`.
  Jamais essayé sur la vraie installation (ni la copie de nuit, ni une restauration depuis la copie).

## État (16/11/2026)
- **0.6.0** (16/11/2026) : chantier B (réglages dans l'appli, sauvegarde, restauration) et anciens noms retirés.
  - réglage d'usage : `recherche_web` (oui/non, défaut oui), `maison.Reglages` sur `<data>/reglages.json` ; défauts et reprise dans `app/config.py` (`REGLAGES`, `REPRISES`, `EXCLUS_SAUVEGARDE`) ; repris de `COMPTOIR_RECHERCHE_WEB` au premier démarrage seulement (ligne « Réglage » au journal), ensuite la variable n'est plus lue. La tâche de fond (`travail.py`) et Connexion lisent le réglage à chaque fois : un changement s'applique tout de suite ;
  - routes (`app/main.py`, section « réglages d'usage ») : `GET/PUT /api/reglages` (session ; mauvais type ou clé inconnue → 400), `GET /externe/sauvegarde` (jeton commun seul ; `MAISON_JETON` vide → 404 ; mauvais jeton → 401), `GET /api/restaurer` (dates), `GET /api/restaurer?le=AAAA-MM-JJ` (différences), `POST /api/restaurer` (applique, ligne « Réglages restaurés » au journal). Anneau injoignable → 503 ; rien chez l'Anneau → 404 ; le faux Anneau des tests et de la démo passe par `ETAT["lire_anneau"]` ;
  - écran : tuiles « Réglages » et « Restaurer les réglages » en tête de `pages/Reglages.svelte` ; Connexion (`Services.svelte`, jusqu'à 0.7.0) renvoyait vers Réglages pour Wikidata ;
  - nettoyage : `maison.mot_de_passe()` sans ancien nom ; `COMPTOIR_PASSWORD` et `COMPTOIR_RECHERCHE_WEB` retirés du compose ; `MAISON_JETON` ajouté (il faut maintenant le donner au conteneur pour la sauvegarde) ;
  - variables lues : `MAISON_PASSWORD`, `MAISON_JETON` (et `MAISON_JETON_ANCIEN`, `MAISON_ANNEAU_URL` par le module), `COMPTOIR_MISTRAL_CLE`, `COMPTOIR_RECHERCHE_WEB` (premier démarrage seulement), et les techniques `COMPTOIR_DATA`, `COMPTOIR_PORT`, `COMPTOIR_MISTRAL_URL`, `COMPTOIR_MISTRAL_MODELE` (hors stack) ;
  - **déploiement en deux temps** : d'abord la nouvelle image avec la stack actuelle (les réglages sont repris des anciennes variables au premier démarrage), vérifier Réglages, puis la nouvelle stack sans les anciennes lignes (`COMPTOIR_PASSWORD`, `COMPTOIR_RECHERCHE_WEB`) et avec `MAISON_JETON` ;
  - attention : la 0.6 ne lit plus `COMPTOIR_PASSWORD` ; si `MAISON_PASSWORD` n'est pas encore dans le conteneur Comptoir, elle ne démarre pas ;
  - **jamais essayé sur la vraie installation** (ni la reprise, ni la collecte par l'Anneau, ni la restauration).
- **0.5.0** (16/11/2026) : variable commune (module `app/maison.py`, copie du socle : ne pas le modifier ici, `python tools/diffuser_maison.py ../comptoir` depuis le socle ; contrat 2 depuis la 0.6). `config.charger` lisait `MAISON_PASSWORD`, repli sur l'ancien nom (retiré en 0.6). Ni jeton entre applis, ni adresse d'une autre appli, ni lecture seule (Comptoir n'écrit chez aucun service). Jamais essayé sur la vraie installation : les nouvelles variables ne sont pas encore dans la stack.
- **0.4.1** : rattachement des ingrédients guidé par le premier mot (`TETES` dans `ingredients.py`) ; 233 nœuds ; Mon bar sans doublon pour les familles sans variante.
- **0.4.0** : verres (1 à 50) ou litres (0,1 à 20) — `Portions.svelte`, `volumeVerre` et `dose` dans `donnees.svelte.js` ; Préparer reçoit `?verres=` ou `?litres=`.
- **0.3.1** : toutes les listes de noms de A à Z (`cle_alpha` dans `main.py`, `localeCompare('fr')` côté écran).
- **0.3.0** : carte zoomable (d3-zoom), retour qui garde le lieu choisi et la position (`vues` dans `donnees.svelte.js`, positions par adresse dans `App.svelte`), pastilles faisable / favori.
- **0.2.3** : variantes entre parenthèses rattachées au nom, rubriques mises en titre, conseils jamais lus comme recettes, chiffres romains. Le conseil « ordre de préparation » de l'essai est vide dans l'EPUB lui-même (Scriptorium n'a gardé que les numéros de la liste).
- **0.2.1** : la note en étoiles mise en titre par le livre ne remplace plus le nom (318 recettes touchées dans l'essai) ; corbeille : « Effacer maintenant », « Réimporter à neuf ». Un livre importé avant se relit ainsi : le redéposer et choisir « Réimporter à neuf » (0.2.2 : plus besoin de le supprimer d'abord).
- **0.2.0** : réglé sur un vrai livre (2 978 recettes, deux colonnes) ; onglet **Conseils** dans Cocktails ; rubriques et étoiles du livre sur la fiche ; écran **Connexion** des services ; 43 tests.
  - sonde : `sonde.py` hors dépôt, sur le livre réel, qui n'entre **jamais** dans le dépôt ; les cas rencontrés sont refaits en inventé dans `tools/fabrique.py` (`livre_deux_colonnes`) ;
  - restent 195 lignes sans ingrédient reconnu sur 13 338 (vraies absences de l'arbre : liqueur de yaourt, sève de bouleau, mascarpone…), 42 recettes sans préparation trouvée, une poignée de recettes lues comme des conseils puis écartées.
- **0.1.1** : icône de Comptoir.
- **0.1.0, temps 1 du dossier** (`docs/dossier.md`) : l'appli pour la maison.
  - import d'EPUB déposés dans Réglages (refus clair d'un livre protégé par DRM, d'un doublon ; un livre en corbeille se restaure au lieu de se réimporter) ;
  - découpage par règles (titre, lignes d'ingrédients, préparation, chapeau), indice de confiance, recettes douteuses dans À traiter ;
  - **page du livre papier** lue dans les repères EPUB 3 (`epub:type="pagebreak"`), « p. 42 » ou « p. 42-43 », rien sans repères ; le « p. 42 » visible de Scriptorium est retiré du texte ;
  - photo du livre reprise en vignette WebP ;
  - arbre des ingrédients (`app/donnees/ingredients.yaml`, 164 nœuds), familles avec précision, équivalences, « toujours là », produits frais ;
  - faisables, « il manque 1 ou 2 », bouteille qui débloque le plus ; favoris ; filtres sans alcool et spiritueux ;
  - lieux évoqués par règles (`app/donnees/lieux.yaml`, 129 lieux, formes ambiguës vers À traiter), origine écrite dans le livre, origine lue dans Wikidata par la tâche de fond (lecture seule, une fois par recette) ; liste pays › région › ville et carte du monde embarquée ;
  - Mistral sur un clic pour relire une recette (texte de la recette seul, proposition validée à la main) ;
  - mode Préparer : plein écran, verres, étape par étape, ingrédients à cocher, écran gardé allumé ;
  - supprimer un livre : corbeille de 30 jours, restauration à l'identique, effacement par la tâche de fond ; le bar ne bouge pas ;
  - journal avec Annuler (corrections, rattachements, recettes écartées) ;
  - tests : 36 (serveur, faux Wikidata, faux Mistral, écran sur PC et iPhone par `tools/demo.py`).
- **Essayé sur la vraie installation (15/11/2026)** : 0.4.1 déployée sur le NAS, livre d'essai réimporté à neuf par l'interface, tuile dans l'Anneau, Wikidata et Mistral vérifiés depuis l'écran Connexion.
- **Jamais essayé sur la vraie installation** :
  - les conseils d'un livre complet : l'essai n'en a que neuf (glace, rolling, filtration fine, pilonnage…) ;
  - la tablette du bar, le HTTPS (écran allumé en mode Préparer), le zoom de la carte en pinçant.

## Prochaine étape
1. Quand le livre complet est scanné : le réimporter à neuf, relire les Conseils (thèmes, passages manquants ou en trop) et rattacher les ingrédients inconnus dans À traiter.
2. HTTPS par Tailscale Serve, puis essai sur la tablette du bar.
3. Temps 2 (carte des invités) après un nouveau passage au conseil. La liste à jour est dans Atlas (`reste_a_faire` de Comptoir).

## Pièges
- **Fiches « Connexion »** : le registre `SERVICES` vit au niveau du module et garde le dernier essai 30 s ; les tests le vident dans `fabriquer_client` (`main.SERVICES._dernier.clear()`). Wikidata « Pas relié » montre « Pour le relier, dans la stack : Réglages › … » (libellé de la fiche commune) alors que c'est un réglage de l'appli.
- **Écran allumé** : l'API Wake Lock ne marche qu'en HTTPS. Ouvert en http par Tailscale, le mode Préparer le dit, et l'écran peut se mettre en veille. Pour la tablette : adresse Tailscale Serve en HTTPS (comme la caméra de Scriptorium).
- Dépôt public : aucun livre, aucune recette réelle, aucune valeur réelle. Les livres de test sont inventés.
- Le format des repères de page est celui que Scriptorium écrit depuis sa 0.2.2 : s'il change, les pages disparaissent ici (test `test_import_et_pages_du_livre_papier`).
- La carte du monde (world-atlas 110 m) a des pays sans identifiant : la boucle est indexée par le rang, pas par l'identifiant.
- `/health` est public et ne rend que des nombres (faisables, à traiter) pour la tuile de l'Anneau.
- `/externe/…` n'est pas gardé par la session (le middleware ne garde que `/api/…`) : chaque route `/externe/` vérifie elle-même le jeton commun.
- Un nouveau réglage d'usage : l'ajouter dans `REGLAGES` (le type de la valeur par défaut fixe son type), son nom dans `NOMS_REGLAGES` (`main.py`), son champ dans la tuile Réglages ; jamais un secret (la clé Mistral reste dans la stack).
- **Conseils** : un passage sans recette est gardé s'il a 200 caractères de texte et au moins un paragraphe de 120 ; même titre ailleurs dans le livre → le plus complet ; une section à rubriques (« VERRE : ») est une recette mal lue, jamais un conseil. Un « Conseil du barman » démarre toujours son propre passage (sinon il est avalé par l'encadré précédent).
- **Deux colonnes** : l'appariement quantités / noms ne se fait que si les deux nombres concordent ; sinon rien n'est recollé et la recette part dans À traiter.
- **Faux titres** : un titre sans lettre n'est jamais un nom de recette (`sans_faux_titres`). La note sous un nom est une note ; seule, elle ouvre une recette « Sans nom » (À traiter), sinon deux recettes se fondent.
- **Carte** : le zoom se lit après la fin de son animation (250 à 450 ms) ; un test qui le compare doit attendre.
- **Litres** : le volume d'un verre ne compte que les lignes avec une quantité et une unité de volume (cl, shot, cuillères, trait, goutte…) ; une recette faite surtout de « compléter avec… » donne un verre trop petit, donc trop de verres pour un litre.
- **Rattachement** : le premier mot du nom (liqueur, crème, sirop, soda, jus…) fixe la catégorie permise (`TETES`). Un alias exact passe toujours ; un alias qui commence par ce mot aussi, sauf s'il n'est que ce mot (« crème » ne prend pas « crème de fraise »). Ajouter un alias exact quand une crème est un produit laitier ou un jus (crème de noix de coco).
- Navigation à six entrées (plafond du socle) : les Conseils sont un onglet de Cocktails, pas une entrée de plus.

## Décisions tranchées
Voir `docs/dossier.md` (v0.4) : temps 1 sans carte des invités ni allergènes (temps 2, nouveau conseil), corbeille de 30 jours, rien n'est inventé pour un livre sans repères de page.
