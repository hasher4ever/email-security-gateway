import { buildApp } from "./app.js";
import { buildPool } from "./db.js";

const port = Number(process.env.PORT ?? 5173);
const pool = buildPool();
const app = buildApp(pool, { staticDir: "../public" });

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`admin-ui listening on :${port}`);
});
