"use client";

import { useState, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter, usePathname } from "next/navigation";
import {
  Activity,
  Waves,
  Signal,
  Brain,
  Newspaper,
  BarChart3,
  Globe,
  Layers,
  Bell,
  Menu,
  X,
  Zap,
  LogOut,
  User,
  Droplets,
  Server,
} from "lucide-react";
import Link from "next/link";

const navItems = [
  { name: "Mission Control", icon: Activity, href: "/", color: "text-emerald-400" },
  { name: "Whale Tracker", icon: Waves, href: "/whales", color: "text-cyan-400" },
  { name: "Signal Ledger", icon: Signal, href: "/signals", color: "text-amber-400" },
  { name: "AI Context", icon: Brain, href: "/ai", color: "text-purple-400" },
  { name: "News Context", icon: Newspaper, href: "/news", color: "text-blue-400" },
  { name: "Market Surface", icon: BarChart3, href: "/market", color: "text-pink-400" },
  { name: "Polkadot", icon: Globe, href: "/polkadot", color: "text-rose-400" },
  { name: "Base L2", icon: Layers, href: "/base", color: "text-indigo-400" },
  { name: "Sui", icon: Droplets, href: "/sui", color: "text-cyan-400" },
  { name: "NodeOps", icon: Server, href: "/nodeops", color: "text-orange-400" },
  { name: "Alerts Access", icon: Bell, href: "/alerts", color: "text-orange-400" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  // Redirect to sign-in if not authenticated
  useEffect(() => {
    if (status === "unauthenticated" && pathname !== "/sign-in") {
      router.push("/sign-in");
    }
  }, [status, pathname, router]);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  // Show loading while checking auth
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-[#06111a] flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-emerald-400 animate-pulse" />
          <span className="text-sm text-slate-400">Loading...</span>
        </div>
      </div>
    );
  }

  // Don't render layout on sign-in page
  if (pathname === "/sign-in") {
    return <>{children}</>;
  }

  // Don't render if not authenticated
  if (!session) {
    return null;
  }

  const userName = session.user?.name || "Operator";
  const userEmail = session.user?.email || "";

  return (
    <div className="min-h-screen bg-[#06111a] text-slate-200 flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky lg:top-0 left-0 z-50 h-screen w-64 flex-shrink-0 border-r border-white/5 bg-[#0b1520]/95 backdrop-blur-md transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Sidebar Header */}
        <div className="h-16 flex items-center gap-2.5 px-4 border-b border-white/5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-emerald-400 text-[#051018] font-bold text-sm">
            <Zap size={16} />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">
              AsyncSignals
            </h1>
            <p className="text-[10px] text-slate-500 -mt-0.5">
              Mission Control
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-0.5 p-3 overflow-y-auto h-[calc(100vh-16rem)]">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-white/10 text-white shadow-sm"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <item.icon size={18} className={isActive ? "text-white" : item.color} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-white/5 bg-[#0b1520]/95">
          <div className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-emerald-400 flex items-center justify-center text-xs font-bold text-[#051018]">
                {userName[0].toUpperCase()}
              </div>
              <div className="overflow-hidden flex-1 min-w-0">
                <p className="text-xs text-white truncate">{userName}</p>
                <p className="text-[10px] text-slate-500 truncate">{userEmail}</p>
              </div>
            </div>
            <button
              onClick={() => signOut({ callbackUrl: "/sign-in" })}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-slate-400 text-xs hover:bg-white/10 hover:text-rose-400 transition-colors"
            >
              <LogOut size={14} />
              Sign Out
            </button>
          </div>
          <div className="px-4 pb-3">
            <p className="text-[10px] text-slate-600">AsyncSignals v3.2</p>
            <p className="text-[10px] text-slate-600">Oracle-backed telemetry</p>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="sticky top-0 z-30 h-16 border-b border-white/5 bg-[#0b1520]/80 backdrop-blur-md flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
              <User size={14} className="text-slate-400" />
              <span className="text-xs text-slate-300">{userName}</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-6">
          <div className="max-w-[1410px] mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
