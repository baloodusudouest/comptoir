# Reprise — Comptoir

À lire en premier ; mis à jour dans le même commit que le code.

## État (14/11/2026)
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
- **Jamais essayé sur la vraie installation** :
  - l'import du vrai livre par l'interface, sur le NAS (le découpage l'a lu ici, hors appli) ;
  - les conseils d'un livre complet : l'essai n'en a que neuf (glace, rolling, filtration fine, pilonnage…) ;
  - le vrai Wikidata et le vrai Mistral depuis le NAS ;
  - la tablette du bar.

## Prochaine étape
1. Déployer la 0.2.0 (service `comptoir` déjà dans `homelab.yml`, port 8092) et importer le livre d'essai par Réglages.
2. Quand le livre complet est scanné : le réimporter (supprimer l'essai d'abord), relire les Conseils (thèmes, passages manquants ou en trop) et les ingrédients inconnus dans À traiter.
3. Tuile dans l'Anneau (`services.yaml`, posé à la main).

## Pièges
- **Écran allumé** : l'API Wake Lock ne marche qu'en HTTPS. Ouvert en http par Tailscale, le mode Préparer le dit, et l'écran peut se mettre en veille. Pour la tablette : adresse Tailscale Serve en HTTPS (comme la caméra de Scriptorium).
- Dépôt public : aucun livre, aucune recette réelle, aucune valeur réelle. Les livres de test sont inventés.
- Le format des repères de page est celui que Scriptorium écrit depuis sa 0.2.2 : s'il change, les pages disparaissent ici (test `test_import_et_pages_du_livre_papier`).
- La carte du monde (world-atlas 110 m) a des pays sans identifiant : la boucle est indexée par le rang, pas par l'identifiant.
- `/health` est public et ne rend que des nombres (faisables, à traiter) pour la tuile de l'Anneau.
- **Conseils** : un passage sans recette est gardé s'il a 200 caractères de texte et au moins un paragraphe de 120 ; même titre ailleurs dans le livre → le plus complet ; une section à rubriques (« VERRE : ») est une recette mal lue, jamais un conseil. Un « Conseil du barman » démarre toujours son propre passage (sinon il est avalé par l'encadré précédent).
- **Deux colonnes** : l'appariement quantités / noms ne se fait que si les deux nombres concordent ; sinon rien n'est recollé et la recette part dans À traiter.
- **Faux titres** : un titre sans lettre n'est jamais un nom de recette (`sans_faux_titres`). La note sous un nom est une note ; seule, elle ouvre une recette « Sans nom » (À traiter), sinon deux recettes se fondent.
- Navigation à six entrées (plafond du socle) : les Conseils sont un onglet de Cocktails, pas une entrée de plus.

## Décisions tranchées
Voir `docs/dossier.md` (v0.4) : temps 1 sans carte des invités ni allergènes (temps 2, nouveau conseil), corbeille de 30 jours, rien n'est inventé pour un livre sans repères de page.
