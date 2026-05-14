"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { storyApi } from "@/lib/api";
import { Story } from "@/types/story";
import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  published: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  approved: "bg-indigo-500/15 text-indigo-400 border-indigo-500/25",
  pending_approval: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  rejected: "bg-red-500/15 text-red-400 border-red-500/25",
  failed: "bg-red-500/15 text-red-400 border-red-500/25",
  discovering: "bg-white/[0.06] text-white/40 border-white/10",
  verifying: "bg-white/[0.06] text-white/40 border-white/10",
  summarizing: "bg-white/[0.06] text-white/40 border-white/10",
  media: "bg-white/[0.06] text-white/40 border-white/10",
  publishing: "bg-blue-500/15 text-blue-400 border-blue-500/25",
};

const TIER_COLORS: Record<string, string> = {
  high: "text-emerald-400",
  medium: "text-amber-400",
  low: "text-red-400",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function StoriesPage() {
  const router = useRouter();
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await storyApi.list(50, 0);
      setStories(res.data);
    } catch {
      setError("Failed to load stories");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    load();
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <div className="border-b border-white/[0.06] px-6 py-3 flex items-center gap-4">
        <button
          onClick={() => router.push("/newsroom")}
          className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors"
        >
          <ArrowLeft size={13} />
          Newsroom
        </button>
        <span className="text-sm font-bold text-white/90 tracking-tight">⚡ Story Archive</span>
        <button
          onClick={load}
          disabled={loading}
          className="ml-auto flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6">
        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-4">
            {error}
          </p>
        )}

        {loading && !stories.length && (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <motion.div
                key={i}
                className="h-24 bg-white/[0.04] rounded-xl"
                animate={{ opacity: [0.4, 0.7, 0.4] }}
                transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.1 }}
              />
            ))}
          </div>
        )}

        {!loading && !stories.length && (
          <div className="text-center py-20 text-white/25">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-sm">No stories yet. Run a pipeline from the Newsroom.</p>
          </div>
        )}

        <div className="space-y-3">
          {stories.map((story, i) => (
            <motion.div
              key={story.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              onClick={() => router.push(`/newsroom?run_id=${story.run_id}`)}
              className="glass-card p-4 hover:bg-white/[0.06] transition-colors cursor-pointer group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h2 className="text-sm font-semibold text-white/90 leading-snug truncate group-hover:text-white transition-colors">
                    {story.headline || <span className="text-white/30 italic">{story.query}</span>}
                  </h2>
                  {story.sub_headline && (
                    <p className="text-xs text-white/45 mt-0.5 truncate">{story.sub_headline}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <span className="text-[10px] text-white/30">{formatDate(story.created_at)}</span>
                    {story.confidence_tier && (
                      <span className={cn("text-[10px] font-medium uppercase tracking-wide", TIER_COLORS[story.confidence_tier])}>
                        {story.confidence_tier} confidence
                        {story.overall_confidence !== undefined && ` · ${Math.round(story.overall_confidence * 100)}%`}
                      </span>
                    )}
                    {story.triggered_by !== "manual" && (
                      <span className="text-[10px] text-indigo-400/60 font-medium">⚡ Auto-discovered</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <span className={cn(
                    "text-[10px] font-medium px-2 py-0.5 rounded-full border capitalize",
                    STATUS_COLORS[story.status] ?? "bg-white/[0.06] text-white/40 border-white/10",
                  )}>
                    {story.status.replace("_", " ")}
                  </span>
                  {story.hashtags && story.hashtags.length > 0 && (
                    <div className="flex gap-1 flex-wrap justify-end max-w-[180px]">
                      {story.hashtags.slice(0, 3).map((tag) => (
                        <span key={tag} className="text-[9px] text-indigo-400/70">#{tag}</span>
                      ))}
                    </div>
                  )}
                  <span className="text-[10px] text-indigo-400/0 group-hover:text-indigo-400/60 transition-colors font-medium">
                    Open →
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
