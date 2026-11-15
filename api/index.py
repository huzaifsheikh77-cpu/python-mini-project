"""Vercel serverless entry point for the Employee Payroll Management System.

Vercel's Python runtime imports this module and looks for a WSGI callable
named ``app``. The project root is added to ``sys.path`` so the application
packages (models, services, storage, analytics, templates, static) resolve
exactly as they do when running ``python app.py`` locally.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app  # noqa: E402  (import after sys.path setup)

# Exposed for the WSGI runtime.
application = app

__all__ = ["app", "application"]
