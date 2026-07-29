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
PAGE_ID = "0a3bfdf523b1336d73b5"
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


def table_visual(
    visual_id: str,
    title: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
) -> dict[str, Any]:
    product = column_projection("F_Credit_Portefeuille", "Produit crédit")
    measures = [
        measure_projection("Prêts actifs"),
        measure_projection("Encours CDF"),
        measure_projection("Encours USD"),
    ]
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": [product, *measures],
                    }
                },
                "sortDefinition": {
                    "sort": [
                        {
                            "field": measure_projection("Encours CDF")["field"],
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
                            "backColor": color("#EAF0F7"),
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
                            "backColorSecondary": color("#F7F9FC"),
                            "wordWrap": literal("false"),
                        }
                    }
                ],
                "grid": [
                    {
                        "properties": {
                            "gridHorizontal": literal("true"),
                            "gridHorizontalColor": color("#E3EAF3"),
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


def update_page() -> None:
    path = PAGE_ROOT / "page.json"
    page = json.loads(path.read_text(encoding="utf-8"))
    page["displayName"] = "Crédit"
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
            "c1000000000000000001",
            "Pilotage du crédit",
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
            "c1000000000000000002",
            "Portefeuille, activité et qualité du risque — chargement par défaut : mois en cours",
            x=40,
            y=56,
            width=760,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            "c1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=840,
            width=256,
            z=3,
            mode="Between",
        ),
        slicer(
            "c1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=1104,
            width=152,
            z=4,
        ),
        card(
            "c1000000000000000005",
            ["Prêts actifs", "Encours CDF", "Encours USD"],
            "Portefeuille actif",
            x=24,
            y=112,
            width=608,
            height=144,
            z=5,
            accent_color="#1F4E79",
        ),
        card(
            "c1000000000000000006",
            ["Prêts décaissés", "Décaissements CDF", "Décaissements USD"],
            "Décaissements sur la période",
            x=648,
            y=112,
            width=608,
            height=144,
            z=6,
            accent_color="#1F77B4",
        ),
        card(
            "c1000000000000000007",
            [
                "Taux PAR 1 CDF",
                "Taux PAR 30 CDF",
                "Taux PAR 90 CDF",
                "Provision CDF",
            ],
            "Qualité du portefeuille — CDF",
            x=24,
            y=272,
            width=608,
            height=144,
            z=7,
            accent_color="#E67E22",
            value_font_size=14,
            label_font_size=9,
        ),
        card(
            "c1000000000000000008",
            [
                "Taux PAR 1 USD",
                "Taux PAR 30 USD",
                "Taux PAR 90 USD",
                "Provision USD",
            ],
            "Qualité du portefeuille — USD",
            x=648,
            y=272,
            width=608,
            height=144,
            z=8,
            accent_color="#E67E22",
            value_font_size=14,
            label_font_size=9,
        ),
        bar_chart(
            "c1000000000000000009",
            "Encours CDF",
            "Encours crédit par produit — CDF",
            "#1F77B4",
            "F_Credit_Portefeuille",
            "Produit crédit",
            x=24,
            y=432,
            width=400,
            height=264,
            z=9,
        ),
        table_visual(
            "c1000000000000000011",
            "Encours et prêts actifs par produit",
            x=440,
            y=432,
            width=816,
            height=264,
            z=10,
        ),
    ]
    update_page()
    for visual in visuals:
        write_visual(visual)
    print(f"{len(visuals)} visuels Crédit générés dans {VISUALS_ROOT}")


if __name__ == "__main__":
    main()
