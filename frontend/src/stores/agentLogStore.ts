import { create } from "zustand";
import { AgentLogEntry } from "@/types/sse";

interface AgentLogStore {
  logs: Record<string, AgentLogEntry[]>;
  addEntry: (runId: string, entry: Omit<AgentLogEntry, "id">) => void;
  clearLogs: (runId: string) => void;
}

export const useAgentLogStore = create<AgentLogStore>((set) => ({
  logs: {},

  addEntry: (runId, entry) =>
    set((state) => ({
      logs: {
        ...state.logs,
        [runId]: [
          ...(state.logs[runId] || []),
          { ...entry, id: `${Date.now()}-${Math.random()}` },
        ],
      },
    })),

  clearLogs: (runId) =>
    set((state) => ({
      logs: { ...state.logs, [runId]: [] },
    })),
}));
