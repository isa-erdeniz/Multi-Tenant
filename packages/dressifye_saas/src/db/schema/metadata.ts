import {
  index,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { metadataScopeTypeEnum } from "./enums.js";
import { tenants } from "./tenants.js";

/**
 * Kiracı kapsamlı ek meta (ör. özelleştirilmiş etiketler, harici SKU eşlemesi).
 * `scope_id` null ise kiracıya özel global bağlam (ör. ingestion_batch) için kullanılabilir.
 */
export const metadataEntries = pgTable(
  "metadata_entries",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    tenantId: uuid("tenant_id")
      .notNull()
      .references(() => tenants.id, { onDelete: "cascade" }),
    scopeType: metadataScopeTypeEnum("scope_type").notNull(),
    scopeId: uuid("scope_id"),
    key: text("key").notNull(),
    value: jsonb("value").$type<unknown>().notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    index("metadata_entries_tenant_scope_idx").on(
      t.tenantId,
      t.scopeType,
      t.scopeId,
    ),
    uniqueIndex("metadata_entries_tenant_scope_key_uidx").on(
      t.tenantId,
      t.scopeType,
      t.scopeId,
      t.key,
    ),
  ],
);
