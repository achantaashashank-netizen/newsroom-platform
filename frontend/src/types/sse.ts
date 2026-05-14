export type SSEEventType =
  | "agent_start"
  | "agent_progress"
  | "agent_done"
  | "agent_error"
  | "story_update"
  | "approval_required"
  | "published"
  | "heartbeat";

export interface SSEEnvelope<T = unknown> {
  event: SSEEventType;
  run_id: string;
  timestamp: string;
  data: T;
}

export interface AgentLogEntry {
  id: string;
  type: "start" | "progress" | "done" | "error";
  node: string;
  message: string;
  timestamp: string;
  progress?: number;
  duration_ms?: number;
}
