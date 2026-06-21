"use client";

import DashboardLayout from "@/components/DashboardLayout";
import { useState, useEffect } from "react";
import {
  fetchNodeOpsMetrics,
  fetchNodeOpsHealth,
  postNodeOpsTelemetry,
  fmtNum,
} from "@/lib/api";
import {
  Server,
  Activity,
  AlertTriangle,
  CheckCircle,
  Download,
  Radio,
  Send,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";

interface NodeMetric {
  node_id: string;
  chain: string;
  ts: string;
  jobs_ok: number;
  jobs_failed: number;
  success_rate: number;
  avg_latency_ms: number;
  gas_spent_native: number;
  rewards_token: number;
  error_code: string | null;
  runbook_severity: string | null;
  runbook_advice: string | null;
  runbook_category: string | null;
}

interface HealthItem {
  node_id: string;
  chain: string;
  last_seen: string;
  avg_success_rate: number;
  avg_latency: number;
  last_error: string | null;
  last_runbook: string | null;
}

export default function NodeOpsPage() {
  const [metrics, setMetrics] = useState<NodeMetric[]>([]);
  const [health, setHealth] = useState<HealthItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [nodeFilter, setNodeFilter] = useState("");
  const [windowHours, setWindowHours] = useState(24);
  const [pushStatus, setPushStatus] = useState<"idle" | "sending" | "ok" | "err">("idle");

  useEffect(() => {
    async function load() {
      try {
        const [m, h] = await Promise.all([
          fetchNodeOpsMetrics(nodeFilter || undefined, windowHours),
          fetchNodeOpsHealth(),
        ]);
        setMetrics(m.items || []);
        setHealth(h.items || []);
      } catch (e: any) {
        setError(e.message || "Failed to load NodeOps data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [nodeFilter, windowHours]);

  const handlePushDemo = async () => {
    setPushStatus("sending");
    try {
      const demoPayload = {
        node_id: `demo-node-${Math.floor(Math.random() * 100)}`,
        chain: ["ethereum", "avalanche", "base"][Math.floor(Math.random() * 3)],
        jobs_ok: Math.floor(Math.random() * 200) + 50,
        jobs_failed: Math.floor(Math.random() * 20),
        avg_latency_ms: Math.random() * 800 + 50,
        gas_spent_native: Math.random() * 0.5,
        rewards_token: Math.random() * 5,
        error_code: Math.random() > 0.7 ? "NODE_OVERLOADED" : null,
      };
      await postNodeOpsTelemetry(demoPayload);
      setPushStatus("ok");
      setTimeout(() => setPushStatus("idle"), 2000);
      // Refresh
      const m = await fetchNodeOpsMetrics(nodeFilter || undefined, windowHours);
      setMetrics(m.items || []);
    } catch (e: any) {
      setPushStatus("err");
      setTimeout(() => setPushStatus("idle"), 3000);
    }
  };

  const downloadCsv = () => {
    const url = `${process.env.NEXT_PUBLIC_API_URL || "https://api.asyncsignals.tech"}/api/v1/nodeops/metrics.csv?window=${windowHours}${nodeFilter ? `&node_id=${nodeFilter}` : ""}`;
    window.open(url, "_blank");
  };

  const avgSuccess = metrics.length
    ? metrics.reduce((s, m) => s + (m.success_rate || 0), 0) / metrics.length
    : 0;
  const totalJobs = metrics.reduce((s, m) => s + (m.jobs_ok || 0) + (m.jobs_failed || 0), 0);
  const errorCount = metrics.filter((m) => m.error_code).length;
  const chains = Array.from(new Set(metrics.map((m) => m.chain)));

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-400 to-amber-500 animate-pulse" />
          <span className="ml-3 text-sm text-slate-400">Loading NodeOps telemetry...</span>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Server size={18} className="text-orange-400" />
              <h2 className="text-xl font-bold text-white">NodeOps Insight Hub</h2>
            </div>
            <p className="text-sm text-slate-400">
              Opt-in telemetry aggregation for validator/oracle nodes. Health scores, error trends, and contextual runbooks.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePushDemo}
              disabled={pushStatus === "sending"}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500/20 text-orange-400 text-xs font-medium border border-orange-500/20 hover:bg-orange-500/30 disabled:opacity-50 transition-colors"
            >
              <Send size={12} />
              {pushStatus === "sending" ? "Pushing..." : pushStatus === "ok" ? "Sent!" : pushStatus === "err" ? "Failed" : "Push Demo"}
            </button>
            <button
              onClick={downloadCsv}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-slate-300 text-xs font-medium border border-white/10 hover:bg-white/10 transition-colors"
            >
              <Download size={12} />
              CSV
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
            <AlertTriangle size={14} className="text-rose-400" />
            <span className="text-xs text-rose-400">{error}</span>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Avg Success Rate</p>
            <p className="text-xl font-bold text-emerald-400">{avgSuccess.toFixed(1)}%</p>
            <p className="text-xs text-emerald-400/70">{metrics.length} records</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-blue-500/10 to-blue-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Total Jobs</p>
            <p className="text-xl font-bold text-blue-400">{fmtNum(totalJobs)}</p>
            <p className="text-xs text-blue-400/70">{chains.join(", ") || "—"}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-amber-500/10 to-amber-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Error Events</p>
            <p className="text-xl font-bold text-amber-400">{errorCount}</p>
            <p className="text-xs text-amber-400/70">{windowHours}h window</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-orange-500/10 to-orange-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Nodes Tracked</p>
            <p className="text-xl font-bold text-orange-400">
              {new Set(metrics.map((m) => m.node_id)).size}
            </p>
            <p className="text-xs text-orange-400/70">Unique IDs</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={nodeFilter}
            onChange={(e) => setNodeFilter(e.target.value)}
            placeholder="Filter by node ID..."
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-orange-500/50 w-48"
          />
          <select
            value={windowHours}
            onChange={(e) => setWindowHours(Number(e.target.value))}
            className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-orange-500/50"
          >
            <option value={1}>1h</option>
            <option value={6}>6h</option>
            <option value={24}>24h</option>
            <option value={72}>72h</option>
            <option value={168}>7d</option>
          </select>
        </div>

        {/* Health Summary */}
        {health.length > 0 && (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Activity size={16} className="text-emerald-400" />
              Node Health Summary
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {health.map((h, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`w-2 h-2 rounded-full ${
                        (h.avg_success_rate || 0) >= 95 ? "bg-emerald-400" :
                        (h.avg_success_rate || 0) >= 80 ? "bg-amber-400" : "bg-rose-400"
                      }`} />
                      <span className="text-sm font-medium text-white">{h.node_id}</span>
                      <span className="text-[10px] text-slate-500 uppercase">{h.chain}</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Last seen: {String(h.last_seen).slice(0, 16)} | Latency: {Number(h.avg_latency || 0).toFixed(0)}ms
                    </p>
                    {h.last_error && (
                      <p className="text-[10px] text-rose-400 mt-1">Last error: {h.last_error}</p>
                    )}
                    {h.last_runbook && (
                      <p className="text-[10px] text-amber-400 mt-0.5">{h.last_runbook}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-bold ${
                      (h.avg_success_rate || 0) >= 95 ? "text-emerald-400" :
                      (h.avg_success_rate || 0) >= 80 ? "text-amber-400" : "text-rose-400"
                    }`}>
                      {Number(h.avg_success_rate || 0).toFixed(1)}%
                    </p>
                    <p className="text-[10px] text-slate-500">success rate</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Metrics Table */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Radio size={16} className="text-cyan-400" />
            Telemetry Stream
          </h3>
          {metrics.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Node</th>
                    <th className="text-left py-2 px-2">Chain</th>
                    <th className="text-right py-2 px-2">Success</th>
                    <th className="text-right py-2 px-2">Failed</th>
                    <th className="text-right py-2 px-2">Rate</th>
                    <th className="text-right py-2 px-2">Latency</th>
                    <th className="text-right py-2 px-2">Gas</th>
                    <th className="text-left py-2 px-2">Error</th>
                    <th className="text-left py-2 px-2">Runbook</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m, i) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(m.ts || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2 text-slate-300 font-mono">{m.node_id}</td>
                      <td className="py-2 px-2">
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-slate-400 uppercase">
                          {m.chain}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-emerald-400">{m.jobs_ok}</td>
                      <td className="py-2 px-2 text-right text-rose-400">{m.jobs_failed}</td>
                      <td className="py-2 px-2 text-right">
                        <span className={`${
                          m.success_rate >= 95 ? "text-emerald-400" :
                          m.success_rate >= 80 ? "text-amber-400" : "text-rose-400"
                        }`}>
                          {m.success_rate}%
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right text-slate-300">{m.avg_latency_ms}ms</td>
                      <td className="py-2 px-2 text-right text-slate-300">{m.gas_spent_native}</td>
                      <td className="py-2 px-2">
                        {m.error_code ? (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                            m.runbook_severity === "critical" ? "bg-rose-500/10 text-rose-400" :
                            m.runbook_severity === "high" ? "bg-orange-500/10 text-orange-400" :
                            "bg-amber-500/10 text-amber-400"
                          }`}>
                            {m.error_code}
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-2 px-2 text-slate-400 max-w-xs truncate">
                        {m.runbook_advice || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-xs text-slate-500 mb-2">No telemetry data for selected window</p>
              <button
                onClick={handlePushDemo}
                className="px-3 py-1.5 rounded-lg bg-orange-500/20 text-orange-400 text-xs border border-orange-500/20 hover:bg-orange-500/30 transition-colors"
              >
                Push Demo Data
              </button>
            </div>
          )}
        </div>

        {/* Runbook Legend */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-3">Runbook Reference</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              { code: "NODE_OVERLOADED", sev: "high", cat: "resource", advice: "Increase CPU/memory or reduce concurrent job count" },
              { code: "RPC_UNAVAILABLE", sev: "critical", cat: "connectivity", advice: "Failover to backup RPC endpoint" },
              { code: "NONCE_TOO_LOW", sev: "medium", cat: "transaction", advice: "Clear local mempool and reset nonce tracker" },
              { code: "REPLACEMENT_UNDERPRICED", sev: "medium", cat: "gas", advice: "Increase gas bump parameters in config" },
              { code: "INSUFFICIENT_FUNDS", sev: "critical", cat: "financial", advice: "Top up node wallet with native gas token" },
            ].map((rb) => (
              <div key={rb.code} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    rb.sev === "critical" ? "bg-rose-400" :
                    rb.sev === "high" ? "bg-orange-400" : "bg-amber-400"
                  }`} />
                  <span className="text-xs font-bold text-white">{rb.code}</span>
                  <span className="text-[10px] text-slate-500 uppercase">{rb.cat}</span>
                </div>
                <p className="text-xs text-slate-400">{rb.advice}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
