from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SQL_CATALOG = ROOT / "data" / "vision" / "requetes.sql"
MODEL_ROOT = (
    ROOT
    / "data"
    / "vision"
    / "power-bi"
    / "IMF BB Tableau de bord.SemanticModel"
    / "definition"
)
TABLES_ROOT = MODEL_ROOT / "tables"

QUERY_HEADER = re.compile(r"^\s*(\d{1,3})\.\s+(.+?)\s*$")


TABLES = {
    97: {
        "name": "F_Credit_Portefeuille",
        "description": "Photographie du portefeuille crédit, du PAR et des provisions à la date de situation.",
        "columns": [
            ("Date situation", "dateTime", "date_situation"),
            ("Code agence", "string", "code_agence_demande"),
            ("Agence", "string", "nom_agence_demande"),
            ("Produit crédit", "string", "produit"),
            ("Devise", "string", "code_devise"),
            ("Prêts actifs", "int64", "nb_prets_actifs"),
            ("Encours", "double", "encours_total"),
            ("PAR 1+", "double", "par_1_plus"),
            ("PAR 30+", "double", "par_30_plus"),
            ("PAR 90+", "double", "par_90_plus"),
            ("PAR 180+", "double", "par_180_plus"),
            ("Provision", "double", "provision_total"),
            ("Taux PAR 1+", "double", "par_1_pct"),
            ("Taux PAR 30+", "double", "par_30_pct"),
            ("Taux PAR 90+", "double", "par_90_pct"),
        ],
    },
    99: {
        "name": "F_Credit_Decaissements",
        "description": "Décaissements de crédits par mois, agence, produit, devise et type de client.",
        "columns": [
            ("Mois décaissement", "dateTime", "mois_decaissement"),
            ("Code agence", "string", "code_agence_demande"),
            ("Agence", "string", "nom_agence_demande"),
            ("Produit crédit", "string", "produit"),
            ("Devise", "string", "code_devise"),
            ("Code type client", "int64", "code_type_client"),
            ("Type client", "string", "type_client"),
            ("Prêts décaissés", "int64", "nb_prets_decaisse"),
            ("Clients décaissés", "int64", "nb_clients_decaisse"),
            ("Montant décaissé", "double", "montant_decaisse"),
            ("Montant moyen prêt", "double", "montant_moyen_pret"),
        ],
    },
    103: {
        "name": "F_Epargne_Soldes",
        "description": "Soldes d'épargne et nombre de comptes par mois, agence, produit et devise.",
        "columns": [
            ("Date situation", "dateTime", "date_situation"),
            ("Mois", "dateTime", "mois"),
            ("Code agence", "string", "code_agence_compte"),
            ("Agence", "string", "nom_agence_compte"),
            ("Produit épargne", "string", "produit_epargne"),
            ("Type compte", "string", "type_compte_adherent"),
            ("Devise", "string", "code_devise"),
            ("Comptes", "int64", "nb_comptes"),
            ("Clients", "int64", "nb_clients"),
            ("Solde épargne", "double", "solde_epargne"),
            ("Solde moyen compte", "double", "solde_moyen_compte"),
        ],
    },
    156: {
        "name": "F_Conformite",
        "description": "Socle unique du cycle conformité, avec un grain défini par le type d'élément.",
        "sql_prelude": "\n".join(
            [
                "DECLARE @seuil_5k_usd_cdf float = 11375000;",
                "DECLARE @seuil_10k_usd_cdf float = 22750000;",
                "DECLARE @id_devise_reporting int = NULL;",
            ]
        ),
        "columns": [
            ("Analyse", "string", "analyse"),
            ("Type élément", "string", "type_element"),
            ("Section", "string", "section"),
            ("Ligne reporting", "string", "ligne_reporting"),
            ("Rubrique", "string", "rubrique"),
            ("Date début", "dateTime", "date_debut"),
            ("Date fin", "dateTime", "date_fin"),
            ("Date événement", "dateTime", "date_evenement"),
            ("Code client", "string", "code_client"),
            ("Nom client", "string", "nom_client"),
            ("Numéro compte", "string", "numero_compte"),
            ("Numéro alerte", "string", "numero_alerte"),
            ("Référence interne", "string", "reference_interne"),
            ("Référence externe", "string", "reference_externe"),
            ("Numéro opération", "string", "numero_operation"),
            ("Type opération", "string", "type_operation"),
            ("Description", "string", "description"),
            ("État", "string", "etat"),
            ("Statut revue", "string", "statut_revue"),
            ("Statut couverture", "string", "statut_couverture"),
            ("Origine déclaration", "string", "origine_declaration"),
            ("Devise", "string", "devise"),
            ("Montant", "double", "montant"),
            ("Volume", "double", "volume"),
            ("Nombre", "int64", "nombre"),
            ("Niveau risque", "string", "niveau_risque"),
            ("Profil risque", "string", "profil_risque"),
            ("Sévérité", "string", "severite"),
            ("Action recommandée", "string", "action_recommandee"),
            ("Origine donnée", "string", "origine_donnee"),
            ("Commentaire", "string", "commentaire"),
            ("Point service", "string", "point_service"),
            ("Motif", "string", "motif"),
            ("Indicateurs", "string", "indicateurs"),
        ],
    },
}

TABLES.update(
    {
        96: {
            "name": "F_Credit_PAR_Detail",
            "description": "Détail du portefeuille à risque par prêt et client à la date de situation.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Code client", "string", "code_client"),
                ("Nom client", "string", "nom_client"),
                ("Numéro prêt", "string", "numero_pret"),
                ("Montant initial", "double", "montant_initial"),
                ("Encours", "double", "mtt_encours"),
                ("Jours retard", "int64", "jours_retard"),
                ("Arriéré", "double", "montant_arriere"),
                ("Provision", "double", "mtt_provision"),
                ("PAR 1-30", "double", "par_1_30"),
                ("PAR 31-60", "double", "par_31_60"),
                ("PAR 61-90", "double", "par_61_90"),
                ("PAR 91-180", "double", "par_91_180"),
                ("PAR 180+", "double", "par_180_plus"),
                ("PAR 30+", "double", "par_30_plus"),
                ("PAR 90+", "double", "par_90_plus"),
            ],
        },
        98: {
            "name": "F_Credit_Top_Encours",
            "description": "Principaux encours de crédit par client et prêt à la date de situation.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Code client", "string", "code_client"),
                ("Nom client", "string", "nom_client"),
                ("Numéro prêt", "string", "numero_pret"),
                ("Montant initial", "double", "montant_initial"),
                ("Encours", "double", "mtt_encours"),
            ],
        },
        100: {
            "name": "F_Credit_Echeances_Futures",
            "description": "Échéances de crédit futures regroupées par mois, produit et devise.",
            "columns": [
                ("Mois échéance", "dateTime", "mois_echeance"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Prêts concernés", "int64", "nb_prets_concernes"),
                ("Échéances", "int64", "nb_echeances"),
                ("Capital attendu", "double", "capital_attendu"),
                ("Intérêt attendu", "double", "interet_attendu"),
                ("Commission attendue", "double", "commission_attendue"),
                ("Épargne attendue", "double", "epargne_attendue"),
                ("Total attendu", "double", "total_attendu"),
            ],
        },
        101: {
            "name": "F_Credit_Retention",
            "description": "Rétention et renouvellement des clients crédit arrivés à échéance.",
            "columns": [
                ("Mois solde", "dateTime", "mois_solde"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Clients arrivés échéance", "int64", "nb_clients_arrives_echeance"),
                ("Prêts soldés", "int64", "nb_prets_soldes"),
                ("Montant prêts soldés", "double", "montant_prets_soldes"),
                ("Clients renouvelés", "int64", "nb_clients_renouveles"),
                ("Clients renouvelés 90j", "int64", "nb_clients_renouveles_90j"),
                ("Rétention", "double", "retention_pct"),
                ("Rétention 90j", "double", "retention_90j_pct"),
                ("Délai moyen renouvellement", "double", "delai_moyen_renouvellement_jours"),
            ],
        },
        102: {
            "name": "F_Credit_Vintage",
            "description": "Qualité des cohortes de décaissement et PAR par âge de cohorte.",
            "columns": [
                ("Cohorte décaissement", "dateTime", "cohorte_decaissement"),
                ("Âge cohorte mois", "int64", "age_cohorte_mois"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Prêts décaissés", "int64", "nb_prets_decaisse"),
                ("Montant initial cohorte", "double", "montant_initial_cohorte"),
                ("Encours restant", "double", "encours_restant"),
                ("PAR 30+", "double", "par_30_plus"),
                ("PAR 90+", "double", "par_90_plus"),
                ("PAR 30 sur initial", "double", "par_30_sur_initial_pct"),
                ("PAR 90 sur initial", "double", "par_90_sur_initial_pct"),
            ],
        },
        104: {
            "name": "F_Credit_Tranches",
            "description": "Portefeuille et PAR par tranche de montant initial.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Tranche montant", "string", "tranche_montant_initial"),
                ("Clients", "int64", "nb_clients"),
                ("Prêts", "int64", "nb_prets"),
                ("Montant initial", "double", "montant_initial_total"),
                ("Encours", "double", "encours_total"),
                ("PAR 1+", "double", "par_1_plus"),
                ("PAR 30+", "double", "par_30_plus"),
                ("PAR 90+", "double", "par_90_plus"),
                ("Taux PAR 1+", "double", "par_1_pct"),
                ("Taux PAR 30+", "double", "par_30_pct"),
                ("Taux PAR 90+", "double", "par_90_pct"),
            ],
        },
        105: {
            "name": "F_Credit_Concentration",
            "description": "Concentration du portefeuille sur les dix pour cent de prêts les plus importants.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Prêts actifs", "int64", "nb_prets_actifs"),
                ("Encours", "double", "encours_total"),
                ("Encours top 10%", "double", "encours_top_10_pct"),
                ("Prêts top 10%", "int64", "nb_prets_top_10_pct"),
                ("Part top 10%", "double", "part_top_10_pct"),
            ],
        },
        106: {
            "name": "F_Credit_Couverture",
            "description": "Couverture des arriérés et du principal par épargne, cautions et garanties.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Code client", "string", "code_client"),
                ("Nom client", "string", "nom_client"),
                ("Numéro prêt", "string", "numero_pret"),
                ("Montant initial", "double", "montant_initial"),
                ("Encours", "double", "mtt_encours"),
                ("Arriéré", "double", "montant_arriere"),
                ("Épargne client", "double", "solde_epargne_client"),
                ("Caution", "double", "solde_caution"),
                ("Garantie", "double", "valeur_garantie"),
                ("Arriéré couvert", "double", "arriere_couvert_par_epargne"),
                ("Principal couvert", "double", "principal_couvert"),
                ("Exposition nette", "double", "exposition_nette_non_couverte"),
            ],
        },
        107: {
            "name": "F_Credit_Provisions_Detail",
            "description": "Provisions de crédit détaillées sur les trois derniers mois.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Code client", "string", "code_client"),
                ("Nom client", "string", "nom_client"),
                ("Numéro prêt", "string", "numero_pret"),
                ("Montant initial", "double", "montant_initial"),
                ("Tranche montant", "string", "tranche_montant_initial"),
                ("Provision", "double", "mtt_provision"),
            ],
        },
        108: {
            "name": "F_Credit_Duree",
            "description": "Durée et nombre d'échéances restantes des prêts actifs.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Numéro prêt", "string", "numero_pret"),
                ("Code client", "string", "code_client"),
                ("Nom client", "string", "nom_client"),
                ("Date effet", "dateTime", "date_effet"),
                ("Date fin échéance", "dateTime", "date_fin_echeance"),
                ("Montant initial", "double", "montant_initial"),
                ("Échéances totales", "int64", "nb_echeances_total"),
                ("Échéances restantes", "int64", "nb_echeances_restantes"),
                ("Durée théorique mois", "int64", "duree_theorique_mois"),
                ("Tranche échéances restantes", "string", "tranche_echeances_restantes"),
                ("Tranche total échéances", "string", "tranche_total_echeances"),
            ],
        },
        109: {
            "name": "F_Credit_Tendance_PAR",
            "description": "Tendance mensuelle de l'encours et du portefeuille à risque.",
            "columns": [
                ("Date situation", "dateTime", "date_situation"),
                ("Code agence", "string", "code_agence_demande"),
                ("Agence", "string", "nom_agence_demande"),
                ("Produit crédit", "string", "produit"),
                ("Devise", "string", "code_devise"),
                ("Prêts actifs", "int64", "nb_prets_actifs"),
                ("Encours", "double", "encours_total"),
                ("PAR 1+", "double", "par_1_plus"),
                ("PAR 30+", "double", "par_30_plus"),
                ("PAR 90+", "double", "par_90_plus"),
                ("Taux PAR 30+", "double", "par_30_pct"),
            ],
        },
        157: {
            "name": "F_Clients",
            "description": "Socle analytique client-devise pour les statuts, comptes, crédits, intérêts et DAT.",
            "sql_prelude": "DECLARE @id_devise_reporting int = NULL;",
            "columns": [
                ("Date début", "dateTime", "date_debut"),
                ("Date fin", "dateTime", "date_fin"),
                ("Code client", "string", "code_client"),
                ("Nom client", "string", "nom_client"),
                ("Type client", "string", "type_client"),
                ("Code agence", "string", "code_agence"),
                ("Agence", "string", "agence"),
                ("Date adhésion", "dateTime", "date_adhesion"),
                ("Devise", "string", "devise"),
                ("Statut client", "string", "statut_client"),
                ("Client actif", "int64", "client_actif"),
                ("Comptes", "int64", "nombre_comptes"),
                ("Comptes ouverts", "int64", "nombre_comptes_ouverts"),
                ("Comptes clôturés", "int64", "nombre_comptes_clotures"),
                ("Comptes bloqués", "int64", "nombre_comptes_bloques"),
                ("Comptes dormants", "int64", "nombre_comptes_dormants"),
                ("Comptes inactifs", "int64", "nombre_comptes_inactifs"),
                ("Dernière opération", "dateTime", "date_derniere_operation"),
                ("Solde épargne", "double", "solde_epargne"),
                ("Crédits actifs", "int64", "nombre_credits_actifs"),
                ("Crédits à rembourser", "int64", "nombre_credits_a_rembourser"),
                ("Échéances crédit", "int64", "nombre_echeances_credit"),
                ("Capital crédit prévu", "double", "capital_credit_prevu"),
                ("Intérêt crédit à rembourser", "double", "interet_credit_a_rembourser"),
                ("Commission crédit prévue", "double", "commission_credit_prevue"),
                ("Épargne crédit prévue", "double", "epargne_credit_prevue"),
                ("Montant crédit à rembourser", "double", "montant_credit_a_rembourser"),
                ("Montant crédit restant", "double", "montant_credit_restant"),
                ("Intérêt épargne crédité", "double", "interet_epargne_credite"),
                ("DAT à échéance", "int64", "nombre_dat_echeance"),
                ("Montant DAT à échéance", "double", "montant_dat_echeance"),
                ("Première échéance DAT", "dateTime", "premiere_echeance_dat"),
                ("Dernière échéance DAT", "dateTime", "derniere_echeance_dat"),
                ("Avec compte ouvert", "int64", "client_avec_compte_ouvert"),
                ("Avec compte bloqué", "int64", "client_avec_compte_bloque"),
                ("Avec compte dormant", "int64", "client_avec_compte_dormant"),
                ("Avec crédit à rembourser", "int64", "client_avec_credit_a_rembourser"),
                ("Avec intérêt crédit à rembourser", "int64", "client_avec_interet_credit_a_rembourser"),
                ("Bénéficiaire intérêt épargne", "int64", "client_beneficiaire_interet_epargne"),
                ("Avec DAT à échéance", "int64", "client_avec_dat_a_echeance"),
            ],
        },
    }
)


def read_sql_catalog() -> list[str]:
    raw = SQL_CATALOG.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
    return raw.decode(encoding, errors="replace").splitlines()


def extract_queries() -> dict[int, str]:
    lines = read_sql_catalog()
    headers: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = QUERY_HEADER.match(line.strip(" /*"))
        if match:
            headers.append((index, int(match.group(1))))

    result: dict[int, str] = {}
    for position, (start, number) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        block = lines[start:end]
        comment_end = next((i for i, line in enumerate(block) if "*/" in line), None)
        sql_lines = block[comment_end + 1 :] if comment_end is not None else block
        while sql_lines and not sql_lines[-1].strip():
            sql_lines.pop()
        if sql_lines and sql_lines[-1].strip() == "/*":
            sql_lines.pop()
        result[number] = "\n".join(sql_lines).strip()
    return result


def q(name: str) -> str:
    if re.search(r"[\s\.\=\:\']", name):
        return "'" + name.replace("'", "''") + "'"
    return name


def m_text(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def build_partition(table_name: str, query_sql: str) -> list[str]:
    sql_lines = [
        m_text("SET NOCOUNT ON;"),
        (
            '"DECLARE @date_debut date = \'" & '
            'Date.ToText(pDateDebut, [Format="yyyy-MM-dd", Culture="en-US"]) & "\';"'
        ),
        (
            '"DECLARE @date_fin date = \'" & '
            'Date.ToText(pDateFin, [Format="yyyy-MM-dd", Culture="en-US"]) & "\';"'
        ),
        *[m_text(line) for line in query_sql.splitlines()],
    ]
    list_lines: list[str] = []
    for index, line in enumerate(sql_lines):
        suffix = "," if index < len(sql_lines) - 1 else ""
        list_lines.append(f"\t\t\t\t{line}{suffix}")

    return [
        f"\tpartition {table_name} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\tlet",
        (
            "\t\t\t\tSource = Sql.Database("
            "pServeur, pBaseDonnees, "
            "[CreateNavigationProperties=false, CommandTimeout=#duration(0, 0, 10, 0)]),"
        ),
        "\t\t\t\tSqlTexte = Text.Combine({",
        *list_lines,
        '\t\t\t\t}, "#(lf)"),',
        (
            "\t\t\t\tResultat = Value.NativeQuery("
            "Source, SqlTexte, null, [EnableFolding=false])"
        ),
        "\t\t\tin",
        "\t\t\t\tResultat",
    ]


def build_import_table(number: int, query_sql: str) -> str:
    spec = TABLES[number]
    name = spec["name"]
    if spec.get("sql_prelude"):
        query_sql = f"{spec['sql_prelude']}\n{query_sql}"
    lines = [
        f"/// {spec['description']}",
        f"table {name}",
        "",
    ]
    for display_name, data_type, source_column in spec["columns"]:
        lines.extend(
            [
                f"\tcolumn {q(display_name)}",
                f"\t\tdataType: {data_type}",
                "\t\tsummarizeBy: none",
                f"\t\tsourceColumn: {source_column}",
                "",
            ]
        )
    lines.extend(build_partition(name, query_sql))
    lines.extend(
        [
            "",
            f"\tannotation RequetePerfectVision = {number}",
            "\tannotation SourceLocale = BB_VISION_PRO_TEST",
            "",
        ]
    )
    return "\n".join(lines)


def build_date_table() -> str:
    return """/// Calendrier commun construit sur la plage réellement chargée dans les faits.
table D_Date

\tcolumn Date
\t\tdataType: dateTime
\t\tformatString: yyyy-MM-dd
\t\tsummarizeBy: none
\t\tsourceColumn: [Date]

\tcolumn 'Année'
\t\tdataType: int64
\t\tsummarizeBy: none
\t\tsourceColumn: [Année]

\tcolumn 'Numéro mois'
\t\tdataType: int64
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: [Numéro mois]

\tcolumn Mois
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: [Mois]
\t\tsortByColumn: 'Numéro mois'

\tcolumn 'Année-mois'
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: [Année-mois]

\tpartition D_Date = calculated
\t\tmode: import
\t\tsource = ```
\t\t\tVAR DateMin = MINX(F_Clients, F_Clients[Date début])
\t\t\tVAR DateMax = MAXX(F_Clients, F_Clients[Date fin])
\t\t\tRETURN
\t\t\t\tADDCOLUMNS(
\t\t\t\t\tCALENDAR(DateMin, DateMax),
\t\t\t\t\t"Année", YEAR([Date]),
\t\t\t\t\t"Numéro mois", MONTH([Date]),
\t\t\t\t\t"Mois", FORMAT([Date], "mmmm", "fr-FR"),
\t\t\t\t\t"Année-mois", FORMAT([Date], "yyyy-MM")
\t\t\t\t)
\t\t\t```

\tannotation PBI_ResultType = Table
"""


def build_currency_table() -> str:
    return """/// Référentiel des devises utilisées dans le reporting, sans conversion ni totalisation implicite.
table D_Devise

\tcolumn Devise
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: [Devise]

\tpartition D_Devise = calculated
\t\tmode: import
\t\tsource = DATATABLE("Devise", STRING, {{"CDF"}, {"USD"}})

\tannotation PBI_ResultType = Table
"""


def build_agency_table() -> str:
    return """/// Référentiel partagé des agences présentes dans les faits crédit et épargne.
table D_Agence

\tcolumn 'Code agence'
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: [Code agence]

\tcolumn Agence
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: [Agence]

\tpartition D_Agence = calculated
\t\tmode: import
\t\tsource = ```
\t\t\tVAR Agences =
\t\t\t\tUNION(
\t\t\t\t\tSELECTCOLUMNS(F_Credit_Portefeuille, "Code agence", F_Credit_Portefeuille[Code agence], "Agence", F_Credit_Portefeuille[Agence]),
\t\t\t\t\tSELECTCOLUMNS(F_Credit_Decaissements, "Code agence", F_Credit_Decaissements[Code agence], "Agence", F_Credit_Decaissements[Agence]),
\t\t\t\t\tSELECTCOLUMNS(F_Epargne_Soldes, "Code agence", F_Epargne_Soldes[Code agence], "Agence", F_Epargne_Soldes[Agence]),
\t\t\t\t\tSELECTCOLUMNS(F_Clients, "Code agence", F_Clients[Code agence], "Agence", F_Clients[Agence])
\t\t\t\t)
\t\t\tRETURN
\t\t\t\tFILTER(DISTINCT(Agences), NOT ISBLANK([Code agence]))
\t\t\t```

\tannotation PBI_ResultType = Table
"""


def build_measures_table() -> str:
    measures = [
        (
            "Prêts actifs",
            "Nombre de prêts actifs à la date de situation.",
            "SUM(F_Credit_Portefeuille[Prêts actifs])",
            "#,##0",
        ),
        (
            "Encours CDF",
            "Encours du portefeuille exprimé uniquement en CDF.",
            'CALCULATE(SUM(F_Credit_Portefeuille[Encours]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "Encours USD",
            "Encours du portefeuille exprimé uniquement en USD.",
            'CALCULATE(SUM(F_Credit_Portefeuille[Encours]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "PAR 1 CDF",
            "Montant du portefeuille à risque de 1 jour et plus, uniquement en CDF.",
            'CALCULATE(SUM(F_Credit_Portefeuille[PAR 1+]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "PAR 1 USD",
            "Montant du portefeuille à risque de 1 jour et plus, uniquement en USD.",
            'CALCULATE(SUM(F_Credit_Portefeuille[PAR 1+]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "PAR 30 CDF",
            "Montant du portefeuille à risque de 30 jours et plus, uniquement en CDF.",
            'CALCULATE(SUM(F_Credit_Portefeuille[PAR 30+]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "PAR 30 USD",
            "Montant du portefeuille à risque de 30 jours et plus, uniquement en USD.",
            'CALCULATE(SUM(F_Credit_Portefeuille[PAR 30+]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "PAR 90 CDF",
            "Montant du portefeuille à risque de 90 jours et plus, uniquement en CDF.",
            'CALCULATE(SUM(F_Credit_Portefeuille[PAR 90+]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "PAR 90 USD",
            "Montant du portefeuille à risque de 90 jours et plus, uniquement en USD.",
            'CALCULATE(SUM(F_Credit_Portefeuille[PAR 90+]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "Taux PAR 1 CDF",
            "PAR 1+ divisé par l'encours CDF.",
            "DIVIDE([PAR 1 CDF], [Encours CDF])",
            "0.00%",
        ),
        (
            "Taux PAR 1 USD",
            "PAR 1+ divisé par l'encours USD.",
            "DIVIDE([PAR 1 USD], [Encours USD])",
            "0.00%",
        ),
        (
            "Taux PAR 30 CDF",
            "PAR 30+ divisé par l'encours CDF.",
            "DIVIDE([PAR 30 CDF], [Encours CDF])",
            "0.00%",
        ),
        (
            "Taux PAR 30 USD",
            "PAR 30+ divisé par l'encours USD.",
            "DIVIDE([PAR 30 USD], [Encours USD])",
            "0.00%",
        ),
        (
            "Taux PAR 90 CDF",
            "PAR 90+ divisé par l'encours CDF.",
            "DIVIDE([PAR 90 CDF], [Encours CDF])",
            "0.00%",
        ),
        (
            "Taux PAR 90 USD",
            "PAR 90+ divisé par l'encours USD.",
            "DIVIDE([PAR 90 USD], [Encours USD])",
            "0.00%",
        ),
        (
            "Provision CDF",
            "Provisions sur crédits exprimées uniquement en CDF.",
            'CALCULATE(SUM(F_Credit_Portefeuille[Provision]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "Provision USD",
            "Provisions sur crédits exprimées uniquement en USD.",
            'CALCULATE(SUM(F_Credit_Portefeuille[Provision]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "Décaissements CDF",
            "Montant décaissé sur la période, uniquement en CDF.",
            'CALCULATE(SUM(F_Credit_Decaissements[Montant décaissé]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "Décaissements USD",
            "Montant décaissé sur la période, uniquement en USD.",
            'CALCULATE(SUM(F_Credit_Decaissements[Montant décaissé]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "Prêts décaissés",
            "Nombre de prêts décaissés sur la période dans le contexte de filtre actif.",
            "SUM(F_Credit_Decaissements[Prêts décaissés])",
            "#,##0",
        ),
        (
            "Épargne CDF",
            "Solde d'épargne exprimé uniquement en CDF.",
            'CALCULATE(SUM(F_Epargne_Soldes[Solde épargne]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            '#,##0" CDF"',
        ),
        (
            "Épargne USD",
            "Solde d'épargne exprimé uniquement en USD.",
            'CALCULATE(SUM(F_Epargne_Soldes[Solde épargne]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            '#,##0.00" USD"',
        ),
        (
            "Clients épargne",
            "Nombre de clients épargne dans le contexte de filtre actif.",
            "SUM(F_Epargne_Soldes[Clients])",
            "#,##0",
        ),
        (
            "Comptes épargne",
            "Nombre de comptes épargne dans le contexte de filtre actif.",
            "SUM(F_Epargne_Soldes[Comptes])",
            "#,##0",
        ),
        (
            "Comptes CDF",
            "Nombre de comptes épargne libellés en CDF.",
            'CALCULATE(SUM(F_Epargne_Soldes[Comptes]), KEEPFILTERS(D_Devise[Devise] = "CDF"))',
            "#,##0",
        ),
        (
            "Comptes USD",
            "Nombre de comptes épargne libellés en USD.",
            'CALCULATE(SUM(F_Epargne_Soldes[Comptes]), KEEPFILTERS(D_Devise[Devise] = "USD"))',
            "#,##0",
        ),
        (
            "Solde moyen CDF",
            "Solde épargne CDF divisé par le nombre de comptes CDF.",
            "DIVIDE([Épargne CDF], [Comptes CDF])",
            '#,##0" CDF"',
        ),
        (
            "Solde moyen USD",
            "Solde épargne USD divisé par le nombre de comptes USD.",
            "DIVIDE([Épargne USD], [Comptes USD])",
            '#,##0.00" USD"',
        ),
        (
            "Lignes 156",
            "Nombre de lignes du socle unique de conformité dans le contexte de filtre actif.",
            "COUNTROWS(F_Conformite)",
            "#,##0",
        ),
        (
            "Lignes sévérité",
            "Nombre de lignes ayant un niveau de sévérité renseigné.",
            "CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(NOT ISBLANK(F_Conformite[Sévérité])))",
            "#,##0",
        ),
        (
            "Analyses LBC-FT",
            "Nombre d'analyses de conformité distinctes présentes dans le socle unique.",
            "DISTINCTCOUNT(F_Conformite[Analyse])",
            "#,##0",
        ),
        (
            "Alertes",
            "Nombre de lignes de type alerte dans le socle unique.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Type élément] = "Alerte")), 0)',
            "#,##0",
        ),
        (
            "CENTIF",
            "Nombre de déclarations de soupçon ou CENTIF présentes dans le socle unique.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Type élément] = "Declaration")), 0)',
            "#,##0",
        ),
        (
            "Profils risque",
            "Nombre de profils de risque présents dans le socle unique.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Type élément] = "Profil de risque")), 0)',
            "#,##0",
        ),
        (
            "Réactivations",
            "Nombre de réactivations de comptes dormants présentes dans le socle unique.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Type élément] = "Reactivation de compte")), 0)',
            "#,##0",
        ),
        (
            "Non couverts",
            "Nombre de lignes de couverture au statut NON_COUVERT.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Statut couverture] = "NON_COUVERT")), 0)',
            "#,##0",
        ),
        (
            "Partiels",
            "Nombre de lignes de couverture au statut PARTIEL.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Statut couverture] = "PARTIEL")), 0)',
            "#,##0",
        ),
        (
            "Couverts",
            "Nombre de lignes de couverture au statut COUVERT.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Statut couverture] = "COUVERT")), 0)',
            "#,##0",
        ),
        (
            "Critiques",
            "Nombre de lignes de conformité classées CRITIQUE.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Sévérité] = "CRITIQUE")), 0)',
            "#,##0",
        ),
        (
            "Contrôles qualité",
            "Nombre de lignes de contrôle qualité présentes dans le socle unique.",
            'COALESCE(CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Type élément] = "Controle qualite")), 0)',
            "#,##0",
        ),
        (
            "Nombre déclaré",
            "Somme du champ Nombre de la requête 156 ; à lire dans le grain et la rubrique affichés.",
            "SUM(F_Conformite[Nombre])",
            "#,##0",
        ),
        (
            "Lignes surveillance",
            "Nombre de lignes actionnables de surveillance : alertes, déclarations, profils de risque, réactivations, fractionnements et gros mouvements.",
            'CALCULATE(COUNTROWS(F_Conformite), KEEPFILTERS(F_Conformite[Type élément] IN {"Alerte", "Declaration", "Profil de risque", "Reactivation de compte", "Fractionnement", "Gros mouvement agrege"}))',
            "#,##0",
        ),
        (
            "Cas surveillance",
            "Nombre de cas actionnables de surveillance dans le contexte de filtre actif.",
            "COALESCE([Lignes surveillance], 0)",
            "#,##0",
        ),
        (
            "Dossiers à revoir",
            "Nombre de cas de surveillance ayant le statut A_REVOIR.",
            'COALESCE(CALCULATE([Lignes surveillance], KEEPFILTERS(F_Conformite[Statut revue] = "A_REVOIR")), 0)',
            "#,##0",
        ),
        (
            "Clients surveillés",
            "Nombre de clients distincts rattachés aux cas actionnables de surveillance.",
            'COALESCE(CALCULATE(DISTINCTCOUNT(F_Conformite[Code client]), KEEPFILTERS(F_Conformite[Type élément] IN {"Alerte", "Declaration", "Profil de risque", "Reactivation de compte", "Fractionnement", "Gros mouvement agrege"}), KEEPFILTERS(NOT ISBLANK(F_Conformite[Code client]))), 0)',
            "#,##0",
        ),
        (
            "Lignes surveillance sévérité",
            "Nombre de cas actionnables de surveillance ayant une sévérité renseignée.",
            'CALCULATE([Lignes surveillance], KEEPFILTERS(NOT ISBLANK(F_Conformite[Sévérité])))',
            "#,##0",
        ),
        (
            "Clients",
            "Nombre de clients distincts dans le socle client-devise.",
            "DISTINCTCOUNT(F_Clients[Code client])",
            "#,##0",
        ),
        (
            "Clients actifs",
            "Nombre de clients distincts répondant à la définition opérationnelle d'un client actif.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Client actif] = 1))",
            "#,##0",
        ),
        (
            "Clients comptes ouverts",
            "Nombre de clients distincts ayant au moins un compte ouvert.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Avec compte ouvert] = 1))",
            "#,##0",
        ),
        (
            "Clients comptes bloqués",
            "Nombre de clients distincts ayant au moins un compte explicitement codé bloqué ou gelé.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Avec compte bloqué] = 1))",
            "#,##0",
        ),
        (
            "Clients comptes dormants",
            "Nombre de clients distincts ayant au moins un compte ouvert sans mouvement depuis 24 mois.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Avec compte dormant] = 1))",
            "#,##0",
        ),
        (
            "Clients crédit à rembourser",
            "Nombre de clients distincts ayant une échéance de crédit dans la période.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Avec crédit à rembourser] = 1))",
            "#,##0",
        ),
        (
            "Clients intérêt épargne",
            "Nombre de clients distincts ayant reçu un intérêt d'épargne ou de DAT pendant la période.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Bénéficiaire intérêt épargne] = 1))",
            "#,##0",
        ),
        (
            "Clients DAT à échéance",
            "Nombre de clients distincts dont un DAT arrive à échéance dans la période.",
            "CALCULATE(DISTINCTCOUNT(F_Clients[Code client]), KEEPFILTERS(F_Clients[Avec DAT à échéance] = 1))",
            "#,##0",
        ),
        (
            "Montant crédit à rembourser",
            "Montant total des échéances de crédit prévues dans la période.",
            "SUM(F_Clients[Montant crédit à rembourser])",
            "#,##0.00",
        ),
        (
            "Montant DAT à échéance",
            "Montant initial des DAT arrivant à échéance dans la période.",
            "SUM(F_Clients[Montant DAT à échéance])",
            "#,##0.00",
        ),
        (
            "Clients PAR",
            "Nombre de clients distincts présents dans le détail du portefeuille à risque.",
            "DISTINCTCOUNT(F_Credit_PAR_Detail[Code client])",
            "#,##0",
        ),
        (
            "Arriéré crédit",
            "Montant total des arriérés du détail PAR.",
            "SUM(F_Credit_PAR_Detail[Arriéré])",
            "#,##0.00",
        ),
        (
            "Exposition nette",
            "Exposition de crédit non couverte après épargne, caution et garantie.",
            "SUM(F_Credit_Couverture[Exposition nette])",
            "#,##0.00",
        ),
        (
            "Part encours top 10%",
            "Part de l'encours portée par les dix pour cent de prêts les plus importants.",
            "DIVIDE(SUM(F_Credit_Concentration[Encours top 10%]), SUM(F_Credit_Concentration[Encours]))",
            "0.00%",
        ),
        (
            "Échéances futures",
            "Montant total attendu sur les échéances futures.",
            "SUM(F_Credit_Echeances_Futures[Total attendu])",
            "#,##0.00",
        ),
        (
            "Taux rétention crédit",
            "Clients renouvelés divisés par les clients arrivés à échéance.",
            "DIVIDE(SUM(F_Credit_Retention[Clients renouvelés]), SUM(F_Credit_Retention[Clients arrivés échéance]))",
            "0.00%",
        ),
        (
            "Provision détaillée",
            "Somme des provisions du détail sur les trois derniers mois.",
            "SUM(F_Credit_Provisions_Detail[Provision])",
            "#,##0.00",
        ),
        (
            "Échéances restantes moyennes",
            "Nombre moyen d'échéances restantes sur les prêts actifs.",
            "AVERAGE(F_Credit_Duree[Échéances restantes])",
            "0.0",
        ),
        (
            "Encours tendance",
            "Encours issu de la série mensuelle de la requête 109.",
            "SUM(F_Credit_Tendance_PAR[Encours])",
            "#,##0.00",
        ),
        (
            "PAR 30 tendance",
            "PAR 30+ issu de la série mensuelle de la requête 109.",
            "SUM(F_Credit_Tendance_PAR[PAR 30+])",
            "#,##0.00",
        ),
        (
            "Encours top clients",
            "Encours des principaux clients sélectionnés par la requête 98.",
            "SUM(F_Credit_Top_Encours[Encours])",
            "#,##0.00",
        ),
        (
            "Encours par tranche",
            "Encours agrégé selon les tranches de montant initial de la requête 104.",
            "SUM(F_Credit_Tranches[Encours])",
            "#,##0.00",
        ),
        (
            "PAR 30 par tranche",
            "PAR 30+ agrégé selon les tranches de montant initial.",
            "SUM(F_Credit_Tranches[PAR 30+])",
            "#,##0.00",
        ),
        (
            "PAR 30 vintage",
            "PAR 30+ agrégé par cohorte de décaissement.",
            "SUM(F_Credit_Vintage[PAR 30+])",
            "#,##0.00",
        ),
        (
            "Prêts par durée",
            "Nombre de prêts distincts dans les tranches d'échéances restantes.",
            "DISTINCTCOUNT(F_Credit_Duree[Numéro prêt])",
            "#,##0",
        ),
    ]
    lines = [
        "/// Mesures de pilotage. Les montants CDF et USD restent toujours séparés.",
        "table _Mesures",
        "",
    ]
    for name, description, dax, format_string in measures:
        lines.extend(
            [
                f"\t/// {description}",
                f"\tmeasure {q(name)} = {dax}",
                f"\t\tformatString: {format_string}",
                "",
            ]
        )
    lines.extend(
        [
            "\tcolumn Technique",
            "\t\tdataType: string",
            "\t\tisHidden",
            "\t\tsummarizeBy: none",
            "\t\tsourceColumn: [Technique]",
            "",
            "\tpartition _Mesures = calculated",
            "\t\tmode: import",
            '\t\tsource = ROW("Technique", BLANK())',
            "",
            "\tannotation PBI_ResultType = Table",
            "",
        ]
    )
    return "\n".join(lines)


def build_relationships() -> str:
    relationships = [
        ("Crédit portefeuille - Date", "F_Credit_Portefeuille.'Date situation'", "D_Date.Date"),
        ("Décaissements - Date", "F_Credit_Decaissements.'Mois décaissement'", "D_Date.Date"),
        ("Épargne - Date", "F_Epargne_Soldes.Mois", "D_Date.Date"),
        ("Conformité - Date", "F_Conformite.'Date fin'", "D_Date.Date"),
        ("PAR détail - Date", "F_Credit_PAR_Detail.'Date situation'", "D_Date.Date"),
        ("Top encours - Date", "F_Credit_Top_Encours.'Date situation'", "D_Date.Date"),
        ("Échéances futures - Date", "F_Credit_Echeances_Futures.'Mois échéance'", "D_Date.Date"),
        ("Rétention - Date", "F_Credit_Retention.'Mois solde'", "D_Date.Date"),
        ("Vintage - Date", "F_Credit_Vintage.'Cohorte décaissement'", "D_Date.Date"),
        ("Tranches - Date", "F_Credit_Tranches.'Date situation'", "D_Date.Date"),
        ("Concentration - Date", "F_Credit_Concentration.'Date situation'", "D_Date.Date"),
        ("Couverture crédit - Date", "F_Credit_Couverture.'Date situation'", "D_Date.Date"),
        ("Provisions détail - Date", "F_Credit_Provisions_Detail.'Date situation'", "D_Date.Date"),
        ("Durée crédit - Date", "F_Credit_Duree.'Date situation'", "D_Date.Date"),
        ("Tendance PAR - Date", "F_Credit_Tendance_PAR.'Date situation'", "D_Date.Date"),
        ("Clients - Date", "F_Clients.'Date fin'", "D_Date.Date"),
        ("Crédit portefeuille - Devise", "F_Credit_Portefeuille.Devise", "D_Devise.Devise"),
        ("Décaissements - Devise", "F_Credit_Decaissements.Devise", "D_Devise.Devise"),
        ("Épargne - Devise", "F_Epargne_Soldes.Devise", "D_Devise.Devise"),
        ("Conformité - Devise", "F_Conformite.Devise", "D_Devise.Devise"),
        ("PAR détail - Devise", "F_Credit_PAR_Detail.Devise", "D_Devise.Devise"),
        ("Top encours - Devise", "F_Credit_Top_Encours.Devise", "D_Devise.Devise"),
        ("Échéances futures - Devise", "F_Credit_Echeances_Futures.Devise", "D_Devise.Devise"),
        ("Rétention - Devise", "F_Credit_Retention.Devise", "D_Devise.Devise"),
        ("Vintage - Devise", "F_Credit_Vintage.Devise", "D_Devise.Devise"),
        ("Tranches - Devise", "F_Credit_Tranches.Devise", "D_Devise.Devise"),
        ("Concentration - Devise", "F_Credit_Concentration.Devise", "D_Devise.Devise"),
        ("Couverture crédit - Devise", "F_Credit_Couverture.Devise", "D_Devise.Devise"),
        ("Provisions détail - Devise", "F_Credit_Provisions_Detail.Devise", "D_Devise.Devise"),
        ("Durée crédit - Devise", "F_Credit_Duree.Devise", "D_Devise.Devise"),
        ("Tendance PAR - Devise", "F_Credit_Tendance_PAR.Devise", "D_Devise.Devise"),
        ("Clients - Devise", "F_Clients.Devise", "D_Devise.Devise"),
        ("Crédit portefeuille - Agence", "F_Credit_Portefeuille.'Code agence'", "D_Agence.'Code agence'"),
        ("Décaissements - Agence", "F_Credit_Decaissements.'Code agence'", "D_Agence.'Code agence'"),
        ("Épargne - Agence", "F_Epargne_Soldes.'Code agence'", "D_Agence.'Code agence'"),
        ("PAR détail - Agence", "F_Credit_PAR_Detail.'Code agence'", "D_Agence.'Code agence'"),
        ("Top encours - Agence", "F_Credit_Top_Encours.'Code agence'", "D_Agence.'Code agence'"),
        ("Échéances futures - Agence", "F_Credit_Echeances_Futures.'Code agence'", "D_Agence.'Code agence'"),
        ("Rétention - Agence", "F_Credit_Retention.'Code agence'", "D_Agence.'Code agence'"),
        ("Vintage - Agence", "F_Credit_Vintage.'Code agence'", "D_Agence.'Code agence'"),
        ("Tranches - Agence", "F_Credit_Tranches.'Code agence'", "D_Agence.'Code agence'"),
        ("Concentration - Agence", "F_Credit_Concentration.'Code agence'", "D_Agence.'Code agence'"),
        ("Couverture crédit - Agence", "F_Credit_Couverture.'Code agence'", "D_Agence.'Code agence'"),
        ("Provisions détail - Agence", "F_Credit_Provisions_Detail.'Code agence'", "D_Agence.'Code agence'"),
        ("Durée crédit - Agence", "F_Credit_Duree.'Code agence'", "D_Agence.'Code agence'"),
        ("Tendance PAR - Agence", "F_Credit_Tendance_PAR.'Code agence'", "D_Agence.'Code agence'"),
        ("Clients - Agence", "F_Clients.'Code agence'", "D_Agence.'Code agence'"),
    ]
    lines: list[str] = []
    for name, source, target in relationships:
        lines.extend(
            [
                f"relationship {q(name)}",
                f"\tfromColumn: {source}",
                f"\ttoColumn: {target}",
                "",
            ]
        )
    return "\n".join(lines)


def build_model() -> str:
    refs = [spec["name"] for spec in TABLES.values()] + [
        "D_Date",
        "D_Devise",
        "D_Agence",
        "_Mesures",
    ]
    lines = [
        "model Model",
        "\tculture: fr-FR",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: fr-FR",
        "\tvalueFilterBehavior: independent",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        'annotation PBI_ProTooling = ["DevMode"]',
        "",
        *[f"ref table {name}" for name in refs],
        "ref cultureInfo fr-FR",
        "",
    ]
    return "\n".join(lines)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    queries = extract_queries()
    missing = sorted(set(TABLES) - set(queries))
    if missing:
        raise SystemExit(f"Requêtes introuvables : {missing}")

    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    for number in TABLES:
        spec = TABLES[number]
        write_text(TABLES_ROOT / f"{spec['name']}.tmdl", build_import_table(number, queries[number]))

    write_text(TABLES_ROOT / "D_Date.tmdl", build_date_table())
    write_text(TABLES_ROOT / "D_Devise.tmdl", build_currency_table())
    write_text(TABLES_ROOT / "D_Agence.tmdl", build_agency_table())
    write_text(TABLES_ROOT / "_Mesures.tmdl", build_measures_table())
    write_text(MODEL_ROOT / "relationships.tmdl", build_relationships())
    write_text(MODEL_ROOT / "model.tmdl", build_model())

    print(f"Modèle Power BI généré dans {MODEL_ROOT}")
    print("Sources : requêtes 96 à 109, 156 et 157 ; période initiale : mois en cours.")


if __name__ == "__main__":
    main()
