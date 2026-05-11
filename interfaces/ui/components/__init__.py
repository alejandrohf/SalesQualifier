"""Módulo `interfaces/ui/components/__init__.py` de la plataforma Sales Qualification Agent."""

from .layout import page_header as page_header
from .layout import set_page_config as set_page_config
from .layout import sidebar_header as sidebar_header
from .render import json_expander as json_expander
from .render import kpi_row as kpi_row
from .render import show_api_error as show_api_error
from .render import show_envelope_result as show_envelope_result

__all__ = [
    "json_expander",
    "kpi_row",
    "page_header",
    "set_page_config",
    "show_api_error",
    "show_envelope_result",
    "sidebar_header",
]
