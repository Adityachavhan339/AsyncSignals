import DashboardLayout from "@/components/DashboardLayout";
import { fetchSignals, fmtUsd } from "@/lib/api";

async function getData() {
  try {
    return await fetchSignals(50);
  } catch (e) {
    console.error("Failed to fetch signals:", e);
    return { items: [] };
  }
}

export default async function SignalLedger() {
  const data = await getData();
  const signals = data.items || [];

  // Stats
  const dangerCount = signals.filter((s: any) => String(s.type).includes("DANGER")).length;
  const oppCount = signals.filter((s: any) => String(s.type).includes("OPPORTUNITY")).length;
  const successCount = signals.filter((s: any) => String(s.status).includes("Success")).length;
  const failedCount = signals.filter((s: any) => String(s.status).includes("Failed")).length;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Signal Ledger</h2>
          <p className="text-sm text-slate-400">
            Execution-oriented signal history from Oracle, including generated status outcomes and signal classifications.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-rose-500/10 to-rose-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Danger Signals</p>
            <p className="text-xl font-bold text-rose-400">{dangerCount}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-emerald-500/10 to-emerald-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Opportunities</p>
            <p className="text-xl font-bold text-emerald-400">{oppCount}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-blue-500/10 to-blue-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Successful</p>
            <p className="text-xl font-bold text-blue-400">{successCount}</p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-gradient-to-b from-amber-500/10 to-amber-500/5 p-4">
            <p className="text-xs text-slate-500 mb-1">Failed</p>
            <p className="text-xl font-bold text-amber-400">{failedCount}</p>
          </div>
        </div>

        {/* Signals Table */}
        <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-4">
          <h3 className="text-sm font-bold text-white mb-4">Signal History</h3>
          {signals.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 px-2">Time</th>
                    <th className="text-left py-2 px-2">Type</th>
                    <th className="text-left py-2 px-2">Message</th>
                    <th className="text-right py-2 px-2">Entry</th>
                    <th className="text-right py-2 px-2">Exit</th>
                    <th className="text-left py-2 px-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((s: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                      <td className="py-2 px-2 text-slate-400 whitespace-nowrap">
                        {String(s.timestamp || "").slice(0, 16)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          String(s.type).includes("DANGER") ? "bg-rose-500/10 text-rose-400" :
                          String(s.type).includes("OPPORTUNITY") ? "bg-emerald-500/10 text-emerald-400" :
                          String(s.type).includes("SOL") ? "bg-purple-500/10 text-purple-400" :
                          "bg-amber-500/10 text-amber-400"
                        }`}>
                          {String(s.type).slice(0, 20)}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-slate-300 max-w-xs truncate">
                        {String(s.msg || "").slice(0, 60)}...
                      </td>
                      <td className="py-2 px-2 text-right text-slate-400 font-mono">
                        {fmtUsd(s.entry_price)}
                      </td>
                      <td className="py-2 px-2 text-right text-slate-400 font-mono">
                        {fmtUsd(s.exit_price)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`text-xs ${
                          String(s.status).includes("Success") ? "text-emerald-400" :
                          String(s.status).includes("Failed") ? "text-rose-400" :
                          String(s.status).includes("Observed") ? "text-blue-400" :
                          "text-amber-400"
                        }`}>
                          {String(s.status || "Pending").slice(0, 25)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No signal records available</p>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
