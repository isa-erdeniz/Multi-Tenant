import type { NextFunction, Request, Response } from "express";
import type { GarmentCoreDb } from "../db/client.js";
import { resolveApiKey } from "../services/api-key-service.js";

function extractApiKey(req: Request): string | null {
  const auth = req.headers.authorization;
  if (typeof auth === "string" && auth.toLowerCase().startsWith("bearer ")) {
    return auth.slice(7).trim() || null;
  }
  const x = req.headers["x-api-key"];
  if (typeof x === "string") return x.trim() || null;
  if (Array.isArray(x)) return x[0]?.trim() || null;
  return null;
}

export function requireApiKey(db: GarmentCoreDb, pepper: string) {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      const raw = extractApiKey(req);
      if (!raw) {
        res.status(401).json({ error: "missing_api_key" });
        return;
      }
      const auth = await resolveApiKey(db, raw, pepper);
      if (!auth) {
        res.status(403).json({ error: "invalid_api_key" });
        return;
      }
      req.garmentAuth = auth;
      next();
    } catch (err) {
      next(err);
    }
  };
}
