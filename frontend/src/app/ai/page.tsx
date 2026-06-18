import DashboardLayout from "@/components/DashboardLayout";
import { fetchSummaries } from "@/lib/api";

async function getData() {
  try {
    return await fetchSummaries();
  } catch (e) {
    console.error("Failed to fetch summaries:", e);
    return { items: [] };
  }
}

export default async function AIContext() {
  const data = await getData();
  const summaries = data.items || [];

  // Group by asset
  const byAsset: Record<string, any[]> = {};
  summaries.forEach((s: any) => {
    const asset = String(s.asset || "UNKNOWN").toUpperCase();
    if (!byAsset[asset]) byAsset[asset] = [];
    byAsset[asset].push(s);
  });

  const assets = Object.keys(byAsset).sort();

  const assetColors: Record<string, string> = {
    BTC: "from-amber-500/10 to-amber-500/5 border-amber-500/20",
    SOL: "from-purple-500/10 to-purple-500/5 border-purple-500/20",
    DOT: "from-rose-500/10 to-rose-500/5 border-rose-500/20",
    BASE: "from-blue-500/10 to-blue-500/5 border-blue-500/20",
  };

  const assetIcons: Record<string, string> = {
    BTC: "₿",
    SOL: "◎",
    DOT: "●",
    BASE: "◆",
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">AI Context</h2>
          <p className="text-sm text-slate-400">
            Oracle-stored model summaries designed to turn raw tables into operator-readable market context.
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {assets.map((asset) => {
            const latest = byAsset[asset][0];
            return (
              <div 
                key={asset}
                className={`rounded-2xl border bg-gradient-to-b p-4 ${assetColors[asset] || "from-white/[0.03] to-white/[0.01] border-white/5"}`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{assetIcons[asset] || "◆"}</span>
                  <span className="text-xs font-bold text-slate-400">{asset}</span>
                </div>
                <p className="text-xs text-slate-500">Last updated</p>
                <p className="text-sm text-slate-300">{String(latest?.timestamp || "Never").slice(0, 16)}</p>
              </div>
            );
          })}
          {assets.length === 0 && (
            <div className="col-span-full rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
              <p className="text-xs text-slate-500">No AI summaries available</p>
            </div>
          )}
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {assets.map((asset) => {
            const latest = byAsset[asset][0];
            const colorClass = assetColors[asset] || "from-white/[0.03] to-white/[0.01] border-white/5";
            return (
              <div 
                key={asset}
                className={`rounded-2xl border bg-gradient-to-b p-5 ${colorClass}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{assetIcons[asset] || "◆"}</span>
                    <h3 className="text-lg font-bold text-white">{asset} Summary</h3>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    {String(latest?.timestamp || "").slice(0, 16)}
                  </span>
                </div>
                <div className="prose prose-invert prose-sm max-w-none">
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {latest?.summary || "No summary available for this asset."}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Raw Summary Table (for debugging/verification) */}
        {summaries.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">All Summaries</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Asset</th>
                    <th className="text-left py-2 px-2">Timestamp</th>
                    <th className="text-left py-2 px-2">Summary Preview</th>
                  </tr>
                </thead>
                <tbody>
                  {summaries.map((s: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          assetColors[String(s.asset).toUpperCase()]?.includes("amber") ? "bg-amber-500/10 text-amber-400" :
                          assetColors[String(s.asset).toUpperCase()]?.includes("purple") ? "bg-purple-500/10 text-purple-400" :
                          assetColors[String(s.asset).toUpperCase()]?.includes("rose") ? "bg-rose-500/10 text-rose-400" :
                          assetColors[String(s.asset).toUpperCase()]?.includes("blue") ? "bg-blue-500/10 text-blue-400" :
                          "bg-white/5 text-slate-400"
                        }`}>
                          {String(s.asset).toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(s.timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2 text-slate-300 max-w-md truncate">
                        {String(s.summary || "").slice(0, 80)}...
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
