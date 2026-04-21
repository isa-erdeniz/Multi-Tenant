-- Cloudflare D1 Console veya: wrangler d1 execute dressifye-db --file=./d1/pricing_plans.sql
-- tier_slug: /fiyatlandirma sayfasında "Satın al" → garment_core tier (starter, elite, platinum, diamond)

CREATE TABLE IF NOT EXISTS pricing_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_usd INTEGER NOT NULL,
    price_try INTEGER,
    description TEXT,
    description_en TEXT,
    features TEXT,
    max_tryon INTEGER,
    is_popular BOOLEAN DEFAULT 0,
    tier_slug TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO pricing_plans (name, price_usd, price_try, description, description_en, features, max_tryon, is_popular, tier_slug) VALUES
('Başlangıç', 49, NULL, 'Bireysel kullanım için ideal', 'Ideal for individuals getting started.', '["Aylık 20 deneme", "Temel raporlama", "E-posta desteği"]', 20, 0, 'starter'),
('Elite', 249, NULL, 'Gelişmiş kullanıcılar ve küçük ekipler', 'Power users and lean teams.', '["Sınırsız deneme", "Gelişmiş AI", "Öncelikli destek"]', 999999, 1, 'elite'),
('Platinum', 899, NULL, 'Büyüyen markalar için', 'Growing brands that need scale and API access.', '["Tüm Elite özellikleri", "API erişimi", "Öncelikli SLA"]', 999999, 0, 'platinum'),
('Kurumsal', 2500, NULL, 'Büyük ekipler için', 'Built for enterprise: custom integrations, API access, and infrastructure tailored to your brand—beyond standard plans.', '["Her şey dahil", "Özel entegrasyon", "7/24 destek", "Dedicated sunucu"]', 999999, 0, 'diamond');
