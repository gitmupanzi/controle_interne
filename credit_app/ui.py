from __future__ import annotations

import html
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


CHART_COLORWAY = ["#1553A1", "#D97B16", "#2D7D46", "#8A5A9E", "#D5A021"]
CHART_NEUTRAL = "#5F6F82"


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
        padding-top: 0.85rem;
        padding-bottom: 2rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f2f6fb 0%, #e8f0f7 100%);
        border-right: 1px solid rgba(11, 44, 99, 0.08);
    }

    section[data-testid="stSidebar"] > div {
        background:
            radial-gradient(circle at top right, rgba(43, 116, 202, 0.08), transparent 28%),
            linear-gradient(180deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.02) 100%);
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
        border-radius: 16px;
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

    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        border-radius: 14px;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        background: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(11, 44, 99, 0.10) !important;
        box-shadow: 0 8px 18px rgba(11, 44, 99, 0.05);
    }

    section[data-testid="stSidebar"] [data-baseweb="tag"] {
        background: rgba(21, 83, 161, 0.10) !important;
        border: 1px solid rgba(21, 83, 161, 0.12) !important;
        color: #0f438f !important;
        font-weight: 700;
    }

    section[data-testid="stSidebar"] .stCheckbox {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(11, 44, 99, 0.08);
        border-radius: 14px;
        padding: 0.35rem 0.55rem 0.15rem;
    }

    .credit-sidebar-card {
        background:
            linear-gradient(140deg, rgba(255,255,255,0.94) 0%, rgba(238,245,255,0.96) 100%);
        border: 1px solid rgba(11, 44, 99, 0.10);
        border-radius: 20px;
        box-shadow: 0 14px 28px rgba(11, 44, 99, 0.08);
        padding: 0.95rem 1rem;
        margin-bottom: 0.8rem;
    }

    .credit-sidebar-card.sidebar-intro {
        background:
            linear-gradient(125deg, rgba(11,44,99,0.96) 0%, rgba(21,83,161,0.94) 55%, rgba(44,117,200,0.92) 100%);
        color: #ffffff;
        box-shadow: 0 18px 34px rgba(11, 44, 99, 0.22);
    }

    .credit-sidebar-kicker {
        font-size: 0.68rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        font-weight: 800;
        opacity: 0.78;
        margin-bottom: 0.25rem;
    }

    .credit-sidebar-title {
        color: #0b2c63;
        font-size: 1rem;
        font-weight: 800;
        line-height: 1.15;
        margin-bottom: 0.25rem;
    }

    .credit-sidebar-card.sidebar-intro .credit-sidebar-title {
        color: #ffffff;
    }

    .credit-sidebar-subtitle {
        color: #43607f;
        font-size: 0.78rem;
        line-height: 1.35;
        margin-bottom: 0.15rem;
    }

    .credit-sidebar-card.sidebar-intro .credit-sidebar-subtitle,
    .credit-sidebar-card.sidebar-intro .credit-sidebar-kicker {
        color: rgba(255,255,255,0.92);
    }

    .credit-sidebar-section {
        margin: 0.7rem 0 0.45rem;
    }

    .credit-sidebar-section .section-title {
        color: #0b2c63;
        font-size: 0.88rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        margin-bottom: 0.12rem;
    }

    .credit-sidebar-section .section-subtitle {
        color: #55708f;
        font-size: 0.75rem;
        line-height: 1.3;
        margin-bottom: 0.28rem;
    }

    .credit-sidebar-stats {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.45rem;
        margin-bottom: 0.65rem;
    }

    .credit-sidebar-stat {
        background: rgba(255,255,255,0.80);
        border: 1px solid rgba(11, 44, 99, 0.08);
        border-radius: 16px;
        padding: 0.55rem 0.65rem;
    }

    .credit-sidebar-stat .label {
        color: #5d7390;
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        margin-bottom: 0.18rem;
    }

    .credit-sidebar-stat .value {
        color: #0b2c63;
        font-size: 0.95rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .credit-hero {
        position: relative;
        overflow: hidden;
        padding: 1.15rem 1.45rem;
        margin-bottom: 1.1rem;
        border-radius: 20px;
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
        margin: 0.55rem 0 0.5rem;
        color: var(--credit-blue-dark);
        font-size: 1rem;
        letter-spacing: 0.015em;
        font-weight: 800;
    }

    .credit-section-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        margin: 1.15rem 0 0.75rem;
        padding-bottom: 0.65rem;
        border-bottom: 1px solid rgba(11, 44, 99, 0.10);
    }

    .credit-section-header h2 {
        color: var(--credit-blue-dark);
        font-size: clamp(1.15rem, 1.8vw, 1.45rem);
        line-height: 1.2;
        margin: 0;
    }

    .credit-section-header p {
        color: #526a86;
        font-size: 0.84rem;
        margin: 0.24rem 0 0;
        max-width: 52rem;
    }

    .credit-section-badge {
        flex: 0 0 auto;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: #eaf2ff;
        color: #1553a1;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .credit-empty-state {
        padding: 1.25rem 1.35rem;
        border: 1px dashed rgba(21, 83, 161, 0.28);
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.78);
        margin: 0.7rem 0 1rem;
    }

    .credit-empty-state .empty-title {
        color: var(--credit-blue-dark);
        font-size: 1rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }

    .credit-empty-state .empty-message {
        color: #526a86;
        font-size: 0.86rem;
        line-height: 1.45;
    }

    .credit-chart-guide {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.65rem;
        margin: 0.55rem 0 0.9rem;
    }

    .credit-chart-guide > div {
        padding: 0.65rem 0.75rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(11,44,99,0.08);
        color: #415a77;
        font-size: 0.76rem;
        line-height: 1.35;
    }

    .credit-chart-guide strong { color: #0b2c63; }

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
        flex-wrap: nowrap;
        overflow-x: auto;
        scrollbar-width: thin;
        padding-bottom: 0.35rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 0.55rem 0.95rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(11, 44, 99, 0.10);
        color: #173963;
        font-weight: 700;
        flex: 0 0 auto;
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
        border-radius: 16px;
        padding: 0.35rem 0.5rem 0.15rem;
        border: 1px solid rgba(11, 44, 99, 0.08);
        box-shadow: 0 8px 20px rgba(11, 44, 99, 0.06);
        margin-bottom: 0.75rem;
    }

    div[data-testid="stPlotlyChart"] .modebar {
        z-index: 30 !important;
    }

    div[data-testid="stPlotlyChart"] .modebar-btn {
        pointer-events: auto !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 999px;
        border: 1px solid rgba(11, 44, 99, 0.10);
        background: linear-gradient(90deg, #0b2c63 0%, #1553a1 100%);
        color: white;
        font-weight: 700;
    }

    button:focus-visible,
    [role="tab"]:focus-visible,
    input:focus-visible {
        outline: 3px solid rgba(21, 83, 161, 0.28) !important;
        outline-offset: 2px;
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

    @media (max-width: 900px) {
        .main .block-container { padding: 0.65rem 0.8rem 1.5rem; }
        .credit-hero { padding: 1rem 1.05rem; border-radius: 16px; }
        .credit-context-row { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.55rem; }
        .credit-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.6rem; }
        .credit-chart-guide { grid-template-columns: 1fr; }
        .credit-section-header { align-items: center; }
    }

    @media (max-width: 560px) {
        .credit-context-row,
        .credit-kpi-grid { grid-template-columns: 1fr; }
        .credit-section-header { display: block; }
        .credit-section-badge { display: inline-block; margin-top: 0.5rem; }
        .credit-hero p { font-size: 0.88rem; }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_professional_header(
    cycle_label: str | None = None,
    cycle_summary: str | None = None,
) -> None:
    badge = cycle_label or "Contrôle interne"
    summary = cycle_summary or (
        "Standardisez une base Excel ou CSV, harmonisez la lecture des opérations et "
        "pilotez les risques, la conformité et les actions de contrôle."
    )
    st.markdown(
        f"""
<div class="credit-hero">
  <div class="credit-hero-badge">{html.escape(badge)}</div>
  <h1>Contrôle interne IMF</h1>
  <p>{html.escape(summary)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_intro_card(
    kicker: str,
    title: str,
    lines: list[str],
    *,
    container: Any | None = None,
) -> None:
    content = "".join(f"<div class='credit-sidebar-subtitle'>{html.escape(str(line))}</div>" for line in lines)
    target = container or st.sidebar
    target.markdown(
        f"""
<div class="credit-sidebar-card sidebar-intro">
  <div class="credit-sidebar-kicker">{html.escape(str(kicker))}</div>
  <div class="credit-sidebar-title">{html.escape(str(title))}</div>
  {content}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_section(
    title: str,
    subtitle: str | None = None,
    *,
    container: Any | None = None,
) -> None:
    subtitle_html = (
        f"<div class='section-subtitle'>{html.escape(str(subtitle))}</div>"
        if subtitle
        else ""
    )
    target = container or st.sidebar
    target.markdown(
        f"""
<div class="credit-sidebar-section">
  <div class="section-title">{html.escape(str(title))}</div>
  {subtitle_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_stat_grid(
    items: list[tuple[str, str]],
    *,
    container: Any | None = None,
) -> None:
    blocks = "".join(
        f"""
<div class="credit-sidebar-stat">
  <div class="label">{html.escape(str(label))}</div>
  <div class="value">{html.escape(str(value))}</div>
</div>
"""
        for label, value in items
    )
    target = container or st.sidebar
    target.markdown(f"<div class='credit-sidebar-stats'>{blocks}</div>", unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        """
<div class="credit-footer">
  Contrôle interne IMF
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


def render_dashboard_section(title: str, description: str, badge: str | None = None) -> None:
    badge_html = (
        f"<div class='credit-section-badge'>{html.escape(str(badge))}</div>"
        if badge
        else ""
    )
    st.markdown(
        f"""
<div class="credit-section-header">
  <div>
    <h2>{html.escape(str(title))}</h2>
    <p>{html.escape(str(description))}</p>
  </div>
  {badge_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, message: str) -> None:
    st.markdown(
        f"""
<div class="credit-empty-state">
  <div class="empty-title">{html.escape(str(title))}</div>
  <div class="empty-message">{html.escape(str(message))}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_chart_guide() -> None:
    st.markdown(
        """
<div class="credit-chart-guide">
  <div><strong>Survoler</strong><br>Affiche les valeurs et la catégorie exacte.</div>
  <div><strong>Cliquer sur la légende</strong><br>Masque ou réaffiche une série.</div>
  <div><strong>Barre d’outils</strong><br>Zoomez ou exportez le graphique en PNG.</div>
</div>
        """,
        unsafe_allow_html=True,
    )


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
    trace_count = len(fig.data)
    has_selectable_pie_categories = any(
        str(getattr(trace, "type", "")).lower() == "pie"
        and getattr(trace, "labels", None) is not None
        and len(trace.labels) > 1
        for trace in fig.data
    )
    named_traces = [
        trace
        for trace in fig.data
        if str(getattr(trace, "name", "")).strip() not in {"", "None", "trace 0"}
    ]
    should_show_legend = has_selectable_pie_categories or (trace_count > 1 and len(named_traces) > 1)
    fig.update_layout(
        template="plotly_white",
        colorway=CHART_COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#20344f", size=11, family="Arial, sans-serif"),
        showlegend=should_show_legend if fig.layout.showlegend is None else fig.layout.showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=10),
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        margin=dict(l=52, r=28, t=38, b=52),
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.97)",
            bordercolor="rgba(11, 44, 99, 0.16)",
            font=dict(color="#173963", size=11),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        automargin=True,
        separatethousands=True,
        linecolor="rgba(9,37,79,0.10)",
        tickfont=dict(size=9, color="#58708f"),
        title_font=dict(size=10, color="#58708f"),
    )
    fig.update_yaxes(
        showgrid=True,
        automargin=True,
        separatethousands=True,
        gridcolor="rgba(9,37,79,0.08)",
        zeroline=False,
        tickfont=dict(size=9, color="#58708f"),
        title_font=dict(size=10, color="#58708f"),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


def style_standard_vertical_bar(fig: go.Figure, *, height: int = 360, tickangle: int = -25) -> go.Figure:
    fig.update_traces(
        marker_line_color="rgba(255,255,255,0.50)",
        marker_line_width=1.15,
        opacity=0.94,
    )
    fig.update_layout(
        height=height,
        showlegend=len(fig.data) > 1,
        bargap=0.22,
        xaxis_tickangle=tickangle,
        yaxis=dict(gridcolor="rgba(15, 53, 103, 0.08)", zeroline=False),
    )
    return fig


def style_standard_horizontal_bar(fig: go.Figure, *, height: int = 360) -> go.Figure:
    fig.update_traces(
        marker_line_color="rgba(255,255,255,0.50)",
        marker_line_width=1.15,
        opacity=0.94,
    )
    fig.update_layout(
        height=height,
        showlegend=len(fig.data) > 1,
        bargap=0.18,
        xaxis=dict(gridcolor="rgba(15, 53, 103, 0.08)", zeroline=False),
        yaxis=dict(gridcolor="rgba(15, 53, 103, 0.00)", zeroline=False),
    )
    return fig


def style_standard_line(fig: go.Figure, *, height: int = 360, tickangle: int = -25) -> go.Figure:
    fig.update_traces(
        line=dict(width=2.6),
        marker=dict(size=6, line=dict(width=1, color="#ffffff")),
    )
    fig.update_layout(
        height=height,
        showlegend=len(fig.data) > 1,
        xaxis_tickangle=tickangle,
        yaxis=dict(gridcolor="rgba(15, 53, 103, 0.08)", zeroline=False),
        hovermode="x unified",
    )
    return fig


def style_standard_donut(fig: go.Figure, *, height: int = 360) -> go.Figure:
    max_slice_count = max(
        (
            len(labels)
            for trace in fig.data
            for labels in [getattr(trace, "labels", None)]
            if labels is not None
        ),
        default=0,
    )
    fig.update_traces(
        textinfo="label+percent" if max_slice_count <= 5 else "percent",
        textposition="auto",
        textfont_size=12,
        marker=dict(line=dict(color="rgba(255,255,255,0.92)", width=2)),
        sort=False,
        hovertemplate="%{label}<br>%{value:,.0f} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        height=height,
        # Plotly allows users to click legend entries to keep only the desired
        # categories. Keep this interaction available even for two slices.
        showlegend=max_slice_count > 1,
        legend=dict(orientation="h"),
        margin=dict(l=30, r=30, t=30, b=44),
    )
    return fig


def style_standard_histogram(fig: go.Figure, *, height: int = 360, tickangle: int = 0) -> go.Figure:
    fig.update_traces(
        marker_line_color="rgba(255,255,255,0.45)",
        marker_line_width=1.0,
        opacity=0.94,
    )
    fig.update_layout(
        height=height,
        # A histogram split by category creates one trace per category. Its
        # legend must remain clickable so users can isolate a population.
        showlegend=len(fig.data) > 1,
        bargap=0.06,
        xaxis_tickangle=tickangle,
        yaxis=dict(gridcolor="rgba(15, 53, 103, 0.08)", zeroline=False),
    )
    return fig


def _json_safe_plotly_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe_plotly_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_plotly_value(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def sanitize_plotly_figure_for_streamlit(fig: go.Figure | None) -> go.Figure | None:
    if fig is None:
        return fig
    try:
        return go.Figure(_json_safe_plotly_value(fig.to_plotly_json()))
    except Exception:
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


def _build_plotly_config(fig: go.Figure) -> dict[str, Any]:
    trace_types = {str(getattr(trace, "type", "")).lower() for trace in fig.data}
    cartesian_types = {
        "bar",
        "scatter",
        "scattergl",
        "histogram",
        "box",
        "violin",
        "heatmap",
        "contour",
        "waterfall",
        "funnel",
        "ohlc",
        "candlestick",
    }
    geo_types = {
        "choropleth",
        "scattergeo",
        "choroplethmap",
        "scattermap",
        "densitymap",
        # Compatibilite de lecture d'anciennes figures mises en cache.
        "choroplethmapbox",
        "scattermapbox",
        "densitymapbox",
    }

    config: dict[str, Any] = {
        "displaylogo": False,
        "displayModeBar": "hover",
        "responsive": True,
        "scrollZoom": False,
        "doubleClick": "reset",
        "showTips": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "controle_interne_imf_graphique",
            "scale": 2,
        },
    }

    if trace_types & geo_types:
        config["modeBarButtonsToAdd"] = ["zoomInGeo", "zoomOutGeo", "resetGeo"]
        return config

    if trace_types & cartesian_types:
        config["modeBarButtons"] = [
            ["toImage"],
            ["zoom2d"],
            ["pan2d"],
            ["zoomIn2d"],
            ["zoomOut2d"],
            ["autoScale2d"],
            ["resetScale2d"],
        ]
        return config

    config["modeBarButtons"] = [["toImage"]]
    return config


def st_plot(
    fig: go.Figure,
    *,
    key: str | None = None,
    height: int | None = None,
    annotate_values: bool | None = None,
    annotation_min_value: float | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source_note: str | None = None,
) -> Any:
    if fig is None or not fig.data:
        st.info("Aucune donnée disponible pour ce graphique avec les filtres actuels.")
        return None
    if title:
        title_text = f"<b>{html.escape(str(title))}</b>"
        if subtitle:
            title_text += f"<br><span style='font-size:11px;color:#58708f'>{html.escape(str(subtitle))}</span>"
        fig.update_layout(
            title=dict(text=title_text, x=0, xanchor="left", font=dict(size=15, color="#0b2c63")),
            margin=dict(t=72),
        )
    if annotate_values is None:
        annotate_values = bool(st.session_state.get("credit_annot_vals", False))
    if annotation_min_value is None:
        annotation_min_value = float(st.session_state.get("credit_annot_min", 1))
    if annotate_values:
        fig = _apply_trace_annotations(fig, min_value=float(annotation_min_value))
    fig = style_plotly_figure(fig, height=height)
    fig = sanitize_plotly_figure_for_streamlit(fig)
    config = _build_plotly_config(fig)
    if key is not None:
        result = st.plotly_chart(fig, width="stretch", key=key, config=config)
    else:
        result = st.plotly_chart(fig, width="stretch", config=config)
    if source_note:
        st.caption(source_note)
    return result


def format_context_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and pd.isna(value):
        return "-"
    return str(value)
