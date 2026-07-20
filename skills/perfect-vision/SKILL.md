---
name: perfect-vision
description: Analyser la base Microsoft SQL Server BB_VISION_PRO et maintenir le tableau de bord Streamlit Perfect Vision, retrouver tables et colonnes dans le schéma, sélectionner ou adapter les requêtes de contrôle interne, expliquer les jointures et produire des requêtes SELECT sûres. Utiliser pour toute question ou modification sur Perfect Vision, BB_VISION_PRO, ses sous-onglets, les opérations, adhérents, comptes, épargne, crédits, HDPM, rapprochements API, indicateurs ou extractions d'audit issues des fichiers SQL du projet.
---

# Perfect Vision

Travailler à partir du schéma et du catalogue SQL réels de BB_VISION_PRO. Ne jamais inventer une table, une colonne ou une relation.

## Procédure de travail

1. Reformuler le besoin en cycle, période, population, mesure et exception recherchée.
2. Lire [references/sources.md](references/sources.md) pour localiser les sources et connaître les garde-fous.
3. Chercher d'abord une requête existante dans `data/vision/requetes.sql` avec `scripts/inspect_vision_sql.py --query "terme"`.
4. Vérifier chaque table et colonne dans `data/vision/BB_VISION_PRO.sql` avec `--table NOM_TABLE` ou `--query NOM_COLONNE`.
5. Réutiliser la requête existante si elle répond au besoin. Sinon, produire une variante minimale et expliquer les adaptations.
6. Afficher la requête complète avec `--number N`, puis vérifier séparément les colonnes techniques internes et les colonnes métier du `SELECT` final.
7. Valider les paramètres de dates, devise, seuils et statut d'annulation avant toute exécution.
8. Livrer la requête, ses hypothèses, les champs de sortie et les contrôles de cohérence.

## Règles SQL

- Produire des requêtes en lecture seule (`SELECT`, CTE, tables temporaires locales si nécessaires).
- Ne jamais exécuter les instructions `CREATE DATABASE`, `ALTER`, `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT` du fichier de schéma.
- Qualifier les objets avec `dbo.` et conserver les noms exacts du schéma.
- Utiliser des bornes de dates explicites. Pour les colonnes datetime, préférer `>= @date_debut AND < DATEADD(day, 1, @date_fin)`.
- Ne jamais additionner CDF et USD. Grouper par `ID_DEVISE` ou filtrer la devise demandée.
- Distinguer les sources back-office et API avant de les réunir avec `UNION ALL`.
- Éviter `NOLOCK` pour les contrôles nécessitant une image cohérente, sauf demande explicite et risque documenté.
- Signaler toute jointure incertaine et la confirmer dans le schéma ou dans une requête existante.
- Ne jamais remplacer les colonnes nécessaires aux CTE, jointures, filtres, agrégations ou tris uniquement pour alléger l'export.
- Éviter `SELECT *` dans la projection finale et afficher seulement les colonnes utiles à la décision et au contrôle.

## Projection métier des exports

- Considérer `data/vision/requetes.sql` comme le catalogue métier/export épuré de référence.
- Simplifier uniquement le `SELECT` final; conserver les calculs et identifiants techniques nécessaires en amont.
- Garder les références auditables : client, transaction, reçu, compte, prêt, demande ou dossier selon le contrôle.
- Préférer les codes, numéros et libellés métier aux identifiants techniques redondants. Conserver un identifiant technique seulement s'il est la seule clé exploitable pour la revue.
- Vérifier que les colonnes finales suffisent pour identifier la population, comprendre l'anomalie, mesurer le montant, connaître la devise, dater le fait et retrouver la pièce source.

## Invariants du tableau de bord Streamlit

- Conserver les analyses détaillées de Perfect Vision dans des `st.tabs`. Perfect Vision constitue un tableau de bord complet : calculer tous les sous-onglets ensemble au chargement initial afin qu'ils soient ensuite immédiatement consultables.
- Ne jamais remplacer ces `st.tabs` par une navigation conditionnelle qui calcule uniquement l'onglet sélectionné. Cette optimisation à la demande est réservée aux modules dont le fonctionnement métier l'autorise, pas à Perfect Vision.
- Améliorer les performances avec `st.cache_data` sur la lecture, la normalisation et les calculs déterministes coûteux. Invalider naturellement le cache lorsque le fichier, la feuille, les paramètres ou les filtres changent; ne pas mettre en cache un rendu Streamlit susceptible de devenir obsolète.
- Vérifier après toute modification que l'ouverture initiale alimente tous les sous-onglets et que le passage d'un onglet déjà chargé à un autre ne déclenche pas un nouveau calcul Python.

## Frontière avec la comptabilité Turbo

- Considérer Perfect Vision comme le cœur métier microfinance et la source à interroger pour les comptes, prêts, échéanciers, remboursements, DAT et écritures officielles disponibles dans son schéma.
- Considérer le volet `Balances et journaux` de `Finance Turbo` dans Solution M-PESA comme une restitution de contrôle des sous-registres opérationnels Turbo. Il produit des balances et positions observées, mais ne remplace pas une balance générale, un bilan ou un compte de résultat validé dans Perfect Vision.
- Utiliser G2 uniquement comme preuve secondaire du canal M-PESA, complément de nom et contrôle `Receipt No = ref_no`; ne jamais reprendre ses montants dans une balance Turbo ou Perfect.
- En cas d'écart Turbo–Perfect Vision, rapprocher par client, téléphone normalisé, devise, référence, produit et date, puis documenter le sens comptable de chaque système avant de conclure. Ne jamais additionner CDF et USD.
- Lire [references/sources.md](references/sources.md) pour la matrice de responsabilité entre Perfect Vision, Turbo et G2.
- Pour transposer une requête Perfect Vision de niveau 9 ou 10 vers les volets de pilotage de `Finance Turbo`, vérifier d'abord que les quatre exports Turbo portent le grain et les champs nécessaires. Adapter les remboursements, évolutions dépôts/crédits, nouveaux crédits, encours, concentration, PAR simplifié, dépôts fréquents, tranches de dépôts, comptes inactifs, DAT sans crédit actif et crédit–épargne disponible. Ne pas copier comme exacts les échéanciers, provisions, garanties ou retards de versement lorsqu'un plan d'amortissement ou un champ métier manque.
- Dans cette transposition, Transactions M-PESA_Turbo fournit les flux, Loans Account les positions de crédit, Savings Account les positions d'épargne/DAT et Customers le référentiel. G2 reste hors des calculs et sert seulement à l'identité et au rapprochement secondaire.

## Norme visuelle commune des onglets

- Conserver une barre d'onglets sobre et professionnelle.
- Afficher l'onglet actif en bleu avec un soulignement rouge.
- Appliquer un survol discret et rendre la navigation au clavier clairement visible.
- Permettre le défilement horizontal des onglets sur les petits écrans.

## Utilitaire de recherche

```powershell
python skills/perfect-vision/scripts/inspect_vision_sql.py --list-queries
python skills/perfect-vision/scripts/inspect_vision_sql.py --query "crédit sans garantie"
python skills/perfect-vision/scripts/inspect_vision_sql.py --number 144
python skills/perfect-vision/scripts/inspect_vision_sql.py --table PRETS
```

Charger seulement les extraits pertinents : le schéma complet dépasse 3 Mo.

## Format de réponse

Fournir, selon le besoin : objectif du contrôle, sources utilisées, paramètres, SQL prêt à relire, clés de jointure, interprétation des résultats, limites et tests de cohérence. Ne présenter aucun résultat comme observé si la requête n'a pas été exécutée.
