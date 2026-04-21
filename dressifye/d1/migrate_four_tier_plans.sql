-- Mevcut D1'de Elite yoksa ekler; platinum/diamond fiyat ve metinlerini yeni yapıya çeker.
-- wrangler d1 execute dressifye-db --remote --file=./d1/migrate_four_tier_plans.sql
-- Önce description_en kolonu yoksa: migrate_add_description_en.sql

INSERT INTO pricing_plans (name, price_usd, price_try, description, description_en, features, max_tryon, is_popular, tier_slug)
SELECT 'Elite', 249, NULL, 'Gelişmiş kullanıcılar ve küçük ekipler', 'Power users and lean teams.', '["Sınırsız deneme", "Gelişmiş AI", "Öncelikli destek"]', 999999, 1, 'elite'
WHERE NOT EXISTS (SELECT 1 FROM pricing_plans WHERE tier_slug = 'elite');

UPDATE pricing_plans SET
  price_usd = 899,
  name = 'Platinum',
  description = 'Büyüyen markalar için',
  description_en = 'Growing brands that need scale and API access.',
  features = '["Tüm Elite özellikleri", "API erişimi", "Öncelikli SLA"]',
  is_popular = 0
WHERE tier_slug = 'platinum';

UPDATE pricing_plans SET price_usd = 2500 WHERE tier_slug = 'diamond';
