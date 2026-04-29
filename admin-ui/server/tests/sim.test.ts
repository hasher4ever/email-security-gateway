import { describe, it, expect } from "vitest";
import request from "supertest";
import { buildApp } from "../src/app.js";

function dbReturning(rows: any[]) {
  return { query: async () => ({ rows }) };
}

describe("/api/sim", () => {
  it("aggregates counts and computes click rate", async () => {
    const db = dbReturning([
      {
        id: "c1",
        name: "Dispatcher rate offer",
        audience: "dispatchers",
        sent_at: "2026-04-01T12:00:00Z",
        sent: "100",
        opened: "60",
        clicked: "25",
        submitted: "8",
        reported: "5",
      },
      {
        id: "c2",
        name: "ELD alert",
        audience: "drivers",
        sent_at: "2026-03-15T09:00:00Z",
        sent: "0",
        opened: "0",
        clicked: "0",
        submitted: "0",
        reported: "0",
      },
    ]);

    const res = await request(buildApp(db)).get("/api/sim");
    expect(res.status).toBe(200);
    const [c1, c2] = res.body.campaigns;
    expect(c1.sent).toBe(100);
    expect(c1.clicked).toBe(25);
    expect(c1.click_rate).toBe(25.0);
    expect(c1.opened).toBe(60);
    expect(c1.submitted).toBe(8);
    expect(c1.reported).toBe(5);

    expect(c2.sent).toBe(0);
    expect(c2.click_rate).toBe(0);
  });

  it("rounds click rate to one decimal", async () => {
    const db = dbReturning([
      {
        id: "c1",
        name: "x",
        audience: null,
        sent_at: null,
        sent: "3",
        opened: "1",
        clicked: "1",
        submitted: "0",
        reported: "0",
      },
    ]);
    const res = await request(buildApp(db)).get("/api/sim");
    expect(res.body.campaigns[0].click_rate).toBe(33.3);
  });
});
