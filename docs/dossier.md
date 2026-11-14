# Comptoir — dossier de conception

Version 0.2 du dossier, 14/11/2026. Écrit après un grill (questions de cadrage), puis revu après un passage au conseil (cinq avis indépendants, relecture croisée, synthèse).
Couleur : orange amer `#e0884a`.

Version publique : les valeurs réelles (adresses, noms, chemins) passent par les variables de la stack, jamais par ce dépôt.

**Changements depuis la v0.1 (après le conseil)**
- **Sonde avant le code** : un vrai livre EPUB sans DRM passe dans le découpeur en script brut. Le résultat décide des lieux.
- **Livraison en deux temps** (avant : un seul bloc).
- **Pas de page invités en V1** : la carte pour les invités de la chambre d'hôte et les allergènes passent au temps 2, avec les exigences du conseil (§ 7).
- **Lieux selon la sonde** : dans la V1 si la couverture de Wikidata est correcte ; sinon « évoque » seul, et « créé à » plus tard.
- **Mode Préparer codé et testé tout de suite sur téléphone et PC** ; seul l'essai sur la tablette du bar reste à faire.

---

## 1. Besoin

Le foyer a des livres de cocktails en EPUB, tous en français. Il veut :

1. **Importer plusieurs livres**, en les déposant dans l'appli. Chaque recette garde son livre d'origine et sa photo quand le livre en a une.
2. **Déclarer son bar** (ce qu'il y a à la maison) et voir :
   - les cocktails **faisables maintenant** ;
   - ceux auxquels **il manque 1 ou 2 ingrédients**, avec le nom de l'ingrédient qui manque ;
   - **la bouteille qui débloquerait le plus de cocktails**.
3. **Marquer des favoris.** Le bar et les favoris sont communs au foyer, derrière le mot de passe commun des applis maison.
4. **Chercher par lieu**, de deux sortes, toujours distinguées sur la fiche :
   - **créé à** : pays, région, ville où le cocktail a été inventé ;
   - **évoque** : le lieu suggéré par le nom (Mexican Mule → Mexique, London Mule → Angleterre / Londres, Moscow Mule → Moscou / Russie).
   La part de « créé à » livrée en V1 dépend de la sonde (§ 2).
5. **Préparer un cocktail** en mode plein écran : écran toujours allumé, nombre de verres, étape par étape, ingrédients à cocher. Utilisé sur téléphone et PC dès la V1, et plus tard sur une tablette posée au bar.
6. **Une tuile dans l'Anneau** (le portail des applis maison).

Temps 2, après usage : **carte des cocktails pour les invités de la chambre d'hôte**, filtrée selon leurs allergies (§ 7).

Hors périmètre : export vers Mealie (il ne sait pas importer d'EPUB, ni gérer des familles d'ingrédients, ni des lieux hiérarchisés ; un bouton « envoyer à Mealie » viendra plus tard).

Écrans : **PC** pour importer et corriger, **téléphone** au quotidien, **tablette** au bar plus tard.

Fréquence : quelques livres importés une fois ; consultation fréquente, surtout le soir.

---

## 2. Technique

### Étape 0 : sonde sur un vrai livre

Avant tout code d'interface : un script lit un vrai EPUB (sans DRM : un livre protégé ne s'importe pas, l'appli le dira clairement) et relève :
- le nombre de recettes trouvées, propres, et douteuses ;
- les libellés d'ingrédients qui ne trouvent pas leur place dans l'arbre ;
- pour les mêmes recettes, la part dont Wikidata ou Wikipédia en français donne l'origine.

Lecture des résultats :
- plus de 30 % de recettes douteuses → les règles sont revues avant d'aller plus loin (l'appli ne doit pas devenir un outil de saisie) ;
- origine trouvée pour une part correcte des recettes (seuil fixé au vu des chiffres) → « créé à » dans la V1 ; sinon « évoque » seul en V1.

Le livre réel n'entre jamais dans ce dépôt ; le compte rendu de la sonde ne contient que des chiffres et des exemples anonymisés.

### Pile

Socle commun des applis maison : FastAPI (Python 3.12) + Svelte 5 + Tailwind 4, une seule image Docker multi-étapes, SQLite dans `/data`. Port proposé **8092**.

### Import d'un EPUB

1. **Dépôt** du fichier `.epub` dans l'appli (PC). Le fichier est gardé dans `/data/livres/` ; une empreinte (SHA-256) évite de réimporter le même livre. Un fichier protégé par DRM est refusé avec un message clair.
2. **Lecture de la structure** : `ebooklib` pour le paquet, `selectolax`/`lxml` pour le XHTML de chaque chapitre. Titre et auteur du livre lus dans les métadonnées OPF.
3. **Découpage par règles** : une recette = un titre (`h1`–`h3` ou classe récurrente), suivi d'une liste d'ingrédients (liste `ul/ol` ou lignes commençant par une quantité), puis d'un texte de préparation. Les règles apprennent la forme dominante du livre sur ses premières recettes (balise du titre, classe des ingrédients) et l'appliquent au reste.
4. **Lecture des lignes d'ingrédients** : quantité (nombre, fraction, « trait », « zeste », « feuilles »), unité (cl, ml, oz → converti en cl, cuillère, trait), nom. Le nom est rapproché d'un **ingrédient de référence** (voir familles).
5. **Indice de confiance** par recette : titre trouvé, au moins deux ingrédients lus, chaque ligne reconnue, préparation présente. Sous le seuil, la recette part dans **À traiter**.
6. **Recettes douteuses** : correction à la main dans un éditeur, ou **envoi à Mistral sur clic** (`COMPTOIR_MISTRAL_CLE`). Mistral reçoit le texte brut de la recette seulement et rend un JSON (titre, ingrédients avec quantité/unité/nom, étapes, origine si écrite). Le résultat est montré à côté de l'original pour validation, jamais enregistré seul.
7. **Photos** : l'image la plus proche du titre dans le XHTML (même chapitre, avant la recette suivante) est associée, recadrée en vignette WebP et gardée dans `/data/photos/`. Sans photo : vignette sobre à la couleur de l'appli.
8. **Origine écrite dans le livre** : recherche dans le chapeau et la préparation de motifs du type « créé à… », « inventé par … au … bar de … », « né à … en 19.. ». Ce qui est trouvé devient un lieu « créé à » de source *livre*.

### Familles d'ingrédients (« avec précision »)

Arbre à trois niveaux : **catégorie** (Spiritueux, Liqueurs, Vins & bulles, Sirops, Jus & fruits, Sodas, Amers, Produits laitiers & œufs, Épices & herbes, Garnitures) → **famille** (Rhum, Gin, Whisky…) → **variante** (rhum ambré, rhum blanc, rhum agricole…).

Règle de correspondance :
- la recette demande une **famille** (« rhum ») → n'importe quelle variante du bar convient ;
- la recette demande une **variante** (« rhum blanc ») → il faut cette variante ;
- **équivalences** fixes et courtes, validées dans Réglages (ex. « jus de citron vert » = « citron vert » frais). Pas de remplaçants approximatifs.

L'arbre de départ est livré avec l'appli (fichier YAML versionné, ~300 ingrédients courants des livres de cocktails français), puis complété par la sonde. Un nom de livre inconnu donne une proposition de rattachement par similarité de texte ; sans proposition sûre, il part dans **À traiter** (« Nouvel ingrédient : *liqueur de violette* → rattacher à… »).

Les ingrédients « toujours là » (eau, glaçons, sucre, sel) sont cochés par défaut et masquables.

### Propositions

Calcul en mémoire à chaque changement du bar (quelques milliers de recettes au plus) :
- **Faisable** : tous les ingrédients non facultatifs satisfaits (garnitures marquées facultatives par les règles : « zeste pour décorer », « cerise »).
- **Il manque 1 ou 2** : liste des manquants.
- **Bouteille qui débloque le plus** : pour chaque ingrédient absent, nombre de recettes qui deviennent faisables s'il est ajouté ; les trois premiers sont affichés.

### Lieux

Table des lieux hiérarchique : pays → région → ville, avec coordonnées. Données de départ embarquées (GeoNames `cities15000` filtré + régions + pays, noms français), quelques Mo, sans appel extérieur pour la carte.

**Évoque** (par règles, sans IA, dans la V1 dans tous les cas) :
- dictionnaire de noms de lieux et de **gentilés** en français et en anglais (mexican, london, moscow, cubain, normand, parisien, havana, tokyo, scotch → Écosse…) ;
- cas sûrs posés seuls ;
- cas ambigus → **À traiter** : nom de lieu qui est aussi un mot courant (« Paloma »), quartier ou lieu indirect (« Manhattan », « Bronx », « Singapore Sling »), gentilé trompeur (« Black Russian » évoque la Russie mais n'y a pas été créé : les deux champs restent séparés).

**Créé à** (dans la V1 si la sonde le justifie), dans cet ordre :
1. ce que dit le livre (source *livre*) ;
2. sinon recherche dans **Wikidata** (pays d'origine `P495`, lieu de création, coordonnées), puis dans l'infobox de **Wikipédia en français** ;
3. résultat douteux (plusieurs candidats, homonyme, origine disputée) → **À traiter** ;
4. rien → « origine inconnue ».

La recherche se fait depuis le serveur, une fois par nouvelle recette, avec cache. Wikidata relie déjà des cocktails à leurs ingrédients (propriété `P186`), mais l'origine est souvent absente ou disputée (Margarita, Old Fashioned) : d'où la mesure de la sonde.

Chaque lieu a une **source** (livre, Wikidata, Wikipédia, règle, main) et un état (sûr, à vérifier, validé).

### Lien avec l'Anneau

`/health` rend le nombre de cocktails faisables pour la tuile de l'Anneau, et le nombre de cas dans À traiter comme « action à faire ».

### Sécurité

- `COMPTOIR_PASSWORD`, obligatoire : sans lui, le conteneur ne démarre pas ; cookie commun `maison_session` accepté.
- Aucune adresse à jeton en V1 (la porte `/ha/…` et `/invite/<jeton>` vient avec le temps 2).
- Comptoir n'écrit chez **aucun** service extérieur : pas de mode lecture seule nécessaire. Watchtower désactivé, comme pour les autres applis maison.
- Appels sortants : Wikidata et Wikipédia (lecture, si « créé à » est retenu), Mistral (sur clic seulement). Chaque appel est journalisé (date, cible, recette).
- Rien de personnel dans ce dépôt public : aucun livre, aucune recette réelle dans les tests (livre EPUB de test inventé).

### Variables de la stack (V1)

```
COMPTOIR_PASSWORD=          # mot de passe commun des applis maison, obligatoire
COMPTOIR_MISTRAL_CLE=       # clé d'API Mistral, facultative (sans elle, pas d'envoi à Mistral)
COMPTOIR_RECHERCHE_WEB=oui  # « non » : aucune recherche Wikidata / Wikipédia
```

Volume : `/data` (comptoir.db, livres/, photos/, cache/).

---

## 3. Parcours des clics et des écrans

Navigation : rail à gauche sur PC, pilule en bas sur téléphone. Cinq entrées : **Au bar** (ouverture), **Cocktails**, **Mon bar**, **À traiter**, **Réglages**. Pas d'écran Connexion de services : les sources extérieures (Wikidata, Mistral) sont dans Réglages, avec un voyant et un bouton **Vérifier**.

Le geste répété est « je veux un cocktail ce soir » : il ne passe pas derrière une tuile, d'où l'ouverture sur **Au bar**.

### Au bar (ouverture)
- En tête : nombre de cocktails faisables, recherche par nom.
- Bandeau « Faisables maintenant » (vignettes photo, nom, lieu évoqué en petit), puis « Il te manque 1 ou 2 » avec l'ingrédient manquant en orange.
- Encart « Une bouteille pour débloquer le plus » : 3 ingrédients, chacun « +12 cocktails ».
- Filtres rapides en pastilles : Favoris, Sans alcool, spiritueux de base, Lieu.
- Clic sur une vignette → **Fiche cocktail**.

### Cocktails
- Liste de toutes les recettes, filtres : livre, spiritueux, faisable/il manque/tout, favoris.
- Onglet **Par lieu** : liste emboîtée pays > région > ville avec compteurs, interrupteur « créé à / évoque / les deux » (seulement « évoque » si « créé à » n'est pas retenu) ; bouton **Carte** : carte du monde embarquée, un point par lieu avec son nombre ; clic sur un point → liste filtrée.

### Fiche cocktail
- Photo, nom, livre et page, étoile Favori.
- Lieux : « Créé à : La Havane, Cuba (livre) » ; « Évoque : Mexique (règle) ». Clic sur un lieu → liste de ce lieu.
- Ingrédients avec quantités, ceux qui manquent en orange ; sélecteur du nombre de verres (1 à 8).
- Préparation.
- Bouton **Préparer** → mode Préparer. Bouton **Corriger** → éditeur.

### Mode Préparer (téléphone, PC, puis tablette)
- Plein écran, très grands caractères, écran maintenu allumé (Wake Lock du navigateur, avec repli sur une vidéo muette si l'API manque).
- Ingrédients à cocher, quantités recalculées pour le nombre de verres.
- Étape en cours en gros, boutons Précédent / Suivant larges (60 px de haut au moins), utilisables mains mouillées ; balayage gauche/droite.
- La pilule de navigation s'efface ; un lien « Quitter » en haut.
- Mise en page qui s'adapte : une colonne sur téléphone, deux colonnes (ingrédients | étape) à partir de la largeur d'une tablette.

### Mon bar
- Ingrédients trouvés dans les livres, par catégorie puis famille, cases à cocher ; recherche pour filtrer la liste.
- Marque « à racheter souvent » sur les produits frais (citron, menthe…) : pastille, et regroupement en tête.
- Compteur « ce bar permet N cocktails » mis à jour à chaque case.

### À traiter (grille de tuiles)
- **Recettes à vérifier** (découpage douteux) → original à gauche, recette lue à droite ; boutons Valider, Corriger, **Envoyer à Mistral**, Ignorer (ce n'est pas une recette).
- **Nouveaux ingrédients** → rattacher à une famille/variante ou créer.
- **Origines à vérifier** (si « créé à » est retenu) → candidats Wikidata/Wikipédia avec leur source ; Choisir, Aucune, Saisir.
- **Lieux évoqués ambigus** → Oui / Non / Autre lieu.
- **Livres en cours d'import** → avancement, nombre de recettes lues et à vérifier.

### Réglages
- **Livres** : déposer un EPUB, liste des livres (recettes, à vérifier), retirer un livre.
- **Sources** : Wikidata/Wikipédia, Mistral : voyant, Vérifier, dernières demandes.
- **Équivalences** d'ingrédients.
- Journal des modifications avec Annuler (corrections, rattachements, lieux).
- Version, déconnexion.

---

## 4. Design

- Format commun des applis maison : toujours sombre, neutres chauds (`#151311`, `#1f1c19`, `#312c27`, `#f2ece2`, `#a89e91`), Inter, titres grands et fins, un seul bouton plein par bloc.
- Couleur de l'appli : **orange amer `#e0884a`** (onglet actif, compteurs, ingrédient manquant, bouton Préparer).
- **Signature** : un fin cercle de zeste d'orange autour du compteur de faisables ; noms de cocktails sur la fiche en capitales fines espacées, comme sur une carte de bar.
- Vignettes photo carrées, coins doux ; sans photo, une vignette unie à la couleur de l'appli avec l'initiale.
- Mode Préparer : contraste renforcé, texte de 28 px minimum pour les étapes, rien d'autre à l'écran.
- Animation sobre : apparition des vignettes, coche des ingrédients.

---

## 5. Schéma de données (SQLite, V1)

```
livre(id, titre, auteur, fichier, empreinte, importe_le, etat)
recette(id, livre_id, titre, slug, page_ref, chapeau, preparation_json, photo,
        confiance, etat[a_verifier|valide|ignore], source[regles|mistral|main], cree_le, modifie_le)
ligne_ingredient(id, recette_id, ordre, texte_original, quantite, unite, ingredient_id, facultatif)
ingredient(id, nom, parent_id, niveau[categorie|famille|variante], toujours_la, frais, sans_alcool)
ingredient_alias(id, ingredient_id, texte)                 -- noms vus dans les livres
equivalence(id, ingredient_a, ingredient_b)
bar(ingredient_id, ajoute_le)
favori(recette_id, ajoute_le)
lieu(id, nom, type[pays|region|ville|quartier], parent_id, lat, lon, geonames_id, wikidata_id)
lieu_recette(recette_id, lieu_id, sorte[cree_a|evoque], etat[sur|a_verifier|valide|refuse], source, preuve)
a_traiter(id, type, cible_id, donnees_json, cree_le, resolu_le)
journal(id, date, action, cible, avant_json, apres_json, annule)
appel_externe(id, date, service, cible, statut)
cache_web(cle, contenu, date)
```

Le temps 2 ajoutera `bouteille`, `allergene_bouteille`, `correspondance_allergene` et `invite_page` (§ 7).

---

## 6. Plan

### Temps 1 — l'appli pour la maison

0. **Sonde** sur un vrai livre (script brut), décision sur « créé à ».
1. Copie du socle : nom, couleur, mot de passe, `/health`, `REPRISE.md`, `CHANGELOG.md`.
2. Import EPUB par règles + livre de test inventé + tests du découpage.
3. Arbre des ingrédients, Mon bar, calcul faisables / il manque / bouteille qui débloque (tests du calcul).
4. Fiche cocktail, favoris, nombre de verres.
5. À traiter : recettes, ingrédients ; envoi à Mistral sur clic.
6. Lieux : « évoque » par règles ; « créé à » si retenu ; liste emboîtée et carte embarquée.
7. Mode Préparer, testé sur téléphone et PC.
8. Entrée dans la stack, tuile dans l'Anneau, tests d'écran PC et téléphone.

Livré et utilisé avant de commencer le temps 2.

### Temps 2 — la carte des invités (après usage)

Voir § 7. Nouveau passage au conseil, centré sur la page invités, avant de la coder.

### Restera à faire

- Essai du mode Préparer sur la tablette du bar (réglage d'affichage, veille, support).
- Temps 2 : carte des invités et allergènes.
- Export vers Mealie.
- « Créé à », si la sonde le renvoie à plus tard.

---

## 7. Temps 2 — carte des invités (cadrage gardé)

Reporté après le conseil. Exigences retenues pour la reprise :

- **Lecture dans Home Assistant** des allergies et des aliments non aimés saisis pour chaque chambre (noms des entités dans la stack, pas ici). Les notes privées des hôtes ne sont jamais lues. Page préparée par Home Assistant (`POST /ha/invite` avec un jeton, page `/invite/<jeton>` valable jusqu'à la fin du séjour, retirée à la remise à zéro de la chambre).
- **Bar à la bouteille** pour ce qui est montré aux invités : variante + marque (ou « maison »), allergènes **validés à la main** par les hôtes. Liste blanche : une bouteille non validée n'apparaît jamais. Bouteille remplacée par une autre marque → allergènes à revalider.
- **Allergènes** : les 14 réglementaires, proposés par règles et recherche web (Open Food Facts, fabricant), toujours validés à la main avant d'apparaître côté invités.
- **Refus d'affichage** si une allergie saisie dans Home Assistant n'est reliée à aucun des 14 : la page ne s'affiche pas et les hôtes sont prévenus.
- **Chambre d'enfants ou d'adolescents** : cocktails sans alcool uniquement.
- **Copie des allergies effacée** à la fin du séjour.
- **Mention visible** : liste indicative, risque de contamination croisée (shaker, sirops maison), demander aux hôtes au moindre doute.
- **Test de bout en bout** obligatoire avant mise en ligne : chambre fictive allergique aux fruits à coque, amaretto au bar, le cocktail ne doit pas apparaître.
- **À vérifier par les hôtes, hors de l'appli** : droit de montrer à des clients des recettes tirées de livres du commerce, et licence de débit de boissons. Ce n'est pas un avis juridique.
