USE BB_VISION_REPORTING;
GO

/*
  Rechargement mensuel du reporting Power BI

  Modifier uniquement @date_debut et @date_fin pour changer la periode.
  @id_devise_reporting = NULL charge toutes les devises utiles au reporting.

  Base source locale actuelle :
  - BB_VISION_PRO_TEST
*/

DECLARE @date_debut date = '2026-06-01';
DECLARE @date_fin   date = '2026-06-30';

EXEC rpt.load_all_facts
    @source_database = N'BB_VISION_PRO_TEST',
    @date_debut = @date_debut,
    @date_fin = @date_fin,
    @id_devise_reporting = NULL;

SELECT TOP (5)
    batch_id,
    source_database,
    date_debut,
    date_fin,
    id_devise_reporting,
    status,
    started_at,
    ended_at,
    message
FROM ctl.etl_batch
ORDER BY batch_id DESC;

SELECT 'f_conformite' AS table_name, COUNT_BIG(*) AS lignes
FROM rpt.f_conformite
WHERE date_debut = @date_debut
  AND date_fin = @date_fin

UNION ALL

SELECT 'f_clients', COUNT_BIG(*)
FROM rpt.f_clients
WHERE date_debut = @date_debut
  AND date_fin = @date_fin;
