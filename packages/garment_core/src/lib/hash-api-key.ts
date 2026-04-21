import { createHash } from "node:crypto";

export function hashApiKey(rawKey: string, pepper: string): string {
  return createHash("sha256")
    .update(`${pepper}\n${rawKey}`, "utf8")
    .digest("hex");
}
