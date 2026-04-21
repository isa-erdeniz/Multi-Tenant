import { index, jsonb, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { securityReviewVerdictEnum } from "./enums.js";
import { tenants } from "./tenants.js";

/**
 * Havuza girişte Erdeniz Security doğrulaması (iz kaydı).
 * `resource_id` ingest öncesi/sonrası hedef kayda işaret edebilir.
 */
export const ingestionSecurityReviews = pgTable(
  "ingestion_security_reviews",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    tenantId: uuid("tenant_id")
      .notNull()
      .references(() => tenants.id, { onDelete: "cascade" }),
    resourceType: text("resource_type").notNull(),
    resourceId: uuid("resource_id"),
    verdict: securityReviewVerdictEnum("verdict").notNull(),
    trace: jsonb("trace").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    index("ingestion_security_reviews_tenant_idx").on(t.tenantId),
    index("ingestion_security_reviews_resource_idx").on(
      t.tenantId,
      t.resourceType,
      t.resourceId,
    ),
  ],
);
