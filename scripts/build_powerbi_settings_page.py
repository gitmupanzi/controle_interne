from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build_powerbi_direction_page import (
    SCHEMA,
    card,
    color,
    literal,
    position,
    slicer,
    textbox,
)
from build_powerbi_extended_pages import PAGES_ROOT, write_page


PAGE_SETTINGS = "f0e1d2c3b4a596877665"

SYNC_GROUPS = {
    ("D_Date", "Date"): "IMFBB_Global_Periode",
    ("D_Devise", "Devise"): "IMFBB_Global_Devise",
    ("F_Clients", "Statut client"): "IMFBB_Clients_Statut",
    ("F_Clients", "Type client"): "IMFBB_Clients_Type",
}


def positioned_slicer(
    visual_id: str,
    table: str,
    field: str,
    title: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    mode: str = "Dropdown",
) -> dict[str, Any]:
    visual = slicer(
        visual_id,
        table,
        field,
        title,
        x=x,
        width=width,
        z=z,
        mode=mode,
    )
    visual["position"].update({"y": y, "height": height})
    return visual


def context_card(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Build a context card without the redundant, space-consuming category label."""
    visual = card(*args, **kwargs)
    visual["visual"]["objects"]["label"][0]["properties"]["show"] = literal("false")
    return visual


def action_button(
    visual_id: str,
    label: str,
    action_type: str,
    tooltip: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    fill_color: str,
    hover_color: str,
    text_color: str = "#FFFFFF",
    outline_color: str | None = None,
) -> dict[str, Any]:
    border_color = outline_color or fill_color
    return {
        "$schema": SCHEMA,
        "name": visual_id,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "actionButton",
            "objects": {
                "shape": [
                    {
                        "properties": {
                            "tileShape": literal("'rectangleRoundedByPixel'"),
                            "rectangleRoundedCurve": literal("10L"),
                        }
                    }
                ],
                "text": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "text": literal(f"'{label}'"),
                            "fontFamily": literal("'Segoe UI Semibold'"),
                            "fontSize": literal("13D"),
                            "bold": literal("true"),
                            "fontColor": color(text_color),
                        },
                        "selector": {"id": "default"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "text": literal(f"'{label}'"),
                            "fontFamily": literal("'Segoe UI Semibold'"),
                            "fontSize": literal("13D"),
                            "bold": literal("true"),
                            "fontColor": color("#7A8798"),
                        },
                        "selector": {"id": "disabled"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "text": literal(f"'{label}'"),
                            "fontFamily": literal("'Segoe UI Semibold'"),
                            "fontSize": literal("13D"),
                            "bold": literal("true"),
                            "fontColor": color(text_color),
                        },
                        "selector": {"id": "selected"},
                    }
                ],
                "fill": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "fillColor": color(fill_color),
                            "transparency": literal("0D"),
                        },
                        "selector": {"id": "default"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "fillColor": color(hover_color),
                            "transparency": literal("0D"),
                        },
                        "selector": {"id": "hover"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "fillColor": color("#E8EDF3"),
                            "transparency": literal("0D"),
                        },
                        "selector": {"id": "disabled"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "fillColor": color(fill_color),
                            "transparency": literal("0D"),
                        },
                        "selector": {"id": "selected"},
                    },
                ],
                "outline": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "lineColor": color(border_color),
                            "transparency": literal("0D"),
                            "weight": literal("1D"),
                        },
                        "selector": {"id": "default"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "lineColor": color("#CBD5E1"),
                            "transparency": literal("0D"),
                            "weight": literal("1D"),
                        },
                        "selector": {"id": "disabled"},
                    },
                    {
                        "properties": {
                            "show": literal("true"),
                            "lineColor": color(border_color),
                            "transparency": literal("0D"),
                            "weight": literal("1D"),
                        },
                        "selector": {"id": "selected"},
                    }
                ],
            },
            "visualContainerObjects": {
                "visualLink": [
                    {
                        "properties": {
                            "show": literal("true"),
                            "type": literal(f"'{action_type}'"),
                            "enabledTooltip": literal(f"'{tooltip}'"),
                            "showDefaultTooltip": literal("true"),
                        }
                    }
                ],
                "background": [{"properties": {"show": literal("false")}}],
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
                "visualHeader": [{"properties": {"show": literal("false")}}],
            },
        },
    }


def information_panel(
    visual_id: str,
    text: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
) -> dict[str, Any]:
    visual = textbox(
        visual_id,
        text,
        x=x,
        y=y,
        width=width,
        height=height,
        z=z,
        font_size=12,
        color_hex="#44546A",
        background_hex="#FFFFFF",
    )
    visual["visual"]["visualContainerObjects"]["border"] = [
        {
            "properties": {
                "show": literal("true"),
                "color": color("#D8E2F0"),
                "width": literal("1D"),
                "radius": literal("8D"),
            }
        }
    ]
    visual["visual"]["visualContainerObjects"]["padding"] = [
        {
            "properties": {
                "top": literal("12D"),
                "bottom": literal("12D"),
                "left": literal("14D"),
                "right": literal("14D"),
            }
        }
    ]
    return visual


def sync_existing_slicers() -> int:
    updated = 0
    for path in PAGES_ROOT.glob("*/visuals/*/visual.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        visual = payload.get("visual", {})
        if visual.get("visualType") != "slicer":
            continue
        projections = (
            visual.get("query", {})
            .get("queryState", {})
            .get("Values", {})
            .get("projections", [])
        )
        if not projections:
            continue
        column = projections[0].get("field", {}).get("Column", {})
        source = column.get("Expression", {}).get("SourceRef", {})
        key = (source.get("Entity"), column.get("Property"))
        group_name = SYNC_GROUPS.get(key)
        if not group_name:
            continue
        desired = {
            "groupName": group_name,
            "fieldChanges": True,
            "filterChanges": True,
        }
        if visual.get("syncGroup") == desired:
            continue
        visual["syncGroup"] = desired
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        updated += 1
    return updated


def build_settings_page() -> None:
    visuals = [
        textbox(
            "s1000000000000000001",
            "Paramétrage et actualisation",
            x=24,
            y=16,
            width=1232,
            height=80,
            z=1,
            font_size=26,
            color_hex="#FFFFFF",
            semibold=True,
            background_hex="#17365D",
        ),
        textbox(
            "s1000000000000000002",
            "Définissez les filtres, appliquez-les en une fois et contrôlez le périmètre chargé.",
            x=40,
            y=56,
            width=1160,
            height=28,
            z=2,
            font_size=13,
            color_hex="#DCE6F2",
        ),
        textbox(
            "s1000000000000000003",
            "Filtres globaux",
            x=40,
            y=116,
            width=300,
            height=32,
            z=3,
            font_size=16,
            color_hex="#17365D",
            semibold=True,
        ),
        positioned_slicer(
            "s1000000000000000004",
            "D_Date",
            "Date",
            "Période",
            x=40,
            y=156,
            width=520,
            height=104,
            z=4,
            mode="Between",
        ),
        positioned_slicer(
            "s1000000000000000005",
            "D_Devise",
            "Devise",
            "Devise",
            x=576,
            y=156,
            width=240,
            height=104,
            z=5,
        ),
        action_button(
            "s1000000000000000006",
            "Appliquer les filtres",
            "ApplyAllSlicers",
            "Appliquer en une fois les sélections de cette page",
            x=840,
            y=168,
            width=192,
            height=72,
            z=6,
            fill_color="#0B5CAD",
            hover_color="#1F77B4",
        ),
        action_button(
            "s1000000000000000007",
            "Réinitialiser",
            "ClearAllSlicers",
            "Effacer toutes les sélections de cette page",
            x=1048,
            y=168,
            width=192,
            height=72,
            z=7,
            fill_color="#FFFFFF",
            hover_color="#E8EDF3",
            text_color="#44546A",
            outline_color="#44546A",
        ),
        textbox(
            "s1000000000000000008",
            "Filtres clients",
            x=40,
            y=284,
            width=300,
            height=32,
            z=8,
            font_size=16,
            color_hex="#17365D",
            semibold=True,
        ),
        positioned_slicer(
            "s1000000000000000009",
            "F_Clients",
            "Statut client",
            "Statut client",
            x=40,
            y=324,
            width=300,
            height=96,
            z=9,
        ),
        positioned_slicer(
            "s1000000000000000010",
            "F_Clients",
            "Type client",
            "Type client",
            x=356,
            y=324,
            width=300,
            height=96,
            z=10,
        ),
        information_panel(
            "s1000000000000000011",
            "Les filtres Période et Devise sont synchronisés avec toutes les feuilles compatibles. "
            "Statut client et Type client s'appliquent à la feuille Clients. Les produits seront "
            "centralisés après création des dimensions Produit dans la base de reporting.",
            x=680,
            y=324,
            width=560,
            height=96,
            z=11,
        ),
        context_card(
            "s1000000000000000012",
            ["Période sélectionnée"],
            "Période active",
            x=40,
            y=444,
            width=392,
            height=112,
            z=12,
            accent_color="#1F77B4",
            value_font_size=18,
            label_font_size=9,
        ),
        context_card(
            "s1000000000000000013",
            ["Devise sélectionnée"],
            "Devise active",
            x=448,
            y=444,
            width=392,
            height=112,
            z=13,
            accent_color="#D43F9A",
            value_font_size=18,
            label_font_size=9,
        ),
        context_card(
            "s1000000000000000014",
            ["Dernière date disponible"],
            "Données chargées jusqu'au",
            x=856,
            y=444,
            width=384,
            height=112,
            z=14,
            accent_color="#70AD47",
            value_font_size=18,
            label_font_size=9,
        ),
        information_panel(
            "s1000000000000000015",
            "ACTUALISATION DES DONNÉES — Dans Power BI Desktop : Accueil > Actualiser. "
            "Dans Power BI Service, le bouton de rafraîchissement sera relié à Power Automate "
            "après publication, configuration de la passerelle et attribution des droits.",
            x=40,
            y=580,
            width=1200,
            height=104,
            z=15,
        ),
    ]
    write_page(PAGE_SETTINGS, "Paramétrage", visuals)


def update_page_order() -> None:
    path = PAGES_ROOT / "pages.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pageOrder"] = [
        PAGE_SETTINGS,
        *[page for page in payload["pageOrder"] if page != PAGE_SETTINGS],
    ]
    payload["activePageName"] = PAGE_SETTINGS
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    build_settings_page()
    updated = sync_existing_slicers()
    update_page_order()
    print(
        "Feuille Paramétrage générée, "
        f"{updated} segment(s) existant(s) synchronisé(s)."
    )


if __name__ == "__main__":
    main()
