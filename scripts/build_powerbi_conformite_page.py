from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build_powerbi_direction_page import (
    SCHEMA,
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
PAGE_ID = "e5739cc2130de8270027"
PAGE_ROOT = (
    ROOT
    / "data"
    / "vision"
    / "power-bi"
    / "IMF BB Tableau de bord.Report"
    / "definition"
    / "pages"
    / PAGE_ID
)
VISUALS_ROOT = PAGE_ROOT / "visuals"


def count_bar_chart(
    visual_id: str,
    title: str,
    category_field: str,
    *,
    measure_name: str = "Lignes 156",
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    bar_color: str,
) -> dict[str, Any]:
    category = column_projection("F_Conformite", category_field)
    measure = measure_projection(measure_name)
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "barChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [category]},
                    "Y": {"projections": [measure]},
                },
                "sortDefinition": {
                    "sort": [
                        {
                            "field": measure["field"],
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
                            "maxMarginFactor": literal("48L"),
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
                            "labelDisplayUnits": literal("0D"),
                            "labelPrecision": literal("0L"),
                        }
                    }
                ],
            },
            "visualContainerObjects": container(title),
            "drillFilterOtherVisuals": True,
        },
    }


def detail_table(
    visual_id: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
) -> dict[str, Any]:
    values = [
        column_projection("F_Conformite", "Analyse"),
        column_projection("F_Conformite", "Rubrique"),
        column_projection("F_Conformite", "Devise"),
        column_projection("F_Conformite", "Statut couverture"),
        column_projection("F_Conformite", "Sévérité"),
        measure_projection("Nombre déclaré"),
    ]
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {"Values": {"projections": values}},
                "sortDefinition": {
                    "sort": [
                        {
                            "field": measure_projection("Nombre déclaré")[
                                "field"
                            ],
                            "direction": "Descending",
                        }
                    ],
                    "isDefaultSort": True,
                },
            },
            "objects": {
                "columnHeaders": [
                    {
                        "properties": {
                            "fontFamily": literal("'Segoe UI Semibold'"),
                            "fontSize": literal("10D"),
                            "bold": literal("true"),
                            "fontColor": color("#17365D"),
                            "backColor": color("#FDEBDD"),
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
                            "backColorSecondary": color("#FFF8F2"),
                            "wordWrap": literal("false"),
                        }
                    }
                ],
                "grid": [
                    {
                        "properties": {
                            "gridHorizontal": literal("true"),
                            "gridHorizontalColor": color("#E9DFD7"),
                            "gridHorizontalWeight": literal("1D"),
                            "gridVertical": literal("false"),
                            "rowPadding": literal("4D"),
                        }
                    }
                ],
                "total": [
                    {
                        "properties": {
                            "totals": literal("false"),
                        }
                    }
                ],
            },
            "visualContainerObjects": container(
                "Détail exploitable du socle conformité"
            ),
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


def update_page() -> None:
    path = PAGE_ROOT / "page.json"
    page = json.loads(path.read_text(encoding="utf-8"))
    page["displayName"] = "Conformité"
    page["displayOption"] = "ActualSize"
    page["height"] = 720
    page["width"] = 1280
    page["objects"] = {
        "background": [
            {
                "properties": {
                    "color": color("#F3F6FA"),
                    "transparency": literal("0D"),
                }
            }
        ]
    }
    path.write_text(
        json.dumps(page, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    visuals = [
        textbox(
            "f1000000000000000001",
            "Pilotage de la conformité",
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
            "f1000000000000000002",
            "Synthèse LBC-FT, couverture et qualité — source unique : requête 156",
            x=40,
            y=56,
            width=760,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            "f1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=840,
            width=256,
            z=3,
            mode="Between",
        ),
        slicer(
            "f1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=1104,
            width=152,
            z=4,
        ),
        card(
            "f1000000000000000005",
            ["Analyses LBC-FT", "Lignes 156"],
            "Dispositif LBC-FT",
            x=24,
            y=112,
            width=400,
            height=144,
            z=5,
            accent_color="#17365D",
            value_font_size=18,
        ),
        card(
            "f1000000000000000006",
            [
                "Non couverts",
                "Partiels",
                "Couverts",
            ],
            "Couverture du dispositif",
            x=440,
            y=112,
            width=400,
            height=144,
            z=6,
            accent_color="#E67E22",
            value_font_size=16,
        ),
        card(
            "f1000000000000000007",
            [
                "Alertes",
                "CENTIF",
                "Profils risque",
                "Réactivations",
            ],
            "Surveillance renforcée",
            x=856,
            y=112,
            width=400,
            height=144,
            z=7,
            accent_color="#C55A11",
            value_font_size=16,
        ),
        count_bar_chart(
            "f1000000000000000008",
            "Lignes disponibles par analyse",
            "Analyse",
            x=24,
            y=272,
            width=400,
            height=200,
            z=8,
            bar_color="#17365D",
        ),
        count_bar_chart(
            "f1000000000000000009",
            "Répartition par sévérité",
            "Sévérité",
            measure_name="Lignes sévérité",
            x=24,
            y=488,
            width=400,
            height=208,
            z=9,
            bar_color="#C55A11",
        ),
        detail_table(
            "f1000000000000000010",
            x=440,
            y=272,
            width=816,
            height=424,
            z=10,
        ),
    ]
    update_page()
    for visual in visuals:
        write_visual(visual)
    print(f"{len(visuals)} visuels Conformité générés dans {VISUALS_ROOT}")


if __name__ == "__main__":
    main()
