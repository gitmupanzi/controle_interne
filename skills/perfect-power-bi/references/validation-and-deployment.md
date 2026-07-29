# Validation et déploiement

## Contrôles de données

Pour chaque fait :

1. confirmer le grain attendu ;
2. compter les lignes et clés distinctes ;
3. rechercher les doublons de clé au grain ;
4. mesurer les valeurs nulles des dimensions et mesures obligatoires ;
5. contrôler les dates minimales et maximales ;
6. rapprocher les totaux par devise, agence et période ;
7. vérifier les annulations et statuts exclus ;
8. comparer au résultat de la requête SQL de référence.

Pour Q156, rapprocher séparément les analyses 38, 39, 48, 57 et 149 à 155.

## Contrôles du modèle

- Relations un-à-plusieurs valides.
- Aucun chemin de filtre ambigu.
- Pas de relation plusieurs-à-plusieurs sans justification.
- Clés techniques et colonnes de tri masquées.
- Mesures explicites et formats corrects.
- Aucun total monétaire CDF + USD.
- Date officielle marquée comme table de dates.
- Hiérarchies et dossiers d'affichage compréhensibles.

## Contrôles des pages

- La page d'accueil répond à la question principale sans interaction.
- Les filtres globaux modifient toutes les pages annoncées.
- Les cartes se rapprochent des tableaux détaillés.
- Les graphiques utilisent des mesures et grains compatibles.
- Les états vides et les périodes sans données restent compréhensibles.
- Les info-bulles indiquent unité, devise, période et définition.
- Les tableaux de détail permettent de retrouver la référence source.
- Les pages restent lisibles sur la résolution cible.
- Les pages respectent la palette, le bandeau, les cartes et la hiérarchie définis dans `SKILL.md`.
- Les filtres `Période` et `Devise` fonctionnent sur les visuels annoncés ; `Agence` n'est affiché que s'il apporte une segmentation réelle.
- Les montants abrégés conservent une espace avant la devise : `2,7M CDF`, jamais `2,7MCDF`.
- Les états `Tout`, `CDF` et `USD` ont été testés dans Power BI Desktop.

## Performances

- Utiliser Performance Analyzer dans Power BI Desktop.
- Identifier les visuels et mesures lentes.
- Réduire les colonnes, la cardinalité et les relations bidirectionnelles.
- Vérifier que les filtres incrémentaux se replient vers SQL Server.
- Tester le temps de chargement initial, les changements de filtres et le rafraîchissement complet.
- Tester DirectQuery uniquement avec la concurrence et la passerelle réelles lorsqu'il est retenu.

## Sécurité

- Tester chaque rôle RLS avec `Afficher comme`.
- Vérifier les utilisateurs multi-agences.
- Restreindre téléphone, adresse, pièce d'identité et autres données personnelles.
- Ne pas accorder la permission Build aux consommateurs qui ne doivent pas explorer le modèle.
- Tester les exports de données et les pages de drill-through.

## Rafraîchissement

- Vérifier que l'ETL a terminé avec succès avant Power BI.
- Utiliser `RangeStart <= date < RangeEnd`.
- Contrôler le premier chargement historique et les rafraîchissements suivants.
- Afficher la date maximale des faits et l'heure du dernier rafraîchissement.
- Documenter la reprise après échec.

## PBIX et PBIP

- Ouvrir et enregistrer le projet avec la version Power BI Desktop installée.
- Pour PBIP, partir d'un projet créé par Power BI Desktop.
- Valider les fichiers TMDL et PBIR avant commit.
- Exclure les caches locaux et secrets.
- Ne pas considérer un fichier textuellement valide comme fonctionnel tant qu'il ne s'ouvre pas dans Power BI Desktop.

## Publication

Avant publication :

1. valider le modèle dans la base de test ;
2. paramétrer la source de production reporting ;
3. publier dans un espace de développement ;
4. associer la passerelle et les informations d'identification ;
5. exécuter un rafraîchissement manuel ;
6. tester les rôles, chiffres, filtres et performances ;
7. promouvoir vers test puis production ;
8. conserver une procédure de retour arrière.

La publication dans Power BI Service exige les autorisations du tenant, de l'espace de travail et de la passerelle. Ne jamais annoncer la publication terminée sans URL ou preuve vérifiée.
