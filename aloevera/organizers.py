"""Organizer functions for arranging figures and content interactively.

Every public function returns an ipywidget with small **Copy** and
**Download** buttons on the right.  Copy puts the raw HTML on the
clipboard (paste into Confluence ``/html``); Download saves a full
standalone ``.html`` file.
"""

import ipywidgets as widgets

from .utils import to_widget, wrap_with_buttons
from .export import (
    content_to_html,
    tabs_html,
    accordion_html,
    dropdown_html,
    scroll_html,
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
    acc = widgets.Accordion(children=children)
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
        options=list(enumerate(titles)),
        description="Select:",
    )
    output = widgets.Box(children=[children[0]])

    def _on_change(change):
        idx = change["new"]
        output.children = [children[idx]]

    dd.observe(_on_change, names="value")
    widget = widgets.VBox([dd, output])

    html_parts = [content_to_html(c) for c in contents]
    html = dropdown_html(titles, html_parts)

    return wrap_with_buttons(widget, html)


def scroll(titles, contents, height="400px"):
    """Display contents in a vertically scrollable list.

    Each item is shown with its title as a header.  Scroll to browse.

    Parameters
    ----------
    titles : list of str
        Section labels shown above each item.
    contents : list
        Items to display.
    height : str, optional
        CSS height of the scrollable container (default ``'400px'``).

    Returns
    -------
    ipywidgets.Widget

    Example
    -------
    >>> avr.scroll(titles=['A', 'B', 'C'], contents=[fig1, fig2, fig3])
    """
    _validate_inputs(titles, contents)
    items = []
    for title, content in zip(titles, contents):
        header = widgets.HTML(
            value=f"<h4 style='margin:8px 0 4px 0;'>{title}</h4>"
        )
        child = to_widget(content)
        items.append(widgets.VBox([header, child]))

    container = widgets.VBox(
        children=items,
        layout=widgets.Layout(
            overflow_y="auto",
            height=height,
            border="1px solid #ddd",
            padding="8px",
        ),
    )

    html_parts = [content_to_html(c) for c in contents]
    html = scroll_html(titles, html_parts, height=height)

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
