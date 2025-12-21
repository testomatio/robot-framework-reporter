"""Alias to support Testomatio.*Listener* syntax"""

from reporter.listener import ReportListener as Report
from reporter.listener import ImportListener as Import

__all__ = ["Report", "Import"]
