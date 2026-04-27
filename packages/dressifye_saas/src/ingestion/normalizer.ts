/**
 * Evrensel ingest: stylecoree / hairinfinitye vb. kaynaklardan gelen ham kayıtları
 * `garments.universal_payload` + `mehlr_attributes` şekline dönüştürür.
 */

export type UniversalIngestInput = {
  tenantSlug: string;
  sourceDomain?: string;
  externalRef?: string;
  raw: Record<string, unknown>;
};

export type UniversalGarmentShape = {
  externalRef: string;
  title: string;
  productKind: "garment" | "cosmetic" | "accessory" | "other";
  normalizedCategory?: string;
  mehlrAttributes: Record<string, unknown>;
  universalPayload: Record<string, unknown>;
};

function pickString(raw: Record<string, unknown>, keys: string[]): string | undefined {
  for (const k of keys) {
    const v = raw[k];
    if (v === undefined || v === null) continue;
    const s = String(v).trim();
    if (s.length > 0) return s;
  }
  return undefined;
}

function pickStringArray(raw: Record<string, unknown>, key: string): string[] | undefined {
  const v = raw[key];
  if (!Array.isArray(v)) return undefined;
  const out = v.map((x) => String(x).trim()).filter(Boolean);
  return out.length ? out : undefined;
}

function inferDomainFromTenantSlug(tenantSlug: string): string {
  const s = tenantSlug.toLowerCase();
  if (s.includes("hair") || s.includes("infinity")) return "hairinfinitye";
  if (s.includes("style") || s.includes("core")) return "stylecoree";
  return s;
}

function inferProductKind(
  tenantSlug: string,
  sourceDomain: string | undefined,
  raw: Record<string, unknown>,
): "garment" | "cosmetic" | "accessory" | "other" {
  const hinted = pickString(raw, ["productKind", "product_kind", "kind", "type"]);
  if (
    hinted === "garment" ||
    hinted === "cosmetic" ||
    hinted === "accessory" ||
    hinted === "other"
  ) {
    return hinted;
  }
  const domain = (sourceDomain ?? inferDomainFromTenantSlug(tenantSlug)).toLowerCase();
  if (domain.includes("hair") || tenantSlug.toLowerCase().includes("hair")) return "cosmetic";
  if (domain.includes("style") || domain.includes("core")) return "garment";
  return "other";
}

function deriveExternalRef(input: UniversalIngestInput): string {
  if (input.externalRef?.trim()) return input.externalRef.trim();
  const raw = input.raw;
  const v = pickString(raw, ["id", "externalRef", "external_ref", "sku", "code"]);
  if (v) return v;
  throw new Error("missing_external_ref");
}

export function normalizeUniversalGarment(input: UniversalIngestInput): UniversalGarmentShape {
  const externalRef = deriveExternalRef(input);
  const raw = input.raw;
  const title =
    pickString(raw, [
      "title",
      "name",
      "outfitTitle",
      "outfit_title",
      "productName",
      "product_name",
      "label",
    ]) ?? "Untitled";

  const fabricType = pickString(raw, [
    "fabricType",
    "fabric_type",
    "fabric",
    "material",
    "kumas",
    "kumaş",
  ]);
  const hairType = pickString(raw, ["hairType", "hair_type", "sacTipi", "sac_tipi"]);
  const styleEra = pickString(raw, ["styleEra", "style_era", "style", "styleTag", "era"]);
  const cosmeticFinish = pickString(raw, [
    "cosmeticFinish",
    "finish",
    "finishType",
    "bitis",
  ]);
  const colorPalette = pickStringArray(raw, "colorPalette") ?? pickStringArray(raw, "colors");

  const mehlrAttributes: Record<string, unknown> = {};
  if (fabricType) mehlrAttributes.fabricType = fabricType;
  if (hairType) mehlrAttributes.hairType = hairType;
  if (styleEra) mehlrAttributes.styleEra = styleEra;
  if (cosmeticFinish) mehlrAttributes.cosmeticFinish = cosmeticFinish;
  if (colorPalette) mehlrAttributes.colorPalette = colorPalette;

  const normalizedCategory = pickString(raw, [
    "normalizedCategory",
    "category",
    "kategori",
    "department",
  ]);

  const sourceDomain = input.sourceDomain ?? inferDomainFromTenantSlug(input.tenantSlug);
  const productKind = inferProductKind(input.tenantSlug, sourceDomain, raw);

  const universalPayload: Record<string, unknown> = {
    source_domain: sourceDomain,
    tenant_slug: input.tenantSlug,
    normalized_at: new Date().toISOString(),
    original: raw,
  };

  return {
    externalRef,
    title,
    productKind,
    normalizedCategory,
    mehlrAttributes,
    universalPayload,
  };
}
