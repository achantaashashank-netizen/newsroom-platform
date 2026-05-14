"use client";
import { useEffect, useRef } from "react";
import { useAgentLogStore } from "@/stores/agentLogStore";
import { useStoryStore } from "@/stores/storyStore";

export function useSSE(runId: string | null, onDone?: () => void) {
  const addEntry = useAgentLogStore((s) => s.addEntry);
  const applyUpdate = useStoryStore((s) => s.applyUpdate);
  const setApprovalRequired = useStoryStore((s) => s.setApprovalRequired);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;

    const token = localStorage.getItem("access_token") || "";
    // Next.js rewrites buffer SSE — connect directly to backend on port 8080
    const backendBase = `http://${window.location.hostname}:8080`;
    const es = new EventSource(`${backendBase}/api/stream/${runId}?token=${encodeURIComponent(token)}`);
    esRef.current = es;

    // SSE payload shape: { event, run_id, timestamp, data: { ...actual fields } }
    const handleAgentEvent = (type: string) => (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        const d = parsed.data ?? parsed;
        addEntry(runId, {
          type: type as "start" | "progress" | "done" | "error",
          node: d.node || "unknown",
          message: d.message || "",
          timestamp: d.timestamp || new Date().toISOString(),
          progress: d.progress,
          duration_ms: d.duration_ms,
        });
      } catch {}
    };

    es.addEventListener("agent_start", handleAgentEvent("start"));
    es.addEventListener("agent_progress", handleAgentEvent("progress"));
    es.addEventListener("agent_done", handleAgentEvent("done"));
    es.addEventListener("agent_error", (e: MessageEvent) => {
      handleAgentEvent("error")(e);
      onDone?.();
    });

    es.addEventListener("story_update", (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        applyUpdate(parsed.data ?? parsed);
      } catch {}
    });

    es.addEventListener("approval_required", (e: MessageEvent) => {
      try {
        const parsed = JSON.parse(e.data);
        setApprovalRequired(parsed.data ?? parsed);
        onDone?.();
      } catch {}
    });

    // Also done when rejected (reject_node fires agent_done then stream ends)
    es.addEventListener("heartbeat", () => {
      // keepalive — no action needed
    });

    es.onerror = () => {
      // EventSource auto-reconnects; backend replays Redis Stream on reconnect
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [runId, addEntry, applyUpdate, setApprovalRequired, onDone]);
}
