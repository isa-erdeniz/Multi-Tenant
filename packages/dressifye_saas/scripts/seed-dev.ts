/**
 * Geliştirme: kiracılar, dressifye platformu, tam erişimli API anahtarı üretir.
 * Çalıştırma: npm run db:seed
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

async function main() {
  const db = createGarmentCoreDb(databaseUrl);

  await db
    .insert(tenants)
    .values([
      {
        slug: "stylecoree",
        displayName: "Style Core",
        domainKind: "fashion_style",
      },
      {
        slug: "hairinfinitye",
        displayName: "Hair Infinity",
        domainKind: "hair_cosmetic",
      },
    ])
    .onConflictDoNothing({ target: tenants.slug });

  const tList = await db
    .select({ id: tenants.id, slug: tenants.slug })
    .from(tenants)
    .where(inArray(tenants.slug, ["stylecoree", "hairinfinitye"]));

  if (tList.length < 2) {
    console.error("Kiracı satırları eksik; migrasyonları uygulayıp tekrar deneyin.");
    process.exit(1);
  }

  await db
    .insert(platformClients)
    .values({
      slug: "dressifye",
      displayName: "Dressifye",
    })
    .onConflictDoNothing({ target: platformClients.slug });

  const [client] = await db
    .select({ id: platformClients.id })
    .from(platformClients)
    .where(eq(platformClients.slug, "dressifye"))
    .limit(1);

  if (!client) {
    console.error("dressifye platform_client bulunamadı.");
    process.exit(1);
  }

  for (const t of tList) {
    await db
      .insert(platformTenantAccess)
      .values({
        platformClientId: client.id,
        tenantId: t.id,
        accessMode: "read_write",
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
    label: "seed-dev",
  });

  console.log("---");
  console.log("API anahtarı (yalnızca bir kez gösterilir):");
  console.log(rawKey);
  console.log("---");
  console.log("Örnek ingest:");
  console.log(
    `curl -sS -X POST http://localhost:8080/v1/garments/ingest -H "Authorization: Bearer ${rawKey}" -H "Content-Type: application/json" -d '{"tenant_slug":"stylecoree","external_ref":"demo-1","raw":{"title":"Retro ceket","fabric":"Pamuk","style":"Retro"}}'`,
  );
}

void main().catch((e) => {
  console.error(e);
  process.exit(1);
});
