import type { GarmentAuthContext } from "../services/api-key-service.js";

declare global {
  namespace Express {
    interface Request {
      garmentAuth?: GarmentAuthContext;
    }
  }
}

export {};
