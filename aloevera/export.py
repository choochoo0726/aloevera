"""Generate standalone HTML for each organizer type.

Every organizer (tabs, accordion, dropdown, slider) has a corresponding
``*_html`` function that returns a self-contained HTML fragment.  The
fragment uses inline styles and minimal JS so it works when pasted into
Confluence's /html macro or similar embeds.

``make_standalone`` wraps a fragment in a full ``<!DOCTYPE html>`` page
with the Plotly CDN included, suitable for downloading as a ``.html`` file.
"""

import json as _json
import uuid as _uuid


# ---------------------------------------------------------------------------
# Shared Plotly init script
# ---------------------------------------------------------------------------

# Figures are stored as <script type="application/json"> (never executed by
# the browser, immune to Jupyter output sanitization).  This script finds
# every .avr-deferred-plot div, reads its paired JSON data, and calls
# Plotly.newPlot() explicitly — no MutationObserver dependency.
PLOTLY_INIT_JS = """\
<script>
(function () {
  function avrInitPlots() {
    if (!window.Plotly) { setTimeout(avrInitPlots, 50); return; }
    document.querySelectorAll('.avr-deferred-plot').forEach(function (el) {
      if (el._avrDone) return;
      var dataEl = document.getElementById('avr-data-' + el.id.replace('avr-plot-', ''));
      if (!dataEl) return;
      el._avrDone = true;
      try {
        var fig = JSON.parse(dataEl.textContent);
        Plotly.newPlot(el, fig.data, fig.layout || {}, {responsive: true});
      } catch (e) { console.warn('aloevera: failed to init plot', el.id, e); }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', avrInitPlots);
  } else {
    avrInitPlots();
  }
  window.avrInitPlots = avrInitPlots;
})();
</script>"""

# Copy / Download helpers for nested organiser toolbars rendered inside iframes.
# The standalone HTML for each nested organiser is stored in a
# <script type="application/json" class="avr-nested-data"> sibling element so
# that JS can read it without any sanitisation concerns.
_NESTED_EXPORT_JS = """\
<script>
window.avrNestedCopy = function (btn) {
  var wrap = btn.closest('.avr-nested-wrap');
  var html = JSON.parse(wrap.querySelector('.avr-nested-data').textContent);
  navigator.clipboard.writeText(html);
  btn.textContent = 'Copied!';
  setTimeout(function () { btn.textContent = 'Copy HTML'; }, 1500);
};
window.avrNestedDownload = function (btn) {
  var wrap = btn.closest('.avr-nested-wrap');
  var html = JSON.parse(wrap.querySelector('.avr-nested-data').textContent);
  var blob = new Blob([html], { type: 'text/html' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url; a.download = 'aloevera_export.html'; a.click();
  URL.revokeObjectURL(url);
};
</script>"""

# Sent from inside an iframe back to the notebook export page so the parent
# can resize the iframe to fit its content after Plotly finishes rendering.
_IFRAME_RESIZE_JS = """\
<script>
(function () {
  if (window.self === window.top) return; // not embedded as iframe, skip
  function notifyH() {
    var h = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
    try { window.parent.postMessage({avrH: h}, '*'); } catch (e) {}
  }
  // Fire once after DOM is ready and again after Plotly has had time to render
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(notifyH, 150);
      setTimeout(notifyH, 800);
    });
  } else {
    setTimeout(notifyH, 150);
    setTimeout(notifyH, 800);
  }
})();
</script>"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def make_standalone(fragment: str, title: str = "aloevera export") -> str:
    """Wrap an HTML fragment in a full standalone page.

    Includes the Plotly CDN and the aloevera deferred-plot init script.
    """
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
{PLOTLY_INIT_JS}
{_IFRAME_RESIZE_JS}
{_NESTED_EXPORT_JS}
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
    # Nested aloevera organizer — render the fragment and add Copy/Download buttons.
    # The standalone HTML is JSON-encoded into a <script type="application/json">
    # sibling so avrNestedCopy/Download (defined in _NESTED_EXPORT_JS) can read it.
    # </  is escaped as <\/ so the HTML parser never sees </script> inside the block.
    if hasattr(content, "_export_html"):
        fragment = content._export_html
        standalone = make_standalone(fragment)
        safe_json = _json.dumps(standalone).replace("</", "<\\/")
        toolbar = (
            '<div class="avr-nested-wrap">'
            '<div style="text-align:right;margin-bottom:4px;">'
            '<button onclick="avrNestedCopy(this)" '
            'style="padding:3px 10px;margin-left:4px;border:1px solid #ccc;'
            'border-radius:4px;background:#fff;cursor:pointer;font-size:12px;color:#444;">'
            'Copy HTML</button>'
            '<button onclick="avrNestedDownload(this)" '
            'style="padding:3px 10px;margin-left:4px;border:1px solid #ccc;'
            'border-radius:4px;background:#fff;cursor:pointer;font-size:12px;color:#444;">'
            'Download HTML</button>'
            '</div>'
            f'<script type="application/json" class="avr-nested-data">{safe_json}</script>'
            f'{fragment}'
            '</div>'
        )
        return toolbar

    # Plain HTML string
    if isinstance(content, str):
        return content

    # Plotly Figure / FigureWidget — deferred rendering via JSON data block.
    # Using <script type="application/json"> avoids MutationObserver issues and
    # is never stripped by Jupyter's output sanitizer (it's data, not code).
    if hasattr(content, "add_trace") and hasattr(content, "update_layout"):
        uid = _uid()
        height = getattr(getattr(content, "layout", None), "height", None) or 450
        return (
            f'<div class="avr-deferred-plot plotly-graph-div" id="avr-plot-{uid}" '
            f'style="width:100%;height:{height}px;"></div>'
            f'<script type="application/json" id="avr-data-{uid}">{content.to_json()}</script>'
        )

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
  /* Init any deferred Plotly charts that were hidden on page load */
  if (window.avrInitPlots) {{ avrInitPlots(); }}
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
  /* Init any deferred Plotly charts that were hidden on page load */
  if (!open && window.avrInitPlots) {{ avrInitPlots(); }}
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
  if (window.avrInitPlots) {{ avrInitPlots(); }}
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
  if (window.avrInitPlots) {{ avrInitPlots(); }}
}}
</script>"""
