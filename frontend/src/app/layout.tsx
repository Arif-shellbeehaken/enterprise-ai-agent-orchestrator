import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Enterprise AI Agent Orchestrator",
  description: "HITL-governed multi-agent orchestration platform",
};

const nav = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/agents", label: "Agents" },
  { href: "/workflows", label: "Approvals" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex">
        {/* Sidebar */}
        <aside className="w-56 shrink-0 border-r border-slate-700 bg-slate-900 flex flex-col">
          <div className="p-5 border-b border-slate-700">
            <h1 className="text-sm font-bold tracking-tight text-blue-400">
              AI Agent Orchestrator
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">Enterprise HITL Platform</p>
          </div>
          <nav className="flex-1 p-3 space-y-1">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block px-3 py-2 rounded-md text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="p-4 border-t border-slate-700 text-xs text-slate-500">
            v0.1.0 · 2026 Stack
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-auto">
          <div className="max-w-6xl mx-auto p-6 md:p-8">{children}</div>
        </main>
      </body>
    </html>
  );
}
