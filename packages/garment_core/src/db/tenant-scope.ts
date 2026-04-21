import { eq, type SQL } from "drizzle-orm";
import type { PgColumn } from "drizzle-orm/pg-core";

/**
 * Kiracı izolasyonu: tüm okuma/yazma sorgularına `whereTenant(...)` ile
 * aynı `tenant_id` filtresi eklenmelidir. Drizzle şemasında her iş tablosunda `tenant_id` bulunur.
 */
export function whereTenant(column: PgColumn, tenantId: string): SQL {
  return eq(column, tenantId);
}
