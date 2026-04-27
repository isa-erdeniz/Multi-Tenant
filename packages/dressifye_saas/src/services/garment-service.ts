import { and, asc, eq, gt, inArray, sql } from "drizzle-orm";
import type { GarmentCoreDb } from "../db/client.js";
import { garments } from "../db/schema/garments.js";
import { ingestionSecurityReviews } from "../db/schema/ingestion-security.js";
import type { SecurityGateResult } from "../security/erdeniz-security-gateway.js";
import type { UniversalGarmentShape } from "../ingestion/normalizer.js";

export async function upsertGarmentWithSecurityAudit(
  db: GarmentCoreDb,
  params: {
    tenantId: string;
    shape: UniversalGarmentShape;
    security: SecurityGateResult;
  },
) {
  const { tenantId, shape, security } = params;
  return db.transaction(async (tx) => {
    const [row] = await tx
      .insert(garments)
      .values({
        tenantId,
        externalRef: shape.externalRef,
        title: shape.title,
        productKind: shape.productKind,
        normalizedCategory: shape.normalizedCategory ?? null,
        mehlrAttributes: shape.mehlrAttributes,
        universalPayload: shape.universalPayload,
      })
      .onConflictDoUpdate({
        target: [garments.tenantId, garments.externalRef],
        set: {
          title: sql`excluded.title`,
          productKind: sql`excluded.product_kind`,
          normalizedCategory: sql`excluded.normalized_category`,
          mehlrAttributes: sql`excluded.mehlr_attributes`,
          universalPayload: sql`excluded.universal_payload`,
          updatedAt: new Date(),
        },
      })
      .returning();

    if (!row) throw new Error("garment_upsert_failed");

    await tx.insert(ingestionSecurityReviews).values({
      tenantId,
      resourceType: "garment",
      resourceId: row.id,
      verdict: security.verdict,
      trace: {
        ...security.trace,
        external_ref: shape.externalRef,
      },
    });

    return row;
  });
}

export async function recordIngestSecurityOnly(
  db: GarmentCoreDb,
  params: {
    tenantId: string;
    security: SecurityGateResult;
    externalRef?: string;
  },
) {
  await db.insert(ingestionSecurityReviews).values({
    tenantId: params.tenantId,
    resourceType: "garment_ingest",
    resourceId: null,
    verdict: params.security.verdict,
    trace: {
      ...params.security.trace,
      external_ref: params.externalRef,
    },
  });
}

export async function getGarmentByIdForTenants(
  db: GarmentCoreDb,
  garmentId: string,
  allowedTenantIds: string[],
) {
  if (!allowedTenantIds.length) return undefined;
  const rows = await db
    .select()
    .from(garments)
    .where(and(eq(garments.id, garmentId), inArray(garments.tenantId, allowedTenantIds)))
    .limit(1);
  return rows[0];
}

export async function listGarmentsForTenant(
  db: GarmentCoreDb,
  params: {
    tenantId: string;
    limit: number;
    cursor?: string;
  },
) {
  const { tenantId, limit } = params;
  const cap = Math.min(Math.max(limit, 1), 100);
  const parts = [eq(garments.tenantId, tenantId)];
  if (params.cursor) parts.push(gt(garments.id, params.cursor));

  const rows = await db
    .select()
    .from(garments)
    .where(and(...parts))
    .orderBy(asc(garments.id))
    .limit(cap + 1);

  const hasMore = rows.length > cap;
  const slice = hasMore ? rows.slice(0, cap) : rows;
  const nextCursor = hasMore ? slice[slice.length - 1]?.id : undefined;

  return { items: slice, nextCursor };
}
