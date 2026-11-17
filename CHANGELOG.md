# Journal des versions

## 0.6.2 — 17 novembre 2026 (connexion plus sûre)
- **Connexion plus sûre** (audit du 17/11/2026, même correctif dans toutes les applis maison) :
  - un cookie portant un caractère non ASCII donnait une erreur 500 sur toute l'API ; il est maintenant simplement refusé ;
  - les clés qui signent les cookies (celui de l'appli et le cookie commun `maison_session` posé par l'Anneau) sont tirées du mot de passe par PBKDF2 : un cookie capté sur le réseau local ne permet plus de chercher le mot de passe à grande vitesse. **Toutes les applis doivent être à jour ensemble** ; une seule reconnexion est demandée après la mise à jour ;
  - des essais de mot de passe lancés en parallèle ne contournent plus le délai : au-delà de 30 essais en 5 minutes, tout est refusé sans comparer.
- Module commun `maison.py` (socle 0.7.0) : l'annuaire de l'Anneau est relu 30 s après un échec (avant : 10 min sans adresses après un redémarrage de la stack) ; un réglage `nan` ou infini est refusé ; un `reglages.json` abîmé est mis de côté (`.corrompu`) au lieu d'être écrasé.

## 0.6.1 — 17 novembre 2026 (corrections de l'audit)
- **Bug** : une réponse de Wikidata qui n'est pas du JSON (portail, panne) faisait sauter la purge horaire de la corbeille ; un livre supprimé pouvait rester au-delà des 30 jours. La purge a maintenant son propre essai, et ces réponses sont notées comme une erreur ordinaire de Wikidata.
- **Plus rapide** : la reconnaissance d'un ingrédient compile ses 712 motifs une seule fois (avant : 58 ms par nom inconnu, recompilés à chaque fois). L'import d'un livre en profite.
- Intégration continue : l'image n'est plus publiée si les tests échouent.

## 0.6.0 — 16 novembre 2026
- **Réglages dans l'appli** : la recherche d'origine dans Wikidata s'allume et se coupe dans Réglages (interrupteur), plus dans la stack. Au premier démarrage, Comptoir reprend la valeur de l'ancienne ligne `COMPTOIR_RECHERCHE_WEB` (une ligne au journal le dit), puis ne la lit plus jamais. Les réglages sont gardés dans `reglages.json`, dans le dossier de données.
- **Sauvegarde par l'Anneau** : nouvelle adresse `/externe/sauvegarde`, ouverte seulement avec le jeton commun `MAISON_JETON`, qui rend les réglages et la version (jamais la clé Mistral, ni mot de passe, ni chemin). Sans `MAISON_JETON`, l'adresse est fermée.
- **Restaurer les réglages** (Réglages) : choisir une nuit sauvegardée par l'Anneau, voir ce qui changerait (actuel → sauvegardé), confirmer. Ni les livres, ni le bar, ni les favoris ne bougent. Anneau injoignable ou rien de sauvegardé : un message le dit.
- **Anciens noms retirés** : `COMPTOIR_PASSWORD` n'est plus lu, seul `MAISON_PASSWORD` compte (sans lui, Comptoir ne démarre pas).
- Connexion : la tuile Wikidata renvoie vers Réglages quand la recherche est coupée.
- Tests : reprise puis variable ignorée, changement de réglage et mauvais type, porte de sauvegarde (jeton commun seul, aucun secret), restauration (dates, différences, application, Anneau injoignable), écran Réglages et Restaurer sur PC et iPhone. 67 tests.

## 0.5.0 — 16 novembre 2026
- **Variable commune de la maison** (module `app/maison.py` du socle 0.5.0, copié tel quel) : le mot de passe est lu dans `MAISON_PASSWORD`, avec repli sur `COMPTOIR_PASSWORD`.
- Comptoir n'échange avec aucune autre appli maison et n'écrit chez aucun service : pas de jeton commun ni de lecture seule.
- Rien ne change tant que la stack n'a pas la nouvelle variable : l'ancien nom reste lu.
- Tests : mot de passe commun puis repli, copie du module non retouchée. 54 tests.

## 0.4.1 — 14 novembre 2026
- Corrigé : un ingrédient était rattaché au mot connu le plus long contenu dans son nom, sans regarder ce qu'il était. « Liqueur de pomme » devenait du jus de pomme, « soda au gingembre » du gingembre, « crème de fraise » des fruits rouges, « sirop de marasquin » la liqueur. Désormais le premier mot (liqueur, crème, sirop, soda, jus, nectar, bitter, eau-de-vie…) dit la catégorie, et le rattachement doit y appartenir ; une marque reste acceptée (« liqueur Galliano »). Sur le livre d'essai, 233 lignes sont mieux rattachées.
- Arbre des ingrédients : 233 nœuds. Nouveaux : liqueurs de pomme, de miel, d'ananas, de pamplemousse, de fruit de la passion, de whisky, de thé ; crèmes de fraise, de myrtille, de citron, de châtaigne, de prune, de figue, de noyaux ; cordial de citron vert, sirop de marasquin, sirop de cannelle ; soda au pamplemousse, bitter lemon.
- Mon bar : une famille sans variante (Liqueur de banane) n'apparaît qu'une fois, sans son nom répété au-dessus.
- Un livre déjà importé garde ses anciens rattachements : le redéposer et choisir « Réimporter à neuf ». 53 tests.

## 0.4.0 — 14 novembre 2026
- **Verres ou litres** sur la fiche et en mode Préparer : un nombre de verres (1 à 50, au lieu de 8), ou un volume en litres (0,1 à 20 l, au quart de litre ou saisi) pour un pichet ou un punch. En litres, l'appli dit à combien de verres cela correspond (« ≈ 10 verres de 11 cl, avant la glace »). Le volume d'un verre est celui des ingrédients mesurés : un « compléter avec… » sans quantité ne compte pas.
- Quantités : au-delà d'un litre, les cl passent en litres ; ce qui se compte (feuilles, zestes, œufs) s'arrondit au demi quand le facteur n'est pas entier.
- Le choix (verres ou litres) suit dans le mode Préparer.
- 52 tests.

## 0.3.1 — 14 novembre 2026
- Listes de A à Z, à la française (« Écorce » avec les E, majuscules ignorées, guillemets du début ignorés : « Two Guns » Miller aux T) : ingrédients de À traiter et des Réglages, Mon bar (catégories, familles, variantes), lieux de Par lieu (le nombre de cocktails reste affiché), recettes.
- 50 tests.

## 0.3.0 — 14 novembre 2026
- **Carte du monde zoomable** : molette et glisser sur PC, pincer et glisser au doigt, double-clic, boutons + / − / Recentrer. Les noms des pays qui ont des cocktails apparaissent à partir du zoom ×2, ceux des villes à partir de ×4 ; choisir un lieu centre la carte sur lui. Traits et points gardent leur épaisseur.
- **Retour** depuis un cocktail : Cocktails retrouve le lieu choisi, la carte ou la liste, « créé à / évoque », le zoom de la carte, les filtres de la liste et la position dans la page.
- **Pastilles** sur les vignettes, lisibles sur les photos à fond blanc : coche verte = j'ai de quoi le faire ; étoile = favori.
- 49 tests.

## 0.2.3 — 14 novembre 2026
- La variante écrite entre parenthèses sous le nom (« (FORMULE CLASSIQUE) », « (RECETTE DIFFORD) », en titre ou en paragraphe) est rattachée au nom : « Blood & Sand (Formule classique) », « Blood & Sand (Recette Difford) ». Avant, elle devenait le nom ou deux variantes portaient le même.
- Une rubrique mise en titre par le livre (« VERRE: martini ») reste une rubrique au lieu de devenir le nom d'une recette.
- Un « Conseil du barman » n'est plus jamais lu comme une recette (5 fausses recettes dans l'essai).
- Chiffres romains gardés en capitales dans les noms (« Amaretto Sour II »).
- Livre d'essai : 2 973 recettes, 176 lignes sans ingrédient reconnu sur 13 319. 47 tests.

## 0.2.2 — 14 novembre 2026
- Redéposer un livre déjà importé propose **Réimporter à neuf** en un clic (il passe par la corbeille et y est effacé), au lieu d'un simple refus. Plus besoin de le supprimer d'abord.
- 47 tests.

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
