/*
  BB_VISION_REPORTING - chargement initial des dimensions

  Source prototype connue :
    serveur : CDBBIMFL065
    base    : BB_VISION_PRO_TEST

  Le script lit la base source et charge seulement les dimensions de base.
*/

USE BB_VISION_REPORTING;
GO

DECLARE @source_database sysname = N'BB_VISION_PRO_TEST';
DECLARE @date_debut date = '2026-06-01';
DECLARE @date_fin date = '2026-06-30';
DECLARE @sql nvarchar(max);

;WITH dates AS (
    SELECT @date_debut AS date_value
    UNION ALL
    SELECT DATEADD(day, 1, date_value)
    FROM dates
    WHERE date_value < @date_fin
)
MERGE rpt.d_date AS tgt
USING (
    SELECT
        CONVERT(int, CONVERT(char(8), date_value, 112)) AS date_key,
        date_value,
        YEAR(date_value) AS annee,
        MONTH(date_value) AS numero_mois,
        DATENAME(month, date_value) AS mois,
        CONVERT(char(7), date_value, 120) AS annee_mois,
        DATEFROMPARTS(YEAR(date_value), MONTH(date_value), 1) AS debut_mois,
        EOMONTH(date_value) AS fin_mois
    FROM dates
) AS src
ON tgt.date_key = src.date_key
WHEN NOT MATCHED THEN
    INSERT (date_key, date_value, annee, numero_mois, mois, annee_mois, debut_mois, fin_mois)
    VALUES (src.date_key, src.date_value, src.annee, src.numero_mois, src.mois, src.annee_mois, src.debut_mois, src.fin_mois)
WHEN MATCHED THEN
    UPDATE SET
        date_value = src.date_value,
        annee = src.annee,
        numero_mois = src.numero_mois,
        mois = src.mois,
        annee_mois = src.annee_mois,
        debut_mois = src.debut_mois,
        fin_mois = src.fin_mois
OPTION (MAXRECURSION 32767);

SET @sql = N'
MERGE rpt.d_devise AS tgt
USING (
    SELECT DISTINCT
        CAST(CODE AS varchar(10)) AS devise,
        CAST(LIBELLE AS varchar(100)) AS libelle,
        CAST(SYMBOLE AS varchar(20)) AS symbole
    FROM ' + QUOTENAME(@source_database) + N'.dbo.DEVISES
    WHERE CODE IS NOT NULL
) AS src
ON tgt.devise = src.devise
WHEN NOT MATCHED THEN
    INSERT (devise, libelle, symbole) VALUES (src.devise, src.libelle, src.symbole)
WHEN MATCHED THEN
    UPDATE SET libelle = src.libelle, symbole = src.symbole, actif = 1;';
EXEC sys.sp_executesql @sql;

SET @sql = N'
MERGE rpt.d_agence AS tgt
USING (
    SELECT DISTINCT
        CAST(CODE AS varchar(50)) AS code_agence,
        CAST(NOM AS varchar(255)) AS agence
    FROM ' + QUOTENAME(@source_database) + N'.dbo.POINTS_SERVICE
    WHERE CODE IS NOT NULL
) AS src
ON tgt.code_agence = src.code_agence
WHEN NOT MATCHED THEN
    INSERT (code_agence, agence) VALUES (src.code_agence, src.agence)
WHEN MATCHED THEN
    UPDATE SET agence = src.agence, actif = 1;';
EXEC sys.sp_executesql @sql;
GO
