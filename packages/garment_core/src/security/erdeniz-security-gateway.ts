import type { ErdenizSecurityMode } from "../config/env.js";

export type SecurityGateInput = {
  tenantId: string;
  tenantSlug?: string;
  resourceType: string;
  resourceId?: string;
  payload: Record<string, unknown>;
};

export type SecurityGateResult = {
  verdict: "allowed" | "blocked" | "quarantined";
  trace: Record<string, unknown>;
};

type RemoteVerdict = SecurityGateResult["verdict"];

function normalizeVerdict(v: unknown): RemoteVerdict | null {
  if (v === "allowed" || v === "blocked" || v === "quarantined") return v;
  return null;
}

/**
 * Uzak `ERDENIZ_SECURITY_INGEST_URL` varsa POST ile doğrular.
 * Yoksa veya hata: `off` → izin; `audit` → izin + trace; `enforce` → uzak hata bloklar.
 */
export async function evaluateWithErdenizSecurity(
  input: SecurityGateInput,
  options: { url: string; mode: ErdenizSecurityMode },
): Promise<SecurityGateResult> {
  const { url, mode } = options;
  const baseTrace = {
    tenant_id: input.tenantId,
    tenant_slug: input.tenantSlug,
    resource_type: input.resourceType,
  };

  if (mode === "off") {
    return { verdict: "allowed", trace: { ...baseTrace, mode: "off", remote: false } };
  }

  if (!url) {
    return {
      verdict: "allowed",
      trace: {
        ...baseTrace,
        mode,
        remote: false,
        note: "ERDENIZ_SECURITY_INGEST_URL tanımlı değil; yerel politika ile izin.",
      },
    };
  }

  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 8000);
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
      signal: controller.signal,
    });
    clearTimeout(t);

    const text = await res.text();
    let body: unknown;
    try {
      body = text ? JSON.parse(text) : {};
    } catch {
      body = { raw: text };
    }
    const obj = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
    const verdict = normalizeVerdict(obj.verdict) ?? (res.ok ? "allowed" : "quarantined");
    const trace = {
      ...baseTrace,
      remote: true,
      http_status: res.status,
      remote_body: obj,
    };
    return { verdict, trace };
  } catch (err) {
    const trace = {
      ...baseTrace,
      remote: true,
      error: err instanceof Error ? err.message : String(err),
    };
    if (mode === "enforce") {
      return { verdict: "blocked", trace };
    }
    return {
      verdict: "allowed",
      trace: {
        ...trace,
        note: "Uzak güvenlik hatası; audit modunda ingest izni verildi.",
      },
    };
  }
}
