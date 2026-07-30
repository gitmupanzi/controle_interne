/*
  BB_VISION_REPORTING - controles qualite rapides
*/

USE BB_VISION_REPORTING;
GO

DECLARE @date_debut date = '2026-06-01';
DECLARE @date_fin date = '2026-06-30';

SELECT 'rpt.d_date' AS table_name, COUNT_BIG(*) AS rows_count FROM rpt.d_date
UNION ALL SELECT 'rpt.d_devise', COUNT_BIG(*) FROM rpt.d_devise
UNION ALL SELECT 'rpt.d_agence', COUNT_BIG(*) FROM rpt.d_agence
UNION ALL SELECT 'rpt.f_credit_portefeuille', COUNT_BIG(*) FROM rpt.f_credit_portefeuille
UNION ALL SELECT 'rpt.f_credit_par_detail', COUNT_BIG(*) FROM rpt.f_credit_par_detail
UNION ALL SELECT 'rpt.f_epargne_soldes', COUNT_BIG(*) FROM rpt.f_epargne_soldes
UNION ALL SELECT 'rpt.f_conformite', COUNT_BIG(*) FROM rpt.f_conformite
UNION ALL SELECT 'rpt.f_clients', COUNT_BIG(*) FROM rpt.f_clients;

SELECT
    'f_credit_portefeuille_devise_nulle' AS controle,
    COUNT_BIG(*) AS nombre
FROM rpt.f_credit_portefeuille
WHERE devise IS NULL OR LTRIM(RTRIM(devise)) = '';

SELECT
    'f_credit_portefeuille_doublon_grain' AS controle,
    date_situation,
    code_agence,
    produit_credit,
    devise,
    COUNT_BIG(*) AS nombre
FROM rpt.f_credit_portefeuille
GROUP BY date_situation, code_agence, produit_credit, devise
HAVING COUNT_BIG(*) > 1;

SELECT
    'f_clients_doublon_grain' AS controle,
    date_fin,
    code_client,
    devise,
    COUNT_BIG(*) AS nombre
FROM rpt.f_clients
GROUP BY date_fin, code_client, devise
HAVING COUNT_BIG(*) > 1;

SELECT
    'montants_credit_multi_devises_a_eviter' AS rappel,
    devise,
    SUM(encours) AS encours
FROM rpt.f_credit_portefeuille
WHERE date_situation BETWEEN @date_debut AND @date_fin
GROUP BY devise
ORDER BY devise;

SELECT
    'conformite_q156_par_analyse' AS controle,
    analyse,
    devise,
    COUNT_BIG(*) AS lignes,
    SUM(ISNULL(nombre, 0)) AS nombre_total,
    SUM(ISNULL(montant, 0)) AS montant_total
FROM rpt.f_conformite
WHERE date_fin BETWEEN @date_debut AND @date_fin
GROUP BY analyse, devise
ORDER BY analyse, devise;
GO
