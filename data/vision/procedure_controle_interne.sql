/*
 Procedure stockee de controle interne - base BB_VISION_PRO
 
 Utilisation :
 EXEC dbo.sp_controle_interne_vision_pro @date_debut = '2026-01-01', @date_fin = '2026-12-31', @controle_id = 1;
 EXEC dbo.sp_controle_interne_vision_pro @date_debut = '2026-01-01', @date_fin = '2026-12-31', @controle_id = 14;
 
 Correspondance devise observee dans dbo.DEVISES :
 ID_DEVISE = 1 : USD - Dollars Americains
 ID_DEVISE = 2 : CDF - Franc Congolais
 
 Exemple pour produire la synthese Excel LBC-FT de juin 2026 en CDF :
 EXEC dbo.sp_controle_interne_vision_pro
 @date_debut = '2026-06-01',
 @date_fin = '2026-06-30',
 @controle_id = 38,
 @seuil_5k_usd_cdf = 14000000,
 @seuil_10k_usd_cdf = 28000000,
 @id_devise_reporting = 2;
 
 Dans cet exemple, les seuils supposent un taux de 1 USD = 2 800 CDF.
 Adapter ces montants au taux officiel retenu pour la periode.
 
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
 38 = Synthese Excel LBC-FT : depots, retraits et mobile banking
 39 = Fractionnement potentiel
 40 = Operations inhabituelles par client
 41 = Clients avec forte activite mais KYC incomplet
 42 = Depots et retraits agreges par client
 43 = Top clients par volume de mouvements
 44 = Analyse detaillee des operations annulees
 45 = Utilisateurs a risque
 46 = Analyse par point de service / agence
 47 = Detail mobile banking par type operation
 48 = Rubriques LBC-FT non couvertes automatiquement et pistes de mapping
 49 = Produits d'epargne inactifs encore utilises
 50 = Produits d'epargne non valides encore utilises
 51 = Produits sans depot ou retrait autorise mais avec mouvements
 52 = Incoherences de devise produit, compte et mouvement
 53 = Comptes sans produit d'epargne exploitable
 54 = Mouvements sans compte ou sans operation rattachee
 55 = Mouvements a montant nul, negatif ou tres eleve
 56 = Depots et retraits par client, compte, agence, devise et produit
 57 = Analyse des gros mouvements par periode
 58 = Analyse des mouvements par point de service
 59 = Demandes de credit sans pret accorde
 60 = Prets incomplets
 61 = Cycles de pret echus non clotures
 62 = Comparaison montant demande et montant accorde
 63 = Analyse des credits par agence, produit, devise et etat
 64 = Clients avec forte activite d'epargne et credit actif
 65 = Clients avec plusieurs demandes de credit sur une meme periode
 66 = Agences avec volume eleve de mouvements ou de credits
 67 = Produits d'epargne les plus utilises et produits credit les plus sollicites
 68 = Anomalies a prioriser pour audit
 69 = Prets decaisses sans validation prealable exploitable
 70 = Couverture de garantie insuffisante par rapport a la tranche
 71 = Caution financiere insuffisante par rapport au dossier
 72 = Garanties sans garant identifiable ou sans piece exploitable
 73 = Dossiers avec analyse obligatoire absente ou inachevee
 74 = Decaissements sans support exploitable ou avec montant incoherent
 75 = Credits de groupe avec nombre de beneficiaires hors norme
 76 = Nombre de prets actifs au-dela de la limite du produit
 77 = Mainlevee ou retrait de garantie avant solde du pret
 78 = Demandes de reechelonnement sans validation exploitable
 79 = Prets marques reechelonnes sans demande formelle
 80 = Prets en contentieux avec incoherences de transfert ou de montant
 81 = Validations de dossier incoherentes avec le dossier ou le pret
 82 = Types de garantie utilises mais non parametres pour l'agence
 83 = Cycles de pret sans echeancier TABAMOR exploitable
 */
USE [BB_VISION_PRO];
GO CREATE
    OR ALTER PROCEDURE dbo.sp_controle_interne_vision_pro @date_debut date = '2026-01-01',
    @date_fin date = '2026-12-31',
    @controle_id int,
    @seuil_5k_usd_cdf float = 0,
    @seuil_10k_usd_cdf float = 0,
    @id_devise_reporting int = NULL AS BEGIN
SET NOCOUNT ON;
IF @controle_id = 1 BEGIN
SELECT 'OPERATIONS' AS table_name,
    COUNT(*) AS nb_lignes
FROM dbo.OPERATIONS
UNION ALL
SELECT 'OPERATIONS_API',
    COUNT(*)
FROM dbo.OPERATIONS_API
UNION ALL
SELECT 'HDPM',
    COUNT(*)
FROM dbo.HDPM
UNION ALL
SELECT 'HDPM_API',
    COUNT(*)
FROM dbo.HDPM_API
UNION ALL
SELECT 'ADHERENTS',
    COUNT(*)
FROM dbo.ADHERENTS;
RETURN;
END;
IF @controle_id = 2 BEGIN
SELECT source_table,
    DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1) AS mois,
    ISNULL(CAST(ANNULE AS varchar(10)), 'NULL') AS statut_annule,
    COUNT(*) AS nb_operations
FROM (
        SELECT 'OPERATIONS' AS source_table,
            DATE_OPERATION,
            ANNULE
        FROM dbo.OPERATIONS
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
        UNION ALL
        SELECT 'OPERATIONS_API',
            DATE_OPERATION,
            ANNULE
        FROM dbo.OPERATIONS_API
        WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    ) x
GROUP BY source_table,
    DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1),
    ANNULE
ORDER BY mois,
    source_table,
    statut_annule;
RETURN;
END;
IF @controle_id = 3 BEGIN
SELECT 'OPERATIONS' AS source_table,
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
    AND (
        o.DATE_VALIDATION IS NULL
        OR o.DATE_VALIDE IS NULL
    )
UNION ALL
SELECT 'OPERATIONS_API',
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
ORDER BY DATE_OPERATION,
    source_table;
RETURN;
END;
IF @controle_id = 4 BEGIN
SELECT 'OPERATIONS' AS source_table,
    o.ID,
    o.DATE_OPERATION,
    o.DATE_SAISIE,
    DATEDIFF(
        day,
        o.DATE_OPERATION,
        CAST(o.DATE_SAISIE AS date)
    ) AS delai_saisie_jours,
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
SELECT 'OPERATIONS_API',
    CAST(oa.ID AS varchar(255)),
    oa.DATE_OPERATION,
    oa.DATE_SAISIE,
    DATEDIFF(
        day,
        oa.DATE_OPERATION,
        CAST(oa.DATE_SAISIE AS date)
    ),
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
ORDER BY delai_saisie_jours DESC,
    DATE_OPERATION;
RETURN;
END;
IF @controle_id = 5 BEGIN
SELECT 'OPERATIONS' AS source_table,
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
        (
            o.DATE_VALIDE IS NOT NULL
            AND o.DATE_SAISIE IS NOT NULL
            AND o.DATE_VALIDE < o.DATE_SAISIE
        )
        OR (
            o.DATE_VALIDATION IS NOT NULL
            AND o.DATE_VALIDATION < o.DATE_OPERATION
        )
    )
UNION ALL
SELECT 'OPERATIONS_API',
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
        (
            oa.DATE_VALIDE IS NOT NULL
            AND oa.DATE_SAISIE IS NOT NULL
            AND oa.DATE_VALIDE < oa.DATE_SAISIE
        )
        OR (
            oa.DATE_VALIDATION IS NOT NULL
            AND oa.DATE_VALIDATION < oa.DATE_OPERATION
        )
    )
ORDER BY DATE_OPERATION;
RETURN;
END;
IF @controle_id = 6 BEGIN
SELECT 'OPERATIONS' AS source_table,
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
    AND (
        o.ID_UTILISATEUR IS NULL
        OR o.ID_POINT_SERVICE IS NULL
        OR o.ID_TYPE_OPERATION IS NULL
    )
UNION ALL
SELECT 'OPERATIONS_API',
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
    AND (
        oa.ID_UTILISATEUR IS NULL
        OR oa.ID_POINT_SERVICE IS NULL
        OR oa.ID_TYPE_OPERATION IS NULL
    )
ORDER BY DATE_OPERATION,
    source_table;
RETURN;
END;
IF @controle_id = 7 BEGIN
SELECT NUM_TRANSACTION,
    COUNT(*) AS nb_operations,
    MIN(DATE_OPERATION) AS premiere_date,
    MAX(DATE_OPERATION) AS derniere_date
FROM dbo.OPERATIONS
WHERE NUM_TRANSACTION IS NOT NULL
    AND LTRIM(RTRIM(NUM_TRANSACTION)) <> ''
GROUP BY NUM_TRANSACTION
HAVING COUNT(*) > 1
ORDER BY nb_operations DESC,
    NUM_TRANSACTION;
RETURN;
END;
IF @controle_id = 8 BEGIN
SELECT NUMERO_RECU,
    COUNT(*) AS nb_operations,
    MIN(DATE_OPERATION) AS premiere_date,
    MAX(DATE_OPERATION) AS derniere_date
FROM dbo.OPERATIONS
WHERE NUMERO_RECU IS NOT NULL
    AND LTRIM(RTRIM(NUMERO_RECU)) <> ''
GROUP BY NUMERO_RECU
HAVING COUNT(*) > 1
ORDER BY nb_operations DESC,
    NUMERO_RECU;
RETURN;
END;
IF @controle_id = 9 BEGIN
SELECT DATE_OPERATION,
    ID_UTILISATEUR,
    ID_POINT_SERVICE,
    ID_TYPE_OPERATION,
    NUM_TRANSACTION,
    NUMERO_RECU,
    DESCRIPTION,
    COUNT(*) AS nb_doublons
FROM dbo.OPERATIONS
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY DATE_OPERATION,
    ID_UTILISATEUR,
    ID_POINT_SERVICE,
    ID_TYPE_OPERATION,
    NUM_TRANSACTION,
    NUMERO_RECU,
    DESCRIPTION
HAVING COUNT(*) > 1
ORDER BY nb_doublons DESC,
    DATE_OPERATION;
RETURN;
END;
IF @controle_id = 10 BEGIN
SELECT ID,
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
IF @controle_id = 11 BEGIN
SELECT o.ID,
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
IF @controle_id = 12 BEGIN
SELECT h.ID,
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
IF @controle_id = 13 BEGIN
SELECT o.ID,
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
IF @controle_id = 14 BEGIN
SELECT h.ID_OPERATION,
    MIN(h.DATE_OPERATION) AS date_operation,
    COUNT(*) AS nb_lignes,
    SUM(
        CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_debit,
    SUM(
        CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_credit,
    SUM(
        CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN - ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS ecart
FROM dbo.HDPM h
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND h.ID_OPERATION IS NOT NULL
GROUP BY h.ID_OPERATION
HAVING ABS(
        SUM(
            CASE
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN - ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        )
    ) > 0.01
ORDER BY ABS(
        SUM(
            CASE
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN - ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        )
    ) DESC;
RETURN;
END;
IF @controle_id = 15 BEGIN
SELECT h.ID_OPERATION,
    MIN(h.DATE_OPERATION) AS date_operation,
    COUNT(*) AS nb_lignes,
    SUM(
        CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_debit,
    SUM(
        CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_credit,
    SUM(
        CASE
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
            WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN - ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS ecart
FROM dbo.HDPM_API h
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND h.ID_OPERATION IS NOT NULL
GROUP BY h.ID_OPERATION
HAVING ABS(
        SUM(
            CASE
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN - ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        )
    ) > 0.01
ORDER BY ABS(
        SUM(
            CASE
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(h.MONTANT_OPERATION, 0)
                WHEN UPPER(ISNULL(h.SENS, '')) IN ('C', 'CREDIT') THEN - ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        )
    ) DESC;
RETURN;
END;
IF @controle_id = 16 BEGIN
SELECT 'HDPM' AS source_table,
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
    AND (
        h.MONTANT_OPERATION IS NULL
        OR h.MONTANT_OPERATION <= 0
        OR h.SENS IS NULL
    )
UNION ALL
SELECT 'HDPM_API',
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
    AND (
        h.MONTANT_OPERATION IS NULL
        OR h.MONTANT_OPERATION <= 0
        OR h.SENS IS NULL
    )
ORDER BY DATE_OPERATION,
    source_table;
RETURN;
END;
IF @controle_id = 17 BEGIN
SELECT ID,
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
IF @controle_id = 18 BEGIN
SELECT h.ID,
    h.DATE_OPERATION,
    h.ID_OPERATION,
    h.ID_COMPTE,
    h.SENS,
    h.MONTANT_OPERATION,
    h.DESCRIPTION
FROM dbo.HDPM h
    LEFT JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND (
        h.ID_COMPTE IS NULL
        OR c.ID IS NULL
    )
ORDER BY h.DATE_OPERATION;
RETURN;
END;
IF @controle_id = 19 BEGIN
SELECT h.ID,
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
IF @controle_id = 20 BEGIN
SELECT COALESCE(o.NUM_TRANSACTION, oa.NUM_TRANSACTION) AS num_transaction,
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
    FULL OUTER JOIN dbo.OPERATIONS_API oa ON oa.NUM_TRANSACTION = o.NUM_TRANSACTION
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
ORDER BY COALESCE(o.DATE_OPERATION, oa.DATE_OPERATION),
    statut_rapprochement;
RETURN;
END;
IF @controle_id = 21 BEGIN WITH hdpm_bo AS (
    SELECT ID_OPERATION,
        COUNT(*) AS nb_lignes_bo,
        SUM(
            CASE
                WHEN UPPER(ISNULL(SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(MONTANT_OPERATION, 0)
                ELSE 0
            END
        ) AS debit_bo,
        SUM(
            CASE
                WHEN UPPER(ISNULL(SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(MONTANT_OPERATION, 0)
                ELSE 0
            END
        ) AS credit_bo
    FROM dbo.HDPM
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    GROUP BY ID_OPERATION
),
hdpm_api AS (
    SELECT ID_OPERATION,
        COUNT(*) AS nb_lignes_api,
        SUM(
            CASE
                WHEN UPPER(ISNULL(SENS, '')) IN ('D', 'DEBIT') THEN ISNULL(MONTANT_OPERATION, 0)
                ELSE 0
            END
        ) AS debit_api,
        SUM(
            CASE
                WHEN UPPER(ISNULL(SENS, '')) IN ('C', 'CREDIT') THEN ISNULL(MONTANT_OPERATION, 0)
                ELSE 0
            END
        ) AS credit_api
    FROM dbo.HDPM_API
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    GROUP BY ID_OPERATION
)
SELECT COALESCE(b.ID_OPERATION, a.ID_OPERATION) AS id_operation,
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
IF @controle_id = 22 BEGIN
SELECT o.ID_UTILISATEUR,
    u.LOGIN,
    u.NOM,
    u.PRENOM,
    COUNT(*) AS nb_operations,
    SUM(
        CASE
            WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1
            ELSE 0
        END
    ) AS nb_annulees,
    AVG(
        CASE
            WHEN o.DATE_SAISIE IS NOT NULL THEN DATEDIFF(
                day,
                o.DATE_OPERATION,
                CAST(o.DATE_SAISIE AS date)
            ) * 1.0
        END
    ) AS delai_moyen_saisie_jours
FROM dbo.OPERATIONS o
    LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY o.ID_UTILISATEUR,
    u.LOGIN,
    u.NOM,
    u.PRENOM
ORDER BY nb_operations DESC;
RETURN;
END;
IF @controle_id = 23 BEGIN
SELECT o.ID,
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
IF @controle_id = 24 BEGIN
SELECT CODE,
    COUNT(*) AS nb_adherents,
    MIN(DATE_INSCRIPTION) AS premiere_inscription,
    MAX(DATE_INSCRIPTION) AS derniere_inscription
FROM dbo.ADHERENTS
WHERE CODE IS NOT NULL
    AND LTRIM(RTRIM(CODE)) <> ''
GROUP BY CODE
HAVING COUNT(*) > 1
ORDER BY nb_adherents DESC,
    CODE;
RETURN;
END;
IF @controle_id = 25 BEGIN
SELECT ID,
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
ORDER BY DATE_INSCRIPTION,
    CODE;
RETURN;
END;
IF @controle_id = 26 BEGIN
SELECT ID,
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
IF @controle_id = 27 BEGIN
SELECT ID,
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
IF @controle_id = 28 BEGIN
SELECT a.ID,
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
IF @controle_id = 29 BEGIN
SELECT DATEFROMPARTS(
        YEAR(h.DATE_OPERATION),
        MONTH(h.DATE_OPERATION),
        1
    ) AS mois,
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
GROUP BY DATEFROMPARTS(
        YEAR(h.DATE_OPERATION),
        MONTH(h.DATE_OPERATION),
        1
    ),
    h.ID_POINT_SERVICE,
    ps.CODE,
    ps.NOM,
    h.ID_DEVISE,
    d.CODE,
    d.LIBELLE,
    d.SYMBOLE,
    h.SENS
ORDER BY mois,
    h.ID_POINT_SERVICE,
    h.ID_DEVISE,
    h.SENS;
RETURN;
END;
IF @controle_id = 30 BEGIN
SELECT TOP (100) h.ID_OPERATION,
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
IF @controle_id = 31 BEGIN
SELECT oa.ID,
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
ORDER BY oa.DATE_OPERATION,
    oa.ID;
RETURN;
END;
IF @controle_id = 32 BEGIN
SELECT oa.ID,
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ID_TYPE_OPERATION,
    oa.ID_POINT_SERVICE,
    oa.NUM_TRANSACTION,
    COUNT(h.ID) AS nb_lignes_hdpm_api,
    SUM(
        CASE
            WHEN h.SENS = 'D' THEN 1
            ELSE 0
        END
    ) AS nb_debit,
    SUM(
        CASE
            WHEN h.SENS = 'C' THEN 1
            ELSE 0
        END
    ) AS nb_credit,
    SUM(
        CASE
            WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_debit,
    SUM(
        CASE
            WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_credit,
    ABS(
        SUM(
            CASE
                WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        ) - SUM(
            CASE
                WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        )
    ) AS ecart
FROM dbo.OPERATIONS_API oa
    LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(oa.ANNULE, 0) = 0
    AND oa.ID_TYPE_OPERATION LIKE 'MOB_%'
GROUP BY oa.ID,
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ID_TYPE_OPERATION,
    oa.ID_POINT_SERVICE,
    oa.NUM_TRANSACTION
HAVING COUNT(h.ID) <> 2
    OR SUM(
        CASE
            WHEN h.SENS = 'D' THEN 1
            ELSE 0
        END
    ) <> 1
    OR SUM(
        CASE
            WHEN h.SENS = 'C' THEN 1
            ELSE 0
        END
    ) <> 1
    OR ABS(
        SUM(
            CASE
                WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        ) - SUM(
            CASE
                WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0)
                ELSE 0
            END
        )
    ) > 0.01
ORDER BY oa.DATE_OPERATION,
    oa.ID;
RETURN;
END;
IF @controle_id = 33 BEGIN
SELECT oa.ID,
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
GROUP BY oa.ID,
    oa.CODE,
    oa.DATE_OPERATION,
    oa.ANNULE,
    oa.ID_OPERATION_ANNULE,
    oa.ID_OPERATION_MERE,
    oa.ID_TYPE_OPERATION,
    oa.NUM_TRANSACTION
ORDER BY oa.DATE_OPERATION,
    oa.ID;
RETURN;
END;
IF @controle_id = 34 BEGIN
SELECT DATEFROMPARTS(YEAR(DATE_OPERATION), MONTH(DATE_OPERATION), 1) AS mois,
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
ORDER BY mois,
    ID_TYPE_OPERATION,
    statut_annulation;
RETURN;
END;
IF @controle_id = 35 BEGIN
SELECT DATE_OPERATION,
    ID_TYPE_OPERATION,
    ID_POINT_SERVICE,
    COUNT(*) AS nb_operations
FROM dbo.OPERATIONS
WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND DATE_OPERATION = EOMONTH(DATE_OPERATION)
GROUP BY DATE_OPERATION,
    ID_TYPE_OPERATION,
    ID_POINT_SERVICE
HAVING COUNT(*) >= 100
ORDER BY DATE_OPERATION,
    nb_operations DESC;
RETURN;
END;
IF @controle_id = 36 BEGIN
SELECT 'BACK_OFFICE' AS source_mouvement,
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
SELECT 'API_MOBILE' AS source_mouvement,
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
ORDER BY DATE_OPERATION,
    source_mouvement,
    id_operation,
    SENS;
RETURN;
END;
IF @controle_id = 37 BEGIN
SELECT 'BACK_OFFICE' AS source_mouvement,
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
SELECT 'API_MOBILE' AS source_mouvement,
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
ORDER BY DATE_OPERATION,
    source_mouvement,
    id_operation,
    id_ecriture;
RETURN;
END;
IF @controle_id = 38 BEGIN WITH mouvements AS (
    SELECT 'BACK_OFFICE' AS source_mouvement,
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
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY o.ID,
        o.DATE_OPERATION,
        o.ID_TYPE_OPERATION,
        h.ID_DEVISE
    UNION ALL
    SELECT 'API_MOBILE' AS source_mouvement,
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
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY oa.CODE,
        oa.DATE_OPERATION,
        oa.ID_TYPE_OPERATION,
        h.ID_DEVISE
)
SELECT '1. ACTIVITE' AS section,
    25 AS ligne_excel,
    'Total Depots' AS rubrique,
    COUNT(*) AS nombre,
    SUM(montant_operation) AS volume,
    'Alimente la ligne Total Depots du reporting.' AS commentaire
FROM mouvements
WHERE type_mouvement IN ('Depot', 'Depot mobile')
UNION ALL
SELECT '3. PRODUIT - SERVICE - OPERATIONS',
    53,
    'Depot >= 10k USD',
    COUNT(*),
    SUM(montant_operation),
    'Seuil a renseigner en CDF dans @seuil_10k_usd_cdf.'
FROM mouvements
WHERE type_mouvement IN ('Depot', 'Depot mobile')
    AND montant_operation >= @seuil_10k_usd_cdf
UNION ALL
SELECT '3. PRODUIT - SERVICE - OPERATIONS',
    54,
    'Retrait >= 10k USD',
    COUNT(*),
    SUM(montant_operation),
    'Seuil a renseigner en CDF dans @seuil_10k_usd_cdf.'
FROM mouvements
WHERE type_mouvement IN ('Retrait', 'Retrait mobile')
    AND montant_operation >= @seuil_10k_usd_cdf
UNION ALL
SELECT '3. PRODUIT - SERVICE - OPERATIONS',
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
SELECT '3. PRODUIT - SERVICE - OPERATIONS',
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
SELECT '4. CANAUX DE DISTRIBUTION',
    132,
    'Operations effectuees par Mobile Banking',
    COUNT(*),
    SUM(montant_operation),
    'Operations API mobiles : MOB_DEPO et MOB_RETR.'
FROM mouvements
WHERE source_mouvement = 'API_MOBILE'
UNION ALL
SELECT '4. CANAUX DE DISTRIBUTION',
    134,
    'Wallet to Bank',
    COUNT(*),
    SUM(montant_operation),
    'Approximation : depots mobiles MOB_DEPO.'
FROM mouvements
WHERE ID_TYPE_OPERATION = 'MOB_DEPO'
ORDER BY ligne_excel;
RETURN;
END;
IF @controle_id = 39 BEGIN WITH mouvements AS (
    SELECT 'BACK_OFFICE' AS source_mouvement,
        o.ID AS id_operation,
        o.DATE_OPERATION,
        o.ID_TYPE_OPERATION,
        CASE
            WHEN o.ID_TYPE_OPERATION = 'DEPO' THEN 'Depot'
            WHEN o.ID_TYPE_OPERATION = 'RETR' THEN 'Retrait'
        END AS type_mouvement,
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
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY o.ID,
        o.DATE_OPERATION,
        o.ID_TYPE_OPERATION,
        ca.ID_ADHERENT,
        a.CODE,
        a.NOM_ADHERENT,
        h.ID_DEVISE
    UNION ALL
    SELECT 'API_MOBILE',
        oa.CODE,
        oa.DATE_OPERATION,
        oa.ID_TYPE_OPERATION,
        CASE
            WHEN oa.ID_TYPE_OPERATION = 'MOB_DEPO' THEN 'Depot'
            WHEN oa.ID_TYPE_OPERATION = 'MOB_RETR' THEN 'Retrait'
        END,
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
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY oa.CODE,
        oa.DATE_OPERATION,
        oa.ID_TYPE_OPERATION,
        ca.ID_ADHERENT,
        a.CODE,
        a.NOM_ADHERENT,
        h.ID_DEVISE
)
SELECT DATE_OPERATION,
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
GROUP BY DATE_OPERATION,
    ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT,
    type_mouvement,
    ID_DEVISE
HAVING COUNT(*) >= 2
    AND SUM(montant_operation) >= @seuil_10k_usd_cdf
ORDER BY montant_cumule DESC,
    DATE_OPERATION;
RETURN;
END;
IF @controle_id = 40 BEGIN WITH mouvements AS (
    SELECT o.DATE_OPERATION,
        ca.ID_ADHERENT,
        a.CODE AS code_adherent,
        a.NOM_ADHERENT,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation
    FROM dbo.OPERATIONS o
        INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
        LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
        LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN DATEADD(month, -3, @date_debut)
        AND @date_fin
        AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
        AND ISNULL(o.ANNULE, 0) = 0
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY o.ID,
        o.DATE_OPERATION,
        ca.ID_ADHERENT,
        a.CODE,
        a.NOM_ADHERENT
),
periode AS (
    SELECT ID_ADHERENT,
        code_adherent,
        NOM_ADHERENT,
        SUM(montant_operation) AS volume_periode,
        COUNT(*) AS nb_operations_periode
    FROM mouvements
    WHERE DATE_OPERATION BETWEEN @date_debut AND @date_fin
    GROUP BY ID_ADHERENT,
        code_adherent,
        NOM_ADHERENT
),
historique AS (
    SELECT ID_ADHERENT,
        AVG(volume_jour) AS moyenne_journaliere_historique
    FROM (
            SELECT ID_ADHERENT,
                DATE_OPERATION,
                SUM(montant_operation) AS volume_jour
            FROM mouvements
            WHERE DATE_OPERATION < @date_debut
            GROUP BY ID_ADHERENT,
                DATE_OPERATION
        ) h
    GROUP BY ID_ADHERENT
)
SELECT p.ID_ADHERENT,
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
    AND (
        h.moyenne_journaliere_historique IS NULL
        OR p.volume_periode >= 3 * h.moyenne_journaliere_historique
    )
ORDER BY p.volume_periode DESC;
RETURN;
END;
IF @controle_id = 41 BEGIN WITH mouvements AS (
    SELECT ca.ID_ADHERENT,
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
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
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
RETURN;
END;
IF @controle_id = 42 BEGIN WITH mouvements AS (
    SELECT ca.ID_ADHERENT,
        a.CODE AS code_adherent,
        a.NOM_ADHERENT,
        CASE
            WHEN o.ID_TYPE_OPERATION = 'DEPO' THEN 'Depot'
            WHEN o.ID_TYPE_OPERATION = 'RETR' THEN 'Retrait'
        END AS type_mouvement,
        MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS montant_operation
    FROM dbo.OPERATIONS o
        INNER JOIN dbo.HDPM h ON h.ID_OPERATION = o.ID
        LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = h.ID_COMPTE
        LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
        AND o.ID_TYPE_OPERATION IN ('DEPO', 'RETR')
        AND ISNULL(o.ANNULE, 0) = 0
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY o.ID,
        ca.ID_ADHERENT,
        a.CODE,
        a.NOM_ADHERENT,
        o.ID_TYPE_OPERATION
)
SELECT ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT,
    SUM(
        CASE
            WHEN type_mouvement = 'Depot' THEN 1
            ELSE 0
        END
    ) AS nb_depots,
    SUM(
        CASE
            WHEN type_mouvement = 'Depot' THEN montant_operation
            ELSE 0
        END
    ) AS volume_depots,
    SUM(
        CASE
            WHEN type_mouvement = 'Retrait' THEN 1
            ELSE 0
        END
    ) AS nb_retraits,
    SUM(
        CASE
            WHEN type_mouvement = 'Retrait' THEN montant_operation
            ELSE 0
        END
    ) AS volume_retraits,
    COUNT(*) AS nb_operations,
    SUM(montant_operation) AS volume_total
FROM mouvements
GROUP BY ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT
ORDER BY volume_total DESC;
RETURN;
END;
IF @controle_id = 43 BEGIN WITH mouvements AS (
    SELECT ca.ID_ADHERENT,
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
        AND (
            @id_devise_reporting IS NULL
            OR h.ID_DEVISE = @id_devise_reporting
        )
    GROUP BY o.ID,
        ca.ID_ADHERENT,
        a.CODE,
        a.NOM_ADHERENT
)
SELECT TOP (50) ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT,
    COUNT(*) AS nb_operations,
    SUM(montant_operation) AS volume_total,
    MAX(montant_operation) AS plus_grosse_operation
FROM mouvements
GROUP BY ID_ADHERENT,
    code_adherent,
    NOM_ADHERENT
ORDER BY volume_total DESC;
RETURN;
END;
IF @controle_id = 44 BEGIN
SELECT 'BACK_OFFICE' AS source_operation,
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
SELECT 'API_MOBILE',
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
ORDER BY DATE_OPERATION,
    source_operation,
    id_operation;
RETURN;
END;
IF @controle_id = 45 BEGIN
SELECT o.ID_UTILISATEUR,
    u.LOGIN,
    u.NOM,
    u.PRENOM,
    COUNT(*) AS nb_operations,
    SUM(
        CASE
            WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1
            ELSE 0
        END
    ) AS nb_annulations,
    SUM(
        CASE
            WHEN o.DATE_SAISIE IS NOT NULL
            AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION THEN 1
            ELSE 0
        END
    ) AS nb_saisies_tardives,
    SUM(
        CASE
            WHEN o.ID_UTILISATEUR IS NOT NULL
            AND o.ID_UTILISATEUR = o.ID_UTILISATEUR_VALIDE THEN 1
            ELSE 0
        END
    ) AS nb_auto_validations,
    COUNT(DISTINCT o.ID_POINT_SERVICE) AS nb_points_service,
    COUNT(DISTINCT o.ID_TYPE_OPERATION) AS nb_types_operation
FROM dbo.OPERATIONS o
    LEFT JOIN dbo.UTILISATEURS u ON u.id = o.ID_UTILISATEUR
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY o.ID_UTILISATEUR,
    u.LOGIN,
    u.NOM,
    u.PRENOM
HAVING COUNT(*) >= 50
    OR SUM(
        CASE
            WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1
            ELSE 0
        END
    ) > 0
    OR SUM(
        CASE
            WHEN o.DATE_SAISIE IS NOT NULL
            AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION THEN 1
            ELSE 0
        END
    ) >= 10
    OR SUM(
        CASE
            WHEN o.ID_UTILISATEUR IS NOT NULL
            AND o.ID_UTILISATEUR = o.ID_UTILISATEUR_VALIDE THEN 1
            ELSE 0
        END
    ) > 0
ORDER BY nb_annulations DESC,
    nb_saisies_tardives DESC,
    nb_operations DESC;
RETURN;
END;
IF @controle_id = 46 BEGIN
SELECT o.ID_POINT_SERVICE,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    o.ID_TYPE_OPERATION,
    COUNT(*) AS nb_operations,
    SUM(
        CASE
            WHEN ISNULL(o.ANNULE, 0) = 1 THEN 1
            ELSE 0
        END
    ) AS nb_annulations,
    SUM(
        CASE
            WHEN o.DATE_SAISIE IS NOT NULL
            AND CAST(o.DATE_SAISIE AS date) > o.DATE_OPERATION THEN 1
            ELSE 0
        END
    ) AS nb_saisies_tardives
FROM dbo.OPERATIONS o
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = o.ID_POINT_SERVICE
WHERE o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY o.ID_POINT_SERVICE,
    ps.CODE,
    ps.NOM,
    o.ID_TYPE_OPERATION
ORDER BY nb_operations DESC;
RETURN;
END;
IF @controle_id = 47 BEGIN
SELECT oa.ID_TYPE_OPERATION,
    DATEFROMPARTS(
        YEAR(oa.DATE_OPERATION),
        MONTH(oa.DATE_OPERATION),
        1
    ) AS mois,
    oa.ID_POINT_SERVICE,
    COUNT(DISTINCT oa.CODE) AS nb_operations,
    COUNT(h.ID) AS nb_lignes_hdpm_api,
    SUM(
        CASE
            WHEN h.SENS = 'D' THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_debit,
    SUM(
        CASE
            WHEN h.SENS = 'C' THEN ISNULL(h.MONTANT_OPERATION, 0)
            ELSE 0
        END
    ) AS total_credit,
    SUM(
        CASE
            WHEN ISNULL(oa.ANNULE, 0) = 1 THEN 1
            ELSE 0
        END
    ) AS nb_annulees
FROM dbo.OPERATIONS_API oa
    LEFT JOIN dbo.HDPM_API h ON h.ID_OPERATION = oa.CODE
WHERE oa.DATE_OPERATION BETWEEN @date_debut AND @date_fin
GROUP BY oa.ID_TYPE_OPERATION,
    DATEFROMPARTS(
        YEAR(oa.DATE_OPERATION),
        MONTH(oa.DATE_OPERATION),
        1
    ),
    oa.ID_POINT_SERVICE
ORDER BY mois,
    oa.ID_TYPE_OPERATION,
    oa.ID_POINT_SERVICE;
RETURN;
END;
IF @controle_id = 48 BEGIN
SELECT *
FROM (
        VALUES (
                'PPE',
                'A mapper avec une table/colonne indiquant les personnes politiquement exposees.'
            ),
            (
                'Non-residents',
                'A mapper avec les donnees pays/adresse/statut resident du client.'
            ),
            (
                'MPME',
                'A mapper avec categorie/type adherent ou secteur activite officiel.'
            ),
            (
                'OBNL',
                'A mapper avec categorie/type adherent, secteur activite ou forme juridique.'
            ),
            (
                'Secteur immobilier',
                'A mapper avec SECTEURS_ACTIVITE / SECTEURS_ACTIVITE_CREDIT.'
            ),
            (
                'Secteur minier',
                'A mapper avec SECTEURS_ACTIVITE / objet de financement.'
            ),
            (
                'DOS / declarations de soupcon',
                'Necessite la table ou le fichier des declarations de soupcon.'
            ),
            (
                'Sanctions financieres ciblees',
                'Necessite la source de screening sanctions et gels/refus.'
            ),
            (
                'Credits rembourses anticipativement',
                'Necessite analyse PRETS / REMBOURSEMENTS / echeanciers.'
            )
    ) v(rubrique_reporting, prerequis_mapping)
ORDER BY rubrique_reporting;
RETURN;
END;
IF @controle_id = 49 BEGIN
SELECT pe.ID AS id_produit_epargne,
    pe.LIBELLE AS produit_epargne,
    pe.ACTIF AS produit_actif,
    c.ID AS id_compte,
    c.NUM_CPTE AS numero_compte,
    c.ETAT AS etat_compte,
    a.ID AS id_adherent,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence
FROM dbo.COMPTES c
    INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
    INNER JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = COALESCE(c.ID_POINT_SERVICE, c.ID_AGENCE)
WHERE ISNULL(pe.ACTIF, 0) = 0
ORDER BY pe.LIBELLE,
    c.NUM_CPTE;
RETURN;
END;
IF @controle_id = 50 BEGIN
SELECT pe.ID AS id_produit_epargne,
    pe.LIBELLE AS produit_epargne,
    pe.IS_EPG_VALIDE,
    c.ID AS id_compte,
    c.NUM_CPTE AS numero_compte,
    c.ETAT AS etat_compte,
    a.ID AS id_adherent,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence
FROM dbo.COMPTES c
    INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
    INNER JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = COALESCE(c.ID_POINT_SERVICE, c.ID_AGENCE)
WHERE ISNULL(pe.IS_EPG_VALIDE, 0) = 0
ORDER BY pe.LIBELLE,
    c.NUM_CPTE;
RETURN;
END;
IF @controle_id = 51 BEGIN
SELECT CASE
        WHEN h.SENS = 'C'
        AND ISNULL(pe.OPERATION_DEPOT, 0) = 0 THEN 'Credits sur produit sans depot autorise'
        WHEN h.SENS = 'D'
        AND ISNULL(pe.OPERATION_RETRAIT, 0) = 0 THEN 'Debits sur produit sans retrait autorise'
        ELSE 'Autre'
    END AS anomalie,
    pe.ID AS id_produit_epargne,
    pe.LIBELLE AS produit_epargne,
    c.ID AS id_compte,
    c.NUM_CPTE AS numero_compte,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence,
    COUNT(*) AS nb_mouvements,
    SUM(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS montant_total
FROM dbo.HDPM_VIEW h
    INNER JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
    INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
    INNER JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = COALESCE(
        h.ID_POINT_SERVICE,
        c.ID_POINT_SERVICE,
        c.ID_AGENCE
    )
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
    AND (
        (
            h.SENS = 'C'
            AND ISNULL(pe.OPERATION_DEPOT, 0) = 0
        )
        OR (
            h.SENS = 'D'
            AND ISNULL(pe.OPERATION_RETRAIT, 0) = 0
        )
    )
GROUP BY CASE
        WHEN h.SENS = 'C'
        AND ISNULL(pe.OPERATION_DEPOT, 0) = 0 THEN 'Credits sur produit sans depot autorise'
        WHEN h.SENS = 'D'
        AND ISNULL(pe.OPERATION_RETRAIT, 0) = 0 THEN 'Debits sur produit sans retrait autorise'
        ELSE 'Autre'
    END,
    pe.ID,
    pe.LIBELLE,
    c.ID,
    c.NUM_CPTE,
    a.CODE,
    a.NOM_ADHERENT,
    ps.CODE,
    ps.NOM
ORDER BY nb_mouvements DESC,
    montant_total DESC;
RETURN;
END;
IF @controle_id = 52 BEGIN
SELECT pe.ID AS id_produit_epargne,
    pe.LIBELLE AS produit_epargne,
    dp.CODE AS devise_produit,
    c.ID AS id_compte,
    c.NUM_CPTE AS numero_compte,
    dc.CODE AS devise_compte,
    h.ID AS id_mouvement,
    h.DATE_OPERATION,
    dh.CODE AS devise_mouvement,
    h.MONTANT_OPERATION,
    h.ID_TYPE_OPERATION,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT
FROM dbo.HDPM_VIEW h
    INNER JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
    INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
    INNER JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    LEFT JOIN dbo.DEVISES dp ON dp.ID = pe.ID_DEVISE
    LEFT JOIN dbo.DEVISES dc ON dc.ID = c.ID_DEVISE
    LEFT JOIN dbo.DEVISES dh ON dh.ID = h.ID_DEVISE
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
    AND (
        ISNULL(pe.ID_DEVISE, -1) <> ISNULL(c.ID_DEVISE, -1)
        OR ISNULL(pe.ID_DEVISE, -1) <> ISNULL(h.ID_DEVISE, -1)
        OR ISNULL(c.ID_DEVISE, -1) <> ISNULL(h.ID_DEVISE, -1)
    )
ORDER BY h.DATE_OPERATION DESC,
    pe.LIBELLE,
    c.NUM_CPTE;
RETURN;
END;
IF @controle_id = 53 BEGIN
SELECT c.ID AS id_compte,
    c.NUM_CPTE AS numero_compte,
    c.ETAT AS etat_compte,
    cai.ID_PRODUIT_EPG AS id_produit_reference,
    pe.LIBELLE AS produit_epargne,
    CASE
        WHEN cai.ID_PRODUIT_EPG IS NULL THEN 'Compte sans produit epargne reference'
        WHEN pe.ID IS NULL THEN 'Produit epargne introuvable'
        WHEN ISNULL(pe.IS_EPG_VALIDE, 0) = 0 THEN 'Produit epargne non valide'
        ELSE 'A verifier'
    END AS anomalie,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence
FROM dbo.COMPTES c
    LEFT JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
    LEFT JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = COALESCE(c.ID_POINT_SERVICE, c.ID_AGENCE)
WHERE cai.ID_PRODUIT_EPG IS NULL
    OR pe.ID IS NULL
    OR ISNULL(pe.IS_EPG_VALIDE, 0) = 0
ORDER BY anomalie,
    c.NUM_CPTE;
RETURN;
END;
IF @controle_id = 54 BEGIN
SELECT h.ID AS id_mouvement,
    h.DATE_OPERATION,
    h.ID_COMPTE,
    c.NUM_CPTE AS numero_compte,
    h.ID_OPERATION,
    h.NUM_TRANSACTION,
    h.NUMERO_RECU,
    h.ID_POINT_SERVICE,
    h.ID_TYPE_OPERATION,
    h.SENS,
    h.MONTANT_OPERATION,
    CASE
        WHEN NULLIF(LTRIM(RTRIM(ISNULL(h.ID_COMPTE, ''))), '') IS NULL THEN 'Mouvement sans compte'
        WHEN c.ID IS NULL THEN 'Mouvement avec compte inexistant'
        WHEN NULLIF(LTRIM(RTRIM(ISNULL(h.ID_OPERATION, ''))), '') IS NULL THEN 'Mouvement sans operation rattachee'
        WHEN o.ID IS NULL
        AND oa.CODE IS NULL THEN 'Operation rattachee introuvable'
        ELSE 'A verifier'
    END AS anomalie
FROM dbo.HDPM_VIEW h
    LEFT JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
    LEFT JOIN dbo.OPERATIONS o ON o.ID = h.ID_OPERATION
    LEFT JOIN dbo.OPERATIONS_API oa ON oa.CODE = h.ID_OPERATION
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND (
        NULLIF(LTRIM(RTRIM(ISNULL(h.ID_COMPTE, ''))), '') IS NULL
        OR c.ID IS NULL
        OR NULLIF(LTRIM(RTRIM(ISNULL(h.ID_OPERATION, ''))), '') IS NULL
        OR (
            o.ID IS NULL
            AND oa.CODE IS NULL
        )
    )
ORDER BY h.DATE_OPERATION DESC,
    anomalie;
RETURN;
END;
IF @controle_id = 55 BEGIN
SELECT h.ID AS id_mouvement,
    h.DATE_OPERATION,
    h.ID_COMPTE,
    c.NUM_CPTE AS numero_compte,
    h.ID_OPERATION,
    h.ID_TYPE_OPERATION,
    h.SENS,
    h.MONTANT_OPERATION,
    h.MONTANT_REEL,
    d.CODE AS devise_mouvement,
    CASE
        WHEN ISNULL(h.MONTANT_OPERATION, 0) = 0 THEN 'Montant nul'
        WHEN ISNULL(h.MONTANT_OPERATION, 0) < 0 THEN 'Montant negatif'
        WHEN ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION)) >= CASE
            WHEN @seuil_10k_usd_cdf > 0 THEN @seuil_10k_usd_cdf
            ELSE 10000000
        END THEN 'Montant eleve'
        ELSE 'A verifier'
    END AS anomalie
FROM dbo.HDPM_VIEW h
    LEFT JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
    LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND (
        ISNULL(h.MONTANT_OPERATION, 0) <= 0
        OR ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION)) >= CASE
            WHEN @seuil_10k_usd_cdf > 0 THEN @seuil_10k_usd_cdf
            ELSE 10000000
        END
    )
ORDER BY ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION)) DESC,
    h.DATE_OPERATION DESC;
RETURN;
END;
IF @controle_id = 56 BEGIN
SELECT CASE
        WHEN h.SENS = 'C' THEN 'Depot / entree'
        WHEN h.SENS = 'D' THEN 'Retrait / sortie'
        ELSE 'Autre'
    END AS nature_mouvement,
    a.ID AS id_adherent,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    c.ID AS id_compte,
    c.NUM_CPTE AS numero_compte,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence,
    d.CODE AS devise,
    pe.ID AS id_produit_epargne,
    pe.LIBELLE AS produit_epargne,
    COUNT(*) AS nb_mouvements,
    SUM(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS montant_total,
    AVG(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS montant_moyen,
    MAX(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS montant_max
FROM dbo.HDPM_VIEW h
    INNER JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
    LEFT JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
    LEFT JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    LEFT JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = ca.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = COALESCE(
        h.ID_POINT_SERVICE,
        c.ID_POINT_SERVICE,
        c.ID_AGENCE
    )
    LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
    AND h.SENS IN ('C', 'D')
GROUP BY CASE
        WHEN h.SENS = 'C' THEN 'Depot / entree'
        WHEN h.SENS = 'D' THEN 'Retrait / sortie'
        ELSE 'Autre'
    END,
    a.ID,
    a.CODE,
    a.NOM_ADHERENT,
    c.ID,
    c.NUM_CPTE,
    ps.CODE,
    ps.NOM,
    d.CODE,
    pe.ID,
    pe.LIBELLE
ORDER BY montant_total DESC,
    nb_mouvements DESC;
RETURN;
END;
IF @controle_id = 57 BEGIN
SELECT DATEFROMPARTS(
        YEAR(h.DATE_OPERATION),
        MONTH(h.DATE_OPERATION),
        1
    ) AS mois,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    d.CODE AS devise,
    COUNT(*) AS nb_gros_mouvements,
    SUM(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS volume_total,
    MAX(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS plus_gros_mouvement
FROM dbo.HDPM_VIEW h
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = h.ID_POINT_SERVICE
    LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION)) >= CASE
        WHEN @seuil_5k_usd_cdf > 0 THEN @seuil_5k_usd_cdf
        ELSE 5000000
    END
GROUP BY DATEFROMPARTS(
        YEAR(h.DATE_OPERATION),
        MONTH(h.DATE_OPERATION),
        1
    ),
    ps.CODE,
    ps.NOM,
    d.CODE
ORDER BY mois,
    volume_total DESC;
RETURN;
END;
IF @controle_id = 58 BEGIN
SELECT h.ID_POINT_SERVICE,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    d.CODE AS devise,
    COUNT(*) AS nb_mouvements,
    COUNT(DISTINCT h.ID_COMPTE) AS nb_comptes_touches,
    COUNT(DISTINCT h.ID_OPERATION) AS nb_operations_rattachees,
    SUM(
        CASE
            WHEN h.SENS = 'C' THEN ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))
            ELSE 0
        END
    ) AS total_credits,
    SUM(
        CASE
            WHEN h.SENS = 'D' THEN ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))
            ELSE 0
        END
    ) AS total_debits
FROM dbo.HDPM_VIEW h
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = h.ID_POINT_SERVICE
    LEFT JOIN dbo.DEVISES d ON d.ID = h.ID_DEVISE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
GROUP BY h.ID_POINT_SERVICE,
    ps.CODE,
    ps.NOM,
    d.CODE
ORDER BY nb_mouvements DESC,
    total_credits + total_debits DESC;
RETURN;
END;
IF @controle_id = 59 BEGIN
SELECT dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    dc.REF_DEMANDE,
    dc.DATE_RECEPTION,
    dc.ETAT_DEMANDE,
    dc.MONTANT_DEMANDE,
    dc.ID_POINT_SERIVCE,
    ps_service.CODE AS code_point_service_demande,
    ps_service.NOM AS nom_point_service_demande,
    dc.ID_AGENCE,
    ps_agence.CODE AS code_agence,
    ps_agence.NOM AS nom_agence,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    p.ID AS id_pret
FROM dbo.DEMANDES_CREDIT dc
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps_service ON ps_service.ID = dc.ID_POINT_SERIVCE
    LEFT JOIN dbo.POINTS_SERVICE ps_agence ON ps_agence.ID = dc.ID_AGENCE
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
    AND p.ID IS NULL
ORDER BY dc.DATE_RECEPTION DESC,
    dc.MONTANT_DEMANDE DESC;
RETURN;
END;
IF @controle_id = 60 BEGIN WITH cycles AS (
    SELECT ID_PRET,
        COUNT(*) AS nb_cycles
    FROM dbo.CYCLES_PRET
    GROUP BY ID_PRET
)
SELECT p.ID AS id_pret,
    p.NUMERO_PRET,
    p.NUMERO_CONTRAT,
    p.DATE_DECAISSEMENT,
    p.MONTANT,
    p.ID_DOSSIER_CREDIT,
    d.NUM_DOSSIER,
    p.ID_COMPTE_CREDIT,
    cc.NUM_CPTE AS numero_compte_credit,
    p.ID_COMPTE_EPARGNE,
    ce.NUM_CPTE AS numero_compte_epargne,
    p.ID_DEVISE,
    dv.CODE AS devise_pret,
    ISNULL(cy.nb_cycles, 0) AS nb_cycles,
    CASE
        WHEN p.ID_DOSSIER_CREDIT IS NULL
        OR d.ID IS NULL THEN 1
        ELSE 0
    END AS anomalie_dossier,
    CASE
        WHEN p.ID_COMPTE_CREDIT IS NULL
        OR cc.ID IS NULL THEN 1
        ELSE 0
    END AS anomalie_compte_credit,
    CASE
        WHEN p.ID_COMPTE_EPARGNE IS NULL
        OR ce.ID IS NULL THEN 1
        ELSE 0
    END AS anomalie_compte_epargne,
    CASE
        WHEN ISNULL(cy.nb_cycles, 0) = 0 THEN 1
        ELSE 0
    END AS anomalie_cycle
FROM dbo.PRETS p
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.COMPTES cc ON cc.ID = p.ID_COMPTE_CREDIT
    LEFT JOIN dbo.COMPTES ce ON ce.ID = p.ID_COMPTE_EPARGNE
    LEFT JOIN dbo.DEVISES dv ON dv.ID = p.ID_DEVISE
    LEFT JOIN cycles cy ON cy.ID_PRET = p.ID
WHERE (
        (
            p.DATE_DECAISSEMENT BETWEEN @date_debut AND @date_fin
        )
        OR (
            p.DATE_EFFET BETWEEN @date_debut AND @date_fin
        )
    )
    AND (
        p.ID_DOSSIER_CREDIT IS NULL
        OR d.ID IS NULL
        OR p.ID_COMPTE_CREDIT IS NULL
        OR cc.ID IS NULL
        OR p.ID_COMPTE_EPARGNE IS NULL
        OR ce.ID IS NULL
        OR ISNULL(cy.nb_cycles, 0) = 0
    )
ORDER BY p.DATE_DECAISSEMENT DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 61 BEGIN
SELECT cp.ID AS id_cycle_pret,
    cp.ID_PRET,
    p.NUMERO_PRET,
    p.NUMERO_CONTRAT,
    cp.NUM_CYCLE,
    cp.DATE_DEBUT,
    cp.FIN_ECHEANCE,
    cp.DATE_CLOTURE,
    cp.MONTANT AS montant_cycle,
    p.MONTANT AS montant_pret,
    d.NUM_DOSSIER,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    DATEDIFF(day, cp.FIN_ECHEANCE, @date_fin) AS jours_de_depassement
FROM dbo.CYCLES_PRET cp
    INNER JOIN dbo.PRETS p ON p.ID = cp.ID_PRET
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
WHERE cp.FIN_ECHEANCE IS NOT NULL
    AND cp.FIN_ECHEANCE < @date_fin
    AND cp.DATE_CLOTURE IS NULL
ORDER BY jours_de_depassement DESC,
    cp.FIN_ECHEANCE;
RETURN;
END;
IF @controle_id = 62 BEGIN
SELECT dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    dc.REF_DEMANDE,
    dc.DATE_RECEPTION,
    dc.ETAT_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    dc.MONTANT_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    d.MONTANT_SOLLICITE,
    d.MONTANT_ACCORDE,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    p.MONTANT AS montant_pret,
    ISNULL(d.MONTANT_ACCORDE, 0) - ISNULL(dc.MONTANT_DEMANDE, 0) AS ecart_dossier_vs_demande,
    ISNULL(p.MONTANT, 0) - ISNULL(dc.MONTANT_DEMANDE, 0) AS ecart_pret_vs_demande
FROM dbo.DEMANDES_CREDIT dc
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
ORDER BY ABS(
        ISNULL(p.MONTANT, 0) - ISNULL(dc.MONTANT_DEMANDE, 0)
    ) DESC,
    dc.DATE_RECEPTION DESC;
RETURN;
END;
IF @controle_id = 63 BEGIN
SELECT dc.ID_AGENCE,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence,
    dc.ID_POINT_SERIVCE,
    pss.CODE AS code_point_service_demande,
    pss.NOM AS nom_point_service_demande,
    pc.ID AS id_produit_credit,
    pc.LIBELLE AS produit_credit,
    dv.CODE AS devise_reference,
    dc.ETAT_DEMANDE,
    COUNT(DISTINCT dc.ID) AS nb_demandes,
    COUNT(DISTINCT d.ID) AS nb_dossiers,
    COUNT(DISTINCT p.ID) AS nb_prets,
    SUM(ISNULL(dc.MONTANT_DEMANDE, 0)) AS total_demande,
    SUM(ISNULL(d.MONTANT_ACCORDE, 0)) AS total_accorde_dossier,
    SUM(ISNULL(p.MONTANT, 0)) AS total_pret
FROM dbo.DEMANDES_CREDIT dc
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.DEVISES dv ON dv.ID = COALESCE(p.ID_DEVISE, pc.ID_DEVISE)
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = dc.ID_AGENCE
    LEFT JOIN dbo.POINTS_SERVICE pss ON pss.ID = dc.ID_POINT_SERIVCE
WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
GROUP BY dc.ID_AGENCE,
    ps.CODE,
    ps.NOM,
    dc.ID_POINT_SERIVCE,
    pss.CODE,
    pss.NOM,
    pc.ID,
    pc.LIBELLE,
    dv.CODE,
    dc.ETAT_DEMANDE
ORDER BY total_demande DESC,
    nb_demandes DESC;
RETURN;
END;
IF @controle_id = 64 BEGIN WITH epargne AS (
    SELECT ca.ID_ADHERENT,
        COUNT(*) AS nb_mouvements_epargne,
        SUM(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS volume_epargne,
        MAX(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS plus_gros_mouvement
    FROM dbo.HDPM_VIEW h
        INNER JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
        INNER JOIN dbo.COMPTES_ADHERENT ca ON ca.id = c.ID
    WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
        AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
    GROUP BY ca.ID_ADHERENT
),
credits AS (
    SELECT dc.ID_ADHERENT,
        COUNT(DISTINCT p.ID) AS nb_prets_actifs,
        SUM(ISNULL(p.MONTANT, 0)) AS encours_reference_credit
    FROM dbo.PRETS p
        INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
        INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    WHERE ISNULL(p.DATE_SOLDE, '9999-12-31') > @date_fin
        AND p.DATE_SORTIE IS NULL
        AND p.DATE_PERTE IS NULL
    GROUP BY dc.ID_ADHERENT
)
SELECT a.ID AS id_adherent,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    e.nb_mouvements_epargne,
    e.volume_epargne,
    e.plus_gros_mouvement,
    c.nb_prets_actifs,
    c.encours_reference_credit
FROM epargne e
    INNER JOIN credits c ON c.ID_ADHERENT = e.ID_ADHERENT
    INNER JOIN dbo.ADHERENTS a ON a.ID = e.ID_ADHERENT
WHERE e.volume_epargne >= CASE
        WHEN @seuil_5k_usd_cdf > 0 THEN @seuil_5k_usd_cdf
        ELSE 5000000
    END
ORDER BY e.volume_epargne DESC,
    c.nb_prets_actifs DESC;
RETURN;
END;
IF @controle_id = 65 BEGIN
SELECT dc.ID_ADHERENT,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    DATEFROMPARTS(
        YEAR(dc.DATE_RECEPTION),
        MONTH(dc.DATE_RECEPTION),
        1
    ) AS mois_reception,
    COUNT(*) AS nb_demandes,
    SUM(ISNULL(dc.MONTANT_DEMANDE, 0)) AS montant_total_demande,
    COUNT(DISTINCT dc.ID_PRODUIT_CREDIT) AS nb_produits_demandes
FROM dbo.DEMANDES_CREDIT dc
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
GROUP BY dc.ID_ADHERENT,
    a.CODE,
    a.NOM_ADHERENT,
    DATEFROMPARTS(
        YEAR(dc.DATE_RECEPTION),
        MONTH(dc.DATE_RECEPTION),
        1
    )
HAVING COUNT(*) > 1
ORDER BY nb_demandes DESC,
    montant_total_demande DESC;
RETURN;
END;
IF @controle_id = 66 BEGIN
SELECT 'MOUVEMENTS' AS source_volume,
    h.ID_POINT_SERVICE AS id_agence,
    ps.CODE AS code_agence,
    ps.NOM AS nom_agence,
    COUNT(*) AS nb_elements,
    SUM(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS volume_total
FROM dbo.HDPM_VIEW h
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = h.ID_POINT_SERVICE
WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
GROUP BY h.ID_POINT_SERVICE,
    ps.CODE,
    ps.NOM
UNION ALL
SELECT 'CREDITS' AS source_volume,
    dc.ID_AGENCE,
    ps.CODE,
    ps.NOM,
    COUNT(DISTINCT dc.ID) AS nb_elements,
    SUM(ISNULL(dc.MONTANT_DEMANDE, 0)) AS volume_total
FROM dbo.DEMANDES_CREDIT dc
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = dc.ID_AGENCE
WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
GROUP BY dc.ID_AGENCE,
    ps.CODE,
    ps.NOM
ORDER BY source_volume,
    volume_total DESC;
RETURN;
END;
IF @controle_id = 67 BEGIN
SELECT 'EPARGNE' AS source_produit,
    CAST(pe.ID AS varchar(50)) AS id_produit,
    pe.LIBELLE AS libelle_produit,
    COUNT(DISTINCT c.ID) AS nb_comptes,
    COUNT(h.ID) AS nb_mouvements,
    SUM(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION))) AS volume_total
FROM dbo.PRODUITS_EPG pe
    INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.ID_PRODUIT_EPG = pe.ID
    INNER JOIN dbo.COMPTES c ON c.ID = cai.id
    LEFT JOIN dbo.HDPM_VIEW h ON h.ID_COMPTE = c.ID
    AND h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(h.ID_TYPE_OPERATION, '') <> 'REPR'
GROUP BY pe.ID,
    pe.LIBELLE
UNION ALL
SELECT 'CREDIT' AS source_produit,
    CAST(pc.ID AS varchar(50)) AS id_produit,
    pc.LIBELLE AS libelle_produit,
    COUNT(DISTINCT dc.ID) AS nb_comptes,
    COUNT(DISTINCT dc.ID) AS nb_mouvements,
    SUM(ISNULL(dc.MONTANT_DEMANDE, 0)) AS volume_total
FROM dbo.PRODUITS_CRD pc
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID_PRODUIT_CREDIT = pc.ID
    AND dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
GROUP BY pc.ID,
    pc.LIBELLE
ORDER BY source_produit,
    volume_total DESC;
RETURN;
END;
IF @controle_id = 68 BEGIN WITH produits_inactifs AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.COMPTES c
        INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
        INNER JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    WHERE ISNULL(pe.ACTIF, 0) = 0
),
produits_non_valides AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.COMPTES c
        INNER JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
        INNER JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    WHERE ISNULL(pe.IS_EPG_VALIDE, 0) = 0
),
comptes_sans_produit AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.COMPTES c
        LEFT JOIN dbo.COMPTES_ADHERENT_INFO cai ON cai.id = c.ID
        LEFT JOIN dbo.PRODUITS_EPG pe ON pe.ID = cai.ID_PRODUIT_EPG
    WHERE cai.ID_PRODUIT_EPG IS NULL
        OR pe.ID IS NULL
),
mouvements_non_justifies AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.HDPM_VIEW h
        LEFT JOIN dbo.COMPTES c ON c.ID = h.ID_COMPTE
        LEFT JOIN dbo.OPERATIONS o ON o.ID = h.ID_OPERATION
        LEFT JOIN dbo.OPERATIONS_API oa ON oa.CODE = h.ID_OPERATION
    WHERE h.DATE_OPERATION BETWEEN @date_debut AND @date_fin
        AND (
            NULLIF(LTRIM(RTRIM(ISNULL(h.ID_COMPTE, ''))), '') IS NULL
            OR c.ID IS NULL
            OR NULLIF(LTRIM(RTRIM(ISNULL(h.ID_OPERATION, ''))), '') IS NULL
            OR (
                o.ID IS NULL
                AND oa.CODE IS NULL
            )
        )
),
demandes_sans_pret AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.DEMANDES_CREDIT dc
        LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
        LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
        AND p.ID IS NULL
),
prets_sans_cycle AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.PRETS p
        LEFT JOIN (
            SELECT ID_PRET,
                COUNT(*) AS nb_cycles
            FROM dbo.CYCLES_PRET
            GROUP BY ID_PRET
        ) cy ON cy.ID_PRET = p.ID
    WHERE (
            (
                p.DATE_DECAISSEMENT BETWEEN @date_debut AND @date_fin
            )
            OR (
                p.DATE_EFFET BETWEEN @date_debut AND @date_fin
            )
        )
        AND ISNULL(cy.nb_cycles, 0) = 0
),
cycles_en_retard AS (
    SELECT COUNT(*) AS nb_cas
    FROM dbo.CYCLES_PRET cp
    WHERE cp.FIN_ECHEANCE IS NOT NULL
        AND cp.FIN_ECHEANCE < @date_fin
        AND cp.DATE_CLOTURE IS NULL
)
SELECT 'Epargne' AS domaine,
    'Produits inactifs encore utilises' AS anomalie,
    'Haute' AS priorite,
    nb_cas
FROM produits_inactifs
UNION ALL
SELECT 'Epargne',
    'Produits non valides encore utilises',
    'Haute',
    nb_cas
FROM produits_non_valides
UNION ALL
SELECT 'Epargne',
    'Comptes sans produit ou avec produit introuvable',
    'Haute',
    nb_cas
FROM comptes_sans_produit
UNION ALL
SELECT 'Mouvements',
    'Mouvements sans reference complete',
    'Haute',
    nb_cas
FROM mouvements_non_justifies
UNION ALL
SELECT 'Credit',
    'Demandes sans pret accorde',
    'Moyenne',
    nb_cas
FROM demandes_sans_pret
UNION ALL
SELECT 'Credit',
    'Prets sans cycle',
    'Haute',
    nb_cas
FROM prets_sans_cycle
UNION ALL
SELECT 'Credit',
    'Cycles echus non clotures',
    'Haute',
    nb_cas
FROM cycles_en_retard
ORDER BY nb_cas DESC,
    domaine,
    anomalie;
RETURN;
END;
IF @controle_id = 69 BEGIN WITH validation_stats AS (
    SELECT v.ID_DOSSIER_CREDIT,
        COUNT(*) AS nb_validations,
        SUM(
            CASE
                WHEN ISNULL(v.etatValid, 0) = 1 THEN 1
                ELSE 0
            END
        ) AS nb_validations_favorables,
        MAX(CAST(v.dateValidation AS date)) AS date_derniere_validation,
        MAX(
            CASE
                WHEN ISNULL(v.etatValid, 0) = 1 THEN CAST(v.dateValidation AS date)
                ELSE NULL
            END
        ) AS date_derniere_validation_favorable
    FROM dbo.VALIDATION_DOSSIER_CREDIT v
    GROUP BY v.ID_DOSSIER_CREDIT
),
debloc_stats AS (
    SELECT d.ID_PRET,
        COUNT(*) AS nb_deblocages,
        MIN(d.DATE_DEBLOC) AS date_premier_debloc,
        MAX(d.DATE_DEBLOC) AS date_dernier_debloc
    FROM dbo.DEBLOCAGES d
    GROUP BY d.ID_PRET
)
SELECT p.ID AS id_pret,
    p.NUMERO_PRET,
    p.DATE_DECAISSEMENT,
    ds.date_premier_debloc,
    dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    ISNULL(vs.nb_validations, 0) AS nb_validations,
    ISNULL(vs.nb_validations_favorables, 0) AS nb_validations_favorables,
    vs.date_derniere_validation,
    vs.date_derniere_validation_favorable,
    CASE
        WHEN vs.ID_DOSSIER_CREDIT IS NULL THEN 'Aucune validation de dossier'
        WHEN ISNULL(vs.nb_validations_favorables, 0) = 0 THEN 'Validation favorable absente'
        WHEN vs.date_derniere_validation_favorable > COALESCE(ds.date_premier_debloc, p.DATE_DECAISSEMENT) THEN 'Validation favorable enregistree apres deboursement'
    END AS anomalie_validation
FROM dbo.PRETS p
    INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN validation_stats vs ON vs.ID_DOSSIER_CREDIT = d.ID
    LEFT JOIN debloc_stats ds ON ds.ID_PRET = p.ID
WHERE COALESCE(ds.date_premier_debloc, p.DATE_DECAISSEMENT, p.DATE_EFFET) BETWEEN @date_debut AND @date_fin
    AND (
        vs.ID_DOSSIER_CREDIT IS NULL
        OR ISNULL(vs.nb_validations_favorables, 0) = 0
        OR vs.date_derniere_validation_favorable > COALESCE(ds.date_premier_debloc, p.DATE_DECAISSEMENT)
    )
ORDER BY COALESCE(ds.date_premier_debloc, p.DATE_DECAISSEMENT) DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 70 BEGIN WITH garantie_stats AS (
    SELECT g.ID_DEMANDE_CREDIT,
        COUNT(*) AS nb_garanties,
        SUM(ISNULL(g.VALEUR, 0)) AS valeur_garantie_totale
    FROM dbo.GARANTIES g
    GROUP BY g.ID_DEMANDE_CREDIT
)
SELECT dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    tr.ID AS id_tranche,
    ISNULL(tr.GARANTIE_OBLIGATOIRE, 0) AS garantie_obligatoire,
    tr.SEUIL_MONTANT_GARANTIE,
    CASE
        WHEN ISNULL(tr.TAUX_VALEUR_GARANTIE, 0) = 0 THEN 120.0
        WHEN tr.TAUX_VALEUR_GARANTIE <= 2 THEN tr.TAUX_VALEUR_GARANTIE * 100.0
        ELSE tr.TAUX_VALEUR_GARANTIE
    END AS taux_garantie_attendu_pct,
    COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) AS montant_reference,
    ISNULL(gs.nb_garanties, 0) AS nb_garanties,
    ISNULL(gs.valeur_garantie_totale, 0) AS valeur_garantie_totale,
    COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
        CASE
            WHEN ISNULL(tr.TAUX_VALEUR_GARANTIE, 0) = 0 THEN 1.20
            WHEN tr.TAUX_VALEUR_GARANTIE <= 2 THEN tr.TAUX_VALEUR_GARANTIE
            ELSE tr.TAUX_VALEUR_GARANTIE / 100.0
        END
    ) AS valeur_garantie_attendue,
    ISNULL(gs.valeur_garantie_totale, 0) - COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
        CASE
            WHEN ISNULL(tr.TAUX_VALEUR_GARANTIE, 0) = 0 THEN 1.20
            WHEN tr.TAUX_VALEUR_GARANTIE <= 2 THEN tr.TAUX_VALEUR_GARANTIE
            ELSE tr.TAUX_VALEUR_GARANTIE / 100.0
        END
    ) AS ecart_valeur_garantie
FROM dbo.DEMANDES_CREDIT dc
    INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.PRODUITS_CRD_TRANCHE tr ON tr.ID = d.ID_PRDT_CRD_TRANCHE
    LEFT JOIN garantie_stats gs ON gs.ID_DEMANDE_CREDIT = dc.ID
WHERE COALESCE(p.DATE_DECAISSEMENT, d.DATE_DECISION, dc.DATE_RECEPTION) BETWEEN @date_debut AND @date_fin
    AND (
        ISNULL(tr.GARANTIE_OBLIGATOIRE, 0) = 1
        OR (
            ISNULL(tr.SEUIL_MONTANT_GARANTIE, 0) > 0
            AND COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) >= tr.SEUIL_MONTANT_GARANTIE
        )
    )
    AND ISNULL(gs.valeur_garantie_totale, 0) < COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
        CASE
            WHEN ISNULL(tr.TAUX_VALEUR_GARANTIE, 0) = 0 THEN 1.20
            WHEN tr.TAUX_VALEUR_GARANTIE <= 2 THEN tr.TAUX_VALEUR_GARANTIE
            ELSE tr.TAUX_VALEUR_GARANTIE / 100.0
        END
    )
ORDER BY ecart_valeur_garantie,
    COALESCE(p.MONTANT, d.MONTANT_ACCORDE, dc.MONTANT_DEMANDE, 0) DESC;
RETURN;
END;
IF @controle_id = 71 BEGIN WITH caution_base AS (
    SELECT c.ID_PRET,
        COUNT(*) AS nb_cautions,
        SUM(ISNULL(c.MONTANT_CAUTION, 0)) AS montant_caution_table
    FROM dbo.CAUTIONS c
    GROUP BY c.ID_PRET
),
caution_compte AS (
    SELECT c.ID_PRET,
        SUM(ISNULL(cfc.MONTANT, 0)) AS montant_caution_compte
    FROM dbo.CAUTIONS c
        INNER JOIN dbo.CAUTIONS_FINANCIERE_COMPTE cfc ON cfc.ID_CAUTION_FIN = c.ID
    GROUP BY c.ID_PRET
)
SELECT p.ID AS id_pret,
    p.NUMERO_PRET,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    tr.ID AS id_tranche,
    ISNULL(tr.CAUTION_FINANCIERE, 0) AS caution_financiere_obligatoire,
    CASE
        WHEN ISNULL(d.TAUX_CAUTION, 0) > 0 THEN d.TAUX_CAUTION
        WHEN ISNULL(tr.TAUX_CAUTION_MIN, 0) > 0 AND tr.TAUX_CAUTION_MIN <= 1 THEN tr.TAUX_CAUTION_MIN * 100.0
        ELSE ISNULL(tr.TAUX_CAUTION_MIN, 0)
    END AS taux_caution_attendu_pct,
    d.MNT_EPG_OBLIGATOIRE,
    COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) AS montant_reference,
    ISNULL(cb.nb_cautions, 0) AS nb_cautions,
    CASE
        WHEN ISNULL(cc.montant_caution_compte, 0) > ISNULL(cb.montant_caution_table, 0) THEN ISNULL(cc.montant_caution_compte, 0)
        ELSE ISNULL(cb.montant_caution_table, 0)
    END AS montant_caution_constate,
    CASE
        WHEN ISNULL(d.MNT_EPG_OBLIGATOIRE, 0) > COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
            CASE
                WHEN ISNULL(d.TAUX_CAUTION, 0) > 0 THEN d.TAUX_CAUTION / 100.0
                WHEN ISNULL(tr.TAUX_CAUTION_MIN, 0) > 0 AND tr.TAUX_CAUTION_MIN <= 1 THEN tr.TAUX_CAUTION_MIN
                ELSE ISNULL(tr.TAUX_CAUTION_MIN, 0) / 100.0
            END
        ) THEN ISNULL(d.MNT_EPG_OBLIGATOIRE, 0)
        ELSE COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
            CASE
                WHEN ISNULL(d.TAUX_CAUTION, 0) > 0 THEN d.TAUX_CAUTION / 100.0
                WHEN ISNULL(tr.TAUX_CAUTION_MIN, 0) > 0 AND tr.TAUX_CAUTION_MIN <= 1 THEN tr.TAUX_CAUTION_MIN
                ELSE ISNULL(tr.TAUX_CAUTION_MIN, 0) / 100.0
            END
        )
    END AS caution_attendue
FROM dbo.PRETS p
    INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.PRODUITS_CRD_TRANCHE tr ON tr.ID = d.ID_PRDT_CRD_TRANCHE
    LEFT JOIN caution_base cb ON cb.ID_PRET = p.ID
    LEFT JOIN caution_compte cc ON cc.ID_PRET = p.ID
WHERE COALESCE(p.DATE_DECAISSEMENT, d.DATE_DECISION, dc.DATE_RECEPTION) BETWEEN @date_debut AND @date_fin
    AND (
        ISNULL(tr.CAUTION_FINANCIERE, 0) = 1
        OR ISNULL(d.MNT_EPG_OBLIGATOIRE, 0) > 0
        OR ISNULL(d.TAUX_CAUTION, 0) > 0
        OR ISNULL(tr.TAUX_CAUTION_MIN, 0) > 0
    )
    AND (
        CASE
            WHEN ISNULL(cc.montant_caution_compte, 0) > ISNULL(cb.montant_caution_table, 0) THEN ISNULL(cc.montant_caution_compte, 0)
            ELSE ISNULL(cb.montant_caution_table, 0)
        END
    ) < CASE
        WHEN ISNULL(d.MNT_EPG_OBLIGATOIRE, 0) > COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
            CASE
                WHEN ISNULL(d.TAUX_CAUTION, 0) > 0 THEN d.TAUX_CAUTION / 100.0
                WHEN ISNULL(tr.TAUX_CAUTION_MIN, 0) > 0 AND tr.TAUX_CAUTION_MIN <= 1 THEN tr.TAUX_CAUTION_MIN
                ELSE ISNULL(tr.TAUX_CAUTION_MIN, 0) / 100.0
            END
        ) THEN ISNULL(d.MNT_EPG_OBLIGATOIRE, 0)
        ELSE COALESCE(p.MONTANT, d.MONTANT_ACCORDE, d.MONTANT_SOLLICITE, dc.MONTANT_DEMANDE, 0) * (
            CASE
                WHEN ISNULL(d.TAUX_CAUTION, 0) > 0 THEN d.TAUX_CAUTION / 100.0
                WHEN ISNULL(tr.TAUX_CAUTION_MIN, 0) > 0 AND tr.TAUX_CAUTION_MIN <= 1 THEN tr.TAUX_CAUTION_MIN
                ELSE ISNULL(tr.TAUX_CAUTION_MIN, 0) / 100.0
            END
        )
    END
ORDER BY p.DATE_DECAISSEMENT DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 72 BEGIN
SELECT g.ID AS id_garantie,
    g.ID_DEMANDE_CREDIT AS id_demande,
    dc.NUM_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    g.DESCRIPTION AS description_garantie,
    g.VALEUR,
    g.ID_GARANT,
    gr.NOM_GARANT,
    gr.NOM,
    gr.NUMERO_PIECE,
    gr.NUM_REGISTRE,
    CASE
        WHEN g.ID_GARANT IS NULL THEN 'Garant non renseigne'
        WHEN gr.ID IS NULL THEN 'Fiche garant introuvable'
        WHEN NULLIF(LTRIM(RTRIM(ISNULL(gr.NOM_GARANT, gr.NOM))), '') IS NULL THEN 'Nom du garant manquant'
        WHEN NULLIF(LTRIM(RTRIM(ISNULL(gr.NUMERO_PIECE, ''))), '') IS NULL
            AND NULLIF(LTRIM(RTRIM(ISNULL(gr.NUM_REGISTRE, ''))), '') IS NULL THEN 'Piece ou registre du garant manquant'
        ELSE 'Garant a revoir'
    END AS anomalie_garant
FROM dbo.GARANTIES g
    INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = g.ID_DEMANDE_CREDIT
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.GARANTS gr ON gr.ID = g.ID_GARANT
WHERE COALESCE(p.DATE_DECAISSEMENT, d.DATE_DECISION, dc.DATE_RECEPTION) BETWEEN @date_debut AND @date_fin
    AND (
        g.ID_GARANT IS NULL
        OR gr.ID IS NULL
        OR NULLIF(LTRIM(RTRIM(ISNULL(gr.NOM_GARANT, gr.NOM))), '') IS NULL
        OR (
            NULLIF(LTRIM(RTRIM(ISNULL(gr.NUMERO_PIECE, ''))), '') IS NULL
            AND NULLIF(LTRIM(RTRIM(ISNULL(gr.NUM_REGISTRE, ''))), '') IS NULL
        )
    )
ORDER BY COALESCE(p.DATE_DECAISSEMENT, d.DATE_DECISION, dc.DATE_RECEPTION) DESC,
    g.VALEUR DESC;
RETURN;
END;
IF @controle_id = 73 BEGIN
SELECT dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    tr.ID AS id_tranche,
    ISNULL(tr.ANALYSE_OBLIGATOIRE, 0) AS analyse_revenu_obligatoire,
    ISNULL(tr.ANALYSE_PROJET_OBLIGATOIRE, 0) AS analyse_projet_obligatoire,
    ar.ID AS id_analyse_revenu,
    ar.REVENU_NET,
    ar.AVIS AS avis_analyse_revenu,
    ap.ID AS id_analyse_projet,
    ap.PRODUIT_RECETTE,
    ap.ACTIF,
    ap.PASSIF,
    ap.AVIS AS avis_analyse_projet,
    CASE
        WHEN ISNULL(tr.ANALYSE_OBLIGATOIRE, 0) = 1
            AND (
                ar.ID IS NULL
                OR ar.REVENU_NET IS NULL
            )
            AND ISNULL(tr.ANALYSE_PROJET_OBLIGATOIRE, 0) = 1
            AND (
                ap.ID IS NULL
                OR ap.PRODUIT_RECETTE IS NULL
            ) THEN 'Analyse revenu et projet a completer'
        WHEN ISNULL(tr.ANALYSE_OBLIGATOIRE, 0) = 1
            AND (
                ar.ID IS NULL
                OR ar.REVENU_NET IS NULL
            ) THEN 'Analyse de revenu a completer'
        WHEN ISNULL(tr.ANALYSE_PROJET_OBLIGATOIRE, 0) = 1
            AND (
                ap.ID IS NULL
                OR ap.PRODUIT_RECETTE IS NULL
            ) THEN 'Analyse de projet a completer'
    END AS anomalie_analyse
FROM dbo.DEMANDES_CREDIT dc
    INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
    LEFT JOIN dbo.PRODUITS_CRD_TRANCHE tr ON tr.ID = d.ID_PRDT_CRD_TRANCHE
    LEFT JOIN dbo.CREDIT_ANALYSE_REVENU ar ON ar.ID_DEMANDE_CREDIT = dc.ID
    LEFT JOIN dbo.CREDIT_ANALYSE_PROJET ap ON ap.ID_DEMANDE_CREDIT = dc.ID
WHERE COALESCE(p.DATE_DECAISSEMENT, d.DATE_DECISION, dc.DATE_RECEPTION) BETWEEN @date_debut AND @date_fin
    AND (
        (
            ISNULL(tr.ANALYSE_OBLIGATOIRE, 0) = 1
            AND (
                ar.ID IS NULL
                OR ar.REVENU_NET IS NULL
            )
        )
        OR (
            ISNULL(tr.ANALYSE_PROJET_OBLIGATOIRE, 0) = 1
            AND (
                ap.ID IS NULL
                OR ap.PRODUIT_RECETTE IS NULL
            )
        )
    )
ORDER BY COALESCE(p.DATE_DECAISSEMENT, d.DATE_DECISION, dc.DATE_RECEPTION) DESC,
    dc.MONTANT_DEMANDE DESC;
RETURN;
END;
IF @controle_id = 74 BEGIN WITH debloc_stats AS (
    SELECT d.ID_PRET,
        COUNT(*) AS nb_deblocages,
        SUM(ISNULL(d.MONTANT_TIRE, 0)) AS montant_total_tire,
        MIN(d.DATE_DEBLOC) AS date_premier_debloc,
        MAX(d.DATE_DEBLOC) AS date_dernier_debloc,
        SUM(
            CASE
                WHEN NULLIF(LTRIM(RTRIM(ISNULL(d.ID_OPERATION, ''))), '') IS NULL THEN 1
                ELSE 0
            END
        ) AS nb_deblocages_sans_operation
    FROM dbo.DEBLOCAGES d
    GROUP BY d.ID_PRET
)
SELECT p.ID AS id_pret,
    p.NUMERO_PRET,
    p.DATE_DECAISSEMENT,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    d.DATE_DECISION,
    dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    p.MONTANT AS montant_pret,
    ISNULL(ds.nb_deblocages, 0) AS nb_deblocages,
    ISNULL(ds.montant_total_tire, 0) AS montant_total_tire,
    ds.date_premier_debloc,
    ds.date_dernier_debloc,
    ISNULL(ds.nb_deblocages_sans_operation, 0) AS nb_deblocages_sans_operation,
    CASE
        WHEN ds.ID_PRET IS NULL THEN 'Aucun deblocage rattache'
        WHEN ISNULL(ds.nb_deblocages_sans_operation, 0) > 0 THEN 'Deblocage sans operation de support'
        WHEN ISNULL(ds.montant_total_tire, 0) <= 0 THEN 'Montant deblocage nul ou negatif'
        WHEN ABS(ISNULL(ds.montant_total_tire, 0) - ISNULL(p.MONTANT, 0)) > 1 THEN 'Ecart entre montant tire et montant du pret'
        WHEN d.DATE_DECISION IS NOT NULL
            AND ds.date_premier_debloc < d.DATE_DECISION THEN 'Deblocage avant decision'
    END AS anomalie_deblocage
FROM dbo.PRETS p
    INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN debloc_stats ds ON ds.ID_PRET = p.ID
WHERE COALESCE(ds.date_premier_debloc, p.DATE_DECAISSEMENT, p.DATE_EFFET) BETWEEN @date_debut AND @date_fin
    AND (
        ds.ID_PRET IS NULL
        OR ISNULL(ds.nb_deblocages_sans_operation, 0) > 0
        OR ISNULL(ds.montant_total_tire, 0) <= 0
        OR ABS(ISNULL(ds.montant_total_tire, 0) - ISNULL(p.MONTANT, 0)) > 1
        OR (
            d.DATE_DECISION IS NOT NULL
            AND ds.date_premier_debloc < d.DATE_DECISION
        )
    )
ORDER BY COALESCE(ds.date_premier_debloc, p.DATE_DECAISSEMENT) DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 75 BEGIN
SELECT dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    dc.REF_DEMANDE,
    dc.DATE_RECEPTION,
    dc.NBRE_BENEFICIAIRE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    pc.LIBELLE AS produit_credit,
    pc.CREDIT_GROUPE,
    CASE
        WHEN dc.NBRE_BENEFICIAIRE IS NULL THEN 'Nombre de beneficiaires absent'
        WHEN dc.NBRE_BENEFICIAIRE < 5 THEN 'Groupe inferieur au minimum recommande'
        WHEN dc.NBRE_BENEFICIAIRE > 10 THEN 'Groupe superieur au maximum recommande'
    END AS anomalie_groupe
FROM dbo.DEMANDES_CREDIT dc
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.PRODUITS_CRD pc ON pc.ID = dc.ID_PRODUIT_CREDIT
WHERE dc.DATE_RECEPTION BETWEEN @date_debut AND @date_fin
    AND (
        NULLIF(LTRIM(RTRIM(ISNULL(pc.CREDIT_GROUPE, ''))), '') IS NOT NULL
        OR ISNULL(dc.NBRE_BENEFICIAIRE, 0) > 1
        OR UPPER(ISNULL(pc.LIBELLE, '')) LIKE '%LIKELEMBA%'
    )
    AND (
        dc.NBRE_BENEFICIAIRE IS NULL
        OR dc.NBRE_BENEFICIAIRE < 5
        OR dc.NBRE_BENEFICIAIRE > 10
    )
ORDER BY dc.DATE_RECEPTION DESC,
    dc.MONTANT_DEMANDE DESC;
RETURN;
END;
IF @controle_id = 76 BEGIN WITH actifs AS (
    SELECT dc.ID_ADHERENT,
        dc.ID_PRODUIT_CREDIT,
        COUNT(DISTINCT p.ID) AS nb_prets_actifs,
        SUM(ISNULL(p.MONTANT, 0)) AS encours_total
    FROM dbo.PRETS p
        INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
        INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    WHERE COALESCE(p.DATE_DECAISSEMENT, p.DATE_EFFET) <= @date_fin
        AND ISNULL(p.DATE_SOLDE, '9999-12-31') > @date_fin
        AND p.DATE_SORTIE IS NULL
        AND p.DATE_PERTE IS NULL
    GROUP BY dc.ID_ADHERENT,
        dc.ID_PRODUIT_CREDIT
)
SELECT a.ID_ADHERENT,
    adh.CODE AS code_adherent,
    adh.NOM_ADHERENT,
    a.ID_PRODUIT_CREDIT,
    pc.LIBELLE AS produit_credit,
    pc.NBRE_MAX_DOSSIER_CLIENT AS limite_produit,
    a.nb_prets_actifs,
    a.encours_total
FROM actifs a
    INNER JOIN dbo.ADHERENTS adh ON adh.ID = a.ID_ADHERENT
    INNER JOIN dbo.PRODUITS_CRD pc ON pc.ID = a.ID_PRODUIT_CREDIT
WHERE ISNULL(pc.NBRE_MAX_DOSSIER_CLIENT, 0) > 0
    AND a.nb_prets_actifs > pc.NBRE_MAX_DOSSIER_CLIENT
ORDER BY a.nb_prets_actifs DESC,
    a.encours_total DESC;
RETURN;
END;
IF @controle_id = 77 BEGIN WITH retraits_garantie AS (
    SELECT g.ID_DEMANDE_CREDIT,
        MIN(
            COALESCE(or1.DATE_OPERATION, oa1.DATE_OPERATION)
        ) AS date_premier_retrait_garantie,
        COUNT(*) AS nb_retraits_garantie
    FROM dbo.GARANTIES g
        LEFT JOIN dbo.OPERATIONS or1 ON or1.ID = g.ID_OPERATION_RETRAIT
        LEFT JOIN dbo.OPERATIONS_API oa1 ON oa1.CODE = g.ID_OPERATION_RETRAIT
    WHERE NULLIF(LTRIM(RTRIM(ISNULL(g.ID_OPERATION_RETRAIT, ''))), '') IS NOT NULL
    GROUP BY g.ID_DEMANDE_CREDIT
    UNION ALL
    SELECT g.ID_DEMANDE_CREDIT,
        MIN(
            COALESCE(or2.DATE_OPERATION, oa2.DATE_OPERATION)
        ) AS date_premier_retrait_garantie,
        COUNT(*) AS nb_retraits_garantie
    FROM dbo.GARANTIES g
        INNER JOIN dbo.GARANTIES_DETAIL gd ON gd.ID_GARANTIE = g.ID
        LEFT JOIN dbo.OPERATIONS or2 ON or2.ID = gd.id_operation_retrait
        LEFT JOIN dbo.OPERATIONS_API oa2 ON oa2.CODE = gd.id_operation_retrait
    WHERE NULLIF(LTRIM(RTRIM(ISNULL(gd.id_operation_retrait, ''))), '') IS NOT NULL
    GROUP BY g.ID_DEMANDE_CREDIT
),
retraits_agreges AS (
    SELECT rg.ID_DEMANDE_CREDIT,
        MIN(rg.date_premier_retrait_garantie) AS date_premier_retrait_garantie,
        SUM(rg.nb_retraits_garantie) AS nb_retraits_garantie
    FROM retraits_garantie rg
    GROUP BY rg.ID_DEMANDE_CREDIT
)
SELECT dc.ID AS id_demande,
    dc.NUM_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    p.DATE_DECAISSEMENT,
    p.DATE_SOLDE,
    ra.date_premier_retrait_garantie,
    ra.nb_retraits_garantie,
    CASE
        WHEN p.DATE_SOLDE IS NULL THEN 'Retrait de garantie observe avant solde du pret'
        WHEN ra.date_premier_retrait_garantie < p.DATE_SOLDE THEN 'Retrait de garantie avant la date de solde'
    END AS anomalie_retrait_garantie
FROM dbo.DEMANDES_CREDIT dc
    INNER JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    INNER JOIN dbo.PRETS p ON p.ID_DOSSIER_CREDIT = d.ID
    INNER JOIN retraits_agreges ra ON ra.ID_DEMANDE_CREDIT = dc.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
WHERE COALESCE(ra.date_premier_retrait_garantie, p.DATE_DECAISSEMENT) BETWEEN @date_debut AND @date_fin
    AND (
        p.DATE_SOLDE IS NULL
        OR ra.date_premier_retrait_garantie < p.DATE_SOLDE
    )
ORDER BY ra.date_premier_retrait_garantie DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 78 BEGIN
SELECT dr.ID AS id_demande_reechelonnement,
    dr.DATE_VALIDATION,
    dr.NBRE_ECHEANCE_CONSERVEES,
    dr.NBRE_ECHEANCE_NLLES,
    dr.NBRE_PERIODE_DIFFERE,
    dr.NBRE_PERIODE_GRACE,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    p.DATE_DECAISSEMENT,
    p.DATE_REECH,
    p.DATE_SOLDE,
    p.DATE_SORTIE,
    p.DATE_PERTE,
    d.NUM_DOSSIER,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    CASE
        WHEN dr.DATE_VALIDATION IS NULL THEN 'Validation de reechelonnement absente'
        WHEN p.DATE_SOLDE IS NOT NULL
            AND dr.DATE_VALIDATION >= p.DATE_SOLDE THEN 'Reechelonnement enregistre sur un pret deja solde'
        WHEN p.DATE_SORTIE IS NOT NULL
            AND dr.DATE_VALIDATION >= p.DATE_SORTIE THEN 'Reechelonnement enregistre sur un pret deja sorti'
        WHEN p.DATE_PERTE IS NOT NULL
            AND dr.DATE_VALIDATION >= p.DATE_PERTE THEN 'Reechelonnement enregistre sur un pret deja passe en perte'
        WHEN dr.NBRE_ECHEANCE_NLLES IS NULL
            AND dr.NBRE_PERIODE_DIFFERE IS NULL
            AND dr.NBRE_PERIODE_GRACE IS NULL THEN 'Parametres du reechelonnement insuffisants'
    END AS anomalie_reechelonnement
FROM dbo.DEMANDES_REECHELONNEMENT dr
    INNER JOIN dbo.PRETS p ON p.ID = dr.ID_PRET
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
WHERE COALESCE(dr.DATE_VALIDATION, p.DATE_REECH, p.DATE_LAST_MODIFIED, p.DATE_DECAISSEMENT) BETWEEN @date_debut AND @date_fin
    AND (
        dr.DATE_VALIDATION IS NULL
        OR (
            p.DATE_SOLDE IS NOT NULL
            AND dr.DATE_VALIDATION >= p.DATE_SOLDE
        )
        OR (
            p.DATE_SORTIE IS NOT NULL
            AND dr.DATE_VALIDATION >= p.DATE_SORTIE
        )
        OR (
            p.DATE_PERTE IS NOT NULL
            AND dr.DATE_VALIDATION >= p.DATE_PERTE
        )
        OR (
            dr.NBRE_ECHEANCE_NLLES IS NULL
            AND dr.NBRE_PERIODE_DIFFERE IS NULL
            AND dr.NBRE_PERIODE_GRACE IS NULL
        )
    )
ORDER BY COALESCE(dr.DATE_VALIDATION, p.DATE_REECH, p.DATE_LAST_MODIFIED) DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 79 BEGIN WITH reech AS (
    SELECT dr.ID_PRET,
        COUNT(*) AS nb_demandes_reechelonnement,
        MAX(dr.DATE_VALIDATION) AS date_derniere_validation_reechelonnement
    FROM dbo.DEMANDES_REECHELONNEMENT dr
    GROUP BY dr.ID_PRET
)
SELECT p.ID AS id_pret,
    p.NUMERO_PRET,
    p.DATE_DECAISSEMENT,
    p.DATE_REECH,
    p.DATE_LAST_MODIFIED,
    d.NUM_DOSSIER,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    ISNULL(r.nb_demandes_reechelonnement, 0) AS nb_demandes_reechelonnement,
    r.date_derniere_validation_reechelonnement
FROM dbo.PRETS p
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN reech r ON r.ID_PRET = p.ID
WHERE COALESCE(p.DATE_REECH, p.DATE_LAST_MODIFIED) BETWEEN @date_debut AND @date_fin
    AND p.DATE_REECH IS NOT NULL
    AND ISNULL(r.nb_demandes_reechelonnement, 0) = 0
ORDER BY p.DATE_REECH DESC,
    p.MONTANT DESC;
RETURN;
END;
IF @controle_id = 80 BEGIN
SELECT pcx.ID AS id_pret_contentieux,
    pcx.DATE_TRANSFERT,
    pcx.MONTANT_CONTENTIEUX,
    pcx.MONTANT_CREDIT,
    pcx.MONTANT_PERTE,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    p.DATE_DECAISSEMENT,
    p.DATE_SOLDE,
    p.DATE_SORTIE,
    p.DATE_PERTE,
    d.NUM_DOSSIER,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    CASE
        WHEN pcx.DATE_TRANSFERT IS NULL THEN 'Date de transfert en contentieux absente'
        WHEN pcx.DATE_TRANSFERT < p.DATE_DECAISSEMENT THEN 'Transfert en contentieux anterieur au decaissement'
        WHEN ISNULL(pcx.MONTANT_CONTENTIEUX, 0) <= 0 THEN 'Montant contentieux nul ou negatif'
        WHEN ISNULL(pcx.MONTANT_CREDIT, 0) > 0
            AND ISNULL(pcx.MONTANT_CONTENTIEUX, 0) > ISNULL(pcx.MONTANT_CREDIT, 0) THEN 'Montant contentieux superieur au montant credit'
        WHEN p.DATE_SOLDE IS NOT NULL
            AND pcx.DATE_TRANSFERT > p.DATE_SOLDE THEN 'Transfert en contentieux apres solde du pret'
    END AS anomalie_contentieux
FROM dbo.PRETS_CONTENTIEUX pcx
    INNER JOIN dbo.PRETS p ON p.ID = pcx.ID_PRET
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
WHERE COALESCE(pcx.DATE_TRANSFERT, p.DATE_PERTE, p.DATE_SORTIE, p.DATE_LAST_MODIFIED) BETWEEN @date_debut AND @date_fin
    AND (
        pcx.DATE_TRANSFERT IS NULL
        OR pcx.DATE_TRANSFERT < p.DATE_DECAISSEMENT
        OR ISNULL(pcx.MONTANT_CONTENTIEUX, 0) <= 0
        OR (
            ISNULL(pcx.MONTANT_CREDIT, 0) > 0
            AND ISNULL(pcx.MONTANT_CONTENTIEUX, 0) > ISNULL(pcx.MONTANT_CREDIT, 0)
        )
        OR (
            p.DATE_SOLDE IS NOT NULL
            AND pcx.DATE_TRANSFERT > p.DATE_SOLDE
        )
    )
ORDER BY COALESCE(pcx.DATE_TRANSFERT, p.DATE_PERTE, p.DATE_SORTIE) DESC,
    ISNULL(pcx.MONTANT_CONTENTIEUX, 0) DESC;
RETURN;
END;
IF @controle_id = 81 BEGIN
SELECT v.id AS id_validation,
    v.TYPE_VALIDATION,
    v.dateValidation,
    v.etatValid,
    v.mntAccorde,
    v.mntValide,
    v.nbEchAccorde,
    v.nbEchValide,
    v.differeAccorde,
    v.differeValide,
    v.graceAccorde,
    v.graceValide,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    d.MONTANT_ACCORDE,
    d.NBRE_ECHEANCE,
    d.NBRE_DIFFERE,
    d.PERIODE_GRACE,
    p.ID AS id_pret,
    p.NUMERO_PRET,
    p.MONTANT AS montant_pret,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    CASE
        WHEN ISNULL(v.etatValid, 0) = 1
            AND v.mntValide IS NULL THEN 'Validation favorable sans montant valide'
        WHEN v.mntValide IS NOT NULL
            AND d.MONTANT_ACCORDE IS NOT NULL
            AND ABS(v.mntValide - d.MONTANT_ACCORDE) > 1 THEN 'Montant valide different du montant accorde dossier'
        WHEN v.mntValide IS NOT NULL
            AND p.MONTANT IS NOT NULL
            AND ABS(v.mntValide - p.MONTANT) > 1 THEN 'Montant valide different du montant du pret'
        WHEN v.nbEchValide IS NOT NULL
            AND d.NBRE_ECHEANCE IS NOT NULL
            AND v.nbEchValide <> d.NBRE_ECHEANCE THEN 'Nombre d''echeances valide different du dossier'
        WHEN v.differeValide IS NOT NULL
            AND d.NBRE_DIFFERE IS NOT NULL
            AND v.differeValide <> d.NBRE_DIFFERE THEN 'Differe valide different du dossier'
        WHEN v.graceValide IS NOT NULL
            AND d.PERIODE_GRACE IS NOT NULL
            AND v.graceValide <> d.PERIODE_GRACE THEN 'Periode de grace validee differente du dossier'
    END AS anomalie_validation_detail
FROM dbo.VALIDATION_DOSSIER_CREDIT v
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = v.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.PRETS p ON p.ID = v.ID_PRET
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = COALESCE(v.ID_DEMANDE_CREDIT, d.ID_DEMANDE)
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
WHERE CAST(v.dateValidation AS date) BETWEEN @date_debut AND @date_fin
    AND (
        (
            ISNULL(v.etatValid, 0) = 1
            AND v.mntValide IS NULL
        )
        OR (
            v.mntValide IS NOT NULL
            AND d.MONTANT_ACCORDE IS NOT NULL
            AND ABS(v.mntValide - d.MONTANT_ACCORDE) > 1
        )
        OR (
            v.mntValide IS NOT NULL
            AND p.MONTANT IS NOT NULL
            AND ABS(v.mntValide - p.MONTANT) > 1
        )
        OR (
            v.nbEchValide IS NOT NULL
            AND d.NBRE_ECHEANCE IS NOT NULL
            AND v.nbEchValide <> d.NBRE_ECHEANCE
        )
        OR (
            v.differeValide IS NOT NULL
            AND d.NBRE_DIFFERE IS NOT NULL
            AND v.differeValide <> d.NBRE_DIFFERE
        )
        OR (
            v.graceValide IS NOT NULL
            AND d.PERIODE_GRACE IS NOT NULL
            AND v.graceValide <> d.PERIODE_GRACE
        )
    )
ORDER BY v.dateValidation DESC,
    dc.NUM_DEMANDE;
RETURN;
END;
IF @controle_id = 82 BEGIN
SELECT g.ID AS id_garantie,
    g.ID_DEMANDE_CREDIT AS id_demande,
    dc.NUM_DEMANDE,
    d.ID AS id_dossier_credit,
    d.NUM_DOSSIER,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    dc.ID_POINT_SERIVCE AS id_point_service,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    tg.ID AS id_type_garantie,
    tg.LIBELLE AS type_garantie,
    dv.CODE AS devise_garantie,
    g.VALEUR,
    tga.ID AS id_parametrage_agence
FROM dbo.GARANTIES g
    INNER JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = g.ID_DEMANDE_CREDIT
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID_DEMANDE = dc.ID
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN dbo.POINTS_SERVICE ps ON ps.ID = dc.ID_POINT_SERIVCE
    LEFT JOIN dbo.TYPES_GARANTIE tg ON tg.ID = g.ID_TYPE_GARANTIE
    LEFT JOIN dbo.DEVISES dv ON dv.ID = g.ID_DEVISE
    LEFT JOIN dbo.TYPES_GARANTIE_AGENCE tga ON tga.ID_POINT_SERVICE = dc.ID_POINT_SERIVCE
        AND tga.ID_TYPE_GARANTIE = g.ID_TYPE_GARANTIE
        AND (
            tga.ID_DEVISE = g.ID_DEVISE
            OR g.ID_DEVISE IS NULL
        )
WHERE COALESCE(d.DATE_DECISION, dc.DATE_RECEPTION) BETWEEN @date_debut AND @date_fin
    AND g.ID_TYPE_GARANTIE IS NOT NULL
    AND tga.ID IS NULL
ORDER BY COALESCE(d.DATE_DECISION, dc.DATE_RECEPTION) DESC,
    g.VALEUR DESC;
RETURN;
END;
IF @controle_id = 83 BEGIN WITH tabamor_stats AS (
    SELECT t.ID_CYCLE_PRET,
        COUNT(*) AS nb_lignes_tabamor,
        MIN(t.DATE_ECHEANCE) AS date_premiere_echeance,
        MAX(t.DATE_ECHEANCE) AS date_derniere_echeance,
        SUM(ISNULL(t.CAPITAL, 0) + ISNULL(t.INTERET, 0) + ISNULL(t.COMMISSION, 0)) AS montant_total_planifie
    FROM dbo.TABAMOR t
    GROUP BY t.ID_CYCLE_PRET
)
SELECT cp.ID AS id_cycle_pret,
    cp.ID_PRET,
    p.NUMERO_PRET,
    cp.NUM_CYCLE,
    cp.DATE_DEBUT,
    cp.FIN_ECHEANCE,
    cp.DATE_CLOTURE,
    cp.MONTANT AS montant_cycle,
    d.NUM_DOSSIER,
    dc.NUM_DEMANDE,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    ISNULL(ts.nb_lignes_tabamor, 0) AS nb_lignes_tabamor,
    ts.date_premiere_echeance,
    ts.date_derniere_echeance,
    ts.montant_total_planifie,
    CASE
        WHEN ts.ID_CYCLE_PRET IS NULL THEN 'Aucune ligne TABAMOR'
        WHEN ISNULL(ts.nb_lignes_tabamor, 0) = 0 THEN 'Echeancier vide'
        WHEN ts.date_premiere_echeance IS NULL THEN 'Premiere echeance absente'
        WHEN ts.date_derniere_echeance IS NULL THEN 'Derniere echeance absente'
    END AS anomalie_echeancier
FROM dbo.CYCLES_PRET cp
    INNER JOIN dbo.PRETS p ON p.ID = cp.ID_PRET
    LEFT JOIN dbo.DOSSIERS_CREDIT d ON d.ID = p.ID_DOSSIER_CREDIT
    LEFT JOIN dbo.DEMANDES_CREDIT dc ON dc.ID = d.ID_DEMANDE
    LEFT JOIN dbo.ADHERENTS a ON a.ID = dc.ID_ADHERENT
    LEFT JOIN tabamor_stats ts ON ts.ID_CYCLE_PRET = cp.ID
WHERE COALESCE(p.DATE_DECAISSEMENT, cp.DATE_DEBUT, p.DATE_EFFET) BETWEEN @date_debut AND @date_fin
    AND (
        ts.ID_CYCLE_PRET IS NULL
        OR ISNULL(ts.nb_lignes_tabamor, 0) = 0
        OR ts.date_premiere_echeance IS NULL
        OR ts.date_derniere_echeance IS NULL
    )
ORDER BY COALESCE(p.DATE_DECAISSEMENT, cp.DATE_DEBUT) DESC,
    cp.MONTANT DESC;
RETURN;
END;
RAISERROR(
    'Controle inconnu. Utiliser un @controle_id entre 1 et 83.',
    16,
    1
);
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
     */
