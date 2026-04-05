"""Organizer functions for arranging figures and content interactively.

Every public function returns an ipywidget with small **Copy** and
**Download** buttons on the right.  Copy puts the raw HTML on the
clipboard (paste into Confluence ``/html``); Download saves a full
standalone ``.html`` file.
"""

import ipywidgets as widgets

from aloevera.utils import to_widget, wrap_with_buttons
from aloevera.export import (
    content_to_html,
    tabs_html,
    accordion_html,
    dropdown_html,
    slider_html,
)


# ---------------------------------------------------------------------------
# Public organizers
# ---------------------------------------------------------------------------


def tabs(titles, contents):
    """Display contents in horizontal tabs.

    Parameters
    ----------
    titles : list of str
        Tab labels.
    contents : list
        Items to display. Each can be a Plotly Figure, DataFrame,
        HTML string, or any ipywidget (including nested organizers).

    Returns
    -------
    ipywidgets.Widget
        A Tab widget with Copy / Download buttons on the side.

    Example
    -------
    >>> avr.tabs(titles=['Bar', 'Line'], contents=[fig1, fig2])
    """
    _validate_inputs(titles, contents)

    # Build ipywidget version
    children = [to_widget(c) for c in contents]
    tab = widgets.Tab(children=children)
    for i, title in enumerate(titles):
        tab.set_title(i, title)

    # Build HTML export
    html_parts = [content_to_html(c) for c in contents]
    html = tabs_html(titles, html_parts)

    return wrap_with_buttons(tab, html)


def accordion(titles, contents):
    """Display contents in a collapsible accordion.

    Parameters
    ----------
    titles : list of str
        Section labels.
    contents : list
        Items to display.

    Returns
    -------
    ipywidgets.Widget

    Example
    -------
    >>> avr.accordion(titles=['Overview', 'Detail'], contents=[fig1, fig2])
    """
    _validate_inputs(titles, contents)

    children = [to_widget(c) for c in contents]
    acc = widgets.Accordion(children=children, selected_index=0)
    for i, title in enumerate(titles):
        acc.set_title(i, title)

    html_parts = [content_to_html(c) for c in contents]
    html = accordion_html(titles, html_parts)

    return wrap_with_buttons(acc, html)


def dropdown(titles, contents):
    """Select content to display via a dropdown menu.

    Parameters
    ----------
    titles : list of str
        Dropdown option labels.
    contents : list
        Items to display.

    Returns
    -------
    ipywidgets.Widget

    Example
    -------
    >>> avr.dropdown(titles=['Scatter', 'Heatmap'], contents=[fig1, fig2])
    """
    _validate_inputs(titles, contents)
    children = [to_widget(c) for c in contents]

    dd = widgets.Dropdown(
        options=[(title, i) for i, title in enumerate(titles)],
        description="Select:",
    )
    output = widgets.Box(children=[children[0]])

    def _on_change(change):
        output.children = [children[change["new"]]]

    dd.observe(_on_change, names="value")
    widget = widgets.VBox([dd, output])

    html_parts = [content_to_html(c) for c in contents]
    html = dropdown_html(titles, html_parts)

    return wrap_with_buttons(widget, html)


def slider(titles, contents):
    """Navigate contents with a horizontal slider above the content area.

    Drag the slider to select an item by title and display its content.

    Parameters
    ----------
    titles : list of str
        Item labels shown on the slider.
    contents : list
        Items to display.

    Returns
    -------
    ipywidgets.Widget

    Example
    -------
    >>> avr.slider(titles=['A', 'B', 'C'], contents=[fig1, fig2, fig3])
    """
    _validate_inputs(titles, contents)
    children = [to_widget(c) for c in contents]

    sel_slider = widgets.SelectionSlider(
        options=titles,
        value=titles[0],
        description="",
        orientation="horizontal",
        readout=True,
        layout=widgets.Layout(width="100%"),
    )
    content_box = widgets.Box(children=[children[0]])

    def _on_change(change):
        content_box.children = [children[titles.index(change["new"])]]

    sel_slider.observe(_on_change, names="value")

    container = widgets.VBox([sel_slider, content_box])

    html_parts = [content_to_html(c) for c in contents]
    html = slider_html(titles, html_parts)

    return wrap_with_buttons(container, html)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_inputs(titles, contents):
    """Check that titles and contents are lists of the same length."""
    if not isinstance(titles, (list, tuple)):
        raise TypeError("titles must be a list or tuple")
    if not isinstance(contents, (list, tuple)):
        raise TypeError("contents must be a list or tuple")
    if len(titles) != len(contents):
        raise ValueError(
            f"titles and contents must have the same length "
            f"(got {len(titles)} titles and {len(contents)} contents)"
        )
    if len(titles) == 0:
        raise ValueError("titles and contents must not be empty")
