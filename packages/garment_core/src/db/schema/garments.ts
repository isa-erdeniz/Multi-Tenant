import {
  index,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { garmentProductKindEnum } from "./enums.js";
import { tenants } from "./tenants.js";

/**
 * Mehlr 1.0 için yapılandırılmış çıkarımlar (ör. kumaş, saç tipi, stil).
 * Uygulama katmanında bu alanın şemasını sabitlemek önerilir; DB tarafında jsonb esneklik sağlar.
 */
export type MehlrAttributes = {
  fabricType?: string;
  hairType?: string;
  styleEra?: string;
  cosmeticFinish?: string;
  colorPalette?: string[];
  /** Ek sabit alanlar buraya genişletilebilir. */
  [key: string]: unknown;
};

/**
 * Evrensel havuzdaki ürün / görünüm kaydı. Kaynak: her zaman `tenant_id` + `external_ref`.
 */
export const garments = pgTable(
  "garments",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    tenantId: uuid("tenant_id")
      .notNull()
      .references(() => tenants.id, { onDelete: "cascade" }),
    /** Kaynak sistemdeki birincil anahtar veya birleşik ref. */
    externalRef: text("external_ref").notNull(),
    title: text("title").notNull(),
    productKind: garmentProductKindEnum("product_kind").notNull().default("other"),
    normalizedCategory: text("normalized_category"),
    mehlrAttributes: jsonb("mehlr_attributes")
      .$type<MehlrAttributes>()
      .notNull()
      .default({}),
    /** Data Normalizer çıktısı — tek tip yapı. */
    universalPayload: jsonb("universal_payload")
      .$type<Record<string, unknown>>()
      .notNull()
      .default({}),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    uniqueIndex("garments_tenant_external_ref_uidx").on(t.tenantId, t.externalRef),
    index("garments_tenant_id_idx").on(t.tenantId),
    index("garments_product_kind_idx").on(t.productKind),
  ],
);
