"""Utilities for converting content types and adding export buttons."""

import json as _json
import ipywidgets as widgets


# ---------------------------------------------------------------------------
# Content → ipywidget
# ---------------------------------------------------------------------------

def to_widget(content):
    """Convert content to an ipywidget for display.

    Supported content types:
        - plotly.graph_objects.Figure -> FigureWidget
        - plotly.graph_objects.FigureWidget -> used directly
        - pandas.DataFrame -> HTML table widget
        - str -> HTML widget (rendered as raw HTML)
        - ipywidgets.Widget -> used directly (enables nesting)

    Parameters
    ----------
    content : Figure, FigureWidget, DataFrame, str, or Widget
        The content to convert.

    Returns
    -------
    ipywidgets.Widget
    """
    # Already an ipywidget (includes FigureWidget) — use directly
    if isinstance(content, widgets.Widget):
        return content

    # Plotly Figure -> FigureWidget
    # Duck-type check runs before importing plotly to avoid masking ImportErrors.
    # add_trace + update_layout together are unique to plotly BaseFigure.
    if hasattr(content, "add_trace") and hasattr(content, "update_layout"):
        import plotly.graph_objects as go
        return go.FigureWidget(content)

    # pandas DataFrame -> HTML table
    try:
        import pandas as pd

        if isinstance(content, pd.DataFrame):
            html = content.to_html(notebook=True)
            return widgets.HTML(value=html)
    except ImportError:
        pass

    # String -> HTML widget
    if isinstance(content, str):
        return widgets.HTML(value=content)

    raise TypeError(
        f"Unsupported content type: {type(content).__name__}. "
        f"Expected a Plotly Figure, DataFrame, HTML string, or ipywidget."
    )


# ---------------------------------------------------------------------------
# Wrap widget with Copy / Download buttons
# ---------------------------------------------------------------------------

def wrap_with_buttons(widget, html_fragment: str):
    """Add small Copy and Download buttons to the top-right of *widget*.

    Parameters
    ----------
    widget : ipywidgets.Widget
        The organizer widget to wrap.
    html_fragment : str
        The standalone HTML fragment (from ``export.*_html``).

    Returns
    -------
    ipywidgets.Widget
        An HBox with the original widget and a narrow button column.
        The returned widget also carries ``_export_html`` so that
        nested organizers can be exported recursively.
    """
    from aloevera.export import make_standalone

    full_html = make_standalone(html_fragment)
    fragment_js = _json.dumps(html_fragment)
    full_js = _json.dumps(full_html)

    # -- Copy button: copies the HTML fragment to clipboard ------------
    copy_btn = widgets.Button(
        description="",
        tooltip="Copy HTML to clipboard (for Confluence, etc.)",
        icon="copy",
        layout=widgets.Layout(width="36px", height="36px"),
    )
    copy_output = widgets.Output()

    def _on_copy(_btn):
        copy_output.clear_output()
        with copy_output:
            from IPython.display import display, Javascript
            display(Javascript(f"navigator.clipboard.writeText({fragment_js});"))

    copy_btn.on_click(_on_copy)

    # -- Download button: downloads a full standalone HTML file --------
    dl_btn = widgets.Button(
        description="",
        tooltip="Download as standalone HTML file",
        icon="download",
        layout=widgets.Layout(width="36px", height="36px"),
    )
    dl_output = widgets.Output()

    def _on_download(_btn):
        dl_output.clear_output()
        with dl_output:
            from IPython.display import display, Javascript
            display(Javascript(
                f"(function(){{"
                f"var b=new Blob([{full_js}],{{type:'text/html'}});"
                f"var u=URL.createObjectURL(b);"
                f"var a=document.createElement('a');"
                f"a.href=u;a.download='aloevera_export.html';a.click();"
                f"URL.revokeObjectURL(u);"
                f"}})();"
            ))

    dl_btn.on_click(_on_download)

    # -- Layout --------------------------------------------------------
    btn_col = widgets.VBox(
        [copy_btn, dl_btn, copy_output, dl_output],
        layout=widgets.Layout(
            width="44px",
            align_items="center",
            padding="4px 0 0 4px",
        ),
    )

    container = widgets.HBox(
        [widget, btn_col],
        layout=widgets.Layout(align_items="flex-start"),
    )

    # Attach HTML so nested organizers can export recursively
    container._export_html = html_fragment

    # Store the HTML fragment as base64 in a hidden marker div so that
    # export_notebook can find and convert it to a self-contained iframe.
    # Using a data attribute avoids all JS/rendering issues in the notebook output.
    try:
        import base64
        from IPython.display import display, HTML as _HTML
        b64 = base64.b64encode(html_fragment.encode()).decode()
        display(_HTML(
            f'<div class="avr-nb-export" data-avr-b64="{b64}" style="display:none"></div>'
        ))
    except Exception:
        pass

    return container
