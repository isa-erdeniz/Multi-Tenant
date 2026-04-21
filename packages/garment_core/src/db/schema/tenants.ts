import {
  index,
  pgTable,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";
import { tenantDomainKindEnum } from "./enums.js";

/**
 * Veri sahibi kiracılar (ör. stylecoree, hairinfinitye).
 * stylecore ile hairinfinity satırları aynı tabloda olsa bile `id` farklıdır; tüm alt tablolar `tenant_id` ile bağlanır.
 */
export const tenants = pgTable(
  "tenants",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    slug: text("slug").notNull().unique(),
    displayName: text("display_name").notNull(),
    domainKind: tenantDomainKindEnum("domain_kind").notNull().default("mixed"),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [index("tenants_domain_kind_idx").on(t.domainKind)],
);
