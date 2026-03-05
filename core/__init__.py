"""
Core execution engine for Otta CLI.

This module contains the main pipeline orchestration logic.
"""

from .pipeline import run_once

__all__ = ["run_once"]
