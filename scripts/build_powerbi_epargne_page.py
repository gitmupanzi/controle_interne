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
PAGE_ID = "584ad687c0ab79234040"
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
    account_type = column_projection("F_Epargne_Soldes", "Type compte")
    measures = [
        measure_projection("Comptes CDF"),
        measure_projection("Comptes USD"),
        measure_projection("Épargne CDF"),
        measure_projection("Épargne USD"),
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
                        "projections": [account_type, *measures],
                    }
                },
                "sortDefinition": {
                    "sort": [
                        {
                            "field": measure_projection("Épargne CDF")["field"],
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
                            "backColor": color("#F7E8F2"),
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
                            "backColorSecondary": color("#FBF6FA"),
                            "wordWrap": literal("false"),
                        }
                    }
                ],
                "grid": [
                    {
                        "properties": {
                            "gridHorizontal": literal("true"),
                            "gridHorizontalColor": color("#E9DFE7"),
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
    page["displayName"] = "Épargne"
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
            "e1000000000000000001",
            "Pilotage de l’épargne",
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
            "e1000000000000000002",
            "Soldes, comptes, types et produits d’épargne — chargement par défaut : mois en cours",
            x=40,
            y=56,
            width=760,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            "e1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=840,
            width=256,
            z=3,
            mode="Between",
        ),
        slicer(
            "e1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=1104,
            width=152,
            z=4,
        ),
        card(
            "e1000000000000000005",
            ["Épargne CDF", "Épargne USD"],
            "Position d’épargne",
            x=24,
            y=112,
            width=400,
            height=144,
            z=5,
            accent_color="#D43F9A",
            value_font_size=18,
        ),
        card(
            "e1000000000000000006",
            ["Comptes CDF", "Comptes USD"],
            "Comptes d’épargne",
            x=440,
            y=112,
            width=400,
            height=144,
            z=6,
            accent_color="#D43F9A",
            value_font_size=18,
        ),
        card(
            "e1000000000000000007",
            ["Solde moyen CDF", "Solde moyen USD"],
            "Solde moyen par compte",
            x=856,
            y=112,
            width=400,
            height=144,
            z=7,
            accent_color="#B83280",
            value_font_size=18,
        ),
        bar_chart(
            "e1000000000000000008",
            "Épargne CDF",
            "Solde épargne par type de compte — CDF",
            "#D43F9A",
            "F_Epargne_Soldes",
            "Type compte",
            x=24,
            y=272,
            width=400,
            height=200,
            z=8,
        ),
        bar_chart(
            "e1000000000000000009",
            "Épargne USD",
            "Solde épargne par type de compte — USD",
            "#B83280",
            "F_Epargne_Soldes",
            "Type compte",
            x=24,
            y=488,
            width=400,
            height=208,
            z=9,
        ),
        table_visual(
            "e1000000000000000010",
            "Comptes et soldes par type de compte",
            x=440,
            y=272,
            width=816,
            height=200,
            z=10,
        ),
        bar_chart(
            "e1000000000000000011",
            "Épargne CDF",
            "Solde par produit d’épargne — CDF",
            "#D43F9A",
            "F_Epargne_Soldes",
            "Produit épargne",
            x=440,
            y=488,
            width=400,
            height=208,
            z=11,
        ),
        bar_chart(
            "e1000000000000000012",
            "Épargne USD",
            "Solde par produit d’épargne — USD",
            "#B83280",
            "F_Epargne_Soldes",
            "Produit épargne",
            x=856,
            y=488,
            width=400,
            height=208,
            z=12,
        ),
    ]
    update_page()
    for visual in visuals:
        write_visual(visual)
    print(f"{len(visuals)} visuels Épargne générés dans {VISUALS_ROOT}")


if __name__ == "__main__":
    main()
