import { Router } from "express";
import type { Querier } from "../db.js";

type Row = {
  id: string;
  name: string;
  audience: string | null;
  sent_at: string | null;
  sent: string;
  opened: string;
  clicked: string;
  submitted: string;
  reported: string;
};

export function simRouter(db: Querier): Router {
  const r = Router();

  r.get("/", async (_req, res) => {
    try {
      const result = await db.query<Row>(
        `SELECT c.id,
                c.name,
                c.audience,
                c.sent_at,
                COUNT(*) FILTER (WHERE e.event_type = 'sent')::text      AS sent,
                COUNT(*) FILTER (WHERE e.event_type = 'opened')::text    AS opened,
                COUNT(*) FILTER (WHERE e.event_type = 'clicked')::text   AS clicked,
                COUNT(*) FILTER (WHERE e.event_type = 'submitted')::text AS submitted,
                COUNT(*) FILTER (WHERE e.event_type = 'reported')::text  AS reported
           FROM sim_campaign c
           LEFT JOIN sim_event e ON e.campaign_id = c.id
          GROUP BY c.id, c.name, c.audience, c.sent_at
          ORDER BY c.sent_at DESC NULLS LAST`,
      );

      const campaigns = result.rows.map((row) => {
        const sent = Number(row.sent);
        const clicked = Number(row.clicked);
        const click_rate = sent > 0 ? Math.round((clicked / sent) * 1000) / 10 : 0;
        return {
          id: row.id,
          name: row.name,
          audience: row.audience,
          sent_at: row.sent_at,
          sent,
          opened: Number(row.opened),
          clicked,
          submitted: Number(row.submitted),
          reported: Number(row.reported),
          click_rate,
        };
      });

      res.json({ campaigns });
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  });

  return r;
}
