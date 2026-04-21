"""
Thread-local tenant ile ``templates/tenants/<slug>/`` öncelikli yükleme.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader

from apps.tenant.middleware import get_current_tenant


class TenantTemplateLoader(Loader):
    """Django, ``('Loader', [])`` biçiminde boş ``dirs`` ile çağırır; kabul et."""

    def __init__(self, engine, dirs=None) -> None:  # noqa: ARG002
        super().__init__(engine)

    def get_template_sources(self, template_name: str):
        tenant = get_current_tenant()
        if not tenant:
            return
        path = Path(settings.BASE_DIR) / "templates" / "tenants" / tenant.slug / template_name
        if path.is_file():
            yield Origin(name=str(path), template_name=template_name, loader=self)

    def get_contents(self, origin: Origin) -> str:
        try:
            with open(origin.name, encoding=self.engine.file_charset) as fp:
                return fp.read()
        except FileNotFoundError as e:
            raise TemplateDoesNotExist(origin) from e
