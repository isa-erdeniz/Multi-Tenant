CREATE TYPE "public"."garment_product_kind" AS ENUM('garment', 'cosmetic', 'accessory', 'other');--> statement-breakpoint
CREATE TYPE "public"."metadata_scope_type" AS ENUM('garment', 'user', 'ingestion_batch');--> statement-breakpoint
CREATE TYPE "public"."platform_tenant_access_mode" AS ENUM('read', 'read_write');--> statement-breakpoint
CREATE TYPE "public"."security_review_verdict" AS ENUM('allowed', 'blocked', 'quarantined');--> statement-breakpoint
CREATE TYPE "public"."tenant_domain_kind" AS ENUM('fashion_style', 'hair_cosmetic', 'mixed');--> statement-breakpoint
CREATE TABLE "tenants" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"slug" text NOT NULL,
	"display_name" text NOT NULL,
	"domain_kind" "tenant_domain_kind" DEFAULT 'mixed' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "tenants_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"tenant_id" uuid NOT NULL,
	"external_id" text NOT NULL,
	"email" text,
	"display_name" text,
	"profile" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "garments" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"tenant_id" uuid NOT NULL,
	"external_ref" text NOT NULL,
	"title" text NOT NULL,
	"product_kind" "garment_product_kind" DEFAULT 'other' NOT NULL,
	"normalized_category" text,
	"mehlr_attributes" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"universal_payload" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "metadata_entries" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"tenant_id" uuid NOT NULL,
	"scope_type" "metadata_scope_type" NOT NULL,
	"scope_id" uuid,
	"key" text NOT NULL,
	"value" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "platform_api_keys" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"platform_client_id" uuid NOT NULL,
	"key_prefix" text NOT NULL,
	"key_hash" text NOT NULL,
	"label" text NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"last_used_at" timestamp with time zone,
	CONSTRAINT "platform_api_keys_key_hash_unique" UNIQUE("key_hash")
);
--> statement-breakpoint
CREATE TABLE "platform_clients" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"slug" text NOT NULL,
	"display_name" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "platform_clients_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
CREATE TABLE "platform_tenant_access" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"platform_client_id" uuid NOT NULL,
	"tenant_id" uuid NOT NULL,
	"access_mode" "platform_tenant_access_mode" DEFAULT 'read' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "ingestion_security_reviews" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"tenant_id" uuid NOT NULL,
	"resource_type" text NOT NULL,
	"resource_id" uuid,
	"verdict" "security_review_verdict" NOT NULL,
	"trace" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "users" ADD CONSTRAINT "users_tenant_id_tenants_id_fk" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "garments" ADD CONSTRAINT "garments_tenant_id_tenants_id_fk" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "metadata_entries" ADD CONSTRAINT "metadata_entries_tenant_id_tenants_id_fk" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "platform_api_keys" ADD CONSTRAINT "platform_api_keys_platform_client_id_platform_clients_id_fk" FOREIGN KEY ("platform_client_id") REFERENCES "public"."platform_clients"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "platform_tenant_access" ADD CONSTRAINT "platform_tenant_access_platform_client_id_platform_clients_id_fk" FOREIGN KEY ("platform_client_id") REFERENCES "public"."platform_clients"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "platform_tenant_access" ADD CONSTRAINT "platform_tenant_access_tenant_id_tenants_id_fk" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "ingestion_security_reviews" ADD CONSTRAINT "ingestion_security_reviews_tenant_id_tenants_id_fk" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "tenants_domain_kind_idx" ON "tenants" USING btree ("domain_kind");--> statement-breakpoint
CREATE UNIQUE INDEX "users_tenant_external_uidx" ON "users" USING btree ("tenant_id","external_id");--> statement-breakpoint
CREATE INDEX "users_tenant_id_idx" ON "users" USING btree ("tenant_id");--> statement-breakpoint
CREATE UNIQUE INDEX "garments_tenant_external_ref_uidx" ON "garments" USING btree ("tenant_id","external_ref");--> statement-breakpoint
CREATE INDEX "garments_tenant_id_idx" ON "garments" USING btree ("tenant_id");--> statement-breakpoint
CREATE INDEX "garments_product_kind_idx" ON "garments" USING btree ("product_kind");--> statement-breakpoint
CREATE INDEX "metadata_entries_tenant_scope_idx" ON "metadata_entries" USING btree ("tenant_id","scope_type","scope_id");--> statement-breakpoint
CREATE UNIQUE INDEX "metadata_entries_tenant_scope_key_uidx" ON "metadata_entries" USING btree ("tenant_id","scope_type","scope_id","key");--> statement-breakpoint
CREATE INDEX "platform_api_keys_client_idx" ON "platform_api_keys" USING btree ("platform_client_id");--> statement-breakpoint
CREATE INDEX "platform_api_keys_active_idx" ON "platform_api_keys" USING btree ("active");--> statement-breakpoint
CREATE INDEX "platform_clients_slug_idx" ON "platform_clients" USING btree ("slug");--> statement-breakpoint
CREATE UNIQUE INDEX "platform_tenant_access_uidx" ON "platform_tenant_access" USING btree ("platform_client_id","tenant_id");--> statement-breakpoint
CREATE INDEX "platform_tenant_access_tenant_idx" ON "platform_tenant_access" USING btree ("tenant_id");--> statement-breakpoint
CREATE INDEX "ingestion_security_reviews_tenant_idx" ON "ingestion_security_reviews" USING btree ("tenant_id");--> statement-breakpoint
CREATE INDEX "ingestion_security_reviews_resource_idx" ON "ingestion_security_reviews" USING btree ("tenant_id","resource_type","resource_id");