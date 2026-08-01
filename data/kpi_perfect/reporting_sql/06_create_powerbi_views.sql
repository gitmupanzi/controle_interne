/*
  BB_VISION_REPORTING - vues exposees a Power BI

  Les vues gardent des noms proches du modele PBIP actuel.
*/

USE BB_VISION_REPORTING;
GO

CREATE OR ALTER VIEW pbi.D_Date AS
SELECT
    date_value AS [Date],
    annee AS [Année],
    numero_mois AS [Numéro mois],
    mois AS [Mois],
    annee_mois AS [Année-mois]
FROM rpt.d_date;
GO

CREATE OR ALTER VIEW pbi.D_Devise AS
SELECT devise AS [Devise]
FROM rpt.d_devise
WHERE actif = 1;
GO

CREATE OR ALTER VIEW pbi.D_Agence AS
SELECT
    code_agence AS [Code agence],
    agence AS [Agence]
FROM rpt.d_agence
WHERE actif = 1;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Portefeuille AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    prets_actifs AS [Prêts actifs],
    encours AS [Encours],
    par_1_plus AS [PAR 1+],
    par_30_plus AS [PAR 30+],
    par_90_plus AS [PAR 90+],
    par_180_plus AS [PAR 180+],
    provision AS [Provision],
    taux_par_1_plus AS [Taux PAR 1+],
    taux_par_30_plus AS [Taux PAR 30+],
    taux_par_90_plus AS [Taux PAR 90+]
FROM rpt.f_credit_portefeuille;
GO

CREATE OR ALTER VIEW pbi.F_Credit_PAR_Detail AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    code_client AS [Code client],
    nom_client AS [Nom client],
    numero_pret AS [Numéro prêt],
    montant_initial AS [Montant initial],
    encours AS [Encours],
    jours_retard AS [Jours retard],
    arriere AS [Arriéré],
    provision AS [Provision],
    par_1_30 AS [PAR 1-30],
    par_31_60 AS [PAR 31-60],
    par_61_90 AS [PAR 61-90],
    par_91_180 AS [PAR 91-180],
    par_180_plus AS [PAR 180+],
    par_30_plus AS [PAR 30+],
    par_90_plus AS [PAR 90+],
    num_manuel,
    prenoms_client,
    code_type_client,
    type_client,
    numero_contrat,
    date_effet,
    date_decaissement,
    date_fin_echeance,
    current_encours
FROM rpt.f_credit_par_detail;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Decaissements AS
SELECT
    mois_decaissement AS [Mois décaissement],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    code_type_client AS [Code type client],
    type_client AS [Type client],
    prets_decaisses AS [Prêts décaissés],
    clients_decaisses AS [Clients décaissés],
    montant_decaisse AS [Montant décaissé],
    montant_moyen_pret AS [Montant moyen prêt]
FROM rpt.f_credit_decaissements;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Echeances_Futures AS
SELECT
    mois_echeance AS [Mois échéance],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    prets_concernes AS [Prêts concernés],
    echeances AS [Échéances],
    capital_attendu AS [Capital attendu],
    interet_attendu AS [Intérêt attendu],
    commission_attendue AS [Commission attendue],
    epargne_attendue AS [Épargne attendue],
    total_attendu AS [Total attendu]
FROM rpt.f_credit_echeances_futures;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Couverture AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    code_client AS [Code client],
    nom_client AS [Nom client],
    numero_pret AS [Numéro prêt],
    montant_initial AS [Montant initial],
    encours AS [Encours],
    arriere AS [Arriéré],
    epargne_client AS [Épargne client],
    caution AS [Caution],
    garantie AS [Garantie],
    arriere_couvert AS [Arriéré couvert],
    principal_couvert AS [Principal couvert],
    exposition_nette AS [Exposition nette],
    prenoms_client
FROM rpt.f_credit_couverture;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Top_Encours AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    code_client AS [Code client],
    nom_client AS [Nom client],
    numero_pret AS [Numéro prêt],
    montant_initial AS [Montant initial],
    encours AS [Encours],
    num_manuel,
    prenoms_client,
    code_type_client,
    type_client,
    date_effet,
    date_decaissement
FROM rpt.f_credit_top_encours;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Concentration AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    prets_actifs AS [Prêts actifs],
    encours AS [Encours],
    encours_top_10_pct AS [Encours top 10%],
    prets_top_10_pct AS [Prêts top 10%],
    part_top_10_pct AS [Part top 10%]
FROM rpt.f_credit_concentration;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Tranches AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    tranche_montant AS [Tranche montant],
    clients AS [Clients],
    prets AS [Prêts],
    montant_initial AS [Montant initial],
    encours AS [Encours],
    par_1_plus AS [PAR 1+],
    par_30_plus AS [PAR 30+],
    par_90_plus AS [PAR 90+],
    taux_par_1_plus AS [Taux PAR 1+],
    taux_par_30_plus AS [Taux PAR 30+],
    taux_par_90_plus AS [Taux PAR 90+]
FROM rpt.f_credit_tranches;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Vintage AS
SELECT
    cohorte_decaissement AS [Cohorte décaissement],
    age_cohorte_mois AS [Âge cohorte mois],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    prets_decaisses AS [Prêts décaissés],
    montant_initial_cohorte AS [Montant initial cohorte],
    encours_restant AS [Encours restant],
    par_30_plus AS [PAR 30+],
    par_90_plus AS [PAR 90+],
    par_30_sur_initial AS [PAR 30 sur initial],
    par_90_sur_initial AS [PAR 90 sur initial]
FROM rpt.f_credit_vintage;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Retention AS
SELECT
    mois_solde AS [Mois solde],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    clients_arrives_echeance AS [Clients arrivés échéance],
    prets_soldes AS [Prêts soldés],
    montant_prets_soldes AS [Montant prêts soldés],
    clients_renouveles AS [Clients renouvelés],
    clients_renouveles_90j AS [Clients renouvelés 90j],
    retention AS [Rétention],
    retention_90j AS [Rétention 90j],
    delai_moyen_renouvellement AS [Délai moyen renouvellement]
FROM rpt.f_credit_retention;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Provisions_Detail AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    code_client AS [Code client],
    nom_client AS [Nom client],
    numero_pret AS [Numéro prêt],
    montant_initial AS [Montant initial],
    tranche_montant AS [Tranche montant],
    provision AS [Provision],
    prenoms_client
FROM rpt.f_credit_provisions_detail;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Duree AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    numero_pret AS [Numéro prêt],
    code_client AS [Code client],
    nom_client AS [Nom client],
    date_effet AS [Date effet],
    date_fin_echeance AS [Date fin échéance],
    montant_initial AS [Montant initial],
    echeances_totales AS [Échéances totales],
    echeances_restantes AS [Échéances restantes],
    duree_theorique_mois AS [Durée théorique mois],
    tranche_echeances_restantes AS [Tranche échéances restantes],
    tranche_total_echeances AS [Tranche total échéances],
    prenoms_client
FROM rpt.f_credit_duree;
GO

CREATE OR ALTER VIEW pbi.F_Credit_Tendance_PAR AS
SELECT
    date_situation AS [Date situation],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_credit AS [Produit crédit],
    devise AS [Devise],
    prets_actifs AS [Prêts actifs],
    encours AS [Encours],
    par_1_plus AS [PAR 1+],
    par_30_plus AS [PAR 30+],
    par_90_plus AS [PAR 90+],
    taux_par_30_plus AS [Taux PAR 30+]
FROM rpt.f_credit_tendance_par;
GO

CREATE OR ALTER VIEW pbi.F_Epargne_Soldes AS
SELECT
    date_situation AS [Date situation],
    mois AS [Mois],
    code_agence AS [Code agence],
    agence AS [Agence],
    produit_epargne AS [Produit épargne],
    type_compte AS [Type compte],
    devise AS [Devise],
    comptes AS [Comptes],
    clients AS [Clients],
    solde_epargne AS [Solde épargne],
    solde_moyen_compte AS [Solde moyen compte]
FROM rpt.f_epargne_soldes;
GO

CREATE OR ALTER VIEW pbi.F_Conformite AS
SELECT
    analyse AS [Analyse],
    type_element AS [Type élément],
    section AS [Section],
    ligne_reporting AS [Ligne reporting],
    rubrique AS [Rubrique],
    date_debut AS [Date début],
    date_fin AS [Date fin],
    date_evenement AS [Date événement],
    code_client AS [Code client],
    nom_client AS [Nom client],
    numero_compte AS [Numéro compte],
    numero_alerte AS [Numéro alerte],
    reference_interne AS [Référence interne],
    reference_externe AS [Référence externe],
    numero_operation AS [Numéro opération],
    type_operation AS [Type opération],
    description AS [Description],
    etat AS [État],
    statut_revue AS [Statut revue],
    statut_couverture AS [Statut couverture],
    origine_declaration AS [Origine déclaration],
    devise AS [Devise],
    montant AS [Montant],
    volume AS [Volume],
    nombre AS [Nombre],
    niveau_risque AS [Niveau risque],
    profil_risque AS [Profil risque],
    severite AS [Sévérité],
    action_recommandee AS [Action recommandée],
    origine_donnee AS [Origine donnée],
    commentaire AS [Commentaire],
    point_service AS [Point service],
    motif AS [Motif],
    indicateurs AS [Indicateurs]
FROM rpt.f_conformite;
GO

CREATE OR ALTER VIEW pbi.F_Clients AS
SELECT
    date_debut AS [Date début],
    date_fin AS [Date fin],
    code_client AS [Code client],
    nom_client AS [Nom client],
    type_client AS [Type client],
    code_agence AS [Code agence],
    agence AS [Agence],
    date_adhesion AS [Date adhésion],
    devise AS [Devise],
    statut_client AS [Statut client],
    client_actif AS [Client actif],
    comptes AS [Comptes],
    comptes_ouverts AS [Comptes ouverts],
    comptes_clotures AS [Comptes clôturés],
    comptes_bloques AS [Comptes bloqués],
    comptes_dormants AS [Comptes dormants],
    comptes_inactifs AS [Comptes inactifs],
    derniere_operation AS [Dernière opération],
    solde_epargne AS [Solde épargne],
    credits_actifs AS [Crédits actifs],
    credits_a_rembourser AS [Crédits à rembourser],
    echeances_credit AS [Échéances crédit],
    capital_credit_prevu AS [Capital crédit prévu],
    interet_credit_a_rembourser AS [Intérêt crédit à rembourser],
    commission_credit_prevue AS [Commission crédit prévue],
    epargne_credit_prevue AS [Épargne crédit prévue],
    montant_credit_a_rembourser AS [Montant crédit à rembourser],
    montant_credit_restant AS [Montant crédit restant],
    interet_epargne_credite AS [Intérêt épargne crédité],
    dat_a_echeance AS [DAT à échéance],
    montant_dat_a_echeance AS [Montant DAT à échéance],
    premiere_echeance_dat AS [Première échéance DAT],
    derniere_echeance_dat AS [Dernière échéance DAT],
    avec_compte_ouvert AS [Avec compte ouvert],
    avec_compte_bloque AS [Avec compte bloqué],
    avec_compte_dormant AS [Avec compte dormant],
    avec_credit_a_rembourser AS [Avec crédit à rembourser],
    avec_interet_credit_a_rembourser AS [Avec intérêt crédit à rembourser],
    beneficiaire_interet_epargne AS [Bénéficiaire intérêt épargne],
    avec_dat_a_echeance AS [Avec DAT à échéance]
FROM rpt.f_clients;
GO
