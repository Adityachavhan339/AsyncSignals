import DashboardLayout from "@/components/DashboardLayout";
import { fetchMarket, fmtUsd } from "@/lib/api";

async function getData() {
  try {
    return await fetchMarket(50);
  } catch (e) {
    console.error("Failed to fetch market:", e);
    return { items: [] };
  }
}

export default async function MarketSurface() {
  const data = await getData();
  const market = data.items || [];

  // Top 12 by market cap for chart
  const topCaps = [...market]
    .sort((a: any, b: any) => (Number(b.market_cap) || 0) - (Number(a.market_cap) || 0))
    .slice(0, 12);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Market Surface</h2>
          <p className="text-sm text-slate-400">
            High-level spot and market-cap reference table, useful for quick price verification and macro checks.
          </p>
        </div>

        {/* Market Table */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4">Market Data</h3>
          {market.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">#</th>
                    <th className="text-left py-2 px-2">Symbol</th>
                    <th className="text-right py-2 px-2">Price</th>
                    <th className="text-right py-2 px-2">Market Cap</th>
                    <th className="text-right py-2 px-2">24h Change</th>
                  </tr>
                </thead>
                <tbody>
                  {market.map((p: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-500">{i + 1}</td>
                      <td className="py-2 px-2">
                        <span className="font-bold text-white">{String(p.symbol).toUpperCase()}</span>
                      </td>
                      <td className="py-2 px-2 text-right text-slate-300 font-mono">
                        {fmtUsd(p.current_price)}
                      </td>
                      <td className="py-2 px-2 text-right text-slate-400 font-mono">
                        {fmtUsd(p.market_cap)}
                      </td>
                      <td className={`py-2 px-2 text-right font-medium ${
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
            <p className="text-xs text-slate-500">No market rows available</p>
          )}
        </div>

        {/* Top Market Caps */}
        {topCaps.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Top 12 by Market Cap</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {topCaps.map((p: any, i: number) => (
                <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-white">{String(p.symbol).toUpperCase()}</span>
                    <span className={`text-[10px] ${
                      Number(p.price_change_percentage_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}>
                      {Number(p.price_change_percentage_24h || 0).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{fmtUsd(p.market_cap)}</p>
                  <p className="text-xs text-slate-500">{fmtUsd(p.current_price)}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
