"use client";

import DashboardLayout from "@/components/DashboardLayout";
import { useState, useEffect } from "react";
import {
  fetchSuiWhales,
  fetchSuiTopWhales,
  fetchSuiProtocolExposure,
  fetchSuiSummary,
  fmtUsd,
  fmtNum,
  shortAddr,
} from "@/lib/api";
import { Droplets, Activity, TrendingUp, AlertCircle, Zap, GitBranch } from "lucide-react";

interface WhaleEvent {
  tx_hash: string;
  event_timestamp: string;
  from_addr: string;
  to_addr: string;
  token: string;
  amount: number;
  usd_value: number;
  protocol_tag: string;
  direction: string;
}

interface TopWhale {
  address: string;
  total_in_usd: number;
  total_out_usd: number;
  net_flow_usd: number;
  protocols_touched: number;
  protocol_list: string;
  tx_count: number;
}

interface ProtocolExposure {
  protocol: string;
  volume_usd: number;
  tx_count: number;
}

export default function SuiPage() {
  const [whales, setWhales] = useState<WhaleEvent[]>([]);
  const [topWhales, setTopWhales] = useState<TopWhale[]>([]);
  const [exposure, setExposure] = useState<ProtocolExposure[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [protocolFilter, setProtocolFilter] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [w, tw, pe, sm] = await Promise.all([
          fetchSuiWhales(50),
          fetchSuiTopWhales(20),
          fetchSuiProtocolExposure(),
          fetchSuiSummary(),
        ]);
        setWhales(w.items || []);
        setTopWhales(tw.items || []);
        setExposure(pe.items || []);
        setSummary(sm.summary || null);
      } catch (e: any) {
        setError(e.message || "Failed to load Sui data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const realTransfers = whales.filter(w => w.usd_value > 0 || w.amount > 0);
  const objectMutations = whales.filter(w => w.usd_value === 0 && w.amount === 0);

  const filteredTransfers = protocolFilter
    ? realTransfers.filter((w) =>
        w.protocol_tag.toLowerCase().includes(protocolFilter.toLowerCase())
      )
    : realTransfers;

  const totalVolume = realTransfers.reduce((s, w) => s + (w.usd_value || 0), 0);
  const protocols = Array.from(new Set(whales.map((w) => w.protocol_tag))).filter(Boolean);

  // Count protocol interactions (the unique feature)
  const protocolInteractions = objectMutations.length;
  const uniqueProtocolsTouched = new Set(objectMutations.map(w => w.protocol_tag)).size;

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500 animate-pulse" />
          <span className="ml-3 text-sm text-slate-400">Loading Sui telemetry...</span>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Hero Header — reframed as Move Intelligence */}
        <div className="relative overflow-hidden rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-[#0a1f2e] to-[#061520] p-6">
          <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full blur-3xl" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-2">
              <GitBranch size={18} className="text-cyan-400" />
              <span className="text-xs font-bold text-cyan-400 tracking-widest uppercase">Move Intelligence</span>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Sui DeFi Behavior Engine</h2>
            <p className="text-sm text-slate-400 max-w-xl">
              Not just token transfers — we decode <span className="text-cyan-400 font-medium">Move object mutations</span> across 
              Cetus, DeepBook, Scallop, Navi, Suilend. See what whales are <span className="text-cyan-400 font-medium">doing</span>, not just where they&apos;re moving money.
            </p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
            <AlertCircle size={14} className="text-rose-400" />
            <span className="text-xs text-rose-400">{error}</span>
          </div>
        )}

        {/* KPI Cards — lead with the unique metric */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-cyan-500/10 to-cyan-500/5 p-4">
            <div className="flex items-center gap-2 mb-1">
              <Zap size={14} className="text-cyan-400" />
              <p className="text-xs text-cyan-400/70">Move Interactions</p>
            </div>
            <p className="text-2xl font-bold text-white">{protocolInteractions}</p>
            <p className="text-xs text-slate-500">Object mutations detected</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-blue-500/10 to-blue-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Tracked Volume</p>
            <p className="text-xl font-bold text-blue-400">{fmtUsd(totalVolume)}</p>
            <p className="text-xs text-blue-400/70">{realTransfers.length} transfers</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Active Whales</p>
            <p className="text-xl font-bold text-emerald-400">{topWhales.filter(w => w.total_in_usd + w.total_out_usd > 0).length}</p>
            <p className="text-xs text-emerald-400/70">7-day window</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-purple-500/10 to-purple-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Protocols</p>
            <p className="text-xl font-bold text-purple-400">{protocols.length}</p>
            <p className="text-xs text-purple-400/70">{uniqueProtocolsTouched} with mutations</p>
          </div>
        </div>

        {/* Protocol Mutation Feed — THE FEATURE */}
        {objectMutations.length > 0 && (
          <div className="rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-[#0a1f2e]/50 to-[#061520]/50 p-5">
            <div className="flex items-center gap-2 mb-4">
              <GitBranch size={16} className="text-cyan-400" />
              <h3 className="text-sm font-bold text-white">Live Protocol Mutation Feed</h3>
              <span className="ml-auto px-2 py-0.5 rounded-full text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                Move-Aware
              </span>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              These transactions mutated protocol state without immediate token transfers. 
              Whales opening positions, adding liquidity, or interacting with DeFi contracts.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-cyan-500/20">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Protocol</th>
                    <th className="text-left py-2 px-2">Address</th>
                    <th className="text-left py-2 px-2">Mutation Type</th>
                    <th className="text-left py-2 px-2">TX Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {objectMutations.slice(0, 10).map((w, i) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-cyan-500/5">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(w.event_timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          w.protocol_tag === "cetus" ? "bg-cyan-500/10 text-cyan-400" :
                          w.protocol_tag === "deepbook" ? "bg-blue-500/10 text-blue-400" :
                          w.protocol_tag === "scallop" ? "bg-emerald-500/10 text-emerald-400" :
                          w.protocol_tag === "navi" ? "bg-purple-500/10 text-purple-400" :
                          "bg-white/5 text-slate-400"
                        }`}>
                          {w.protocol_tag}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-slate-300 font-mono">
                        {shortAddr(w.from_addr)}
                      </td>
                      <td className="py-2 px-2">
                        <span className="text-[10px] text-cyan-400 font-medium">Object Mutation</span>
                      </td>
                      <td className="py-2 px-2 text-slate-500 font-mono">
                        {shortAddr(w.tx_hash)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* AI Summary */}
        {summary && (
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-[#0d1722] to-[#09131c] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Activity size={16} className="text-purple-400" />
              <h3 className="text-sm font-bold text-white">AI Summary</h3>
              <span className="text-[10px] text-slate-500 ml-auto">
                {summary.summary_type || "rule-based"}
              </span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {summary.summary_text || "No summary available."}
            </p>
            {summary.note && (
              <p className="text-xs text-slate-500 mt-2 italic">{summary.note}</p>
            )}
          </div>
        )}

        {/* Protocol Exposure */}
        {exposure.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingUp size={16} className="text-emerald-400" />
                Protocol Exposure
              </h3>
            </div>
            <div className="space-y-3">
              {exposure.map((p, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-24 text-xs text-slate-400 capitalize">{p.protocol}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-slate-500">{p.tx_count} txs</span>
                      <span className="text-xs font-bold text-emerald-400">
                        {fmtUsd(p.volume_usd)}
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-400"
                        style={{
                          width: `${Math.min(100, (p.volume_usd / (exposure[0]?.volume_usd || 1)) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Whales */}
        {topWhales.filter(w => w.total_in_usd + w.total_out_usd > 0).length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4">Top Whale Addresses (7D)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Address</th>
                    <th className="text-right py-2 px-2">In</th>
                    <th className="text-right py-2 px-2">Out</th>
                    <th className="text-right py-2 px-2">Net Flow</th>
                    <th className="text-left py-2 px-2">Protocols</th>
                    <th className="text-right py-2 px-2">TXs</th>
                  </tr>
                </thead>
                <tbody>
                  {topWhales.filter(w => w.total_in_usd + w.total_out_usd > 0).map((w, i) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-300 font-mono">
                        {shortAddr(w.address)}
                      </td>
                      <td className="py-2 px-2 text-right text-emerald-400">
                        {fmtUsd(w.total_in_usd)}
                      </td>
                      <td className="py-2 px-2 text-right text-rose-400">
                        {fmtUsd(w.total_out_usd)}
                      </td>
                      <td className={`py-2 px-2 text-right font-bold ${
                        w.net_flow_usd >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}>
                        {fmtUsd(w.net_flow_usd)}
                      </td>
                      <td className="py-2 px-2 text-slate-400">
                        {w.protocol_list || "—"}
                      </td>
                      <td className="py-2 px-2 text-right text-slate-400">
                        {w.tx_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Traditional Whale Transfers */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white">Value Transfers</h3>
            <div className="flex items-center gap-2">
              <select
                value={protocolFilter}
                onChange={(e) => setProtocolFilter(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50"
              >
                <option value="">All Protocols</option>
                {protocols.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <span className="text-xs text-slate-500">{filteredTransfers.length} rows</span>
            </div>
          </div>

          {filteredTransfers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Protocol</th>
                    <th className="text-left py-2 px-2">Token</th>
                    <th className="text-right py-2 px-2">Amount</th>
                    <th className="text-right py-2 px-2">USD</th>
                    <th className="text-left py-2 px-2">From</th>
                    <th className="text-left py-2 px-2">To</th>
                    <th className="text-left py-2 px-2">Dir</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTransfers.slice(0, 50).map((w, i) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(w.event_timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          w.protocol_tag === "cetus" ? "bg-cyan-500/10 text-cyan-400" :
                          w.protocol_tag === "deepbook" ? "bg-blue-500/10 text-blue-400" :
                          w.protocol_tag === "scallop" ? "bg-emerald-500/10 text-emerald-400" :
                          w.protocol_tag === "navi" ? "bg-purple-500/10 text-purple-400" :
                          "bg-white/5 text-slate-400"
                        }`}>
                          {w.protocol_tag}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-slate-300">{w.token}</td>
                      <td className="py-2 px-2 text-right text-slate-300 font-mono">
                        {Number(w.amount || 0).toFixed(4)}
                      </td>
                      <td className="py-2 px-2 text-right text-white font-medium">
                        {fmtUsd(w.usd_value)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">
                        {shortAddr(w.from_addr)}
                      </td>
                      <td className="py-2 px-2 text-slate-400 font-mono">
                        {shortAddr(w.to_addr)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`text-[10px] ${
                          w.direction === "in" ? "text-emerald-400" :
                          w.direction === "out" ? "text-rose-400" : "text-slate-400"
                        }`}>
                          {w.direction}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No value transfers in current window</p>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
