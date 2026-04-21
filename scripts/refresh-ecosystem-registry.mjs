/**
 * Multi-Tenant kökündeki dizinleri tarar; ecosystem/registry.json içine
 * eksik tenant satırları ekler (mevcut origins korunur).
 */
import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const REGISTRY = path.join(ROOT, "ecosystem", "registry.json");

const BLOCK = new Set([
  "node_modules",
  "gateway",
  ".git",
  "packages",
  "ecosystem",
  "dist",
  "__pycache__",
  ".venv",
  "venv",
  "scripts",
  "garment_core",
  "mehlr_1.0",
  "erdeniz_security",
]);

function slugify(name) {
  return String(name)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

async function main() {
  let data = { version: 1, tenants: [] };
  try {
    const raw = await readFile(REGISTRY, "utf8");
    data = JSON.parse(raw);
  } catch {
    // yoksa sıfırdan
  }
  if (!data.tenants || !Array.isArray(data.tenants)) data.tenants = [];

  const bySlug = new Map(data.tenants.map((t) => [t.slug, t]));
  const entries = await readdir(ROOT, { withFileTypes: true });

  for (const ent of entries) {
    if (!ent.isDirectory()) continue;
    const name = ent.name;
    if (name.startsWith(".")) continue;
    if (BLOCK.has(name)) continue;
    const slug = slugify(name);
    if (!slug) continue;
    if (bySlug.has(slug)) continue;
    const row = {
      slug,
      folder: name,
      origins: [],
    };
    data.tenants.push(row);
    bySlug.set(slug, row);
  }

  data.tenants.sort((a, b) => String(a.slug).localeCompare(String(b.slug)));
  await writeFile(REGISTRY, JSON.stringify(data, null, 2) + "\n", "utf8");
  console.log("registry güncellendi:", REGISTRY, "tenant sayısı:", data.tenants.length);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
