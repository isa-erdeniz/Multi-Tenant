"""
FAZ 2/14: Vücut Analiz & Beden Tahmini.
MEHLR veya hesaplama tabanlı beden önerisi.
"""
from typing import Optional


def estimate_size_from_measurements(
    bust: int,
    waist: int,
    hips: int,
    system: str = "tr",
) -> Optional[str]:
    """
    Ölçülerden beden tahmini (basit hesaplama).
    TR/EU/US/UK karşılıkları.
    """
    if not all([bust, waist, hips]):
        return None
    avg = (bust + waist + hips) / 3
    if system == "tr":
        if avg < 80:
            return "XS"
        if avg < 85:
            return "S"
        if avg < 90:
            return "M"
        if avg < 95:
            return "L"
        if avg < 100:
            return "XL"
        return "XXL"
    if system == "eu":
        if avg < 80:
            return "32"
        if avg < 85:
            return "34"
        if avg < 90:
            return "36"
        if avg < 95:
            return "38"
        if avg < 100:
            return "40"
        return "42"
    return "M"  # fallback
