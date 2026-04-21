import { and, eq } from "drizzle-orm";
import type { GarmentCoreDb } from "../db/client.js";
import { HttpError } from "../http/errors.js";
import { hashApiKey } from "../lib/hash-api-key.js";
import {
  platformApiKeys,
  platformClients,
  platformTenantAccess,
} from "../db/schema/platform.js";
import { tenants } from "../db/schema/tenants.js";

export type GarmentGrant = {
  tenantId: string;
  tenantSlug: string;
  accessMode: "read" | "read_write";
};

export type GarmentAuthContext = {
  apiKeyId: string;
  platformClientId: string;
  platformSlug: string;
  grants: GarmentGrant[];
};

export async function resolveApiKey(
  db: GarmentCoreDb,
  rawKey: string,
  pepper: string,
): Promise<GarmentAuthContext | null> {
  const keyHash = hashApiKey(rawKey, pepper);
  const rows = await db
    .select({
      apiKeyId: platformApiKeys.id,
      platformClientId: platformApiKeys.platformClientId,
      platformSlug: platformClients.slug,
    })
    .from(platformApiKeys)
    .innerJoin(
      platformClients,
      eq(platformApiKeys.platformClientId, platformClients.id),
    )
    .where(and(eq(platformApiKeys.keyHash, keyHash), eq(platformApiKeys.active, true)))
    .limit(1);

  const row = rows[0];
  if (!row) return null;

  const grantRows = await db
    .select({
      tenantId: platformTenantAccess.tenantId,
      accessMode: platformTenantAccess.accessMode,
      tenantSlug: tenants.slug,
    })
    .from(platformTenantAccess)
    .innerJoin(tenants, eq(platformTenantAccess.tenantId, tenants.id))
    .where(eq(platformTenantAccess.platformClientId, row.platformClientId));

  const grants: GarmentGrant[] = grantRows.map((g) => ({
    tenantId: g.tenantId,
    tenantSlug: g.tenantSlug,
    accessMode: g.accessMode,
  }));

  void db
    .update(platformApiKeys)
    .set({ lastUsedAt: new Date() })
    .where(eq(platformApiKeys.id, row.apiKeyId))
    .catch(() => undefined);

  return {
    apiKeyId: row.apiKeyId,
    platformClientId: row.platformClientId,
    platformSlug: row.platformSlug,
    grants,
  };
}

export function findGrant(
  auth: GarmentAuthContext,
  tenantSlug: string,
): GarmentGrant | undefined {
  const needle = tenantSlug.trim().toLowerCase();
  return auth.grants.find((g) => g.tenantSlug.toLowerCase() === needle);
}

export function assertReadGrant(auth: GarmentAuthContext, tenantSlug: string): GarmentGrant {
  const g = findGrant(auth, tenantSlug);
  if (!g) {
    throw new HttpError(403, "tenant_forbidden", "Bu kiracı için yetki yok.");
  }
  return g;
}

export function assertWriteGrant(auth: GarmentAuthContext, tenantSlug: string): GarmentGrant {
  const g = assertReadGrant(auth, tenantSlug);
  if (g.accessMode !== "read_write") {
    throw new HttpError(403, "tenant_read_only", "Bu kiracı için yalnızca okuma izni var.");
  }
  return g;
}
