from __future__ import annotations

import plotly.graph_objects as go

from credit_app.ui import (
    CHART_COLORWAY,
    _build_plotly_config,
    style_plotly_figure,
    style_standard_donut,
    style_standard_histogram,
    style_standard_line,
)


def test_multi_series_line_keeps_a_readable_legend() -> None:
    fig = go.Figure()
    fig.add_scatter(x=[1, 2], y=[2, 3], name="CDF")
    fig.add_scatter(x=[1, 2], y=[1, 4], name="USD")

    style_standard_line(fig)
    style_plotly_figure(fig)

    assert fig.layout.showlegend is True
    assert fig.layout.legend.orientation == "h"


def test_single_series_line_does_not_add_a_redundant_legend() -> None:
    fig = go.Figure(go.Scatter(x=[1, 2], y=[2, 3], name="Encours"))

    style_standard_line(fig)
    style_plotly_figure(fig)

    assert fig.layout.showlegend is False


def test_small_donut_labels_slices_directly() -> None:
    fig = go.Figure(go.Pie(labels=["Conforme", "À revoir"], values=[8, 2], hole=0.5))

    style_standard_donut(fig)

    assert fig.data[0].textinfo == "label+percent"
    assert fig.layout.showlegend is True


def test_pie_legend_stays_visible_after_shared_theme() -> None:
    fig = go.Figure(go.Pie(labels=["Féminin", "Masculin", "Autre"], values=[6, 3, 1]))

    style_plotly_figure(fig)

    assert fig.layout.showlegend is True
    assert fig.layout.legend.itemclick == "toggle"
    assert fig.layout.legend.itemdoubleclick == "toggleothers"


def test_histogram_categories_keep_clickable_legend() -> None:
    fig = go.Figure()
    fig.add_histogram(x=[20, 30], name="Féminin")
    fig.add_histogram(x=[25, 35], name="Masculin")

    style_standard_histogram(fig)
    style_plotly_figure(fig)

    assert fig.layout.showlegend is True
    assert fig.layout.legend.itemclick == "toggle"


def test_shared_chart_theme_uses_accessible_palette_and_auto_margins() -> None:
    fig = go.Figure(go.Bar(x=["Agence A"], y=[10]))

    style_plotly_figure(fig, height=320)

    assert list(fig.layout.colorway) == CHART_COLORWAY
    assert fig.layout.height == 320
    assert fig.layout.paper_bgcolor == "#ffffff"
    assert fig.layout.plot_bgcolor == "#ffffff"
    assert fig.layout.xaxis.automargin is True
    assert fig.layout.yaxis.automargin is True


def test_plotly_controls_do_not_capture_page_scroll() -> None:
    fig = go.Figure(go.Bar(x=["A"], y=[1]))

    config = _build_plotly_config(fig)

    assert config["displayModeBar"] == "hover"
    assert config["scrollZoom"] is False
    assert config["responsive"] is True


def test_plotly_maplibre_trace_uses_geo_controls() -> None:
    fig = go.Figure(go.Scattermap(lat=[-4.32], lon=[15.31]))

    config = _build_plotly_config(fig)

    assert config["modeBarButtonsToAdd"] == ["zoomInGeo", "zoomOutGeo", "resetGeo"]
