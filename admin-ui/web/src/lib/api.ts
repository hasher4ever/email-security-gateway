export type Attachment = { filename?: string; content_type?: string; sha256?: string };

export type QuarantineRow = {
  id: string;
  received_at: string;
  sender: string | null;
  sender_domain: string | null;
  subject: string | null;
  score: string | number | null;
  verdict: string;
  matched_rules: string[] | null;
  urls: string[] | null;
  attachments: Attachment[] | null;
  detonator_calls: unknown[] | null;
  raw_headers: string | null;
};

export type QuarantineResponse = {
  rows: QuarantineRow[];
  total: number;
  page: number;
  pageSize: number;
};

export type SimCampaign = {
  id: string;
  name: string;
  audience: string | null;
  sent_at: string | null;
  sent: number;
  opened: number;
  clicked: number;
  submitted: number;
  reported: number;
  click_rate: number;
};

export type SimResponse = { campaigns: SimCampaign[] };

export async function fetchQuarantine(page: number, pageSize = 50): Promise<QuarantineResponse> {
  const r = await fetch(`/api/quarantine?page=${page}&pageSize=${pageSize}`);
  if (!r.ok) throw new Error(`quarantine: HTTP ${r.status}`);
  return r.json();
}

export async function fetchSim(): Promise<SimResponse> {
  const r = await fetch("/api/sim");
  if (!r.ok) throw new Error(`sim: HTTP ${r.status}`);
  return r.json();
}
