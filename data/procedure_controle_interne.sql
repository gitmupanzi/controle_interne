/*
Procedure stockee de controle interne - base BB_VISION_PRO

Utilisation :
  EXEC dbo.sp_controle_interne_vision_pro @date_debut = '2026-01-01', @date_fin = '2026-12-31', @controle_id = 1;
  EXEC dbo.sp_controle_interne_vision_pro @date_debut = '2026-01-01', @date_fin = '2026-12-31', @controle_id = 14;

Liste des controles :
  1  = Volumetrie des tables principales
  2  = Volumetrie des operations par mois
  3  = Operations creees mais non validees
  4  = Operations saisies apres la date d'operation
  5  = Operations validees avant la saisie ou avant la date d'operation
  6  = Operations sans utilisateur, point de service ou type operation
  7  = Doublons de numero de transaction dans OPERATIONS
  8  = Doublons de numero de recu dans OPERATIONS
  9  = Doublons metier potentiels
  10 = Operations annulees sans operation annulee referencee
  11 = Operations referencees comme annulees mais introuvables
  12 = HDPM sans operation back-office correspondante
  13 = Operations back-office sans ecriture HDPM
  14 = Equilibre debit/credit par operation dans HDPM
  15 = Equilibre debit/credit par operation dans HDPM_API
  16 = Lignes HDPM avec montant nul, negatif ou sens absent
  17 = Ecritures comptables avec date valeur differente
  18 = Mouvements HDPM sans compte ou avec compte inexistant
  19 = Mouvements sur comptes clotures/inactifs selon ETAT
  20 = Rapprochement OPERATIONS vs OPERATIONS_API par NUM_TRANSACTION
  21 = Rapprochement des totaux HDPM vs HDPM_API
  22 = Operations par utilisateur avec volumes et delais moyens
  23 = Operations saisies et validees par le meme utilisateur
  24 = Adherents inscrits en doublon par code
  25 = Adherents sans informations essentielles
  26 = Adherents non valides ou droit d'adhesion non paye
  27 = Adherents inscrits apres leur derniere modification
  28 = Adherents sans compte adherent ou avec compte adherent introuvable
  29 = Synthese mensuelle des montants HDPM
  30 = Top operations par montant cumule HDPM
  31 = Operations API sans ecritures HDPM_API rattachees
  32 = Operations API mobiles sans paire debit/credit equilibree
  33 = Operations API annulees et leurs ecritures HDPM_API
  34 = Synthese des operations API par statut annulation et type
  35 = Pics de fin de mois dans OPERATIONS par type operation
  36 = Liste de tous les depots et retraits, back-office et API mobile
  37 = Liste de tous les mouvements comptables, tous types confondus
*/

USE [BB_VISION_PRO];
GO

CREATE OR ALTER PROCEDURE dbo.sp_controle_interne_vision_pro
    @date_debut date = '2026-01-01',
    @date_fin   date = '2026-12-31',
    @controle_id int
AS
BEGIN
    SET NOCOUNT ON;

    IF @controle_id = 1
    BEGIN
        SELECT 'OPERATIONS' AS table_name, COUNT(*) AS nb_lignes FROM dbo.OPERATIONS
        UNION ALL SELECT 'OPERATIONS_API', COUNT(*) FROM dbo.OPERATIONS_API
        UNION ALL SELECT 'HDPM', COUNT(*) FROM dbo.HDPM
        UNION ALL SELECT 'HDPM_API', COUNT(*) FROM dbo.HDPM_API
        UNION ALL SELECT 'ADHERENTS', COUNT(*) FROM dbo.ADHERENTS;
        RETURN;
    END;

    IF @controle_id = 2
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 3
    BEGIN
        SELECT
            'OPERATIONS' AS source_table,
            ID,
            DATE_OPERATION,
            DATE_SAISIE,
            DATE_VALIDATION,
            DATE_VALIDE,
            ID_POINT_SERVICE,
            ID_TYPE_OPERATION,
            CAST(ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
            DESCRIPTION
        FROM dbo.OPERATIONS
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND ISNULL(ANNULE, 0) = 0
          AND (DATE_VALIDATION IS NULL OR DATE_VALIDE IS NULL)
        UNION ALL
        SELECT
            'OPERATIONS_API',
            CAST(ID AS varchar(255)),
            DATE_OPERATION,
            DATE_SAISIE,
            DATE_VALIDATION,
            DATE_VALIDE,
            ID_POINT_SERVICE,
            ID_TYPE_OPERATION,
            ID_UTILISATEUR,
            DESCRIPTION
        FROM dbo.OPERATIONS_API
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND ISNULL(ANNULE, 0) = 0
          AND DATE_VALIDATION IS NULL
        ORDER BY DATE_OPERATION, source_table;
        RETURN;
    END;

    IF @controle_id = 4
    BEGIN
        SELECT
            'OPERATIONS' AS source_table,
            ID,
            DATE_OPERATION,
            DATE_SAISIE,
            DATEDIFF(day, DATE_OPERATION, CAST(DATE_SAISIE AS date)) AS delai_saisie_jours,
            CAST(ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
            ID_POINT_SERVICE,
            DESCRIPTION
        FROM dbo.OPERATIONS
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND DATE_SAISIE IS NOT NULL
          AND CAST(DATE_SAISIE AS date) > DATE_OPERATION
        UNION ALL
        SELECT
            'OPERATIONS_API',
            CAST(ID AS varchar(255)),
            DATE_OPERATION,
            DATE_SAISIE,
            DATEDIFF(day, DATE_OPERATION, CAST(DATE_SAISIE AS date)),
            ID_UTILISATEUR,
            ID_POINT_SERVICE,
            DESCRIPTION
        FROM dbo.OPERATIONS_API
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND DATE_SAISIE IS NOT NULL
          AND CAST(DATE_SAISIE AS date) > DATE_OPERATION
        ORDER BY delai_saisie_jours DESC, DATE_OPERATION;
        RETURN;
    END;

    IF @controle_id = 5
    BEGIN
        SELECT
            'OPERATIONS' AS source_table,
            ID,
            DATE_OPERATION,
            DATE_SAISIE,
            DATE_VALIDE,
            CAST(ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
            CAST(ID_UTILISATEUR_VALIDE AS bigint) AS ID_UTILISATEUR_VALIDE,
            DESCRIPTION
        FROM dbo.OPERATIONS
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND (
                (DATE_VALIDE IS NOT NULL AND DATE_SAISIE IS NOT NULL AND DATE_VALIDE < DATE_SAISIE)
                OR (DATE_VALIDATION IS NOT NULL AND DATE_VALIDATION < DATE_OPERATION)
              )
        UNION ALL
        SELECT
            'OPERATIONS_API',
            CAST(ID AS varchar(255)),
            DATE_OPERATION,
            DATE_SAISIE,
            DATE_VALIDE,
            ID_UTILISATEUR,
            ID_UTILISATEUR_VALIDE,
            DESCRIPTION
        FROM dbo.OPERATIONS_API
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND (
                (DATE_VALIDE IS NOT NULL AND DATE_SAISIE IS NOT NULL AND DATE_VALIDE < DATE_SAISIE)
                OR (DATE_VALIDATION IS NOT NULL AND DATE_VALIDATION < DATE_OPERATION)
              )
        ORDER BY DATE_OPERATION;
        RETURN;
    END;

    IF @controle_id = 6
    BEGIN
        SELECT
            'OPERATIONS' AS source_table,
            ID,
            DATE_OPERATION,
            CAST(ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
            ID_POINT_SERVICE,
            ID_TYPE_OPERATION,
            DESCRIPTION
        FROM dbo.OPERATIONS
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND (ID_UTILISATEUR IS NULL OR ID_POINT_SERVICE IS NULL OR ID_TYPE_OPERATION IS NULL)
        UNION ALL
        SELECT
            'OPERATIONS_API',
            CAST(ID AS varchar(255)),
            DATE_OPERATION,
            ID_UTILISATEUR,
            ID_POINT_SERVICE,
            ID_TYPE_OPERATION,
            DESCRIPTION
        FROM dbo.OPERATIONS_API
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND (ID_UTILISATEUR IS NULL OR ID_POINT_SERVICE IS NULL OR ID_TYPE_OPERATION IS NULL)
        ORDER BY DATE_OPERATION, source_table;
        RETURN;
    END;

    IF @controle_id = 7
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 8
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 9
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 10
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 11
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 12
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 13
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 14
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 15
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 16
    BEGIN
        SELECT
            'HDPM' AS source_table,
            ID,
            DATE_OPERATION,
            ID_OPERATION,
            ID_COMPTE,
            SENS,
            MONTANT_OPERATION,
            ID_DEVISE,
            DESCRIPTION
        FROM dbo.HDPM
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND (MONTANT_OPERATION IS NULL OR MONTANT_OPERATION <= 0 OR SENS IS NULL)
        UNION ALL
        SELECT
            'HDPM_API',
            CAST(ID AS varchar(255)),
            DATE_OPERATION,
            ID_OPERATION,
            ID_COMPTE,
            SENS,
            MONTANT_OPERATION,
            ID_DEVISE,
            DESCRIPTION
        FROM dbo.HDPM_API
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND (MONTANT_OPERATION IS NULL OR MONTANT_OPERATION <= 0 OR SENS IS NULL)
        ORDER BY DATE_OPERATION, source_table;
        RETURN;
    END;

    IF @controle_id = 17
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 18
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 19
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 20
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 21
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 22
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 23
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 24
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 25
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 26
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 27
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 28
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 29
    BEGIN
        SELECT
            DATEFROMPARTS(YEAR(h.DATE_OPERATION), MONTH(h.DATE_OPERATION), 1) AS mois,
            h.ID_POINT_SERVICE,
            ps.CODE AS code_point_service,
            ps.NOM AS nom_point_service,
            h.ID_DEVISE,
            h.SENS,
            COUNT(*) AS nb_lignes,
            SUM(ISNULL(h.MONTANT_OPERATION, 0)) AS montant_total
        FROM dbo.HDPM h
        LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = h.ID_POINT_SERVICE
        WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
        GROUP BY DATEFROMPARTS(YEAR(h.DATE_OPERATION), MONTH(h.DATE_OPERATION), 1),
                 h.ID_POINT_SERVICE, ps.CODE, ps.NOM, h.ID_DEVISE, h.SENS
        ORDER BY mois, h.ID_POINT_SERVICE, h.ID_DEVISE, h.SENS;
        RETURN;
    END;

    IF @controle_id = 30
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 31
    BEGIN
        SELECT
            oa.ID,
            oa.CODE,
            oa.DATE_OPERATION,
            oa.ID_TYPE_OPERATION,
            oa.ID_POINT_SERVICE,
            oa.ID_UTILISATEUR,
            oa.NUM_TRANSACTION,
            oa.DESCRIPTION
        FROM dbo.OPERATIONS_API oa
        LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
        WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND ISNULL(oa.ANNULE, 0) = 0
          AND h.ID IS NULL
        ORDER BY oa.DATE_OPERATION, oa.ID;
        RETURN;
    END;

    IF @controle_id = 32
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 33
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 34
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 35
    BEGIN
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
        RETURN;
    END;

    IF @controle_id = 36
    BEGIN
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
            o.NUM_TRANSACTION,
            o.NUMERO_RECU,
            o.ID_POINT_SERVICE,
            CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
            o.DESCRIPTION
        FROM dbo.OPERATIONS o
        INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
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
            oa.NUM_TRANSACTION,
            oa.NUMERO_RECU,
            oa.ID_POINT_SERVICE,
            oa.ID_UTILISATEUR,
            oa.DESCRIPTION
        FROM dbo.OPERATIONS_API oa
        INNER JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
        WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
          AND oa.ID_TYPE_OPERATION IN ('MOB_DEPO', 'MOB_RETR')
          AND ISNULL(oa.ANNULE, 0) = 0

        ORDER BY DATE_OPERATION, source_mouvement, id_operation, SENS;
        RETURN;
    END;

    IF @controle_id = 37
    BEGIN
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
            COALESCE(o.NUM_TRANSACTION, h.NUM_TRANSACTION) AS NUM_TRANSACTION,
            COALESCE(o.NUMERO_RECU, h.NUMERO_RECU) AS NUMERO_RECU,
            COALESCE(o.ID_POINT_SERVICE, h.ID_POINT_SERVICE) AS ID_POINT_SERVICE,
            CAST(o.ID_UTILISATEUR AS bigint) AS ID_UTILISATEUR,
            COALESCE(o.DESCRIPTION, h.DESCRIPTION) AS DESCRIPTION
        FROM dbo.HDPM h
        LEFT JOIN dbo.OPERATIONS o ON o.ID = h.ID_OPERATION
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
            COALESCE(oa.NUM_TRANSACTION, h.NUM_TRANSACTION) AS NUM_TRANSACTION,
            COALESCE(oa.NUMERO_RECU, h.NUMERO_RECU) AS NUMERO_RECU,
            COALESCE(oa.ID_POINT_SERVICE, h.ID_POINT_SERVICE) AS ID_POINT_SERVICE,
            oa.ID_UTILISATEUR,
            COALESCE(oa.DESCRIPTION, h.DESCRIPTION) AS DESCRIPTION
        FROM dbo.HDPM_API h
        LEFT JOIN dbo.OPERATIONS_API oa ON oa.CODE = h.ID_OPERATION
        WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin

        ORDER BY DATE_OPERATION, source_mouvement, id_operation, id_ecriture;
        RETURN;
    END;

    RAISERROR('Controle inconnu. Utiliser un @controle_id entre 1 et 37.', 16, 1);
END;
GO

/*
Exemples d'utilisation :

EXEC dbo.sp_controle_interne_vision_pro
    @date_debut = '2026-01-01',
    @date_fin = '2026-12-31',
    @controle_id = 1;

EXEC dbo.sp_controle_interne_vision_pro
    @date_debut = '2026-01-01',
    @date_fin = '2026-12-31',
    @controle_id = 14;
/*
