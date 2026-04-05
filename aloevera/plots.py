"""Thin wrappers around plotly.express for quick figure creation.

Instead of::

    import plotly.express as px
    fig = px.line(df, x='day', y='price', title='Trend')

use::

    fig = avr.plot('line', df, x='day', y='price', title='Trend')

The ``kind`` argument is the name of any ``plotly.express`` function.
All remaining positional and keyword arguments are forwarded to it unchanged.
"""

import plotly.graph_objects as _go

# Representative subset used only in error messages.
_COMMON_KINDS = [
    "area", "bar", "box", "density_contour", "density_heatmap",
    "ecdf", "funnel", "histogram", "line", "pie", "scatter",
    "scatter_3d", "scatter_matrix", "strip", "sunburst", "treemap", "violin",
]


def plot(kind: str, *args, **kwargs) -> _go.Figure:
    """Create a Plotly Express figure.

    Parameters
    ----------
    kind : str
        Name of the ``plotly.express`` function to call.
        ``'line'`` → ``px.line``, ``'bar'`` → ``px.bar``, etc.
    *args, **kwargs
        Forwarded directly to the ``plotly.express`` function.

    Returns
    -------
    plotly.graph_objects.Figure

    Examples
    --------
    >>> avr.plot('line', df, x='day', y='price', title='Price Trend')
    >>> avr.plot('bar', df, x='month', y='revenue', color='category')
    >>> avr.plot('scatter', df, x='customers', y='revenue', size='profit')
    >>> avr.plot('histogram', df, x='value', nbins=30)

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

    return func(*args, **kwargs)
