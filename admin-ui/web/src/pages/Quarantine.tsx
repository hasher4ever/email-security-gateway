import { useEffect, useState, Fragment } from "react";
import { fetchQuarantine, type QuarantineRow } from "../lib/api";

const PAGE_SIZE = 50;

export default function Quarantine() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ rows: QuarantineRow[]; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetchQuarantine(page, PAGE_SIZE)
      .then((d) => setData({ rows: d.rows, total: d.total }))
      .catch((e) => setError(String(e)));
  }, [page]);

  if (error) return <div className="empty">Error: {error}</div>;
  if (!data) return <div className="empty">Loading…</div>;

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div>
      <h1>Quarantine review</h1>
      {data.rows.length === 0 ? (
        <div className="empty">No flagged or quarantined mail.</div>
      ) : (
        <table data-testid="quarantine-table">
          <thead>
            <tr>
              <th>Received</th>
              <th>Sender</th>
              <th>Subject</th>
              <th>Score</th>
              <th>Verdict</th>
              <th>Matched rules</th>
              <th>URLs</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <Fragment key={row.id}>
                <tr
                  className="row"
                  data-testid="quarantine-row"
                  onClick={() => setExpandedId(expandedId === row.id ? null : row.id)}
                >
                  <td>{formatDate(row.received_at)}</td>
                  <td>{row.sender ?? <span className="muted">—</span>}</td>
                  <td>{row.subject ?? <span className="muted">(no subject)</span>}</td>
                  <td>{row.score ?? "—"}</td>
                  <td className={`verdict ${row.verdict}`}>{row.verdict}</td>
                  <td>{(row.matched_rules ?? []).join(", ")}</td>
                  <td>
                    <span className="tooltip" title={(row.urls ?? []).join("\n")}>
                      {(row.urls ?? []).length}
                    </span>
                  </td>
                </tr>
                {expandedId === row.id && (
                  <tr>
                    <td colSpan={7} className="drawer" data-testid="quarantine-drawer">
                      <h3>Raw headers</h3>
                      <pre>{row.raw_headers ?? "(none)"}</pre>
                      <h3>URLs</h3>
                      <pre>{(row.urls ?? []).join("\n") || "(none)"}</pre>
                      <h3>Attachments</h3>
                      <pre>{JSON.stringify(row.attachments ?? [], null, 2)}</pre>
                      <h3>Detonator calls</h3>
                      <pre>{JSON.stringify(row.detonator_calls ?? [], null, 2)}</pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
      <div className="pagination">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
          Prev
        </button>
        <span>
          Page {page} / {totalPages} ({data.total} rows)
        </span>
        <button onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages}>
          Next
        </button>
      </div>
    </div>
  );
}

function formatDate(s: string): string {
  if (!s) return "—";
  try {
    return new Date(s).toISOString().replace("T", " ").slice(0, 19) + "Z";
  } catch {
    return s;
  }
}
