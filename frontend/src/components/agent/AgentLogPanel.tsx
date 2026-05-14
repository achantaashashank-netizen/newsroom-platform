"use client";
import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAgentLogStore } from "@/stores/agentLogStore";
import { AgentLogEntry } from "@/types/sse";
import { LiveIndicator } from "./LiveIndicator";
import { cn, getNodeIcon, getNodeLabel } from "@/lib/utils";

interface AgentLogPanelProps {
  runId: string | null;
  isLive: boolean;
}

function LogEntry({ entry }: { entry: AgentLogEntry }) {
  const typeColors = {
    start: "text-indigo-400",
    progress: "text-blue-300",
    done: "text-emerald-400",
    error: "text-red-400",
  };
  const typeSymbols = {
    start: "▶",
    progress: "◦",
    done: "✓",
    error: "✗",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className="flex gap-2 py-1.5 px-3 hover:bg-white/[0.03] rounded-md group"
    >
      <span className={cn("text-xs mt-0.5 shrink-0 font-mono", typeColors[entry.type])}>
        {typeSymbols[entry.type]}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-[10px] text-white/30">{getNodeIcon(entry.node)}</span>
          <span className="text-[10px] font-medium text-white/40 uppercase tracking-wide">
            {getNodeLabel(entry.node)}
          </span>
        </div>
        <p className="text-xs text-white/70 leading-relaxed break-words">{entry.message}</p>
        {entry.progress !== undefined && entry.type === "progress" && (
          <div className="mt-1.5 h-0.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-indigo-500/70 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${entry.progress}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}

export function AgentLogPanel({ runId, isLive }: AgentLogPanelProps) {
  const logs = useAgentLogStore((s) => (runId ? s.logs[runId] || [] : []));
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs.length]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-white/50 uppercase tracking-widest">Agent Logs</span>
        </div>
        <LiveIndicator isLive={isLive} />
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-2 space-y-0.5"
      >
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-white/20">
            <div className="text-3xl">⚡</div>
            <p className="text-xs text-center px-4">
              Start a pipeline run to see real-time agent execution logs
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((entry) => (
              <LogEntry key={entry.id} entry={entry} />
            ))}
          </AnimatePresence>
        )}
      </div>

      {logs.length > 0 && (
        <div className="px-4 py-2 border-t border-white/[0.06]">
          <p className="text-[10px] text-white/25">{logs.length} log entries</p>
        </div>
      )}
    </div>
  );
}
