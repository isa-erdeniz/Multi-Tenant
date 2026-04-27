import {
  index,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { tenants } from "./tenants.js";

/**
 * Kiracıya bağlı kullanıcılar. Sorgularda `tenant_id` zorunlu filtredir (çapraz kiracı sızıntısı yok).
 */
export const users = pgTable(
  "users",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    tenantId: uuid("tenant_id")
      .notNull()
      .references(() => tenants.id, { onDelete: "cascade" }),
    externalId: text("external_id").notNull(),
    email: text("email"),
    displayName: text("display_name"),
    /** Kaynak sistemden kalan alanlar; normalizer sonrası `garments.universal_payload` ile uyumlu olabilir. */
    profile: jsonb("profile")
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
    uniqueIndex("users_tenant_external_uidx").on(t.tenantId, t.externalId),
    index("users_tenant_id_idx").on(t.tenantId),
  ],
);
