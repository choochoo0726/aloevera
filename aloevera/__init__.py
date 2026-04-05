"""aloevera - Organize and display Plotly figures interactively."""

from .organizers import tabs, accordion, dropdown, slider
from .utils import to_widget
from .export import make_standalone

__version__ = "0.1.0"
__all__ = ["tabs", "accordion", "dropdown", "slider", "to_widget", "make_standalone"]
