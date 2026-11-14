# Reprise — Comptoir

À lire en premier ; mis à jour dans le même commit que le code.

## État (14/11/2026)
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
  - un vrai livre (le découpage n'a vu que les deux livres inventés de `tools/fabrique.py`) ;
  - le vrai Wikidata et le vrai Mistral depuis le NAS ;
  - la tablette du bar.

## Prochaine étape
1. **Le vrai livre** (EPUB fabriqué par Scriptorium) : l'importer, relever recettes propres / à vérifier / ingrédients inconnus et la part d'origines trouvées ; régler les règles de découpage et compléter l'arbre des ingrédients et les lieux. Le résultat décide si « créé à » reste affiché.
2. Déployer : service `comptoir` dans `homelab.yml`, variables `COMPTOIR_MISTRAL_CLE`, `COMPTOIR_RECHERCHE_WEB`, port 8092.
3. Tuile dans l'Anneau (`services.yaml`, posé à la main).

## Pièges
- **Écran allumé** : l'API Wake Lock ne marche qu'en HTTPS. Ouvert en http par Tailscale, le mode Préparer le dit, et l'écran peut se mettre en veille. Pour la tablette : adresse Tailscale Serve en HTTPS (comme la caméra de Scriptorium).
- Dépôt public : aucun livre, aucune recette réelle, aucune valeur réelle. Les livres de test sont inventés.
- Le format des repères de page est celui que Scriptorium écrit depuis sa 0.2.2 : s'il change, les pages disparaissent ici (test `test_import_et_pages_du_livre_papier`).
- La carte du monde (world-atlas 110 m) a des pays sans identifiant : la boucle est indexée par le rang, pas par l'identifiant.
- `/health` est public et ne rend que des nombres (faisables, à traiter) pour la tuile de l'Anneau.

## Décisions tranchées
Voir `docs/dossier.md` (v0.3) : temps 1 sans carte des invités ni allergènes (temps 2, nouveau conseil), corbeille de 30 jours, rien n'est inventé pour un livre sans repères de page.
