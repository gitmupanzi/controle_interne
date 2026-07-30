/*
  BB_VISION_REPORTING - faits alignes avec le modele Power BI actuel
*/

USE BB_VISION_REPORTING;
GO

IF OBJECT_ID(N'rpt.f_credit_portefeuille', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_portefeuille (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        prets_actifs int NULL,
        encours decimal(19,4) NULL,
        par_1_plus decimal(19,4) NULL,
        par_30_plus decimal(19,4) NULL,
        par_90_plus decimal(19,4) NULL,
        par_180_plus decimal(19,4) NULL,
        provision decimal(19,4) NULL,
        taux_par_1_plus decimal(18,8) NULL,
        taux_par_30_plus decimal(18,8) NULL,
        taux_par_90_plus decimal(18,8) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_portefeuille_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_par_detail', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_par_detail (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        code_client varchar(100) NULL,
        nom_client varchar(500) NULL,
        numero_pret varchar(100) NULL,
        montant_initial decimal(19,4) NULL,
        encours decimal(19,4) NULL,
        jours_retard int NULL,
        arriere decimal(19,4) NULL,
        provision decimal(19,4) NULL,
        par_1_30 decimal(19,4) NULL,
        par_31_60 decimal(19,4) NULL,
        par_61_90 decimal(19,4) NULL,
        par_91_180 decimal(19,4) NULL,
        par_180_plus decimal(19,4) NULL,
        par_30_plus decimal(19,4) NULL,
        par_90_plus decimal(19,4) NULL,
        num_manuel varchar(100) NULL,
        prenoms_client varchar(255) NULL,
        code_type_client varchar(100) NULL,
        type_client varchar(255) NULL,
        numero_contrat varchar(100) NULL,
        date_effet date NULL,
        date_decaissement date NULL,
        date_fin_echeance date NULL,
        current_encours decimal(19,4) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_par_detail_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_top_encours', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_top_encours (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        code_client varchar(100) NULL,
        nom_client varchar(500) NULL,
        numero_pret varchar(100) NULL,
        montant_initial decimal(19,4) NULL,
        encours decimal(19,4) NULL,
        num_manuel varchar(100) NULL,
        prenoms_client varchar(255) NULL,
        code_type_client varchar(100) NULL,
        type_client varchar(255) NULL,
        date_effet date NULL,
        date_decaissement date NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_top_encours_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_decaissements', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_decaissements (
        mois_decaissement date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        code_type_client varchar(100) NULL,
        type_client varchar(255) NULL,
        prets_decaisses int NULL,
        clients_decaisses int NULL,
        montant_decaisse decimal(19,4) NULL,
        montant_moyen_pret decimal(19,4) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_decaissements_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_echeances_futures', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_echeances_futures (
        mois_echeance date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        prets_concernes int NULL,
        echeances int NULL,
        capital_attendu decimal(19,4) NULL,
        interet_attendu decimal(19,4) NULL,
        commission_attendue decimal(19,4) NULL,
        epargne_attendue decimal(19,4) NULL,
        total_attendu decimal(19,4) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_echeances_futures_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_couverture', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_couverture (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        code_client varchar(100) NULL,
        nom_client varchar(500) NULL,
        numero_pret varchar(100) NULL,
        montant_initial decimal(19,4) NULL,
        encours decimal(19,4) NULL,
        arriere decimal(19,4) NULL,
        epargne_client decimal(19,4) NULL,
        caution decimal(19,4) NULL,
        garantie decimal(19,4) NULL,
        arriere_couvert decimal(19,4) NULL,
        principal_couvert decimal(19,4) NULL,
        exposition_nette decimal(19,4) NULL,
        prenoms_client varchar(255) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_couverture_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_concentration', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_concentration (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        prets_actifs int NULL,
        encours decimal(19,4) NULL,
        encours_top_10_pct decimal(19,4) NULL,
        prets_top_10_pct int NULL,
        part_top_10_pct decimal(18,8) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_concentration_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_tranches', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_tranches (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        tranche_montant varchar(100) NULL,
        clients int NULL,
        prets int NULL,
        montant_initial decimal(19,4) NULL,
        encours decimal(19,4) NULL,
        par_1_plus decimal(19,4) NULL,
        par_30_plus decimal(19,4) NULL,
        par_90_plus decimal(19,4) NULL,
        taux_par_1_plus decimal(18,8) NULL,
        taux_par_30_plus decimal(18,8) NULL,
        taux_par_90_plus decimal(18,8) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_tranches_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_vintage', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_vintage (
        cohorte_decaissement date NOT NULL,
        age_cohorte_mois int NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        prets_decaisses int NULL,
        montant_initial_cohorte decimal(19,4) NULL,
        encours_restant decimal(19,4) NULL,
        par_30_plus decimal(19,4) NULL,
        par_90_plus decimal(19,4) NULL,
        par_30_sur_initial decimal(18,8) NULL,
        par_90_sur_initial decimal(18,8) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_vintage_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_retention', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_retention (
        mois_solde date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        clients_arrives_echeance int NULL,
        prets_soldes int NULL,
        montant_prets_soldes decimal(19,4) NULL,
        clients_renouveles int NULL,
        clients_renouveles_90j int NULL,
        retention decimal(18,8) NULL,
        retention_90j decimal(18,8) NULL,
        delai_moyen_renouvellement decimal(18,4) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_retention_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_provisions_detail', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_provisions_detail (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        code_client varchar(100) NULL,
        nom_client varchar(500) NULL,
        numero_pret varchar(100) NULL,
        montant_initial decimal(19,4) NULL,
        tranche_montant varchar(100) NULL,
        provision decimal(19,4) NULL,
        prenoms_client varchar(255) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_provisions_detail_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_duree', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_duree (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        numero_pret varchar(100) NULL,
        code_client varchar(100) NULL,
        nom_client varchar(500) NULL,
        date_effet date NULL,
        date_fin_echeance date NULL,
        montant_initial decimal(19,4) NULL,
        echeances_totales int NULL,
        echeances_restantes int NULL,
        duree_theorique_mois int NULL,
        tranche_echeances_restantes varchar(100) NULL,
        tranche_total_echeances varchar(100) NULL,
        prenoms_client varchar(255) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_duree_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_credit_tendance_par', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_credit_tendance_par (
        date_situation date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_credit varchar(255) NULL,
        devise varchar(10) NOT NULL,
        prets_actifs int NULL,
        encours decimal(19,4) NULL,
        par_1_plus decimal(19,4) NULL,
        par_30_plus decimal(19,4) NULL,
        par_90_plus decimal(19,4) NULL,
        taux_par_30_plus decimal(18,8) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_credit_tendance_par_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_epargne_soldes', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_epargne_soldes (
        date_situation date NOT NULL,
        mois date NOT NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        produit_epargne varchar(255) NULL,
        type_compte varchar(100) NULL,
        devise varchar(10) NOT NULL,
        comptes int NULL,
        clients int NULL,
        solde_epargne decimal(19,4) NULL,
        solde_moyen_compte decimal(19,4) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_epargne_soldes_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_conformite', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_conformite (
        analyse varchar(255) NULL,
        type_element varchar(255) NULL,
        section varchar(255) NULL,
        ligne_reporting int NULL,
        rubrique varchar(500) NULL,
        date_debut date NULL,
        date_fin date NULL,
        date_evenement date NULL,
        code_client varchar(100) NULL,
        nom_client varchar(500) NULL,
        numero_compte varchar(100) NULL,
        numero_alerte varchar(100) NULL,
        reference_interne varchar(255) NULL,
        reference_externe varchar(255) NULL,
        numero_operation varchar(255) NULL,
        type_operation varchar(255) NULL,
        description varchar(1000) NULL,
        etat varchar(255) NULL,
        statut_revue varchar(100) NULL,
        statut_couverture varchar(100) NULL,
        origine_declaration varchar(255) NULL,
        devise varchar(10) NULL,
        montant decimal(19,4) NULL,
        volume decimal(19,4) NULL,
        nombre decimal(19,4) NULL,
        niveau_risque varchar(255) NULL,
        profil_risque varchar(255) NULL,
        severite varchar(100) NULL,
        action_recommandee varchar(1000) NULL,
        origine_donnee varchar(255) NULL,
        commentaire varchar(2000) NULL,
        point_service varchar(255) NULL,
        motif varchar(1000) NULL,
        indicateurs varchar(1000) NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_conformite_loaded_at DEFAULT (sysdatetime())
    );
END;
GO

IF OBJECT_ID(N'rpt.f_clients', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.f_clients (
        date_debut date NOT NULL,
        date_fin date NOT NULL,
        code_client varchar(100) NOT NULL,
        nom_client varchar(500) NULL,
        type_client varchar(255) NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        date_adhesion date NULL,
        devise varchar(10) NOT NULL,
        statut_client varchar(100) NULL,
        client_actif bit NULL,
        comptes int NULL,
        comptes_ouverts int NULL,
        comptes_clotures int NULL,
        comptes_bloques int NULL,
        comptes_dormants int NULL,
        comptes_inactifs int NULL,
        derniere_operation date NULL,
        solde_epargne decimal(19,4) NULL,
        credits_actifs int NULL,
        credits_a_rembourser int NULL,
        echeances_credit int NULL,
        capital_credit_prevu decimal(19,4) NULL,
        interet_credit_a_rembourser decimal(19,4) NULL,
        commission_credit_prevue decimal(19,4) NULL,
        epargne_credit_prevue decimal(19,4) NULL,
        montant_credit_a_rembourser decimal(19,4) NULL,
        montant_credit_restant decimal(19,4) NULL,
        interet_epargne_credite decimal(19,4) NULL,
        dat_a_echeance int NULL,
        montant_dat_a_echeance decimal(19,4) NULL,
        premiere_echeance_dat date NULL,
        derniere_echeance_dat date NULL,
        avec_compte_ouvert bit NULL,
        avec_compte_bloque bit NULL,
        avec_compte_dormant bit NULL,
        avec_credit_a_rembourser bit NULL,
        avec_interet_credit_a_rembourser bit NULL,
        beneficiaire_interet_epargne bit NULL,
        avec_dat_a_echeance bit NULL,
        batch_id bigint NULL,
        loaded_at datetime2(0) NOT NULL CONSTRAINT df_rpt_f_clients_loaded_at DEFAULT (sysdatetime())
    );
END;
GO
