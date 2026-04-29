import { test, expect } from "@playwright/test";

const stubRow = {
  id: "11111111-1111-1111-1111-111111111111",
  received_at: "2026-04-28T10:30:00.000Z",
  sender: "dispatch@hlghway.com",
  sender_domain: "hlghway.com",
  subject: "Rate confirmation #99812",
  score: 12.4,
  verdict: "shadow_flag",
  matched_rules: ["LOOKALIKE_SENDER", "PHISH_URL"],
  urls: ["https://hlghway.com/portal/login", "https://hlghway.com/track"],
  attachments: [{ filename: "rate.pdf", content_type: "application/pdf" }],
  detonator_calls: [{ url: "https://hlghway.com/portal/login", verdict: "phishing" }],
  raw_headers: "From: dispatch@hlghway.com\nSubject: Rate confirmation #99812\nReceived: by gw1",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/quarantine**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ rows: [stubRow], total: 1, page: 1, pageSize: 50 }),
    });
  });
});

test("renders the quarantine table with expected columns and a row", async ({ page }) => {
  await page.goto("/quarantine");

  const table = page.getByTestId("quarantine-table");
  await expect(table).toBeVisible();
  for (const header of ["Received", "Sender", "Subject", "Score", "Verdict", "Matched rules", "URLs"]) {
    await expect(table.locator("th", { hasText: header })).toBeVisible();
  }

  const rows = page.getByTestId("quarantine-row");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("hlghway.com");
  await expect(rows.first()).toContainText("LOOKALIKE_SENDER");
});

test("clicking a row reveals the drawer with raw_headers", async ({ page }) => {
  await page.goto("/quarantine");
  await page.getByTestId("quarantine-row").first().click();

  const drawer = page.getByTestId("quarantine-drawer");
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Raw headers");
  await expect(drawer).toContainText("dispatch@hlghway.com");
  await expect(drawer).toContainText("rate.pdf");
});
