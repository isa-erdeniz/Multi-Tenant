-- wrangler d1 execute dressifye-db --file=./d1/migrate_add_description_en.sql
ALTER TABLE pricing_plans ADD COLUMN description_en TEXT;

UPDATE pricing_plans SET description_en = 'Ideal for individuals getting started.' WHERE tier_slug = 'starter';
UPDATE pricing_plans SET description_en = 'Power users and lean teams.' WHERE tier_slug = 'elite';
UPDATE pricing_plans SET description_en = 'Growing brands that need scale and API access.' WHERE tier_slug = 'platinum';
UPDATE pricing_plans SET description_en = 'Built for enterprise: custom integrations, API access, and infrastructure tailored to your brand—beyond standard plans.' WHERE tier_slug = 'diamond';
