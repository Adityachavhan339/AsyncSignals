import DashboardLayout from "@/components/DashboardLayout";
import { fetchBundle, fmtUsd, fmtNum } from "@/lib/api";
import WhaleFlowChart from "@/components/charts/WhaleFlowChart";

async function getData() {
  try {
    return await fetchBundle();
  } catch (e) {
    console.error("Failed to fetch bundle:", e);
    return null;
  }
}

export default async function MissionControl() {
  const data = await getData();
  
  const highlights = data?.highlights || {};
  const market = data?.market || [];
  const whales = data?.whales || [];
  const signals = data?.signals || [];
  const summaries = data?.summaries || [];
  const polkadot = data?.polkadot || {};
  const base = data?.base || {};
  
  const priceMap: Record<string, any> = {};
  market.forEach((p: any) => {
    priceMap[String(p.symbol).toUpperCase()] = p;
  });
  
  const btc = priceMap["BTC"] || {};
  const eth = priceMap["ETH"] || {};
  const sol = priceMap["SOL"] || {};
  const dot = priceMap["DOT"] || {};
  
  const whaleChartData = whales.slice(0, 20).map((w: any, i: number) => ({
    name: `${String(w.asset || "?").slice(0, 3)} ${i + 1}`,
    usd: Number(w.raw_qty) || 0,
    asset: String(w.asset || "?").toUpperCase(),
  }));
  
  const latestSignal = signals[0] || null;
  
  // Check if chain data exists
  const hasPolkadot = polkadot.available && polkadot.chain_activity?.length > 0;
  const hasBase = base.available && base.chain_activity?.length > 0;
  
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Hero */}
        <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-gradient-to-br from-[#111c2b] to-[#071018] p-6 shadow-2xl">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.02] to-transparent" />
          <div className="relative">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold text-blue-400 tracking-widest uppercase">
                    ◆ AsyncSignals
                  </span>
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  Multi-chain telemetry infrastructure
                </h2>
                <p className="text-sm text-slate-400 max-w-xl">
                  Live feeds from Solana, EVM, Base L2, and Polkadot parachain ecosystems.
                  Oracle-backed ingestion with visual signal layers.
                </p>
              </div>
              <div className="flex gap-2">
                <span className="px-3 py-1.5 rounded-full text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Live Oracle Feed
                </span>
                <span className="px-3 py-1.5 rounded-full text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  Multi-Chain
                </span>
                <span className="px-3 py-1.5 rounded-full text-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  B2B Telemetry
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Latest Signal */}
        {latestSignal && (
          <div className="flex items-center gap-3 rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
            <span className="text-lg">
              {latestSignal.type?.includes("DANGER") ? "🚨" : 
               latestSignal.type?.includes("OPPORTUNITY") ? "🚀" : "🐋"}
            </span>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-bold ${
                latestSignal.type?.includes("DANGER") ? "text-rose-400" :
                latestSignal.type?.includes("OPPORTUNITY") ? "text-emerald-400" : "text-amber-400"
              }`}>
                {latestSignal.type}
              </div>
              <div className="text-xs text-slate-500 truncate">
                {String(latestSignal.msg || "").slice(0, 80)}...
              </div>
            </div>
            <span className="text-xs px-2 py-1 rounded-full bg-white/5 text-slate-400 whitespace-nowrap">
              {latestSignal.status || "Pending"}
            </span>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { 
              label: "BTC spot", 
              value: fmtUsd(btc.current_price), 
              delta: `${Number(btc.price_change_percentage_24h || 0) >= 0 ? "+" : ""}${Number(btc.price_change_percentage_24h || 0).toFixed(2)}%`,
              deltaColor: Number(btc.price_change_percentage_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
            },
            { 
              label: "ETH spot", 
              value: fmtUsd(eth.current_price), 
              delta: `${Number(eth.price_change_percentage_24h || 0) >= 0 ? "+" : ""}${Number(eth.price_change_percentage_24h || 0).toFixed(2)}%`,
              deltaColor: Number(eth.price_change_percentage_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
            },
            { 
              label: "SOL spot", 
              value: fmtUsd(sol.current_price), 
              delta: `${Number(sol.price_change_percentage_24h || 0) >= 0 ? "+" : ""}${Number(sol.price_change_percentage_24h || 0).toFixed(2)}%`,
              deltaColor: Number(sol.price_change_percentage_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
            },
            { 
              label: "DOT spot", 
              value: fmtUsd(dot.current_price) === "n/a" ? fmtUsd(dot.price) : fmtUsd(dot.current_price), 
              delta: dot.price_change_percentage_24h ? `${Number(dot.price_change_percentage_24h || 0) >= 0 ? "+" : ""}${Number(dot.price_change_percentage_24h || 0).toFixed(2)}%` : "n/a",
              deltaColor: Number(dot.price_change_percentage_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
            },
            { 
              label: "Base L2", 
              value: fmtUsd(base.items?.ecosystem?.[0]?.eth_price_usd) === "n/a" ? "Live" : fmtUsd(base.items?.ecosystem?.[0]?.eth_price_usd), 
              delta: `ETH on Base | ${fmtUsd(highlights.total_whale_usd || 0)} flow`,
              deltaColor: "text-slate-400"
            },
          ].map((kpi) => (
            <div
              key={kpi.label}
              className="relative overflow-hidden rounded-2xl border border-white/5 bg-gradient-to-b from-white/[0.03] to-white/[0.01] p-4 min-h-[132px]"
            >
              <div className="absolute -top-5 -right-5 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl" />
              <p className="text-xs text-slate-500 mb-1">{kpi.label}</p>
              <p className="text-xl font-bold text-white mb-1">{kpi.value}</p>
              <p className={`text-xs ${kpi.deltaColor}`}>{kpi.delta}</p>
            </div>
          ))}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Market Snapshot */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-3">Market snapshot</h3>
            {market.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-500 border-b border-white/5">
                      <th className="text-left py-2 px-2">Asset</th>
                      <th className="text-right py-2 px-2">Price</th>
                      <th className="text-right py-2 px-2">24h Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {market.slice(0, 8).map((p: any) => (
                      <tr key={p.symbol} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                        <td className="py-2 px-2 font-medium text-white">{String(p.symbol).toUpperCase()}</td>
                        <td className="py-2 px-2 text-right text-slate-300">{fmtUsd(p.current_price)}</td>
                        <td className={`py-2 px-2 text-right ${
                          Number(p.price_change_percentage_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                        }`}>
                          {Number(p.price_change_percentage_24h || 0).toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No market data available</p>
            )}
          </div>

          {/* Whale Flow Chart */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-3">Cross-chain whale flow</h3>
            <WhaleFlowChart data={whaleChartData} />
          </div>
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Signal History */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-3">Recent signal history</h3>
            {signals.length > 0 ? (
              <div className="overflow-x-auto max-h-[280px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-[#0d1722]">
                    <tr className="text-slate-500 border-b border-white/5">
                      <th className="text-left py-2 px-2">Time</th>
                      <th className="text-left py-2 px-2">Type</th>
                      <th className="text-left py-2 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signals.slice(0, 10).map((s: any, i: number) => (
                      <tr key={i} className="border-b border-white/[0.03]">
                        <td className="py-2 px-2 text-slate-400">{String(s.timestamp || "").slice(0, 16)}</td>
                        <td className="py-2 px-2 text-white truncate max-w-[120px]">{String(s.type || "").slice(0, 30)}</td>
                        <td className="py-2 px-2">
                          <span className={`text-xs ${
                            String(s.status).includes("Success") ? "text-emerald-400" :
                            String(s.status).includes("Failed") ? "text-rose-400" : "text-slate-400"
                          }`}>
                            {String(s.status || "Pending").slice(0, 20)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No signals yet</p>
            )}
          </div>

          {/* Data Status Panel (replaces chain pulse) */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-3">Ingestion Status</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-sm text-white">Core Ingestion</span>
                </div>
                <span className="text-xs text-emerald-400">Active (*/5 min)</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${hasPolkadot ? "bg-emerald-400" : "bg-amber-400"}`} />
                  <span className="text-sm text-white">Polkadot Worker</span>
                </div>
                <span className={`text-xs ${hasPolkadot ? "text-emerald-400" : "text-amber-400"}`}>
                  {hasPolkadot ? "Data fresh" : "Syncing (+2 min offset)"}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${hasBase ? "bg-emerald-400" : "bg-amber-400"}`} />
                  <span className="text-sm text-white">Base L2 Worker</span>
                </div>
                <span className={`text-xs ${hasBase ? "text-emerald-400" : "text-amber-400"}`}>
                  {hasBase ? "Data fresh" : "Syncing (+1 min offset)"}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-400" />
                  <span className="text-sm text-white">AI Summaries</span>
                </div>
                <span className="text-xs text-blue-400">Every 2 hours</span>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500">
                  Workers run on staggered schedules. Polkadot and Base data may appear 1-3 minutes after core ingestion. Check individual tabs for detailed telemetry.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Operator Brief */}
        <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-[#0d1722] to-[#09131c] p-4">
          <h3 className="text-sm font-bold text-white mb-2">Operator brief</h3>
          <p className="text-xs text-slate-400 mb-3 leading-relaxed">
            AsyncSignals ingests on-chain data from Solana, EVM, Base L2, and Polkadot ecosystems into Oracle-backed persistence.
            Use the Whale Tracker for flow inspection, the Polkadot tab for parachain telemetry, the Base L2 tab for L2 signals, and the Signal Ledger for execution history.
          </p>
          <p className="text-xs text-slate-600">
            Cross-chain flow: {fmtUsd(highlights.total_whale_usd || 0)} | 
            Signals: {signals.length} | 
            Prices: {market.length} | 
            Summaries: {summaries.length}
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
