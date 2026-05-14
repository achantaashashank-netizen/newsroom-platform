import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function getNodeLabel(nodeName: string): string {
  const labels: Record<string, string> = {
    discovery_node: "News Discovery",
    verification_node: "Verification",
    summarization_node: "Summarization",
    media_node: "Media",
    human_approval_node: "Human Approval",
    publishing_node: "Publishing",
    reject_node: "Rejected",
  };
  return labels[nodeName] || nodeName;
}

export function getNodeIcon(nodeName: string): string {
  const icons: Record<string, string> = {
    discovery_node: "🔍",
    verification_node: "🛡",
    summarization_node: "✍",
    media_node: "🖼",
    human_approval_node: "👤",
    publishing_node: "📡",
    reject_node: "✗",
  };
  return icons[nodeName] || "⚙";
}
