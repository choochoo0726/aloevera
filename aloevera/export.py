"""Generate standalone HTML for each organizer type.

Every organizer (tabs, accordion, dropdown, slider) has a corresponding
``*_html`` function that returns a self-contained HTML fragment.  The
fragment uses inline styles and minimal JS so it works when pasted into
Confluence's /html macro or similar embeds.

``make_standalone`` wraps a fragment in a full ``<!DOCTYPE html>`` page
with the Plotly CDN included, suitable for downloading as a ``.html`` file.
"""

import uuid as _uuid


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def make_standalone(fragment: str, title: str = "aloevera export") -> str:
    """Wrap an HTML fragment in a full standalone page.

    Includes the Plotly CDN so any embedded Plotly charts render correctly.
    """
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; }}
</style>
</head>
<body>
{fragment}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Content → HTML
# ---------------------------------------------------------------------------

def content_to_html(content) -> str:
    """Convert a single content item to an HTML string.

    Handles:
    * ``str`` – used verbatim (assumed to be HTML already).
    * ``plotly.graph_objects.Figure / FigureWidget`` – rendered via
      ``to_html(include_plotlyjs=False)``.
    * ``pandas.DataFrame`` – converted with ``to_html()``.
    * Any ipywidget that carries ``_export_html`` (i.e. a nested
      aloevera organizer) – uses that attribute.
    """
    # Nested aloevera organizer
    if hasattr(content, "_export_html"):
        return content._export_html

    # Plain HTML string
    if isinstance(content, str):
        return content

    # Plotly Figure / FigureWidget
    try:
        import plotly.graph_objects as go

        if isinstance(content, (go.Figure, go.FigureWidget)):
            return content.to_html(include_plotlyjs=False, full_html=False)
    except ImportError:
        pass

    # pandas DataFrame
    try:
        import pandas as pd

        if isinstance(content, pd.DataFrame):
            return content.to_html()
    except ImportError:
        pass

    # Fallback
    return f"<div>{str(content)}</div>"


# ---------------------------------------------------------------------------
# Organizer HTML generators
# ---------------------------------------------------------------------------

def _uid() -> str:
    return _uuid.uuid4().hex[:8]


def tabs_html(titles: list, contents_html: list) -> str:
    """Generate an HTML tabs component."""
    uid = _uid()
    buttons = []
    panels = []
    for i, (title, html) in enumerate(zip(titles, contents_html)):
        active_btn = ' avr-tab-active' if i == 0 else ''
        active_panel = 'display:block' if i == 0 else 'display:none'
        buttons.append(
            f'<button class="avr-tab-btn{active_btn}" '
            f'onclick="avrTab_{uid}({i})">{title}</button>'
        )
        panels.append(
            f'<div class="avr-tab-panel" id="avr-panel-{uid}-{i}" '
            f'style="{active_panel}">{html}</div>'
        )

    return f"""\
<div class="avr-tabs" id="avr-tabs-{uid}">
<style>
  #avr-tabs-{uid} .avr-tab-bar {{ display:flex; gap:0; border-bottom:2px solid #e0e0e0; margin-bottom:8px; }}
  #avr-tabs-{uid} .avr-tab-btn {{ padding:8px 18px; border:none; background:none; cursor:pointer; font-size:14px; color:#555; border-bottom:2px solid transparent; margin-bottom:-2px; }}
  #avr-tabs-{uid} .avr-tab-btn.avr-tab-active {{ color:#1a73e8; border-bottom-color:#1a73e8; font-weight:600; }}
  #avr-tabs-{uid} .avr-tab-btn:hover {{ background:#f5f5f5; }}
  #avr-tabs-{uid} .avr-tab-panel {{ padding:8px 0; }}
</style>
<div class="avr-tab-bar">{''.join(buttons)}</div>
{''.join(panels)}
</div>
<script>
function avrTab_{uid}(idx) {{
  var tabs = document.getElementById('avr-tabs-{uid}');
  tabs.querySelectorAll('.avr-tab-btn').forEach(function(b,i) {{
    b.classList.toggle('avr-tab-active', i===idx);
  }});
  tabs.querySelectorAll('.avr-tab-panel').forEach(function(p,i) {{
    p.style.display = i===idx ? 'block' : 'none';
  }});
  /* Plotly charts may need a resize after becoming visible */
  var visible = document.getElementById('avr-panel-{uid}-'+idx);
  if (visible && window.Plotly) {{
    visible.querySelectorAll('.plotly-graph-div').forEach(function(d) {{
      Plotly.Plots.resize(d);
    }});
  }}
}}
</script>"""


def accordion_html(titles: list, contents_html: list) -> str:
    """Generate an HTML accordion component."""
    uid = _uid()
    items = []
    for i, (title, html) in enumerate(zip(titles, contents_html)):
        items.append(f"""\
<div class="avr-acc-item">
  <button class="avr-acc-hdr" onclick="avrAcc_{uid}({i})">
    <span class="avr-acc-arrow" id="avr-arrow-{uid}-{i}">&#9654;</span> {title}
  </button>
  <div class="avr-acc-body" id="avr-accbody-{uid}-{i}" style="display:none">{html}</div>
</div>""")

    return f"""\
<div class="avr-accordion" id="avr-acc-{uid}">
<style>
  #avr-acc-{uid} .avr-acc-item {{ border:1px solid #e0e0e0; border-radius:4px; margin-bottom:4px; }}
  #avr-acc-{uid} .avr-acc-hdr {{ width:100%; padding:10px 14px; border:none; background:#fafafa; cursor:pointer; font-size:14px; text-align:left; }}
  #avr-acc-{uid} .avr-acc-hdr:hover {{ background:#f0f0f0; }}
  #avr-acc-{uid} .avr-acc-arrow {{ display:inline-block; transition:transform .2s; font-size:10px; margin-right:6px; }}
  #avr-acc-{uid} .avr-acc-arrow.avr-open {{ transform:rotate(90deg); }}
  #avr-acc-{uid} .avr-acc-body {{ padding:8px 14px; }}
</style>
{''.join(items)}
</div>
<script>
function avrAcc_{uid}(idx) {{
  var body = document.getElementById('avr-accbody-{uid}-'+idx);
  var arrow = document.getElementById('avr-arrow-{uid}-'+idx);
  var open = body.style.display !== 'none';
  body.style.display = open ? 'none' : 'block';
  arrow.classList.toggle('avr-open', !open);
  /* Resize Plotly charts when section opens */
  if (!open && window.Plotly) {{
    body.querySelectorAll('.plotly-graph-div').forEach(function(d) {{
      Plotly.Plots.resize(d);
    }});
  }}
}}
</script>"""


def dropdown_html(titles: list, contents_html: list) -> str:
    """Generate an HTML dropdown selector component."""
    uid = _uid()
    options = []
    panels = []
    for i, (title, html) in enumerate(zip(titles, contents_html)):
        options.append(f'<option value="{i}">{title}</option>')
        display = 'block' if i == 0 else 'none'
        panels.append(
            f'<div class="avr-dd-panel" id="avr-dd-{uid}-{i}" '
            f'style="display:{display}">{html}</div>'
        )

    return f"""\
<div class="avr-dropdown" id="avr-dropdown-{uid}">
<style>
  #avr-dropdown-{uid} select {{ padding:6px 12px; font-size:14px; border:1px solid #ccc; border-radius:4px; margin-bottom:8px; }}
</style>
<select onchange="avrDD_{uid}(this.value)">{''.join(options)}</select>
{''.join(panels)}
</div>
<script>
function avrDD_{uid}(idx) {{
  var container = document.getElementById('avr-dropdown-{uid}');
  container.querySelectorAll('.avr-dd-panel').forEach(function(p,i) {{
    p.style.display = i===parseInt(idx) ? 'block' : 'none';
  }});
  var visible = document.getElementById('avr-dd-{uid}-'+idx);
  if (visible && window.Plotly) {{
    visible.querySelectorAll('.plotly-graph-div').forEach(function(d) {{
      Plotly.Plots.resize(d);
    }});
  }}
}}
</script>"""


def slider_html(titles: list, contents_html: list) -> str:
    """Generate an HTML slider-navigator component."""
    uid = _uid()
    panels = []
    for i, html in enumerate(contents_html):
        display = 'block' if i == 0 else 'none'
        panels.append(
            f'<div class="avr-sl-panel" id="avr-sl-{uid}-{i}" '
            f'style="display:{display}">{html}</div>'
        )

    return f"""\
<div class="avr-slider" id="avr-slider-{uid}">
<style>
  #avr-slider-{uid} .avr-sl-label {{ font-size:13px; color:#555; margin-bottom:6px; font-weight:600; }}
  #avr-slider-{uid} input[type=range] {{ width:100%; cursor:pointer; }}
</style>
<input type="range" min="0" max="{len(titles)-1}" value="0" step="1"
  oninput="avrSl_{uid}(this.value)">
<div class="avr-sl-label" id="avr-sl-label-{uid}">{titles[0] if titles else ""}</div>
{''.join(panels)}
</div>
<script>
function avrSl_{uid}(val) {{
  var idx = parseInt(val);
  var titles = {titles!r};
  document.getElementById('avr-sl-label-{uid}').textContent = titles[idx];
  var container = document.getElementById('avr-slider-{uid}');
  container.querySelectorAll('.avr-sl-panel').forEach(function(p,i) {{
    p.style.display = i===idx ? 'block' : 'none';
  }});
  var visible = document.getElementById('avr-sl-{uid}-'+idx);
  if (visible && window.Plotly) {{
    visible.querySelectorAll('.plotly-graph-div').forEach(function(d) {{
      Plotly.Plots.resize(d);
    }});
  }}
}}
</script>"""
