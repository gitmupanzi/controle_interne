from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build_powerbi_direction_page import (
    SCHEMA,
    bar_chart,
    card,
    color,
    column_projection,
    container,
    literal,
    measure_projection,
    position,
    slicer,
    textbox,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = (
    ROOT
    / "data"
    / "vision"
    / "power-bi"
    / "IMF BB Tableau de bord.Report"
    / "definition"
)
PAGES_ROOT = REPORT_ROOT / "pages"

PAGE_RISK = "7f8e9d0c1b2a34567890"
PAGE_FORECAST = "8a9b0c1d2e3f45678901"
PAGE_CLIENTS = "9b0c1d2e3f4a56789012"
PAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/2.1.0/schema.json"
)


def multi_bar_chart(
    visual_id: str,
    title: str,
    category_table: str,
    category_field: str,
    measures: list[str],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    bar_color: str = "#1F77B4",
) -> dict[str, Any]:
    category = column_projection(category_table, category_field)
    values = [measure_projection(name) for name in measures]
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "barChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [category]},
                    "Y": {"projections": values},
                },
                "sortDefinition": {
                    "sort": [
                        {
                            "field": values[0]["field"],
                            "direction": "Descending",
                        }
                    ],
                    "isDefaultSort": True,
                },
            },
            "objects": {
                "categoryAxis": [
                    {
                        "properties": {
                            "showAxisTitle": literal("false"),
                            "maxMarginFactor": literal("45L"),
                            "innerPadding": literal("24L"),
                            "labelColor": color("#44546A"),
                        }
                    }
                ],
                "valueAxis": [
                    {
                        "properties": {
                            "start": literal("0D"),
                            "showAxisTitle": literal("false"),
                            "labelColor": color("#44546A"),
                            "gridlineColor": color("#E7EDF5"),
                            "gridlineStyle": literal("'dotted'"),
                        }
                    }
                ],
                "dataPoint": [
                    {"properties": {"defaultColor": color(bar_color)}}
                ],
                "legend": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "position": literal("'Top'"),
                            "fontSize": literal("9D"),
                        }
                    }
                ],
                "labels": [{"properties": {"show": literal("false")}}],
            },
            "visualContainerObjects": container(title),
            "drillFilterOtherVisuals": True,
        },
    }


def line_chart(
    visual_id: str,
    title: str,
    category_table: str,
    category_field: str,
    measures: list[str],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
) -> dict[str, Any]:
    category = column_projection(category_table, category_field)
    values = [measure_projection(name) for name in measures]
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "lineChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [category]},
                    "Y": {"projections": values},
                },
                "sortDefinition": {
                    "sort": [
                        {
                            "field": category["field"],
                            "direction": "Ascending",
                        }
                    ],
                    "isDefaultSort": True,
                },
            },
            "objects": {
                "categoryAxis": [
                    {
                        "properties": {
                            "showAxisTitle": literal("false"),
                            "labelColor": color("#44546A"),
                        }
                    }
                ],
                "valueAxis": [
                    {
                        "properties": {
                            "start": literal("0D"),
                            "showAxisTitle": literal("false"),
                            "labelColor": color("#44546A"),
                            "gridlineColor": color("#E7EDF5"),
                            "gridlineStyle": literal("'dotted'"),
                        }
                    }
                ],
                "legend": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "position": literal("'Top'"),
                            "fontSize": literal("9D"),
                        }
                    }
                ],
                "labels": [{"properties": {"show": literal("false")}}],
            },
            "visualContainerObjects": container(title),
            "drillFilterOtherVisuals": True,
        },
    }


def detail_table(
    visual_id: str,
    title: str,
    columns: list[tuple[str, str]],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    sort_column: tuple[str, str] | None = None,
    descending: bool = True,
) -> dict[str, Any]:
    values = [column_projection(table, field) for table, field in columns]
    query: dict[str, Any] = {"queryState": {"Values": {"projections": values}}}
    if sort_column:
        sort = column_projection(*sort_column)
        query["sortDefinition"] = {
            "sort": [
                {
                    "field": sort["field"],
                    "direction": "Descending" if descending else "Ascending",
                }
            ],
            "isDefaultSort": True,
        }
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "tableEx",
            "query": query,
            "objects": {
                "columnHeaders": [
                    {
                        "properties": {
                            "fontFamily": literal("'Segoe UI Semibold'"),
                            "fontSize": literal("10D"),
                            "bold": literal("true"),
                            "fontColor": color("#17365D"),
                            "backColor": color("#EAF1F8"),
                            "autoSizeColumnWidth": literal("true"),
                            "wordWrap": literal("true"),
                        }
                    }
                ],
                "values": [
                    {
                        "properties": {
                            "fontFamily": literal("'Segoe UI'"),
                            "fontSize": literal("9D"),
                            "fontColorPrimary": color("#25364D"),
                            "backColorPrimary": color("#FFFFFF"),
                            "fontColorSecondary": color("#25364D"),
                            "backColorSecondary": color("#F7FAFD"),
                            "wordWrap": literal("false"),
                        }
                    }
                ],
                "grid": [
                    {
                        "properties": {
                            "gridHorizontal": literal("true"),
                            "gridHorizontalColor": color("#E7EDF5"),
                            "gridHorizontalWeight": literal("1D"),
                            "gridVertical": literal("false"),
                            "rowPadding": literal("4D"),
                        }
                    }
                ],
                "total": [{"properties": {"totals": literal("false")}}],
            },
            "visualContainerObjects": container(title),
            "drillFilterOtherVisuals": True,
        },
    }


def new_page(page_id: str, display_name: str) -> Path:
    page_root = PAGES_ROOT / page_id
    page_root.mkdir(parents=True, exist_ok=True)
    page = {
        "$schema": PAGE_SCHEMA,
        "name": page_id,
        "displayName": display_name,
        "displayOption": "ActualSize",
        "height": 720,
        "width": 1280,
        "objects": {
            "background": [
                {
                    "properties": {
                        "color": color("#F3F6FA"),
                        "transparency": literal("0D"),
                    }
                }
            ]
        },
    }
    (page_root / "page.json").write_text(
        json.dumps(page, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return page_root


def write_page(page_id: str, display_name: str, visuals: list[dict[str, Any]]) -> None:
    page_root = new_page(page_id, display_name)
    visuals_root = page_root / "visuals"
    for visual in visuals:
        path = visuals_root / visual["name"] / "visual.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(visual, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def common_header(
    prefix: str,
    title: str,
    subtitle: str,
) -> list[dict[str, Any]]:
    return [
        textbox(
            f"{prefix}1000000000000000001",
            title,
            x=24,
            y=16,
            width=792,
            height=80,
            z=1,
            font_size=26,
            color_hex="#FFFFFF",
            semibold=True,
            background_hex="#17365D",
        ),
        textbox(
            f"{prefix}1000000000000000002",
            subtitle,
            x=40,
            y=56,
            width=760,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            f"{prefix}1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=840,
            width=256,
            z=3,
            mode="Between",
        ),
        slicer(
            f"{prefix}1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=1104,
            width=152,
            z=4,
        ),
    ]


def build_risk_page() -> None:
    visuals = common_header(
        "r",
        "Risque et concentration du crédit",
        "PAR détaillé, gros encours, concentration et couverture — requêtes 96, 98, 104, 105 et 106",
    )
    visuals.extend(
        [
            card(
                "r1000000000000000005",
                ["Clients PAR"],
                "Clients exposés au PAR",
                x=24,
                y=112,
                width=296,
                height=128,
                z=5,
                accent_color="#C55A11",
            ),
            card(
                "r1000000000000000006",
                ["Arriéré crédit"],
                "Arriéré total",
                x=336,
                y=112,
                width=296,
                height=128,
                z=6,
                accent_color="#C00000",
            ),
            card(
                "r1000000000000000007",
                ["Part encours top 10%"],
                "Concentration top 10 %",
                x=648,
                y=112,
                width=296,
                height=128,
                z=7,
                accent_color="#7030A0",
            ),
            card(
                "r1000000000000000008",
                ["Exposition nette"],
                "Exposition non couverte",
                x=960,
                y=112,
                width=296,
                height=128,
                z=8,
                accent_color="#E67E22",
            ),
            bar_chart(
                "r1000000000000000009",
                "Encours top clients",
                "Principaux encours par client",
                "#1F77B4",
                "F_Credit_Top_Encours",
                "Nom client",
                x=24,
                y=256,
                width=400,
                height=216,
                z=9,
            ),
            multi_bar_chart(
                "r1000000000000000010",
                "Encours et PAR 30+ par tranche",
                "F_Credit_Tranches",
                "Tranche montant",
                ["Encours par tranche", "PAR 30 par tranche"],
                x=440,
                y=256,
                width=400,
                height=216,
                z=10,
                bar_color="#5B9BD5",
            ),
            bar_chart(
                "r1000000000000000011",
                "Exposition nette",
                "Exposition non couverte par produit",
                "#C55A11",
                "F_Credit_Couverture",
                "Produit crédit",
                x=856,
                y=256,
                width=400,
                height=216,
                z=11,
            ),
            detail_table(
                "r1000000000000000012",
                "Prêts à investiguer",
                [
                    ("F_Credit_PAR_Detail", "Code client"),
                    ("F_Credit_PAR_Detail", "Nom client"),
                    ("F_Credit_PAR_Detail", "Numéro prêt"),
                    ("F_Credit_PAR_Detail", "Produit crédit"),
                    ("F_Credit_PAR_Detail", "Devise"),
                    ("F_Credit_PAR_Detail", "Jours retard"),
                    ("F_Credit_PAR_Detail", "Encours"),
                    ("F_Credit_PAR_Detail", "Arriéré"),
                    ("F_Credit_PAR_Detail", "Provision"),
                ],
                x=24,
                y=488,
                width=1232,
                height=208,
                z=12,
                sort_column=("F_Credit_PAR_Detail", "Arriéré"),
            ),
        ]
    )
    write_page(PAGE_RISK, "Risque crédit", visuals)


def build_forecast_page() -> None:
    visuals = common_header(
        "p",
        "Prévisions et dynamique du crédit",
        "Échéances, rétention, vintage, provisions, durée et tendance — requêtes 100 à 102 et 107 à 109",
    )
    visuals.extend(
        [
            card(
                "p1000000000000000005",
                ["Échéances futures"],
                "Échéances attendues",
                x=24,
                y=112,
                width=400,
                height=128,
                z=5,
                accent_color="#1F77B4",
            ),
            card(
                "p1000000000000000006",
                ["Taux rétention crédit"],
                "Rétention crédit",
                x=440,
                y=112,
                width=400,
                height=128,
                z=6,
                accent_color="#70AD47",
            ),
            card(
                "p1000000000000000007",
                ["Échéances restantes moyennes"],
                "Durée résiduelle moyenne",
                x=856,
                y=112,
                width=400,
                height=128,
                z=7,
                accent_color="#7030A0",
            ),
            line_chart(
                "p1000000000000000008",
                "Échéances attendues par mois",
                "F_Credit_Echeances_Futures",
                "Mois échéance",
                ["Échéances futures"],
                x=24,
                y=256,
                width=400,
                height=216,
                z=8,
            ),
            line_chart(
                "p1000000000000000009",
                "PAR 30+ par cohorte",
                "F_Credit_Vintage",
                "Cohorte décaissement",
                ["PAR 30 vintage"],
                x=440,
                y=256,
                width=400,
                height=216,
                z=9,
            ),
            bar_chart(
                "p1000000000000000010",
                "Prêts par durée",
                "Prêts par durée résiduelle",
                "#7030A0",
                "F_Credit_Duree",
                "Tranche échéances restantes",
                x=856,
                y=256,
                width=400,
                height=216,
                z=10,
            ),
            line_chart(
                "p1000000000000000011",
                "Tendance encours et PAR 30+",
                "F_Credit_Tendance_PAR",
                "Date situation",
                ["Encours tendance", "PAR 30 tendance"],
                x=24,
                y=488,
                width=608,
                height=208,
                z=11,
            ),
            bar_chart(
                "p1000000000000000012",
                "Provision détaillée",
                "Provision par tranche de montant",
                "#C55A11",
                "F_Credit_Provisions_Detail",
                "Tranche montant",
                x=648,
                y=488,
                width=608,
                height=208,
                z=12,
            ),
        ]
    )
    write_page(PAGE_FORECAST, "Prévisions crédit", visuals)


def build_clients_page() -> None:
    visuals = [
        textbox(
            "l1000000000000000001",
            "Pilotage des clients",
            x=24,
            y=16,
            width=600,
            height=80,
            z=1,
            font_size=26,
            color_hex="#FFFFFF",
            semibold=True,
            background_hex="#17365D",
        ),
        textbox(
            "l1000000000000000002",
            "Statuts, comptes, crédits, intérêts et DAT — source : requête autonome 157",
            x=40,
            y=56,
            width=560,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            "l1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=640,
            width=240,
            z=3,
            mode="Between",
        ),
        slicer(
            "l1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=888,
            width=112,
            z=4,
        ),
        slicer(
            "l1000000000000000005",
            "F_Clients",
            "Statut client",
            "Statut",
            x=1008,
            width=120,
            z=5,
        ),
        slicer(
            "l1000000000000000006",
            "F_Clients",
            "Type client",
            "Type client",
            x=1136,
            width=120,
            z=6,
        ),
        card(
            "l1000000000000000007",
            ["Clients actifs"],
            "Clients actifs",
            x=24,
            y=112,
            width=296,
            height=128,
            z=7,
            accent_color="#70AD47",
        ),
        card(
            "l1000000000000000008",
            ["Clients comptes ouverts"],
            "Avec compte ouvert",
            x=336,
            y=112,
            width=296,
            height=128,
            z=8,
            accent_color="#1F77B4",
        ),
        card(
            "l1000000000000000009",
            ["Clients comptes dormants"],
            "Avec compte dormant",
            x=648,
            y=112,
            width=296,
            height=128,
            z=9,
            accent_color="#C55A11",
        ),
        card(
            "l1000000000000000010",
            ["Clients comptes bloqués"],
            "Avec compte bloqué",
            x=960,
            y=112,
            width=296,
            height=128,
            z=10,
            accent_color="#C00000",
        ),
        card(
            "l1000000000000000011",
            ["Clients crédit à rembourser"],
            "Crédit à rembourser",
            x=24,
            y=256,
            width=400,
            height=128,
            z=11,
            accent_color="#1F4E79",
        ),
        card(
            "l1000000000000000012",
            ["Clients intérêt épargne"],
            "Intérêt épargne crédité",
            x=440,
            y=256,
            width=400,
            height=128,
            z=12,
            accent_color="#D43F9A",
        ),
        card(
            "l1000000000000000013",
            ["Clients DAT à échéance"],
            "DAT à échéance",
            x=856,
            y=256,
            width=400,
            height=128,
            z=13,
            accent_color="#7030A0",
        ),
        bar_chart(
            "l1000000000000000014",
            "Clients",
            "Portefeuille par type de client",
            "#1F77B4",
            "F_Clients",
            "Type client",
            x=24,
            y=400,
            width=304,
            height=296,
            z=14,
        ),
        detail_table(
            "l1000000000000000015",
            "Détail client exploitable",
            [
                ("F_Clients", "Code client"),
                ("F_Clients", "Nom client"),
                ("F_Clients", "Type client"),
                ("F_Clients", "Devise"),
                ("F_Clients", "Statut client"),
                ("F_Clients", "Comptes ouverts"),
                ("F_Clients", "Comptes dormants"),
                ("F_Clients", "Comptes bloqués"),
                ("F_Clients", "Crédits à rembourser"),
                ("F_Clients", "Montant crédit à rembourser"),
                ("F_Clients", "Intérêt épargne crédité"),
                ("F_Clients", "DAT à échéance"),
                ("F_Clients", "Première échéance DAT"),
            ],
            x=344,
            y=400,
            width=912,
            height=296,
            z=15,
            sort_column=("F_Clients", "Nom client"),
            descending=False,
        ),
    ]
    write_page(PAGE_CLIENTS, "Clients", visuals)


def update_page_order() -> None:
    path = PAGES_ROOT / "pages.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    existing = [
        page
        for page in payload["pageOrder"]
        if page not in {PAGE_RISK, PAGE_FORECAST, PAGE_CLIENTS}
    ]
    credit_page = "0a3bfdf523b1336d73b5"
    savings_page = "584ad687c0ab79234040"
    result: list[str] = []
    for page in existing:
        result.append(page)
        if page == credit_page:
            result.extend([PAGE_RISK, PAGE_FORECAST])
        if page == savings_page:
            result.append(PAGE_CLIENTS)
    payload["pageOrder"] = result
    payload["activePageName"] = PAGE_CLIENTS
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    build_risk_page()
    build_forecast_page()
    build_clients_page()
    update_page_order()
    print("Feuilles Risque crédit, Prévisions crédit et Clients générées.")


if __name__ == "__main__":
    main()
