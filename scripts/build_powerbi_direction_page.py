from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PAGE_ID = "10c8006f0380b4495b63"
VISUALS_ROOT = (
    ROOT
    / "data"
    / "vision"
    / "power-bi"
    / "IMF BB Tableau de bord.Report"
    / "definition"
    / "pages"
    / PAGE_ID
    / "visuals"
)
SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.9.0/schema.json"
)


def literal(value: str) -> dict[str, Any]:
    return {"expr": {"Literal": {"Value": value}}}


def color(value: str) -> dict[str, Any]:
    return {"solid": {"color": literal(f"'{value}'")}}


def position(
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
) -> dict[str, Any]:
    return {
        "x": x,
        "y": y,
        "z": z,
        "height": height,
        "width": width,
        "tabOrder": z,
    }


def measure_projection(name: str) -> dict[str, Any]:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "_Mesures"}},
                "Property": name,
            }
        },
        "queryRef": f"_Mesures.{name}",
        "nativeQueryRef": name,
        "active": True,
    }


def column_projection(table: str, name: str) -> dict[str, Any]:
    return {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": name,
            }
        },
        "queryRef": f"{table}.{name}",
        "nativeQueryRef": name,
        "active": True,
    }


def container(title: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "background": [
            {
                "properties": {
                    "show": literal("true"),
                    "color": color("#FFFFFF"),
                    "transparency": literal("0D"),
                }
            }
        ],
        "border": [
            {
                "properties": {
                    "show": literal("true"),
                    "color": color("#D8E2F0"),
                    "width": literal("1D"),
                    "radius": literal("8D"),
                }
            }
        ],
        "padding": [
            {
                "properties": {
                    "top": literal("8D"),
                    "bottom": literal("8D"),
                    "left": literal("8D"),
                    "right": literal("8D"),
                }
            }
        ],
        "visualHeader": [{"properties": {"show": literal("false")}}],
    }
    if title:
        result["title"] = [
            {
                "properties": {
                    "show": literal("true"),
                    "text": literal(f"'{title}'"),
                    "fontSize": literal("13D"),
                    "fontColor": color("#17365D"),
                    "bold": literal("true"),
                }
            }
        ]
    return result


def textbox(
    visual_id: str,
    text: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    font_size: int,
    color_hex: str,
    semibold: bool = False,
    background_hex: str | None = None,
) -> dict[str, Any]:
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "value": text,
                                            "textStyle": {
                                                "fontFamily": (
                                                    "Segoe UI Semibold"
                                                    if semibold
                                                    else "Segoe UI"
                                                ),
                                                "fontSize": f"{font_size}px",
                                                "color": color_hex,
                                            },
                                        }
                                    ],
                                    "horizontalTextAlignment": "left",
                                }
                            ]
                        }
                    }
                ]
            },
            "visualContainerObjects": {
                "background": [
                    {
                        "properties": {
                            "show": literal(
                                "true" if background_hex else "false"
                            ),
                            **(
                                {
                                    "color": color(background_hex),
                                    "transparency": literal("0D"),
                                }
                                if background_hex
                                else {}
                            ),
                        }
                    }
                ],
                "border": [{"properties": {"show": literal("false")}}],
                "padding": [
                    {
                        "properties": {
                            "top": literal("0D"),
                            "bottom": literal("0D"),
                            "left": literal("0D"),
                            "right": literal("0D"),
                        }
                    }
                ],
            },
        },
    }


def slicer(
    visual_id: str,
    table: str,
    field: str,
    title: str,
    *,
    x: int,
    width: int,
    z: int,
    mode: str = "Dropdown",
) -> dict[str, Any]:
    sync_groups = {
        ("D_Date", "Date"): "IMFBB_Global_Periode",
        ("D_Devise", "Devise"): "IMFBB_Global_Devise",
        ("F_Clients", "Statut client"): "IMFBB_Clients_Statut",
        ("F_Clients", "Type client"): "IMFBB_Clients_Type",
    }
    sync_group = sync_groups.get((table, field))
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, 16, width, 80, z),
        "visual": {
            "visualType": "slicer",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": [column_projection(table, field)]
                    }
                }
            },
            "objects": {
                "data": [
                    {
                        "properties": {
                            "mode": literal(f"'{mode}'"),
                        }
                    }
                ],
                "header": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "text": literal(f"'{title}'"),
                        }
                    }
                ],
            },
            **(
                {
                    "syncGroup": {
                        "groupName": sync_group,
                        "fieldChanges": True,
                        "filterChanges": True,
                    }
                }
                if sync_group
                else {}
            ),
            "visualContainerObjects": container(),
        },
    }


def card(
    visual_id: str,
    measures: list[str],
    title: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    accent_color: str,
    value_font_size: int = 22,
    label_font_size: int = 10,
) -> dict[str, Any]:
    vco = container(title)
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {
                    "Data": {
                        "projections": [
                            measure_projection(measure) for measure in measures
                        ]
                    }
                }
            },
            "objects": {
                "accentBar": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "position": literal("'Top'"),
                            "color": color(accent_color),
                            "width": literal("5D"),
                            "transparency": literal("0D"),
                        },
                        "selector": {"id": "default"},
                    }
                ],
                "outline": [
                    {
                        "properties": {"show": literal("false")},
                        "selector": {"id": "default"},
                    }
                ],
                "value": [
                    {
                        "properties": {
                            "fontSize": literal(f"{value_font_size}D"),
                            "fontColor": color("#0B5CAD"),
                        },
                        "selector": {"id": "default"},
                    }
                ],
                "label": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "fontSize": literal(f"{label_font_size}D"),
                            "fontColor": color("#44546A"),
                        },
                        "selector": {"id": "default"},
                    }
                ],
            },
            "visualContainerObjects": vco,
        },
    }


def bar_chart(
    visual_id: str,
    measure: str,
    title: str,
    bar_color: str,
    category_table: str,
    category_field: str,
    *,
    x: int,
    z: int,
    y: int = 432,
    width: int = 608,
    height: int = 264,
) -> dict[str, Any]:
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "barChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [
                            column_projection(
                                category_table, category_field
                            )
                        ]
                    },
                    "Y": {
                        "projections": [measure_projection(measure)]
                    },
                },
                "sortDefinition": {
                    "sort": [
                        {
                            "field": measure_projection(measure)["field"],
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
                            "maxMarginFactor": literal("40L"),
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
                    {
                        "properties": {
                            "defaultColor": color(bar_color),
                        }
                    }
                ],
                "labels": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "labelPosition": literal("'OutsideEnd'"),
                            "fontSize": literal("9D"),
                            "color": color("#17365D"),
                            "labelDisplayUnits": literal("1000000D"),
                            "labelPrecision": literal("1L"),
                        }
                    }
                ],
            },
            "visualContainerObjects": container(title),
            "drillFilterOtherVisuals": True,
        },
    }


def write_visual(visual: dict[str, Any]) -> None:
    path = VISUALS_ROOT / visual["name"] / "visual.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(visual, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    visuals = [
        textbox(
            "d1000000000000000001",
            "Tableau de bord IMF BB",
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
            "d1000000000000000002",
            "Pilotage crédit, épargne et qualité du portefeuille — chargement par défaut : mois en cours",
            x=40,
            y=56,
            width=760,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            "d1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=840,
            width=256,
            z=3,
            mode="Between",
        ),
        slicer(
            "d1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=1104,
            width=152,
            z=4,
        ),
        card(
            "d1000000000000000005",
            ["Prêts actifs", "Encours CDF", "Encours USD"],
            "Portefeuille crédit",
            x=24,
            y=112,
            width=608,
            height=144,
            z=5,
            accent_color="#1F4E79",
        ),
        card(
            "d1000000000000000006",
            [
                "Taux PAR 30 CDF",
                "Taux PAR 30 USD",
                "Provision CDF",
                "Provision USD",
            ],
            "Risque et provisionnement",
            x=648,
            y=112,
            width=608,
            height=144,
            z=6,
            accent_color="#E67E22",
        ),
        card(
            "d1000000000000000007",
            ["Décaissements CDF", "Décaissements USD"],
            "Décaissements sur la période",
            x=24,
            y=272,
            width=608,
            height=144,
            z=7,
            accent_color="#1F77B4",
        ),
        card(
            "d1000000000000000008",
            ["Épargne CDF", "Épargne USD"],
            "Épargne sur la période",
            x=648,
            y=272,
            width=608,
            height=144,
            z=8,
            accent_color="#D43F9A",
        ),
        bar_chart(
            "d1000000000000000009",
            "Encours CDF",
            "Encours crédit par produit — CDF",
            "#1F77B4",
            "F_Credit_Portefeuille",
            "Produit crédit",
            x=24,
            z=9,
        ),
        bar_chart(
            "d1000000000000000010",
            "Épargne CDF",
            "Solde épargne par produit — CDF",
            "#D43F9A",
            "F_Epargne_Soldes",
            "Produit épargne",
            x=648,
            z=10,
        ),
    ]
    for visual in visuals:
        write_visual(visual)
    print(f"{len(visuals)} visuels Direction générés dans {VISUALS_ROOT}")


if __name__ == "__main__":
    main()
