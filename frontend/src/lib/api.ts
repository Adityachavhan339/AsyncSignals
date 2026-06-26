const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.asyncsignals.tech";

export async function fetchBundle() {
  const res = await fetch(`${API_URL}/bundle`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchMarket(limit = 25) {
  const res = await fetch(`${API_URL}/market?limit=${limit}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchWhales(limit = 50) {
  const res = await fetch(`${API_URL}/whales?limit=${limit}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSummaries() {
  const res = await fetch(`${API_URL}/summaries`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSignals(limit = 20) {
  const res = await fetch(`${API_URL}/signals?limit=${limit}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchPolkadot() {
  const res = await fetch(`${API_URL}/polkadot`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchBase() {
  const res = await fetch(`${API_URL}/base`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSpot() {
  const res = await fetch(`${API_URL}/spot`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── BNB Chain endpoints ──
export async function fetchBnb(whaleLimit = 50, poolLimit = 50, derivedLimit = 25) {
  const res = await fetch(
    `${API_URL}/bnb?whale_limit=${whaleLimit}&pool_limit=${poolLimit}&derived_limit=${derivedLimit}`,
    { next: { revalidate: 60 } }
  );
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Sui endpoints ──
export async function fetchSuiWhales(limit = 50, protocol?: string) {
  const url = new URL(`${API_URL}/sui/whale-transfers`);
  url.searchParams.set("limit", String(limit));
  if (protocol) url.searchParams.set("protocol", protocol);
  const res = await fetch(url.toString(), { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSuiTopWhales(limit = 50, window = "7d") {
  const res = await fetch(`${API_URL}/sui/top-whales?limit=${limit}&window=${window}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSuiProtocolExposure() {
  const res = await fetch(`${API_URL}/sui/protocol-exposure`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSuiSummary() {
  const res = await fetch(`${API_URL}/sui/summary`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── NodeOps endpoints ──
export async function fetchNodeOpsMetrics(nodeId?: string, window = 24, limit = 100) {
  const url = new URL(`${API_URL}/api/v1/nodeops/metrics`);
  if (nodeId) url.searchParams.set("node_id", nodeId);
  url.searchParams.set("window", String(window));
  url.searchParams.set("limit", String(limit));
  const res = await fetch(url.toString(), { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchNodeOpsHealth() {
  const res = await fetch(`${API_URL}/api/v1/nodeops/health`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function postNodeOpsTelemetry(payload: Record<string, any>) {
  const res = await fetch(`${API_URL}/api/v1/nodeops/telemetry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Solana endpoints ──
export async function fetchSol(whaleLimit = 50) {
  const res = await fetch(`${API_URL}/sol?whale_limit=${whaleLimit}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSolWhales(limit = 50, minUsd = 10000, protocol?: string, tier?: string) {
  const url = new URL(`${API_URL}/sol/whales`);
  url.searchParams.set("limit", String(limit));
  url.searchParams.set("min_usd", String(minUsd));
  if (protocol) url.searchParams.set("protocol", protocol);
  if (tier && tier !== "all") url.searchParams.set("tier", tier);
  const res = await fetch(url.toString(), { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchSolIntelligence() {
  const res = await fetch(`${API_URL}/sol/intelligence`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Utilities ──
export function fmtUsd(value: number | null | undefined): string {
  if (value == null) return "n/a";
  const num = Number(value);
  if (Math.abs(num) >= 1_000_000_000) return `$${(num / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(num) >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
  if (Math.abs(num) >= 1_000) return `$${(num / 1_000).toFixed(2)}K`;
  return `$${num.toFixed(2)}`;
}

export function fmtNum(value: number | null | undefined): string {
  if (value == null) return "--";
  const num = Number(value);
  if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
  if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(2)}K`;
  return `${num.toFixed(0)}`;
}

export function shortAddr(value: string | null | undefined): string {
  if (!value) return "-";
  if (value.length <= 14) return value;
  return `${value.slice(0, 6)}...${value.slice(-6)}`;
}
