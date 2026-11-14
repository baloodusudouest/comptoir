# Comptoir

Les cocktails de la maison : Comptoir lit des livres de cocktails en EPUB, compare leurs recettes au bar déclaré, et montre ce qui est faisable ce soir, ce à quoi il manque 1 ou 2 ingrédients, et la bouteille qui en débloquerait le plus. Favoris, recherche par lieu (lieu de création, lieu évoqué par le nom), page du livre papier sur chaque recette, mode Préparer étape par étape.

Appli maison auto-hébergée (FastAPI + Svelte, une image Docker `ghcr.io/baloodusudouest/comptoir`), au format commun des applis du dépôt `baloodusudouest/socle`.

- Lire d'abord `REPRISE.md`, puis `docs/dossier.md`.
- Déployer : `docker-compose.yml` et `.env.example`.
- Démonstration locale : `cd frontend && npm ci && npx vite build && cd .. && python -m tools.demo` (mot de passe `demo-demo-demo`).
