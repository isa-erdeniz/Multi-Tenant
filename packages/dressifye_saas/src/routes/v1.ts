import { Router } from "express";
import type { GarmentCoreDb } from "../db/client.js";
import { getEnv } from "../config/env.js";
import { asyncHandler } from "../http/async-handler.js";
import { HttpError } from "../http/errors.js";
import { normalizeUniversalGarment } from "../ingestion/normalizer.js";
import { evaluateWithErdenizSecurity } from "../security/erdeniz-security-gateway.js";
import {
  assertReadGrant,
  assertWriteGrant,
} from "../services/api-key-service.js";
import {
  listGarmentsForTenant,
  recordIngestSecurityOnly,
  upsertGarmentWithSecurityAudit,
  getGarmentByIdForTenants,
} from "../services/garment-service.js";

function parseLimit(raw: unknown, fallback: number): number {
  const n = typeof raw === "string" ? Number(raw) : typeof raw === "number" ? raw : NaN;
  if (!Number.isFinite(n)) return fallback;
  return n;
}

export function createV1Router(db: GarmentCoreDb) {
  const env = getEnv();
  const r = Router();

  r.get(
    "/tenants",
    asyncHandler(async (req, res) => {
      const auth = req.garmentAuth;
      if (!auth) throw new HttpError(500, "auth_missing");
      const seen = new Map<string, { tenantId: string; tenantSlug: string; accessMode: string }>();
      for (const g of auth.grants) {
        seen.set(g.tenantId, {
          tenantId: g.tenantId,
          tenantSlug: g.tenantSlug,
          accessMode: g.accessMode,
        });
      }
      res.json({ tenants: [...seen.values()] });
    }),
  );

  r.get(
    "/garments",
    asyncHandler(async (req, res) => {
      const auth = req.garmentAuth;
      if (!auth) throw new HttpError(500, "auth_missing");
      const tenantSlug = String(req.query.tenant_slug ?? "").trim();
      if (!tenantSlug) {
        throw new HttpError(400, "missing_tenant_slug", "tenant_slug sorgu parametresi gerekli.");
      }
      const grant = assertReadGrant(auth, tenantSlug);
      const limit = parseLimit(req.query.limit, 25);
      const cursor =
        typeof req.query.cursor === "string" && req.query.cursor.trim()
          ? req.query.cursor.trim()
          : undefined;
      const { items, nextCursor } = await listGarmentsForTenant(db, {
        tenantId: grant.tenantId,
        limit,
        cursor,
      });
      res.json({
        tenantSlug: grant.tenantSlug,
        items: items.map((row) => ({
          id: row.id,
          tenantId: row.tenantId,
          externalRef: row.externalRef,
          title: row.title,
          productKind: row.productKind,
          normalizedCategory: row.normalizedCategory,
          mehlrAttributes: row.mehlrAttributes,
          universalPayload: row.universalPayload,
          createdAt: row.createdAt,
          updatedAt: row.updatedAt,
        })),
        nextCursor,
      });
    }),
  );

  r.get(
    "/garments/:id",
    asyncHandler(async (req, res) => {
      const auth = req.garmentAuth;
      if (!auth) throw new HttpError(500, "auth_missing");
      const id = req.params.id;
      const allowed = auth.grants.map((g) => g.tenantId);
      const row = await getGarmentByIdForTenants(db, id, allowed);
      if (!row) {
        throw new HttpError(404, "garment_not_found", "Kayıt bulunamadı veya erişim yok.");
      }
      const grant = auth.grants.find((g) => g.tenantId === row.tenantId);
      if (!grant) throw new HttpError(403, "tenant_forbidden");
      res.json({
        id: row.id,
        tenantSlug: grant.tenantSlug,
        externalRef: row.externalRef,
        title: row.title,
        productKind: row.productKind,
        normalizedCategory: row.normalizedCategory,
        mehlrAttributes: row.mehlrAttributes,
        universalPayload: row.universalPayload,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      });
    }),
  );

  r.post(
    "/garments/ingest",
    asyncHandler(async (req, res) => {
      const auth = req.garmentAuth;
      if (!auth) throw new HttpError(500, "auth_missing");
      const body = req.body as Record<string, unknown>;
      const tenantSlug = String(body.tenant_slug ?? "").trim();
      if (!tenantSlug) {
        throw new HttpError(400, "missing_tenant_slug", "tenant_slug gerekli.");
      }
      const grant = assertWriteGrant(auth, tenantSlug);
      const raw = body.raw;
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        throw new HttpError(400, "invalid_raw", "raw bir nesne olmalıdır.");
      }
      const sourceDomain =
        typeof body.source_domain === "string" ? body.source_domain : undefined;
      const externalRef =
        typeof body.external_ref === "string" ? body.external_ref : undefined;

      let shape;
      try {
        shape = normalizeUniversalGarment({
          tenantSlug,
          sourceDomain,
          externalRef,
          raw: raw as Record<string, unknown>,
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "normalize_failed";
        throw new HttpError(400, "normalize_error", msg);
      }

      const security = await evaluateWithErdenizSecurity(
        {
          tenantId: grant.tenantId,
          tenantSlug: grant.tenantSlug,
          resourceType: "garment_ingest",
          payload: {
            external_ref: shape.externalRef,
            universal_payload: shape.universalPayload,
            mehlr_attributes: shape.mehlrAttributes,
            platform_client: auth.platformSlug,
          },
        },
        { url: env.erdenizSecurityUrl, mode: env.erdenizSecurityMode },
      );

      if (security.verdict !== "allowed") {
        await recordIngestSecurityOnly(db, {
          tenantId: grant.tenantId,
          security,
          externalRef: shape.externalRef,
        });
        const status = security.verdict === "blocked" ? 403 : 422;
        res.status(status).json({
          error: security.verdict === "blocked" ? "security_blocked" : "security_quarantined",
          verdict: security.verdict,
          trace: security.trace,
        });
        return;
      }

      const row = await upsertGarmentWithSecurityAudit(db, {
        tenantId: grant.tenantId,
        shape,
        security,
      });

      res.status(200).json({
        id: row.id,
        tenantSlug: grant.tenantSlug,
        externalRef: row.externalRef,
        verdict: security.verdict,
      });
    }),
  );

  return r;
}
