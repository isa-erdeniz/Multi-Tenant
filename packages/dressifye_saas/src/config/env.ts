export type ErdenizSecurityMode = "off" | "audit" | "enforce";

export function getEnv() {
  const databaseUrl = process.env.DATABASE_URL ?? "";
  const apiKeyPepper = process.env.GARMENT_CORE_API_KEY_PEPPER ?? "";
  const erdenizSecurityUrl = process.env.ERDENIZ_SECURITY_INGEST_URL?.trim() ?? "";
  const erdenizSecurityMode = parseSecurityMode(
    process.env.ERDENIZ_SECURITY_MODE ?? "audit",
  );
  const corsOrigins = (process.env.CORS_ORIGINS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return {
    port: Number(process.env.PORT || 8080),
    databaseUrl,
    nodeEnv: process.env.NODE_ENV ?? "development",
    apiKeyPepper,
    erdenizSecurityUrl,
    erdenizSecurityMode,
    corsOrigins,
  };
}

function parseSecurityMode(raw: string): ErdenizSecurityMode {
  if (raw === "off" || raw === "audit" || raw === "enforce") return raw;
  return "audit";
}
