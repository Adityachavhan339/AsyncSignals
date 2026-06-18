import DashboardLayout from "@/components/DashboardLayout";
import { fetchWhales, fmtUsd, fmtNum, shortAddr } from "@/lib/api";

async function getData() {
  try {
    return await fetchWhales(100);
  } catch (e) {
    console.error("Failed to fetch whales:", e);
    return { items: [] };
  }
}

export default async function WhaleTracker() {
  const data = await getData();
  const whales = data.items || [];

  // Split by asset type
  const solWhales = whales.filter((w: any) => String(w.asset).toUpperCase() === "SOL");
  const ethWhales = whales.filter((w: any) => ["ETH", "WETH"].includes(String(w.asset).toUpperCase()));
  const btcWhales = whales.filter((w: any) => ["BTC", "WBTC"].includes(String(w.asset).toUpperCase()));
  const otherWhales = whales.filter((w: any) => {
    const a = String(w.asset).toUpperCase();
    return !["SOL", "ETH", "WETH", "BTC", "WBTC"].includes(a);
  });

  const totalUsd = whales.reduce((sum: number, w: any) => sum + (Number(w.raw_qty) || 0), 0);
  const solUsd = solWhales.reduce((sum: number, w: any) => sum + (Number(w.raw_qty) || 0), 0);
  const ethUsd = ethWhales.reduce((sum: number, w: any) => sum + (Number(w.raw_qty) || 0), 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Whale Tracker</h2>
          <p className="text-sm text-slate-400">
            Raw token amount in <span className="font-mono text-slate-300">amount</span>. 
            USD-converted value in <span className="font-mono text-slate-300">raw_qty</span>.
          </p>
        </div>

        {/* Summary KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-white/[0.03] to-white/[0.01] p-4">
            <p className="text-xs text-slate-500 mb-1">Total Tracked</p>
            <p className="text-xl font-bold text-white">{fmtUsd(totalUsd)}</p>
            <p className="text-xs text-slate-400">{whales.length} transfers</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">SOL Flow</p>
            <p className="text-xl font-bold text-emerald-400">{fmtUsd(solUsd)}</p>
            <p className="text-xs text-emerald-400/70">{solWhales.length} transfers</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-purple-500/10 to-purple-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">ETH Flow</p>
            <p className="text-xl font-bold text-purple-400">{fmtUsd(ethUsd)}</p>
            <p className="text-xs text-purple-400/70">{ethWhales.length} transfers</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-amber-500/10 to-amber-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Other Assets</p>
            <p className="text-xl font-bold text-amber-400">{otherWhales.length}</p>
            <p className="text-xs text-amber-400/70">Mixed tokens</p>
          </div>
        </div>

        {/* All Whales Table */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white">Cross-Chain Whale Flow</h3>
            <span className="text-xs text-slate-500">{whales.length} rows</span>
          </div>
          
          {whales.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Asset</th>
                    <th className="text-right py-2 px-2">Amount</th>
                    <th className="text-right py-2 px-2">USD Value</th>
                    <th className="text-left py-2 px-2">From</th>
                    <th className="text-left py-2 px-2">To</th>
                  </tr>
                </thead>
                <tbody>
                  {whales.slice(0, 50).map((w: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(w.time || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          String(w.asset).toUpperCase() === "SOL" ? "bg-emerald-500/10 text-emerald-400" :
                          ["ETH", "WETH"].includes(String(w.asset).toUpperCase()) ? "bg-purple-500/10 text-purple-400" :
                          ["BTC", "WBTC"].includes(String(w.asset).toUpperCase()) ? "bg-amber-500/10 text-amber-400" :
                          "bg-blue-500/10 text-blue-400"
                        }`}>
                          {String(w.asset).toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-slate-300 font-mono">
                        {Number(w.amount || 0).toFixed(6)}
                      </td>
                      <td className="py-2 px-2 text-right text-white font-medium">
                        {fmtUsd(w.raw_qty)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">
                        {shortAddr(w.from_address)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">
                        {shortAddr(w.to_address)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No whale data available</p>
          )}
        </div>

        {/* SOL Spotlight */}
        {solWhales.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/5 to-transparent p-4">
            <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              SOL Spotlight
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-right py-2 px-2">SOL Amount</th>
                    <th className="text-right py-2 px-2">USD Value</th>
                    <th className="text-left py-2 px-2">From</th>
                    <th className="text-left py-2 px-2">To</th>
                  </tr>
                </thead>
                <tbody>
                  {solWhales.slice(0, 20).map((w: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400">{String(w.time || "").slice(0, 16)}</td>
                      <td className="py-2 px-2 text-right text-emerald-400 font-mono">
                        {Number(w.amount || 0).toFixed(6)}
                      </td>
                      <td className="py-2 px-2 text-right text-white font-medium">
                        {fmtUsd(w.raw_qty)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">{shortAddr(w.from_address)}</td>
                      <td className="py-2 px-2 text-slate-400 font-mono">{shortAddr(w.to_address)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Asset Distribution */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-3">Asset Distribution</h3>
          <div className="flex flex-wrap gap-2">
            {[
              { label: "SOL", count: solWhales.length, color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
              { label: "ETH", count: ethWhales.length, color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
              { label: "BTC", count: btcWhales.length, color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
              { label: "Other", count: otherWhales.length, color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
            ].map((item) => (
              <div key={item.label} className={`px-3 py-2 rounded-xl border ${item.color}`}>
                <p className="text-xs font-bold">{item.label}</p>
                <p className="text-[10px] opacity-70">{item.count} transfers</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
