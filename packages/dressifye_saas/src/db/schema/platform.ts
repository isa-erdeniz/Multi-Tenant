import {
  boolean,
  index,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { platformTenantAccessModeEnum } from "./enums.js";
import { tenants } from "./tenants.js";

/** Dressifye vb. tüketen platformlar (veri sahibi kiracıdan farklı). */
export const platformClients = pgTable(
  "platform_clients",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    slug: text("slug").notNull().unique(),
    displayName: text("display_name").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [index("platform_clients_slug_idx").on(t.slug)],
);

/**
 * API anahtarı — yalnızca hash saklanır.
 * İstek doğrulaması: anahtar → client → `platform_tenant_access` ile izin verilen `tenant_id` listesi.
 */
export const platformApiKeys = pgTable(
  "platform_api_keys",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    platformClientId: uuid("platform_client_id")
      .notNull()
      .references(() => platformClients.id, { onDelete: "cascade" }),
    /** Liste/dropdown için; tam anahtar saklanmaz. */
    keyPrefix: text("key_prefix").notNull(),
    keyHash: text("key_hash").notNull().unique(),
    label: text("label").notNull(),
    active: boolean("active").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
  },
  (t) => [
    index("platform_api_keys_client_idx").on(t.platformClientId),
    index("platform_api_keys_active_idx").on(t.active),
  ],
);

/** Hangi platformun hangi kiracının satırlarına erişebileceği (ortak / çoklu kiracı izni burada). */
export const platformTenantAccess = pgTable(
  "platform_tenant_access",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    platformClientId: uuid("platform_client_id")
      .notNull()
      .references(() => platformClients.id, { onDelete: "cascade" }),
    tenantId: uuid("tenant_id")
      .notNull()
      .references(() => tenants.id, { onDelete: "cascade" }),
    accessMode: platformTenantAccessModeEnum("access_mode").notNull().default("read"),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    uniqueIndex("platform_tenant_access_uidx").on(t.platformClientId, t.tenantId),
    index("platform_tenant_access_tenant_idx").on(t.tenantId),
  ],
);
