# Reprise — Comptoir

À lire en premier ; mis à jour dans le même commit que le code.

## État (14/11/2026)
- **Conception terminée** : grill, passage au conseil, dossier v0.2 (`docs/dossier.md`). Aucun code.
- Livraison en deux temps : temps 1 = l'appli pour la maison ; temps 2 = carte des invités et allergènes, après usage et un nouveau conseil.

## Prochaine étape
- **Sonde** (étape 0 du plan) : un script lit un vrai livre EPUB sans DRM, en dehors de ce dépôt, et relève les recettes propres, les recettes à traiter, les ingrédients hors de l'arbre et la couverture de Wikidata pour l'origine. Le résultat décide si « créé à » entre dans la V1.
- Puis : copie du socle (`baloodusudouest/socle`), nom, couleur `#e0884a`, mot de passe, `/health`.

## Pièges
- Dépôt public : aucun livre, aucune recette réelle, aucune valeur réelle (adresses, noms, chemins). Le livre de test est inventé.
- Un EPUB protégé par DRM ne s'importe pas : le dire clairement à l'import.
- Le mode Préparer est codé et testé sur téléphone et PC ; l'essai sur la tablette du bar reste à faire.
