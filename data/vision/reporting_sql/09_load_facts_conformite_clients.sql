/*
  BB_VISION_REPORTING - chargements reels Conformite et Clients

  Ce script cree les premieres procedures de chargement du data mart :
  - rpt.load_f_conformite : alimente rpt.f_conformite depuis la logique autonome de la requete 156 ;
  - rpt.load_f_clients    : alimente rpt.f_clients depuis la logique autonome de la requete 157 ;
  - rpt.load_all_facts    : orchestre les deux chargements prioritaires.

  Les procedures lisent la base source passee en parametre, par defaut BB_VISION_PRO_TEST.
  Elles ne creent pas de dependance a une vue ni a une autre requete.
*/

USE BB_VISION_REPORTING;
GO

CREATE OR ALTER PROCEDURE rpt.load_f_conformite
    @source_database sysname = N'BB_VISION_PRO_TEST',
    @date_debut date,
    @date_fin date,
    @id_devise_reporting int = NULL,
    @seuil_5k_usd_cdf decimal(38, 2) = 11375000,
    @seuil_10k_usd_cdf decimal(38, 2) = 22750000,
    @batch_id bigint = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @date_debut IS NULL OR @date_fin IS NULL
        THROW 51000, 'Les parametres @date_debut et @date_fin sont obligatoires.', 1;

    IF @date_debut > @date_fin
        THROW 51001, '@date_debut ne peut pas etre posterieure a @date_fin.', 1;

    IF DB_ID(@source_database) IS NULL
        THROW 51002, 'La base source demandee est introuvable.', 1;

    DECLARE @own_batch bit = 0;
    IF @batch_id IS NULL
    BEGIN
        SET @own_batch = 1;
        EXEC ctl.start_batch
            @source_database = @source_database,
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = @id_devise_reporting,
            @batch_id = @batch_id OUTPUT;
    END;

    DECLARE @sql nvarchar(max) = N'
USE ' + QUOTENAME(@source_database) + N';

DECLARE @devise_code varchar(10) = NULL;
SELECT @devise_code = CODE
FROM dbo.DEVISES
WHERE ID = @id_devise_reporting;

DELETE FROM BB_VISION_REPORTING.rpt.f_conformite
WHERE date_debut = @date_debut
  AND date_fin = @date_fin
  AND (
        @id_devise_reporting IS NULL
        OR devise = @devise_code
        OR devise IS NULL
      );

/*
 156. Socle unique cycle Conformite LBC-FT pour analyses 38, 39, 48, 57 et 149 a 155
 Export : 156_cycle_conformite_lbc_ft_socle_unique_analyses_38_39_48_57_149_155
 Objectif : produire un seul fichier a televerser dans l''application pour couvrir la synthese des flux,
 le fractionnement, les trous de couverture, les gros mouvements, le reporting, les alertes, declarations,
 profils de risque, sanctions, comptes reactives et controles qualite LBC-FT.
 Lecture : une ligne par element de controle, avec analyse_source pour distinguer les blocs 38, 39, 48, 57 et 149 a 155.
 Niveau d''importance de la requete : 10
 Usage operationnel : Televerser un fichier unique pour couvrir les analyses conformite LBC-FT prevues.
 Periodicite recommandee : Mensuel et a chaque televersement du cycle conformite

 Parametres :
 - @date_debut et @date_fin : periode inclusive ;
 - @id_devise_reporting : NULL pour les details multi-devises, ou 1/2 pour filtrer USD/CDF ;
 - @seuil_5k_usd_cdf et @seuil_10k_usd_cdf : seuils equivalents dans la devise de reporting.

 Garde-fou : les montants gardent toujours leur devise. Si @id_devise_reporting est NULL,
 les lignes monetaires sont produites par devise, sans consolidation multi-devises.
 */
DROP TABLE IF EXISTS #mouvements_conformite_156;

SELECT
  CAST(''BACK_OFFICE'' AS varchar(20)) AS source_mouvement,
  CAST(o.ID AS varchar(255)) AS id_operation,
  CAST(o.DATE_OPERATION AS date) AS date_operation,
  CAST(o.ID_TYPE_OPERATION AS varchar(255)) AS type_operation,
  MAX(CAST(ABS(ISNULL(h.MONTANT_OPERATION, 0)) AS decimal(38, 2))) AS montant_operation,
  h.ID_DEVISE AS id_devise
INTO #mouvements_conformite_156
FROM dbo.OPERATIONS AS o
INNER JOIN dbo.HDPM AS h
  ON h.ID_OPERATION = o.ID
WHERE
  o.DATE_OPERATION >= @date_debut
  AND o.DATE_OPERATION < DATEADD(day, 1, @date_fin)
  AND ISNULL(o.ANNULE, 0) = 0
  AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
GROUP BY
  o.ID,
  CAST(o.DATE_OPERATION AS date),
  o.ID_TYPE_OPERATION,
  h.ID_DEVISE
UNION ALL
SELECT
  CAST(''API'' AS varchar(20)),
  CAST(oa.CODE AS varchar(255)),
  CAST(oa.DATE_OPERATION AS date),
  CAST(oa.ID_TYPE_OPERATION AS varchar(255)),
  MAX(CAST(ABS(ISNULL(ha.MONTANT_OPERATION, 0)) AS decimal(38, 2))),
  ha.ID_DEVISE
FROM dbo.OPERATIONS_API AS oa
INNER JOIN dbo.HDPM_API AS ha
  ON ha.ID_OPERATION = oa.CODE
WHERE
  oa.DATE_OPERATION >= @date_debut
  AND oa.DATE_OPERATION < DATEADD(day, 1, @date_fin)
  AND ISNULL(oa.ANNULE, 0) = 0
  AND (@id_devise_reporting IS NULL OR ha.ID_DEVISE = @id_devise_reporting)
GROUP BY
  oa.CODE,
  CAST(oa.DATE_OPERATION AS date),
  oa.ID_TYPE_OPERATION,
  ha.ID_DEVISE;

CREATE CLUSTERED INDEX IX_mouvements_conformite_156
  ON #mouvements_conformite_156 (id_devise, type_operation, date_operation, id_operation);

WITH devises_reporting AS (
  SELECT
    d.ID AS id_devise,
    d.CODE AS code_devise,
    CAST(CASE WHEN UPPER(ISNULL(d.CODE, '''')) = ''USD'' THEN 5000 ELSE @seuil_5k_usd_cdf END AS decimal(38, 2)) AS seuil_5k,
    CAST(CASE WHEN UPPER(ISNULL(d.CODE, '''')) = ''USD'' THEN 10000 ELSE @seuil_10k_usd_cdf END AS decimal(38, 2)) AS seuil_10k
  FROM dbo.DEVISES AS d
  WHERE @id_devise_reporting IS NULL OR d.ID = @id_devise_reporting
), mouvements AS (
  SELECT
    source_mouvement,
    id_operation,
    date_operation,
    type_operation,
    montant_operation,
    id_devise
  FROM #mouvements_conformite_156
), alertes_periode AS (
  SELECT
    la.ID,
    la.NUM_ALERTE,
    COALESCE(CAST(la.DATE_CREATED AS date), la.DATE_OPERATION) AS date_alerte,
    la.DATE_OPERATION AS date_operation,
    la.ID_ADHERENT,
    la.NOM,
    la.ID_OPERATION_PERFECT,
    la.ID_OPERATION,
    la.ID_TYPE_OPERATION,
    la.TYPE_ALERTE,
    la.DESCRIPTION_ALERTE,
    CAST(ABS(ISNULL(la.MONTANT, 0)) AS decimal(38, 2)) AS montant,
    la.ID_DEVISE,
    la.ETAT_ALERTE,
    la.MOTIF_ETAT_ALERTE,
    la.ID_POINT_SERVICE,
    pdr.LIBELLE_RISQUE AS niveau_risque,
    pr.LIBELLE AS profil_risque,
    CASE
      WHEN UPPER(ISNULL(la.ETAT_ALERTE, '''')) LIKE ''TRAIT%''
        OR UPPER(ISNULL(la.ETAT_ALERTE, '''')) LIKE ''CLOTUR%''
        OR UPPER(ISNULL(la.ETAT_ALERTE, '''')) LIKE ''VALID%''
      THEN 1
      ELSE 0
    END AS est_traitee
  FROM dbo.LAB_ALERTES AS la
  LEFT JOIN dbo.LAB_PROFILS_DE_RISQUE AS pdr
    ON pdr.ID = la.ID_RISQUE_DE_PROFIL
  LEFT JOIN dbo.LAB_PROFIL_RISQUES AS pr
    ON pr.ID = la.ID_PROFIL_RISQUE
  WHERE
    COALESCE(CAST(la.DATE_CREATED AS date), la.DATE_OPERATION) >= @date_debut
    AND COALESCE(CAST(la.DATE_CREATED AS date), la.DATE_OPERATION) < DATEADD(day, 1, @date_fin)
    AND (@id_devise_reporting IS NULL OR la.ID_DEVISE = @id_devise_reporting)
), remboursements_anticipes AS (
  SELECT
    oc.ID_PRET,
    CAST(oc.ID_OPERATION AS varchar(255)) AS id_operation,
    CAST(o.DATE_OPERATION AS date) AS date_operation,
    oc.ID_DEVISE AS id_devise,
    MAX(CAST(ABS(ISNULL(oc.MONTANT, 0)) AS decimal(38, 2))) AS montant
  FROM dbo.OPERATIONS_CRD AS oc
  INNER JOIN dbo.OPERATIONS AS o
    ON o.ID = oc.ID_OPERATION
  WHERE
    ISNULL(oc.REMB_ANTICIPER, 0) = 1
    AND ISNULL(o.ANNULE, 0) = 0
    AND o.DATE_OPERATION >= @date_debut
    AND o.DATE_OPERATION < DATEADD(day, 1, @date_fin)
    AND (@id_devise_reporting IS NULL OR oc.ID_DEVISE = @id_devise_reporting)
  GROUP BY
    oc.ID_PRET,
    oc.ID_OPERATION,
    CAST(o.DATE_OPERATION AS date),
    oc.ID_DEVISE
), reactivations (
  id_reactivation,
  id_devise,
  date_operation,
  NUM_TRANSACTION,
  NUMERO_RECU,
  numero_compte,
  DATE_CLOTURE,
  DATE_REOUVERTURE,
  motif_cloture,
  montant,
  ID_POINT_SERVICE,
  ID_UTILISATEUR,
  ID_UTILISATEUR_VALIDE
) AS (
  SELECT
    r.ID AS id_reactivation,
    r.ID_DEVISE AS id_devise,
    CAST(o.DATE_OPERATION AS date) AS date_operation,
    o.NUM_TRANSACTION,
    o.NUMERO_RECU,
    c.ID_COMPTE AS numero_compte,
    c.DATE_CLOTURE,
    c.DATE_REOUVERTURE,
    mc.LIBELLE AS motif_cloture,
    CAST(ABS(ISNULL(r.MONTANT_A_PAYER, 0)) AS decimal(38, 2)) AS montant,
    o.ID_POINT_SERVICE,
    o.ID_UTILISATEUR,
    o.ID_UTILISATEUR_VALIDE
  FROM dbo.REACTIVATION_COMPTE_EPG AS r
  INNER JOIN dbo.OPERATIONS AS o
    ON o.ID = r.ID_OPERATION
  LEFT JOIN dbo.CLOTURE_COMPTE AS c
    ON c.ID = r.ID_CLOTURE_COMPTE
  LEFT JOIN dbo.MOTIFS_CLOTURE AS mc
    ON mc.ID = c.ID_MOTIF_CLOTURE
  WHERE
    ISNULL(o.ANNULE, 0) = 0
    AND o.DATE_OPERATION >= @date_debut
    AND o.DATE_OPERATION < DATEADD(day, 1, @date_fin)
    AND (@id_devise_reporting IS NULL OR r.ID_DEVISE = @id_devise_reporting)
), declarations AS (
  SELECT
    ''LAB_DECLARATION_SOUPCONS'' AS source_declaration,
    CAST(ds.ID AS varchar(255)) AS id_declaration,
    CAST(ds.dateDeclaration AS date) AS date_declaration,
    ds.referenceInterne AS reference_interne,
    ds.referenceCentif AS reference_externe,
    COALESCE(NULLIF(ds.nomPersonnePP, ''''), NULLIF(ds.raisonSocialePM, ''''), NULLIF(ds.nomPM, '''')) AS personne_declaree,
    ds.numeroCompte AS numero_compte,
    CAST(ABS(ISNULL(ds.montantTotal, 0)) AS decimal(38, 2)) AS montant,
    COALESCE(NULLIF(ds.devise, ''''), NULLIF(ds.pays, '''')) AS devise_texte,
    ISNULL(ds.annuleOui, 0) AS est_annulee,
    ISNULL(ds.operationFractionne, 0) AS operation_fractionnee,
    ISNULL(ds.operationGelFond, 0) AS operation_gel_fonds,
    ISNULL(ds.operationHautRisque, 0) AS operation_haut_risque,
    ISNULL(ds.blanchimentCapitaux, 0) AS soupcon_blanchiment,
    ISNULL(ds.financementTerrorisme, 0) AS soupcon_financement_terrorisme
  FROM dbo.LAB_DECLARATION_SOUPCONS AS ds
  WHERE
    ds.dateDeclaration >= @date_debut
    AND ds.dateDeclaration < DATEADD(day, 1, @date_fin)
  UNION ALL
  SELECT
    ''LAB_DECLARATION_CENTIF'',
    CAST(dc.ID AS varchar(255)),
    CAST(dc.DATE_DECLARATION AS date),
    dc.NUMERO_REF_INT,
    dc.REF_CENTIF,
    COALESCE(NULLIF(dc.NOM, ''''), NULLIF(dc.RAISON_SOCIAL, ''''), NULLIF(dc.NOM_PM, '''')),
    dc.NUM_COMPTE,
    CAST(ABS(ISNULL(dc.MONTANT_TOTAL, 0)) AS decimal(38, 2)),
    dc.DEVISE,
    ISNULL(dc.ANNULEE_CLIENT_LE, 0),
    CAST(0 AS bit),
    CAST(0 AS bit),
    CAST(0 AS bit),
    ISNULL(dc.BLANCHIMENT_CAPITAUX, 0),
    ISNULL(dc.FNC_TERRORISME, 0)
  FROM dbo.LAB_DECLARATION_CENTIF AS dc
  WHERE
    dc.DATE_DECLARATION >= @date_debut
    AND dc.DATE_DECLARATION < DATEADD(day, 1, @date_fin)
), profils_clients AS (
  SELECT
    apr.ID_ADHERENT AS id_adherent_lab,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT AS nom_adherent,
    a.DATE_INSCRIPTION AS date_inscription,
    apr.ID_POINT_SERVICE AS point_service_lab,
    pr.CODE AS code_profil,
    pr.LIBELLE AS profil_risque,
    pdr.CODE AS code_niveau_risque,
    pdr.LIBELLE_RISQUE AS niveau_risque,
    pdr.LIBELLE_COULEUR AS couleur_risque,
    apr.RISQUE_MANUEL AS risque_attribue_manuellement,
    apr.UTILISATEUR_MANUEL AS utilisateur_attribution,
    CASE WHEN a.ID IS NULL THEN 1 ELSE 0 END AS anomalie_adherent_introuvable
  FROM dbo.LAB_ADHERENT_PROFIL_RISQUES AS apr
  LEFT JOIN dbo.ADHERENTS AS a
    ON a.ID = apr.ID_ADHERENT OR a.CODE = apr.ID_ADHERENT
  LEFT JOIN dbo.LAB_PROFIL_RISQUES AS pr
    ON pr.ID = apr.ID_PROFIL_RISQUE
  LEFT JOIN dbo.LAB_PROFILS_DE_RISQUE AS pdr
    ON pdr.ID = apr.ID_RISQUE_DE_PROFIL
), noms_blacklist AS (
  SELECT
    n.ID_BLACKLIST,
    STRING_AGG(CAST(n.NOM AS varchar(max)), '' | '') AS autres_noms
  FROM dbo.LAB_BLACKLIST_NAMES AS n
  GROUP BY n.ID_BLACKLIST
), pieces_blacklist AS (
  SELECT
    p.ID_BLACKLIST,
    STRING_AGG(CAST(p.NUMERO_PIECE AS varchar(max)), '' | '') AS autres_pieces
  FROM dbo.LAB_BLACKLIST_PIECES AS p
  GROUP BY p.ID_BLACKLIST
), pseudos_blacklist AS (
  SELECT
    p.ID_BLACKLIST,
    STRING_AGG(CAST(p.PSEUDO AS varchar(max)), '' | '') AS pseudos
  FROM dbo.LAB_BLACKLIST_PSEUDOS AS p
  GROUP BY p.ID_BLACKLIST
), blacklist AS (
  SELECT
    b.ID AS id_blacklist,
    b.IDENTIFIANT AS identifiant_liste,
    b.TYPE_LISTE AS type_liste,
    b.REGIME_SANCTION AS regime_sanction,
    b.TYPE_PERSONNE AS type_personne,
    b.DESIGNATION AS designation,
    b.NOM AS nom_principal,
    n.autres_noms,
    ps.pseudos,
    b.NIN,
    p.autres_pieces,
    b.NATIONALITE AS nationalite,
    CAST(b.DATE_INSCRIPTION AS date) AS date_inscription,
    b.FONDEMENT_JURIDIQUE AS fondement_juridique,
    CASE
      WHEN NULLIF(LTRIM(RTRIM(ISNULL(b.NOM, ''''))), '''') IS NULL
        AND NULLIF(LTRIM(RTRIM(ISNULL(b.DESIGNATION, ''''))), '''') IS NULL
      THEN 1 ELSE 0
    END AS anomalie_identite_absente
  FROM dbo.LAB_BLACKLISTS AS b
  LEFT JOIN noms_blacklist AS n ON n.ID_BLACKLIST = b.ID
  LEFT JOIN pieces_blacklist AS p ON p.ID_BLACKLIST = b.ID
  LEFT JOIN pseudos_blacklist AS ps ON ps.ID_BLACKLIST = b.ID
), synthese_038 AS (
  SELECT ''1. ACTIVITE'' AS section, 38 AS ligne_excel, ''Total Depots'' AS rubrique,
    dr.id_devise, COUNT_BIG(m.id_operation) AS nombre,
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)) AS volume,
    ''Alimente la ligne Total Depots du reporting.'' AS commentaire
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.type_operation IN (''DEPO'', ''MOB_DEPO'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 71, ''Depot >= 10k USD'',
    dr.id_devise, COUNT_BIG(m.id_operation),
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''Seuil applique par devise : USD=10000, CDF=@seuil_10k_usd_cdf.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.type_operation IN (''DEPO'', ''MOB_DEPO'')
    AND m.montant_operation >= dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 72, ''Retrait >= 10k USD'',
    dr.id_devise, COUNT_BIG(m.id_operation),
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''Seuil applique par devise : USD=10000, CDF=@seuil_10k_usd_cdf.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.type_operation IN (''RETR'', ''MOB_RETR'')
    AND m.montant_operation >= dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 73, ''Depot >= 5k USD et < 10k USD'',
    dr.id_devise, COUNT_BIG(m.id_operation),
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''Seuils appliques par devise : USD=5000/10000, CDF=parametres CDF.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.type_operation IN (''DEPO'', ''MOB_DEPO'')
    AND m.montant_operation >= dr.seuil_5k
    AND m.montant_operation < dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 74, ''Retrait >= 5k USD et < 10k USD'',
    dr.id_devise, COUNT_BIG(m.id_operation),
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''Seuils appliques par devise : USD=5000/10000, CDF=parametres CDF.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.type_operation IN (''RETR'', ''MOB_RETR'')
    AND m.montant_operation >= dr.seuil_5k
    AND m.montant_operation < dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''4. CANAUX DE DISTRIBUTION'', 152, ''Operations effectuees par Mobile Banking'',
    dr.id_devise, COUNT_BIG(m.id_operation),
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''Operations API mobiles : MOB_DEPO et MOB_RETR.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.source_mouvement = ''API''
    AND m.type_operation IN (''MOB_DEPO'', ''MOB_RETR'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''4. CANAUX DE DISTRIBUTION'', 154, ''Wallet to Bank'',
    dr.id_devise, COUNT_BIG(m.id_operation),
    CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''Approximation : depots mobiles MOB_DEPO.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m
    ON m.id_devise = dr.id_devise
    AND m.type_operation = ''MOB_DEPO''
  GROUP BY dr.id_devise
), mouvements_fractionnement AS (
  SELECT
    ''BACK_OFFICE'' AS source_mouvement,
    CAST(o.ID AS varchar(255)) AS id_operation,
    CAST(o.DATE_OPERATION AS date) AS date_operation,
    CASE
      WHEN o.ID_TYPE_OPERATION = ''DEPO'' THEN ''Depot''
      WHEN o.ID_TYPE_OPERATION = ''RETR'' THEN ''Retrait''
    END AS type_mouvement,
    ca.ID_ADHERENT,
    a.CODE AS code_adherent,
    a.NOM_ADHERENT,
    a.ID_TYPE_ADHERENT AS code_type_client,
    ta.LIBELLE AS type_client,
    CAST(MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS decimal(38, 2)) AS montant_operation,
    h.ID_DEVISE
  FROM dbo.OPERATIONS AS o
  INNER JOIN dbo.HDPM AS h
    ON h.ID_OPERATION = o.ID
  INNER JOIN devises_reporting AS dr
    ON dr.id_devise = h.ID_DEVISE
  LEFT JOIN dbo.COMPTES_ADHERENT AS ca
    ON ca.ID = h.ID_COMPTE
  LEFT JOIN dbo.ADHERENTS AS a
    ON a.ID = ca.ID_ADHERENT
  LEFT JOIN dbo.TYPES_ADHERENT AS ta
    ON ta.ID = a.ID_TYPE_ADHERENT
  WHERE
    o.DATE_OPERATION >= @date_debut
    AND o.DATE_OPERATION < DATEADD(day, 1, @date_fin)
    AND o.ID_TYPE_OPERATION IN (''DEPO'', ''RETR'')
    AND ISNULL(o.ANNULE, 0) = 0
  GROUP BY
    o.ID,
    CAST(o.DATE_OPERATION AS date),
    o.ID_TYPE_OPERATION,
    ca.ID_ADHERENT,
    a.CODE,
    a.NOM_ADHERENT,
    a.ID_TYPE_ADHERENT,
    ta.LIBELLE,
    h.ID_DEVISE
  UNION ALL
  SELECT
    ''API_MOBILE'',
    CAST(oa.CODE AS varchar(255)),
    CAST(oa.DATE_OPERATION AS date),
    CASE
      WHEN oa.ID_TYPE_OPERATION = ''MOB_DEPO'' THEN ''Depot''
      WHEN oa.ID_TYPE_OPERATION = ''MOB_RETR'' THEN ''Retrait''
    END,
    ca.ID_ADHERENT,
    a.CODE,
    a.NOM_ADHERENT,
    a.ID_TYPE_ADHERENT,
    ta.LIBELLE,
    CAST(MAX(ABS(ISNULL(h.MONTANT_OPERATION, 0))) AS decimal(38, 2)),
    h.ID_DEVISE
  FROM dbo.OPERATIONS_API AS oa
  INNER JOIN dbo.HDPM_API AS h
    ON h.ID_OPERATION = oa.CODE
  INNER JOIN devises_reporting AS dr
    ON dr.id_devise = h.ID_DEVISE
  LEFT JOIN dbo.COMPTES_ADHERENT AS ca
    ON ca.ID = h.ID_COMPTE
  LEFT JOIN dbo.ADHERENTS AS a
    ON a.ID = ca.ID_ADHERENT
  LEFT JOIN dbo.TYPES_ADHERENT AS ta
    ON ta.ID = a.ID_TYPE_ADHERENT
  WHERE
    oa.DATE_OPERATION >= @date_debut
    AND oa.DATE_OPERATION < DATEADD(day, 1, @date_fin)
    AND oa.ID_TYPE_OPERATION IN (''MOB_DEPO'', ''MOB_RETR'')
    AND ISNULL(oa.ANNULE, 0) = 0
  GROUP BY
    oa.CODE,
    CAST(oa.DATE_OPERATION AS date),
    oa.ID_TYPE_OPERATION,
    ca.ID_ADHERENT,
    a.CODE,
    a.NOM_ADHERENT,
    a.ID_TYPE_ADHERENT,
    ta.LIBELLE,
    h.ID_DEVISE
), fractionnements AS (
  SELECT
    m.date_operation,
    m.ID_ADHERENT,
    m.code_adherent,
    m.NOM_ADHERENT,
    m.code_type_client,
    m.type_client,
    m.type_mouvement,
    m.ID_DEVISE AS id_devise,
    COUNT_BIG(*) AS nb_operations,
    CAST(SUM(m.montant_operation) AS decimal(38, 2)) AS montant_cumule,
    CAST(MAX(m.montant_operation) AS decimal(38, 2)) AS montant_max_unitaire,
    dr.seuil_10k AS seuil_reference
  FROM mouvements_fractionnement AS m
  INNER JOIN devises_reporting AS dr
    ON dr.id_devise = m.ID_DEVISE
  WHERE
    m.montant_operation < dr.seuil_10k
  GROUP BY
    m.date_operation,
    m.ID_ADHERENT,
    m.code_adherent,
    m.NOM_ADHERENT,
    m.code_type_client,
    m.type_client,
    m.type_mouvement,
    m.ID_DEVISE,
    dr.seuil_10k
  HAVING
    COUNT_BIG(*) >= 2
    AND SUM(m.montant_operation) >= dr.seuil_10k
), couverture_conformite AS (
  SELECT
    CAST(rubrique_reporting AS varchar(255)) AS rubrique_reporting,
    CAST(statut_couverture AS varchar(255)) AS statut_couverture,
    CAST(source_identifiee AS varchar(1000)) AS source_identifiee,
    CAST(prerequis_mapping AS varchar(1000)) AS prerequis_mapping
  FROM (VALUES
    (''PPE'', ''PARTIEL'', ''dbo.LAB_DECLARATION_CENTIF.PPE / PPE_PM et profils LAB'',
      ''Le marqueur PPE existe dans les declarations, mais pas comme attribut date du referentiel client.''),
    (''Non-residents'', ''PARTIEL'', ''dbo.ADRESSES, dbo.PAYS et nationalite des tables LAB'',
      ''A mapper avec les donnees pays/adresse/statut resident du client.''),
    (''MPME'', ''PARTIEL'', ''dbo.SECTEURS_ACTIVITE, dbo.LAB_PROFILAGE et dbo.LAB_PERFECT_SECTEUR'',
      ''Faire valider la nomenclature sectorielle officielle par la Conformite.''),
    (''OBNL'', ''PARTIEL'', ''dbo.SECTEURS_ACTIVITE, dbo.TYPES_ADHERENT et dbo.LAB_PROFILAGE'',
      ''A mapper avec categorie/type adherent, secteur activite ou forme juridique.''),
    (''Secteur immobilier'', ''PARTIEL'', ''dbo.SECTEURS_ACTIVITE / dbo.SECTEURS_ACTIVITE_CREDIT'',
      ''A mapper avec SECTEURS_ACTIVITE / SECTEURS_ACTIVITE_CREDIT.''),
    (''Secteur minier'', ''PARTIEL'', ''dbo.SECTEURS_ACTIVITE / dbo.SECTEURS_ACTIVITE_CREDIT'',
      ''Faire valider les codes secteur et objets de financement retenus.''),
    (''Alertes LBC-FT'', ''COUVERT'', ''dbo.LAB_ALERTES et dbo.LAB_RECHERCHES_NON_FRUCTUEUSES'',
      ''Valider la liste des valeurs ETAT_ALERTE considerees comme traitees.''),
    (''DOS / declarations de soupcon'', ''COUVERT'', ''dbo.LAB_DECLARATION_SOUPCONS et dbo.LAB_DECLARATION_CENTIF'',
      ''Verifier si les deux tables representent deux formulaires ou deux etapes afin d eviter un double comptage.''),
    (''Listes de sanctions'', ''COUVERT'', ''dbo.LAB_BLACKLISTS et tables enfants noms, pieces et pseudos'',
      ''La base contient le referentiel des listes, pas la preuve d un gel ou d une transaction refusee.''),
    (''Gels et transactions refusees pour sanctions'', ''NON_COUVERT'', ''Aucune table d action de gel/refus identifiee'',
      ''Ne pas assimiler une inscription en blacklist a une mesure de gel effectivement executee.''),
    (''Credits rembourses anticipativement'', ''COUVERT'', ''dbo.OPERATIONS_CRD.REMB_ANTICIPER, dbo.OPERATIONS et dbo.PRETS'',
      ''La requete de reporting compte les prets distincts et les montants d operations sur la periode.''),
    (''Comptes dormants reactives'', ''COUVERT'', ''dbo.REACTIVATION_COMPTE_EPG, dbo.CLOTURE_COMPTE et dbo.OPERATIONS'',
      ''La date de l operation de reactivation definit la periode de reporting.'')
  ) AS v(rubrique_reporting, statut_couverture, source_identifiee, prerequis_mapping)
), mouvements_comptables_057 AS (
  SELECT
    h.DATE_OPERATION,
    h.ID_DEVISE,
    h.ID_POINT_SERVICE,
    CAST(ABS(ISNULL(h.MONTANT_REEL, h.MONTANT_OPERATION)) AS decimal(38, 2)) AS montant_mouvement
  FROM dbo.HDPM AS h
  WHERE
    h.DATE_OPERATION >= @date_debut
    AND h.DATE_OPERATION < DATEADD(day, 1, @date_fin)
    AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
  UNION ALL
  SELECT
    h.DATE_OPERATION,
    h.ID_DEVISE,
    h.ID_POINT_SERVICE,
    CAST(ABS(h.MONTANT_OPERATION) AS decimal(38, 2))
  FROM dbo.HDPM_API AS h
  WHERE
    h.DATE_OPERATION >= @date_debut
    AND h.DATE_OPERATION < DATEADD(day, 1, @date_fin)
    AND (@id_devise_reporting IS NULL OR h.ID_DEVISE = @id_devise_reporting)
), gros_mouvements_057 AS (
  SELECT
    DATEFROMPARTS(YEAR(h.DATE_OPERATION), MONTH(h.DATE_OPERATION), 1) AS mois,
    ps.CODE AS code_point_service,
    ps.NOM AS nom_point_service,
    h.ID_DEVISE AS id_devise,
    dr.seuil_5k AS seuil_reference,
    COUNT_BIG(*) AS nb_gros_mouvements,
    CAST(SUM(h.montant_mouvement) AS decimal(38, 2)) AS volume_total,
    CAST(MAX(h.montant_mouvement) AS decimal(38, 2)) AS plus_gros_mouvement
  FROM mouvements_comptables_057 AS h
  INNER JOIN devises_reporting AS dr
    ON dr.id_devise = h.ID_DEVISE
  LEFT JOIN dbo.POINTS_SERVICE AS ps
    ON ps.ID = h.ID_POINT_SERVICE
  WHERE
    h.montant_mouvement >= dr.seuil_5k
  GROUP BY
    DATEFROMPARTS(YEAR(h.DATE_OPERATION), MONTH(h.DATE_OPERATION), 1),
    ps.CODE,
    ps.NOM,
    h.ID_DEVISE,
    dr.seuil_5k
), reporting AS (
  SELECT ''1. TAILLE'' AS section, 26 AS ligne_excel, ''Total operations comptabilisees'' AS rubrique,
    dr.id_devise, COUNT_BIG(m.id_operation) AS nombre, CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)) AS volume,
    ''COUVERT'' AS statut_couverture, ''dbo.OPERATIONS + dbo.HDPM et sources API'' AS source_donnee,
    ''Une operation est comptee une fois avec le montant absolu maximal de ses lignes HDPM.'' AS commentaire
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''1. TAILLE'', 27, ''Total operations en especes'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.OPERATIONS + dbo.HDPM'',
    ''Definition operationnelle : depots et retraits DEPO/RETR ; faire valider les autres modes especes.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.type_operation IN (''DEPO'', ''RETR'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''1. TAILLE'', 38, ''Total depots'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''COUVERT'', ''dbo.OPERATIONS/HDPM + dbo.OPERATIONS_API/HDPM_API'',
    ''Flux de depots DEPO et MOB_DEPO sur la periode, distinct du stock d epargne.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.type_operation IN (''DEPO'', ''MOB_DEPO'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''2. PORTEFEUILLE CLIENT'', 65, ''Clients enregistres durant la periode'', NULL,
    COUNT_BIG(*), CAST(NULL AS decimal(38, 2)),
    ''COUVERT'', ''dbo.ADHERENTS'',
    ''Nombre de clients IMF distincts inscrits dans la periode ; aucun volume monetaire n est calcule.''
  FROM dbo.ADHERENTS AS a
  WHERE a.ID_CATEGORIE_ADHERENT = ''IMF''
    AND a.DATE_INSCRIPTION >= @date_debut
    AND a.DATE_INSCRIPTION < DATEADD(day, 1, @date_fin)
  UNION ALL
  SELECT ''2. PORTEFEUILLE CLIENT'', 66, ''Clients actuellement classes a haut risque'', NULL,
    COUNT_BIG(DISTINCT pc.id_adherent_lab), CAST(NULL AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ADHERENT_PROFIL_RISQUES + dbo.LAB_PROFILS_DE_RISQUE'',
    ''La table ne porte pas de date de reclassement ; le resultat est un stock actuel, pas un flux de la periode.''
  FROM profils_clients AS pc
  WHERE UPPER(ISNULL(pc.niveau_risque, '''')) LIKE ''%HAUT%''
     OR UPPER(ISNULL(pc.code_niveau_risque, '''')) LIKE ''%HAUT%''
     OR UPPER(ISNULL(pc.couleur_risque, '''')) LIKE ''%ROUGE%''
  UNION ALL
  SELECT ''2. PORTEFEUILLE CLIENT'', 68, ''Clients sous surveillance renforcee'', NULL,
    COUNT_BIG(DISTINCT pc.id_adherent_lab), CAST(NULL AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ADHERENT_PROFIL_RISQUES + dbo.LAB_PROFILS_DE_RISQUE'',
    ''Approximation par profil de risque eleve ; faire valider la regle de surveillance renforcee.''
  FROM profils_clients AS pc
  WHERE UPPER(ISNULL(pc.niveau_risque, '''')) LIKE ''%HAUT%''
     OR UPPER(ISNULL(pc.code_niveau_risque, '''')) LIKE ''%HAUT%''
     OR UPPER(ISNULL(pc.couleur_risque, '''')) LIKE ''%ROUGE%''
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 71, ''Depot >= equivalent 10k USD'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''COUVERT'', ''Mouvements DEPO et MOB_DEPO'', ''Seuil applique par devise : USD=10000, CDF=@seuil_10k_usd_cdf.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.type_operation IN (''DEPO'', ''MOB_DEPO'') AND m.montant_operation >= dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 72, ''Retrait >= equivalent 10k USD'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''COUVERT'', ''Mouvements RETR et MOB_RETR'', ''Seuil applique par devise : USD=10000, CDF=@seuil_10k_usd_cdf.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.type_operation IN (''RETR'', ''MOB_RETR'') AND m.montant_operation >= dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 73, ''Depot entre equivalents 5k et 10k USD'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''COUVERT'', ''Mouvements DEPO et MOB_DEPO'', ''Seuils appliques par devise : USD=5000/10000, CDF=parametres CDF.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.type_operation IN (''DEPO'', ''MOB_DEPO'')
    AND m.montant_operation >= dr.seuil_5k AND m.montant_operation < dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 74, ''Retrait entre equivalents 5k et 10k USD'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''COUVERT'', ''Mouvements RETR et MOB_RETR'', ''Seuils appliques par devise : USD=5000/10000, CDF=parametres CDF.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.type_operation IN (''RETR'', ''MOB_RETR'')
    AND m.montant_operation >= dr.seuil_5k AND m.montant_operation < dr.seuil_10k
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 142, ''Credits rembourses anticipativement'', dr.id_devise,
    COUNT_BIG(ra.ID_PRET), CAST(ISNULL(SUM(ra.montant), 0) AS decimal(38, 2)),
    ''COUVERT'', ''dbo.OPERATIONS_CRD.REMB_ANTICIPER + dbo.OPERATIONS'',
    ''Nombre de prets distincts marques comme rembourses anticipativement dans la periode.''
  FROM devises_reporting AS dr
  LEFT JOIN remboursements_anticipes AS ra ON ra.id_devise = dr.id_devise
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 144, ''Total alertes generees'', dr.id_devise,
    COUNT_BIG(a.ID), CAST(ISNULL(SUM(a.montant), 0) AS decimal(38, 2)),
    ''COUVERT'', ''dbo.LAB_ALERTES'', ''Periode fondee sur DATE_CREATED puis DATE_OPERATION en repli.''
  FROM devises_reporting AS dr
  LEFT JOIN alertes_periode AS a ON a.ID_DEVISE = dr.id_devise
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 145, ''Total alertes traitees'', dr.id_devise,
    COUNT_BIG(a.ID), CAST(ISNULL(SUM(a.montant), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ALERTES.ETAT_ALERTE'',
    ''Etats commencant par TRAIT, CLOTUR ou VALID ; nomenclature a valider par la Conformite.''
  FROM devises_reporting AS dr
  LEFT JOIN alertes_periode AS a ON a.ID_DEVISE = dr.id_devise AND a.est_traitee = 1
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 146, ''Alertes especes >= equivalent 10k USD'', dr.id_devise,
    COUNT_BIG(a.ID), CAST(ISNULL(SUM(a.montant), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ALERTES'', ''Seuil applique par devise ; type especes reconnu par mots-clefs.''
  FROM devises_reporting AS dr
  LEFT JOIN alertes_periode AS a ON a.ID_DEVISE = dr.id_devise AND a.montant >= dr.seuil_10k
    AND (UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%ESPEC%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%ESPEC%'' OR UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%CASH%'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 147, ''Alertes traitees especes >= equivalent 10k USD'', dr.id_devise,
    COUNT_BIG(a.ID), CAST(ISNULL(SUM(a.montant), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ALERTES'', ''Cumule le critere de seuil/especes et la regle provisoire des etats traites.''
  FROM devises_reporting AS dr
  LEFT JOIN alertes_periode AS a ON a.ID_DEVISE = dr.id_devise AND a.est_traitee = 1 AND a.montant >= dr.seuil_10k
    AND (UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%ESPEC%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%ESPEC%'' OR UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%CASH%'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 148, ''Operations suspectes ou atypiques detectees'', dr.id_devise,
    COUNT_BIG(a.ID), CAST(ISNULL(SUM(a.montant), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ALERTES'', ''Detection par libelle/type contenant SUSPECT ou ATYPI.''
  FROM devises_reporting AS dr
  LEFT JOIN alertes_periode AS a ON a.ID_DEVISE = dr.id_devise
    AND (UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%SUSPECT%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%SUSPECT%''
      OR UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%ATYPI%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%ATYPI%'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 149, ''Comptes dormants reactives'', dr.id_devise,
    COUNT_BIG(r.id_reactivation), CAST(ISNULL(SUM(r.montant), 0) AS decimal(38, 2)),
    ''COUVERT'', ''dbo.REACTIVATION_COMPTE_EPG + dbo.OPERATIONS'',
    ''Le volume correspond au montant a payer de la reactivation, pas au solde du compte.''
  FROM devises_reporting AS dr
  LEFT JOIN reactivations AS r ON r.id_devise = dr.id_devise
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''3. PRODUIT - SERVICE - OPERATIONS'', 150, ''Operations fractionnees detectees'', dr.id_devise,
    COUNT_BIG(a.ID), CAST(ISNULL(SUM(a.montant), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_ALERTES'', ''Detection par mots-clefs FRACTION ou STRUCTUR dans les alertes officielles.''
  FROM devises_reporting AS dr
  LEFT JOIN alertes_periode AS a ON a.ID_DEVISE = dr.id_devise
    AND (UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%FRACTION%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%FRACTION%''
      OR UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%STRUCTUR%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%STRUCTUR%'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''4. CANAUX DE DISTRIBUTION'', 152, ''Operations effectuees par Mobile Banking'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''COUVERT'', ''dbo.OPERATIONS_API + dbo.HDPM_API'', ''Operations API MOB_DEPO et MOB_RETR.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.source_mouvement = ''API'' AND m.type_operation IN (''MOB_DEPO'', ''MOB_RETR'')
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''4. CANAUX DE DISTRIBUTION'', 153, ''Bank to Wallet'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.OPERATIONS_API + dbo.HDPM_API'',
    ''Hypothese : MOB_RETR debite le compte bancaire vers le wallet ; sens a confirmer.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.source_mouvement = ''API'' AND m.type_operation = ''MOB_RETR''
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''4. CANAUX DE DISTRIBUTION'', 154, ''Wallet to Bank'', dr.id_devise,
    COUNT_BIG(m.id_operation), CAST(ISNULL(SUM(m.montant_operation), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.OPERATIONS_API + dbo.HDPM_API'',
    ''Hypothese : MOB_DEPO credite le compte bancaire depuis le wallet ; sens a confirmer.''
  FROM devises_reporting AS dr
  LEFT JOIN mouvements AS m ON m.id_devise = dr.id_devise AND m.source_mouvement = ''API'' AND m.type_operation = ''MOB_DEPO''
  GROUP BY dr.id_devise
  UNION ALL
  SELECT ''5. DECLARATIONS DES SOUPCONS'', 164, ''DOS enregistrees'', NULL,
    COUNT_BIG(*), CAST(ISNULL(SUM(montant), 0) AS decimal(38, 2)),
    ''PARTIEL'', ''dbo.LAB_DECLARATION_SOUPCONS + dbo.LAB_DECLARATION_CENTIF'',
    ''La devise est stockee en texte dans chaque declaration ; controler devise_texte avant consolidation.''
  FROM declarations
  WHERE est_annulee = 0
  UNION ALL
  SELECT ''5. DECLARATIONS DES SOUPCONS'', 163, ''Declarations automatiques'', NULL,
    CAST(NULL AS bigint), CAST(NULL AS decimal(38, 2)),
    ''NON_COUVERT'', ''Aucune source explicitement qualifiee automatique'',
    ''Ne pas assimiler automatiquement LAB_DECLARATION_CENTIF a une declaration automatique.''
  UNION ALL
  SELECT ''6. SANCTIONS FINANCIERES CIBLEES'', 166, ''Gels des avoirs'', NULL,
    CAST(NULL AS bigint), CAST(NULL AS decimal(38, 2)),
    ''NON_COUVERT'', ''Referentiel dbo.LAB_BLACKLISTS uniquement'',
    ''Aucune table d action de gel execute identifiee dans le schema.''
  UNION ALL
  SELECT ''6. SANCTIONS FINANCIERES CIBLEES'', 167, ''Transactions refusees pour sanctions'', NULL,
    CAST(NULL AS bigint), CAST(NULL AS decimal(38, 2)),
    ''NON_COUVERT'', ''Referentiel dbo.LAB_BLACKLISTS uniquement'',
    ''Aucune table de decision de refus liee a une correspondance blacklist identifiee.''
), controles_qualite AS (
  SELECT
    ''ALERTE_SANS_NUMERO'' AS controle,
    COUNT_BIG(*) AS nombre_anomalies,
    ''ELEVEE'' AS severite,
    ''Rendre NUM_ALERTE obligatoire et unique pour assurer la piste d audit.'' AS action_recommandee
  FROM alertes_periode
  WHERE NULLIF(LTRIM(RTRIM(ISNULL(NUM_ALERTE, ''''))), '''') IS NULL
  UNION ALL
  SELECT ''ALERTE_SANS_CLIENT'', COUNT_BIG(*), ''ELEVEE'',
    ''Completer ID_ADHERENT avant cloture de l alerte.''
  FROM alertes_periode
  WHERE NULLIF(LTRIM(RTRIM(ISNULL(ID_ADHERENT, ''''))), '''') IS NULL
  UNION ALL
  SELECT ''ALERTE_SANS_DEVISE'', COUNT_BIG(*), ''ELEVEE'',
    ''Rendre ID_DEVISE obligatoire pour eviter les consolidations multi-devises.''
  FROM alertes_periode
  WHERE ID_DEVISE IS NULL
  UNION ALL
  SELECT ''ALERTE_SANS_ETAT'', COUNT_BIG(*), ''ELEVEE'',
    ''Rendre ETAT_ALERTE obligatoire et normaliser les valeurs autorisees.''
  FROM alertes_periode
  WHERE NULLIF(LTRIM(RTRIM(ISNULL(ETAT_ALERTE, ''''))), '''') IS NULL
  UNION ALL
  SELECT ''NUMERO_ALERTE_DUPLIQUE'', COUNT_BIG(*), ''CRITIQUE'',
    ''Investiguer les numeros repetes et poser une contrainte d unicite si la regle metier le confirme.''
  FROM (
    SELECT NUM_ALERTE
    FROM alertes_periode
    WHERE NULLIF(LTRIM(RTRIM(ISNULL(NUM_ALERTE, ''''))), '''') IS NOT NULL
    GROUP BY NUM_ALERTE
    HAVING COUNT_BIG(*) > 1
  ) AS doublons
  UNION ALL
  SELECT ''DOS_SANS_REFERENCE_INTERNE'', COUNT_BIG(*), ''ELEVEE'',
    ''Renseigner referenceInterne pour relier la declaration au dossier de Conformite.''
  FROM dbo.LAB_DECLARATION_SOUPCONS AS ds
  WHERE
    ds.dateDeclaration >= @date_debut
    AND ds.dateDeclaration < DATEADD(day, 1, @date_fin)
    AND NULLIF(LTRIM(RTRIM(ISNULL(ds.referenceInterne, ''''))), '''') IS NULL
  UNION ALL
  SELECT ''DOS_SANS_DEVISE'', COUNT_BIG(*), ''ELEVEE'',
    ''Renseigner la devise avant toute consolidation des montants declares.''
  FROM dbo.LAB_DECLARATION_SOUPCONS AS ds
  WHERE
    ds.dateDeclaration >= @date_debut
    AND ds.dateDeclaration < DATEADD(day, 1, @date_fin)
    AND NULLIF(LTRIM(RTRIM(ISNULL(ds.devise, ''''))), '''') IS NULL
  UNION ALL
  SELECT ''PROFIL_LAB_SANS_ADHERENT'', COUNT_BIG(*), ''CRITIQUE'',
    ''Corriger la cle ID_ADHERENT ou CODE afin de garantir le rattachement au client Perfect Vision.''
  FROM profils_clients
  WHERE anomalie_adherent_introuvable = 1
  UNION ALL
  SELECT ''BLACKLIST_SANS_IDENTITE'', COUNT_BIG(*), ''CRITIQUE'',
    ''Completer au minimum NOM ou DESIGNATION pour rendre le screening exploitable.''
  FROM blacklist
  WHERE anomalie_identite_absente = 1
), socle AS (
SELECT
  ''149_REPORTING_LBC_FT'' AS analyse_source,
  ''REPORTING'' AS type_ligne,
  CAST(r.section AS varchar(255)) AS section,
  CAST(r.ligne_excel AS int) AS ligne_excel,
  CAST(r.rubrique AS varchar(255)) AS rubrique,
  @date_debut AS date_debut,
  @date_fin AS date_fin,
  CAST(NULL AS date) AS date_alerte,
  CAST(NULL AS date) AS date_declaration,
  CAST(NULL AS date) AS date_operation,
  CAST(NULL AS varchar(255)) AS client_id,
  CAST(NULL AS varchar(255)) AS code_adherent,
  CAST(NULL AS varchar(255)) AS nom_client,
  CAST(NULL AS varchar(255)) AS numero_compte,
  CAST(NULL AS varchar(255)) AS numero_alerte,
  CAST(NULL AS varchar(255)) AS reference_interne,
  CAST(NULL AS varchar(255)) AS reference_externe,
  CAST(NULL AS varchar(255)) AS id_operation,
  CAST(NULL AS varchar(255)) AS type_operation,
  CAST(NULL AS varchar(255)) AS type_alerte,
  CAST(NULL AS varchar(1000)) AS description_alerte,
  CAST(NULL AS varchar(255)) AS etat_alerte,
  CAST(NULL AS varchar(255)) AS statut_revue_conformite,
  CAST(r.statut_couverture AS varchar(255)) AS statut_couverture,
  CAST(NULL AS varchar(255)) AS source_declaration,
  CAST(r.id_devise AS int) AS id_devise,
  CAST(dv.CODE AS varchar(255)) AS devise,
  CAST(NULL AS decimal(38, 2)) AS montant,
  CAST(r.volume AS decimal(38, 2)) AS volume,
  CAST(r.nombre AS bigint) AS nombre,
  CAST(NULL AS varchar(255)) AS niveau_risque,
  CAST(NULL AS varchar(255)) AS profil_risque,
  CAST(NULL AS varchar(255)) AS severite,
  CAST(NULL AS varchar(255)) AS controle,
  CAST(NULL AS bigint) AS nombre_anomalies,
  CAST(NULL AS varchar(1000)) AS action_recommandee,
  CAST(r.source_donnee AS varchar(1000)) AS source_donnee,
  CAST(r.commentaire AS varchar(1000)) AS commentaire,
  CAST(NULL AS varchar(255)) AS point_service,
  CAST(NULL AS varchar(255)) AS motif_etat,
  CAST(NULL AS bit) AS operation_fractionnee,
  CAST(NULL AS bit) AS operation_gel_fonds,
  CAST(NULL AS bit) AS operation_haut_risque,
  CAST(NULL AS bit) AS soupcon_blanchiment,
  CAST(NULL AS bit) AS soupcon_financement_terrorisme,
  CAST(NULL AS bit) AS anomalie_adherent_introuvable,
  CAST(NULL AS bit) AS anomalie_identite_absente
FROM reporting AS r
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = r.id_devise
UNION ALL
SELECT
  ''149_DETAIL_MOUVEMENTS_REPORTING_LBC_FT'',
  ''MOUVEMENT_OPERATION'',
  CAST(md.section AS varchar(255)),
  CAST(md.ligne_excel AS int),
  CAST(md.rubrique AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  md.date_operation,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  md.id_operation,
  CAST(md.type_operation AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(md.source_mouvement AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(''DETAIL_SOURCE_REPORTING_149'' AS varchar(255)),
  CAST(md.statut_couverture AS varchar(255)),
  CAST(NULL AS varchar(255)),
  md.id_devise,
  CAST(dv.CODE AS varchar(255)),
  md.montant_operation,
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(md.source_donnee AS varchar(1000)),
  CAST(md.commentaire AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM (
  SELECT
    m.source_mouvement,
    m.id_operation,
    m.date_operation,
    m.type_operation,
    m.montant_operation,
    m.id_devise,
    ''1. TAILLE'' AS section,
    26 AS ligne_excel,
    ''Detail - total operations comptabilisees'' AS rubrique,
    ''COUVERT'' AS statut_couverture,
    ''dbo.OPERATIONS + dbo.HDPM et sources API'' AS source_donnee,
    ''Ligne source du total operations ; une operation peut aussi alimenter une rubrique seuil/canal.'' AS commentaire
  FROM mouvements AS m
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''1. TAILLE'', 27, ''Detail - operations en especes'', ''PARTIEL'', ''dbo.OPERATIONS + dbo.HDPM'',
    ''Definition operationnelle : depots et retraits DEPO/RETR ; faire valider les autres modes especes.''
  FROM mouvements AS m
  WHERE m.type_operation IN (''DEPO'', ''RETR'')
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''1. TAILLE'', 38, ''Detail - total depots'', ''COUVERT'', ''dbo.OPERATIONS/HDPM + dbo.OPERATIONS_API/HDPM_API'',
    ''Flux de depots DEPO et MOB_DEPO sur la periode, distinct du stock d epargne.''
  FROM mouvements AS m
  WHERE m.type_operation IN (''DEPO'', ''MOB_DEPO'')
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''3. PRODUIT - SERVICE - OPERATIONS'', 71, ''Detail - depot >= equivalent 10k USD'', ''COUVERT'', ''Mouvements DEPO et MOB_DEPO'',
    ''Seuil applique par devise : USD=10000, CDF=@seuil_10k_usd_cdf.''
  FROM mouvements AS m
  INNER JOIN devises_reporting AS dr ON dr.id_devise = m.id_devise
  WHERE m.type_operation IN (''DEPO'', ''MOB_DEPO'') AND m.montant_operation >= dr.seuil_10k
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''3. PRODUIT - SERVICE - OPERATIONS'', 72, ''Detail - retrait >= equivalent 10k USD'', ''COUVERT'', ''Mouvements RETR et MOB_RETR'',
    ''Seuil applique par devise : USD=10000, CDF=@seuil_10k_usd_cdf.''
  FROM mouvements AS m
  INNER JOIN devises_reporting AS dr ON dr.id_devise = m.id_devise
  WHERE m.type_operation IN (''RETR'', ''MOB_RETR'') AND m.montant_operation >= dr.seuil_10k
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''3. PRODUIT - SERVICE - OPERATIONS'', 73, ''Detail - depot entre equivalents 5k et 10k USD'', ''COUVERT'', ''Mouvements DEPO et MOB_DEPO'',
    ''Seuils appliques par devise : USD=5000/10000, CDF=parametres CDF.''
  FROM mouvements AS m
  INNER JOIN devises_reporting AS dr ON dr.id_devise = m.id_devise
  WHERE m.type_operation IN (''DEPO'', ''MOB_DEPO'') AND m.montant_operation >= dr.seuil_5k AND m.montant_operation < dr.seuil_10k
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''3. PRODUIT - SERVICE - OPERATIONS'', 74, ''Detail - retrait entre equivalents 5k et 10k USD'', ''COUVERT'', ''Mouvements RETR et MOB_RETR'',
    ''Seuils appliques par devise : USD=5000/10000, CDF=parametres CDF.''
  FROM mouvements AS m
  INNER JOIN devises_reporting AS dr ON dr.id_devise = m.id_devise
  WHERE m.type_operation IN (''RETR'', ''MOB_RETR'') AND m.montant_operation >= dr.seuil_5k AND m.montant_operation < dr.seuil_10k
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''4. CANAUX DE DISTRIBUTION'', 152, ''Detail - operations effectuees par Mobile Banking'', ''COUVERT'', ''dbo.OPERATIONS_API + dbo.HDPM_API'',
    ''Operations API MOB_DEPO et MOB_RETR.''
  FROM mouvements AS m
  WHERE m.source_mouvement = ''API'' AND m.type_operation IN (''MOB_DEPO'', ''MOB_RETR'')
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''4. CANAUX DE DISTRIBUTION'', 153, ''Detail - Bank to Wallet'', ''PARTIEL'', ''dbo.OPERATIONS_API + dbo.HDPM_API'',
    ''Hypothese : MOB_RETR debite le compte bancaire vers le wallet ; sens a confirmer.''
  FROM mouvements AS m
  WHERE m.source_mouvement = ''API'' AND m.type_operation = ''MOB_RETR''
  UNION ALL
  SELECT m.source_mouvement, m.id_operation, m.date_operation, m.type_operation, m.montant_operation, m.id_devise,
    ''4. CANAUX DE DISTRIBUTION'', 154, ''Detail - Wallet to Bank'', ''PARTIEL'', ''dbo.OPERATIONS_API + dbo.HDPM_API'',
    ''Hypothese : MOB_DEPO credite le compte bancaire depuis le wallet ; sens a confirmer.''
  FROM mouvements AS m
  WHERE m.source_mouvement = ''API'' AND m.type_operation = ''MOB_DEPO''
) AS md
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = md.id_devise
UNION ALL
SELECT
  ''149_DETAIL_REMBOURSEMENTS_ANTICIPES'',
  ''REMBOURSEMENT_ANTICIPE'',
  CAST(''3. PRODUIT - SERVICE - OPERATIONS'' AS varchar(255)),
  CAST(142 AS int),
  CAST(''Detail - credits rembourses anticipativement'' AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  ra.date_operation,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  ra.id_operation,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(''DETAIL_SOURCE_REPORTING_149'' AS varchar(255)),
  CAST(''COUVERT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  ra.id_devise,
  CAST(dv.CODE AS varchar(255)),
  ra.montant,
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''dbo.OPERATIONS_CRD.REMB_ANTICIPER + dbo.OPERATIONS'' AS varchar(1000)),
  CAST(CONCAT(''ID_PRET='', ISNULL(CAST(ra.ID_PRET AS varchar(255)), ''''), '' ; remboursement anticipe detaille de la periode.'') AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM remboursements_anticipes AS ra
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = ra.id_devise
UNION ALL
SELECT
  ''150_ALERTES_LBC_FT'',
  ''ALERTE'',
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(a.TYPE_ALERTE AS varchar(255)),
  @date_debut,
  @date_fin,
  a.date_alerte,
  CAST(NULL AS date),
  a.date_operation,
  CAST(a.ID_ADHERENT AS varchar(255)),
  CAST(a.ID_ADHERENT AS varchar(255)),
  CAST(a.NOM AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(a.NUM_ALERTE AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  COALESCE(CAST(a.ID_OPERATION_PERFECT AS varchar(255)), CAST(a.ID_OPERATION AS varchar(255))),
  CAST(a.ID_TYPE_OPERATION AS varchar(255)),
  CAST(a.TYPE_ALERTE AS varchar(255)),
  CAST(a.DESCRIPTION_ALERTE AS varchar(1000)),
  CAST(a.ETAT_ALERTE AS varchar(255)),
  CASE WHEN a.est_traitee = 1 THEN ''TRAITEE_SELON_REGLE_PROVISOIRE'' ELSE ''A_REVOIR'' END,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  a.ID_DEVISE,
  CAST(dv.CODE AS varchar(255)),
  a.montant,
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(a.niveau_risque AS varchar(255)),
  CAST(a.profil_risque AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''dbo.LAB_ALERTES'' AS varchar(1000)),
  CAST(''Piste detaillee des alertes de la periode.'' AS varchar(1000)),
  CAST(a.ID_POINT_SERVICE AS varchar(255)),
  CAST(a.MOTIF_ETAT_ALERTE AS varchar(255)),
  CAST(CASE WHEN UPPER(ISNULL(a.TYPE_ALERTE, '''')) LIKE ''%FRACTION%'' OR UPPER(ISNULL(a.DESCRIPTION_ALERTE, '''')) LIKE ''%FRACTION%'' THEN 1 ELSE 0 END AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM alertes_periode AS a
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = a.ID_DEVISE
UNION ALL
SELECT
  ''151_DECLARATIONS_SOUPCON_CENTIF'',
  ''DECLARATION'',
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(source_declaration AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  date_declaration,
  CAST(NULL AS date),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(personne_declaree AS varchar(255)),
  CAST(numero_compte AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(reference_interne AS varchar(255)),
  CAST(reference_externe AS varchar(255)),
  CAST(id_declaration AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CASE WHEN est_annulee = 1 THEN ''ANNULEE'' ELSE ''ACTIVE'' END,
  CAST(NULL AS varchar(255)),
  CAST(source_declaration AS varchar(255)),
  CAST(NULL AS int),
  CAST(devise_texte AS varchar(255)),
  montant,
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''dbo.LAB_DECLARATION_SOUPCONS + dbo.LAB_DECLARATION_CENTIF'' AS varchar(1000)),
  CAST(''Declarations reglementaires detaillees ; ne pas additionner sans controle des doublons.'' AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  operation_fractionnee,
  operation_gel_fonds,
  operation_haut_risque,
  soupcon_blanchiment,
  soupcon_financement_terrorisme,
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM declarations
UNION ALL
SELECT
  ''152_PROFILS_RISQUE_CLIENTS'',
  ''PROFIL_RISQUE'',
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(profil_risque AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(date_inscription AS date),
  CAST(id_adherent_lab AS varchar(255)),
  CAST(code_adherent AS varchar(255)),
  CAST(nom_adherent AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(id_adherent_lab AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS decimal(38, 2)),
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(niveau_risque AS varchar(255)),
  CAST(profil_risque AS varchar(255)),
  CASE WHEN anomalie_adherent_introuvable = 1 THEN ''CRITIQUE'' ELSE NULL END,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''dbo.LAB_ADHERENT_PROFIL_RISQUES + dbo.ADHERENTS'' AS varchar(1000)),
  CAST(CONCAT(''Code niveau='', ISNULL(code_niveau_risque, ''''), '' ; couleur='', ISNULL(couleur_risque, ''''), '' ; manuel='', ISNULL(CAST(risque_attribue_manuellement AS varchar(10)), '''')) AS varchar(1000)),
  CAST(point_service_lab AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(anomalie_adherent_introuvable AS bit),
  CAST(NULL AS bit)
FROM profils_clients
UNION ALL
SELECT
  ''153_REFERENTIEL_SANCTIONS'',
  ''BLACKLIST'',
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(type_liste AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  date_inscription,
  CAST(id_blacklist AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(COALESCE(NULLIF(nom_principal, ''''), NULLIF(designation, ''''), identifiant_liste) AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(identifiant_liste AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(id_blacklist AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(CONCAT(''Designation='', ISNULL(designation, ''''), '' ; autres noms='', ISNULL(autres_noms, ''''), '' ; pseudos='', ISNULL(pseudos, ''''), '' ; pieces='', ISNULL(autres_pieces, '''')) AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''REFERENTIEL_SEULEMENT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS decimal(38, 2)),
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(regime_sanction AS varchar(255)),
  CAST(type_personne AS varchar(255)),
  CASE WHEN anomalie_identite_absente = 1 THEN ''CRITIQUE'' ELSE NULL END,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''dbo.LAB_BLACKLISTS et tables de noms/pieces/pseudos'' AS varchar(1000)),
  CAST(CONCAT(''Nationalite='', ISNULL(nationalite, ''''), '' ; NIN='', ISNULL(NIN, ''''), '' ; fondement='', ISNULL(fondement_juridique, '''')) AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(anomalie_identite_absente AS bit)
FROM blacklist
UNION ALL
SELECT
  ''154_COMPTES_DORMANTS_REACTIVES'',
  ''REACTIVATION_COMPTE'',
  CAST(NULL AS varchar(255)),
  CAST(149 AS int),
  CAST(''Compte dormant reactive'' AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  rc.date_operation,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(rc.numero_compte AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(rc.NUM_TRANSACTION AS varchar(255)),
  CAST(rc.NUMERO_RECU AS varchar(255)),
  CAST(rc.id_reactivation AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(rc.motif_cloture AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''COUVERT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  rc.id_devise,
  CAST(dv.CODE AS varchar(255)),
  rc.montant,
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''dbo.REACTIVATION_COMPTE_EPG + dbo.OPERATIONS'' AS varchar(1000)),
  CAST(CONCAT(''Cloture='', CONVERT(varchar(10), rc.DATE_CLOTURE, 23), '' ; reouverture='', CONVERT(varchar(10), rc.DATE_REOUVERTURE, 23), '' ; utilisateur_saisie='', ISNULL(CAST(rc.ID_UTILISATEUR AS varchar(20)), ''''), '' ; utilisateur_validation='', ISNULL(CAST(rc.ID_UTILISATEUR_VALIDE AS varchar(20)), '''')) AS varchar(1000)),
  CAST(rc.ID_POINT_SERVICE AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM reactivations AS rc
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = rc.id_devise
UNION ALL
SELECT
  ''155_QUALITE_DONNEES_LBC_FT'',
  ''CONTROLE_QUALITE'',
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(controle AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS decimal(38, 2)),
  CAST(NULL AS decimal(38, 2)),
  CAST(nombre_anomalies AS bigint),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(severite AS varchar(255)),
  CAST(controle AS varchar(255)),
  CAST(nombre_anomalies AS bigint),
  CAST(action_recommandee AS varchar(1000)),
  CAST(''Controles de coherence du dispositif LBC-FT'' AS varchar(1000)),
  CAST(''Une ligne par controle qualite ; prioriser CRITIQUE puis ELEVEE.'' AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM controles_qualite
UNION ALL
SELECT
  ''038_SYNTHESE_HISTORIQUE_LBC_FT'',
  ''SYNTHESE_FLUX'',
  CAST(s.section AS varchar(255)),
  CAST(s.ligne_excel AS int),
  CAST(s.rubrique AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(''SYNTHESE'' AS varchar(255)),
  CAST(''COUVERT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  s.id_devise,
  CAST(dv.CODE AS varchar(255)),
  CAST(NULL AS decimal(38, 2)),
  s.volume,
  s.nombre,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(NULL AS varchar(1000)),
  CAST(''Logique autonome de la requete 38 : OPERATIONS/HDPM et sources API'' AS varchar(1000)),
  CAST(s.commentaire AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM synthese_038 AS s
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = s.id_devise
UNION ALL
SELECT
  ''039_FRACTIONNEMENT_POTENTIEL'',
  ''FRACTIONNEMENT'',
  CAST(''SURVEILLANCE LBC-FT'' AS varchar(255)),
  CAST(NULL AS int),
  CAST(''Fractionnement potentiel'' AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  f.date_operation,
  CAST(f.ID_ADHERENT AS varchar(255)),
  CAST(f.code_adherent AS varchar(255)),
  CAST(f.NOM_ADHERENT AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(f.type_mouvement AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''Plusieurs mouvements unitaires sous le seuil mais cumul journalier au-dessus.'' AS varchar(1000)),
  CAST(''SIGNAL_DETECTE'' AS varchar(255)),
  CAST(''A_REVOIR'' AS varchar(255)),
  CAST(''COUVERT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  f.id_devise,
  CAST(dv.CODE AS varchar(255)),
  f.montant_max_unitaire,
  f.montant_cumule,
  f.nb_operations,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''ELEVEE'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(''Examiner les operations sources et documenter la justification economique du cumul.'' AS varchar(1000)),
  CAST(''Logique autonome de la requete 39 : mouvements client sous seuil regroupes par jour et devise'' AS varchar(1000)),
  CAST(
    CONCAT(
      ''Seuil='', CAST(f.seuil_reference AS varchar(50)),
      '' ; type_client='', ISNULL(CAST(f.type_client AS varchar(255)), ''''),
      '' ; code_type_client='', ISNULL(CAST(f.code_type_client AS varchar(255)), ''''),
      '' ; montant_max_unitaire stocke dans montant ; montant_cumule stocke dans volume.''
    ) AS varchar(1000)
  ),
  CAST(NULL AS varchar(255)),
  CAST(''FRACTIONNEMENT_SOUS_SEUIL'' AS varchar(255)),
  CAST(1 AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM fractionnements AS f
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = f.id_devise
UNION ALL
SELECT
  ''048_TROUS_COUVERTURE_LBC_FT'',
  ''COUVERTURE'',
  CAST(''COUVERTURE DU DISPOSITIF'' AS varchar(255)),
  CAST(NULL AS int),
  c.rubrique_reporting,
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(NULL AS date),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(''REFERENTIEL_COUVERTURE'' AS varchar(255)),
  c.statut_couverture,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS int),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS decimal(38, 2)),
  CAST(NULL AS decimal(38, 2)),
  CAST(1 AS bigint),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(
    CASE
      WHEN c.statut_couverture = ''NON_COUVERT'' THEN ''CRITIQUE''
      WHEN c.statut_couverture = ''PARTIEL'' THEN ''ELEVEE''
      ELSE ''INFORMATION''
    END AS varchar(255)
  ),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  c.prerequis_mapping,
  c.source_identifiee,
  CAST(''Checklist autonome issue de la requete 48.'' AS varchar(1000)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM couverture_conformite AS c
UNION ALL
SELECT
  ''057_GROS_MOUVEMENTS_PERIODE'',
  ''GROS_MOUVEMENT_AGREGE'',
  CAST(''SURVEILLANCE FINANCIERE'' AS varchar(255)),
  CAST(NULL AS int),
  CAST(''Gros mouvements superieurs au seuil de revue'' AS varchar(255)),
  @date_debut,
  @date_fin,
  CAST(NULL AS date),
  CAST(NULL AS date),
  g.mois,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''GROS_MOUVEMENT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''Aggregation mensuelle des mouvements superieurs au seuil de revue.'' AS varchar(1000)),
  CAST(''SIGNAL_DETECTE'' AS varchar(255)),
  CAST(''A_REVOIR'' AS varchar(255)),
  CAST(''COUVERT'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  g.id_devise,
  CAST(dv.CODE AS varchar(255)),
  g.plus_gros_mouvement,
  g.volume_total,
  g.nb_gros_mouvements,
  CAST(NULL AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(''ELEVEE'' AS varchar(255)),
  CAST(NULL AS varchar(255)),
  CAST(NULL AS bigint),
  CAST(''Examiner les plus gros mouvements et rapprocher les pieces et justificatifs du point de service.'' AS varchar(1000)),
  CAST(''Logique autonome de la requete 57 : dbo.HDPM + dbo.HDPM_API'' AS varchar(1000)),
  CAST(
    CONCAT(
      ''Seuil='', CAST(g.seuil_reference AS varchar(50)),
      '' ; point_service='', ISNULL(g.code_point_service, ''''),
      '' - '', ISNULL(g.nom_point_service, ''''),
      '' ; plus_gros_mouvement stocke dans montant ; volume_total stocke dans volume.''
    ) AS varchar(1000)
  ),
  CAST(CONCAT(ISNULL(g.code_point_service, ''''), '' - '', ISNULL(g.nom_point_service, '''')) AS varchar(255)),
  CAST(''MOUVEMENT_SUPERIEUR_SEUIL'' AS varchar(255)),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit),
  CAST(NULL AS bit)
FROM gros_mouvements_057 AS g
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = g.id_devise
)
INSERT INTO BB_VISION_REPORTING.rpt.f_conformite (
    analyse,
    type_element,
    section,
    ligne_reporting,
    rubrique,
    date_debut,
    date_fin,
    date_evenement,
    code_client,
    nom_client,
    numero_compte,
    numero_alerte,
    reference_interne,
    reference_externe,
    numero_operation,
    type_operation,
    description,
    etat,
    statut_revue,
    statut_couverture,
    origine_declaration,
    devise,
    montant,
    volume,
    nombre,
    niveau_risque,
    profil_risque,
    severite,
    action_recommandee,
    origine_donnee,
    commentaire,
    point_service,
    motif,
    indicateurs,
    batch_id
)
SELECT
  CASE analyse_source
    WHEN ''038_SYNTHESE_HISTORIQUE_LBC_FT'' THEN ''38 - Synthese historique LBC-FT''
    WHEN ''039_FRACTIONNEMENT_POTENTIEL'' THEN ''39 - Fractionnement potentiel''
    WHEN ''048_TROUS_COUVERTURE_LBC_FT'' THEN ''48 - Couverture du dispositif LBC-FT''
    WHEN ''057_GROS_MOUVEMENTS_PERIODE'' THEN ''57 - Gros mouvements par periode''
    WHEN ''149_REPORTING_LBC_FT'' THEN ''149 - Reporting LBC-FT''
    WHEN ''149_DETAIL_MOUVEMENTS_REPORTING_LBC_FT'' THEN ''149 - Detail des mouvements du reporting''
    WHEN ''149_DETAIL_REMBOURSEMENTS_ANTICIPES'' THEN ''149 - Remboursements anticipes''
    WHEN ''150_ALERTES_LBC_FT'' THEN ''150 - Alertes LBC-FT''
    WHEN ''151_DECLARATIONS_SOUPCON_CENTIF'' THEN ''151 - Declarations de soupcon CENTIF''
    WHEN ''152_PROFILS_RISQUE_CLIENTS'' THEN ''152 - Profils de risque clients''
    WHEN ''153_REFERENTIEL_SANCTIONS'' THEN ''153 - Referentiel sanctions''
    WHEN ''154_COMPTES_DORMANTS_REACTIVES'' THEN ''154 - Comptes dormants reactives''
    WHEN ''155_QUALITE_DONNEES_LBC_FT'' THEN ''155 - Qualite des donnees LBC-FT''
    ELSE analyse_source
  END AS analyse,
  CASE type_ligne
    WHEN ''REPORTING'' THEN ''Reporting agrege''
    WHEN ''MOUVEMENT_OPERATION'' THEN ''Mouvement''
    WHEN ''REMBOURSEMENT_ANTICIPE'' THEN ''Remboursement anticipe''
    WHEN ''ALERTE'' THEN ''Alerte''
    WHEN ''DECLARATION'' THEN ''Declaration''
    WHEN ''PROFIL_RISQUE'' THEN ''Profil de risque''
    WHEN ''BLACKLIST'' THEN ''Sanction''
    WHEN ''REACTIVATION_COMPTE'' THEN ''Reactivation de compte''
    WHEN ''CONTROLE_QUALITE'' THEN ''Controle qualite''
    WHEN ''SYNTHESE_FLUX'' THEN ''Synthese des flux''
    WHEN ''FRACTIONNEMENT'' THEN ''Fractionnement''
    WHEN ''COUVERTURE'' THEN ''Couverture''
    WHEN ''GROS_MOUVEMENT_AGREGE'' THEN ''Gros mouvement agrege''
    ELSE type_ligne
  END AS type_element,
  section,
  ligne_excel AS ligne_reporting,
  rubrique,
  date_debut,
  date_fin,
  COALESCE(date_alerte, date_declaration, date_operation) AS date_evenement,
  COALESCE(NULLIF(code_adherent, ''''), client_id) AS code_client,
  nom_client,
  numero_compte,
  numero_alerte,
  reference_interne,
  reference_externe,
  id_operation AS numero_operation,
  type_operation,
  description_alerte AS description,
  etat_alerte AS etat,
  statut_revue_conformite AS statut_revue,
  statut_couverture,
  source_declaration AS origine_declaration,
  devise,
  montant,
  volume,
  nombre,
  niveau_risque,
  profil_risque,
  severite,
  action_recommandee,
  source_donnee AS origine_donnee,
  commentaire,
  point_service,
  motif_etat AS motif,
  NULLIF(
    CONCAT_WS(
      '' | '',
      CASE WHEN operation_fractionnee = 1 THEN ''Fractionnement potentiel'' END,
      CASE WHEN operation_gel_fonds = 1 THEN ''Gel des fonds'' END,
      CASE WHEN operation_haut_risque = 1 THEN ''Operation a haut risque'' END,
      CASE WHEN soupcon_blanchiment = 1 THEN ''Soupcon de blanchiment'' END,
      CASE WHEN soupcon_financement_terrorisme = 1 THEN ''Soupcon de financement du terrorisme'' END,
      CASE WHEN anomalie_adherent_introuvable = 1 THEN ''Client introuvable'' END,
      CASE WHEN anomalie_identite_absente = 1 THEN ''Identite absente'' END
    ),
    ''''
  ) AS indicateurs,
  @batch_id AS batch_id
FROM socle
OPTION (MAXDOP 1, RECOMPILE, MAX_GRANT_PERCENT = 10);
';

    BEGIN TRY
        EXEC sys.sp_executesql
            @sql,
            N'@date_debut date, @date_fin date, @id_devise_reporting int, @seuil_5k_usd_cdf decimal(38,2), @seuil_10k_usd_cdf decimal(38,2), @batch_id bigint',
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = @id_devise_reporting,
            @seuil_5k_usd_cdf = @seuil_5k_usd_cdf,
            @seuil_10k_usd_cdf = @seuil_10k_usd_cdf,
            @batch_id = @batch_id;

        IF @own_batch = 1
        BEGIN
            DECLARE @rows bigint;
            SELECT @rows = COUNT_BIG(*) FROM rpt.f_conformite WHERE batch_id = @batch_id;
            DECLARE @success_message varchar(max) = CONCAT('Chargement rpt.f_conformite termine. Lignes inserees : ', @rows, '.');
            EXEC ctl.end_batch
                @batch_id = @batch_id,
                @status = 'SUCCESS',
                @message = @success_message;
        END;
    END TRY
    BEGIN CATCH
        IF @own_batch = 1 AND @batch_id IS NOT NULL
        BEGIN
            DECLARE @error_message nvarchar(max) = ERROR_MESSAGE();
            EXEC ctl.end_batch
                @batch_id = @batch_id,
                @status = 'FAILED',
                @message = @error_message;
        END;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE rpt.load_f_clients
    @source_database sysname = N'BB_VISION_PRO_TEST',
    @date_debut date,
    @date_fin date,
    @id_devise_reporting int = NULL,
    @batch_id bigint = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @date_debut IS NULL OR @date_fin IS NULL
        THROW 51100, 'Les parametres @date_debut et @date_fin sont obligatoires.', 1;

    IF @date_debut > @date_fin
        THROW 51101, '@date_debut ne peut pas etre posterieure a @date_fin.', 1;

    IF DB_ID(@source_database) IS NULL
        THROW 51102, 'La base source demandee est introuvable.', 1;

    DECLARE @own_batch bit = 0;
    IF @batch_id IS NULL
    BEGIN
        SET @own_batch = 1;
        EXEC ctl.start_batch
            @source_database = @source_database,
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = @id_devise_reporting,
            @batch_id = @batch_id OUTPUT;
    END;

    IF @id_devise_reporting IS NULL
    BEGIN
        /*
          Chargement toutes devises.

          Sur la base Perfect Vision locale, les devises utiles au reporting sont :
          - 1 = USD ;
          - 2 = CDF.

          On charge volontairement devise par devise pour eviter les plans SQL Server trop gourmands en memoire
          lorsque la requete 157 est executee en une seule fois avec @id_devise_reporting = NULL.
        */
        DELETE FROM rpt.f_clients
        WHERE date_debut = @date_debut
          AND date_fin = @date_fin;

        EXEC rpt.load_f_clients
            @source_database = @source_database,
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = 1,
            @batch_id = @batch_id OUTPUT;

        EXEC rpt.load_f_clients
            @source_database = @source_database,
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = 2,
            @batch_id = @batch_id OUTPUT;

        IF @own_batch = 1
        BEGIN
            DECLARE @rows_all_devises bigint;
            SELECT @rows_all_devises = COUNT_BIG(*) FROM rpt.f_clients WHERE batch_id = @batch_id;
            DECLARE @success_message_all_devises varchar(max) = CONCAT('Chargement rpt.f_clients toutes devises termine. Lignes inserees : ', @rows_all_devises, '.');
            EXEC ctl.end_batch
                @batch_id = @batch_id,
                @status = 'SUCCESS',
                @message = @success_message_all_devises;
        END;

        RETURN;
    END;

    DECLARE @sql nvarchar(max) = N'
USE ' + QUOTENAME(@source_database) + N';

DECLARE @devise_code varchar(10) = NULL;
SELECT @devise_code = CODE
FROM dbo.DEVISES
WHERE ID = @id_devise_reporting;

DELETE FROM BB_VISION_REPORTING.rpt.f_clients
WHERE date_debut = @date_debut
  AND date_fin = @date_fin
  AND (
        @id_devise_reporting IS NULL
        OR devise = @devise_code
      );

/*
 157. Socle clients par devise pour le tableau de bord
 Export : 157_cycle_clients_socle_indicateurs_par_client_et_devise
 Objectif : alimenter une feuille Power BI Clients avec une ligne par client et par devise utile.
 Lecture :
 - client actif = adherent Perfect valide, non parti a @date_fin et avec au moins un compte ouvert;
 - compte dormant = compte ouvert sans mouvement depuis au moins 24 mois, selon la logique de la requete 110;
 - credit a rembourser = echeance TABAMOR comprise entre @date_debut et @date_fin;
 - interet de credit = interet que le client doit payer sur les echeances de la periode;
 - interet epargne credite = interet effectivement credite au client sur epargne ou DAT pendant la periode;
 - DAT a echeance = cycle DAT dont DATE_FIN est comprise dans la periode.
 La requete est autonome et ne depend d aucune vue ni d une autre requete du catalogue.
 Renseigner @id_devise_reporting avec 1 ou 2 pour filtrer une devise; laisser NULL pour toutes les devises.
 Niveau d''importance de la requete : 10
 Usage operationnel : Alimenter la feuille Clients et les indicateurs transversaux par devise.
 Periodicite recommandee : Mensuel et a chaque actualisation du tableau de bord clients
 */
WITH clients AS (
  SELECT
    a.ID AS id_client,
    a.CODE AS code_client,
    a.NOM_ADHERENT AS nom_client,
    ta.LIBELLE AS type_client,
    a.DATE_INSCRIPTION AS date_adhesion,
    a.EST_PERFECT AS client_perfect,
    a.EST_VALIDE AS client_valide,
    ps.CODE AS code_agence,
    ps.NOM AS agence
  FROM dbo.ADHERENTS AS a
  LEFT JOIN dbo.TYPES_ADHERENT AS ta
    ON ta.ID = a.ID_TYPE_ADHERENT
  LEFT JOIN dbo.POINTS_SERVICE AS ps
    ON ps.ID = COALESCE(a.ID_POINT_SERVICE, a.ID_AGENCE)
  WHERE
    a.DATE_INSCRIPTION <= @date_fin
    AND ISNULL(a.EST_PERFECT, 0) = 1
), departs_actifs AS (
  SELECT
    da.ID_ADHERENT AS id_client,
    MAX(da.DATE_DEPART) AS date_depart
  FROM dbo.DEPARTS_ADHERENT AS da
  WHERE
    da.DATE_DEPART <= @date_fin
    AND (
      da.DATE_RETOUR IS NULL OR da.DATE_RETOUR > @date_fin
    )
  GROUP BY
    da.ID_ADHERENT
), devises_client AS (
  SELECT
    ca.ID_ADHERENT AS id_client,
    c.ID_DEVISE AS id_devise
  FROM dbo.COMPTES_ADHERENT AS ca
  INNER JOIN dbo.COMPTES AS c
    ON c.ID = ca.ID
  WHERE
    c.DATE_OUVERTURE <= @date_fin
  UNION
  SELECT
    dem.ID_ADHERENT,
    p.ID_DEVISE
  FROM dbo.PRETS AS p
  INNER JOIN dbo.DOSSIERS_CREDIT AS dc
    ON dc.ID = p.ID_DOSSIER_CREDIT
  INNER JOIN dbo.DEMANDES_CREDIT AS dem
    ON dem.ID = dc.ID_DEMANDE
  WHERE
    p.DATE_EFFET <= @date_fin
  UNION
  SELECT
    dd.ID_ADHERENT,
    c.ID_DEVISE
  FROM dbo.DOSSIERS_DAT AS dd
  INNER JOIN dbo.COMPTES AS c
    ON c.ID = dd.ID_COMPTE_DAT
  WHERE
    dd.DATE_EFFET <= @date_fin
), grain_client_devise AS (
  SELECT
    c.id_client,
    dc.id_devise
  FROM clients AS c
  LEFT JOIN devises_client AS dc
    ON dc.id_client = c.id_client
  WHERE
    @id_devise_reporting IS NULL
    OR dc.id_devise = @id_devise_reporting
), cloture_compte AS (
  SELECT
    cc.ID_COMPTE AS id_compte,
    MAX(
      CASE
        WHEN cc.DATE_CLOTURE <= @date_fin
         AND (
           cc.DATE_REOUVERTURE IS NULL
           OR cc.DATE_REOUVERTURE > @date_fin
         )
        THEN 1
        ELSE 0
      END
    ) AS compte_cloture
  FROM dbo.CLOTURE_COMPTE AS cc
  GROUP BY
    cc.ID_COMPTE
), mouvements_comptes AS (
  SELECT
    m.ID_COMPTE AS id_compte,
    MAX(
      CASE
        WHEN ISNULL(m.ID_TYPE_OPERATION, '''') <> ''REPR''
        THEN m.DATE_OPERATION
      END
    ) AS date_derniere_operation,
    SUM(
      CASE
        WHEN m.SENS = ''D'' THEN -ISNULL(m.MONTANT_OPERATION, 0)
        WHEN m.SENS = ''C'' THEN ISNULL(m.MONTANT_OPERATION, 0)
        ELSE 0
      END
    ) AS solde_compte
  FROM (
    SELECT
      h.ID_COMPTE,
      h.DATE_OPERATION,
      h.ID_TYPE_OPERATION,
      h.SENS,
      h.MONTANT_OPERATION
    FROM dbo.HDPM AS h
    WHERE
      h.DATE_OPERATION <= @date_fin
    UNION ALL
    SELECT
      h.ID_COMPTE,
      h.DATE_OPERATION,
      h.ID_TYPE_OPERATION,
      h.SENS,
      h.MONTANT_OPERATION
    FROM dbo.HDPM_API AS h
    WHERE
      h.DATE_OPERATION <= @date_fin
  ) AS m
  GROUP BY
    m.ID_COMPTE
), comptes_client AS (
  SELECT
    ca.ID_ADHERENT AS id_client,
    c.ID_DEVISE AS id_devise,
    COUNT(DISTINCT c.ID) AS nombre_comptes,
    COUNT(
      DISTINCT CASE
        WHEN c.DATE_OUVERTURE <= @date_fin
         AND ISNULL(cl.compte_cloture, 0) = 0
         AND UPPER(ISNULL(c.ETAT, ''O'')) IN (''A'', ''O'', ''ACTIF'', ''ACTIVE'', ''OUVERT'', ''OUVERTE'', ''OPEN'')
        THEN c.ID
      END
    ) AS nombre_comptes_ouverts,
    COUNT(
      DISTINCT CASE
        WHEN ISNULL(cl.compte_cloture, 0) = 1
          OR UPPER(ISNULL(c.ETAT, '''')) IN (''C'', ''CLOTURE'', ''CLOTUREE'', ''CLOSED'')
        THEN c.ID
      END
    ) AS nombre_comptes_clotures,
    COUNT(
      DISTINCT CASE
        WHEN UPPER(ISNULL(c.ETAT, '''')) IN (''B'', ''BLOQUE'', ''BLOQUEE'', ''BLOCKED'', ''G'', ''GELE'', ''GELEE'')
          OR UPPER(ISNULL(cai.STATUT, '''')) IN (''B'', ''BLOQUE'', ''BLOQUEE'', ''BLOCKED'', ''G'', ''GELE'', ''GELEE'')
        THEN c.ID
      END
    ) AS nombre_comptes_bloques,
    COUNT(
      DISTINCT CASE
        WHEN c.DATE_OUVERTURE <= @date_fin
         AND ISNULL(cl.compte_cloture, 0) = 0
         AND UPPER(ISNULL(c.ETAT, ''O'')) IN (''A'', ''O'', ''ACTIF'', ''ACTIVE'', ''OUVERT'', ''OUVERTE'', ''OPEN'')
         AND DATEDIFF(
           MONTH,
           COALESCE(mc.date_derniere_operation, c.DATE_OUVERTURE, @date_debut),
           @date_fin
         ) >= 24
        THEN c.ID
      END
    ) AS nombre_comptes_dormants,
    COUNT(
      DISTINCT CASE
        WHEN c.DATE_OUVERTURE <= @date_fin
         AND ISNULL(cl.compte_cloture, 0) = 0
         AND UPPER(ISNULL(c.ETAT, ''O'')) IN (''A'', ''O'', ''ACTIF'', ''ACTIVE'', ''OUVERT'', ''OUVERTE'', ''OPEN'')
         AND DATEDIFF(
           MONTH,
           COALESCE(mc.date_derniere_operation, c.DATE_OUVERTURE, @date_debut),
           @date_fin
         ) BETWEEN 12 AND 23
        THEN c.ID
      END
    ) AS nombre_comptes_inactifs,
    SUM(
      CASE
        WHEN c.DATE_OUVERTURE <= @date_fin
         AND ISNULL(cl.compte_cloture, 0) = 0
         AND ca.TYPE_CPTE_ADH IN (''CAU'', ''DAT'', ''PLN'', ''DAV'', ''TNT'')
        THEN ISNULL(mc.solde_compte, 0)
        ELSE 0
      END
    ) AS solde_epargne,
    MAX(mc.date_derniere_operation) AS date_derniere_operation
  FROM dbo.COMPTES_ADHERENT AS ca
  INNER JOIN dbo.COMPTES AS c
    ON c.ID = ca.ID
  LEFT JOIN dbo.COMPTES_ADHERENT_INFO AS cai
    ON cai.ID = c.ID
  LEFT JOIN cloture_compte AS cl
    ON cl.id_compte = c.ID
  LEFT JOIN mouvements_comptes AS mc
    ON mc.id_compte = c.ID
  WHERE
    c.DATE_OUVERTURE <= @date_fin
    AND (
      @id_devise_reporting IS NULL
      OR c.ID_DEVISE = @id_devise_reporting
    )
  GROUP BY
    ca.ID_ADHERENT,
    c.ID_DEVISE
), cycles_pret_classes AS (
  SELECT
    cp.ID,
    cp.ID_PRET,
    cp.DATE_DEBUT,
    cp.DATE_CLOTURE,
    ROW_NUMBER() OVER (
      PARTITION BY cp.ID_PRET
      ORDER BY
        cp.DATE_DEBUT DESC,
        cp.NUM_CYCLE DESC,
        cp.ID DESC
    ) AS rang_cycle
  FROM dbo.CYCLES_PRET AS cp
  WHERE
    cp.DATE_DEBUT <= @date_fin
), remboursements_echeance AS (
  SELECT
    rc.ID_TABAMORT AS id_echeance,
    SUM(ISNULL(rc.CAPITAL, 0)) AS capital_rembourse,
    SUM(ISNULL(rc.INTERET, 0)) AS interet_rembourse,
    SUM(ISNULL(rc.COMMISSION, 0)) AS commission_remboursee,
    SUM(ISNULL(rc.EPARGNE, 0)) AS epargne_remboursee
  FROM dbo.REMBOURS_CRD AS rc
  INNER JOIN dbo.OPERATIONS_CRD AS oc
    ON oc.ID = rc.ID_OPERATION_CRD
  INNER JOIN dbo.OPERATIONS AS o
    ON o.ID = oc.ID_OPERATION
  WHERE
    o.DATE_OPERATION <= @date_fin
    AND ISNULL(o.ANNULE, 0) = 0
  GROUP BY
    rc.ID_TABAMORT
), echeances_client AS (
  SELECT
    dem.ID_ADHERENT AS id_client,
    p.ID_DEVISE AS id_devise,
    COUNT(DISTINCT p.ID) AS nombre_credits_echeance,
    COUNT(DISTINCT t.ID) AS nombre_echeances_credit,
    SUM(ISNULL(t.CAPITAL, 0)) AS capital_prevu,
    SUM(ISNULL(t.INTERET, 0)) AS interet_credit_prevu,
    SUM(ISNULL(t.COMMISSION, 0)) AS commission_prevue,
    SUM(ISNULL(t.EPARGNE, 0)) AS epargne_prevue,
    SUM(
      ISNULL(t.CAPITAL, 0)
      + ISNULL(t.INTERET, 0)
      + ISNULL(t.COMMISSION, 0)
      + ISNULL(t.EPARGNE, 0)
    ) AS montant_echeances_prevues,
    SUM(
      CASE
        WHEN
          ISNULL(t.CAPITAL, 0)
          + ISNULL(t.INTERET, 0)
          + ISNULL(t.COMMISSION, 0)
          + ISNULL(t.EPARGNE, 0)
          > ISNULL(re.capital_rembourse, 0)
          + ISNULL(re.interet_rembourse, 0)
          + ISNULL(re.commission_remboursee, 0)
          + ISNULL(re.epargne_remboursee, 0)
        THEN
          ISNULL(t.CAPITAL, 0)
          + ISNULL(t.INTERET, 0)
          + ISNULL(t.COMMISSION, 0)
          + ISNULL(t.EPARGNE, 0)
          - ISNULL(re.capital_rembourse, 0)
          - ISNULL(re.interet_rembourse, 0)
          - ISNULL(re.commission_remboursee, 0)
          - ISNULL(re.epargne_remboursee, 0)
        ELSE 0
      END
    ) AS montant_restant_a_rembourser
  FROM cycles_pret_classes AS cp
  INNER JOIN dbo.PRETS AS p
    ON p.ID = cp.ID_PRET
  INNER JOIN dbo.DOSSIERS_CREDIT AS dc
    ON dc.ID = p.ID_DOSSIER_CREDIT
  INNER JOIN dbo.DEMANDES_CREDIT AS dem
    ON dem.ID = dc.ID_DEMANDE
  INNER JOIN dbo.TABAMOR AS t
    ON t.ID_CYCLE_PRET = cp.ID
  LEFT JOIN remboursements_echeance AS re
    ON re.id_echeance = t.ID
  WHERE
    cp.rang_cycle = 1
    AND t.DATE_ECHEANCE BETWEEN @date_debut AND @date_fin
    AND p.DATE_EFFET <= @date_fin
    AND (
      p.DATE_PERTE IS NULL OR p.DATE_PERTE > @date_fin
    )
    AND (
      @id_devise_reporting IS NULL
      OR p.ID_DEVISE = @id_devise_reporting
    )
  GROUP BY
    dem.ID_ADHERENT,
    p.ID_DEVISE
), credits_actifs AS (
  SELECT
    dem.ID_ADHERENT AS id_client,
    p.ID_DEVISE AS id_devise,
    COUNT(DISTINCT p.ID) AS nombre_credits_actifs
  FROM cycles_pret_classes AS cp
  INNER JOIN dbo.PRETS AS p
    ON p.ID = cp.ID_PRET
  INNER JOIN dbo.DOSSIERS_CREDIT AS dc
    ON dc.ID = p.ID_DOSSIER_CREDIT
  INNER JOIN dbo.DEMANDES_CREDIT AS dem
    ON dem.ID = dc.ID_DEMANDE
  WHERE
    cp.rang_cycle = 1
    AND p.DATE_EFFET <= @date_fin
    AND (
      p.DATE_SOLDE IS NULL OR p.DATE_SOLDE > @date_fin
    )
    AND (
      p.DATE_PERTE IS NULL OR p.DATE_PERTE > @date_fin
    )
    AND (
      cp.DATE_CLOTURE IS NULL OR cp.DATE_CLOTURE > @date_fin
    )
    AND (
      @id_devise_reporting IS NULL
      OR p.ID_DEVISE = @id_devise_reporting
    )
  GROUP BY
    dem.ID_ADHERENT,
    p.ID_DEVISE
), interets_epargne AS (
  SELECT
    ca.ID_ADHERENT AS id_client,
    oe.ID_DEVISE AS id_devise,
    SUM(ISNULL(ic.MONTANT, 0)) AS interet_epargne_credite
  FROM dbo.INTERETS_CREDITEUR AS ic
  INNER JOIN dbo.OPERATIONS_EPG AS oe
    ON oe.ID = ic.ID_OPERATION_EPG
  INNER JOIN dbo.OPERATIONS AS o
    ON o.ID = oe.ID_OPERATION
  INNER JOIN dbo.COMPTES_ADHERENT AS ca
    ON ca.ID = oe.ID_COMPTE_EPG
  WHERE
    o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(o.ANNULE, 0) = 0
    AND (
      @id_devise_reporting IS NULL
      OR oe.ID_DEVISE = @id_devise_reporting
    )
  GROUP BY
    ca.ID_ADHERENT,
    oe.ID_DEVISE
  UNION ALL
  SELECT
    dd.ID_ADHERENT,
    od.ID_DEVISE,
    SUM(ISNULL(idt.MONTANT, 0))
  FROM dbo.INTERETS_DAT AS idt
  INNER JOIN dbo.OPERATIONS AS o
    ON o.ID = idt.ID_OPERATION
  INNER JOIN dbo.OPERATIONS_DAT AS od
    ON od.ID_OPERATION = o.ID
    AND od.ID_CYCLE_DAT = idt.ID_CYCLE_DAT
  INNER JOIN dbo.CYCLES_DAT AS cd
    ON cd.ID = idt.ID_CYCLE_DAT
  INNER JOIN dbo.DOSSIERS_DAT AS dd
    ON dd.ID = cd.ID_DOSSIER_DAT
  WHERE
    o.DATE_OPERATION BETWEEN @date_debut AND @date_fin
    AND ISNULL(o.ANNULE, 0) = 0
    AND (
      @id_devise_reporting IS NULL
      OR od.ID_DEVISE = @id_devise_reporting
    )
  GROUP BY
    dd.ID_ADHERENT,
    od.ID_DEVISE
), interets_epargne_client AS (
  SELECT
    ie.id_client,
    ie.id_devise,
    SUM(ie.interet_epargne_credite) AS interet_epargne_credite
  FROM interets_epargne AS ie
  GROUP BY
    ie.id_client,
    ie.id_devise
), dat_echeance AS (
  SELECT
    dd.ID_ADHERENT AS id_client,
    c.ID_DEVISE AS id_devise,
    COUNT(DISTINCT cd.ID) AS nombre_dat_echeance,
    SUM(ISNULL(cd.MONTANT, 0)) AS montant_dat_echeance,
    MIN(cd.DATE_FIN) AS premiere_echeance_dat,
    MAX(cd.DATE_FIN) AS derniere_echeance_dat
  FROM dbo.CYCLES_DAT AS cd
  INNER JOIN dbo.DOSSIERS_DAT AS dd
    ON dd.ID = cd.ID_DOSSIER_DAT
  INNER JOIN dbo.COMPTES AS c
    ON c.ID = dd.ID_COMPTE_DAT
  WHERE
    cd.DATE_FIN BETWEEN @date_debut AND @date_fin
    AND (
      cd.DATE_CLOTURE IS NULL OR cd.DATE_CLOTURE >= cd.DATE_FIN
    )
    AND (
      dd.DATE_CLOTURE IS NULL OR dd.DATE_CLOTURE >= cd.DATE_FIN
    )
    AND (
      @id_devise_reporting IS NULL
      OR c.ID_DEVISE = @id_devise_reporting
    )
  GROUP BY
    dd.ID_ADHERENT,
    c.ID_DEVISE
)
INSERT INTO BB_VISION_REPORTING.rpt.f_clients (
    date_debut,
    date_fin,
    code_client,
    nom_client,
    type_client,
    code_agence,
    agence,
    date_adhesion,
    devise,
    statut_client,
    client_actif,
    comptes,
    comptes_ouverts,
    comptes_clotures,
    comptes_bloques,
    comptes_dormants,
    comptes_inactifs,
    derniere_operation,
    solde_epargne,
    credits_actifs,
    credits_a_rembourser,
    echeances_credit,
    capital_credit_prevu,
    interet_credit_a_rembourser,
    commission_credit_prevue,
    epargne_credit_prevue,
    montant_credit_a_rembourser,
    montant_credit_restant,
    interet_epargne_credite,
    dat_a_echeance,
    montant_dat_a_echeance,
    premiere_echeance_dat,
    derniere_echeance_dat,
    avec_compte_ouvert,
    avec_compte_bloque,
    avec_compte_dormant,
    avec_credit_a_rembourser,
    avec_interet_credit_a_rembourser,
    beneficiaire_interet_epargne,
    avec_dat_a_echeance,
    batch_id
)
SELECT
  @date_debut AS date_debut,
  @date_fin AS date_fin,
  c.code_client,
  c.nom_client,
  c.type_client,
  c.code_agence,
  c.agence,
  c.date_adhesion,
  ISNULL(dv.CODE, ''Sans devise'') AS devise,
  CASE
    WHEN da.id_client IS NOT NULL THEN ''Parti''
    WHEN ISNULL(c.client_valide, 0) = 0 THEN ''Non valide''
    WHEN ISNULL(cc.nombre_comptes_ouverts, 0) = 0 THEN ''Sans compte ouvert''
    ELSE ''Actif''
  END AS statut_client,
  CASE
    WHEN da.id_client IS NULL
     AND ISNULL(c.client_valide, 0) = 1
     AND ISNULL(cc.nombre_comptes_ouverts, 0) > 0
    THEN 1 ELSE 0
  END AS client_actif,
  ISNULL(cc.nombre_comptes, 0) AS nombre_comptes,
  ISNULL(cc.nombre_comptes_ouverts, 0) AS nombre_comptes_ouverts,
  ISNULL(cc.nombre_comptes_clotures, 0) AS nombre_comptes_clotures,
  ISNULL(cc.nombre_comptes_bloques, 0) AS nombre_comptes_bloques,
  ISNULL(cc.nombre_comptes_dormants, 0) AS nombre_comptes_dormants,
  ISNULL(cc.nombre_comptes_inactifs, 0) AS nombre_comptes_inactifs,
  cc.date_derniere_operation,
  ISNULL(cc.solde_epargne, 0) AS solde_epargne,
  ISNULL(ca.nombre_credits_actifs, 0) AS nombre_credits_actifs,
  ISNULL(ec.nombre_credits_echeance, 0) AS nombre_credits_a_rembourser,
  ISNULL(ec.nombre_echeances_credit, 0) AS nombre_echeances_credit,
  ISNULL(ec.capital_prevu, 0) AS capital_credit_prevu,
  ISNULL(ec.interet_credit_prevu, 0) AS interet_credit_a_rembourser,
  ISNULL(ec.commission_prevue, 0) AS commission_credit_prevue,
  ISNULL(ec.epargne_prevue, 0) AS epargne_credit_prevue,
  ISNULL(ec.montant_echeances_prevues, 0) AS montant_credit_a_rembourser,
  ISNULL(ec.montant_restant_a_rembourser, 0) AS montant_credit_restant,
  ISNULL(ie.interet_epargne_credite, 0) AS interet_epargne_credite,
  ISNULL(de.nombre_dat_echeance, 0) AS nombre_dat_echeance,
  ISNULL(de.montant_dat_echeance, 0) AS montant_dat_echeance,
  de.premiere_echeance_dat,
  de.derniere_echeance_dat,
  CASE WHEN ISNULL(cc.nombre_comptes_ouverts, 0) > 0 THEN 1 ELSE 0 END AS client_avec_compte_ouvert,
  CASE WHEN ISNULL(cc.nombre_comptes_bloques, 0) > 0 THEN 1 ELSE 0 END AS client_avec_compte_bloque,
  CASE WHEN ISNULL(cc.nombre_comptes_dormants, 0) > 0 THEN 1 ELSE 0 END AS client_avec_compte_dormant,
  CASE WHEN ISNULL(ec.nombre_credits_echeance, 0) > 0 THEN 1 ELSE 0 END AS client_avec_credit_a_rembourser,
  CASE WHEN ISNULL(ec.interet_credit_prevu, 0) > 0 THEN 1 ELSE 0 END AS client_avec_interet_credit_a_rembourser,
  CASE WHEN ISNULL(ie.interet_epargne_credite, 0) > 0 THEN 1 ELSE 0 END AS client_beneficiaire_interet_epargne,
  CASE WHEN ISNULL(de.nombre_dat_echeance, 0) > 0 THEN 1 ELSE 0 END AS client_avec_dat_a_echeance,
  @batch_id AS batch_id
FROM grain_client_devise AS gcd
INNER JOIN clients AS c
  ON c.id_client = gcd.id_client
LEFT JOIN departs_actifs AS da
  ON da.id_client = c.id_client
LEFT JOIN dbo.DEVISES AS dv
  ON dv.ID = gcd.id_devise
LEFT JOIN comptes_client AS cc
  ON cc.id_client = gcd.id_client
  AND (
    cc.id_devise = gcd.id_devise
    OR (cc.id_devise IS NULL AND gcd.id_devise IS NULL)
  )
LEFT JOIN credits_actifs AS ca
  ON ca.id_client = gcd.id_client
  AND ca.id_devise = gcd.id_devise
LEFT JOIN echeances_client AS ec
  ON ec.id_client = gcd.id_client
  AND ec.id_devise = gcd.id_devise
LEFT JOIN interets_epargne_client AS ie
  ON ie.id_client = gcd.id_client
  AND ie.id_devise = gcd.id_devise
LEFT JOIN dat_echeance AS de
  ON de.id_client = gcd.id_client
  AND de.id_devise = gcd.id_devise
OPTION (MAXDOP 1, RECOMPILE, MAX_GRANT_PERCENT = 10);
';

    BEGIN TRY
        EXEC sys.sp_executesql
            @sql,
            N'@date_debut date, @date_fin date, @id_devise_reporting int, @batch_id bigint',
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = @id_devise_reporting,
            @batch_id = @batch_id;

        IF @own_batch = 1
        BEGIN
            DECLARE @rows bigint;
            SELECT @rows = COUNT_BIG(*) FROM rpt.f_clients WHERE batch_id = @batch_id;
            DECLARE @success_message varchar(max) = CONCAT('Chargement rpt.f_clients termine. Lignes inserees : ', @rows, '.');
            EXEC ctl.end_batch
                @batch_id = @batch_id,
                @status = 'SUCCESS',
                @message = @success_message;
        END;
    END TRY
    BEGIN CATCH
        IF @own_batch = 1 AND @batch_id IS NOT NULL
        BEGIN
            DECLARE @error_message nvarchar(max) = ERROR_MESSAGE();
            EXEC ctl.end_batch
                @batch_id = @batch_id,
                @status = 'FAILED',
                @message = @error_message;
        END;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE rpt.load_all_facts
    @source_database sysname = N'BB_VISION_PRO_TEST',
    @date_debut date,
    @date_fin date,
    @id_devise_reporting int = NULL,
    @seuil_5k_usd_cdf decimal(38, 2) = 11375000,
    @seuil_10k_usd_cdf decimal(38, 2) = 22750000
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @batch_id bigint;
    EXEC ctl.start_batch
        @source_database = @source_database,
        @date_debut = @date_debut,
        @date_fin = @date_fin,
        @id_devise_reporting = @id_devise_reporting,
        @batch_id = @batch_id OUTPUT;

    BEGIN TRY
        EXEC rpt.load_f_conformite
            @source_database = @source_database,
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = @id_devise_reporting,
            @seuil_5k_usd_cdf = @seuil_5k_usd_cdf,
            @seuil_10k_usd_cdf = @seuil_10k_usd_cdf,
            @batch_id = @batch_id OUTPUT;

        EXEC rpt.load_f_clients
            @source_database = @source_database,
            @date_debut = @date_debut,
            @date_fin = @date_fin,
            @id_devise_reporting = @id_devise_reporting,
            @batch_id = @batch_id OUTPUT;

        DECLARE @rows bigint;
        SELECT @rows =
            (SELECT COUNT_BIG(*) FROM rpt.f_conformite WHERE batch_id = @batch_id)
            + (SELECT COUNT_BIG(*) FROM rpt.f_clients WHERE batch_id = @batch_id);
        DECLARE @success_message varchar(max) = CONCAT('Chargement prioritaire Conformite + Clients termine. Lignes inserees : ', @rows, '.');

        EXEC ctl.end_batch
            @batch_id = @batch_id,
            @status = 'SUCCESS',
            @message = @success_message;
    END TRY
    BEGIN CATCH
        DECLARE @error_message nvarchar(max) = ERROR_MESSAGE();
        EXEC ctl.end_batch
            @batch_id = @batch_id,
            @status = 'FAILED',
            @message = @error_message;
        THROW;
    END CATCH;
END;
GO
