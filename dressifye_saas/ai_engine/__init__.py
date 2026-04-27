"""
Dressifye AI Engine — MEHLR entegrasyonu ve modüller.

Kalıcı AI / oturum verisi Django ORM'de tutulur (ör. apps.tryon.TryOnSession,
apps.styling.StyleSession, apps.wardrobe.Garment.ai_analysis); bu pakette
model yok. İşleyiciler ID ile çalışır; tenant izolasyonu ORM katmanında
(TenantScopedManager) sağlanır.
"""
