from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build_powerbi_conformite_page import count_bar_chart
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
PAGE_ID = "bb42ec5670606782aa6d"
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


def investigation_table(
    visual_id: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
) -> dict[str, Any]:
    date_event = column_projection("F_Conformite", "Date événement")
    values = [
        date_event,
        column_projection("F_Conformite", "Type élément"),
        column_projection("F_Conformite", "Nom client"),
        column_projection("F_Conformite", "Code client"),
        column_projection("F_Conformite", "Numéro compte"),
        column_projection("F_Conformite", "Numéro alerte"),
        column_projection("F_Conformite", "Référence interne"),
        column_projection("F_Conformite", "Numéro opération"),
        column_projection("F_Conformite", "Type opération"),
        column_projection("F_Conformite", "Devise"),
        column_projection("F_Conformite", "Montant"),
        column_projection("F_Conformite", "Statut revue"),
        column_projection("F_Conformite", "Sévérité"),
        column_projection("F_Conformite", "Action recommandée"),
        measure_projection("Lignes surveillance"),
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
                            "field": date_event["field"],
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
                "Dossiers et signaux à investiguer"
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
    page["displayName"] = "Surveillance"
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
            "s1000000000000000001",
            "Pilotage de la surveillance",
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
            "s1000000000000000002",
            "Investigation des signaux LBC-FT — source unique : requête 156",
            x=40,
            y=56,
            width=560,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        slicer(
            "s1000000000000000003",
            "D_Date",
            "Date",
            "Période",
            x=640,
            width=240,
            z=3,
            mode="Between",
        ),
        slicer(
            "s1000000000000000004",
            "D_Devise",
            "Devise",
            "Devise",
            x=888,
            width=112,
            z=4,
        ),
        slicer(
            "s1000000000000000005",
            "F_Conformite",
            "Sévérité",
            "Sévérité",
            x=1008,
            width=120,
            z=5,
        ),
        slicer(
            "s1000000000000000006",
            "F_Conformite",
            "Statut revue",
            "Revue",
            x=1136,
            width=120,
            z=6,
        ),
        card(
            "s1000000000000000007",
            ["Cas surveillance"],
            "Cas de surveillance",
            x=24,
            y=112,
            width=400,
            height=144,
            z=7,
            accent_color="#C55A11",
            value_font_size=24,
        ),
        card(
            "s1000000000000000008",
            ["Dossiers à revoir"],
            "Charge à traiter",
            x=440,
            y=112,
            width=400,
            height=144,
            z=8,
            accent_color="#C00000",
            value_font_size=24,
        ),
        card(
            "s1000000000000000009",
            ["Clients surveillés"],
            "Clients concernés",
            x=856,
            y=112,
            width=400,
            height=144,
            z=9,
            accent_color="#17365D",
            value_font_size=24,
        ),
        count_bar_chart(
            "s1000000000000000010",
            "Cas par type de signal",
            "Type élément",
            measure_name="Lignes surveillance",
            x=24,
            y=272,
            width=400,
            height=200,
            z=10,
            bar_color="#17365D",
        ),
        count_bar_chart(
            "s1000000000000000011",
            "Priorité des cas par sévérité",
            "Sévérité",
            measure_name="Lignes surveillance sévérité",
            x=24,
            y=488,
            width=400,
            height=208,
            z=11,
            bar_color="#C55A11",
        ),
        investigation_table(
            "s1000000000000000012",
            x=440,
            y=272,
            width=816,
            height=424,
            z=12,
        ),
    ]
    update_page()
    for visual in visuals:
        write_visual(visual)
    print(
        f"{len(visuals)} visuels Surveillance générés dans {VISUALS_ROOT}"
    )


if __name__ == "__main__":
    main()
