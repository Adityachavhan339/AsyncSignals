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
