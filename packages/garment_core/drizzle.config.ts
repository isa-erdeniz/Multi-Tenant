import { defineConfig } from "drizzle-kit";

/** `drizzle-kit generate` şema dosyalarından çalışır; canlı DB gerekmez. `migrate` / `push` için gerçek URL verin. */
const databaseUrl =
  process.env.DATABASE_URL ??
  "postgresql://garment:garment@127.0.0.1:5432/garment_core";

export default defineConfig({
  // Kaynakta `*.ts` → `import "./x.js"` (NodeNext); drizzle-kit CJS yükleyicisi için derlenmiş şema kullanılır.
  schema: "./dist/db/schema/index.js",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: {
    url: databaseUrl,
  },
  strict: true,
});
