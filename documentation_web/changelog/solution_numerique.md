# Changelog Solution Numérique

## 17 août 2026

### Ajouté

- Ajout de l'onglet `Analyse des risques` : lecture transversale Loans Account + Savings Account par client et devise, avec couverture crédit/épargne, exposition nette, PAR 1/7/30/60/90, risque DAT, liquidité, rentabilité estimée, concentration, alertes et qualité des données.
- Ajout du taux `encours crédit / encours épargne` dans l'analyse des risques, afin de mesurer explicitement la transformation ou l'utilisation de l'épargne en crédit, sans le confondre avec la couverture `épargne / crédit`.
- Ajout d'un export Excel préparé uniquement à la demande avec les feuilles `Synthese_risque`, `Risque_clients`, `Risque_credit`, `Risque_DAT`, `Liquidite`, `Rentabilite`, `Concentration`, `Alertes`, `Qualite_donnees`, `Parametres`, `Data_gaps` et `Audit`.

### Amélioré

- Optimisation de l'agrégation des risques sur les gros fichiers Savings Account : les regroupements et le scoring client sont vectorisés pour réduire le temps de calcul.

## 10 août 2026

### Amélioré

- Priorisation des analyses en ligne dans les onglets lourds : les KPI, tableaux, alertes et graphiques sont consultés dans Streamlit avant tout export.
- Les exports Excel volumineux suivent désormais le parcours `Préparer` puis `Télécharger`, afin d'éviter la génération automatique des classeurs au chargement.
- Le cockpit Clients dispose d'un bloc global `Export du cockpit Clients`, indépendant des opportunités affichées.
- Les cockpits Excel `Clients`, `Crédits` et `Épargnes` sont allégés pour le partage opérationnel : seules les feuilles importantes sont exportées par défaut. `Credit_Encours_A_Date` et `Epargne_Encours_A_Date` deviennent les feuilles de référence pour les encours à une date.
- La documentation FAQ précise où trouver le cockpit Clients, pourquoi les boutons `Actualiser` sont nécessaires et pourquoi les Excel sont préparés à la demande.

## 08 août 2026

### Ajouté

- Création de la documentation web Solution Numérique.
- Documentation initiale des sources, contrats, extraits clients, finance, balances, clients, épargnes, crédits, G2, statistiques et projections.

### Règles rappelées

- G2 enrichit l'identité et contrôle les écritures, mais ne pilote pas les montants.
- CDF et USD restent séparés.
