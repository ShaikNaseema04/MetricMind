"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  BarChart2,
  Database,
  Sparkles,
  Settings as SettingsIcon,
  Plus,
  Send,
  Pin,
  Menu,
  X,
  Code2,
  Eye,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ChevronRight,
  TrendingUp,
} from "lucide-react";

import dynamic from "next/dynamic";
import AnimatedAnalyticsHero from "@/components/AnimatedAnalyticsHero";
import MetricMindDataTable from "@/components/MetricMindDataTable";

const MetricMindEChart = dynamic(() => import("@/components/MetricMindEChart"), {
  ssr: false,
});
import ViewSqlModal, { SqlTrace } from "@/components/ViewSqlModal";
import ViewApiCallModal, { ApiTrace } from "@/components/ViewApiCallModal";
import DataSourcesView from "@/components/DataSourcesView";
import AnalyticsView from "@/components/AnalyticsView";
import IntegrationsView from "@/components/IntegrationsView";
import SettingsView from "@/components/SettingsView";
import { API_BASE_URL, fetchHealth } from "@/mock/api";

type ActiveTab = "chat" | "analytics" | "data_sources" | "integrations" | "settings";

interface KpiItem {
  label: string;
  value: unknown;
  formatted_value: string;
  description?: string;
}

interface ChartMeta {
  chart_type: "bar" | "line" | "donut" | "horizontal_bar" | "kpi" | "table";
  title: string;
  x_key?: string;
  y_keys: string[];
  series_names?: string[];
  x_label?: string;
  y_label?: string;
}

interface SecondaryBreakdown {
  dimension: string;
  title: string;
  data: Record<string, unknown>[];
  explanation: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  data?: Record<string, unknown>[];
  chart_meta?: ChartMeta | null;
  kpi_items?: KpiItem[];
  sql_trace?: SqlTrace;
  api_trace?: ApiTrace;
  secondary_breakdown?: SecondaryBreakdown;
  timestamp: string;
  isError?: boolean;
}

export default function MetricMindApp() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [backendConnected, setBackendConnected] = useState(true);

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [pinnedQuestions, setPinnedQuestions] = useState<string[]>([]);
  const [recentChats, setRecentChats] = useState<string[]>([]);

  // Modals state
  const [activeSqlTrace, setActiveSqlTrace] = useState<SqlTrace | null>(null);
  const [activeApiTrace, setActiveApiTrace] = useState<ApiTrace | null>(null);
  const [activeRawResponse, setActiveRawResponse] = useState<unknown>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check health periodically
  useEffect(() => {
    const checkConnection = async () => {
      const health = await fetchHealth();
      setBackendConnected(health !== null);
    };
    checkConnection();
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, []);

  // Auto scroll chat
  useEffect(() => {
    if (activeTab === "chat" && messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, activeTab]);

  const [conversationId, setConversationId] = useState<string>(() => `conv-${Date.now()}`);

  const handleSendQuestion = async (textToSend?: string) => {
    const question = (textToSend || inputValue).trim();
    if (!question || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setLoading(true);

    // Update recent chats
    if (!recentChats.includes(question)) {
      setRecentChats((prev) => [question, ...prev.slice(0, 5)]);
    }

    try {
      // Call frontend API route which proxies to FastAPI backend
      let res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, conversation_id: conversationId }),
      });

      if (!res.ok && res.status === 404) {
        res = await fetch(`${API_BASE_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, conversation_id: conversationId }),
        });
      }

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.error || `HTTP error ${res.status}`);
      }

      const data = await res.json();

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.explanation || data.answer || data.response || data.message || "Query processed successfully.",
        data: data.data || data.results,
        chart_meta: data.chart_meta,
        kpi_items: data.kpi_items,
        sql_trace: data.sql_trace,
        api_trace: data.api_trace,
        secondary_breakdown: data.secondary_breakdown,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Failed to connect to analytical engine";
      const errorAssistantMsg: Message = {
        id: `assistant-err-${Date.now()}`,
        role: "assistant",
        content: `Error executing analytical plan: ${errorMsg}. Please ensure the MetricMind backend is running at ${API_BASE_URL}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isError: true,
      };
      setMessages((prev) => [...prev, errorAssistantMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendQuestion();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setConversationId(`conv-${Date.now()}`);
    setActiveTab("chat");
  };

  const togglePin = (q: string) => {
    if (pinnedQuestions.includes(q)) {
      setPinnedQuestions(pinnedQuestions.filter((item) => item !== q));
    } else {
      setPinnedQuestions([...pinnedQuestions, q]);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#070e1c] text-slate-100 font-sans">
      {/* 1. LEFT SIDEBAR */}
      <aside
        className={`${
          sidebarOpen ? "w-64" : "w-0 -translate-x-full"
        } relative flex flex-col justify-between border-r border-slate-800/80 bg-[#060c18] transition-all duration-300 ease-in-out lg:static lg:translate-x-0 z-30`}
      >
        <div className="flex flex-col h-full overflow-y-auto p-4 custom-scrollbar">
          {/* Logo */}
          <div className="flex items-center gap-3 px-1 py-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-600 to-cyan-400 font-bold text-white shadow-lg shadow-indigo-900/40">
              M
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-white">MetricMind</div>
              <div className="text-[10px] font-semibold tracking-wider text-cyan-400">
                SEMANTIC BI
              </div>
            </div>
          </div>

          {/* New Chat Button */}
          <button
            onClick={handleNewChat}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 via-purple-600 to-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-purple-950/50 transition-all hover:opacity-95 hover:shadow-cyan-950/50"
          >
            <Plus size={15} />
            <span>New Chat</span>
          </button>

          {/* Workspace Nav Items */}
          <div className="mt-6">
            <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Workspace
            </div>
            <nav className="space-y-1">
              {[
                { id: "analytics", label: "Analytics", icon: BarChart2 },
                { id: "data_sources", label: "Data Sources", icon: Database },
                { id: "integrations", label: "Integrations", icon: Sparkles },
                { id: "settings", label: "Settings", icon: SettingsIcon },
              ].map((item) => {
                const IconComp = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id as ActiveTab)}
                    className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-medium transition-all ${
                      isActive
                        ? "border border-cyan-500/30 bg-gradient-to-r from-cyan-950/50 to-blue-950/30 text-cyan-300 shadow-sm"
                        : "text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
                    }`}
                  >
                    <IconComp
                      size={15}
                      className={isActive ? "text-cyan-400" : "text-slate-400"}
                    />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Pinned Section */}
          <div className="mt-6">
            <div className="px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Pinned
            </div>
            {pinnedQuestions.length === 0 ? (
              <p className="mt-1 px-2 text-[11px] text-slate-500">
                Pin important questions to keep them here.
              </p>
            ) : (
              <div className="mt-1 space-y-1">
                {pinnedQuestions.map((q) => (
                  <div
                    key={q}
                    className="group flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-900/60"
                  >
                    <button
                      onClick={() => {
                        setActiveTab("chat");
                        handleSendQuestion(q);
                      }}
                      className="truncate text-left font-normal hover:text-cyan-300"
                    >
                      {q}
                    </button>
                    <button
                      onClick={() => togglePin(q)}
                      className="opacity-0 group-hover:opacity-100 text-cyan-400 hover:text-cyan-200"
                    >
                      <Pin size={12} className="fill-cyan-400" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Suggested Section */}
          <div className="mt-6">
            <div className="px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Suggested
            </div>
            <div className="mt-1.5 space-y-1">
              {[
                "Show revenue by country",
                "Show profit by country",
                "Show monthly revenue trends",
                "Which product has the highest sales?",
                "What is the profit margin?",
              ].map((q) => {
                const isPinned = pinnedQuestions.includes(q);
                return (
                  <div
                    key={q}
                    className="group flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-900/60 transition-colors"
                  >
                    <button
                      onClick={() => {
                        setActiveTab("chat");
                        handleSendQuestion(q);
                      }}
                      className="flex items-center gap-2 truncate text-left hover:text-cyan-300"
                    >
                      <BarChart2 size={13} className="text-slate-500 group-hover:text-cyan-400 shrink-0" />
                      <span className="truncate">{q}</span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePin(q);
                      }}
                      className="text-slate-500 hover:text-cyan-400 ml-1.5 shrink-0"
                    >
                      <Pin size={12} className={isPinned ? "fill-cyan-400 text-cyan-400" : ""} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Chats Section */}
          <div className="mt-6">
            <div className="px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Recent Chats
            </div>
            {recentChats.length === 0 ? (
              <p className="mt-1 px-2 text-[11px] text-slate-500">No recent chats</p>
            ) : (
              <div className="mt-1 space-y-1">
                {recentChats.map((c, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setActiveTab("chat");
                      handleSendQuestion(c);
                    }}
                    className="w-full truncate rounded-lg px-2.5 py-1 text-left text-xs text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
                  >
                    {c}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* User Profile at Bottom */}
        <div className="border-t border-slate-800/80 p-3">
          <div className="flex items-center justify-between rounded-xl p-2 hover:bg-slate-900/50">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-violet-600 to-indigo-600 text-xs font-bold text-white shadow-md">
                N
              </div>
              <div>
                <div className="text-xs font-semibold text-white">Naseema</div>
                <div className="text-[10px] text-slate-400">Analyst</div>
              </div>
            </div>
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
          </div>
        </div>
      </aside>

      {/* 2. MAIN WORKSPACE */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="flex h-14 items-center justify-between border-b border-slate-800/80 bg-[#060d1b] px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <Menu size={18} />
            </button>
            <span className="text-xs font-medium text-slate-400">
              {activeTab === "chat" && "Agentic Semantic Chat"}
              {activeTab === "analytics" && "Executive BI Analytics"}
              {activeTab === "data_sources" && "Dataset & Column Mappings"}
              {activeTab === "integrations" && "Platform Connectors"}
              {activeTab === "settings" && "Preferences & Motion"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Real Connection Status Pill */}
            <div
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold ${
                backendConnected
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.2)]"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-400"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  backendConnected
                    ? "bg-emerald-400 shadow-[0_0_6px_#10b981]"
                    : "bg-amber-400"
                }`}
              />
              <span>{backendConnected ? "Connected" : "Reconnecting"}</span>
            </div>

            {/* Profile Avatar */}
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-violet-600 font-bold text-xs text-white">
              N
            </div>
          </div>
        </header>

        {/* Content Workspace Area */}
        <main className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          {activeTab === "analytics" && <AnalyticsView />}
          {activeTab === "data_sources" && <DataSourcesView />}
          {activeTab === "integrations" && <IntegrationsView />}
          {activeTab === "settings" && <SettingsView />}

          {activeTab === "chat" && (
            <div className="mx-auto flex h-full max-w-4xl flex-col justify-between">
              {/* WELCOME SCREEN (When no messages) */}
              {messages.length === 0 ? (
                <div className="my-auto flex flex-col items-center justify-center text-center animate-in fade-in duration-300">
                  {/* CONTINUOUS ANIMATED ANALYTICS HERO (Bars, Waves, Hill Areas) */}
                  <div className="mb-6 w-full">
                    <AnimatedAnalyticsHero />
                  </div>

                  <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">
                    Ask MetricMind anything
                  </h1>
                  <p className="mt-1 text-sm text-slate-400">
                    Turn your business data into clear answers and insights.
                  </p>
                </div>
              ) : (
                /* CHAT CONVERSATION THREAD */
                <div className="space-y-6 pb-6">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${
                        msg.role === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      {msg.role === "user" ? (
                        <div className="max-w-xl rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-xs text-white shadow-lg shadow-blue-950/40">
                          {msg.content}
                        </div>
                      ) : (
                        <div className="w-full space-y-4 rounded-2xl border border-slate-800 bg-[#091326]/90 p-5 shadow-2xl backdrop-blur-md">
                          {/* Assistant Header */}
                          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                            <div className="flex items-center gap-2">
                              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-tr from-cyan-400 to-blue-600 text-[10px] font-bold text-slate-950">
                                MM
                              </div>
                              <span className="text-xs font-semibold text-cyan-300">
                                MetricMind Analytical Response
                              </span>
                            </div>

                            {/* View SQL and View API Call Buttons */}
                            <div className="flex items-center gap-2">
                              {msg.sql_trace && (
                                <button
                                  onClick={() => setActiveSqlTrace(msg.sql_trace || null)}
                                  className="flex items-center gap-1 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-300 hover:bg-cyan-500/20"
                                >
                                  <Code2 size={13} />
                                  <span>View SQL</span>
                                </button>
                              )}
                              {msg.api_trace && (
                                <button
                                  onClick={() => {
                                    setActiveApiTrace(msg.api_trace || null);
                                    setActiveRawResponse(msg.data);
                                  }}
                                  className="flex items-center gap-1 rounded-lg border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-[11px] font-semibold text-violet-300 hover:bg-violet-500/20"
                                >
                                  <Eye size={13} />
                                  <span>View API Call</span>
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Natural Language Explanation */}
                          <div className="text-xs leading-relaxed text-slate-200">
                            {msg.content}
                          </div>

                          {/* KPI Badges */}
                          {msg.kpi_items && msg.kpi_items.length > 0 && (
                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                              {msg.kpi_items.map((kpi, kIdx) => (
                                <div
                                  key={kIdx}
                                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 shadow-sm"
                                >
                                  <div className="text-[10px] uppercase tracking-wider text-slate-400">
                                    {kpi.label}
                                  </div>
                                  <div className="mt-1 font-mono text-base font-bold text-white">
                                    {kpi.formatted_value}
                                  </div>
                                  {kpi.description && (
                                    <div className="mt-0.5 text-[10px] text-slate-500">
                                      {kpi.description}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Analytical Chart (ECharts) */}
                          {msg.chart_meta && msg.chart_meta.chart_type !== "kpi" && msg.data && msg.data.length > 0 && (
                            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
                              <h4 className="mb-2 text-xs font-semibold text-cyan-300">
                                {msg.chart_meta.title}
                              </h4>
                              <MetricMindEChart
                                chartType={msg.chart_meta.chart_type}
                                title={msg.chart_meta.title}
                                data={msg.data}
                                xKey={msg.chart_meta.x_key}
                                yKeys={msg.chart_meta.y_keys}
                                seriesNames={msg.chart_meta.series_names}
                                height={260}
                              />
                            </div>
                          )}

                          {/* Secondary Root Cause Breakdown Table */}
                          {msg.secondary_breakdown && (
                            <div className="space-y-2 rounded-xl border border-violet-900/40 bg-violet-950/20 p-4">
                              <div className="text-xs font-bold text-violet-300">
                                {msg.secondary_breakdown.title}
                              </div>
                              <p className="text-[11px] text-slate-300">
                                {msg.secondary_breakdown.explanation}
                              </p>
                              <div className="overflow-x-auto">
                                <table className="w-full text-left font-mono text-[11px] text-slate-300">
                                  <thead>
                                    <tr className="border-b border-violet-900/60 text-violet-400">
                                      <th className="py-1">Segment</th>
                                      <th className="py-1">Revenue</th>
                                      <th className="py-1">Profit</th>
                                      <th className="py-1">Margin %</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-violet-950/40">
                                    {msg.secondary_breakdown.data.map((r, i) => (
                                      <tr key={i}>
                                        <td className="py-1">{String(Object.values(r)[0])}</td>
                                        <td className="py-1">${Number(r.revenue || 0).toLocaleString()}</td>
                                        <td className="py-1">${Number(r.profit || 0).toLocaleString()}</td>
                                        <td className="py-1">{String(r.profit_margin ?? "")}%</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Data Table */}
                          {msg.data && msg.data.length > 1 && (
                            <MetricMindDataTable
                              data={msg.data}
                              title="Detailed Analytical Records"
                              pageSize={5}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  ))}

                  {loading && (
                    <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-[#081224] p-4 text-xs text-cyan-400">
                      <Sparkles className="animate-spin text-cyan-400" size={16} />
                      <span>Validating semantic plan and executing analytical query...</span>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}

              {/* CHAT INPUT BAR AT BOTTOM */}
              <div className="sticky bottom-0 pt-4">
                <div className="relative flex items-center rounded-2xl border border-blue-900/50 bg-[#09152b]/95 p-2 shadow-2xl shadow-cyan-950/20 backdrop-blur-md">
                  <div className="pl-3 pr-2 text-cyan-400">
                    <Sparkles size={16} />
                  </div>
                  <textarea
                    rows={1}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question about your business data..."
                    className="flex-1 resize-none bg-transparent py-2 text-xs text-white placeholder-slate-400 focus:outline-none"
                  />
                  <button
                    onClick={() => handleSendQuestion()}
                    disabled={!inputValue.trim() || loading}
                    className="ml-2 flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-blue-600 text-white shadow-md shadow-blue-900/40 transition-all hover:opacity-90 disabled:opacity-40"
                  >
                    <Send size={15} />
                  </button>
                </div>
                <div className="mt-2 text-center text-[10px] text-slate-500">
                  Press Enter to send · Shift + Enter for a new line
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* 3. MODALS */}
      <ViewSqlModal
        isOpen={Boolean(activeSqlTrace)}
        onClose={() => setActiveSqlTrace(null)}
        sqlTrace={activeSqlTrace}
      />

      <ViewApiCallModal
        isOpen={Boolean(activeApiTrace)}
        onClose={() => setActiveApiTrace(null)}
        apiTrace={activeApiTrace}
        rawResponse={activeRawResponse}
      />
    </div>
  );
}
