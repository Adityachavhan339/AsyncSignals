import DashboardLayout from "@/components/DashboardLayout";
import { fetchBase, fmtUsd, fmtNum, shortAddr } from "@/lib/api";

async function getData() {
  try {
    return await fetchBase();
  } catch (e) {
    console.error("Failed to fetch base:", e);
    return { items: {} };
  }
}

export default async function BaseL2Page() {
  const data = await getData();
  const base = data.items || {};

  const rpc = base.rpc_snapshot?.[0] || {};
  const activity = base.chain_activity?.[0] || {};
  const ecosystem = base.ecosystem?.[0] || {};
  const transfers = base.transfers || [];
  const derived = base.derived_signals || [];

  const totalWhaleUsd = transfers.reduce((sum: number, t: any) => sum + (Number(t.value_usd) || 0), 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Base L2 Telemetry</h2>
          <p className="text-sm text-slate-400">
            Base chain activity, whale transfers, gas pressure, and derived signals from Oracle-backed ingestion.
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-white/[0.03] to-white/[0.01] p-4">
            <p className="text-xs text-slate-500 mb-1">Latest Block</p>
            <p className="text-xl font-bold text-white">{fmtNum(rpc.latest_block_number)}</p>
            <p className="text-xs text-slate-400">Gas: {fmtNum(rpc.gas_used_total)}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-indigo-500/10 to-indigo-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">TPS (1m)</p>
            <p className="text-xl font-bold text-indigo-400">{Number(rpc.tps_1min || 0).toFixed(1)}</p>
            <p className="text-xs text-indigo-400/70">Sequencer throughput</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-blue-500/10 to-blue-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Whale Flow</p>
            <p className="text-xl font-bold text-blue-400">{fmtUsd(totalWhaleUsd)}</p>
            <p className="text-xs text-blue-400/70">{transfers.length} transfers</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Derived Signals</p>
            <p className="text-xl font-bold text-emerald-400">{derived.length}</p>
            <p className="text-xs text-emerald-400/70">Active intelligence</p>
          </div>
        </div>

        {/* Chain Activity */}
        {activity.activity_date && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Chain Activity</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Transactions</p>
                <p className="text-lg font-bold text-white">{fmtNum(activity.tx_count)}</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">TPS</p>
                <p className="text-lg font-bold text-white">{Number(activity.tps || 0).toFixed(3)}</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Fees USD</p>
                <p className="text-lg font-bold text-white">{fmtUsd(activity.total_fees_usd)}</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Activity Score</p>
                <p className={`text-lg font-bold ${
                  Number(activity.activity_score || 0) >= 400 ? "text-rose-400" :
                  Number(activity.activity_score || 0) >= 200 ? "text-amber-400" : "text-emerald-400"
                }`}>
                  {Number(activity.activity_score || 0).toFixed(1)}
                </p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded-full ${
                activity.alert_level === "high" ? "bg-rose-500/10 text-rose-400" :
                activity.alert_level === "medium" ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
              }`}>
                {activity.alert_level?.toUpperCase()} ALERT
              </span>
            </div>
          </div>
        )}

        {/* RPC Snapshot */}
        {rpc.captured_at && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">RPC Snapshot</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <div>
                <p className="text-slate-500 mb-1">Block Time</p>
                <p className="text-slate-300">{Number(rpc.avg_block_time_seconds || 0).toFixed(1)}s</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">Base Fee</p>
                <p className="text-slate-300">{Number(rpc.base_fee_gwei || 0).toFixed(4)} gwei</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">Captured</p>
                <p className="text-slate-300">{String(rpc.captured_at).slice(0, 16)}</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">Block Hash</p>
                <p className="text-slate-300 font-mono">{shortAddr(rpc.latest_block_hash)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Whale Transfers */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4">Base Whale Transfers</h3>
          {transfers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Asset</th>
                    <th className="text-right py-2 px-2">USD</th>
                    <th className="text-left py-2 px-2">From</th>
                    <th className="text-left py-2 px-2">To</th>
                    <th className="text-left py-2 px-2">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.slice(0, 30).map((t: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(t.timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 text-blue-400">
                          {String(t.asset_symbol || "?").toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-white font-medium">
                        {fmtUsd(t.value_usd)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">{shortAddr(t.from_address)}</td>
                      <td className="py-2 px-2 text-slate-400 font-mono">{shortAddr(t.to_address)}</td>
                      <td className="py-2 px-2 text-slate-500">{t.transfer_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No Base whale transfers available</p>
          )}
        </div>

        {/* Derived Signals */}
        {derived.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Derived Signals</h3>
            <div className="space-y-3">
              {derived.slice(0, 10).map((d: any, i: number) => (
                <div 
                  key={i} 
                  className="p-3 rounded-lg border-l-4 bg-white/[0.02] border-white/[0.04]"
                  style={{ 
                    borderLeftColor: d.severity === "high" ? "#ff6b7a" : 
                                    d.severity === "medium" ? "#ffb84d" : "#14f195" 
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-white">{d.title}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      d.severity === "high" ? "bg-rose-500/10 text-rose-400" :
                      d.severity === "medium" ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
                    }`}>
                      {d.severity?.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{d.description}</p>
                  <p className="text-[10px] text-slate-600">
                    {d.signal_family} | Score: {d.score} | Ref: {shortAddr(d.reference_id)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
