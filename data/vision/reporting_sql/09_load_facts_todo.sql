/*
  BB_VISION_REPORTING - plan de chargement des faits

  Ce fichier est volontairement un squelette. Il documente les requetes sources a transformer
  progressivement en procedures de chargement rpt.load_*.

  Regle : chaque chargement doit rester autonome, separer les devises et enregistrer batch_id.
*/

USE BB_VISION_REPORTING;
GO

/*
  Mapping prioritaire Power BI -> requetes.sql

  rpt.f_credit_portefeuille       <- Q97, Q109 ; rapprochement detail Q96
  rpt.f_credit_par_detail         <- Q96 et Q145
  rpt.f_credit_top_encours        <- Q98
  rpt.f_credit_decaissements      <- Q99
  rpt.f_credit_echeances_futures  <- Q100 et Q146
  rpt.f_credit_retention          <- Q101
  rpt.f_credit_vintage            <- Q102
  rpt.f_epargne_soldes            <- Q103, Q110, Q113
  rpt.f_credit_tranches           <- Q104
  rpt.f_credit_concentration      <- Q105
  rpt.f_credit_couverture         <- Q106 et Q147
  rpt.f_credit_provisions_detail  <- Q107
  rpt.f_credit_duree              <- Q108
  rpt.f_credit_tendance_par       <- Q109
  rpt.f_conformite                <- Q156
  rpt.f_clients                   <- Q157
*/

CREATE OR ALTER PROCEDURE rpt.load_all_facts
    @source_database sysname = N'BB_VISION_PRO_TEST',
    @date_debut date,
    @date_fin date,
    @id_devise_reporting int = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @batch_id bigint;
    EXEC ctl.start_batch
        @source_database = @source_database,
        @date_debut = @date_debut,
        @date_fin = @date_fin,
        @id_devise_reporting = @id_devise_reporting,
        @batch_id = @batch_id OUTPUT;

    /*
      Prochaine implementation :
      1. Transformer chaque requete source en INSERT INTO rpt.f_*.
      2. Supprimer d'abord les lignes du meme perimetre date/devise si le chargement est rejouable.
      3. Inserer batch_id et loaded_at.
      4. Executer 07_quality_checks.sql.
      5. Alimenter ctl.kpi_reconciliation.
    */

    EXEC ctl.end_batch
        @batch_id = @batch_id,
        @status = 'TODO',
        @message = 'Squelette cree. Implementer les INSERT depuis requetes.sql avant utilisation production.';
END;
GO
