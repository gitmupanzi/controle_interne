/*
  BB_VISION_REPORTING - index de demarrage

  A ajuster apres observation des plans d'execution et du volume reel.
*/

USE BB_VISION_REPORTING;
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_f_credit_portefeuille_date_devise_agence' AND object_id = OBJECT_ID(N'rpt.f_credit_portefeuille'))
    CREATE INDEX ix_f_credit_portefeuille_date_devise_agence
    ON rpt.f_credit_portefeuille (date_situation, devise, code_agence)
    INCLUDE (produit_credit, prets_actifs, encours, par_30_plus, par_90_plus, provision);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_f_credit_par_detail_date_devise_client' AND object_id = OBJECT_ID(N'rpt.f_credit_par_detail'))
    CREATE INDEX ix_f_credit_par_detail_date_devise_client
    ON rpt.f_credit_par_detail (date_situation, devise, code_client)
    INCLUDE (numero_pret, produit_credit, jours_retard, arriere, encours, provision);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_f_credit_echeances_futures_mois_devise' AND object_id = OBJECT_ID(N'rpt.f_credit_echeances_futures'))
    CREATE INDEX ix_f_credit_echeances_futures_mois_devise
    ON rpt.f_credit_echeances_futures (mois_echeance, devise, code_agence)
    INCLUDE (produit_credit, total_attendu);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_f_epargne_soldes_mois_devise_agence' AND object_id = OBJECT_ID(N'rpt.f_epargne_soldes'))
    CREATE INDEX ix_f_epargne_soldes_mois_devise_agence
    ON rpt.f_epargne_soldes (mois, devise, code_agence)
    INCLUDE (produit_epargne, type_compte, comptes, clients, solde_epargne);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_f_conformite_date_devise_type' AND object_id = OBJECT_ID(N'rpt.f_conformite'))
    CREATE INDEX ix_f_conformite_date_devise_type
    ON rpt.f_conformite (date_fin, devise, type_element)
    INCLUDE (analyse, statut_couverture, statut_revue, severite, nombre, montant);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_f_clients_date_devise_client' AND object_id = OBJECT_ID(N'rpt.f_clients'))
    CREATE INDEX ix_f_clients_date_devise_client
    ON rpt.f_clients (date_fin, devise, code_client)
    INCLUDE (type_client, statut_client, client_actif, avec_compte_ouvert, avec_compte_dormant, avec_credit_a_rembourser, avec_dat_a_echeance);
GO
