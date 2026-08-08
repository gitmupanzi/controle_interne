# Tests et limites Perfect Vision

## Tests attendus

| Scénario | Comportement protégé |
|---|---|
| Lecture des fichiers Perfect | Colonnes reconnues et renommées correctement |
| Filtres par cycle | Les filtres agissent sur les tableaux et synthèses concernés |
| Requêtes prioritaires | Les contrôles de niveau 9/10 restent traçables |
| Export | Les tableaux exportés conservent les colonnes utiles |

## Limites documentées

- Le schéma SQL est large ; toutes les tables ne sont pas documentées individuellement.
- Certaines requêtes dépendent de paramètres SQL (`@date_debut`, `@date_fin`, `@id_devise_reporting`).
- Les montants multi-devises doivent rester séparés.
- Toute requête non testée sur une base réelle doit être marquée comme non validée.
