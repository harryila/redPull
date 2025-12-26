"""Output modules for Slack, Sheets, and Console."""

from .slack import send_to_slack
from .sheets import write_to_sheets
from .console import print_to_console

__all__ = ["send_to_slack", "write_to_sheets", "print_to_console"]

