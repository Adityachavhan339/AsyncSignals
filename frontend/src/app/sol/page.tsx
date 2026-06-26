import DashboardLayout from "@/components/DashboardLayout";
import { fetchSol, fmtUsd, fmtNum, shortAddr } from "@/lib/api";

async function getData() {
  try {
    return await fetchSol(100);
  } catch (e) {
    console.error("Failed to fetch Solana:", e);
    return { items: {} };
  }
}

function tierBadge(tier: string) {
  switch (tier?.toLowerCase()) {
    case "mega_whale":
      return "bg-rose-500/10 text-rose-400 border-rose-500/20";
    case "institutional":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    case "retail":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    default:
      return "bg-slate-500/10 text-slate-400 border-slate-500/20";
  }
}

function riskBadge(flag: string) {
  switch (flag?.toLowerCase()) {
    case "high_impact":
      return "bg-rose-500/10 text-rose-400";
    case "medium_impact":
      return "bg-amber-500/10 text-amber-400";
    default:
      return "bg-slate-500/10 text-slate-400";
  }
}

function impactColor(score: number) {
  if (score >= 70) return "text-rose-400";
  if (score >= 50) return "text-amber-400";
  if (score >= 30) return "text-yellow-400";
  return "text-emerald-400";
}

function liquidityLabel(level: string) {
  switch (level?.toLowerCase()) {
    case "extreme":
      return "text-rose-400 font-bold";
    case "high":
      return "text-amber-400";
    case "medium":
      return "text-yellow-400";
    default:
      return "text-emerald-400";
  }
}

function protocolColor(protocol: string) {
  const p = protocol?.toLowerCase() || "";
  if (p.includes("jupiter")) return "bg-orange-500/10 text-orange-400";
  if (p.includes("raydium")) return "bg-cyan-500/10 text-cyan-400";
  if (p.includes("orca")) return "bg-blue-500/10 text-blue-400";
  if (p.includes("pump")) return "bg-purple-500/10 text-purple-400";
  if (p.includes("meteora")) return "bg-pink-500/10 text-pink-400";
  if (p.includes("lifinity")) return "bg-indigo-500/10 text-indigo-400";
  if (p.includes("saros")) return "bg-teal-500/10 text-teal-400";
  if (p.includes("cropper")) return "bg-lime-500/10 text-lime-400";
  return "bg-white/5 text-slate-400";
}

function stressColor(index: number) {
  if (index >= 70) return "text-rose-400";
  if (index >= 40) return "text-amber-400";
  if (index >= 20) return "text-yellow-400";
  return "text-emerald-400";
}

function stressBg(index: number) {
  if (index >= 70) return "bg-rose-400";
  if (index >= 40) return "bg-amber-400";
  if (index >= 20) return "bg-yellow-400";
  return "bg-emerald-400";
}

export default async function SolanaPage() {
  const data = await getData();
  const sol = data.items || {};

  const whales = sol.whales || [];
  const intelligence = sol.market_intelligence || {};
  const protocols = sol.protocol_analytics || [];
  const summary = sol.summary || {};

  const megaCount = whales.filter((w: any) => w.from_tier === "mega_whale" || w.to_tier === "mega_whale").length;
  const highImpactCount = whales.filter((w: any) => (w.impact_score || 0) >= 70).length;
  const solVolume = whales
    .filter((w: any) => String(w.token).toUpperCase() === "SOL")
    .reduce((s: number, w: any) => s + (Number(w.usd_value) || 0), 0);
  const stableVolume = whales
    .filter((w: any) => ["USDC", "USDT"].includes(String(w.token).toUpperCase()))
    .reduce((s: number, w: any) => s + (Number(w.usd_value) || 0), 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Solana Institutional Intelligence</h2>
          <p className="text-sm text-slate-400">
            Helius-backed whale tracking with protocol identification, wallet tiering, market impact scoring, and liquidity pressure analysis.
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-purple-500/10 to-purple-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Total Whale Volume</p>
            <p className="text-xl font-bold text-purple-400">{fmtUsd(summary.total_whale_volume_usd || 0)}</p>
            <p className="text-xs text-purple-400/70">{whales.length} events tracked</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">SOL Volume</p>
            <p className="text-xl font-bold text-emerald-400">{fmtUsd(solVolume)}</p>
            <p className="text-xs text-emerald-400/70">Native token flow</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-blue-500/10 to-blue-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Stable Volume</p>
            <p className="text-xl font-bold text-blue-400">{fmtUsd(stableVolume)}</p>
            <p className="text-xs text-blue-400/70">USDC/USDT flow</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-rose-500/10 to-rose-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">High Impact Events</p>
            <p className="text-xl font-bold text-rose-400">{highImpactCount}</p>
            <p className="text-xs text-rose-400/70">{megaCount} mega-whales</p>
          </div>
        </div>

        {/* Market Intelligence + Protocol Dominance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Market Intelligence */}
          {intelligence.computed_at && (
            <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
              <h3 className="text-sm font-bold text-white mb-4">Market Intelligence</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-slate-500 mb-1">Market Stress</p>
                  <div className="flex items-center gap-2">
                    <span className={`text-lg font-bold ${stressColor(intelligence.market_stress_index || 0)}`}>
                      {intelligence.market_stress_index || 0}
                    </span>
                    <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${stressBg(intelligence.market_stress_index || 0)}`}
                        style={{ width: `${Math.min(100, (intelligence.market_stress_index || 0) * 1.5)}%` }}
                      />
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {intelligence.signal_label || "normal_flow"}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-slate-500 mb-1">Dominant Protocol</p>
                  <p className="text-sm font-bold text-white">{intelligence.dominant_protocol || "unknown"}</p>
                  <p className="text-[10px] text-slate-500 mt-1">
                    Top 5 concentration: {intelligence.top_5_concentration_pct || 0}%
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-slate-500 mb-1">Whale Count</p>
                  <p className="text-lg font-bold text-white">{intelligence.whale_count || 0}</p>
                  <p className="text-[10px] text-slate-500">
                    Mega: {intelligence.mega_whale_count || 0} | High Impact: {intelligence.high_impact_count || 0}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-slate-500 mb-1">Avg Impact Score</p>
                  <p className={`text-lg font-bold ${impactColor(intelligence.avg_impact_score || 0)}`}>
                    {(intelligence.avg_impact_score || 0).toFixed(1)}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    Computed {String(intelligence.computed_at).slice(0, 16)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Protocol Dominance */}
          {protocols.length > 0 && (
            <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
              <h3 className="text-sm font-bold text-white mb-4">Protocol Dominance</h3>
              <div className="space-y-3">
                {protocols.slice(0, 8).map((p: any, i: number) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="w-28 text-xs text-slate-400 truncate">{p.protocol}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-slate-500">
                          {p.tx_count} txs | avg {fmtUsd(p.avg_tx_size)}
                        </span>
                        <span className="text-xs font-bold text-emerald-400">
                          {fmtUsd(p.volume_usd_24h)}
                        </span>
                      </div>
                      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-purple-400"
                          style={{
                            width: `${Math.min(100, (p.volume_usd_24h / (protocols[0]?.volume_usd_24h || 1)) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Whale Events Table */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white">Institutional Whale Flows</h3>
            <span className="text-xs text-slate-500">
              Threshold: 50 SOL / $10K USD | Mega: 500 SOL / $100K
            </span>
          </div>

          {whales.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Asset</th>
                    <th className="text-right py-2 px-2">USD</th>
                    <th className="text-left py-2 px-2">From</th>
                    <th className="text-left py-2 px-2">To</th>
                    <th className="text-left py-2 px-2">Protocol</th>
                    <th className="text-left py-2 px-2">Tier</th>
                    <th className="text-right py-2 px-2">Impact</th>
                    <th className="text-right py-2 px-2">Slippage</th>
                    <th className="text-left py-2 px-2">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {whales.slice(0, 50).map((w: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(w.event_timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                          String(w.token).toUpperCase() === "SOL"
                            ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                            : String(w.token).toUpperCase() === "USDC"
                            ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                            : String(w.token).toUpperCase() === "USDT"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-white/5 text-slate-400 border-white/10"
                        }`}>
                          {String(w.token || "?").toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-white font-medium">
                        {fmtUsd(w.usd_value)}
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-slate-300 font-mono">{shortAddr(w.from_address)}</span>
                          <span className={`text-[10px] px-1 py-0 rounded w-fit ${tierBadge(w.from_tier)}`}>
                            {w.from_tier}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-slate-300 font-mono">{shortAddr(w.to_address)}</span>
                          <span className={`text-[10px] px-1 py-0 rounded w-fit ${tierBadge(w.to_tier)}`}>
                            {w.to_tier}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${protocolColor(w.protocol)}`}>
                          {w.protocol || "unknown"}
                        </span>
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex gap-1">
                          <span className={`text-[10px] px-1 py-0 rounded ${tierBadge(w.from_tier)}`}>
                            {w.from_tier?.slice(0, 3)}
                          </span>
                          <span className="text-slate-600">→</span>
                          <span className={`text-[10px] px-1 py-0 rounded ${tierBadge(w.to_tier)}`}>
                            {w.to_tier?.slice(0, 3)}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 px-2 text-right">
                        <span className={`font-bold ${impactColor(w.impact_score || 0)}`}>
                          {w.impact_score || 0}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-slate-400">
                        {w.slippage_estimate ? `${w.slippage_estimate}%` : "—"}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${riskBadge(w.risk_flag)}`}>
                          {w.risk_flag || "none"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No Solana whale events available. Run sol.py to populate SOL_WHALE_EVENTS.</p>
          )}
        </div>

        {/* Bottom Row: Volume Breakdown + Top Flows */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Volume by Asset */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Volume by Asset</h3>
            {(() => {
              const byAsset: Record<string, number> = {};
              whales.forEach((w: any) => {
                const asset = String(w.token || "UNKNOWN").toUpperCase();
                byAsset[asset] = (byAsset[asset] || 0) + (Number(w.usd_value) || 0);
              });
              const sorted = Object.entries(byAsset).sort((a, b) => b[1] - a[1]);
              if (sorted.length === 0) return <p className="text-xs text-slate-500">No data</p>;
              return (
                <div className="space-y-3">
                  {sorted.map(([asset, vol]) => (
                    <div key={asset} className="flex items-center gap-4">
                      <div className="w-16 text-xs font-bold text-slate-300">{asset}</div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-slate-500">
                            {whales.filter((w: any) => String(w.token).toUpperCase() === asset).length} events
                          </span>
                          <span className="text-xs font-bold text-white">{fmtUsd(vol)}</span>
                        </div>
                        <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              asset === "SOL" ? "bg-purple-400" :
                              asset === "USDC" ? "bg-blue-400" :
                              asset === "USDT" ? "bg-emerald-400" :
                              "bg-slate-400"
                            }`}
                            style={{ width: `${Math.min(100, (vol / (sorted[0][1] || 1)) * 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Top 5 Mega Flows */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Top 5 Mega Flows</h3>
            {whales
              .filter((w: any) => (w.usd_value || 0) >= 100000)
              .sort((a: any, b: any) => (b.usd_value || 0) - (a.usd_value || 0))
              .slice(0, 5)
              .map((w: any, i: number) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] mb-2 last:mb-0">
                  <span className="text-lg">🚨</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-white">
                        {String(w.token).toUpperCase()} {fmtUsd(w.usd_value)}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${riskBadge(w.risk_flag)}`}>
                        {w.risk_flag || "none"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-500">
                      <span className="font-mono text-slate-400">{shortAddr(w.from_address)}</span>
                      <span>→</span>
                      <span className="font-mono text-slate-400">{shortAddr(w.to_address)}</span>
                      <span className="text-slate-600">|</span>
                      <span className={protocolColor(w.protocol)}>{w.protocol || "unknown"}</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className={`text-[10px] ${impactColor(w.impact_score || 0)}`}>
                        Impact: {w.impact_score || 0}
                      </span>
                      <span className={`text-[10px] ${liquidityLabel(w.liquidity_pressure)}`}>
                        Liquidity: {w.liquidity_pressure || "low"}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        Fee: {w.fee_sol ? `${w.fee_sol.toFixed(6)} SOL` : "—"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            {whales.filter((w: any) => (w.usd_value || 0) >= 100000).length === 0 && (
              <p className="text-xs text-slate-500">No mega-whale flows ($100K+) in current window</p>
            )}
          </div>
        </div>

        {/* Fee & Compute Analysis */}
        {whales.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Transaction Economics</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {(() => {
                const avgFee = whales.reduce((s: number, w: any) => s + (Number(w.fee_sol) || 0), 0) / whales.length;
                const avgCu = whales.reduce((s: number, w: any) => s + (Number(w.compute_units) || 0), 0) / whales.length;
                const maxFee = Math.max(...whales.map((w: any) => Number(w.fee_sol) || 0));
                const maxCu = Math.max(...whales.map((w: any) => Number(w.compute_units) || 0));
                return (
                  <>
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-xs text-slate-500 mb-1">Avg Fee</p>
                      <p className="text-lg font-bold text-white">{avgFee.toFixed(6)} SOL</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-xs text-slate-500 mb-1">Max Fee</p>
                      <p className="text-lg font-bold text-amber-400">{maxFee.toFixed(6)} SOL</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-xs text-slate-500 mb-1">Avg Compute Units</p>
                      <p className="text-lg font-bold text-white">{Math.round(avgCu).toLocaleString()}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-xs text-slate-500 mb-1">Max Compute Units</p>
                      <p className="text-lg font-bold text-rose-400">{Math.round(maxCu).toLocaleString()}</p>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
