"""Thin wrappers around plotly.express for quick figure creation.

Instead of::

    import plotly.express as px
    fig = px.line(df, x='day', y='price', title='Trend')

use::

    fig = avr.plot('line', df, x='day', y='price', title='Trend')

The ``kind`` argument is the name of any ``plotly.express`` function.
All remaining positional and keyword arguments are forwarded to it unchanged,
and ``DEFAULT_LAYOUT`` is applied on top as a baseline style.
"""

import plotly.graph_objects as _go

# ---------------------------------------------------------------------------
# Default layout applied to every avr.plot() figure.
# Any key present here is skipped if the caller already supplied it as a kwarg,
# so per-call overrides always win.  Mutate this dict to change the global
# default (e.g. ``avr.DEFAULT_LAYOUT['height'] = 600``).
# ---------------------------------------------------------------------------
DEFAULT_LAYOUT: dict = {
    'template': 'plotly_white',
    'height': 400,
    'width': 700,
    'title_x': 0.5,   # centre the title
}

# Representative subset used only in error messages.
_COMMON_KINDS = [
    "area", "bar", "box", "density_contour", "density_heatmap",
    "ecdf", "funnel", "histogram", "line", "pie", "scatter",
    "scatter_3d", "scatter_matrix", "strip", "sunburst", "treemap", "violin",
]

# These keys are valid kwargs for plotly.express functions and should be
# injected before the px call so the figure is built with the right values.
# Everything else in DEFAULT_LAYOUT goes through fig.update_layout() after.
_PX_LAYOUT_KEYS = frozenset({'template', 'height', 'width'})


def plot(kind: str, *args, **kwargs) -> _go.Figure:
    """Create a Plotly Express figure with aloevera's default styling.

    Parameters
    ----------
    kind : str
        Name of the ``plotly.express`` function to call.
        ``'line'`` → ``px.line``, ``'bar'`` → ``px.bar``, etc.
    *args, **kwargs
        Forwarded directly to the ``plotly.express`` function.
        Any key that also appears in ``DEFAULT_LAYOUT`` overrides the default
        for this call only.

    Returns
    -------
    plotly.graph_objects.Figure

    Examples
    --------
    >>> avr.plot('line', df, x='day', y='price', title='Price Trend')
    >>> avr.plot('bar', df, x='month', y='revenue', color='category')
    >>> avr.plot('scatter', df, x='customers', y='revenue', size='profit')
    >>> avr.plot('histogram', df, x='value', nbins=30)
    >>> # Override a default for one call:
    >>> avr.plot('line', df, x='day', y='price', height=600, template='ggplot2')

    Combine with organizers:

    >>> avr.tabs(
    ...     titles=['Line', 'Bar', 'Scatter'],
    ...     contents=[
    ...         avr.plot('line', df, x='day', y='price'),
    ...         avr.plot('bar', df, x='month', y='revenue'),
    ...         avr.plot('scatter', df, x='customers', y='revenue'),
    ...     ],
    ... )
    """
    try:
        import plotly.express as px
    except ImportError as exc:
        raise ImportError("plotly is required for avr.plot()") from exc

    func = getattr(px, kind, None)
    if func is None or not callable(func):
        raise ValueError(
            f"Unknown plot kind: {kind!r}. "
            f"Pass the name of any plotly.express function, e.g. "
            f"{', '.join(repr(k) for k in _COMMON_KINDS[:6])}, ..."
        )

    # Inject px-level defaults (template, height, width) before the call;
    # caller kwargs take priority via the right-hand merge.
    px_defaults = {k: DEFAULT_LAYOUT[k] for k in _PX_LAYOUT_KEYS if k in DEFAULT_LAYOUT}
    fig = func(*args, **{**px_defaults, **kwargs})

    # Apply remaining DEFAULT_LAYOUT keys (e.g. title_x) via update_layout,
    # skipping any that the caller already supplied.
    post_updates = {
        k: v for k, v in DEFAULT_LAYOUT.items()
        if k not in _PX_LAYOUT_KEYS and k not in kwargs
    }
    if post_updates:
        fig.update_layout(**post_updates)

    return fig
