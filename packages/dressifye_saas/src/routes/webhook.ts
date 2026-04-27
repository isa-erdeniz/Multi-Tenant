/**
 * POST /webhook/mehlr — Mehlr'den gelen imzalı olayları alır.
 * Dahili kullanım: harici API anahtarı gerektirmez; HMAC ile doğrulanır.
 */
import { Router, type Request, type Response } from "express";
import { eq } from "drizzle-orm";
import type { GarmentCoreDb } from "../db/client.js";
import { asyncHandler } from "../http/async-handler.js";
import { HttpError } from "../http/errors.js";
import { verifyHubSignature } from "../lib/verify-hmac.js";
import { normalizeUniversalGarment } from "../ingestion/normalizer.js";
import { evaluateWithErdenizSecurity } from "../security/erdeniz-security-gateway.js";
import {
  recordIngestSecurityOnly,
  upsertGarmentWithSecurityAudit,
} from "../services/garment-service.js";
import { tenants } from "../db/schema/tenants.js";
import { getEnv } from "../config/env.js";

type MehlrEventBody = {
  event: string;
  tenant_slug: string;
  payload: Record<string, unknown>;
};

function isValidBody(b: unknown): b is MehlrEventBody {
  return (
    b !== null &&
    typeof b === "object" &&
    typeof (b as Record<string, unknown>).event === "string" &&
    typeof (b as Record<string, unknown>).tenant_slug === "string" &&
    typeof (b as Record<string, unknown>).payload === "object"
  );
}

export function createWebhookRouter(
  db: GarmentCoreDb,
  rawBodyStore: WeakMap<Request, Buffer>,
) {
  const env = getEnv();
  const secret = process.env.GARMENT_CORE_WEBHOOK_SECRET ?? "";
  const r = Router();

  r.post(
    "/mehlr",
    asyncHandler(async (req: Request, res: Response) => {
      const rawBody = rawBodyStore.get(req);

      const sig = req.headers["x-hub-signature-256"] as string | undefined;
      if (!verifyHubSignature(rawBody ?? Buffer.alloc(0), sig, secret)) {
        throw new HttpError(401, "invalid_signature", "HMAC doğrulaması başarısız.");
      }

      if (!isValidBody(req.body)) {
        throw new HttpError(400, "invalid_body", "event, tenant_slug ve payload zorunludur.");
      }

      const { event, tenant_slug, payload } = req.body;

      const tenantRows = await db
        .select({ id: tenants.id })
        .from(tenants)
        .where(eq(tenants.slug, tenant_slug))
        .limit(1);

      const tenant = tenantRows[0];
      if (!tenant) {
        throw new HttpError(404, "tenant_not_found", `Kiracı bulunamadı: ${tenant_slug}`);
      }

      if (event === "garment.upserted") {
        return handleGarmentUpserted(db, tenant.id, tenant_slug, payload, env, res);
      }

      if (event === "recommendation.created") {
        res.json({ ok: true, event, note: "recommendation alındı (işlenmedi)" });
        return;
      }

      res.json({ ok: true, event, note: "bilinmeyen event; yok sayıldı" });
    }),
  );

  return r;
}

async function handleGarmentUpserted(
  db: GarmentCoreDb,
  tenantId: string,
  tenantSlug: string,
  payload: Record<string, unknown>,
  env: ReturnType<typeof getEnv>,
  res: Response,
) {
  const raw = payload.raw;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new HttpError(400, "invalid_raw", "payload.raw bir nesne olmalıdır.");
  }

  const externalRef =
    typeof payload.external_ref === "string" ? payload.external_ref : undefined;

  let shape;
  try {
    shape = normalizeUniversalGarment({
      tenantSlug,
      externalRef,
      raw: raw as Record<string, unknown>,
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "normalize_failed";
    throw new HttpError(400, "normalize_error", msg);
  }

  const security = await evaluateWithErdenizSecurity(
    {
      tenantId,
      tenantSlug,
      resourceType: "garment_ingest",
      payload: { source: "mehlr_webhook", ...shape },
    },
    { url: env.erdenizSecurityUrl, mode: env.erdenizSecurityMode },
  );

  if (security.verdict !== "allowed") {
    await recordIngestSecurityOnly(db, { tenantId, security, externalRef: shape.externalRef });
    res.status(422).json({ ok: false, verdict: security.verdict });
    return;
  }

  const row = await upsertGarmentWithSecurityAudit(db, { tenantId, shape, security });
  res.json({ ok: true, id: row.id, externalRef: row.externalRef, verdict: "allowed" });
}
