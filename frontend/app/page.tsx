
"use client";

import { useEffect, useState } from "react";
import AIChat from "./components/ai-chat";
import DocumentManager from "./components/document-manager";

import {
  Activity,
  BrainCircuit,
  ChevronDown,
  CircleHelp,
  Clock3,
  FileText,
  FolderOpen,
  LayoutDashboard,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
  X,
  Zap,
} from "lucide-react";

const activity = [
  {
    question: "How many vacation days do employees receive?",
    time: "Recent API test",
    status: "Answered",
  },
  {
    question: "When does health insurance become active?",
    time: "Example question",
    status: "Answered",
  },
  {
    question: "What are the retirement plan eligibility rules?",
    time: "Example question",
    status: "Answered",
  },
];

const bars = [34, 48, 39, 62, 52, 75, 58, 86, 65, 92, 72, 100];

const navigation = [
  { label: "Overview", href: "#overview", icon: LayoutDashboard },
  { label: "Knowledge Base", href: "#knowledge", icon: FolderOpen },
  { label: "AI Assistant", href: "#assistant", icon: MessageSquare },
  { label: "Activity", href: "#activity", icon: Activity },
];


export default function Home() {
  const greeting = "Welcome back";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("overview");
  const [documentsCount, setDocumentsCount] = useState(0);

  useEffect(() => {

    const sections = navigation
      .map((item) => document.getElementById(item.href.slice(1)))
      .filter((section): section is HTMLElement => section !== null);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (a, b) => b.intersectionRatio - a.intersectionRatio
          );

        if (visible[0]) {
          setActiveSection(visible[0].target.id);
        }
      },
      {
        rootMargin: "-15% 0px -65% 0px",
        threshold: [0, 0.2, 0.5],
      }
    );

    sections.forEach((section) => observer.observe(section));

    return () => observer.disconnect();
  }, []);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <main className="min-h-screen scroll-smooth bg-[#f7f8fc] text-slate-900">
      <div className="flex min-h-screen">

        {/* Desktop sidebar */}
        <aside className="hidden w-[260px] shrink-0 flex-col bg-[#111827] text-white lg:flex">
          <div className="flex h-[76px] items-center gap-3 border-b border-white/10 px-6">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-600">
              <BrainCircuit size={23} />
            </div>

            <div className="min-w-0">
              <p className="text-sm font-bold tracking-wide">
                NEXUS AI
              </p>
              <p className="whitespace-nowrap text-[10px] tracking-[1.5px] text-slate-400">
                KNOWLEDGE PLATFORM
              </p>
            </div>
          </div>

          <div className="px-4 py-7">
            <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-[2px] text-slate-400">
              Workspace
            </p>

            <nav className="space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = activeSection === item.href.slice(1);

                return (
                  <a
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "text-slate-300 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    <Icon size={18} />
                    {item.label}
                  </a>
                );
              })}
            </nav>

            <p className="mb-3 mt-9 px-3 text-xs font-semibold uppercase tracking-[2px] text-slate-400">
              Administration
            </p>

            <nav className="space-y-1">
              <a
                href="#activity"
                className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                <Users size={18} />
                Team activity
              </a>

              <a
                href="#settings"
                onClick={(event) => event.preventDefault()}
                className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                <Settings size={18} />
                Settings
              </a>

              <a
                href="#help"
                onClick={(event) => event.preventDefault()}
                className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              >
                <CircleHelp size={18} />
                Help & Support
              </a>
            </nav>
          </div>

          <div className="mt-auto p-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                <ShieldCheck size={17} className="text-emerald-400" />
                System status
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Dashboard preview
              </div>

              <p className="mt-2 text-xs text-slate-400">
                Live API health is available separately.
              </p>
            </div>

            <div className="mt-5 flex items-center gap-3 border-t border-white/10 pt-5">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-violet-500 text-xs font-bold">
                SR
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold">Workspace Admin</p>
                <p className="text-xs text-slate-400">Administrator</p>
              </div>

              <MoreHorizontal size={18} className="text-slate-400" />
            </div>
          </div>
        </aside>

        {/* Main workspace */}
        <section className="min-w-0 flex-1">
          <header className="sticky top-0 z-40 flex h-[76px] items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur sm:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Open navigation menu"
                aria-expanded={mobileMenuOpen}
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 lg:hidden"
              >
                {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
              </button>

              <div>
                <p className="text-xs text-slate-500">
                  Workspace / Overview
                </p>
                <p className="text-sm font-semibold text-slate-800">
                  Enterprise Knowledge
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-500 sm:flex">
                <Search size={15} />
                Search workspace
                <span className="rounded border border-slate-200 px-1.5 py-0.5 text-xs">
                  ⌘ K
                </span>
              </div>

              <button
                type="button"
                aria-label="Workspace options"
                className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <MoreHorizontal size={19} />
              </button>

              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                SR
              </div>
            </div>
          </header>

          {/* Mobile navigation */}
          {mobileMenuOpen && (
            <div className="fixed inset-x-0 top-[76px] z-30 border-b border-slate-200 bg-white p-4 shadow-lg lg:hidden">
              <nav className="space-y-1">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeSection === item.href.slice(1);

                  return (
                    <a
                      key={item.href}
                      href={item.href}
                      onClick={closeMobileMenu}
                      className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                        isActive
                          ? "bg-blue-50 text-blue-700"
                          : "text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <Icon size={19} />
                      {item.label}
                    </a>
                  );
                })}
              </nav>
            </div>
          )}

          <div className="mx-auto max-w-[1500px] space-y-7 p-5 sm:p-8">

            {/* Welcome hero */}
            <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 p-6 text-white shadow-lg sm:p-8">
              <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
              <div className="pointer-events-none absolute -bottom-24 right-1/3 h-48 w-48 rounded-full bg-violet-300/20 blur-3xl" />

              <div className="relative z-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-[2px] text-blue-100">
                    Enterprise AI workspace
                  </p>

                  <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                    {greeting}, welcome back.
                  </h1>

                  <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100 sm:text-base">
                    Your organization&apos;s knowledge, connected and ready to explore.
                  </p>
                </div>

                <a
                  href="#assistant"
                  className="inline-flex items-center justify-center gap-2 self-start rounded-xl bg-white px-5 py-3 text-sm font-semibold text-blue-700 shadow-md transition hover:-translate-y-0.5 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
                >
                  <Sparkles size={17} />
                  Ask AI Assistant
                </a>
              </div>
            </section>

            {/* KPI cards */}
            <div
              id="overview"
              className="scroll-mt-24 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
            >
              {[
                {
                  title: "Documents",
                  value: String(documentsCount).padStart(2, "0"),
                  detail: "Indexed PDFs",
                  icon: FileText,
                  color: "blue",
                  comingSoon: false,
                },
                {
                  title: "Questions answered",
                  value: "—",
                  detail: "Usage analytics not connected",
                  icon: MessageSquare,
                  color: "violet",
                  comingSoon: true,
                },
                {
                  title: "Knowledge coverage",
                  value: "—",
                  detail: "Evaluation pending",
                  icon: BrainCircuit,
                  color: "emerald",
                  comingSoon: true,
                },
                {
                  title: "API protection",
                  value: "Active",
                  detail: "Authentication enabled",
                  icon: ShieldCheck,
                  color: "amber",
                  comingSoon: false,
                },
              ].map((card) => {
                const Icon = card.icon;

                const iconColor =
                  card.color === "blue"
                    ? "bg-gradient-to-br from-blue-500 to-blue-600"
                    : card.color === "violet"
                    ? "bg-gradient-to-br from-violet-500 to-violet-600"
                    : card.color === "emerald"
                    ? "bg-gradient-to-br from-emerald-500 to-emerald-600"
                    : "bg-gradient-to-br from-amber-400 to-amber-500";

                return (
                  <div
                    key={card.title}
                    className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-900/5 transition duration-200 hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="flex min-h-[2.5rem] items-center text-sm font-medium text-slate-600">
                        {card.title}
                      </p>

                      <div
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${iconColor}`}
                      >
                        <Icon size={19} />
                      </div>
                    </div>

                    <div className="mt-4 flex items-center gap-2">
                      <p className="text-2xl font-bold tracking-tight tabular-nums text-slate-900">
                        {card.value}
                      </p>

                      {card.comingSoon && (
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
                          Coming soon
                        </span>
                      )}
                    </div>

                    <p className="mt-2 text-xs text-slate-500">
                      {card.detail}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Analytics and AI assistant */}
            <div className="grid gap-6 xl:grid-cols-[1.55fr_1fr]">
              <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-900/5 transition hover:shadow-md sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-base font-bold text-slate-800">
                      Query activity
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                      Sample visual — live usage data not connected yet
                    </p>
                  </div>

                  <button
                    type="button"
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    Last 12 periods
                    <ChevronDown size={14} />
                  </button>
                </div>

                <div className="relative mt-10 h-[190px] border-b border-slate-200">
                  <div
                    className="pointer-events-none absolute inset-0 flex flex-col justify-between"
                    aria-hidden="true"
                  >
                    {[0, 1, 2, 3].map((line) => (
                      <div
                        key={line}
                        className="w-full border-t border-dashed border-slate-200"
                      />
                    ))}
                  </div>

                  <div className="relative flex h-full items-end gap-2 sm:gap-4">
                    {bars.map((height, index) => (
                      <div
                        key={index}
                        className="group relative flex h-full flex-1 flex-col justify-end"
                      >
                        <span className="absolute -top-7 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-white opacity-0 shadow-md transition group-hover:opacity-100 group-focus-within:opacity-100">
                          {height}
                        </span>

                        <div
                          tabIndex={0}
                          aria-label={`Sample activity value ${height}`}
                          className="w-full cursor-default rounded-t-md bg-gradient-to-t from-blue-600 to-violet-400 opacity-80 transition duration-200 group-hover:opacity-100 group-hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                          style={{ height: `${height}%` }}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 flex justify-between text-xs text-slate-500">
                  <span>Period 1</span>
                  <span>Period 4</span>
                  <span>Period 8</span>
                  <span>Period 12</span>
                </div>
              </section>

              <section
                id="assistant"
                className="scroll-mt-24 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-900/5 transition hover:shadow-md"
              >
                <AIChat />
              </section>
            </div>

            {/* Knowledge base and activity */}
            <div className="grid gap-6 xl:grid-cols-[1.55fr_1fr]">
              <section
                id="knowledge"
                className="scroll-mt-24 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-900/5 transition hover:shadow-md"
              >
                <div className="flex items-center justify-between border-b border-slate-100 p-5">
                  <div>
                    <h2 className="text-base font-bold text-slate-800">
                      Knowledge Base
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                      Documents currently indexed in the RAG knowledge base
                    </p>
                  </div>

                  <span className="rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700">
                    {documentsCount} documents
                  </span>
                </div>

                <DocumentManager onCountChange={setDocumentsCount} />
              </section>

              <section
                id="activity"
                className="scroll-mt-24 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-900/5 transition hover:shadow-md"
              >
                <div className="border-b border-slate-100 p-5">
                  <h2 className="text-base font-bold text-slate-800">
                    Recent activity
                  </h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Example questions from our API tests
                  </p>
                </div>

                <div className="divide-y divide-slate-100 px-5">
                  {activity.map((item) => (
                    <div
                      key={item.question}
                      className="rounded-lg py-4 transition hover:bg-slate-50"
                    >
                      <p className="text-sm font-medium leading-5 text-slate-700">
                        {item.question}
                      </p>

                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1 text-xs text-slate-500">
                          <Clock3 size={13} />
                          {item.time}
                        </span>

                        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                          {item.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <footer className="flex flex-col justify-between gap-2 border-t border-slate-200 py-5 text-xs text-slate-500 sm:flex-row">
              <p>© 2026 Nexus AI · Enterprise Knowledge Platform</p>
              <p className="flex items-center gap-2">
                <Zap size={13} />
                Dashboard prototype · Analytics are illustrative
              </p>
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
}
