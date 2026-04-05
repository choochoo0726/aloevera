"""aloevera - Organize and display Plotly figures interactively."""

from aloevera.organizers import tabs, accordion, dropdown, slider
from aloevera.plots import plot
from aloevera.utils import to_widget
from aloevera.export import make_standalone
from aloevera.notebook import export_notebook

__version__ = "0.1.0"
__all__ = ["tabs", "accordion", "dropdown", "slider", "plot", "to_widget", "make_standalone", "export_notebook"]
