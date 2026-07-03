"use client";

import { ComponentType, FormEvent, ReactNode, useEffect, useMemo, useRef, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  History,
  Link as LinkIcon,
  Loader2,
  Mail,
  Network,
  RefreshCw,
  Search,
  Server,
  Sparkles,
  Timer,
  Play,
  Info,
  Edit,
  Send,
  X,
  FileText,
  MousePointerClick,
  ChevronRight,
  TrendingUp,
  User,
  Cpu,
  Check,
  ArrowLeft,
  Target,
  Plus
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type NodeEvent = {
  id: string;
  event_id?: string;
  campaign_id: string;
  sequence: number;
  timestamp: string;
  type: "workflow_started" | "node_update" | "workflow_completed" | "workflow_failed";
  node: string;
  agent?: string;
  status: string;
  message: string;
  provider?: string;
  model?: string;
  duration?: number;
  is_simulated?: boolean;
  data?: JsonRecord;
  node_run?: NodeRun;
};

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
type JsonRecord = Record<string, JsonValue>;
type IconType = ComponentType<{ className?: string }>;

type Campaign = {
  campaign_id: string;
  our_url: string;
  target_url?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  business_profile?: JsonRecord;
  keywords?: string[];
  competitors?: string[];
  services?: string[];
  target_url_discovered?: string;
  contact_info?: JsonRecord;
  outreach_email?: JsonRecord;
  fit_score?: number;
  score_breakdown?: JsonRecord;
  analytics?: Record<string, number>;
  node_runs?: Record<string, NodeRun>;
  outreach_status?: string;
};

type NodeRun = {
  node: string;
  agent?: string;
  status?: string;
  provider?: string;
  provider_purpose?: string;
  model?: string;
  duration?: number;
  confidence?: number;
  is_simulated?: boolean;
  retry_count?: number;
  api_source?: string;
  cache_state?: string;
  raw_input?: JsonRecord;
  raw_output?: JsonRecord;
  structured_json?: JsonRecord;
  error?: string | null;
  score_breakdown?: JsonRecord;
};

type ProviderHealthEntry = {
  configured?: boolean;
  available?: boolean;
  mock?: boolean;
  stats?: any;
};

type ProviderHealth = {
  llm?: Record<string, ProviderHealthEntry>;
  search?: ProviderHealthEntry;
  mongodb?: ProviderHealthEntry;
  crawler?: ProviderHealthEntry;
};

// Fixed Node Order to match Backend Graph
const workflowNodes = [
  { id: "crawl_website", label: "Crawler", icon: Network },
  { id: "analyze_business", label: "BI", icon: BrainCircuit },
  { id: "extract_keywords", label: "Keywords", icon: Search },
  { id: "discover_competitors", label: "Competitors", icon: BarChart3 },
  { id: "discover_backlinks", label: "Backlinks", icon: LinkIcon },
  { id: "discover_contacts", label: "Contacts", icon: Mail },
  { id: "extract_services", label: "Services", icon: Database },
  { id: "qualify_opportunity", label: "Qualification", icon: Gauge },
  { id: "generate_outreach", label: "Outreach", icon: Sparkles },
];

function hostname(url?: string) {
  if (!url) return "New campaign";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function formatDuration(seconds?: number) {
  if (!seconds) return "0.0s";
  return `${seconds.toFixed(1)}s`;
}

function displayValue(value: JsonValue | undefined) {
  if (value === undefined || value === null || value === "") return "pending";
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : JSON.stringify(value);
}

function jsonForCopy(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function asArray(value: JsonValue | undefined): JsonValue[] {
  return Array.isArray(value) ? value : [];
}

function statusTone(status?: string) {
  if (!status) return "bg-zinc-800 text-zinc-300 border-zinc-700";
  if (status.includes("failed")) return "bg-red-950/60 text-red-200 border-red-800";
  if (status.includes("skipped") || status.includes("borderline")) return "bg-amber-950/60 text-amber-200 border-amber-800";
  if (status.includes("completed") || status.includes("generated") || status.includes("discovered") || status.includes("extracted") || status.includes("crawled") || status.includes("qualified") || status.includes("sent")) {
    return "bg-emerald-950/60 text-emerald-200 border-emerald-800";
  }
  return "bg-blue-950/60 text-blue-200 border-blue-800";
}

function StartPanel({ onStarted }: { onStarted: (id: string) => void }) {
  const [url, setUrl] = useState("https://www.boat-lifestyle.com/");
  const [targetUrl, setTargetUrl] = useState("");
  const [strategy, setStrategy] = useState("auto");
  const [error, setError] = useState("");
  const [isStarting, setIsStarting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setIsStarting(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/campaign/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ our_url: url, target_url: targetUrl || undefined, strategy }),
      });
      if (!response.ok) throw new Error("Failed to start campaign");
      const data = await response.json();
      onStarted(data.campaign_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start campaign");
    } finally {
      setIsStarting(false);
    }
  }

  const [campaigns, setCampaigns] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    const fetchCampaigns = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/campaigns`);
        if (!res.ok) return;
        const data = await res.json();
        if (mounted && data.campaigns && Array.isArray(data.campaigns)) {
          setCampaigns(data.campaigns);
        } else if (mounted && Array.isArray(data)) {
          setCampaigns(data);
        }
      } catch (err) {
        // Backend might be restarting, fail silently in UI
      }
    };
    fetchCampaigns();
    return () => { mounted = false; };
  }, []);

  return (
    <section className="mx-auto grid min-h-dvh w-full max-w-7xl grid-cols-1 items-start gap-10 px-6 py-10 xl:grid-cols-[1fr_420px]">
      <div className="max-w-3xl pt-10">
        <div className="mb-5 inline-flex items-center gap-2 border border-zinc-800 bg-zinc-950 px-3 py-1 text-xs text-zinc-400 backdrop-blur-md">
          <Activity className="h-3.5 w-3.5 text-emerald-300" />
          Production workflow console
        </div>
        <h1 className="text-balance text-5xl font-semibold leading-[0.95] text-zinc-50 md:text-7xl lg:text-8xl">
          AI outreach operating system
        </h1>
        <p className="mt-6 max-w-2xl text-pretty text-lg leading-8 text-zinc-400">
          Start a campaign and watch crawler, intelligence, discovery, qualification, and outreach stages synchronize from backend state in real time. Features deterministic reasoning, AI explainability, and full provider transparency.
        </p>
        <div className="mt-10 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4">
          {["Exact-once SSE", "Provider fallback", "Mongo replay", "Explainability"].map((item) => (
            <div key={item} className="border border-zinc-800 bg-zinc-950/70 p-4 backdrop-blur-sm transition-all hover:border-emerald-900/50">
              <CheckCircle2 className="mb-3 h-4 w-4 text-emerald-300" />
              <div className="text-xs font-medium text-zinc-200">{item}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-8 pt-10">
        <form onSubmit={submit} className="border border-zinc-800 bg-zinc-950/90 p-6 shadow-2xl shadow-black/50 backdrop-blur-xl">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-zinc-50">Launch campaign</h2>
            <p className="mt-2 text-sm text-zinc-500">Displayed data comes from the API and live event stream.</p>
          </div>
          <label className="mb-2 block text-sm font-medium text-zinc-300" htmlFor="our-url">Company URL</label>
          <input
            id="our-url"
            required
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            className="mb-4 w-full border border-zinc-800 bg-black/50 px-4 py-3 text-sm text-zinc-100 outline-none transition focus:border-emerald-400 focus:bg-zinc-950"
          />
          <label className="mb-2 block text-sm font-medium text-zinc-300" htmlFor="target-url">Optional target URL (skips discovery)</label>
          <input
            id="target-url"
            type="url"
            value={targetUrl}
            onChange={(event) => setTargetUrl(event.target.value)}
            placeholder="https://example.com/resource"
            className="mb-4 w-full border border-zinc-800 bg-black/50 px-4 py-3 text-sm text-zinc-100 outline-none transition focus:border-emerald-400 focus:bg-zinc-950"
          />
          <label className="mb-2 block text-sm font-medium text-zinc-300" htmlFor="strategy">Discovery Strategy</label>
          <select
            id="strategy"
            value={strategy}
            onChange={(event) => setStrategy(event.target.value)}
            className="mb-5 w-full border border-zinc-800 bg-black/50 px-4 py-3 text-sm text-zinc-100 outline-none transition focus:border-emerald-400 focus:bg-zinc-950 appearance-none"
          >
            <option value="auto">Auto-Select (AI Planner)</option>
            <option value="guest_post">Guest Post</option>
            <option value="resource_page">Resource Page</option>
            <option value="startup_directory">Startup Directory</option>
            <option value="business_directory">Business Directory</option>
            <option value="industry_blog">Industry Blog</option>
            <option value="podcast">Podcast</option>
            <option value="broken_link">Broken Link</option>
            <option value="unlinked_brand_mention">Unlinked Brand Mention</option>
          </select>
          {error && (
            <div className="mb-4 border border-red-800 bg-red-950/50 p-3 text-sm text-red-200">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={isStarting}
            className="group flex w-full items-center justify-center gap-2 bg-emerald-400 px-4 py-3 text-sm font-semibold text-zinc-950 transition-all hover:bg-emerald-300 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isStarting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Network className="h-4 w-4 transition-transform group-hover:scale-110" />}
            Start workflow
          </button>
        </form>

        {campaigns.length === 0 && (
          <div className="mt-4 flex justify-end">
            <button 
              type="button"
              onClick={async () => {
                try {
                  const res = await fetch(`${API_BASE}/api/v1/campaigns`);
                  if (!res.ok) return;
                  const data = await res.json();
                  if (data.campaigns && Array.isArray(data.campaigns)) {
                    setCampaigns(data.campaigns);
                  }
                } catch (e) {}
              }}
              className="text-xs text-zinc-500 hover:text-emerald-400 flex items-center gap-1 transition-colors"
            >
              <RefreshCw className="h-3 w-3" /> Load previous campaigns
            </button>
          </div>
        )}

        {campaigns.length > 0 && (
          <div className="border border-zinc-800 bg-zinc-950/90 p-6 shadow-2xl backdrop-blur-xl">
            <h2 className="text-sm font-bold text-zinc-50 uppercase tracking-wide mb-4">Campaign History</h2>
            <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-2">
              {campaigns.map(camp => (
                <button 
                  key={camp.campaign_id} 
                  onClick={() => onStarted(camp.campaign_id)}
                  className="text-left p-3 border border-zinc-800 bg-black/40 hover:border-emerald-500/50 transition-all text-xs"
                >
                  <div className="text-zinc-200 font-semibold mb-1 truncate">{hostname(camp.our_url)}</div>
                  <div className="flex items-center justify-between text-zinc-500">
                    <span>{new Date(camp.created_at).toLocaleDateString()}</span>
                    <span className={camp.status === 'completed' ? 'text-emerald-400' : ''}>{camp.status.replace(/_/g, ' ')}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function Dashboard({ campaignId, onReset, onSelectCampaign }: { campaignId: string; onReset: () => void; onSelectCampaign: (id: string) => void }) {
  const [events, setEvents] = useState<NodeEvent[]>([]);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [providerHealth, setProviderHealth] = useState<ProviderHealth>({});
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  
  const [connected, setConnected] = useState(false);
  const [isReplaying, setIsReplaying] = useState(false);
  
  // Explainability
  const [inspectNodeId, setInspectNodeId] = useState<string | null>(null);
  
  const completedRef = useRef<boolean>(false);
  const seenEvents = useRef<Set<string>>(new Set());

  // Outreach management
  const [isEditingOutreach, setIsEditingOutreach] = useState(false);
  const [outreachSubject, setOutreachSubject] = useState("");
  const [outreachBody, setOutreachBody] = useState("");
  const [isSending, setIsSending] = useState(false);

  // Phase 4 & 5
  const [mockEmailBody, setMockEmailBody] = useState("We'd love to publish this! Let me know the price.");
  const [mockReplyResult, setMockReplyResult] = useState<any>(null);
  const [auditReport, setAuditReport] = useState<any>(null);

  const handleMockReply = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/campaign/${campaignId}/mock_reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email_body: mockEmailBody })
      });
      if (res.ok) setMockReplyResult(await res.json());
    } catch (e) { console.error(e); }
  };

  const handleVerifyBacklink = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/campaign/${campaignId}/verify_backlink`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: campaign?.target_url || "https://example.com/post" })
      });
      if (res.ok) alert(JSON.stringify(await res.json(), null, 2));
    } catch (e) { console.error(e); }
  };

  const handleProviderAudit = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/campaign/${campaignId}/provider_audit`);
      if (res.ok) setAuditReport(await res.json());
    } catch (e) { console.error(e); }
  };

  const loadData = useCallback(async () => {
    try {
      const fetchWithCatch = (url: string) => fetch(url).catch(() => ({ ok: false, json: async () => null }));
      const [campRes, campsRes, healthRes, analyticsRes] = await Promise.all([
        fetchWithCatch(`${API_BASE}/api/v1/campaign/${campaignId}`),
        fetchWithCatch(`${API_BASE}/api/v1/campaigns`),
        fetchWithCatch(`${API_BASE}/api/v1/providers/health`),
        fetchWithCatch(`${API_BASE}/api/v1/campaign/${campaignId}/analytics`)
      ]);
      
      if ((campRes as any).ok) {
        const data = await (campRes as any).json();
        setCampaign(data);
        if (data.status?.includes("completed") || data.status === "failed") {
          completedRef.current = true;
        }
        if (data.outreach_email) {
          setOutreachSubject(data.outreach_email.subject || "");
          setOutreachBody(data.outreach_email.body || "");
        }
      }
      if (campsRes.ok) setCampaigns((await campsRes.json()).campaigns ?? []);
      if (healthRes.ok) setProviderHealth(await healthRes.json());
      if (analyticsRes && analyticsRes.ok) setAnalyticsData(await analyticsRes.json());
      
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    }
  }, [campaignId]);

  useEffect(() => {
    completedRef.current = false;
    setEvents([]);
    loadData();
  }, [campaignId, loadData]);

  // SSE Stream
  useEffect(() => {
    // If we know it's already completed from the fetch, don't even open SSE unless we are replaying
    if (completedRef.current && !isReplaying) return;

    seenEvents.current = new Set();
    const source = new EventSource(`${API_BASE}/api/v1/campaign/${campaignId}/stream`);
    
    source.onopen = () => setConnected(true);
    source.onerror = () => {
      setConnected(false);
      // Close strictly if completed to prevent infinite polling
      if (completedRef.current) {
        source.close();
      }
    };
    
    source.onmessage = (event) => {
      if (event.data === ": heartbeat") return;
      try {
        const data: NodeEvent = JSON.parse(event.data);
        if (seenEvents.current.has(data.id)) return;
        seenEvents.current.add(data.id);
        
        setEvents((prev) => [...prev, data]);
        
        if (data.data) {
          setCampaign((prev) => ({ ...(prev ?? { campaign_id: campaignId, our_url: "", status: "running" }), ...data.data }) as Campaign);
        }
        
        if (data.type === "workflow_completed" || data.type === "workflow_failed") {
          completedRef.current = true;
          source.close(); // Close immediately!
          setConnected(false);
          loadData(); // Final refresh
          setIsReplaying(false);
        }
      } catch (e) {
        console.error("Error parsing SSE", e);
      }
    };

    return () => {
      source.close();
    };
  }, [campaignId, isReplaying, loadData]);

  const latestByNode = useMemo(() => {
    const map = new Map<string, NodeEvent>();
    for (const event of events) {
      if (event.type === "node_update") map.set(event.node, event);
    }
    return map;
  }, [events]);

  const handleReplay = async () => {
    setEvents([]);
    setIsReplaying(true);
    completedRef.current = false;
    // Re-trigger the SSE effect which will replay events from sequence 0
  };

  const handleSendOutreach = async () => {
    setIsSending(true);
    try {
      // First save changes if editing
      if (isEditingOutreach) {
        await fetch(`${API_BASE}/api/v1/campaign/${campaignId}/outreach`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subject: outreachSubject, body: outreachBody })
        });
      }
      // Send
      const res = await fetch(`${API_BASE}/api/v1/campaign/${campaignId}/outreach/send`, {
        method: "POST"
      });
      if (res.ok) {
        await loadData();
        setIsEditingOutreach(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSending(false);
    }
  };

  const completedNodes = workflowNodes.filter(n => {
    const status = latestByNode.get(n.id)?.status || campaign?.node_runs?.[n.id]?.status;
    return status && !status.includes("failed") && status !== "waiting";
  }).length;
  
  const pipelineConf = campaign?.analytics?.pipeline_confidence;
  const confDisplay = pipelineConf !== undefined ? `${Math.round(pipelineConf * 100)}%` : "pending";
  
  const inspectNodeData = inspectNodeId ? (latestByNode.get(inspectNodeId)?.node_run || campaign?.node_runs?.[inspectNodeId]) : null;

  return (
    <main className="flex min-h-dvh flex-col overflow-x-hidden bg-[#080908] text-zinc-100 lg:flex-row">
      <aside className="border-b border-zinc-800 bg-zinc-950/90 p-4 lg:w-72 lg:shrink-0 lg:border-b-0 lg:border-r lg:overflow-y-auto z-20 hidden md:block">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <BrainCircuit className="h-5 w-5 text-emerald-400" />
            Backlink OS
          </div>
          <button onClick={onReset} className="flex items-center gap-1.5 border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-xs text-zinc-300 transition hover:border-emerald-500 hover:text-emerald-100" aria-label="New Campaign">
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
        </div>

        <section className="mb-6">
          <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            <Server className="h-3.5 w-3.5" />
            Provider Health
          </h2>
          <div className="space-y-1.5">
            {Object.entries(providerHealth.llm ?? {}).map(([name, value]) => (
              <div key={name} className="flex items-center justify-between border border-zinc-800 bg-black/40 px-3 py-2 text-xs">
                <span className="capitalize text-zinc-300">{name}</span>
                <div className="flex items-center gap-2">
                  <span className={value.available && value.configured ? "text-emerald-400" : "text-amber-400"}>
                    {value.configured ? (value.available ? "ready" : "open") : "missing"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            <History className="h-3.5 w-3.5" />
            Campaign History
          </h2>
          <div className="space-y-2">
            {campaigns.map((item) => (
              <button key={item.campaign_id} onClick={() => onSelectCampaign(item.campaign_id)} className={`block w-full border border-zinc-800 p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-emerald-500/50 ${item.campaign_id === campaignId ? 'bg-emerald-950/20 border-emerald-900/50' : 'bg-black/30 hover:bg-zinc-900'}`}>
                <div className="truncate text-sm font-medium text-zinc-200">{hostname(item.our_url)}</div>
                <div className="mt-2 flex items-center justify-between text-xs text-zinc-500">
                  <span className="truncate max-w-[120px]">{item.status.replace(/_/g, ' ')}</span>
                  <span className={item.fit_score && item.fit_score >= 5 ? 'text-emerald-400 font-medium' : ''}>{item.fit_score ? `${item.fit_score}/10` : "pending"}</span>
                </div>
              </button>
            ))}
          </div>
        </section>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col overflow-hidden relative">
        <header className="border-b border-zinc-800 bg-zinc-950/80 px-4 py-3 md:px-6 md:py-4 backdrop-blur-md z-10 flex-shrink-0">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <button className="md:hidden border border-zinc-800 p-2" onClick={onReset}><RefreshCw className="h-4 w-4"/></button>
              <div>
                <p className="break-all text-xs text-zinc-500 font-mono">{campaignId}</p>
                <h1 className="mt-1 text-xl font-semibold text-zinc-50 md:text-2xl truncate">{hostname(campaign?.our_url)}</h1>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {completedRef.current && (
                <button onClick={handleReplay} disabled={isReplaying} className="flex items-center gap-2 border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-medium hover:bg-zinc-800 transition-colors disabled:opacity-50">
                  <Play className="h-3.5 w-3.5" /> Replay
                </button>
              )}
              <div aria-live="polite" className={`flex items-center gap-2 border px-3 py-1.5 text-xs font-medium ${connected ? "border-emerald-800/50 bg-emerald-950/40 text-emerald-300" : (completedRef.current ? "border-zinc-800 bg-zinc-900 text-zinc-400" : "border-amber-800/50 bg-amber-950/40 text-amber-300")}`}>
                <span className={`h-2 w-2 rounded-full ${connected ? "animate-pulse bg-emerald-400" : (completedRef.current ? "bg-zinc-600" : "bg-amber-400")}`} />
                {connected ? "SSE Connected" : (completedRef.current ? "Completed" : "Reconnecting...")}
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          {/* Main Content Area */}
          <div className="grid grid-cols-1 gap-6 p-4 md:p-6 lg:grid-cols-[1fr_400px] xl:grid-cols-[1fr_450px]">
            
            {/* Left Column - Execution & Graph */}
            <div className="min-w-0 space-y-6">
              
              {/* Analytics Metrics */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Metric icon={CheckCircle2} label="Nodes" value={`${completedNodes}/${workflowNodes.length}`} />
                <Metric icon={Timer} label="Exec Time" value={analyticsData ? `${analyticsData.total_execution_time}s` : formatDuration(events.at(-1)?.duration)} />
                <Metric 
                  icon={Gauge} 
                  label="Fit Score" 
                  value={campaign?.fit_score ? `${campaign.fit_score}/10` : "pending"} 
                  color={campaign?.fit_score && campaign.fit_score >= 7 ? "text-emerald-400" : campaign?.fit_score && campaign.fit_score >= 5 ? "text-amber-400" : "text-zinc-50"}
                />
                <Metric icon={Activity} label="Confidence" value={confDisplay} />
              </div>

              {/* Phase 5 Extra Metrics */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <Metric icon={TrendingUp} label="Avg DA [MOCK]" value={analyticsData?.average_da > 0 ? analyticsData.average_da : 68} color="text-emerald-400" tooltip="Moz/Ahrefs APIs are paid, so this data is simulated based on domain attributes." />
                <Metric 
                  icon={BrainCircuit} 
                  label="Strategy" 
                  value={String(campaign?.analytics?.strategy || campaign?.strategy || "guest_post").replace(/_/g, " ")} 
                  tooltip={campaign?.search_queries?.length > 0 ? `Query: ${campaign.search_queries[0]}` : "AI selected backlink strategy."}
                />
                <Metric icon={LinkIcon} label="Live Links [MOCK]" value={analyticsData?.live_backlinks > 0 ? analyticsData.live_backlinks : 14} color="text-emerald-400" tooltip="Actual backlink placement requires CMS credentials or authorization for third-party sites which we don't have, so this metric is simulated." />
                <Metric icon={Mail} label="Open Rate [MOCK]" value="45%" color="text-emerald-400" tooltip="Requires SendGrid/SMTP webhooks which are not currently provisioned." />
                <Metric icon={Send} label="Reply Rate [MOCK]" value="12%" color="text-emerald-400" tooltip="Requires IMAP/SendGrid inbound parsing which is not currently provisioned." />
              </div>

              {/* Execution Graph */}
              <section className="border border-zinc-800 bg-zinc-950/60 p-5 backdrop-blur-sm">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-lg flex items-center gap-2">
                      <Network className="h-5 w-5 text-emerald-400"/> Execution Graph
                    </h2>
                    <span className="text-xs text-zinc-500">Live deterministic execution</span>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {workflowNodes.map((node, index) => {
                    const event = latestByNode.get(node.id);
                    const run = event?.node_run ?? campaign?.node_runs?.[node.id];
                    const Icon = node.icon;
                    const isActive = event || run;
                    return (
                      <motion.div
                        key={node.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.05 }}
                        className={`relative flex flex-col justify-between border p-4 transition-all ${isActive ? statusTone(run?.status || event?.status) : "border-zinc-800 bg-black/30 text-zinc-600"}`}
                      >
                        <div className="flex items-start justify-between">
                          <Icon className={`h-5 w-5 ${isActive ? "" : "opacity-50"}`} />
                          {isActive && (
                            <button 
                              onClick={() => setInspectNodeId(node.id)}
                              className="p-1.5 hover:bg-black/20 transition-colors rounded-sm"
                              title="Inspect Node"
                            >
                              <Info className="h-3.5 w-3.5 opacity-70" />
                            </button>
                          )}
                        </div>
                        <div className="mt-3">
                          <div className="text-sm font-semibold tracking-wide">{node.label}</div>
                          <div className="mt-1 flex items-center gap-2 text-[10px] uppercase opacity-70">
                            {run?.status || event?.status || "waiting"}
                          </div>
                        </div>
                        <div className="mt-3 flex items-center justify-between border-t border-black/10 pt-2 text-xs opacity-80">
                          <span className="flex items-center gap-1"><Clock3 className="h-3 w-3"/>{formatDuration(run?.duration || event?.duration)}</span>
                          {run?.provider && <span className="font-mono text-[9px] bg-black/20 px-1 py-0.5">{run.provider.substring(0,10)}</span>}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </section>

              {/* Knowledge Graph Visualization */}
              <section className="border border-zinc-800 bg-zinc-950/60 p-5 overflow-hidden">
                <h2 className="mb-5 font-semibold text-lg flex items-center gap-2">
                  <Share2 className="h-5 w-5 text-emerald-400"/> Knowledge Graph
                </h2>
                <div className="relative py-4 px-2 flex flex-col gap-6 text-sm">
                  {/* Simplistic Tree representation */}
                  <GraphNode label="Industry" value={campaign?.business_profile?.industry} icon={Database} delay={0.1} />
                  
                  <div className="pl-6 border-l-2 border-emerald-900/30 ml-4 flex flex-col gap-6 relative">
                    <GraphNode label="Competitors" values={campaign?.competitors} icon={BarChart3} delay={0.2} />
                    <GraphNode label="Keywords" values={campaign?.keywords} icon={Search} delay={0.3} />
                    
                    <div className="pl-6 border-l-2 border-emerald-900/30 ml-4 flex flex-col gap-6">
                      <GraphNode label="Target Match" value={campaign?.target_url} icon={LinkIcon} delay={0.4} />
                      
                      <div className="pl-6 border-l-2 border-emerald-900/30 ml-4 flex flex-col gap-6">
                        <GraphNode 
                          label="Contact Verification" 
                          value={campaign?.contact_info?.email ? `${campaign.contact_info.email} (${campaign.contact_info.verification_status})` : undefined} 
                          icon={Mail} 
                          delay={0.5} 
                          highlight={campaign?.contact_info?.verification_status?.includes("verified")}
                        />
                        <GraphNode 
                          label="LinkedIn" 
                          values={campaign?.contact_info?.linkedin_profiles as any[]} 
                          icon={Network} 
                          delay={0.6} 
                        />
                        <GraphNode 
                          label="Contact Forms" 
                          values={campaign?.contact_info?.contact_forms as any[]} 
                          icon={FileText} 
                          delay={0.7} 
                        />
                        <GraphNode 
                          label="Submit Guidelines" 
                          values={campaign?.contact_info?.submission_guidelines as any[]} 
                          icon={FileText} 
                          delay={0.8} 
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </section>

            </div>

            {/* Right Column - Insights & Timeline */}
            <div className="space-y-6">
              
              {/* Qualification Insight */}
              <InsightCard title="Qualification Reasoning" icon={Gauge}>
                 {campaign?.score_breakdown ? (
                   <div className="space-y-4">
                     <div className="flex items-end justify-between">
                        <div>
                          <div className="text-3xl font-bold text-zinc-100">{campaign.fit_score}<span className="text-lg text-zinc-500">/10</span></div>
                          <div className="text-xs text-zinc-500 uppercase tracking-wider mt-1">{campaign.status.replace(/_/g, " ")}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs font-mono text-zinc-500">Raw: {campaign.score_breakdown.computed_raw}</div>
                        </div>
                     </div>
                     
                     <div className="space-y-2 mt-4">
                        <ProgressBar label="Industry (25%)" val={campaign.score_breakdown.industry_relevance} />
                        <ProgressBar label="Authority (25%)" val={campaign.score_breakdown.domain_authority} />
                        <ProgressBar label="Content (15%)" val={campaign.score_breakdown.content_freshness} />
                        <ProgressBar label="Keywords (20%)" val={campaign.score_breakdown.keyword_overlap} />
                        <ProgressBar label="Editorial (10%)" val={campaign.score_breakdown.editorial_relevance} />
                     </div>

                     {campaign.qualification_reason && (
                       <div className="mt-4 space-y-2 text-xs">
                         <div>
                           <span className="font-semibold text-zinc-300">Target Audience:</span>
                           <ul className="list-disc pl-5 mt-1 opacity-90">
                             {(() => {
                               try {
                                 const parsed = typeof campaign.bi_insights === 'string' ? JSON.parse(campaign.bi_insights) : (campaign.bi_insights || {});
                                 return Array.isArray(parsed?.audience) ? parsed.audience.map((a: any, i: number) => (
                                   <li key={i}>{typeof a === 'string' ? a : (a.category ? `${a.category}: ${a.description || ''}` : JSON.stringify(a))}</li>
                                 )) : null;
                               } catch { return null; }
                             })()}
                           </ul>
                         </div>
                         <div>
                           <span className="font-semibold text-zinc-300">Key Products/Services:</span>
                           <ul className="list-disc pl-5 mt-1 opacity-90">
                             {(() => {
                               try {
                                 const parsed = typeof campaign.bi_insights === 'string' ? JSON.parse(campaign.bi_insights) : (campaign.bi_insights || {});
                                 return Array.isArray(parsed?.services) ? parsed.services.map((s: any, i: number) => (
                                   <li key={i}>{typeof s === 'string' ? s : JSON.stringify(s)}</li>
                                 )) : null;
                               } catch { return null; }
                             })()}
                           </ul>
                         </div>
                         {(() => {
                           try {
                             const parsed = typeof campaign.qualification_reason === 'string' ? JSON.parse(campaign.qualification_reason) : (campaign.qualification_reason || {});
                             return Array.isArray(parsed?.reasons) ? parsed.reasons.map((r: any, i: number) => (
                               <div key={i} className="flex items-start gap-2 text-emerald-200 bg-emerald-950/20 p-2 border border-emerald-900/30 mt-2">
                                 <Check className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                                 <span>{typeof r === 'string' ? r : JSON.stringify(r)}</span>
                               </div>
                             )) : null;
                           } catch { return null; }
                         })()}
                       </div>
                     )}
                   </div>
                 ) : (
                   <div className="text-sm text-zinc-500 italic p-4 text-center">Pending deterministic qualification...</div>
                 )}
              </InsightCard>

              {/* Outreach Management */}
              <InsightCard title="Outreach Management" icon={Send}>
                {campaign?.outreach_email ? (
                  <div className="space-y-3 relative">
                    {/* Status badge */}
                    {campaign.outreach_status && (
                      <div className={`absolute -top-10 right-0 text-[10px] uppercase font-bold px-2 py-1 ${campaign.outreach_status === 'sent' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
                        {campaign.outreach_status}
                      </div>
                    )}
                    
                    <div className="flex gap-2">
                      <input 
                        className={`w-full bg-black/40 border border-zinc-800 p-2 text-sm font-medium ${isEditingOutreach ? 'focus:border-emerald-500 outline-none text-white' : 'text-zinc-300'}`}
                        value={outreachSubject}
                        onChange={e => setOutreachSubject(e.target.value)}
                        readOnly={!isEditingOutreach}
                        placeholder="Subject"
                      />
                    </div>
                    <textarea 
                      className={`w-full bg-black/40 border border-zinc-800 p-3 text-sm min-h-[200px] leading-relaxed resize-none ${isEditingOutreach ? 'focus:border-emerald-500 outline-none text-white' : 'text-zinc-400'}`}
                      value={outreachBody}
                      onChange={e => setOutreachBody(e.target.value)}
                      readOnly={!isEditingOutreach}
                    />
                    
                    <div className="flex items-center gap-2 mt-4 pt-4 border-t border-zinc-800">
                      {isEditingOutreach ? (
                        <>
                          <button onClick={handleSendOutreach} disabled={isSending} className="flex-1 bg-emerald-500 text-zinc-950 text-sm font-bold py-2 px-3 flex justify-center items-center gap-2 hover:bg-emerald-400 transition-colors disabled:opacity-50">
                            {isSending ? <Loader2 className="h-4 w-4 animate-spin"/> : <Send className="h-4 w-4"/>} 
                            Save & Send
                          </button>
                          <button onClick={() => setIsEditingOutreach(false)} className="px-3 py-2 border border-zinc-700 hover:bg-zinc-800 text-sm">Cancel</button>
                        </>
                      ) : (
                        <>
                          {campaign.outreach_status !== 'sent' && (
                            <button onClick={handleSendOutreach} disabled={isSending} className="flex-1 bg-emerald-950 text-emerald-400 border border-emerald-800 text-sm font-bold py-2 px-3 flex justify-center items-center gap-2 hover:bg-emerald-900 transition-colors">
                              {isSending ? <Loader2 className="h-4 w-4 animate-spin"/> : <Send className="h-4 w-4"/>} 
                              Approve & Send
                            </button>
                          )}
                          <button onClick={() => setIsEditingOutreach(true)} className="flex-1 border border-zinc-800 bg-zinc-900 text-zinc-300 text-sm font-medium py-2 px-3 flex justify-center items-center gap-2 hover:bg-zinc-800 transition-colors">
                            <Edit className="h-4 w-4"/> Edit
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-zinc-500 italic p-4 text-center border border-dashed border-zinc-800">
                    Draft will appear here if opportunity qualifies.
                  </div>
                )}
              </InsightCard>

              {/* Generated Article */}
              <InsightCard title="Generated Article [MOCK CMS]" icon={FileText} tooltip="Article placement is mocked because direct automated publishing requires direct integration with target site CMS systems (like WordPress API) which we do not have access to for random sites.">
                {campaign?.generated_article ? (
                  <div className="space-y-3">
                    <div className="text-sm font-semibold text-zinc-200 border-b border-zinc-800 pb-2">
                      {campaign.generated_article.title}
                    </div>
                    <div className="max-h-[250px] overflow-y-auto text-xs text-zinc-400 prose prose-invert prose-p:leading-relaxed prose-h1:text-sm prose-h1:font-bold prose-h2:text-xs prose-h2:font-semibold">
                      <div dangerouslySetInnerHTML={{ __html: campaign.generated_article.body }} />
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-zinc-500 italic p-4 text-center border border-dashed border-zinc-800">
                    Article will appear here if generated.
                  </div>
                )}
              </InsightCard>

              {/* Timeline */}
              <InsightCard title="Live Timeline" icon={Activity}>
                <div className="space-y-3 max-h-[250px] overflow-y-auto pr-2" aria-live="polite">
                  <AnimatePresence initial={false}>
                    {events.map((event) => (
                      <motion.div
                        key={event.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`grid gap-2 border-l-2 pl-3 py-1 ${event.status.includes('failed') ? 'border-red-500' : 'border-zinc-700'}`}
                      >
                        <div className="text-[10px] font-mono text-zinc-500">{new Date(event.timestamp).toLocaleTimeString()}</div>
                        <div>
                          <div className="text-sm text-zinc-200">{event.message}</div>
                          {event.provider && <div className="mt-1 text-[10px] text-zinc-500 font-mono">[{event.provider}]</div>}
                        </div>
                      </motion.div>
                    ))}
                    {events.length === 0 && <div className="text-xs text-zinc-600 italic">Waiting for events...</div>}
                  </AnimatePresence>
                </div>
              </InsightCard>

              {/* Simulation & Audit (Phase 4/5) */}
              <InsightCard title="Simulation & Audit [MOCK]" icon={Server} tooltip="These interactive utilities let you simulate downstream integrations like checking if a backlink went live or receiving an inbound reply, as we do not have an active SMTP/IMAP listener configured for a real domain.">
                <div className="space-y-4">
                  <div className="text-xs text-zinc-500 italic border-l-2 border-emerald-900 pl-2">
                    These actions simulate downstream processes (inbound emails and CMS integrations) for testing purposes.
                  </div>
                  <div className="border border-zinc-800 p-3 bg-black/40">
                    <h3 className="text-xs font-semibold uppercase text-zinc-400 mb-2">Backlink Verification</h3>
                    <button onClick={handleVerifyBacklink} className="w-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-sm font-bold py-1.5 px-3 hover:bg-emerald-900 transition-colors">
                      Verify Mock Backlink
                    </button>
                  </div>

                  <div className="border border-zinc-800 p-3 bg-black/40">
                    <h3 className="text-xs font-semibold uppercase text-zinc-400 mb-2">Reply Handling (Mock)</h3>
                    <textarea 
                      className="w-full bg-black/40 border border-zinc-800 p-2 text-xs text-zinc-300 mb-2 h-16"
                      value={mockEmailBody}
                      onChange={e => setMockEmailBody(e.target.value)}
                    />
                    <button onClick={handleMockReply} className="w-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-sm font-bold py-1.5 px-3 hover:bg-emerald-900 transition-colors">
                      Simulate Inbound Reply
                    </button>
                    
                    {mockReplyResult && (
                      <div className="mt-3 text-xs bg-zinc-950 border border-zinc-800 p-2">
                        <div className="font-semibold mb-1 text-zinc-200">Classification: {mockReplyResult.classification}</div>
                        <div className="text-zinc-400">{mockReplyResult.draft_response}</div>
                      </div>
                    )}
                  </div>

                  <div className="border border-zinc-800 p-3 bg-black/40">
                    <h3 className="text-xs font-semibold uppercase text-zinc-400 mb-2">Provider Audit</h3>
                    <button onClick={handleProviderAudit} className="w-full bg-zinc-800 text-zinc-200 text-sm font-bold py-1.5 px-3 hover:bg-zinc-700 transition-colors">
                      Run Compliance Audit
                    </button>
                    {auditReport && (
                      <div className="mt-3 text-xs bg-zinc-900 p-2 border border-zinc-700 max-h-[150px] overflow-y-auto">
                        <div className={`font-semibold mb-1 ${auditReport.compliance_status === 'pass' ? 'text-emerald-400' : 'text-red-400'}`}>
                          Status: {auditReport.compliance_status.toUpperCase()}
                        </div>
                        {auditReport.issues.length > 0 ? (
                          <ul className="list-disc pl-4 text-red-300">
                            {auditReport.issues.map((i: any, idx: number) => (
                              <li key={idx}>{i.node}: {i.issue}</li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-emerald-300">No issues found. LLM did not perform search/crawl tasks.</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </InsightCard>

            </div>
          </div>
        </div>
      </section>

      {/* AI Explainability Drawer */}
      <AnimatePresence>
        {inspectNodeId && inspectNodeData && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
              onClick={() => setInspectNodeId(null)}
            />
            <motion.div
              initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 h-full w-full max-w-2xl bg-zinc-950 border-l border-zinc-800 z-50 flex flex-col shadow-2xl"
            >
              <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/50">
                <div className="flex items-center gap-3">
                  <Cpu className="h-5 w-5 text-emerald-400" />
                  <div>
                    <h3 className="font-semibold">{inspectNodeData.task || inspectNodeId}</h3>
                    <p className="text-xs text-zinc-400 font-mono">{inspectNodeData.agent || "System"}</p>
                  </div>
                </div>
                <button onClick={() => setInspectNodeId(null)} className="p-2 hover:bg-zinc-800 rounded-md transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <HoverField label="Status" value={inspectNodeData.status} />
                  <HoverField label="Duration" value={formatDuration(inspectNodeData.duration)} />
                  <HoverField label="Provider" value={inspectNodeData.provider} />
                  <HoverField label="Purpose" value={inspectNodeData.provider_purpose} />
                </div>
                
                {inspectNodeData.error && (
                  <div className="border border-red-900/50 bg-red-950/20 p-4 text-sm text-red-300 whitespace-pre-wrap font-mono">
                    {inspectNodeData.error}
                  </div>
                )}

                {inspectNodeData.raw_input && (
                  <div>
                    <h4 className="text-xs font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Input State Snapshot</h4>
                    <pre className="bg-black/50 border border-zinc-800 p-4 text-[11px] font-mono text-zinc-300 overflow-x-auto rounded-sm">
                      {jsonForCopy(inspectNodeData.raw_input)}
                    </pre>
                  </div>
                )}

                {inspectNodeData.raw_output && (
                  <div>
                    <h4 className="text-xs font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Raw API Output</h4>
                    <pre className="bg-black/50 border border-zinc-800 p-4 text-[11px] font-mono text-emerald-300/80 overflow-x-auto rounded-sm">
                      {jsonForCopy(inspectNodeData.raw_output)}
                    </pre>
                  </div>
                )}

                {inspectNodeData.structured_json && (
                  <div>
                    <h4 className="text-xs font-semibold text-zinc-500 mb-2 uppercase tracking-wider">Final Parsed JSON</h4>
                    <pre className="bg-black/50 border border-zinc-800 p-4 text-[11px] font-mono text-blue-300/80 overflow-x-auto rounded-sm">
                      {jsonForCopy(inspectNodeData.structured_json)}
                    </pre>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

    </main>
  );
}

// Helpers for components

function Metric({ icon: Icon, label, value, color = "text-zinc-50", tooltip }: { icon: IconType; label: string; value: string, color?: string, tooltip?: string }) {
  return (
    <div className="border border-zinc-800 bg-zinc-950/70 p-4 shadow-sm relative group">
      <Icon className="mb-3 h-5 w-5 text-zinc-500" />
      <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold flex items-center gap-1">
        {label}
        {tooltip && <Info className="h-3 w-3 text-zinc-400 cursor-help" />}
      </div>
      <div className={`mt-1 text-xl font-bold tracking-tight ${color}`}>{value}</div>
      {tooltip && (
        <div className="absolute left-0 bottom-full mb-2 hidden w-48 bg-zinc-800 p-2 text-xs text-zinc-200 shadow-xl group-hover:block z-50">
          {tooltip}
        </div>
      )}
    </div>
  );
}

function InsightCard({ title, icon: Icon, children, tooltip }: { title: string; icon: IconType; children: ReactNode; tooltip?: string }) {
  return (
    <section className="border border-zinc-800 bg-zinc-950/70 p-5 shadow-sm relative">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-zinc-100 uppercase tracking-wide group">
        <Icon className="h-4 w-4 text-emerald-500" />
        {title}
        {tooltip && (
          <div className="relative inline-flex items-center">
            <Info className="h-4 w-4 text-zinc-400 cursor-help" />
            <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden w-64 bg-zinc-800 p-2 text-xs text-zinc-200 shadow-xl group-hover:block z-50 font-normal normal-case tracking-normal">
              {tooltip}
            </div>
          </div>
        )}
      </h2>
      {children}
    </section>
  );
}

function HoverField({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-zinc-800 bg-black/40 p-3 rounded-sm">
      <div className="text-[10px] text-zinc-500 uppercase font-semibold">{label}</div>
      <div className="mt-1 truncate text-sm font-medium text-zinc-200">{value || "-"}</div>
    </div>
  );
}

function ProgressBar({ label, val }: { label: string, val: any }) {
  const num = typeof val === 'number' ? val : 0;
  return (
    <div>
      <div className="flex justify-between text-[10px] text-zinc-400 mb-1">
        <span>{label}</span>
        <span>{Math.round(num * 100)}%</span>
      </div>
      <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden">
        <div className="h-full bg-emerald-500 transition-all duration-1000" style={{ width: `${num * 100}%` }} />
      </div>
    </div>
  );
}

function GraphNode({ label, value, values, icon: Icon, delay, highlight }: { label: string, value?: any, values?: any[], icon: any, delay: number, highlight?: boolean }) {
  if (!value && (!values || values.length === 0)) return null;
  
  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay }}
      className={`relative flex items-center gap-3 p-2 border ${highlight ? 'border-emerald-500/50 bg-emerald-950/20' : 'border-zinc-800 bg-black/40'} rounded-sm z-10`}
    >
      <div className={`p-1.5 rounded-sm ${highlight ? 'bg-emerald-900/50 text-emerald-400' : 'bg-zinc-900 text-zinc-400'}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">{label}</div>
        <div className="text-sm text-zinc-200 truncate mt-0.5">
          {value ? displayValue(value) : values?.slice(0,3).join(", ") + (values && values.length > 3 ? "..." : "")}
        </div>
      </div>
    </motion.div>
  );
}

// Custom Share2 icon as it's not imported at the top
function Share2(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  );
}

export default function App() {
  const [campaignId, setCampaignIdState] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const saved = window.localStorage.getItem("activeCampaignId");
    if (saved) setCampaignIdState(saved);
  }, []);

  const setCampaignId = (id: string | null) => {
    setCampaignIdState(id);
    if (id) window.localStorage.setItem("activeCampaignId", id);
    else window.localStorage.removeItem("activeCampaignId");
  };

  if (!isMounted) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[#080908]">
        <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-[#080908] font-sans text-zinc-100 selection:bg-emerald-900/50">
      {campaignId ? (
        <Dashboard key={campaignId} campaignId={campaignId} onReset={() => setCampaignId(null)} onSelectCampaign={setCampaignId} />
      ) : (
        <StartPanel onStarted={setCampaignId} />
      )}
    </div>
  );
}
