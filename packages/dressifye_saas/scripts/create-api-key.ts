/**
 * Mevcut platform_client + kiracılar için yeni API anahtarı üretir.
 * Ortam: DATABASE_URL, GARMENT_CORE_API_KEY_PEPPER (seed ile aynı olmalı),
 * GARMENT_CORE_PLATFORM_SLUG (varsayılan dressifye),
 * GARMENT_CORE_TENANT_SLUGS (virgülle, örn. stylecoree,hairinfinitye),
 * GARMENT_CORE_KEY_LABEL (örn. prod-2026).
 */
import { randomBytes } from "node:crypto";
import { eq, inArray } from "drizzle-orm";
import { createGarmentCoreDb } from "../src/db/client.js";
import { hashApiKey } from "../src/lib/hash-api-key.js";
import {
  platformApiKeys,
  platformClients,
  platformTenantAccess,
} from "../src/db/schema/platform.js";
import { tenants } from "../src/db/schema/tenants.js";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) {
  console.error("DATABASE_URL gerekli.");
  process.exit(1);
}

const pepper = process.env.GARMENT_CORE_API_KEY_PEPPER ?? "";
const platformSlug = process.env.GARMENT_CORE_PLATFORM_SLUG ?? "dressifye";
const tenantSlugs = (process.env.GARMENT_CORE_TENANT_SLUGS ?? "stylecoree,hairinfinitye")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const label = process.env.GARMENT_CORE_KEY_LABEL ?? `api-key-${new Date().toISOString()}`;
const accessMode =
  process.env.GARMENT_CORE_ACCESS_MODE === "read" ? "read" : "read_write";

async function main() {
  const db = createGarmentCoreDb(databaseUrl);

  const [client] = await db
    .select({ id: platformClients.id })
    .from(platformClients)
    .where(eq(platformClients.slug, platformSlug))
    .limit(1);

  if (!client) {
    console.error(`platform_client bulunamadı: ${platformSlug}`);
    process.exit(1);
  }

  const tList = await db
    .select({ id: tenants.id, slug: tenants.slug })
    .from(tenants)
    .where(inArray(tenants.slug, tenantSlugs));

  if (tList.length !== tenantSlugs.length) {
    console.error("Bazı kiracı slug'ları veritabanında yok:", tenantSlugs);
    process.exit(1);
  }

  for (const t of tList) {
    await db
      .insert(platformTenantAccess)
      .values({
        platformClientId: client.id,
        tenantId: t.id,
        accessMode,
      })
      .onConflictDoNothing({
        target: [platformTenantAccess.platformClientId, platformTenantAccess.tenantId],
      });
  }

  const rawKey = `gkc_${randomBytes(32).toString("base64url")}`;
  const keyHash = hashApiKey(rawKey, pepper);
  const keyPrefix = rawKey.slice(0, 12);

  await db.insert(platformApiKeys).values({
    platformClientId: client.id,
    keyPrefix,
    keyHash,
    label,
  });

  console.log("---");
  console.log("Yeni API anahtarı:");
  console.log(rawKey);
  console.log("---");
}

void main().catch((e) => {
  console.error(e);
  process.exit(1);
});
