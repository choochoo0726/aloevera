# aloevera

**aloevera** is a Python library for organizing and displaying Plotly figures interactively in Jupyter notebooks, with one-command HTML export for sharing outside Jupyter (e.g. Confluence, static sites).

---

## Installation

```bash
uv add aloevera
# or from source
git clone https://github.com/choochoo0726/aloevera
cd aloevera && uv sync
```

---

## Quick start

```python
import aloevera as avr
import polars as pl

df = pl.read_csv("sales.csv")

# Create figures
fig_line = avr.plot('line', df.to_pandas(), x='month', y='revenue', title='Revenue')
fig_bar  = avr.plot('bar',  df.to_pandas(), x='month', y='expenses', title='Expenses')

# Organize into tabs
avr.tabs(
    titles=['Revenue', 'Expenses'],
    contents=[fig_line, fig_bar],
)
```

---

## API reference

### Plotting — `avr.plot()`

A thin wrapper around `plotly.express` that applies a consistent default layout.

```python
avr.plot(kind, *args, **kwargs) -> go.Figure
```

| Parameter | Description |
|-----------|-------------|
| `kind` | Name of any `plotly.express` function: `'line'`, `'bar'`, `'scatter'`, `'histogram'`, `'box'`, `'violin'`, `'area'`, `'pie'`, `'density_heatmap'`, `'strip'`, … |
| `*args / **kwargs` | Forwarded directly to the `px` function |

**Default layout** (`avr.DEFAULT_LAYOUT`):

| Key | Default |
|-----|---------|
| `template` | `'plotly_white'` |
| `height` | `400` |
| `width` | `700` |
| `title_x` | `0.5` (centred) |

Override per-call or globally:

```python
# Per-call override
avr.plot('bar', df, x='x', y='y', height=600, template='ggplot2')

# Global override
avr.DEFAULT_LAYOUT['height'] = 500
```

---

### Organizers

All organizers accept a list of titles and a list of contents. Contents can be Plotly figures, DataFrames, HTML strings, or nested organizers.

Each organizer returns an ipywidget with **Copy** and **Download** buttons for exporting the widget as a standalone HTML file.

#### `avr.tabs()`

Horizontal tab strip — click a tab header to switch content.

```python
avr.tabs(titles=['A', 'B'], contents=[fig1, fig2])
```

#### `avr.accordion()`

Collapsible sections — click a header to expand/collapse.

```python
avr.accordion(titles=['Overview', 'Detail'], contents=[fig1, fig2])
```

#### `avr.dropdown()`

Dropdown selector above the content area.

```python
avr.dropdown(titles=['Option A', 'Option B'], contents=[fig1, fig2])
```

#### `avr.slider()`

Horizontal slider above the content area — drag to navigate between items.

```python
avr.slider(titles=['Jan', 'Feb', 'Mar'], contents=[fig1, fig2, fig3])
```

**Nesting** — organizers can be placed inside other organizers:

```python
inner = avr.accordion(titles=['Bar', 'Line'], contents=[fig1, fig2])
avr.tabs(titles=['Charts', 'Scatter'], contents=[inner, fig3])
```

---

### HTML export

#### Copy / Download buttons (in-notebook)

Every organizer widget has **Copy HTML** and **Download HTML** buttons on the right. Copy puts the HTML fragment on the clipboard (paste into Confluence's `/html` macro); Download saves a self-contained `.html` file.

#### `avr.make_standalone()`

Wrap an HTML fragment in a full `<!DOCTYPE html>` page with the Plotly CDN included.

```python
html = avr.make_standalone(widget._export_html, title='My Dashboard')
with open('dashboard.html', 'w') as f:
    f.write(html)
```

#### `avr.export_notebook()`

Convert a `.ipynb` notebook to a standalone HTML file with:
- A **fixed left sidebar** containing a table of contents and a code-toggle button
- All aloevera organizers rendered as interactive iframes
- Widget state stripped to keep the file small

```python
avr.export_notebook('demo/demo_organizers.ipynb')
avr.export_notebook('demo/demo_organizers.ipynb', output_path='out/dashboard.html')
```

#### CLI

```bash
aloevera export-html demo/demo_organizers.ipynb
aloevera export-html demo/demo_organizers.ipynb -o out/dashboard.html
```

---

## Demo notebooks

| Notebook | Description |
|----------|-------------|
| `demo/demo_plots.ipynb` | `avr.plot()` examples: line, bar, scatter, histogram, box, violin, area, pie, heatmap, strip |
| `demo/demo_organizers.ipynb` | Organizer examples: tabs, accordion, dropdown, slider, nesting, and notebook export |

---

## Project structure

```
aloevera/
├── aloevera/
│   ├── plots.py        # avr.plot() — plotly.express wrapper
│   ├── organizers.py   # tabs, accordion, dropdown, slider
│   ├── utils.py        # to_widget(), wrap_with_buttons()
│   ├── export.py       # HTML generation, make_standalone()
│   ├── notebook.py     # export_notebook(), sidebar injection
│   ├── cli.py          # aloevera export-html CLI entry point
│   └── __init__.py
├── demo/
│   ├── demo_plots.ipynb
│   └── demo_organizers.ipynb
└── pyproject.toml
```
