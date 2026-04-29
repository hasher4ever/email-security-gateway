import { describe, it, expect } from "vitest";
import request from "supertest";
import { buildApp } from "../src/app.js";

const stubDb = { query: async () => ({ rows: [] }) };

describe("/healthz", () => {
  it("returns ok", async () => {
    const res = await request(buildApp(stubDb)).get("/healthz");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});
