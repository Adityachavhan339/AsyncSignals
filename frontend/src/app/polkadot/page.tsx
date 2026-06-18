import DashboardLayout from "@/components/DashboardLayout";
import { fetchPolkadot, fmtUsd, fmtNum } from "@/lib/api";

async function getData() {
  try {
    return await fetchPolkadot();
  } catch (e) {
    console.error("Failed to fetch polkadot:", e);
    return { items: {} };
  }
}

export default async function PolkadotPage() {
  const data = await getData();
  const polkadot = data.items || {};

  const rpc = polkadot.rpc_snapshot?.[0] || {};
  const activity = polkadot.chain_activity || [];
  const staking = polkadot.staking || [];
  const treasury = polkadot.treasury || [];
  const validators = polkadot.validators || [];
  const opengov = polkadot.opengov || [];
  const xcmSummary = polkadot.xcm_summary || [];
  const xcmTransfers = polkadot.xcm_transfers || [];
  const derived = polkadot.derived_signals || [];

  const activeChains = new Set(activity.map((a: any) => a.chain_name)).size;
  const xcm24h = xcmSummary.reduce((sum: number, x: any) => sum + (Number(x.total_messages) || 0), 0);
  const maxUrgency = opengov.length > 0 ? Math.max(...opengov.map((o: any) => Number(o.urgency_score) || 0)) : 0;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Polkadot Telemetry</h2>
          <p className="text-sm text-slate-400">
            Parachain activity, staking economics, treasury allocation, governance urgency, XCM routes, and derived signals.
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-white/[0.03] to-white/[0.01] p-4">
            <p className="text-xs text-slate-500 mb-1">Latest Block</p>
            <p className="text-xl font-bold text-white">{fmtNum(rpc.latest_block_number_int)}</p>
            <p className="text-xs text-slate-400">Extrinsics: {fmtNum(rpc.extrinsics_in_latest_block)}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-rose-500/10 to-rose-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Active Parachains</p>
            <p className="text-xl font-bold text-rose-400">{activeChains || "--"}</p>
            <p className="text-xs text-rose-400/70">From latest activity</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-cyan-500/10 to-cyan-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">XCM 24h Messages</p>
            <p className="text-xl font-bold text-cyan-400">{fmtNum(xcm24h)}</p>
            <p className="text-xs text-cyan-400/70">Cross-chain volume</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-amber-500/10 to-amber-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Max Gov Urgency</p>
            <p className="text-xl font-bold text-amber-400">{maxUrgency || "--"}</p>
            <p className="text-xs text-amber-400/70">OpenGov pressure</p>
          </div>
        </div>

        {/* Chain Activity */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4">Chain Activity Leaders</h3>
          {activity.length > 0 ? (
            <div className="space-y-3">
              {activity.slice(0, 10).map((a: any, i: number) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-24 text-xs text-slate-400">{a.chain_name}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-slate-500">
                        TX: {fmtNum(a.tx_count)} | TPS: {Number(a.tps || 0).toFixed(3)}
                      </span>
                      <span className={`text-xs font-bold ${
                        a.alert_level === "high" ? "text-rose-400" :
                        a.alert_level === "medium" ? "text-amber-400" : "text-emerald-400"
                      }`}>
                        {Number(a.activity_score || 0).toFixed(1)}
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${
                          a.alert_level === "high" ? "bg-rose-400" :
                          a.alert_level === "medium" ? "bg-amber-400" : "bg-emerald-400"
                        }`}
                        style={{ width: `${Math.min(100, (Number(a.activity_score) || 0) / 5)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No chain activity data</p>
          )}
        </div>

        {/* Two Column: Staking + Treasury */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Staking */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Staking Overview</h3>
            {staking.length > 0 ? (
              <div className="space-y-3">
                {staking.slice(0, 5).map((s: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-sm font-medium text-white">{s.chain_name}</p>
                    <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
                      <div>
                        <p className="text-slate-500">Validators</p>
                        <p className="text-slate-300">{fmtNum(s.number_of_validators)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Nominators</p>
                        <p className="text-slate-300">{fmtNum(s.number_of_nominators)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Staked</p>
                        <p className="text-emerald-400">{fmtNum(s.staked_dot)} DOT</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Min Stake</p>
                        <p className="text-amber-400">{fmtNum(s.minimum_nominator_active_stake)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No staking data</p>
            )}
          </div>

          {/* Treasury */}
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Treasury Allocation</h3>
            {treasury.length > 0 ? (
              <div className="space-y-3">
                {treasury.slice(0, 8).map((t: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div>
                      <p className="text-sm font-medium text-white">{t.asset_symbol}</p>
                      <p className="text-xs text-slate-500">{t.chain_name}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-white">{fmtUsd(t.balance_usd)}</p>
                      <p className="text-xs text-slate-500">
                        {Number(t.treasury_share_pct || 0).toFixed(1)}% of treasury
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No treasury data</p>
            )}
          </div>
        </div>

        {/* Governance */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4">OpenGov Urgency</h3>
          {opengov.length > 0 ? (
            <div className="space-y-3">
              {opengov.slice(0, 6).map((o: any, i: number) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-12 text-xs text-slate-500">#{o.referendum_index}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-white">{o.origin_name}</span>
                      <span className={`text-xs font-bold ${
                        Number(o.urgency_score || 0) >= 70 ? "text-rose-400" :
                        Number(o.urgency_score || 0) >= 40 ? "text-amber-400" : "text-emerald-400"
                      }`}>
                        {Number(o.urgency_score || 0).toFixed(0)}
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${
                          Number(o.urgency_score || 0) >= 70 ? "bg-rose-400" :
                          Number(o.urgency_score || 0) >= 40 ? "bg-amber-400" : "bg-emerald-400"
                        }`}
                        style={{ width: `${Math.min(100, Number(o.urgency_score) || 0)}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">
                      {o.outcome_status} | Turnout: {fmtNum(o.turnout_total)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No governance data</p>
          )}
        </div>

        {/* XCM Summary */}
        {xcmSummary.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">XCM Summary</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {xcmSummary.slice(0, 1).map((x: any, i: number) => (
                <div key={i} className="grid grid-cols-2 lg:grid-cols-4 gap-4 col-span-full">
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-slate-500 mb-1">Success Rate</p>
                    <p className="text-lg font-bold text-emerald-400">{Number(x.success_rate || 0).toFixed(1)}%</p>
                  </div>
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-slate-500 mb-1">Avg Latency</p>
                    <p className="text-lg font-bold text-cyan-400">{Number(x.avg_latency_seconds || 0).toFixed(1)}s</p>
                  </div>
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-slate-500 mb-1">Unmatched</p>
                    <p className="text-lg font-bold text-rose-400">{fmtNum(x.unmatched_messages)}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <p className="text-xs text-slate-500 mb-1">Total Messages</p>
                    <p className="text-lg font-bold text-white">{fmtNum(x.total_messages)}</p>
                  </div>
                </div>
              ))}
            </div>
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
                    {d.chain_name} | {d.signal_family} | Score: {d.score}
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
