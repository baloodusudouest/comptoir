# Journal des versions

## 0.2.1 — 14 novembre 2026
- Corrigé : 318 recettes du livre d'essai avaient pour nom leurs étoiles (« ★★★★☆ »). Le livre écrit la note, et parfois un « 0 », comme des titres sous le nom du cocktail. Ces faux titres sont écartés et la note est lue comme note. Le nom est cherché au-dessus, même séparé par une image ou un parasite du scan (« O-E »), ou écrit en simple paragraphe en capitales. Une note sans aucun nom au-dessus donne une recette « Sans nom, p. N » envoyée dans À traiter, au lieu de se fondre dans la précédente.
- Petits parasites du scan (moins de trois lettres) écartés du chapeau.
- Corbeille : **Effacer maintenant** ; et en redéposant un livre qui est dans la corbeille, **Réimporter à neuf** (relu avec le découpage de la version installée) à côté de « Restaurer tel quel ».
- 45 tests.

## 0.2.0 — 14 novembre 2026 — réglé sur un vrai livre
- Découpage réglé sur un vrai livre de 2 978 recettes mis en page en deux colonnes : toutes ont leur page, 1 806 leur photo ;
  les lignes d'ingrédients sans ingrédient reconnu passent de 232 à 195 sur 13 338.
  - colonnes de quantités suivies de colonnes de noms (« 30 ml », « 15 ml »… puis « de rhum… », « de xérès… ») : appariées dans l'ordre quand les nombres concordent ;
  - rubriques du livre (Verre, Déco, Méthode, Mon avis, Origine, Variante, Autre nom) et note en étoiles rangées à part ; la préparation est tirée de « Méthode » ;
  - lieu de création lu d'abord dans les parenthèses de la rubrique « Origine » ;
  - arbre des ingrédients porté à 213 nœuds (marques, liqueurs, thé, herbes…).
- **Conseils** : nouvel onglet de Cocktails. Les passages du livre qui ne sont pas des recettes (glace, techniques, verres, matériel…) y sont rangés par thème, avec leur page ; recherche et filtre par thème. Les encadrés répétés (légende des étoiles) sont écartés.
- Fiche : note du livre en étoiles, verre et déco, « Dans le livre » (avis, origine, variante). Le mode Préparer montre le verre et la déco.
- Écran **Connexion** (format commun) : une tuile par service (Wikidata, Mistral), avec voyant, ce qu'il lit, ce qu'il écrit, réglage, derniers appels et Vérifier. Sorti des Réglages.
- Base d'une 0.1 mise à niveau au démarrage (colonnes `infos` et `note`, table `conseil`). Un livre déjà importé n'a ni rubriques ni conseils : le supprimer puis le réimporter.
- Livres inventés des tests fabriqués à date fixe : le test du doublon en corbeille échouait au hasard (une seconde d'écart changeait l'empreinte).
- 43 tests (nouveau livre inventé en deux colonnes, mise à niveau de la base, écrans Conseils et Connexion).

## 0.1.1 — 14 novembre 2026
- Icône propre à Comptoir (verre à cocktail et rondelle d'orange amer), à la place de celle reprise du squelette.

## 0.1.0 — 14 novembre 2026 — temps 1 : l'appli pour la maison
- Import d'EPUB, découpage par règles, page du livre papier (repères EPUB 3), photos.
- Mon bar (familles avec précision, équivalences, produits frais), faisables, « il manque 1 ou 2 », bouteille qui débloque le plus, favoris.
- Lieux évoqués (règles) et lieu de création (livre, puis Wikidata en lecture seule), liste et carte du monde embarquée.
- À traiter : recettes douteuses, ingrédients inconnus, origines, lieux ambigus ; Mistral sur un clic.
- Mode Préparer (verres, étapes, ingrédients à cocher, écran allumé en HTTPS).
- Supprimer un livre : corbeille de 30 jours. Journal avec Annuler.
- 36 tests (serveur et écran PC / iPhone).

## Conception — 14 novembre 2026 (v0.3 du dossier)
- Supprimer un livre supprime tous ses cocktails, avec une corbeille de 30 jours ; le bar ne change pas.
- Page du livre papier sur chaque recette (« p. 42 » ou « p. 42-43 »), lue dans les repères de page EPUB 3 ; rien quand l'EPUB n'en a pas.

## Conception — 14 novembre 2026
- Dossier de conception v0.2 (`docs/dossier.md`), après le grill et le passage au conseil : sonde sur un vrai livre d'abord, livraison en deux temps, carte des invités et allergènes reportées au temps 2, mode Préparer testé sur téléphone et PC.
