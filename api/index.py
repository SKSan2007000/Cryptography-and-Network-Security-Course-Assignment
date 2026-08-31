"""Vercel entry point for EHR CryptoGuard.
Vercel imports the top-level `app` ASGI instance from this module.
"""
from app.main import app

__all__ = ["app"]
