/*
Catalogue de requetes de controle interne - base BB_VISION_PRO
Tables principales analysees :
  - dbo.OPERATIONS
  - dbo.OPERATIONS_API
  - dbo.HDPM
  - dbo.HDPM_API
  - dbo.ADHERENTS

Notes :
  - Ajuster @date_debut et @date_fin selon la periode d'audit.
  - Pour executer une requete seule dans SSMS, selectionner aussi les deux lignes DECLARE ci-dessous.
  - Les rapprochements API utilisent surtout CODE / NUM_TRANSACTION / NUMERO_RECU.
  - Correspondance devise observee dans dbo.DEVISES :
      ID_DEVISE = 1 : USD - Dollars Americains
      ID_DEVISE = 2 : CDF - Franc Congolais
  - Pour le reporting BCC/LBC-FT en CDF, utiliser @id_devise_reporting = 2.
  - Exemple de seuils si le taux retenu est 1 USD = 2 800 CDF :
      5 000 USD  = 14 000 000 CDF
      10 000 USD = 28 000 000 CDF
*/

USE [BB_VISION_PRO];
GO

DECLARE @date_debut date = '2026-01-01';
DECLARE @date_fin   date = '2026-12-31';
DECLARE @seuil_5k_usd_cdf  float = 0; -- A renseigner avec l'equivalent CDF de 5 000 USD.
DECLARE @seuil_10k_usd_cdf float = 0; -- A renseigner avec l'equivalent CDF de 10 000 USD.
DECLARE @id_devise_reporting int = NULL; -- Utiliser 2 pour CDF. NULL = toutes devises.

/*
Exemple pour produire la synthese Excel LBC-FT de juin 2026 en CDF :

DECLARE @date_debut date = '2026-06-01';
DECLARE @date_fin   date = '2026-06-30';
DECLARE @seuil_5k_usd_cdf  float = 14000000;
DECLARE @seuil_10k_usd_cdf float = 28000000;
DECLARE @id_devise_reporting int = 2;

Puis executer la requete 38.
*/

/*
01. Volumetrie des tables principales
Objectif : donner une vue rapide du nombre de lignes disponibles dans les tables d'analyse.
Lecture : sert de controle de presence des donnees avant les analyses detaillees.
*/
SELECT 'OPERATIONS' AS table_name, COUNT(*) AS nb_lignes FROM dbo.OPERATIONS
UNION ALL SELECT 'OPERATIONS_API', COUNT(*) FROM dbo.OPERATIONS_API
UNION ALL SELECT 'HDPM', COUNT(*) FROM dbo.HDPM
UNION ALL SELECT 'HDPM_API', COUNT(*) FROM dbo.HDPM_API
UNION ALL SELECT 'ADHERENTS', COUNT(*) FROM dbo.ADHERENTS;

/*
02. Volumetrie des operations par mois, source et statut annule
Objectif : suivre le nombre d'operations par mois, par source et selon le statut d'annulation.
Lecture : permet d'identifier les pics d'activite et les mois anormaux.
*/
SELECT
    source_table,
    DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1) AS mois,
    ISNULL(CAST(ANNULE AS varchar(10)), 'NULL') AS statut_annule,
    COUNT(*) AS nb_operations
FROM (
    SELECT 'OPERATIONS' AS source_table, DATE_OPERATION, ANNULE
    FROM dbo.OPERATIONS
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    UNION ALL
    SELECT 'OPERATIONS_API', DATE_OPERATION, ANNULE
    FROM dbo.OPERATIONS_API
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
) x
GROUP BY source_table, DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1), ANNULE
ORDER BY mois, source_table, statut_annule;

/*
03. Operations creees mais non validees
Objectif : lister les operations actives dont la validation est absente ou incomplete.
Lecture : met en evidence les operations a regulariser ou a expliquer.
*/
SELECT
    'OPERATIONS' AS source_table,
    o.ID,
    o.DATE_OPERATION,
    o.DATE_SAISIE,
    o.DATE_VALIDATION,
    o.DATE_VALIDE,
    o.ID_POINT_SERVICE,
    o.ID_TYPE_OPERATION,
    CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(o.ANNULE, 0) = 0
  AND (o.DATE_VALIDATION IS NULL OR o.DATE_VALIDE IS NULL)
UNION ALL
SELECT
    'OPERATIONS_API',
    CAST(oa.ID AS varchar(255)),
    oa.DATE_OPERATION,
    oa.DATE_SAISIE,
    oa.DATE_VALIDATION,
    oa.DATE_VALIDE,
    oa.ID_POINT_SERVICE,
    oa.ID_TYPE_OPERATION,
    oa.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(oa.ANNULE, 0) = 0
  AND oa.DATE_VALIDATION IS NULL
ORDER BY DATE_OPERATION, source_table;

/*
04. Operations saisies apres la date d'operation
Objectif : detecter les operations enregistrees apres leur date effective.
Lecture : un delai important peut signaler une saisie tardive ou un rattrapage manuel.
*/
SELECT
    'OPERATIONS' AS source_table,
    o.ID,
    o.DATE_OPERATION,
    o.DATE_SAISIE,
    DATEDIFF(day, o.DATE_OPERATION, CAST(o.DATE_SAISIE AS date)) AS delai_saisie_jours,
    CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    o.ID_POINT_SERVICE,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND o.DATE_SAISIE IS NOT NULL
  AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION
UNION ALL
SELECT
    'OPERATIONS_API',
    CAST(oa.ID AS varchar(255)),
    oa.DATE_OPERATION,
    oa.DATE_SAISIE,
    DATEDIFF(day, oa.DATE_OPERATION, CAST(oa.DATE_SAISIE AS date)),
    oa.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    oa.ID_POINT_SERVICE,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND oa.DATE_SAISIE IS NOT NULL
  AND CAST(oa.DATE_SAISIE AS date) > oa.DATE_OPERATION
ORDER BY delai_saisie_jours DESC, DATE_OPERATION;

/*
05. Operations validees avant la saisie ou avant la date d'operation
Objectif : identifier les incoherences chronologiques entre operation, saisie et validation.
Lecture : ces cas doivent etre verifies car ils peuvent reveler un probleme de workflow ou de donnees.
*/
SELECT
    'OPERATIONS' AS source_table,
    o.ID,
    o.DATE_OPERATION,
    o.DATE_SAISIE,
    o.DATE_VALIDE,
    CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
    CAST(o.ID_UTILISATEUR_VALIDE AS bigint) AS ID_UTILISATEUR_VALIDE,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    uv.LOGIN AS login_validateur,
    uv.NOM AS nom_validateur,
    uv.PRENOM AS prenom_validateur,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
LEFT JOIN dbo.UTILISATEURS uv ON uv.id = o.ID_UTILISATEUR_VALIDE
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (
        (o.DATE_VALIDE IS NOT NULL AND o.DATE_SAISIE IS NOT NULL AND o.DATE_VALIDE < o.DATE_SAISIE)
        OR (o.DATE_VALIDATION IS NOT NULL AND o.DATE_VALIDATION < o.DATE_OPERATION)
      )
UNION ALL
SELECT
    'OPERATIONS_API',
    CAST(oa.ID AS varchar(255)),
    oa.DATE_OPERATION,
    oa.DATE_SAISIE,
    oa.DATE_VALIDE,
    oa.ID_UTILISATEUR,
    oa.ID_UTILISATEUR_VALIDE,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    uv.LOGIN AS login_validateur,
    uv.NOM AS nom_validateur,
    uv.PRENOM AS prenom_validateur,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
LEFT JOIN dbo.UTILISATEURS uv ON uv.id = oa.ID_UTILISATEUR_VALIDE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (
        (oa.DATE_VALIDE IS NOT NULL AND oa.DATE_SAISIE IS NOT NULL AND oa.DATE_VALIDE < oa.DATE_SAISIE)
        OR (oa.DATE_VALIDATION IS NOT NULL AND oa.DATE_VALIDATION < oa.DATE_OPERATION)
      )
ORDER BY DATE_OPERATION;

/*
06. Operations sans utilisateur, point de service ou type operation
Objectif : reperer les operations avec des champs de rattachement essentiels manquants.
Lecture : ces absences limitent la tracabilite operationnelle et le reporting par agence/utilisateur.
*/
SELECT
    'OPERATIONS' AS source_table,
    o.ID,
    o.DATE_OPERATION,
    CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    o.ID_POINT_SERVICE,
    o.ID_TYPE_OPERATION,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (o.ID_UTILISATEUR IS NULL OR o.ID_POINT_SERVICE IS NULL OR o.ID_TYPE_OPERATION IS NULL)
UNION ALL
SELECT
    'OPERATIONS_API',
    CAST(oa.ID AS varchar(255)),
    oa.DATE_OPERATION,
    oa.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    oa.ID_POINT_SERVICE,
    oa.ID_TYPE_OPERATION,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (oa.ID_UTILISATEUR IS NULL OR oa.ID_POINT_SERVICE IS NULL OR oa.ID_TYPE_OPERATION IS NULL)
ORDER BY DATE_OPERATION, source_table;

/*
07. Doublons de numero de transaction dans OPERATIONS
Objectif : detecter les numeros de transaction utilises plusieurs fois dans le back-office.
Lecture : chaque doublon doit etre rapproche du metier pour distinguer cas normal, reprise ou anomalie.
*/
SELECT
    NUM_TRANSACTION,
    COUNT(*) AS nb_operations,
    MIN(DATE_OPERATION) AS premiere_date,
    MAX(DATE_OPERATION) AS derniere_date
FROM dbo.OPERATIONS
WHERE NUM_TRANSACTION IS NOT NULL
  AND LTRIM(RTRIM(NUM_TRANSACTION)) <> ''
GROUP BY NUM_TRANSACTION
HAVING COUNT(*) > 1
ORDER BY nb_operations DESC, NUM_TRANSACTION;

/*
08. Doublons de numero de recu dans OPERATIONS
Objectif : detecter les recus partages par plusieurs operations.
Lecture : utile pour verifier l'unicite documentaire et les risques de double comptabilisation.
*/
SELECT
    NUMERO_RECU,
    COUNT(*) AS nb_operations,
    MIN(DATE_OPERATION) AS premiere_date,
    MAX(DATE_OPERATION) AS derniere_date
FROM dbo.OPERATIONS
WHERE NUMERO_RECU IS NOT NULL
  AND LTRIM(RTRIM(NUMERO_RECU)) <> ''
GROUP BY NUMERO_RECU
HAVING COUNT(*) > 1
ORDER BY nb_operations DESC, NUMERO_RECU;

/*
09. Doublons metier potentiels : meme date, utilisateur, type, reference et description
Objectif : identifier les operations tres similaires pouvant correspondre a une double saisie.
Lecture : le resultat doit etre examine operation par operation avec les justificatifs.
*/
SELECT
    DATE_OPERATION,
    ID_UTILISATEUR,
    ID_POINT_SERVICE,
    ID_TYPE_OPERATION,
    NUM_TRANSACTION,
    NUMERO_RECU,
    DESCRIPTION,
    COUNT(*) AS nb_doublons
FROM dbo.OPERATIONS
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY DATE_OPERATION, ID_UTILISATEUR, ID_POINT_SERVICE, ID_TYPE_OPERATION, NUM_TRANSACTION, NUMERO_RECU, DESCRIPTION
HAVING COUNT(*) > 1
ORDER BY nb_doublons DESC, DATE_OPERATION;

/*
10. Operations annulees sans operation annulee referencee
Objectif : lister les operations marquees annulees sans lien vers l'operation d'origine.
Lecture : absence de reference = tracabilite d'annulation incomplete.
*/
SELECT
    ID,
    DATE_OPERATION,
    ANNULE,
    ID_OPERATION_ANNULE,
    ID_OPERATION_MERE,
    NUM_TRANSACTION,
    NUMERO_RECU,
    DESCRIPTION
FROM dbo.OPERATIONS
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(ANNULE, 0) = 1
  AND ID_OPERATION_ANNULE IS NULL
ORDER BY DATE_OPERATION;

/*
11. Operations referencees comme annulees mais introuvables
Objectif : verifier que les references d'annulation pointent vers une operation existante.
Lecture : les lignes retournees indiquent des liens rompus ou des donnees manquantes.
*/
SELECT
    o.ID,
    o.DATE_OPERATION,
    o.ID_OPERATION_ANNULE,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.OPERATIONS oa ON oa.ID = o.ID_OPERATION_ANNULE
WHERE o.ID_OPERATION_ANNULE IS NOT NULL
  AND oa.ID IS NULL
ORDER BY o.DATE_OPERATION;

/*
12. HDPM sans operation back-office correspondante
Objectif : detecter les ecritures comptables HDPM rattachees a une operation inexistante.
Lecture : ces cas doivent etre expliques car ils cassent le lien operation-comptabilite.
*/
SELECT
    h.ID,
    h.DATE_OPERATION,
    h.ID_OPERATION,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.NUM_TRANSACTION,
    h.NUMERO_RECU,
    h.DESCRIPTION
FROM dbo.HDPM h
LEFT JOIN dbo.OPERATIONS o ON o.ID = h.ID_OPERATION
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND h.ID_OPERATION IS NOT NULL
  AND o.ID IS NULL
ORDER BY h.DATE_OPERATION;

/*
13. Operations back-office sans ecriture HDPM
Objectif : identifier les operations actives sans impact comptable retrouve dans HDPM.
Lecture : utile pour verifier l'exhaustivite de la comptabilisation.
*/
SELECT
    o.ID,
    o.DATE_OPERATION,
    o.NUM_TRANSACTION,
    o.NUMERO_RECU,
    o.ID_TYPE_OPERATION,
    o.ID_POINT_SERVICE,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(o.ANNULE, 0) = 0
  AND h.ID IS NULL
ORDER BY o.DATE_OPERATION;

/*
14. Equilibre debit/credit par operation dans HDPM
Objectif : controler que les ecritures back-office sont equilibrees entre debit et credit.
Lecture : un ecart non nul signale une anomalie comptable potentielle.
*/
SELECT
    h.ID_OPERATION,
    MIN(h.DATE_OPERATION) AS date_operation,
    COUNT(*) AS nb_lignes,
    SUM(CASE WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_debit,
    SUM(CASE WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_credit,
    SUM(CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN -ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END) AS ecart
FROM dbo.HDPM h
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND h.ID_OPERATION IS NOT NULL
GROUP BY h.ID_OPERATION
HAVING ABS(SUM(CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN -ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END)) > 0.01
ORDER BY ABS(SUM(CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN -ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END)) DESC;

/*
15. Equilibre debit/credit par operation dans HDPM_API
Objectif : controler l'equilibre debit/credit des ecritures issues de l'API mobile.
Lecture : chaque operation mobile devrait generalement avoir une paire debit/credit equilibree.
*/
SELECT
    h.ID_OPERATION,
    MIN(h.DATE_OPERATION) AS date_operation,
    COUNT(*) AS nb_lignes,
    SUM(CASE WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_debit,
    SUM(CASE WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_credit,
    SUM(CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN -ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END) AS ecart
FROM dbo.HDPM_API h
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND h.ID_OPERATION IS NOT NULL
GROUP BY h.ID_OPERATION
HAVING ABS(SUM(CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN -ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END)) > 0.01
ORDER BY ABS(SUM(CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN -ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END)) DESC;

/*
16. Lignes HDPM avec montant nul, negatif ou sens absent
Objectif : reperer les ecritures comptables dont les montants ou le sens sont invalides/incomplets.
Lecture : ces lignes sont prioritaires pour controle de qualite des donnees comptables.
*/
SELECT
    'HDPM' AS source_table,
    h.ID,
    h.DATE_OPERATION,
    h.ID_OPERATION,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    h.DESCRIPTION
FROM dbo.HDPM h
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (h.MONTANT_OPERATION IS NULL OR h.MONTANT_OPERATION <= 0 OR h.SENS IS NULL)
UNION ALL
SELECT
    'HDPM_API',
    CAST(h.ID AS varchar(255)),
    h.DATE_OPERATION,
    h.ID_OPERATION,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    h.DESCRIPTION
FROM dbo.HDPM_API h
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (h.MONTANT_OPERATION IS NULL OR h.MONTANT_OPERATION <= 0 OR h.SENS IS NULL)
ORDER BY DATE_OPERATION, source_table;

/*
17. Ecritures comptables avec date valeur differente de la date operation
Objectif : lister les ecritures dont la date valeur differe de la date d'operation.
Lecture : un ecart important peut etre normal mais doit etre justifie selon la procedure.
*/
SELECT
    ID,
    DATE_OPERATION,
    DATE_VALEUR,
    DATEDIFF(day, DATE_OPERATION, DATE_VALEUR) AS ecart_jours,
    ID_OPERATION,
    ID_COMPTE,
    SENS,
    MONTANT_OPERATION,
    DESCRIPTION
FROM dbo.HDPM
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND DATE_VALEUR IS NOT NULL
  AND DATE_OPERATION IS NOT NULL
  AND DATE_VALEUR <> DATE_OPERATION
ORDER BY ABS(DATEDIFF(day, DATE_OPERATION, DATE_VALEUR)) DESC;

/*
18. Mouvements HDPM sans compte ou avec compte inexistant
Objectif : verifier le rattachement de chaque ecriture a un compte existant.
Lecture : les lignes retournees indiquent un probleme de referentiel compte.
*/
SELECT
    h.ID,
    h.DATE_OPERATION,
    h.ID_OPERATION,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.DESCRIPTION
FROM dbo.HDPM h
LEFT JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND (h.ID_COMPTE IS NULL OR c.ID IS NULL)
ORDER BY h.DATE_OPERATION;

/*
19. Mouvements sur comptes clotures/inactifs selon ETAT
Objectif : detecter les mouvements passes sur des comptes dont l'etat n'est pas actif/ouvert.
Lecture : ces mouvements doivent etre justifies ou corriges selon le statut du compte.
*/
SELECT
    h.ID,
    h.DATE_OPERATION,
    h.ID_OPERATION,
    h.ID_COMPTE,
    c.NUM_CPTE,
    c.ETAT,
    h.SENS,
    h.MONTANT_OPERATION,
    h.DESCRIPTION
FROM dbo.HDPM h
INNER JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(c.ETAT, '') NOT IN ('O', 'A')
ORDER BY h.DATE_OPERATION;

/*
20. Rapprochement OPERATIONS vs OPERATIONS_API par NUM_TRANSACTION
Objectif : comparer les operations back-office et API sur les references communes.
Lecture : signale les absences ou differences de date, recu, point de service ou type operation.
*/
SELECT
    COALESCE(o.NUM_TRANSACTION, oa.NUM_TRANSACTION) AS num_transaction,
    o.ID AS id_operation_bo,
    oa.CODE AS code_operation_api,
    oa.ID AS id_operation_api,
    o.DATE_OPERATION AS date_operation_bo,
    oa.DATE_OPERATION AS date_operation_api,
    o.NUMERO_RECU AS numero_recu_bo,
    oa.NUMERO_RECU AS numero_recu_api,
    o.ID_POINT_SERVICE AS point_service_bo,
    oa.ID_POINT_SERVICE AS point_service_api,
    o.ID_TYPE_OPERATION AS type_operation_bo,
    oa.ID_TYPE_OPERATION AS type_operation_api,
    CASE
        WHEN o.ID IS NULL THEN 'Absent OPERATIONS'
        WHEN oa.ID IS NULL THEN 'Absent OPERATIONS_API'
        WHEN o.DATE_OPERATION <> oa.DATE_OPERATION THEN 'Date differente'
        WHEN ISNULL(o.NUMERO_RECU, '') <> ISNULL(oa.NUMERO_RECU, '') THEN 'Numero recu different'
        WHEN ISNULL(o.ID_POINT_SERVICE, '') <> ISNULL(oa.ID_POINT_SERVICE, '') THEN 'Point service different'
        WHEN ISNULL(o.ID_TYPE_OPERATION, '') <> ISNULL(oa.ID_TYPE_OPERATION, '') THEN 'Type operation different'
        ELSE 'OK'
    END AS statut_rapprochement
FROM dbo.OPERATIONS o
FULL OUTER JOIN dbo.OPERATIONS_API oa
    ON oa.NUM_TRANSACTION = o.NUM_TRANSACTION
   AND oa.NUM_TRANSACTION IS NOT NULL
   AND LTRIM(RTRIM(oa.NUM_TRANSACTION)) <> ''
WHERE COALESCE(o.DATE_OPERATION, oa.DATE_OPERATION) BETWEEN @date_debut AND @date_fin
  AND (
        o.ID IS NULL
        OR oa.ID IS NULL
        OR o.DATE_OPERATION <> oa.DATE_OPERATION
        OR ISNULL(o.NUMERO_RECU, '') <> ISNULL(oa.NUMERO_RECU, '')
        OR ISNULL(o.ID_POINT_SERVICE, '') <> ISNULL(oa.ID_POINT_SERVICE, '')
        OR ISNULL(o.ID_TYPE_OPERATION, '') <> ISNULL(oa.ID_TYPE_OPERATION, '')
      )
ORDER BY COALESCE(o.DATE_OPERATION, oa.DATE_OPERATION), statut_rapprochement;

/*
21. Rapprochement des totaux HDPM vs HDPM_API par reference operation
Objectif : comparer les volumes et montants comptables entre HDPM et HDPM_API.
Lecture : met en evidence les operations presentes dans une source mais pas l'autre ou avec ecarts.
*/
WITH hdpm_bo AS (
    SELECT
        ID_OPERATION,
        COUNT(*) AS nb_lignes_bo,
        SUM(CASE WHEN UPPER(ISNULL(SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(MONTANT_OPERATION, 0) ELSE 0 END) AS debit_bo,
        SUM(CASE WHEN UPPER(ISNULL(SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(MONTANT_OPERATION, 0) ELSE 0 END) AS credit_bo
    FROM dbo.HDPM
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    GROUP BY ID_OPERATION
),
hdpm_api AS (
    SELECT
        ID_OPERATION,
        COUNT(*) AS nb_lignes_api,
        SUM(CASE WHEN UPPER(ISNULL(SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(MONTANT_OPERATION, 0) ELSE 0 END) AS debit_api,
        SUM(CASE WHEN UPPER(ISNULL(SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(MONTANT_OPERATION, 0) ELSE 0 END) AS credit_api
    FROM dbo.HDPM_API
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    GROUP BY ID_OPERATION
)
SELECT
    COALESCE(b.ID_OPERATION, a.ID_OPERATION) AS id_operation,
    b.nb_lignes_bo,
    a.nb_lignes_api,
    b.debit_bo,
    a.debit_api,
    b.credit_bo,
    a.credit_api,
    ISNULL(b.debit_bo, 0) - ISNULL(a.debit_api, 0) AS ecart_debit,
    ISNULL(b.credit_bo, 0) - ISNULL(a.credit_api, 0) AS ecart_credit
FROM hdpm_bo b
FULL OUTER JOIN hdpm_api a ON a.ID_OPERATION = b.ID_OPERATION
WHERE b.ID_OPERATION IS NULL
   OR a.ID_OPERATION IS NULL
   OR ISNULL(b.nb_lignes_bo, 0) <> ISNULL(a.nb_lignes_api, 0)
   OR ABS(ISNULL(b.debit_bo, 0) - ISNULL(a.debit_api, 0)) > 0.01
   OR ABS(ISNULL(b.credit_bo, 0) - ISNULL(a.credit_api, 0)) > 0.01
ORDER BY ABS(ISNULL(b.debit_bo, 0) - ISNULL(a.debit_api, 0)) + ABS(ISNULL(b.credit_bo, 0) - ISNULL(a.credit_api, 0)) DESC;

/*
22. Operations par utilisateur avec volumes et delais moyens
Objectif : mesurer l'activite et les delais moyens de saisie par utilisateur.
Lecture : aide a reperer les profils atypiques ou les besoins de supervision.
*/
SELECT
    o.ID_UTILISATEUR,
    u.LOGIN,
    u.NOM,
    u.PRENOM,
    COUNT(*) AS nb_operations,
    SUM(CASE WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1 ELSE 0 END) AS nb_annulees,
    AVG(CASE WHEN o.DATE_SAISIE IS NOT NULL THEN DATEDIFF(day, o.DATE_OPERATION, CAST(o.DATE_SAISIE AS date)) * 1.0 END) AS delai_moyen_saisie_jours
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY o.ID_UTILISATEUR, u.LOGIN, u.NOM, u.PRENOM
ORDER BY nb_operations DESC;

/*
23. Operations saisies et validees par le meme utilisateur
Objectif : detecter les cas d'auto-validation.
Lecture : utile pour verifier la separation des taches et les habilitations.
*/
SELECT
    o.ID,
    o.DATE_OPERATION,
    o.ID_UTILISATEUR,
    u.LOGIN,
    o.ID_UTILISATEUR_VALIDE,
    o.DATE_SAISIE,
    o.DATE_VALIDE,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND o.ID_UTILISATEUR IS NOT NULL
  AND o.ID_UTILISATEUR_VALIDE IS NOT NULL
  AND o.ID_UTILISATEUR = o.ID_UTILISATEUR_VALIDE
ORDER BY o.DATE_OPERATION;

/*
24. Adherents inscrits en doublon par code
Objectif : verifier l'unicite du code adherent.
Lecture : les doublons peuvent perturber le KYC, les comptes et les reportings clients.
*/
SELECT
    CODE,
    COUNT(*) AS nb_adherents,
    MIN(DATE_INSCRIPTION) AS premiere_inscription,
    MAX(DATE_INSCRIPTION) AS derniere_inscription
FROM dbo.ADHERENTS
WHERE CODE IS NOT NULL
  AND LTRIM(RTRIM(CODE)) <> ''
GROUP BY CODE
HAVING COUNT(*) > 1
ORDER BY nb_adherents DESC, CODE;

/*
25. Adherents sans informations essentielles
Objectif : reperer les fiches adherents incompletes sur les champs de base.
Lecture : sert au nettoyage KYC et a l'amelioration de la qualite du referentiel client.
*/
SELECT
    ID,
    CODE,
    NOM_ADHERENT,
    DATE_INSCRIPTION,
    ID_CATEGORIE_ADHERENT,
    ID_TYPE_ADHERENT,
    ID_POINT_SERVICE,
    ID_GESTIONNAIRE,
    EST_VALIDE,
    DROIT_PAYE
FROM dbo.ADHERENTS
WHERE CODE IS NULL
   OR LTRIM(RTRIM(CODE)) = ''
   OR NOM_ADHERENT IS NULL
   OR LTRIM(RTRIM(NOM_ADHERENT)) = ''
   OR DATE_INSCRIPTION IS NULL
   OR ID_POINT_SERVICE IS NULL
   OR ID_TYPE_ADHERENT IS NULL
ORDER BY DATE_INSCRIPTION, CODE;

/*
26. Adherents non valides ou droit d'adhesion non paye
Objectif : identifier les adherents non valides ou dont le droit d'adhesion n'est pas paye.
Lecture : a rapprocher avec les ouvertures de comptes et l'activite transactionnelle.
*/
SELECT
    ID,
    CODE,
    NOM_ADHERENT,
    DATE_INSCRIPTION,
    ID_POINT_SERVICE,
    EST_VALIDE,
    DROIT_PAYE,
    OBSERVATION
FROM dbo.ADHERENTS
WHERE ISNULL(EST_VALIDE, 0) = 0
   OR ISNULL(DROIT_PAYE, 0) = 0
ORDER BY DATE_INSCRIPTION DESC;

/*
27. Adherents inscrits apres leur derniere modification
Objectif : detecter une incoherence chronologique dans les dates adherent.
Lecture : peut indiquer une reprise de donnees ou une date de modification incorrecte.
*/
SELECT
    ID,
    CODE,
    NOM_ADHERENT,
    DATE_INSCRIPTION,
    DATE_LAST_MODIFIED,
    ID_POINT_SERVICE
FROM dbo.ADHERENTS
WHERE DATE_INSCRIPTION IS NOT NULL
  AND DATE_LAST_MODIFIED IS NOT NULL
  AND DATE_LAST_MODIFIED < DATE_INSCRIPTION
ORDER BY DATE_INSCRIPTION DESC;

/*
28. Adherents sans compte adherent ou avec compte adherent introuvable
Objectif : verifier le rattachement de l'adherent a son compte adherent.
Lecture : les cas retournes peuvent bloquer l'analyse par client et le suivi KYC.
*/
SELECT
    a.ID,
    a.CODE,
    a.NOM_ADHERENT,
    a.ID_COMPTE_ADHERENT,
    a.DATE_INSCRIPTION,
    a.ID_POINT_SERVICE
FROM dbo.ADHERENTS a
LEFT JOIN dbo.COMPTES c ON c.ID = a.ID_COMPTE_ADHERENT
WHERE a.ID_COMPTE_ADHERENT IS NULL
   OR c.ID IS NULL
ORDER BY a.DATE_INSCRIPTION DESC;

/*
29. Synthese mensuelle des montants HDPM par point de service, devise et sens
Objectif : produire une vision agregee des mouvements comptables par agence, devise et sens.
Lecture : utile pour tableaux de bord mensuels et comparaison entre agences.
*/
SELECT
    DATEFROMPARTS(YEAR(h.DATE_OPERATION), MONTH(h.DATE_OPERATION), 1) AS mois,
    h.ID_POINT_SERVICE,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    h.SENS,
    COUNT(*) AS nb_lignes,
    SUM(ISNULL(h.MONTANT_OPERATION, 0)) AS montant_total
FROM dbo.HDPM h
LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = h.ID_POINT_SERVICE
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY DATEFROMPARTS(YEAR(h.DATE_OPERATION), MONTH(h.DATE_OPERATION), 1),
         h.ID_POINT_SERVICE, ps.CODE, ps.NOM, h.ID_DEVISE, d.CODE, d.LIBELLE, d.SYMBOLE, h.SENS
ORDER BY mois, h.ID_POINT_SERVICE, h.ID_DEVISE, h.SENS;

/*
30. Top operations par montant cumule HDPM
Objectif : lister les operations les plus importantes en montant comptable cumule.
Lecture : priorise les controles sur les operations a impact financier eleve.
*/
SELECT TOP (100)
    h.ID_OPERATION,
    MIN(h.DATE_OPERATION) AS date_operation,
    COUNT(*) AS nb_lignes,
    SUM(ISNULL(h.MONTANT_OPERATION, 0)) AS montant_cumule_lignes,
    MAX(h.DESCRIPTION) AS description
FROM dbo.HDPM h
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY h.ID_OPERATION
ORDER BY SUM(ISNULL(h.MONTANT_OPERATION, 0)) DESC;

/*
31. Operations API sans ecritures HDPM_API rattachees
Objectif : verifier que chaque operation API active a des ecritures comptables API.
Lecture : absence d'ecriture = anomalie d'integration ou de comptabilisation potentielle.
*/
SELECT
    oa.ID,
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ID_TYPE_OPERATION,
    oa.ID_POINT_SERVICE,
    oa.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    oa.NUM_TRANSACTION,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(oa.ANNULE, 0) = 0
  AND h.ID IS NULL
ORDER BY oa.DATE_OPERATION, oa.ID;

/*
32. Operations API mobiles sans paire debit/credit equilibree dans HDPM_API
Objectif : controler que les operations mobiles ont une paire debit/credit coherente.
Lecture : signale les mobiles incomplets, desequilibres ou mal rattaches.
*/
SELECT
    oa.ID,
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ID_TYPE_OPERATION,
    oa.ID_POINT_SERVICE,
    oa.NUM_TRANSACTION,
    COUNT(h.ID) AS nb_lignes_hdpm_api,
    SUM(CASE WHEN h.SENS = 'D' THEN 1 ELSE 0 END) AS nb_debit,
    SUM(CASE WHEN h.SENS = 'C' THEN 1 ELSE 0 END) AS nb_credit,
    SUM(CASE WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_debit,
    SUM(CASE WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_credit,
    ABS(
        SUM(CASE WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END)
      - SUM(CASE WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END)
    ) AS ecart
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(oa.ANNULE, 0) = 0
  AND oa.ID_TYPE_OPERATION LIKE 'MOB_%'
GROUP BY oa.ID, oa.CODE, oa.DATE_OPERATION, oa.ID_TYPE_OPERATION, oa.ID_POINT_SERVICE, oa.NUM_TRANSACTION
HAVING COUNT(h.ID) <> 2
    OR SUM(CASE WHEN h.SENS = 'D' THEN 1 ELSE 0 END) <> 1
    OR SUM(CASE WHEN h.SENS = 'C' THEN 1 ELSE 0 END) <> 1
    OR ABS(
        SUM(CASE WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END)
      - SUM(CASE WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END)
    ) > 0.01
ORDER BY oa.DATE_OPERATION, oa.ID;

/*
33. Operations API annulees et leurs ecritures HDPM_API
Objectif : documenter les operations API annulees avec leur impact comptable.
Lecture : facilite la revue des annulations mobile banking.
*/
SELECT
    oa.ID,
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ANNULE,
    oa.ID_OPERATION_ANNULE,
    oa.ID_OPERATION_MERE,
    oa.ID_TYPE_OPERATION,
    oa.NUM_TRANSACTION,
    COUNT(h.ID) AS nb_lignes_hdpm_api,
    SUM(ISNULL(h.MONTANT_OPERATION, 0)) AS montant_cumule_lignes
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(oa.ANNULE, 0) = 1
GROUP BY oa.ID, oa.CODE, oa.DATE_OPERATION, oa.ANNULE, oa.ID_OPERATION_ANNULE,
         oa.ID_OPERATION_MERE, oa.ID_TYPE_OPERATION, oa.NUM_TRANSACTION
ORDER BY oa.DATE_OPERATION, oa.ID;

/*
34. Synthese des operations API par statut annulation et type
Objectif : suivre l'activite API par mois, type operation et statut d'annulation.
Lecture : utile pour surveiller les tendances mobile banking.
*/
SELECT
    DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1) AS mois,
    ID_TYPE_OPERATION,
    CASE
        WHEN ANNULE = 1 THEN 'Annulee'
        WHEN ANNULE = 0 THEN 'Active'
        ELSE 'Statut NULL'
    END AS statut_annulation,
    COUNT(*) AS nb_operations
FROM dbo.OPERATIONS_API
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1),
         ID_TYPE_OPERATION,
         CASE
             WHEN ANNULE = 1 THEN 'Annulee'
             WHEN ANNULE = 0 THEN 'Active'
             ELSE 'Statut NULL'
         END
ORDER BY mois, ID_TYPE_OPERATION, statut_annulation;

/*
35. Pics de fin de mois dans OPERATIONS par type operation
Objectif : identifier les volumes importants passes en fin de mois.
Lecture : permet de distinguer traitements batch, regularisations et anomalies de concentration.
*/
SELECT
    DATE_OPERATION,
    ID_TYPE_OPERATION,
    ID_POINT_SERVICE,
    COUNT(*) AS nb_operations
FROM dbo.OPERATIONS
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND DATE_OPERATION = EOMONTH(DATE_OPERATION)
GROUP BY DATE_OPERATION, ID_TYPE_OPERATION, ID_POINT_SERVICE
HAVING COUNT(*) >= 100
ORDER BY DATE_OPERATION, nb_operations DESC;

/*
36. Liste de tous les depots et retraits, back-office et API mobile
Objectif : obtenir le detail unifie des depots/retraits toutes sources.
Lecture : base de travail pour extraction Excel, controle LBC-FT et investigations transactionnelles.
*/
SELECT
    'BACK_OFFICE' AS source_mouvement,
    o.ID AS id_operation,
    o.DATE_OPERATION,
    o.ID_TYPE_OPERATION,
    CASE
        WHEN o.ID_TYPE_OPERATION = 'DEPO' THEN 'Depot'
        WHEN o.ID_TYPE_OPERATION = 'RETR' THEN 'Retrait'
        ELSE o.ID_TYPE_OPERATION
    END AS type_mouvement,
    h.ID AS id_ecriture,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    o.NUM_TRANSACTION,
    o.NUMERO_RECU,
    o.ID_POINT_SERVICE,
    CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
  AND ISNULL(o.ANNULE, 0) = 0

UNION ALL

SELECT
    'API_MOBILE' AS source_mouvement,
    oa.CODE AS id_operation,
    oa.DATE_OPERATION,
    oa.ID_TYPE_OPERATION,
    CASE
        WHEN oa.ID_TYPE_OPERATION = 'MOB_DEPO' THEN 'Depot mobile'
        WHEN oa.ID_TYPE_OPERATION = 'MOB_RETR' THEN 'Retrait mobile'
        ELSE oa.ID_TYPE_OPERATION
    END AS type_mouvement,
    CAST(h.ID AS varchar(255)) AS id_ecriture,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    oa.NUM_TRANSACTION,
    oa.NUMERO_RECU,
    oa.ID_POINT_SERVICE,
    oa.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
INNER JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND oa.ID_TYPE_OPERATION IN ('MOB_DEPO', 'MOB_RETR')
  AND ISNULL(oa.ANNULE, 0) = 0

ORDER BY DATE_OPERATION, source_mouvement, id_operation, SENS;

/*
37. Liste de tous les mouvements comptables, tous types confondus
Objectif : produire un listing complet HDPM + HDPM_API sans filtrer les types operation.
Lecture : sert d'export exhaustif des mouvements comptables sur la periode.
*/
SELECT
    'BACK_OFFICE' AS source_mouvement,
    h.ID_OPERATION AS id_operation,
    h.DATE_OPERATION,
    COALESCE(o.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION) AS ID_TYPE_OPERATION,
    CASE
        WHEN COALESCE(o.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION) = 'DEPO' THEN 'Depot'
        WHEN COALESCE(o.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION) = 'RETR' THEN 'Retrait'
        ELSE COALESCE(o.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION)
    END AS type_mouvement,
    h.ID AS id_ecriture,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    COALESCE(o.NUM_TRANSACTION, h.NUM_TRANSACTION) AS NUM_TRANSACTION,
    COALESCE(o.NUMERO_RECU, h.NUMERO_RECU) AS NUMERO_RECU,
    COALESCE(o.ID_POINT_SERVICE, h.ID_POINT_SERVICE) AS ID_POINT_SERVICE,
    CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    COALESCE(o.DESCRIPTION, h.DESCRIPTION) AS DESCRIPTION
FROM dbo.HDPM h
LEFT JOIN dbo.OPERATIONS o ON o.ID = h.ID_OPERATION
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin

UNION ALL

SELECT
    'API_MOBILE' AS source_mouvement,
    h.ID_OPERATION AS id_operation,
    h.DATE_OPERATION,
    COALESCE(oa.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION) AS ID_TYPE_OPERATION,
    CASE
        WHEN COALESCE(oa.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION) = 'MOB_DEPO' THEN 'Depot mobile'
        WHEN COALESCE(oa.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION) = 'MOB_RETR' THEN 'Retrait mobile'
        ELSE COALESCE(oa.ID_TYPE_OPERATION, h.ID_TYPE_OPERATION)
    END AS type_mouvement,
    CAST(h.ID AS varchar(255)) AS id_ecriture,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.ID_DEVISE,
    d.CODE AS code_devise,
    d.LIBELLE AS libelle_devise,
    d.SYMBOLE AS symbole_devise,
    COALESCE(oa.NUM_TRANSACTION, h.NUM_TRANSACTION) AS NUM_TRANSACTION,
    COALESCE(oa.NUMERO_RECU, h.NUMERO_RECU) AS NUMERO_RECU,
    COALESCE(oa.ID_POINT_SERVICE, h.ID_POINT_SERVICE) AS ID_POINT_SERVICE,
    oa.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    u.NOM AS nom_utilisateur,
    u.PRENOM AS prenom_utilisateur,
    COALESCE(oa.DESCRIPTION, h.DESCRIPTION) AS DESCRIPTION
FROM dbo.HDPM_API h
LEFT JOIN dbo.OPERATIONS_API oa ON oa.CODE = h.ID_OPERATION
LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin

ORDER BY DATE_OPERATION, source_mouvement, id_operation, id_ecriture;

/*
38. Synthese Excel LBC-FT : depots, retraits et mobile banking
Objectif : produire une table directement exploitable pour certaines lignes du reporting BCC/LBC-FT.
Lecture : renseigne section, ligne Excel, rubrique, nombre, volume et commentaire.
*/
WITH mouvements AS (
    SELECT
        'BACK_OFFICE' AS source_mouvement,
        o.ID AS id_operation,
        o.DATE_OPERATION,
        o.ID_TYPE_OPERATION,
        CASE
            WHEN o.ID_TYPE_OPERATION = 'DEPO' THEN 'Depot'
            WHEN o.ID_TYPE_OPERATION = 'RETR' THEN 'Retrait'
            ELSE o.ID_TYPE_OPERATION
        END AS type_mouvement,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation,
        h.ID_DEVISE
    FROM dbo.OPERATIONS o
    INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
    WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
      AND ISNULL(o.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY o.ID, o.DATE_OPERATION, o.ID_TYPE_OPERATION, h.ID_DEVISE

    UNION ALL

    SELECT
        'API_MOBILE' AS source_mouvement,
        oa.CODE AS id_operation,
        oa.DATE_OPERATION,
        oa.ID_TYPE_OPERATION,
        CASE
            WHEN oa.ID_TYPE_OPERATION = 'MOB_DEPO' THEN 'Depot mobile'
            WHEN oa.ID_TYPE_OPERATION = 'MOB_RETR' THEN 'Retrait mobile'
            ELSE oa.ID_TYPE_OPERATION
        END AS type_mouvement,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation,
        h.ID_DEVISE
    FROM dbo.OPERATIONS_API oa
    INNER JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
    WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND oa.ID_TYPE_OPERATION IN ('MOB_DEPO', 'MOB_RETR')
      AND ISNULL(oa.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY oa.CODE, oa.DATE_OPERATION, oa.ID_TYPE_OPERATION, h.ID_DEVISE
)
SELECT
    '1. ACTIVITE' AS section,
    25 AS ligne_excel,
    'Total Depots' AS rubrique,
    COUNT(*) AS nombre,
    SUM(montant_operation) AS volume,
    'Alimente la ligne Total Depots du reporting.' AS commentaire
FROM mouvements
WHERE type_mouvement IN ('Depot', 'Depot mobile')

UNION ALL

SELECT
    '3. PRODUIT - SERVICE - OPERATIONS',
    53,
    'Depot >= 10k USD',
    COUNT(*),
    SUM(montant_operation),
    'Seuil a renseigner en CDF dans @seuil_10k_usd_cdf.'
FROM mouvements
WHERE type_mouvement IN ('Depot', 'Depot mobile')
  AND montant_operation >= @seuil_10k_usd_cdf

UNION ALL

SELECT
    '3. PRODUIT - SERVICE - OPERATIONS',
    54,
    'Retrait >= 10k USD',
    COUNT(*),
    SUM(montant_operation),
    'Seuil a renseigner en CDF dans @seuil_10k_usd_cdf.'
FROM mouvements
WHERE type_mouvement IN ('Retrait', 'Retrait mobile')
  AND montant_operation >= @seuil_10k_usd_cdf

UNION ALL

SELECT
    '3. PRODUIT - SERVICE - OPERATIONS',
    55,
    'Depot >= 5k USD et < 10k USD',
    COUNT(*),
    SUM(montant_operation),
    'Seuils a renseigner en CDF dans @seuil_5k_usd_cdf et @seuil_10k_usd_cdf.'
FROM mouvements
WHERE type_mouvement IN ('Depot', 'Depot mobile')
  AND montant_operation >= @seuil_5k_usd_cdf
  AND montant_operation < @seuil_10k_usd_cdf

UNION ALL

SELECT
    '3. PRODUIT - SERVICE - OPERATIONS',
    56,
    'Retrait >= 5k USD et < 10k USD',
    COUNT(*),
    SUM(montant_operation),
    'Seuils a renseigner en CDF dans @seuil_5k_usd_cdf et @seuil_10k_usd_cdf.'
FROM mouvements
WHERE type_mouvement IN ('Retrait', 'Retrait mobile')
  AND montant_operation >= @seuil_5k_usd_cdf
  AND montant_operation < @seuil_10k_usd_cdf

UNION ALL

SELECT
    '4. CANAUX DE DISTRIBUTION',
    132,
    'Operations effectuees par Mobile Banking',
    COUNT(*),
    SUM(montant_operation),
    'Operations API mobiles : MOB_DEPO et MOB_RETR.'
FROM mouvements
WHERE source_mouvement = 'API_MOBILE'

UNION ALL

SELECT
    '4. CANAUX DE DISTRIBUTION',
    134,
    'Wallet to Bank',
    COUNT(*),
    SUM(montant_operation),
    'Approximation : depots mobiles MOB_DEPO.'
FROM mouvements
WHERE ID_TYPE_OPERATION = 'MOB_DEPO'
ORDER BY ligne_excel;

/*
39. Fractionnement potentiel : plusieurs mouvements sous seuil mais cumul au-dessus du seuil
Objectif : detecter les clients avec plusieurs operations sous seuil dont le cumul depasse le seuil journalier.
Lecture : cas typique de surveillance LBC-FT sur contournement possible des seuils.
*/
WITH mouvements AS (
    SELECT
        'BACK_OFFICE' AS source_mouvement,
        o.ID AS id_operation,
        o.DATE_OPERATION,
        o.ID_TYPE_OPERATION,
        CASE WHEN o.ID_TYPE_OPERATION = 'DEPO' THEN 'Depot' WHEN o.ID_TYPE_OPERATION = 'RETR' THEN 'Retrait' END AS type_mouvement,
        ca.ID_ADHERENT,
        a.CODE AS code_adherent,
        a.NOM_ADHERENT,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation,
        h.ID_DEVISE
    FROM dbo.OPERATIONS o
    INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
      AND ISNULL(o.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY o.ID, o.DATE_OPERATION, o.ID_TYPE_OPERATION, ca.ID_ADHERENT, a.CODE, a.NOM_ADHERENT, h.ID_DEVISE

    UNION ALL

    SELECT
        'API_MOBILE',
        oa.CODE,
        oa.DATE_OPERATION,
        oa.ID_TYPE_OPERATION,
        CASE WHEN oa.ID_TYPE_OPERATION = 'MOB_DEPO' THEN 'Depot' WHEN oa.ID_TYPE_OPERATION = 'MOB_RETR' THEN 'Retrait' END,
        ca.ID_ADHERENT,
        a.CODE,
        a.NOM_ADHERENT,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))),
        h.ID_DEVISE
    FROM dbo.OPERATIONS_API oa
    INNER JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND oa.ID_TYPE_OPERATION IN ('MOB_DEPO', 'MOB_RETR')
      AND ISNULL(oa.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY oa.CODE, oa.DATE_OPERATION, oa.ID_TYPE_OPERATION, ca.ID_ADHERENT, a.CODE, a.NOM_ADHERENT, h.ID_DEVISE
)
SELECT
    DATE_OPERATION,
    ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT,
    type_mouvement,
    ID_DEVISE,
    COUNT(*) AS nb_operations,
    SUM(montant_operation) AS montant_cumule,
    MAX(montant_operation) AS montant_max_unitaire,
    'Plusieurs mouvements unitaires sous le seuil 10k USD mais cumul journalier au-dessus.' AS alerte
FROM mouvements
WHERE montant_operation < @seuil_10k_usd_cdf
GROUP BY DATE_OPERATION, ID_ADHERENT, code_adherent, NOM_ADHERENT, type_mouvement, ID_DEVISE
HAVING COUNT(*) >= 2
   AND SUM(montant_operation) >= @seuil_10k_usd_cdf
ORDER BY montant_cumule DESC, DATE_OPERATION;

/*
40. Operations inhabituelles par client : volume periode vs moyenne des 3 mois precedents
Objectif : comparer le volume de la periode avec l'historique recent du client.
Lecture : les multiples eleves ou l'absence d'historique doivent etre investigues.
*/
WITH mouvements AS (
    SELECT
        o.DATE_OPERATION,
        ca.ID_ADHERENT,
        a.CODE AS code_adherent,
        a.NOM_ADHERENT,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation
    FROM dbo.OPERATIONS o
    INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN DATEADD(month, -3, @date_debut) AND @date_fin
      AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
      AND ISNULL(o.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY o.ID, o.DATE_OPERATION, ca.ID_ADHERENT, a.CODE, a.NOM_ADHERENT
),
periode AS (
    SELECT ID_ADHERENT, code_adherent, NOM_ADHERENT, SUM(montant_operation) AS volume_periode, COUNT(*) AS nb_operations_periode
    FROM mouvements
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    GROUP BY ID_ADHERENT, code_adherent, NOM_ADHERENT
),
historique AS (
    SELECT ID_ADHERENT, AVG(volume_jour) AS moyenne_journaliere_historique
    FROM (
        SELECT ID_ADHERENT, DATE_OPERATION, SUM(montant_operation) AS volume_jour
        FROM mouvements
        WHERE DATE_OPERATION < @date_debut
        GROUP BY ID_ADHERENT, DATE_OPERATION
    ) h
    GROUP BY ID_ADHERENT
)
SELECT
    p.ID_ADHERENT,
    p.code_adherent,
    p.NOM_ADHERENT,
    p.nb_operations_periode,
    p.volume_periode,
    h.moyenne_journaliere_historique,
    CASE
        WHEN h.moyenne_journaliere_historique IS NULL THEN NULL
        ELSE p.volume_periode / NULLIF(h.moyenne_journaliere_historique, 0)
    END AS multiple_vs_moyenne_historique
FROM periode p
LEFT JOIN historique h ON h.ID_ADHERENT = p.ID_ADHERENT
WHERE p.volume_periode >= @seuil_10k_usd_cdf
  AND (h.moyenne_journaliere_historique IS NULL OR p.volume_periode >= 3 * h.moyenne_journaliere_historique)
ORDER BY p.volume_periode DESC;

/*
41. Clients avec forte activite mais donnees KYC incompletes ou atypiques
Objectif : croiser volume transactionnel et qualite des donnees adherent.
Lecture : priorise les dossiers KYC incomplets ayant une activite significative.
*/
WITH mouvements AS (
    SELECT
        ca.ID_ADHERENT,
        MAX(a.CODE) AS code_adherent,
        MAX(a.NOM_ADHERENT) AS NOM_ADHERENT,
        MAX(a.ID_CATEGORIE_ADHERENT) AS ID_CATEGORIE_ADHERENT,
        MAX(a.ID_TYPE_ADHERENT) AS ID_TYPE_ADHERENT,
        MAX(a.ID_POINT_SERVICE) AS ID_POINT_SERVICE,
        MAX(CAST(ISNULL(a.EST_VALIDE, 0) AS int)) AS EST_VALIDE,
        MAX(CAST(ISNULL(a.DROIT_PAYE, 0) AS int)) AS DROIT_PAYE,
        MAX(a.ID_GESTIONNAIRE) AS ID_GESTIONNAIRE,
        COUNT(DISTINCT o.ID) AS nb_operations,
        SUM(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS volume_lignes
    FROM dbo.OPERATIONS o
    INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
      AND ISNULL(o.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY ca.ID_ADHERENT
)
SELECT *
FROM mouvements
WHERE volume_lignes >= @seuil_10k_usd_cdf
  AND (
        ID_ADHERENT IS NULL
        OR code_adherent IS NULL
        OR LTRIM(RTRIM(ISNULL(NOM_ADHERENT, ''))) = ''
        OR ID_TYPE_ADHERENT IS NULL
        OR ID_POINT_SERVICE IS NULL
        OR ID_GESTIONNAIRE IS NULL
        OR EST_VALIDE = 0
        OR DROIT_PAYE = 0
      )
ORDER BY volume_lignes DESC;

/*
42. Depots et retraits agreges par client
Objectif : calculer nombres et volumes de depots/retraits par adherent.
Lecture : base pour profilage client et suivi commercial/risque.
*/
WITH mouvements AS (
    SELECT
        ca.ID_ADHERENT,
        a.CODE AS code_adherent,
        a.NOM_ADHERENT,
        CASE WHEN o.ID_TYPE_OPERATION = 'DEPO' THEN 'Depot' WHEN o.ID_TYPE_OPERATION = 'RETR' THEN 'Retrait' END AS type_mouvement,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation
    FROM dbo.OPERATIONS o
    INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
      AND ISNULL(o.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY o.ID, ca.ID_ADHERENT, a.CODE, a.NOM_ADHERENT, o.ID_TYPE_OPERATION
)
SELECT
    ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT,
    SUM(CASE WHEN type_mouvement = 'Depot' THEN 1 ELSE 0 END) AS nb_depots,
    SUM(CASE WHEN type_mouvement = 'Depot' THEN montant_operation ELSE 0 END) AS volume_depots,
    SUM(CASE WHEN type_mouvement = 'Retrait' THEN 1 ELSE 0 END) AS nb_retraits,
    SUM(CASE WHEN type_mouvement = 'Retrait' THEN montant_operation ELSE 0 END) AS volume_retraits,
    COUNT(*) AS nb_operations,
    SUM(montant_operation) AS volume_total
FROM mouvements
GROUP BY ID_ADHERENT, code_adherent, NOM_ADHERENT
ORDER BY volume_total DESC;

/*
43. Top clients par volume de mouvements
Objectif : afficher les 50 clients les plus actifs en montant sur la periode.
Lecture : utile pour selectionner les dossiers a examiner en priorite.
*/
WITH mouvements AS (
    SELECT
        ca.ID_ADHERENT,
        a.CODE AS code_adherent,
        a.NOM_ADHERENT,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation
    FROM dbo.OPERATIONS o
    INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
      AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
      AND ISNULL(o.ANNULE, 0) = 0
      AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
    GROUP BY o.ID, ca.ID_ADHERENT, a.CODE, a.NOM_ADHERENT
)
SELECT TOP (50)
    ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT,
    COUNT(*) AS nb_operations,
    SUM(montant_operation) AS volume_total,
    MAX(montant_operation) AS plus_grosse_operation
FROM mouvements
GROUP BY ID_ADHERENT, code_adherent, NOM_ADHERENT
ORDER BY volume_total DESC;

/*
44. Analyse detaillee des operations annulees
Objectif : lister les annulations avec utilisateur, validateur et references operationnelles.
Lecture : facilite la revue des annulations et de leur justification.
*/
SELECT
    'BACK_OFFICE' AS source_operation,
    o.ID AS id_operation,
    o.DATE_OPERATION,
    o.ID_OPERATION_ANNULE,
    o.ID_OPERATION_MERE,
    o.ID_TYPE_OPERATION,
    o.ID_POINT_SERVICE,
    o.ID_UTILISATEUR,
    u.LOGIN AS login_utilisateur,
    o.ID_UTILISATEUR_VALIDE,
    uv.LOGIN AS login_validateur,
    o.NUM_TRANSACTION,
    o.NUMERO_RECU,
    o.DESCRIPTION
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
LEFT JOIN dbo.UTILISATEURS uv ON uv.id = o.ID_UTILISATEUR_VALIDE
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(o.ANNULE, 0) = 1

UNION ALL

SELECT
    'API_MOBILE',
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ID_OPERATION_ANNULE,
    oa.ID_OPERATION_MERE,
    oa.ID_TYPE_OPERATION,
    oa.ID_POINT_SERVICE,
    oa.ID_UTILISATEUR,
    u.LOGIN,
    oa.ID_UTILISATEUR_VALIDE,
    uv.LOGIN,
    oa.NUM_TRANSACTION,
    oa.NUMERO_RECU,
    oa.DESCRIPTION
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.UTILISATEURS u ON u.id = oa.ID_UTILISATEUR
LEFT JOIN dbo.UTILISATEURS uv ON uv.id = oa.ID_UTILISATEUR_VALIDE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
  AND ISNULL(oa.ANNULE, 0) = 1
ORDER BY DATE_OPERATION, source_operation, id_operation;

/*
45. Utilisateurs a risque : volumes, annulations, saisies tardives et auto-validation
Objectif : identifier les utilisateurs dont l'activite presente des signaux de supervision.
Lecture : combine volume, annulations, saisies tardives et separation des taches.
*/
SELECT
    o.ID_UTILISATEUR,
    u.LOGIN,
    u.NOM,
    u.PRENOM,
    COUNT(*) AS nb_operations,
    SUM(CASE WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1 ELSE 0 END) AS nb_annulations,
    SUM(CASE WHEN o.DATE_SAISIE IS NOT NULL AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION THEN 1 ELSE 0 END) AS nb_saisies_tardives,
    SUM(CASE WHEN o.ID_UTILISATEUR IS NOT NULL AND o.ID_UTILISATEUR = o.ID_UTILISATEUR_VALIDE THEN 1 ELSE 0 END) AS nb_auto_validations,
    COUNT(DISTINCT o.ID_POINT_SERVICE) AS nb_points_service,
    COUNT(DISTINCT o.ID_TYPE_OPERATION) AS nb_types_operation
FROM dbo.OPERATIONS o
LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY o.ID_UTILISATEUR, u.LOGIN, u.NOM, u.PRENOM
HAVING COUNT(*) >= 50
    OR SUM(CASE WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1 ELSE 0 END) > 0
    OR SUM(CASE WHEN o.DATE_SAISIE IS NOT NULL AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION THEN 1 ELSE 0 END) >= 10
    OR SUM(CASE WHEN o.ID_UTILISATEUR IS NOT NULL AND o.ID_UTILISATEUR = o.ID_UTILISATEUR_VALIDE THEN 1 ELSE 0 END) > 0
ORDER BY nb_annulations DESC, nb_saisies_tardives DESC, nb_operations DESC;

/*
46. Analyse par point de service / agence
Objectif : agreger les operations par agence, type et indicateurs d'anomalie.
Lecture : compare les agences et identifie les points de service atypiques.
*/
SELECT
    o.ID_POINT_SERVICE,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    o.ID_TYPE_OPERATION,
    COUNT(*) AS nb_operations,
    SUM(CASE WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1 ELSE 0 END) AS nb_annulations,
    SUM(CASE WHEN o.DATE_SAISIE IS NOT NULL AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION THEN 1 ELSE 0 END) AS nb_saisies_tardives
FROM dbo.OPERATIONS o
LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = o.ID_POINT_SERVICE
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY o.ID_POINT_SERVICE, ps.CODE, ps.NOM, o.ID_TYPE_OPERATION
ORDER BY nb_operations DESC;

/*
47. Detail mobile banking par type operation
Objectif : suivre les operations API par type mobile, mois et point de service.
Lecture : aide au reporting mobile banking et au controle de l'equilibre debit/credit.
*/
SELECT
    oa.ID_TYPE_OPERATION,
    DATEFROMPARTS(YEAR(oa.DATE_OPERATION), MONTH(oa.DATE_OPERATION), 1) AS mois,
    oa.ID_POINT_SERVICE,
    COUNT(DISTINCT oa.CODE) AS nb_operations,
    COUNT(h.ID) AS nb_lignes_hdpm_api,
    SUM(CASE WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_debit,
    SUM(CASE WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0) ELSE 0 END) AS total_credit,
    SUM(CASE WHEN ISNULL(oa.ANNULE, 0) = 1 THEN 1 ELSE 0 END) AS nb_annulees
FROM dbo.OPERATIONS_API oa
LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY oa.ID_TYPE_OPERATION, DATEFROMPARTS(YEAR(oa.DATE_OPERATION), MONTH(oa.DATE_OPERATION), 1), oa.ID_POINT_SERVICE
ORDER BY mois, oa.ID_TYPE_OPERATION, oa.ID_POINT_SERVICE;

/*
48. Rubriques LBC-FT non couvertes automatiquement et pistes de mapping
Objectif : documenter les rubriques du reporting qui necessitent encore une source ou un mapping metier.
Lecture : sert de checklist pour completer le reporting BCC/LBC-FT au-dela des mouvements financiers.
*/
SELECT *
FROM (VALUES
    ('PPE', 'A mapper avec une table/colonne indiquant les personnes politiquement exposees.'),
    ('Non-residents', 'A mapper avec les donnees pays/adresse/statut resident du client.'),
    ('MPME', 'A mapper avec categorie/type adherent ou secteur activite officiel.'),
    ('OBNL', 'A mapper avec categorie/type adherent, secteur activite ou forme juridique.'),
    ('Secteur immobilier', 'A mapper avec SECTEURS_ACTIVITE / SECTEURS_ACTIVITE_CREDIT.'),
    ('Secteur minier', 'A mapper avec SECTEURS_ACTIVITE / objet de financement.'),
    ('DOS / declarations de soupcon', 'Necessite la table ou le fichier des declarations de soupcon.'),
    ('Sanctions financieres ciblees', 'Necessite la source de screening sanctions et gels/refus.'),
    ('Credits rembourses anticipativement', 'Necessite analyse PRETS / REMBOURSEMENTS / echeanciers.')
) v(rubrique_reporting, prerequis_mapping)
ORDER BY rubrique_reporting;


