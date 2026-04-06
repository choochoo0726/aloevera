"""Thin wrappers around plotly.express for quick figure creation.

Instead of::

    import plotly.express as px
    fig = px.line(df, x='day', y='price', title='Trend')

use::

    fig = avr.plot(df, 'line', x='day', y='price', title='Trend')

Because ``data_frame`` is the first argument, you can also use Polars/pandas
``pipe``::

    df.pipe(avr.plot, 'line', x='day', y='price', title='Trend')

The ``kind`` argument is the name of any ``plotly.express`` function.
All keyword arguments are forwarded to it unchanged, and ``DEFAULT_LAYOUT``
is applied on top as a baseline style.
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
    'width': 900,
    'title_x': 0.5,                    # centre the title
    'margin_t': 40,                    # tighten gap between title and plot top
    # 'color_continuous_scale': 'Plotly',  # default colormap
    # 4-sided border: showline draws the axis line; mirror=True reflects it
    # onto the opposite side, completing the box around the plot area.
    'xaxis_showline': True,
    'xaxis_linewidth': 1,
    'xaxis_linecolor': '#888888',
    'xaxis_mirror': True,
    'yaxis_showline': True,
    'yaxis_linewidth': 1,
    'yaxis_linecolor': '#888888',
    'yaxis_mirror': True,
}

# Representative subset used only in error messages.
_COMMON_KINDS = [
    "area", "bar", "box", "density_contour", "density_heatmap",
    "ecdf", "funnel", "histogram", "line", "pie", "scatter",
    "scatter_3d", "scatter_matrix", "strip", "sunburst", "treemap", "violin",
]

# Keys injected directly into the px function call (not via update_layout).
_PX_LAYOUT_KEYS = frozenset({'template', 'height', 'width', 'color_continuous_scale'})

# Keys stripped on TypeError retry.  color_discrete_sequence is accepted by
# virtually all px functions so it stays in the retry; only
# color_continuous_scale is rejected by some (pie, sunburst, treemap, …).
_PX_OPTIONAL_KEYS = frozenset({'color_continuous_scale'})


def plot(data_frame, kind: str, **kwargs) -> _go.Figure:
    """Create a Plotly Express figure with aloevera's default styling.

    Parameters
    ----------
    data_frame : pl.DataFrame | pl.LazyFrame | pd.DataFrame | None
        Data source.  Polars DataFrames (including LazyFrames) are converted
        to pandas automatically.  Pass ``None`` for px functions that don't
        require a DataFrame.
    kind : str
        Name of the ``plotly.express`` function to call.
        ``'line'`` → ``px.line``, ``'bar'`` → ``px.bar``, etc.
        Can be passed positionally or as a keyword argument.
    **kwargs
        Forwarded directly to the ``plotly.express`` function.
        Any key that also appears in ``DEFAULT_LAYOUT`` overrides the default
        for this call only.

    Returns
    -------
    plotly.graph_objects.Figure

    Examples
    --------
    >>> avr.plot(df, 'line', x='day', y='price', title='Price Trend')
    >>> avr.plot(df, 'bar', x='month', y='revenue', color='category')
    >>> avr.plot(df, 'scatter', x='customers', y='revenue', size='profit')
    >>> avr.plot(df, 'histogram', x='value', nbins=30)

    Use with ``pipe`` to keep a Polars/pandas chain readable:

    >>> df.pipe(avr.plot, 'line', x='day', y='price', title='Trend')
    >>> (
    ...     df.filter(pl.col('region') == 'West')
    ...       .pipe(avr.plot, 'bar', x='month', y='revenue')
    ... )

    Override a default for one call:

    >>> avr.plot(df, 'line', x='day', y='price', height=600, template='ggplot2')

    Combine with organizers:

    >>> avr.tabs(
    ...     titles=['Line', 'Bar', 'Scatter'],
    ...     contents=[
    ...         avr.plot(df, 'line', x='day', y='price'),
    ...         avr.plot(df, 'bar', x='month', y='revenue'),
    ...         avr.plot(df, 'scatter', x='customers', y='revenue'),
    ...     ],
    ... )
    """
    # Auto-convert Polars DataFrame / LazyFrame to pandas
    try:
        import polars as _pl
        if isinstance(data_frame, _pl.LazyFrame):
            data_frame = data_frame.collect().to_pandas()
        elif isinstance(data_frame, _pl.DataFrame):
            data_frame = data_frame.to_pandas()
    except ImportError:
        pass

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

    # Inject px-level defaults before the call; caller kwargs take priority.
    px_defaults = {k: DEFAULT_LAYOUT[k] for k in _PX_LAYOUT_KEYS if k in DEFAULT_LAYOUT}
    merged_px = {**px_defaults, **kwargs}

    # Derive color_discrete_sequence from color_continuous_scale so that
    # categorical-color charts (bar, line, histogram …) also respect the
    # colormap setting.  Skip if the caller already supplied a discrete sequence.
    cscale = merged_px.get('color_continuous_scale')
    if cscale and 'color_discrete_sequence' not in merged_px:
        try:
            merged_px['color_discrete_sequence'] = px.colors.sample_colorscale(cscale, 10)
        except Exception:
            pass

    # Different px functions accept different subsets of color kwargs:
    #   histogram/bar/line: accept color_discrete_sequence, reject color_continuous_scale
    #   density_heatmap:    accept color_continuous_scale, reject color_discrete_sequence
    #   pie/sunburst:       reject both
    # Try all combinations until one succeeds.
    try:
        fig = func(data_frame, **merged_px)
    except TypeError:
        without_cscale = {k: v for k, v in merged_px.items() if k != 'color_continuous_scale'}
        try:
            fig = func(data_frame, **without_cscale)           # histogram, bar, line …
        except TypeError:
            without_disc = {k: v for k, v in merged_px.items() if k != 'color_discrete_sequence'}
            try:
                fig = func(data_frame, **without_disc)         # density_heatmap …
            except TypeError:
                without_both = {k: v for k, v in merged_px.items()
                                if k not in {'color_continuous_scale', 'color_discrete_sequence'}}
                fig = func(data_frame, **without_both)         # pie, sunburst …

    # Apply remaining DEFAULT_LAYOUT keys (e.g. title_x) via update_layout,
    # skipping any that the caller already supplied.
    post_updates = {
        k: v for k, v in DEFAULT_LAYOUT.items()
        if k not in _PX_LAYOUT_KEYS and k not in kwargs
    }
    if post_updates:
        fig.update_layout(**post_updates)

    return fig
