---
name: perfect-power-bi
description: Concevoir, construire, tester et maintenir les tableaux de bord Microsoft Power BI alimentés par Perfect Vision et BB_VISION_PRO. Utiliser pour choisir entre Import, DirectQuery ou modèle composite, définir une base miroir ou un data mart, créer un modèle en étoile, des mesures DAX, des requêtes Power Query M, un projet PBIX/PBIP/TMDL, une passerelle, un rafraîchissement incrémental, une sécurité RLS, appliquer le système visuel IMF BB et ses formats monétaires, ou diagnostiquer les performances et rapprocher les chiffres Power BI avec data/vision/requetes.sql.
---

# Perfect Power BI

Construire une couche décisionnelle stable au-dessus de Perfect Vision sans faire porter la charge analytique à la base opérationnelle.

## Objectif de maturité

Faire évoluer le projet d'un prototype avancé vers une plateforme institutionnelle de pilotage du contrôle interne, fiable, performante, sécurisée et exploitable en production.

Considérer le projet comme prêt pour la production uniquement lorsque les conditions suivantes sont démontrées :

- toutes les feuilles Power BI sont stabilisées sur une période de référence, puis testées sur le mois courant et sur une plage historique ;
- chaque KPI est rapproché avec sa requête SQL de référence, avec une définition documentée du grain, de la période, de la devise, des exclusions et des règles de calcul ;
- les requêtes, colonnes, mesures et analyses redondantes sont supprimées sans perdre la traçabilité nécessaire à l'audit ;
- le modèle Power BI utilise des faits et dimensions cohérents, des mesures DAX explicites et des relations sans ambiguïté ;
- les alimentations durables sont matérialisées dans une base de reporting séparée telle que `BB_VISION_REPORTING`, sans charge analytique directe excessive sur Perfect Vision en production ;
- les temps d'exécution SQL, le rafraîchissement du modèle et les interactions des pages respectent les objectifs de performance convenus ;
- les données personnelles, les droits d'export et les périmètres d'accès sont protégés par des rôles et une RLS testés ;
- la passerelle, les informations d'identification, l'ordonnancement ETL et les rafraîchissements Power BI sont testés après publication ;
- le projet PBIP reste versionnable, validé et ouvrable dans Power BI Desktop ;
- un dictionnaire officiel des indicateurs, des sources et des responsabilités de maintenance est disponible.

Appliquer cette trajectoire dans cet ordre :

1. stabiliser les pages et filtres sur la période de test ;
2. rapprocher les chiffres Power BI avec SQL Server ;
3. construire la base de reporting et simplifier les sources du modèle ;
4. optimiser les performances et le rafraîchissement ;
5. mettre en place la sécurité, la passerelle et les environnements développement, test et production ;
6. valider l'exploitation et documenter la reprise après incident.

Ne jamais qualifier le projet de prêt pour la production tant qu'un de ces contrôles critiques reste non testé ou non démontré.

## Sources obligatoires

1. Lire entièrement `../perfect-vision/SKILL.md`, puis les références qu'il impose.
2. Utiliser comme sources de vérité :
   - `../../data/vision/BB_VISION_PRO.sql` pour le schéma ;
   - `../../data/vision/requetes.sql` pour les contrôles et calculs métier ;
   - `../../data/vision/Indicateurs_perfect_vision.xlsx` pour le catalogue d'indicateurs ;
   - `../../data/Rename_columns.xlsx` et `../../data/Replace_values.xlsx` pour les conventions de normalisation.
3. Considérer les profils présents sous `../../reports/` comme des résultats de test datés, jamais comme le schéma canonique.
4. Ne jamais inventer une table, une relation, une mesure ou une définition d'indicateur.

## Workflow

### 1. Cadrer le tableau de bord

Définir l'audience, les décisions attendues, les cycles couverts, la fraîcheur requise, la période historique, les filtres, les accès et le niveau de détail.

Privilégier un premier périmètre cohérent :

- Direction microfinance ;
- Crédit ;
- Épargne ;
- Conformité ;
- Surveillance et qualité des données.

### 2. Vérifier l'environnement

Contrôler en lecture seule :

- l'instance et l'édition SQL Server ;
- la base de test et la base de production ciblées ;
- SQL Server Agent, Always On et le mode de récupération ;
- la présence de Power BI Desktop ;
- l'existence éventuelle d'une passerelle, d'un espace Power BI et d'un projet PBIX/PBIP.

Ne jamais présenter la configuration de test comme celle de production sans vérification.

### 3. Choisir l'architecture

Lire [references/architecture-and-connectivity.md](references/architecture-and-connectivity.md).

Appliquer par défaut :

- prototype : `BB_VISION_PRO_TEST` en mode Import ;
- production : base ou serveur de reporting séparé, alimenté en lecture seule depuis Perfect Vision ;
- Power BI Service : passerelle locale en mode standard ;
- DirectQuery : uniquement sur une couche de reporting optimisée et avec une exigence de quasi-temps réel démontrée.

Ne pas connecter un rapport DirectQuery directement à la production par défaut.

### 4. Concevoir le modèle décisionnel

Lire [references/semantic-model-and-pages.md](references/semantic-model-and-pages.md).

- Construire un modèle en étoile avec un grain explicite par table de faits.
- Séparer les faits de flux des faits d'instantané.
- Utiliser des dimensions conformes pour date, devise, agence, client, produit et type d'opération.
- Conserver les références nécessaires au drill-through et à l'audit, mais masquer les clés techniques dans l'expérience utilisateur.
- Créer des mesures DAX explicites ; ne pas dépendre des agrégations implicites de colonnes.
- Ne jamais additionner CDF et USD. Exiger une devise unique pour les mesures monétaires nominales ou créer une mesure de conversion distincte et documentée.
- Utiliser Q156 comme source fonctionnelle unique du cycle conformité ; utiliser Q149 à Q155 pour le rapprochement, pas comme tables concurrentes dans le même modèle.

### 5. Préparer la couche SQL de reporting

Utiliser `requetes.sql` comme catalogue de logique métier, pas comme une liste de 156 requêtes natives à coller dans Power BI.

- Matérialiser les faits et dimensions durables dans une base telle que `BB_VISION_REPORTING`.
- Garder chaque alimentation SQL autonome ou explicitement dépendante d'une couche de reporting gouvernée.
- Éviter les tables temporaires et les requêtes natives opaques comme sources finales du modèle Power BI.
- Préserver le query folding pour les tables soumises au rafraîchissement incrémental.
- Ajouter les index sur dates, devises, agences et clés de relation après observation des plans d'exécution.
- Ne jamais modifier le schéma du progiciel en production sans validation de l'éditeur et de l'administrateur SQL.

### 6. Construire Power BI

- Utiliser Power BI Desktop pour créer le fichier initial et la connexion.
- Préférer un projet PBIP/TMDL versionnable lorsque l'équipe accepte les fonctions Preview ; sinon conserver le PBIX et versionner séparément SQL, M, DAX, thème et documentation.
- Ne jamais inventer manuellement une structure PBIP non vérifiée. Partir d'un projet enregistré par Power BI Desktop ou d'un modèle existant qui s'ouvre correctement.
- Avant d'ajouter une page, un visuel ou une mesure, inspecter le projet existant sous `../../data/vision/power-bi` lorsqu'il existe. Relever les pages, les tables de faits, les mesures et les visuels déjà présents afin de ne pas dupliquer une analyse couverte.
- Dans le projet IMF BB actuel, considérer comme déjà prévues les pages `Paramétrage`, `Direction`, `Clients`, `Crédit`, `Risque crédit`, `Prévisions crédit`, `Épargne`, `Conformité` et `Surveillance`. Toute nouvelle analyse doit donc compléter une question métier manquante, pas recréer cette ossature.
- Désactiver la date/heure automatique et utiliser une dimension Date officielle.
- Définir les relations en sens unique par défaut et éviter les relations plusieurs-à-plusieurs sans justification.
- Organiser les mesures dans des dossiers d'affichage et masquer les colonnes techniques.
- Utiliser des pages de synthèse, tendance, diagnostic et détail plutôt qu'une page unique surchargée.
- Pour les analyses complémentaires, lire la section `Analyses avancées après V1` dans `references/semantic-model-and-pages.md` et choisir uniquement les ajouts dont la source SQL, le grain, la devise, la période et le test de rapprochement sont identifiés.

### 6 bis. Appliquer le système visuel IMF BB

Réutiliser ces règles sur les pages Direction, Crédit, Épargne, Conformité et Surveillance. Consulter `../../SOP/Dashbord` pour les références visuelles, sans reproduire leur densité lorsque cela nuit à la lisibilité.

#### Structure des pages

- Utiliser un canevas logique 16:9 et conserver des marges, alignements et espacements réguliers.
- Placer en haut un bandeau institutionnel bleu nuit avec le titre de la page et un sous-titre court.
- Placer les filtres globaux dans la zone supérieure droite du bandeau ou immédiatement à sa suite.
- Organiser le contenu dans cet ordre : indicateurs essentiels, risques ou qualité, activité, puis ventilations explicatives.
- Utiliser des cartes blanches aux angles sobres sur un fond bleu-gris très clair.
- Limiter les éléments visibles aux informations utiles au lecteur métier ; masquer les clés et colonnes techniques.
- Garder la page lisible à 100 % sur la résolution cible, sans chevauchement, libellé tronqué ni défilement horizontal.

#### Palette et typographie

- Fond de page : `#F3F6FA`.
- Bandeau et titres institutionnels : `#17365D`.
- Texte principal des indicateurs : `#0B5CAD`.
- Crédit et portefeuille : `#1F4E79` ou `#1F77B4`.
- Risque et provisionnement : `#E67E22`.
- Épargne : `#D43F9A`.
- Cartes : fond `#FFFFFF`, bordure discrète bleu-gris.
- Utiliser Segoe UI, des titres courts en français et une hiérarchie typographique constante.
- Réserver les couleurs fortes aux familles métier et aux alertes ; ne pas colorer chaque visuel arbitrairement.

#### Filtres globaux

- Afficher par défaut `Période` et `Devise`.
- Charger le mois en cours par défaut, avec possibilité de sélectionner une autre période dans les données chargées.
- Laisser `Devise` sur `Tout` par défaut tout en conservant des mesures CDF et USD séparées.
- Vérifier qu'une sélection `CDF` masque les mesures USD et qu'une sélection `USD` masque les mesures CDF.
- N'afficher `Agence` que si plusieurs agences existent ou si ce filtre apporte une décision réelle ; ne pas occuper l'espace avec un filtre constant.
- Conserver les mêmes filtres globaux et la même position sur les autres onglets lorsque les dimensions sont disponibles.

#### Feuille de paramétrage

- Créer une feuille `Paramétrage` en première position lorsque les utilisateurs doivent définir un périmètre commun avant de parcourir le rapport.
- Synchroniser les segments avec des groupes PBIR stables : `IMFBB_Global_Periode`, `IMFBB_Global_Devise` et, lorsque les champs sont conformes, les groupes propres aux clients, agences et produits.
- Synchroniser uniquement des champs reposant sur une dimension conforme ou sur la même colonne métier. Ne jamais présenter un segment comme global s'il ne filtre qu'une table de faits.
- Ajouter les boutons Power BI natifs `ApplyAllSlicers` et `ClearAllSlicers` pour appliquer ou effacer les sélections en une seule action.
- Afficher sur la feuille la période active, la devise active et la date maximale disponible dans le chargement.
- Distinguer explicitement l'application des filtres du rafraîchissement de la source : en mode Import, un segment filtre les données déjà chargées et ne modifie pas directement les paramètres Power Query.
- Dans Power BI Desktop, utiliser `Accueil > Actualiser` pour recharger la source. Dans Power BI Service, ne configurer un bouton Power Automate de rafraîchissement qu'après publication, association de la passerelle et validation des droits sur le modèle sémantique.
- Centraliser les produits de crédit et d'épargne uniquement après création de dimensions Produit conformes dans la couche de reporting.

#### Montants et devises

- Ne jamais afficher `2,7MCDF`, `135MCDF` ou `6,14MUSD`.
- Afficher `2,7M CDF`, `135M CDF` et `6,14M USD`, avec une espace insécable ou un espace inclus dans le suffixe de format.
- Dans les formats Power BI, placer l'espace dans le littéral de devise : `#,##0" CDF"` et `#,##0.00" USD"`. Ne pas utiliser `#,##0 "CDF"` si les unités automatiques `K` ou `M` sont actives, car Power BI peut supprimer cet espace.
- Appliquer la même règle aux cartes, étiquettes de données, axes, info-bulles, tableaux et exports.
- Autoriser les unités automatiques `K`, `M` ou `Md` seulement si elles restent compréhensibles et identiques entre visuels comparables.
- Indiquer la devise dans le titre d'un graphique lorsqu'il n'affiche qu'une devise, par exemple `Encours crédit par produit — CDF`.
- Ne jamais agréger CDF et USD dans un total nominal ; utiliser une mesure de conversion explicitement nommée si elle existe.

#### Cartes et graphiques

- Utiliser une barre d'accent en haut des cartes KPI, colorée selon la famille métier.
- Afficher un indicateur principal par zone lisible ; réduire la taille ou scinder une carte avant d'accepter des valeurs tronquées.
- Ne jamais répéter la même question analytique sur une même page. Avant d'ajouter un visuel, comparer sa mesure, sa dimension et la décision qu'il éclaire avec les visuels existants. Si deux visuels expriment la même analyse, conserver le plus lisible et utiliser l'espace libéré pour une analyse complémentaire.
- Une carte KPI et un graphique ne peuvent coexister sur le même sujet que s'ils répondent à deux questions distinctes, par exemple niveau actuel et évolution temporelle. Une simple répétition du même total par catégorie est interdite.
- Utiliser des barres pour comparer produits, agences, segments ou catégories sur une période.
- Utiliser une courbe uniquement lorsqu'il existe plusieurs points temporels et qu'une tendance est réellement lisible.
- Séparer les graphiques CDF et USD lorsqu'une comparaison directe des montants nominaux serait trompeuse.
- Conserver des libellés et info-bulles permettant d'identifier la mesure, la période, la devise et la catégorie.

#### Contrôle visuel obligatoire

- Ouvrir le PBIX/PBIP dans Power BI Desktop après modification.
- Tester `Tout`, `CDF` et `USD` dans le filtre Devise.
- Vérifier au moins un montant abrégé dans une carte et une étiquette de graphique.
- Confirmer l'espace entre l'unité et la devise, l'absence de chevauchement et la cohérence des couleurs.
- Confirmer qu'aucune analyse n'est dupliquée dans deux visuels de la même page.
- Enregistrer une capture de contrôle lorsque le rendu a été modifié de manière significative.

### 7. Configurer sécurité et rafraîchissement

- Utiliser un compte SQL ou Windows de service en lecture seule.
- Mettre en place la RLS par agence ou périmètre lorsque les responsables ne doivent pas voir l'ensemble du portefeuille.
- Restreindre les données personnelles dans les pages Direction et les exports.
- Faire exécuter l'ETL avant le rafraîchissement Power BI.
- Afficher la dernière date de données et la dernière date de rafraîchissement.
- Utiliser `RangeStart` inclusif et `RangeEnd` exclusif pour le rafraîchissement incrémental.

### 8. Valider avant livraison

Lire [references/validation-and-deployment.md](references/validation-and-deployment.md).

Vérifier au minimum :

- grain, doublons, valeurs nulles et relations ;
- rapprochement de chaque KPI avec sa requête SQL de référence ;
- séparation stricte des devises ;
- filtres de dates et statuts d'annulation ;
- performances des pages et du rafraîchissement ;
- sécurité RLS et exposition des données personnelles ;
- ouverture du PBIX/PBIP dans Power BI Desktop ;
- fonctionnement de la passerelle et du rafraîchissement après publication.

Ne jamais annoncer qu'un rapport, un rafraîchissement ou une publication fonctionne sans l'avoir testé.

## Livrables attendus

Selon la demande, produire :

- architecture et matrice de décision de connexion ;
- scripts SQL du data mart et des alimentations ;
- dictionnaire des faits, dimensions, grains et relations ;
- catalogue des mesures DAX avec source, formule et devise ;
- requêtes Power Query M ;
- projet PBIX/PBIP/TMDL ou kit d'intégration Power BI ;
- thème JSON et structure des pages ;
- matrice RLS ;
- rapport de rapprochement et de performance ;
- procédure de passerelle, rafraîchissement et publication.

## Format de réponse

Commencer par la recommandation. Indiquer les sources, hypothèses, grain, fréquence, devise, sécurité, limites et tests. Distinguer clairement ce qui est proposé, créé, exécuté, ouvert dans Power BI Desktop et publié dans Power BI Service.
