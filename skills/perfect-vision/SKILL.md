---
name: perfect-vision
description: Analyser la base Microsoft SQL Server BB_VISION_PRO de Perfect Vision, retrouver tables et colonnes dans le schéma, sélectionner ou adapter les requêtes de contrôle interne, expliquer les jointures et produire des requêtes SELECT sûres. Utiliser pour toute question sur Perfect Vision, BB_VISION_PRO, les opérations, adhérents, comptes, épargne, crédits, HDPM, rapprochements API, indicateurs ou extractions d'audit issues des fichiers SQL du projet.
---

# Perfect Vision

Travailler à partir du schéma et du catalogue SQL réels de BB_VISION_PRO. Ne jamais inventer une table, une colonne ou une relation.

## Procédure de travail

1. Reformuler le besoin en cycle, période, population, mesure et exception recherchée.
2. Lire [references/sources.md](references/sources.md) pour localiser les sources et connaître les garde-fous.
3. Chercher d'abord une requête existante dans `data/vision/requetes.sql` avec `scripts/inspect_vision_sql.py --query "terme"`.
4. Vérifier chaque table et colonne dans `data/vision/BB_VISION_PRO.sql` avec `--table NOM_TABLE` ou `--query NOM_COLONNE`.
5. Réutiliser la requête existante si elle répond au besoin. Sinon, produire une variante minimale et expliquer les adaptations.
6. Valider les paramètres de dates, devise, seuils et statut d'annulation avant toute exécution.
7. Livrer la requête, ses hypothèses, les champs de sortie et les contrôles de cohérence.

## Règles SQL

- Produire des requêtes en lecture seule (`SELECT`, CTE, tables temporaires locales si nécessaires).
- Ne jamais exécuter les instructions `CREATE DATABASE`, `ALTER`, `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT` du fichier de schéma.
- Qualifier les objets avec `dbo.` et conserver les noms exacts du schéma.
- Utiliser des bornes de dates explicites. Pour les colonnes datetime, préférer `>= @date_debut AND < DATEADD(day, 1, @date_fin)`.
- Ne jamais additionner CDF et USD. Grouper par `ID_DEVISE` ou filtrer la devise demandée.
- Distinguer les sources back-office et API avant de les réunir avec `UNION ALL`.
- Éviter `NOLOCK` pour les contrôles nécessitant une image cohérente, sauf demande explicite et risque documenté.
- Signaler toute jointure incertaine et la confirmer dans le schéma ou dans une requête existante.

## Utilitaire de recherche

```powershell
python skills/perfect-vision/scripts/inspect_vision_sql.py --list-queries
python skills/perfect-vision/scripts/inspect_vision_sql.py --query "crédit sans garantie"
python skills/perfect-vision/scripts/inspect_vision_sql.py --table PRETS
```

Charger seulement les extraits pertinents : le schéma complet dépasse 3 Mo.

## Format de réponse

Fournir, selon le besoin : objectif du contrôle, sources utilisées, paramètres, SQL prêt à relire, clés de jointure, interprétation des résultats, limites et tests de cohérence. Ne présenter aucun résultat comme observé si la requête n'a pas été exécutée.
