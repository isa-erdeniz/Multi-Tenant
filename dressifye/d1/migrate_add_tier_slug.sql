-- Tabloyu önceki şema ile oluşturduysan (tier_slug yoksa) bir kez çalıştır:
-- wrangler d1 execute dressifye-db --file=./d1/migrate_add_tier_slug.sql

ALTER TABLE pricing_plans ADD COLUMN tier_slug TEXT;

UPDATE pricing_plans SET tier_slug = 'starter' WHERE name = 'Başlangıç' AND (tier_slug IS NULL OR tier_slug = '');
UPDATE pricing_plans SET tier_slug = 'platinum' WHERE name = 'Profesyonel' AND (tier_slug IS NULL OR tier_slug = '');
UPDATE pricing_plans SET tier_slug = 'diamond' WHERE name = 'Kurumsal' AND (tier_slug IS NULL OR tier_slug = '');
