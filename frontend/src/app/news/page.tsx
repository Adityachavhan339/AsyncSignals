import DashboardLayout from "@/components/DashboardLayout";
import { fetchBundle } from "@/lib/api";

async function getData() {
  try {
    const data = await fetchBundle();
    return data.news || [];
  } catch (e) {
    console.error("Failed to fetch news:", e);
    return [];
  }
}

export default async function NewsContext() {
  const news = await getData();

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-white mb-1">News Context</h2>
          <p className="text-sm text-slate-400">
            Recent headlines feeding the narrative layer behind volatility and whale movement.
          </p>
        </div>

        {/* News Cards */}
        {news.length > 0 ? (
          <div className="space-y-4">
            {news.map((n: any, i: number) => (
              <div key={i} className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-5 hover:border-white/10 transition-colors">
                <h3 className="text-base font-bold text-white mb-2 leading-snug">
                  {n.title || "Untitled"}
                </h3>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs text-slate-500">{n.source_id || "Unknown source"}</span>
                  <span className="text-xs text-slate-600">|</span>
                  <span className="text-xs text-slate-500">{n.pubdate || ""}</span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed mb-4">
                  {String(n.description || "").slice(0, 280)}
                  {String(n.description || "").length > 280 ? "..." : ""}
                </p>
                {n.link && (
                  <a 
                    href={n.link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    Open source article →
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-white/5 bg-[#0d1722]/90 p-8 text-center">
            <p className="text-sm text-slate-500">No recent news found</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
