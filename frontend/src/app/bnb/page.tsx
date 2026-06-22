import DashboardLayout from "@/components/DashboardLayout";
import { fetchBnb, fmtUsd, fmtNum, shortAddr } from "@/lib/api";

async function getData() {
  try {
    return await fetchBnb();
  } catch (e) {
    console.error("Failed to fetch BNB:", e);
    return { items: {} };
  }
}

export default async function BnbPage() {
  const data = await getData();
  const bnb = data.items || {};

  const rpc = bnb.rpc_snapshot?.[0] || {};
  const whales = bnb.whales || [];
  const pools = bnb.pools || [];
  const riskScores = bnb.risk_scores || [];
  const validators = bnb.validators || [];
  const gas = bnb.gas_forecast?.[0] || {};
  const derived = bnb.derived_signals || [];

  const totalWhaleUsd = whales.reduce((sum: number, w: any) => sum + (Number(w.value_usd) || 0), 0);
  const badValidators = validators.filter((v: any) => (v.missed_blocks_count || 0) > 5);
  const highRiskPools = pools.filter((p: any) => (p.risk_score || 0) >= 70);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">BNB Chain Telemetry</h2>
          <p className="text-sm text-slate-400">
            BNB Chain RPC snapshot, whale flow, PancakeSwap pools, validator health, gas forecasts, and yield risk scores.
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-white/[0.03] to-white/[0.01] p-4">
            <p className="text-xs text-slate-500 mb-1">Latest Block</p>
            <p className="text-xl font-bold text-white">{fmtNum(rpc.latest_block_number)}</p>
            <p className="text-xs text-slate-400">Gas: {fmtNum(rpc.gas_used_total)}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-yellow-500/10 to-yellow-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">TPS (1m)</p>
            <p className="text-xl font-bold text-yellow-400">{Number(rpc.tps_1min || 0).toFixed(1)}</p>
            <p className="text-xs text-yellow-400/70">BSC throughput</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-amber-500/10 to-amber-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Whale Flow</p>
            <p className="text-xl font-bold text-amber-400">{fmtUsd(totalWhaleUsd)}</p>
            <p className="text-xs text-amber-400/70">{whales.length} events</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Derived Signals</p>
            <p className="text-xl font-bold text-emerald-400">{derived.length}</p>
            <p className="text-xs text-emerald-400/70">Active intelligence</p>
          </div>
        </div>

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
                <p className="text-slate-500 mb-1">Gas Price</p>
                <p className="text-slate-300">{Number(rpc.gas_price_gwei || 0).toFixed(2)} gwei</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">TX Count</p>
                <p className="text-slate-300">{fmtNum(rpc.tx_count)}</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">Captured</p>
                <p className="text-slate-300">{String(rpc.captured_at).slice(0, 16)}</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">Validator</p>
                <p className="text-slate-300 font-mono">{shortAddr(rpc.validator_address)}</p>
              </div>
              <div>
                <p className="text-slate-500 mb-1">Block Hash</p>
                <p className="text-slate-300 font-mono">{shortAddr(rpc.latest_block_hash)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Gas Forecast */}
        {gas.forecast_at && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Gas Forecast</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Current</p>
                <p className="text-lg font-bold text-white">{Number(gas.current_gas_price_gwei || 0).toFixed(2)} gwei</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Avg (50 blocks)</p>
                <p className="text-lg font-bold text-slate-300">{Number(gas.avg_gas_50_blocks || 0).toFixed(2)} gwei</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Forecast (1h)</p>
                <p className="text-lg font-bold text-yellow-400">{Number(gas.forecast_1h_gwei || 0).toFixed(2)} gwei</p>
              </div>
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <p className="text-xs text-slate-500 mb-1">Congestion</p>
                <p className={`text-lg font-bold ${
                  gas.congestion_level === "high" ? "text-rose-400" :
                  gas.congestion_level === "medium" ? "text-amber-400" : "text-emerald-400"
                }`}>
                  {String(gas.congestion_level || "low").toUpperCase()}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Whale Events */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4">BNB Whale Events</h3>
          {whales.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Asset</th>
                    <th className="text-right py-2 px-2">USD</th>
                    <th className="text-right py-2 px-2">Raw</th>
                    <th className="text-left py-2 px-2">From</th>
                    <th className="text-left py-2 px-2">To</th>
                    <th className="text-left py-2 px-2">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {whales.slice(0, 30).map((w: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(w.timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-yellow-500/10 text-yellow-400">
                          {String(w.asset_symbol || "?").toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-white font-medium">
                        {fmtUsd(w.value_usd)}
                      </td>
                      <td className="py-2 px-2 text-right text-slate-400 font-mono">
                        {Number(w.value_raw || 0).toFixed(4)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">{shortAddr(w.from_address)}</td>
                      <td className="py-2 px-2 text-slate-400 font-mono">{shortAddr(w.to_address)}</td>
                      <td className="py-2 px-2 text-slate-500">{w.transfer_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No BNB whale events available</p>
          )}
        </div>

        {/* DEX Pools */}
        {pools.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">PancakeSwap Pools</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Pool</th>
                    <th className="text-right py-2 px-2">TVL</th>
                    <th className="text-right py-2 px-2">Vol 24h</th>
                    <th className="text-right py-2 px-2">TXs 24h</th>
                    <th className="text-right py-2 px-2">Price Chg</th>
                  </tr>
                </thead>
                <tbody>
                  {pools.slice(0, 20).map((p: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2">
                        <span className="text-slate-300 font-medium">
                          {String(p.token0_symbol || "?").toUpperCase()}/{String(p.token1_symbol || "?").toUpperCase()}
                        </span>
                        <p className="text-[10px] text-slate-600 font-mono">{shortAddr(p.pool_id)}</p>
                      </td>
                      <td className="py-2 px-2 text-right text-white">{fmtUsd(p.tvl_usd)}</td>
                      <td className="py-2 px-2 text-right text-slate-300">{fmtUsd(p.volume_24h_usd)}</td>
                      <td className="py-2 px-2 text-right text-slate-400">{fmtNum(p.tx_count_24h)}</td>
                      <td className={`py-2 px-2 text-right font-medium ${
                        Number(p.price_change_24h || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}>
                        {Number(p.price_change_24h || 0).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Risk Scores */}
        {riskScores.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Yield Risk Scores</h3>
            <div className="space-y-3">
              {riskScores.slice(0, 10).map((r: any, i: number) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-32 text-xs text-slate-400 truncate">{r.pool_name}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-slate-500">{r.explanation}</span>
                      <span className={`text-xs font-bold ${
                        r.risk_flag === "high" ? "text-rose-400" :
                        r.risk_flag === "watch" ? "text-amber-400" : "text-emerald-400"
                      }`}>
                        {r.risk_score}/100
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          r.risk_flag === "high" ? "bg-rose-400" :
                          r.risk_flag === "watch" ? "bg-amber-400" : "bg-emerald-400"
                        }`}
                        style={{ width: `${Math.min(100, r.risk_score)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Validators */}
        {validators.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Validator Health</h3>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              {validators.slice(0, 15).map((v: any, i: number) => (
                <div key={i} className={`p-3 rounded-lg border ${
                  (v.missed_blocks_count || 0) > 5 
                    ? "bg-rose-500/5 border-rose-500/20" 
                    : "bg-white/[0.02] border-white/[0.04]"
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300">{shortAddr(v.validator_address)}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      v.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-500/10 text-slate-400"
                    }`}>
                      {v.is_active ? "ACTIVE" : "INACTIVE"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Missed: <span className={(v.missed_blocks_count || 0) > 5 ? "text-rose-400 font-bold" : "text-slate-400"}>
                      {v.missed_blocks_count || 0}
                    </span>
                    {v.staking_apr != null && (
                      <span className="ml-2">APR: {Number(v.staking_apr).toFixed(1)}%</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
            {badValidators.length > 0 && (
              <div className="mt-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />
                <span className="text-xs text-rose-400">
                  {badValidators.length} validator(s) with missed block anomalies
                </span>
              </div>
            )}
          </div>
        )}

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
