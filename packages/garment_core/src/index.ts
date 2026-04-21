import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { getEnv } from "./config/env.js";
import { createGarmentCoreDb } from "./db/client.js";
import { createApp } from "./create-app.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

function readVersion(): string {
  try {
    return readFileSync(join(__dirname, "..", "VERSION"), "utf8").trim();
  } catch {
    return process.env.GARMENT_CORE_VERSION || "0.0.0";
  }
}

const env = getEnv();
const version = readVersion();
const db = env.databaseUrl ? createGarmentCoreDb(env.databaseUrl) : null;

if (!db) {
  console.warn("garment_core: DATABASE_URL yok — /v1 uçları 503 döner.");
}

const app = createApp({ db, version });
const { port } = env;

app.listen(port, () => {
  console.log(`garment_core listening on ${port}`);
});
