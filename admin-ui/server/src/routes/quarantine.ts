import { Router } from "express";
import type { Querier } from "../db.js";

const MAX_PAGE_SIZE = 200;
const DEFAULT_PAGE_SIZE = 50;

export function quarantineRouter(db: Querier): Router {
  const r = Router();

  r.get("/", async (req, res) => {
    const page = Math.max(1, parseInt(String(req.query.page ?? "1"), 10) || 1);
    const rawSize = parseInt(String(req.query.pageSize ?? DEFAULT_PAGE_SIZE), 10) || DEFAULT_PAGE_SIZE;
    const pageSize = Math.min(MAX_PAGE_SIZE, Math.max(1, rawSize));
    const offset = (page - 1) * pageSize;

    try {
      const totalRes = await db.query<{ count: string }>(
        `SELECT COUNT(*)::text AS count
           FROM mail_audit
          WHERE verdict IN ('shadow_flag', 'quarantine')`,
      );
      const total = Number(totalRes.rows[0]?.count ?? 0);

      const rowsRes = await db.query(
        `SELECT id, received_at, sender, sender_domain, subject, score, verdict,
                matched_rules, urls, attachments, detonator_calls, raw_headers
           FROM mail_audit
          WHERE verdict IN ('shadow_flag', 'quarantine')
          ORDER BY received_at DESC
          LIMIT $1 OFFSET $2`,
        [pageSize, offset],
      );

      res.json({ rows: rowsRes.rows, total, page, pageSize });
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  });

  return r;
}
