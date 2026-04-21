import { createHmac, timingSafeEqual } from "node:crypto";

/**
 * `X-Hub-Signature-256: sha256=<hex>` başlığını doğrular.
 * Secret boşsa doğrulama atlanır (geliştirme ortamı).
 */
export function verifyHubSignature(
  rawBody: Buffer,
  signatureHeader: string | undefined,
  secret: string,
): boolean {
  if (!secret) return true;
  if (!signatureHeader) return false;
  const prefix = "sha256=";
  if (!signatureHeader.startsWith(prefix)) return false;
  const received = Buffer.from(signatureHeader.slice(prefix.length), "hex");
  const expected = Buffer.from(
    createHmac("sha256", secret).update(rawBody).digest("hex"),
    "hex",
  );
  if (received.length !== expected.length) return false;
  return timingSafeEqual(received, expected);
}
