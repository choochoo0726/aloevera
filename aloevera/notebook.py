"""Export Jupyter notebooks to HTML with a sidebar.

The sidebar provides:
- A button to show / hide all code cells
- A table of contents built from Markdown headings

Each aloevera organizer stores its HTML fragment as base64 in a hidden
``avr-nb-export`` marker div.  ``_inject_sidebar`` decodes those markers and
replaces them with self-contained ``<iframe srcdoc>`` elements — the same
isolated rendering environment used by the Download button, so Plotly works
without any MutationObserver or CDN-timing workarounds.

Size optimisations applied during export:
* The ``application/vnd.jupyter.widget-state+json`` blob that nbconvert
  embeds is stripped — it duplicates all FigureWidget data and can be tens
  of megabytes.  The iframes are self-contained, so the blob is redundant.
* Nested organiser markers (e.g. an ``avr.accordion`` whose HTML is already
  embedded inside an outer ``avr.tabs``) are removed rather than converted to
  a second iframe, avoiding duplicate figure JSON in the page.
"""

import base64
import html as _html_lib
import json as _json
import re
import struct
import subprocess
import sys
import uuid as _uuid
from pathlib import Path

from aloevera.export import make_standalone


# Map Plotly's compact dtype strings to (struct_char, item_size_bytes).
# Plotly stores numeric arrays as base64-encoded little-endian binary blobs
# when rendering in Jupyter.  Plotly.js can decode these natively, but only
# when the figure is loaded via its own MIME renderer — not when the data is
# passed to Plotly.newPlot() as a plain JS object.  We therefore decode bdata
# back to ordinary Python lists so the serialised JSON uses plain arrays.
_BDATA_DTYPE_MAP = {
    'f4': ('f', 4), 'f8': ('d', 8),
    'i1': ('b', 1), 'i2': ('h', 2), 'i4': ('i', 4), 'i8': ('q', 8),
    'u1': ('B', 1), 'u2': ('H', 2), 'u4': ('I', 4), 'u8': ('Q', 8),
}


def _decode_bdata(obj):
    """Recursively decode ``{bdata, dtype}`` typed-array objects to plain lists."""
    if isinstance(obj, dict):
        if 'bdata' in obj and 'dtype' in obj:
            dtype = obj['dtype']
            if dtype in _BDATA_DTYPE_MAP:
                fmt_char, item_size = _BDATA_DTYPE_MAP[dtype]
                raw = base64.b64decode(obj['bdata'])
                n = len(raw) // item_size
                return list(struct.unpack_from(f'<{n}{fmt_char}', raw))
        return {k: _decode_bdata(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode_bdata(item) for item in obj]
    return obj


def _preprocess_notebook(nb_path: Path) -> tuple:
    """Rewrite Plotly JSON outputs as avr-nb-export markers so nbconvert
    passes them through as HTML instead of falling back to static PNG.

    Returns ``(path_to_use, tmp_path_or_None)``.  The caller must delete
    ``tmp_path_or_None`` when done (even on error).
    """
    with open(nb_path, encoding="utf-8") as f:
        nb = _json.load(f)

    modified = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        new_outputs = []
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            plotly_data = data.get("application/vnd.plotly.v1+json")
            if plotly_data is None:
                new_outputs.append(output)
                continue
            # Decode compact bdata typed arrays so Plotly.js can handle the
            # data when passed via Plotly.newPlot() in the iframe context.
            plotly_data = _decode_bdata(plotly_data)
            # Build a deferred-plot fragment identical to what content_to_html()
            # produces for go.Figure objects, so PLOTLY_INIT_JS handles it.
            uid = _uuid.uuid4().hex[:8]
            height = (plotly_data.get("layout") or {}).get("height") or 450
            fig_json = _json.dumps(plotly_data)
            fragment = (
                f'<div class="avr-deferred-plot plotly-graph-div" '
                f'id="avr-plot-{uid}" style="width:100%;height:{height}px;"></div>'
                f'<script type="application/json" id="avr-data-{uid}">{fig_json}</script>'
            )
            b64 = base64.b64encode(fragment.encode()).decode()
            marker_html = (
                f'<div class="avr-nb-export" data-avr-b64="{b64}" '
                f'style="display:none"></div>'
            )
            new_outputs.append({
                "output_type": "display_data",
                "data": {"text/html": marker_html},
                "metadata": {},
            })
            modified = True
        cell["outputs"] = new_outputs

    if not modified:
        return nb_path, None

    tmp_path = nb_path.parent / (nb_path.stem + ".__avr_tmp__.ipynb")
    with open(tmp_path, "w", encoding="utf-8") as f:
        _json.dump(nb, f)
    return tmp_path, tmp_path


def export_notebook(notebook_path: str, output_path: str = None) -> str:
    """Convert a Jupyter notebook to a standalone HTML file with a sidebar.

    Parameters
    ----------
    notebook_path : str
        Path to the ``.ipynb`` file.
    output_path : str, optional
        Destination ``.html`` path.  Defaults to same directory as the
        notebook with a ``.html`` extension.

    Returns
    -------
    str
        Absolute path to the generated HTML file.

    Example
    -------
    >>> import aloevera as avr
    >>> avr.export_notebook("demo/demo.ipynb")
    """
    nb_path = Path(notebook_path).resolve()
    out_path = Path(output_path).resolve() if output_path else nb_path.with_suffix(".html")

    convert_path, tmp_path = _preprocess_notebook(nb_path)
    try:
        subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert",
             "--to", "html", "--output", str(out_path), str(convert_path)],
            check=True,
        )
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()

    html = out_path.read_text(encoding="utf-8")
    html = _inject_sidebar(html)
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# Sidebar CSS / HTML / JS
# ---------------------------------------------------------------------------

_CSS = """\
<style>
#avr-sidebar {
  position: fixed; top: 0; left: 0;
  width: 240px; height: 100vh;
  background: #f8f9fa; border-right: 1px solid #e0e0e0;
  display: flex; flex-direction: column;
  padding: 14px 12px; box-sizing: border-box;
  overflow-y: auto; z-index: 1000;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 13px;
}
#avr-sidebar h3 {
  margin: 0 0 6px 0; font-size: 11px;
  text-transform: uppercase; letter-spacing: .07em; color: #999;
}
#avr-code-toggle {
  width: 100%; padding: 7px 10px; margin-bottom: 14px;
  border: 1px solid #ccc; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 13px; text-align: left;
}
#avr-code-toggle:hover { background: #f0f0f0; }
#avr-toc-list { list-style: none; padding: 0; margin: 0; }
#avr-toc-list li { margin: 1px 0; }
#avr-toc-list a {
  text-decoration: none; color: #333;
  display: block; padding: 3px 6px; border-radius: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#avr-toc-list a:hover { background: #e8eaed; color: #1a73e8; }
#avr-toc-list .avr-h2 { padding-left: 14px; font-size: 12px; }
#avr-toc-list .avr-h3 { padding-left: 26px; font-size: 11px; color: #666; }
body { margin-left: 256px !important; }
h1, h2, h3 { scroll-margin-top: 12px; }
/* aloevera export container */
.avr-export-wrap { margin: 4px 0; }
.avr-export-bar { text-align: right; margin-bottom: 4px; }
.avr-export-bar button {
  padding: 3px 10px; margin-left: 4px;
  border: 1px solid #ccc; border-radius: 4px;
  background: #fff; cursor: pointer; font-size: 12px; color: #444;
}
.avr-export-bar button:hover { background: #f0f0f0; }
/* aloevera iframes */
.avr-widget-frame { width: 100%; border: none; display: block; min-height: 200px; }
/* In cells that have an avr iframe, hide all other output entries.
   nbconvert may embed widget state so ipywidgets render alongside the iframe;
   the iframe is the authoritative interactive copy. */
.avr-cell-has-iframe .jp-OutputArea-output:not(.avr-iframe-output),
.avr-cell-has-iframe .output:not(.avr-iframe-output) { display: none !important; }
</style>
"""

_SIDEBAR_HTML = """\
<div id="avr-sidebar">
  <button id="avr-code-toggle" onclick="avrToggleCode()">Hide Code</button>
  <h3>Contents</h3>
  <ul id="avr-toc-list"></ul>
</div>
"""

_JS = """\
<script>
(function () {
  // ----- Table of contents -----
  var headings = document.querySelectorAll([
    '.jp-MarkdownOutput h1', '.jp-MarkdownOutput h2', '.jp-MarkdownOutput h3',
    '.jp-RenderedMarkdown h1', '.jp-RenderedMarkdown h2', '.jp-RenderedMarkdown h3',
    '.text_cell_render h1', '.text_cell_render h2', '.text_cell_render h3'
  ].join(','));

  var toc = document.getElementById('avr-toc-list');
  var counter = 0;
  headings.forEach(function (h) {
    if (!h.id) { h.id = 'avr-h-' + (counter++); }
    var targetId = h.id;
    var level = h.tagName[1];
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = '#' + targetId;
    a.textContent = h.textContent.trim();
    if (level === '2') a.className = 'avr-h2';
    if (level === '3') a.className = 'avr-h3';
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var target = document.getElementById(targetId);
      if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
    li.appendChild(a);
    toc.appendChild(li);
  });

  // ----- Code cell toggle -----
  // Scope selectors to code cells only — markdown cells in JupyterLab's
  // nbconvert template put their rendered content inside .jp-Cell-inputWrapper
  // too, so a broad selector would hide headings and prose.
  var codeShown = true;
  window.avrToggleCode = function () {
    codeShown = !codeShown;
    [
      '.jp-CodeCell .jp-Cell-inputWrapper',   // JupyterLab nbconvert template
      '.code_cell .input',                     // Classic notebook template
    ].forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.style.display = codeShown ? '' : 'none';
      });
    });
    document.getElementById('avr-code-toggle').textContent =
      codeShown ? 'Hide Code' : 'Show Code';
  };

  // ----- Hide duplicate widget renders beside avr iframes -----
  // nbconvert embeds widget state so ipywidgets may render alongside the
  // iframe.  Mark the cell and iframe's output entry so CSS hides the rest.
  document.querySelectorAll('.avr-widget-frame').forEach(function (f) {
    var iframeOut = f.closest('.jp-OutputArea-output') || f.closest('.output');
    if (iframeOut) { iframeOut.classList.add('avr-iframe-output'); }
    var cell = f.closest('.jp-Cell') || f.closest('.cell');
    if (cell) { cell.classList.add('avr-cell-has-iframe'); }
  });

  // ----- Resize iframes via postMessage -----
  // make_standalone() sends {avrH: scrollHeight} after Plotly renders.
  window.addEventListener('message', function (e) {
    if (!e.data || typeof e.data.avrH !== 'number') return;
    document.querySelectorAll('.avr-widget-frame').forEach(function (f) {
      try {
        if (f.contentWindow === e.source) {
          f.style.height = (e.data.avrH + 20) + 'px';
        }
      } catch (ex) {}
    });
  });

  // ----- Copy / Download buttons -----
  window.avrExportCopy = function (btn) {
    var f = btn.closest('.avr-export-wrap').querySelector('.avr-widget-frame');
    if (!f) return;
    navigator.clipboard.writeText(f.srcdoc);
    btn.textContent = 'Copied!';
    setTimeout(function () { btn.textContent = 'Copy HTML'; }, 1500);
  };

  window.avrExportDownload = function (btn) {
    var f = btn.closest('.avr-export-wrap').querySelector('.avr-widget-frame');
    if (!f) return;
    var blob = new Blob([f.srcdoc], { type: 'text/html' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'aloevera_export.html'; a.click();
    URL.revokeObjectURL(url);
  };
})();
</script>
"""


# ---------------------------------------------------------------------------
# Inject helpers
# ---------------------------------------------------------------------------

def _strip_widget_state(html: str) -> str:
    """Remove the widget-state JSON blob that nbconvert embeds.

    This single script tag can be tens of megabytes because it serialises every
    FigureWidget's full data.  The avr iframes are self-contained, so the blob
    is entirely redundant in the exported HTML.
    """
    return re.sub(
        r'<script\s+type="application/vnd\.jupyter\.widget-state\+json"[^>]*>.*?</script>',
        '',
        html,
        flags=re.DOTALL,
    )


def _replace_export_markers(html: str) -> str:
    """Replace avr-nb-export marker divs with iframe widgets + copy/download toolbar.

    Nested-organiser deduplication
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    When an inner organiser (e.g. ``avr.accordion``) is used as content inside
    an outer one (e.g. ``avr.tabs``), the outer's HTML fragment already contains
    the inner's HTML verbatim.  Both emit a marker, but converting both to
    iframes would show the inner content twice.  We detect this by checking
    whether one decoded fragment is a substring of another, and suppress the
    nested (inner) markers.
    """
    _PATTERN = (
        r'<div\s+class="avr-nb-export"\s+data-avr-b64="([^"]+)"\s+style="display:none">'
        r'\s*</div>'
    )

    matches = list(re.finditer(_PATTERN, html))
    if not matches:
        return html

    # Decode every unique b64 token exactly once.
    fragments: dict[str, str | None] = {}
    for m in matches:
        b64 = m.group(1)
        if b64 not in fragments:
            try:
                fragments[b64] = base64.b64decode(b64.encode()).decode("utf-8")
            except Exception:
                fragments[b64] = None

    # A fragment is "nested" if its text appears verbatim inside another fragment.
    valid = [(b64, frag) for b64, frag in fragments.items() if frag is not None]
    nested_b64s: set[str] = set()
    for i, (b64_i, frag_i) in enumerate(valid):
        for j, (b64_j, frag_j) in enumerate(valid):
            if i != j and frag_i in frag_j:
                nested_b64s.add(b64_i)
                break

    def _make_iframe(m: re.Match) -> str:
        b64 = m.group(1)
        if b64 in nested_b64s:
            return ''  # inner organiser already embedded inside outer's iframe
        fragment = fragments.get(b64)
        if not fragment:
            return m.group(0)
        standalone = make_standalone(fragment)
        escaped = _html_lib.escape(standalone, quote=True)
        return (
            '<div class="avr-export-wrap">'
            '<div class="avr-export-bar">'
            '<button onclick="avrExportCopy(this)">Copy HTML</button>'
            '<button onclick="avrExportDownload(this)">Download HTML</button>'
            '</div>'
            f'<iframe class="avr-widget-frame" srcdoc="{escaped}"></iframe>'
            '</div>'
        )

    return re.sub(_PATTERN, _make_iframe, html)


def _inject_sidebar(html: str) -> str:
    # 1. Strip the large widget-state blob before any other processing.
    html = _strip_widget_state(html)
    # 2. Replace widget markers with iframes (nested markers are suppressed).
    html = _replace_export_markers(html)
    # 3. Inject CSS, sidebar HTML, and JS.
    html = html.replace("</head>", _CSS + "</head>", 1)
    html = re.sub(r"(<body[^>]*>)", r"\1\n" + _SIDEBAR_HTML.replace("\\", "\\\\"), html, count=1)
    html = html.replace("</body>", _JS + "</body>", 1)
    return html
