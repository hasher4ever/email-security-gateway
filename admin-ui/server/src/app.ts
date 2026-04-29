import express, { type Express } from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Querier } from "./db.js";
import { quarantineRouter } from "./routes/quarantine.js";
import { simRouter } from "./routes/sim.js";

export function buildApp(db: Querier, opts: { staticDir?: string } = {}): Express {
  const app = express();

  app.get("/healthz", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.use("/api/quarantine", quarantineRouter(db));
  app.use("/api/sim", simRouter(db));

  if (opts.staticDir) {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const staticAbs = path.resolve(here, opts.staticDir);
    app.use(express.static(staticAbs));
    app.get("*", (req, res, next) => {
      if (req.path.startsWith("/api") || req.path === "/healthz") return next();
      res.sendFile(path.join(staticAbs, "index.html"));
    });
  }

  return app;
}
