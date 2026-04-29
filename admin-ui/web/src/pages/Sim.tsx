import { useEffect, useState } from "react";
import { fetchSim, type SimCampaign } from "../lib/api";

export default function Sim() {
  const [campaigns, setCampaigns] = useState<SimCampaign[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSim()
      .then((d) => setCampaigns(d.campaigns))
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="empty">Error: {error}</div>;
  if (!campaigns) return <div className="empty">Loading…</div>;
  if (campaigns.length === 0) return <div className="empty">No campaigns yet.</div>;

  return (
    <div>
      <h1>Sim metrics</h1>
      <table data-testid="sim-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Audience</th>
            <th>Sent at</th>
            <th>Sent</th>
            <th>Opened</th>
            <th>Clicked</th>
            <th>Submitted</th>
            <th>Reported</th>
            <th>Click rate</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr key={c.id} data-testid="sim-row">
              <td>{c.name}</td>
              <td>{c.audience ?? <span className="muted">—</span>}</td>
              <td>{c.sent_at ? new Date(c.sent_at).toISOString().slice(0, 10) : "—"}</td>
              <td>{c.sent}</td>
              <td>{c.opened}</td>
              <td>{c.clicked}</td>
              <td>{c.submitted}</td>
              <td>{c.reported}</td>
              <td data-testid="click-rate">{c.click_rate}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
