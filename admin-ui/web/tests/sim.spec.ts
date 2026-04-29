import { test, expect } from "@playwright/test";

const campaigns = [
  {
    id: "aaaa1111-1111-1111-1111-111111111111",
    name: "Dispatcher rate offer",
    audience: "dispatchers",
    sent_at: "2026-04-15T09:00:00.000Z",
    sent: 50,
    opened: 30,
    clicked: 12,
    submitted: 4,
    reported: 6,
    click_rate: 24.0,
  },
  {
    id: "bbbb2222-2222-2222-2222-222222222222",
    name: "ELD compliance alert",
    audience: "drivers",
    sent_at: "2026-03-10T09:00:00.000Z",
    sent: 80,
    opened: 40,
    clicked: 20,
    submitted: 5,
    reported: 10,
    click_rate: 25.0,
  },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/sim**", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ campaigns }),
    });
  });
});

test("renders campaign rows with computed click_rate", async ({ page }) => {
  await page.goto("/sim");

  const table = page.getByTestId("sim-table");
  await expect(table).toBeVisible();

  const rows = page.getByTestId("sim-row");
  await expect(rows).toHaveCount(2);

  await expect(rows.first()).toContainText("Dispatcher rate offer");
  await expect(rows.first()).toContainText("dispatchers");

  const rates = page.getByTestId("click-rate");
  await expect(rates.nth(0)).toHaveText("24%");
  await expect(rates.nth(1)).toHaveText("25%");
});
