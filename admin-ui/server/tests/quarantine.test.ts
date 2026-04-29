import { describe, it, expect } from "vitest";
import request from "supertest";
import { buildApp } from "../src/app.js";

type Call = { text: string; params?: unknown[] };

function makeDb(rows: any[], total = rows.length) {
  const calls: Call[] = [];
  const db = {
    query: async <T = unknown>(text: string, params?: unknown[]) => {
      calls.push({ text, params });
      if (text.includes("COUNT(*)")) {
        return { rows: [{ count: String(total) }] as unknown as T[] };
      }
      return { rows: rows as unknown as T[] };
    },
  };
  return { db, calls };
}

describe("/api/quarantine", () => {
  it("filters to shadow_flag and quarantine verdicts only", async () => {
    const { db, calls } = makeDb([]);
    await request(buildApp(db)).get("/api/quarantine");
    const sql = calls.map((c) => c.text).join("\n");
    expect(sql).toMatch(/verdict IN \('shadow_flag', 'quarantine'\)/);
  });

  it("paginates with default 50/page", async () => {
    const { db, calls } = makeDb([{ id: "a" }], 137);
    const res = await request(buildApp(db)).get("/api/quarantine");
    expect(res.status).toBe(200);
    expect(res.body.page).toBe(1);
    expect(res.body.pageSize).toBe(50);
    expect(res.body.total).toBe(137);
    const dataCall = calls.find((c) => !c.text.includes("COUNT(*)"));
    expect(dataCall?.params).toEqual([50, 0]);
  });

  it("computes offset from page param", async () => {
    const { db, calls } = makeDb([], 0);
    await request(buildApp(db)).get("/api/quarantine?page=3&pageSize=20");
    const dataCall = calls.find((c) => !c.text.includes("COUNT(*)"));
    expect(dataCall?.params).toEqual([20, 40]);
  });

  it("caps pageSize at 200", async () => {
    const { db, calls } = makeDb([], 0);
    await request(buildApp(db)).get("/api/quarantine?pageSize=9999");
    const dataCall = calls.find((c) => !c.text.includes("COUNT(*)"));
    expect(dataCall?.params).toEqual([200, 0]);
  });

  it("clamps invalid page to 1", async () => {
    const { db, calls } = makeDb([], 0);
    await request(buildApp(db)).get("/api/quarantine?page=-5");
    const dataCall = calls.find((c) => !c.text.includes("COUNT(*)"));
    expect(dataCall?.params?.[1]).toBe(0);
  });
});
