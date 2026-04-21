"""Dressifye ve diğer dış entegrasyonlar.

Not: ``webhooks`` modülü paket ``__init__`` içinde içe aktarılmaz (context_manager ile döngü önlenir).
"""

from mehlr.integrations.dressifye_client import DressifyeClient

__all__ = ["DressifyeClient"]
