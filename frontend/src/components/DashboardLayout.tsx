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
    <div className="min-h-screen bg-[#06111a] text-slate-200">
      {/* Top Header */}
      <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-white/5 bg-[#0b1520]/80 backdrop-blur-md">
        <div className="flex h-full items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-white/5"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <div className="flex items-center gap-2.5">
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
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
            
            <div className="flex items-center gap-2">
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
                <User size={14} className="text-slate-400" />
                <span className="text-xs text-slate-300">{userName}</span>
              </div>
              <button
                onClick={() => signOut({ callbackUrl: "/sign-in" })}
                className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-rose-400 transition-colors"
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside
        className={`fixed top-16 left-0 z-40 h-[calc(100vh-4rem)] w-64 transform border-r border-white/5 bg-[#0b1520]/90 backdrop-blur-md transition-transform duration-200 lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <nav className="flex flex-col gap-1 p-3">
          {navItems.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              onClick={() => setSidebarOpen(false)}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
            >
              <item.icon size={18} className={item.color} />
              {item.name}
            </Link>
          ))}
        </nav>
        
        <div className="absolute bottom-16 left-0 right-0 p-4 border-t border-white/5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-emerald-400 flex items-center justify-center text-xs font-bold text-[#051018]">
              {userName[0].toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs text-white truncate">{userName}</p>
              <p className="text-[10px] text-slate-500 truncate">{userEmail}</p>
            </div>
          </div>
        </div>
        
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/5">
          <p className="text-[10px] text-slate-600">AsyncSignals v3.2</p>
          <p className="text-[10px] text-slate-600">Oracle-backed telemetry</p>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="lg:ml-64 pt-16 min-h-screen">
        <div className="p-4 lg:p-6 max-w-[1410px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
