from __future__ import annotations

import html
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def inject_professional_credit_css() -> None:
    st.markdown(
        """
<style>
    :root {
        --credit-blue-dark: #0b2c63;
        --credit-blue: #1553a1;
        --credit-blue-soft: #eaf2ff;
        --credit-green: #2d7d46;
        --credit-green-soft: #eef8f1;
        --credit-orange: #d97b16;
        --credit-orange-soft: #fff4e8;
        --credit-red: #b9353f;
        --credit-slate: #44536a;
        --credit-border: rgba(18, 53, 106, 0.10);
        --credit-shadow: 0 14px 30px rgba(11, 44, 99, 0.10);
        --credit-card-bg: rgba(255, 255, 255, 0.92);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(39, 107, 191, 0.12), transparent 30%),
            radial-gradient(circle at top right, rgba(45, 125, 70, 0.12), transparent 26%),
            linear-gradient(180deg, #f4f8fd 0%, #edf3f9 46%, #f6f8fc 100%);
    }

    .main .block-container {
        max-width: 1480px;
        padding-top: 1.15rem;
        padding-bottom: 2rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f2f6fb 0%, #e8f0f7 100%);
        border-right: 1px solid rgba(11, 44, 99, 0.08);
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .st-emotion-cache-pkbazv {
        color: #18365f;
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.76);
        border: 1px dashed rgba(21, 83, 161, 0.24);
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #0b2c63;
        letter-spacing: 0.01em;
        font-weight: 800;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.48);
        border: 1px solid rgba(11, 44, 99, 0.08);
        border-radius: 16px;
        overflow: hidden;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary {
        background: rgba(255, 255, 255, 0.62);
        border-radius: 16px;
    }

    .credit-hero {
        position: relative;
        overflow: hidden;
        padding: 1.35rem 1.75rem;
        margin-bottom: 1.1rem;
        border-radius: 24px;
        color: #ffffff;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02)),
            linear-gradient(90deg, #072654 0%, #0f438f 56%, #2c75c8 100%);
        box-shadow: 0 18px 40px rgba(7, 38, 84, 0.24);
        border: 1px solid rgba(255,255,255,0.18);
    }

    .credit-hero::before,
    .credit-hero::after {
        content: "";
        position: absolute;
        border-radius: 50%;
        background: rgba(255,255,255,0.10);
        filter: blur(6px);
    }

    .credit-hero::before {
        width: 220px;
        height: 220px;
        top: -130px;
        right: -30px;
    }

    .credit-hero::after {
        width: 160px;
        height: 160px;
        bottom: -90px;
        left: -20px;
    }

    .credit-hero-badge {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        margin-bottom: 0.8rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.16);
        font-size: 0.82rem;
        letter-spacing: 0.14em;
        font-weight: 700;
        text-transform: uppercase;
    }

    .credit-hero h1 {
        margin: 0;
        font-size: clamp(1.6rem, 2.8vw, 2.2rem);
        line-height: 1.15;
        letter-spacing: 0.03em;
        font-weight: 800;
    }

    .credit-hero p {
        margin: 0.45rem 0 0;
        font-size: 1rem;
        opacity: 0.94;
        font-weight: 500;
        max-width: 62rem;
    }

    .credit-context-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 0.8rem;
        margin: 0.8rem 0 1rem;
    }

    .credit-context-chip {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid var(--credit-border);
        box-shadow: var(--credit-shadow);
        border-radius: 18px;
        padding: 0.85rem 1rem;
    }

    .credit-context-chip .label {
        color: var(--credit-slate);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }

    .credit-context-chip .value {
        color: var(--credit-blue-dark);
        font-size: 1rem;
        font-weight: 800;
        margin-top: 0.28rem;
    }

    .credit-kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(205px, 1fr));
        gap: 0.9rem;
        margin-bottom: 0.75rem;
        align-items: stretch;
    }

    .credit-kpi-card {
        min-height: 108px;
        border-radius: 16px;
        padding: 0.86rem 0.92rem 0.82rem;
        color: var(--credit-blue-dark);
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 18px rgba(18, 53, 106, 0.08);
        height: 100%;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, var(--card-soft, rgba(247, 250, 255, 0.96)) 100%);
        border: 1px solid color-mix(in srgb, var(--card-accent) 22%, rgba(18, 53, 106, 0.08));
        --card-accent: #2b74ca;
        --card-soft: rgba(234, 243, 255, 0.72);
    }

    .credit-kpi-card::before {
        content: "";
        position: absolute;
        inset: auto 0 0 0;
        height: 3px;
        background: var(--card-accent);
    }

    .credit-kpi-card::after {
        display: none;
    }

    .credit-kpi-card.blue { --card-accent: #2b74ca; --card-soft: rgba(231, 241, 255, 0.88); }
    .credit-kpi-card.navy { --card-accent: #314468; --card-soft: rgba(237, 241, 248, 0.88); }
    .credit-kpi-card.orange { --card-accent: #e78a1f; --card-soft: rgba(255, 244, 228, 0.92); }
    .credit-kpi-card.green { --card-accent: #179256; --card-soft: rgba(233, 249, 241, 0.92); }
    .credit-kpi-card.red { --card-accent: #ea3c3c; --card-soft: rgba(255, 238, 238, 0.94); }
    .credit-kpi-card.slate { --card-accent: #6b768d; --card-soft: rgba(241, 244, 249, 0.94); }

    .credit-kpi-title {
        color: #58708f;
        opacity: 1;
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        line-height: 1.16;
        font-weight: 800;
        margin-bottom: 0.26rem;
    }

    .credit-kpi-value {
        color: var(--card-accent);
        font-size: clamp(1.06rem, 1.55vw, 1.55rem);
        line-height: 1;
        font-weight: 800;
        margin-bottom: 0.26rem;
        word-break: break-word;
    }

    .credit-kpi-subtitle {
        color: #314968;
        opacity: 1;
        font-size: 0.72rem;
        line-height: 1.15;
        font-weight: 500;
        word-break: break-word;
    }

    .credit-panel-title {
        margin: 0.35rem 0 0.55rem;
        color: var(--credit-blue-dark);
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .credit-summary-box {
        padding: 0.95rem 1rem;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid var(--credit-border);
        box-shadow: var(--credit-shadow);
        margin-bottom: 0.8rem;
    }

    .credit-summary-box .summary-lead {
        color: var(--credit-blue-dark);
        font-weight: 800;
        margin-bottom: 0.35rem;
    }

    .credit-summary-box p,
    .credit-summary-box li {
        color: #26415f;
        margin-bottom: 0.2rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 0.55rem 0.95rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(11, 44, 99, 0.10);
        color: #173963;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #0b2c63 0%, #1553a1 100%);
        color: #ffffff !important;
        border-color: transparent;
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid rgba(11, 44, 99, 0.08);
        border-radius: 16px;
        padding: 0.45rem 0.65rem;
        box-shadow: 0 10px 24px rgba(11, 44, 99, 0.08);
    }

    div[data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.84);
        border-radius: 18px;
        padding: 0.15rem;
        border: 1px solid rgba(11, 44, 99, 0.08);
        box-shadow: 0 10px 24px rgba(11, 44, 99, 0.06);
    }

    div[data-testid="stPlotlyChart"] {
        background: rgba(255, 255, 255, 0.92);
        border-radius: 20px;
        padding: 0.55rem 0.75rem 0.25rem;
        border: 1px solid rgba(11, 44, 99, 0.08);
        box-shadow: 0 14px 28px rgba(11, 44, 99, 0.08);
        margin-bottom: 0.75rem;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 999px;
        border: 1px solid rgba(11, 44, 99, 0.10);
        background: linear-gradient(90deg, #0b2c63 0%, #1553a1 100%);
        color: white;
        font-weight: 700;
    }

    .credit-footer {
        margin-top: 1.25rem;
        padding: 0.85rem 1rem;
        color: #44536a;
        font-size: 0.92rem;
        text-align: center;
    }

    @media (max-width: 1280px) {
        .credit-kpi-grid {
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        }

        .credit-kpi-value {
            font-size: clamp(1rem, 1.45vw, 1.4rem);
        }
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_professional_header() -> None:
    st.markdown(
        """
<div class="credit-hero">
  <div class="credit-hero-badge">Plateforme credit</div>
  <h1>Analyste Credit</h1>
  <p>
    Standardisez une base Excel ou CSV, appliquez une lecture metier credit commune
    et restituez les analyses portefeuille, risque, remboursement et qualite dans
    une interface unique.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
<div class="credit-footer">
  Analyste Credit
</div>
        """,
        unsafe_allow_html=True,
    )


def render_context_row(context_items: list[tuple[str, str]]) -> None:
    html_blocks = []
    for label, value in context_items:
        html_blocks.append(
            f"""
<div class="credit-context-chip">
  <div class="label">{html.escape(str(label))}</div>
  <div class="value">{html.escape(str(value))}</div>
</div>
"""
        )
    st.markdown(f"<div class='credit-context-row'>{''.join(html_blocks)}</div>", unsafe_allow_html=True)


def build_kpi_card_html(title: str, value: str, subtitle: str, theme: str) -> str:
    return f"""
<div class="credit-kpi-card {html.escape(theme)}">
  <div class="credit-kpi-title">{html.escape(str(title))}</div>
  <div class="credit-kpi-value">{html.escape(str(value))}</div>
  <div class="credit-kpi-subtitle">{html.escape(str(subtitle))}</div>
</div>
"""


def render_kpi_cards(cards: list[tuple[str, str, str, str]]) -> None:
    cards_html = "".join(build_kpi_card_html(*card) for card in cards)
    st.markdown(f"<div class='credit-kpi-grid'>{cards_html}</div>", unsafe_allow_html=True)


def render_panel_title(title: str) -> None:
    st.markdown(f"<div class='credit-panel-title'>{html.escape(str(title))}</div>", unsafe_allow_html=True)


def render_summary_box(lead: str, lines: list[str]) -> None:
    content = "".join(f"<li>{html.escape(str(line))}</li>" for line in lines)
    st.markdown(
        f"""
<div class="credit-summary-box">
  <div class="summary-lead">{html.escape(str(lead))}</div>
  <ul>{content}</ul>
</div>
        """,
        unsafe_allow_html=True,
    )


def style_plotly_figure(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#20344f", size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=10),
        ),
        margin=dict(l=42, r=20, t=46, b=42),
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.97)",
            bordercolor="rgba(11, 44, 99, 0.16)",
            font=dict(color="#173963", size=11),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor="rgba(9,37,79,0.10)",
        tickfont=dict(size=9, color="#58708f"),
        title_font=dict(size=10, color="#58708f"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(9,37,79,0.08)",
        zeroline=False,
        tickfont=dict(size=9, color="#58708f"),
        title_font=dict(size=10, color="#58708f"),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


def _format_annotation_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(numeric_value):
        return ""
    if abs(numeric_value) >= 1000:
        return f"{numeric_value:,.0f}".replace(",", " ")
    if numeric_value.is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:.1f}"


def _annotation_text(value: Any, min_value: float) -> str:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return ""
    if pd.isna(numeric_value) or numeric_value < min_value:
        return ""
    return _format_annotation_value(numeric_value)


def _apply_trace_annotations(fig: go.Figure, min_value: float = 1.0) -> go.Figure:
    for trace in fig.data:
        trace_type = getattr(trace, "type", "")
        if trace_type == "bar":
            orientation = getattr(trace, "orientation", "v")
            raw_values = getattr(trace, "x" if orientation == "h" else "y", None)
            values = list(raw_values) if raw_values is not None else []
            texts = [_annotation_text(value, min_value) for value in values]
            if any(texts):
                trace.text = texts
                trace.textposition = "outside"
                trace.cliponaxis = False
                trace.textfont = dict(size=10, color="#42566f")
        elif trace_type == "scatter":
            raw_values = getattr(trace, "y", None)
            values = list(raw_values) if raw_values is not None else []
            texts = [_annotation_text(value, min_value) for value in values]
            if any(texts):
                mode = str(getattr(trace, "mode", "lines"))
                if "text" not in mode:
                    trace.mode = mode + "+text"
                trace.text = texts
                trace.textposition = "top center"
                trace.textfont = dict(size=9, color="#42566f")
        elif trace_type == "pie":
            raw_values = getattr(trace, "values", None)
            values = list(raw_values) if raw_values is not None else []
            visible_texts = [_annotation_text(value, min_value) for value in values]
            if any(visible_texts):
                trace.textinfo = "percent"
                trace.textposition = "inside"
                trace.insidetextfont = dict(size=11, color="#ffffff")
    return fig


def st_plot(
    fig: go.Figure,
    *,
    key: str | None = None,
    height: int | None = None,
    annotate_values: bool | None = None,
    annotation_min_value: float | None = None,
) -> Any:
    if annotate_values is None:
        annotate_values = bool(st.session_state.get("credit_annot_vals", False))
    if annotation_min_value is None:
        annotation_min_value = float(st.session_state.get("credit_annot_min", 1))
    if annotate_values:
        fig = _apply_trace_annotations(fig, min_value=float(annotation_min_value))
    fig = style_plotly_figure(fig, height=height)
    config = {
        "displaylogo": False,
        "displayModeBar": False,
        "responsive": True,
    }
    if key is not None:
        return st.plotly_chart(fig, width="stretch", key=key, config=config)
    return st.plotly_chart(fig, width="stretch", config=config)


def format_context_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and pd.isna(value):
        return "-"
    return str(value)
