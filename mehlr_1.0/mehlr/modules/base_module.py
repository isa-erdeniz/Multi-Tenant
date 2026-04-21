"""
Tüm MEHLR modüllerinin miras aldığı temel sınıf.
"""
from abc import ABC


class BaseMEHLRModule(ABC):
    """Tüm MEHLR modüllerinin temel sınıfı."""
    module_name: str = ""
    version: str = "1.0"
    description: str = ""
    supported_projects: list = []

    def initialize(self):
        """Modül başlatma — override edilebilir."""
        pass

    def analyze(self, data: dict, project: str) -> dict:
        """Ana analiz fonksiyonu — override edilmeli."""
        raise NotImplementedError

    def recommend(self, analysis_result: dict) -> list:
        """Analiz sonucuna göre öneri üret — override edilebilir."""
        return []

    def report(self, analysis_result: dict, format: str = "markdown") -> str:
        """Rapor üret — override edilebilir."""
        return ""

    def is_supported(self, project_slug: str) -> bool:
        """Bu modül belirtilen projeyi destekliyor mu?"""
        return project_slug in self.supported_projects or not self.supported_projects
