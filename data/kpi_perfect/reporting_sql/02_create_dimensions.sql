/*
  BB_VISION_REPORTING - dimensions conformes
*/

USE BB_VISION_REPORTING;
GO

IF OBJECT_ID(N'rpt.d_date', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.d_date (
        date_key int NOT NULL CONSTRAINT pk_rpt_d_date PRIMARY KEY,
        date_value date NOT NULL CONSTRAINT uq_rpt_d_date_date_value UNIQUE,
        annee smallint NOT NULL,
        numero_mois tinyint NOT NULL,
        mois varchar(20) NOT NULL,
        annee_mois char(7) NOT NULL,
        debut_mois date NOT NULL,
        fin_mois date NOT NULL
    );
END;
GO

IF OBJECT_ID(N'rpt.d_devise', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.d_devise (
        devise varchar(10) NOT NULL CONSTRAINT pk_rpt_d_devise PRIMARY KEY,
        libelle varchar(100) NULL,
        symbole varchar(20) NULL,
        actif bit NOT NULL CONSTRAINT df_rpt_d_devise_actif DEFAULT (1)
    );
END;
GO

IF OBJECT_ID(N'rpt.d_agence', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.d_agence (
        code_agence varchar(50) NOT NULL CONSTRAINT pk_rpt_d_agence PRIMARY KEY,
        agence varchar(255) NOT NULL,
        zone varchar(255) NULL,
        actif bit NOT NULL CONSTRAINT df_rpt_d_agence_actif DEFAULT (1)
    );
END;
GO

IF OBJECT_ID(N'rpt.d_client', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.d_client (
        code_client varchar(100) NOT NULL CONSTRAINT pk_rpt_d_client PRIMARY KEY,
        nom_client varchar(500) NULL,
        type_client varchar(255) NULL,
        statut_client varchar(100) NULL,
        code_agence varchar(50) NULL,
        agence varchar(255) NULL,
        date_adhesion date NULL,
        actif bit NULL
    );
END;
GO

IF OBJECT_ID(N'rpt.d_produit_credit', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.d_produit_credit (
        produit_credit varchar(255) NOT NULL CONSTRAINT pk_rpt_d_produit_credit PRIMARY KEY,
        objet_financement varchar(255) NULL,
        secteur_activite varchar(255) NULL,
        periodicite varchar(100) NULL,
        actif bit NOT NULL CONSTRAINT df_rpt_d_produit_credit_actif DEFAULT (1)
    );
END;
GO

IF OBJECT_ID(N'rpt.d_produit_epargne', N'U') IS NULL
BEGIN
    CREATE TABLE rpt.d_produit_epargne (
        produit_epargne varchar(255) NOT NULL CONSTRAINT pk_rpt_d_produit_epargne PRIMARY KEY,
        type_compte varchar(100) NULL,
        actif bit NOT NULL CONSTRAINT df_rpt_d_produit_epargne_actif DEFAULT (1)
    );
END;
GO
