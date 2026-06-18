"use client";

import DashboardLayout from "@/components/DashboardLayout";
import { useState } from "react";
import { Bell, CheckCircle, AlertTriangle } from "lucide-react";

export default function AlertsAccess() {
  const [chatId, setChatId] = useState("");
  const [status, setStatus] = useState("idle");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatId.trim()) {
      setStatus("error");
      return;
    }
    setStatus("success");
    setChatId("");
    setTimeout(() => setStatus("idle"), 3000);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Alerts Access</h2>
          <p className="text-sm text-slate-400">
            Register a Telegram destination for operational signal delivery.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-5">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Bell size={16} className="text-amber-400" />
              Register Alert Channel
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Telegram Chat ID</label>
                <input
                  type="text"
                  value={chatId}
                  onChange={(e) => setChatId(e.target.value)}
                  placeholder="e.g. 123456789"
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2.5 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-purple-500/50 transition-colors"
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-2.5 rounded-lg bg-purple-500/20 text-purple-400 text-sm font-medium border border-purple-500/20 hover:bg-purple-500/30 transition-colors"
              >
                Register Alert Channel
              </button>
              {status === "success" && (
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <CheckCircle size={14} />
                  Alert channel registered successfully
                </div>
              )}
              {status === "error" && (
                <div className="flex items-center gap-2 text-xs text-rose-400">
                  <AlertTriangle size={14} />
                  Please enter a valid chat ID
                </div>
              )}
            </form>
          </div>

          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-5">
            <h3 className="text-sm font-bold text-white mb-4">Deployment Note</h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              AsyncSignals uses Oracle-backed persistence for signal history and subscriber routing.
              This surface is intended for teams, analysts, and ecosystem operators rather than retail chart browsing.
            </p>
            <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <p className="text-xs text-slate-500 mb-1">Recommended Demo Flow</p>
              <p className="text-xs text-slate-300">
                Mission Control → Whale Tracker → Polkadot → Signal Ledger → AI Context
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
