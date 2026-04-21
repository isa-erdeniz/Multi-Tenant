import { pgEnum } from "drizzle-orm/pg-core";

/** Kaynak kiracının ürün alanı (evrensel havuzda ayrıştırma / Mehlr bağlamı). */
export const tenantDomainKindEnum = pgEnum("tenant_domain_kind", [
  "fashion_style",
  "hair_cosmetic",
  "mixed",
]);

export const garmentProductKindEnum = pgEnum("garment_product_kind", [
  "garment",
  "cosmetic",
  "accessory",
  "other",
]);

export const metadataScopeTypeEnum = pgEnum("metadata_scope_type", [
  "garment",
  "user",
  "ingestion_batch",
]);

export const platformTenantAccessModeEnum = pgEnum("platform_tenant_access_mode", [
  "read",
  "read_write",
]);

export const securityReviewVerdictEnum = pgEnum("security_review_verdict", [
  "allowed",
  "blocked",
  "quarantined",
]);
