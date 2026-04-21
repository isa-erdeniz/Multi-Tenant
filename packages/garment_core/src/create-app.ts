import express, {
  Router,
  type NextFunction,
  type Request,
  type Response,
} from "express";
import { getEnv } from "./config/env.js";
import type { GarmentCoreDb } from "./db/client.js";
import { HttpError } from "./http/errors.js";
import { corsMiddleware } from "./middleware/cors.js";
import { requireApiKey } from "./middleware/require-api-key.js";
import { createV1Router } from "./routes/v1.js";
import { createWebhookRouter } from "./routes/webhook.js";

export function createApp(opts: { db: GarmentCoreDb | null; version: string }) {
  const env = getEnv();
  const app = express();
  app.disable("x-powered-by");

  if (opts.db) {
    (app.locals as { db?: GarmentCoreDb }).db = opts.db;
  }

  app.use(corsMiddleware(env.corsOrigins));

  // Ham gövdeyi HMAC doğrulaması için saklıyoruz; sadece webhook rotası kullanır.
  const rawBodyStore = new WeakMap<Request, Buffer>();
  app.use(
    express.json({
      limit: "1mb",
      verify: (req: Request, _res, buf) => {
        rawBodyStore.set(req, buf);
      },
    }),
  );

  app.get("/health", (_req: Request, res: Response) => {
    res.json({
      ok: true,
      service: "garment_core",
      database: Boolean(opts.db),
    });
  });

  app.get("/version", (_req: Request, res: Response) => {
    res.json({
      name: "garment_core",
      version: opts.version,
      node: process.version,
    });
  });

  const v1 = Router();
  v1.use((_req: Request, res: Response, next: NextFunction) => {
    if (!opts.db) {
      res.status(503).json({ error: "database_unconfigured" });
      return;
    }
    next();
  });
  if (opts.db) {
    v1.use(requireApiKey(opts.db, env.apiKeyPepper));
    v1.use(createV1Router(opts.db));
  }
  app.use("/v1", v1);

  if (opts.db) {
    app.use("/webhook", createWebhookRouter(opts.db, rawBodyStore));
  }

  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "not_found" });
  });

  app.use(
    (err: unknown, _req: Request, res: Response, _next: NextFunction) => {
      if (err instanceof HttpError) {
        res.status(err.status).json({ error: err.code, message: err.message });
        return;
      }
      console.error(err);
      res.status(500).json({ error: "internal_error" });
    },
  );

  return app;
}
