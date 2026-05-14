"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { PanelGroup, Panel, PanelResizeHandle } from "react-resizable-panels";
import { Play, Search, LogOut } from "lucide-react";
import { storyApi } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { useStoryStore } from "@/stores/storyStore";
import { AgentLogPanel } from "@/components/agent/AgentLogPanel";
import { StoryPreview } from "@/components/story/StoryPreview";
import { ApprovalPanel } from "@/components/approval/ApprovalPanel";
import { TrendingPanel } from "@/components/trending/TrendingPanel";

export default function NewsroomPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const setStory = useStoryStore((s) => s.setStory);
  const setPendingApproval = useStoryStore((s) => s.setApprovalRequired);
  const reset = useStoryStore((s) => s.reset);

  // Auth guard
  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
    }
  }, [router]);

  // Load existing story if ?run_id= is in the URL (opened from Stories list)
  useEffect(() => {
    const paramRunId = searchParams.get("run_id");
    if (!paramRunId) return;
    reset();
    setRunId(paramRunId);
    storyApi.getByRunId(paramRunId).then((res) => {
      const s = res.data;
      setStory(s);
      setQuery(s.query || "");
      // If it's pending approval, surface the approval panel
      if (s.approval_status === "pending" && s.status === "pending_approval") {
        setPendingApproval({
          story_id: s.id,
          run_id: paramRunId,
          headline: s.headline || s.query,
          confidence_tier: s.confidence_tier,
        });
      }
    }).catch(console.error);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Pipeline done when approval fires or agent_error fires
  const handleDone = useCallback(() => setIsRunning(false), []);

  useSSE(runId, handleDone);

  function handleTrendingGenerate(topicQuery: string) {
    setQuery(topicQuery);
    // Small delay to let state settle before triggering run
    setTimeout(() => {
      if (!isRunning) {
        setIsRunning(true);
        reset();
        storyApi.run(topicQuery.trim()).then((res) => {
          const { run_id, story_id } = res.data;
          setRunId(run_id);
          setStory({
            id: story_id,
            run_id,
            query: topicQuery.trim(),
            status: "discovering",
            language: "en",
            approval_status: "pending",
            triggered_by: "manual",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
        }).catch((e) => {
          console.error(e);
          setIsRunning(false);
        });
      }
    }, 50);
  }

  async function handleRun() {
    if (!query.trim() || isRunning) return;
    setIsRunning(true);
    reset();
    try {
      const res = await storyApi.run(query.trim());
      const { run_id, story_id } = res.data;
      setRunId(run_id);
      setStory({
        id: story_id,
        run_id,
        query: query.trim(),
        status: "discovering",
        language: "en",
        approval_status: "pending",
        triggered_by: "manual",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (e) {
      console.error(e);
      setIsRunning(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    router.replace("/login");
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f] overflow-hidden">
      {/* Top bar */}
      <div className="h-12 border-b border-white/[0.06] flex items-center px-4 gap-4 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-white/90 tracking-tight">⚡ Newsroom</span>
          <span className="text-[10px] text-white/25 font-mono">AI Editorial Platform</span>
        </div>

        <div className="flex-1 flex items-center gap-2 max-w-xl">
          <div className="flex-1 relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRun()}
              placeholder="Enter news topic to discover and verify..."
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-lg pl-8 pr-3 py-1.5 text-sm text-white/80 placeholder-white/25 outline-none focus:border-indigo-500/50 focus:bg-white/[0.07] transition-all"
            />
          </div>
          <motion.button
            onClick={handleRun}
            disabled={!query.trim() || isRunning}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-1.5 bg-indigo-500/90 hover:bg-indigo-500 disabled:bg-white/[0.06] disabled:text-white/30 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
          >
            <Play size={11} />
            {isRunning ? "Running..." : "Run Pipeline"}
          </motion.button>
          <TrendingPanel onGenerate={handleTrendingGenerate} />
        </div>

        <div className="ml-auto flex items-center gap-3">
          <a href="/stories" className="text-xs text-white/40 hover:text-white/70 transition-colors">Stories</a>
          <a href="/settings" className="text-xs text-white/40 hover:text-white/70 transition-colors">Settings</a>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-xs text-white/30 hover:text-white/60 transition-colors"
          >
            <LogOut size={12} />
            Logout
          </button>
        </div>
      </div>

      {/* 3-Panel layout */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="horizontal" className="h-full">
          {/* Left — Agent Logs */}
          <Panel defaultSize={22} minSize={16} maxSize={35}>
            <div className="h-full glass border-r border-white/[0.06]">
              <AgentLogPanel runId={runId} isLive={isRunning} />
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-white/[0.04] hover:bg-indigo-500/30 transition-colors cursor-col-resize" />

          {/* Center — Story Preview */}
          <Panel defaultSize={52} minSize={35}>
            <div className="h-full glass border-r border-white/[0.06]">
              <StoryPreview />
            </div>
          </Panel>

          <PanelResizeHandle className="w-1 bg-white/[0.04] hover:bg-indigo-500/30 transition-colors cursor-col-resize" />

          {/* Right — Approval Panel */}
          <Panel defaultSize={26} minSize={20} maxSize={38}>
            <div className="h-full glass">
              <ApprovalPanel runId={runId} />
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
}
